import os
import dotenv
import hmac
import hashlib
import requests
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify
from github import GithubIntegration, Github
from sqlmodel import Session
from models import PREvent, engine  # also import your other models if needed
from utils import container, checker, llm, analysis  # your utility modules

dotenv.load_dotenv()

webhook_app = Blueprint('webhook', __name__)

# GitHub App configuration
GITHUB_APP_ID: str = os.environ['GITHUB_APP_ID']
GITHUB_PRIVATE_KEY_PATH: str = os.environ['GITHUB_PRIVATE_KEY_PATH']
GITHUB_WEBHOOK_SECRET: str = os.environ.get('GITHUB_WEBHOOK_SECRET', '')

with open(GITHUB_PRIVATE_KEY_PATH, 'r') as key_file:
    GITHUB_PRIVATE_KEY: str = key_file.read()

github_integration = GithubIntegration(GITHUB_APP_ID, GITHUB_PRIVATE_KEY)

def is_valid_signature(payload_body: bytes, signature: str) -> bool:
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(f'sha256={mac.hexdigest()}', signature)

def update_event(repo_name: str, event: str, pr_number: int, extra: Dict[str, Any]) -> None:
    with Session(engine) as session:
        new_event = PREvent(
            repo_name=repo_name,
            event=event,
            pr_number=pr_number,
            extra=extra
        )
        session.add(new_event)
        session.commit()

def handle_pull_request(payload: Dict[str, Any]) -> None:
    repo_url = payload['repository']['clone_url']
    repo_name = payload['repository']['full_name']
    pr_number = payload['pull_request']['number']
    pr_url = payload['pull_request']['url']
    pr_title = payload['pull_request']['title']
    pr_body = payload['pull_request']['body']
    dockerfile_relative = os.path.join('.sadguard', 'Dockerfile')
    image_name = 'sandbox-container'

    # Example: leave a comment and log the event
    PRUtils.comment(
        repo_name=repo_name,
        pr_number=pr_number,
        comment="Thanks for the pull request! 🎉"
    )
    update_event(repo_name, "PR_OPENED", pr_number, {"review": "Thanks for the pull request! 🎉"})

    is_dockerfile_modified = False
    is_wrapper_modified = False

    files = requests.get(f'{pr_url}/files').json()
    for file in files:
        if file['status'] != 'modified':
            continue
        if file['filename'] == ".sadguard/Dockerfile":
            is_dockerfile_modified = True
            continue
        if file['filename'] == ".sadguard/wrapper.sh":
            is_wrapper_modified = True
            continue
        filename = file['filename']
        diff = file['patch']
        review = llm.get_review(pr_title, pr_body, filename, diff)
        formatted_review = f"# Review for `{filename}`\n{review}"
        PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=formatted_review)
    
    if is_dockerfile_modified and is_wrapper_modified:
        warning_message = ".sadguard/Dockerfile or .sadguard/wrapper.sh is modified."
        PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=warning_message)
        update_event(repo_name, "SADGUARD_CONFIG_MODIFIED", pr_number, {"error": warning_message})
    
    pr_branch = payload.get("pull_request", {}).get("head", {}).get("ref")
    if not pr_branch:
        error_msg = "Could not determine pull request branch from payload."
        PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
        update_event(repo_name, "clone_error", pr_number, {"error": error_msg})
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            subprocess.check_call([
                "git", "clone",
                "--branch", pr_branch,
                "--single-branch",
                repo_url,
                temp_dir
            ])
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to clone repository on branch '{pr_branch}': {e}"
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
            update_event(repo_name, "clone_error", pr_number, {"error": error_msg})
            return

        full_dockerfile_path = os.path.join(temp_dir, dockerfile_relative)
        try:
            container.build_container(
                image_name=image_name,
                context_path=temp_dir,
                dockerfile=full_dockerfile_path
            )
        except Exception as e:
            error_msg = f"Error during container build: {e}"
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
            update_event(repo_name, "build_error", pr_number, {"error": error_msg})
            return

        try:
            result = container.run_container(image_name=image_name, timeout=60)
        except Exception as e:
            error_msg = f"Error while running container: {e}"
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
            update_event(repo_name, "container_run_error", pr_number, {"error": error_msg})
            return

        test_logs = result.get("logs", "No logs captured.")
        exit_code = result.get("exit_code", -1)

        code_output = analysis.extract_section(test_logs, "Code Output")
        result_section = analysis.extract_section(test_logs, "Code Error")
        mitm_log = analysis.extract_section(test_logs, "Mitmproxy Log (HTTP/HTTPS flows)")
        tcpdump_log = analysis.extract_section(test_logs, "Tcpdump Log (All network traffic)")

        is_mitm_valid = len(mitm_log.split("\n")) > 4
        is_tcpdump_valid = len(tcpdump_log.split("\n")) > 10

        mitm_review = llm.get_network_analysis_output(mitm_log) if is_mitm_valid else "Not enough Mitmproxy logs captured."
        tcpdump_review = llm.get_network_analysis_output(tcpdump_log) if is_tcpdump_valid else "No / Not enough Tcpdump logs captured."

        comment_message = f"## Sandbox Analysis\nExit code: {exit_code}\n\n"
        comment_message += (
            "### Mitmproxy Analysis\n"
            f"{mitm_review}\n"
        )
        comment_message += (
            "### Tcpdump Analysis\n"
            f"{tcpdump_review}\n"
        )
        comment_message += (
            "## Complete Test Logs\n"
            "### Unit Tests\n"
            "```\n"
            f"{code_output}\n"
            "```\n"
            "### Code Error\n"
            "```\n"
            f"{result_section}\n"
            "```\n"
        )
        PRUtils.comment(
            repo_name=repo_name,
            pr_number=pr_number,
            comment=comment_message
        )
        update_event(repo_name, "TESTS_COMPLETE", pr_number, {"result": result_section})

# Blueprint routes
@webhook_app.route('/', methods=['POST'])
def webhook() -> Any:
    signature = request.headers.get('X-Hub-Signature-256')
    if not is_valid_signature(request.data, signature):
        return jsonify({'message': 'Invalid signature'}), 403

    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    print(f"Received event {event}")

    if event == 'pull_request':  # and payload['action'] in ['opened', 'synchronize']:
        handle_pull_request(payload)

    return jsonify({'message': 'Event received'}), 200

@webhook_app.route('/test', methods=['GET'])
def test() -> Any:
    return jsonify({'message': 'Webhook is working!'}), 200

# ----------------------
# PR Utilities Class remains unchanged
class PRUtils:
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
