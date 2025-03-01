import os
import dotenv
import hmac
import hashlib
import json
import requests
import base64
import tempfile
from datetime import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify
from github import GithubIntegration, Github

from utils import container, checker, llm 

dotenv.load_dotenv()

DB_FILE = r"data.json"

webhook_app = Blueprint('webhook', __name__)

# GitHub App configuration
GITHUB_APP_ID: str = os.environ['GITHUB_APP_ID']
GITHUB_PRIVATE_KEY_PATH: str = os.environ['GITHUB_PRIVATE_KEY_PATH']
GITHUB_WEBHOOK_SECRET: str = os.environ.get('GITHUB_WEBHOOK_SECRET', '')

with open(GITHUB_PRIVATE_KEY_PATH, 'r') as key_file:
    GITHUB_PRIVATE_KEY: str = key_file.read()

github_integration = GithubIntegration(GITHUB_APP_ID, GITHUB_PRIVATE_KEY)

# ----------------------
# JSON Database Functions
# ----------------------
def load_db() -> Dict[str, Any]:
    """Load the JSON database from file; if not present or invalid, return default structure."""
    if not os.path.exists(DB_FILE):
        return {"repos": {}}
    with open(DB_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"repos": {}}
    return data

def save_db(data: Dict[str, Any]) -> None:
    """Save the given dictionary to the JSON database file."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_db(repo_name: str, event: str, pr_number: int, extra: Dict[str, Any]) -> None:
    """
    Update the JSON database with an event for a repository.
    
    Args:
        repo_name: Full name of the repository (e.g., "owner/repo").
        event: A string describing the event (e.g., "pull_request_opened", "sandbox_analysis").
        pr_number: The pull request number.
        extra: A dict with extra details (e.g., filename, output, logs).
    """
    data = load_db()
    if "repos" not in data:
        data["repos"] = {}
    if repo_name not in data["repos"]:
        data["repos"][repo_name] = {"pr_events": []}
    event_data = {
        "event": event,
        "pr_number": pr_number,
        "extra": extra,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    data["repos"][repo_name]["pr_events"].append(event_data)
    save_db(data)

# ----------------------
# Helper Functions
# ----------------------
def is_valid_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verify the HMAC signature of the incoming webhook request.
    """
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(f'sha256={mac.hexdigest()}', signature)

# ----------------------
# Event Handling
# ----------------------
def handle_pull_request(payload: Dict[str, Any]) -> None:
    """
    Handle a new pull request event by commenting and performing sandbox analysis.
    Also updates the JSON database with detailed logs.
    """
    repo_name = payload['repository']['full_name']
    pr_number = payload['pull_request']['number']
    pr_url = payload['pull_request']['url']
    pr_title = payload['pull_request']['title']
    pr_body = payload['pull_request']['body']

    PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment="Thanks for the pull request! 🎉")
    update_db(repo_name, "llm_review", pr_number, {"filename": "xyz.py", "review": "Thanks for the pull request! 🎉"})
    update_db(repo_name, "llm_review", pr_number, {"filename": "xyz.py", "review": "Thanks for the pull request2! 🎉"})

    # You can include an LLM review for modified files here.
    # files = requests.get(f'{pr_url}/files').json()
    # for file in files:
    #     if file['status'] != 'modified':
    #         continue
    #     filename = file['filename']
    #     diff = file.get('patch', '')
    #     review = llm.get_review(pr_title, pr_body, filename, diff)
    #     formatted_review = f"# Review for `{filename}`\n{review}"
    #     PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=formatted_review)
    #     update_db(repo_name, "llm_review", pr_number, {"filename": filename, "review": review})

    # Process added files for sandbox analysis
    files = requests.get(f'{pr_url}/files').json()
    for file in files:
        if file['status'] != 'added':
            continue

        contents_response = requests.get(file['contents_url'])
        if contents_response.status_code != 200:
            continue
        file_info = contents_response.json()
        encoded_contents = file_info.get('content')
        if not encoded_contents:
            continue
        file_contents = base64.b64decode(encoded_contents)

        if not checker.check_executable(file_contents):
            continue

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, os.path.basename(file['filename']))
            with open(file_path, 'wb') as f:
                f.write(file_contents)

            image_name = 'sandbox-container'
            context_path = './sandbox/'
            container.build_container(image_name, context_path)
            output = container.run_container(image_name, temp_dir)
            formatted_output = f"# Sandbox Analysis for `{file['filename']}`\n{output}"
            
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=formatted_output)
            
            update_db(repo_name, "sandbox_analysis", pr_number, {
                "filename": file['filename'],
                "sandbox_output": output
            })

# ----------------------
# Blueprint Routes
# ----------------------
@webhook_app.route('/', methods=['POST'])
def webhook() -> Any:
    signature = request.headers.get('X-Hub-Signature-256')
    if not is_valid_signature(request.data, signature):
        return jsonify({'message': 'Invalid signature'}), 403

    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    print(f"Received event {event}")
    #print(payload)

    if event == 'pull_request' and payload['action'] in ['opened', 'synchronize']:
        handle_pull_request(payload)

    return jsonify({'message': 'Event received'}), 200

@webhook_app.route('/test', methods=['GET'])
def test() -> Any:
    return jsonify({'message': 'Webhook is working!'}), 200

# ----------------------
# PR Utilities Class
# ----------------------
class PRUtils:
    """
    A utility class for interacting with GitHub pull requests.
    """
    @staticmethod
    def comment(repo_name: str, pr_number: int, comment: str) -> None:
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)
        repo = github.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)
        pull_request.create_issue_comment(comment)

    @staticmethod
    def list_open_prs(repo_name: str) -> List[Dict[str, Any]]:
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)
        repo = github.get_repo(repo_name)
        pulls = repo.get_pulls(state='open', sort='created')
        return [{"number": pr.number, "title": pr.title, "author": pr.user.login} for pr in pulls]

    @staticmethod
    def close_pr(repo_name: str, pr_number: int) -> None:
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)
        repo = github.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)
        pull_request.edit(state='closed')

    @staticmethod
    def _get_access_token(repo_name: str) -> str:
        if not github_integration:
            raise Exception("GitHub integration not initialized.")
        owner, repo = repo_name.split('/')
        installation_id = github_integration.get_installation(owner, repo).id
        return github_integration.get_access_token(installation_id).token
