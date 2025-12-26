#!/bin/sh
##############################################################################
# @file target_discover.sh
# @brief Discover target system capabilities for FC-1 profiling
# @author Claude Code
# @date 2025-12-21
#
# @description
#   SSH into a target system and collect comprehensive system information
#   to determine available profiling capabilities. Saves results to a
#   timestamped report file.
#
# @usage
#   ./scripts/target_discover.sh user@target
#
# @output
#   artifacts/target_reports/target_report_<host>_<timestamp>.txt
#
##############################################################################

set -eu

##############################################################################
# Configuration
##############################################################################

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
    printf "Discover target system capabilities for FC-1 profiling.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (e.g., root@192.168.1.100)\n"
    printf "\n"
    printf "Output:\n"
    printf "  Report saved to: artifacts/target_reports/target_report_<host>_<timestamp>.txt\n"
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

# Print a section header in the report
section() {
    printf "\n"
    printf "========================================\n"
    printf "  %s\n" "$1"
    printf "========================================\n"
}

# Run a command on the target, capturing output
# Returns empty string if command fails
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
REPORT_FILE="$REPORT_DIR/target_report_${TARGET_HOST}_${TIMESTAMP}.txt"

# Ensure report directory exists
mkdir -p "$REPORT_DIR"

status "Connecting to target: $TARGET"
status "Report will be saved to: $REPORT_FILE"

# Test SSH connectivity
if ! ssh $SSH_OPTS "$TARGET" "echo 'SSH connection successful'" >/dev/null 2>&1; then
    error "Cannot connect to target via SSH"
    error "Ensure SSH key-based authentication is configured"
    exit 1
fi

status "SSH connection established"

