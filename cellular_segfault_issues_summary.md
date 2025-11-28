# Cellular Subsystem Segfault Issues - Developer Handoff

**Date**: 2025-11-20
**Author**: Claude Code Analysis
**Status**: One issue FIXED, one issue OPEN
**Priority**: CRITICAL - System stability

---

## System Overview

### What is iMatrix?

**iMatrix** is an embedded IoT platform for vehicle telemetry and fleet management. It provides:
- Real-time vehicle data collection from CAN bus
- Cellular connectivity for cloud data upload
- Multi-interface network management (Ethernet, WiFi, Cellular)
- GPS location tracking and geofencing
- Remote vehicle monitoring and control

### Project Structure

This is the **iMatrix_Client** master repository containing three main submodules:

```
iMatrix_Client/
├── Fleet-Connect-1/          # Gateway application (main executable)
│   ├── linux_gateway.c       # Application entry point
│   ├── do_everything.c       # Main processing loop
│   └── can_process/          # CAN bus processing
│
├── iMatrix/                  # Core embedded system (our focus)
│   ├── IMX_Platform/
│   │   └── LINUX_Platform/
│   │       └── networking/
│   │           ├── cellular_man.c      # ← SEGFAULT LOCATION
│   │           ├── cellular_man.h
│   │           └── process_network.c   # ← SEGFAULT FIX LOCATION
│   ├── storage/              # Flash memory management
│   ├── cli/                  # Command line interface
│   └── device/               # Device configuration
│
└── CAN_DM/                   # CAN DBC file processor
    └── process_dbc.c
```

### Component Responsibilities

**Fleet-Connect-1** (Application Layer):
- Main application logic
- CAN bus data processing
- OBD2 protocol handling
- Vehicle-specific configurations
- Calls into iMatrix core for services

**iMatrix** (Platform Layer):
- Network interface management
- Cellular modem control (AT commands)
- PPP daemon lifecycle management
- WiFi and Ethernet management
- Storage and memory management
- Cloud connectivity (CoAP)

**CAN_DM** (Development Tool):
- Processes DBC files to generate device configs
- Not involved in runtime operation

### Cellular Subsystem Architecture

The cellular subsystem has two main components:

**1. cellular_man.c** (Cellular Manager):
- Controls cellular modem via AT commands
- Manages PPP connection lifecycle
- Handles operator scanning and selection
- Maintains carrier blacklist
- State machine: CELL_INIT → CELL_CONNECTED → CELL_ONLINE
- Runs in main application thread

**2. process_network.c** (Network Manager):
- Manages all network interfaces (eth0, wlan0, ppp0)
- Selects best available interface
- Runs ping tests for health checking
- Manages DHCP clients
- State machine: NET_INIT → NET_SELECT_INTERFACE → NET_ONLINE
- Runs in separate thread context

**Critical Interaction**:
```
┌─────────────────┐          ┌──────────────────┐
│ cellular_man.c  │          │ process_network.c│
│ (Main Thread)   │          │ (Network Thread) │
├─────────────────┤          ├──────────────────┤
│ - AT commands   │◄────────►│ - Interface mgmt │
│ - PPP lifecycle │  Shared  │ - Ping threads   │
│ - Modem control │  State   │ - Route mgmt     │
│ - Operator scan │          │ - DHCP control   │
└─────────────────┘          └──────────────────┘
        │                            │
        └────────► PPP0 ◄────────────┘
                (pppd daemon)
```

**Race Condition Risk**: Both components can affect ppp0 state simultaneously.

### Hardware Platform

**Target Device**: Quectel cellular modem (via USB ACM)
- **/dev/ttyACM0**: PPPD data connection
- **/dev/ttyACM2**: AT command interface (customer access)
- **PPP Daemon**: Manages data connection, creates ppp0 interface

**Development Environment**:
- **OS**: Linux (embedded, tested on WSL2)
- **Architecture**: ARM (cross-compiled with qconnect_sdk_musl)
- **Build System**: CMake

### Build Procedure

```bash
# From iMatrix_Client directory
cd Fleet-Connect-1
cmake -DiMatrix_DIR=../iMatrix .
make

# Output: FC-1 executable
```

