# PROJECT 2: Package Initialization
# File: src/__init__.py

"""
Voice Accessibility CLI - Generate accessible audio from text
Powered by ElevenLabs TTS
"""

from .audio import (
    AccessibleAudio,
    AudioConfig,
    AudioMetadata,
    EventToSpeech,
    Voice,
    SpeechRate,
)

__version__ = "1.0.0"
__author__ = "Hacktoberfest 2026"

__all__ = [
    "AccessibleAudio",
    "AudioConfig",
    "AudioMetadata",
    "EventToSpeech",
    "Voice",
    "SpeechRate",
]
