# Cellular Scan Coordination Fix Plan

**Date**: 2025-11-21
**Issue**: process_network.c continues PPP operations during cellular operator scan
**Priority**: HIGH - Blocks proper cellular initialization
**Root Cause**: Incomplete coordination between cellular_man.c and process_network.c

---

## Problem Statement

### User's Observation

> "After the cell scan command is issued I see that cellular_man.c code issues the AT+COPS=?
> Problem is that the process_network is continuing to scan and do pings. When the cell scan
> command is issued this should set flags to tell process_network to stop trying to connect
> as the cellular system doing a scan for best solution."

### Technical Analysis

When a cellular operator scan is triggered:

**cellular_man.c does**:
1. ✅ Sets `cellular_scanning = true`
2. ✅ Sets `cellular_now_ready = false`
3. ✅ Sends `AT+COPS=?` to modem to scan for operators
4. ✅ Waits for scan results (30-120 seconds typically)

**process_network.c SHOULD do**:
1. ❌ **STOP all PPP-related activity**
2. ❌ **STOP ping tests on ppp0**
3. ❌ **STOP trying to establish routes**
4. ❌ **STOP opportunistic PPP activation**
5. ❌ **WAIT for scan to complete**

**What ACTUALLY happens** (from net8.txt analysis):
1. ✅ PPP activation skipped (line 4302 check works)
2. ❌ **Ping tests continue** → "Network unreachable" errors
3. ❌ **Route establishment attempts continue** → "Device ppp0 does not exist" errors
4. ❌ **State machine keeps cycling** → Retries every 3-5 seconds
5. ❌ **Scan never completes** → 8 scan attempts, 189 AT+COPS commands

**Result**: System stuck in loop, never reaches CELL_ONLINE

---

## Root Cause Analysis

### Why Modem Can't Scan While PPP Active

**Hardware Limitation**:
- Cellular modem has ONE radio
- Radio is either in DATA mode (PPP) or COMMAND mode (AT commands)
- Operator scan (`AT+COPS=?`) requires COMMAND mode
- Modem CANNOT scan while data connection active

**Current Flow (BROKEN)**:
```
User: "cell scan"
  ↓
cellular_man.c:
  - Sets cellular_scanning = true
  - Sets cellular_now_ready = false
  - Stops own PPP operations (sort of)
  - Sends AT+COPS=?
  ↓
process_network.c: (PROBLEM!)
  ✅ Skips PPP activation (line 4302)
  ❌ Continues ping tests
  ❌ Tries to restore routes
  ❌ Marks PPP as failed
  ❌ Triggers interface re-selection
  ❌ Cycles through states rapidly
  ↓
Modem: "I'm busy scanning, can't handle pings/routes"
  ↓
process_network.c: "PPP failed, retry"
  ↓
cellular_man.c: "Network not ready, scan failed, retry"
  ↓
INFINITE LOOP ∞
```

---

## Current Coordination (Insufficient)

### cellular_man.c

**Setting the flag** (Line 2248):
```c
else if( cellular_flags.cell_scan )
{
    PRINTF("[Cellular Connection - Starting operator scan]\r\n");

    cellular_scanning = true;  // ✅ Sets flag
    cellular_state = CELL_PROCIESS_INITIALIZATION;
    current_command = HANDLE_ATCOPS_SET_NUMERIC_MODE;
    cellular_now_ready = false;
    cellular_link_reset = true;
    check_for_connected = false;
    cellular_flags.cell_scan = false;
}
```

**Clearing the flag** (Line 2426):
```c
case CELL_SELECT_OPERATOR:
    // ... operator selection logic ...
    cellular_scanning = false;  // ✅ Clears flag
    PRINTF("[Cellular Connection - Scan complete, selecting best operator]\r\n");
    cellular_state = CELL_SETUP_OPERATOR;
    break;
```

**Export function** (Line 3077):
```c
bool imx_is_cellular_scanning(void)
{
    return cellular_scanning;
}
```

### process_network.c

**Check #1** - Skip PPP activation (Line 4302):
```c
// Don't start PPP if scanning is in progress
if (imx_is_cellular_scanning())
{
    NETMGR_LOG_PPP0(ctx, "Cellular is scanning for operators, skipping PPP activation");
    should_activate_ppp = false;  // ✅ Works
}
```

