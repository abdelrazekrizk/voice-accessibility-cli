# Voice Accessibility CLI: usage examples

Start with the installation and API-key setup in [Setup](SETUP.md). Commands below run from the project root and make paid/limited remote requests when they generate audio.

## CLI examples

### Generate speech from text

```powershell
& .\.venv\Scripts\python.exe src\cli.py generate --text "Motion detected at the back door" --output motion.mp3
```

The output is saved to `audio_output/motion.mp3`. To see all options, run `src\cli.py generate --help`.

### Compose a smart-home event alert

```powershell
& .\.venv\Scripts\python.exe src\cli.py event --event-type doorbell --location "Front door" --urgency high --output doorbell.mp3
```

The command constructs text such as “Urgent alert: doorbell detected at Front door” and sends it through the audio generator.

### Batch text input

Create `texts.json` containing either a JSON array:

```json
[
  "Doorbell at the front door",
  "Motion detected near the garage"
]
```

or an object with a `texts` array:

```json
{
  "texts": [
    "Doorbell at the front door",
    "Motion detected near the garage"
  ]
}
```

Then run:

```powershell
& .\.venv\Scripts\python.exe src\cli.py batch --input-file .\texts.json --output-dir .\audio_output\alerts
```

Batch items must be strings. Object items with per-event `voice` or `rate` fields are not supported. Files are named `audio_000.mp3`, `audio_001.mp3`, and so on.

## Python API

`AccessibleAudio.generate_audio` returns a tuple of `(audio_bytes, metadata)`. Relative output paths are resolved under this project's `audio_output/`; an absolute path is preserved.

```python
from src.audio import AccessibleAudio, AudioConfig

audio = AccessibleAudio()  # Reads ELEVENLABS_API_KEY from the environment/.env.
config = AudioConfig(
    voice_id="your-account-enabled-voice-id",
    model="your-account-enabled-model-id",
)
audio_bytes, metadata = audio.generate_audio(
    "A person is at your front door.",
    config=config,
    output_file="front-door.mp3",
)

print(f"Saved to: {metadata.file_path}")
print(f"Bytes: {len(audio_bytes or b'')}")
print(f"Fallback used: {metadata.used_fallback}")
```

Choose IDs that your ElevenLabs account is permitted to use. If the primary request fails specifically with HTTP 402 `paid_plan_required`, the implementation retries using `fallback_voice_id` and `fallback_model` from `AudioConfig`. Other errors are raised; fallback is not a general retry mechanism.

`AudioConfig.voice` is a descriptive enum stored in metadata; the API request uses `voice_id`. Similarly, `rate`, `stability`, and `similarity_boost` are currently stored but are not passed as synthesis settings in the SDK calls. Do not rely on these fields to change generated speech until the implementation wires them to supported API parameters.

### Generate an event description from Python

```python
from src.audio import EventToSpeech

audio_bytes, metadata = EventToSpeech().describe_event(
    event_type="motion",
    location="Back door",
    urgency="high",
    output_file="motion-alert.mp3",
)
print(metadata.file_path)
```

`describe_event` returns the same `(audio_bytes, metadata)` tuple as `generate_audio`.

### Batch generation from Python

```python
from src.audio import AccessibleAudio

audio = AccessibleAudio()
results = audio.batch_generate(
    ["Doorbell at the front door", "Motion at the garage"],
    output_dir="audio_output/batch",
)
for path, metadata in results:
    print(path, metadata.character_count)
```

Each result is a `(path_or_none, metadata)` tuple. Failed items are reported to standard output and have a `None` path; the method continues processing subsequent items.

## Optional event-validator demo

The example integrates with the sibling `event-schema-validator` checkout. Keep both project folders next to each other, set up the voice project's `.env`, and run from the voice project root:

```powershell
& .\.venv\Scripts\python.exe examples\event_validator_audio_demo.py
```

It validates a sample Ring event, builds a spoken alert from the normalized result, and writes `audio_output/event_validator_demo.mp3`. The demo makes a real ElevenLabs request and may consume account quota.

### Optional Backboard comparison

Backboard is not part of the voice CLI or this event-validator demo. The demo uses the sibling validator's local `SchemaValidator`; it needs an ElevenLabs key, but no Backboard key. To compare an event remotely, configure and call `BackboardClient` from the `event-schema-validator` project first, following its [standalone Backboard guide](https://github.com/abdelrazekrizk/event-schema-validator/blob/main/docs/BACKBOARD.md). That separate helper sends event data to Backboard; it does not provide TTS input automatically. After reviewing the event, pass suitable narration text to this project's `AccessibleAudio` or `EventToSpeech` API. Only send data to Backboard if it is appropriate to share.
