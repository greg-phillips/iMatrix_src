# Cellular Manager Fixes Plan

**Date**: 2025-12-09
**Author**: Claude Code Analysis
**Status**: Draft - Pending Review

---

## Executive Summary

This document outlines the implementation plan for two critical fixes to `cellular_man.c`:

1. **Issue 1**: Add `AT+COPS=2` to disconnect from current carrier before scanning
2. **Issue 2**: Use `sv restart pppd` for subsequent PPP starts instead of the startup script

---

## Issue 1: Add AT+COPS=2 Before Carrier Scan

### Problem Statement

When commencing a scan for a new carrier, the modem must first disconnect from the current carrier using the `AT+COPS=2` command. Currently, the scan sequence jumps directly from stopping PPP to sending `AT+COPS=?` without deregistering from the network first.

The `AT+COPS=2` command tells the modem to:
- Deregister from the current network
- Stop attempting automatic registration
- Enter an idle state ready for manual operator selection

### Current Flow (Problematic)

```
CELL_SCAN_STOP_PPP          → Stop PPP daemon
CELL_SCAN_STOP_PPP_WAIT_SV  → Wait for sv down
CELL_SCAN_VERIFY_STOPPED    → Verify PPP stopped
CELL_SCAN_GET_OPERATORS     → Send AT+COPS=? (PROBLEM: Still registered!)
...
```

### Proposed Flow (Fixed)

```
CELL_SCAN_STOP_PPP          → Stop PPP daemon
CELL_SCAN_STOP_PPP_WAIT_SV  → Wait for sv down
CELL_SCAN_VERIFY_STOPPED    → Verify PPP stopped
CELL_SCAN_DEREGISTER        → NEW: Send AT+COPS=2 (deregister)
CELL_SCAN_WAIT_DEREGISTER   → NEW: Wait for OK response
CELL_SCAN_GET_OPERATORS     → Send AT+COPS=?
...
```

### Implementation Details

#### New States Required

1. **CELL_SCAN_DEREGISTER** - Send `AT+COPS=2` command to deregister from network
2. **CELL_SCAN_WAIT_DEREGISTER** - Wait for OK response (with timeout)

#### State Enum Changes

Add two new states to `CellularState_t` enum (after `CELL_SCAN_VERIFY_STOPPED`):
```c
CELL_SCAN_DEREGISTER,       // Send AT+COPS=2 to deregister from network
CELL_SCAN_WAIT_DEREGISTER,  // Wait for deregister response
```

#### State String Array Changes

Add corresponding strings to `cellularStateStrings[]`:
```c
"SCAN_DEREGISTER",
"SCAN_WAIT_DEREGISTER",
```

#### State Machine Logic

**CELL_SCAN_VERIFY_STOPPED** - Change transition:
- Current: `cellular_state = CELL_SCAN_GET_OPERATORS;`
- New: `cellular_state = CELL_SCAN_DEREGISTER;`

**CELL_SCAN_DEREGISTER** (new state):
```c
case CELL_SCAN_DEREGISTER:
    PRINTF("[Cellular Scan - Deregistering from current network (AT+COPS=2)]\r\n");

    // Send AT+COPS=2 to deregister from network
    if (send_AT_command(cell_fd, "+COPS=2") < 0) {
        PRINTF("[Cellular Scan - FATAL: Cannot send AT+COPS=2, aborting scan]\r\n");
        cellular_state = CELL_SCAN_FAILED;
        break;
    }

    // Initialize response buffer
    memset(response_buffer, 0, sizeof(response_buffer));
    initATResponseState(&state, current_time);

    // Set timeout for deregistration (10 seconds should be sufficient)
    scan_timeout = current_time + 10000;

    cellular_state = CELL_SCAN_WAIT_DEREGISTER;
    break;
```

**CELL_SCAN_WAIT_DEREGISTER** (new state):
```c
case CELL_SCAN_WAIT_DEREGISTER:
    {
        ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 10);

        if (status == AT_RESPONSE_SUCCESS) {
            PRINTF("[Cellular Scan - Deregistered from network, proceeding with scan]\r\n");
            cellular_state = CELL_SCAN_GET_OPERATORS;
        }
        else if (status == AT_RESPONSE_ERROR || imx_is_later(current_time, scan_timeout)) {
            // Log the error but continue anyway - scan might still work
            PRINTF("[Cellular Scan - WARNING: Deregister command failed/timed out, continuing scan]\r\n");
            cellular_state = CELL_SCAN_GET_OPERATORS;
        }
        // else: Still waiting (AT_RESPONSE_CONTINUE)
    }
    break;
```

---

## Issue 2: Use sv restart pppd for Subsequent PPP Starts

### Problem Statement

Currently, `start_pppd()` always calls `/etc/start_pppd.sh` to start PPP. This is correct for the first time after power up, but for subsequent starts, it should use `sv restart pppd` instead (which properly uses the runit service manager).

