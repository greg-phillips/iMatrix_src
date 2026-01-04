# Debug Initialization Test and Validation Plan

**Date**: 2026-01-03
**Related Document**: debug_initialization_plan.md
**Author**: Claude Code
**Status**: READY FOR TESTING

---

## Overview

This document outlines the test and validation procedures for verifying that the startup printf/imx_printf to imx_cli_log_printf conversion is working correctly.

## Test Objectives

1. Verify all startup messages appear in the filesystem log file (`/var/log/fc-1.log`)
2. Verify messages include timestamps
3. Verify no segmentation faults during startup
4. Verify messages still appear on console output
5. Verify no regression in system functionality

---

## Prerequisites

### Hardware/Environment
- QConnect gateway device (or development Linux system)
- Network connectivity to gateway (192.168.7.1)
- Development host with fc1 script

### Software
- Updated FC-1 binary with debug_initialization changes
- sshpass installed on development host (`sudo apt-get install sshpass`)

### Tools Location
```bash
cd /home/greg/iMatrix/iMatrix_Client/scripts
```

---

## Test Procedures

### Test 1: Pre-Deployment Log Baseline

**Purpose**: Capture current state before deploying changes

```bash
# Capture current service status
./fc1 status > baseline_status.txt

# Capture current log tail
./fc1 ssh "tail -100 /var/log/fc-1.log" > baseline_log.txt

# Note the current boot count
./fc1 cmd "c" | grep boot_count
```

**Expected Result**: Baseline captured for comparison

---

### Test 2: Deploy Updated Binary

**Purpose**: Deploy the modified FC-1 binary

```bash
# Stop service, push binary, start service
./fc1 stop
./fc1 push -run

# Wait for startup to complete (10-15 seconds)
sleep 15

# Verify service is running
./fc1 status
```

**Expected Result**:
- Service status shows "run: FC-1"
- No crash or restart loops

---

### Test 3: Verify Startup Messages in Filesystem Log

**Purpose**: Confirm all converted messages appear in /var/log/fc-1.log with timestamps

```bash
# View recent log entries
./fc1 ssh "tail -200 /var/log/fc-1.log" > startup_log.txt

# Search for specific startup messages
./fc1 ssh "grep -i 'Configuration Loaded' /var/log/fc-1.log | tail -5"
./fc1 ssh "grep -i 'Core System Initialized' /var/log/fc-1.log | tail -5"
./fc1 ssh "grep -i 'Initialization Complete' /var/log/fc-1.log | tail -5"
./fc1 ssh "grep -i 'Command Line Processor' /var/log/fc-1.log | tail -5"
./fc1 ssh "grep -i 'memory tracking initialized' /var/log/fc-1.log | tail -5"
./fc1 ssh "grep -i 'lockfile' /var/log/fc-1.log | tail -5"
```

**Expected Messages in Log (with timestamps)**:
```
[HH:MM:SS.mmm] Startup looking for lockfile: /var/lock/fc-1.lock
[HH:MM:SS.mmm] iMatrix Configuration size: XXXX
[HH:MM:SS.mmm] Configuration Loaded
[HH:MM:SS.mmm] Core System Initialized
[HH:MM:SS.mmm] iMatrix memory tracking initialized
[HH:MM:SS.mmm] Setting up <ProductName>, Product ID: XXXX, Serial Number: XXXX
[HH:MM:SS.mmm] Initializing Controls & Sensors
[HH:MM:SS.mmm] Initializing Location System
[HH:MM:SS.mmm] Command Line Processor
[HH:MM:SS.mmm] Initialization Complete, Thing will run in <mode> mode
```

**Validation Criteria**:
- [ ] All messages have timestamp prefix `[HH:MM:SS.mmm]`
- [ ] Messages appear in chronological order
- [ ] No duplicate messages from old printf calls

---

### Test 4: Verify No Segmentation Fault

**Purpose**: Confirm the segfault issue is resolved

```bash
# Check for crash evidence
./fc1 ssh "dmesg | grep -i segfault | tail -10"

# Check service status (should show stable uptime)
./fc1 status

# Verify boot count increment (should be +1 from baseline)
./fc1 cmd "c" | grep boot_count

# Force a restart and watch for crash
./fc1 restart
sleep 20
./fc1 status
```

**Expected Result**:
- No segfault messages in dmesg
- Service uptime increases (not restarting)
- Boot count increases by exactly 1 per intentional restart

---

### Test 5: Console Output Verification (Optional - requires console access)

**Purpose**: Verify messages still appear on console