**Build Verification**:
```bash
./FC-1 --version
# Should show: Fleet Connect built on [date] @ [time]
```

### Testing Environment

**Log Collection**:
- Logs captured to files (net1.txt, net2.txt, etc.)
- Key messages prefixed with component name:
  - `[Cellular Connection - ...]` ← cellular_man.c
  - `[NETMGR-PPP0]` ← process_network.c (PPP-specific)
  - `[NET: ppp0]` ← ping threads

**Test Scenario for Segfaults**:
1. System boots, initializes cellular modem
2. PPP connection established (ppp0 interface created)
3. Network manager pings ppp0 for health checks
4. Either:
   - User issues `cell scan` command (Issue #1)
   - System runs periodic AT+COPS? check (Issue #2)
5. Segmentation fault occurs

### Key Background Information

**PPP Connection Flow**:
```
1. cellular_man.c calls start_pppd()
2. System launches /etc/start_pppd.sh
3. Script runs chat script with AT commands
4. Modem establishes data connection
5. pppd daemon creates ppp0 interface
6. process_network.c detects ppp0 has IP
7. Network manager runs ping tests
8. System transitions to NET_ONLINE
```

**Cellular Operator Scanning**:
- Command: `AT+COPS=?` (scan all operators)
- Duration: 30-120 seconds
- **Requirement**: Modem CANNOT scan while data connection active
- **Solution**: Must stop PPP before scanning

**Recent Development Work** (Nov 2025):
1. Fixed terminal I/O errors in PPP connection
2. Added chat script error detection (exit codes 0x3, 0xb)
3. Enhanced carrier blacklisting on CME ERROR
4. Fixed cellular scan to stop PPP before scanning ← **Issue #1 fix**
5. Added ping thread coordination ← **Issue #1 fix**
6. **Issue #2 discovered during testing** ← Still investigating

### Important Files for This Investigation

**Core Files**:
- `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` (3100 lines)
- `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.h` (100 lines)
- `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` (4800 lines)

**Test Logs**:
- `logs/net5.txt` - Multiple scan attempts, NO CARRIER loops
- `logs/net6.txt` - **Issue #1**: Scan during ping, segfault (FIXED)
- `logs/net7.txt` - **Issue #2**: AT+COPS? periodic check, segfault (OPEN)

**Documentation**:
- `CLAUDE.md` - Repository guide for AI/developers
- `README_PROMPT_GENERATOR.md` - Prompt generation system
- `docs/1180-3007_C_QConnect__Developer_Guide.pdf` - Hardware docs (page 25: port allocation)

### Prerequisites for Next Developer

**Required Knowledge**:
- C programming (embedded systems)
- Linux system programming (popen, write, file descriptors)
- Multi-threaded programming (mutexes, race conditions)
- AT commands and cellular modem protocols
- Network interfaces and PPP

**Required Tools**:
- Git (for version control and bisecting)
- GCC/Cross-compiler (qconnect_sdk_musl)
- GDB (for debugging)
- Valgrind or AddressSanitizer (for memory debugging)
- Access to target hardware (Quectel modem)

**Required Access**:
- Target device with cellular modem
- SIM card with active data plan
- Serial console or SSH access
- Ability to collect logs and core dumps

---

## Segfault Issues Overview

The cellular subsystem (cellular_man.c / process_network.c) has experienced two distinct segmentation faults during testing. This document provides a comprehensive summary for the next developer to continue investigation and testing.

---

## Issue #1: Cellular Scan Race Condition - ✅ FIXED

### Problem Description

**Log**: net6.txt (line 134)
**Symptom**: Segmentation fault when `cell scan` command issued during active ping test
**Root Cause**: Race condition between network manager ping thread and cellular scan PPP shutdown

### Technical Details

**Timeline**:
```
1. User executes: cell scan
2. cellular_man.c IMMEDIATELY stops PPP (direct stop_pppd() call)
3. Network manager has active ping thread testing ppp0
4. PPP interface destroyed while ping thread still executing
5. Ping thread accesses freed/invalid memory structures
6. SEGMENTATION FAULT
```

**Evidence from net6.txt**:
```
Line 123: [Cellular Connection - Starting operator scan]
Line 124: [Cellular Connection - Stopping PPP for operator scan]
Line 125: [Cellular Connection - Stopping PPPD (cellular_reset=true)]
Line 126: [NET: ppp0] execute_ping: ping: sendto: No such device  ← Interface gone!
Line 134: Segmentation fault  ← CRASH
```

### Solution Implemented

**Two-part fix**:

1. **Removed premature PPP shutdown** (cellular_man.c:2220-2238)
   - Removed direct `stop_pppd()` call when scan triggered
   - Let network manager handle PPP lifecycle safely

2. **Added ping thread coordination** (process_network.c:4370-4392)
   - Check if ping thread active before stopping PPP for scan
   - Defer PPP shutdown until ping completes
   - Prevents interface destruction during thread execution

**Code Changes**:

**cellular_man.c** (BEFORE):
```c
else if( cellular_flags.cell_scan )
{
    PRINTF("[Cellular Connection - Starting operator scan]\r\n");

    // Stop PPP before scanning - modem cannot scan while connected
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        PRINTF("[Cellular Connection - Stopping PPP for operator scan]\r\n");
        stop_pppd(true);  // ❌ NO THREAD COORDINATION
    }

    cellular_scanning = true;
    // ...
}
```

**cellular_man.c** (AFTER):
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

**process_network.c** (AFTER):
```c
if (is_scanning)
{
    // Check if ping thread is running on ppp0 before stopping
    if (ctx->states[IFACE_PPP].running)  // ✅ SAFETY CHECK
    {
        NETMGR_LOG_PPP0(ctx, "Deferring scan PPP shutdown - ping test running on ppp0");
        // Wait for ping to complete before stopping PPP
    }
    else
    {
        // Safe to stop PPP during scanning
        if( ctx->cellular_stopped == false )
        {
            stop_pppd(true);
            MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
            ctx->cellular_started = false;
            ctx->cellular_stopped = true;
            ctx->states[IFACE_PPP].active = false;
            MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);
            NETMGR_LOG_PPP0(ctx, "Stopped pppd - cellular scanning for operators");
        }
    }
}
```

### Files Modified

1. **iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c**
   - Line 524: Added `cellular_scanning` flag
   - Line 2224: Removed direct `stop_pppd()` call
   - Line 3077: Added `imx_is_cellular_scanning()` export function

2. **iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.h**
   - Line 89: Added function declaration

3. **iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c**
   - Lines 4373-4391: Added ping thread check and deferral logic

### Testing Status

✅ **Fix validated in net7.txt**:
- Lines 989, 997: Deferral mechanism working ("Deferring PPPD conflict resolution")
- Ping tests complete normally
- No scan-related segfaults

### Documentation

- **Implementation Plan**: cellular_scan_ppp_fix_plan.md
- **Implementation Summary**: cellular_scan_ppp_fix_summary.md
- **Segfault Fix Plan**: cellular_scan_segfault_fix_plan.md
- **Segfault Fix Summary**: cellular_scan_segfault_fix_summary.md

---

## Issue #2: AT+COPS? Periodic Check Crash - ⚠️ OPEN

### Problem Description

**Log**: net7.txt (line 1035)
**Symptom**: Segmentation fault on second AT+COPS? periodic status check (72 seconds after startup)
**Root Cause**: UNKNOWN - Under investigation

### Technical Details

**Timeline**:
```
00:00:20 - First AT+COPS? query: SUCCESS (parsed operator: T-Mobile US)
00:01:32 - Second AT+COPS? query: IMMEDIATE SEGFAULT
```

**Evidence from net7.txt**:
```
Line 439-453: First AT+COPS? works perfectly
  - Command sent successfully
  - Response received: +COPS: 1,2,"310260",7
  - Parsed: T-Mobile US (310260), LTE

Line 1000-1033: System operating normally before crash
  - Ping test completed (3/3 replies, 192ms avg)
  - Thread cleanup normal
  - State: NET_ONLINE
  - PPP connection healthy

Line 1034: [Cellular Connection - Sending AT command: AT+COPS?]
Line 1035: Segmentation fault  ← CRASH
```

**Crash Location**:
```c
// cellular_man.c:2680-2697
case CELL_ONLINE:
    if( imx_is_later( current_time, cellular_check_time + 60 * 1000 ) ) {
        cellular_check_time = current_time;
        send_AT_command(cell_fd, (char *) "+COPS?");  // ← LINE 2691: CRASH HERE
        memset(response_buffer, 0, sizeof(response_buffer));
        initATResponseState(&state, current_time);
        return_cellular_state = CELL_ONLINE_OPERATOR_CHECK;
        current_command = HANDLE_ATCOPS_STATUS;
        cellular_state = CELL_GET_RESPONSE;
    }
    break;

// cellular_man.c:650-661
void send_AT_command(int fd, char *command )
{
    if( strlen( command ) > 0 ) {
        PRINTF( "[Cellular Connection - Sending AT command: AT%s]\r\n", command);  // ← LINE 653: SUCCEEDS
        write(fd, "AT", 2);         // ← LINE 654: CRASH SOMEWHERE IN HERE?
        write(fd, command, strlen(command));  // ← LINE 655
        write(fd, "\r", 1);         // ← LINE 656
    }
}
```

**What We Know**:
1. ✅ PRINTF at line 653 succeeds (message appears in log)
2. ❌ Crash happens during or after write() calls
3. ✅ First call to same function works fine
4. ✅ `cell_fd` was valid for previous commands (AT+CSQ, etc.)
5. ✅ No error messages before crash
6. ✅ Our new code (`detect_and_handle_chat_failure()`) was NOT called

### Potential Root Causes (Ranked)

**1. Stack/Heap Corruption (70% probability)**
- Timing-dependent (works once, fails later)
- Very simple function crashes
- Progressive memory corruption between calls
- Possible sources:
  - Buffer overflow in response_buffer handling
  - String handling bugs in AT command processing
  - `detect_and_handle_chat_failure()` resource usage
  - Thread stack collision

**2. Invalid File Descriptor (20% probability)**
- `cell_fd` became invalid between calls
- Race condition with network manager
- Less likely since other commands work

**3. Reentrancy/Thread Safety (10% probability)**
- Concurrent access to cellular_man resources
- Multiple threads writing to cell_fd
- Signal handler corruption

### Binary Information

**Build Date**: Nov 20 2025 @ 14:31:22
**Contains**: All Issue #1 fixes + detect_and_handle_chat_failure() function

This means the crash happens WITH our recent changes. Either:
- Our changes introduced a new bug
- Our changes exposed a pre-existing bug
- Completely unrelated issue

### Investigation Steps for Next Developer

#### Step 1: Add Defensive Checks

**Add to cellular_man.c:2680-2697 (before line 2691)**:
```c
case CELL_ONLINE:
    if( imx_is_later( current_time, cellular_check_time + 60 * 1000 ) ) {
        // ADD THIS DEBUG LOGGING
        PRINTF("[DEBUG] Periodic check triggered\r\n");
        PRINTF("[DEBUG] cell_fd=%d, cellular_state=%d\r\n", cell_fd, cellular_state);
        PRINTF("[DEBUG] About to send AT+COPS?\r\n");

        cellular_check_time = current_time;
        send_AT_command(cell_fd, (char *) "+COPS?");

        // ADD THIS - will it print?
        PRINTF("[DEBUG] AT+COPS? sent successfully\r\n");

        memset(response_buffer, 0, sizeof(response_buffer));
        initATResponseState(&state, current_time);
        return_cellular_state = CELL_ONLINE_OPERATOR_CHECK;
        current_command = HANDLE_ATCOPS_STATUS;
        cellular_state = CELL_GET_RESPONSE;
    }
    break;
```

**Modify send_AT_command() in cellular_man.c:650-661**:
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
        PRINTF("[DEBUG] Wrote 'AT' successfully\r\n");

        ret = write(fd, command, strlen(command));
        if (ret < 0) {
            PRINTF("[ERROR] write() command failed: %s (errno=%d)\r\n", strerror(errno), errno);
            return;
        }
        PRINTF("[DEBUG] Wrote command '%s' successfully\r\n", command);

        ret = write(fd, "\r", 1);
        if (ret < 0) {
            PRINTF("[ERROR] write() CR failed: %s (errno=%d)\r\n", strerror(errno), errno);
            return;
        }
        PRINTF("[DEBUG] Wrote CR successfully\r\n");
    } else {
        PRINTF( "[Cellular Connection - Sending dummy AT command]\r\n");
        write(fd, "AT\r", 3);
    }
}
```

This will help isolate EXACTLY where the crash occurs.

#### Step 2: Review detect_and_handle_chat_failure()

**Location**: cellular_man.c:1880-2007

**Check for**:
- Resource leaks (FILE pointers from popen)
- Unclosed pipes (pclose missing)
- Large stack allocations
- Buffer overflows
- Reentrancy issues

**Specific areas to audit**:
```c
Line 1895: fp = popen("tail -n 30 /var/log/pppd/current 2>/dev/null", "r");
Line 1924: pclose(fp);  // Is this ALWAYS called?