**Check #2** - Stop PPP if scanning (Line 4365-4373):
```c
bool is_scanning = imx_is_cellular_scanning();

if ((imx_is_cellular_now_ready() == false) || (imx_is_cellular_link_reset() == true) || is_scanning)
{
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
            // Safe to stop PPP during scanning
            // ... PPP shutdown logic ...
        }
    }
}
```

### What's Missing ❌

**process_network.c does NOT check scanning flag in**:
1. ❌ Ping thread launching
2. ❌ Interface health checks
3. ❌ Route establishment
4. ❌ DNS operations
5. ❌ State transition logic
6. ❌ Opportunistic discovery
7. ❌ Interface scoring
8. ❌ Default route setting

**Result**: All these operations continue during scan, interfering with modem

---

## Evidence from net8.txt Log

### Scan Attempts (8 total)

```
[00:00:57.554] Starting operator scan  ← Attempt 1
[00:01:33.042] Starting operator scan  ← Attempt 2
[00:02:02.091] Starting operator scan  ← Attempt 3
[00:02:31.367] Starting operator scan  ← Attempt 4
[00:03:27.477] Starting operator scan  ← Attempt 5
[00:03:54.684] Starting operator scan  ← Attempt 6
[00:04:20.674] Starting operator scan  ← Attempt 7
[00:04:48.460] Starting operator scan  ← Attempt 8
```

**Average retry interval**: ~25 seconds
**Total AT+COPS commands**: 189

### Concurrent Operations During Scan

**Line 711-729** (00:00:34, during first scan):
```
[NETMGR-PPP0] Starting interface test for ppp0  ← ❌ Should NOT happen
[NET] ping_thread_fn: Starting ping thread for ppp0  ← ❌ Should NOT happen
[NET: ppp0] execute_ping: Executing command: ping -n -I ppp0 -c 3 -W 1 -s 56
[NET: ppp0] execute_ping: Raw output: ping: sendto: Network unreachable  ← Modem busy scanning!
```

**Line 7229-7237** (00:04:48, during 8th scan):
```
[NETMGR-PPP0] Cellular is scanning for operators, skipping PPP activation  ← ✅ This works
[NET] WARNING: Default route not found for ppp0  ← ❌ Should NOT try this
[NET] Device ppp0 does not exist, cannot set default route  ← ❌ Modem busy!
```

**Line 7256** (00:04:48, scan failing):
```
[Cellular Connection - Sending AT command: AT+COPS=3,2]
[Cellular Connection - Line: +CME ERROR: unknown]  ← Modem can't respond, busy!
```

### The Problem Pattern

```
1. cellular_man starts scan
2. process_network sees scanning flag
3. process_network skips PPP activation ✅
4. BUT process_network still runs ping tests ❌
5. Ping fails (modem busy)
6. process_network marks PPP as failed ❌
7. process_network tries to restore routes ❌
8. Route fails (interface down)
9. process_network cycles to re-select interface ❌
10. Cycle repeats every 3-5 seconds ❌
11. cellular_man scan gets interrupted ❌
12. cellular_man retries scan ~25 seconds later ❌
13. GOTO step 1 → INFINITE LOOP
```

---

## Solution: Comprehensive Scan Coordination

### Principle

**When `cellular_scanning == true`, process_network.c must be COMPLETELY PASSIVE regarding PPP/cellular**

**Actions Required**:
1. ✅ Skip PPP activation (already done)
2. ✅ Stop PPP if running (already done)
3. ❌ **NEW**: Skip ALL ppp0 ping tests
4. ❌ **NEW**: Skip ALL ppp0 route operations
5. ❌ **NEW**: Skip ALL ppp0 interface checks
6. ❌ **NEW**: Treat ppp0 as "temporarily unavailable"
7. ❌ **NEW**: Don't mark ppp0 as failed during scan
8. ❌ **NEW**: Don't trigger retries based on ppp0 state

---

## Implementation Plan

### Phase 1: Add Early-Exit Guards

Add scanning checks at the TOP of each function that operates on PPP:

