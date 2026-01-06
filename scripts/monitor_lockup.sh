#!/bin/bash
#
# monitor_lockup.sh - Automated lockup detection and log collection
#
# Monitors FC-1 devices every 10 minutes for lockup conditions.
# When lockup detected, downloads logs for root cause analysis.
#
# Usage:
#   ./monitor_lockup.sh              # Monitor default devices
#   ./monitor_lockup.sh 10.2.0.169   # Monitor single device
#
# Author: Claude Code
# Date: 2026-01-06
#

set -u

# Configuration
DEFAULT_DEVICES=("10.2.0.169" "10.2.0.179")
SSH_PORT="22222"
SSH_PASS="PasswordQConnect"
CHECK_INTERVAL=600  # 10 minutes in seconds
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FC1_SCRIPT="$SCRIPT_DIR/fc1"
LOG_BASE_DIR="/home/greg/iMatrix/iMatrix_Client/logs/lockup_investigation"
SUCCESS_DURATION=$((24 * 60 * 60))  # 24 hours in seconds

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# TTS announcement function
announce() {
    local message="$1"

    # Try spd-say first (speech-dispatcher)
    if command -v spd-say &> /dev/null; then
        spd-say "$message" 2>/dev/null &
        return
    fi

    # Fall back to espeak
    if command -v espeak &> /dev/null; then
        espeak "$message" 2>/dev/null &
        return
    fi

    # Fall back to festival
    if command -v festival &> /dev/null; then
        echo "$message" | festival --tts 2>/dev/null &
        return
    fi

    # WSL: Use PowerShell to invoke Windows SAPI
    if command -v powershell.exe &> /dev/null; then
        powershell.exe -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('$message')" 2>/dev/null &
        return
    fi

    # No TTS available - silent
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    DEVICES=("$@")
else
    DEVICES=("${DEFAULT_DEVICES[@]}")
fi

# State tracking (associative arrays)
declare -A DEVICE_START_TIME
declare -A DEVICE_LOCKUP_COUNT
declare -A DEVICE_LAST_LOOP_COUNT

# Create timestamped log directory for this session
SESSION_START=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$LOG_BASE_DIR/session_$SESSION_START"
mkdir -p "$LOG_DIR"

# Log function with timestamp
log_msg() {
    local level="${2:-INFO}"
    local color=""
    case $level in
        ERROR) color=$RED ;;
        WARN)  color=$YELLOW ;;
        OK)    color=$GREEN ;;
        INFO)  color=$BLUE ;;
        *)     color=$NC ;;
    esac
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $1${NC}" | tee -a "$LOG_DIR/monitor.log"
}

# Run loopstatus via expect on remote device
run_loopstatus_remote() {
    local device=$1

    # Use the deployed expect wrapper
    # Create expect script inline and run on target
    sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "root@$device" '/usr/qk/etc/sv/FC-1/expect/bin/expect-wrapper -c "
set timeout 10
log_user 1
spawn microcom /usr/qk/etc/sv/FC-1/console
sleep 0.3
send \"\\r\"
expect {
    \"app>\" { }
    \">\" {
        send \"app\\r\"
        expect \"app>\"
    }
    timeout {
        send \"\\r\"
        expect {
            \"app>\" { }
            \">\" {
                send \"app\\r\"
                expect \"app>\"
            }
        }
    }
}
send \"loopstatus\\r\"
set timeout 20
expect \"app>\"
send \"\\x18\"
expect eof
"' 2>&1
}

