# Implementation Plan: Fix Cell Scan PPP Reconnection Failure

**Date:** 2025-12-29
**Author:** Claude Code Analysis
**Status:** READY FOR IMPLEMENTATION
**Related Analysis:** `docs/gen/cell_scan_ppp_reconnection_failure_analysis.md`

---

## 1. Problem Summary

After a cell scan operation completes, the PPP connection fails to re-establish because:

1. **Flag Synchronization Failure**: `cellular_ready` remains `NO` after `sv up pppd` is called
2. **Premature PPP Termination**: Network Manager kills PPPD because flags indicate PPP is "not ready"
3. **Connect Script Failure**: Subsequent PPPD attempts fail because modem is in unstable state

**Important Clarification:**
- The "not replacing default route to wlan0" message is **expected behavior**, not an error
- Per Network Manager Architecture: eth0 → wlan0 → ppp0 priority order
- wlan0 **keeps default route** when connected; ppp0 is backup for when wlan0 fails
- Bringing back ppp0 does NOT constitute making it the default route

---

## 2. Root Cause Details

### 2.1 Current Broken Flow
```
SCAN_COMPLETE
    ↓
sv up pppd (starts PPPD)
    ↓
WAIT_PPP_STARTUP state entered
    ↓
PPPD gets IP from carrier
    ↓
Network Manager checks ppp0:
  - cellular_ready=NO (WRONG!)
  - cellular_started=NO (WRONG!)
    ↓
Network Manager skips ppp0 testing
    ↓
"PPP0 timeout" detected
    ↓
Network Manager KILLS PPPD  ← BUG
    ↓
runsv restarts PPPD
    ↓
Connect script fails (modem unstable after forced kill)
```

### 2.2 Expected Correct Flow
```
SCAN_COMPLETE
    ↓
Set cellular_ready=YES, cellular_started=YES  ← FIX #1
    ↓
sv up pppd (starts PPPD)
    ↓
WAIT_PPP_STARTUP with protection window     ← FIX #2
    ↓
PPPD gets IP from carrier
    ↓
Network Manager checks ppp0:
  - cellular_ready=YES
  - cellular_started=YES
  - has_ip=YES
    ↓
Network Manager runs ping test on ppp0
    ↓
PPP tested successfully (backup link available)
    ↓
wlan0 remains default route (correct - higher priority)
    ↓
ppp0 available as backup when wlan0 fails
```

---

## 3. Implementation Tasks

### 3.1 Task 1: Set Flags BEFORE Starting PPPD (CRITICAL)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location:** `SCAN_COMPLETE` state handler (around line 1050-1080)

**Current Code:**
```c
case CELL_SCAN_COMPLETE:
    // ... scan completion logging ...
    imx_printf("[Cellular Scan - Re-enabling runsv supervision: sv up pppd]\n");
    system("sv up pppd 2>/dev/null");
    cellular_state = CELL_WAIT_PPP_STARTUP;
    // ... cellular_now_ready set later when PPP interface detected ...
```

**Required Change:**
```c
case CELL_SCAN_COMPLETE:
    // ... scan completion logging ...

    // CRITICAL: Set flags BEFORE starting PPPD so Network Manager doesn't kill it
    imx_printf("[Cellular Scan - Setting cellular_ready=YES before starting PPPD]\n");
    cellular_now_ready = true;  // Tell network manager cellular is ready

    imx_printf("[Cellular Scan - Re-enabling runsv supervision: sv up pppd]\n");
    system("sv up pppd 2>/dev/null");

    // Set protection window to prevent premature termination
    ppp_scan_protection_until = current_time + SCAN_PPP_PROTECTION_MS;  // 30 seconds

    cellular_state = CELL_WAIT_PPP_STARTUP;
```

**New Define:**
```c
#define SCAN_PPP_PROTECTION_MS  30000  // 30 seconds protection after scan
```

**New Variable:**
```c
static imx_time_t ppp_scan_protection_until = 0;
```

---

### 3.2 Task 2: Add Protection Window Check (CRITICAL)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Purpose:** Provide API for Network Manager to check if PPP is protected after scan.

