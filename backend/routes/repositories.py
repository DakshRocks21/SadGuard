from flask import Blueprint, session, jsonify, abort
from github import Github, Auth
import os
import json

repos_bp = Blueprint('repos', __name__)

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

@repos_bp.route('/repos', methods=['GET'])
def get_repos():
    access_token = session.get('access_token')
    if not access_token:
        abort(401, "Not authenticated")

    auth = Auth.Token(access_token)
    g = Github(auth=auth)
    
    installed_repos = []
    try:
        user = g.get_user()
        db_data = load_db()
        bot_repos = db_data.get("repos", {}) 

        for repo in user.get_repos():
            if repo.full_name in bot_repos:
                repo_info = {
                    "full_name": repo.full_name,
                    "html_url": repo.html_url,
                    "bot_data": bot_repos[repo.full_name]  
                }
                installed_repos.append(repo_info)
    except Exception as e:
        abort(500, str(e))
    finally:
        g.close()
        
    return jsonify(installed_repos)
