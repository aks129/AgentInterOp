# VoIP Integration Plan: Agent-Powered Phone Calls

## Executive Summary

This plan outlines the integration of VoIP functionality into AgentInterOp using the [open-telephony-stack](https://github.com/VectorlyApp/open-telephony-stack), enabling agents like the Colonoscopy Scheduling Agent to make actual phone calls to clinics, insurance companies, and patients.

## Problem Statement

Currently, the Colonoscopy Scheduling Agent can:
- Collect patient intake information via chat
- Verify insurance (simulated)
- Find appointments (simulated)
- Provide prep instructions

What it **cannot** do:
- Actually call the GI clinic to schedule the appointment
- Call insurance companies for real-time eligibility verification
- Call the patient to confirm appointment details
- Handle incoming calls from patients

## Solution: Open Telephony Stack Integration

### Why Open Telephony Stack?

| Feature | Open Telephony | Twilio |
|---------|---------------|--------|
| HIPAA Compliance | Self-managed, full control | $2,000+/mo BAA required |
| Cost | AWS Chime ($0.004/min) + infrastructure | $0.013-0.02/min |
| Customization | Full Asterisk dialplan control | Limited to API features |
| Lock-in | None - standard SIP | Proprietary APIs |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AgentInterOp Platform                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────────┐  │
│  │ Colonoscopy   │    │ A2A/MCP       │    │ Voice Agent Bridge    │  │
│  │ Scheduler     │───▶│ Protocols     │───▶│ (New Component)       │  │
│  │ Agent         │    │               │    │                       │  │
│  └───────────────┘    └───────────────┘    └──────────┬────────────┘  │
│                                                        │               │
└────────────────────────────────────────────────────────┼───────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Open Telephony Stack                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────────┐  │
│  │ Voice Agent   │    │ Shim Server   │    │ Asterisk PBX         │  │
│  │ Server        │◀──▶│ (FastAPI)     │◀──▶│ (Docker)             │  │
│  │ (WebSocket)   │    │               │    │                       │  │
│  └───────────────┘    └───────────────┘    └──────────┬────────────┘  │
│                                                        │               │
└────────────────────────────────────────────────────────┼───────────────┘
                                                         │
                                                         ▼
                                              ┌───────────────────────┐
                                              │ AWS Chime SDK         │
                                              │ SIP Trunking          │
                                              │ (PSTN Connectivity)   │
                                              └───────────────────────┘
                                                         │
                                                         ▼
                                              ┌───────────────────────┐
                                              │ Real Phone Numbers    │
                                              │ - GI Clinic           │
                                              │ - Insurance           │
                                              │ - Patients            │
                                              └───────────────────────┘
```

## Implementation Phases

### Phase 1: Infrastructure Setup (Week 1-2)

#### 1.1 AWS Setup
- Create AWS account with Chime SDK access
- Set up SIP Media Application
- Provision phone number(s)
- Configure Voice Connector

#### 1.2 Server Infrastructure
- Deploy EC2 instance (t3.medium minimum)
- Configure Elastic IP
- Set up DNS A-record
- Install Docker and Docker Compose

#### 1.3 Asterisk Deployment
```bash
# Clone the telephony stack
git clone https://github.com/VectorlyApp/open-telephony-stack.git

# Configure environment
cp .env.example .env
# Edit with your AWS credentials and domain

# Deploy Asterisk
docker-compose up -d asterisk
```

#### 1.4 TLS Certificate Setup
```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d voice.yourdomain.com

# Configure Asterisk to use certificates
```

### Phase 2: Voice Agent Server (Week 2-3)

#### 2.1 Create New Module: `app/telephony/`

```
app/telephony/
├── __init__.py
├── config.py              # VoIP configuration
├── voice_agent_server.py  # WebSocket handler
├── call_manager.py        # Call lifecycle management
├── audio_processor.py     # Audio format handling
└── router.py              # FastAPI endpoints
```

#### 2.2 Voice Agent Server Implementation

```python
# app/telephony/voice_agent_server.py
"""
Voice Agent Server - Bridges phone calls to AgentInterOp agents.
Handles bidirectional audio streaming via WebSocket.
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

@dataclass
class CallState:
    """State for an active phone call"""
    call_id: str
    stream_id: str
    caller: str
    callee: str
    agent_id: str
    started_at: datetime = field(default_factory=datetime.now)
    transcript: list = field(default_factory=list)
    intake_data: dict = field(default_factory=dict)
    status: str = "active"

class VoiceAgentServer:
    """
    Handles WebSocket connections from the Asterisk shim server.
    Converts audio to text, processes with agents, converts response to audio.
    """

    def __init__(self, agent_factory):
        self.active_calls: Dict[str, CallState] = {}
        self.agent_factory = agent_factory

    async def handle_call(self, websocket: WebSocket, call_id: str):
        """Handle incoming WebSocket connection for a phone call"""
        await websocket.accept()

        try:
            # Wait for start event
            start_event = await websocket.receive_json()
            if start_event.get("event") != "start":
                return

            # Extract call metadata
            metadata = start_event.get("start", {})
            stream_id = metadata.get("streamSid")
            custom_params = metadata.get("customParameters", {})

            # Determine which agent to use based on call routing
            agent_id = custom_params.get("agent", "colonoscopy_scheduler")

            # Create call state
            call_state = CallState(
                call_id=call_id,
                stream_id=stream_id,
                caller=custom_params.get("from", "unknown"),
                callee=custom_params.get("to", "unknown"),
                agent_id=agent_id
            )
            self.active_calls[call_id] = call_state

            # Initialize agent
            agent = self.agent_factory(agent_id)

            # Send initial greeting
            greeting = self._get_greeting(agent_id)
            await self._send_audio(websocket, greeting, stream_id)

            # Process call events
            await self._process_call_events(websocket, call_state, agent)

        except WebSocketDisconnect:
            logger.info(f"Call {call_id} disconnected")
        finally:
            if call_id in self.active_calls:
                del self.active_calls[call_id]

    async def _process_call_events(self, websocket: WebSocket,
                                    call_state: CallState, agent):
        """Process audio events from the call"""
        audio_buffer = bytearray()

        while True:
            event = await websocket.receive_json()
            event_type = event.get("event")

            if event_type == "media":
                # Accumulate audio for speech-to-text
                payload = event.get("media", {}).get("payload", "")
                audio_buffer.extend(base64.b64decode(payload))

                # Process when we have enough audio (e.g., after silence detection)
                if self._detect_end_of_speech(audio_buffer):
                    # Convert speech to text
                    text = await self._speech_to_text(audio_buffer)
                    audio_buffer.clear()

                    if text:
                        # Add to transcript
                        call_state.transcript.append({
                            "role": "user",
                            "content": text,
                            "timestamp": datetime.now().isoformat()
                        })

                        # Process with agent
                        response = agent.process_message(text)

                        # Extract response text
                        response_text = response.get("message", "")

                        # Add to transcript
                        call_state.transcript.append({
                            "role": "agent",
                            "content": response_text,
                            "timestamp": datetime.now().isoformat()
                        })

                        # Convert to speech and send
                        await self._send_audio(
                            websocket,
                            response_text,
                            call_state.stream_id
                        )

            elif event_type == "stop":
                break

    async def _speech_to_text(self, audio: bytes) -> str:
        """Convert audio to text using speech recognition"""
        # Integration point: OpenAI Whisper, AWS Transcribe, etc.
        # For now, placeholder
        pass

    async def _send_audio(self, websocket: WebSocket, text: str, stream_id: str):
        """Convert text to speech and send via WebSocket"""
        # Integration point: OpenAI TTS, AWS Polly, etc.
        # Audio must be 8kHz μ-law format
        pass

    def _get_greeting(self, agent_id: str) -> str:
        """Get initial greeting for the agent"""
        greetings = {
            "colonoscopy_scheduler": (
                "Hello, this is the GI Scheduling Assistant. "
                "I can help you schedule your colonoscopy appointment. "
                "May I have your name please?"
            ),
            # Add more agent greetings
        }
        return greetings.get(agent_id, "Hello, how may I help you?")
```

#### 2.3 FastAPI Router for Telephony

```python
# app/telephony/router.py
"""
FastAPI router for telephony endpoints.
"""

from fastapi import APIRouter, WebSocket, HTTPException
from typing import Dict, Any
import uuid

from .voice_agent_server import VoiceAgentServer
from .call_manager import CallManager

router = APIRouter(prefix="/api/telephony", tags=["telephony"])

# Initialize components
call_manager = CallManager()
voice_server = VoiceAgentServer(call_manager.get_agent)

@router.websocket("/call/{call_id}")
async def voice_websocket(websocket: WebSocket, call_id: str):
    """WebSocket endpoint for voice calls from Asterisk shim"""
    await voice_server.handle_call(websocket, call_id)

@router.post("/originate")
async def originate_call(request: Dict[str, Any]):
    """
    Initiate an outbound call from an agent.

    Example: Colonoscopy agent calling a clinic to schedule.
    """
    phone_number = request.get("phone_number")
    agent_id = request.get("agent_id", "colonoscopy_scheduler")
    context = request.get("context", {})

    if not phone_number:
        raise HTTPException(status_code=400, detail="phone_number required")

    # Validate phone number format
    if not _validate_phone(phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number")

    # Create call via shim server
    call_id = await call_manager.originate(
        phone_number=phone_number,
        agent_id=agent_id,
        context=context
    )

    return {
        "success": True,
        "call_id": call_id,
        "status": "initiating"
    }

@router.get("/calls")
async def list_active_calls():
    """List all active calls"""
    return {
        "calls": [
            {
                "call_id": call_id,
                "caller": state.caller,
                "callee": state.callee,
                "agent": state.agent_id,
                "started": state.started_at.isoformat(),
                "status": state.status
            }
            for call_id, state in voice_server.active_calls.items()
        ]
    }

@router.get("/calls/{call_id}")
async def get_call(call_id: str):
    """Get call details including transcript"""
    if call_id not in voice_server.active_calls:
        raise HTTPException(status_code=404, detail="Call not found")

    state = voice_server.active_calls[call_id]
    return {
        "call_id": call_id,
        "caller": state.caller,
        "callee": state.callee,
        "agent": state.agent_id,
        "started": state.started_at.isoformat(),
        "status": state.status,
        "transcript": state.transcript,
        "intake_data": state.intake_data
    }

@router.post("/calls/{call_id}/hangup")
async def hangup_call(call_id: str):
    """End an active call"""
    result = await call_manager.hangup(call_id)
    return {"success": result}

def _validate_phone(number: str) -> bool:
    """Validate phone number format"""
    import re
    # E.164 format
    return bool(re.match(r'^\+1\d{10}$', number))
```

### Phase 3: Agent Voice Capabilities (Week 3-4)

#### 3.1 Update Colonoscopy Scheduler Agent

Add voice-specific methods to the agent:

```python
# app/agents/colonoscopy_scheduler.py - additions

class ColonoscopySchedulerAgent:
    # ... existing code ...

    def get_voice_greeting(self) -> str:
        """Get voice-optimized greeting"""
        return (
            "Hello! This is the colonoscopy scheduling assistant. "
            "I'll help you schedule your procedure today. "
            "First, may I please have your full name?"
        )

    def process_voice_message(self, text: str, call_context: dict) -> dict:
        """
        Process a message from a phone call.
        Optimized for voice: shorter responses, clearer questions.
        """
        # Use existing process_message logic
        result = self.process_message(text, call_context)

        # Optimize for voice
        result["message"] = self._optimize_for_voice(result.get("message", ""))

        # Check if we need to make an outbound call
        if result.get("action") == "schedule_with_clinic":
            result["trigger_call"] = {
                "phone_number": "+1-555-GI-CLINIC",  # Would be real number
                "purpose": "schedule_appointment",
                "patient_data": self.workflow_state["intake_data"]
            }

        return result

    def _optimize_for_voice(self, text: str) -> str:
        """Make text more suitable for text-to-speech"""
        # Shorten long responses
        if len(text) > 200:
            # Keep just the key message
            sentences = text.split('. ')
            text = '. '.join(sentences[:3]) + '.'

        # Replace abbreviations
        replacements = {
            "DOB": "date of birth",
            "PCP": "primary care provider",
            "GI": "G I",  # Spell out for TTS
            "ID": "I D",
        }
        for abbr, full in replacements.items():
            text = text.replace(abbr, full)

        return text
```

#### 3.2 Voice Workflow: Patient Scheduling Call

```python
# app/telephony/workflows/patient_scheduling.py
"""
Voice workflow for patient calling to schedule colonoscopy.
"""

class PatientSchedulingWorkflow:
    """
    Handles inbound calls from patients wanting to schedule.

    Flow:
    1. Greet patient
    2. Collect demographics (name, DOB)
    3. Verify insurance
    4. Get referral info
    5. Find available appointments
    6. Confirm selection
    7. Provide prep instructions
    """

    states = [
        "greeting",
        "collect_name",
        "collect_dob",
        "verify_insurance",
        "get_referral",
        "search_appointments",
        "confirm_appointment",
        "send_instructions",
        "complete"
    ]

    def __init__(self, agent, call_state):
        self.agent = agent
        self.call_state = call_state
        self.current_state = "greeting"

    async def process(self, user_input: str) -> str:
        """Process user input and return response"""

        # Let agent process the message
        result = self.agent.process_voice_message(
            user_input,
            {"call_id": self.call_state.call_id}
        )

        # Check for state transitions
        if result.get("action") == "intake_complete":
            self.current_state = "search_appointments"

        return result.get("message", "")
```

### Phase 4: AI Voice Integration (Week 4-5)

#### 4.1 Speech-to-Text Integration

```python
# app/telephony/audio_processor.py
"""
Audio processing: STT and TTS integration.
"""

import os
from openai import OpenAI

class AudioProcessor:
    """Handles speech-to-text and text-to-speech"""

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def speech_to_text(self, audio_data: bytes, format: str = "mulaw") -> str:
        """
        Convert audio to text using OpenAI Whisper.

        Args:
            audio_data: Raw audio bytes (μ-law 8kHz from phone)
            format: Audio format

        Returns:
            Transcribed text
        """
        # Convert μ-law to WAV for Whisper
        wav_data = self._mulaw_to_wav(audio_data)

        # Call Whisper API
        response = self.openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", wav_data, "audio/wav")
        )

        return response.text

    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to audio using OpenAI TTS.

        Args:
            text: Text to convert

        Returns:
            μ-law 8kHz audio bytes for phone playback
        """
        # Call TTS API
        response = self.openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
            response_format="pcm"
        )

        # Convert to μ-law 8kHz for phone
        mulaw_data = self._pcm_to_mulaw(response.content)

        return mulaw_data

    def _mulaw_to_wav(self, mulaw_data: bytes) -> bytes:
        """Convert μ-law to WAV format"""
        import audioop
        import struct
        import io

        # Decode μ-law to linear PCM
        pcm_data = audioop.ulaw2lin(mulaw_data, 2)

        # Create WAV file
        wav_buffer = io.BytesIO()
        # Write WAV header for 8kHz mono
        wav_buffer.write(b'RIFF')
        wav_buffer.write(struct.pack('<I', 36 + len(pcm_data)))
        wav_buffer.write(b'WAVE')
        wav_buffer.write(b'fmt ')
        wav_buffer.write(struct.pack('<IHHIIHH', 16, 1, 1, 8000, 16000, 2, 16))
        wav_buffer.write(b'data')
        wav_buffer.write(struct.pack('<I', len(pcm_data)))
        wav_buffer.write(pcm_data)

        return wav_buffer.getvalue()

    def _pcm_to_mulaw(self, pcm_data: bytes) -> bytes:
        """Convert PCM to μ-law format"""
        import audioop

        # Resample if needed (OpenAI outputs 24kHz)
        pcm_8k = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)[0]

        # Convert to μ-law
        return audioop.lin2ulaw(pcm_8k, 2)
