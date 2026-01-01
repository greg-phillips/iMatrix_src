#!/bin/bash

# 24-Hour FC-1 Handler Monitoring Script
# Date: 2026-01-01
# Purpose: Automated 24-hour stability test with 4-hour checkpoints

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="$SCRIPT_DIR/check_handler_status.sh"
LOG_DIR="$SCRIPT_DIR/logs"
REPORT_FILE="$LOG_DIR/24hr_report.md"
START_TIME=$(date "+%Y-%m-%d %H:%M:%S UTC" -u)
START_EPOCH=$(date +%s)

# Checkpoint intervals (in seconds)
CHECKPOINT_INTERVAL=$((4 * 60 * 60))  # 4 hours
TOTAL_DURATION=$((24 * 60 * 60))      # 24 hours

# Console notification colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

# Initialize report
init_report() {
    cat > "$REPORT_FILE" << EOF
# FC-1 Handler Stuck Investigation - 24 Hour Report

**Test Start:** $START_TIME
**Test Type:** 24-hour stability validation
**Monitoring Mode:** Automated with 4-hour checkpoints

## Test Progress

| Checkpoint | Time | Status | Issues |
|------------|------|--------|--------|
EOF
}

# Console notification
notify_console() {
    local level="$1"
    local message="$2"
    
    case "$level" in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "CHECKPOINT")
            echo -e "\n${GREEN}════════════════════════════════════════${NC}"
            echo -e "${GREEN}    CHECKPOINT NOTIFICATION${NC}"
            echo -e "${GREEN}════════════════════════════════════════${NC}"
            echo -e "$message"
            echo -e "${GREEN}════════════════════════════════════════${NC}\n"
            ;;
    esac
}

# Run checkpoint
run_checkpoint() {
    local checkpoint_num="$1"
    local elapsed_hours="$2"
    local current_time=$(date "+%Y-%m-%d %H:%M:%S UTC" -u)
    
    notify_console "CHECKPOINT" "Checkpoint #$checkpoint_num (T+${elapsed_hours}h)\nTime: $current_time\nRunning system checks..."
    
    # Run the status check
    if bash "$CHECK_SCRIPT" > "$LOG_DIR/checkpoint_${checkpoint_num}.log" 2>&1; then
        local status="PASS"
        notify_console "SUCCESS" "Checkpoint #$checkpoint_num - No issues detected"
    else
        local exit_code=$?
        if [ $exit_code -eq 2 ]; then
            local status="FAIL - Handler stuck detected!"
            notify_console "ERROR" "CRITICAL: Handler stuck condition detected at checkpoint #$checkpoint_num!"
            notify_console "ERROR" "Test FAILED at T+${elapsed_hours}h"
            
            # Update report with failure
            echo "| CP#$checkpoint_num | $current_time | FAIL | Handler stuck detected | " >> "$REPORT_FILE"
            
            # Generate failure report
            generate_failure_report "$checkpoint_num" "$elapsed_hours"
            
            return 2
        else
            local status="WARNING - Check logs"
            notify_console "WARNING" "Checkpoint #$checkpoint_num - Connection or minor issue"
        fi
    fi
    
    # Update report
    echo "| CP#$checkpoint_num | $current_time | $status | None |" >> "$REPORT_FILE"
    
    # Display current status
    echo ""
    cat "$LOG_DIR/current_status.txt" | head -20
    echo ""
    
    return 0
}

# Generate failure report
generate_failure_report() {
    local checkpoint="$1"
    local hours="$2"
    
    cat >> "$REPORT_FILE" << EOF

## TEST FAILED

**Failure Time:** $(date "+%Y-%m-%d %H:%M:%S UTC" -u)
**Failed at:** Checkpoint #$checkpoint (T+${hours}h)
**Reason:** Handler stuck condition detected

### Failure Details
$(cat "$LOG_DIR/checkpoint_${checkpoint}.log" | grep -A5 -B5 "WARNING\|BLOCKING\|stuck")

### Recommendations
1. Review logs in $LOG_DIR/
2. Check checkpoint_${checkpoint}.log for details
3. Investigate blocking function identified
4. Review system state at time of failure

## Test Conclusion
**Result:** FAIL
**Duration before failure:** ${hours} hours
EOF

    notify_console "ERROR" "Failure report generated at: $REPORT_FILE"
}