**Locations to modify**:

1. **Ping thread launching** (~line 4500-4600)
2. **Interface testing** (~line 4200-4300)
3. **Route establishment** (~line 3000-3200)
4. **Interface health checks** (~line 4400-4500)
5. **Interface scoring** (~line 2500-2600)
6. **State transitions** (~line 3500-3700)

**Pattern**:
```c
// At the start of any PPP-related operation:
if (imx_is_cellular_scanning() && interface == IFACE_PPP)
{
    NETMGR_LOG_PPP0(ctx, "Skipping operation - cellular scan in progress");
    return;  // or appropriate early exit
}
```

### Phase 2: Add Scanning State Handling

**In main state machine** (~line 3800-4800):

```c
// Check for scanning state early in processing
if (imx_is_cellular_scanning())
{
    // During scan, keep current state but skip PPP operations
    if (ctx->current_interface == IFACE_PPP)
    {
        NETMGR_LOG(ctx, "Scan in progress - maintaining state without PPP operations");

        // Don't mark PPP as failed
        // Don't trigger re-selection
        // Don't launch ping tests
        // Just wait for scan to complete
        return;
    }
}
```

### Phase 3: Add Scan Completion Handling

**When scan completes** (cellular_man.c clears flag):

process_network.c should detect transition and trigger re-evaluation:

```c
// Track previous scanning state
static bool prev_scanning_state = false;

bool is_scanning = imx_is_cellular_scanning();

if (prev_scanning_state && !is_scanning)
{
    // Scan just completed
    NETMGR_LOG_PPP0(ctx, "Cellular scan completed - re-evaluating PPP availability");

    // Trigger interface re-selection
    ctx->state = NET_INIT;
    prev_scanning_state = false;
    return;
}

prev_scanning_state = is_scanning;
```

---

## Detailed Changes Required

### Change 1: Skip Ping Tests During Scan

**File**: process_network.c
**Location**: ~line 4500 (launch_ping_thread function)

**BEFORE**:
```c
static void launch_ping_thread(netmgr_context_t *ctx, interface_t interface)
{
    NETMGR_LOG(ctx, "[THREAD] %s: launch_ping_thread called",
               ctx->states[interface].name);

    // ... launch ping thread ...
}
```

**AFTER**:
```c
static void launch_ping_thread(netmgr_context_t *ctx, interface_t interface)
{
    // Skip ping tests during cellular scan
    if (interface == IFACE_PPP && imx_is_cellular_scanning())
    {
        NETMGR_LOG_PPP0(ctx, "Skipping ping test - cellular scan in progress");
        return;
    }

    NETMGR_LOG(ctx, "[THREAD] %s: launch_ping_thread called",
               ctx->states[interface].name);

    // ... launch ping thread ...
}
```

### Change 2: Skip Route Operations During Scan

**File**: process_network.c
**Location**: ~line 3000 (set_default_route function)

**BEFORE**:
```c
static bool set_default_route(netmgr_context_t *ctx, interface_t interface)
{
    // ... set route logic ...
}
```

**AFTER**:
```c
static bool set_default_route(netmgr_context_t *ctx, interface_t interface)
{
    // Skip route operations during cellular scan
    if (interface == IFACE_PPP && imx_is_cellular_scanning())
    {
        NETMGR_LOG_PPP0(ctx, "Skipping route setup - cellular scan in progress");
        return false;  // Don't consider this a failure
    }

    // ... set route logic ...
}
```

### Change 3: Skip Interface Health Checks During Scan

**File**: process_network.c
**Location**: ~line 4200 (interface checking logic in main loop)

**BEFORE**:
```c
// Check if we should test ppp0
if (ctx->states[IFACE_PPP].active)
{
    // Test the interface
    launch_ping_thread(ctx, IFACE_PPP);
}
```

**AFTER**:
```c
// Check if we should test ppp0
if (ctx->states[IFACE_PPP].active)
{
    // Skip testing during scan
    if (imx_is_cellular_scanning())
    {
        NETMGR_LOG_PPP0(ctx, "Skipping health check - cellular scan in progress");
    }
    else
    {
        // Test the interface
        launch_ping_thread(ctx, IFACE_PPP);
    }
}
```

