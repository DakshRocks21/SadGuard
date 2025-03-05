from fastapi import APIRouter, Depends
from utils.db import Session, get_session
from sqlmodel import select
from typing import Annotated
from schemas import UserProfile
from utils.db import User
from utils.common import get_current_active_user

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/users/", tags=["users"])
async def read_users(session: SessionDep):
    users = session.exec(select(User)).all()
    return users


@router.get("/users/me/", response_model=UserProfile)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user
