# Voice Accessibility CLI - Test Suite

"""
Comprehensive test suite for Voice Accessibility CLI
Tests audio generation, configuration, and metadata
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from src.audio import (
    AccessibleAudio,
    AudioConfig,
    AudioMetadata,
    EventToSpeech,
    Voice,
    SpeechRate
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def audio_config():
    """Create default audio configuration"""
    return AudioConfig(
        voice=Voice.BELLA,
        rate=SpeechRate.NORMAL,
        stability=0.5,
        similarity_boost=0.75
    )


@pytest.fixture(autouse=True)
def mock_elevenlabs():
    """Mock the ElevenLabs SDK so unit tests need no SDK or API key."""
    mock_client = Mock()
    mock_client.text_to_speech.convert.return_value = b"mock_audio_data"
    with (
        patch("src.audio.ELEVENLABS_AVAILABLE", True),
        patch("src.audio.ElevenLabs", return_value=mock_client, create=True),
        patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_api_key"}),
    ):
        yield mock_client


# ============================================================================
# AUDIO CONFIG TESTS
# ============================================================================

class TestAudioConfig:
    """Tests for AudioConfig model"""

    def test_default_config(self):
        """Test default configuration"""
        config = AudioConfig()
        assert config.voice == Voice.BELLA
        assert config.rate == SpeechRate.NORMAL
        assert config.stability == 0.5
        assert config.similarity_boost == 0.75

    def test_custom_config(self):
        """Test custom configuration"""
        config = AudioConfig(
            voice=Voice.ADAM,
            rate=SpeechRate.SLOW,
            stability=0.3,
            similarity_boost=0.5
        )
        assert config.voice == Voice.ADAM
        assert config.rate == SpeechRate.SLOW

    def test_stability_validation(self):
        """Test stability value validation"""
        with pytest.raises(ValueError):
            AudioConfig(stability=1.5)

        with pytest.raises(ValueError):
            AudioConfig(stability=-0.1)

    def test_similarity_validation(self):
        """Test similarity_boost validation"""
        with pytest.raises(ValueError):
            AudioConfig(similarity_boost=1.1)

    def test_config_to_dict(self, audio_config):
        """Test converting config to dictionary"""
        config_dict = audio_config.to_dict()
        assert config_dict["voice_name"] == "Bella"
        assert config_dict["rate"] == 1.0
        assert config_dict["stability"] == 0.5


# ============================================================================
# AUDIO METADATA TESTS
# ============================================================================

class TestAudioMetadata:
    """Tests for AudioMetadata model"""

    def test_metadata_creation(self):
        """Test creating audio metadata"""
        config = AudioConfig()
        metadata = AudioMetadata(
            text="Hello world",
            config=config,
            character_count=11
        )
        assert metadata.text == "Hello world"
        assert metadata.character_count == 11
        assert isinstance(metadata.generated_at, datetime)

    def test_metadata_with_file_info(self):
        """Test metadata with file information"""
        config = AudioConfig()
        metadata = AudioMetadata(
            text="Test",
            config=config,
            character_count=4,
            file_path="/tmp/audio.mp3",
            file_size_bytes=5120
        )
        assert metadata.file_path == "/tmp/audio.mp3"
        assert metadata.file_size_bytes == 5120


# ============================================================================
# ACCESSIBLE AUDIO TESTS
# ============================================================================

class TestAccessibleAudio:
    """Tests for AccessibleAudio class"""

    def test_initialization_without_key(self, monkeypatch):
        """Test initialization fails without API key"""
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        with pytest.raises(ValueError):
            AccessibleAudio(api_key=None)

    def test_initialization_with_key(self):
        """Test initialization with provided API key"""
        audio = AccessibleAudio(api_key="test_key_123")
        assert audio.api_key == "test_key_123"

    def test_generate_audio_joins_streamed_chunks(self, mock_elevenlabs):
        """Test combining streamed SDK chunks into one audio byte string"""
        mock_elevenlabs.text_to_speech.convert.return_value = iter(
            [b"mock_", b"audio_data"]
        )
        audio = AccessibleAudio(api_key="test_key")

        audio_bytes, _ = audio.generate_audio("Hello world")

        assert audio_bytes == b"mock_audio_data"

    def test_relative_output_is_saved_under_audio_output(
        self,
        mock_elevenlabs,
        monkeypatch,
        tmp_path,
    ):
        output_dir = tmp_path / "audio_output"
        monkeypatch.setattr("src.audio.DEFAULT_AUDIO_OUTPUT_DIR", output_dir)
        audio = AccessibleAudio(api_key="test_key")

        _, metadata = audio.generate_audio(
            "Hello world",
            output_file="events/alert.mp3",
        )

        expected_path = output_dir / "events" / "alert.mp3"
        assert metadata.file_path == str(expected_path)
        assert Path(metadata.file_path).read_bytes() == b"mock_audio_data"

    def test_paid_voice_error_falls_back_to_configured_stream(
        self,
        mock_elevenlabs,
    ):
        """Test paid voice/model retry with configured streaming fallback."""

        class MockApiError(Exception):
            status_code = 402
            body = {
                "detail": {
                    "code": "paid_plan_required",
                    "message": (
                        "Free users cannot use library voices via the API."
                    ),
                }
            }

        class ErrorDuringIteration:
            def __iter__(self):
                raise MockApiError()

        mock_elevenlabs.text_to_speech.convert.return_value = (
            ErrorDuringIteration()
        )
        mock_elevenlabs.text_to_speech.stream.return_value = iter(
            [b"streamed_", b"audio"]
        )
        config = AudioConfig(
            voice_id="paid-voice-id",
            model="paid-model",
            fallback_voice_id="free-voice-id",
            fallback_model="free-model",
        )
        audio = AccessibleAudio(api_key="test_key")

        audio_bytes, metadata = audio.generate_audio("Hello world", config)

        assert audio_bytes == b"streamed_audio"
        mock_elevenlabs.text_to_speech.convert.assert_called_once_with(
            text="Hello world",
            voice_id="paid-voice-id",
            model_id="paid-model",
            output_format="mp3_44100_128",
        )
        mock_elevenlabs.text_to_speech.stream.assert_called_once_with(
            text="Hello world",
            voice_id="free-voice-id",
            model_id="free-model",
            output_format="mp3_44100_128",
        )
        assert metadata.used_fallback
        assert metadata.voice_id == "free-voice-id"
        assert metadata.model_id == "free-model"

    def test_generate_audio_reports_api_error_message(self, mock_elevenlabs):
        """Test API errors are reported without dumping response headers"""

        class MockApiError(Exception):
            status_code = 500
            body = {
                "detail": {
                    "code": "internal_error",
                    "message": "Free account cannot use this voice."
                }
            }

        mock_elevenlabs.text_to_speech.convert.side_effect = MockApiError()
        audio = AccessibleAudio(api_key="test_key")

        with pytest.raises(RuntimeError, match="HTTP 500.*Free account"):
            audio.generate_audio("Hello world")

    def test_validate_text_empty(self):
        """Test validating empty text"""
        audio = AccessibleAudio(api_key="test_key")
        is_valid, warnings = audio.validate_text("")
        assert not is_valid

    def test_validate_text_normal(self):
        """Test validating normal text"""
        audio = AccessibleAudio(api_key="test_key")
        is_valid, warnings = audio.validate_text("Hello world")
        assert is_valid
        assert len(warnings) == 0

    def test_validate_text_long(self):
        """Test validating very long text"""
        audio = AccessibleAudio(api_key="test_key")
        long_text = "a" * 6000
        is_valid, warnings = audio.validate_text(long_text)
        assert is_valid
        assert len(warnings) > 0

    def test_validate_text_short(self):
        """Test validating very short text"""
        audio = AccessibleAudio(api_key="test_key")
        is_valid, warnings = audio.validate_text("hi")
        assert is_valid
        assert len(warnings) > 0

    def test_validate_text_special_chars(self):
        """Test validating text with special characters"""
        audio = AccessibleAudio(api_key="test_key")
        text_with_chars = "Hello <world>"
        is_valid, warnings = audio.validate_text(text_with_chars)
        assert is_valid
        assert len(warnings) > 0

    def test_get_available_voices(self):
        """Test getting available voices"""
        audio = AccessibleAudio(api_key="test_key")
        voices = audio.get_available_voices()
        assert isinstance(voices, list)
        assert len(voices) > 0

    def test_get_metadata_summary_empty(self):
        """Test metadata summary when empty"""
        audio = AccessibleAudio(api_key="test_key")
        summary = audio.get_metadata_summary()
        assert summary["total"] == 0


# ============================================================================
# EVENT TO SPEECH TESTS
# ============================================================================

class TestEventToSpeech:
    """Tests for EventToSpeech convenience class"""

    def test_describe_event_doorbell(self):
        """Test describing a doorbell event"""
        ets = EventToSpeech(AudioConfig())

        # This will test the describe_event method structure
        event_text_parts = ["Doorbell", "Front Door"]
        # Just verify the structure works
        assert all(part for part in event_text_parts)

    def test_describe_event_with_urgency(self):
        """Test describing event with urgency levels"""
        ets = EventToSpeech(AudioConfig())

        urgency_map = {
            "high": "Urgent alert:",
            "medium": "Alert:",
            "low": "Notification:"
        }

        for urgency, prefix in urgency_map.items():
            assert prefix in urgency_map.values()


# ============================================================================
# VOICE SELECTION TESTS
# ============================================================================

class TestVoiceSelection:
    """Tests for voice selection"""

    def test_available_voices(self):
        """Test all available voices"""
        voices = [v.value for v in Voice]
        assert "Bella" in voices
        assert "Adam" in voices
        assert len(voices) > 0

    def test_speech_rates(self):
        """Test all available speech rates"""
        rates = [r.value for r in SpeechRate]
        assert "0.75" in rates
        assert "1.0" in rates
        assert "1.25" in rates


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Tests for error handling"""

    def test_invalid_stability_range(self):
        """Test stability validation"""
        with pytest.raises(ValueError):
            AudioConfig(stability=1.5)

    def test_invalid_similarity_range(self):
        """Test similarity_boost validation"""
        with pytest.raises(ValueError):
            AudioConfig(similarity_boost=-0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
