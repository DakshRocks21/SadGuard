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
import subprocess
from utils import container, checker, llm, analysis


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
    repo_url = payload['repository']['clone_url']
    repo_name = payload['repository']['full_name']
    pr_number = payload['pull_request']['number']
    pr_url = payload['pull_request']['url']
    pr_title = payload['pull_request']['title']
    pr_body = payload['pull_request']['body']
    dockerfile_relative = os.path.join('.sadguard', 'Dockerfile')
    image_name = 'sandbox-container'

    PRUtils.comment(
        repo_name=repo_name,
        pr_number=pr_number,
        comment="Thanks for the pull request! 🎉"
    )
    update_db(repo_name, "PR_OPENED", pr_number, {"review": "Thanks for the pull request! 🎉"})

    is_dockerfile_modified = False
    is_wrapper_modified = False

    files = requests.get(f'{pr_url}/files').json()
    for file in files:
        print(file)
        print(file['filename'])
        if file['status'] != 'modified': continue
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
        
    # Check if Dockerfile is modified
    if is_dockerfile_modified and is_wrapper_modified:
        warning_message = ".sadguard/Dockerfile or .sadguard/wrapper.sh is modified."
        PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=warning_message)
        update_db(repo_name, "SADGUARD_CONFIG_MODIFIED", pr_number, {"error": warning_message})
        

    pr_branch = payload.get("pull_request", {}).get("head", {}).get("ref")
    if not pr_branch:
        error_msg = "Could not determine pull request branch from payload."
        PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
        update_db(repo_name, "clone_error", pr_number, {"error": error_msg})
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
            update_db(repo_name, "clone_error", pr_number, {"error": error_msg})
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
            update_db(repo_name, "build_error", pr_number, {"error": error_msg})
            return

        try:
            result = container.run_container(image_name=image_name, timeout=60)
        except Exception as e:
            error_msg = f"Error while running container: {e}"
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
            update_db(repo_name, "container_run_error", pr_number, {"error": error_msg})
            return

        test_logs = result.get("logs", "No logs captured.")
        exit_code = result.get("exit_code", -1)

        code_output = analysis.extract_section(test_logs, "Code Output")
        result = analysis.extract_section(test_logs, "Code Error")
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
        
        
        # Always include complete test logs (code output and error).
        comment_message += (
            "## Complete Test Logs\n"
            "### Unit Tests\n"
            "```\n"
            f"{code_output}\n"
            "```\n"
            "### Code Error\n"
            "```\n"
            f"{result}\n"
            "```\n"
        )

        PRUtils.comment(
            repo_name=repo_name,
            pr_number=pr_number,
            comment=comment_message
        )
        update_db(repo_name, "TESTS_COMPLETE", pr_number, {"result": result})
        
        

    # # Process added files for sandbox analysis
    # files = requests.get(f'{pr_url}/files').json()
    # for file in files:
    #     if file['status'] != 'added':
    #         continue

    #     contents_response = requests.get(file['contents_url'])
    #     if contents_response.status_code != 200:
    #         continue
    #     file_info = contents_response.json()
    #     encoded_contents = file_info.get('content')
    #     if not encoded_contents:
    #         continue
    #     file_contents = base64.b64decode(encoded_contents)

    #     if not checker.check_executable(file_contents):
    #         continue

    #     with tempfile.TemporaryDirectory() as temp_dir:
    #         file_path = os.path.join(temp_dir, os.path.basename(file['filename']))
    #         with open(file_path, 'wb') as f:
    #             f.write(file_contents)

    #         image_name = 'sandbox-container'
    #         context_path = './sandbox/'
    #         container.build_container(image_name, context_path)
    #         output = container.run_container(image_name, temp_dir)
    #         formatted_output = f"# Sandbox Analysis for `{file['filename']}`\n{output}"
            
    #         PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=formatted_output)
            
    #         update_db(repo_name, "sandbox_analysis", pr_number, {
    #             "filename": file['filename'],
    #             "sandbox_output": output
    #         })
    
    # # --- Network Analysis ---
    # # Build and run a container that executes your network analysis shell script.
    # # The Dockerfile in './network_analysis/' should include your network analysis script.
    # try:
    #     network_image = 'network-analysis-container'
    #     network_context = './network_analysis/'
    #     container.build_container(network_image, network_context)
    # except Exception as e:
    #     PRUtils.comment(repo_name, pr_number, f"Error building network analysis container: {e}")
    #     return

    # with tempfile.TemporaryDirectory() as net_temp_dir:
    #     network_output = container.run_container(network_image, net_temp_dir)
    
    # # Retrieve repository context (e.g., description, full name) for LLM analysis.
    # access_token = PRUtils._get_access_token(repo_name)
    # github = Github(access_token)
    # repo_object = github.get_repo(repo_name)
    # repo_description = repo_object.description or "No description available."
    # repo_context = f"Repository: {repo_object.full_name}\nDescription: {repo_description}"

    # # Run the LLM analysis on the network output using the generated context.
    # network_review = llm.get_network_analysis_output(repo_context, network_output)
    # formatted_network_review = f"# Network Analysis Report\n{network_review}"
    
    # # Post the network analysis review as a comment.
    # PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=formatted_network_review)
    # update_db(repo_name, "network_analysis", pr_number, {
    #     "network_output": network_output,
    #     "llm_review": network_review
    # })
            
    

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

    if event == 'pull_request' : #and payload['action'] in ['opened', 'synchronize']:
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
