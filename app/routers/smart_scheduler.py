"""
Smart Scheduling Agent Router

Exposes the Smart Scheduling Agent capabilities via REST and A2A endpoints.
Enables provider search, availability lookup, and appointment booking via SMART Scheduling Links.

Designed to be callable as:
1. A2A JSON-RPC endpoint for agent-to-agent communication
2. REST API for direct integrations
3. MCP tool for Claude agent invocation
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import base64
from datetime import datetime

from app.agents.smart_scheduler import (
    SmartSchedulerAgent,
    create_smart_scheduler_agent,
    DEFAULT_API_BASE
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/smart-scheduler", tags=["Smart Scheduler"])

# Global agent instance
_default_agent: Optional[SmartSchedulerAgent] = None


def get_agent() -> SmartSchedulerAgent:
    """Get or create an agent instance"""
    global _default_agent
    if _default_agent is None:
        _default_agent = create_smart_scheduler_agent()
    return _default_agent


def reset_agent() -> SmartSchedulerAgent:
    """Reset agent state for new session"""
    global _default_agent
    _default_agent = create_smart_scheduler_agent()
    return _default_agent


# Request/Response Models
class SearchRequest(BaseModel):
    specialty: Optional[str] = None
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    languages: Optional[List[str]] = None
    insurance: Optional[List[str]] = None
    available_only: bool = True


class AvailabilityRequest(BaseModel):
    provider_id: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class BookingRequest(BaseModel):
    slot_id: str


class MessageRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


# REST Endpoints
@router.get("/info")
async def get_agent_info():
    """Get information about the Smart Scheduling Agent"""
    agent = get_agent()
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "domain": agent.domain,
        "api_base": agent.api_base,
        "capabilities": agent.get_capabilities(),
        "use_cases": [
            "Search for healthcare providers by specialty and location",
            "Find available appointment slots",
            "Retrieve booking links for online scheduling",
            "Support multi-publisher FHIR data aggregation"
        ],
        "endpoints": {
            "info": "/api/smart-scheduler/info",
            "search": "/api/smart-scheduler/search",
            "availability": "/api/smart-scheduler/availability",
            "booking": "/api/smart-scheduler/booking",
            "providers": "/api/smart-scheduler/providers",
            "locations": "/api/smart-scheduler/locations",
            "slots": "/api/smart-scheduler/slots",
            "status": "/api/smart-scheduler/status",
            "a2a": "/api/smart-scheduler/a2a"
        }
    }


@router.post("/search")
async def search_providers(request: SearchRequest):
    """Search for healthcare providers"""
    agent = get_agent()
    result = await agent.search_providers(
        specialty=request.specialty,
        location=request.location,
        date_from=request.date_from,
        date_to=request.date_to,
        languages=request.languages,
        insurance=request.insurance,
        available_only=request.available_only
    )
    return result


@router.post("/availability")
async def get_availability(request: AvailabilityRequest):
    """Get available appointment slots for a provider"""
    agent = get_agent()
    result = await agent.get_provider_availability(
        provider_id=request.provider_id,
        date_from=request.date_from,
        date_to=request.date_to
    )
    return result


@router.get("/availability/{provider_id}")
async def get_provider_availability(
    provider_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get available appointment slots for a provider (GET variant)"""
    agent = get_agent()
    result = await agent.get_provider_availability(
        provider_id=provider_id,
        date_from=date_from,
        date_to=date_to
    )
    return result


@router.get("/booking/{slot_id}")
async def get_booking_info(slot_id: str):
    """Get booking information for a specific slot"""
    agent = get_agent()
    result = await agent.get_booking_info(slot_id)
    return result


@router.post("/booking")
async def get_booking(request: BookingRequest):
    """Get booking information (POST variant)"""
    agent = get_agent()
    result = await agent.get_booking_info(request.slot_id)
    return result


@router.get("/providers")
async def get_all_providers():
    """Get all available providers"""
    agent = get_agent()
    result = await agent.get_all_providers()
    return result


