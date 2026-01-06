# PPP Testing Status - Handoff Document

**Date**: 2025-12-30
**Last Updated**: 17:48 UTC
**Status**: Testing in progress - Fix applied, awaiting verification

---

## Executive Summary

We are fixing a bug where PPP is killed immediately after connecting following a cell scan. Multiple fixes have been applied and deployed. The current test is in progress.

---

## The Problem

After a carrier scan completes, pppd is restarted but gets killed ~0.5 seconds after connecting. The system eventually recovers after multiple retry attempts, but this causes unnecessary delays.

**Symptom Pattern in Logs**:
```
Connect: ppp0 <--> /dev/ttyACM0
Finish Pppd runit service...        # Killed 0.5s after connect!
Start Pppd runit service...
NO CARRIER
Connect script failed
```

---

## Root Causes Identified

### Root Cause 1: ppp_start_time Not Reset
When pppd restarts after a scan, `ctx->ppp_start_time` was NOT being reset. The network manager's timeout check uses this old timestamp (from before the 5+ minute scan), causing an immediate false timeout.

**Location**: `process_network.c` line ~4941
```c
if (imx_is_later(current_time, ctx->ppp_start_time + ctx->config.PPP_WAIT_FOR_CONNECTION))
```

### Root Cause 2: sv restart vs sv up
The `start_pppd()` function was using `sv restart pppd` which kills any existing pppd process. During scan recovery, this was killing the pppd that just connected.

**Location**: `cellular_man.c` line ~3261

---

## Fixes Applied

### Fix 1: Protect Existing PPP at Startup (Previous Session)
**File**: `cellular_man.c` lines 3847-3856
**Change**: Set `cellular_now_ready=true` when existing PPP detected at startup

### Fix 2: Don't Stop Working PPP Connections (Previous Session)
**File**: `process_network.c` lines 4878-4886
**Change**: Added `ppp_has_working_ip` check before considering pppd termination

### Fix 3: Reset ppp_start_time After Scan (This Session)
**File**: `process_network.c` lines 5350-5354
**Change**: Reset `ppp_start_time` when detecting PPP in scan protection window

```c
if (is_scan_protected)
{
    imx_time_get_time(&ctx->ppp_start_time);
    NETMGR_LOG_PPP0(ctx, "Reset ppp_start_time - PPP restarted after scan");
}
```

### Fix 3b: Reset ppp_start_time Earlier (This Session)
**File**: `process_network.c` line ~4837
**Change**: Also reset `ppp_start_time` when starting pppd during scan protection

### Fix 3c: Protection Check in CELL_STOP_PPP_INIT
**File**: `cellular_man.c` in CELL_STOP_PPP_INIT state
**Change**: Skip PPP stop if scan protection is active and ppp0 has valid IP

### Fix 4: Change sv restart to sv up (This Session - LATEST)
**File**: `cellular_man.c` line ~3261 in `start_pppd()`
**Change**: Changed from `sv restart pppd` to `sv up pppd`

```c
// OLD (problematic):
system("sv restart pppd 2>/dev/null");

// NEW (fixed):
system("sv up pppd 2>/dev/null");
```

**Rationale**: `sv restart` kills any running pppd, then starts fresh. `sv up` just ensures the service is running without killing an existing process.

---

## Current Deployment Status

**Build**: Compiled successfully with all fixes
**Deployed**: Yes, to gateway at 192.168.7.1
**FC-1 Status**: Running (restarted with new binary)

---

## Test Results

### Test 1: Initial PPP Stability - PASSED
- PPP connected after FC-1 restart
- IP: 10.183.201.229
- Stable connection

### Test 2: Cell Scan Reconnection - IN PROGRESS
- Cell scan triggered via CLI
- Scan completed (selected AT&T)
- PPP eventually reconnected and is stable (uptime 1m 44s as of last check)
- BUT: Still saw some kill/retry cycles before stabilizing

