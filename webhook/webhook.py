from flask import Flask, request, jsonify
from github import GithubIntegration, Github
import hmac
import hashlib
import os
import dotenv
from typing import Dict, Any, List
from flask import Blueprint

# Define the blueprint
webhook_app = Blueprint('webhook', __name__)

dotenv.load_dotenv()

app = Flask(__name__)

GITHUB_APP_ID: str = os.environ['GITHUB_APP_ID']
GITHUB_PRIVATE_KEY_PATH: str = os.environ['GITHUB_PRIVATE_KEY_PATH']
GITHUB_WEBHOOK_SECRET: str = os.environ.get('GITHUB_WEBHOOK_SECRET', '')

with open(GITHUB_PRIVATE_KEY_PATH, 'r') as key_file:
    GITHUB_PRIVATE_KEY: str = key_file.read()

github_integration = GithubIntegration(GITHUB_APP_ID, GITHUB_PRIVATE_KEY)

@webhook_app.route('/', methods=['POST'])
def webhook() -> Any:
    signature = request.headers.get('X-Hub-Signature-256')
    if not is_valid_signature(request.data, signature):
        return jsonify({'message': 'Invalid signature'}), 403

    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    print(f"Received event {event}")
    print(payload)

    if event == 'pull_request' and (payload['action'] == 'opened' or payload['action'] == 'synchronize'):
        handle_pull_request(payload)

    return jsonify({'message': 'Event received'}), 200

@webhook_app.route('/test', methods=['GET'])
def test() -> Any:
    """
    Test route to check if the webhook is working. If this is down, something is wrong with the webhook
    route.com/webhook/test/
    """
    return jsonify({'message': 'Webhook is working!'}), 200


def is_valid_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verify the HMAC signature of the incoming webhook request.

    Args:
        payload_body (bytes): Raw payload of the request body.
        signature (str): The HMAC signature from the webhook headers.

    Returns:
        bool: Whether the signature is valid.
        
    Please dont ask me why I am using this function, I just copied it from somewhere 
    """
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(f'sha256={mac.hexdigest()}', signature)


def handle_pull_request(payload: Dict[str, Any]) -> None:
    """
    Handle a new pull request and comment on it with details.

    Args:
        payload (Dict[str, Any]): The payload from the GitHub webhook.
    # TODO: Implement this function to run things properly
    """
    
    
    repo_name = payload['repository']['full_name']
    pr_number = payload['pull_request']['number']

    # Post a comment using the utility function
    PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment="👋 Thanks for your pull request!")


# === MODULE INTERFACE ===
class PRUtils:
    """
    A utility class for interacting with GitHub pull requests programmatically.
    """
    @staticmethod
    def comment(repo_name: str, pr_number: int, comment: str) -> None:
        """
        Post a comment on a pull request.

        Args:
            repo_name (str): The full name of the repository (e.g., "owner/repo").
            pr_number (int): The pull request number.
            comment (str): The body of the comment to post.
        """
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)

        repo = github.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)
        pull_request.create_issue_comment(comment)

    @staticmethod
    def list_open_prs(repo_name: str) -> List[Dict[str, Any]]:
        """
        List all open pull requests for a repository.

        Args:
            repo_name (str): The full name of the repository (e.g., "owner/repo").

        Returns:
            List[Dict[str, Any]]: A list of open pull requests with basic details.
        """
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)

        repo = github.get_repo(repo_name)
        pulls = repo.get_pulls(state='open', sort='created')
        return [{"number": pr.number, "title": pr.title, "author": pr.user.login} for pr in pulls]

    @staticmethod
    def close_pr(repo_name: str, pr_number: int) -> None:
        """
        Close a pull request without merging.

        Args:
            repo_name (str): The full name of the repository (e.g., "owner/repo").
            pr_number (int): The pull request number.
        """
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)

        repo = github.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)
        pull_request.edit(state='closed')

    @staticmethod
    def _get_access_token(repo_name: str) -> str:
        """
        Get the access token for a repository.

        Args:
            repo_name (str): The full name of the repository (e.g., "owner/repo").

        Returns:
            str: The access token for the repository.
        """
        if not github_integration:
            raise Exception("GitHub integration not initialized.")
        
        owner, repo = repo_name.split('/')
        
        installation_id = github_integration.get_installation(owner, repo).id
        
        return github_integration.get_access_token(installation_id).token
