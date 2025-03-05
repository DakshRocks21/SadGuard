import requests
import dotenv
import os
dotenv.load_dotenv("../.env")

GITHUB_APP_CLIENT_ID = os.environ['GITHUB_CLIENT_ID']
GITHUB_APP_CLIENT_SECRET = os.environ['GITHUB_CLIENT_SECRET']

def login_oauth(code: str) -> requests.Response:
    r = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_APP_CLIENT_ID,
            "client_secret": GITHUB_APP_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )
    return r


def get_user(token: str) -> requests.Response:
    r = requests.get(
        "https://api.github.com/user",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    return r


def get_repos(token: str) -> requests.Response:
    r = requests.get(
        "https://api.github.com/user/repos",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    return r


def get_repos_branches(token: str, repos: list) -> requests.Response:
    final = []
    for repo in repos:
        r = requests.get(
            f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}/branches",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        repo["branches"] = r.json()
        final.append(repo)
    return final


def get_commits(token: str, owner: str, repo: str, branch: str) -> requests.Response:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits",
        headers={"Authorization": f"Bearer {token}"},
        params={"sha": branch},
    )
    return r


def get_commit(token: str, owner: str, repo: str, sha: str) -> requests.Response:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return r
