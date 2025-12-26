#!/bin/sh
##############################################################################
# @file sample_cpu.sh
# @brief CPU sampling profiler for FC-1 - shows which functions are running
# @author Claude Code
# @date 2025-12-22
#
# @description
#   Samples all FC-1 threads at regular intervals by reading /proc/[pid]/syscall
#   to capture the program counter. Decodes addresses to function names using
#   addr2line and the debug symbols in the FC-1 binary.
#
# @usage
#   ./scripts/sample_cpu.sh [--duration 30] [--interval 0.1]
#
##############################################################################

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

. "$SCRIPT_DIR/common_ssh.sh"

# Default settings
DURATION=30
INTERVAL="0.05"  # 50ms = 20 samples/sec
FC1_BINARY="/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1"
ADDR2LINE="/opt/qconnect_sdk_musl/bin/arm-linux-addr2line"

# FC-1 is loaded at this base address (from /proc/[pid]/maps)
FC1_BASE=0x00010000
FC1_END=0x003d7000

usage() {
    printf "Usage: %s [--duration N] [--interval N]\n" "$(basename "$0")"
    printf "\nCPU sampling profiler for FC-1\n\n"
    printf "Options:\n"
    printf "  --duration N   Sampling duration in seconds (default: 30)\n"
    printf "  --interval N   Sample interval in seconds (default: 0.05)\n"
    printf "  --binary PATH  Path to FC-1 binary with debug symbols\n"
    printf "\nOutput: Profile showing which functions consume most CPU time\n"
    exit 0
}

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --duration) DURATION="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        --binary) FC1_BINARY="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) shift ;;
    esac
done

# Verify binary exists
if [ ! -f "$FC1_BINARY" ]; then
    printf "[!] ERROR: FC-1 binary not found: %s\n" "$FC1_BINARY"
    exit 1
fi

if [ ! -x "$ADDR2LINE" ]; then
    printf "[!] ERROR: addr2line not found: %s\n" "$ADDR2LINE"
    exit 1
fi

# Initialize SSH
TARGET=$(get_configured_target)
[ -z "$TARGET" ] && { printf "ERROR: No target configured\n"; exit 1; }
init_ssh "$TARGET"

printf "[*] FC-1 CPU Sampling Profiler\n"
printf "[*] Target: %s\n" "$TARGET"
printf "[*] Duration: %ds, Interval: %ss\n" "$DURATION" "$INTERVAL"

# Find FC-1 PID and threads
FC1_PID=$(remote_cmd "pidof FC-1 2>/dev/null || true")
if [ -z "$FC1_PID" ]; then
    printf "[!] ERROR: FC-1 not running\n"
    exit 1
fi
printf "[+] FC-1 PID: %s\n" "$FC1_PID"

# Get thread list
THREADS=$(remote_cmd "ls /proc/$FC1_PID/task/")
THREAD_COUNT=$(echo "$THREADS" | wc -w)
printf "[+] Threads: %d\n" "$THREAD_COUNT"

# Get actual base address from maps
FC1_BASE_ACTUAL=$(remote_cmd "head -1 /proc/$FC1_PID/maps | cut -d'-' -f1")
printf "[+] FC-1 base address: 0x%s\n" "$FC1_BASE_ACTUAL"

# Create output directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$PROFILER_DIR/artifacts/profiles/cpu_profile_${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

RAW_SAMPLES="$OUTPUT_DIR/raw_samples.txt"
PROFILE_REPORT="$OUTPUT_DIR/profile_report.txt"

printf "[*] Sampling all threads for %ds...\n" "$DURATION"

