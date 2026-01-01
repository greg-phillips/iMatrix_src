#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///
"""
User Prompt Submit Hook for iMatrix_Client
Logs user prompts and manages session data.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def log_user_prompt(session_id, input_data):
    """Log user prompt to logs directory."""
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'user_prompt_submit.json'

    if log_file.exists():
        with open(log_file, 'r') as f:
            try:
                log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = []
    else:
        log_data = []

    log_data.append(input_data)

    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)


def manage_session_data(session_id, prompt, name_agent=False):
    """Manage session data in the JSON structure."""
    import subprocess

    sessions_dir = Path(".claude/data/sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)

    session_file = sessions_dir / f"{session_id}.json"

    if session_file.exists():
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            session_data = {"session_id": session_id, "prompts": []}
    else:
        session_data = {"session_id": session_id, "prompts": []}

    session_data["prompts"].append(prompt)

    # Generate agent name if requested and not already present
    if name_agent and "agent_name" not in session_data:
        try:
            result = subprocess.run(
                ["uv", "run", ".claude/hooks/utils/llm/anth.py", "--agent-name"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                agent_name = result.stdout.strip()
                if len(agent_name.split()) == 1 and agent_name.isalnum():
                    session_data["agent_name"] = agent_name
        except Exception:
            pass

    try:
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
    except Exception:
        pass


def validate_prompt(prompt):
    """
    Validate the user prompt for security or policy violations.
    Returns tuple (is_valid, reason).
    """
    blocked_patterns = [
        # Add any patterns you want to block
    ]

    prompt_lower = prompt.lower()

    for pattern, reason in blocked_patterns:
        if pattern.lower() in prompt_lower:
            return False, reason

    return True, None


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--validate', action='store_true',
                          help='Enable prompt validation')
        parser.add_argument('--log-only', action='store_true',
                          help='Only log prompts, no validation or blocking')
        parser.add_argument('--store-last-prompt', action='store_true',
                          help='Store the last prompt for status line display')
        parser.add_argument('--name-agent', action='store_true',
                          help='Generate an agent name for the session')
        args = parser.parse_args()

        input_data = json.loads(sys.stdin.read())

        session_id = input_data.get('session_id', 'unknown')
        prompt = input_data.get('prompt', '')

        log_user_prompt(session_id, input_data)

        if args.store_last_prompt or args.name_agent:
            manage_session_data(session_id, prompt, name_agent=args.name_agent)

        if args.validate and not args.log_only:
            is_valid, reason = validate_prompt(prompt)
            if not is_valid:
                print(f"Prompt blocked: {reason}", file=sys.stderr)
                sys.exit(2)

        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == '__main__':
    main()
