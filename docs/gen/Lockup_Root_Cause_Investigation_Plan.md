# Lockup Root Cause Investigation Plan

**Date**: 2026-01-06
**Status**: IN PROGRESS
**Priority**: Critical
**Author**: Claude Code Analysis
**Related**: Lockup_fix_1_plan.md

---

## Objective

Determine the **root cause** of the sector chain corruption that leads to infinite loops in MM2 read operations. The safety counters we added prevent lockups but don't fix the underlying corruption mechanism.

---

## Phase 1: Automated Monitoring System

### 1.1 Monitoring Script

Create `/home/greg/iMatrix/iMatrix_Client/scripts/monitor_lockup.sh`:

```bash
#!/bin/bash
#
# monitor_lockup.sh - Automated lockup detection and log collection
#
# Monitors FC-1 devices every 10 minutes for lockup conditions.
# When lockup detected, downloads logs for root cause analysis.
#

# Configuration
DEVICES=("10.2.0.169" "10.2.0.179")
SSH_PORT="22222"
SSH_PASS="PasswordQConnect"
CHECK_INTERVAL=600  # 10 minutes in seconds
FC1_SCRIPT="/home/greg/iMatrix/iMatrix_Client/scripts/fc1"
LOG_DIR="/home/greg/iMatrix/iMatrix_Client/logs/lockup_investigation"
SUCCESS_DURATION=$((24 * 60 * 60))  # 24 hours in seconds

# State tracking
declare -A DEVICE_START_TIME
declare -A DEVICE_LOCKUP_COUNT

# Initialize
mkdir -p "$LOG_DIR"
SCRIPT_START=$(date +%s)

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/monitor.log"
}

check_device() {
    local device=$1
    local timestamp=$(date +%Y%m%d_%H%M%S)

    log_msg "Checking device $device..."

    # Execute loopstatus command
    local output=$($FC1_SCRIPT -d "$device" cmd "app: loopstatus" 2>&1)
    local exit_code=$?

    # Save raw output
    echo "$output" > "$LOG_DIR/${device}_${timestamp}_loopstatus.txt"

    # Check for lockup indicators
    if echo "$output" | grep -q "BLOCKING IN:"; then
        log_msg "*** LOCKUP DETECTED on $device ***"
        return 1
    fi

    if echo "$output" | grep -q "WARNING: Handler stuck"; then
        log_msg "*** LOCKUP DETECTED on $device (handler stuck) ***"
        return 1
    fi

    # Check if we got valid output
    if echo "$output" | grep -q "Loop Executions:"; then
        log_msg "Device $device is healthy"
        return 0
    fi

    # Connection issue or other problem
    log_msg "WARNING: Could not get valid status from $device"
    return 2
}

download_logs() {
    local device=$1
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local device_log_dir="$LOG_DIR/lockup_${device}_${timestamp}"

    mkdir -p "$device_log_dir"
    log_msg "Downloading logs from $device to $device_log_dir"

    # Download all relevant logs
    sshpass -p "$SSH_PASS" scp -P "$SSH_PORT" -o StrictHostKeyChecking=no \
        "root@$device:/var/log/fc-1.log" "$device_log_dir/" 2>/dev/null

    sshpass -p "$SSH_PASS" scp -P "$SSH_PORT" -o StrictHostKeyChecking=no \
        "root@$device:/var/log/FC-1/current" "$device_log_dir/service.log" 2>/dev/null

    # Get process info before restart
    sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no \
        "root@$device" 'cat /proc/$(pidof FC-1)/status 2>/dev/null' \
        > "$device_log_dir/process_status.txt" 2>/dev/null

    sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no \
        "root@$device" 'cat /proc/$(pidof FC-1)/stack 2>/dev/null' \
        > "$device_log_dir/process_stack.txt" 2>/dev/null

    # Get memory info
    sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no \
        "root@$device" 'cat /proc/meminfo' \
        > "$device_log_dir/meminfo.txt" 2>/dev/null

    log_msg "Logs downloaded to $device_log_dir"
    echo "$device_log_dir"
}

restart_device() {
    local device=$1
    log_msg "Restarting FC-1 on $device..."

    $FC1_SCRIPT -d "$device" restart 2>&1 | tee -a "$LOG_DIR/monitor.log"

    sleep 5

    # Verify restart
    $FC1_SCRIPT -d "$device" status 2>&1 | tee -a "$LOG_DIR/monitor.log"

    # Reset timer for this device
    DEVICE_START_TIME[$device]=$(date +%s)
}

enable_debug_logging() {
    local device=$1
    log_msg "Enabling enhanced debug logging on $device..."

    # Enable memory manager debug (0x4000) and upload debug (0x10)
    $FC1_SCRIPT -d "$device" cmd "debug +0x4010" 2>&1 >> "$LOG_DIR/monitor.log"

    log_msg "Debug logging enabled on $device"
}

analyze_lockup() {
    local log_dir=$1
    local report_file="$log_dir/analysis_report.txt"

    log_msg "Analyzing logs in $log_dir..."

    {
        echo "=========================================="
        echo "LOCKUP ANALYSIS REPORT"
        echo "Generated: $(date)"
        echo "=========================================="
        echo ""

        # Look for CHAIN CORRUPTION messages
        echo "=== CHAIN CORRUPTION MESSAGES ==="
        grep -i "CHAIN CORRUPTION" "$log_dir/fc-1.log" 2>/dev/null || echo "None found"
        echo ""

        # Look for MM2 errors
        echo "=== MM2 ERRORS ==="
        grep -i "MM2\|memory_manager\|sector" "$log_dir/fc-1.log" 2>/dev/null | tail -50 || echo "None found"
        echo ""

        # Look for last normal activity before lockup
        echo "=== LAST 100 LINES BEFORE LOCKUP ==="
        tail -100 "$log_dir/fc-1.log" 2>/dev/null
        echo ""

        # Memory state
        echo "=== MEMORY STATE ==="
        cat "$log_dir/meminfo.txt" 2>/dev/null || echo "Not available"
        echo ""

        # Process state
        echo "=== PROCESS STATE ==="
        cat "$log_dir/process_status.txt" 2>/dev/null || echo "Not available"
        echo ""

        # Process stack trace
        echo "=== PROCESS STACK ==="
        cat "$log_dir/process_stack.txt" 2>/dev/null || echo "Not available"

    } > "$report_file"

    log_msg "Analysis report saved to $report_file"

    # Print key findings
    echo ""
    echo "=== KEY FINDINGS ==="
    grep -i "CHAIN CORRUPTION" "$log_dir/fc-1.log" 2>/dev/null | head -5
}

# Main monitoring loop
main() {
    log_msg "=========================================="
    log_msg "Starting Lockup Monitor"
    log_msg "Devices: ${DEVICES[*]}"
    log_msg "Check Interval: $CHECK_INTERVAL seconds"
    log_msg "Success Duration: $SUCCESS_DURATION seconds (24 hours)"
    log_msg "=========================================="

    # Initialize device start times
    for device in "${DEVICES[@]}"; do
        DEVICE_START_TIME[$device]=$(date +%s)
        DEVICE_LOCKUP_COUNT[$device]=0

        # Enable debug logging on start
        enable_debug_logging "$device"
    done

    local check_count=0

    while true; do
        check_count=$((check_count + 1))
        log_msg "--- Check #$check_count ---"

        local all_healthy=true
        local all_passed_24h=true

        for device in "${DEVICES[@]}"; do
            check_device "$device"
            local status=$?

            if [ $status -eq 1 ]; then
                # Lockup detected
                all_healthy=false
                DEVICE_LOCKUP_COUNT[$device]=$((DEVICE_LOCKUP_COUNT[$device] + 1))

                log_msg "Lockup #${DEVICE_LOCKUP_COUNT[$device]} on $device"

                # Download logs
                local log_dir=$(download_logs "$device")

                # Analyze logs
                analyze_lockup "$log_dir"

                # Restart device
                restart_device "$device"

                # Re-enable debug logging
                enable_debug_logging "$device"

            elif [ $status -eq 0 ]; then
                # Device healthy - check uptime
                local now=$(date +%s)
                local start=${DEVICE_START_TIME[$device]}
                local uptime=$((now - start))

                log_msg "Device $device uptime: $uptime seconds"

                if [ $uptime -lt $SUCCESS_DURATION ]; then
                    all_passed_24h=false
                fi
            else
                # Connection issue
                all_healthy=false
                all_passed_24h=false
            fi
        done

        # Check if we've achieved 24 hours without lockup on all devices
        if $all_passed_24h; then
            log_msg "=========================================="
            log_msg "SUCCESS! All devices have run 24 hours without lockup!"
            log_msg "=========================================="

            # Summary
            for device in "${DEVICES[@]}"; do
                log_msg "Device $device: ${DEVICE_LOCKUP_COUNT[$device]} lockups during test"
            done

            exit 0
        fi

        # Sleep until next check
        log_msg "Next check in $CHECK_INTERVAL seconds..."
        sleep $CHECK_INTERVAL
    done
}

# Run main function
main "$@"
```

