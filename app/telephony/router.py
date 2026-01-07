"""
Telephony Router - FastAPI endpoints for VoIP functionality.

Endpoints:
- POST /api/telephony/originate - Initiate outbound call
- GET /api/telephony/calls - List active calls
- GET /api/telephony/calls/{call_id} - Get call details
- POST /api/telephony/calls/{call_id}/hangup - End a call
- GET /api/telephony/status - System status
- GET /api/telephony/history - Call history
- WebSocket /api/telephony/voice/{call_id} - Voice stream
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field

from .config import get_telephony_config, is_telephony_enabled
from .call_manager import get_call_manager, CallManager
from .voice_agent_server import VoiceAgentServer
from .audio_processor import get_audio_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telephony", tags=["telephony"])


# Request/Response Models

class OriginateRequest(BaseModel):
    """Request to originate an outbound call."""
    phone_number: str = Field(..., description="Destination phone number (E.164 format, e.g., +15551234567)")
    agent_id: str = Field(default="colonoscopy_scheduler", description="Agent to handle the call")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for the agent")
    caller_id: Optional[str] = Field(default=None, description="Override caller ID")


class OriginateResponse(BaseModel):
    """Response from call origination."""
    success: bool
    call_id: Optional[str] = None
    status: str
    message: Optional[str] = None


class CallDetailsResponse(BaseModel):
    """Detailed call information."""
    call_id: str
    direction: str
    caller: str
    callee: str
    agent_id: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[List[Dict[str, Any]]] = None
    intake_data: Optional[Dict[str, Any]] = None
    outcome: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """Telephony system status."""
    enabled: bool
    ready: bool
    shim_server: Dict[str, Any]
    config: Dict[str, Any]
    active_calls: int


# Dependency: Get call manager instance
def get_manager() -> CallManager:
    """Get the call manager, ensuring telephony is enabled."""
    config = get_telephony_config()
    if not config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Telephony features are disabled. Set TELEPHONY_ENABLED=true"
        )
    return get_call_manager()


# Voice Agent Server instance (created lazily)
_voice_server: Optional[VoiceAgentServer] = None


def get_voice_server() -> VoiceAgentServer:
    """Get or create the voice agent server."""
    global _voice_server
    if _voice_server is None:
        call_manager = get_call_manager()
        audio_processor = get_audio_processor() if is_telephony_enabled() else None
        _voice_server = VoiceAgentServer(
            agent_factory=call_manager.get_agent,
            audio_processor=audio_processor
        )
    return _voice_server


# Endpoints

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get telephony system status.

    Returns configuration, connectivity, and active call count.
    """
    config = get_telephony_config()

    # Check shim server connectivity
    shim_status = {"connected": False, "error": "Not checked"}
    if config.enabled:
        try:
            manager = get_call_manager()
            shim_status = await manager.get_shim_server_status()
        except Exception as e:
            shim_status = {"connected": False, "error": str(e)}

    # Get active call count
    active_calls = 0
    if config.enabled:
        voice_server = get_voice_server()
        active_calls = len(voice_server.active_calls)

    return SystemStatusResponse(
        enabled=config.enabled,
        ready=config.is_ready,
        shim_server=shim_status,
        config={
            "shim_server_url": config.shim_server_url,
            "max_concurrent_calls": config.max_concurrent_calls,
            "voice_enabled_agents": config.voice_enabled_agents,
            "use_realtime_api": config.use_realtime_api,
        },
        active_calls=active_calls,
    )


