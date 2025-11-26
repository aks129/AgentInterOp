from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime, timezone, date
import json, time, uuid, asyncio
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from app.scheduling.discovery import discover_slots, SlotQuery
from app.scheduling.config import get_scheduling_config


def evaluate_bcse_direct(payload: dict) -> dict:
    """
    Direct BCS-E evaluation from simplified JSON payload.

    Expected payload format:
    {
        "sex": "female",
        "dob": "1970-03-15" OR "age": 55,
        "last_mammogram": "2024-06-01"
    }

    Returns dict with: eligible (bool), decision (str), rationale (str)
    """
    result = {"eligible": False, "decision": "needs-more-info", "rationale": ""}

    try:
        # Extract sex
        sex = payload.get("sex", "").lower()
        if not sex:
            result["rationale"] = "Missing required field: sex"
            return result

        # Extract age (from 'age' field or calculate from 'dob')
        age = payload.get("age")
        if age is None:
            dob_str = payload.get("dob") or payload.get("birthDate") or payload.get("birth_date")
            if dob_str:
                try:
                    dob = parse(dob_str).date()
                    today = date.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                except:
                    result["rationale"] = "Invalid date of birth format"
                    return result
            else:
                result["rationale"] = "Missing required field: age or dob"
                return result

        # Extract last mammogram date
        mammogram_str = payload.get("last_mammogram") or payload.get("lastMammogram") or payload.get("mammogram_date")
        if not mammogram_str:
            result["rationale"] = "Missing required field: last_mammogram"
            return result

        try:
            mammogram_date = parse(mammogram_str).date()
        except:
            result["rationale"] = "Invalid mammogram date format"
            return result

        # Calculate months since mammogram
        today = date.today()
        months_since = (today.year - mammogram_date.year) * 12 + (today.month - mammogram_date.month)

        # Evaluate BCS-E criteria
        reasons = []

        # 1. Must be female
        if sex != "female":
            reasons.append(f"sex is {sex} (must be female)")

        # 2. Must be 50-74 years old
        if not (50 <= age <= 74):
            reasons.append(f"age is {age} (must be 50-74)")

        # 3. Mammogram within 27 months
        if months_since > 27:
            reasons.append(f"mammogram was {months_since} months ago (must be within 27 months)")

        if reasons:
            result["eligible"] = False
            result["decision"] = "ineligible"
            result["rationale"] = f"Not eligible: {'; '.join(reasons)}"
        else:
            result["eligible"] = True
            result["decision"] = "eligible"
            result["rationale"] = f"Eligible: female patient, age {age}, mammogram {months_since} months ago - all criteria met for breast cancer screening"

        # Add metadata
        result["criteria"] = {
            "sex": sex,
            "age": age,
            "months_since_mammogram": months_since
        }

        return result

    except Exception as e:
        result["rationale"] = f"Evaluation error: {str(e)}"
        return result

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
        text = next((p.get("text") for p in parts if p.get("type")=="text" or p.get("kind")=="text"),"")
        tid = str(uuid.uuid4())[:8]
        history = [{"role":"user","parts":parts,"kind":"message"}]
        # If text contains a JSON payload, evaluate BCS-E
        decision = None
        try:
            for p in parts:
                if (p.get("type")=="text" or p.get("kind")=="text") and "{" in p.get("text",""):
                    payload = json.loads(p["text"])
                    decision = evaluate_bcse_direct(payload)
                    break
        except Exception as e:
            decision = {"eligible": False, "decision": "error", "rationale": f"Parse error: {str(e)}"}
        snap = _task_snapshot(tid, "working", history=history, context={"scenario":"bcse"})
        if decision:
            # Add BCS decision to history
            snap["history"].append({"role":"agent","parts":[{"kind":"text","text":json.dumps(decision)}],"kind":"message"})
            
            # If eligible, add scheduling guidance and artifacts
            if decision.get("eligible", False):
                try:
                    # Search for available slots asynchronously
                    config = get_scheduling_config()
                    if config.publishers:
                        query = SlotQuery(
                            specialty=config.default_specialty,
                            radius_km=config.default_radius_km,
                            start=datetime.now(),
                            end=datetime.now().replace(hour=23, minute=59, second=59) + timezone.utc,
                            limit=5
                        )
                        
                        # Run slot discovery in background
                        slots_result = await discover_slots(query)
                        slots = slots_result.get("slots", [])
                        
                        if slots:
                            # Add scheduling artifact
                            scheduling_artifact = {
                                "kind": "ProposedAppointments",
                                "slots": slots[:5],  # First 5 slots
                                "searched_at": datetime.now(timezone.utc).isoformat(),
                                "specialty": query.specialty,
                                "radius_km": query.radius_km
                            }
                            
                            snap["artifacts"].append({
                                "name": "ProposedAppointments.json",
                                "content": json.dumps(scheduling_artifact, indent=2),
                                "mimeType": "application/json"
                            })
                            
                            # Add guidance message
                            guidance_text = f"Eligible for screening. Found {len(slots)} available appointment slots."
                            snap["history"].append({
                                "role": "agent",
                                "parts": [{"kind": "text", "text": guidance_text}],
                                "kind": "message"
                            })
                        else:
                            # No slots found
                            guidance_text = "Eligible for screening. Searching for available appointment slots..."
                            snap["history"].append({
                                "role": "agent", 
                                "parts": [{"kind": "text", "text": guidance_text}],
                                "kind": "message"
                            })
                            
                except Exception as e:
                    print(f"[WARN] Scheduling integration failed: {e}")
                    # Fallback guidance without slots
                    guidance_text = "Eligible for screening. Please contact your provider to schedule an appointment."
                    snap["history"].append({
                        "role": "agent",
                        "parts": [{"kind": "text", "text": guidance_text}], 
                        "kind": "message"
                    })
            
            snap["status"] = {"state": "completed"}
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