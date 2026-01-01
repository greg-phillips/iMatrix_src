#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyttsx3",
# ]
# ///
"""
pyttsx3 TTS Script for iMatrix_Client

Uses pyttsx3 for offline text-to-speech synthesis.
Accepts optional text prompt as command-line argument.

Usage:
    uv run pyttsx3_tts.py                    # Uses default text
    uv run pyttsx3_tts.py "Your custom text" # Uses provided text

Features:
    - Offline TTS (no API key required)
    - Cross-platform compatibility
    - Configurable voice settings
    - Immediate audio playback
"""

import sys
import random


def main():
    """Main entry point for pyttsx3 TTS."""
    try:
        import pyttsx3

        # Initialize TTS engine
        engine = pyttsx3.init()

        # Configure engine settings
        engine.setProperty('rate', 180)    # Speech rate (words per minute)
        engine.setProperty('volume', 0.8)  # Volume (0.0 to 1.0)

        # Get text from command line argument or use default
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])
        else:
            # Default completion messages
            completion_messages = [
                "Work complete!",
                "All done!",
                "Task finished!",
                "Job complete!",
                "Ready for next task!"
            ]
            text = random.choice(completion_messages)

        # Speak the text
        engine.say(text)
        engine.runAndWait()

    except ImportError:
        print("Error: pyttsx3 package not installed", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
