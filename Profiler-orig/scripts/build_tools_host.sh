#!/bin/sh
##############################################################################
# @file build_tools_host.sh
# @brief Cross-compile profiling tools on host for target deployment
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Build profiling tools (strace, iperf3, etc.) on the host machine for
#   deployment to the embedded target. Detects target architecture via SSH
#   and uses appropriate cross-compiler.
#
# @usage
#   ./scripts/build_tools_host.sh user@target
#
# @output
#   build/target_tools/<arch>/bin/*
#   tools/manifests/target_tools_<arch>_<timestamp>.txt
#
# @prerequisites
#   - Cross-compiler for target architecture (arm-linux-gnueabihf-gcc, etc.)
#   - Build tools: make, git, wget/curl
#   - Source packages will be downloaded if not present
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
BUILD_DIR="$PROFILER_DIR/build"
MANIFEST_DIR="$PROFILER_DIR/tools/manifests"

# Tool versions (known stable versions)
STRACE_VERSION="6.5"
STRACE_URL="https://github.com/strace/strace/releases/download/v${STRACE_VERSION}/strace-${STRACE_VERSION}.tar.xz"

IPERF3_VERSION="3.15"
IPERF3_URL="https://github.com/esnet/iperf/releases/download/${IPERF3_VERSION}/iperf-${IPERF3_VERSION}.tar.gz"

##############################################################################
# Functions
##############################################################################

usage() {
    printf "Usage: %s user@target\n" "$(basename "$0")"
    printf "\n"
    printf "Cross-compile profiling tools on host for target deployment.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target to detect architecture\n"
    printf "\n"
    printf "The script will:\n"
    printf "  1. Detect target architecture via SSH\n"
    printf "  2. Find appropriate cross-compiler\n"
    printf "  3. Download and build tools\n"
    printf "  4. Output to build/target_tools/<arch>/bin/\n"
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

# Run a command on target
remote_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "$1" 2>/dev/null || true
}

# Detect target architecture and map to cross-compiler prefix
detect_arch() {
    ARCH=$(remote_cmd "uname -m")

    case "$ARCH" in
        armv7l|armv6l|armv5tel|arm)
            # Check for hard float
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

# Find cross-compiler for architecture
find_cross_compiler() {
    arch="$1"

    case "$arch" in
        armhf)
            # Try common ARM hard-float cross-compiler prefixes
            for prefix in arm-linux-gnueabihf arm-none-linux-gnueabihf armv7-unknown-linux-gnueabihf; do
                if command -v "${prefix}-gcc" >/dev/null 2>&1; then
                    printf "%s" "$prefix"
                    return 0
                fi
            done
            # Check for SDK-specific compiler
            if [ -x "/opt/qconnect_sdk_musl/bin/arm-linux-gcc" ]; then
                printf "/opt/qconnect_sdk_musl/bin/arm-linux"
                return 0
            fi
            ;;
        armel)
            for prefix in arm-linux-gnueabi arm-none-linux-gnueabi; do
                if command -v "${prefix}-gcc" >/dev/null 2>&1; then
                    printf "%s" "$prefix"
                    return 0
                fi
            done
            ;;
        aarch64)
            for prefix in aarch64-linux-gnu aarch64-none-linux-gnu; do
                if command -v "${prefix}-gcc" >/dev/null 2>&1; then
                    printf "%s" "$prefix"
                    return 0
                fi
            done
            ;;
        x86_64|i686)
            # Native compilation
            printf "native"
            return 0
            ;;
    esac

    printf "none"
    return 1
}

# Download a file if not present
download() {
    url="$1"
    dest="$2"

    if [ -f "$dest" ]; then
        status "Using cached: $dest"
        return 0
    fi

    status "Downloading: $url"

    if command -v wget >/dev/null 2>&1; then
        wget -q -O "$dest" "$url"
    elif command -v curl >/dev/null 2>&1; then
        curl -sL -o "$dest" "$url"
    else
        error "Neither wget nor curl available"
        return 1
    fi
}

