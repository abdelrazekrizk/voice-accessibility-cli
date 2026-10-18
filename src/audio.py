# Voice Accessibility CLI - Audio Module

"""
Voice Accessibility CLI - Text to Speech for event accessibility
Demonstrates Best Use of ElevenLabs for the Hacktoberfest challenge
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json
from dotenv import load_dotenv

# Import ElevenLabs SDK
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.play import play
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_OUTPUT_DIR = PROJECT_ROOT / "audio_output"


def _resolve_output_path(output_file: str) -> Path:
    """Put relative audio paths in the project's audio output directory."""
    path = Path(output_file)
    if not path.is_absolute():
        if path.parts and path.parts[0] == DEFAULT_AUDIO_OUTPUT_DIR.name:
            path = PROJECT_ROOT / path
        else:
            path = DEFAULT_AUDIO_OUTPUT_DIR / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class Voice(str, Enum):
    """Available ElevenLabs voices"""
    ADAM = "Adam"
    BELLA = "Bella"
    ANTONI = "Antoni"
    SAM = "Sam"
    RACHAEL = "Rachael"
    JONATHAN = "Jonathan"
    DANIEL = "Daniel"
    LILY = "Lily"


class SpeechRate(str, Enum):
    """Speech rate options (playback speed multipliers)"""
    SLOW = "0.75"
    NORMAL = "1.0"
    FAST = "1.25"


class AudioConfig(BaseModel):
    """Audio configuration for TTS"""

    voice: Voice = Field(default=Voice.BELLA, description="Voice to use")
    voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM",
        description="Primary ElevenLabs voice ID",
    )
    rate: SpeechRate = Field(
        default=SpeechRate.NORMAL,
        description="Speech rate",
    )
    language: str = Field(
        default="en",
        description="Language code (e.g., en, es, fr)",
    )
    stability: float = Field(
        default=0.5,
        description="Voice stability (0-1, higher = more stable)",
    )
    similarity_boost: float = Field(
        default=0.75,
        description="Similarity boost (0-1)",
    )
    model: str = Field(
        default="eleven_v4",
        description="Primary ElevenLabs model",
    )
    fallback_voice_id: str = Field(
        default="JBFqnCBsd6RMkjVDRZzb",
        description="Voice ID used for streaming fallback",
    )
    fallback_model: str = Field(
        default="eleven_multilingual_v2",
        description="Model used for streaming fallback",
    )

    @validator("stability", "similarity_boost")
    def validate_range(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Value must be between 0 and 1")
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "voice_name": self.voice.value,
            "voice_id": self.voice_id,
            "rate": float(self.rate.value),
            "language": self.language,
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "model": self.model,
            "fallback_voice_id": self.fallback_voice_id,
            "fallback_model": self.fallback_model,
        }


class AudioMetadata(BaseModel):
    """Metadata for generated audio"""

    text: str
    config: AudioConfig
    voice_id: Optional[str] = None
    model_id: Optional[str] = None
    used_fallback: bool = False
    duration_seconds: Optional[float] = None
    character_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None


