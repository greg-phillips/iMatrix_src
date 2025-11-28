# Cellular Serial Port Management Fix Plan

**Date**: 2025-11-21
**Issue**: Segmentation fault on second AT+COPS? query due to closed serial port
**Root Cause**: Serial port incorrectly closed before PPP start and never reopened
**Priority**: CRITICAL - System crashes after 60-80 seconds

---

## Executive Summary

The cellular subsystem closes the AT command serial port (`/dev/ttyACM2`, fd stored in `cell_fd`) before starting PPP, but **never reopens it**. This causes a segmentation fault when attempting to send AT commands (like `AT+COPS?` or `AT+CSQ`) while PPP is running.

**Critical Insight**: The two serial ports serve different purposes and **do not conflict**:
- **`/dev/ttyACM0`**: PPP data connection (used by pppd daemon)
- **`/dev/ttyACM2`**: AT command interface (used by cellular_man.c for monitoring)

The AT command port should **remain open at all times** except during full cellular reset.

---

## Root Cause Analysis

### Current Buggy Flow

```
CELL_INIT (line 2301)
  ├─ Open /dev/ttyACM2 → cell_fd = 12 ✅
  └─ Configure serial port ✅

AT Commands work fine ✅
  ├─ AT+CSQ (signal quality)
  ├─ AT+COPS=3,2 (set operator format)
  └─ AT+COPS? (query operator) ← Works at 00:00:20 ✅

start_pppd() called (line 2056)
  ├─ Line 2073-2081: Close cell_fd ❌ BUG!
  │   ├─ tcflush(cell_fd)
  │   ├─ close(cell_fd)
  │   └─ cell_fd = -1
  ├─ Start /etc/start_pppd.sh
  └─ pppd uses /dev/ttyACM0 (different port!)

System runs for 72 seconds
  └─ PPP connection active on ppp0

CELL_ONLINE periodic check (line 2722, at 00:01:32)
  ├─ 60 seconds elapsed, trigger AT+COPS? check
  ├─ Line 2736: send_AT_command(cell_fd, "+COPS?")
  │   └─ cell_fd = -1 ❌ INVALID!
  └─ write(-1, "AT", 2) ← SEGMENTATION FAULT 💥
```

### Why Serial Port Never Reopens

The `stop_pppd()` function (line 2171) only reopens the serial port if:
```c
if (!cellular_reset && cell_fd == -1)
```

