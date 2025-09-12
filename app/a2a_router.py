# app/a2a_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any
import asyncio, json, uuid, time

from app.a2a_store import STORE

router = APIRouter()

def _new_context_id() -> str:
    return f"ctx_{uuid.uuid4().hex[:8]}"

async def _simulate_admin_reply(user_text: str, task_id: str = None) -> Dict[str, Any]:
    """
    Simulate an admin agent that evaluates breast cancer screening eligibility.
    This is a demo implementation that progresses through a realistic conversation.
    """
    import re
    from datetime import datetime
    
    # Get conversation history to understand context
    task = STORE.get(task_id) if task_id else None
    history = task["history"] if task else []
    
    # Count user messages to determine conversation stage
    user_messages = [msg for msg in history if msg["role"] == "user"]
    conversation_stage = len(user_messages)
    
    # Parse potential dates from user input
    date_patterns = [
        r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(\d{1,2})[\/\-](\d{4})\b',                  # MM/YYYY
    ]
    
    found_date = None
    for pattern in date_patterns:
        match = re.search(pattern, user_text)
        if match:
            found_date = match.group(0)
            break
    
    # Check for age information in current input (avoid dates)
    current_age = None
    if not found_date:  # Only look for age if not processing a date
        age_patterns = [
            r'\b(?:I am|I\'m|am|age)\s*(\d{2})\s*(?:years?\s*old|yo|year)?\b',
            r'\b(\d{2})\s*(?:years?\s*old|yo)\b',
            r'\bage\s*(\d{2})\b'
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, user_text, re.IGNORECASE)
            if age_match and 18 <= int(age_match.group(1)) <= 100:
                current_age = int(age_match.group(1))
                break
    
    # Extract patient age from conversation history
    patient_age = current_age  # Use current input first
    if not patient_age:
        for msg in history:
            if msg["role"] == "user":
                text = msg["parts"][0].get("text", "") if msg["parts"] else ""
                # Don't extract age from messages that contain dates
                if not any(re.search(pattern, text) for pattern in date_patterns):
                    age_patterns = [
                        r'\b(?:I am|I\'m|am|age)\s*(\d{2})\s*(?:years?\s*old|yo|year)?\b',
                        r'\b(\d{2})\s*(?:years?\s*old|yo)\b'
                    ]
                    for pattern in age_patterns:
                        age_match = re.search(pattern, text, re.IGNORECASE)
                        if age_match and 18 <= int(age_match.group(1)) <= 100:
                            patient_age = int(age_match.group(1))
                            break
                    if patient_age:
                        break
    
    # Stage 1: Initial greeting/inquiry
    if conversation_stage <= 1:
        reply = "Hello! I'm here to help evaluate your breast cancer screening eligibility. To get started, I'll need some information. What is your age?"
        return {
            "role": "agent", 
            "parts": [{"kind": "text", "text": reply}],
            "status": {"state": "input-required"}
        }
    
    # Stage 2: Collect age and ask for mammogram date
    elif conversation_stage == 2:
        if patient_age:
            if patient_age < 40:
                reply = f"Thank you. At age {patient_age}, routine mammography screening is typically not recommended unless you have specific risk factors. When was your last mammogram? Please provide the date (MM/DD/YYYY) or let me know if you've never had one."
            elif patient_age >= 50 and patient_age <= 74:
                reply = f"Thank you. At age {patient_age}, you fall within the recommended age range for breast cancer screening. When was your last mammogram? Please provide the date (MM/DD/YYYY)."
            else:
                reply = f"Thank you. At age {patient_age}, screening recommendations may vary. When was your last mammogram? Please provide the date (MM/DD/YYYY)."
            
            return {
                "role": "agent",
                "parts": [{"kind": "text", "text": reply}],
                "status": {"state": "input-required"}
            }
        else:
            reply = "I need to know your age to provide appropriate screening guidance. Could you please tell me how old you are?"
            return {
                "role": "agent",
                "parts": [{"kind": "text", "text": reply}],
                "status": {"state": "input-required"}
            }
    
    # Stage 3+: Process mammogram date and make eligibility determination
    else:
        # Handle "never" case
        if any(word in user_text.lower() for word in ['never', 'none', 'no', "haven't"]):
            age = patient_age or 55  # Default age
            if age >= 50:
                reply = f"Based on your information:\\n- Age: {age}\\n- No previous mammograms\\n\\nELIGIBLE: Since you are {age} years old and have never had a mammogram, you should schedule one. Guidelines recommend mammography every 1-2 years for women aged 50-74."
            elif age >= 40:
                reply = f"Based on your information:\\n- Age: {age}\\n- No previous mammograms\\n\\nDISCUSS WITH DOCTOR: You're in the 40-49 age group. Some guidelines suggest annual screening starting at 40. Please discuss with your healthcare provider."
            else:
                reply = f"Based on your information:\\n- Age: {age}\\n- No previous mammograms\\n\\nNOT TYPICALLY RECOMMENDED: Routine screening is typically not recommended under age 40 unless you have risk factors."
            
            return {
                "role": "agent",
                "parts": [{"kind": "text", "text": reply}],
                "status": {"state": "completed"}
            }
        
        # Process mammogram date
        if found_date:
            try:
                current_date = datetime.now()
                last_mammogram = None
                
                # Try different date formats
                for fmt in ['%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y', '%Y-%m-%d', '%m/%Y']:
                    try:
                        last_mammogram = datetime.strptime(found_date, fmt)
                        if fmt == '%m/%Y':
                            last_mammogram = last_mammogram.replace(day=1)
                        break
                    except ValueError:
                        continue
                
                if last_mammogram:
                    months_since = (current_date - last_mammogram).days / 30.44
                    age = patient_age or 55
                    
                    # Make eligibility determination
                    if age >= 50 and age <= 74:
                        if months_since >= 24:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nELIGIBLE: You meet the criteria for breast cancer screening. It's been {int(months_since)} months since your last mammogram, so you are due for screening."
                        elif months_since >= 12:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nCONSIDER: You may be ready for screening. Many guidelines suggest screening every 1-2 years, so you could consider scheduling soon."
                        else:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nNOT DUE: You had a recent mammogram. You're likely not due yet unless you have specific risk factors."
                    elif age >= 40:
                        reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date}\\n\\nDISCUSS WITH DOCTOR: You're in the 40-49 age group where screening recommendations vary. Please discuss with your healthcare provider."
                    else:
                        reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date}\\n\\nScreening recommendations for your age group may differ from standard guidelines. Please consult with your healthcare provider."
                    
                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": "completed"}
                    }
                    
            except Exception:
                reply = "I had trouble parsing that date format. Could you please provide your last mammogram date in MM/DD/YYYY format? For example: 01/15/2021"
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "input-required"}
                }
        
        # If no date found in input
        reply = "I need the date of your last mammogram to evaluate your eligibility. Please provide the date in MM/DD/YYYY format (for example: 01/15/2021). If you've never had a mammogram, please let me know."
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
        admin = await _simulate_admin_reply(text, task["id"])
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
        admin = await _simulate_admin_reply(text, task["id"])
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