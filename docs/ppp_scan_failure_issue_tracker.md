# PPP Scan Failure Issue Tracker

**Issue ID**: PPP-001
**Created**: 2025-12-09
**Last Updated**: 2025-12-09
**Priority**: High
**Status**: IMPLEMENTED - Awaiting Testing

---

## Issue Summary

After implementing the AT+COPS=2 deregistration fix for cellular scanning, the PPP connection fails because:
1. The modem remains deregistered (`+COPS: 2`) after scan completes
2. PPP dial attempts fail because no carrier is registered
3. The `sv restart pppd` command causes rapid restart loops

This issue was observed when a manual `cell scan` command was executed.

---

## Current Status

| Phase | Status | Date |
|-------|--------|------|
| Analysis | Complete | 2025-12-09 |
| Plan Created | Complete | 2025-12-09 |
| Implementation | Complete | 2025-12-09 |
| Code Review | Pending | - |
| Testing | Pending | - |
| Deployed | Pending | - |

---

## Root Cause

From log analysis (`logs/var_log_pppd_current_log_1.txt`):

1. **AT+COPS=2 deregistration works** (line 329):
   ```
   AT+COPS?
   +COPS: 2
   ```
   Modem is in deregistered state (no network).

2. **PPP dial fails while deregistered** (lines 332-333):
   ```
   ATDT*99***1#Script /usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto finished (pid 5319), status = 0x3
   Connect script failed
   ```
   Status 0x3 = TIMEOUT (no carrier response because modem isn't registered).

3. **Rapid sv restart loops** (lines 279-281):
   ```
   2025-12-10_00:06:34.43556 Finish Pppd runit service...
   2025-12-10_00:06:34.45376 Start Pppd runit service...
   2025-12-10_00:06:34.52729 Finish Pppd runit service...
   ```
   PPP service starts and finishes within milliseconds.

---

## Proposed Solution

### Fix 1: Verify Registration Before PPP Start

Add a new state `CELL_SCAN_VERIFY_REGISTRATION` after `CELL_SCAN_COMPLETE`:

1. Query `AT+COPS?` to check registration status
2. If response shows `+COPS: 2` or `+COPS: 0`, send `AT+COPS=0` (auto-register)
3. Wait up to 30 seconds for registration
4. Only proceed to PPP start after confirmed registration

### Fix 2: Change sv restart to sv up

Replace `sv restart pppd` with `sv up pppd` in `start_pppd()`:
- `sv up` starts if not running, no-op if running
- Prevents rapid restart loops
- Falls back to script if sv fails

---

## Implementation Plan

### Phase 1: Registration Verification

| Task | Status | Details |
|------|--------|---------|
| 1.1 Add CELL_SCAN_VERIFY_REGISTRATION state to enum | Pending | After CELL_SCAN_COMPLETE |
| 1.2 Add state string to cellularStateStrings[] | Pending | "SCAN_VERIFY_REGISTRATION" |
| 1.3 Modify CELL_SCAN_COMPLETE to query AT+COPS? | Pending | Transition to new state |
| 1.4 Implement CELL_SCAN_VERIFY_REGISTRATION logic | Pending | Check registration, auto-register if needed |
| 1.5 Add timeout and retry logic | Pending | 30 second timeout |
| 1.6 Update documentation | Pending | cellular_state_machine.md |

### Phase 2: Fix sv restart Issue

| Task | Status | Details |
|------|--------|---------|
| 2.1 Change sv restart to sv up in start_pppd() | Pending | For subsequent starts |
| 2.2 Add logging to distinguish start methods | Pending | First start vs subsequent |
| 2.3 Add fallback if sv up fails | Pending | Fall back to script |

---

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | Add registration verification state, fix start_pppd() |
| `docs/cellular_state_machine.md` | Update state documentation |

---

## Code Changes (Planned)

### New State in cellular_man.c

```c
case CELL_SCAN_VERIFY_REGISTRATION:
    {
        ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 5);

        if (status == AT_RESPONSE_SUCCESS) {
            // Check if registered (should not show +COPS: 2)
            if (strstr(response_buffer, "+COPS: 2") != NULL ||
                strstr(response_buffer, "+COPS: 0") != NULL) {
                // Not registered - request auto-registration
                PRINTF("[Cellular Scan - Modem not registered, requesting auto-registration]\r\n");
                send_AT_command(cell_fd, "+COPS=0");
                scan_timeout = current_time + 30000;  // 30 sec for registration
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

### Modified start_pppd() (sv up instead of sv restart)

```c
if (pppd_first_start) {
    // First start: use script
    system("/etc/start_pppd.sh");
    pppd_first_start = false;
} else {
    // Subsequent starts: use sv up (not restart)
    PRINTF("[Cellular Connection - Starting PPPD (subsequent): sv up pppd]\r\n");
    int result = system("sv up pppd");
    if (result != 0) {
        PRINTF("[Cellular Connection - sv up failed, using script]\r\n");
        system("/etc/start_pppd.sh");
    }
}
```

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
Deregister (AT+COPS=2)        ← Already implemented
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
Verify Registration (AT+COPS?)  ← TO BE IMPLEMENTED
    │
    ├── If +COPS: 2 or 0 → AT+COPS=0 (auto-register) → re-verify
    │
    ▼
Start PPP (sv up pppd)          ← TO BE FIXED (not sv restart)
    │
    ▼
Verify PPP Interface
```

---

## Testing Checklist

- [ ] Test carrier scan with new registration verification
- [ ] Verify PPP connects after scan
- [ ] Test manual scan via CLI (`cell scan`)
- [ ] Test automatic scan trigger
- [ ] Verify no rapid restart loops
- [ ] Test timeout behavior (30 seconds)
- [ ] Test fallback to script if sv up fails

---

## Progress History

| Date | Action | Details |
|------|--------|---------|
| 2025-12-09 | Issue identified | Analyzed var_log_pppd_current_log_1.txt, found PPP fails after deregistration |
| 2025-12-09 | Plan created | Created ppp_scan_failure_issue_plan.md |
| 2025-12-09 | WiFi fix completed | WiFi linkdown recovery implemented first |
| 2025-12-09 | Implementation complete | Modified CELL_SCAN_VERIFY_CARRIER to detect +COPS: 2 and trigger auto-registration |
| 2025-12-09 | Build verified | Code compiles without errors |

---

## Related Documents

- [PPP Scan Failure Issue Plan](ppp_scan_failure_issue_plan.md)
- [Cellular Manager Fixes Plan](cellular_man_fixes_plan.md)
- [Cellular State Machine](cellular_state_machine.md)

---

## Implementation Details

### File Modified

`iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

### Changes Made (lines 5000-5065)

Modified `CELL_SCAN_VERIFY_CARRIER` state to detect deregistered modem status:

1. **Added deregistration detection** (lines 5012-5028):
   - Checks for `+COPS: 2` (explicitly deregistered)
   - Checks for `+COPS: 0` without quoted operator (auto mode, not registered)

2. **Added auto-registration recovery** (lines 5050-5065):
   - When deregistered state detected, sends `AT+COPS=0` command
   - Waits 5 seconds then re-queries `AT+COPS?` to verify registration
   - Uses existing `CELL_SCAN_VERIFY_WAIT` state for retry loop

### Code Snippet

```c
// Check for deregistered state: +COPS: 2 (deregistered) or +COPS: 0 (auto mode, not registered)
if (strstr(response_buffer[i], "+COPS: 2") != NULL)
{
    PRINTF("[Cellular Scan - Modem deregistered (+COPS: 2), requesting auto-registration]\r\n");
    modem_deregistered = true;
    break;
}

// Handle deregistered modem - send AT+COPS=0 to trigger auto-registration
if (modem_deregistered)
{
    if (send_AT_command(cell_fd, "+COPS=0") < 0)
    {
        PRINTF("[Cellular Scan - FATAL: Cannot send AT+COPS=0, aborting]\r\n");
        cellular_state = CELL_SCAN_FAILED;
        break;
    }
    scan_timeout = current_time + 5000;
    cellular_state = CELL_SCAN_VERIFY_WAIT;
    break;
}
```

### Note on sv restart vs sv up

The existing `CELL_SCAN_COMPLETE` state already uses `sv up pppd` (not `sv restart`), so no change was needed for Fix 2.

---

## Notes

- This issue only occurs after a carrier scan (manual or automatic)
- The user noted: "PPP failed when I did a manual cell scan command as expected"
- The existing AT+COPS=2 deregistration implementation is working correctly
- The fix adds detection of the deregistered state and triggers auto-registration
