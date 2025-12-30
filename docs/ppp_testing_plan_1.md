# PPP Connection Testing Plan and Analysis

**Document Version**: 1.1
**Date**: 2025-12-30
**Last Updated**: 2025-12-30 17:48 UTC
**Author**: Development Team
**Status**: Testing In Progress - Multiple fixes deployed, awaiting final verification

## Executive Summary

This document captures comprehensive testing of the PPP (Point-to-Point Protocol) cellular connection system in the FC-1 gateway application. Testing identified and fixed a critical bug where PPP connections were being prematurely terminated by the network manager, causing connection instability.

## Table of Contents

1. [Background](#background)
2. [System Architecture](#system-architecture)
3. [Bug Discovery and Analysis](#bug-discovery-and-analysis)
4. [Fixes Applied](#fixes-applied)
5. [Testing Conducted](#testing-conducted)
6. [Remaining Issues](#remaining-issues)
7. [Test Procedures](#test-procedures)
8. [Files Modified](#files-modified)
9. [Future Testing](#future-testing)

---

## Background

### Problem Statement
PPP connections were being terminated approximately 0.5 seconds after successfully connecting, causing a restart loop. The log pattern observed:
```
Connect: ppp0 <--> /dev/ttyACM0
Finish Pppd runit service...      # Killed ~0.5s later
Start Pppd runit service...       # Restart attempt
NO CARRIER                        # Often fails on retry
Connect script failed
```

### Impact
- Cellular connectivity unreliable
- Connections cycling repeatedly
- NO CARRIER errors after forced restarts
- System unable to maintain stable cellular link

### Discovery Method
1. Observed PPP restart pattern in logs
2. Tested with FC-1 stopped - PPP worked perfectly
3. Concluded FC-1 was interfering with pppd after connection

---

## System Architecture

### Dual Modem Configuration
The gateway contains two separate cellular modems:

| Modem | Device | Function |
|-------|--------|----------|
| Qualcomm 4108 | `/dev/ttyACM0` | Data connection (pppd uses this) |
| Cinterion PLS63-W | `/dev/ttyACM2` | AT commands (FC-1 cellular_man uses this) |

**Critical Understanding**: pppd and FC-1's cellular manager use DIFFERENT modems. They should not directly interfere with each other at the modem level.

### Key Components

#### 1. Network Manager (`process_network.c`)
- Manages multiple network interfaces (eth0, wlan0, ppp0)
- Performs health checks (ping tests) on interfaces
- Decides when to start/stop interfaces based on availability and health
- Located at: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

#### 2. Cellular Manager (`cellular_man.c`)
- Manages cellular modem initialization
- Handles carrier scanning and selection
- Controls PPP start/stop via runit service
- Maintains state flags: `cellular_now_ready`, `cellular_link_reset`, `cellular_scanning`
- Located at: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

#### 3. PPPD Service
- Runit-managed service at `/usr/qk/etc/sv/pppd/`
- Uses Qualcomm modem for data connection
- Logs to `/var/log/pppd/current`

### State Flag Interactions

The network manager checks these flags from cellular_man to decide whether to stop pppd:

| Flag | Purpose | Effect when TRUE |
|------|---------|------------------|
| `cellular_now_ready` | Cellular is initialized and ready | Prevents pppd termination |
| `cellular_link_reset` | Link reset in progress | Triggers pppd termination |
| `cellular_scanning` | Carrier scan active | Triggers pppd termination |

---

## Bug Discovery and Analysis

### Root Cause 1: Startup Race Condition

**Location**: `cellular_man.c`, CELL_INIT state (line ~3848)

**Problem**: When FC-1 detected an existing PPP connection with valid IP at startup, it incorrectly set `cellular_now_ready=false`:

```c
// BUGGY CODE
if (ppp0_has_valid_ip()) {
    set_cellular_now_ready(false);  // BUG: Should be true!
    cellular_state = CELL_QUICK_STATUS_INIT;
}
```

**Effect**: Network manager saw `cellular_now_ready=false` and stopped pppd because "other interfaces available" (eth0/wifi0 were configured).

### Root Cause 2: Network Manager Logic Flaw

**Location**: `process_network.c`, line ~4879

**Problem**: The network manager would stop pppd if `cellular_now_ready=false` OR `cellular_link_reset=true`, regardless of whether ppp0 had a working IP address:

```c
// BUGGY CODE
if ((imx_is_cellular_now_ready() == false) ||
    (imx_is_cellular_link_reset() == true) ||
    is_scanning)
{
    // Would stop pppd even if it had valid IP
    stop_pppd(false);
}
```

**Effect**: During FC-1 initialization, these flags are temporarily in "not ready" state. If pppd connected during this window, it would be killed.

### Timeline of Bug Manifestation

1. **T+0.0s**: pppd connects, creates ppp0 interface
2. **T+0.1s**: pppd obtains IP address
3. **T+0.3s**: Network manager runs periodic check
4. **T+0.3s**: Sees `cellular_now_ready=false` (FC-1 still initializing)
5. **T+0.3s**: eth0 or wifi0 configured → "other interfaces available"
6. **T+0.5s**: Network manager calls `stop_pppd()` → pppd killed
7. **T+0.6s**: runit restarts pppd
8. **T+1.0s**: NO CARRIER (modem not ready for immediate reconnect)

---

## Fixes Applied

### Fix 1: Protect Existing PPP at Startup

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`
**Location**: CELL_INIT state, line ~3847-3856

**Change**: Set `cellular_now_ready=true` when existing PPP detected:

```c
// FIXED CODE
if (ppp0_has_valid_ip()) {
    PRINTF("[Cellular Connection - INIT: Detected existing PPP0 with valid IP]\r\n");

    // CRITICAL FIX: Set cellular_now_ready=true IMMEDIATELY to protect the
    // existing PPP connection from being stopped by the network manager.
    set_cellular_now_ready(true);  // Changed from false to true
    cellular_link_reset = false;
    cellular_state = CELL_QUICK_STATUS_INIT;
}
```

### Fix 2: Don't Stop Working PPP Connections

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
**Location**: PPP management section, line ~4878-4886

**Change**: Added check for valid IP before considering pppd termination:

```c
// FIXED CODE
bool ppp_has_working_ip = has_valid_ip_address("ppp0");

// CRITICAL FIX: Don't stop pppd if it has a working IP, unless we're scanning.
if (is_scanning ||
    (!ppp_has_working_ip &&
     ((imx_is_cellular_now_ready() == false) || (imx_is_cellular_link_reset() == true))))
{
    // Only enter stop logic if:
    // 1. We're scanning (must stop for scan), OR
    // 2. PPP doesn't have IP AND (not ready OR link reset)
}
```

**Logic Explanation**:
- If scanning: Always allow stop (needed for carrier scan)
- If ppp0 has valid IP: Never stop for ready/reset flag reasons
- If ppp0 has no IP AND flags indicate not ready: Consider stopping

### Fix 3: Reset ppp_start_time After Scan (2025-12-30)

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
**Location**: PPP detection section, line ~5350-5354

**Problem**: After a cell scan, pppd is restarted by the cellular manager (`sv up pppd`), but the network manager's `ctx->ppp_start_time` is not reset. The timeout check at line ~4941 uses this old timestamp to determine if pppd has exceeded `PPP_WAIT_FOR_CONNECTION`. Since the scan takes 5+ minutes, the timeout immediately triggers, killing the just-restarted pppd.

**Change**: Reset `ppp_start_time` when detecting PPP in the scan protection window:

```c
// FIXED CODE (inside the detection block at line ~5336-5355)
if (!ctx->cellular_started)
{
    ctx->cellular_started = true;
    ctx->cellular_stopped = false;
    NETMGR_LOG_PPP0(ctx, "Marking cellular_started=true due to existing PPP0 connection");
    /* Track when PPP0 got its IP for grace period */
    imx_time_get_time(&ctx->states[IFACE_PPP].ip_obtained_time);

    /* CRITICAL FIX: Reset ppp_start_time when detecting PPP after scan.
     * After a cell scan, pppd is restarted but ppp_start_time still holds
     * the OLD value from before the scan. This causes the timeout check
     * at line ~4941 to immediately trigger because it thinks pppd has been
     * trying to connect for the entire scan duration (5+ minutes).
     * Resetting ppp_start_time here prevents this false timeout. */
    if (is_scan_protected)
    {
        imx_time_get_time(&ctx->ppp_start_time);
        NETMGR_LOG_PPP0(ctx, "Reset ppp_start_time - PPP restarted after scan");
    }
}
```

**Logic Explanation**:
- Only reset `ppp_start_time` when both:
  1. We're detecting an existing PPP connection (`!ctx->cellular_started`)
  2. We're within the scan protection window (`is_scan_protected`)
- This ensures the timeout logic correctly tracks when pppd actually started after a scan

### Fix 3b: Reset ppp_start_time Earlier (2025-12-30)

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
**Location**: Line ~4837 (when starting pppd)

**Change**: Also reset `ppp_start_time` when starting pppd during scan protection:

```c
if (imx_is_ppp_scan_protected())
{
    imx_time_get_time(&ctx->ppp_start_time);
    NETMGR_LOG_PPP0(ctx, "Reset ppp_start_time - starting PPP in scan protection window");
}
```

### Fix 3c: Protection Check in CELL_STOP_PPP_INIT (2025-12-30)

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`
**Location**: CELL_STOP_PPP_INIT state

**Change**: Skip PPP stop if scan protection is active and ppp0 has valid IP

### Fix 4: Change sv restart to sv up (2025-12-30)

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`
**Location**: `start_pppd()` function, line ~3261

**Problem**: The `start_pppd()` function was using `sv restart pppd` which kills any existing pppd process before starting. During scan recovery, this was killing the pppd that just connected.

**Change**: Changed from `sv restart` to `sv up`:

```c
// OLD (problematic):
system("sv restart pppd 2>/dev/null");

// NEW (fixed):
system("sv up pppd 2>/dev/null");
```

**Rationale**:
- `sv restart` = stop + start (kills existing process)
- `sv up` = ensure running (no-op if already running)

This prevents killing a just-connected pppd process during scan recovery.

---

## Testing Conducted

### Test 1: Basic Connectivity (PASSED)

**Date**: 2025-12-30
**Objective**: Verify PPP stays connected when FC-1 starts

**Procedure**:
1. Deploy fixed FC-1 binary
2. Start FC-1 service
3. Wait for PPP to connect
4. Monitor for 60+ seconds

**Results**:
- PPP connected successfully
- Connection stable for 10+ minutes
- No restart loop observed

**Evidence**:
```
Status:     [OK] CONNECTED
Local IP:   10.183.201.229
Uptime:     10m 33s
```

### Test 2: Cell Scan and Reconnection (PARTIAL PASS)

**Date**: 2025-12-30
**Objective**: Verify PPP reconnects properly after carrier scan

**Procedure**:
1. Verify PPP connected on AT&T (initial carrier)
2. Trigger cell scan via CLI: `cell scan`
3. Monitor scan progress (3-5 minutes)
4. Verify PPP reconnects after scan

**Results**:
- Scan triggered successfully
- Carriers found: FirstNet (313100), AT&T (310410), Verizon (311480), T-Mobile (310260)
- Best carrier selected: Verizon Wireless Global IoT
- **Issue**: First reconnection attempt killed after 0.5s
- **Recovery**: System recovered on 4th retry, stable since

**Evidence**:
```
15:48:11.57  Connect: ppp0 <--> /dev/ttyACM0
15:48:12.14  Finish Pppd runit service...  # Killed!
15:48:13     Connect script failed
15:48:15     NO CARRIER
15:48:25     Connect: ppp0 <--> /dev/ttyACM0  # Success
[Stable for 3+ minutes after]
```

**Final State**:
```
Carrier:    Verizon Wireless Global IoT
Status:     [OK] CONNECTED
Uptime:     3m 47s
```

---

## Remaining Issues

### Issue 1: Post-Scan PPP Kill (MULTIPLE FIXES APPLIED - 2025-12-30)

**Severity**: Medium (system recovers, but causes delay)

**Status**: **FIXES APPLIED - AWAITING FINAL VERIFICATION**

**Description**: After carrier scan completion, the first PPP reconnection attempt was being killed ~0.5s after connecting. The system would eventually recover after multiple retries.

**Root Causes Identified**:

1. **ppp_start_time not reset**: When pppd restarts after a scan, `ctx->ppp_start_time` was NOT being reset. The timeout check would immediately trigger using the old timestamp.

2. **sv restart killing pppd**: The `start_pppd()` function was using `sv restart pppd` which kills any existing pppd process before starting, including one that just connected.

**Fixes Applied**:

| Fix | File | Location | Change |
|-----|------|----------|--------|
| Fix 3 | `process_network.c` | Line ~5350 | Reset ppp_start_time in scan protection window |
| Fix 3b | `process_network.c` | Line ~4837 | Reset ppp_start_time when starting PPP during scan protection |
| Fix 3c | `cellular_man.c` | CELL_STOP_PPP_INIT | Skip PPP stop if protection active and has IP |
| Fix 4 | `cellular_man.c` | Line ~3261 | Change `sv restart pppd` to `sv up pppd` |

**Latest Test (2025-12-30 17:46 UTC)**:
- All fixes deployed
- PPP connected and stable (IP: 10.183.201.229, uptime: 1m 44s)
- Some kill/retry cycles still observed during scan - needs re-verification
- See `docs/ppp_testing_status.md` for full handoff details

### Issue 2: Carrier Scan Timeout (FIXED in previous session)

**Status**: Fixed

**Previous Problem**: Scan timeout was 180s but scans take 180-240s

**Fix Applied**: Changed timeout from 180000ms to 270000ms

---

## Test Procedures

### Procedure A: Basic PPP Stability Test

```bash
# 1. Deploy and start FC-1
cd /home/greg/iMatrix/iMatrix_Client/scripts
./fc1 push -run

# 2. Wait 20 seconds for initialization
sleep 20

# 3. Check PPP status
./fc1 ppp

# 4. Verify:
#    - Status: CONNECTED
#    - Has valid IP address
#    - Uptime increasing (not restarting)

# 5. Wait another 60 seconds and check again
sleep 60
./fc1 ppp

# 6. PASS if uptime > 60s with same PID
```

### Procedure B: Cell Scan Test

```bash
# 1. Verify initial state
./fc1 ppp   # Should show CONNECTED

# 2. Connect to FC-1 CLI
ssh -p 22222 root@192.168.7.1
microcom /dev/pts/2
# Press Enter for prompt

# 3. Note current carrier
cell status

# 4. Trigger scan
cell scan

# 5. Monitor debug output for ~5 minutes
#    Watch for:
#    - "Scanning for operators"
#    - "Selected best operator"
#    - "Scan complete"

# 6. Exit microcom (Ctrl+X)

# 7. Verify reconnection
./fc1 ppp

# 8. PASS if:
#    - PPP reconnected
#    - Uptime > 60s
#    - Connection stable
```

### Procedure C: Stress Test (Repeated Scans)

```bash
# Run 3 consecutive scans with 5-minute intervals
for i in 1 2 3; do
    echo "=== Scan $i ==="
    sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 \
        "echo 'cell scan' > /dev/pts/2"
    sleep 300  # Wait 5 minutes
    ./fc1 ppp
    echo "---"
done

# PASS if all 3 scans complete with successful reconnection
```

---

## Files Modified

### Primary Files

| File | Changes | Purpose |
|------|---------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | Lines 3847-3856 | Fix 1: Protect existing PPP |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Lines 4878-4886 | Fix 2: Don't kill working PPP |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Lines 5350-5354 | Fix 3: Reset ppp_start_time after scan |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Line ~4837 | Fix 3b: Reset ppp_start_time when starting PPP |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | CELL_STOP_PPP_INIT | Fix 3c: Skip stop if protected with IP |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | Line ~3261 | Fix 4: sv restart → sv up |

### Supporting Files

| File | Changes | Purpose |
|------|---------|---------|
| `cellular_man.c` | Lines 4642, 4757, 5029 | Scan timeout and AT+COPS fixes |
| `cellular_man.c` | Line 393 | Added access_technology to operator_info_t |
| `scripts/fc1` | Added push command | Deployment helper |

### Detailed Change Locations

#### cellular_man.c

```c
// Line 393 - Added field to struct
typedef struct {
    char operator_id[16];
    char operator_name[64];
    int signal_strength;
    int access_technology;  // ADDED: Network access technology (7=LTE)
    bool blacklisted;
    bool tested;
} operator_info_t;

// Line 3847-3856 - CELL_INIT fix
if (ppp0_has_valid_ip()) {
    set_cellular_now_ready(true);  // CHANGED: was false
    ...
}

// Line 4642 - Scan timeout
scan_timeout = current_time + 270000;  // CHANGED: was 180000

// Line 4757 - AT+COPS with access technology
snprintf(cmd, sizeof(cmd), "+COPS=1,2,\"%s\",%d",
         op->operator_id, op->access_technology);  // ADDED: access_technology

// Line 5029 - Same fix for CELL_SCAN_CONNECT_BEST
snprintf(cmd, sizeof(cmd), "+COPS=1,2,\"%s\",%d",
         best->operator_id, best->access_technology);
```

#### process_network.c

```c
// Lines 4878-4886 - PPP stop logic fix (Fix 2)
bool ppp_has_working_ip = has_valid_ip_address("ppp0");  // ADDED

if (is_scanning ||
    (!ppp_has_working_ip &&  // ADDED: Only if no working IP
     ((imx_is_cellular_now_ready() == false) ||
      (imx_is_cellular_link_reset() == true))))
{
    // Stop logic here
}

// Lines 5350-5354 - Reset ppp_start_time after scan (Fix 3)
if (is_scan_protected)
{
    imx_time_get_time(&ctx->ppp_start_time);
    NETMGR_LOG_PPP0(ctx, "Reset ppp_start_time - PPP restarted after scan");
}
```

---

## Future Testing

### Priority 1: Verify Post-Scan Kill Fix (READY FOR TESTING)

**Status**: Fix 3 applied - needs verification testing

**Objective**: Confirm PPP reconnects on first attempt after scan (no more kill/retry cycle)

**Test Procedure**:
1. Deploy FC-1 with Fix 3: `./fc1 push -run`
2. Wait for initial PPP connection
3. Trigger cell scan: `cell scan` via CLI
4. Monitor for PPP reconnection after scan completes
5. **PASS**: PPP connects on FIRST attempt, no "Finish Pppd runit service" message
6. **FAIL**: PPP still killed after connecting (indicates additional fix needed)

**Expected Log Pattern (SUCCESS)**:
```
[Cellular Scan - State 11: Scan complete]
[Cellular Scan - Set cellular_now_ready=true BEFORE starting PPPD]
[Cellular Scan - PPP protection window set for 30000 ms]
Connect: ppp0 <--> /dev/ttyACM0
[PPP0] Reset ppp_start_time - PPP restarted after scan
local IP address X.X.X.X
```

**What was fixed**: The root cause was `ctx->ppp_start_time` not being reset when PPP restarts after scan, causing the timeout check to immediately trigger.

### Priority 2: Multi-Carrier Testing

**Objective**: Verify connection stability on all available carriers

**Test Matrix**:
| Carrier | Manual Select | Auto Select | Stability |
|---------|--------------|-------------|-----------|
| AT&T | TBD | TBD | TBD |
| Verizon | TBD | Tested - OK | TBD |
| T-Mobile | TBD | TBD | TBD |
| FirstNet | TBD | TBD | TBD |

### Priority 3: Long-Duration Stability

**Objective**: Verify 24+ hour stability

**Procedure**:
1. Deploy fixed build
2. Let run for 24 hours
3. Monitor via periodic status checks
4. Log any disconnections/reconnections

### Priority 4: Edge Cases

**Test Cases to Add**:
- [ ] PPP behavior when modem loses signal
- [ ] Recovery from modem crash
- [ ] Behavior during firmware updates
- [ ] Simultaneous WiFi and cellular usage
- [ ] Rapid carrier switching (scan while connecting)

---

## Appendix A: Useful Commands

```bash
# PPP status (from host)
./fc1 ppp

# Cellular status (from FC-1 CLI)
cell status
cell operators
cell blacklist

# Force carrier selection (from FC-1 CLI)
cell scan

# Restart services (from gateway SSH)
sv restart FC-1
sv restart pppd

# View logs
tail -f /var/log/FC-1/current
tail -f /var/log/pppd/current

# Direct modem access
microcom /dev/ttyACM2
AT+COPS?     # Current carrier
AT+CSQ       # Signal strength
```

## Appendix B: Log Patterns

### Healthy Connection
```
Connect: ppp0 <--> /dev/ttyACM0
sent [LCP ConfReq ...]
rcvd [LCP ConfAck ...]
sent [IPCP ConfReq ...]
rcvd [IPCP ConfAck ...]
local IP address X.X.X.X
```

### Bug Pattern (PPP Kill)
```
Connect: ppp0 <--> /dev/ttyACM0
Finish Pppd runit service...     # <-- Killed too fast
Start Pppd runit service...
NO CARRIER
Connect script failed
```

### Successful Scan Completion
```
[Cellular Scan - State 11: Scan complete]
[Cellular Scan - Set cellular_now_ready=true BEFORE starting PPPD]
[Cellular Scan - PPP protection window set for 30000 ms]
[Cellular Scan - Re-enabling runsv supervision: sv up pppd]
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-30 | Initial document |

---

*Related Documents:*
- `docs/testing_fc_1_application.md` - FC-1 testing procedures
- `docs/gen/cell_scan_test_plan.md` - Cell scan test checklist
