#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "openai",
#     "openai[voice_helpers]",
#     "python-dotenv",
# ]
# ///
"""
OpenAI TTS Script for iMatrix_Client

Uses OpenAI's latest TTS model for high-quality text-to-speech.
Accepts optional text prompt as command-line argument.

Usage:
    uv run openai_tts.py                    # Uses default text
    uv run openai_tts.py "Your custom text" # Uses provided text

Features:
    - OpenAI gpt-4o-mini-tts model (latest)
    - Nova voice (engaging and warm)
    - Streaming audio with instructions support
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv


async def main():
    """Main entry point for OpenAI TTS."""
    # Load environment variables
    load_dotenv()

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables", file=sys.stderr)
        sys.exit(1)

    try:
        from openai import AsyncOpenAI
        from openai.helpers import LocalAudioPlayer

        # Initialize OpenAI client
        openai = AsyncOpenAI(api_key=api_key)

        # Get text from command line argument or use default
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])
        else:
            text = "Today is a wonderful day to build something people love!"

        try:
            # Generate and stream audio using OpenAI TTS
            async with openai.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="nova",
                input=text,
                instructions="Speak in a cheerful, positive yet professional tone.",
                response_format="mp3",
            ) as response:
                await LocalAudioPlayer().play(response)

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
    asyncio.run(main())
