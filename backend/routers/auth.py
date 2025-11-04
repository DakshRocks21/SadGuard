from fastapi import APIRouter, Depends, HTTPException
import schemas
import requests
from typing import Annotated
from sqlmodel import select
from datetime import timedelta

from utils.common import create_access_token, get_current_user, Token
from utils.db import Session, get_session, User
from modules.github import *
from schemas import UserCreate
from config import ACCESS_TOKEN_EXPIRE_MINUTES

SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.post("/github")
async def github_oauth(data: schemas.GithubOAuth, session: SessionDep):
    if not data.code:
        raise HTTPException(status_code=403, detail="Unauthorized")
    r = login_oauth(data.code)
    if r.status_code != 200:
        raise HTTPException(status_code=403, detail="Unauthorized")
    resp = r.json()
    if "access_token" not in resp:
        raise HTTPException(status_code=403, detail="Unauthorized")
    access_token = resp["access_token"]
    r = get_user(access_token)
    if r.status_code != 200:
        raise HTTPException(status_code=403, detail="Unauthorized")
    user_info = r.json()
    handle = user_info["login"]
    avatar = user_info["avatar_url"]
    db_user = session.exec(select(User).filter_by(username=handle)).first()
    if db_user:
        db_user.avatar_url = avatar
        db_user.github_access_token = access_token
        session.commit()
        session.refresh(db_user)
    else:
        new_user = UserCreate(
            username=handle, avatar_url=avatar, github_access_token=access_token
        )
        new_db_user = User.model_validate(new_user)
        session.add(new_db_user)
        session.commit()
        session.refresh(new_db_user)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": handle}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


# @router.put(
#     "/{item_id}",
#     tags=["custom"],
#     responses={403: {"description": "Operation forbidden"}},
# )
# async def update_item(item_id: str):
#     if item_id != "plumbus":
#         raise HTTPException(
#             status_code=403, detail="You can only update the item: plumbus"
#         )
#     return {"item_id": item_id, "name": "The great Plumbus"}
