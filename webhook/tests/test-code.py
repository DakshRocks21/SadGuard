"""Simple test script to exercise handle_pull_request and reproduce logging-driver issues.

Usage:
    python -m tests.test-code

This script will:
- Import the webhook handler
- Monkeypatch PRUtils.comment/upsert_progress_comment and update_event to avoid GitHub/DB calls
- Stub requests.get to return an empty file list (so no file diffs are processed)
- Call handle_pull_request with the PR URL you provided

Adjust constants below if you want a different PR or behavior.
"""
import sys
import json
import traceback

# Ensure project root is on sys.path when running as a module
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import webhook as webhook_module

# Safety stubs to avoid making real GitHub or DB calls during this debug run
def noop_comment(repo_name, pr_number, comment=None):
    print(f"[PR COMMENT stub] repo={repo_name} pr={pr_number} comment_len={len(comment) if comment else 0}")

def noop_upsert(repo_name, pr_number, body, marker='<!-- sadguard-progress -->'):
    print(f"[PR PROGRESS upsert stub] repo={repo_name} pr={pr_number} body_len={len(body) if body else 0}")

def noop_update_event(repo_name, event, pr_number, extra=None):
    print(f"[UPDATE_EVENT stub] repo={repo_name} event={event} pr={pr_number} extra={extra}")

# Stub requests.get so webhook doesn't try to call GitHub API unauthenticated
class DummyResponse:
    def __init__(self, data):
        self._data = data
    def json(self):
        return self._data

def dummy_requests_get(url, *args, **kwargs):
    print(f"[requests.get stub] called: {url}")
    # If URL ends with /files, return an empty list (no modified files)
    if url.endswith('/files'):
        return DummyResponse([])
    return DummyResponse({})


def main():
    # Apply stubs
    webhook_module.PRUtils.comment = staticmethod(noop_comment)
    webhook_module.PRUtils.upsert_progress_comment = staticmethod(noop_upsert)
    webhook_module.update_event = noop_update_event
    webhook_module.requests.get = dummy_requests_get

    # The PR you asked to test
    pr_api_url = 'https://api.github.com/repos/DakshRocks21/test-part-20/pulls/1'

    payload = {
        'repository': {
            'clone_url': 'https://github.com/DakshRocks21/test-part-20.git',
            'full_name': 'DakshRocks21/test-part-20'
        },
        'pull_request': {
            'number': 1,
            'url': pr_api_url,
            'title': 'Test repro PR',
            'body': 'Trigger sandbox run to debug logging-driver fallback',
            'head': {'ref': 'new-code'}
        }
    }

    try:
        print("Calling handle_pull_request... (this may clone the repo and build a container)")
        webhook_module.handle_pull_request(payload)
        print("handle_pull_request returned normally")
    except Exception as e:
        print("Exception while running handle_pull_request:")
        traceback.print_exc()


if __name__ == '__main__':
    main()
