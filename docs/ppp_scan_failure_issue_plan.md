# PPP Scan Failure Issue Analysis and Fix Plan

**Date**: 2025-12-09
**Issue Type**: Cellular Manager Bug
**Priority**: High
**Status**: Analysis Complete - Ready for Implementation

---

## Executive Summary

After implementing the AT+COPS=2 deregistration fix, the cellular scan successfully deregisters from the network. However, the PPP connection fails afterward because:

1. The modem remains deregistered (+COPS: 2) after scan completes
2. PPP dial attempts fail because no carrier is registered
3. The `sv restart pppd` causes rapid restart loops

---

## Problem Analysis

### Evidence from Logs (var_log_pppd_current_log_1.txt)

#### 1. AT+COPS=2 Deregistration Works (line 329)
```
AT+COPS?
+COPS: 2
```
This shows the modem is in deregistered state (no network).

#### 2. PPP Dial Fails While Deregistered (lines 332-333)
```
ATDT*99***1#Script /usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto finished (pid 5319), status = 0x3
Connect script failed
```
Status 0x3 = TIMEOUT (no carrier response because modem isn't registered).

#### 3. Rapid sv restart Loops (lines 279-281, 312-314)
```
2025-12-10_00:06:34.43556 Finish Pppd runit service...
2025-12-10_00:06:34.45376 Start Pppd runit service...
2025-12-10_00:06:34.52729 Finish Pppd runit service...
```
PPP service starts and finishes within milliseconds - `sv restart` triggering loops.

#### 4. Successful Connection Pattern (lines 210-241)
When properly registered to a carrier:
```
AT+COPS?
+COPS: 1,0,"Verizon Wireless",7    <-- Registered to carrier
...
ATDT*99***1#
CONNECT                            <-- Dial succeeds
```

### Root Cause

**Issue 1: Missing Re-registration After Deregistration**

The scan state machine flow:
```
CELL_SCAN_VERIFY_STOPPED → CELL_SCAN_DEREGISTER → CELL_SCAN_WAIT_DEREGISTER
    → CELL_SCAN_GET_OPERATORS → ... → CELL_SCAN_COMPLETE → CELL_WAIT_PPP_STARTUP
```

After `AT+COPS=2`, the scan completes but:
- The selected carrier is set via `AT+COPS=1,2,"carrier"`
- But if that command fails or times out, modem stays deregistered
- PPP start is attempted while modem shows `+COPS: 2`

Looking at the scan states, `CELL_SCAN_CONNECT_BEST` should re-register, but either:
1. The registration command failed
2. Not enough time was given for registration to complete
3. The registration wasn't verified before PPP start

**Issue 2: sv restart Causing Loops**

The `sv restart pppd` command in `start_pppd()` is problematic:
- It sends SIGTERM to running pppd
- Then immediately starts new pppd
- If modem isn't ready, pppd fails immediately
- runsv detects failure and restarts again
- Creates rapid restart loop

---

## Proposed Solutions

### Fix 1: Verify Registration Before PPP Start

After scan completes and before starting PPP, verify the modem is registered:

1. Add `CELL_SCAN_VERIFY_REGISTRATION` state after `CELL_SCAN_COMPLETE`
2. Query `AT+COPS?` and verify response shows registration (not `+COPS: 2`)
3. If not registered, wait and retry AT+COPS=1 to auto-register
4. Only proceed to PPP start after confirmed registration

### Fix 2: Fix sv restart Behavior

The `sv restart pppd` issue:
- Don't use `sv restart` immediately after a scan
- Use `sv up pppd` instead (starts if not running, no-op if running)
- Or add delay between stop and start
- Or use the script for all starts during/after scans

### Implementation Details

#### State Machine Changes (cellular_man.c)

Add verification before PPP startup:

```c
case CELL_SCAN_COMPLETE:
    // After selecting best carrier, verify registration before PPP
    PRINTF("[Cellular Scan - Verifying carrier registration before PPP start]\r\n");

    // Query current registration status
    if (send_AT_command(cell_fd, "+COPS?") < 0) {
        PRINTF("[Cellular Scan - WARNING: Cannot query COPS, proceeding anyway]\r\n");
        cellular_state = CELL_WAIT_PPP_STARTUP;
        break;
    }

    memset(response_buffer, 0, sizeof(response_buffer));
    initATResponseState(&state, current_time);
    scan_timeout = current_time + 5000;  // 5 second timeout

    cellular_state = CELL_SCAN_VERIFY_REGISTRATION;
    break;

case CELL_SCAN_VERIFY_REGISTRATION:
    {
        ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 5);

        if (status == AT_RESPONSE_SUCCESS) {
            // Check if registered (should not show +COPS: 2)
            if (strstr(response_buffer, "+COPS: 2") != NULL ||
                strstr(response_buffer, "+COPS: 0") != NULL) {
                // Not registered or searching - need to re-register
                PRINTF("[Cellular Scan - Modem not registered, requesting auto-registration]\r\n");
                send_AT_command(cell_fd, "+COPS=0");  // Auto-register
                scan_timeout = current_time + 30000;  // 30 sec for registration
                // Stay in this state to re-verify
            }
            else {
                // Registered to a carrier
                PRINTF("[Cellular Scan - Registration verified, starting PPP]\r\n");
                cellular_state = CELL_WAIT_PPP_STARTUP;
            }
        }
        else if (status == AT_RESPONSE_ERROR || imx_is_later(current_time, scan_timeout)) {
            PRINTF("[Cellular Scan - Registration check timeout, proceeding with PPP]\r\n");
            cellular_state = CELL_WAIT_PPP_STARTUP;
        }
    }
    break;
```

#### start_pppd() Fix

Change the subsequent-start logic:

```c
if (pppd_first_start) {
    // First start: use script
    system("/etc/start_pppd.sh");
    pppd_first_start = false;
} else {
    // After scan or failure: use sv up (not restart)
    // sv up is idempotent - starts if down, no-op if running
    PRINTF("[Cellular Connection - Starting PPPD (subsequent): sv up pppd]\r\n");
    int result = system("sv up pppd");

    if (result != 0) {
        PRINTF("[Cellular Connection - sv up failed, using script]\r\n");
        system("/etc/start_pppd.sh");
    }
}
```

---

## Implementation Todo List

### Phase 1: Fix Registration Verification

- [ ] **1.1** Add `CELL_SCAN_VERIFY_REGISTRATION` state to enum
- [ ] **1.2** Add state string "SCAN_VERIFY_REGISTRATION"
- [ ] **1.3** Modify `CELL_SCAN_COMPLETE` to query `AT+COPS?`
- [ ] **1.4** Implement `CELL_SCAN_VERIFY_REGISTRATION` state logic
- [ ] **1.5** Handle unregistered case with `AT+COPS=0` auto-register
- [ ] **1.6** Add timeout and retry logic
- [ ] **1.7** Update documentation

### Phase 2: Fix sv restart Issue

- [ ] **2.1** Change `sv restart pppd` to `sv up pppd` in start_pppd()
- [ ] **2.2** Add logging to distinguish start methods
- [ ] **2.3** Test sv up behavior

### Phase 3: Testing

- [ ] **3.1** Test carrier scan with new registration verification
- [ ] **3.2** Verify PPP connects after scan
- [ ] **3.3** Test manual scan via CLI
- [ ] **3.4** Test automatic scan trigger
- [ ] **3.5** Verify no rapid restart loops

---

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | Add registration verification state, fix start_pppd() |
| `docs/cellular_state_machine.md` | Update state documentation |

---

## Risk Assessment

### Low Risk
- Adding new verification state (isolated change)
- Changing sv restart to sv up

### Medium Risk
- Adding delay for registration (could slow PPP startup)
- Auto-registration command might select wrong carrier

### Mitigations
1. Short timeout (30s) for registration verification
2. Fall through to PPP start on timeout
3. Comprehensive logging for debugging
4. `sv up` is safer than `sv restart` for runsv managed services

---

## Sequence Diagram: Fixed Flow

```
Scan Trigger
    │
    ▼
Stop PPP (sv down pppd)
    │
    ▼
Verify PPP Stopped
    │
    ▼
Deregister (AT+COPS=2)        ← NEW (implemented)
    │
    ▼
Wait for Deregister OK
    │
    ▼
Scan Operators (AT+COPS=?)
    │
    ▼
Test Each Carrier (AT+COPS=1,2,"xxx")
    │
    ▼
Select Best Carrier
    │
    ▼
Connect to Best (AT+COPS=1,2,"best")
    │
    ▼
Verify Registration (AT+COPS?)  ← NEW (to be implemented)
    │
    ├── If +COPS: 2 or 0 → AT+COPS=0 (auto-register) → re-verify
    │
    ▼
Start PPP (sv up pppd)          ← FIXED (not sv restart)
    │
    ▼
Verify PPP Interface
```

---

**Review Status**: Awaiting approval before implementation (after WiFi fix is complete)
