# Cell Scan Test Plan

**Date**: 2025-12-30
**Last Updated**: 2025-12-30 17:48 UTC
**Purpose**: Test the cellular network scan functionality after PPP restart bug fixes
**Status**: Initial test complete - Awaiting final verification after Fix 4

## Fixes Being Tested

| Fix | File | Description |
|-----|------|-------------|
| Fix 3 | process_network.c | Reset ppp_start_time in scan protection window |
| Fix 3b | process_network.c | Reset ppp_start_time when starting PPP during protection |
| Fix 3c | cellular_man.c | Skip PPP stop if protection active and has IP |
| Fix 4 | cellular_man.c | Changed `sv restart pppd` to `sv up pppd` |

## Prerequisites

1. FC-1 service running on gateway
2. PPP connection established and stable
3. SSH access to gateway (192.168.7.1:22222)
4. Two terminal sessions recommended

## Connection Commands

### Terminal 1: Debug Output Monitor
```bash
# SSH to gateway
ssh -p 22222 root@192.168.7.1
# Password: PasswordQConnect

# Connect to FC-1 CLI for debug output
microcom /dev/pts/2
```
> **Note**: Press Enter after connecting to see the prompt. Debug output will stream continuously.

### Terminal 2: Status Monitoring (optional)
```bash
# From host machine
cd /home/greg/iMatrix/iMatrix_Client/scripts
./fc1 ppp        # Check PPP status
./fc1 status     # Check FC-1 service status
./fc1 log        # View logs
```

## FC-1 CLI Commands Reference

Once connected via `microcom /dev/pts/2`:

| Command | Description |
|---------|-------------|
| `cell` | Print cellular status summary |
| `cell status` | Same as `cell` |
| `cell scan` | **Trigger network scan** (manual, bypasses protection) |
| `cell reset` | Soft reset cellular state machine |
| `cell reset hard` | Hardware GPIO modem reset |
| `cell reinit` | Reinitialize cellular modem |
| `cell operators` | List discovered operators |
| `cell blacklist` | Show blacklisted operators |
| `ppp` | PPP connection status |
| `ppp log` | Recent PPP log output |

## Test Procedure

### Step 1: Verify Initial State
1. Connect to FC-1 CLI: `microcom /dev/pts/2`
2. Press Enter to get prompt
3. Run `cell status` - verify cellular is ONLINE
4. Run `ppp` - verify PPP is connected with valid IP

**Expected Output:**
```
Cellular State: ONLINE
PPP0: Connected, IP: 10.x.x.x
```

### Step 2: Record Pre-Scan Status
1. Note current carrier (e.g., AT&T, T-Mobile, Verizon)
2. Note signal strength (CSQ value)
3. Note PPP IP address

### Step 3: Trigger Cell Scan
1. In FC-1 CLI, type: `cell scan`
2. Press Enter

**Expected Debug Output Sequence:**
```
[Cellular Connection - MANUAL SCAN: Bypassing connection protection]
[Cellular Connection - SCAN MANUAL - Starting]
[Cellular Connection - SCAN STARTED - All PPP operations will be suspended]
[Cellular Scan - State 1: Stopping PPP and disabling runsv supervision]
[Cellular Scan - Executing: sv down pppd]
[Cellular Scan - State 1b: sv down complete, now stopping pppd]
[Cellular Scan - State 2: PPP stopped successfully]
[Cellular Scan - State 3: Sending AT+COPS=2 to deregister]
[Cellular Scan - State 4: Scanning for operators (AT+COPS=?)]
```

### Step 4: Wait for Scan (3-5 minutes)
The scan takes **180-270 seconds** as it queries each carrier.

**Monitor for these messages:**
```
[Cellular Scan - State 4: Found X operators]
[Cellular Scan - State 5: Testing carrier: FirstNet (313100)]
[Cellular Scan - State 5: Testing carrier: AT&T (310410)]
[Cellular Scan - State 5: Testing carrier: Verizon (311480)]
[Cellular Scan - State 5: Testing carrier: T-Mobile (310260)]
```

### Step 5: Verify Carrier Selection
Watch for best carrier selection:
```
[Cellular Scan - State 8: Selected best operator: <CARRIER> (signal: XX)]
[Cellular Scan - State 9: Connecting to <CARRIER>]
[Cellular Scan - State 11: Scan complete]
[Cellular Scan - Set cellular_now_ready=true BEFORE starting PPPD]
```

### Step 6: Verify PPP Reconnection (CRITICAL)
**This is the main test - verify PPP reconnects successfully**

Watch for:
```
[Cellular Connection - Starting PPPD...]
Connect: ppp0 <--> /dev/ttyACM0
local IP address X.X.X.X
```

**PASS Criteria:**
- PPP reconnects within 30 seconds after scan completes
- No "Finish Pppd runit service..." immediately after connect
- `ppp` command shows connected with valid IP

**FAIL Criteria:**
- PPP restart loop (multiple "Finish/Start" messages)
- NO CARRIER errors
- PPP fails to establish IP after scan

### Step 7: Verify Stability
1. Wait 60 seconds
2. Run `ppp` - verify still connected
3. Run `cell status` - verify ONLINE state
4. Run `cell operators` - verify operators list populated

## Expected Scan Timeline

| Time | Event |
|------|-------|
| 0:00 | `cell scan` command entered |
| 0:01 | PPP stop initiated |
| 0:05 | Modem deregistered |
| 0:10 | AT+COPS=? sent |
| 3:00-4:30 | Operators found |
| 4:00-5:00 | Signal testing complete |
| 5:00-5:30 | Best carrier selected |
| 5:30-6:00 | PPP reconnected |

## Troubleshooting

### If scan hangs at "Scanning for operators":
- Normal - scan takes 180-270 seconds
- Wait at least 5 minutes before considering it hung

### If PPP fails to reconnect after scan:
1. Run `cell status` - check state
2. Run `ppp log` - check for errors
3. Run `cell reset` - soft reset
4. If still failing: `cell reset hard` - hardware reset

### If "CME ERROR: no network service":
- Normal for some carriers (e.g., Verizon without provisioned eSIM)
- Scan will move to next carrier automatically

## Post-Test Verification

```bash
# From host machine
./fc1 ppp
```

Should show:
```
Status:     [OK] CONNECTED
Local IP:   10.x.x.x
Uptime:     >60s
```

## Exit CLI

To exit microcom: **Press Ctrl+X**

---

## Quick Test Commands (Copy/Paste)

```
# Pre-scan status
cell status
ppp

# Trigger scan
cell scan

# Post-scan verification (run after ~6 minutes)
cell status
ppp
cell operators
```

---

## Test Results (2025-12-30)

### Initial Test (Before Fix 4)
| Item | Result |
|------|--------|
| Scan Completed | YES |
| Operators Found | Multiple (AT&T, T-Mobile, etc.) |
| Best Carrier Selected | AT&T Global IoT |
| PPP Reconnected | YES (eventually) |
| PPP Killed After Connect | YES - Multiple times |
| Retry Attempts | 2+ |
| Final Status | CONNECTED (stable after retries) |

**Observed Issue**: PPP was still being killed ~0.5s after connecting, requiring multiple retry attempts before stabilizing.

### After Fix 4 Applied
Fix 4 changed `sv restart pppd` to `sv up pppd` in `start_pppd()` function. This should prevent killing an existing pppd process during scan recovery.

**Status**: Awaiting verification test

---

## Next Steps

1. Run another `cell scan` test with all fixes deployed
2. Monitor for clean PPP connection (no kill between connect and IP assignment)
3. Document results in this file and `docs/ppp_testing_status.md`