```bash
# SSH to gateway and connect to console
./fc1 ssh
microcom /usr/qk/etc/sv/FC-1/console

# In another terminal, restart service to see startup messages
./fc1 restart
```

**Expected Result**: Startup messages visible on console

---

### Test 6: Telnet CLI Functionality

**Purpose**: Verify CLI is still accessible and functional

```bash
# Test basic CLI commands
./fc1 cmd "?"              # Help should display
./fc1 cmd "v"              # Version should display
./fc1 cmd "s"              # Status should display
./fc1 cmd "ms"             # Memory stats should display
./fc1 cmd "debug ?"        # Debug flags should list
```

**Expected Result**: All commands respond correctly

---

### Test 7: Debug Flag Functionality

**Purpose**: Verify debug flag system still works with new logging

```bash
# Enable debug and verify logging
./fc1 cmd "debug on"
./fc1 cmd "debug 0x800"    # DEBUGS_FOR_APPLICATION_START (bit 11)

# Trigger some activity
./fc1 cmd "imx flush"

# Check log for debug output
./fc1 ssh "tail -50 /var/log/fc-1.log"

# Disable debug
./fc1 cmd "debug off"
```

**Expected Result**: Debug messages appear in log when enabled

---

### Test 8: Stress Test - Multiple Restarts

**Purpose**: Verify system stability across multiple restart cycles

```bash
# Perform 5 restart cycles
for i in {1..5}; do
    echo "=== Restart cycle $i ==="
    ./fc1 restart
    sleep 20
    ./fc1 status
    ./fc1 cmd "c" | grep boot_count
done
```

**Expected Result**:
- All 5 restarts complete successfully
- Boot count increments by 5 total
- No crash loops or segfaults

---

### Test 9: Log File Rotation Verification

**Purpose**: Ensure logs don't grow unbounded

```bash
# Check log file size
./fc1 ssh "ls -lh /var/log/fc-1.log*"

# Check for rotation
./fc1 ssh "ls -la /var/log/fc-1.log*"
```

**Expected Result**: Log files exist and are reasonable size

---

## Validation Checklist

### Required (Must Pass)
- [ ] FC-1 starts without segmentation fault
- [ ] Startup messages appear in `/var/log/fc-1.log`
- [ ] Messages have timestamp prefix `[HH:MM:SS.mmm]`
- [ ] CLI accessible via telnet (port 23)
- [ ] All basic CLI commands work (`?`, `v`, `s`, `ms`)
- [ ] Service remains stable (no restart loops)

### Recommended (Should Pass)
- [ ] Debug flag system works correctly
- [ ] Multiple restart cycles complete successfully
- [ ] Boot count increments correctly
- [ ] Log file rotation working
- [ ] Console output still functional

---

## Test Commands Quick Reference

```bash
# Deployment
./fc1 push -run              # Deploy and start

# Monitoring
./fc1 status                 # Service status
./fc1 log                    # Recent logs
./fc1 ssh "tail -f /var/log/fc-1.log"  # Live log watch

# CLI Testing
./fc1 cmd "?"               # Help
./fc1 cmd "v"               # Version
./fc1 cmd "s"               # Status
./fc1 cmd "c"               # Config (includes boot_count)
./fc1 cmd "ms"              # Memory stats
./fc1 cmd "debug ?"         # Debug flags

# Specific Log Searches
./fc1 ssh "grep -i 'Configuration Loaded' /var/log/fc-1.log | tail -5"
./fc1 ssh "grep -i 'Initialization Complete' /var/log/fc-1.log | tail -5"
./fc1 ssh "dmesg | grep -i segfault"
```

---

## Rollback Procedure

If testing reveals issues:

```bash
# Stop the service
./fc1 stop

# Restore previous binary (if backed up)
./fc1 ssh "cp /usr/qk/etc/sv/FC-1/run.backup /usr/qk/etc/sv/FC-1/run"

# Or rebuild from original branch
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
git -C ../iMatrix checkout Aptera_1_Clean
make clean && make -j4
./fc1 push -run
```

---

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| Test 1: Baseline | | |
| Test 2: Deploy | | |
| Test 3: Filesystem Log | | |
| Test 4: No Segfault | | |
| Test 5: Console Output | | |
| Test 6: Telnet CLI | | |
| Test 7: Debug Flags | | |
| Test 8: Stress Test | | |
| Test 9: Log Rotation | | |

**Overall Result**: _____________

**Tester**: _____________

**Date Tested**: _____________

---

*Document created: 2026-01-03*
