#!/bin/sh
##############################################################################
# @file verify_fc1.sh
# @brief Verify FC-1 binary exists and is executable on target
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Check that /home/FC-1 exists on the target system, is executable,
#   and gather information about the binary.
#
# @usage
#   ./scripts/verify_fc1.sh user@target
#
# @output
#   artifacts/target_reports/fc1_verify_<host>_<timestamp>.txt
#
# @return
#   0 - FC-1 verified successfully
#   1 - FC-1 not found or not executable
#
##############################################################################

set -eu

##############################################################################
# Configuration
##############################################################################

# The FC-1 binary path (MUST NOT be changed per requirements)
FC1_PATH="/home/FC-1"

# SSH options for non-interactive, timeout-controlled connections
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"

# Script directory (for relative path resolution)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROFILER_DIR/artifacts/target_reports"

##############################################################################
# Functions
##############################################################################

# Print usage information
usage() {
    printf "Usage: %s user@target\n" "$(basename "$0")"
    printf "\n"
    printf "Verify FC-1 binary exists and is executable on target.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (e.g., root@192.168.1.100)\n"
    printf "\n"
    printf "The binary is expected at: %s\n" "$FC1_PATH"
    exit 1
}

# Print a status message
status() {
    printf "[*] %s\n" "$1"
}

# Print an error message
error() {
    printf "[!] ERROR: %s\n" "$1" >&2
}

# Print a success message
success() {
    printf "[+] %s\n" "$1"
}

# Run a command on the target, capturing output
remote_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "$1" 2>/dev/null || true
}

# Check if a command exists on target
remote_has_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "command -v $1 >/dev/null 2>&1" 2>/dev/null
}

##############################################################################
# Main
##############################################################################

