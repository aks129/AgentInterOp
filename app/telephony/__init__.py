"""
Telephony Module - VoIP integration for agent phone calling capabilities.

This module enables agents to make and receive phone calls using the
open-telephony-stack (Asterisk + AWS Chime SIP trunking).

Components:
- voice_agent_server: WebSocket handler for voice calls
- call_manager: Call lifecycle management
- audio_processor: Speech-to-text and text-to-speech
- workflows: Pre-built calling workflows
"""

from .config import TelephonyConfig, get_telephony_config
from .call_manager import CallManager
from .voice_agent_server import VoiceAgentServer

__all__ = [
    "TelephonyConfig",
    "get_telephony_config",
    "CallManager",
    "VoiceAgentServer",
]
