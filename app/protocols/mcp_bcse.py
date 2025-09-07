from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import json
from app.scenarios import bcse as BCS

router = APIRouter(prefix="/api/mcp/bcse", tags=["MCP-BCSE"])

_CONV = {}

@router.post("/begin_chat_thread")
async def begin():
    cid = datetime.now(timezone.utc).strftime("bcse-%H%M%S")
    _CONV[cid] = []
    return JSONResponse({"content":[{"type":"text","text":json.dumps({"conversationId":cid})}]})

@router.post("/send_message_to_chat_thread")
async def send(req: Request):
    body = await req.json()
    cid = body.get("conversationId")
    msg = body.get("message") or ""
    _CONV.setdefault(cid,[]).append({"from":"applicant","text":msg})
    return JSONResponse({"guidance":"Message received","status":"working"})

@router.post("/check_replies")
async def check(req: Request):
    body = await req.json()
    cid = body.get("conversationId")
    turn = {"from":"administrator","at": datetime.now(timezone.utc).isoformat(),
            "text":"Provide sex, birthDate, last_mammogram (YYYY-MM-DD).","attachments":[]}
    return JSONResponse({
      "messages":[turn],
      "guidance":"Agent administrator finished a turn. It's your turn to respond.",
      "status":"input-required","conversation_ended": False
    })