```

#### 4.2 Real-Time Voice AI (Optional - OpenAI Realtime API)

For lower latency, use OpenAI's Realtime API directly:

```python
# app/telephony/realtime_voice.py
"""
Integration with OpenAI Realtime API for voice-to-voice.
"""

import asyncio
import websockets
import json
import os

class RealtimeVoiceAgent:
    """
    Uses OpenAI Realtime API for direct voice-to-voice.
    Lower latency than STT -> Agent -> TTS pipeline.
    """

    def __init__(self, agent):
        self.agent = agent
        self.openai_url = "wss://api.openai.com/v1/realtime"
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def connect(self, asterisk_ws, call_state):
        """Bridge Asterisk WebSocket to OpenAI Realtime"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        async with websockets.connect(self.openai_url, extra_headers=headers) as openai_ws:
            # Configure session
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "voice": "alloy",
                    "instructions": self._get_system_prompt(),
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "tools": self._get_tools()
                }
            }))

            # Bridge audio streams
            await asyncio.gather(
                self._forward_asterisk_to_openai(asterisk_ws, openai_ws),
                self._forward_openai_to_asterisk(openai_ws, asterisk_ws, call_state)
            )

    def _get_system_prompt(self) -> str:
        """System prompt for voice agent"""
        return """You are a friendly healthcare scheduling assistant helping patients schedule colonoscopy appointments.