# Start report
{
    printf "FC-1 Target Discovery Report\n"
    printf "Generated: %s\n" "$(date)"
    printf "Target: %s\n" "$TARGET"
    printf "Host machine: %s\n" "$(hostname)"

    ##########################################################################
    section "BASIC SYSTEM INFORMATION"
    ##########################################################################

    printf "\n--- uname -a ---\n"
    remote_cmd "uname -a"

    printf "\n--- /etc/os-release ---\n"
    remote_cmd "cat /etc/os-release 2>/dev/null || echo 'Not available'"

    printf "\n--- BusyBox version ---\n"
    remote_cmd "busybox 2>&1 | head -n 1 || echo 'BusyBox not found'"

    ##########################################################################
    section "ARCHITECTURE AND LIBC"
    ##########################################################################

    printf "\n--- uname -m (architecture) ---\n"
    remote_cmd "uname -m"

    printf "\n--- ldd version ---\n"
    remote_cmd "ldd --version 2>&1 | head -n 1 || echo 'ldd not available'"

    printf "\n--- libc libraries ---\n"
    remote_cmd "ls -la /lib/libc* /lib/*/libc* 2>/dev/null || echo 'No libc found in standard locations'"

    printf "\n--- musl detection ---\n"
    remote_cmd "ls -la /lib/ld-musl* 2>/dev/null || echo 'musl not detected'"

    ##########################################################################
    section "KERNEL PERF/TRACING CAPABILITIES"
    ##########################################################################

    printf "\n--- /proc/config.gz (PERF_EVENT) ---\n"
    if remote_has_cmd zcat; then
        remote_cmd "zcat /proc/config.gz 2>/dev/null | grep -E 'PERF_EVENT|FTRACE|TRACING' || echo 'Cannot read /proc/config.gz'"
    else
        printf "zcat not available to read /proc/config.gz\n"
    fi

    printf "\n--- /sys/kernel/debug/tracing presence ---\n"
    remote_cmd "ls -la /sys/kernel/debug/tracing 2>/dev/null | head -n 5 || echo 'tracing directory not accessible'"

    printf "\n--- perf probe test ---\n"
    if remote_has_cmd perf; then
        remote_cmd "perf stat true 2>&1 || echo 'perf stat failed'"
    else
        printf "perf command not found\n"
    fi

    ##########################################################################
    section "AVAILABLE TOOLS"
    ##########################################################################

    printf "\n--- Tool availability check ---\n"
    for tool in perf strace ltrace gdbserver tcpdump ethtool ip ss netstat top ps htop iotop lsof iperf3 gdb; do
        if remote_has_cmd "$tool"; then
            printf "  [+] %-12s : AVAILABLE\n" "$tool"
        else
            printf "  [-] %-12s : not found\n" "$tool"
        fi
    done

    ##########################################################################
    section "PACKAGE MANAGER DETECTION"
    ##########################################################################

    printf "\n--- Package manager check ---\n"
    PKG_MGR="none"
    for pm in opkg apk apt yum dnf; do
        if remote_has_cmd "$pm"; then
            printf "  [+] %s detected\n" "$pm"
            PKG_MGR="$pm"
        fi
    done
    if [ "$PKG_MGR" = "none" ]; then
        printf "  [-] No package manager found\n"
    fi

    ##########################################################################
    section "INIT/SERVICE SYSTEM DETECTION"
    ##########################################################################

    printf "\n--- Init system check ---\n"

    # Check runit
    remote_cmd "test -d /etc/sv && echo '  [+] runit (/etc/sv) detected' || true"

    # Check sysvinit
    remote_cmd "test -d /etc/init.d && echo '  [+] sysvinit (/etc/init.d) detected' || true"

    # Check systemd
    if remote_has_cmd systemctl; then
        printf "  [+] systemd detected\n"
    fi

    # Check OpenRC
    if remote_has_cmd rc-service; then
        printf "  [+] OpenRC detected\n"
    fi

    ##########################################################################
    section "CPU INFORMATION"
    ##########################################################################

    printf "\n--- /proc/cpuinfo summary ---\n"
    remote_cmd "cat /proc/cpuinfo | grep -E 'processor|model name|Hardware|CPU|BogoMIPS' | head -n 20"

    printf "\n--- Core count ---\n"
    remote_cmd "grep -c processor /proc/cpuinfo || echo 'Unknown'"

    printf "\n--- CPU frequency governor ---\n"
    remote_cmd "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'cpufreq not available'"

    printf "\n--- Available governors ---\n"
    remote_cmd "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null || echo 'Not available'"

    ##########################################################################
    section "MEMORY INFORMATION"
    ##########################################################################

    printf "\n--- /proc/meminfo summary ---\n"
    remote_cmd "cat /proc/meminfo | head -n 10"

    ##########################################################################
    section "STORAGE INFORMATION"
    ##########################################################################

    printf "\n--- df -h ---\n"
    remote_cmd "df -h"

    printf "\n--- mount ---\n"
    remote_cmd "mount"

    ##########################################################################
    section "NETWORK INFORMATION"
    ##########################################################################

    printf "\n--- ip addr ---\n"
    remote_cmd "ip addr 2>/dev/null || ifconfig 2>/dev/null || echo 'Network info not available'"

    printf "\n--- ip route ---\n"
    remote_cmd "ip route 2>/dev/null || route 2>/dev/null || echo 'Route info not available'"

    printf "\n--- ip -s link ---\n"
    remote_cmd "ip -s link 2>/dev/null || echo 'Not available'"

    printf "\n--- /proc/net/dev ---\n"
    remote_cmd "cat /proc/net/dev"

    ##########################################################################
    section "END OF REPORT"
    ##########################################################################

    printf "\nReport generated at: %s\n" "$(date)"

} > "$REPORT_FILE"

status "Report saved to: $REPORT_FILE"

# Print summary to stdout
printf "\n"
printf "=== TARGET DISCOVERY SUMMARY ===\n"
printf "Target: %s\n" "$TARGET"
printf "\n"

# Extract key info from report
printf "Architecture: "
grep -A1 "uname -m" "$REPORT_FILE" | tail -n 1

printf "Kernel: "
grep -A1 "uname -a" "$REPORT_FILE" | tail -n 1 | awk '{print $3}'

printf "Package Manager: "
grep -E "^\s+\[\+\] (opkg|apk|apt|yum|dnf)" "$REPORT_FILE" | head -n 1 | awk '{print $2}' || printf "none\n"

printf "Init System: "
grep -E "^\s+\[\+\] (runit|sysvinit|systemd|OpenRC)" "$REPORT_FILE" | head -n 1 | awk '{print $2}' || printf "unknown\n"

printf "\nKey Tools:\n"
grep -E "^\s+\[\+\].*AVAILABLE" "$REPORT_FILE" | head -n 10

printf "\nFull report: %s\n" "$REPORT_FILE"