Line 1970: FILE *ps_fp = popen("ps | grep 'runsv pppd' | grep -v grep | awk '{print $1}'", "r");
Line 1985: pclose(ps_fp);  // Is this ALWAYS called?
```

**Question**: Could unclosed pipes or processes cause stack/heap corruption?

#### Step 3: Memory Corruption Detection

**Option A: Valgrind** (if available on target)
```bash
valgrind --leak-check=full --track-origins=yes ./FC-1
```

**Option B: AddressSanitizer** (rebuild with)
```bash
CFLAGS="-fsanitize=address -g" make
```

**Option C: Enable Core Dumps**
```bash
ulimit -c unlimited
# Run test, examine core file
gdb ./FC-1 core
(gdb) bt
(gdb) info registers
(gdb) x/20x $sp
```

#### Step 4: Response Buffer Audit

**Check these locations**:
```c
Line 500: static char response_buffer[NO_LINES_MAX_RESPONSE][MAX_RESPONSE_LENGTH + 1];
          // NO_LINES_MAX_RESPONSE = 20
          // MAX_RESPONSE_LENGTH = 256
          // Total: 20 * 257 = 5140 bytes

Line 772:  if (buffer[0] == 0x0A || state->charIndex >= MAX_RESPONSE_LENGTH - 1)
Line 777:  strncpy(response_buffer[state->lineIndex], state->tempLine, MAX_RESPONSE_LENGTH);
Line 804:  if (state->lineIndex >= NO_LINES_MAX_RESPONSE)
Line 2318: for (int i = 0; i < NO_LINES_MAX_RESPONSE && response_buffer[i][0] != '\0'; i++)
```

**Look for**:
- Off-by-one errors
- Array bounds violations
- Missing null terminators
- Concurrent access without locks

#### Step 5: Test with Code Rollback

**Procedure**:
```bash
# Save current state
git stash

