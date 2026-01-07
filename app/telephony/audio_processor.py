"""
Audio Processor - Speech-to-Text and Text-to-Speech integration.

Handles:
- μ-law (G.711) audio format conversion for telephony
- Speech-to-text via OpenAI Whisper
- Text-to-speech via OpenAI TTS
- Optional: OpenAI Realtime API for low-latency voice-to-voice
"""

import asyncio
import audioop
import io
import logging
import struct
import wave
from typing import Optional

from .config import get_telephony_config, TelephonyConfig

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Handles speech-to-text and text-to-speech for telephone audio.

    Audio Format:
    - Phone audio is 8kHz μ-law (G.711)
    - OpenAI APIs expect/produce different formats
    - This class handles all conversions
    """

    def __init__(self, config: Optional[TelephonyConfig] = None):
        """
        Initialize audio processor.

        Args:
            config: Telephony configuration
        """
        self.config = config or get_telephony_config()
        self._openai_client = None

    @property
    def openai_client(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=self.config.openai_api_key)
            except ImportError:
                logger.error("OpenAI package not installed. Run: pip install openai")
                raise
        return self._openai_client

    async def speech_to_text(self, audio_data: bytes) -> str:
        """
        Convert μ-law audio to text using OpenAI Whisper.

        Args:
            audio_data: Raw μ-law 8kHz audio bytes

        Returns:
            Transcribed text
        """
        if not audio_data or len(audio_data) < 1600:  # Less than 0.2s
            return ""

        try:
            # Convert μ-law to WAV for Whisper
            wav_data = self._mulaw_to_wav(audio_data)

            # Create a file-like object
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"

            # Call Whisper API
            response = await self.openai_client.audio.transcriptions.create(
                model=self.config.openai_stt_model,
                file=audio_file,
                response_format="text",
            )

            text = response.strip() if isinstance(response, str) else response.text.strip()
            logger.debug(f"STT result: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Speech-to-text error: {e}")
            return ""

    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to μ-law audio using OpenAI TTS.

        Args:
            text: Text to convert

        Returns:
            μ-law 8kHz audio bytes suitable for phone playback
        """
        if not text:
            return b""

        try:
            # Call TTS API - request PCM format
            response = await self.openai_client.audio.speech.create(
                model=self.config.openai_tts_model,
                voice=self.config.openai_tts_voice,
                input=text,
                response_format="pcm",  # 24kHz 16-bit mono PCM
            )

            # Get the raw audio content
            pcm_data = response.content

            # Convert to μ-law 8kHz for phone
            mulaw_data = self._pcm_to_mulaw(pcm_data, input_rate=24000)

            logger.debug(f"TTS output: {len(mulaw_data)} bytes for {len(text)} chars")
            return mulaw_data

        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
            return b""

    def _mulaw_to_wav(self, mulaw_data: bytes) -> bytes:
        """
        Convert μ-law audio to WAV format.

        Args:
            mulaw_data: Raw μ-law 8kHz audio

        Returns:
            WAV file bytes
        """
        # Decode μ-law to linear 16-bit PCM
        pcm_data = audioop.ulaw2lin(mulaw_data, 2)

        # Create WAV file in memory
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(pcm_data)

        return wav_buffer.getvalue()

    def _pcm_to_mulaw(self, pcm_data: bytes, input_rate: int = 24000) -> bytes:
        """
        Convert PCM audio to μ-law format.

        Args:
            pcm_data: Raw 16-bit PCM audio
            input_rate: Input sample rate (OpenAI outputs 24kHz)

        Returns:
            μ-law 8kHz audio bytes
        """
        # Resample to 8kHz if needed
        if input_rate != 8000:
            pcm_8k, _ = audioop.ratecv(
                pcm_data,
                2,  # 16-bit = 2 bytes per sample
                1,  # mono
                input_rate,
                8000,
                None
            )
        else:
            pcm_8k = pcm_data

        # Convert linear PCM to μ-law
        mulaw_data = audioop.lin2ulaw(pcm_8k, 2)

        return mulaw_data

    def _wav_to_mulaw(self, wav_data: bytes) -> bytes:
        """
        Convert WAV file to μ-law format.

        Args:
            wav_data: WAV file bytes

        Returns:
            μ-law 8kHz audio bytes
        """
        wav_buffer = io.BytesIO(wav_data)

        with wave.open(wav_buffer, 'rb') as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            pcm_data = wav_file.readframes(wav_file.getnframes())

        # Convert stereo to mono if needed
        if channels == 2:
            pcm_data = audioop.tomono(pcm_data, sample_width, 0.5, 0.5)

        # Resample to 8kHz if needed
        if frame_rate != 8000:
            pcm_data, _ = audioop.ratecv(
                pcm_data,
                sample_width,
                1,
                frame_rate,
                8000,
                None
            )

        # Ensure 16-bit for μ-law conversion
        if sample_width == 1:
            pcm_data = audioop.lin2lin(pcm_data, 1, 2)

        # Convert to μ-law
        return audioop.lin2ulaw(pcm_data, 2)

    def generate_silence(self, duration_ms: int) -> bytes:
        """
        Generate silence in μ-law format.

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            μ-law silence bytes
        """
        # μ-law silence is 0xFF (corresponds to 0 in linear)
        num_samples = int(8000 * duration_ms / 1000)
        return bytes([0xFF] * num_samples)

    def generate_tone(self, frequency: int, duration_ms: int, amplitude: float = 0.5) -> bytes:
        """
        Generate a tone in μ-law format.

        Useful for DTMF, busy signals, etc.

        Args:
            frequency: Tone frequency in Hz
            duration_ms: Duration in milliseconds
            amplitude: Volume (0.0 to 1.0)

        Returns:
            μ-law audio bytes
        """
        import math

        sample_rate = 8000
        num_samples = int(sample_rate * duration_ms / 1000)

        # Generate sine wave PCM
        pcm_samples = []
        for i in range(num_samples):
            t = i / sample_rate
            sample = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
            pcm_samples.append(struct.pack('<h', sample))

        pcm_data = b''.join(pcm_samples)

        # Convert to μ-law
        return audioop.lin2ulaw(pcm_data, 2)

    def calculate_audio_level(self, audio_data: bytes) -> float:
        """
        Calculate the audio level (for voice activity detection).

        Args:
            audio_data: μ-law audio bytes

        Returns:
            RMS level normalized to 0.0-1.0
        """
        if not audio_data:
            return 0.0

        # Convert to linear for RMS calculation
        pcm_data = audioop.ulaw2lin(audio_data, 2)

        # Calculate RMS
        rms = audioop.rms(pcm_data, 2)

        # Normalize (32767 is max for 16-bit)
        return min(rms / 32767.0, 1.0)

    def is_speech(self, audio_data: bytes, threshold: float = 0.02) -> bool:
        """
        Detect if audio contains speech (voice activity detection).

        Args:
            audio_data: μ-law audio bytes
            threshold: Minimum level to consider as speech

        Returns:
            True if speech detected
        """
        level = self.calculate_audio_level(audio_data)
        return level > threshold