### Change 4: Don't Mark PPP Failed During Scan

**File**: process_network.c
**Location**: ~line 4600 (ping result processing)

**BEFORE**:
```c
if (ctx->states[IFACE_PPP].score == 0)
{
    NETMGR_LOG_PPP0(ctx, "PPP0 ping failure %d/%d, will retry",
                    ppp_failure_count, MAX_PPP_FAILURES);

    if (ppp_failure_count >= MAX_PPP_FAILURES)
    {
        // Mark as failed, trigger re-selection
        ctx->state = NET_INIT;
    }
}
```

**AFTER**:
```c
if (ctx->states[IFACE_PPP].score == 0)
{
    // Don't count failures during scan
    if (imx_is_cellular_scanning())
    {
        NETMGR_LOG_PPP0(ctx, "Ignoring ping failure - cellular scan in progress");
    }
    else
    {
        NETMGR_LOG_PPP0(ctx, "PPP0 ping failure %d/%d, will retry",
                        ppp_failure_count, MAX_PPP_FAILURES);

        if (ppp_failure_count >= MAX_PPP_FAILURES)
        {
            // Mark as failed, trigger re-selection
            ctx->state = NET_INIT;
        }
    }
}
```

### Change 5: Add Scan State Logging

**File**: cellular_man.c
**Location**: Line 2248 (when setting scanning flag)

**BEFORE**:
```c
cellular_scanning = true;
```

**AFTER**:
```c
cellular_scanning = true;
PRINTF("[Cellular Connection - SCAN STARTED - All PPP operations will be suspended]\r\n");
```

**Location**: Line 2426 (when clearing scanning flag)

**BEFORE**:
```c
cellular_scanning = false;
```

**AFTER**:
```c
cellular_scanning = false;
PRINTF("[Cellular Connection - SCAN COMPLETED - PPP operations can resume]\r\n");
```

---

## Expected Behavior After Fix

### Correct Scan Flow

```
User: "cell scan"
  ↓
cellular_man.c:
  - Sets cellular_scanning = true
  - Sets cellular_now_ready = false
  - Logs "SCAN STARTED - All PPP operations suspended"
  - Stops PPP (if running)
  - Sends AT+COPS=?
  ↓
process_network.c:
  ✅ Skips PPP activation
  ✅ Skips ALL ping tests on ppp0
  ✅ Skips ALL route operations on ppp0
  ✅ Skips ALL health checks on ppp0
  ✅ Treats ppp0 as "temporarily unavailable"
  ✅ Uses other interfaces (eth0, wlan0) if available
  ✅ Waits patiently for scan to complete
  ↓
Modem:
  - Scans for operators (30-120 seconds)
  - Returns list of available networks
  ↓
cellular_man.c:
  - Receives scan results
  - Selects best operator
  - Clears cellular_scanning = false
  - Logs "SCAN COMPLETED - PPP operations can resume"
  - Sets cellular_now_ready = true
  ↓
process_network.c:
  ✅ Detects scan completion
  ✅ Triggers interface re-evaluation
  ✅ Activates PPP with best operator
  ✅ Resumes normal operations
  ↓
System reaches CELL_ONLINE and NET_ONLINE ✅
```

---

## Testing Plan

### Test 1: Manual Scan Command

**Procedure**:
```bash
./FC-1 &
# Wait for initialization
sleep 30
# Trigger scan
echo "cell scan" | ./FC-1
# Monitor log
tail -f /tmp/scan_test.txt
```

**Expected**:
```
[Cellular Connection - SCAN STARTED - All PPP operations will be suspended]
[NETMGR-PPP0] Skipping ping test - cellular scan in progress
[NETMGR-PPP0] Skipping route setup - cellular scan in progress
[NETMGR-PPP0] Skipping health check - cellular scan in progress
... (30-120 seconds of silence) ...
[Cellular Connection - SCAN COMPLETED - PPP operations can resume]
[NETMGR-PPP0] Cellular scan completed - re-evaluating PPP availability
[Cellular Connection - Scan complete, selecting best operator]
[Cellular Connection - Setting up operator: T-Mobile US]
[NETMGR-PPP0] Activating cellular: cellular_ready=YES
```

