"""
Voice Agent Server - Handles WebSocket connections from Asterisk shim server.

Bridges phone calls to AgentInterOp agents, handling:
- Bidirectional audio streaming
- Speech-to-text conversion
- Agent message processing
- Text-to-speech conversion

WebSocket Protocol (Twilio-compatible):
- "start" event: Call initiated with metadata
- "media" event: Audio frames (base64 μ-law)
- "mark" event: Audio playback position tracking
- "stop" event: Call ended
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

logger = logging.getLogger(__name__)


class CallStatus(str, Enum):
    """Status of an active call."""
    CONNECTING = "connecting"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    TRANSFERRING = "transferring"
    ENDED = "ended"
    FAILED = "failed"


@dataclass
class CallState:
    """State for an active phone call."""
    call_id: str
    stream_id: str
    caller: str
    callee: str
    agent_id: str
    direction: str = "inbound"  # inbound or outbound
    status: CallStatus = CallStatus.CONNECTING
    started_at: datetime = field(default_factory=datetime.now)
    transcript: List[Dict[str, Any]] = field(default_factory=list)
    intake_data: Dict[str, Any] = field(default_factory=dict)
    audio_buffer: bytearray = field(default_factory=bytearray)
    last_activity: datetime = field(default_factory=datetime.now)
    greeting_sent: bool = False
    current_question: Optional[str] = None
    pending_marks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "call_id": self.call_id,
            "stream_id": self.stream_id,
            "caller": self.caller,
            "callee": self.callee,
            "agent_id": self.agent_id,
            "direction": self.direction,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "transcript_length": len(self.transcript),
            "intake_data_count": len(self.intake_data),
        }


class VoiceAgentServer:
    """
    Handles WebSocket connections from the Asterisk shim server.
    Converts audio to text, processes with agents, converts response to audio.
    """

    def __init__(self, agent_factory: Callable, audio_processor=None):
        """
        Initialize voice agent server.

        Args:
            agent_factory: Function that creates agents given agent_id
            audio_processor: AudioProcessor instance for STT/TTS
        """
        self.active_calls: Dict[str, CallState] = {}
        self.agent_factory = agent_factory
        self.audio_processor = audio_processor
        self._agents: Dict[str, Any] = {}  # Cache of agent instances per call

    async def handle_call(self, websocket, call_id: str):
        """
        Handle incoming WebSocket connection for a phone call.

        Args:
            websocket: WebSocket connection from shim server
            call_id: Unique identifier for this call
        """
        logger.info(f"New call connection: {call_id}")

        try:
            # Wait for start event
            start_data = await websocket.receive_text()
            start_event = json.loads(start_data)

            if start_event.get("event") != "start":
                logger.error(f"Expected 'start' event, got: {start_event.get('event')}")
                return

            # Extract call metadata
            metadata = start_event.get("start", {})
            stream_id = metadata.get("streamSid", call_id)
            custom_params = metadata.get("customParameters", {})

            # Determine which agent to use based on call routing
            agent_id = custom_params.get("agent", "colonoscopy_scheduler")
            direction = custom_params.get("direction", "inbound")

            # Create call state
            call_state = CallState(
                call_id=call_id,
                stream_id=stream_id,
                caller=custom_params.get("from", "unknown"),
                callee=custom_params.get("to", "unknown"),
                agent_id=agent_id,
                direction=direction,
                status=CallStatus.ACTIVE,
            )
            self.active_calls[call_id] = call_state

            # Initialize agent for this call
            agent = self.agent_factory(agent_id)
            self._agents[call_id] = agent

            logger.info(
                f"Call {call_id} started: {call_state.caller} -> {call_state.callee}, "
                f"agent={agent_id}, direction={direction}"
            )

            # Send initial greeting
            greeting = self._get_greeting(agent_id, direction)
            await self._send_audio_response(websocket, greeting, stream_id)
            call_state.greeting_sent = True

            # Add greeting to transcript
            call_state.transcript.append({
                "role": "agent",
                "content": greeting,
                "timestamp": datetime.now().isoformat(),
            })

            # Process call events
            await self._process_call_events(websocket, call_state, agent)

        except Exception as e:
            logger.exception(f"Error handling call {call_id}: {e}")
            if call_id in self.active_calls:
                self.active_calls[call_id].status = CallStatus.FAILED
        finally:
            # Cleanup
            await self._cleanup_call(call_id)

    async def _process_call_events(self, websocket, call_state: CallState, agent):
        """
        Process audio events from the call.

        Accumulates audio, detects speech end, converts to text,
        processes with agent, and responds with audio.
        """
        silence_threshold = 0.5  # seconds of silence to detect end of speech
        last_audio_time = datetime.now()

        while call_state.status == CallStatus.ACTIVE:
            try:
                # Receive with timeout for idle detection
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 1 minute idle timeout
                )
                event = json.loads(data)
                event_type = event.get("event")

                if event_type == "media":
                    # Accumulate audio
                    payload = event.get("media", {}).get("payload", "")
                    if payload:
                        audio_bytes = base64.b64decode(payload)
                        call_state.audio_buffer.extend(audio_bytes)
                        call_state.last_activity = datetime.now()
                        last_audio_time = datetime.now()

                    # Check for end of speech (silence detection)
                    # In production, use VAD (Voice Activity Detection)
                    if len(call_state.audio_buffer) > 16000:  # ~2 seconds of audio
                        if self._detect_silence(call_state.audio_buffer[-1600:]):
                            await self._process_speech(
                                websocket, call_state, agent
                            )

                elif event_type == "mark":
                    # Audio playback position marker
                    mark_name = event.get("mark", {}).get("name")
                    if mark_name:
                        call_state.pending_marks.append(mark_name)
                        logger.debug(f"Mark received: {mark_name}")

                elif event_type == "stop":
                    logger.info(f"Call {call_state.call_id} received stop event")
                    call_state.status = CallStatus.ENDED
                    break

                elif event_type == "clear":
                    # Clear audio buffer (user interrupted)
                    call_state.audio_buffer.clear()
                    logger.debug("Audio buffer cleared (interruption)")

            except asyncio.TimeoutError:
                # Idle timeout - check if call should end
                idle_seconds = (datetime.now() - call_state.last_activity).total_seconds()
                if idle_seconds > 120:  # 2 minutes idle
                    logger.info(f"Call {call_state.call_id} idle timeout")
                    await self._send_audio_response(
                        websocket,
                        "I haven't heard from you in a while. "
                        "Please say something or I'll end the call.",
                        call_state.stream_id
                    )
                    # Give them 30 more seconds
                    await asyncio.sleep(30)
                    if (datetime.now() - call_state.last_activity).total_seconds() > 150:
                        call_state.status = CallStatus.ENDED
                        break

            except Exception as e:
                logger.exception(f"Error processing event: {e}")
                break

    async def _process_speech(self, websocket, call_state: CallState, agent):
        """Process accumulated speech audio."""
        if not call_state.audio_buffer:
            return

        # Get the audio data
        audio_data = bytes(call_state.audio_buffer)
        call_state.audio_buffer.clear()

        # Convert speech to text
        if self.audio_processor:
            try:
                text = await self.audio_processor.speech_to_text(audio_data)
            except Exception as e:
                logger.error(f"STT error: {e}")
                text = ""
        else:
            # Placeholder when audio processor not available
            logger.warning("No audio processor configured, skipping STT")
            text = "[Audio received but STT not configured]"

        if not text or len(text.strip()) < 2:
            return

        logger.info(f"User said: {text}")

        # Add to transcript
        call_state.transcript.append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now().isoformat(),
        })

        # Process with agent
        try:
            response = agent.process_message(text, {
                "call_id": call_state.call_id,
                "caller": call_state.caller,
                "channel": "voice",
            })

            # Extract response text
            response_text = response.get("message", "")
            if not response_text:
                response_text = "I'm sorry, I didn't understand that. Could you please repeat?"

            # Optimize for voice
            response_text = self._optimize_for_voice(response_text)

            # Add to transcript
            call_state.transcript.append({
                "role": "agent",
                "content": response_text,
                "timestamp": datetime.now().isoformat(),
            })

            # Store any captured intake data
            if response.get("captured_data"):
                call_state.intake_data.update(response["captured_data"])

            # Check for call end triggers
            if response.get("action") == "end_call" or response.get("status") == "completed":
                # Send closing message and end
                await self._send_audio_response(
                    websocket, response_text, call_state.stream_id
                )
                await asyncio.sleep(3)  # Wait for audio to play
                call_state.status = CallStatus.ENDED
                return

            # Send audio response
            await self._send_audio_response(
                websocket, response_text, call_state.stream_id
            )

        except Exception as e:
            logger.exception(f"Error processing with agent: {e}")
            await self._send_audio_response(
                websocket,
                "I'm having trouble processing that. Could you please try again?",
                call_state.stream_id
            )

    async def _send_audio_response(self, websocket, text: str, stream_id: str):
        """Convert text to speech and send via WebSocket."""
        logger.info(f"Agent says: {text}")

        if self.audio_processor:
            try:
                audio_data = await self.audio_processor.text_to_speech(text)

                # Send audio in chunks (160 bytes = 20ms at 8kHz μ-law)
                chunk_size = 160
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    payload = base64.b64encode(chunk).decode()

                    message = {
                        "event": "media",
                        "streamSid": stream_id,
                        "media": {
                            "payload": payload,
                        }
                    }
                    await websocket.send_text(json.dumps(message))

                    # Pace at 20ms intervals
                    await asyncio.sleep(0.02)

                # Send mark to track playback completion
                mark_id = f"msg-{datetime.now().timestamp()}"
                await websocket.send_text(json.dumps({
                    "event": "mark",
                    "streamSid": stream_id,
                    "mark": {"name": mark_id}
                }))

            except Exception as e:
                logger.error(f"TTS error: {e}")
        else:
            logger.warning("No audio processor configured, skipping TTS")

    def _get_greeting(self, agent_id: str, direction: str) -> str:
        """Get initial greeting for the agent."""
        if direction == "outbound":
            # Agent initiated the call
            greetings = {
                "colonoscopy_scheduler": (
                    "Hello, this is the automated scheduling assistant calling from "
                    "G I Specialists. I'm calling to help schedule a colonoscopy appointment. "
                    "Is this a good time to talk?"
                ),
            }
        else:
            # Inbound call from patient
            greetings = {
                "colonoscopy_scheduler": (
                    "Hello, thank you for calling G I Specialists scheduling. "
                    "I'm an automated assistant and I can help you schedule your "
                    "colonoscopy appointment. To get started, may I have your full name please?"
                ),
            }

        return greetings.get(agent_id, "Hello, how may I help you today?")

    def _optimize_for_voice(self, text: str) -> str:
        """Make text more suitable for text-to-speech."""
        # Limit length for voice
        if len(text) > 300:
            sentences = text.split('. ')
            text = '. '.join(sentences[:4])
            if not text.endswith('.'):
                text += '.'

        # Replace abbreviations for better TTS pronunciation
        replacements = {
            "DOB": "date of birth",
            "PCP": "primary care provider",
            "GI": "G I",
            "ID": "I D",
            "Dr.": "Doctor",
            "Appt": "Appointment",
            "appt": "appointment",
            "w/": "with",
            "vs": "versus",
            "&": "and",
        }
        for abbr, full in replacements.items():
            text = text.replace(abbr, full)

        # Remove markdown formatting
        text = text.replace("**", "")
        text = text.replace("*", "")
        text = text.replace("`", "")

        return text

    def _detect_silence(self, audio_chunk: bytes) -> bool:
        """
        Detect if audio chunk is silence.

        For μ-law audio, silence is typically 0xFF (127 in linear).
        """
        if not audio_chunk:
            return True

        # Count silence samples (0xFF in μ-law)
        silence_count = sum(1 for b in audio_chunk if b == 0xFF or b == 0x7F)
        silence_ratio = silence_count / len(audio_chunk)

        return silence_ratio > 0.9  # 90% silence

    async def _cleanup_call(self, call_id: str):
        """Clean up resources for ended call."""
        if call_id in self.active_calls:
            call_state = self.active_calls[call_id]
            call_state.status = CallStatus.ENDED

            # Log final transcript
            logger.info(f"Call {call_id} ended. Transcript length: {len(call_state.transcript)}")

            # Store transcript for later retrieval
            # In production, save to database

            # Remove from active calls after brief delay
            await asyncio.sleep(5)
            if call_id in self.active_calls:
                del self.active_calls[call_id]

        if call_id in self._agents:
            del self._agents[call_id]

        logger.info(f"Call {call_id} cleaned up")

    def get_active_calls(self) -> List[Dict[str, Any]]:
        """Get list of active calls."""
        return [call.to_dict() for call in self.active_calls.values()]

    def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get call details including transcript."""
        if call_id not in self.active_calls:
            return None

        call = self.active_calls[call_id]
        result = call.to_dict()
        result["transcript"] = call.transcript
        result["intake_data"] = call.intake_data
        return result
