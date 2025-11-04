import os
import dotenv
import hmac
import hashlib
import requests
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify
from github import GithubIntegration, Github
from sqlmodel import Session
from models import PREvent, engine, PRRun, AIReview  # also import your other models if needed
from utils import container, checker, llm, analysis  # your utility modules
from jinja2 import Environment, FileSystemLoader
import json

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
    dockerfile_relative = Path('.sadguard', 'Dockerfile').as_posix()
    image_name = 'sandbox-container'
    progress_comment_marker = '<!-- sadguard-progress -->'
    progress_comment_cached_id: Optional[int] = None

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
    diffs_list: List[Dict[str, str]] = []
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
        diffs_list.append({"filename": filename, "diff": diff})
    # Keep old single-file review call for reference (commented out):
    # review = llm.get_review(pr_title, pr_body, filename, diff)
    # formatted_review = f"# Review for `{filename}`\n{review}"
    # PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=formatted_review)

    # We'll perform an iterative LLM review loop over all diffs below and post consolidated results.
    
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
        print("Repository cloned to", temp_dir)
        full_dockerfile_path = Path(temp_dir, dockerfile_relative).as_posix()
        print("Using Dockerfile at", full_dockerfile_path)
        # Detect project environment and dynamically generate .sadguard files if not present
        sadguard_dir = Path(temp_dir, '.sadguard')
        sadguard_dir.mkdir(parents=True, exist_ok=True)

        # Simple environment detection
        repo_files = {p.name for p in Path(temp_dir).glob('*')}
        language = 'python'
        install_cmd = "pip install -r requirements.txt"
        test_command = "ENV DEFAULT_CMD=\"pytest -v tests/test_app.py\""
        base_image = 'python:3.10-slim'

        if (Path(temp_dir) / 'package.json').is_file():
            language = 'node'
            base_image = 'node:18-bullseye'
            install_cmd = 'npm install'
            # try to read package.json to get test script
            try:
                pkg = json.load(open(Path(temp_dir) / 'package.json'))
                scripts = pkg.get('scripts', {})
                test_command = scripts.get('test', 'npm test')
            except Exception:
                test_command = 'npm test'

        elif (Path(temp_dir) / 'pyproject.toml').is_file() or (Path(temp_dir) / 'requirements.txt').is_file():
            language = 'python'
            base_image = 'python:3.10-slim'
            install_cmd = 'pip install -r requirements.txt' if (Path(temp_dir) / 'requirements.txt').is_file() else 'pip install .'

        # If user provided .sadguard/Dockerfile in PR, prefer it
        provided_dockerfile = Path(temp_dir, '.sadguard', 'Dockerfile')
        provided_wrapper = Path(temp_dir, '.sadguard', 'wrapper.sh')

        if not provided_dockerfile.is_file() or not provided_wrapper.is_file():
            # Render templates from project templates directory
            templates_path = Path(__file__).resolve().parents[1] / 'templates'
            env = Environment(loader=FileSystemLoader(str(templates_path)))
            docker_tpl = env.get_template('Dockerfile.j2')
            wrapper_tpl = env.get_template('wrapper.sh.j2')

            rendered_docker = docker_tpl.render(
                language=language,
                install_cmd=install_cmd,
                base_image=base_image,
                test_command=test_command,
            )
            rendered_wrapper = wrapper_tpl.render(
                test_command=test_command
            )

            # Write generated files
            provided_dockerfile.write_text(rendered_docker)
            provided_wrapper.write_text(rendered_wrapper, encoding='utf-8')

        assert Path(temp_dir, '.sadguard', 'Dockerfile').is_file()

        # Create a PRRun entry before build so we can attach metadata and persist progress_comment_id
        pr_run = PRRun(repo_name=repo_name, pr_number=pr_number, run_status="building", image_name=image_name)
        with Session(engine) as session:
            session.add(pr_run)
            session.commit()
            session.refresh(pr_run)

        # --- Perform iterative LLM review loop on code diffs before building/running sandbox ---
        try:
            code_questions = [
                "Does the change introduce network connections to external hosts? If so, list probable destinations.",
                "Does the diff introduce elevated permissions, use of privileged operations, or system calls that look suspicious?",
                "Are the new or modified files performing filesystem, subprocess, or network operations that could be abused?",
                "When analyzing tcpdump outputs, ignore promiscuous mode warnings or errors — focus on real flows and suspicious connections.",
            ]

            def _store_code_review(iteration: int, content: str):
                try:
                    with Session(engine) as session:
                        ar = AIReview(pr_run_id=pr_run.id, role='assistant', content=content)
                        session.add(ar)
                        session.commit()
                except Exception:
                    pass

            orchestration_code = llm.orchestrate_review_loop(
                pr_title=pr_title,
                pr_body=pr_body,
                diffs=diffs_list,
                run_results=None,
                analysis_results=None,
                questions=code_questions,
                max_iterations=3,
                store_callback=_store_code_review,
            )

            # Create a consolidated PR comment with all AI-generated data from the loop
            try:
                combined_parts = ["## Iterative LLM Code Review (SadGuard)\n"]
                for item in orchestration_code:
                    itr = item.get('iteration')
                    content = item.get('content', '')
                    combined_parts.append(f"### Iteration {itr}\n")
                    combined_parts.append(content)
                    combined_parts.append("\n---\n")
                combined_comment = "\n".join(combined_parts)
                # Upsert the consolidated code-review comment and persist its id on PRRun
                try:
                    with Session(engine) as session:
                        comment_id = pr_run.code_review_comment_id
                    created_id = PRUtils.upsert_progress_comment(repo_name=repo_name, pr_number=pr_number, body=combined_comment, marker=progress_comment_marker, comment_id=comment_id)
                    if created_id and (pr_run.code_review_comment_id != created_id):
                        with Session(engine) as session:
                            pr_run.code_review_comment_id = created_id
                            session.add(pr_run)
                            session.commit()
                except Exception:
                    # fallback to create a normal comment
                    try:
                        PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=combined_comment)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            # If orchestration fails, continue to build/run sandbox
            pass

        try:
            container.build_container(
                image_name=image_name,
                context_path=temp_dir,
                dockerfile=dockerfile_relative
            )
        except Exception as e:
            error_msg = f"Error during container build: {e}"
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=error_msg)
            update_event(repo_name, "build_error", pr_number, {"error": error_msg})
            with Session(engine) as session:
                pr_run.run_status = "build_error"
                pr_run.notes = error_msg
                session.add(pr_run)
                session.commit()
            return

        # Run the container with streaming logs and stats. We'll stream incremental comments.
        aggregated_logs = []
        last_comment_time = datetime.utcnow()

        def logs_callback(chunk: str):
            # accumulate and occasionally post to PR
            aggregated_logs.append(chunk)
            nonlocal last_comment_time
            now = datetime.utcnow()
            # Post an incremental comment every ~10 seconds worth of logs
            if (now - last_comment_time).total_seconds() > 10:
                try:
                    snippet = ''.join(aggregated_logs[-50:])
                    comment_text = (
                        f"{progress_comment_marker}\n"
                        "## SadGuard Sandbox Progress\n"
                        "_Streaming logs below (truncated)_\n\n"
                        "```\n"
                        + snippet + "\n```")
                    # Use stored comment id if available for reliable edits
                    with Session(engine) as session:
                        session.add(pr_run)
                        session.commit()
                        comment_id = pr_run.progress_comment_id

                    created_id = PRUtils.upsert_progress_comment(repo_name=repo_name, pr_number=pr_number, body=comment_text, marker=progress_comment_marker, comment_id=comment_id)
                    # persist comment id if newly created
                    if created_id and (not pr_run.progress_comment_id):
                        with Session(engine) as session:
                            pr_run.progress_comment_id = created_id
                            session.add(pr_run)
                            session.commit()
                except Exception:
                    pass
                last_comment_time = now

        def stats_callback(stat: Dict[str, Any]):
            # Optionally, post resource summary as a short status comment
            try:
                summary = f"CPU: {stat.get('cpu_percent'):.2f}% Mem: {stat.get('mem_usage')} / {stat.get('mem_limit')} Net RX/TX: {stat.get('net_rx')}/{stat.get('net_tx')}"
            except Exception:
                summary = str(stat)
            print(summary)
            # Post a short PR comment with stats (could be rate-limited)
            now = datetime.utcnow()
            if (now - last_comment_time).total_seconds() > 30:
                try:
                    comment_text = (
                        f"{progress_comment_marker}\n"
                        "## SadGuard Resource Stats\n"
                        f"{stat}")
                    with Session(engine) as session:
                        comment_id = pr_run.progress_comment_id
                    created_id = PRUtils.upsert_progress_comment(repo_name=repo_name, pr_number=pr_number, body=comment_text, marker=progress_comment_marker, comment_id=comment_id)
                    if created_id and (not pr_run.progress_comment_id):
                        with Session(engine) as session:
                            pr_run.progress_comment_id = created_id
                            session.add(pr_run)
                            session.commit()
                except Exception:
                    pass

        try:
            result = container.run_container_streaming(
                image_name=image_name,
                timeout=300,
                logs_callback=logs_callback,
                stats_callback=stats_callback
            )
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

        # Run the iterative LLM orchestrator with explicit questions and persist each AIReview
        questions = [
            "Does the change introduce network connections to external hosts? If so, list probable destinations.",
            "Does the diff introduce any elevated permissions or privileged operations?",
            "Are the provided tests sufficient to cover new functionality?",
        ]

        def _store_review(iteration: int, content: str):
            print("Storing ", content)
            try:
                with Session(engine) as session:
                    ar = AIReview(pr_run_id=pr_run.id, role='assistant', content=content)
                    session.add(ar)
                    session.commit()
            except Exception:
                pass

        try:
            orchestration = llm.orchestrate_review_loop(
                pr_title=pr_title,
                pr_body=pr_body,
                diffs=diffs_list,
                run_results=code_output,
                analysis_results=(mitm_review + "\n\n" + tcpdump_review),
                questions=questions,
                max_iterations=3,
                store_callback=_store_review,
            )
            print(orchestration)
        except Exception:
            orchestration = []

        # mark PRRun finished
        with Session(engine) as session:
            pr_run.run_status = 'completed'
            pr_run.exit_code = exit_code
            pr_run.finished_at = datetime.utcnow()
            session.add(pr_run)
            session.commit()

        # Build a consolidated AI-loop comment for the sandbox run (agentic review outputs)
        try:
            sandbox_parts = ["## Iterative LLM Sandbox Review (SadGuard)\n"]
            for item in orchestration:
                itr = item.get('iteration')
                content = item.get('content', '')
                sandbox_parts.append(f"### Iteration {itr}\n")
                sandbox_parts.append(content)
                sandbox_parts.append("\n---\n")
            # Include the original structured analysis (kept commented for reviewers) below the AI outputs
            sandbox_parts.append("\n<!-- Original Sandbox Analysis (kept for reference) -->\n")
            sandbox_parts.append("## Sandbox Analysis\n")
            sandbox_parts.append(f"Exit code: {exit_code}\n\n")
            sandbox_parts.append("### Mitmproxy Analysis\n")
            sandbox_parts.append(mitm_review + "\n")
            sandbox_parts.append("### Tcpdump Analysis\n")
            sandbox_parts.append(tcpdump_review + "\n")
            sandbox_parts.append("## Complete Test Logs\n")
            sandbox_parts.append("### Unit Tests\n```")
            sandbox_parts.append(code_output + "\n```")
            sandbox_parts.append("### Code Error\n```")
            sandbox_parts.append(result_section + "\n```")

            consolidated = "\n".join(sandbox_parts)
            # Upsert the consolidated sandbox-review comment and persist its id on PRRun
            try:
                with Session(engine) as session:
                    comment_id = pr_run.sandbox_review_comment_id
                created_id = PRUtils.upsert_progress_comment(repo_name=repo_name, pr_number=pr_number, body=consolidated, marker=progress_comment_marker, comment_id=comment_id)
                if created_id and (pr_run.sandbox_review_comment_id != created_id):
                    with Session(engine) as session:
                        pr_run.sandbox_review_comment_id = created_id
                        session.add(pr_run)
                        session.commit()
            except Exception:
                # fallback to simple comment
                try:
                    PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=consolidated)
                except Exception:
                    pass
        except Exception:
            # Fallback: post the original analysis comment (kept commented in code below)
            # comment_message = f"## Sandbox Analysis\nExit code: {exit_code}\n\n" + ...
            try:
                comment_message = f"## Sandbox Analysis\nExit code: {exit_code}\n\n"\
                    + ("### Mitmproxy Analysis\n" + mitm_review + "\n")\
                    + ("### Tcpdump Analysis\n" + tcpdump_review + "\n")\
                    + ("## Complete Test Logs\n" + "### Unit Tests\n" + "```\n" + code_output + "\n```\n" + "### Code Error\n" + "```\n" + result_section + "\n```\n")
                # PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=comment_message)
                update_event(repo_name, "TESTS_COMPLETE", pr_number, {"result": result_section})
            except Exception:
                pass

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

    @staticmethod
    def upsert_progress_comment(repo_name: str, pr_number: int, body: str, marker: str = '<!-- sadguard-progress -->', comment_id: Optional[int] = None) -> Optional[int]:
        """Create or update a single progress comment marked with `marker`.

        If a comment containing the marker exists on the PR, edit it. Otherwise, create a new comment.
        """
        access_token = PRUtils._get_access_token(repo_name)
        github = Github(access_token)
        repo = github.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)
        try:
            # If we were provided a comment_id, try editing that exact comment first
            if comment_id:
                try:
                    # Use get_issue_comment for issue/pr comments (PyGithub)
                    c = repo.get_issue_comment(comment_id)
                    c.edit(body)
                    return c.id
                except Exception:
                    # fall through to search/create
                    pass

            comments = pull_request.get_issue_comments()
            for c in comments:
                try:
                    if marker in (c.body or ""):
                        c.edit(body)
                        return c.id
                except Exception:
                    continue
        except Exception:
            # fallback: continue to create a comment
            pass

        # create new comment if none edited
        created = pull_request.create_issue_comment(body)
        try:
            return created.id
        except Exception:
            return None