# Check if device is locked up
check_device() {
    local device=$1
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_file="$LOG_DIR/${device}_${timestamp}_loopstatus.txt"

    log_msg "Checking device $device..." "INFO"

    # Execute loopstatus command via SSH+expect
    local output
    output=$(run_loopstatus_remote "$device" 2>&1)
    local exit_code=$?

    # Save raw output
    echo "$output" > "$output_file"

    # Check for lockup indicators
    if echo "$output" | grep -q "BLOCKING IN:"; then
        log_msg "*** LOCKUP DETECTED on $device - BLOCKING IN detected ***" "ERROR"
        local short_ip="${device##*.}"
        announce "LOCKUP DETECTED on device $short_ip"
        return 1
    fi

    if echo "$output" | grep -q "WARNING: Handler stuck"; then
        log_msg "*** LOCKUP DETECTED on $device - Handler stuck ***" "ERROR"
        local short_ip="${device##*.}"
        announce "LOCKUP DETECTED on device $short_ip"
        return 1
    fi

    # Check if we got valid output and extract loop count
    if echo "$output" | grep -q "Loop Executions:"; then
        local loop_count=$(echo "$output" | grep "Loop Executions:" | awk '{print $NF}')
        local prev_count=${DEVICE_LAST_LOOP_COUNT[$device]:-0}

        # If loop count hasn't changed, might be stuck
        if [ "$loop_count" -eq "$prev_count" ] && [ "$prev_count" -gt 0 ]; then
            log_msg "WARNING: Loop count unchanged on $device (still $loop_count) - possible lockup" "WARN"
            # Don't return lockup yet, give it another check
        fi

        DEVICE_LAST_LOOP_COUNT[$device]=$loop_count
        log_msg "Device $device is healthy (loop count: $loop_count)" "OK"
        local short_ip="${device##*.}"
        announce "Device $short_ip healthy, $loop_count loops"
        return 0
    fi

    # Connection issue or other problem
    log_msg "WARNING: Could not get valid status from $device (exit=$exit_code)" "WARN"
    echo "Raw output:" >> "$output_file"
    echo "$output" >> "$output_file"
    return 2
}

# Download logs from device
download_logs() {
    local device=$1
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local device_log_dir="$LOG_DIR/lockup_${device}_${timestamp}"

    mkdir -p "$device_log_dir"
    log_msg "Downloading logs from $device to $device_log_dir" "INFO"

    # Download application log
    sshpass -p "$SSH_PASS" scp -P "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "root@$device:/var/log/fc-1.log" "$device_log_dir/" 2>/dev/null && \
        log_msg "  Downloaded fc-1.log" "OK" || \
        log_msg "  Failed to download fc-1.log" "WARN"

    # Download service log
    sshpass -p "$SSH_PASS" scp -P "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "root@$device:/var/log/FC-1/current" "$device_log_dir/service.log" 2>/dev/null && \
        log_msg "  Downloaded service.log" "OK" || \
        log_msg "  Failed to download service.log" "WARN"

    # Get process info before restart
    local pid
    pid=$(sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "root@$device" 'pidof FC-1' 2>/dev/null)

    if [ -n "$pid" ]; then
        sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no \
            "root@$device" "cat /proc/$pid/status 2>/dev/null" \
            > "$device_log_dir/process_status.txt" 2>/dev/null && \
            log_msg "  Downloaded process status (PID=$pid)" "OK"

        sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no \
            "root@$device" "cat /proc/$pid/stack 2>/dev/null" \
            > "$device_log_dir/process_stack.txt" 2>/dev/null && \
            log_msg "  Downloaded process stack" "OK"

        sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no \
            "root@$device" "cat /proc/$pid/maps 2>/dev/null" \
            > "$device_log_dir/process_maps.txt" 2>/dev/null
    fi

    # Get memory info
    sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "root@$device" 'cat /proc/meminfo' \
        > "$device_log_dir/meminfo.txt" 2>/dev/null && \
        log_msg "  Downloaded meminfo" "OK"

    # Get loopstatus output (might have useful info even if stuck)
    sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "root@$device" 'timeout 5 microcom -s 115200 /usr/qk/etc/sv/FC-1/console' \
        < <(echo -e "\napp: loopstatus\n") \
        > "$device_log_dir/loopstatus_at_lockup.txt" 2>/dev/null

    log_msg "Logs downloaded to $device_log_dir" "OK"
    echo "$device_log_dir"
}

