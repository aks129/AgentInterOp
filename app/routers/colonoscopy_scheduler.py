"""
Colonoscopy Scheduling Agent Router

Exposes the Colonoscopy Scheduling Agent capabilities via REST and A2A endpoints.
Solves the problem of complex colonoscopy scheduling with 40+ intake questions and long phone queues.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import base64
from datetime import datetime

from app.agents.colonoscopy_scheduler import (
    ColonoscopySchedulerAgent,
    create_colonoscopy_scheduler_agent,
    INTAKE_FORM_SECTIONS,
    PREP_INSTRUCTIONS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/colonoscopy-scheduler", tags=["Colonoscopy Scheduler"])

# Global agent instance
_default_agent: Optional[ColonoscopySchedulerAgent] = None


def get_agent() -> ColonoscopySchedulerAgent:
    """Get or create an agent instance"""
    global _default_agent
    if _default_agent is None:
        _default_agent = create_colonoscopy_scheduler_agent()
    return _default_agent


def reset_agent() -> ColonoscopySchedulerAgent:
    """Reset agent state for new scheduling session"""
    global _default_agent
    _default_agent = create_colonoscopy_scheduler_agent()
    return _default_agent


# Request/Response Models
class MessageRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class IntakeAnswerRequest(BaseModel):
    question_id: str
    answer: Any


class BulkIntakeRequest(BaseModel):
    answers: Dict[str, Any]


class AppointmentSelectRequest(BaseModel):
    appointment_id: str


class SearchPreferencesRequest(BaseModel):
    preferred_dates: Optional[str] = None
    preferred_location: Optional[str] = None
    time_of_day: Optional[str] = None


# REST Endpoints
@router.get("/info")
async def get_agent_info():
    """Get information about the Colonoscopy Scheduling Agent"""
    agent = get_agent()
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "domain": agent.domain,
        "capabilities": agent.get_capabilities(),
        "problem_solved": {
            "issue": "Colonoscopy scheduling is frustrating",
            "pain_points": [
                "Long phone queue wait times",
                "40+ question intake forms",
                "Coordination between patient, PCP, specialist, insurance"
            ],
            "solution": "AI agent automates intake, verification, and scheduling"
        },
        "endpoints": {
            "info": "/api/colonoscopy-scheduler/info",
            "intake_form": "/api/colonoscopy-scheduler/intake-form",
            "message": "/api/colonoscopy-scheduler/message",
            "status": "/api/colonoscopy-scheduler/status",
            "verify_insurance": "/api/colonoscopy-scheduler/verify-insurance",
            "search_appointments": "/api/colonoscopy-scheduler/search-appointments",
            "schedule": "/api/colonoscopy-scheduler/schedule",
            "prep_instructions": "/api/colonoscopy-scheduler/prep-instructions",
            "a2a": "/api/colonoscopy-scheduler/a2a"
        }
    }


@router.get("/intake-form")
async def get_intake_form():
    """Get the complete intake form structure"""
    return {
        "sections": INTAKE_FORM_SECTIONS,
        "total_questions": sum(len(s["questions"]) for s in INTAKE_FORM_SECTIONS.values()),
        "section_count": len(INTAKE_FORM_SECTIONS)
    }


@router.get("/intake-form/{section_id}")
async def get_intake_section(section_id: str):
    """Get a specific intake form section"""
    if section_id not in INTAKE_FORM_SECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Section '{section_id}' not found. Available: {list(INTAKE_FORM_SECTIONS.keys())}"
        )
    return INTAKE_FORM_SECTIONS[section_id]


@router.post("/message")
async def process_message(request: MessageRequest):
    """Process a natural language message"""
    agent = get_agent()
    response = agent.process_message(request.message, request.context)
    return response


@router.post("/intake/answer")
async def submit_intake_answer(request: IntakeAnswerRequest):
    """Submit an answer to a single intake question"""
    agent = get_agent()
    result = agent.process_intake_answer(request.question_id, request.answer)
    return result


@router.post("/intake/bulk")
async def submit_bulk_intake(request: BulkIntakeRequest):
    """Submit multiple intake answers at once"""
    agent = get_agent()
    result = agent.bulk_process_intake(request.answers)
    return result


@router.get("/intake/progress")
async def get_intake_progress():
    """Get current intake form progress"""
    agent = get_agent()
    return agent.get_intake_progress()


@router.get("/intake/next-questions")
async def get_next_questions(count: int = 3):
    """Get the next unanswered intake questions"""
    agent = get_agent()
    return {
        "questions": agent.get_next_questions(count),
        "progress": agent.get_intake_progress()
    }


@router.post("/verify-insurance")
async def verify_insurance():
    """Verify insurance coverage for colonoscopy"""
    agent = get_agent()
    result = agent.verify_insurance()
    return result


@router.post("/verify-referral")
async def verify_referral():
    """Verify PCP referral"""
    agent = get_agent()
    result = agent.verify_referral()
    return result


@router.post("/search-appointments")
async def search_appointments(preferences: Optional[SearchPreferencesRequest] = None):
    """Search for available colonoscopy appointments"""
    agent = get_agent()
    prefs = preferences.dict() if preferences else {}
    result = agent.search_appointments(prefs)
    return result


@router.post("/schedule")
async def schedule_appointment(request: AppointmentSelectRequest):
    """Select and confirm an appointment"""
    agent = get_agent()
    result = agent.select_appointment(request.appointment_id)
    return result


@router.get("/prep-instructions")
async def get_prep_instructions():
    """Get colonoscopy preparation instructions"""
    agent = get_agent()
    result = agent.get_prep_instructions()
    return result


@router.get("/prep-instructions/template")
async def get_prep_template():
    """Get the generic prep instructions template"""
    return PREP_INSTRUCTIONS


@router.get("/status")
async def get_workflow_status():
    """Get current workflow status"""
    agent = get_agent()
    return agent.get_workflow_status()


@router.post("/workflow/execute")
async def execute_full_workflow(patient_data: Optional[BulkIntakeRequest] = None):
    """Execute the complete scheduling workflow"""
    agent = get_agent()
    data = patient_data.answers if patient_data else None
    result = agent.execute_full_workflow(data)
    return result


@router.post("/reset")
async def reset_session():
    """Reset the scheduling session"""
    agent = reset_agent()
    return {
        "success": True,
        "message": "Scheduling session reset",
        "status": agent.get_workflow_status()
    }


# A2A JSON-RPC Endpoint
class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@router.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A JSON-RPC endpoint for the Colonoscopy Scheduling Agent"""
    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Parse error"},
            "id": None
        })

    method = body.get("method")
    params = body.get("params", {})
    message_id = body.get("id")

    agent = get_agent()

    try:
        # Handle A2A message/send - main entry point
        if method == "message/send":
            msg = params.get("message", {})
            parts = msg.get("parts", [])

            # Extract text from message parts
            text = ""
            for part in parts:
                if part.get("kind") == "text":
                    text = part.get("text", "")
                    break

            if not text:
                text = "Help me schedule a colonoscopy"

            # Process the message
            response = agent.process_message(text)

            # Format A2A response
            response_text = response.get("message", "")
            if response.get("next_questions"):
                questions_text = "\n".join([
                    f"- {q['question']}" for q in response["next_questions"]
                ])
                response_text += f"\n\n**Next questions:**\n{questions_text}"

            if response.get("appointments"):
                appts_text = "\n".join([
                    f"- {a['date_display']} at {a['time_display']} ({a['id']})"
                    for a in response["appointments"][:5]
                ])
                response_text += f"\n\n**Available appointments:**\n{appts_text}"

            # Build artifacts if prep instructions were requested
            artifacts = []
            if response.get("prep_instructions"):
                import json
                prep_content = json.dumps(response["prep_instructions"], indent=2)
                artifacts.append({
                    "kind": "file",
                    "file": {
                        "name": "colonoscopy_prep_instructions.json",
                        "mimeType": "application/json",
                        "bytes": base64.b64encode(prep_content.encode()).decode()
                    }
                })

            result = {
                "id": message_id or f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "contextId": agent.agent_id,
                "status": {"state": "input-required"},
                "history": [
                    {
                        "role": "user",
                        "parts": parts or [{"kind": "text", "text": text}],
                        "kind": "message"
                    },
                    {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": response_text}],
                        "kind": "message"
                    }
                ],
                "artifacts": artifacts,
                "kind": "task",
                "metadata": {
                    "scenario": "colonoscopy_scheduling",
                    "agent": agent.agent_id,
                    "status": agent.workflow_state["status"].value,
                    "progress": agent.get_intake_progress()
                }
            }

            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": message_id,
                "result": result
            })

        # Direct method calls
        elif method == "get_capabilities":
            result = agent.get_capabilities()
        elif method == "get_status":
            result = agent.get_workflow_status()
        elif method == "get_intake_form":
            result = {"sections": INTAKE_FORM_SECTIONS}
        elif method == "process_intake":
            result = agent.bulk_process_intake(params.get("answers", {}))
        elif method == "verify_insurance":
            result = agent.verify_insurance()
        elif method == "verify_referral":
            result = agent.verify_referral()
        elif method == "search_appointments":
            result = agent.search_appointments(params)
        elif method == "select_appointment":
            result = agent.select_appointment(params.get("appointment_id"))
        elif method == "get_prep_instructions":
            result = agent.get_prep_instructions()
        elif method == "execute_workflow":
            result = agent.execute_full_workflow(params.get("patient_data"))
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": message_id
            })

        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": message_id,
            "result": result
        })

    except Exception as e:
        logger.error(f"A2A error: {str(e)}")
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": str(e)},
            "id": message_id
        })