# Validate arguments
if [ $# -lt 1 ]; then
    usage
fi

TARGET="$1"

# Extract hostname for report filename
TARGET_HOST=$(printf "%s" "$TARGET" | sed 's/.*@//')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/fc1_verify_${TARGET_HOST}_${TIMESTAMP}.txt"

# Ensure report directory exists
mkdir -p "$REPORT_DIR"

status "Verifying FC-1 binary on target: $TARGET"
status "Expected path: $FC1_PATH"

# Test SSH connectivity
if ! ssh $SSH_OPTS "$TARGET" "echo 'SSH OK'" >/dev/null 2>&1; then
    error "Cannot connect to target via SSH"
    exit 1
fi

# Start report
{
    printf "FC-1 Binary Verification Report\n"
    printf "================================\n"
    printf "Generated: %s\n" "$(date)"
    printf "Target: %s\n" "$TARGET"
    printf "Expected path: %s\n" "$FC1_PATH"
    printf "\n"

    ##########################################################################
    # Check if file exists
    ##########################################################################

    printf "--- File Existence Check ---\n"

    # shellcheck disable=SC2086
    if ssh $SSH_OPTS "$TARGET" "test -e $FC1_PATH" 2>/dev/null; then
        printf "File exists: YES\n"
        FC1_EXISTS=1
    else
        printf "File exists: NO\n"
        FC1_EXISTS=0
    fi

    ##########################################################################
    # Check if file is executable
    ##########################################################################

    printf "\n--- Executable Check ---\n"

    if [ "$FC1_EXISTS" = "1" ]; then
        # shellcheck disable=SC2086
        if ssh $SSH_OPTS "$TARGET" "test -x $FC1_PATH" 2>/dev/null; then
            printf "Executable: YES\n"
            FC1_EXECUTABLE=1
        else
            printf "Executable: NO\n"
            FC1_EXECUTABLE=0
        fi
    else
        printf "Executable: N/A (file does not exist)\n"
        FC1_EXECUTABLE=0
    fi

    ##########################################################################
    # File details
    ##########################################################################

    printf "\n--- File Details (ls -l) ---\n"
    remote_cmd "ls -l $FC1_PATH 2>&1"

    printf "\n--- File Type (file command) ---\n"
    if remote_has_cmd file; then
        remote_cmd "file $FC1_PATH 2>&1"
    else
        printf "file command not available\n"
    fi

    ##########################################################################
    # ELF header information
    ##########################################################################

    printf "\n--- ELF Header (readelf -h) ---\n"
    if remote_has_cmd readelf; then
        remote_cmd "readelf -h $FC1_PATH 2>&1"
    else
        printf "readelf not available, trying strings fallback...\n"
        if remote_has_cmd strings; then
            printf "\n--- Strings (first 20 lines) ---\n"
            remote_cmd "strings $FC1_PATH 2>/dev/null | head -n 20"
        else
            printf "strings not available\n"
        fi
    fi

    ##########################################################################
    # Debug symbols check
    ##########################################################################

    printf "\n--- Debug Symbols Check ---\n"
    if remote_has_cmd readelf; then
        DEBUG_INFO=$(remote_cmd "readelf -S $FC1_PATH 2>/dev/null | grep -c debug || echo 0")
        if [ "$DEBUG_INFO" -gt 0 ]; then
            printf "Debug sections found: %s\n" "$DEBUG_INFO"
            printf "Debug symbols: PRESENT\n"
        else
            printf "Debug sections found: 0\n"
            printf "Debug symbols: NOT PRESENT (may affect profiling)\n"
        fi
    else
        printf "Cannot check debug symbols (readelf not available)\n"
    fi

    ##########################################################################
    # File size and checksums
    ##########################################################################

    printf "\n--- File Size ---\n"
    remote_cmd "ls -lh $FC1_PATH 2>/dev/null | awk '{print \$5}'"

    printf "\n--- MD5 Checksum ---\n"
    if remote_has_cmd md5sum; then
        remote_cmd "md5sum $FC1_PATH 2>/dev/null"
    else
        printf "md5sum not available\n"
    fi

    ##########################################################################
    # Check if FC-1 is currently running
    ##########################################################################

    printf "\n--- Running Process Check ---\n"
    FC1_PID=$(remote_cmd "pidof FC-1 2>/dev/null || pgrep -f '/home/FC-1' 2>/dev/null || true")
    if [ -n "$FC1_PID" ]; then
        printf "FC-1 is RUNNING with PID: %s\n" "$FC1_PID"
        printf "\n--- Process Details ---\n"
        remote_cmd "ps -p $FC1_PID -o pid,ppid,user,vsz,rss,comm 2>/dev/null || ps | grep $FC1_PID"
    else
        printf "FC-1 is NOT currently running\n"
    fi

    ##########################################################################
    # Summary
    ##########################################################################

    printf "\n--- Verification Summary ---\n"
    printf "File exists:     %s\n" "$([ "$FC1_EXISTS" = "1" ] && echo 'YES' || echo 'NO')"
    printf "Executable:      %s\n" "$([ "$FC1_EXECUTABLE" = "1" ] && echo 'YES' || echo 'NO')"
    printf "Currently running: %s\n" "$([ -n "$FC1_PID" ] && echo 'YES' || echo 'NO')"

} > "$REPORT_FILE"

status "Report saved to: $REPORT_FILE"

# Print summary and exit status
printf "\n"
printf "=== FC-1 VERIFICATION SUMMARY ===\n"
printf "Target: %s\n" "$TARGET"
printf "Binary path: %s\n" "$FC1_PATH"
printf "\n"

# Read key values from report
if grep -q "File exists: YES" "$REPORT_FILE"; then
    success "File exists"
    if grep -q "Executable: YES" "$REPORT_FILE"; then
        success "File is executable"
        if grep -q "is RUNNING" "$REPORT_FILE"; then
            status "FC-1 is currently running"
        else
            status "FC-1 is not currently running"
        fi
        printf "\nFC-1 verified successfully.\n"
        printf "Full report: %s\n" "$REPORT_FILE"
        exit 0
    else
        error "File is NOT executable"
        printf "\nNext steps:\n"
        printf "  1. SSH to target: ssh %s\n" "$TARGET"
        printf "  2. Make executable: chmod +x %s\n" "$FC1_PATH"
        exit 1
    fi
else
    error "FC-1 binary NOT FOUND at $FC1_PATH"
    printf "\nNext steps:\n"
    printf "  1. Build FC-1 for the target platform\n"
    printf "  2. Deploy to target: scp FC-1 %s:%s\n" "$TARGET" "$FC1_PATH"
    printf "  3. Make executable: ssh %s 'chmod +x %s'\n" "$TARGET" "$FC1_PATH"
    printf "\nFull report: %s\n" "$REPORT_FILE"
    exit 1
fi
