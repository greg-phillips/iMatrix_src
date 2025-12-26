#!/bin/sh
##############################################################################
# @file install_tools_target.sh
# @brief Install profiling tools on target via package manager
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Detect the package manager on the target system and attempt to install
#   profiling tools (strace, tcpdump, ethtool, iperf3, etc.).
#
# @usage
#   ./scripts/install_tools_target.sh user@target
#
# @return
#   0 - All critical tools installed successfully
#   1 - SSH connection failed
#   2 - No package manager found OR critical tools missing (use host build)
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
LOG_DIR="$PROFILER_DIR/artifacts/logs"

# Tools to install (priority order)
# Critical tools - must have at least strace
CRITICAL_TOOLS="strace"
# Recommended tools
RECOMMENDED_TOOLS="tcpdump ethtool iperf3 lsof"
# Optional tools
OPTIONAL_TOOLS="procps sysstat perf htop iotop gdb gdbserver"

##############################################################################
# Functions
##############################################################################

# Print usage information
usage() {
    printf "Usage: %s user@target\n" "$(basename "$0")"
    printf "\n"
    printf "Install profiling tools on target via package manager.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (e.g., root@192.168.1.100)\n"
    printf "\n"
    printf "Exit codes:\n"
    printf "  0 - Critical tools installed successfully\n"
    printf "  1 - SSH connection failed\n"
    printf "  2 - No package manager or critical tools missing\n"
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

# Print a warning message
warning() {
    printf "[~] WARNING: %s\n" "$1"
}

# Run a command on the target
remote_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "$1" 2>/dev/null || true
}

# Run a command on target with exit code
remote_cmd_status() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "$1" 2>/dev/null
}

# Check if a command exists on target
remote_has_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "command -v $1 >/dev/null 2>&1" 2>/dev/null
}

# Detect package manager on target
detect_pkg_manager() {
    if remote_has_cmd opkg; then
        printf "opkg"
    elif remote_has_cmd apk; then
        printf "apk"
    elif remote_has_cmd apt-get; then
        printf "apt"
    elif remote_has_cmd apt; then
        printf "apt"
    elif remote_has_cmd yum; then
        printf "yum"
    elif remote_has_cmd dnf; then
        printf "dnf"
    else
        printf "none"
    fi
}

# Install package using detected package manager
install_package() {
    pkg="$1"
    case "$PKG_MGR" in
        opkg)
            remote_cmd "opkg install $pkg" >/dev/null 2>&1 && return 0
            ;;
        apk)
            remote_cmd "apk add $pkg" >/dev/null 2>&1 && return 0
            ;;
        apt)
            remote_cmd "apt-get install -y $pkg" >/dev/null 2>&1 && return 0
            ;;
        yum)
            remote_cmd "yum install -y $pkg" >/dev/null 2>&1 && return 0
            ;;
        dnf)
            remote_cmd "dnf install -y $pkg" >/dev/null 2>&1 && return 0
            ;;
    esac
    return 1
}

# Update package lists
update_pkg_lists() {
    status "Updating package lists..."
    case "$PKG_MGR" in
        opkg)
            remote_cmd "opkg update" >/dev/null 2>&1 || true
            ;;
        apk)
            remote_cmd "apk update" >/dev/null 2>&1 || true
            ;;
        apt)
            remote_cmd "apt-get update" >/dev/null 2>&1 || true
            ;;
        yum|dnf)
            # yum/dnf auto-update metadata
            ;;
    esac
}

##############################################################################
# Main
##############################################################################

