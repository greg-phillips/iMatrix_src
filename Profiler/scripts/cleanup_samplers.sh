#!/bin/sh
##############################################################################
# @file cleanup_samplers.sh
# @brief Kill any orphaned sampling scripts on target
# @author Claude Code
# @date 2025-12-22
##############################################################################

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/common_ssh.sh"

# Get target from config or argument
if [ $# -ge 1 ]; then
    TARGET="$1"
else
    TARGET=$(get_configured_target)
    if [ -z "$TARGET" ]; then
        printf "ERROR: No target configured\n" >&2
        exit 1
    fi
fi

init_ssh "$TARGET"

printf "[*] Checking for orphaned samplers on %s...\n" "$TARGET"

# Find samplers - use ps format that works on BusyBox
SAMPLERS=$(remote_cmd "ps | grep 'sample.sh' | grep -v grep || true")

if [ -n "$SAMPLERS" ]; then
    printf "[!] Found orphaned samplers:\n"
    printf "%s\n" "$SAMPLERS"
    printf "\n[*] Killing all sample.sh processes...\n"

    # BusyBox pkill may not support -f properly, so extract PIDs and kill directly
    # Use awk to get first column (PID) from ps output
    remote_cmd "ps | grep 'sample.sh' | grep -v grep | awk '{print \$1}' | while read pid; do kill -9 \$pid 2>/dev/null; done"
    sleep 1

    # Verify
    REMAINING=$(remote_cmd "ps | grep 'sample.sh' | grep -v grep || true")
    if [ -z "$REMAINING" ]; then
        printf "[+] All samplers killed successfully\n"
    else
        printf "[!] Some samplers may still be running:\n"
        printf "%s\n" "$REMAINING"
    fi
else
    printf "[+] No orphaned samplers found\n"
fi
