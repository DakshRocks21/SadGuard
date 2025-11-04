from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Form,
    File,
    UploadFile,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from typing import Annotated, Optional, List
from routers import users, auth, webhooks
from utils.common import hash_password, random_string
from utils.db import Session, get_session, User, create_db_and_tables, Scan, SuspiciousFiles,PREvent
from utils.common import get_current_active_user
from modules.github import *
from werkzeug.utils import secure_filename
import uvicorn
from schemas import Repo, Commit, GetCommits, GetCommit, CommitRef, CommitsResponse, RepoRequest
import requests
from datetime import datetime
import dotenv
import os
dotenv.load_dotenv("../.env")

SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(webhooks.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/repos", response_model=List[Repo])
async def http_get_repos(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    r = get_repos(current_user.github_access_token)
    repos = get_repos_branches(current_user.github_access_token, r)
    return repos


@app.post("/commits", response_model=CommitsResponse)
async def http_get_commits(
    params: GetCommits, current_user: Annotated[User, Depends(get_current_active_user)], session: SessionDep
):
    r = get_commits(
        current_user.github_access_token,
        current_user.username,
        params.repo,
        params.branch,
    )
    # select all scans of this repo
    scans = session.exec(select(Scan).filter(Scan.repo_name == params.repo)).all()
    scan_dict = {}
    for i in scans:
        # get files
        suspicious_files = session.exec(select(SuspiciousFiles).filter(SuspiciousFiles.scan_id == i.id)).all()
        scan_dict[i.commit_sha] = []
        for j in suspicious_files:
            scan_dict[i.commit_sha].append({j.filename: j.reason})
            
        
    commits = r.json()
    return {
        "commits": commits,
        "scans": scan_dict
    }


@app.get("/commit", response_model=Commit)
async def http_get_commit(
    params: GetCommit, current_user: Annotated[User, Depends(get_current_active_user)]
) -> Commit:
    r = get_commit(
        current_user.github_access_token, current_user.username, params.repo, params.sha
    )
    commit = r.json()
    with open("commit.json", "w") as f:
        f.write(str(commit))
    return commit


@app.post("/scan", response_model=List[dict])
async def scan_commit(
    params: GetCommit, current_user: Annotated[User, Depends(get_current_active_user)], session: SessionDep
):
    r = get_commit(
        current_user.github_access_token, current_user.username, params.repo, params.sha
    )
    commit_json = r.json()
    # print(commit_json)
    output_list = []
    if commit_json["files"]:
        files_changed = len(commit_json["files"])
        for i in range(files_changed):
            if "patch" not in commit_json["files"][i]:
                continue
            filename = commit_json["files"][i]["filename"]
            raw_url = commit_json["files"][i]["raw_url"]
            original_code = requests.get(raw_url).text
            code_patch = commit_json["files"][i]["patch"]

            prompt = f"""
            Given {original_code} as the context,
            is this patch malicious: {code_patch}
            
            at the end of your answer add a YES or NO to represent if the code given is malicious anot and surroud your answer with *
            """

            GOOGLE_AI_STUDIO_KEY = os.environ['GOOGLE_AI_STUDIO_KEY']
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GOOGLE_AI_STUDIO_KEY}"
            LLM_query = {"contents": [{"parts": [{"text": f"{prompt}"}]}]}
            LLM_request = requests.post(
                url, json=LLM_query, headers={"Content-Type": "application/json"}
            )
            LLM_response = LLM_request.json()
            LLM_response_text = LLM_response["candidates"][0]["content"]["parts"][0][
                "text"
            ]

            yes_no = LLM_response_text[-6:].upper()
            if "YES" in yes_no:
                # output_list.append({f"{filename}": "YES"})

                prompt = f"why is this malicious ?\n{code_patch}"
                LLM_query = {"contents": [{"parts": [{"text": f"{prompt}"}]}]}
                LLM_request = requests.post(
                    url, json=LLM_query, headers={"Content-Type": "application/json"}
                )
                LLM_response = LLM_request.json()
                reason = LLM_response["candidates"][0]["content"]["parts"][0]["text"]
                output_list.append({filename: f"{reason}"})
            elif "NO" in yes_no:
                # output_list.append({f"{filename}": "NO"})
                pass
            else:
                output_list.append({f"{filename}": "ERR"})


            # sandbox
            # image_name = "sandbox-container"
            # context_path = "./sandbox/benchmarker/Dockerfile"
            # build_container(image_name, context_path)
            # run_container(image_name=image_name)

    # delete previous scan of this commit in the repo
    previous_scan = session.exec(select(Scan).filter(Scan.commit_sha == params.sha, Scan.repo_name == params.repo)).first()
    if previous_scan:
        session.delete(previous_scan)
        session.commit()
        # delete previous suspicious files
        previous_suspicious_files = session.exec(select(SuspiciousFiles).filter(SuspiciousFiles.scan_id == previous_scan.id)).all()
        for i in previous_suspicious_files:
            session.delete(i)
        session.commit()
        

    # update db
    scan = Scan(
        user_id=current_user.id,
        repo_name=params.repo,
        commit_sha=params.sha,
        scan_status="COMPLETED",
        last_scanned=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    session.add(scan)
    session.commit()
    
    for i in output_list:
        suspicious_file = SuspiciousFiles(
            scan_id=scan.id,
            filename=list(i.keys())[0],
            reason=list(i.values())[0],
        )
        session.add(suspicious_file)
        session.commit()
    return output_list


@app.post("/pulls")
async def http_get_pull_requests(
    request: RepoRequest, current_user: Annotated[User, Depends(get_current_active_user)]
):
    r = get_pull_requests(current_user.github_access_token, current_user.username, request.repo)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Failed to fetch PRs")
    return r.json()


@app.post("/events", response_model=List[dict])
async def http_get_events(
    session: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # TODO: filter by repo
    statement = select(PREvent).order_by(PREvent.timestamp.desc())
    events = session.exec(statement).all()
    events = [event.to_dict() for event in events]
    
    return events


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
