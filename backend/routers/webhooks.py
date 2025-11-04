from fastapi import APIRouter, Depends, HTTPException, Request
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
    prefix="/webhooks",
    tags=["webhook"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.post("/github")
async def github_webhook(request: Request):
    data = await request.json()
    #print(data)
    return {"status": "ok"}