class AccessibleAudio:
    """
    Main class for generating accessible audio from text
    Integrates with ElevenLabs for high-quality TTS
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize audio generator

        Args:
            api_key: ElevenLabs API key (or uses environment variable)
        """
        if not ELEVENLABS_AVAILABLE:
            raise ImportError("ElevenLabs SDK not installed. Install with: pip install elevenlabs")

        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set and not provided")

        self.client = ElevenLabs(api_key=self.api_key)
        self.metadata_history: List[AudioMetadata] = []

    def generate_audio(
        self,
        text: str,
        config: Optional[AudioConfig] = None,
        output_file: Optional[str] = None,
        stream_audio: bool = False
    ) -> Tuple[Optional[bytes], AudioMetadata]:
        """
        Generate audio from text

        Args:
            text: Text to convert to speech
            config: Audio configuration (uses default if None)
            output_file: Optional file path to save audio
            stream_audio: Whether to stream audio (play immediately)

        Returns:
            Tuple of (audio_bytes, metadata)
        """
        if config is None:
            config = AudioConfig()

        metadata = AudioMetadata(
            text=text,
            config=config,
            character_count=len(text)
        )

        used_fallback = False
        voice_id = config.voice_id
        model_id = config.model

        try:
            try:
                audio_data = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id=model_id,
                    output_format="mp3_44100_128",
                )
                audio_bytes = self._collect_audio(audio_data)
            except Exception as primary_error:
                if not self._is_paid_voice_restriction(primary_error):
                    raise

                voice_id = config.fallback_voice_id
                model_id = config.fallback_model
                used_fallback = True
                audio_data = self.client.text_to_speech.stream(
                    text=text,
                    voice_id=voice_id,
                    model_id=model_id,
                    output_format="mp3_44100_128",
                )
                audio_bytes = self._collect_audio(audio_data)

            metadata.voice_id = voice_id
            metadata.model_id = model_id
            metadata.used_fallback = used_fallback

            # Save to file if specified
            if output_file:
                output_path = _resolve_output_path(output_file)
                with output_path.open("wb") as f:
                    f.write(audio_bytes)
                metadata.file_path = str(output_path)
                metadata.file_size_bytes = len(audio_bytes)

                # Estimate duration (rough: ~150 chars per second)
                metadata.duration_seconds = len(text) / 150.0

            self.metadata_history.append(metadata)
            return audio_bytes, metadata

        except Exception as e:
            raise RuntimeError(
                f"Failed to generate audio: {self._format_api_error(e)}"
            ) from e

    @staticmethod
    def _collect_audio(audio_data) -> bytes:
        """Collect the SDK's byte response or lazy byte iterator."""
        if isinstance(audio_data, bytes):
            return audio_data
        return b"".join(audio_data)

    @staticmethod
    def _error_details(
        error: Exception,
    ) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        status_code = getattr(error, "status_code", None)
        error_body = getattr(error, "body", None)
        detail = (
            error_body.get("detail", {})
            if isinstance(error_body, dict)
            else {}
        )
        if not isinstance(detail, dict):
            return status_code, None, None
        return status_code, detail.get("code"), detail.get("message")

    @classmethod
    def _is_paid_voice_restriction(cls, error: Exception) -> bool:
        status_code, error_code, message = cls._error_details(error)
        return status_code == 402 and (
            error_code == "paid_plan_required"
            or "free users cannot use library voices"
            in (message or "").lower()
        )

    @classmethod
    def _format_api_error(cls, error: Exception) -> str:
        status_code, _, message = cls._error_details(error)
        if status_code and message:
            return f"ElevenLabs returned HTTP {status_code}: {message}"
        return str(error)

    def batch_generate(
        self,
        texts: List[str],
        config: Optional[AudioConfig] = None,
        output_dir: Optional[str] = None,
    ) -> List[Tuple[Optional[str], AudioMetadata]]:
        """
        Generate audio for multiple texts

        Args:
            texts: List of texts to convert
            config: Audio configuration
            output_dir: Directory to save audio files

        Returns:
            List of (file_path, metadata) tuples
        """
        if config is None:
            config = AudioConfig()

        if output_dir:
            output_directory = Path(output_dir)
            if not output_directory.is_absolute():
                output_directory = output_directory.resolve()
            output_directory.mkdir(parents=True, exist_ok=True)
        else:
            output_directory = None

        results = []
        for i, text in enumerate(texts):
            output_file = None
            if output_directory:
                output_file = str(output_directory / f"audio_{i:03d}.mp3")

            try:
                _, metadata = self.generate_audio(text, config, output_file)
                results.append((output_file, metadata))
            except Exception as e:
                print(f"Error generating audio {i}: {str(e)}")
                results.append((None, AudioMetadata(text=text, config=config)))

        return results

    def get_available_voices(self) -> List[str]:
        """Get list of available voices"""
        try:
            if ELEVENLABS_AVAILABLE:
                voices_list = get_voices()
                return [v.name for v in voices_list]
        except Exception:
            pass

        # Return hardcoded list if API call fails
        return [v.value for v in Voice]

    def validate_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate text for audio generation

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        if not text:
            return False, ["Text is empty"]

        if len(text) > 5000:
            warnings.append(f"Text is long ({len(text)} chars), may take time to process")

        if len(text) < 5:
            warnings.append("Text is very short, audio may be brief")

        # Check for problematic characters
        if any(c in text for c in ['<', '>', '{', '}']):
            warnings.append("Text contains special characters that may affect pronunciation")

        return True, warnings

    def get_metadata_summary(self) -> dict:
        """Get summary of all generated audio"""
        if not self.metadata_history:
            return {"total": 0, "history": []}

        return {
            "total": len(self.metadata_history),
            "total_characters": sum(m.character_count for m in self.metadata_history),
            "total_duration_seconds": sum(m.duration_seconds or 0 for m in self.metadata_history),
            "history": [
                {
                    "text": m.text[:50] + "..." if len(m.text) > 50 else m.text,
                    "voice": m.config.voice.value,
                    "characters": m.character_count,
                    "file_path": m.file_path,
                    "generated_at": m.generated_at.isoformat()
                }
                for m in self.metadata_history
            ]
        }


class EventToSpeech:
    """
    Convenience class for converting events to accessible speech
    Perfect for integration with AccessibleAudioApp
    """

    def __init__(self, default_config: Optional[AudioConfig] = None):
        self.audio = AccessibleAudio()
        self.default_config = default_config or AudioConfig()

    def describe_event(
        self,
        event_type: str,
        location: str,
        urgency: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Tuple[Optional[bytes], AudioMetadata]:
        """
        Generate audio description of an event

        Args:
            event_type: Type of event (doorbell, motion, etc.)
            location: Location of event
            urgency: Urgency level (high, medium, low)
            output_file: Optional file to save audio

        Returns:
            Tuple of (audio_bytes, metadata)
        """
        # Build natural language description
        urgency_map = {
            "high": "Urgent alert:",
            "medium": "Alert:",
            "low": "Notification:"
        }

        prefix = urgency_map.get(urgency, "Alert:")
        text = f"{prefix} {event_type} detected at {location}"

        return self.audio.generate_audio(text, self.default_config, output_file)


# Export main classes
__all__ = [
    "AccessibleAudio",
    "AudioConfig",
    "AudioMetadata",
    "EventToSpeech",
    "Voice",
    "SpeechRate",
]
