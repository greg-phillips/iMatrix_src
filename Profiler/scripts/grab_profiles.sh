#!/bin/sh
##############################################################################
# @file grab_profiles.sh
# @brief Retrieve profile bundles from target to local machine
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Locate and download the newest profile bundle from the target system.
#   Checks both preferred (/var/log/fc-1/profiles) and fallback
#   (/home/<user>/fc-1-profiles) locations.
#
# @usage
#   ./scripts/grab_profiles.sh user@target
#
# @output
#   artifacts/profiles/<host>/<timestamp>.tar.gz
#
##############################################################################

set -eu

##############################################################################
# Configuration
##############################################################################

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILES_DIR="$PROFILER_DIR/artifacts/profiles"

# Source common SSH functions (supports sshpass for password auth)
. "$SCRIPT_DIR/common_ssh.sh"

##############################################################################
# Functions
##############################################################################

usage() {
    printf "Usage: %s [user@target] [--all]\n" "$(basename "$0")"
    printf "\n"
    printf "Retrieve profile bundles from target.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (optional, uses config if not specified)\n"
    printf "\n"
    printf "Configuration:\n"
    printf "  Connection settings loaded from config/target_connection.conf\n"
    printf "\n"
    printf "Options:\n"
    printf "  --all          Download all bundles (default: newest only)\n"
    printf "\n"
    printf "Output:\n"
    printf "  artifacts/profiles/<host>/<filename>\n"
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

# Note: remote_cmd, scp_from_target provided by common_ssh.sh

##############################################################################
# Argument parsing
##############################################################################

# Parse arguments - first non-option is target
TARGET=""
GRAB_ALL=0

while [ $# -gt 0 ]; do
    case "$1" in
        --all)
            GRAB_ALL=1
            ;;
        -h|--help)
            usage
            ;;
        --*)
            error "Unknown option: $1"
            usage
            ;;
        *)
            # If not an option and no target yet, treat as target
            if [ -z "$TARGET" ]; then
                TARGET="$1"
            else
                error "Unknown argument: $1"
                usage
            fi
            ;;
    esac
    shift
done

# If no target from args, get from config
if [ -z "$TARGET" ]; then
    TARGET=$(get_configured_target)
    if [ -z "$TARGET" ]; then
        printf "ERROR: No target specified and TARGET_HOST not set in config\n" >&2
        printf "Either provide target as argument or configure config/target_connection.conf\n" >&2
        exit 1
    fi
fi

# Initialize SSH with password support from config
init_ssh "$TARGET"

##############################################################################
# Main
##############################################################################

# Extract hostname and user
TARGET_HOST=$(printf "%s" "$TARGET" | sed 's/.*@//')
TARGET_USER=$(printf "%s" "$TARGET" | sed 's/@.*//')

# Create local profiles directory for this host
LOCAL_DIR="$PROFILES_DIR/$TARGET_HOST"
mkdir -p "$LOCAL_DIR"

status "Searching for profile bundles on: $TARGET (port $SSH_PORT)"

# Test SSH connection
if ! test_ssh_connection; then
    error "Cannot connect to target via SSH"
    error "Check target IP, port ($SSH_PORT), and credentials"
    exit 1
fi

##############################################################################
# Find profile bundles
##############################################################################

# Check both locations
SEARCH_PATHS="/var/log/fc-1/profiles"

REMOTE_HOME=$(remote_cmd "echo \$HOME")
if [ -z "$REMOTE_HOME" ]; then
    REMOTE_HOME="/home/$TARGET_USER"
fi
SEARCH_PATHS="$SEARCH_PATHS $REMOTE_HOME/fc-1-profiles"

BUNDLES=""

for path in $SEARCH_PATHS; do
    status "Checking: $path"

    # Find bundle files
    FOUND=$(remote_cmd "ls -t $path/profile_bundle_*.tar.gz 2>/dev/null || true")

    if [ -n "$FOUND" ]; then
        for bundle in $FOUND; do
            BUNDLES="$BUNDLES $bundle"
        done
    fi
done

# Remove leading space
BUNDLES=$(echo "$BUNDLES" | sed 's/^ //')

if [ -z "$BUNDLES" ]; then
    error "No profile bundles found on target"
    printf "\nSearched locations:\n"
    for path in $SEARCH_PATHS; do
        printf "  %s\n" "$path"
    done
    printf "\nRun profile_fc1.sh first to create a profile.\n"
    exit 1
fi

# Count bundles
BUNDLE_COUNT=$(echo "$BUNDLES" | wc -w)
status "Found $BUNDLE_COUNT bundle(s)"

##############################################################################
# Download bundles
##############################################################################

if [ "$GRAB_ALL" = "1" ]; then
    status "Downloading all bundles..."
    DOWNLOAD_LIST="$BUNDLES"
else
    # Just get the newest (first in list, since ls -t sorts by time)
    DOWNLOAD_LIST=$(echo "$BUNDLES" | awk '{print $1}')
    status "Downloading newest bundle..."
fi

DOWNLOADED=""
FAILED=""

for bundle in $DOWNLOAD_LIST; do
    filename=$(basename "$bundle")
    local_path="$LOCAL_DIR/$filename"

    printf "  Downloading %s... " "$filename"

    # Check if already exists locally
    if [ -f "$local_path" ]; then
        printf "already exists (skipping)\n"
        DOWNLOADED="$DOWNLOADED $filename"
        continue
    fi

    # Download via scp
    if scp_from_target "$bundle" "$local_path" >/dev/null 2>&1; then
        SIZE=$(ls -lh "$local_path" | awk '{print $5}')
        printf "OK (%s)\n" "$SIZE"
        DOWNLOADED="$DOWNLOADED $filename"
    else
        printf "FAILED\n"
        FAILED="$FAILED $filename"
    fi
done

##############################################################################
# Summary
##############################################################################

printf "\n"
printf "%s\n" "=== DOWNLOAD SUMMARY ==="
printf "\n"
printf "Target: %s\n" "$TARGET"
printf "Local directory: %s\n" "$LOCAL_DIR"
printf "\n"

if [ -n "$DOWNLOADED" ]; then
    success "Downloaded:"
    for f in $DOWNLOADED; do
        printf "  %s/%s\n" "$LOCAL_DIR" "$f"
    done
fi

if [ -n "$FAILED" ]; then
    printf "\n"
    error "Failed:"
    for f in $FAILED; do
        printf "  %s\n" "$f"
    done
fi

# Show newest download path
if [ -n "$DOWNLOADED" ]; then
    NEWEST=$(echo "$DOWNLOADED" | awk '{print $1}')
    NEWEST_PATH="$LOCAL_DIR/$NEWEST"

    printf "\n"
    status "Newest bundle: $NEWEST_PATH"

    # Show contents
    printf "\nBundle contents:\n"
    tar tzf "$NEWEST_PATH" | head -20

    TOTAL=$(tar tzf "$NEWEST_PATH" | wc -l)
    if [ "$TOTAL" -gt 20 ]; then
        printf "  ... and %d more files\n" "$((TOTAL - 20))"
    fi

    printf "\nTo extract:\n"
    printf "  cd %s && tar xzf %s\n" "$LOCAL_DIR" "$NEWEST"
fi

printf "\n"
success "Profile retrieval completed"
