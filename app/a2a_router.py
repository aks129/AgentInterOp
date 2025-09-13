# app/a2a_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any
import asyncio, json, uuid, time, re
from datetime import datetime, timedelta

from app.a2a_store import STORE

router = APIRouter()

def _new_context_id() -> str:
    return f"ctx_{uuid.uuid4().hex[:8]}"

async def _search_appointments(location_text: str) -> Dict[str, Any]:
    """Search for mammography appointments using Zocdoc SmartScheduling reference server."""
    import httpx
    
    try:
        # Try Zocdoc SmartScheduling reference server first
        zocdoc_url = "https://zocdoc-smartscheduling.netlify.app/$bulk-publish"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Fetch FHIR Schedule resources from reference server
                response = await client.get(
                    zocdoc_url,
                    headers={
                        'Accept': 'application/fhir+json',
                        'User-Agent': 'AgentInterOp-Scheduler/1.0'
                    }
                )
                
                if response.status_code == 200:
                    fhir_data = response.json()
                    
                    # Process FHIR Bundle to extract mammography appointments
                    slots = []
                    if fhir_data.get("resourceType") == "Bundle":
                        for entry in fhir_data.get("entry", []):
                            resource = entry.get("resource", {})
                            
                            # Look for Schedule or Slot resources
                            if resource.get("resourceType") == "Schedule":
                                # Extract schedule info
                                service_type = resource.get("serviceType", [])
                                service_category = resource.get("serviceCategory", [])
                                
                                # Check if it's mammography-related
                                is_mammography = any(
                                    "mammogr" in str(stype).lower() or 
                                    "breast" in str(stype).lower() or
                                    "screening" in str(stype).lower()
                                    for stype in [service_type, service_category]
                                )
                                
                                if is_mammography:
                                    # Extract practitioner and location info
                                    actor_refs = resource.get("actor", [])
                                    schedule_period = resource.get("planningHorizon", {})
                                    
                                    slots.append({
                                        "id": resource.get("id"),
                                        "serviceType": "Mammography Screening",
                                        "start": schedule_period.get("start"),
                                        "end": schedule_period.get("end"),
                                        "org": "Healthcare Provider",
                                        "location": {"address": f"Near {location_text}"}
                                    })
                            
                            elif resource.get("resourceType") == "Slot":
                                # Process individual slots
                                service_type = resource.get("serviceType", [])
                                if any("mammogr" in str(stype).lower() or "breast" in str(stype).lower() 
                                      for stype in service_type):
                                    slots.append({
                                        "id": resource.get("id"),
                                        "serviceType": "Mammography",
                                        "start": resource.get("start"),
                                        "end": resource.get("end"),
                                        "status": resource.get("status"),
                                        "org": "SmartScheduling Provider",
                                        "location": {"address": f"Location near {location_text}"}
                                    })
                    
                    # Format successful response with real data
                    if slots:
                        slots_text = "Here are available mammography appointments from SmartScheduling providers:\\n\\n"
                        
                        for i, slot in enumerate(slots[:3], 1):  # Show top 3
                            start_time = slot.get("start", "")
                            org = slot.get("org", "Healthcare Provider")
                            service_type = slot.get("serviceType", "Mammography")
                            location_info = slot.get("location", {})
                            address = location_info.get("address", f"Near {location_text}")
                            
                            # Format the date/time
                            if start_time:
                                try:
                                    if "T" in start_time:
                                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                        formatted_time = dt.strftime("%A, %B %d at %I:%M %p")
                                    else:
                                        formatted_time = start_time
                                except:
                                    formatted_time = start_time
                            else:
                                formatted_time = "Next available appointment"
                            
                            slots_text += f"{i}. {org}\\n   {service_type}\\n   {formatted_time}\\n   {address}\\n\\n"
                        
                        slots_text += "These appointments are available through the SmartScheduling network. To book, please contact the provider directly or use their online scheduling system."
                        
                        return {
                            "success": True,
                            "message": slots_text,
                            "found_slots": len(slots),
                            "source": "zocdoc_smartscheduling"
                        }
                    else:
                        # No mammography slots found in SmartScheduling data
                        pass  # Fall through to local search
                        
            except (httpx.TimeoutException, httpx.ConnectError):
                # SmartScheduling server unavailable, fall through to local search
                pass
        
        # Fallback to local scheduling system
        try:
            from app.scheduling.discovery import SlotQuery, discover_slots
            
            # Create search query for mammography
            query = SlotQuery(
                specialty="mammography",
                location_text=location_text,
                start=datetime.now(),
                end=datetime.now() + timedelta(days=30),  # Search next 30 days
                limit=5  # Limit to top 5 results
            )
            
            # Search for slots
            results = await discover_slots(query)
            
            if results.get("slots"):
                slots_text = "Here are available mammography appointments (local providers):\\n\\n"
                for i, slot in enumerate(results["slots"][:3], 1):  # Show top 3
                    start_time = slot.get("start", "")
                    org = slot.get("org", "Healthcare Provider")
                    location = slot.get("location", {})
                    address = location.get("address", "Address not available")
                    
                    # Format the date/time
                    if start_time:
                        try:
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            formatted_time = dt.strftime("%A, %B %d at %I:%M %p")
                        except:
                            formatted_time = start_time
                    else:
                        formatted_time = "Time TBD"
                    
                    slots_text += f"{i}. {org}\\n   {formatted_time}\\n   {address}\\n\\n"
                
                slots_text += "To book an appointment, please contact the provider directly or visit their website."
                
                return {
                    "success": True,
                    "message": slots_text,
                    "found_slots": len(results["slots"]),
                    "source": "local_discovery"
                }
                
        except Exception:
            pass  # Fall through to default message
        
        # Default response when no appointments found
        return {
            "success": True, 
            "message": f"I searched multiple scheduling networks for mammography appointments near {location_text} but didn't find any available slots in the next 30 days.\\n\\nThis might be because:\\n1. The location wasn't recognized\\n2. No providers are currently offering online scheduling\\n3. All nearby slots are booked\\n\\nI recommend:\\n- Calling local healthcare providers directly\\n- Checking with imaging centers in your area\\n- Contacting your primary care physician for referrals",
            "found_slots": 0,
            "source": "no_results"
        }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"I had trouble searching for appointments. This might be a temporary issue with the scheduling systems. Please try contacting local healthcare providers directly.\\n\\nFor immediate assistance, you can:\\n- Call your healthcare provider\\n- Visit imaging center websites\\n- Use healthcare apps like Zocdoc",
            "error": str(e),
            "source": "error"
        }

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
    
    # Debug logging (removed for production)
    
    # Check for scheduling keywords early (works across all conversation stages)
    scheduling_keywords = ['schedule', 'book', 'appointment', 'yes', 'find', 'search', 'available', 'when', 'where']
    wants_scheduling = any(word in user_text.lower() for word in scheduling_keywords)
    
    # Check for location/ZIP code patterns for appointment search
    location_patterns = [
        r'\b\d{5}\b',  # ZIP code
        r'\b[A-Za-z\s]+,\s*[A-Z]{2}\b',  # City, State
        r'\b[A-Za-z\s]+\s+\d{5}\b',  # City ZIP
    ]
    location_provided = any(re.search(pattern, user_text) for pattern in location_patterns)
    
    # If user wants scheduling and provides location, search immediately
    if wants_scheduling and location_provided:
        # Extract location from user input
        location = user_text.strip()
        search_result = await _search_appointments(location)
        reply = search_result["message"]
        return {
            "role": "agent",
            "parts": [{"kind": "text", "text": reply}],
            "status": {"state": "completed"}
        }
    
    # If user wants scheduling but no location, ask for it
    elif wants_scheduling and not location_provided:
        reply = "Great! I'll help you find available mammography appointments. To search for the best options, could you please tell me your ZIP code or city/state? For example: '10001' or 'New York, NY'"
        return {
            "role": "agent", 
            "parts": [{"kind": "text", "text": reply}],
            "status": {"state": "location-request"}
        }
    
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
            r'\b(?:I am|I\'m|am|age)\s*(\d{1,2})\s*(?:years?\s*old|yo|year)?\b',
            r'\b(\d{1,2})\s*(?:years?\s*old|yo)\b',
            r'\bage\s*(\d{1,2})\b',
            r'\b(\d{2})\s*$'  # Just a number at end of message
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
                        r'\b(?:I am|I\'m|am|age)\s*(\d{1,2})\s*(?:years?\s*old|yo|year)?\b',
                        r'\b(\d{1,2})\s*(?:years?\s*old|yo)\b',
                        r'\b(\d{2})\s*$'  # Just a number at end
                    ]
                    for pattern in age_patterns:
                        age_match = re.search(pattern, text, re.IGNORECASE)
                        if age_match and 18 <= int(age_match.group(1)) <= 100:
                            patient_age = int(age_match.group(1))
                            break
                    if patient_age:
                        break
    
    # Stage 1: Initial greeting (first user message, regardless of content)
    if conversation_stage == 1:
        # If user included age in first message, acknowledge and ask for mammogram date
        if patient_age:
            if patient_age < 40:
                reply = f"Hello! At age {patient_age}, routine mammography screening is typically not recommended unless you have specific risk factors. When was your last mammogram? Please provide the date (MM/DD/YYYY) or let me know if you've never had one."
            elif patient_age >= 50 and patient_age <= 74:
                reply = f"Hello! At age {patient_age}, you fall within the recommended age range for breast cancer screening. When was your last mammogram? Please provide the date (MM/DD/YYYY)."
            else:
                reply = f"Hello! At age {patient_age}, screening recommendations may vary. When was your last mammogram? Please provide the date (MM/DD/YYYY)."
        else:
            # No age detected, ask for age
            reply = f"[STAGE1] Hello! I'm here to help evaluate your breast cancer screening eligibility. To get started, I'll need some information. What is your age?"
        
        return {
            "role": "agent",
            "parts": [{"kind": "text", "text": reply}],
            "status": {"state": "input-required"}
        }
    
    # Stage 2: Process age (if not provided in first message)
    elif conversation_stage == 2 and patient_age:
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
    
    # Age not detected, ask again
    elif conversation_stage == 2 and not patient_age:
        reply = f"[STAGE2] I didn't catch your age. Could you please tell me how old you are? For example, just say the number like '45' or '60'."
        return {
            "role": "agent",
            "parts": [{"kind": "text", "text": reply}],
            "status": {"state": "input-required"}
        }
    
    # Stage 3: Process mammogram date and eligibility determination (conversation continues after age provided)
    elif conversation_stage >= 3:
        # Handle "never" case  
        if any(word in user_text.lower() for word in ['never', 'none', 'no', "haven't"]):
            age = patient_age or 55
            if age >= 50:
                reply = f"Based on your information:\\n- Age: {age}\\n- No previous mammograms\\n\\nELIGIBLE: Since you are {age} years old and have never had a mammogram, you should schedule one. Guidelines recommend mammography every 1-2 years for women aged 50-74.\\n\\nWould you like me to help you find available screening appointments in your area?"
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "scheduling-offer"}
                }
            elif age >= 40:
                reply = f"Based on your information:\\n- Age: {age}\\n- No previous mammograms\\n\\nDISCUSS WITH DOCTOR: You're in the 40-49 age group. Some guidelines suggest annual screening starting at 40. Please discuss with your healthcare provider about what's right for you."
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "completed"}
                }
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
                    
                    # Make eligibility determination with scheduling offer
                    if age >= 50 and age <= 74:
                        if months_since >= 24:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nELIGIBLE: You meet the criteria for breast cancer screening. It's been {int(months_since)} months since your last mammogram, so you are due for screening.\\n\\nWould you like me to help you find available screening appointments in your area?"
                            status = "scheduling-offer"
                        elif months_since >= 12:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nCONSIDER: You may be ready for screening. Many guidelines suggest screening every 1-2 years, so you could consider scheduling soon.\\n\\nWould you like me to help you find available screening appointments in your area?"
                            status = "scheduling-offer"  
                        else:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nNOT DUE: You had a recent mammogram. You're likely not due yet unless you have specific risk factors."
                            status = "completed"
                    elif age >= 40:
                        reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date}\\n\\nDISCUSS WITH DOCTOR: You're in the 40-49 age group where screening recommendations vary. Please discuss with your healthcare provider."
                        status = "completed"
                    else:
                        reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date}\\n\\nScreening recommendations for your age group may differ from standard guidelines. Please consult with your healthcare provider."
                        status = "completed"
                    
                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": status}
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
    
    # Stage 3+: Handle scheduling and location requests  
    else:
        # Check if the last agent message offered scheduling
        last_agent_message = None
        for msg in reversed(history):
            if msg.get("role") == "agent":
                last_agent_message = msg["parts"][0].get("text", "") if msg["parts"] else ""
                break
        
        offered_scheduling = (last_agent_message and 
                            ("would you like me to help" in last_agent_message.lower() or
                             "zip code" in last_agent_message.lower() or
                             "city" in last_agent_message.lower()))
        
        # If user wants to schedule
        if any(word in user_text.lower() for word in ['schedule', 'book', 'appointment', 'yes', 'find']):
            # Ask for location to search for appointments
            reply = "Great! I'll help you find available mammography appointments. To search for the best options, could you please tell me your ZIP code or city/state? For example: '10001' or 'New York, NY'"
            return {
                "role": "agent", 
                "parts": [{"kind": "text", "text": reply}],
                "status": {"state": "location-request"}
            }
        
        # If we asked for location and got a response
        elif offered_scheduling and ("zip" in last_agent_message.lower() or "city" in last_agent_message.lower()):
            # User provided location, search for appointments
            location = user_text.strip()
            if location:
                search_result = await _search_appointments(location)
                reply = search_result["message"]
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "completed"}
                }
            else:
                reply = "I need a location to search for appointments. Could you please provide your ZIP code or city/state? For example: '10001' or 'New York, NY'"
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "location-request"}
                }
        
        # If user declines scheduling
        elif any(word in user_text.lower() for word in ['no', 'not now', 'later']):
            reply = "No problem! Feel free to reach out anytime if you'd like help scheduling a mammography appointment. Take care and remember to keep up with your screening schedule."
            return {
                "role": "agent",
                "parts": [{"kind": "text", "text": reply}],
                "status": {"state": "completed"}
            }
        
        # Default response for post-evaluation 
        else:
            reply = "I've completed your breast cancer screening eligibility evaluation. Would you like me to help you schedule an appointment, or do you have any other questions?"
            return {
                "role": "agent",
                "parts": [{"kind": "text", "text": reply}],
                "status": {"state": "scheduling-offer"}
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
            # Debug: continuing conversation
        else:
            task = STORE.new_task(_new_context_id())
            # Debug: new conversation created

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
        # Message response with required fields
        message_result = {
            "role": "agent",
            "parts": admin["parts"],
            "kind": "message", 
            "messageId": admin_mid,
            "taskId": task["id"],
            "contextId": task["contextId"]
        }
        msg_frame = {"jsonrpc":"2.0","id":rid,"result":message_result}
        yield f"data: {json.dumps(msg_frame)}\n\n"
        await asyncio.sleep(0.1)

        # terminal status-update with required fields
        final_state = STORE.get(task["id"])["status"]
        status_result = {
            "kind": "status-update",
            "status": final_state,
            "final": True,
            "taskId": task["id"],
            "contextId": task["contextId"]
        }
        term = {"jsonrpc":"2.0","id":rid,"result":status_result}
        yield f"data: {json.dumps(term)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")

# Short alias still supported
@router.post("/a2a")
async def a2a_alias(request: Request):
    return await a2a_jsonrpc(request)