# Build strace
build_strace() {
    status "Building strace..."

    src_dir="$BUILD_DIR/src/strace-${STRACE_VERSION}"
    tarball="$BUILD_DIR/src/strace-${STRACE_VERSION}.tar.xz"

    mkdir -p "$BUILD_DIR/src"

    # Download if needed
    if ! download "$STRACE_URL" "$tarball"; then
        warning "Could not download strace, skipping"
        return 1
    fi

    # Extract
    if [ ! -d "$src_dir" ]; then
        status "Extracting strace..."
        cd "$BUILD_DIR/src"
        tar xf "$tarball"
    fi

    cd "$src_dir"

    # Clean previous build
    if [ -f "Makefile" ]; then
        make clean >/dev/null 2>&1 || true
    fi

    # Configure
    if [ "$CROSS_PREFIX" = "native" ]; then
        ./configure --prefix="$OUTPUT_DIR" \
            LDFLAGS="-static" \
            >/dev/null 2>&1
    else
        ./configure --prefix="$OUTPUT_DIR" \
            --host="$CROSS_PREFIX" \
            CC="${CROSS_PREFIX}-gcc" \
            LDFLAGS="-static" \
            >/dev/null 2>&1
    fi

    # Build
    if make -j"$(nproc 2>/dev/null || echo 1)" >/dev/null 2>&1; then
        # Install binary only
        cp -f src/strace "$OUTPUT_DIR/bin/"
        if [ "$CROSS_PREFIX" != "native" ]; then
            "${CROSS_PREFIX}-strip" "$OUTPUT_DIR/bin/strace" 2>/dev/null || true
        else
            strip "$OUTPUT_DIR/bin/strace" 2>/dev/null || true
        fi
        success "strace built successfully"
        return 0
    else
        error "strace build failed"
        return 1
    fi
}

# Build iperf3
build_iperf3() {
    status "Building iperf3..."

    src_dir="$BUILD_DIR/src/iperf-${IPERF3_VERSION}"
    tarball="$BUILD_DIR/src/iperf-${IPERF3_VERSION}.tar.gz"

    mkdir -p "$BUILD_DIR/src"

    # Download if needed
    if ! download "$IPERF3_URL" "$tarball"; then
        warning "Could not download iperf3, skipping"
        return 1
    fi

    # Extract
    if [ ! -d "$src_dir" ]; then
        status "Extracting iperf3..."
        cd "$BUILD_DIR/src"
        tar xf "$tarball"
    fi

    cd "$src_dir"

    # Clean previous build
    if [ -f "Makefile" ]; then
        make clean >/dev/null 2>&1 || true
    fi

    # Configure
    if [ "$CROSS_PREFIX" = "native" ]; then
        ./configure --prefix="$OUTPUT_DIR" \
            --disable-shared \
            --enable-static \
            >/dev/null 2>&1
    else
        ./configure --prefix="$OUTPUT_DIR" \
            --host="$CROSS_PREFIX" \
            CC="${CROSS_PREFIX}-gcc" \
            --disable-shared \
            --enable-static \
            >/dev/null 2>&1
    fi

    # Build
    if make -j"$(nproc 2>/dev/null || echo 1)" >/dev/null 2>&1; then
        cp -f src/iperf3 "$OUTPUT_DIR/bin/"
        if [ "$CROSS_PREFIX" != "native" ]; then
            "${CROSS_PREFIX}-strip" "$OUTPUT_DIR/bin/iperf3" 2>/dev/null || true
        else
            strip "$OUTPUT_DIR/bin/iperf3" 2>/dev/null || true
        fi
        success "iperf3 built successfully"
        return 0
    else
        warning "iperf3 build failed (optional tool, continuing)"
        return 1
    fi
}

# Generate manifest
generate_manifest() {
    manifest_file="$MANIFEST_DIR/target_tools_${TARGET_ARCH}_${TIMESTAMP}.txt"

    status "Generating manifest: $manifest_file"

    {
        printf "Target Tools Manifest\n"
        printf "=====================\n"
        printf "Generated: %s\n" "$(date)"
        printf "Target: %s\n" "$TARGET"
        printf "Architecture: %s\n" "$TARGET_ARCH"
        printf "Cross-compiler: %s\n" "$CROSS_PREFIX"
        printf "\n"
        printf "Built tools:\n"
        printf "------------\n"

        for tool in "$OUTPUT_DIR/bin/"*; do
            if [ -f "$tool" ]; then
                name=$(basename "$tool")
                size=$(ls -lh "$tool" | awk '{print $5}')
                md5=$(md5sum "$tool" | awk '{print $1}')
                printf "  %s\n" "$name"
                printf "    Size: %s\n" "$size"
                printf "    MD5:  %s\n" "$md5"
            fi
        done
    } > "$manifest_file"

    success "Manifest saved to: $manifest_file"
}