Your tasks:
1. Collect patient information (name, date of birth, insurance)
2. Verify their referral from their primary care doctor
3. Help them find and book an available appointment
4. Provide preparation instructions

Be concise and clear. Speak naturally as on a phone call.
Ask one question at a time. Confirm important information by repeating it back."""

    def _get_tools(self) -> list:
        """Tools available to the voice agent"""
        return [
            {
                "type": "function",
                "name": "search_appointments",
                "description": "Search for available colonoscopy appointments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preferred_date": {"type": "string"},
                        "preferred_time": {"type": "string"}
                    }
                }
            },
            {
                "type": "function",
                "name": "book_appointment",
                "description": "Book a specific appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {"type": "string"}
                    },
                    "required": ["appointment_id"]
                }
            },
            {
                "type": "function",
                "name": "end_call",
                "description": "End the call politely",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
```

### Phase 5: Outbound Calling (Week 5-6)

#### 5.1 Agent-Initiated Calls

Enable agents to make outbound calls to clinics/insurance:

```python
# app/telephony/call_manager.py
"""
Manages call lifecycle including outbound calls.
"""

import httpx
import os

class CallManager:
    """Manages call origination and lifecycle"""

    def __init__(self):
        self.shim_server_url = os.getenv(
            "SHIM_SERVER_URL",
            "http://localhost:8080"
        )
        self.agents = {}

    async def originate(self, phone_number: str, agent_id: str,
                        context: dict) -> str:
        """
        Originate an outbound call.

        Used when agent needs to call a clinic to schedule.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.shim_server_url}/calls/originate",
                json={
                    "destination": phone_number,
                    "callerId": os.getenv("CALLER_ID", "+15551234567"),
                    "customParameters": {
                        "agent": agent_id,
                        **context
                    }
                }
            )

            result = response.json()
            return result.get("callId")

    async def hangup(self, call_id: str) -> bool:
        """Hang up an active call"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.shim_server_url}/calls/{call_id}/hangup"
            )
            return response.status_code == 200
```

#### 5.2 Clinic Scheduling Flow

```python
# app/telephony/workflows/clinic_scheduling.py
"""
Workflow for agent calling clinic to schedule on behalf of patient.
"""

class ClinicSchedulingWorkflow:
    """
    Agent calls GI clinic to schedule colonoscopy.

    Flow:
    1. Identify as scheduling assistant
    2. Provide patient information
    3. Request appointment
    4. Confirm date/time
    5. Get confirmation number
    """

    def __init__(self, agent, patient_data: dict):
        self.agent = agent
        self.patient = patient_data

    def get_opening_script(self) -> str:
        """What agent says when clinic answers"""
        return f"""Hello, this is an automated scheduling assistant calling