But PPP is **still running** during normal operation! `stop_pppd()` is only called when:
1. Cellular scan requested (but we removed the direct call in Issue #1 fix)
2. Cellular reset/re-init
3. System shutdown

Therefore, during normal operation with active PPP:
- Port is closed before PPP start
- PPP runs successfully
- `stop_pppd()` is never called
- Port remains closed (cell_fd = -1)
- First periodic AT command crashes

---

## Evidence from Logs

### net7.txt Timeline

```
Line 476:  [00:00:21.731] Closing serial port (fd=12) before starting PPP
Line 477:  [00:00:21.877] Serial port closed, ready for PPP
Line 478:  [00:00:21.902] Starting PPPD: /etc/start_pppd.sh

[... 72 seconds of normal operation ...]

Line 1034: [00:01:32.645] Sending AT command: AT+COPS?
Line 1035: Segmentation fault
```

**No "Reopening serial port" message ever appears!**

### First AT+COPS? Query (SUCCESS)

```
Line 439: [00:00:20.937] Sending AT command: AT+COPS?
Line 443: [00:00:21.038] Line: AT+COPS?
Line 450: [00:00:21.140] Line 0: AT+COPS?
Line 453: [00:00:21.242] Line 1: +COPS: 1,2,"310260",7
```
- Timestamp: 00:00:20
- cell_fd = 12 (valid)
- Command succeeds ✅

### Second AT+COPS? Query (CRASH)

```
Line 1034: [00:01:32.645] Sending AT command: AT+COPS?
Line 1035: Segmentation fault
```
- Timestamp: 00:01:32 (72 seconds later)
- cell_fd = -1 (closed)
- Crash on write() call ❌

---

## The Fundamental Mistake

### Incorrect Assumption (Old Code)
```c
// start_pppd() - Line 2071-2086
// CRITICAL: Ensure serial ports are properly closed before PPP starts
// This prevents "Can't get terminal parameters: I/O error" in chat script
if (cell_fd != -1) {
    PRINTF("[Cellular Connection - Closing serial port (fd=%d) before starting PPP]\r\n", cell_fd);
    tcflush(cell_fd, TCIOFLUSH);
    close(cell_fd);
    cell_fd = -1;  // ❌ BUG: This should never happen!
    usleep(100000);
}
```

**Why this comment is WRONG**:
- The "I/O error" refers to `/dev/ttyACM0` (PPP data port), not `/dev/ttyACM2` (AT command port)
- These are separate USB ACM devices with independent file descriptors
- Closing `/dev/ttyACM2` does not help `/dev/ttyACM0` access

### Hardware Architecture (QConnect Developer Guide p.25)

```
Quectel Modem (USB)
  ├─ /dev/ttyACM0 ─── PPP Daemon (pppd) ─── ppp0 interface
  ├─ /dev/ttyACM1 ─── (NMEA GPS data)
  └─ /dev/ttyACM2 ─── AT Commands (cellular_man.c) ─── cell_fd
```

**These ports are INDEPENDENT!**
- PPP using ACM0 does NOT affect AT commands on ACM2
- Both can be open simultaneously
- Closing ACM2 is unnecessary and harmful

---

## Fix Strategy

### Principle
**The AT command serial port (`/dev/ttyACM2`) should remain open for the entire lifecycle, except during full reset.**

### Changes Required

1. **Remove port closure from `start_pppd()`**
   - Location: cellular_man.c:2071-2086
   - Action: Delete the entire `if (cell_fd != -1)` block
   - Rationale: Port should remain open for monitoring

2. **Remove port reopening from `stop_pppd()`**
   - Location: cellular_man.c:2169-2180
   - Action: Delete the `if (!cellular_reset && cell_fd == -1)` block
   - Rationale: Port should never have been closed, so no need to reopen

3. **Keep port closure in CELL_INIT reset path**
   - Location: cellular_man.c:2293-2296
   - Action: NO CHANGE (this is correct)
   - Rationale: Full reset requires closing and reopening port

4. **Keep port closure in CELL_PROCESS_RETRY**
   - Location: cellular_man.c:2787
   - Action: NO CHANGE (this is correct)
   - Rationale: Retry count exceeded triggers full re-initialization

5. **Add validation to `send_AT_command()`**
   - Location: cellular_man.c:651-687
   - Action: Keep existing validation (already added in debugging)
   - Rationale: Defense in depth - catch invalid fd early

---

## Detailed Implementation

### Change 1: Remove Port Closure from start_pppd()

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location**: Lines 2071-2086

**REMOVE THIS CODE**:
```c
    // CRITICAL: Ensure serial ports are properly closed before PPP starts
    // This prevents "Can't get terminal parameters: I/O error" in chat script
    if (cell_fd != -1) {
        PRINTF("[Cellular Connection - Closing serial port (fd=%d) before starting PPP]\r\n", cell_fd);

        // Ensure any pending data is flushed
        tcflush(cell_fd, TCIOFLUSH);

        // Close the file descriptor
        close(cell_fd);
        cell_fd = -1;  // Mark as closed

        // Small delay to ensure port is fully released
        usleep(100000);  // 100ms delay
        PRINTF("[Cellular Connection - Serial port closed, ready for PPP]\r\n");
    }
```

**KEEP THIS CODE** (lock file cleanup):
```c
    // Ensure no lock files are blocking the PPP device
    system("rm -f /var/lock/LCK..ttyACM0 2>/dev/null");
```

**NEW CODE** (optional logging):
```c
    // AT command port (/dev/ttyACM2) remains open for monitoring
    // PPP will use /dev/ttyACM0 (separate device)
    if (cell_fd != -1) {
        PRINTF("[Cellular Connection - AT command port remains open (fd=%d) during PPP]\r\n", cell_fd);
    }
```

### Change 2: Remove Port Reopening from stop_pppd()

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location**: Lines 2169-2180

**REMOVE THIS CODE**:
```c
    // Reopen the serial port for cellular monitoring (unless it's a reset which will handle it)
    extern int cell_fd;
    if (!cellular_reset && cell_fd == -1) {
        PRINTF("[Cellular Connection - Reopening serial port for monitoring after PPP stop]\r\n");
        cell_fd = open_serial_port(CELLULAR_SERIAL_PORT);
        if (cell_fd != -1) {
            configure_serial_port(cell_fd);
            PRINTF("[Cellular Connection - Serial port reopened (fd=%d)]\r\n", cell_fd);
        } else {
            PRINTF("[Cellular Connection - Failed to reopen serial port]\r\n");
        }
    }
```

**NEW CODE** (optional validation):
```c
    // AT command port should still be open (it was never closed)
    extern int cell_fd;
    if (cell_fd == -1) {
        PRINTF("[Cellular Connection - WARNING: AT command port unexpectedly closed!]\r\n");
        // This should never happen in normal operation
    }
```

### Change 3: Verify Port Stays Open During Scanning

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location**: Lines 2220-2238 (cellular scan handling)

**CURRENT CODE** (already fixed in Issue #1):
```c
else if( cellular_flags.cell_scan )
{
    PRINTF("[Cellular Connection - Starting operator scan]\r\n");

    // Set scanning state - network manager will handle PPP shutdown safely
    cellular_scanning = true;  // ✅ Signal to network manager
    cellular_state = CELL_PROCIESS_INITIALIZATION;
    current_command = HANDLE_ATCOPS_SET_NUMERIC_MODE;
    cellular_now_ready = false;
    cellular_link_reset = true;
    check_for_connected = false;
    cellular_flags.cell_scan = false;
}
```

**VERIFY**: No `close(cell_fd)` in this path ✅
**VERIFY**: No `stop_pppd()` call here (network manager handles it) ✅
**VERIFY**: Port remains open during scan ✅

### Change 4: Add Defensive Check to send_AT_command()

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location**: Lines 651-687

**CURRENT CODE** (already has validation from debugging):
```c
void send_AT_command(int fd, char *command )
{
    // ADD VALIDATION
    if (fd < 0) {
        PRINTF("[ERROR] Invalid file descriptor: %d\r\n", fd);
        return;
    }

    if (command == NULL) {
        PRINTF("[ERROR] NULL command pointer\r\n");
        return;
    }

    if( strlen( command ) > 0 ) {
        PRINTF( "[Cellular Connection - Sending AT command: AT%s]\r\n", command);

        // ADD ERROR CHECKING
        ssize_t ret;

        ret = write(fd, "AT", 2);
        if (ret < 0) {
            PRINTF("[ERROR] write() AT failed: %s (errno=%d)\r\n", strerror(errno), errno);
            return;
        }

        ret = write(fd, command, strlen(command));
        if (ret < 0) {
            PRINTF("[ERROR] write() command failed: %s (errno=%d)\r\n", strerror(errno), errno);
            return;
        }

        ret = write(fd, "\r", 1);
        if (ret < 0) {
            PRINTF("[ERROR] write() CR failed: %s (errno=%d)\r\n", strerror(errno), errno);
            return;
        }
    } else {
        PRINTF( "[Cellular Connection - Sending dummy AT command]\r\n");
        write(fd, "AT\r", 3);
    }
}
```

**KEEP THIS** - Good defensive programming! ✅

---

## Port Lifecycle Management (CORRECTED)

### Normal Operation (No Resets)

```
CELL_INIT
  └─ Open /dev/ttyACM2 → cell_fd = 12 ✅

[Port remains OPEN through entire lifecycle]

AT Commands
  ├─ AT+CSQ (signal quality) ✅
  ├─ AT+COPS? (operator status) ✅
  └─ AT+CPIN? (SIM status) ✅

start_pppd()
  ├─ Port stays OPEN (no close) ✅
  └─ pppd uses /dev/ttyACM0 (different port) ✅

CELL_ONLINE
  └─ Periodic AT+COPS? every 60s ✅

stop_pppd() [if called]
  └─ Port still OPEN (no reopen needed) ✅

[Port remains OPEN until shutdown or reset]
```

### Cellular Reset Flow

```
CELL_PROCESS_RETRY (retry count exceeded)
  └─ close(cell_fd) ✅
  └─ cellular_state = CELL_INIT

CELL_INIT
  ├─ stop_pppd(true) [cellular_reset=true]
  ├─ if (cell_fd != -1) close(cell_fd) ✅
  ├─ cell_fd = open_serial_port() ✅
  └─ configure_serial_port(cell_fd) ✅
```

### Operator Scan Flow

```
User: "cell scan"
  └─ cellular_flags.cell_scan = true

cellular_man.c processes flag
  ├─ cellular_scanning = true
  ├─ Port stays OPEN ✅
  └─ Signal network manager

process_network.c
  ├─ Detect scanning flag
  ├─ Wait for ping thread completion
  ├─ Call stop_pppd(true) [cellular_reset=true]
  └─ Port still OPEN (AT commands can continue) ✅

Scan completes
  └─ start_pppd() to resume connection
  └─ Port still OPEN ✅
```

---

## Testing Plan

### Test 1: Normal Operation (Primary Test)

**Objective**: Verify AT commands work during PPP connection

**Procedure**:
```bash
./FC-1 > test1.txt 2>&1
```

**Expected Results**:
```
[00:00:20] First AT+COPS? query ✅ SUCCESS
[00:01:20] Second AT+COPS? query ✅ SUCCESS
[00:02:20] Third AT+COPS? query ✅ SUCCESS
[00:03:20] Fourth AT+COPS? query ✅ SUCCESS
```

**Success Criteria**:
- [ ] No "Closing serial port before starting PPP" message
- [ ] No segmentation faults
- [ ] All periodic AT+COPS? queries succeed
- [ ] All periodic AT+CSQ queries succeed
- [ ] cell_fd remains valid (>0) throughout

### Test 2: PPP Start/Stop Cycles

**Objective**: Verify port stays open through PPP lifecycle

**Procedure**:
```bash
# In FC-1 CLI:
cell init        # Start cellular
# Wait 2 minutes
cell reset       # Force reset
# Wait 2 minutes
cell init        # Restart
```

**Expected Results**:
```
[Initial] cell_fd opened ✅
[PPP Start] cell_fd stays open ✅
[PPP Running] AT commands work ✅
[Cell Reset] cell_fd closed and reopened ✅
[PPP Restart] cell_fd stays open ✅
```

**Success Criteria**:
- [ ] Port opens on CELL_INIT
- [ ] Port stays open during PPP
- [ ] Port closes only on explicit reset
- [ ] Port reopens after reset
- [ ] No segfaults at any point

### Test 3: Operator Scan During PPP

**Objective**: Verify scan works without closing AT command port

**Procedure**:
```bash
# In FC-1 CLI:
cell init        # Start cellular and PPP
# Wait for PPP connection (ppp0 online)
cell scan        # Trigger operator scan
# Wait for scan completion
# Verify PPP restarts
```

**Expected Results**:
```
[Before Scan] cell_fd=12, PPP running ✅
[Scan Start] PPP stops, cell_fd=12 (still open) ✅
[Scanning] AT commands work during scan ✅
[Scan Complete] PPP restarts, cell_fd=12 ✅
[After Scan] AT commands work ✅
```

**Success Criteria**:
- [ ] Scan triggers PPP stop (via network manager)
- [ ] cell_fd remains open during scan
- [ ] AT commands work during scan
- [ ] PPP restarts after scan
- [ ] No segfaults

### Test 4: Signal Quality Monitoring

**Objective**: Verify AT+CSQ works continuously during PPP

**Procedure**:
```bash
# Monitor signal quality every 10 seconds for 5 minutes
# AT+CSQ should be called frequently
./FC-1 > test4.txt 2>&1
# After 5 minutes, check log
grep "AT+CSQ" test4.txt | wc -l
# Should show ~30 queries
```

**Success Criteria**:
- [ ] All AT+CSQ queries succeed
- [ ] No gaps in signal monitoring
- [ ] No segfaults
- [ ] Signal strength reported correctly

### Test 5: Long-Duration Stability

**Objective**: Verify no issues over extended runtime

**Procedure**:
```bash
# Run for 30 minutes with PPP active
timeout 1800 ./FC-1 > test5.txt 2>&1
# Check for any errors
grep -i "error\|fault\|fail" test5.txt
```

**Success Criteria**:
- [ ] No segmentation faults
- [ ] All AT+COPS? queries succeed (~30 queries)
- [ ] All AT+CSQ queries succeed
- [ ] PPP connection stable
- [ ] cell_fd valid throughout

### Test 6: Stress Test (Multiple Resets)

**Objective**: Verify reset handling works correctly

**Procedure**:
```bash
# Script to reset cellular 10 times
for i in {1..10}; do
    echo "Reset cycle $i"
    # Trigger reset via CLI
    echo "cell reset" | ./FC-1
    sleep 60
done
```

**Success Criteria**:
- [ ] All resets complete successfully
- [ ] Port closes and reopens correctly each time
- [ ] No file descriptor leaks
- [ ] No segfaults
- [ ] AT commands work after each reset

---

## Verification Checklist

### Code Review
- [ ] Removed port close from start_pppd()
- [ ] Removed port reopen from stop_pppd()
- [ ] Verified CELL_INIT still opens port
- [ ] Verified CELL_PROCESS_RETRY still closes port
- [ ] Verified send_AT_command() has validation
- [ ] No other code paths close cell_fd unexpectedly

### Build & Compilation
- [ ] Code compiles without warnings
- [ ] No syntax errors
- [ ] Executable built successfully
- [ ] Build timestamp updated

### Testing
- [ ] Test 1 (Normal Operation) passes ✅
- [ ] Test 2 (PPP Cycles) passes ✅
- [ ] Test 3 (Operator Scan) passes ✅
- [ ] Test 4 (Signal Monitoring) passes ✅
- [ ] Test 5 (Long Duration) passes ✅
- [ ] Test 6 (Stress Test) passes ✅

### Documentation
- [ ] Updated cellular_segfault_issues_summary.md
- [ ] Created cellular_serial_port_fix_summary.md
- [ ] Updated CLAUDE.md if needed
- [ ] Commented code changes appropriately

---

## Risk Assessment

### Low Risk Changes ✅
- Removing port close from start_pppd()
  - **Why safe**: Two different ports (ACM0 vs ACM2)
  - **Validation**: Hardware documentation confirms independence

- Removing port reopen from stop_pppd()
  - **Why safe**: Port should never have been closed
  - **Validation**: No other code depends on this reopen

### No Risk to Existing Functionality ✅
- Reset flows unchanged (port still closes/reopens on reset)
- Scan flows unchanged (Issue #1 fix still works)
- PPP lifecycle unchanged (pppd still uses ACM0)
- All other AT commands unchanged

### Benefits
- ✅ Eliminates segmentation fault
- ✅ Simplifies port lifecycle management
- ✅ Enables continuous signal monitoring
- ✅ Removes unnecessary port operations
- ✅ More efficient (no close/reopen overhead)

---

## Rollback Plan

If issues arise after fix:

### Step 1: Revert Changes
```bash
cd iMatrix
git checkout HEAD -- IMX_Platform/LINUX_Platform/networking/cellular_man.c
```

### Step 2: Rebuild
```bash
cd Fleet-Connect-1
make clean
make
```

### Step 3: Test Reverted Version
```bash
./FC-1 > rollback_test.txt 2>&1
```

### Step 4: Compare Logs
```bash
diff rollback_test.txt test1.txt
```

---

## Success Criteria

The fix is considered successful when:

1. ✅ **No Segmentation Faults**: System runs for extended periods without crashes
2. ✅ **AT Commands Work**: All AT+COPS?, AT+CSQ, etc. succeed during PPP
3. ✅ **PPP Stable**: Data connection remains active and healthy
4. ✅ **Port Lifecycle Clean**: No unnecessary open/close operations
5. ✅ **Reset Works**: Full reset still closes and reopens port correctly
6. ✅ **Scan Works**: Operator scan completes without issues
7. ✅ **Logging Clear**: No error messages about invalid file descriptors

---

## Next Steps

1. **Implement Changes** (30 minutes)
   - Remove port close from start_pppd()
   - Remove port reopen from stop_pppd()
   - Review all code paths

2. **Build and Test** (2 hours)
   - Clean build
   - Run Test 1 (Normal Operation)
   - Run Test 5 (Long Duration)

3. **Extended Testing** (4 hours)
   - All 6 test scenarios
   - Collect comprehensive logs
   - Verify no regressions

4. **Documentation** (1 hour)
   - Update summary documents
   - Create fix summary report
   - Update CLAUDE.md if needed

**Total Estimated Time**: 7-8 hours

---

## Related Documents

- **cellular_segfault_issues_summary.md**: Original issue report and analysis
- **at_cops_segfault_analysis.md**: Detailed crash analysis
- **cellular_scan_ppp_fix_summary.md**: Issue #1 fix (related)
- **ppp_connection_fix_summary.md**: PPP connection fixes (background)
- **QConnect Developer Guide p.25**: Hardware port documentation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Status**: Ready for Implementation
**Estimated Fix Time**: 30 minutes
**Estimated Test Time**: 6-8 hours