@router.post("/originate", response_model=OriginateResponse)
async def originate_call(request: OriginateRequest):
    """
    Initiate an outbound call.

    The agent will call the specified phone number and handle
    the conversation according to its configuration.

    Example use case: Agent calling a clinic to schedule an appointment.
    """
    manager = get_manager()

    try:
        call_id = await manager.originate(
            phone_number=request.phone_number,
            agent_id=request.agent_id,
            context=request.context,
            caller_id=request.caller_id,
        )

        return OriginateResponse(
            success=True,
            call_id=call_id,
            status="initiating",
            message=f"Call initiated to {request.phone_number}"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Error originating call: {e}")
        raise HTTPException(status_code=500, detail="Failed to originate call")


@router.get("/calls")
async def list_active_calls():
    """
    List all active calls.

    Returns basic information about calls currently in progress.
    """
    if not is_telephony_enabled():
        return {"calls": [], "count": 0, "enabled": False}

    voice_server = get_voice_server()
    calls = voice_server.get_active_calls()

    return {
        "calls": calls,
        "count": len(calls),
        "enabled": True,
    }


@router.get("/calls/{call_id}", response_model=CallDetailsResponse)
async def get_call_details(call_id: str):
    """
    Get detailed information about a specific call.

    Includes transcript if the call is still active or recently completed.
    """
    manager = get_manager()

    # Check active calls first
    voice_server = get_voice_server()
    active_call = voice_server.get_call(call_id)
    if active_call:
        return CallDetailsResponse(**active_call)

    # Check call history
    history = manager.get_call_details(call_id)
    if history:
        return CallDetailsResponse(**history)

    raise HTTPException(status_code=404, detail=f"Call {call_id} not found")


@router.post("/calls/{call_id}/hangup")
async def hangup_call(call_id: str):
    """
    End an active call.

    The call will be terminated gracefully.
    """
    manager = get_manager()

    success = await manager.hangup(call_id)
    if success:
        return {"success": True, "call_id": call_id, "status": "ended"}
    else:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found or already ended")


@router.post("/calls/{call_id}/transfer")
async def transfer_call(call_id: str, destination: str):
    """
    Transfer a call to another number.

    Used when the patient needs to speak with a human.
    """
    manager = get_manager()

    success = await manager.transfer(call_id, destination)
    if success:
        return {"success": True, "call_id": call_id, "transferred_to": destination}
    else:
        raise HTTPException(status_code=400, detail="Transfer failed")


@router.get("/history")
async def get_call_history(
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    since: Optional[str] = Query(None, description="ISO datetime to filter from"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
):
    """
    Get call history.

    Returns completed and active calls with optional filtering.
    """
    if not is_telephony_enabled():
        return {"calls": [], "count": 0, "enabled": False}

    manager = get_call_manager()

    # Parse datetime if provided
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format")

    calls = manager.get_call_history(
        agent_id=agent_id,
        since=since_dt,
        limit=limit,
    )

    return {
        "calls": calls,
        "count": len(calls),
        "filters": {
            "agent_id": agent_id,
            "since": since,
            "limit": limit,
        }
    }


@router.websocket("/voice/{call_id}")
async def voice_websocket(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for voice streaming.

    This is called by the Asterisk shim server to stream audio
    for a phone call. The voice agent server handles the conversation.

    Protocol: Twilio-compatible Media Streams
    - "start" event: Call initiated with metadata
    - "media" event: Audio frames (base64 μ-law)
    - "mark" event: Audio playback position
    - "stop" event: Call ended
    """
    config = get_telephony_config()
    if not config.enabled:
        await websocket.close(code=1008, reason="Telephony disabled")
        return

    voice_server = get_voice_server()

    try:
        await voice_server.handle_call(websocket, call_id)
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {call_id}")
    except Exception as e:
        logger.exception(f"Voice WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


@router.get("/agents")
async def list_voice_enabled_agents():
    """
    List agents that are enabled for voice calls.

    These agents can make and receive phone calls.
    """
    config = get_telephony_config()

    agents = []
    for agent_id in config.voice_enabled_agents:
        agents.append({
            "agent_id": agent_id,
            "name": agent_id.replace("_", " ").title(),
            "voice_enabled": True,
        })

    return {
        "agents": agents,
        "count": len(agents),
    }


@router.get("/config")
async def get_telephony_configuration():
    """
    Get current telephony configuration.

    Sensitive values (passwords, API keys) are masked.
    """
    config = get_telephony_config()

    return {
        "enabled": config.enabled,
        "ready": config.is_ready,
        "issues": config.validate(),
        "settings": {
            "shim_server_url": config.shim_server_url,
            "caller_id": config.caller_id,
            "max_concurrent_calls": config.max_concurrent_calls,
            "max_call_duration_seconds": config.max_call_duration_seconds,
            "idle_timeout_seconds": config.idle_timeout_seconds,
            "use_realtime_api": config.use_realtime_api,
            "tts_voice": config.openai_tts_voice,
            "log_transcripts": config.log_transcripts,
            "record_calls": config.record_calls,
        }
    }


# Health check for the telephony subsystem
@router.get("/health")
async def health_check():
    """
    Health check for telephony subsystem.

    Used by monitoring systems.
    """
    config = get_telephony_config()

    if not config.enabled:
        return {
            "status": "disabled",
            "message": "Telephony features are disabled",
        }

    try:
        manager = get_call_manager()
        shim_status = await manager.get_shim_server_status()

        if shim_status.get("connected"):
            return {
                "status": "healthy",
                "shim_connected": True,
                "active_calls": len(get_voice_server().active_calls),
            }
        else:
            return {
                "status": "degraded",
                "shim_connected": False,
                "error": shim_status.get("error"),
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