**Last Known PPP Status**:
```
Status:     [OK] CONNECTED
Local IP:   10.183.201.229
Uptime:     1m 44s
```

---

## How to Continue Testing

### 1. Check Current PPP Status
```bash
cd /home/greg/iMatrix/iMatrix_Client/scripts
./fc1 ppp
```

### 2. Run Another Cell Scan Test
```bash
# SSH to gateway
ssh -p 22222 root@192.168.7.1
# Password: PasswordQConnect

# Connect to FC-1 CLI
microcom /dev/pts/2
# Press Enter

# Trigger scan
cell scan

# Monitor for 3-5 minutes
# Exit microcom: Ctrl+X
```

### 3. Check PPP Log for Kill Pattern
```bash
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 \
  "cat /var/log/pppd/current | tail -100"
```

**Look for**:
- `Connect: ppp0 <--> /dev/ttyACM0` followed immediately by
- `Finish Pppd runit service...` = PPP was killed (BAD)
- `local IP address X.X.X.X` without kill message = Success (GOOD)

### 4. Look for Fix Log Messages
```bash
# Check for "Reset ppp_start_time" message (Fix 3)
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 \
  "dmesg | grep -i 'ppp_start_time\|scan.*protect'"
```

---

## Key Files and Locations

| File | Key Lines | Purpose |
|------|-----------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | 4837, 4878-4886, 4941, 5350-5354 | Network manager PPP handling |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | 3261, 3847-3856, 5352-5390 | Cellular state machine, start_pppd |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.h` | 97-98 | Protection window function declarations |

---

## Quick Commands Reference

```bash
# Deploy new build
cd /home/greg/iMatrix/iMatrix_Client/scripts
./fc1 push -run

# Check status
./fc1 status
./fc1 ppp

# Restart FC-1
./fc1 restart

# View logs
./fc1 log

# SSH to gateway
ssh -p 22222 root@192.168.7.1
# Password: PasswordQConnect

# FC-1 CLI via microcom
microcom /dev/pts/2
# Exit: Ctrl+X

# Useful CLI commands
cell status
cell scan
ppp
```

---

## What Success Looks Like

After a cell scan, the PPP log should show:
```
[Cellular Scan - State 11: Scan complete]
[Cellular Scan - PPP protection window set for 30000 ms]
Connect: ppp0 <--> /dev/ttyACM0
[PPP0] Reset ppp_start_time - PPP restarted after scan
local IP address X.X.X.X
```

**NO** `Finish Pppd runit service...` message between `Connect:` and `local IP address`.

---

## If Testing Fails (PPP Still Being Killed)

### Additional Debug Steps

1. **Add more logging** to trace which code path is killing pppd:
   - In `process_network.c` before each `stop_pppd()` call
   - In `cellular_man.c` in CELL_STOP_PPP states

2. **Check threading**: The cellular manager and network manager may have race conditions

3. **Check protection window timing**: Verify `imx_is_ppp_scan_protected()` returns true when expected

4. **Possible additional fix locations**:
   - `process_network.c` line 4922 - another stop_pppd call
   - `process_network.c` line 4963 - timeout stop path
   - Any other `sv down pppd` or `killall pppd` calls

---

## Related Documentation

- `docs/ppp_testing_plan_1.md` - Full testing plan and history
- `docs/testing_fc_1_application.md` - FC-1 CLI access guide
- `docs/gen/fix3_deployment_test_plan.md` - Deployment procedure
- `docs/gen/cell_scan_test_plan.md` - Cell scan test procedure

---

## Contact / Notes

- All fixes are in the iMatrix submodule
- Build is in Fleet-Connect-1/build/FC-1
- Gateway IP: 192.168.7.1, SSH port 22222
- Current carrier after last scan: AT&T Global IoT

---

**Next Step**: Verify if the latest fix (sv up instead of sv restart) resolved the issue by running another cell scan test and checking if PPP connects on the first attempt without being killed.
