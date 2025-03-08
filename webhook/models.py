from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, Column
from sqlalchemy.dialects.mysql import LONGTEXT, JSON
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USERNAME

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    avatar_url: str
    github_access_token: str

class Scan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    repo_name: str
    commit_sha: str
    pr_id: str
    scan_status: str
    scan_result: Optional[str] = Field(default=None)
    last_scanned: str

class SuspiciousFiles(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scan_id: int
    filename: str
    reason: str = Field(sa_type=LONGTEXT)

class PREvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_name: str = Field(index=True)
    event: str
    pr_number: int
    extra: dict = Field(sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# MySQL database URL and engine setup.
db_url = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(db_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
