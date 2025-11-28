# PPP Connection Fix Plan

**Date:** November 20, 2024
**Priority:** HIGH
**Scope:** Fix PPP connection initialization failures and network manager state detection

---

## Executive Summary

The PPP connection experiences multiple issues during initialization:
1. Chat script fails with "Can't get terminal parameters: I/O error"
2. Incorrect device remapping (ttyACM0 → ttyACM2) in code
3. Network manager fails to detect PPP0 has an IP address
4. System eventually recovers but with unnecessary delays

---

## Root Cause Analysis

### Issue 1: Chat Script I/O Error
- **Error:** `chat[13941]: Can't get terminal parameters: I/O error`
- **Cause:** Chat script cannot access serial port terminal settings
- **Likely Reasons:**
  - Serial port already in use
  - Incorrect terminal mode (not a tty)
  - Permission issues
  - Device not ready

### Issue 2: Incorrect Device Remapping
- **Location:** cellular_man.c lines 1898-1903
- **Problem:** Code changes PPP config from ttyACM0 to ttyACM2
- **Impact:** PPP tries to use wrong device (customer AT port instead of PPP port)
- **Per Documentation:** ttyACM0 is correct for PPP, ttyACM2 is for customer AT commands

### Issue 3: IP Address Detection Failure
- **Symptom:** PPP0 shows "CONNECTED (IP: 10.183.106.95)" but has_ip=NO
- **Location:** Network manager state machine
- **Impact:** Network manager doesn't recognize active PPP connection

---

## Implementation Plan

### Phase 1: Remove Incorrect Device Remapping (CRITICAL)
**Priority:** IMMEDIATE
**Risk:** LOW
**Impact:** HIGH

1. Remove sed commands from cellular_man.c (lines 1898-1903)
2. Ensure PPP uses ttyACM0 as intended
3. Test that cellular_man.c still uses ttyACM2 for AT commands

### Phase 2: Fix Chat Script I/O Error
**Priority:** HIGH
**Risk:** MEDIUM
**Impact:** HIGH

1. Add terminal checking before starting PPP
2. Ensure serial port is properly released before PPP starts
3. Add retry logic for terminal access errors
4. Consider using `-E` flag for chat to disable terminal echo requirements

### Phase 3: Fix IP Address Detection
**Priority:** HIGH
**Risk:** LOW
**Impact:** MEDIUM

1. Locate has_ip detection logic in process_network.c
2. Fix detection when PPP0 status shows IP address
3. Ensure proper state transitions when IP is detected

### Phase 4: Enhanced Error Handling
**Priority:** MEDIUM
**Risk:** LOW
**Impact:** MEDIUM

1. Add detection for "Can't get terminal parameters" error
2. Implement automatic recovery for this error type
3. Add logging to track terminal state issues

---

## Todo List

### Immediate Actions
- [ ] Remove incorrect sed commands from cellular_man.c
- [ ] Test PPP with correct ttyACM0 device
- [ ] Verify cellular AT commands still work on ttyACM2

### Chat Script Fixes
- [ ] Research chat "Can't get terminal parameters" error
- [ ] Add terminal validation before PPP start
- [ ] Implement chat script error detection for I/O errors
- [ ] Add retry mechanism for terminal errors

### Network Manager Fixes
- [ ] Find has_ip detection code in process_network.c
- [ ] Fix IP address parsing from PPP status
- [ ] Ensure state machine recognizes connected PPP
- [ ] Test state transitions with active PPP

### Testing & Validation
- [ ] Test PPP startup sequence
- [ ] Verify no device remapping occurs
- [ ] Confirm IP detection works properly
- [ ] Check recovery from chat script errors
- [ ] Monitor for regression issues

### Documentation
- [ ] Update comments in cellular_man.c
- [ ] Document proper device allocation
- [ ] Add troubleshooting guide for chat errors
- [ ] Update ppp0_status.md with findings

---

## Code Changes Required

### 1. cellular_man.c (Remove lines 1898-1903)
```c
// REMOVE THESE LINES - THEY ARE INCORRECT:
// PRINTF("[Cellular Connection - Updating PPP config to use correct device /dev/ttyACM2]\r\n");
// system("sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/provider 2>/dev/null");
// system("sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/quake 2>/dev/null");
// system("sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/isp 2>/dev/null");
```

### 2. cellular_man.c (Add terminal check)
```c
// Before starting PPP, ensure terminal is accessible
if (isatty(cell_fd)) {
    // Terminal settings might interfere
    close(cell_fd);
    cell_fd = -1;
}
```

### 3. process_network.c (Fix IP detection)
```c
// Find and fix the has_ip detection logic
// Ensure it properly parses "CONNECTED (IP: x.x.x.x)" status
```

---

## Success Criteria

1. PPP connects without chat script I/O errors
2. PPP uses correct device (ttyACM0)
3. Network manager correctly detects PPP0 has IP
4. System transitions to NET_ONLINE without delays
5. No "Can't get terminal parameters" errors in logs

---

## Risk Mitigation

1. **Test on target device** before deployment
2. **Keep backup** of original code
3. **Monitor logs** for new error patterns
4. **Have rollback plan** if issues arise

---

## Timeline

- **Phase 1:** Immediate (15 minutes)
- **Phase 2:** 1 hour
- **Phase 3:** 30 minutes
- **Phase 4:** 30 minutes
- **Testing:** 1 hour

**Total Estimated Time:** 3-4 hours

---

*Document created: November 20, 2024*
*Last updated: November 20, 2024*