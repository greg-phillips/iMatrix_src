#!/bin/sh
##############################################################################
# @file deploy_tools.sh
# @brief Deploy built profiling tools to target system
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Deploy host-built tools from build/target_tools/<arch>/bin to the target.
#   Prefers /opt/fc-1-tools/bin if root writable, otherwise uses home directory.
#
# @usage
#   ./scripts/deploy_tools.sh user@target
#
# @output
#   Tools deployed to /opt/fc-1-tools/bin or /home/<user>/fc-1-tools/bin
#   artifacts/logs/deploy_tools_<host>_<timestamp>.txt
#
##############################################################################

set -eu

##############################################################################
# Configuration
##############################################################################

# SSH options
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROFILER_DIR/build/target_tools"
LOG_DIR="$PROFILER_DIR/artifacts/logs"

# Preferred deploy locations
DEPLOY_OPT="/opt/fc-1-tools"
DEPLOY_HOME_SUFFIX="fc-1-tools"

##############################################################################
# Functions
##############################################################################

usage() {
    printf "Usage: %s user@target\n" "$(basename "$0")"
    printf "\n"
    printf "Deploy host-built profiling tools to target system.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (e.g., root@192.168.1.100)\n"
    printf "\n"
    printf "Prerequisites:\n"
    printf "  Run build_tools_host.sh first to build the tools.\n"
    exit 1
}

status() {
    printf "[*] %s\n" "$1"
}

error() {
    printf "[!] ERROR: %s\n" "$1" >&2
}

success() {
    printf "[+] %s\n" "$1"
}

warning() {
    printf "[~] WARNING: %s\n" "$1"
}

# Run command on target
remote_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "$1" 2>/dev/null || true
}

# Run command on target with exit status
remote_cmd_status() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "$1" 2>/dev/null
}

# Check if target path is writable
remote_writable() {
    path="$1"
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "test -w $path || mkdir -p $path 2>/dev/null && test -w $path" 2>/dev/null
}

# Detect target architecture
detect_arch() {
    ARCH=$(remote_cmd "uname -m")

    case "$ARCH" in
        armv7l|armv6l|armv5tel|arm)
            if remote_cmd "readelf -A /bin/busybox 2>/dev/null | grep -q 'hard-float'" 2>/dev/null; then
                printf "armhf"
            else
                printf "armel"
            fi
            ;;
        aarch64|arm64)
            printf "aarch64"
            ;;
        x86_64)
            printf "x86_64"
            ;;
        i686|i386)
            printf "i686"
            ;;
        *)
            printf "unknown"
            ;;
    esac
}

##############################################################################
# Main
##############################################################################

