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

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROFILER_DIR/artifacts/logs"

# Source common SSH functions (supports sshpass for password auth)
. "$SCRIPT_DIR/common_ssh.sh"

# FC-1 binary path
FC1_PATH="/usr/qk/bin/FC-1"

# Default settings
DURATION=60
DO_TCPDUMP=1
SAMPLE_INTERVAL=5

##############################################################################
# Functions
##############################################################################

usage() {
    printf "Usage: %s [user@target] [options]\n" "$(basename "$0")"
    printf "\n"
    printf "Run profiling session on FC-1.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (optional, uses config if not specified)\n"
    printf "\n"
    printf "Configuration:\n"
    printf "  Connection settings loaded from config/target_connection.conf\n"
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

# Note: remote_cmd, remote_cmd_status, remote_has_cmd provided by common_ssh.sh

# Cleanup any orphaned profile scripts from previous runs
# Note: BusyBox pkill -f doesn't work properly, so we use PID-based killing
cleanup_old_samplers() {
    status "Checking for orphaned sampling scripts..."
    OLD_SAMPLERS=$(remote_cmd "ps | grep 'sample.sh' | grep -v grep || true")
    if [ -n "$OLD_SAMPLERS" ]; then
        warning "Found orphaned samplers:"
        printf "%s\n" "$OLD_SAMPLERS"
        status "Killing orphaned samplers..."
        remote_cmd "ps | grep 'sample.sh' | grep -v grep | awk '{print \$1}' | while read pid; do kill -9 \$pid 2>/dev/null; done"
        sleep 1
    fi
}

# Cleanup function for exit
# Note: BusyBox pkill -f doesn't work properly, so we use PID-based killing
cleanup_on_exit() {
    printf "\n[*] Cleaning up...\n"
    # Kill all sample.sh processes using reliable PID-based method
    remote_cmd "ps | grep 'sample.sh' | grep -v grep | awk '{print \$1}' | while read pid; do kill -9 \$pid 2>/dev/null; done"
    printf "[*] Cleanup complete\n"
}

# Find FC-1 PID
find_fc1_pid() {
    # Try multiple methods
    PID=$(remote_cmd "pidof FC-1 2>/dev/null || true")

    if [ -z "$PID" ]; then
        PID=$(remote_cmd "pgrep -f '/usr/qk/bin/FC-1' 2>/dev/null || true")
    fi

    if [ -z "$PID" ]; then
        PID=$(remote_cmd "ps aux 2>/dev/null | grep '/usr/qk/bin/FC-1' | grep -v grep | awk '{print \$1}' | head -n 1 || true")
    fi

    if [ -z "$PID" ]; then
        PID=$(remote_cmd "ps | grep 'FC-1' | grep -v grep | awk '{print \$1}' | head -n 1 || true")
    fi

    printf "%s" "$PID"
}

##############################################################################
# Argument parsing
##############################################################################

# First, check if first arg is a target (contains @) or an option (starts with -)
TARGET=""
if [ $# -ge 1 ]; then
    case "$1" in
        -h|--help)
            usage
            ;;
        --*)
            # First arg is an option, use config for target
            ;;
        *@*)
            # First arg contains @, treat as target
            TARGET="$1"
            shift
            ;;
        *)
            # Could be target without @ or something else - try config
            ;;
    esac
fi

# If no target from args, get from config
if [ -z "$TARGET" ]; then
    TARGET=$(get_configured_target)
    if [ -z "$TARGET" ]; then
        printf "ERROR: No target specified and TARGET_HOST not set in config\n" >&2
        printf "Either provide target as argument or configure config/target_connection.conf\n" >&2
        exit 1
    fi
fi

# Parse remaining options
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

# Initialize SSH with password support from config
init_ssh "$TARGET"

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

status "Starting profiling session on: $TARGET (port $SSH_PORT)"
status "Duration: ${DURATION}s"

# Test SSH connection
if ! test_ssh_connection; then
    error "Cannot connect to target via SSH"
    error "Check target IP, port ($SSH_PORT), and credentials"
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
# Cleanup old samplers and set trap
##############################################################################

# Clean up any orphaned samplers from previous runs
cleanup_old_samplers

# Set trap to cleanup on exit or interrupt
trap cleanup_on_exit EXIT INT TERM

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
    printf "%s\n" "======================"
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

# Record profiling start time
PROFILE_START_TIME=$(date +%s)

##############################################################################
# Run strace
##############################################################################

status "Running strace for ${DURATION}s..."

STRACE_CMD=""
if remote_has_cmd strace; then
    STRACE_CMD="strace"
elif remote_cmd_status "test -x /usr/qk/bin/strace"; then
    STRACE_CMD="/usr/qk/bin/strace"
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

    # Strace sample duration: 30s or DURATION if shorter
    STRACE_SAMPLE=$((DURATION < 30 ? DURATION : 30))

    # Run strace summary (counts syscalls) for sample period
    # Note: BusyBox may not have 'timeout', so we use background + sleep + kill
    status "Running strace summary for ${STRACE_SAMPLE}s..."
    remote_cmd "$STRACE_CMD -c -p $FC1_PID > $PROFILE_DIR/strace_summary.txt 2>&1 & STRACE_PID=\$!; sleep $STRACE_SAMPLE; kill -INT \$STRACE_PID 2>/dev/null; wait \$STRACE_PID 2>/dev/null || true"

    # Also capture actual syscalls for a shorter period (10s or DURATION if shorter)
    TRACE_DURATION=$((DURATION < 10 ? DURATION : 10))
    status "Running strace trace for ${TRACE_DURATION}s..."
    remote_cmd "$STRACE_CMD -tt -T -p $FC1_PID > $PROFILE_DIR/strace_trace.txt 2>&1 & STRACE_PID=\$!; sleep $TRACE_DURATION; kill -INT \$STRACE_PID 2>/dev/null; wait \$STRACE_PID 2>/dev/null || true"

    success "strace sampling completed"