@router.get("/locations")
async def get_all_locations():
    """Get all available locations"""
    agent = get_agent()
    result = await agent.get_all_locations()
    return result


@router.get("/slots")
async def get_all_slots(
    available_only: bool = True,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get all available slots"""
    agent = get_agent()
    result = await agent.get_all_slots(
        available_only=available_only,
        date_from=date_from,
        date_to=date_to
    )
    return result


@router.post("/message")
async def process_message(request: MessageRequest):
    """Process a natural language message"""
    agent = get_agent()
    result = await agent.process_message(request.message, request.context)
    return result


@router.get("/status")
async def get_status():
    """Get current agent status"""
    agent = get_agent()
    return agent.get_status()


@router.post("/reset")
async def reset_session():
    """Reset the agent session"""
    agent = reset_agent()
    return {
        "success": True,
        "message": "Session reset",
        "status": agent.get_status()
    }


# A2A JSON-RPC Endpoint
@router.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A JSON-RPC endpoint for the Smart Scheduling Agent"""
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
                text = "Help me find a healthcare provider"

            # Also check for context parameters
            context = params.get("context", {})

            # Process the message
            response = await agent.process_message(text, context)

            # Format A2A response
            response_text = response.get("message", "")

            # Add provider list if available
            if response.get("providers"):
                providers_text = "\n".join([
                    f"- {p.get('name', 'Unknown')} ({p.get('specialty', 'N/A')}) - ID: {p.get('id', 'N/A')}"
                    for p in response["providers"][:5]
                ])
                response_text += f"\n\n**Providers found:**\n{providers_text}"

            # Add slots if available
            if response.get("slots"):
                slots_text = "\n".join([
                    f"- {s.get('display', s.get('start', 'Unknown'))} - ID: {s.get('id', 'N/A')}"
                    for s in response["slots"][:5]
                ])
                response_text += f"\n\n**Available slots:**\n{slots_text}"

            # Add booking info if available
            if response.get("booking_url"):
                response_text += f"\n\n**Book online:** {response['booking_url']}"
            if response.get("booking_phone"):
                response_text += f"\n**Call to book:** {response['booking_phone']}"

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
                "artifacts": [],
                "kind": "task",
                "metadata": {
                    "scenario": "smart_scheduling",
                    "agent": agent.agent_id,
                    "action": response.get("action"),
                    "status": agent.get_status()
                }
            }

            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": message_id,
                "result": result
            })

        # Direct method calls for programmatic access
        elif method == "search_providers":
            result = await agent.search_providers(
                specialty=params.get("specialty"),
                location=params.get("location"),
                date_from=params.get("date_from"),
                date_to=params.get("date_to"),
                languages=params.get("languages"),
                insurance=params.get("insurance"),
                available_only=params.get("available_only", True)
            )

        elif method == "get_availability":
            provider_id = params.get("provider_id")
            if not provider_id:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Missing provider_id parameter"},
                    "id": message_id
                })
            result = await agent.get_provider_availability(
                provider_id=provider_id,
                date_from=params.get("date_from"),
                date_to=params.get("date_to")
            )

        elif method == "get_booking":
            slot_id = params.get("slot_id")
            if not slot_id:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Missing slot_id parameter"},
                    "id": message_id
                })
            result = await agent.get_booking_info(slot_id)

        elif method == "get_providers":
            result = await agent.get_all_providers()

        elif method == "get_locations":
            result = await agent.get_all_locations()

        elif method == "get_slots":
            result = await agent.get_all_slots(
                available_only=params.get("available_only", True),
                date_from=params.get("date_from"),
                date_to=params.get("date_to")
            )

        elif method == "get_status":
            result = agent.get_status()

        elif method == "get_capabilities":
            result = agent.get_capabilities()

        elif method == "reset":
            reset_agent()
            result = {"success": True, "message": "Session reset"}

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
    """Get the A2A agent card for the Smart Scheduling Agent"""
    base_url = str(request.base_url).rstrip("/")

    return {
        "protocolVersion": "0.2.9",
        "preferredTransport": "JSONRPC",
        "name": "Smart Scheduling Agent",
        "description": "Search healthcare providers and find available appointments using SMART Scheduling Links",
        "url": f"{base_url}/api/smart-scheduler/a2a",
        "capabilities": {
            "streaming": False,
            "protocols": ["A2A", "REST"],
            "provider_search": True,
            "availability_lookup": True,
            "booking_retrieval": True,
            "multi_publisher_aggregation": True
        },
        "skills": [
            {
                "id": "provider_search",
                "name": "Provider Search",
                "description": "Search for healthcare providers by specialty, location, insurance, and languages",
                "tags": ["healthcare", "scheduling", "provider", "search", "fhir"],
                "discovery": {
                    "url": f"{base_url}/api/smart-scheduler/a2a"
                },
                "examples": [
                    "Find dermatologists in Boston",
                    "Search for cardiologists accepting Medicare",
                    "Look for Spanish-speaking primary care doctors"
                ]
            },
            {
                "id": "appointment_availability",
                "name": "Appointment Availability",
                "description": "Check available appointment slots for a specific provider",
                "tags": ["healthcare", "scheduling", "appointments", "availability"],
                "discovery": {
                    "url": f"{base_url}/api/smart-scheduler/a2a"
                }
            },
            {
                "id": "appointment_booking",
                "name": "Appointment Booking",
                "description": "Get booking links and phone numbers to schedule appointments",
                "tags": ["healthcare", "scheduling", "booking"],
                "discovery": {
                    "url": f"{base_url}/api/smart-scheduler/a2a"
                }
            }
        ],
        "methods": [
            "message/send",
            "search_providers",
            "get_availability",
            "get_booking",
            "get_providers",
            "get_locations",
            "get_slots",
            "get_status",
            "get_capabilities",
            "reset"
        ],
        "supported_formats": [
            "application/json"
        ],
        "data_sources": [
            "SMART Scheduling Links",
            "Zocdoc Demo",
            "Defacto SMART Scheduling",
            "Rendeva SMART Aligned Dataset"
        ]
    }


