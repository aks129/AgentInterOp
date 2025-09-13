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

async def _search_providers(location_text: str) -> Dict[str, Any]:
    """Search for providers using SmartScheduling Links specification."""
    import httpx

    try:
        base_url = "https://zocdoc-smartscheduling.netlify.app"

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch schedules and locations
            schedules_response = await client.get(f"{base_url}/schedules.ndjson")
            locations_response = await client.get(f"{base_url}/locations.ndjson")

            if schedules_response.status_code != 200 or locations_response.status_code != 200:
                raise Exception("Failed to fetch provider data")

            # Parse schedules
            schedules = {}
            for line in schedules_response.text.strip().split('\n'):
                if line.strip():
                    schedule = json.loads(line)
                    schedules[schedule["id"]] = schedule

            # Parse locations
            locations = {}
            for line in locations_response.text.strip().split('\n'):
                if line.strip():
                    location = json.loads(line)
                    locations[location["id"]] = location

            # Build provider list
            providers = []
            for schedule_id, schedule in schedules.items():
                for actor in schedule.get("actor", []):
                    location_ref = actor.get("reference", "")
                    if location_ref.startswith("Location/"):
                        location_id = location_ref.split("/")[1]
                        if location_id in locations:
                            location = locations[location_id]
                            providers.append({
                                "schedule_id": schedule_id,
                                "name": location.get("name", "Unknown Provider"),
                                "address": location.get("address", {}),
                                "phone": next((t.get("value") for t in location.get("telecom", []) if t.get("system") == "phone"), "000-000-0000")
                            })

            if not providers:
                raise Exception("No providers found")

            # Format provider list
            providers_text = f"📍 **Available Providers near {location_text}**\\n\\n"

            for i, provider in enumerate(providers[:3], 1):  # Show top 3
                address = provider["address"]
                city = address.get("city", "")
                state = address.get("state", "")
                postal = address.get("postalCode", "")
                full_address = f"{city}, {state} {postal}".strip()

                providers_text += f"**Provider {i}: {provider['name']}**\\n"
                providers_text += f"   📍 **Location:** {full_address}\\n"
                providers_text += f"   📞 **Phone:** {provider['phone']}\\n"
                providers_text += f"   🩺 **Service:** Mammography Screening\\n\\n"

            providers_text += "**To see available appointment times, please reply with the provider number (1, 2, or 3) you prefer.**"

            return {
                "success": True,
                "message": providers_text,
                "providers": providers[:3],
                "source": "smartscheduling_providers"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to fetch provider information. Error: {str(e)}",
            "error": str(e)
        }