# Analyze downloaded logs
analyze_lockup() {
    local log_dir=$1
    local report_file="$log_dir/analysis_report.txt"

    log_msg "Analyzing logs in $log_dir..." "INFO"

    {
        echo "=========================================="
        echo "LOCKUP ANALYSIS REPORT"
        echo "Generated: $(date)"
        echo "Log Directory: $log_dir"
        echo "=========================================="
        echo ""

        # Look for CHAIN CORRUPTION messages (our safety counter triggered)
        echo "=== CHAIN CORRUPTION MESSAGES ==="
        if [ -f "$log_dir/fc-1.log" ]; then
            grep -i "CHAIN CORRUPTION" "$log_dir/fc-1.log" 2>/dev/null || echo "None found"
        else
            echo "fc-1.log not available"
        fi
        echo ""

        # Look for MM2 errors
        echo "=== MM2/MEMORY MESSAGES (last 100) ==="
        if [ -f "$log_dir/fc-1.log" ]; then
            grep -i "MM2\|memory\|sector\|chain" "$log_dir/fc-1.log" 2>/dev/null | tail -100 || echo "None found"
        fi
        echo ""

        # Look for upload messages
        echo "=== UPLOAD MESSAGES (last 50) ==="
        if [ -f "$log_dir/fc-1.log" ]; then
            grep -i "upload\|imatrix_upload\|bulk" "$log_dir/fc-1.log" 2>/dev/null | tail -50 || echo "None found"
        fi
        echo ""

        # Look for last normal activity before lockup
        echo "=== LAST 200 LINES OF LOG ==="
        if [ -f "$log_dir/fc-1.log" ]; then
            tail -200 "$log_dir/fc-1.log" 2>/dev/null
        fi
        echo ""

        # Memory state
        echo "=== MEMORY STATE ==="
        if [ -f "$log_dir/meminfo.txt" ]; then
            head -20 "$log_dir/meminfo.txt"
        else
            echo "Not available"
        fi
        echo ""

        # Process state
        echo "=== PROCESS STATE ==="
        if [ -f "$log_dir/process_status.txt" ]; then
            cat "$log_dir/process_status.txt"
        else
            echo "Not available"
        fi
        echo ""

        # Process stack trace
        echo "=== PROCESS STACK ==="
        if [ -f "$log_dir/process_stack.txt" ]; then
            cat "$log_dir/process_stack.txt"
        else
            echo "Not available"
        fi

    } > "$report_file"

    log_msg "Analysis report saved to $report_file" "OK"

    # Print key findings to console
    echo ""
    echo -e "${YELLOW}=== KEY FINDINGS ===${NC}"
    if [ -f "$log_dir/fc-1.log" ]; then
        local chain_errors=$(grep -c "CHAIN CORRUPTION" "$log_dir/fc-1.log" 2>/dev/null || echo "0")
        echo -e "Chain corruption messages: ${chain_errors}"

        if [ "$chain_errors" -gt 0 ]; then
            echo -e "${RED}Chain corruption detected - safety counter working!${NC}"
            grep "CHAIN CORRUPTION" "$log_dir/fc-1.log" | head -5
        else
            echo -e "${YELLOW}No chain corruption logged - lockup may be in different code path${NC}"
        fi
    fi

    # Check process state
    if [ -f "$log_dir/process_status.txt" ]; then
        local state=$(grep "^State:" "$log_dir/process_status.txt" | awk '{print $2}')
        echo -e "Process state at lockup: ${state:-unknown}"
        if [ "$state" = "R" ]; then
            echo -e "${RED}Process was RUNNING (R) - infinite loop confirmed${NC}"
        fi
    fi
    echo ""
}

# Restart device
restart_device() {
    local device=$1
    log_msg "Restarting FC-1 on $device..." "INFO"

    "$FC1_SCRIPT" -d "$device" restart 2>&1 | tee -a "$LOG_DIR/monitor.log"

    sleep 5

    # Verify restart
    "$FC1_SCRIPT" -d "$device" status 2>&1 | tee -a "$LOG_DIR/monitor.log"

    # Reset tracking for this device
    DEVICE_START_TIME[$device]=$(date +%s)
    DEVICE_LAST_LOOP_COUNT[$device]=0

    log_msg "Device $device restarted" "OK"
}

# Enable debug logging on device
enable_debug_logging() {
    local device=$1
    log_msg "Enabling enhanced debug logging on $device..." "INFO"

    # Enable memory manager debug (0x4000) and upload debug (0x10)
    "$FC1_SCRIPT" -d "$device" cmd "debug +0x4010" 2>&1 >> "$LOG_DIR/monitor.log"

    log_msg "Debug logging enabled on $device" "OK"
}

