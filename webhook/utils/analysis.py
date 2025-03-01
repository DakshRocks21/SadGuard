# analysis.py (server 1)
from flask import Blueprint, request, jsonify, abort
import os
import tempfile
import base64
from datetime import datetime
from utils import container, checker 
import requests
import json

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/trigger-analysis', methods=['POST'])
def trigger_analysis():
    """
    Trigger a code analysis on server 1.

    Expected JSON payload:
      {
          "repo_name": "owner/repo",
          "pr_number": <number>,
          "file_url": "<url for file contents>"
      }
    """
    data = request.get_json()
    if not data:
        abort(400, "Invalid JSON payload")
    
    repo_name = data.get('repo_name')
    pr_number = data.get('pr_number')
    file_url = data.get('file_url')

    if not (repo_name and pr_number and file_url):
        abort(400, "Missing required parameters")

    try:
        response = requests.get(file_url)
        if response.status_code != 200:
            abort(400, "Could not fetch file contents")
        file_info = response.json()
        encoded_contents = file_info.get('content')
        if not encoded_contents:
            abort(400, "No content found in file response")
        file_contents = base64.b64decode(encoded_contents)

        if not checker.check_executable(file_contents):
            return jsonify({"message": "File is not executable; skipping analysis"}), 200

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "analyzed_file")
            with open(file_path, 'wb') as f:
                f.write(file_contents)

            # Build or ensure the container is ready.
            image_name = 'sandbox-container'
            context_path = './sandbox/'
            container.build_container(image_name, context_path)
            output = container.run_container(image_name, temp_dir)


        analysis_event = {
            "repo_name": repo_name,
            "pr_number": pr_number,
            "sandbox_output": output,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return jsonify({"message": "Analysis completed", "analysis_result": output})
    except Exception as e:
        abort(500, f"Error during analysis: {str(e)}")
        
DB_FILE = r"data.json"

def load_db() -> dict:
    """Load the JSON database from the file."""
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    return data

@analysis_bp.route('/sandbox-output', methods=['GET'])
def get_sandbox_output():
    """
    Retrieve sandbox analysis output for a repository and PR.
    Expected query parameters:
      - repo_name: full name of the repository (e.g., "owner/repo")
      - pr_number: pull request number
    """
    repo_name = request.args.get('repo_name')
    pr_number = request.args.get('pr_number')
    
    if not repo_name or not pr_number:
        abort(400, "Missing required parameters: repo_name and pr_number")

    try:
        data = load_db()
        repo_data = data.get("repos", {}).get(repo_name, {})
        print(repo_data)
        pr_events = repo_data.get("pr_events", [])

        sandbox_events = [
            event for event in pr_events 
            if event.get("event") == "sandbox_analysis" and str(event.get("pr_number")) == pr_number
        ]
        return jsonify(sandbox_events)
    except Exception as e:
        abort(500, f"Error retrieving sandbox output: {str(e)}")
        
@analysis_bp.route('/llm-review-output', methods=['GET'])
def get_llm_review_output():
    """
    Retrieve LLM review output for a repository and pull request.
    Expected query parameters:
      - repo_name: full name of the repository (e.g., "owner/repo")
      - pr_number: pull request number
    """
    repo_name = request.args.get('repo_name')
    pr_number = request.args.get('pr_number')
    
    if not repo_name or not pr_number:
        abort(400, "Missing required parameters: repo_name and pr_number")

    try:
        data = load_db()
        repo_data = data.get("repos", {}).get(repo_name, {})
        pr_events = repo_data.get("pr_events", [])

        llm_review_events = [
            event for event in pr_events 
            if event.get("event") == "llm_review" and str(event.get("pr_number")) == pr_number
        ]
        return jsonify(llm_review_events)
    except Exception as e:
        abort(500, f"Error retrieving LLM review output: {str(e)}")