# Claude Code Hooks Implementation Guide

**Date**: 2026-01-01
**Document Version**: 1.1
**Status**: Active
**Author**: Claude Code
**Last Updated**: 2026-01-01

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Hook Types](#hook-types)
5. [TTS System](#tts-system)
6. [LLM Integration](#llm-integration)
7. [Security Features](#security-features)
8. [Configuration](#configuration)
9. [Logging](#logging)
10. [Troubleshooting](#troubleshooting)
11. [Extending the System](#extending-the-system)

---

## Overview

The Claude Code hooks system provides an extensible framework for automating actions during Claude Code sessions. It enables:

- **Audio Feedback**: Text-to-speech notifications when Claude needs input or completes tasks
- **Security Controls**: Pre-execution validation to block dangerous commands
- **Comprehensive Logging**: Audit trail of all tool usage and events
- **Session Management**: Context loading and transcript backup

### Key Benefits

| Feature | Description |
|---------|-------------|
| TTS Notifications | Spoken alerts so you don't need to watch the terminal |
| Security Blocking | Prevents accidental destructive operations |
| Event Logging | Debug and audit all Claude Code activity |
| Graceful Fallbacks | System continues working even if API keys unavailable |

---

## Architecture

### Directory Structure

```
.claude/
├── hooks/
│   ├── pre_tool_use.py       # Security validation (runs BEFORE every tool)
│   ├── post_tool_use.py      # Logging (runs AFTER every tool)
│   ├── notification.py       # TTS when Claude needs input
│   ├── stop.py               # TTS when task completes
│   ├── subagent_stop.py      # TTS when subagent completes
│   ├── user_prompt_submit.py # Logs user prompts
│   ├── session_start.py      # Loads context at session start
│   ├── pre_compact.py        # Backs up transcript before compaction
│   └── utils/
│       ├── tts/
│       │   ├── elevenlabs_tts.py  # ElevenLabs Turbo v2.5 (highest quality)
│       │   ├── openai_tts.py      # OpenAI gpt-4o-mini-tts
│       │   └── pyttsx3_tts.py     # Local offline fallback
│       └── llm/
│           ├── anth.py            # Anthropic Claude 3.5 Haiku
│           ├── oai.py             # OpenAI GPT-4o-mini
│           └── ollama.py          # Local Ollama (llama3.2)
├── data/
│   └── sessions/                  # Session data storage
├── settings.json                  # Hooks configuration
└── settings.local.json            # Permission rules

.env.sample                        # Environment variable template
.env                               # Your API keys (not committed to git)
logs/                              # Hook event logs
```

### Data Flow

```
┌─────────────────┐
│   Claude Code   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  PreToolUse     │────►│ Security Check   │
│  Hook           │     │ (blocks if bad)  │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│   Tool Runs     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  PostToolUse    │────►│ Logging          │
│  Hook           │     │                  │
└─────────────────┘     └──────────────────┘
```

---

## Quick Start

### 1. Create Environment File

```bash
cd /home/greg/iMatrix/iMatrix_Client
cp .env.sample .env
```

### 2. Add Your API Keys

Edit `.env` and add at least one API key:

```bash
# For TTS (pick one or more):
ELEVENLABS_API_KEY=your_key_here   # Best quality
OPENAI_API_KEY=your_key_here       # Good quality

# For LLM completion messages:
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here       # Same key works for both

# Personalization:
ENGINEER_NAME=YourName
```

### 3. Install UV (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 4. Install WSL Audio Dependencies (WSL only)

```bash
sudo apt install sox libsox-fmt-mp3 pulseaudio-utils
```

### 5. Restart Claude Code

The hooks activate automatically when Claude Code starts.

### 6. Test TTS (Optional)

```bash
cd /home/greg/iMatrix/iMatrix_Client
uv run .claude/hooks/utils/tts/elevenlabs_tts.py "Testing TTS"
```

---

## Hook Types

### PreToolUse

**File**: `pre_tool_use.py`
**When**: Before every tool execution
**Purpose**: Security validation
**Exit Code 2**: Blocks the tool and returns error to Claude

```python
# Example: How blocking works
if is_dangerous_rm_command(command):
    print("BLOCKED: Dangerous rm command detected", file=sys.stderr)
    sys.exit(2)  # Exit code 2 = block tool
```

### PostToolUse

**File**: `post_tool_use.py`
**When**: After every tool execution
**Purpose**: Logging tool results

### Notification

**File**: `notification.py`
**When**: Claude needs user input
**Purpose**: TTS announcement to get your attention

The hook skips the generic "Claude is waiting for your input" message to avoid excessive notifications.

### Stop

**File**: `stop.py`
**When**: Claude finishes responding
**Purpose**: TTS completion announcement

Features:
- Generates dynamic completion messages using LLM
- Falls back to predefined messages if no LLM available
- Optionally copies transcript to `logs/chat.json`

### SubagentStop

**File**: `subagent_stop.py`
**When**: A subagent (Task tool) completes
**Purpose**: TTS notification for background task completion

### UserPromptSubmit

**File**: `user_prompt_submit.py`
**When**: User submits a prompt
**Purpose**: Logging and session tracking

### SessionStart

**File**: `session_start.py`
**When**: Claude Code starts or resumes
**Purpose**: Load development context

Automatically loads:
- Git branch and uncommitted changes
- Recent commits
- Project TODO files
- GitHub issues (if `gh` CLI available)

### PreCompact

**File**: `pre_compact.py`
**When**: Before context compaction
**Purpose**: Backup transcript

Creates backups in `logs/transcript_backups/` with format:
```
{session_name}_pre_compact_{trigger}_{timestamp}.jsonl
```

---

## TTS System

### Provider Priority

The system tries TTS providers in order until one works:

| Priority | Provider | API Key Required | Quality |
|----------|----------|------------------|---------|
| 1 | ElevenLabs Turbo v2.5 | `ELEVENLABS_API_KEY` | Excellent |
| 2 | OpenAI tts-1 | `OPENAI_API_KEY` | Very Good |
| 3 | pyttsx3 (local) | None | Basic |

### How Provider Selection Works

```python
def get_tts_script_path():
    # Check for ElevenLabs API key (highest priority)
    if os.getenv('ELEVENLABS_API_KEY'):
        return "elevenlabs_tts.py"

    # Check for OpenAI API key (second priority)
    if os.getenv('OPENAI_API_KEY'):
        return "openai_tts.py"

    # Fall back to pyttsx3 (no API key required)
    return "pyttsx3_tts.py"
```

### ElevenLabs Configuration

- **Voice ID**: `21m00Tcm4TlvDq8ikWAM` (Rachel - default voice)
- **Model**: `eleven_turbo_v2_5` (fast, production-ready)
- **Output**: MP3 44.1kHz 128kbps

### OpenAI Configuration

- **Model**: `tts-1` (fast)
- **Voice**: `nova` (engaging and warm)
- **Output**: MP3

### WSL Audio Requirements

TTS in WSL requires specific setup because Python audio libraries don't work directly with WSLg:

**Required packages:**
```bash
sudo apt install sox libsox-fmt-mp3 pulseaudio-utils
```

**How it works:**
1. TTS API generates MP3 audio
2. `sox` converts MP3 to WAV format
3. `paplay` plays WAV through WSLg PulseAudio

**Audio pipeline:**
```
API (MP3) → sox (convert) → WAV → paplay → WSLg PulseAudio → Windows Audio
```

### Manual TTS Testing

```bash
# Test ElevenLabs
uv run .claude/hooks/utils/tts/elevenlabs_tts.py "Hello world"

# Test OpenAI
uv run .claude/hooks/utils/tts/openai_tts.py "Hello world"

# Test local (requires espeak-ng: sudo apt install espeak-ng)
uv run .claude/hooks/utils/tts/pyttsx3_tts.py "Hello world"

# Test WSL audio directly (should hear a tone)
sox -n -r 44100 -c 1 /tmp/test.wav synth 1 sine 440 && paplay /tmp/test.wav && rm /tmp/test.wav
```

---

## LLM Integration

### Purpose

LLMs generate dynamic, natural completion messages instead of static text.

### Provider Priority

| Priority | Provider | API Key Required | Model |
|----------|----------|------------------|-------|
| 1 | OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| 2 | Anthropic | `ANTHROPIC_API_KEY` | claude-3-5-haiku |
| 3 | Ollama (local) | None | llama3.2 |

### Features

**Completion Messages** (`--completion`):
```bash
uv run .claude/hooks/utils/llm/anth.py --completion
# Output: "All set and ready for your next task!"
```

**Agent Names** (`--agent-name`):
```bash
uv run .claude/hooks/utils/llm/anth.py --agent-name
# Output: "Phoenix"
```

### Personalization

Set `ENGINEER_NAME` in `.env` for personalized messages:
```
ENGINEER_NAME=Greg
```

This gives a 30% chance of including your name:
- "Greg, all done!"
- "Ready for you, Greg!"

---

## Security Features

### Blocked Patterns

The `pre_tool_use.py` hook blocks these dangerous operations:

| Pattern | Description | Example |
|---------|-------------|---------|
| `rm -rf` variants | Recursive force delete | `rm -rf /`, `rm -Rf ~` |
| `sudo rm` | Privileged delete | `sudo rm /etc/passwd` |
| `chmod 777` | World-writable permissions | `chmod 777 secret.key` |
| `.env` file access | Environment secrets | `cat .env`, `edit .env` |
| Credential files | Keys and certificates | `*.key`, `*.pem`, `credentials.json` |
| Force push to main | Destructive git ops | `git push --force main` |
| PPP config | Network secrets | `/etc/ppp/peers/*` |

### How Blocking Works

```python
# In pre_tool_use.py
def main():
    input_data = json.load(sys.stdin)
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    if tool_name == 'Bash':
        command = tool_input.get('command', '')

        if is_dangerous_rm_command(command):
            print("BLOCKED: Dangerous rm command", file=sys.stderr)
            sys.exit(2)  # Exit 2 = block and return error to Claude

    sys.exit(0)  # Exit 0 = allow tool to proceed
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Allow tool execution |
| 1 | Error (tool still runs) |
| 2 | Block tool and return error to Claude |

### Adding Custom Security Rules

Edit `pre_tool_use.py` to add project-specific rules:

```python
def is_imatrix_dangerous_command(command):
    # Add your custom rules here
    if 'my_sensitive_file' in command:
        return True, "Access to my_sensitive_file is blocked"
    return False, None
```

---

## Configuration

### settings.json

The hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [{
          "type": "command",
          "command": "sh -c 'cd /home/greg/iMatrix/iMatrix_Client && uv run .claude/hooks/pre_tool_use.py'"
        }]
      }
    ],
    "PostToolUse": [...],
    "Notification": [...],
    "Stop": [...],
    "SubagentStop": [...],
    "UserPromptSubmit": [...],
    "PreCompact": [...],
    "SessionStart": [...]
  }
}
```

### Hook Command Structure

Each hook entry has:
- `matcher`: Regex to match (empty = match all)
- `hooks`: Array of hook definitions
  - `type`: Currently only "command" supported
  - `command`: Shell command to execute

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ELEVENLABS_API_KEY` | ElevenLabs TTS API key | No |
| `OPENAI_API_KEY` | OpenAI API key (TTS + LLM) | No |
| `ANTHROPIC_API_KEY` | Anthropic API key (LLM) | No |
| `ENGINEER_NAME` | Your name for personalized TTS | No |
| `OLLAMA_MODEL` | Override Ollama model (default: llama3.2) | No |

---

## Logging

### Log Files

All hooks log to the `logs/` directory:

| File | Contents |
|------|----------|
| `pre_tool_use.json` | All tool invocations (before execution) |
| `post_tool_use.json` | Tool results (after execution) |
| `notification.json` | Notification events |
| `stop.json` | Session stop events |
| `session_start.json` | Session start/resume events |
| `pre_compact.json` | Compaction events |
| `chat.json` | Full transcript (if `--chat` flag used) |
| `transcript_backups/` | Pre-compaction transcript backups |

### Log Format

Each log file contains a JSON array of events:

```json
[
  {
    "tool_name": "Bash",
    "tool_input": {
      "command": "ls -la"
    },
    "timestamp": "2026-01-01T15:30:00Z"
  },
  ...
]
```

### Viewing Logs

```bash
# View recent tool usage
cat logs/pre_tool_use.json | jq '.[-5:]'

# View session starts
cat logs/session_start.json | jq '.'

# Search for blocked operations
grep -i "blocked" logs/pre_tool_use.json
```

---

## Troubleshooting

### Hooks Not Running

1. **Check settings.json exists**:
   ```bash
   ls -la .claude/settings.json
   ```

2. **Verify UV is installed**:
   ```bash
   uv --version
   ```

3. **Test hook manually**:
   ```bash
   echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | \
     uv run .claude/hooks/pre_tool_use.py
   ```

### TTS Not Working

1. **Check API key is set**:
   ```bash
   grep ELEVENLABS_API_KEY .env
   ```

2. **Test TTS script directly**:
   ```bash
   uv run .claude/hooks/utils/tts/elevenlabs_tts.py "Test"
   ```

3. **Check for audio device issues**:
   ```bash
   # Linux
   aplay -l

   # WSL - ensure PulseAudio is running
   pactl info
   ```

### TTS Not Working in WSL

1. **Install required packages**:
   ```bash
   sudo apt install sox libsox-fmt-mp3 pulseaudio-utils
   ```

2. **Test WSL audio directly**:
   ```bash
   sox -n -r 44100 -c 1 /tmp/test.wav synth 1 sine 440 && paplay /tmp/test.wav
   ```
   If you hear a tone, WSL audio is working.

3. **Check PulseAudio sink status**:
   ```bash
   pactl list sinks short
   ```
   If sink shows "SUSPENDED", it will auto-activate on first play.

4. **Check WSLg is enabled**:
   ```bash
   ls /mnt/wslg/PulseServer
   ```
   If file doesn't exist, WSLg may not be enabled in your WSL installation.

5. **Verify sox can read MP3**:
   ```bash
   apt list --installed | grep libsox-fmt
   ```
   You need `libsox-fmt-mp3` or `libsox-fmt-all` installed.

### Hook Errors Breaking Claude Code

Hooks are designed to fail gracefully:
- All exceptions are caught and return `sys.exit(0)`
- Only explicit `sys.exit(2)` blocks tools
- Log files capture errors for debugging

If hooks cause issues, temporarily disable by renaming:
```bash
mv .claude/settings.json .claude/settings.json.bak
```

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "Failed to spawn hook" | UV not found or script missing | Install UV, check file exists |
| "ELEVENLABS_API_KEY not found" | Missing API key | Add to .env file |
| "Error calling Anthropic API" | Invalid API key or network | Check key, test connectivity |
| "voice_not_found" | Invalid ElevenLabs voice ID | Use valid voice ID (default: `21m00Tcm4TlvDq8ikWAM`) |
| "Stream error: Timeout" | PulseAudio sink suspended | Audio will auto-activate on retry |
| "Error querying device -1" | Python audio lib in WSL | Scripts use sox+paplay instead |
| "symbol lookup error: libpango" | ffplay library conflict in WSL | Scripts use sox+paplay instead |
| "espeak not installed" | pyttsx3 missing dependency | `sudo apt install espeak-ng` |

---

## Extending the System

### Adding a New TTS Provider

1. Create `utils/tts/your_provider_tts.py`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["your-sdk", "python-dotenv"]
# ///

import os
import sys
from dotenv import load_dotenv

def main():
    load_dotenv()
    api_key = os.getenv('YOUR_API_KEY')
    if not api_key:
        sys.exit(1)

    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello"

    # Your TTS implementation here
    # ...

if __name__ == "__main__":
    main()
```

2. Update `get_tts_script_path()` in hooks that use TTS.

### Adding a New LLM Provider

1. Create `utils/llm/your_provider.py` with these functions:
   - `prompt_llm(prompt_text)` - General prompting
   - `generate_completion_message()` - Task completion messages
   - `generate_agent_name()` - Session naming

2. Update `get_llm_completion_message()` in `stop.py`.

### Adding a New Hook

1. Create hook script in `.claude/hooks/`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["python-dotenv"]
# ///

import json
import sys

def main():
    try:
        input_data = json.load(sys.stdin)
        # Your hook logic here
        sys.exit(0)
    except Exception:
        sys.exit(0)  # Fail gracefully

if __name__ == '__main__':
    main()
```

2. Add to `.claude/settings.json`:

```json
"YourHookEvent": [
  {
    "matcher": "",
    "hooks": [{
      "type": "command",
      "command": "uv run .claude/hooks/your_hook.py"
    }]
  }
]
```

### Input Data by Hook Type

| Hook | Key Fields |
|------|------------|
| PreToolUse | `tool_name`, `tool_input` |
| PostToolUse | `tool_name`, `tool_input`, `tool_result` |
| Notification | `message` |
| Stop | `session_id`, `transcript_path`, `stop_hook_active` |
| SubagentStop | `session_id`, `agent_id` |
| UserPromptSubmit | `prompt`, `session_id` |
| SessionStart | `session_id`, `source` ("startup", "resume", "clear") |
| PreCompact | `session_id`, `transcript_path`, `trigger`, `custom_instructions` |

---

## Summary

The hooks system provides a powerful way to customize Claude Code behavior:

1. **Security**: Block dangerous commands before they run
2. **Feedback**: TTS notifications keep you informed
3. **Logging**: Full audit trail of all activity
4. **Context**: Automatic project context loading

Start with basic setup (just `.env` with one API key) and expand as needed.

---

*Document Last Updated: 2026-01-01 (v1.1 - Added WSL audio fixes)*
