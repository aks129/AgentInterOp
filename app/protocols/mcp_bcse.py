from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
import json
import asyncio
from app.scenarios import bcse as BCS
from app.scheduling.discovery import discover_slots, choose_slot, SlotQuery
from app.scheduling.config import get_scheduling_config

router = APIRouter(prefix="/api/mcp/bcse", tags=["MCP-BCSE"])

_CONV = {}

@router.post("/begin_chat_thread")
async def begin():
    cid = datetime.now(timezone.utc).strftime("bcse-%H%M%S")
    _CONV[cid] = []
    return JSONResponse({"content":[{"type":"text","text":json.dumps({"conversationId":cid})}]})

@router.post("/send_message_to_chat_thread")
async def send(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": "Parse error"}, status_code=400)
        
    cid = body.get("conversationId")
    if not cid:
        return JSONResponse({"error": "Missing conversationId"}, status_code=400)
    if cid not in _CONV:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    msg = body.get("message") or ""
    _CONV[cid].append({"from":"applicant","text":msg})
    return JSONResponse({"guidance":"Message received","status":"working"})

@router.post("/check_replies")
async def check(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": "Parse error"}, status_code=400)
        
    cid = body.get("conversationId")
    if not cid:
        return JSONResponse({"error": "Missing conversationId"}, status_code=400)
    if cid not in _CONV:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    
    # Simulate wait time if specified
    wait_ms = body.get("waitMs")
    if wait_ms and wait_ms > 0:
        await asyncio.sleep(min(wait_ms / 1000.0, 5.0))  # Max 5 seconds
        
    turn = {"from":"administrator","at": datetime.now(timezone.utc).isoformat(),
            "text":"Provide sex, birthDate, last_mammogram (YYYY-MM-DD).","attachments":[]}
    return JSONResponse({
      "messages":[turn],
      "guidance":"Agent administrator finished a turn. It's your turn to respond.",
      "status":"input-required","conversation_ended": False
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