# Agent Card Endpoint
@router.get("/.well-known/agent-card.json")
async def get_agent_card(request: Request):
    """Get the A2A agent card for the Colonoscopy Scheduling Agent"""
    base_url = str(request.base_url).rstrip("/")

    return {
        "protocolVersion": "0.2.9",
        "preferredTransport": "JSONRPC",
        "name": "Colonoscopy Scheduling Agent",
        "description": "Automates colonoscopy scheduling - eliminates long phone queues and 40+ question intake forms",
        "url": f"{base_url}/api/colonoscopy-scheduler/a2a",
        "capabilities": {
            "streaming": False,
            "protocols": ["A2A"],
            "intake_automation": True,
            "insurance_verification": True,
            "appointment_scheduling": True,
            "prep_instructions": True
        },
        "skills": [
            {
                "id": "colonoscopy_scheduling",
                "name": "Colonoscopy Scheduling",
                "description": "Complete colonoscopy scheduling workflow - intake, insurance verification, appointment booking, and prep instructions",
                "tags": ["healthcare", "scheduling", "colonoscopy", "gi", "screening"],
                "discovery": {
                    "url": f"{base_url}/api/colonoscopy-scheduler/a2a"
                }
            }
        ],
        "methods": [
            "message/send",
            "get_capabilities",
            "get_status",
            "get_intake_form",
            "process_intake",
            "verify_insurance",
            "verify_referral",
            "search_appointments",
            "select_appointment",
            "get_prep_instructions",
            "execute_workflow"
        ],
        "supported_formats": [
            "application/json"
        ],
        "problem_solved": "Eliminates long phone queue waits and complex 40+ question intake forms for colonoscopy scheduling"
    }
