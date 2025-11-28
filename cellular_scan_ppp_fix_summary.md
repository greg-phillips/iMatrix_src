# Cellular Scan PPP Fix - Implementation Summary

## Overview
Implemented proper PPP shutdown and restart behavior when cellular operator scanning occurs, ensuring the modem can perform scans without active data connections.

## Problem Statement
When the cellular subsystem initiated an operator scan (either via CLI command or after connection failure), the PPP connection was not properly stopped before scanning began. This caused:
1. Modem unable to scan while maintaining data connection
2. Scan operations potentially failing or incomplete
3. PPP not properly restarting after scan completion

## Implementation Date
2025-11-20

## Files Modified

### 1. iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c

#### Added Scanning State Tracking (Line 524)
```c
static bool cellular_scanning = false;  // Track if operator scan is in progress
```

#### Modified Scan Trigger to Stop PPP (Lines 2220-2238)
```c
else if( cellular_flags.cell_scan )
{
    PRINTF("[Cellular Connection - Starting operator scan]\r\n");

    // Stop PPP before scanning - modem cannot scan while connected
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        PRINTF("[Cellular Connection - Stopping PPP for operator scan]\r\n");
        stop_pppd(true);  // Stop due to scan operation
    }

    // Set scanning state
    cellular_scanning = true;
    cellular_state = CELL_PROCIESS_INITIALIZATION;
    current_command = HANDLE_ATCOPS_SET_NUMERIC_MODE;
    cellular_now_ready = false;
    cellular_link_reset = true;
    check_for_connected = false;
    cellular_flags.cell_scan = false;
}
```

#### Added Export Function (Lines 3066-3075)
```c
/**
 * @brief       Check if the cellular modem is currently scanning for operators
 * @param[in]:  None
 * @param[out]: None
 * @return:     bool - True if the cellular modem is performing an operator scan
 */
bool imx_is_cellular_scanning(void)
{
    return cellular_scanning;
}
```

#### Clear Scanning Flag After Scan Completes (Lines 2406-2412)
```c
active_operator = 0;
selected_operator = -1;
// Clear scanning flag - scan complete, now selecting operator
cellular_scanning = false;
PRINTF("[Cellular Connection - Scan complete, selecting best operator]\r\n");
cellular_state = CELL_SETUP_OPERATOR;
```

#### Clear Scanning Flag When Connected (Lines 2474-2479)
```c
if (strstr(response_buffer[1], "OK") != NULL) {
    cellular_state = CELL_CONNECTED;
    cellular_now_ready = true;
    cellular_link_reset = false;
    // Ensure scanning flag is cleared when connected
    cellular_scanning = false;
```

### 2. iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.h

#### Added Function Declaration (Line 89)
```c
bool imx_is_cellular_scanning(void);
```

### 3. iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c

#### Prevent PPP Start During Scan (Lines 4301-4316)
```c
// Don't start PPP if scanning is in progress
if (imx_is_cellular_scanning())
{
    NETMGR_LOG_PPP0(ctx, "Cellular is scanning for operators, skipping PPP activation");
    should_activate_ppp = false;
}
else if (imx_is_cellular_now_ready() == true)
{
    should_activate_ppp = true;
}
else if (!imx_use_eth0() && !imx_use_wifi0())
{
    // If both eth0 and wifi are disabled, try to activate ppp0
    NETMGR_LOG_PPP0(ctx, "No other interfaces available, attempting to activate ppp0");
    should_activate_ppp = true;
}
```

#### Stop PPP When Scanning Begins (Lines 4364-4401)
```c
// Check if cellular is scanning, not ready, or link reset
bool is_scanning = imx_is_cellular_scanning();

if ((imx_is_cellular_now_ready() == false) || (imx_is_cellular_link_reset() == true) || is_scanning)
{
    // Always stop PPP if scanning, otherwise don't stop if it's the only available interface
    if (is_scanning)
    {
        // Always stop PPP during scanning - modem cannot scan while connected
        if( ctx->cellular_stopped == false )
        {
            stop_pppd(true);  // Stopping for scan operation
            MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
            ctx->cellular_started = false;
            ctx->cellular_stopped = true;
            ctx->states[IFACE_PPP].active = false;
            MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);
            NETMGR_LOG_PPP0(ctx, "Stopped pppd - cellular scanning for operators");
        }
    }
    else if (imx_use_eth0() || imx_use_wifi0())
    {
        // Only stop if we have other interfaces available (non-scan case)
        if( ctx->cellular_stopped == false )
        {
            stop_pppd(false);  // Stopping because other interfaces are available
            MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
            ctx->cellular_started = false;
            ctx->cellular_stopped = true;
            ctx->states[IFACE_PPP].active = false;
            MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);
            NETMGR_LOG_PPP0(ctx, "Stopped pppd - other interfaces available");
        }
    }
    else
    {
        NETMGR_LOG_PPP0(ctx, "Keeping ppp0 active as no other interfaces available");
    }
}
```

## Behavior Flow

### When Scan is Triggered (CLI "cell scan" or automatic after failure):

1. **cellular_man.c** detects scan request
2. Checks if pppd is running and stops it
3. Sets `cellular_scanning = true`
4. Sets `cellular_now_ready = false` and `cellular_link_reset = true`
5. Begins initialization sequence for scan operation

### During Scan:

1. **process_network.c** checks `imx_is_cellular_scanning()`
2. Prevents PPP from starting while scanning is active
3. If PPP is still running, forces shutdown with message "Stopped pppd - cellular scanning for operators"

### After Scan Completes:

1. **cellular_man.c** processes operator list
2. Clears `cellular_scanning = false` when transitioning to CELL_SETUP_OPERATOR
3. Selects best non-blacklisted operator (STATUS_AVAILABLE or STATUS_CURRENT with NAT_E_UTRAN)
4. Attempts to connect to selected operator
5. When connected successfully:
   - Sets `cellular_now_ready = true`
   - Clears `cellular_scanning = false` (redundant safety)
   - Transitions to CELL_CONNECTED

### Automatic PPP Restart:

1. **process_network.c** detects `imx_is_cellular_now_ready() == true`
2. Checks `imx_is_cellular_scanning() == false`
3. Sets `should_activate_ppp = true`
4. Calls `start_pppd()` automatically
5. PPP connection re-establishes without user intervention

## Key Features

### 1. Automatic PPP Shutdown Before Scan
- PPP is always stopped when scan begins, even if it's the only available interface
- Modem cannot scan for operators while maintaining a data connection

### 2. Scan State Tracking
- New `cellular_scanning` flag prevents race conditions
- Network manager aware of scan state through `imx_is_cellular_scanning()`

### 3. Automatic Carrier Selection
- System automatically selects best non-blacklisted carrier after scan
- Filters by:
  - Operator status: STATUS_AVAILABLE or STATUS_CURRENT
  - Technology: NAT_E_UTRAN (LTE)
  - Blacklist: Excludes operators marked as `bad_operator`

### 4. Automatic PPP Restart
- PPP automatically restarts when cellular_now_ready becomes true
- No user intervention required
- Network manager handles timing and state transitions

### 5. Safety Mechanisms
- Scanning flag cleared at multiple points to prevent stuck states
- Redundant flag clearing when connected (safety net)
- Proper state machine transitions

## Testing Checklist

### Manual Testing Required:

- [ ] **CLI Scan Test**: Execute "cell scan" command with PPP active
  - Verify PPP stops before scan begins
  - Verify scan completes successfully
  - Verify PPP restarts automatically after scan

- [ ] **Automatic Scan Test**: Trigger scan by blacklisting current carrier
  - Verify PPP stops before scan
  - Verify new carrier is selected
  - Verify PPP restarts with new carrier

- [ ] **Single Interface Test**: Disable eth0 and wifi0, trigger scan with only PPP
  - Verify PPP stops despite being only interface
  - Verify scan completes
  - Verify PPP restarts

- [ ] **Multiple Scan Test**: Trigger multiple scans in succession
  - Verify scanning flag properly cleared between scans
  - Verify no stuck states

- [ ] **Carrier Blacklist Test**: Verify blacklisted carriers are skipped during selection
  - Create scenario with multiple operators
  - Blacklist one operator
  - Verify system selects different operator

### Log Verification:

Expected log messages:
```
[Cellular Connection - Starting operator scan]
[Cellular Connection - Stopping PPP for operator scan]
Stopped pppd - cellular scanning for operators
[Cellular Connection - Scan complete, selecting best operator]
[Cellular Connection - Testing Operator 1:...]
[Cellular Connection - AT+COPS command response received.]
Activating cellular: cellular_ready=YES
Started pppd, will monitor for PPP0 device creation
```

## Integration with Previous Fixes

This implementation works in conjunction with:
1. **PPP Cleanup Fix**: Uses enhanced `stop_pppd()` with process cleanup
2. **Chat Script Error Detection**: Handles exit codes 0x3 and 0xb correctly
3. **Carrier Blacklisting**: Respects blacklist during operator selection
4. **Network Manager State Machine**: Integrates with existing PPP lifecycle management

## Potential Issues and Mitigations

### Issue 1: Scan Takes Too Long
- **Mitigation**: Network manager has timeout mechanisms
- **Recovery**: System will continue even if scan times out

### Issue 2: No Operators Found
- **Behavior**: System transitions to CELL_DISCONNECTED
- **Recovery**: Will retry on next cellular check cycle

### Issue 3: All Operators Blacklisted
- **Behavior**: Blacklist entries expire over time
- **Recovery**: System will eventually retry blacklisted operators

### Issue 4: Race Condition During State Transitions
- **Mitigation**: Multiple flag clearing points prevent stuck states
- **Mitigation**: Network manager checks scanning state before PPP operations

## Rollback Plan

If issues are discovered:

1. **Revert cellular_man.c** (Lines 524, 2220-2238, 2408-2410, 2479, 3066-3075)
2. **Revert cellular_man.h** (Line 89)
3. **Revert process_network.c** (Lines 4301-4306, 4364-4401)
4. System will return to previous behavior (no forced PPP shutdown during scan)

## Documentation References

- **Implementation Plan**: `cellular_scan_ppp_fix_plan.md`
- **QConnect Developer Guide**: Page 25 (Port allocation: ttyACM0 for PPPD)
- **Previous PPP Fixes**: `ppp_connection_fix_summary.md`

## Conclusion

The cellular scan PPP fix ensures proper modem operation during operator scanning by:
1. Forcing PPP shutdown before scan begins
2. Preventing PPP restart during scan
3. Automatically selecting best non-blacklisted carrier
4. Automatically restarting PPP after successful connection

This provides a seamless experience for both manual CLI scans and automatic carrier switching after connection failures.
