<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/add_hooks.yaml
Generated on: 2025-12-30
Schema version: 1.0
Complexity level: moderate
Auto-populated sections: project structure, hardware info, development guidelines

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Add Claude Code Hooks Infrastructure to iMatrix_Client

**Date:** 2025-12-30
**Branch:** feature/add-claude-hooks
**Objective:** Implement Claude Code hooks system with TTS feedback and security controls for the iMatrix development workflow

---

## Code Structure

**iMatrix (Core Library):** Contains all core telematics functionality including data logging, communications, and peripheral management for the embedded IoT platform.

**Fleet-Connect-1 (Main Application):** Gateway application for vehicle connectivity, integrating OBD2 protocols, CAN bus processing, and iMatrix cloud platform.

**Additional Context:**
This task adds Claude Code hooks infrastructure to the iMatrix_Client repository.
The hooks will provide:
- Audio TTS feedback when Claude needs input or completes tasks
- Security validation to block dangerous commands
- Logging of all tool usage for audit/debugging
- Session context loading on startup

Reference implementation: /home/greg/agentic_lessons/claude-code-hooks-mastery

---

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH.
The WiFi communications uses a combination Wi-Fi/Bluetooth chipset.
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is **Greg**.

---

## Read and Understand the Following

### Primary Documentation (Read First)

1. `/home/greg/agentic_lessons/claude-code-hooks-mastery/README.md` - Complete hooks mastery guide
2. `/home/greg/agentic_lessons/claude-code-hooks-mastery/.claude/settings.json` - Reference hook configuration
3. `/home/greg/agentic_lessons/claude-code-hooks-mastery/ai_docs/cc_hooks_docs.md` - Official Anthropic hooks documentation

### Source Files to Study

**Hook Scripts** (`/home/greg/agentic_lessons/claude-code-hooks-mastery/.claude/hooks/`):
- `notification.py` - TTS notification when Claude needs input
- `stop.py` - AI-generated completion messages with TTS
- `pre_tool_use.py` - Security blocking of dangerous commands
- `user_prompt_submit.py` - Prompt logging and context injection
- `session_start.py` - Development context loading on startup

**TTS Utilities** (`/home/greg/agentic_lessons/claude-code-hooks-mastery/.claude/hooks/utils/tts/`):
- `elevenlabs_tts.py` - ElevenLabs Turbo v2.5 TTS
- `openai_tts.py` - OpenAI TTS fallback
- `pyttsx3_tts.py` - Local pyttsx3 fallback (no API required)

### Templates

- `/home/greg/agentic_lessons/claude-code-hooks-mastery/.env.sample` - Environment variable template

---

## Guidelines

**Core Principles:**
- Keep hooks lightweight - they run on every tool call
- Fail gracefully - hooks should not break Claude Code if they error
- Use UV single-file scripts for dependency isolation
- Log all events for debugging but don't expose sensitive data
- TTS should be optional - work without API keys configured

**Use the KISS principle - do not over-engineer. Keep it simple and maintainable.**

Always create extensive comments using Doxygen style where applicable.

---

## Task

### Summary

Implement Claude Code hooks with TTS feedback for iMatrix_Client development workflow.

### Description

Create a hooks infrastructure adapted from the claude-code-hooks-mastery lesson.
The hooks will enhance the iMatrix development experience by:

1. Providing audio feedback when Claude needs input (notification hook)
2. Announcing task completion with AI-generated summaries (stop hook)
3. Blocking dangerous commands before execution (pre_tool_use hook)
4. Logging all prompts and tool usage for debugging (all hooks)
5. Loading project context on session start (session_start hook)

### Requirements

1. Create `.claude/hooks/` directory structure in iMatrix_Client
2. Implement all 8 hook types from the reference implementation
3. Set up TTS provider priority: ElevenLabs > OpenAI > pyttsx3
4. Configure hooks in `.claude/settings.json` (merge with existing settings.local.json)
5. Create `.env.sample` with required API keys (ELEVENLABS_API_KEY, OPENAI_API_KEY, ENGINEER_NAME)
6. Adapt security patterns for iMatrix-specific dangerous commands
7. Set up `logs/` directory for hook event logging
8. Use UV single-file script architecture for dependency isolation

### Implementation Notes