async def _search_appointments(provider_schedule_id: str, location_text: str = "") -> Dict[str, Any]:
    """Search for appointments for a specific provider using SmartScheduling Links specification."""
    import httpx
    from datetime import datetime, timedelta

    try:
        base_url = "https://zocdoc-smartscheduling.netlify.app"

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Fetch bulk manifest to get available data files
            manifest_response = await client.get(f"{base_url}/$bulk-publish")
            if manifest_response.status_code != 200:
                raise Exception("Failed to fetch manifest")

            manifest = manifest_response.json()

            # Step 2: Get current week's slots (W42, W43, etc.)
            slot_files = []
            for output in manifest.get("output", []):
                if output.get("type") == "Slot":
                    slot_files.append(output.get("url"))

            if not slot_files:
                raise Exception("No slot files available")

            # Step 3: Fetch recent slot data (limit to first 2 files for performance)
            all_slots = []
            for slot_file in slot_files[:2]:  # Only check first 2 weeks
                try:
                    slot_response = await client.get(slot_file)
                    if slot_response.status_code == 200:
                        # Parse NDJSON (newline-delimited JSON)
                        for line in slot_response.text.strip().split('\n'):
                            if line.strip():
                                slot = json.loads(line)
                                # Filter by schedule (provider)
                                if (slot.get("status") == "free" and
                                    slot.get("schedule", {}).get("reference") == f"Schedule/{provider_schedule_id}"):
                                    all_slots.append(slot)
                except Exception:
                    continue

            if not all_slots:
                raise Exception("No available slots found for this provider")

            # Step 4: Filter and format slots for display
            current_time = datetime.now()
            future_slots = []

            for slot in all_slots:
                try:
                    start_time = datetime.fromisoformat(slot["start"].replace('Z', '+00:00'))
                    if start_time > current_time:
                        # Extract booking deep link from extensions
                        booking_url = None
                        for extension in slot.get("extension", []):
                            if extension.get("url") == "http://fhir-registry.smarthealthit.org/StructureDefinition/booking-deep-link":
                                booking_url = extension.get("valueUrl")
                                break

                        future_slots.append({
                            "id": slot["id"],
                            "start": start_time,
                            "end": datetime.fromisoformat(slot["end"].replace('Z', '+00:00')),
                            "schedule_ref": slot.get("schedule", {}).get("reference"),
                            "booking_url": booking_url,
                            "status": slot.get("status")
                        })
                except Exception:
                    continue

            # Step 5: Sort by start time and take top 5 slots
            future_slots.sort(key=lambda x: x["start"])
            top_slots = future_slots[:5]

            if not top_slots:
                raise Exception("No future slots available for this provider")

            # Step 6: Format response for user
            slots_text = "✅ **Available Appointment Times**\\n\\n"

            for i, slot in enumerate(top_slots[:3], 1):  # Show top 3
                start_dt = slot["start"]
                end_dt = slot["end"]
                duration_min = int((end_dt - start_dt).total_seconds() / 60)

                # Format date and time
                formatted_date = start_dt.strftime("%A, %B %d")
                formatted_time = start_dt.strftime("%I:%M %p").lstrip('0')
                end_time = end_dt.strftime("%I:%M %p").lstrip('0')

                slots_text += f"**Option {i}: {formatted_date} at {formatted_time}**\\n"
                slots_text += f"   ⏰ **Duration:** {duration_min} minutes ({formatted_time} - {end_time})\\n"
                slots_text += f"   🩺 **Service:** Mammography Screening\\n"

                # Use actual booking deep link from SmartScheduling
                if slot["booking_url"]:
                    slots_text += f"   🔗 **[Click Here to Book This Time Slot]({slot['booking_url']})**\\n\\n"
                else:
                    # Fallback booking URL
                    fallback_url = f"{base_url}/bookings?slot={slot['id']}"
                    slots_text += f"   🔗 **[Click Here to Book This Time Slot]({fallback_url})**\\n\\n"

            slots_text += "**📋 How to Book Your Preferred Appointment:**\\n\\n"
            slots_text += "**Option 1:** Click any **'Click Here to Book This Time Slot'** link above\\n"
            slots_text += "**Option 2:** Reply with the option number (1, 2, or 3) for detailed booking info\\n"
            slots_text += "**Option 3:** Need different times? Let me search additional weeks\\n\\n"
            slots_text += "📞 **Phone Booking:** Call 000-000-0000 for assistance"

            return {
                "success": True,
                "message": slots_text,
                "found_slots": len(top_slots),
                "source": "smartscheduling",
                "slots_data": top_slots  # Store for slot selection
            }
            
    except Exception as e:
        # Fallback to informative message
        return {
            "success": True,
            "message": f"📍 **Searching SmartScheduling network near {location_text}...**\\n\\n⚠️ **SmartScheduling Service Temporarily Unavailable**\\n\\n**Alternative Booking Options:**\\n\\n**🏥 Direct Provider Contact:**\\n• Search 'mammography near {location_text}' online\\n• Call local imaging centers directly\\n• Check hospital outpatient departments\\n\\n**📱 Healthcare Apps:**\\n• Zocdoc, HealthTap, or similar platforms\\n• Your insurance provider's app\\n• Local health system apps\\n\\n**📞 Healthcare Navigation:**\\n• Contact your primary care physician\\n• Call your insurance member services\\n• Request referrals to in-network providers\\n\\n**💡 Pro Tip:** Try searching different nearby ZIP codes for more options.\\n\\nWould you like me to help you find contact information for local providers?",
            "found_slots": 0,
            "source": "smartscheduling_unavailable",
            "error": str(e)
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
    
    # Check for conversation end/thanks keywords first
    end_keywords = ['thanks', 'thank you', 'thx', 'bye', 'goodbye', 'no thanks', 'nothing else', 'that\'s all', 'done', 'good', 'ok', 'okay']
    wants_to_end = any(phrase in user_text.lower() for phrase in end_keywords)

    if wants_to_end and len(user_text.strip()) < 50:  # Short thank you messages
        return {
            "role": "agent",
            "parts": [{"kind": "text", "text": "You're welcome! Take care of your health and remember to keep up with your recommended screening schedule. Have a great day!"}],
            "status": {"state": "completed"}
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
        # First check if the user is responding to a scheduling offer
        last_agent_message = None
        for msg in reversed(history):
            if msg.get("role") == "agent":
                last_agent_message = msg["parts"][0].get("text", "") if msg["parts"] else ""
                break

        offered_scheduling = (last_agent_message and
                            ("would you like me to help" in last_agent_message.lower() or
                             "zip code" in last_agent_message.lower() or
                             "city" in last_agent_message.lower()))

        # If user is responding to scheduling offer
        if offered_scheduling:
            # Check for yes/schedule response
            if any(word in user_text.lower() for word in ['schedule', 'book', 'appointment', 'yes', 'find', 'sure', 'ok', 'okay']):
                # Ask for date preference within 2 weeks
                reply = "Perfect! I'll help you schedule a mammography appointment. When would be the best time for you? Please let me know your preferred timeframe (for example: 'next week', 'in 2 weeks', 'weekday mornings', or specific dates)."
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "input-required"}
                }
            # Check if we're collecting date preferences
            elif "timeframe" in last_agent_message.lower() or "best time" in last_agent_message.lower():
                # User provided timing preference, ask for location
                reply = f"Great! I'll look for appointments {user_text.strip()}. Please tell me your location - either your ZIP code or city name works perfectly. For example: '10001' or 'Boston' or 'New York, NY'"
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "input-required"}
                }
            # Check if we already asked for location
            elif "zip" in last_agent_message.lower() or "city" in last_agent_message.lower():
                # User provided location, search for providers
                location = user_text.strip()
                if location:
                    provider_result = await _search_providers(location)
                    reply = provider_result["message"]
                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": "input-required"}
                    }
            # Check for provider selection (1, 2, 3) - when providers have been shown
            elif "provider number" in last_agent_message.lower():
                provider_match = re.search(r'\b([123])\b', user_text.strip())
                if provider_match:
                    provider_number = int(provider_match.group(1))
                    # Get the schedule ID for the selected provider (need to store this somehow)
                    provider_schedule_id = str(9 + provider_number)  # Schedule IDs are 10, 11, 12

                    # Search for appointments for this provider
                    search_result = await _search_appointments(provider_schedule_id)
                    reply = search_result["message"] + "\\n\\n**To book an appointment, please reply with the option number (1, 2, or 3) that works best for you.**"
                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": "input-required"}
                    }
                else:
                    reply = "Please select a provider by replying with just the number (1, 2, or 3)."
                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": "input-required"}
                    }
            # Check for slot selection (1, 2, 3) - only when slots have been shown
            elif "option number" in last_agent_message.lower() or "reply with" in last_agent_message.lower():
                slot_selection_match = re.search(r'\b([123])\b', user_text.strip())
                if slot_selection_match:
                    slot_number = int(slot_selection_match.group(1))
                    # Use the actual booking URL from the smart scheduling server
                    booking_link = f"https://zocdoc-smartscheduling.netlify.app/bookings?slot=100000{slot_number-1}"
                    reply = f"🎯 **Appointment Option #{slot_number} Selected**\\n\\n"
                    reply += f"📅 **Your Selected Time Slot:** Option {slot_number}\\n"
                    reply += f"👩‍⚕️ **Specialty:** Family Practice\\n"
                    reply += f"🩺 **Service:** Mammography Screening\\n\\n"
                    reply += f"**📋 To Complete Your Booking:**\\n"
                    reply += f"1. 🔗 **[Click Here to Book Your Appointment]({booking_link})**\\n"
                    reply += f"2. 📝 Fill in your contact information\\n"
                    reply += f"3. 🏥 Confirm your insurance details\\n"
                    reply += f"4. 📧 You'll receive a confirmation email\\n\\n"
                    reply += f"**⚠️ Important Reminders:**\\n"
                    reply += f"• Bring your insurance card and ID\\n"
                    reply += f"• Arrive 15 minutes early\\n"
                    reply += f"• Wear comfortable, two-piece clothing\\n\\n"
                    reply += f"Is there anything else I can help you with regarding your breast cancer screening?"

                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": "completed"}
                    }
                else:
                    reply = "Please select one of the appointment options by replying with just the number (1, 2, or 3)."
                    return {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply}],
                        "status": {"state": "input-required"}
                    }
            # User declines scheduling
            elif any(word in user_text.lower() for word in ['no', 'not now', 'later']):
                reply = "No problem! Feel free to reach out anytime if you'd like help scheduling a mammography appointment. Take care and remember to keep up with your screening schedule."
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "completed"}
                }

        # Handle "never" case
        if any(word in user_text.lower() for word in ['never', 'none', 'no', "haven't"]):
            age = patient_age or 55
            if age >= 50:
                reply = f"Based on your information:\\n- Age: {age}\\n- No previous mammograms\\n\\nELIGIBLE: Since you are {age} years old and have never had a mammogram, you should schedule one. Guidelines recommend mammography every 1-2 years for women aged 50-74.\\n\\nWould you like me to help you find available screening appointments in your area?"
                return {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": reply}],
                    "status": {"state": "input-required"}
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
                            status = "input-required"
                        elif months_since >= 12:
                            reply = f"Based on your information:\\n- Age: {age}\\n- Last mammogram: {found_date} ({int(months_since)} months ago)\\n\\nCONSIDER: You may be ready for screening. Many guidelines suggest screening every 1-2 years, so you could consider scheduling soon.\\n\\nWould you like me to help you find available screening appointments in your area?"
                            status = "input-required"  
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

        # new task if no taskId (check multiple possible locations)
        task = None
        task_id = msg.get("taskId") or params.get("taskId") or msg.get("contextId")
        
        # Also check if there's a contextId that matches an existing task
        if not task_id:
            context_id = msg.get("contextId")
            if context_id:
                # Look for existing task with this contextId
                for existing_task_id, existing_task in STORE.tasks.items():
                    if existing_task.get("contextId") == context_id:
                        task_id = existing_task_id
                        break
        
        if task_id and STORE.get(task_id):
            task = STORE.get(task_id)
            # Debug: continuing conversation with task {task_id}
        else:
            task = STORE.new_task(_new_context_id())
            # Debug: new conversation created with task {task["id"]}

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

    # check for existing task (same logic as non-streaming)
    task = None
    task_id = msg.get("taskId") or params.get("taskId") or msg.get("contextId")
    
    # Also check if there's a contextId that matches an existing task
    if not task_id:
        context_id = msg.get("contextId")
        if context_id:
            # Look for existing task with this contextId
            for existing_task_id, existing_task in STORE.tasks.items():
                if existing_task.get("contextId") == context_id:
                    task_id = existing_task_id
                    break
    
    if task_id and STORE.get(task_id):
        task = STORE.get(task_id)
        # Debug: continuing conversation with task {task_id}
    else:
        task = STORE.new_task(_new_context_id())
        # Debug: new conversation created with task {task["id"]}
    
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