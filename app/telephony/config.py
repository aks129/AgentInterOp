"""
Telephony Configuration - Environment and settings for VoIP integration.

Environment Variables:
- TELEPHONY_ENABLED: Enable/disable telephony features (default: false)
- SHIM_SERVER_URL: URL of the Asterisk shim server
- CALLER_ID: Outbound caller ID number (E.164 format)
- OPENAI_API_KEY: For speech-to-text and text-to-speech
- AWS_CHIME_PHONE_NUMBER: Phone number provisioned in AWS Chime
- RTP_PORT_START: Start of RTP port range (default: 10000)
- RTP_PORT_END: End of RTP port range (default: 10299)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class TelephonyConfig:
    """Configuration for telephony/VoIP features."""

    # Feature flag
    enabled: bool = False

    # Shim server (bridges Asterisk to voice agents)
    shim_server_url: str = "http://localhost:8080"
    shim_server_timeout: int = 30

    # Asterisk ARI configuration
    ari_base_url: str = "http://localhost:8088/ari"
    ari_username: str = "ariuser"
    ari_password: str = ""
    ari_app_name: str = "voice-agent"

    # Caller ID for outbound calls (E.164 format)
    caller_id: str = "+15551234567"

    # AWS Chime configuration
    aws_chime_phone_number: Optional[str] = None
    aws_region: str = "us-east-1"

    # RTP port range (for concurrent calls)
    rtp_port_start: int = 10000
    rtp_port_end: int = 10299

    # AI/Voice configuration
    openai_api_key: Optional[str] = None
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"
    openai_stt_model: str = "whisper-1"

    # Realtime API (optional, for lower latency)
    use_realtime_api: bool = False
    realtime_voice: str = "alloy"

    # Call settings
    max_call_duration_seconds: int = 1800  # 30 minutes
    idle_timeout_seconds: int = 60
    max_concurrent_calls: int = 50

    # Audio settings
    audio_sample_rate: int = 8000  # 8kHz for telephony
    audio_encoding: str = "mulaw"  # G.711 μ-law

    # Logging and debugging
    log_transcripts: bool = True
    record_calls: bool = False
    recording_storage_path: str = "/var/recordings"

    # Supported agents for voice
    voice_enabled_agents: List[str] = field(default_factory=lambda: [
        "colonoscopy_scheduler",
    ])

    @classmethod
    def from_env(cls) -> "TelephonyConfig":
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("TELEPHONY_ENABLED", "false").lower() == "true",
            shim_server_url=os.getenv("SHIM_SERVER_URL", "http://localhost:8080"),
            shim_server_timeout=int(os.getenv("SHIM_SERVER_TIMEOUT", "30")),
            ari_base_url=os.getenv("ARI_BASE_URL", "http://localhost:8088/ari"),
            ari_username=os.getenv("ARI_USERNAME", "ariuser"),
            ari_password=os.getenv("ARI_PASSWORD", ""),
            ari_app_name=os.getenv("ARI_APP_NAME", "voice-agent"),
            caller_id=os.getenv("CALLER_ID", "+15551234567"),
            aws_chime_phone_number=os.getenv("AWS_CHIME_PHONE_NUMBER"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            rtp_port_start=int(os.getenv("RTP_PORT_START", "10000")),
            rtp_port_end=int(os.getenv("RTP_PORT_END", "10299")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "tts-1"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
            openai_stt_model=os.getenv("OPENAI_STT_MODEL", "whisper-1"),
            use_realtime_api=os.getenv("USE_REALTIME_API", "false").lower() == "true",
            realtime_voice=os.getenv("REALTIME_VOICE", "alloy"),
            max_call_duration_seconds=int(os.getenv("MAX_CALL_DURATION", "1800")),
            idle_timeout_seconds=int(os.getenv("IDLE_TIMEOUT", "60")),
            max_concurrent_calls=int(os.getenv("MAX_CONCURRENT_CALLS", "50")),
            log_transcripts=os.getenv("LOG_TRANSCRIPTS", "true").lower() == "true",
            record_calls=os.getenv("RECORD_CALLS", "false").lower() == "true",
            recording_storage_path=os.getenv("RECORDING_STORAGE_PATH", "/var/recordings"),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if self.enabled:
            if not self.openai_api_key:
                issues.append("OPENAI_API_KEY required for speech processing")

            if not self.ari_password:
                issues.append("ARI_PASSWORD required for Asterisk connection")

            if self.rtp_port_start >= self.rtp_port_end:
                issues.append("RTP_PORT_START must be less than RTP_PORT_END")

            # Check port range supports concurrent calls
            port_count = self.rtp_port_end - self.rtp_port_start
            if port_count < self.max_concurrent_calls:
                issues.append(
                    f"RTP port range ({port_count}) smaller than max concurrent calls "
                    f"({self.max_concurrent_calls})"
                )

        return issues

    @property
    def is_ready(self) -> bool:
        """Check if telephony is enabled and properly configured."""
        return self.enabled and len(self.validate()) == 0

    @property
    def max_rtp_ports(self) -> int:
        """Number of available RTP ports (max concurrent calls)."""
        return self.rtp_port_end - self.rtp_port_start


@lru_cache()
def get_telephony_config() -> TelephonyConfig:
    """Get cached telephony configuration."""
    config = TelephonyConfig.from_env()

    if config.enabled:
        issues = config.validate()
        if issues:
            for issue in issues:
                logger.warning(f"Telephony config issue: {issue}")
        else:
            logger.info("Telephony configuration loaded successfully")
            logger.info(f"  Shim server: {config.shim_server_url}")
            logger.info(f"  Max concurrent calls: {config.max_concurrent_calls}")
            logger.info(f"  Voice agents: {config.voice_enabled_agents}")
    else:
        logger.info("Telephony features disabled")

    return config


def is_telephony_enabled() -> bool:
    """Quick check if telephony is enabled."""
    return os.getenv("TELEPHONY_ENABLED", "false").lower() == "true"