### Current Behavior

```c
void start_pppd(void) {
    // ... checks ...
    system("/etc/start_pppd.sh");  // Always uses script
}
```

### Proposed Behavior

```c
void start_pppd(void) {
    static bool first_start = true;  // Track first start after power up

    if (first_start) {
        // First start: use the initialization script
        system("/etc/start_pppd.sh");
        first_start = false;
    } else {
        // Subsequent starts: use sv restart
        system("sv restart pppd");
    }
}
```

### Implementation Details

#### New Static Variable

Add a static variable to track first start:
```c
static bool pppd_first_start = true;  // True = first start after power up
```

This variable:
- Initialized to `true` at program start
- Set to `false` after first successful PPP start
- Never reset (persists for lifetime of process)

#### Modified start_pppd() Function

```c
void start_pppd(void)
{
    extern int cell_fd;

    // First check for any previous chat script failures and clean up
    if (detect_and_handle_chat_failure()) {
        PRINTF("[Cellular Connection - Cleaned up previous PPP failure before starting new session]\r\n");
    }

    // Check if pppd is already running
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        PRINTF("[Cellular Connection - PPPD already running, skipping start]\r\n");
        return;
    }

    if (cell_fd != -1) {
        PRINTF("[Cellular Connection - AT command port remains open (fd=%d) during PPP]\r\n", cell_fd);
    }

    // Ensure no lock files are blocking the PPP device
    system("rm -f /var/lock/LCK..ttyACM0 2>/dev/null");

    if (pppd_first_start) {
        // First start after power up: use the initialization script
        if (access("/etc/start_pppd.sh", X_OK) != 0) {
            PRINTF("[Cellular Connection - ERROR: /etc/start_pppd.sh not found or not executable]\r\n");
            PRINTF("[Cellular Connection - PPP connection unavailable]\r\n");
            return;
        }

        PRINTF("[Cellular Connection - Starting PPPD (first start): /etc/start_pppd.sh]\r\n");
        int result = system("/etc/start_pppd.sh");

        if (result != 0) {
            PRINTF("[Cellular Connection - WARNING: start_pppd.sh returned %d]\r\n", result);
        }

        pppd_first_start = false;  // Mark first start complete
    } else {
        // Subsequent starts: use sv restart for proper service management
        PRINTF("[Cellular Connection - Starting PPPD (subsequent): sv restart pppd]\r\n");
        int result = system("sv restart pppd");

        if (result != 0) {
            PRINTF("[Cellular Connection - WARNING: sv restart pppd returned %d, falling back to script]\r\n", result);
            // Fallback to script if sv fails
            system("/etc/start_pppd.sh");
        }
    }

    pppd_start_count++;
    PRINTF("[Cellular Connection - PPPD start initiated (count=%d, first_start=%s)]\r\n",
           pppd_start_count, pppd_first_start ? "true" : "false");
}
```

#### Considerations

1. **Fallback Behavior**: If `sv restart pppd` fails (returns non-zero), fall back to using the script
2. **No Reset**: The `pppd_first_start` flag is never reset - this is intentional as we only want to use the script once after power up
3. **Logging**: Clear log messages distinguish between first and subsequent starts

---

## Implementation Todo List

### Phase 1: Preparation (No Code Changes)

