#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "openai",
#     "python-dotenv",
# ]
# ///
"""
OpenAI TTS Script for iMatrix_Client

Uses OpenAI's TTS model for high-quality text-to-speech.
Accepts optional text prompt as command-line argument.

Usage:
    uv run openai_tts.py                    # Uses default text
    uv run openai_tts.py "Your custom text" # Uses provided text

Features:
    - OpenAI tts-1 model (fast)
    - Nova voice (engaging and warm)
    - WSL compatible (uses paplay)
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv


def play_audio_wsl(audio_path):
    """Play audio using paplay (works in WSL with WSLg)."""
    wav_path = None
    try:
        # Convert MP3 to WAV using sox
        wav_path = audio_path.replace('.mp3', '.wav')
        result = subprocess.run(
            ['sox', audio_path, wav_path],
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
    except Exception:
        pass
    finally:
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)


def main():
    """Main entry point for OpenAI TTS."""
    # Load environment variables
    load_dotenv()

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables", file=sys.stderr)
        sys.exit(1)

    try:
        from openai import OpenAI

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        # Get text from command line argument or use default
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])
        else:
            text = "Today is a wonderful day to build something people love!"

        try:
            # Generate audio using OpenAI TTS
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text,
                response_format="mp3",
            )

            # Save to temp file and play
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(response.content)
                temp_path = f.name

            try:
                play_audio_wsl(temp_path)
            finally:
                os.unlink(temp_path)

        except Exception as e:
            print(f"Error generating audio: {e}", file=sys.stderr)
            sys.exit(1)

    except ImportError as e:
        print("Error: Required package not installed", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
