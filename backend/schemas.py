from pydantic import BaseModel
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    avatar_url: str


class UserProfile(BaseModel):
    username: str
    avatar_url: str


class UserCreate(UserBase):
    github_access_token: str
    pass


class User(UserBase):
    id: int

    class Config:
        from_attributes = True


class GithubOAuth(BaseModel):
    code: str


class CommitInfo(BaseModel):
    message: str
    author: dict


class File(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    raw_url: str
    patch: str


class Commit(BaseModel):
    sha: str
    commit: Optional[CommitInfo] = None
    files: Optional[List[File]] = None


class CommitRef(BaseModel):
    sha: str
    
    
class CommitsResponse(BaseModel):
    commits: List[Commit]
    scans: dict


class Branch(BaseModel):
    name: str
    commit: CommitRef


class Repo(BaseModel):
    id: int
    name: str
    html_url: str
    description: Optional[str]
    branches: List[Branch]


class GetCommits(BaseModel):
    repo: str
    branch: Optional[str] = ""


class GetCommit(BaseModel):
    sha: str
    repo: str


class Pr(BaseModel):
    id: str
    commits_url: Optional[CommitInfo] = None


class RepoRequest(BaseModel):
    repo: str