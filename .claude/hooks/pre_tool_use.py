#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///
"""
Pre-Tool-Use Hook for iMatrix_Client
Validates and blocks dangerous operations before they execute.
Exit code 2 blocks the tool and feeds error back to Claude.
"""

import json
import sys
import re
from pathlib import Path


def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    """
    normalized = ' '.join(command.lower().split())

    # Pattern 1: Standard rm -rf variations
    patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf, rm -fr, rm -Rf, etc.
        r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
        r'\brm\s+--recursive\s+--force',
        r'\brm\s+--force\s+--recursive',
        r'\brm\s+-r\s+.*-f',
        r'\brm\s+-f\s+.*-r',
    ]

    for pattern in patterns:
        if re.search(pattern, normalized):
            return True

    # Pattern 2: Check for rm with recursive flag targeting dangerous paths
    dangerous_paths = [
        r'/',
        r'/\*',
        r'~',
        r'~/',
        r'\$HOME',
        r'\.\.',
        r'\*',
        r'\.',
        r'\.\s*$',
    ]

    if re.search(r'\brm\s+.*-[a-z]*r', normalized):
        for path in dangerous_paths:
            if re.search(path, normalized):
                return True

    return False


def is_imatrix_dangerous_command(command):
    """
    iMatrix-specific dangerous command detection.
    Blocks operations that could damage the iMatrix codebase.
    """
    normalized = ' '.join(command.lower().split())

    # Block sudo rm operations
    if re.search(r'\bsudo\s+rm\b', normalized):
        return True, "sudo rm commands are blocked"

    # Block chmod 777 (dangerous permissions)
    if re.search(r'\bchmod\s+777\b', normalized):
        return True, "chmod 777 is blocked - use more restrictive permissions"

    # Block force push to main/master
    if re.search(r'\bgit\s+push\s+.*--force.*\b(main|master)\b', normalized):
        return True, "Force push to main/master is blocked"
    if re.search(r'\bgit\s+push\s+.*\b(main|master)\b.*--force', normalized):
        return True, "Force push to main/master is blocked"

    # Block modifications to PPP config (sensitive)
    if re.search(r'/etc/ppp/peers', normalized):
        return True, "Direct modifications to /etc/ppp/peers are blocked"

    return False, None


def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.
    """
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if '.env' in file_path and not file_path.endswith('.env.sample'):
                return True

        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            env_patterns = [
                r'\b\.env\b(?!\.sample)',
                r'cat\s+.*\.env\b(?!\.sample)',
                r'echo\s+.*>\s*\.env\b(?!\.sample)',
                r'touch\s+.*\.env\b(?!\.sample)',
                r'cp\s+.*\.env\b(?!\.sample)',
                r'mv\s+.*\.env\b(?!\.sample)',
            ]

            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True

    return False


def is_sensitive_file_write(tool_name, tool_input):
    """
    Block writes to sensitive files like credentials and keys.
    """
    if tool_name in ['Edit', 'MultiEdit', 'Write']:
        file_path = tool_input.get('file_path', '').lower()
        sensitive_patterns = [
            'credentials.json',
            '.key',
            '.pem',
            '.p12',
            'id_rsa',
            'id_ed25519',
            '.secret',
        ]

        for pattern in sensitive_patterns:
            if pattern in file_path:
                return True

    return False


def main():
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Check for .env file access
        if is_env_file_access(tool_name, tool_input):
            print("BLOCKED: Access to .env files containing sensitive data is prohibited", file=sys.stderr)
            print("Use .env.sample for template files instead", file=sys.stderr)
            sys.exit(2)

        # Check for sensitive file writes
        if is_sensitive_file_write(tool_name, tool_input):
            print("BLOCKED: Writing to sensitive credential/key files is prohibited", file=sys.stderr)
            sys.exit(2)

        # Check for dangerous commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')

            # Block rm -rf commands
            if is_dangerous_rm_command(command):
                print("BLOCKED: Dangerous rm command detected and prevented", file=sys.stderr)
                sys.exit(2)

            # Block iMatrix-specific dangerous operations
            is_dangerous, reason = is_imatrix_dangerous_command(command)
            if is_dangerous:
                print(f"BLOCKED: {reason}", file=sys.stderr)
                sys.exit(2)

        # Log the tool use
        log_dir = Path.cwd() / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'pre_tool_use.json'

        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        log_data.append(input_data)

        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == '__main__':
    main()