**Add New Function:**
```c
/**
 * @brief Check if PPP is in scan recovery protection window
 * @return true if PPP should not be terminated, false otherwise
 *
 * After a cell scan completes, PPP needs time to re-establish connection.
 * This function returns true during the protection window (30 seconds).
 */
bool imx_is_ppp_scan_protected(void)
{
    if (ppp_scan_protection_until == 0) {
        return false;
    }

    imx_time_t current_time;
    imx_time_get_time(&current_time);

    if (imx_is_later(current_time, ppp_scan_protection_until)) {
        // Protection window expired
        ppp_scan_protection_until = 0;
        return false;
    }

    return true;
}
```

**Add to header:** `cellular_man.h`
```c
extern bool imx_is_ppp_scan_protected(void);
```

---

### 3.3 Task 3: Network Manager - Respect Protection Window (CRITICAL)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

**Location:** PPP timeout/termination logic (around line 5700-5800)

**Find code similar to:**
```c
// "PPP0 timeout but other interfaces available, stopping without blacklist"
if (ppp_timeout_detected && other_interfaces_available) {
    stop_pppd(false);  // This kills PPP prematurely!
}
```

**Add Protection Check:**
```c
// Check if PPP is in scan recovery protection window
if (imx_is_ppp_scan_protected()) {
    imx_printf("[NETMGR-PPP0] PPP in scan recovery protection window, skipping termination\n");
    // Don't terminate - let it finish connecting
} else if (ppp_timeout_detected && other_interfaces_available) {
    imx_printf("[NETMGR-PPP0] PPP0 timeout but other interfaces available, stopping without blacklist\n");
    stop_pppd(false);
}
```

---

### 3.4 Task 4: Network Manager - Allow Testing When Scan Protected

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

**Location:** Where ppp0 is skipped due to cellular_ready=NO

**Current Logic:**
```c
if (!imx_is_cellular_now_ready() || !ctx->cellular_started) {
    imx_printf("[NETMGR-PPP0] Skipping ppp0: cellular_ready=NO, cellular_started=NO\n");
    // Skip PPP testing
}
```

**Modified Logic:**
```c
bool cellular_ready = imx_is_cellular_now_ready();
bool scan_protected = imx_is_ppp_scan_protected();

if (!cellular_ready && !scan_protected) {
    imx_printf("[NETMGR-PPP0] Skipping ppp0: cellular_ready=NO, not scan protected\n");
    // Skip PPP testing
} else if (!cellular_ready && scan_protected) {
    imx_printf("[NETMGR-PPP0] PPP in scan recovery, allowing test despite cellular_ready=NO\n");
    // Allow testing - scan just completed
}
```

---

### 3.5 Task 5: Add Modem Stabilization State (REQUIRED)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location:** After `SCAN_VERIFY_CARRIER` confirms carrier switch, before `SCAN_COMPLETE`

**Purpose:** Give modem time to stabilize on new carrier before starting PPP. This state NEEDS TO BE ADDED.

**New Enum Value:**
```c
// Add to CellularState_t enum
CELL_SCAN_STABILIZE,        // Wait for modem to stabilize after carrier switch
```

**New State String:**
```c
// Add to state string array
"SCAN_STABILIZE",
```

**New Variable:**
```c
static imx_time_t stabilize_timeout = 0;
```

**New Define:**
```c
#define CARRIER_STABILIZE_MS  2000  // 2 seconds - VALIDATE AFTER TESTING
```

**Implementation - Modify SCAN_VERIFY_CARRIER exit:**
```c
case CELL_SCAN_VERIFY_CARRIER:
    // ... existing verification code ...
    if (carrier_verified_successfully) {
        imx_printf("[Cellular Scan - Carrier verified, starting stabilization]\n");
        stabilize_timeout = current_time + CARRIER_STABILIZE_MS;
        cellular_state = CELL_SCAN_STABILIZE;  // NEW: Go to stabilize first
    }
    break;
```

**Implementation - New SCAN_STABILIZE state:**
```c
case CELL_SCAN_STABILIZE:
    // Wait for modem to stabilize on new carrier before starting PPP
    if (imx_is_later(current_time, stabilize_timeout)) {
        imx_printf("[Cellular Scan - Modem stabilization complete (%d ms)]\n",
                   CARRIER_STABILIZE_MS);
        cellular_state = CELL_SCAN_COMPLETE;
    }
    // Stay in this state until timeout expires
    break;
```