### 1.2 Script Installation

```bash
# Make script executable
chmod +x /home/greg/iMatrix/iMatrix_Client/scripts/monitor_lockup.sh

# Create log directory
mkdir -p /home/greg/iMatrix/iMatrix_Client/logs/lockup_investigation

# Start monitoring in background with logging
nohup /home/greg/iMatrix/iMatrix_Client/scripts/monitor_lockup.sh \
    > /home/greg/iMatrix/iMatrix_Client/logs/lockup_investigation/monitor_stdout.log 2>&1 &

# Or run in foreground to watch
/home/greg/iMatrix/iMatrix_Client/scripts/monitor_lockup.sh
```

---

## Phase 2: Root Cause Investigation

### 2.1 Data Collection Points

When a lockup is detected, the script collects:

| Data | Purpose |
|------|---------|
| `/var/log/fc-1.log` | Application logs - look for MM2 operations |
| `/var/log/FC-1/current` | Service logs - startup issues |
| `/proc/PID/status` | Process state (R=running in infinite loop) |
| `/proc/PID/stack` | Kernel stack trace |
| `/proc/meminfo` | Memory pressure at time of lockup |

### 2.2 Log Patterns to Search For (Root Cause Indicators)

**CRITICAL**: When analyzing logs, search for these specific patterns that indicate root cause:

