# backend/routes/auth.py
from flask import Blueprint, request, redirect, jsonify, session
import requests, os

auth_bp = Blueprint('auth', __name__)

GITHUB_CLIENT_ID = os.environ['GITHUB_CLIENT_ID']
GITHUB_CLIENT_SECRET = os.environ['GITHUB_CLIENT_SECRET']
REDIRECT_URI = os.environ.get('GITHUB_REDIRECT_URI', 'http://localhost:5173/auth/github/callback')

@auth_bp.route('/github/login')
def github_login():
    return redirect(
        f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=read:user,repo,read:org"
    )


@auth_bp.route('/github/callback')
def github_callback():
    code = request.args.get('code')
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Accept": "application/json"}
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    if not access_token:
        return jsonify({"error": "Authentication failed"}), 400

    session['access_token'] = access_token

    return redirect("http://localhost:3000/dashboard")

@auth_bp.route('/logout')
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})
