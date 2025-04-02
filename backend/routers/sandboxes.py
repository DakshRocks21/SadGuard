# backend/routes/sandboxes.py
import os
import json
from flask import Blueprint, jsonify, request, abort
from utils.db import Session, get_session, User
from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Annotated

SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(
    prefix="/sandboxes",
    tags=["sandboxes"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)



# Determine the path to the data file (e.g., ../data/sandboxes.json)
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'sandboxes.json')

def load_sandboxes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_sandboxes(sandboxes):
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(sandboxes, f, indent=2)

@router.get("/sandboxes")
async def get_sandboxes():
    sandboxes = load_sandboxes()
    return jsonify(sandboxes)

@router.post("/sandboxes")
async def create_sandbox(request: Request):
    data = request.json
    sandboxes = load_sandboxes()
    new_id = max([sandbox['id'] for sandbox in sandboxes], default=0) + 1
    new_sandbox = {"id": new_id, **data}
    sandboxes.append(new_sandbox)
    save_sandboxes(sandboxes)
    return jsonify(new_sandbox), 201

@router.put("/sandboxes/{sandbox_id}")
async def update_sandbox(request: Request, sandbox_id: str):
    data = request.json
    sandboxes = load_sandboxes()
    for sandbox in sandboxes:
        if sandbox['id'] == sandbox_id:
            sandbox.update(data)
            save_sandboxes(sandboxes)
            return jsonify(sandbox)
    abort(404)

@router.delete("/sandboxes/{sandbox_id}")
async def delete_sandbox(sandbox_id: str):
    sandboxes = load_sandboxes()
    sandboxes = [s for s in sandboxes if s['id'] != sandbox_id]
    save_sandboxes(sandboxes)
    return jsonify({"message": "Sandbox deleted"})
