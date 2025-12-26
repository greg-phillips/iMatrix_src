#!/bin/sh
##############################################################################
# @file test_connection.sh
# @brief Test SSH connection to target using configured credentials
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Tests the SSH connection to the target device using credentials from
#   config/target_connection.conf. Useful for verifying connectivity before
#   running profiling scripts.
#
# @usage
#   ./scripts/test_connection.sh [target_ip]
#
#   If target_ip is provided, it overrides TARGET_HOST in config.
#
##############################################################################

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$PROFILER_DIR/config/target_connection.conf"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    . "$CONFIG_FILE"
else
    echo "ERROR: Config file not found: $CONFIG_FILE"
    echo "Please create it from the template."
    exit 1
fi

# Override TARGET_HOST if provided as argument
if [ $# -ge 1 ]; then
    TARGET_HOST="$1"
fi

# Check if TARGET_HOST is set
if [ -z "$TARGET_HOST" ]; then
    echo "ERROR: TARGET_HOST not set."
    echo ""
    echo "Either:"
    echo "  1. Edit $CONFIG_FILE and set TARGET_HOST"
    echo "  2. Run: $0 <target_ip>"
    exit 1
fi

echo "Testing connection to ${TARGET_USER}@${TARGET_HOST}:${TARGET_PORT}..."
echo ""

# Check for sshpass
if command -v sshpass >/dev/null 2>&1; then
    echo "[+] sshpass found - using password authentication"
    SSH_CMD="sshpass -p '$TARGET_PASS' ssh $SSH_BASE_OPTS -p $TARGET_PORT ${TARGET_USER}@${TARGET_HOST}"
else
    echo "[~] sshpass not found - will prompt for password"
    echo "    Install with: sudo apt-get install sshpass"
    echo ""
    SSH_CMD="ssh $SSH_BASE_OPTS -p $TARGET_PORT ${TARGET_USER}@${TARGET_HOST}"
fi

echo ""
echo "Running: uname -a"
echo "---"

if command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$TARGET_PASS" ssh $SSH_BASE_OPTS -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_HOST}" "uname -a"
else
    ssh $SSH_BASE_OPTS -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_HOST}" "uname -a"
fi

result=$?

echo "---"
echo ""

if [ $result -eq 0 ]; then
    echo "[+] Connection successful!"
    echo ""
    echo "You can now run profiling scripts with:"
    echo "  ./scripts/target_discover.sh ${TARGET_USER}@${TARGET_HOST}"
    echo ""
    echo "Or set TARGET_HOST in config/target_connection.conf for convenience."
else
    echo "[!] Connection failed (exit code: $result)"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify target IP is correct: $TARGET_HOST"
    echo "  2. Verify credentials: user=$TARGET_USER"
    echo "  3. Check if SSH is running on target"
    echo "  4. Check network connectivity: ping $TARGET_HOST"
fi

exit $result