---

### 3.6 Task 6: Update WAIT_PPP_STARTUP State

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location:** `CELL_WAIT_PPP_STARTUP` state handler

**Current Issue:** This state detects PPP interface and sets `cellular_now_ready`, but by then Network Manager may have already killed PPP.

**Updated Logic:**
```c
case CELL_WAIT_PPP_STARTUP:
    // cellular_now_ready already set in SCAN_COMPLETE (Task 1)

    if (ppp0_has_valid_ip()) {
        imx_printf("[Cellular Scan - PPP interface detected with valid IP]\n");

        // Clear protection window early since PPP connected successfully
        ppp_scan_protection_until = 0;

        // Verify connection with AT+COPS?
        cellular_state = CELL_ONLINE;
    } else if (imx_is_later(current_time, ppp_startup_timeout)) {
        imx_printf("[Cellular Scan - PPP startup timeout, connection failed]\n");

        // Clear protection window
        ppp_scan_protection_until = 0;

        // Handle timeout - blacklist carrier or retry
        cellular_state = CELL_ONLINE;  // Fall back to online state
        cellular_now_ready = false;  // Mark as not ready since PPP failed
    }
    break;
```

---

### 3.7 Task 7: Clear Protection Window on PPP Stop

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**Location:** `stop_pppd()` function

**Add at start of function:**
```c
void stop_pppd(bool cellular_reset)
{
    // Clear scan protection window when PPP is explicitly stopped
    ppp_scan_protection_until = 0;

    // ... rest of existing code ...
}
```

---

## 4. File Changes Summary

| File | Changes |
|------|---------|
| `cellular_man.c` | Add SCAN_PPP_PROTECTION_MS define |
| `cellular_man.c` | Add ppp_scan_protection_until variable |
| `cellular_man.c` | Set cellular_now_ready=true BEFORE sv up pppd in SCAN_COMPLETE |
| `cellular_man.c` | Add imx_is_ppp_scan_protected() function |
| `cellular_man.c` | Add CARRIER_STABILIZE_MS delay before SCAN_COMPLETE |
| `cellular_man.c` | Update WAIT_PPP_STARTUP to handle protection window |
| `cellular_man.c` | Clear protection window in stop_pppd() |
| `cellular_man.h` | Declare imx_is_ppp_scan_protected() |
| `process_network.c` | Check imx_is_ppp_scan_protected() before terminating PPP |
| `process_network.c` | Allow PPP testing when scan protected even if cellular_ready=NO |

---

## 5. Testing Plan

### 5.1 Pre-Test: Verify Current Failure
```bash
./fc1 ppp         # Verify PPP working
cell scan         # Trigger scan via CLI
./fc1 ppp         # Should fail (current behavior)
```

### 5.2 Post-Implementation Tests

**Test 1: Basic Scan Recovery**
```bash
./fc1 ppp         # Verify PPP working (has IP)
cell scan         # Trigger scan
# Wait for scan to complete (~2 minutes)
./fc1 ppp         # Verify PPP reconnected
```

**Test 2: Verify wlan0 Keeps Default Route**
```bash
./fc1 ssh
ip route          # Should show: default via 10.2.0.1 dev wlan0
                  # ppp0 should NOT have default route
```

**Test 3: Verify PPP Used on wlan0 Failure**
```bash
./fc1 ssh
ip link set wlan0 down   # Simulate wlan0 failure
ip route                  # Should now show: default dev ppp0
```

**Test 4: Check Logs for Correct Sequence**
```bash
# Look for these log messages in order:
[Cellular Scan - Setting cellular_ready=YES before starting PPPD]
[Cellular Scan - Re-enabling runsv supervision: sv up pppd]
[NETMGR-PPP0] PPP in scan recovery protection window, skipping termination
[Cellular Scan - PPP interface detected with valid IP]
```

**Test 5: No "Connect script failed" Errors**
```bash
# After scan, verify no errors in syslog:
./fc1 ssh
dmesg | grep pppd
# Should NOT see: "Connect script failed"
```

### 5.3 Expected Final State After Scan

