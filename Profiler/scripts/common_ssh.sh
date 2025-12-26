#!/bin/sh
##############################################################################
# @file common_ssh.sh
# @brief Common SSH functions for profiler scripts
# @author Claude Code
# @date 2025-12-22
#
# @description
#   Provides SSH wrapper functions that support password authentication via
#   sshpass. Source this file from other scripts.
#
# @usage
#   . "$(dirname "$0")/common_ssh.sh"
#   init_ssh "$TARGET"
#   remote_cmd "uname -a"
#
##############################################################################

# Default SSH options
SSH_BASE_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null"

# Default port
SSH_PORT="${SSH_PORT:-22}"

# Password (can be overridden by config)
SSH_PASS="${SSH_PASS:-}"

# Find Profiler directory - scripts are always in Profiler/scripts/
# This file (common_ssh.sh) is in scripts/, so parent is Profiler
_COMMON_SSH_SCRIPT_DIR=""
_PROFILER_DIR=""
_CONFIG_FILE=""

_find_config() {
    # Method 1: Use the calling script's directory (set before sourcing)
    if [ -n "${SCRIPT_DIR:-}" ] && [ -f "$SCRIPT_DIR/../config/target_connection.conf" ]; then
        _PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    # Method 2: Try relative to $0
    elif [ -f "$(dirname "$0")/../config/target_connection.conf" ]; then
        _PROFILER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    # Method 3: Try current working directory
    elif [ -f "./config/target_connection.conf" ]; then
        _PROFILER_DIR="$(pwd)"
    elif [ -f "../config/target_connection.conf" ]; then
        _PROFILER_DIR="$(cd ".." && pwd)"
    fi

    if [ -n "$_PROFILER_DIR" ]; then
        _CONFIG_FILE="$_PROFILER_DIR/config/target_connection.conf"
    fi
}

_find_config

##############################################################################
# Load configuration if available
##############################################################################
load_ssh_config() {
    if [ -f "$_CONFIG_FILE" ]; then
        # Source config but don't fail if missing
        . "$_CONFIG_FILE" 2>/dev/null || true

        # Map config variables to our variables
        if [ -n "${TARGET_PASS:-}" ]; then
            SSH_PASS="$TARGET_PASS"
        fi
        if [ -n "${TARGET_PORT:-}" ]; then
            SSH_PORT="$TARGET_PORT"
        fi
    fi
}

##############################################################################
# Initialize SSH for a target
# Usage: init_ssh ["user@host"]
# If no argument provided, uses TARGET_USER@TARGET_HOST from config
##############################################################################
init_ssh() {
    # Load config first
    load_ssh_config

    # Use argument if provided, otherwise build from config
    if [ $# -ge 1 ] && [ -n "$1" ]; then
        SSH_TARGET="$1"
    elif [ -n "${TARGET_USER:-}" ] && [ -n "${TARGET_HOST:-}" ]; then
        SSH_TARGET="${TARGET_USER}@${TARGET_HOST}"
    else
        echo "ERROR: No target specified and TARGET_HOST not set in config" >&2
        return 1
    fi

    # Check for sshpass
    if command -v sshpass >/dev/null 2>&1 && [ -n "$SSH_PASS" ]; then
        SSH_USE_SSHPASS=1
    else
        SSH_USE_SSHPASS=0
    fi
}

##############################################################################
# Get the configured target string (user@host)
# Usage: get_target
##############################################################################
get_configured_target() {
    load_ssh_config
    if [ -n "${TARGET_USER:-}" ] && [ -n "${TARGET_HOST:-}" ]; then
        echo "${TARGET_USER}@${TARGET_HOST}"
    else
        echo ""
    fi
}

##############################################################################
# Run SSH command on target
# Usage: remote_cmd "command"
# Returns: command output, empty on failure
##############################################################################
remote_cmd() {
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        sshpass -p "$SSH_PASS" ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "$1" 2>/dev/null || true
    else
        ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "$1" 2>/dev/null || true
    fi
}

##############################################################################
# Run SSH command and return exit status
# Usage: remote_cmd_status "command"
# Returns: exit status of remote command
##############################################################################
remote_cmd_status() {
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        sshpass -p "$SSH_PASS" ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "$1" 2>/dev/null
    else
        ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "$1" 2>/dev/null
    fi
}

##############################################################################
# Check if command exists on target
# Usage: remote_has_cmd "command"
# Returns: 0 if exists, 1 if not
##############################################################################
remote_has_cmd() {
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        sshpass -p "$SSH_PASS" ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "command -v $1" >/dev/null 2>&1
    else
        ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "command -v $1" >/dev/null 2>&1
    fi
}

##############################################################################
# Test SSH connection
# Usage: test_ssh_connection
# Returns: 0 if successful, 1 if failed
##############################################################################
test_ssh_connection() {
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        sshpass -p "$SSH_PASS" ssh $SSH_BASE_OPTS -p "$SSH_PORT" "$SSH_TARGET" "echo OK" >/dev/null 2>&1
    else
        ssh $SSH_BASE_OPTS -o BatchMode=yes -p "$SSH_PORT" "$SSH_TARGET" "echo OK" >/dev/null 2>&1
    fi
}

##############################################################################
# Copy file to target via SCP
# Usage: scp_to_target "local_file" "remote_path"
##############################################################################
scp_to_target() {
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        sshpass -p "$SSH_PASS" scp $SSH_BASE_OPTS -P "$SSH_PORT" "$1" "${SSH_TARGET}:$2"
    else
        scp $SSH_BASE_OPTS -P "$SSH_PORT" "$1" "${SSH_TARGET}:$2"
    fi
}

##############################################################################
# Copy file from target via SCP
# Usage: scp_from_target "remote_path" "local_file"
##############################################################################
scp_from_target() {
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        sshpass -p "$SSH_PASS" scp $SSH_BASE_OPTS -P "$SSH_PORT" "${SSH_TARGET}:$1" "$2"
    else
        scp $SSH_BASE_OPTS -P "$SSH_PORT" "${SSH_TARGET}:$1" "$2"
    fi
}

##############################################################################
# Print SSH connection info
##############################################################################
print_ssh_info() {
    echo "Target: $SSH_TARGET"
    echo "Port: $SSH_PORT"
    if [ "$SSH_USE_SSHPASS" = "1" ]; then
        echo "Auth: sshpass (password)"
    else
        echo "Auth: key-based or interactive"
    fi
}