# MCP Tool Definitions (for Claude agent integration)
@router.get("/mcp/tools")
async def get_mcp_tools(request: Request):
    """Get MCP tool definitions for Claude agent integration"""
    base_url = str(request.base_url).rstrip("/")

    return {
        "tools": [
            {
                "name": "search_healthcare_providers",
                "description": "Search for healthcare providers by specialty, location, insurance, and language preferences. Returns a list of matching providers with their IDs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "specialty": {
                            "type": "string",
                            "description": "Medical specialty (e.g., dermatology, cardiology, primary care)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Geographic location (city, state, or region)"
                        },
                        "insurance": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of accepted insurance plans"
                        },
                        "languages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of languages spoken by provider"
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for availability (YYYY-MM-DD)"
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for availability (YYYY-MM-DD)"
                        }
                    }
                },
                "endpoint": f"{base_url}/api/smart-scheduler/search"
            },
            {
                "name": "get_provider_availability",
                "description": "Get available appointment slots for a specific healthcare provider. Requires provider_id from search results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider_id": {
                            "type": "string",
                            "description": "The provider's unique identifier (from search results)"
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for availability (YYYY-MM-DD)"
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for availability (YYYY-MM-DD)"
                        }
                    },
                    "required": ["provider_id"]
                },
                "endpoint": f"{base_url}/api/smart-scheduler/availability"
            },
            {
                "name": "get_appointment_booking_link",
                "description": "Get the booking URL and/or phone number to schedule an appointment for a specific time slot.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slot_id": {
                            "type": "string",
                            "description": "The appointment slot's unique identifier (from availability results)"
                        }
                    },
                    "required": ["slot_id"]
                },
                "endpoint": f"{base_url}/api/smart-scheduler/booking"
            }
        ]
    }
