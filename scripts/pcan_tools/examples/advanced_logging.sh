#!/bin/bash
#
# Advanced PCAN TRC Logging Examples
# These examples demonstrate advanced usage patterns and integration scenarios
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="${SCRIPT_DIR}/../pcan_trc_logger.py"
LOG_DIR="${SCRIPT_DIR}/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "============================================"
echo "PCAN TRC Logger - Advanced Usage Examples"
echo "============================================"
echo ""

# Function to check if logger is installed
check_logger() {
    if [ ! -f "$LOGGER" ]; then
        echo "Error: PCAN TRC Logger not found at $LOGGER"
        exit 1
    fi
    
    if ! python3 -c "import can" 2>/dev/null; then
        echo "Error: python-can not installed. Run: pip install python-can"
        exit 1
    fi
}

# Example 1: Continuous logging with automatic file rotation
continuous_logging_with_rotation() {
    echo "Example 1: Continuous logging with file rotation"
    echo "Starting continuous logging with hourly rotation..."
    
    while true; do
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        OUTPUT_FILE="${LOG_DIR}/continuous_${TIMESTAMP}.trc"
        
        echo "Logging to: $OUTPUT_FILE"
        timeout 3600 $LOGGER --bitrate 500000 --outfile "$OUTPUT_FILE" || true
        
        # Optional: Compress old logs
        find "$LOG_DIR" -name "*.trc" -mmin +60 -exec gzip {} \;
    done
}

# Example 2: Multi-channel logging (requires multiple adapters)
multi_channel_logging() {
    echo "Example 2: Multi-channel simultaneous logging"
    echo "Starting loggers on multiple channels..."
    
    # Start logger on channel 1
    $LOGGER --bitrate 500000 --channel PCAN_USBBUS1 \
            --outfile "${LOG_DIR}/channel1.trc" &
    PID1=$!
    
    # Start logger on channel 2
    $LOGGER --bitrate 250000 --channel PCAN_USBBUS2 \
            --outfile "${LOG_DIR}/channel2.trc" &
    PID2=$!
    
    echo "Logging on channels 1 and 2 (PIDs: $PID1, $PID2)"
    echo "Press Ctrl+C to stop both loggers"
    
    # Wait for interrupt
    trap "kill $PID1 $PID2; exit" INT
    wait
}

# Example 3: Triggered logging based on system events
event_triggered_logging() {
    echo "Example 3: Event-triggered logging"
    echo "Monitoring for trigger file to start/stop logging..."
    
    TRIGGER_FILE="/tmp/start_can_logging"
    
    while true; do
        if [ -f "$TRIGGER_FILE" ]; then
            echo "Trigger detected! Starting CAN logging..."
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            OUTPUT_FILE="${LOG_DIR}/triggered_${TIMESTAMP}.trc"
            
            $LOGGER --bitrate 500000 --outfile "$OUTPUT_FILE" &
            LOGGER_PID=$!
            
            # Wait for stop trigger
            while [ -f "$TRIGGER_FILE" ]; do
                sleep 1
            done
            
            echo "Stop trigger detected! Stopping CAN logging..."
            kill -INT $LOGGER_PID
            wait $LOGGER_PID
        fi
        sleep 1
    done
}

# Example 4: Performance testing with statistics
performance_test() {
    echo "Example 4: Performance testing with statistics"
    echo "Running 60-second performance test..."
    
    OUTPUT_FILE="${LOG_DIR}/performance_test.trc"
    
    # Run with statistics every 5 seconds
    $LOGGER --bitrate 1000000 \
            --outfile "$OUTPUT_FILE" \
            --duration 60 \
            --stats-interval 5 \
            -v
    
    # Analyze the output file
    if [ -f "$OUTPUT_FILE" ]; then
        echo ""
        echo "Performance Test Results:"
        echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
        echo "Line count: $(wc -l < "$OUTPUT_FILE")"
        
        # Calculate average message rate (approximate)
        LINES=$(wc -l < "$OUTPUT_FILE")
        # Subtract header lines (approximately 10)
        MESSAGES=$((LINES - 10))
        RATE=$((MESSAGES / 60))
        echo "Approximate message rate: $RATE msg/s"
    fi
}

