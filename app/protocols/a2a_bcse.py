from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime, timezone
import json, time, uuid
from app.scenarios import bcse as BCS

router = APIRouter(prefix="/api/bridge/bcse/a2a", tags=["A2A-BCSE"])

_TASKS = {}  # taskId -> snapshot (in-memory for demo)

def _task_snapshot(tid, state, history=None, artifacts=None, context=None):
    return {
      "id": tid, "contextId": tid,
      "status": {"state": state},
      "history": history or [],
      "artifacts": artifacts or [],
      "kind":"task",
      "metadata": context or {}
    }

def _ok(result): return JSONResponse({"jsonrpc":"2.0","id":"1","result":result})
def _err(id_, code, message, data=None):
    return JSONResponse({"jsonrpc":"2.0","id":id_,"error":{"code":code,"message":message,"data":data or {}}}, status_code=200)

@router.post("")
async def rpc(req: Request):
    body = await req.json()
    method = body.get("method")
    id_ = body.get("id","1")
    params = body.get("params") or {}
    if method == "message/send":
        parts = (params.get("message") or {}).get("parts") or []
        text = next((p.get("text") for p in parts if p.get("kind")=="text"),"")
        tid = str(uuid.uuid4())[:8]
        history = [{"role":"user","parts":parts,"kind":"message"}]
        # If text contains a JSON payload, evaluate BCS
        decision=None
        try:
            for p in parts:
                if p.get("kind")=="text" and "{" in p.get("text",""):
                    decision = BCS.evaluate(json.loads(p["text"]))
        except Exception as e:
            pass
        snap = _task_snapshot(tid, "working", history=history, context={"scenario":"bcse"})
        if decision:
            snap["history"].append({"role":"agent","parts":[{"kind":"text","text":json.dumps(decision)}],"kind":"message"})
            snap["status"] = {"state":"completed"}
        _TASKS[tid]=snap
        return _ok(snap)
    elif method == "message/stream":
        # SSE stream: submitted -> working -> (agent message) -> input-required
        def gen():
            tid = str(uuid.uuid4())[:8]
            snap = _task_snapshot(tid, "working", history=[{"role":"user","parts":[],"kind":"message"}], context={"scenario":"bcse"})
            _TASKS[tid]=snap
            yield f"data: {json.dumps({'jsonrpc':'2.0','id':'sse','result':{'id':tid,'status':{'state':'working'},'kind':'task'}})}\n\n"
            time.sleep(0.2)
            msg = {"role":"agent","parts":[{"kind":"text","text":"Provide sex, birthDate, last_mammogram (YYYY-MM-DD)."}],"kind":"message"}
            yield f"data: {json.dumps({'jsonrpc':'2.0','id':'sse','result':msg})}\n\n"
            time.sleep(0.2)
            yield f"data: {json.dumps({'jsonrpc':'2.0','id':'sse','result':{'kind':'status-update','status':{'state':'input-required'},'final':True}})}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")
    elif method == "tasks/get":
        tid = (params or {}).get("id")
        if not tid or tid not in _TASKS:
            return _err(id_, -32001, "Task not found")
        return _ok(_TASKS[tid])
    elif method == "tasks/cancel":
        tid = (params or {}).get("id")
        if not tid or tid not in _TASKS:
            return _err(id_, -32001, "Task not found")
        snap=_TASKS[tid]; snap["status"]={"state":"canceled"}; return _ok(snap)
    else:
        return _err(id_, -32601, "Method not found")