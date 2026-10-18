"""Validate a smart-home event, then announce it with the voice CLI.

Run from the voice-accessibility-cli project root with:
    python examples/event_validator_audio_demo.py

The sibling event-schema-validator checkout is loaded from its source file so
both projects can remain independent and keep their own ``src`` packages.
"""

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys

from dotenv import load_dotenv

VOICE_PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = VOICE_PROJECT_ROOT.parent
VALIDATOR_FILE = (
    WORKSPACE_ROOT
    / "event-schema-validator"
    / "src"
    / "validators.py"
)
OUTPUT_FILE = VOICE_PROJECT_ROOT / "audio_output" / "event_validator_demo.mp3"


def load_schema_validator():
    """Load the sibling validator without colliding with this project's src."""
    if not VALIDATOR_FILE.is_file():
        raise FileNotFoundError(
            "Could not find event-schema-validator at "
            f"{VALIDATOR_FILE}. Place both project folders side-by-side."
        )

    module_name = "event_schema_validator_demo_validators"
    spec = importlib.util.spec_from_file_location(module_name, VALIDATOR_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load validator module: {VALIDATOR_FILE}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.SchemaValidator


def main() -> None:
    """Validate a Ring event and generate an MP3 for the normalized event."""
    sys.path.insert(0, str(VOICE_PROJECT_ROOT))
    load_dotenv(VOICE_PROJECT_ROOT / ".env")

    SchemaValidator = load_schema_validator()
    validator = SchemaValidator()
    event = {
        "source": "ring",
        "eventType": "doorbell",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "Front door",
        "deviceId": "demo-ring-doorbell",
    }

    result = validator.validate(event)
    if not result.valid or result.normalized_event is None:
        raise RuntimeError(f"Event validation failed: {result.errors}")

    normalized = result.normalized_event
    narration = (
        f"{normalized.urgency.value.capitalize()} alert: "
        f"{normalized.event_type.value} detected at {normalized.location}."
    )

    from src.audio import AccessibleAudio

    audio = AccessibleAudio()
    _, metadata = audio.generate_audio(
        narration,
        output_file=str(OUTPUT_FILE),
    )

    print("Event validation: passed")
    print(f"Source: {normalized.source.value}")
    print(f"Event: {normalized.event_type.value} at {normalized.location}")
    print(f"Audio file: {metadata.file_path}")
    print(f"Audio size: {metadata.file_size_bytes} bytes")
    print(f"Streaming fallback used: {metadata.used_fallback}")


if __name__ == "__main__":
    main()