if [ $# -lt 1 ]; then
    usage
fi

TARGET="$1"

# Extract hostname and user
TARGET_HOST=$(printf "%s" "$TARGET" | sed 's/.*@//')
TARGET_USER=$(printf "%s" "$TARGET" | sed 's/@.*//')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/deploy_tools_${TARGET_HOST}_${TIMESTAMP}.txt"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

status "Deploying tools to target: $TARGET"

# Test SSH connection
if ! ssh $SSH_OPTS "$TARGET" "echo 'SSH OK'" >/dev/null 2>&1; then
    error "Cannot connect to target via SSH"
    exit 1
fi

# Detect target architecture
TARGET_ARCH=$(detect_arch)
status "Target architecture: $TARGET_ARCH"

# Find built tools directory
TOOLS_SRC="$BUILD_DIR/$TARGET_ARCH/bin"

if [ ! -d "$TOOLS_SRC" ]; then
    error "No built tools found for architecture: $TARGET_ARCH"
    printf "Expected: %s\n" "$TOOLS_SRC"
    printf "\nRun first: ./scripts/build_tools_host.sh %s\n" "$TARGET"
    exit 1
fi

# Count available tools
TOOL_COUNT=$(find "$TOOLS_SRC" -type f | wc -l)
if [ "$TOOL_COUNT" -eq 0 ]; then
    error "No tools found in: $TOOLS_SRC"
    exit 1
fi

status "Found $TOOL_COUNT tool(s) in: $TOOLS_SRC"

# Start logging
{
    printf "Tool Deployment Log\n"
    printf "===================\n"
    printf "Generated: %s\n" "$(date)"
    printf "Target: %s\n" "$TARGET"
    printf "Architecture: %s\n" "$TARGET_ARCH"
    printf "Source: %s\n\n" "$TOOLS_SRC"
} > "$LOG_FILE"

##############################################################################
# Determine deploy location
##############################################################################

DEPLOY_DIR=""

# Try /opt/fc-1-tools first (requires root or writable /opt)
status "Checking /opt/fc-1-tools availability..."
if remote_writable "$DEPLOY_OPT"; then
    DEPLOY_DIR="$DEPLOY_OPT"
    success "Using: $DEPLOY_DIR"
else
    # Fall back to home directory
    REMOTE_HOME=$(remote_cmd "echo \$HOME")
    if [ -z "$REMOTE_HOME" ]; then
        REMOTE_HOME="/home/$TARGET_USER"
    fi
    DEPLOY_DIR="$REMOTE_HOME/$DEPLOY_HOME_SUFFIX"
    status "Using fallback: $DEPLOY_DIR"
fi

# Create deploy directories
status "Creating directories on target..."
remote_cmd "mkdir -p $DEPLOY_DIR/bin"
remote_cmd "mkdir -p $DEPLOY_DIR/lib"

{
    printf "Deploy location: %s\n\n" "$DEPLOY_DIR"
} >> "$LOG_FILE"

##############################################################################
# Deploy tools
##############################################################################

status "Deploying tools..."

DEPLOYED=""
FAILED=""

for tool in "$TOOLS_SRC"/*; do
    if [ -f "$tool" ]; then
        name=$(basename "$tool")
        printf "  Deploying %s... " "$name"

        # Copy tool to target
        # shellcheck disable=SC2086
        if scp $SSH_OPTS "$tool" "$TARGET:$DEPLOY_DIR/bin/" >/dev/null 2>&1; then
            # Make executable
            remote_cmd "chmod +x $DEPLOY_DIR/bin/$name"
            printf "OK\n"
            DEPLOYED="$DEPLOYED $name"
            printf "  Deployed: %s\n" "$name" >> "$LOG_FILE"
        else
            printf "FAILED\n"
            FAILED="$FAILED $name"
            printf "  Failed: %s\n" "$name" >> "$LOG_FILE"
        fi
    fi
done

##############################################################################
# Verify deployment
##############################################################################

printf "\n"
status "Verifying deployed tools..."

{
    printf "\nVerification:\n"
    printf "-------------\n"
} >> "$LOG_FILE"

for tool in $DEPLOYED; do
    printf "  Checking %s... " "$tool"

    # Try to run the tool with version flag
    VERSION_OUTPUT=""
    case "$tool" in
        strace)
            VERSION_OUTPUT=$(remote_cmd "$DEPLOY_DIR/bin/strace -V 2>&1 | head -n 1")
            ;;
        iperf3)
            VERSION_OUTPUT=$(remote_cmd "$DEPLOY_DIR/bin/iperf3 --version 2>&1 | head -n 1")
            ;;
        *)
            VERSION_OUTPUT=$(remote_cmd "$DEPLOY_DIR/bin/$tool --version 2>&1 | head -n 1" || \
                           remote_cmd "$DEPLOY_DIR/bin/$tool -V 2>&1 | head -n 1" || \
                           echo "version unknown")
            ;;
    esac

    if [ -n "$VERSION_OUTPUT" ]; then
        printf "OK (%s)\n" "$VERSION_OUTPUT"
        printf "  %s: %s\n" "$tool" "$VERSION_OUTPUT" >> "$LOG_FILE"
    else
        printf "OK\n"
        printf "  %s: verified\n" "$tool" >> "$LOG_FILE"
    fi
done

##############################################################################
# Generate PATH instructions
##############################################################################

printf "\n"
printf "=== DEPLOYMENT SUMMARY ===\n"
printf "\n"
printf "Deploy location: %s\n" "$DEPLOY_DIR"
printf "\n"

if [ -n "$DEPLOYED" ]; then
    success "Deployed tools:$DEPLOYED"
fi

if [ -n "$FAILED" ]; then
    error "Failed tools:$FAILED"
fi

printf "\n"
printf "To use the tools on target, run:\n"
printf "\n"
printf "  export PATH=%s/bin:\$PATH\n" "$DEPLOY_DIR"
printf "\n"

# Also create a helper script on target
status "Creating path helper script on target..."
remote_cmd "cat > $DEPLOY_DIR/setup_path.sh << 'EOF'
#!/bin/sh
# Source this file to add fc-1-tools to PATH
export PATH=$DEPLOY_DIR/bin:\$PATH
echo \"Added $DEPLOY_DIR/bin to PATH\"
EOF"
remote_cmd "chmod +x $DEPLOY_DIR/setup_path.sh"

printf "Or source the helper script:\n"
printf "\n"
printf "  . %s/setup_path.sh\n" "$DEPLOY_DIR"
printf "\n"

# Append to log
{
    printf "\nPATH export:\n"
    printf "  export PATH=%s/bin:\$PATH\n" "$DEPLOY_DIR"
    printf "\nHelper script:\n"
    printf "  %s/setup_path.sh\n" "$DEPLOY_DIR"
} >> "$LOG_FILE"

status "Log saved to: $LOG_FILE"

# Check for critical tools
if echo "$DEPLOYED" | grep -q "strace"; then
    printf "\n"
    success "Deployment completed successfully"
    printf "Next step: ./scripts/setup_fc1_service.sh %s\n" "$TARGET"
else
    printf "\n"
    error "Critical tool 'strace' was not deployed"
    exit 1
fi
