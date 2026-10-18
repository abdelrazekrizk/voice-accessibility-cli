# Voice Accessibility CLI

A Python command-line tool and API that turns short text or smart-home event descriptions into MP3 speech using the ElevenLabs cloud text-to-speech service. Audio is generated remotely; this project does not include an offline speech model.

- **Repository:** [github.com/abdelrazekrizk/voice-accessibility-cli](https://github.com/abdelrazekrizk/voice-accessibility-cli)
- **License:** [MIT](LICENSE)

## What it does

Use the `generate` command to submit text to ElevenLabs, `event` to compose a spoken event alert, or `batch` to generate files for a list of text strings. The Python API returns audio bytes and metadata, and can optionally save the audio under `audio_output/`.

An ElevenLabs API key and network access are required for real generation. API usage may incur charges or be subject to account and voice restrictions. Unit tests mock the SDK and do not make requests.

Backboard belongs to the optional event-comparison helper in the sibling [Event Schema Validator project](https://github.com/abdelrazekrizk/event-schema-validator); it is not required by this CLI. The included event-validator demo uses that project's local `SchemaValidator`, then calls ElevenLabs—it does not call Backboard. For the Backboard helper's purpose and direct usage, see the validator project's [Backboard guide](https://github.com/abdelrazekrizk/event-schema-validator/blob/main/docs/BACKBOARD.md).

## Features

- Text-to-speech generation through the ElevenLabs SDK.
- Single-text, event-description, and batch workflows.
- Audio metadata including character count, selected voice/model IDs, and output file details.
- Configurable primary and fallback voice/model IDs through the Python `AudioConfig`.
- Optional fallback for the specific HTTP 402 `paid_plan_required` response.

**Current CLI limitations:** `--voice`, `--rate`, `--stability`, and `--similarity` are accepted and stored in configuration, but the current SDK calls do not use those values as synthesis settings. `--voice` does not select the provider voice ID; set `AudioConfig.voice_id` through the Python API to choose that ID. The CLI does not currently expose a voice-ID option. `list-voices` returns the built-in list rather than querying the account.

## Project structure

```text
voice-accessibility-cli/
├── .env.example                  # Environment-variable placeholders
├── .gitattributes
├── .gitignore                    # Excludes secrets, virtualenvs, and generated audio
├── LICENSE
├── README.md
├── requirements.txt              # Runtime and test dependencies
├── audio_output/                 # Generated audio destination
├── docs/
│   ├── API_REQUIREMENTS.md        # Current API and credential requirements
│   ├── SETUP.md                   # Installation and credentials
│   └── USAGE.md                   # CLI, Python, batch, and demo examples
├── examples/
│   └── event_validator_audio_demo.py  # Optional sibling-project integration
├── src/
│   ├── __init__.py
│   ├── audio.py                   # TTS API, configuration, and metadata
│   └── cli.py                     # Click command-line interface
└── tests/
    ├── __init__.py
    └── test_audio.py              # Mocked audio/configuration tests
```

Generated audio, `.env`, `.venv/`, and test caches are local files and should not be committed. The internal `.dev/` material is intentionally excluded from the public project commit.

## Requirements and installation

Use Python 3.10 or later. From the project root in PowerShell:

```powershell
if (-not (Test-Path .\.venv\Scripts\python.exe)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` and set `ELEVENLABS_API_KEY` to a key for your account. Keep the file private; it is ignored by Git. See [Setup](docs/SETUP.md) for credential safety and account cautions.

## Quick start

From the project root, generate a spoken alert and save it:

```powershell
& .\.venv\Scripts\python.exe src\cli.py generate --text "Doorbell rang at the front door" --output doorbell.mp3
```

Relative output paths are written under `audio_output/`, so the generated file is `audio_output/doorbell.mp3`. Other commands:

```powershell
& .\.venv\Scripts\python.exe src\cli.py --help
& .\.venv\Scripts\python.exe src\cli.py event --event-type motion --location "Back door" --urgency high --output motion.mp3
& .\.venv\Scripts\python.exe src\cli.py batch --input-file .\texts.json --output-dir .\audio_output\batch
```

Batch JSON is a list of strings or an object containing a `texts` list. See [Usage examples](docs/USAGE.md) for exact formats and the Python API.

## Documentation

- [Setup](docs/SETUP.md) — install, configure the API key, understand billing/access limitations, and run tests.
- [Usage examples](docs/USAGE.md) — CLI commands, Python API, batch input, and optional event-validator demo.

## Tests

Run the suite from the project root with the local virtual environment:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/ -v
```

The tests mock ElevenLabs calls; passing tests do not verify API credentials, account access, network availability, or generated audio quality.