**Success Criteria**:
- [ ] ONE scan attempt (not 8+)
- [ ] NO ping tests during scan
- [ ] NO route errors during scan
- [ ] NO "Network unreachable" errors
- [ ] Scan completes in 30-120 seconds
- [ ] PPP activates after scan
- [ ] System reaches CELL_ONLINE

### Test 2: Automatic Scan on Weak Signal

**Procedure**:
```bash
# Simulate weak signal triggering automatic scan
./FC-1 &
# System should detect weak signal and scan automatically
# Monitor for proper coordination
```

**Expected**:
- Same as Test 1, but triggered automatically
- No manual intervention needed

### Test 3: Scan Interruption Handling

**Procedure**:
```bash
./FC-1 &
sleep 30
echo "cell scan" | ./FC-1
# Immediately try to use network
curl http://example.com
# Should gracefully handle attempt to use PPP during scan
```

**Expected**:
- Network operation waits or uses alternate interface
- Scan completes normally
- Network operation succeeds after scan

---

## Rollout Plan

### Phase 1: Implementation (2 hours)
1. Add early-exit guards to all PPP operations
2. Add scan state tracking
3. Add scan completion detection
4. Add comprehensive logging

### Phase 2: Testing (3 hours)
1. Test manual scan command
2. Test automatic scan
3. Test scan interruption
4. Test long scan duration (120 sec)

### Phase 3: Validation (1 hour)
1. Compare with net8.txt (should NOT get stuck)
2. Verify single scan attempt
3. Verify no interference messages
4. Verify proper completion

### Phase 4: Integration (1 hour)
1. Test with serial port fix (Nov 21 build)
2. Verify both fixes work together
3. Run extended stability test
4. Update documentation

**Total Estimated Time**: 7 hours

---

## Risk Assessment

### Changes Required
- **Files Modified**: 2 (process_network.c, cellular_man.c)
- **Lines Added**: ~100
- **Lines Modified**: ~50
- **Complexity**: MODERATE

### Risk Level: LOW

**Why**:
1. Only adds early-exit guards (defensive)
2. Doesn't change existing logic flow
3. Only affects PPP during scan (narrow scope)
4. Easy to test and verify
5. Easy to rollback if issues

### Rollback Plan
```bash
cd iMatrix
git checkout HEAD -- IMX_Platform/LINUX_Platform/networking/process_network.c
git checkout HEAD -- IMX_Platform/LINUX_Platform/networking/cellular_man.c
cd ../../Fleet-Connect-1/build
make clean && make
```

---

## Success Metrics

### Before Fix (net8.txt)
- ❌ 8 scan attempts over 4 minutes
- ❌ 189 AT+COPS commands total
- ❌ System stuck in loop
- ❌ Never reaches CELL_ONLINE
- ❌ "Network unreachable" errors
- ❌ "Device ppp0 does not exist" errors

### After Fix (Expected)
- ✅ 1 scan attempt
- ✅ 1-3 AT+COPS commands total
- ✅ Scan completes in 30-120 seconds
- ✅ System reaches CELL_ONLINE
- ✅ NO interference errors
- ✅ Clean logs with proper coordination

---

## Related Issues

### Issue #1: Cellular Scan Race Condition (FIXED)
- Added ping thread coordination
- This fix builds on that work

### Issue #2: Serial Port Management (FIXED)
- Port stays open during operations
- This fix ensures scan can complete

### Issue #3: Scan Coordination (THIS FIX)
- Comprehensive PPP suspension during scan
- Completes the coordination picture

---

## Summary

**Problem**: process_network.c interferes with cellular scan by continuing PPP operations

**Solution**: Add comprehensive scanning checks to skip ALL PPP operations during scan

**Impact**: Enables successful operator scanning and proper cellular initialization

**Effort**: 7 hours (2 implementation, 3 testing, 1 validation, 1 integration)

**Risk**: LOW (defensive changes, easy rollback)

**Priority**: HIGH (blocks cellular functionality)

---

**Document Version**: 1.0
**Date**: 2025-11-21
**Status**: Ready for Implementation
**Reviewer**: Greg (User)