class RealtimeVoiceProcessor:
    """
    Integration with OpenAI Realtime API for low-latency voice-to-voice.

    This provides direct voice-to-voice without intermediate STT/TTS,
    resulting in much lower latency (~300ms vs ~2s).
    """

    def __init__(self, config: Optional[TelephonyConfig] = None):
        """
        Initialize realtime voice processor.

        Args:
            config: Telephony configuration
        """
        self.config = config or get_telephony_config()
        self._ws = None

    async def connect(self, system_prompt: str, tools: list = None):
        """
        Connect to OpenAI Realtime API.

        Args:
            system_prompt: Instructions for the voice AI
            tools: Function tools available to the AI
        """
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed. Run: pip install websockets")
            raise

        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        self._ws = await websockets.connect(url, extra_headers=headers)

        # Configure session
        await self._ws.send({
            "type": "session.update",
            "session": {
                "voice": self.config.realtime_voice,
                "instructions": system_prompt,
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "tools": tools or [],
            }
        })

        logger.info("Connected to OpenAI Realtime API")

    async def send_audio(self, audio_data: bytes):
        """
        Send audio to the realtime API.

        Args:
            audio_data: μ-law audio bytes
        """
        if self._ws is None:
            raise RuntimeError("Not connected to Realtime API")

        import base64
        await self._ws.send({
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_data).decode(),
        })

    async def receive(self):
        """
        Receive events from the realtime API.

        Yields:
            Events from the API (audio, transcripts, function calls)
        """
        if self._ws is None:
            raise RuntimeError("Not connected to Realtime API")

        import json
        async for message in self._ws:
            event = json.loads(message)
            yield event

    async def close(self):
        """Close the connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None


# Singleton instance
_audio_processor: Optional[AudioProcessor] = None


def get_audio_processor() -> AudioProcessor:
    """Get or create the global audio processor instance."""
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor()
    return _audio_processor