on behalf of {self.patient.get('full_name')}.
I'm calling to schedule a colonoscopy appointment.
The patient has a referral from {self.patient.get('referring_physician')}.
Is this a good time to schedule?"""

    async def process_clinic_response(self, response: str) -> str:
        """Process what clinic staff says and respond appropriately"""
        # Use Claude to understand clinic response and generate reply
        from app.llm.anthropic import get_completion

        prompt = f"""You are a scheduling assistant on a phone call with a clinic.

Patient information:
- Name: {self.patient.get('full_name')}
- DOB: {self.patient.get('dob')}
- Insurance: {self.patient.get('insurance_provider')}
- Referral from: {self.patient.get('referring_physician')}
- Reason: {self.patient.get('referral_reason')}

The clinic staff just said: "{response}"

Respond appropriately to move toward scheduling an appointment.
If they're asking for information, provide it.
If they're offering times, select one that works.
Be professional and concise."""

        return await get_completion(prompt)
```

### Phase 6: Testing & Production (Week 6-8)

#### 6.1 Local Development Testing

```python
# tests/telephony/test_voice_agent.py
"""
Tests for voice agent functionality.
"""

import pytest
from app.telephony.voice_agent_server import VoiceAgentServer
from app.agents.colonoscopy_scheduler import create_colonoscopy_scheduler_agent

@pytest.fixture
def voice_server():
    return VoiceAgentServer(lambda _: create_colonoscopy_scheduler_agent())

@pytest.mark.asyncio
async def test_greeting():
    """Test that agent provides appropriate greeting"""
    agent = create_colonoscopy_scheduler_agent()
    greeting = agent.get_voice_greeting()

    assert "colonoscopy" in greeting.lower()
    assert "name" in greeting.lower()

@pytest.mark.asyncio
async def test_name_extraction():
    """Test that agent extracts name from speech"""
    agent = create_colonoscopy_scheduler_agent()

    # Simulate voice interaction
    response = agent.process_voice_message(
        "Hi, my name is John Smith",
        {"call_id": "test-123"}
    )

    assert agent.workflow_state["intake_data"].get("full_name")
    assert "John Smith" in agent.workflow_state["intake_data"]["full_name"]
```

#### 6.2 Integration Testing

```bash
# Test with actual phone call
curl -X POST http://localhost:8000/api/telephony/originate \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+15551234567",
    "agent_id": "colonoscopy_scheduler",
    "context": {
      "patient_name": "Test Patient",
      "purpose": "scheduling_test"
    }
  }'
```

#### 6.3 Production Deployment Checklist

- [ ] AWS Chime SIP trunk configured
- [ ] Phone number provisioned
- [ ] TLS certificates installed and auto-renewing
- [ ] Asterisk container running
- [ ] Shim server deployed
- [ ] Voice agent server integrated with AgentInterOp
- [ ] Monitoring and logging configured
- [ ] HIPAA audit logging enabled
- [ ] Call recording storage (encrypted)
- [ ] Failover and high availability tested

## Cost Estimates

### AWS Chime Voice Connector
- Per-minute inbound: $0.004
- Per-minute outbound: $0.004
- Phone number: $1.00/month

### Infrastructure (EC2)
- t3.medium (50 concurrent calls): ~$30/month
- t3.large (200 concurrent calls): ~$60/month

### AI Services
- OpenAI Whisper (STT): $0.006/minute
- OpenAI TTS: $0.015/1K characters (~$0.02/minute)
- OpenAI Realtime: $0.06/minute (combined)

### Estimated Monthly Cost
For 1,000 minutes of calls:
- Chime: $8
- EC2: $30
- OpenAI Realtime: $60
- **Total: ~$100/month**

Compare to Twilio with BAA: $2,000+/month minimum

## Security & Compliance

### HIPAA Considerations
1. **Encryption**: All audio encrypted in transit (TLS 1.3)
2. **Access Control**: Only authorized agents can initiate calls
3. **Audit Logging**: All calls logged with timestamps, participants
4. **Data Retention**: Call recordings encrypted and retained per policy
5. **BAA**: Not required - self-hosted infrastructure

### Security Measures
```python
# Environment variables (never commit)
SHIM_SERVER_URL=https://voice-internal.yourdomain.com
AWS_ACCESS_KEY_ID=xxxx
AWS_SECRET_ACCESS_KEY=xxxx
OPENAI_API_KEY=xxxx
ASTERISK_ARI_PASSWORD=xxxx
```

## Files to Create

```
app/telephony/
├── __init__.py
├── config.py
├── router.py
├── voice_agent_server.py
├── call_manager.py
├── audio_processor.py
├── realtime_voice.py
└── workflows/
    ├── __init__.py
    ├── patient_scheduling.py
    └── clinic_scheduling.py

deployment/
├── docker-compose.telephony.yml
├── asterisk/
│   ├── pjsip.conf
│   └── extensions.conf
└── env.example
```

## Next Steps

1. **Review this plan** with stakeholders
2. **Create AWS account** and configure Chime
3. **Set up development environment** with Docker
4. **Implement Phase 1** infrastructure
5. **Iterate** through remaining phases

## References

- [Open Telephony Stack](https://github.com/VectorlyApp/open-telephony-stack)
- [AWS Chime SDK SIP Trunking](https://docs.aws.amazon.com/chime-sdk/latest/ag/sip-trunking.html)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [Asterisk ARI Documentation](https://wiki.asterisk.org/wiki/display/AST/Asterisk+REST+Interface)
