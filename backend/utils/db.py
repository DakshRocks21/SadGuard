from typing import Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.dialects.mysql import LONGTEXT
from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USERNAME


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    # email: str = Field(index=True)
    # password: str = Field()
    avatar_url: str = Field()
    github_access_token: str = Field()


class Scan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    repo_name: str = Field()
    # branch_name: str = Field()
    commit_sha: str = Field()
    scan_status: str = Field()
    scan_result: str | None = Field()
    last_scanned: str = Field()
    

class SuspiciousFiles(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scan_id: int 
    filename: str
    # reason should be a very long string
    reason: str = Field(sa_type=LONGTEXT)

# mysql
db_url = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# connect_args = {"check_same_thread": False}
engine = create_engine(db_url)  # , connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
