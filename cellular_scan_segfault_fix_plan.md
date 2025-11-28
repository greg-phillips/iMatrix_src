# Cellular Scan Segfault Fix Plan

**Date**: 2025-11-20
**Issue**: Segmentation fault when cellular scan stops PPP while ping thread is active
**Severity**: CRITICAL - System crash

---

## Problem Summary

### Observed Behavior (net6.txt)

```
Line 123: [Cellular Connection - Starting operator scan]
Line 124: [Cellular Connection - Stopping PPP for operator scan]
Line 125: [Cellular Connection - Stopping PPPD (cellular_reset=true)]
Line 126: [NET: ppp0] execute_ping: Raw output: ping: sendto: No such device
Line 134: Segmentation fault
```

### Root Cause

The segfault is a **race condition** introduced by the cellular scan PPP fix:

1. **Network manager launches ping thread** on ppp0 (normal health check)
2. **User issues `cell scan`** command
3. **cellular_man.c immediately stops PPP** (line 2227) without checking for active threads
4. **PPP interface destroyed** while ping thread still executing
5. **Ping thread tries to access ppp0 structures** after interface is gone
6. **Segmentation fault** due to invalid memory access

### Code Analysis

#### Problematic Code (cellular_man.c:2224-2228)

```c
// Stop PPP before scanning - modem cannot scan while connected
if (system("pidof pppd >/dev/null 2>&1") == 0) {
    PRINTF("[Cellular Connection - Stopping PPP for operator scan]\r\n");
    stop_pppd(true);  // ❌ PROBLEM: No ping thread coordination
}
```

**Issue**: Direct `stop_pppd()` call bypasses network manager's thread safety checks.

#### Existing Safety Mechanism (process_network.c:1118-1125)

The network manager **already has** ping thread deferral logic:

```c
/* Defer if any ping tests are running */
for (uint32_t i = 0; i < IFACE_COUNT; i++)
{
    if (ctx->states[i].running)
    {
        NETMGR_LOG_PPP0(ctx, "Deferring PPPD conflict resolution - ping test running on %s", if_names[i]);
        return false;  // ✅ Safely defers until ping completes
    }
}
```

#### Network Manager Scan Handler (process_network.c:4364-4382)