else
    warning "strace not available, skipping"
    remote_cmd "echo 'strace not available' > $PROFILE_DIR/strace_summary.txt"
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
    # perf sample duration: 30s or DURATION if shorter
    PERF_SAMPLE=$((DURATION < 30 ? DURATION : 30))
    status "Running perf stat for ${PERF_SAMPLE}s..."

    # perf stat on the process (use background + sleep + kill for BusyBox compatibility)
    remote_cmd "perf stat -p $FC1_PID 2> $PROFILE_DIR/perf_stat.txt & PERF_PID=\$!; sleep $PERF_SAMPLE; kill -INT \$PERF_PID 2>/dev/null; wait \$PERF_PID 2>/dev/null || true"

    # Try a short perf record (10s max)
    RECORD_DURATION=$((DURATION < 10 ? DURATION : 10))
    if remote_cmd_status "perf record -p $FC1_PID -o $PROFILE_DIR/perf.data -- sleep 1 2>/dev/null"; then
        status "Running perf record for ${RECORD_DURATION}s..."
        remote_cmd "perf record -p $FC1_PID -o $PROFILE_DIR/perf.data & PERF_PID=\$!; sleep $RECORD_DURATION; kill -INT \$PERF_PID 2>/dev/null; wait \$PERF_PID 2>/dev/null || true"

        # Generate report
        remote_cmd "perf report -i $PROFILE_DIR/perf.data --stdio > $PROFILE_DIR/perf_report.txt 2>/dev/null || true"
        success "perf data collected"
    else
        warning "perf record not available"
    fi
else
    remote_cmd "echo 'perf not available or not functional' > $PROFILE_DIR/perf_stat.txt"
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
            remote_cmd "echo 'ftrace not writable' > $PROFILE_DIR/ftrace.txt"
        fi
    else
        warning "ftrace not available"
        remote_cmd "echo 'ftrace not available' > $PROFILE_DIR/ftrace.txt"
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
    elif remote_cmd_status "test -x /usr/qk/bin/tcpdump"; then
        TCPDUMP_CMD="/usr/qk/bin/tcpdump"
    elif remote_cmd_status "test -x /opt/fc-1-tools/bin/tcpdump"; then
        TCPDUMP_CMD="/opt/fc-1-tools/bin/tcpdump"
    fi

    if [ -n "$TCPDUMP_CMD" ]; then
        # Short capture (10s max)
        CAP_DURATION=$((DURATION < 10 ? DURATION : 10))
        status "Capturing network traffic for ${CAP_DURATION}s..."

        # Capture on default interface, limit packets (background + sleep + kill for BusyBox)
        remote_cmd "$TCPDUMP_CMD -c 1000 -w $PROFILE_DIR/capture.pcap 2>/dev/null & TCPDUMP_PID=\$!; sleep $CAP_DURATION; kill \$TCPDUMP_PID 2>/dev/null || true"

        # Also get network stats
        if remote_has_cmd ss; then
            remote_cmd "ss -s > $PROFILE_DIR/ss_summary.txt 2>/dev/null || true"
            remote_cmd "ss -tuanp > $PROFILE_DIR/ss_connections.txt 2>/dev/null || true"
        elif remote_has_cmd netstat; then
            remote_cmd "netstat -s > $PROFILE_DIR/netstat_summary.txt 2>/dev/null || true"
            remote_cmd "netstat -tuanp > $PROFILE_DIR/netstat_connections.txt 2>/dev/null || true"
        fi

        success "Network capture completed"
    else
        warning "tcpdump not available, skipping network capture"
    fi
else
    status "Network capture skipped (--no-tcpdump)"
fi

##############################################################################
# Wait remaining duration
##############################################################################

# Calculate elapsed time and remaining wait
CURRENT_TIME=$(date +%s)
ELAPSED=$((CURRENT_TIME - PROFILE_START_TIME))
REMAINING=$((DURATION - ELAPSED))

if [ "$REMAINING" -gt 0 ]; then
    status "Sampling in progress... ${ELAPSED}s elapsed, ${REMAINING}s remaining"
    status "Background sampler collecting data every ${SAMPLE_INTERVAL}s"

    # Show progress updates every 30 seconds for long runs
    while [ "$REMAINING" -gt 0 ]; do
        if [ "$REMAINING" -gt 30 ]; then
            WAIT_CHUNK=30
        else
            WAIT_CHUNK=$REMAINING
        fi
        sleep "$WAIT_CHUNK"

        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - PROFILE_START_TIME))
        REMAINING=$((DURATION - ELAPSED))

        if [ "$REMAINING" -gt 0 ]; then
            printf "\r[*] Sampling: %ds / %ds (%d%%)   " "$ELAPSED" "$DURATION" "$((ELAPSED * 100 / DURATION))"
        fi
    done
    printf "\n"
    success "Profiling duration completed (${DURATION}s)"
else
    status "Profiling tools already ran for ${ELAPSED}s (requested: ${DURATION}s)"
fi

##############################################################################
# Stop sampling and collect final state
##############################################################################

status "Stopping sampler and collecting final state..."

# Kill sampler (use -9 to ensure it stops, match specific profile dir)
remote_cmd "pkill -9 -f '$PROFILE_DIR/sample.sh' 2>/dev/null || true"
# Also try generic kill as backup
remote_cmd "pkill -9 -f 'sample.sh' 2>/dev/null || true"
sleep 1

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
printf "%s\n" "=== PROFILING SUMMARY ==="
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

# Disable cleanup trap since we already cleaned up
trap - EXIT INT TERM