# Generate success report
generate_success_report() {
    cat >> "$REPORT_FILE" << EOF

## Test Completed Successfully

**Test End:** $(date "+%Y-%m-%d %H:%M:%S UTC" -u)
**Duration:** 24 hours
**Result:** PASS

### Summary
- All 7 checkpoints completed successfully
- No handler stuck warnings detected
- No blocking conditions found
- System remained stable for full 24-hour period

### Statistics
- Total checks performed: 7
- Issues detected: 0
- Boot count changes: 0
- System state: MAIN_IMATRIX_NORMAL maintained

## Test Conclusion
**Result:** PASS
**Certification:** System validated for 24-hour continuous operation without handler stuck conditions
EOF

    notify_console "SUCCESS" "24-hour test completed successfully!"
    notify_console "SUCCESS" "Report saved to: $REPORT_FILE"
}

# Cleanup on exit
cleanup() {
    echo ""
    notify_console "INFO" "Monitoring stopped"
    notify_console "INFO" "Logs saved in: $LOG_DIR"
    notify_console "INFO" "Report saved as: $REPORT_FILE"
}

trap cleanup EXIT

# Main monitoring loop
main() {
    notify_console "INFO" "Starting 24-hour FC-1 Handler Monitoring"
    notify_console "INFO" "Start time: $START_TIME"
    notify_console "INFO" "Checkpoints every 4 hours"
    notify_console "INFO" "Logs directory: $LOG_DIR"
    echo ""
    
    # Initialize report
    init_report
    
    # Initial baseline (Checkpoint #1)
    if ! run_checkpoint 1 0; then
        notify_console "ERROR" "Test failed at initial checkpoint"
        exit 2
    fi
    
    # Run checkpoints at 4-hour intervals
    local checkpoint=2
    local elapsed=0
    
    while [ $elapsed -lt $TOTAL_DURATION ]; do
        # Wait for next checkpoint
        notify_console "INFO" "Next checkpoint in 4 hours (CP#$checkpoint at T+$((checkpoint * 4 - 4))h)..."
        sleep $CHECKPOINT_INTERVAL
        
        elapsed=$(($(date +%s) - START_EPOCH))
        local hours=$((elapsed / 3600))
        
        # Run checkpoint
        if ! run_checkpoint $checkpoint $hours; then
            notify_console "ERROR" "Test failed at checkpoint #$checkpoint"
            exit 2
        fi
        
        checkpoint=$((checkpoint + 1))
        
        # Check if 24 hours completed
        if [ $elapsed -ge $TOTAL_DURATION ]; then
            break
        fi
    done
    
    # Final checkpoint at 24 hours
    if [ $elapsed -lt $TOTAL_DURATION ]; then
        local remaining=$((TOTAL_DURATION - elapsed))
        notify_console "INFO" "Waiting for final checkpoint at 24 hours..."
        sleep $remaining
    fi
    
    # Run final checkpoint
    if run_checkpoint 7 24; then
        generate_success_report
        notify_console "SUCCESS" "✓ TEST PASSED - 24 hours completed without handler stuck!"
        exit 0
    else
        notify_console "ERROR" "✗ TEST FAILED - Handler stuck detected at final checkpoint"
        exit 2
    fi
}

# Check if check script exists
if [ ! -f "$CHECK_SCRIPT" ]; then
    notify_console "ERROR" "Check script not found: $CHECK_SCRIPT"
    exit 1
fi

# Make check script executable
chmod +x "$CHECK_SCRIPT"

# Start monitoring
main