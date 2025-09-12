# app/a2a_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any
import asyncio, json, uuid, time

from app.a2a_store import STORE

router = APIRouter()

def _new_context_id() -> str:
    return f"ctx_{uuid.uuid4().hex[:8]}"

async def _simulate_admin_reply(user_text: str) -> Dict[str, Any]:
    """
    Minimal demo: if user sent text, reply once and require input.
    Replace with your real admin/applicant logic later.
    """
    reply = f"Thanks. You said: {user_text}. Please provide last mammogram date."
    return {
        "role": "agent",
        "parts": [{"kind": "text", "text": reply}],
        "status": {"state": "input-required"}
    }

def _rpc_ok(id_, payload):
    return {"jsonrpc": "2.0", "id": id_, "result": payload}

def _rpc_err(id_, code, msg):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}

@router.post("/api/bridge/demo/a2a")
async def a2a_jsonrpc(request: Request):
    """
    Supports message/send, message/stream, tasks/get, tasks/cancel (JSON body).
    If Accept: text/event-stream AND method=message/stream => SSE stream.
    """
    # SSE path
    if "text/event-stream" in request.headers.get("accept", ""):
        body = await request.json()
        if body.get("method") != "message/stream":
            return JSONResponse(_rpc_err(body.get("id"), -32601, "Use method=message/stream for SSE"), status_code=400)
        return await _handle_stream(request, body)

    # Non-SSE path
    body = await request.json()
    m = body.get("method")
    rid = body.get("id")

    if m == "message/send":
        params = body.get("params", {}) or {}
        msg = params.get("message", {})
        parts = msg.get("parts", [])
        text = ""
        for p in parts:
            if p.get("kind") == "text":
                text = p.get("text", "")
                break

        # Handle direct content parameter for inspector compatibility
        if not text and "content" in params:
            text = params["content"]
            parts = [{"kind": "text", "text": text}]

        # new task if no taskId
        task = None
        task_id = msg.get("taskId")
        if task_id and STORE.get(task_id):
            task = STORE.get(task_id)
        else:
            task = STORE.new_task(_new_context_id())

        # record user message
        user_mid = f"msg_{uuid.uuid4().hex[:8]}"
        STORE.add_history(task["id"], "user", parts, user_mid)
        STORE.update_status(task["id"], "working")

        # simulate an admin turn (sync; keep it short)
        admin = await _simulate_admin_reply(text)
        admin_mid = f"msg_{uuid.uuid4().hex[:8]}"
        STORE.add_history(task["id"], admin["role"], admin["parts"], admin_mid)
        STORE.update_status(task["id"], admin["status"]["state"])

        return JSONResponse(_rpc_ok(rid, STORE.get(task["id"])))

    elif m == "message/stream":
        # This should not happen in non-SSE path, but handle gracefully
        return JSONResponse(_rpc_err(rid, -32602, "message/stream requires Accept: text/event-stream header"), status_code=400)

    elif m == "tasks/get":
        params = body.get("params", {}) or {}
        tid = params.get("id")
        t = STORE.get(tid) if tid else None
        if not t:
            return JSONResponse(_rpc_ok(rid, {"id": None, "status": {"state": "failed"}, "kind": "task"}))
        return JSONResponse(_rpc_ok(rid, t))

    elif m == "tasks/cancel":
        params = body.get("params", {}) or {}
        tid = params.get("id")
        t = STORE.get(tid)
        if not t:
            return JSONResponse(_rpc_err(rid, -32001, "Task not found"), status_code=404)
        STORE.update_status(tid, "canceled")
        return JSONResponse(_rpc_ok(rid, STORE.get(tid)))

    elif m == "tasks/resubscribe":
        # Optional method - return the current task state
        params = body.get("params", {}) or {}
        tid = params.get("id")
        t = STORE.get(tid)
        if not t:
            return JSONResponse(_rpc_err(rid, -32001, "Task not found"), status_code=404)
        return JSONResponse(_rpc_ok(rid, t))

    else:
        return JSONResponse(_rpc_err(rid, -32601, "Method not found"), status_code=404)

async def _handle_stream(request: Request, body: Dict[str, Any]):
    rid = body.get("id")
    params = body.get("params", {}) or {}
    msg = params.get("message", {})
    parts = msg.get("parts", [])
    text = ""
    for p in parts:
        if p.get("kind") == "text":
            text = p.get("text", "")
            break

    # Handle direct content parameter
    if not text and "content" in params:
        text = params["content"]
        parts = [{"kind": "text", "text": text}]

    # create task
    task = STORE.new_task(_new_context_id())
    user_mid = f"msg_{uuid.uuid4().hex[:8]}"
    STORE.add_history(task["id"], "user", parts, user_mid)
    STORE.update_status(task["id"], "working")

    async def event_gen():
        # initial snapshot
        snap = STORE.get(task["id"]).copy()
        yield f"data: {json.dumps({'jsonrpc':'2.0','id':rid,'result':snap})}\n\n"
        await asyncio.sleep(0.2)

        # admin reply
        admin = await _simulate_admin_reply(text)
        admin_mid = f"msg_{uuid.uuid4().hex[:8]}"
        STORE.add_history(task["id"], admin["role"], admin["parts"], admin_mid)
        STORE.update_status(task["id"], admin["status"]["state"])
        msg_frame = {"jsonrpc":"2.0","id":rid,"result":{"role":"agent","parts":admin["parts"],"kind":"message"}}
        yield f"data: {json.dumps(msg_frame)}\n\n"
        await asyncio.sleep(0.1)

        # terminal status-update
        final_state = STORE.get(task["id"])["status"]
        term = {"jsonrpc":"2.0","id":rid,"result":{"kind":"status-update","status":final_state,"final": True}}
        yield f"data: {json.dumps(term)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")

# Short alias still supported
@router.post("/a2a")
async def a2a_alias(request: Request):
    return await a2a_jsonrpc(request)