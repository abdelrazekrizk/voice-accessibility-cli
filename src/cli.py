# Voice Accessibility CLI - CLI Interface

"""
Command-line interface for Voice Accessibility CLI
"""

import click
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from audio import AccessibleAudio, AudioConfig, EventToSpeech, Voice, SpeechRate


@click.group()
def cli():
    """Voice Accessibility CLI - Generate accessible audio from text"""
    pass


@cli.command()
@click.option("--text", type=str, required=True, help="Text to convert to audio")
@click.option("--output", type=str, default=None, help="Output MP3 file path")
@click.option("--voice", type=click.Choice([v.value for v in Voice]), default="Bella")
@click.option("--rate", type=click.Choice(["0.75", "1.0", "1.25"]), default="1.0")
@click.option("--stability", type=float, default=0.5, help="Voice stability (0-1)")
@click.option("--similarity", type=float, default=0.75, help="Similarity boost (0-1)")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def generate(
    text: str,
    output: Optional[str],
    voice: str,
    rate: str,
    stability: float,
    similarity: float,
    verbose: bool
):
    """Generate audio from text"""
    try:
        # Validate text
        audio_gen = AccessibleAudio()
        is_valid, warnings = audio_gen.validate_text(text)

        if not is_valid:
            click.echo(click.style("✗ Invalid text", fg="red"))
            return

        if warnings and verbose:
            click.echo(click.style("Warnings:", fg="yellow"))
            for warning in warnings:
                click.echo(f"  - {warning}")

        # Create config
        config = AudioConfig(
            voice=Voice[voice.upper() if voice != "Bella" else "BELLA"],
            rate=SpeechRate(rate),
            stability=stability,
            similarity_boost=similarity
        )

        click.echo(click.style(f"Generating audio...", fg="cyan"))

        # Generate audio
        audio_bytes, metadata = audio_gen.generate_audio(text, config, output)

        if output:
            click.echo(
                click.style(
                    f"✓ Audio generated: {metadata.file_path}",
                    fg="green",
                    bold=True,
                )
            )
            click.echo(f"  Size: {metadata.file_size_bytes / 1024:.1f} KB")
            click.echo(f"  Duration: ~{metadata.duration_seconds:.1f}s")
        else:
            click.echo(click.style("✓ Audio generated (not saved)", fg="green"))

        if verbose:
            click.echo(f"  Characters: {metadata.character_count}")
            click.echo(f"  Voice: {config.voice.value}")
            click.echo(f"  Rate: {rate}x")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg="red"))


@cli.command()
@click.option("--input-file", type=str, required=True, help="JSON file with texts")
@click.option("--output-dir", type=str, default="./audio_output", help="Output directory")
@click.option("--voice", type=click.Choice([v.value for v in Voice]), default="Bella")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def batch(input_file: str, output_dir: str, voice: str, verbose: bool):
    """Generate audio for multiple texts from JSON file"""
    try:
        if not os.path.exists(input_file):
            click.echo(click.style(f"✗ File not found: {input_file}", fg="red"))
            return

        with open(input_file) as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            texts = data
        elif isinstance(data, dict) and "texts" in data:
            texts = data["texts"]
        else:
            click.echo(click.style("✗ Invalid JSON format", fg="red"))
            return

        audio_gen = AccessibleAudio()
        config = AudioConfig(voice=Voice[voice.upper() if voice != "Bella" else "BELLA"])

        click.echo(f"Generating audio for {len(texts)} texts...")

        results = audio_gen.batch_generate(texts, config, output_dir)

        successful = sum(1 for path, _ in results if path)
        failed = len(results) - successful

        click.echo(click.style(f"✓ Complete", fg="green", bold=True))
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Output directory: {output_dir}")

        if verbose:
            for i, (path, metadata) in enumerate(results, 1):
                status = "✓" if path else "✗"
                click.echo(f"  {i}. {status} {metadata.text[:40]}...")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg="red"))


@cli.command()
def list_voices():
    """List available voices"""
    audio_gen = AccessibleAudio()
    voices = audio_gen.get_available_voices()

    click.echo("Available Voices:")
    for i, voice in enumerate(voices, 1):
        click.echo(f"  {i}. {voice}")


@cli.command()
@click.option("--event-type", type=str, required=True, help="Type of event (doorbell, motion, etc.)")
@click.option("--location", type=str, required=True, help="Location of event")
@click.option("--urgency", type=click.Choice(["low", "medium", "high"]), default="medium")
@click.option("--output", type=str, default=None, help="Output MP3 file path")
def event(event_type: str, location: str, urgency: str, output: Optional[str]):
    """Generate audio description for a smart home event"""
    try:
        event_to_speech = EventToSpeech()
        audio_bytes, metadata = event_to_speech.describe_event(
            event_type=event_type,
            location=location,
            urgency=urgency,
            output_file=output
        )

        if output:
            click.echo(click.style(f"✓ Event audio generated: {output}", fg="green", bold=True))
            click.echo(f"  Event: {event_type} at {location}")
            click.echo(f"  Urgency: {urgency}")
        else:
            click.echo(click.style("✓ Event audio generated", fg="green"))

    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg="red"))


@cli.command()
def version():
    """Show version information"""
    click.echo("Voice Accessibility CLI v1.0.0")
    click.echo("Built for Hacktoberfest 2026")
    click.echo("Best Use of ElevenLabs Category")


if __name__ == "__main__":
    cli()