#### Pattern 1: Chain Corruption Safety Counter Triggered
```bash
grep -i "CHAIN CORRUPTION" fc-1.log
```
- **If found**: Our safety counters are working. Note which function reported it.
- **Log example**: `read_bulk: CHAIN CORRUPTION - exceeded max sectors (256) sensor=CAN_0x123`
- **Root cause clue**: This tells us WHICH code path was corrupted

#### Pattern 2: Disk Spillover Activity
```bash
grep -i "disk\|spill\|spool" fc-1.log
```
- **Look for**: Operations happening just before lockup
- **Root cause clue**: Corruption often occurs during disk spillover under memory pressure

#### Pattern 3: Concurrent Sensor Operations
```bash
grep -i "sensor_lock\|mutex" fc-1.log
```
- **Look for**: Multiple sensors being accessed simultaneously
- **Root cause clue**: Race condition between different sensor chains

#### Pattern 4: Sector Allocation/Deallocation
```bash
grep -i "alloc_sector\|free_sector\|sector_chain" fc-1.log
```
- **Look for**: Sector operations just before lockup
- **Root cause clue**: Chain corruption likely happens here

#### Pattern 5: Memory Pressure
```bash
grep -i "RAM\|memory\|80%\|90%" fc-1.log
```
- **Look for**: High RAM utilization triggering spillover
- **Root cause clue**: Corruption correlates with memory pressure

#### Pattern 6: Upload Operations
```bash
grep -i "imatrix_upload\|bulk_read\|pending" fc-1.log
```
- **Look for**: Upload operations in progress
- **Root cause clue**: Upload reads chains while writes continue

### 2.3 Analysis Questions

For each lockup, determine:

1. **Which loop caused the lockup?**
   - Did we log "CHAIN CORRUPTION"? Which function?
   - If no corruption log, the loop may be in a different file

2. **What was the memory state?**
   - RAM utilization percentage
   - Was disk spillover active?

3. **What operations preceded the lockup?**
   - Heavy CAN bus activity?
   - Upload in progress?
   - Disk spillover operations?

4. **When did it occur?**
   - Time since boot
   - Time of day (patterns?)

### 2.3 Root Cause Hypotheses

Based on previous investigation, likely root causes:

| Hypothesis | Evidence Needed | Mitigation |
|------------|-----------------|------------|
| **Race condition in disk spillover** | Lockup during spill, logs show disk operations | Add mutex protection to `free_sector()` |
| **Sector reuse before chain update** | Chain points to freed sector | Add generation counter to sectors |
| **Concurrent write/read corruption** | Multiple sensors active simultaneously | Serialize sector allocation |
| **Integer overflow in chain pointer** | Sector ID > total_sectors | Add bounds checking |
| **Memory corruption from buffer overflow** | Random sector IDs in chain | Memory sanitizer testing |

