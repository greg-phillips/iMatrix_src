# Cellular Scan PPP Disconnection Fix Plan

**Date:** November 20, 2024
**Priority:** HIGH
**Issue:** PPP connection not properly shut down before cellular scanning

---

## Problem Analysis

### Current Behavior (INCORRECT)

When a cellular scan is triggered (via CLI `cell scan` or on connection failure):

1. **cellular_man.c** (lines 2219-2227):
   - Sets `cellular_now_ready = false`
   - Sets `cellular_link_reset = true`
   - Changes state to `CELL_PROCIESS_INITIALIZATION`
   - **DOES NOT stop PPP**

2. **process_network.c** (lines 4358-4378):
   - Detects `cellular_now_ready = false`
   - Only stops PPP if OTHER interfaces are available
   - **Keeps PPP active if it's the only interface**

### Why This Is Wrong

1. **Modem Conflict**: Most cellular modems cannot maintain a data connection while performing a network scan
2. **Resource Contention**: PPP holds the modem's data channel, preventing scan operations
3. **Incorrect Results**: Scan may fail or return incomplete/incorrect operator list
4. **Connection Instability**: Active PPP during scan can cause unexpected disconnections

### Expected Behavior

When entering scan mode:
1. Mark cellular as not ready
2. **ALWAYS stop PPP** (regardless of other interfaces)
3. Close serial port if needed
4. Perform scan operation
5. Re-establish connection after scan completes

---

## Root Cause

The issue stems from two design decisions:

1. **cellular_man.c** assumes the network manager will handle PPP shutdown
2. **process_network.c** tries to maintain connectivity by keeping PPP active when no alternatives exist

This creates a situation where PPP remains active during scanning when it's the only interface.

---

## Implementation Plan

### Solution 1: Force PPP Shutdown in cellular_man.c (RECOMMENDED)

**Location:** `cellular_man.c`, scan trigger handling
**Approach:** Stop PPP immediately when scan is triggered

#### Changes Required:

1. **Modify scan trigger handling** (line ~2219):
```c
else if( cellular_flags.cell_scan )
{
    // Stop PPP before scanning - modem cannot scan while connected
    PRINTF("[Cellular Connection - Stopping PPP for operator scan]\r\n");
    stop_pppd(true);  // Stop due to scan operation

    // Set state for scanning
    cellular_state = CELL_PROCIESS_INITIALIZATION;
    current_command = HANDLE_ATCOPS_SET_NUMERIC_MODE;
    cellular_now_ready = false;
    cellular_link_reset = true;
    check_for_connected = false;
    cellular_flags.cell_scan = false;
}
```

2. **Add similar handling for connection failures** that trigger scans

3. **Notify network manager** about scan state:
```c
// Add new function
void imx_notify_cellular_scanning(bool scanning)
{
    // Notify network manager that scanning is in progress
}
```

### Solution 2: Override Protection in process_network.c (ALTERNATIVE)

**Location:** `process_network.c`, PPP shutdown logic
**Approach:** Add exception for scanning state

#### Changes Required:

1. **Add scan detection**:
```c
// Check if cellular is scanning
bool is_scanning = imx_is_cellular_scanning();

if ((imx_is_cellular_now_ready() == false) ||
    (imx_is_cellular_link_reset() == true) ||
    is_scanning)  // NEW: Always stop if scanning
{
    if (!is_scanning && !imx_use_eth0() && !imx_use_wifi0())
    {
        // Only keep active if NOT scanning and no alternatives
        NETMGR_LOG_PPP0(ctx, "Keeping ppp0 active as no other interfaces");
    }
    else
    {
        // Stop PPP for scanning or when alternatives exist
        stop_pppd(false);
        // ... rest of shutdown code
    }
}
```

---

## Detailed Implementation Steps

### Phase 1: Add Scan State Tracking
1. Add `bool cellular_scanning` flag in cellular_man.c
2. Set flag when scan starts
3. Clear flag when scan completes
4. Export via `imx_is_cellular_scanning()` function

### Phase 2: Stop PPP on Scan
1. Add `stop_pppd(true)` call when scan triggered
2. Ensure serial port is closed if needed
3. Add logging for visibility

### Phase 3: Update Network Manager
1. Detect scanning state
2. Force PPP shutdown during scan
3. Prevent PPP restart until scan completes

### Phase 4: Handle Scan Completion
1. Clear scanning flag
2. Allow normal PPP reconnection
3. Restore previous operator if scan was informational

---

## Test Cases

### 1. Manual Scan Test
```bash
# Start with PPP connected
cell status  # Verify connected
cell scan    # Trigger scan
ps | grep pppd  # Should show NO pppd process
cell status  # Should show scanning
# Wait for scan to complete
cell operators  # Should show scan results
```

### 2. Scan with No Alternatives
- Disconnect Ethernet and WiFi
- Ensure only PPP is available
- Trigger scan
- **Verify PPP stops despite being only interface**

### 3. Automatic Scan on Failure
- Simulate connection failure
- Verify automatic scan triggers
- Verify PPP stopped before scan

### 4. Scan Recovery
- After scan completes
- Verify PPP reconnects automatically
- Verify connection restored

---

## Risk Assessment

### Risks:
1. **Temporary Loss of Connectivity**: PPP will disconnect during scan
2. **Scan Duration**: Scans can take 30-120 seconds
3. **Failed Reconnection**: PPP might not reconnect after scan

### Mitigations:
1. Add scan timeout (max 120 seconds)
2. Automatic PPP restart after scan
3. Scan result caching to reduce frequency
4. Warning messages before manual scans

---

## Files to Modify

1. **cellular_man.c**:
   - Add `stop_pppd()` call in scan trigger
   - Add scanning state flag
   - Export scanning state function

2. **cellular_man.h**:
   - Add `bool imx_is_cellular_scanning(void)` declaration

3. **process_network.c**:
   - Check scanning state in PPP management
   - Force shutdown during scans

---

## Success Criteria

1. ✓ PPP always stops before scan begins
2. ✓ Scan completes successfully
3. ✓ PPP reconnects after scan
4. ✓ No hanging PPP processes during scan
5. ✓ Clear logging of scan operations

---

## Timeline

- Implementation: 1 hour
- Testing: 1 hour
- Documentation: 30 minutes

**Total: 2.5 hours**

---

## Rollback Plan

If issues occur:
1. Remove scan-triggered PPP shutdown
2. Revert to original behavior
3. Document scan limitations for users

---

## Alternative Approaches

### Option A: Disable Scans When Connected
- Reject scan command if PPP active
- Require manual PPP shutdown first
- Simpler but less user-friendly

### Option B: Queue Scan for Idle Time
- Delay scan until PPP idle
- Complex scheduling required
- May never execute if constantly active

### Option C: Use AT Command Timeout
- Let scan fail with timeout
- PPP remains connected
- Scan results unreliable

**Recommendation:** Implement Solution 1 (Force shutdown in cellular_man.c)

---

*Document created: November 20, 2024*
*Author: Claude + Greg*