The network manager **already stops PPP for scanning**:

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
            stop_pppd(true);  // ✅ This path has thread coordination
            // ... safe cleanup ...
        }
    }
}
```

**However**: This network manager code doesn't have the ping thread check either!

---

## Solution

### Two-Part Fix

#### Part 1: Remove Direct PPP Shutdown from cellular_man.c

**Change**: Remove lines 2224-2228 that directly call `stop_pppd()`

**Rationale**:
- Let network manager handle PPP lifecycle
- Network manager runs more frequently and has state coordination
- Setting `cellular_scanning = true` is sufficient signal

#### Part 2: Add Ping Thread Check Before Scan Shutdown

**Change**: Add ping thread check in process_network.c before stopping PPP for scan

**Location**: process_network.c:4370-4382

**New Logic**:
```c
if (is_scanning)
{
    // Check if ping thread is running on ppp0
    if (ctx->states[IFACE_PPP].running)
    {
        NETMGR_LOG_PPP0(ctx, "Deferring scan PPP shutdown - ping test running on ppp0");
        // Don't stop PPP yet, wait for ping to complete
    }
    else
    {
        // Safe to stop PPP - no active ping thread
        if( ctx->cellular_stopped == false )
        {
            stop_pppd(true);
            MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
            ctx->cellular_started = false;
            ctx->cellular_stopped = true;
            ctx->states[IFACE_PPP].active = false;
            MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);
            NETMGR_LOG_PPP0(ctx, "Stopped pppd - cellular scanning for operators");
        }
    }
}
```

---

## Implementation Plan

### Step 1: Remove Premature PPP Shutdown

**File**: iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c

**Remove** lines 2224-2228:
```c
// Delete these lines:
// Stop PPP before scanning - modem cannot scan while connected
if (system("pidof pppd >/dev/null 2>&1") == 0) {
    PRINTF("[Cellular Connection - Stopping PPP for operator scan]\r\n");
    stop_pppd(true);  // Stop due to scan operation
}
```

**Keep** lines 2230-2237 (state management):
```c
// Set scanning state
cellular_scanning = true;
cellular_state = CELL_PROCIESS_INITIALIZATION;
current_command = HANDLE_ATCOPS_SET_NUMERIC_MODE;
cellular_now_ready = false;
cellular_link_reset = true;
check_for_connected = false;
cellular_flags.cell_scan = false;
```

### Step 2: Add Ping Thread Coordination

**File**: iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c

**Modify** the scan shutdown logic at lines 4370-4382:

**Before** (current code):
```c
if (is_scanning)
{
    // Always stop PPP during scanning - modem cannot scan while connected
    if( ctx->cellular_stopped == false )
    {
        stop_pppd(true);  // Stopping for scan operation
        // ... rest of shutdown ...
    }
}
```

**After** (with ping coordination):
```c
if (is_scanning)
{
    // Check if ping thread is running on ppp0 before stopping
    if (ctx->states[IFACE_PPP].running)
    {
        NETMGR_LOG_PPP0(ctx, "Deferring scan PPP shutdown - ping test running on ppp0");
        // Wait for ping to complete before stopping PPP
    }
    else
    {
        // Safe to stop PPP during scanning - modem cannot scan while connected
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
}
```

---

## Expected Behavior After Fix

### Scenario: User Issues `cell scan` During Ping

1. **User executes** `cell scan` command
2. **cellular_man.c sets** `cellular_scanning = true`
3. **cellular_man.c sets** `cellular_now_ready = false` and `cellular_link_reset = true`
4. **Network manager detects** `imx_is_cellular_scanning() == true`
5. **Network manager checks** `ctx->states[IFACE_PPP].running`
6. **If ping running**: Defers PPP shutdown, logs "Deferring scan PPP shutdown - ping test running on ppp0"
7. **Ping completes** normally (may fail due to cellular becoming not ready)
8. **Next network manager cycle**: Ping not running, safe to stop PPP
9. **PPP stopped** cleanly without race condition
10. **Scan proceeds** normally
11. **No segfault**

### Log Sequence (Expected)

```
[Cellular Connection - Starting operator scan]
[NETMGR-PPP0] State: NET_ONLINE | Deferring scan PPP shutdown - ping test running on ppp0
[NET: ppp0] execute_ping: Ping command completed normally
[NETMGR-PPP0] State: NET_ONLINE | Stopped pppd - cellular scanning for operators
[Cellular Connection - Sending AT command: AT+COPS=3,2]
```

---

## Testing Plan

### Test Case 1: Scan During Ping

```bash
# Establish PPP connection
# Wait for system to reach NET_ONLINE state
# Issue scan command immediately (triggers ping during scan)
cell scan
# Expected: Deferred shutdown, no segfault
```

### Test Case 2: Scan Between Pings

```bash
# Establish PPP connection
# Wait for ping cycle to complete
# Issue scan command during idle period
cell scan
# Expected: Immediate shutdown, no segfault
```

### Test Case 3: Rapid Scan Commands

```bash
# Establish PPP connection
cell scan
# Wait 1 second
cell scan
# Expected: Second scan deferred until first completes, no segfault
```

### Test Case 4: Automatic Scan After Failure

```bash
# Establish PPP connection
# Force connection failure (blacklist carrier, disconnect, etc.)
# System automatically triggers scan
# Expected: Safe shutdown even if ping running, no segfault
```

---

## Rollback Plan

If issues occur:

1. **Revert process_network.c** changes (restore lines 4370-4382 to original)
2. **Revert cellular_man.c** changes (restore lines 2224-2228)
3. **Keep** cellular_scanning flag and state management (lines 2230-2237)
4. System returns to previous behavior (with segfault risk)

---

## Risk Analysis

### Low Risk

- **Scan delay**: Maximum ~3 seconds (ping timeout) before PPP stops
- **User experience**: Minimal impact, scan still proceeds
- **Compatibility**: No API changes, all existing code works

### High Benefit

- **Eliminates segfault**: Critical stability fix
- **Thread safety**: Proper coordination between subsystems
- **Clean shutdown**: PPP stopped gracefully every time

---

## Files Modified

1. **iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c**
   - Remove lines 2224-2228 (direct stop_pppd call)

2. **iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c**
   - Modify lines 4370-4382 (add ping thread check)

---

## Related Issues

- **Original PPP scan fix**: cellular_scan_ppp_fix_summary.md
- **PPP connection fixes**: ppp_connection_fix_summary.md
- **Chat script handling**: ppp_connection_fix_plan.md

---

**Status**: Plan complete, ready for implementation