##############################################################################
# Main
##############################################################################

if [ $# -lt 1 ]; then
    usage
fi

TARGET="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create directories
mkdir -p "$BUILD_DIR/src"
mkdir -p "$MANIFEST_DIR"

status "Detecting target architecture..."

# Test SSH connection
if ! ssh $SSH_OPTS "$TARGET" "echo 'SSH OK'" >/dev/null 2>&1; then
    error "Cannot connect to target via SSH"
    exit 1
fi

# Detect architecture
TARGET_ARCH=$(detect_arch)
status "Target architecture: $TARGET_ARCH"

if [ "$TARGET_ARCH" = "unknown" ]; then
    error "Unknown target architecture"
    exit 1
fi

# Find cross-compiler
status "Finding cross-compiler..."
CROSS_PREFIX=$(find_cross_compiler "$TARGET_ARCH")

if [ "$CROSS_PREFIX" = "none" ]; then
    error "No cross-compiler found for $TARGET_ARCH"
    printf "\nPlease install a cross-compiler:\n"
    case "$TARGET_ARCH" in
        armhf)
            printf "  Ubuntu/Debian: sudo apt-get install gcc-arm-linux-gnueabihf\n"
            ;;
        armel)
            printf "  Ubuntu/Debian: sudo apt-get install gcc-arm-linux-gnueabi\n"
            ;;
        aarch64)
            printf "  Ubuntu/Debian: sudo apt-get install gcc-aarch64-linux-gnu\n"
            ;;
    esac
    exit 1
fi

if [ "$CROSS_PREFIX" = "native" ]; then
    status "Using native compiler (same architecture)"
else
    success "Found cross-compiler: $CROSS_PREFIX"
fi

# Setup output directory
OUTPUT_DIR="$BUILD_DIR/target_tools/$TARGET_ARCH"
mkdir -p "$OUTPUT_DIR/bin"
mkdir -p "$OUTPUT_DIR/lib"

status "Output directory: $OUTPUT_DIR"

##############################################################################
# Build tools
##############################################################################

BUILT_TOOLS=""
FAILED_TOOLS=""

# Build strace (critical)
if build_strace; then
    BUILT_TOOLS="$BUILT_TOOLS strace"
else
    FAILED_TOOLS="$FAILED_TOOLS strace"
fi

# Build iperf3 (optional)
if build_iperf3; then
    BUILT_TOOLS="$BUILT_TOOLS iperf3"
else
    FAILED_TOOLS="$FAILED_TOOLS iperf3"
fi

# Note about perf
printf "\n"
warning "perf requires matching kernel source and is not built automatically"
status "If perf is needed, obtain kernel source and build tools/perf manually"
status "Alternatively, ftrace will be used as a fallback in profile_fc1.sh"

##############################################################################
# Generate manifest and summary
##############################################################################

generate_manifest

printf "\n"
printf "=== BUILD SUMMARY ===\n"
printf "\n"
printf "Architecture: %s\n" "$TARGET_ARCH"
printf "Cross-compiler: %s\n" "$CROSS_PREFIX"
printf "Output: %s\n" "$OUTPUT_DIR"
printf "\n"

if [ -n "$BUILT_TOOLS" ]; then
    success "Built tools:$BUILT_TOOLS"
fi

if [ -n "$FAILED_TOOLS" ]; then
    warning "Failed tools:$FAILED_TOOLS"
fi

# List built binaries
printf "\nBuilt binaries:\n"
ls -lh "$OUTPUT_DIR/bin/"

# Check for critical tools
if [ ! -f "$OUTPUT_DIR/bin/strace" ]; then
    printf "\n"
    error "Critical tool 'strace' was not built"
    exit 1
fi

printf "\n"
success "Build completed"
printf "Next step: ./scripts/deploy_tools.sh %s\n" "$TARGET"
