#!/bin/sh
##############################################################################
# @file profile_fc1.sh
# @brief Run profiling session on FC-1 and collect artifacts
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Perform comprehensive profiling of the FC-1 application on the target.
#   Collects system state, CPU/memory usage, strace output, and optionally
#   perf/ftrace data. Creates a bundled archive of all artifacts.
#
# @usage
#   ./scripts/profile_fc1.sh user@target [--duration 60] [--no-tcpdump]
#
# @options
#   --duration N    Profile duration in seconds (default: 60)
#   --no-tcpdump    Skip network capture
#
# @output
#   Profile bundle on target at:
#   /var/log/fc-1/profiles/<timestamp>/profile_bundle_<timestamp>.tar.gz
#   or
#   /home/<user>/fc-1-profiles/<timestamp>/profile_bundle_<timestamp>.tar.gz
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
LOG_DIR="$PROFILER_DIR/artifacts/logs"

# FC-1 binary path
FC1_PATH="/home/FC-1"

# Default settings
DURATION=60
DO_TCPDUMP=1
SAMPLE_INTERVAL=5

##############################################################################
# Functions
##############################################################################

usage() {
    printf "Usage: %s user@target [options]\n" "$(basename "$0")"
    printf "\n"
    printf "Run profiling session on FC-1.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (e.g., root@192.168.1.100)\n"
    printf "\n"
    printf "Options:\n"
    printf "  --duration N   Profile duration in seconds (default: %d)\n" "$DURATION"
    printf "  --no-tcpdump   Skip network capture\n"
    printf "\n"
    printf "Output:\n"
    printf "  Profile bundle created on target\n"
    printf "  Use grab_profiles.sh to retrieve it\n"
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

# Check if a command exists on target
remote_has_cmd() {
    # shellcheck disable=SC2086
    ssh $SSH_OPTS "$TARGET" "command -v $1 >/dev/null 2>&1" 2>/dev/null
}

# Find FC-1 PID
find_fc1_pid() {
    # Try multiple methods
    PID=$(remote_cmd "pidof FC-1 2>/dev/null || true")

    if [ -z "$PID" ]; then
        PID=$(remote_cmd "pgrep -f '/home/FC-1' 2>/dev/null || true")
    fi

    if [ -z "$PID" ]; then
        PID=$(remote_cmd "ps aux 2>/dev/null | grep '/home/FC-1' | grep -v grep | awk '{print \$2}' | head -n 1 || true")
    fi

    if [ -z "$PID" ]; then
        PID=$(remote_cmd "ps | grep 'FC-1' | grep -v grep | awk '{print \$1}' | head -n 1 || true")
    fi

    printf "%s" "$PID"
}

##############################################################################
# Argument parsing
##############################################################################

if [ $# -lt 1 ]; then
    usage
fi

TARGET="$1"
shift

while [ $# -gt 0 ]; do
    case "$1" in
        --duration)
            shift
            DURATION="${1:-60}"
            ;;
        --no-tcpdump)
            DO_TCPDUMP=0
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            usage
            ;;
    esac
    shift
done

##############################################################################
# Main
##############################################################################

# Extract hostname and user
TARGET_HOST=$(printf "%s" "$TARGET" | sed 's/.*@//')
TARGET_USER=$(printf "%s" "$TARGET" | sed 's/@.*//')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_LOG="$LOG_DIR/profile_${TARGET_HOST}_${TIMESTAMP}.txt"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

status "Starting profiling session on: $TARGET"
status "Duration: ${DURATION}s"

# Test SSH connection
if ! ssh $SSH_OPTS "$TARGET" "echo 'SSH OK'" >/dev/null 2>&1; then
    error "Cannot connect to target via SSH"
    exit 1
fi

# Find FC-1 process
FC1_PID=$(find_fc1_pid)

if [ -z "$FC1_PID" ]; then
    error "FC-1 is not running on target"
    printf "Start FC-1 first, or use setup_fc1_service.sh\n"
    exit 1
fi

success "FC-1 found with PID: $FC1_PID"

##############################################################################
# Determine profile directory on target
##############################################################################

# Try system path first
if remote_cmd_status "test -w /var/log/fc-1/profiles 2>/dev/null || mkdir -p /var/log/fc-1/profiles 2>/dev/null"; then
    PROFILE_BASE="/var/log/fc-1/profiles"
else
    REMOTE_HOME=$(remote_cmd "echo \$HOME")
    if [ -z "$REMOTE_HOME" ]; then
        REMOTE_HOME="/home/$TARGET_USER"
    fi
    PROFILE_BASE="$REMOTE_HOME/fc-1-profiles"
    remote_cmd "mkdir -p $PROFILE_BASE"
fi

PROFILE_DIR="$PROFILE_BASE/$TIMESTAMP"
remote_cmd "mkdir -p $PROFILE_DIR"

status "Profile directory: $PROFILE_DIR"

# Start local log
{
    printf "FC-1 Profiling Session\n"
    printf "======================\n"
    printf "Generated: %s\n" "$(date)"
    printf "Target: %s\n" "$TARGET"
    printf "FC-1 PID: %s\n" "$FC1_PID"
    printf "Duration: %ds\n" "$DURATION"
    printf "Profile directory: %s\n\n" "$PROFILE_DIR"
} > "$LOCAL_LOG"

##############################################################################
# Collect baseline information
##############################################################################

status "Collecting baseline system information..."

# System info
remote_cmd "uname -a > $PROFILE_DIR/uname.txt"
remote_cmd "cat /proc/cpuinfo > $PROFILE_DIR/cpuinfo.txt 2>/dev/null || true"
remote_cmd "cat /proc/meminfo > $PROFILE_DIR/meminfo_start.txt 2>/dev/null || true"
remote_cmd "cat /proc/interrupts > $PROFILE_DIR/interrupts_start.txt 2>/dev/null || true"
remote_cmd "cat /proc/diskstats > $PROFILE_DIR/diskstats_start.txt 2>/dev/null || true"

# Storage
remote_cmd "df -h > $PROFILE_DIR/df.txt 2>/dev/null || df > $PROFILE_DIR/df.txt"
remote_cmd "mount > $PROFILE_DIR/mounts.txt"

# Network
remote_cmd "ip addr > $PROFILE_DIR/ip_addr.txt 2>/dev/null || ifconfig > $PROFILE_DIR/ip_addr.txt 2>/dev/null || true"
remote_cmd "ip route > $PROFILE_DIR/ip_route.txt 2>/dev/null || route > $PROFILE_DIR/ip_route.txt 2>/dev/null || true"
remote_cmd "ip -s link > $PROFILE_DIR/ip_link_stats.txt 2>/dev/null || true"
remote_cmd "cat /proc/net/dev > $PROFILE_DIR/proc_net_dev_start.txt 2>/dev/null || true"

# Process info
remote_cmd "cat /proc/$FC1_PID/status > $PROFILE_DIR/proc_status_start.txt 2>/dev/null || true"
remote_cmd "cat /proc/$FC1_PID/stat > $PROFILE_DIR/proc_stat_start.txt 2>/dev/null || true"
remote_cmd "cat /proc/$FC1_PID/io > $PROFILE_DIR/proc_io_start.txt 2>/dev/null || true"
remote_cmd "cat /proc/$FC1_PID/maps > $PROFILE_DIR/proc_maps.txt 2>/dev/null || true"
remote_cmd "cat /proc/$FC1_PID/fd > $PROFILE_DIR/proc_fd.txt 2>/dev/null || ls -la /proc/$FC1_PID/fd > $PROFILE_DIR/proc_fd.txt 2>/dev/null || true"

# Dmesg (if permitted)
remote_cmd "dmesg | tail -100 > $PROFILE_DIR/dmesg_tail.txt 2>/dev/null || true"

success "Baseline collected"

##############################################################################
# Start background sampling
##############################################################################

status "Starting background sampling (every ${SAMPLE_INTERVAL}s)..."

# Create sampling script on target
remote_cmd "cat > $PROFILE_DIR/sample.sh << 'SAMPLEEOF'
#!/bin/sh
PROFILE_DIR=\"$PROFILE_DIR\"
FC1_PID=\"$FC1_PID\"
INTERVAL=\"$SAMPLE_INTERVAL\"
SAMPLES=0
SAMPLE_FILE=\"\$PROFILE_DIR/samples.txt\"

echo \"Sample collection started at \$(date)\" > \$SAMPLE_FILE

while true; do
    SAMPLES=\$((SAMPLES + 1))
    echo \"\" >> \$SAMPLE_FILE
    echo \"=== Sample \$SAMPLES at \$(date) ===\" >> \$SAMPLE_FILE

    # Top output
    if command -v top >/dev/null 2>&1; then
        top -b -n 1 2>/dev/null | head -20 >> \$SAMPLE_FILE
    fi

    # Process stats
    if [ -f /proc/\$FC1_PID/stat ]; then
        echo \"--- /proc/\$FC1_PID/stat ---\" >> \$SAMPLE_FILE
        cat /proc/\$FC1_PID/stat >> \$SAMPLE_FILE 2>/dev/null
    fi

    if [ -f /proc/\$FC1_PID/status ]; then
        echo \"--- /proc/\$FC1_PID/status (memory) ---\" >> \$SAMPLE_FILE
        grep -E 'VmSize|VmRSS|VmData|VmStk|Threads' /proc/\$FC1_PID/status >> \$SAMPLE_FILE 2>/dev/null
    fi

    if [ -f /proc/\$FC1_PID/io ]; then
        echo \"--- /proc/\$FC1_PID/io ---\" >> \$SAMPLE_FILE
        cat /proc/\$FC1_PID/io >> \$SAMPLE_FILE 2>/dev/null
    fi

    # Disk stats
    echo \"--- /proc/diskstats ---\" >> \$SAMPLE_FILE
    cat /proc/diskstats >> \$SAMPLE_FILE 2>/dev/null

    sleep \$INTERVAL
done
SAMPLEEOF"

remote_cmd "chmod +x $PROFILE_DIR/sample.sh"

# Start sampler in background
remote_cmd "nohup sh $PROFILE_DIR/sample.sh > /dev/null 2>&1 &"
SAMPLER_PID=$(remote_cmd "echo \$!")
status "Sampler started (will run during profiling)"

##############################################################################
# Run strace
##############################################################################

status "Running strace for ${DURATION}s..."

STRACE_CMD=""
if remote_has_cmd strace; then
    STRACE_CMD="strace"
elif remote_cmd_status "test -x /opt/fc-1-tools/bin/strace"; then
    STRACE_CMD="/opt/fc-1-tools/bin/strace"
else
    REMOTE_HOME=$(remote_cmd "echo \$HOME")
    if remote_cmd_status "test -x $REMOTE_HOME/fc-1-tools/bin/strace"; then
        STRACE_CMD="$REMOTE_HOME/fc-1-tools/bin/strace"
    fi
fi

if [ -n "$STRACE_CMD" ]; then
    # Run strace with summary mode
    status "Attaching strace to PID $FC1_PID..."

    # Note: strace -c gives summary, -p attaches to process
    # We run it for DURATION seconds then send SIGINT
    remote_cmd "timeout $DURATION $STRACE_CMD -c -p $FC1_PID > $PROFILE_DIR/strace_summary.txt 2>&1 || true" &
    STRACE_BG_PID=$!

    # Also try to capture actual syscalls for a shorter period (10s or DURATION if shorter)
    TRACE_DURATION=$((DURATION < 10 ? DURATION : 10))
    remote_cmd "timeout $TRACE_DURATION $STRACE_CMD -tt -T -p $FC1_PID > $PROFILE_DIR/strace_trace.txt 2>&1 || true"

    # Wait for summary strace
    wait $STRACE_BG_PID 2>/dev/null || true

    success "strace completed"
else
    warning "strace not available, skipping"
    printf "strace not available\n" > "$PROFILE_DIR/strace_summary.txt"
fi

##############################################################################
# Check for perf
##############################################################################

status "Checking perf availability..."

PERF_AVAILABLE=0
if remote_has_cmd perf; then
    # Test if perf actually works
    if remote_cmd_status "perf stat true 2>/dev/null"; then
        PERF_AVAILABLE=1
        success "perf is available and functional"
    else
        warning "perf exists but cannot run (kernel support missing?)"
    fi
else
    warning "perf not found"
fi

if [ "$PERF_AVAILABLE" = "1" ]; then
    status "Running perf stat for ${DURATION}s..."

    # perf stat on the process
    remote_cmd "timeout $DURATION perf stat -p $FC1_PID 2> $PROFILE_DIR/perf_stat.txt || true"

    # Try a short perf record (10s max)
    RECORD_DURATION=$((DURATION < 10 ? DURATION : 10))
    if remote_cmd_status "perf record -p $FC1_PID -o $PROFILE_DIR/perf.data -- sleep 1 2>/dev/null"; then
        status "Running perf record for ${RECORD_DURATION}s..."
        remote_cmd "timeout $RECORD_DURATION perf record -p $FC1_PID -o $PROFILE_DIR/perf.data 2>/dev/null || true"

        # Generate report
        remote_cmd "perf report -i $PROFILE_DIR/perf.data --stdio > $PROFILE_DIR/perf_report.txt 2>/dev/null || true"
        success "perf data collected"
    else
        warning "perf record not available"
    fi
else
    printf "perf not available or not functional\n" > "$PROFILE_DIR/perf_stat.txt"
fi

##############################################################################
# Check for ftrace (fallback)
##############################################################################

if [ "$PERF_AVAILABLE" = "0" ]; then
    status "Checking ftrace availability..."

    if remote_cmd_status "test -d /sys/kernel/debug/tracing 2>/dev/null"; then
        if remote_cmd_status "test -w /sys/kernel/debug/tracing/trace 2>/dev/null"; then
            success "ftrace is accessible"

            # Short ftrace capture (5s max)
            FTRACE_DURATION=$((DURATION < 5 ? DURATION : 5))
            status "Running ftrace for ${FTRACE_DURATION}s..."

            remote_cmd "echo 0 > /sys/kernel/debug/tracing/tracing_on 2>/dev/null || true"
            remote_cmd "echo > /sys/kernel/debug/tracing/trace 2>/dev/null || true"
            remote_cmd "echo function_graph > /sys/kernel/debug/tracing/current_tracer 2>/dev/null || true"
            remote_cmd "echo 1 > /sys/kernel/debug/tracing/tracing_on 2>/dev/null || true"

            sleep "$FTRACE_DURATION"

            remote_cmd "echo 0 > /sys/kernel/debug/tracing/tracing_on 2>/dev/null || true"
            remote_cmd "cat /sys/kernel/debug/tracing/trace > $PROFILE_DIR/ftrace.txt 2>/dev/null || true"
            remote_cmd "echo nop > /sys/kernel/debug/tracing/current_tracer 2>/dev/null || true"

            success "ftrace data collected"
        else
            warning "ftrace directory exists but not writable (need root?)"
            printf "ftrace not writable\n" > "$PROFILE_DIR/ftrace.txt"
        fi
    else
        warning "ftrace not available"
        printf "ftrace not available\n" > "$PROFILE_DIR/ftrace.txt"
    fi
fi

##############################################################################
# Network capture
##############################################################################

if [ "$DO_TCPDUMP" = "1" ]; then
    status "Checking tcpdump availability..."

    TCPDUMP_CMD=""
    if remote_has_cmd tcpdump; then
        TCPDUMP_CMD="tcpdump"
    elif remote_cmd_status "test -x /opt/fc-1-tools/bin/tcpdump"; then
        TCPDUMP_CMD="/opt/fc-1-tools/bin/tcpdump"
    fi

    if [ -n "$TCPDUMP_CMD" ]; then
        # Short capture (10s max)
        CAP_DURATION=$((DURATION < 10 ? DURATION : 10))
        status "Capturing network traffic for ${CAP_DURATION}s..."

        # Capture on default interface, limit packets
        remote_cmd "timeout $CAP_DURATION $TCPDUMP_CMD -c 1000 -w $PROFILE_DIR/capture.pcap 2>/dev/null &"

        # Also get network stats
        if remote_has_cmd ss; then
            remote_cmd "ss -s > $PROFILE_DIR/ss_summary.txt 2>/dev/null || true"
            remote_cmd "ss -tuanp > $PROFILE_DIR/ss_connections.txt 2>/dev/null || true"
        elif remote_has_cmd netstat; then
            remote_cmd "netstat -s > $PROFILE_DIR/netstat_summary.txt 2>/dev/null || true"
            remote_cmd "netstat -tuanp > $PROFILE_DIR/netstat_connections.txt 2>/dev/null || true"
        fi

        sleep "$CAP_DURATION"
        success "Network capture completed"
    else
        warning "tcpdump not available, skipping network capture"
    fi
else
    status "Network capture skipped (--no-tcpdump)"
fi

##############################################################################
# Wait remaining duration if any
##############################################################################

# Calculate how much time we've already spent
# (strace ran for DURATION, but other things might have extended it)
# For simplicity, we just ensure the background sampler ran long enough
status "Waiting for profiling to complete..."
sleep 2

##############################################################################
# Stop sampling and collect final state
##############################################################################

status "Stopping sampler and collecting final state..."

# Kill sampler
remote_cmd "pkill -f 'sample.sh' 2>/dev/null || true"

# Collect final state
remote_cmd "cat /proc/meminfo > $PROFILE_DIR/meminfo_end.txt 2>/dev/null || true"
remote_cmd "cat /proc/interrupts > $PROFILE_DIR/interrupts_end.txt 2>/dev/null || true"
remote_cmd "cat /proc/diskstats > $PROFILE_DIR/diskstats_end.txt 2>/dev/null || true"
remote_cmd "cat /proc/net/dev > $PROFILE_DIR/proc_net_dev_end.txt 2>/dev/null || true"
remote_cmd "cat /proc/$FC1_PID/status > $PROFILE_DIR/proc_status_end.txt 2>/dev/null || true"
remote_cmd "cat /proc/$FC1_PID/io > $PROFILE_DIR/proc_io_end.txt 2>/dev/null || true"

success "Final state collected"

##############################################################################
# Create bundle
##############################################################################

status "Creating profile bundle..."

BUNDLE_NAME="profile_bundle_${TIMESTAMP}.tar.gz"
remote_cmd "cd $PROFILE_BASE && tar czf $BUNDLE_NAME $TIMESTAMP"

BUNDLE_PATH="$PROFILE_BASE/$BUNDLE_NAME"
BUNDLE_SIZE=$(remote_cmd "ls -lh $BUNDLE_PATH 2>/dev/null | awk '{print \$5}'")

success "Bundle created: $BUNDLE_PATH ($BUNDLE_SIZE)"

##############################################################################
# Summary
##############################################################################

# List collected files
FILES_COUNT=$(remote_cmd "ls -1 $PROFILE_DIR | wc -l")

printf "\n"
printf "=== PROFILING SUMMARY ===\n"
printf "\n"
printf "Target: %s\n" "$TARGET"
printf "FC-1 PID: %s\n" "$FC1_PID"
printf "Duration: %ds\n" "$DURATION"
printf "Profile directory: %s\n" "$PROFILE_DIR"
printf "Files collected: %s\n" "$FILES_COUNT"
printf "\n"
printf "Bundle: %s\n" "$BUNDLE_PATH"
printf "Size: %s\n" "$BUNDLE_SIZE"
printf "\n"

# List key files
status "Collected artifacts:"
remote_cmd "ls -la $PROFILE_DIR" | while read -r line; do
    printf "  %s\n" "$line"
done

printf "\n"
success "Profiling completed"
printf "\nTo retrieve the bundle:\n"
printf "  ./scripts/grab_profiles.sh %s\n" "$TARGET"

# Update local log
{
    printf "\nProfiling completed at: %s\n" "$(date)"
    printf "Bundle: %s\n" "$BUNDLE_PATH"
    printf "Files: %s\n" "$FILES_COUNT"
} >> "$LOCAL_LOG"

status "Local log saved to: $LOCAL_LOG"
