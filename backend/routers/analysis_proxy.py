# In server 2's routes, e.g., analysis_proxy.py
from flask import Blueprint, request, jsonify, abort
import requests
from utils.db import Session, get_session, User

SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(
    prefix="/analysis_proxy",
    tags=["analysis_proxy"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

SERVER1_URL = "http://127.0.0.1:3001" 

@router.post("/trigger-analysis")
async def proxy_trigger_analysis(request: Request):
    data = request.get_json()
    if not data:
        abort(400, "Invalid payload")
    try:
        # Forward the request to server 1.
        response = requests.post(f"{SERVER1_URL}/api/trigger-analysis", json=data)
        if response.status_code != 200:
            abort(response.status_code, response.text)
        return jsonify(response.json())
    except Exception as e:
        abort(500, f"Error contacting server 1: {str(e)}")

@router.get("/llm-review-output")
async def proxy_llm_review_output(request: Request):
    # Forward query parameters from server 2 to server 1
    params = request.args.to_dict()
    try:
        response = requests.get(f"{SERVER1_URL}/api/llm-review-output", params=params)
        if response.status_code != 200:
            abort(response.status_code, response.text)
        return jsonify(response.json())
    except Exception as e:
        abort(500, f"Error contacting server 1: {str(e)}")