```
+==================================================+
| INTERFACE | ACTIVE | LINK_UP | IP_ADDRESS        |
+-----------+--------+---------+-------------------+
| eth0      | NO     | NO      | 192.168.7.1       |
| wlan0     | YES    | YES     | 10.2.0.179        |  ← DEFAULT ROUTE
| ppp0      | YES    | YES     | 10.x.x.x          |  ← BACKUP (no default route)
+==================================================+

Routing table:
default via 10.2.0.1 dev wlan0     ← wlan0 is primary
10.x.x.x dev ppp0 proto kernel     ← ppp0 connected but NOT default
```

---

## 6. Implementation Checklist

- [ ] **Task 1**: Set cellular_now_ready=true BEFORE sv up pppd in SCAN_COMPLETE state
- [ ] **Task 2**: Add imx_is_ppp_scan_protected() function and ppp_scan_protection_until variable
- [ ] **Task 3**: Network Manager - check protection window before terminating PPP
- [ ] **Task 4**: Network Manager - allow PPP testing when scan protected
- [ ] **Task 5**: Add CELL_SCAN_STABILIZE state (REQUIRED - needs to be added)
- [ ] **Task 6**: Update WAIT_PPP_STARTUP to clear protection on success/timeout
- [ ] **Task 7**: Clear protection window in stop_pppd()
- [ ] **Task 8**: Add imx_is_ppp_scan_protected() to cellular_man.h header
- [ ] **Test**: Verify scan recovery works
- [ ] **Test**: Verify wlan0 keeps default route
- [ ] **Test**: Verify no "Connect script failed" errors
- [ ] **Test**: Verify PPP takes over when wlan0 fails
- [ ] **Validate**: SCAN_PPP_PROTECTION_MS (30s initial) - adjust based on testing
- [ ] **Validate**: CARRIER_STABILIZE_MS (2s initial) - adjust based on testing

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Protection window too short | Low | PPP still terminated | Increase from 30s to 45s if needed |
| Protection window too long | Low | Delayed failover | 30s is reasonable; can tune |
| Flag race conditions | Medium | Intermittent failures | Use mutex if issues persist |
| Modem stabilization insufficient | Low | Connect failures | Increase CARRIER_STABILIZE_MS |

---

## 8. Configuration Values Requiring Validation

> **IMPORTANT**: The following timing values are initial estimates and MUST be validated through testing on actual hardware. Adjust as needed based on test results.

### 8.1 Protection Window Duration
```c
#define SCAN_PPP_PROTECTION_MS  30000  // 30 seconds - VALIDATE AFTER TESTING
```
- **Initial Value**: 30 seconds
- **Rationale**: Allows time for PPP to establish connection after scan
- **Validation Required**: Test with actual cell scan and measure time to PPP IP assignment
- **Adjustment**: Increase if PPP still terminated before connection; decrease if failover too slow

### 8.2 Carrier Stabilization Delay
```c
#define CARRIER_STABILIZE_MS  2000  // 2 seconds - VALIDATE AFTER TESTING
```
- **Initial Value**: 2 seconds
- **Rationale**: Modem needs time to register on new carrier after AT+COPS
- **Validation Required**: Test carrier switching and check for "Connect script failed" errors
- **Adjustment**: Increase if connect failures persist; decrease if connection is reliable

### 8.3 Stabilization State
- **Status**: NEEDS TO BE ADDED
- **Location**: Add new `CELL_SCAN_STABILIZE` state between `SCAN_CONNECT_BEST` and `SCAN_COMPLETE`

---

## 9. Post-Implementation Validation Checklist

After implementing fixes, perform these tests to validate timing values:

- [ ] **Test 1**: Run cell scan 5 times, record time from `sv up pppd` to PPP IP assignment
  - If > 25 seconds average: Increase SCAN_PPP_PROTECTION_MS
  - If < 10 seconds average: Can reduce SCAN_PPP_PROTECTION_MS

- [ ] **Test 2**: Check for "Connect script failed" errors after scan
  - If errors occur: Increase CARRIER_STABILIZE_MS by 1 second increments
  - If no errors with 2s: Value is adequate

- [ ] **Test 3**: Measure total scan recovery time (scan start to PPP connected)
  - Target: < 3 minutes total
  - If too slow: Review if delays can be reduced

- [ ] **Test 4**: Stress test - run 10 consecutive scans
  - All should recover PPP successfully
  - Note any intermittent failures for timing adjustment

---

**Document End**