# Print status summary
print_status() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}       MONITORING STATUS SUMMARY        ${NC}"
    echo -e "${BLUE}========================================${NC}"

    local now=$(date +%s)
    local script_uptime=$((now - $(stat -c %Y "$LOG_DIR" 2>/dev/null || echo $now)))

    echo -e "Session: $SESSION_START"
    echo -e "Log Directory: $LOG_DIR"
    echo -e "Target: 24 hours without lockup"
    echo ""

    for device in "${DEVICES[@]}"; do
        local start=${DEVICE_START_TIME[$device]:-$now}
        local uptime=$((now - start))
        local uptime_h=$((uptime / 3600))
        local uptime_m=$(((uptime % 3600) / 60))
        local lockups=${DEVICE_LOCKUP_COUNT[$device]:-0}
        local loops=${DEVICE_LAST_LOOP_COUNT[$device]:-0}

        local progress=$((uptime * 100 / SUCCESS_DURATION))
        [ $progress -gt 100 ] && progress=100

        if [ $uptime -ge $SUCCESS_DURATION ]; then
            echo -e "${GREEN}$device: PASSED 24hr [$progress%] (lockups: $lockups, loops: $loops)${NC}"
        else
            echo -e "$device: ${uptime_h}h ${uptime_m}m [$progress%] (lockups: $lockups, loops: $loops)"
        fi
    done
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Cleanup handler
cleanup() {
    echo ""
    log_msg "Monitor interrupted. Cleaning up..." "WARN"
    print_status
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main monitoring loop
main() {
    log_msg "==========================================" "INFO"
    log_msg "Starting Lockup Monitor" "INFO"
    log_msg "Devices: ${DEVICES[*]}" "INFO"
    log_msg "Check Interval: $CHECK_INTERVAL seconds (10 min)" "INFO"
    log_msg "Success Duration: 24 hours" "INFO"
    log_msg "Log Directory: $LOG_DIR" "INFO"
    log_msg "==========================================" "INFO"

    # Initialize device start times
    for device in "${DEVICES[@]}"; do
        DEVICE_START_TIME[$device]=$(date +%s)
        DEVICE_LOCKUP_COUNT[$device]=0
        DEVICE_LAST_LOOP_COUNT[$device]=0

        # Enable debug logging on start
        enable_debug_logging "$device"
    done

    local check_count=0

    while true; do
        check_count=$((check_count + 1))
        log_msg "--- Check #$check_count ---" "INFO"

        local all_passed_24h=true

        for device in "${DEVICES[@]}"; do
            check_device "$device"
            local status=$?

            if [ $status -eq 1 ]; then
                # Lockup detected
                DEVICE_LOCKUP_COUNT[$device]=$((DEVICE_LOCKUP_COUNT[$device] + 1))

                log_msg "Lockup #${DEVICE_LOCKUP_COUNT[$device]} on $device" "ERROR"

                # Download logs
                local lockup_log_dir
                lockup_log_dir=$(download_logs "$device")

                # Analyze logs
                analyze_lockup "$lockup_log_dir"

                # Restart device
                restart_device "$device"

                # Re-enable debug logging
                enable_debug_logging "$device"

                all_passed_24h=false

            elif [ $status -eq 0 ]; then
                # Device healthy - check uptime
                local now=$(date +%s)
                local start=${DEVICE_START_TIME[$device]}
                local uptime=$((now - start))

                if [ $uptime -lt $SUCCESS_DURATION ]; then
                    all_passed_24h=false
                fi
            else
                # Connection issue - don't reset timer
                all_passed_24h=false
            fi
        done

        # Print status summary
        print_status

        # Check if we've achieved 24 hours without lockup on all devices
        if $all_passed_24h; then
            log_msg "==========================================" "OK"
            log_msg "SUCCESS! All devices have run 24 hours without lockup!" "OK"
            log_msg "==========================================" "OK"

            # Final summary
            for device in "${DEVICES[@]}"; do
                log_msg "Device $device: ${DEVICE_LOCKUP_COUNT[$device]} lockups during test" "OK"
            done

            announce "SUCCESS! 24 hour test complete. All devices passed without lockup."

            echo ""
            echo -e "${GREEN}ROOT CAUSE INVESTIGATION COMPLETE${NC}"
            echo -e "${GREEN}The fix is working. Please review logs for any chain corruption warnings.${NC}"
            exit 0
        fi

        # Sleep until next check
        log_msg "Next check in $CHECK_INTERVAL seconds ($(date -d "+$CHECK_INTERVAL seconds" '+%H:%M:%S'))..." "INFO"
        sleep $CHECK_INTERVAL
    done
}

# Check prerequisites
check_prerequisites() {
    if ! command -v sshpass &> /dev/null; then
        echo -e "${RED}ERROR: sshpass not found. Install with: sudo apt-get install sshpass${NC}"
        exit 1
    fi

    if [ ! -x "$FC1_SCRIPT" ]; then
        echo -e "${RED}ERROR: fc1 script not found or not executable: $FC1_SCRIPT${NC}"
        exit 1
    fi
}

# Run
check_prerequisites
main "$@"