# Validate arguments
if [ $# -lt 1 ]; then
    usage
fi

TARGET="$1"

# Extract hostname for log filename
TARGET_HOST=$(printf "%s" "$TARGET" | sed 's/.*@//')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/install_tools_${TARGET_HOST}_${TIMESTAMP}.txt"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

status "Installing profiling tools on target: $TARGET"

# Test SSH connectivity
if ! ssh $SSH_OPTS "$TARGET" "echo 'SSH OK'" >/dev/null 2>&1; then
    error "Cannot connect to target via SSH"
    exit 1
fi

# Start logging
{
    printf "Tool Installation Log\n"
    printf "=====================\n"
    printf "Generated: %s\n" "$(date)"
    printf "Target: %s\n\n" "$TARGET"

    ##########################################################################
    # Detect package manager
    ##########################################################################

    PKG_MGR=$(detect_pkg_manager)
    printf "Package manager detected: %s\n\n" "$PKG_MGR"

    if [ "$PKG_MGR" = "none" ]; then
        printf "No package manager found on target.\n"
        printf "Host-side build required.\n"
    fi

} >> "$LOG_FILE"

# Export for use in functions
PKG_MGR=$(detect_pkg_manager)

if [ "$PKG_MGR" = "none" ]; then
    error "No package manager found on target"
    printf "\nNo package manager detected. You need to build tools on the host.\n"
    printf "Run: ./scripts/build_tools_host.sh %s\n" "$TARGET"
    exit 2
fi

success "Package manager detected: $PKG_MGR"

# Update package lists
update_pkg_lists

##############################################################################
# Install tools
##############################################################################

CRITICAL_INSTALLED=""
CRITICAL_FAILED=""
RECOMMENDED_INSTALLED=""
RECOMMENDED_FAILED=""
OPTIONAL_INSTALLED=""
OPTIONAL_FAILED=""

# Install critical tools
printf "\nInstalling critical tools...\n"
for tool in $CRITICAL_TOOLS; do
    printf "  Installing %s... " "$tool"

    # Check if already installed
    if remote_has_cmd "$tool"; then
        printf "already installed\n"
        CRITICAL_INSTALLED="$CRITICAL_INSTALLED $tool"
    elif install_package "$tool"; then
        printf "OK\n"
        CRITICAL_INSTALLED="$CRITICAL_INSTALLED $tool"
    else
        printf "FAILED\n"
        CRITICAL_FAILED="$CRITICAL_FAILED $tool"
    fi
done

# Install recommended tools
printf "\nInstalling recommended tools...\n"
for tool in $RECOMMENDED_TOOLS; do
    printf "  Installing %s... " "$tool"

    if remote_has_cmd "$tool"; then
        printf "already installed\n"
        RECOMMENDED_INSTALLED="$RECOMMENDED_INSTALLED $tool"
    elif install_package "$tool"; then
        printf "OK\n"
        RECOMMENDED_INSTALLED="$RECOMMENDED_INSTALLED $tool"
    else
        printf "FAILED\n"
        RECOMMENDED_FAILED="$RECOMMENDED_FAILED $tool"
    fi
done

# Install optional tools
printf "\nInstalling optional tools...\n"
for tool in $OPTIONAL_TOOLS; do
    printf "  Installing %s... " "$tool"

    if remote_has_cmd "$tool"; then
        printf "already installed\n"
        OPTIONAL_INSTALLED="$OPTIONAL_INSTALLED $tool"
    elif install_package "$tool"; then
        printf "OK\n"
        OPTIONAL_INSTALLED="$OPTIONAL_INSTALLED $tool"
    else
        printf "skipped (not available)\n"
        OPTIONAL_FAILED="$OPTIONAL_FAILED $tool"
    fi
done

##############################################################################
# Log results
##############################################################################

{
    printf "\n--- Installation Results ---\n"
    printf "\nCritical tools installed:%s\n" "$CRITICAL_INSTALLED"
    printf "Critical tools failed:%s\n" "$CRITICAL_FAILED"
    printf "\nRecommended tools installed:%s\n" "$RECOMMENDED_INSTALLED"
    printf "Recommended tools failed:%s\n" "$RECOMMENDED_FAILED"
    printf "\nOptional tools installed:%s\n" "$OPTIONAL_INSTALLED"
    printf "Optional tools skipped:%s\n" "$OPTIONAL_FAILED"
} >> "$LOG_FILE"

##############################################################################
# Summary and exit
##############################################################################

printf "\n"
printf "=== INSTALLATION SUMMARY ===\n"
printf "\n"

if [ -n "$CRITICAL_INSTALLED" ]; then
    success "Critical tools:$CRITICAL_INSTALLED"
fi
if [ -n "$CRITICAL_FAILED" ]; then
    error "Critical tools FAILED:$CRITICAL_FAILED"
fi

if [ -n "$RECOMMENDED_INSTALLED" ]; then
    success "Recommended tools:$RECOMMENDED_INSTALLED"
fi
if [ -n "$RECOMMENDED_FAILED" ]; then
    warning "Recommended tools missing:$RECOMMENDED_FAILED"
fi

if [ -n "$OPTIONAL_INSTALLED" ]; then
    status "Optional tools:$OPTIONAL_INSTALLED"
fi

printf "\nLog saved to: %s\n" "$LOG_FILE"

# Determine exit code
if [ -n "$CRITICAL_FAILED" ]; then
    printf "\n"
    error "Critical tools could not be installed via package manager"
    printf "Run: ./scripts/build_tools_host.sh %s\n" "$TARGET"
    exit 2
fi

# Warn about strace specifically
if ! remote_has_cmd strace; then
    printf "\n"
    error "strace is not available on target"
    printf "Run: ./scripts/build_tools_host.sh %s\n" "$TARGET"
    exit 2
fi

success "Tool installation completed"
printf "You can now run: ./scripts/profile_fc1.sh %s\n" "$TARGET"
exit 0