# Collect samples - read syscall from each thread to get PC
remote_cmd "
END=\$((SECONDS + $DURATION))
while [ \$SECONDS -lt \$END ]; do
    for tid in /proc/$FC1_PID/task/*; do
        if [ -f \"\$tid/syscall\" ]; then
            # Read syscall - last field is PC
            read line < \"\$tid/syscall\" 2>/dev/null && echo \"\$line\" || true
        fi
    done
    sleep $INTERVAL
done
" > "$RAW_SAMPLES" 2>/dev/null

# Count samples
TOTAL_SAMPLES=$(wc -l < "$RAW_SAMPLES")
printf "[+] Collected %d samples\n" "$TOTAL_SAMPLES"

if [ "$TOTAL_SAMPLES" -eq 0 ]; then
    printf "[!] No samples collected\n"
    exit 1
fi

# Extract PCs (last field of each line, remove trailing whitespace)
printf "[*] Extracting program counters...\n"
awk '{print $NF}' "$RAW_SAMPLES" | sed 's/[^0-9a-fA-Fx]//g' | grep -v "^$" > "$OUTPUT_DIR/raw_pcs.txt"

# Count unique PCs
sort "$OUTPUT_DIR/raw_pcs.txt" | uniq -c | sort -rn > "$OUTPUT_DIR/pc_counts.txt"
UNIQUE_PCS=$(wc -l < "$OUTPUT_DIR/pc_counts.txt")
printf "[+] Unique addresses: %d\n" "$UNIQUE_PCS"

# Decode addresses
printf "[*] Decoding addresses to functions...\n"

# Process each PC and decode
{
    printf "FC-1 CPU Profile Report\n"
    printf "=======================\n"
    printf "Date: %s\n" "$(date)"
    printf "Target: %s\n" "$TARGET"
    printf "PID: %s (%d threads)\n" "$FC1_PID" "$THREAD_COUNT"
    printf "Duration: %ds\n" "$DURATION"
    printf "Total Samples: %d\n" "$TOTAL_SAMPLES"
    printf "\n"
    printf "Top Functions by CPU Time\n"
    printf "=========================\n"
    printf "\n"
    printf "%8s %6s  %-50s %s\n" "Samples" "%" "Function" "Source"
    printf "%8s %6s  %-50s %s\n" "-------" "-----" "--------------------------------------------------" "------"
} > "$PROFILE_REPORT"

# Process top 50 addresses
head -50 "$OUTPUT_DIR/pc_counts.txt" | while read count pc; do
    # Skip if PC is empty or not hex
    [ -z "$pc" ] && continue
    echo "$pc" | grep -q "^0x" || continue

    # Convert to decimal for comparison
    pc_dec=$(printf "%d" "$pc" 2>/dev/null || echo 0)

    # Check if in FC-1 code range (0x10000 - 0x3d7000)
    if [ "$pc_dec" -ge 65536 ] && [ "$pc_dec" -le 4018176 ]; then
        # In FC-1 range - decode with addr2line
        result=$($ADDR2LINE -e "$FC1_BINARY" -f -C "$pc" 2>/dev/null || echo "??")
        func=$(echo "$result" | head -1)
        src=$(echo "$result" | tail -1)
    else
        # In shared library or kernel
        func="[external/kernel]"
        src="$pc"
    fi

    # Calculate percentage
    pct=$(awk "BEGIN {printf \"%.1f\", ($count / $TOTAL_SAMPLES) * 100}")

    # Truncate function name if needed
    func_short=$(printf "%.50s" "$func")

    printf "%8s %5s%%  %-50s %s\n" "$count" "$pct" "$func_short" "$src"
done >> "$PROFILE_REPORT"

# Show results
printf "\n"
cat "$PROFILE_REPORT"

printf "\n[+] Full report saved to: %s\n" "$PROFILE_REPORT"
printf "[+] Raw data in: %s\n" "$OUTPUT_DIR"

# Summary
printf "\n"
printf "=== Summary ===\n"
IN_FC1=$(awk '{print $2}' "$OUTPUT_DIR/pc_counts.txt" | while read pc; do
    pc_dec=$(printf "%d" "$pc" 2>/dev/null || echo 0)
    [ "$pc_dec" -ge 65536 ] && [ "$pc_dec" -le 4018176 ] && echo "1"
done | wc -l)

printf "Samples in FC-1 code: %d\n" "$IN_FC1"
printf "Samples in libraries/kernel: %d\n" "$((UNIQUE_PCS - IN_FC1))"
