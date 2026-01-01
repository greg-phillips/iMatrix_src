#!/bin/bash

# FC-1 Handler Status Check Script
# Date: 2026-01-01
# Purpose: Check for handler stuck conditions in FC-1

TARGET_HOST="192.168.7.1"
TARGET_PORT="22222"
TARGET_USER="root"
TARGET_PASS="PasswordQConnect"
LOG_DIR="/home/greg/iMatrix/iMatrix_Client/monitoring/logs"
CHECKPOINT_FILE="$LOG_DIR/checkpoints.log"
STATUS_FILE="$LOG_DIR/current_status.txt"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to run SSH command
run_ssh_cmd() {
    sshpass -p "$TARGET_PASS" ssh -p "$TARGET_PORT" \
        -o StrictHostKeyChecking=accept-new \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 \
        "$TARGET_USER@$TARGET_HOST" "$1" 2>/dev/null
}

# Function to get current timestamp
get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S UTC" -u
}

# Function to check system status
check_system_status() {
    echo "=== FC-1 Handler Status Check ===" 
    echo "Timestamp: $(get_timestamp)"
    echo ""
    
    # Get uptime
    UPTIME=$(run_ssh_cmd "uptime")
    echo "Uptime: $UPTIME"
    
    # Get FC-1 PID
    FC1_PID=$(run_ssh_cmd "pidof FC-1")
    if [ -z "$FC1_PID" ]; then
        echo "WARNING: FC-1 is not running!"
        return 1
    fi
    echo "FC-1 PID: $FC1_PID"
    
    # Get memory info
    MEMORY=$(run_ssh_cmd "free | grep Mem | awk '{print \"Used: \" \$3 \"/\" \$2 \" (\" int(\$3*100/\$2) \"%)\"}'")
    echo "Memory: $MEMORY"
    
    # Get boot count if available
    BOOT_COUNT=$(run_ssh_cmd "cat /sys/class/misc/bootcount/count 2>/dev/null || echo 'N/A'")
    echo "Boot Count: $BOOT_COUNT"
    
    # Check for handler stuck warnings in logs
    echo ""
    echo "Checking for handler stuck warnings..."
    STUCK_WARNINGS=$(run_ssh_cmd "grep -c 'WARNING: Handler stuck' /var/log/fc-1/*.log 2>/dev/null || echo '0'")
    echo "Handler stuck warnings found: $STUCK_WARNINGS"
    
    # Check for blocking messages
    BLOCKING_MSG=$(run_ssh_cmd "grep -c 'BLOCKING IN:' /var/log/fc-1/*.log 2>/dev/null || echo '0'")
    echo "Blocking messages found: $BLOCKING_MSG"
    
    # Return status
    if [ "$STUCK_WARNINGS" != "0" ] || [ "$BLOCKING_MSG" != "0" ]; then
        echo ""
        echo "*** FAILURE DETECTED ***"
        echo "Handler stuck or blocking condition found!"
        return 2
    fi
    
    echo ""
    echo "Status: NORMAL - No issues detected"
    return 0
}

# Function to interact with CLI via expect/minicom
check_cli_status() {
    echo ""
    echo "=== CLI Status Check ===" 
    
    # Create expect script for CLI interaction
    cat > /tmp/cli_check.exp << 'EOF'
#!/usr/bin/expect -f

set timeout 10
set host "192.168.7.1"
set port "22222"
set user "root"
set pass "PasswordQConnect"

spawn sshpass -p $pass ssh -p $port $user@$host "minicom"

# Wait for CLI prompt
expect {
    ">" { send "s\r" }
    timeout { 
        send_user "Timeout waiting for CLI prompt\n"
        exit 1
    }
}

# Check main state
expect {
    "MAIN_IMATRIX_NORMAL" { 
        send_user "\nMain State: NORMAL\n" 
    }
    timeout { 
        send_user "\nWarning: Unexpected main state\n"
    }
}

# Check threads
send "threads\r"
expect {
    "WARNING: Handler stuck" {
        send_user "\n*** HANDLER STUCK DETECTED ***\n"
        exit 2
    }
    ">" {
        send_user "Threads: No warnings\n"
    }
    timeout {
        send_user "Timeout checking threads\n"
    }
}

# Switch to app mode
send "app\r"
expect {
    "app>" { send "loopstatus\r" }
    timeout {
        send_user "Failed to enter app mode\n"
        exit 1
    }
}

# Check loop status
expect {
    "app>" {
        send_user "Loop Status: Checked\n"
    }
    timeout {
        send_user "Timeout checking loop status\n"
    }
}

# Exit
send "exit\r"
expect ">"
send "\003"

EOF
    
    # Make expect script executable and run it
    chmod +x /tmp/cli_check.exp
    if command -v expect > /dev/null 2>&1; then
        /tmp/cli_check.exp 2>/dev/null || true
    else
        echo "Note: 'expect' not installed - skipping interactive CLI check"
        echo "Install with: sudo apt-get install expect"
    fi
    
    rm -f /tmp/cli_check.exp
}

# Main execution
echo "Starting FC-1 Handler Monitoring Check"
echo "======================================"
echo ""

# Save status to file
{
    check_system_status
    STATUS=$?
    
    # Try CLI check if system is running
    if [ $STATUS -eq 0 ]; then
        check_cli_status
    fi
    
    echo ""
    echo "======================================"
    
    # Return appropriate exit code
    exit $STATUS
} | tee "$STATUS_FILE"

# Append to checkpoint log
echo "--- Checkpoint at $(get_timestamp) ---" >> "$CHECKPOINT_FILE"
cat "$STATUS_FILE" >> "$CHECKPOINT_FILE"
echo "" >> "$CHECKPOINT_FILE"

# Check exit status
EXIT_CODE=${PIPESTATUS[0]}
if [ $EXIT_CODE -eq 2 ]; then
    echo "*** TEST FAILED - Handler stuck detected! ***"
    exit 2
elif [ $EXIT_CODE -eq 1 ]; then
    echo "Warning: FC-1 not running or connection issue"
    exit 1
else
    echo "Check completed successfully"
    exit 0
fi