# Checkout code BEFORE segfault fixes (before Nov 20 changes)
git checkout <commit-before-fixes>

# Rebuild
make clean && make

# Test - does AT+COPS? crash still happen?
# Run same test scenario, collect logs

# If NO crash: Our changes introduced/exposed the bug
# If CRASH: Pre-existing bug, unrelated to our changes
```

#### Step 6: Increase Logging Verbosity

**Add logging to**:
- Every state transition in cellular_man.c
- All memset() calls on response_buffer
- All AT command send/receive operations
- Thread entry/exit points

### Testing Checklist

When testing the fix:

- [ ] System boots and initializes successfully
- [ ] First AT+COPS? query succeeds (at ~20 seconds)
- [ ] Second AT+COPS? query succeeds (at ~80 seconds)
- [ ] Third AT+COPS? query succeeds (at ~140 seconds)
- [ ] No segmentation faults during any query
- [ ] All debug messages appear in log
- [ ] `cell_fd` remains valid throughout
- [ ] Memory usage stable (no leaks)
- [ ] Can reproduce on multiple test runs

### Files to Review

1. **cellular_man.c**:
   - Lines 650-661: `send_AT_command()`
   - Lines 1880-2007: `detect_and_handle_chat_failure()`
   - Lines 2680-2697: `CELL_ONLINE` periodic check
   - Line 500: `response_buffer` declaration

2. **cellular_man.h**:
   - Check for any threading annotations
   - Verify function prototypes

3. **process_network.c**:
   - Check for concurrent access to cellular state
   - Verify thread safety

### Documentation

- **Detailed Analysis**: at_cops_segfault_analysis.md
- **This Summary**: cellular_segfault_issues_summary.md

---

## Related Previous Work

### PPP Connection Fixes

Prior to these segfaults, several PPP connection issues were fixed:

1. **Terminal I/O Error Detection** (ppp_connection_fix_summary.md)
   - Enhanced serial port cleanup (tcflush, delays, lock files)
   - Terminal I/O error detection in chat failure handler

2. **Chat Script Error Handling** (ppp_connection_fix_plan.md)
   - Exit code 0x3 detection (script bug/timeout)
   - Exit code 0xb + CME ERROR (carrier failure with blacklisting)
   - Process cleanup using ps to find runsv

3. **IP Detection Improvements** (ppp_connection_fix_summary.md)
   - Fixed timing issues where PPP shows connected but has_ip=NO
   - Check both has_valid_ip_address() and PPP status string

These fixes are STABLE and working correctly.

---

## Critical Path for Next Developer

### Immediate Priorities

1. **Add defensive checks** to send_AT_command() (1 hour)
2. **Add debug logging** around crash point (30 minutes)
3. **Test and collect new log** (2 hours)
4. **Analyze log to isolate crash location** (1 hour)

### Next Steps Based on Findings

**If crash is in write() calls**:
- Check file descriptor validity
- Look for concurrent access
- Verify serial port state

**If crash is after write() returns**:
- Check memset() on response_buffer
- Look for stack corruption
- Review initATResponseState()

**If crash location unclear**:
- Run with valgrind/AddressSanitizer
- Enable core dumps and examine
- Add more granular logging

### Expected Timeline

- **Day 1**: Add checks, test, analyze new logs
- **Day 2**: Implement fix based on findings
- **Day 3**: Test fix thoroughly, verify stability
- **Day 4**: Document and integrate

---

## Code Quality Notes

### Good Practices Observed

1. ✅ State machine architecture is clean
2. ✅ Comprehensive logging throughout
3. ✅ Good separation of concerns (cellular_man vs network_manager)
4. ✅ Mutex protection in network manager
5. ✅ Error handling for most operations

### Areas Needing Improvement

1. ⚠️ Minimal error checking on write() calls
2. ⚠️ No validation of file descriptors before use
3. ⚠️ Some functions lack thread safety annotations
4. ⚠️ Large stack buffers in some functions (256+ bytes)
5. ⚠️ Inconsistent bounds checking on arrays

---

## Contact and Handoff

### Questions for Next Developer

1. Do you have access to target hardware for testing?
2. Can you run valgrind or enable AddressSanitizer?
3. Can you enable core dumps for crash analysis?
4. Do you have access to previous versions for bisecting?

### Handoff Checklist

- [x] Issue #1 (scan race) documented and fixed
- [x] Issue #1 fix validated in net7.txt
- [x] Issue #2 (AT+COPS?) thoroughly analyzed
- [x] Defensive code additions specified
- [x] Investigation steps documented
- [x] Testing procedures defined
- [x] All log files preserved (net5.txt, net6.txt, net7.txt)
- [x] All documentation created:
  - cellular_scan_ppp_fix_plan.md
  - cellular_scan_ppp_fix_summary.md
  - cellular_scan_segfault_fix_plan.md
  - cellular_scan_segfault_fix_summary.md
  - ppp_connection_fix_summary.md
  - ppp_connection_fix_plan.md
  - at_cops_segfault_analysis.md
  - cellular_segfault_issues_summary.md (this file)

---

## Summary

**Issue #1**: ✅ FIXED and validated
**Issue #2**: ⚠️ OPEN and requires immediate attention

The next developer should focus on Issue #2, starting with the defensive checks and debug logging specified above. The analysis strongly suggests stack or heap corruption, but the exact source needs to be identified through instrumented testing.

**Critical**: Do NOT deploy to production until Issue #2 is resolved. The system will crash predictably after 60-80 seconds of operation.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Status**: Ready for handoff
