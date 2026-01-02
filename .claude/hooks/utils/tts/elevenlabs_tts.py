#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "elevenlabs",
#     "python-dotenv",
# ]
# ///
"""
ElevenLabs TTS Script for iMatrix_Client

Uses ElevenLabs' Turbo v2.5 model for fast, high-quality text-to-speech.
Accepts optional text prompt as command-line argument.

Usage:
    uv run elevenlabs_tts.py                    # Uses default text
    uv run elevenlabs_tts.py "Your custom text" # Uses provided text

Features:
    - Fast generation (optimized for real-time use)
    - High-quality voice synthesis
    - Stable production model
    - WSL compatible (uses paplay)
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv


def play_audio_wsl(audio_data):
    """Play audio using paplay (works in WSL with WSLg)."""
    mp3_path = None
    wav_path = None
    try:
        # Write MP3 to temp file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            for chunk in audio_data:
                f.write(chunk)
            mp3_path = f.name

        # Convert MP3 to WAV using sox
        wav_path = mp3_path.replace('.mp3', '.wav')
        result = subprocess.run(
            ['sox', mp3_path, wav_path],
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            return

        # Play WAV with paplay (works with WSLg PulseAudio)
        subprocess.run(
            ['paplay', wav_path],
            capture_output=True,
            timeout=30
        )
    finally:
        if mp3_path and os.path.exists(mp3_path):
            os.unlink(mp3_path)
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)


def main():
    """Main entry point for ElevenLabs TTS."""
    # Load environment variables
    load_dotenv()

    # Get API key from environment
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not found in environment variables", file=sys.stderr)
        sys.exit(1)

    try:
        from elevenlabs.client import ElevenLabs

        # Initialize client
        elevenlabs = ElevenLabs(api_key=api_key)

        # Get text from command line argument or use default
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])
        else:
            text = "The first move is what sets everything in motion."

        try:
            # Generate audio
            # Using "Rachel" - a default ElevenLabs voice
            audio = elevenlabs.text_to_speech.convert(
                text=text,
                voice_id="21m00Tcm4TlvDq8ikWAM",
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128",
            )

            # Play using WSL-compatible method
            play_audio_wsl(audio)

        except Exception as e:
            print(f"Error generating audio: {e}", file=sys.stderr)
            sys.exit(1)

    except ImportError:
        print("Error: elevenlabs package not installed", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