# Example 5: Automated test sequence logging
test_sequence_logging() {
    echo "Example 5: Automated test sequence with logging"
    echo "Running test sequence with CAN logging..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    TEST_NAME="test_sequence_${TIMESTAMP}"
    OUTPUT_FILE="${LOG_DIR}/${TEST_NAME}.trc"
    REPORT_FILE="${LOG_DIR}/${TEST_NAME}_report.txt"
    
    # Start logging in background
    $LOGGER --bitrate 500000 --outfile "$OUTPUT_FILE" &
    LOGGER_PID=$!
    
    # Wait for logger to initialize
    sleep 2
    
    # Run test sequence
    {
        echo "Test Sequence Report"
        echo "===================="
        echo "Start time: $(date)"
        echo ""
        
        echo "Step 1: Initialization"
        # Your initialization commands here
        sleep 5
        
        echo "Step 2: Normal operation test"
        # Your test commands here
        sleep 10
        
        echo "Step 3: Stress test"
        # Your stress test commands here
        sleep 10
        
        echo "Step 4: Shutdown sequence"
        # Your shutdown commands here
        sleep 5
        
        echo ""
        echo "End time: $(date)"
        echo "Test completed successfully"
    } | tee "$REPORT_FILE"
    
    # Stop logging
    kill -INT $LOGGER_PID
    wait $LOGGER_PID
    
    echo ""
    echo "Test complete!"
    echo "CAN log saved to: $OUTPUT_FILE"
    echo "Test report saved to: $REPORT_FILE"
}

# Example 6: Logging with data filtering (post-processing)
filtered_logging() {
    echo "Example 6: Logging with post-processing filter"
    echo "Logging all data, then filtering for specific CAN IDs..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    RAW_FILE="${LOG_DIR}/raw_${TIMESTAMP}.trc"
    FILTERED_FILE="${LOG_DIR}/filtered_${TIMESTAMP}.trc"
    
    # Log for 30 seconds
    $LOGGER --bitrate 500000 --outfile "$RAW_FILE" --duration 30
    
    # Filter for specific CAN IDs (example: 0x100-0x1FF)
    echo "Filtering for CAN IDs 0x100-0x1FF..."
    grep -E "0x1[0-9A-F][0-9A-F]" "$RAW_FILE" > "$FILTERED_FILE" || true
    
    # Add header to filtered file
    head -n 10 "$RAW_FILE" > "${FILTERED_FILE}.tmp"
    cat "$FILTERED_FILE" >> "${FILTERED_FILE}.tmp"
    mv "${FILTERED_FILE}.tmp" "$FILTERED_FILE"
    
    echo "Original file: $RAW_FILE ($(wc -l < "$RAW_FILE") lines)"
    echo "Filtered file: $FILTERED_FILE ($(wc -l < "$FILTERED_FILE") lines)"
}

# Example 7: Logging with system monitoring
system_monitoring() {
    echo "Example 7: CAN logging with system monitoring"
    echo "Logging CAN data while monitoring system resources..."
    
    OUTPUT_FILE="${LOG_DIR}/monitored_session.trc"
    STATS_FILE="${LOG_DIR}/system_stats.txt"
    
    # Start logger
    $LOGGER --bitrate 500000 --outfile "$OUTPUT_FILE" &
    LOGGER_PID=$!
    
    # Monitor system resources
    {
        echo "Time,CPU%,Memory%,Disk_IO"
        while kill -0 $LOGGER_PID 2>/dev/null; do
            TIMESTAMP=$(date +%H:%M:%S)
            CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
            MEM=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
            IO=$(iostat -d 1 2 | tail -n2 | awk '{print $3}')
            
            echo "${TIMESTAMP},${CPU},${MEM},${IO}"
            sleep 5
        done
    } | tee "$STATS_FILE" &
    MONITOR_PID=$!
    
    # Run for 60 seconds
    sleep 60
    
    # Stop both processes
    kill -INT $LOGGER_PID
    kill $MONITOR_PID 2>/dev/null
    wait
    
    echo ""
    echo "Logging complete!"
    echo "CAN log: $OUTPUT_FILE"
    echo "System stats: $STATS_FILE"
}

# Main menu
show_menu() {
    echo ""
    echo "Select an example to run:"
    echo "1) Continuous logging with rotation"
    echo "2) Multi-channel logging"
    echo "3) Event-triggered logging"
    echo "4) Performance test"
    echo "5) Test sequence logging"
    echo "6) Filtered logging"
    echo "7) System monitoring"
    echo "q) Quit"
    echo ""
    read -p "Enter choice: " choice
    
    case $choice in
        1) continuous_logging_with_rotation ;;
        2) multi_channel_logging ;;
        3) event_triggered_logging ;;
        4) performance_test ;;
        5) test_sequence_logging ;;
        6) filtered_logging ;;
        7) system_monitoring ;;
        q) exit 0 ;;
        *) echo "Invalid choice"; show_menu ;;
    esac
}

# Check prerequisites
check_logger

# Show menu if no arguments, otherwise run specific example
if [ $# -eq 0 ]; then
    show_menu
else
    case $1 in
        continuous) continuous_logging_with_rotation ;;
        multi) multi_channel_logging ;;
        trigger) event_triggered_logging ;;
        performance) performance_test ;;
        test) test_sequence_logging ;;
        filter) filtered_logging ;;
        monitor) system_monitoring ;;
        *) echo "Unknown example: $1"; show_menu ;;
    esac
fi