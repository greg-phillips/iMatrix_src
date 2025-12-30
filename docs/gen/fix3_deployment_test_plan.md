# Fix 3/3b/3c/4 Deployment and Test Plan

**Date**: 2025-12-30
**Last Updated**: 2025-12-30 17:48 UTC
**Fix**: Post-Scan PPP Kill Fix (Multiple Fixes Applied)
**Status**: Deployed - Awaiting Final Verification

---

## Overview

This plan covers deployment and verification testing of Fixes 3, 3b, 3c, and 4, which address the post-scan PPP kill issue where pppd was being terminated ~0.5s after connecting following a carrier scan.

**Root Causes Fixed**:
1. `ctx->ppp_start_time` was not being reset when PPP restarts after scan, causing false timeout detection
2. `sv restart pppd` was killing existing pppd processes during scan recovery

## All Fixes Applied

| Fix | File | Location | Description |
|-----|------|----------|-------------|
| Fix 3 | process_network.c | Lines 5350-5354 | Reset ppp_start_time in scan protection window |
| Fix 3b | process_network.c | Line ~4837 | Reset ppp_start_time when starting PPP during protection |
| Fix 3c | cellular_man.c | CELL_STOP_PPP_INIT | Skip PPP stop if protection active and has IP |
| Fix 4 | cellular_man.c | Line ~3261 | Changed `sv restart pppd` to `sv up pppd` |

---

## Pre-Deployment Checklist

- [x] Fix 3 applied to `process_network.c` lines 5350-5354
- [x] Fix 3b applied to `process_network.c` line ~4837
- [x] Fix 3c applied to `cellular_man.c` CELL_STOP_PPP_INIT state
- [x] Fix 4 applied to `cellular_man.c` line ~3261
- [x] Build successful (FC-1 binary compiled)
- [x] Documentation updated
- [x] **Deployed to gateway** (2025-12-30 17:30 UTC)

---

## Deployment Steps

### Step 1: Verify Build

```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
ls -la FC-1
# Verify timestamp is recent
```

### Step 2: Deploy to Gateway

```bash
cd /home/greg/iMatrix/iMatrix_Client/scripts
./fc1 push -run
```

This command will:
1. Stop the running FC-1 service
2. Copy the new binary to `/usr/qk/etc/sv/FC-1/FC-1`
3. Start the FC-1 service

### Step 3: Verify Deployment

```bash
# Check FC-1 is running
./fc1 status

# Check PPP status
./fc1 ppp
```

**Expected**: FC-1 running, PPP connected (may take 30-60 seconds to establish)

---

## Test Procedure

### Test 1: Initial PPP Stability (Sanity Check)

**Objective**: Verify basic PPP connectivity still works after fix

**Steps**:
1. Wait for PPP to connect after deployment
2. Check PPP status: `./fc1 ppp`
3. Wait 2 minutes
4. Check PPP status again

**Pass Criteria**:
- PPP connected with valid IP
- Uptime > 2 minutes
- No restart loop

---

### Test 2: Post-Scan PPP Reconnection (Main Test)

**Objective**: Verify Fix 3 - PPP reconnects on FIRST attempt after scan

**Steps**:

#### 2.1 Connect to FC-1 CLI
```bash
# Terminal 1: SSH to gateway
ssh -p 22222 root@192.168.7.1
# Password: PasswordQConnect

# Connect to FC-1 CLI
microcom /dev/pts/2
# Press Enter to see prompt
```

#### 2.2 Record Initial State
```
cell status
ppp
```
Note: Current carrier, signal, PPP IP, uptime

#### 2.3 Trigger Cell Scan
```
cell scan
```

#### 2.4 Monitor Scan Progress (3-5 minutes)
Watch for these messages:
```
[Cellular Scan - State 1: Stopping PPP...]
[Cellular Scan - State 4: Scanning for operators...]
[Cellular Scan - State 4: Found X operators]
[Cellular Scan - State 8: Selected best operator: <CARRIER>]
[Cellular Scan - State 11: Scan complete]
[Cellular Scan - PPP protection window set for 30000 ms]
```

#### 2.5 Monitor PPP Reconnection (CRITICAL)
Watch for these messages after scan completes:
```
Connect: ppp0 <--> /dev/ttyACM0
[PPP0] Reset ppp_start_time - PPP restarted after scan   <-- NEW LOG from Fix 3
local IP address X.X.X.X
```

**PASS Criteria**:
- NO "Finish Pppd runit service..." message after "Connect: ppp0"
- See "Reset ppp_start_time - PPP restarted after scan" log message
- PPP gets IP address on FIRST attempt

**FAIL Criteria**:
- "Finish Pppd runit service..." appears after connect (PPP killed)
- Multiple "NO CARRIER" errors
- PPP requires multiple retry attempts

#### 2.6 Verify Final State
```
# In FC-1 CLI
cell status
ppp

# Exit microcom: Ctrl+X

# From host
./fc1 ppp
```

**Expected**:
- PPP connected
- Valid IP address
- Uptime > 60 seconds

---

## Test Results

### Test 1: Initial PPP Stability - PASSED
| Item | Result |
|------|--------|
| PPP Connected | YES |
| IP Address | 10.183.201.229 |
| Uptime after 2 min | Stable |
| Status | **PASS** |

### Test 2: Post-Scan Reconnection - PARTIALLY PASSED
| Item | Result |
|------|--------|
| Initial Carrier | AT&T Global IoT |
| Scan Duration | ~4 minutes |
| Final Carrier | AT&T Global IoT |
| "Reset ppp_start_time" log seen | YES |
| PPP killed after connect | YES (before Fix 4) |
| Retry attempts needed | 2+ (before final stable) |
| Final PPP Status | CONNECTED |
| Final IP | 10.183.201.229 |
| Status | **NEEDS RETEST** - Fix 4 applied after initial test |

**Note**: Fix 4 (`sv up` instead of `sv restart`) was applied after observing kill/retry cycles. Another cell scan test is needed to verify if this resolves the immediate kill issue.

---

## Rollback Procedure

If fix causes issues:

```bash
# SSH to gateway
ssh -p 22222 root@192.168.7.1

# Stop FC-1
sv stop FC-1

# Restore previous binary (if backup exists)
# Or rebuild from previous commit
```

---

## Quick Reference Commands

```bash
# Deploy
./fc1 push -run

# Status checks
./fc1 status
./fc1 ppp
./fc1 log

# SSH access
ssh -p 22222 root@192.168.7.1
# Password: PasswordQConnect

# FC-1 CLI
microcom /dev/pts/2
# Exit: Ctrl+X

# CLI commands
cell status
cell scan
ppp
```

---

## Expected Outcome

After successful testing:
1. PPP reconnects on FIRST attempt after scan (no kill/retry cycle)
2. New log message confirms fix is active: "Reset ppp_start_time - PPP restarted after scan"
3. System maintains stable cellular connection
4. NO "Finish Pppd runit service..." message between "Connect:" and "local IP address"

---

## Post-Test Actions

- [x] Update `docs/ppp_testing_plan_1.md` with test results
- [x] Create `docs/ppp_testing_status.md` handoff document
- [ ] Run final verification test after Fix 4
- [ ] Mark all fixes as verified in documentation
- [ ] Consider long-duration stability test (24+ hours)

---

## Next Steps

1. Run another `cell scan` test to verify Fix 4 resolved the immediate kill issue
2. Check PPP log for clean connection (no kill between connect and IP assignment)
3. Update this document with final test results