---

## Phase 3: Enhanced Debugging

### 3.1 Add Trace Logging

If lockups continue, add detailed trace logging to track chain operations:

**File**: `iMatrix/cs_ctrl/mm2_pool.c`

```c
// Add to sector chain operations
#define TRACE_CHAIN_OP(op, sector, prev, next) \
    LOG_MM2_DEBUG("CHAIN_TRACE: %s sector=%u prev=%u next=%u", \
                  op, sector, prev, next)
```

Track these operations:
- `alloc_sector()` - when new sector added to chain
- `free_sector()` - when sector removed from chain
- `get_next_sector_in_chain()` - chain traversal
- Chain head/tail updates

### 3.2 Chain Integrity Validation

Add periodic chain validation:

```c
/**
 * @brief Validate all sensor chains for corruption
 * @return Number of corrupted chains found
 */
uint32_t mm2_validate_all_chains(void) {
    uint32_t corrupted = 0;

    for (uint16_t i = 0; i < MAX_NO_CONTROL_SENSOR; i++) {
        control_sensor_data_t *csd = get_control_sensor_data(i);
        if (csd && csd->mmcb.ram_start_sector_id != NULL_SECTOR_ID) {
            if (!mm2_validate_sensor_chain(csd, "periodic_check")) {
                corrupted++;
            }
        }
    }

    return corrupted;
}
```

Call this periodically (e.g., every 1000 main loop iterations).

---

## Phase 4: Iterative Fix Process

### 4.1 Fix Development Workflow

For each root cause identified:

1. **Document finding** in this plan
2. **Create hypothesis** for fix
3. **Implement fix** in feature branch
4. **Build and deploy** to test devices
5. **Monitor for 24 hours**
6. **If lockup occurs**: Return to Phase 2 with new data
7. **If 24 hours pass**: Fix verified, document and merge

### 4.2 Fix Tracking Table

| Fix # | Date | Root Cause Found | Fix Applied | Result | Duration |
|-------|------|------------------|-------------|--------|----------|
| v1 | 2026-01-06 | Loop at line 882 | Safety counter | Failed (11 min) | - |
| v2 | 2026-01-06 | All loops vulnerable | Safety counters to all 7 loops | Testing | - |
| v3 | TBD | TBD | TBD | TBD | - |

---

## Phase 5: Success Criteria

### Monitoring Complete When:

1. **Both devices** run for **24 consecutive hours** without lockup
2. **No CHAIN CORRUPTION** messages logged during that period
3. **Normal operation** (uploads, CAN processing) occurs throughout

### Root Cause Identified When:

1. We can **explain** exactly how corruption occurs
2. We have **logs showing** the sequence of events
3. We have a **fix that addresses** the mechanism, not just the symptom

---

## Implementation Todo List

- [ ] Create monitoring script `/home/greg/iMatrix/iMatrix_Client/scripts/monitor_lockup.sh`
- [ ] Create log collection directory
- [ ] Start monitoring both devices
- [ ] When lockup occurs:
  - [ ] Download and analyze logs
  - [ ] Identify which loop (if any) triggered safety counter
  - [ ] Identify operations before lockup
  - [ ] Form hypothesis for root cause
  - [ ] Implement targeted fix
  - [ ] Build, deploy, restart monitoring
- [ ] Continue until 24 hours achieved
- [ ] Document root cause and final fix

---

## Quick Start Commands

```bash
# Start monitoring
/home/greg/iMatrix/iMatrix_Client/scripts/monitor_lockup.sh

# Check monitoring status
tail -f /home/greg/iMatrix/iMatrix_Client/logs/lockup_investigation/monitor.log

# Manual loopstatus check
/home/greg/iMatrix/iMatrix_Client/scripts/fc1 -d 10.2.0.169 cmd "app: loopstatus"
/home/greg/iMatrix/iMatrix_Client/scripts/fc1 -d 10.2.0.179 cmd "app: loopstatus"

# Download logs manually
sshpass -p 'PasswordQConnect' scp -P 22222 root@10.2.0.169:/var/log/fc-1.log ./logs/

# Enable debug on device
/home/greg/iMatrix/iMatrix_Client/scripts/fc1 -d 10.2.0.169 cmd "debug +0x4010"
```

---

**Plan Created By:** Claude Code
**Generated:** 2026-01-06
