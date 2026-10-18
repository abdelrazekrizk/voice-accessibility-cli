# API and service requirements

This page describes which parts of the project need external services and credentials.

## Automated tests

- **External API:** None.
- **Credentials:** None.
- **Network access:** None required by the test suite.
- **Why:** The tests mock the ElevenLabs SDK and do not generate live audio.

Install the dependencies listed in `requirements.txt` and run the commands in [Setup](SETUP.md).

## Real text-to-speech generation

- **External service:** ElevenLabs, called through the SDK in `src/audio.py`.
- **Credential:** `ELEVENLABS_API_KEY`, supplied through the environment or a private project-root `.env` file.
- **Network access:** Required to request and receive generated audio.
- **Account access and cost:** Availability of voices, models, quotas, and pricing depends on the user's current account and provider terms. Check those terms before sending requests; do not rely on a fixed free-tier quota.

See [Setup](SETUP.md) for credential configuration and [Usage](USAGE.md) for CLI and Python examples. Real requests can consume quota or incur charges.

## Backboard

This project does not call Backboard and does not need `BACKBOARD_API_KEY`. The optional Backboard helper belongs to the sibling `event-schema-validator` project; see its [Backboard guide](https://github.com/abdelrazekrizk/event-schema-validator/blob/main/docs/BACKBOARD.md). The event-validator audio demo uses that project's local `SchemaValidator`, then sends narration text to ElevenLabs; it does not call Backboard.

## Data and key safety

Text submitted for real generation is sent to ElevenLabs. Avoid sending sensitive event descriptions unless permitted by your organization's policies and your provider's terms. Keep `.env` and API keys out of source control, shell history, logs, issues, and commits. The project `.gitignore` excludes `.env`.