- [ ] **1.1** Backup current `cellular_man.c` before making changes
- [ ] **1.2** Review current state enum ordering to ensure new states are inserted correctly
- [ ] **1.3** Identify all places where state ID numbers are hardcoded (shouldn't be any, but verify)
- [ ] **1.4** Review test coverage for cellular scan functionality

### Phase 2: Issue 1 - AT+COPS=2 Deregistration

#### 2.1 Add New States to Enum
- [ ] **2.1.1** Add `CELL_SCAN_DEREGISTER` to `CellularState_t` enum after `CELL_SCAN_VERIFY_STOPPED`
- [ ] **2.1.2** Add `CELL_SCAN_WAIT_DEREGISTER` to `CellularState_t` enum after `CELL_SCAN_DEREGISTER`
- [ ] **2.1.3** Verify `NO_CELL_STATES` sentinel value is still at end of enum
- [ ] **2.1.4** Count total states and verify count matches `NO_CELL_STATES`

#### 2.2 Update State String Array
- [ ] **2.2.1** Add "SCAN_DEREGISTER" string to `cellularStateStrings[]` at correct position
- [ ] **2.2.2** Add "SCAN_WAIT_DEREGISTER" string to `cellularStateStrings[]` at correct position
- [ ] **2.2.3** Verify string array order matches enum order exactly

#### 2.3 Modify Existing State Transition
- [ ] **2.3.1** In `CELL_SCAN_VERIFY_STOPPED` case, change target state from `CELL_SCAN_GET_OPERATORS` to `CELL_SCAN_DEREGISTER`
- [ ] **2.3.2** Update any comments referencing the old transition

#### 2.4 Implement New CELL_SCAN_DEREGISTER State
- [ ] **2.4.1** Add case for `CELL_SCAN_DEREGISTER` in main switch statement
- [ ] **2.4.2** Add PRINTF logging for state entry
- [ ] **2.4.3** Add `send_AT_command(cell_fd, "+COPS=2")` call
- [ ] **2.4.4** Add error check for send failure
- [ ] **2.4.5** Initialize response_buffer with memset
- [ ] **2.4.6** Call `initATResponseState(&state, current_time)`
- [ ] **2.4.7** Set scan_timeout to current_time + 10000 (10 seconds)
- [ ] **2.4.8** Transition to `CELL_SCAN_WAIT_DEREGISTER`

#### 2.5 Implement New CELL_SCAN_WAIT_DEREGISTER State
- [ ] **2.5.1** Add case for `CELL_SCAN_WAIT_DEREGISTER` in main switch statement
- [ ] **2.5.2** Call `storeATResponse()` with 10 second timeout
- [ ] **2.5.3** Handle `AT_RESPONSE_SUCCESS`: log success, transition to `CELL_SCAN_GET_OPERATORS`
- [ ] **2.5.4** Handle `AT_RESPONSE_ERROR` or timeout: log warning, still transition to `CELL_SCAN_GET_OPERATORS` (graceful degradation)
- [ ] **2.5.5** Handle `AT_RESPONSE_CONTINUE`: do nothing (remain in state)

#### 2.6 Update Documentation
- [ ] **2.6.1** Update state count in `cellular_state_machine.md`
- [ ] **2.6.2** Add new states to state table in documentation
- [ ] **2.6.3** Update state transition diagram to include new states

### Phase 3: Issue 2 - PPP Start Method Selection

#### 3.1 Add Static Variable
- [ ] **3.1.1** Add `static bool pppd_first_start = true;` declaration near other pppd static variables (around line 634)
- [ ] **3.1.2** Add comment explaining the purpose of the variable

#### 3.2 Modify start_pppd() Function
- [ ] **3.2.1** Add conditional check for `pppd_first_start` at start of PPP launch logic
- [ ] **3.2.2** Implement first-start branch using `/etc/start_pppd.sh`
- [ ] **3.2.3** Set `pppd_first_start = false` after first successful start
- [ ] **3.2.4** Implement subsequent-start branch using `sv restart pppd`
- [ ] **3.2.5** Add fallback to script if `sv restart` fails
- [ ] **3.2.6** Update logging to indicate which method was used

#### 3.3 Update Logging
- [ ] **3.3.1** Update PRINTF statements to show first_start status
- [ ] **3.3.2** Add distinct log messages for each PPP start method
- [ ] **3.3.3** Add warning log if sv restart fails and fallback is used

### Phase 4: Testing

#### 4.1 Compilation Testing
- [ ] **4.1.1** Compile the modified code without errors
- [ ] **4.1.2** Verify no new compiler warnings

#### 4.2 Unit Testing (if applicable)
- [ ] **4.2.1** Test state enum ordering is correct
- [ ] **4.2.2** Test state string array matches enum

#### 4.3 Integration Testing
- [ ] **4.3.1** Test first PPP start after power up uses script
- [ ] **4.3.2** Test subsequent PPP starts use sv restart
- [ ] **4.3.3** Test carrier scan sends AT+COPS=2 before AT+COPS=?
- [ ] **4.3.4** Test scan still works if AT+COPS=2 times out
- [ ] **4.3.5** Test manual scan via CLI (`cell scan`)
- [ ] **4.3.6** Test automatic scan triggered by PPP failures

#### 4.4 Regression Testing
- [ ] **4.4.1** Verify normal PPP connection still works
- [ ] **4.4.2** Verify carrier selection still works
- [ ] **4.4.3** Verify blacklisting still works
- [ ] **4.4.4** Verify hardware reset still works

### Phase 5: Code Review and Cleanup

- [ ] **5.1** Review all changes for consistency with existing code style
- [ ] **5.2** Verify no debug code left in
- [ ] **5.3** Update CLAUDE.md if any workflow changes needed
- [ ] **5.4** Document any caveats or known limitations

---

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | Add new states, modify start_pppd() |
| `docs/cellular_state_machine.md` | Update state documentation |

---

## Risk Assessment

### Low Risk
- Adding new states to enum (isolated change)
- Adding logging statements

### Medium Risk
- Changing state transitions (could affect scan flow)
- Modifying start_pppd() (could affect PPP startup)

### Mitigations
1. New states have fallback behavior if AT+COPS=2 fails
2. `sv restart` has fallback to script if it fails
3. All changes have extensive logging for debugging
4. Changes are isolated to specific functions

---

## Rollback Plan

If issues are discovered:
1. Revert `cellular_man.c` to backup
2. Revert documentation changes
3. Rebuild and redeploy

---

**Review Status**: IMPLEMENTED - 2025-12-09
