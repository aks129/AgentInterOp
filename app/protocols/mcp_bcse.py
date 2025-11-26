from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta, date
import json
from dateutil.parser import parse
from app.scheduling.discovery import discover_slots, choose_slot, SlotQuery
from app.scheduling.config import get_scheduling_config


def evaluate_bcse_direct(payload: dict) -> dict:
    """Direct BCS-E evaluation from simplified JSON payload."""
    result = {"eligible": False, "decision": "needs-more-info", "rationale": ""}

    try:
        sex = payload.get("sex", "").lower()
        if not sex:
            result["rationale"] = "Missing required field: sex"
            return result

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

        mammogram_str = payload.get("last_mammogram") or payload.get("lastMammogram") or payload.get("mammogram_date")
        if not mammogram_str:
            result["rationale"] = "Missing required field: last_mammogram"
            return result

        try:
            mammogram_date = parse(mammogram_str).date()
        except:
            result["rationale"] = "Invalid mammogram date format"
            return result

        today = date.today()
        months_since = (today.year - mammogram_date.year) * 12 + (today.month - mammogram_date.month)

        reasons = []
        if sex != "female":
            reasons.append(f"sex is {sex} (must be female)")
        if not (50 <= age <= 74):
            reasons.append(f"age is {age} (must be 50-74)")
        if months_since > 27:
            reasons.append(f"mammogram was {months_since} months ago (must be within 27 months)")

        if reasons:
            result["eligible"] = False
            result["decision"] = "ineligible"
            result["rationale"] = f"Not eligible: {'; '.join(reasons)}"
        else:
            result["eligible"] = True
            result["decision"] = "eligible"
            result["rationale"] = f"Eligible: female patient, age {age}, mammogram {months_since} months ago - all criteria met"

        result["criteria"] = {"sex": sex, "age": age, "months_since_mammogram": months_since}
        return result

    except Exception as e:
        result["rationale"] = f"Evaluation error: {str(e)}"
        return result

router = APIRouter(prefix="/api/mcp/bcse", tags=["MCP-BCSE"])

_CONV = {}  # conversationId -> {"messages": [...], "evaluated": bool, "result": dict}

@router.post("/begin_chat_thread")
async def begin():
    cid = datetime.now(timezone.utc).strftime("bcse-%H%M%S")
    _CONV[cid] = {"messages": [], "evaluated": False, "result": None}
    return JSONResponse({"content":[{"type":"text","text":json.dumps({"conversationId":cid})}]})

@router.post("/send_message_to_chat_thread")
async def send(req: Request):
    body = await req.json()
    cid = body.get("conversationId")
    msg = body.get("message") or ""

    if cid not in _CONV:
        _CONV[cid] = {"messages": [], "evaluated": False, "result": None}

    _CONV[cid]["messages"].append({"from": "applicant", "text": msg, "at": datetime.now(timezone.utc).isoformat()})

    # Try to parse and evaluate JSON payload
    result = None
    try:
        if "{" in msg:
            payload = json.loads(msg)
            result = evaluate_bcse_direct(payload)
            _CONV[cid]["evaluated"] = True
            _CONV[cid]["result"] = result
    except:
        pass

    if result:
        guidance = f"Evaluation complete: {result['decision']} - {result['rationale']}"
        status = "completed"
    else:
        guidance = "Message received. Provide JSON with: sex, age/dob, last_mammogram"
        status = "working"

    return JSONResponse({"guidance": guidance, "status": status})

@router.post("/check_replies")
async def check(req: Request):
    body = await req.json()
    cid = body.get("conversationId")

    conv = _CONV.get(cid, {"messages": [], "evaluated": False, "result": None})

    if conv["evaluated"] and conv["result"]:
        # Return evaluation result
        result = conv["result"]
        turn = {
            "from": "administrator",
            "at": datetime.now(timezone.utc).isoformat(),
            "text": json.dumps(result),
            "attachments": []
        }
        return JSONResponse({
            "messages": [turn],
            "guidance": f"Eligibility determination: {result['decision']}",
            "status": "completed",
            "conversation_ended": True
        })
    else:
        # Prompt for input
        turn = {
            "from": "administrator",
            "at": datetime.now(timezone.utc).isoformat(),
            "text": "Provide sex, age/dob, last_mammogram (YYYY-MM-DD) as JSON.",
            "attachments": []
        }
        return JSONResponse({
            "messages": [turn],
            "guidance": "Agent administrator is waiting for patient data.",
            "status": "input-required",
            "conversation_ended": False
        })

# MCP Scheduling Tools
@router.post("/find_specialist_slots")
async def find_specialist_slots(req: Request):
    """MCP tool to discover available specialist slots."""
    try:
        body = await req.json()
        
        # Extract parameters
        specialty = body.get("specialty")
        start_date = body.get("start_date") 
        end_date = body.get("end_date")
        lat = body.get("lat")
        lng = body.get("lng") 
        radius_km = body.get("radius_km")
        org = body.get("org")
        location_text = body.get("location_text")
        limit = body.get("limit", 50)
        publishers = body.get("publishers")
        
        # Build query
        query = SlotQuery(
            specialty=specialty,
            start=datetime.fromisoformat(start_date) if start_date else None,
            end=datetime.fromisoformat(end_date) if end_date else None,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            org=org,
            location_text=location_text,
            limit=limit,
            publishers=publishers
        )
        
        # Discover slots
        result = await discover_slots(query)
        
        slots_count = len(result.get("slots", []))
        guidance = f"Found {slots_count} available specialist slots"
        if specialty:
            guidance += f" for {specialty}"
        if slots_count == 0:
            guidance += ". Try expanding your search criteria."
        else:
            guidance += f". Use choose_slot to book an appointment."
        
        return JSONResponse({
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "guidance": guidance
        })
        
    except Exception as e:
        return JSONResponse({
            "content": [{"type": "text", "text": f"Error discovering slots: {str(e)}"}],
            "guidance": f"Slot discovery failed: {str(e)}"
        })

@router.post("/choose_slot") 
async def choose_slot_mcp(req: Request):
    """MCP tool to choose and book a specific slot."""
    try:
        body = await req.json()
        
        slot_id = body.get("slot_id")
        publisher_url = body.get("publisher_url")
        note = body.get("note")
        
        if not slot_id or not publisher_url:
            return JSONResponse({
                "content": [{"type": "text", "text": "Error: slot_id and publisher_url are required"}],
                "guidance": "Slot selection failed - missing required parameters"
            })
        
        # Choose the slot
        result = await choose_slot(slot_id, publisher_url, note)
        
        if result.get("success", False):
            guidance = result.get("guidance", "Slot selected successfully")
            if result.get("booking_link"):
                guidance += f". {result['confirmation']}"
                if result.get("is_simulation"):
                    guidance += " (simulated booking link)"
        else:
            guidance = f"Slot selection failed: {result.get('error', 'Unknown error')}"
        
        return JSONResponse({
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "guidance": guidance
        })
        
    except Exception as e:
        return JSONResponse({
            "content": [{"type": "text", "text": f"Error choosing slot: {str(e)}"}],
            "guidance": f"Slot selection failed: {str(e)}"
        })