- Reference implementation uses `uv run` for script execution - ensure UV is installed
- The hooks use python-dotenv for environment variable loading
- ElevenLabs uses voice_id `WejK3H1m7MI9CHnIjW9K` and turbo_v2_5 model
- Security blocking uses exit code 2 to feed error back to Claude
- PreToolUse hook should block: rm -rf, sudo rm, chmod 777, writes to .env files
- Notification hook has 30% chance to include ENGINEER_NAME for personalization
- Stop hook can generate completion messages using LLM (priority: OpenAI > Anthropic > Ollama)
- Session start hook should load git status and recent issues for context

---

## Detailed Specifications

### Directory Structure

```
.claude/
├── hooks/
│   ├── notification.py
│   ├── stop.py
│   ├── subagent_stop.py
│   ├── pre_tool_use.py
│   ├── post_tool_use.py
│   ├── user_prompt_submit.py
│   ├── pre_compact.py
│   ├── session_start.py
│   └── utils/
│       ├── tts/
│       │   ├── elevenlabs_tts.py
│       │   ├── openai_tts.py
│       │   └── pyttsx3_tts.py
│       └── llm/
│           ├── oai.py
│           ├── anth.py
│           └── ollama.py
├── settings.json (merged config)
└── data/
    └── sessions/
logs/
.env (created from .env.sample, NOT committed)
```

### Hook Configuration (settings.json)

Merge with existing settings.local.json permissions, add:

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/pre_tool_use.py"}]}],
    "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/post_tool_use.py"}]}],
    "Notification": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/notification.py --notify"}]}],
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/stop.py --chat"}]}],
    "SubagentStop": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/subagent_stop.py --notify"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "uv run .claude/hooks/user_prompt_submit.py --log-only --store-last-prompt"}]}],
    "PreCompact": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/pre_compact.py"}]}],
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "uv run .claude/hooks/session_start.py"}]}]
  }
}
```

### iMatrix-Specific Security Patterns

Block these patterns in `pre_tool_use.py`:

- `rm -rf` (especially on iMatrix, Fleet-Connect-1 directories)
- `sudo rm` operations
- `chmod 777` (dangerous permissions)
- Writes to `.env`, `credentials.json`, `*.key` files
- Force pushes to main/master branches
- Any command touching `/etc/ppp/peers` (sensitive config)
- Modifications to build output directories without explicit approval

---

## Questions & Answers

| Question | Answer |
|----------|--------|
| TTS Provider: Which TTS provider do you have API keys for? | ElevenLabs (API key to be stored in .env file only) |
| Should the stop hook generate AI completion messages, or use static messages? | AI-generated using Anthropic API (key to be stored in .env file only) |
| Security Level: Should pre_tool_use block operations or just warn? | Block with exit code 2 |
| Logging: Where should hook logs be stored? | logs/ directory in project root |
| Session Context: What context should session_start.py load? | Git status, recent commits, and project issues |
| Engineer Name: What name should be used for personalized TTS? | Greg |

---

## Deliverables

### Workflow

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.

2. Detailed plan document, ***docs/gen/add_hooks_plan.md***, of all aspects and detailed todo list for me to review before commencing the implementation.

3. Once plan is approved, implement and check off the items on the todo list as they are completed.

4. **Build verification**: After every code change, verify scripts are syntactically correct. If errors are found, fix them immediately.

5. **Final verification**: Before marking work complete, verify:
   - All hook scripts execute without errors
   - TTS works (if API keys configured)
   - Security blocking works as expected
   - Logging captures events correctly

6. Once I have determined the work is completed successfully, add a concise description to the plan document of the work undertaken.

7. Include in the update the number of tokens used, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.

8. Merge the branch back into the original branch.

9. Update all documents with relevant details.

### Additional Implementation Steps

- Install UV package manager if not present: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Copy and adapt hook scripts from reference implementation
- Create `.env.sample` with placeholder API keys
- Create actual `.env` file with user's API keys (do not commit)
- Add `.env` to `.gitignore` if not already present
- Test each hook individually before full integration
- Verify TTS works (if API keys configured)
- Document hook behavior in CLAUDE.md

### Additional Deliverables

- Working hooks infrastructure in `.claude/hooks/`
- Merged `settings.json` configuration
- `logs/` directory for event tracking
- Updated `.gitignore` with `.env` exclusion
- Test verification that hooks execute correctly

---

## Security Note

**IMPORTANT:** API keys should NEVER be stored in YAML files, code, or committed to git.

Store all API keys in the `.env` file only:

```bash
# .env (never commit this file!)
ELEVENLABS_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ENGINEER_NAME=Greg
```

Ensure `.env` is in `.gitignore` before creating it.

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/add_hooks.yaml
**Generated:** 2025-12-30
**Auto-populated:** 3 sections (project structure, hardware info, development guidelines)
