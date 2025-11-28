# Cellular Blacklist & Rescan - Comprehensive Review

**Date**: 2025-11-24
**Time**: 08:00
**Reviewer**: Claude Code Analysis
**Status**: ⚠️ **CRITICAL ISSUE FOUND**

---

## Executive Summary

The rescan fix has been successfully implemented, BUT there is a **CRITICAL DESIGN FLAW** that defeats the entire blacklist system:

- ✅ Rescan flag checking: **WORKING**
- ✅ State machine integration: **WORKING**
- ✅ Blacklist add/check logic: **WORKING**
- ❌ **CRITICAL**: Blacklist cleared on every scan at line 3203

---

## Detailed Review

### 1. ✅ Blacklist Logic (Working Correctly)

**File**: `cellular_blacklist.c`

#### Adding Carriers (lines 200-234):
```c
// Carrier not found in blacklist, add it as a new entry
if (blacklist_count < NO_BLACKLISTED_CARRIERS) {
    blacklist[blacklist_count].carrier_id = operator_id;
    blacklist[blacklist_count].blacklist_start_time = current_time;
    blacklist[blacklist_count].blacklisted = true;
    blacklist[blacklist_count].current_blacklist_time = DEFAULT_BLACKLIST_TIME;
    blacklist_count++;
}
```

**Status**: ✅ Correctly adds new carriers to blacklist

#### Checking Carriers (lines 241-252):
```c
bool is_carrier_blacklisted(uint32_t carrier_id) {
    for (uint32_t i = 0; i < blacklist_count; i++) {
        if (blacklist[i].carrier_id == carrier_id && blacklist[i].blacklisted == true) {
            return true;
        }
    }
    return false;
}
```

**Status**: ✅ Correctly checks blacklist flag

#### Skipping Operators (cellular_man.c lines 2807-2812):
```c
if( is_carrier_blacklisted( operators[active_operator].numeric ) ) {
    PRINTF("[Cellular Connection - Operator %d (%s) is blacklisted, skipping]\r\n", ...);
    active_operator++;
    cellular_state = CELL_SETUP_OPERATOR;
    break;  // Exit this case to skip the operator
}
```

**Status**: ✅ Correctly skips blacklisted operators

---

### 2. ✅ CME ERROR Handling (Working Correctly)

**File**: `cellular_man.c` (lines 2022-2044)

```c
else if (has_cme_error) {
    PRINTF("[Cellular Connection - DETECTED carrier failure (CME ERROR)]\r\n");

    // Get current time
    struct timeval tv;
    gettimeofday(&tv, NULL);
    imx_time_t current_time = (tv.tv_sec * 1000) + (tv.tv_usec / 1000);

    // Blacklist the carrier
    PRINTF("[Cellular Connection - Blacklisting carrier due to CME ERROR rejection]\r\n");
    blacklist_current_carrier(current_time);

    // Request rescan
    PRINTF("[Cellular Connection - Requesting carrier rescan after CME ERROR]\r\n");
    cellular_request_rescan = true;
}
```

**Status**: ✅ ANY CME ERROR triggers blacklist and rescan request

---

### 3. ✅ Script Timeout Handling (Working Correctly)

**File**: `cellular_man.c` (lines 2046-2086)

```c
else if (script_bug_0x3) {
    static int consecutive_script_timeouts = 0;
    static uint32_t script_timeout_carrier = 0;

    uint32_t current_carrier = imx_get_4G_operator_id();

    // Track consecutive timeouts with same carrier
    if (current_carrier == script_timeout_carrier) {
        consecutive_script_timeouts++;
    } else {
        consecutive_script_timeouts = 1;
        script_timeout_carrier = current_carrier;
    }

    // After 3 consecutive timeouts, blacklist
    if (consecutive_script_timeouts >= 3 && current_carrier != OPERATOR_UNKNOWN) {
        blacklist_current_carrier(current_time);
        cellular_request_rescan = true;
        consecutive_script_timeouts = 0;
    }
}
```

**Status**: ✅ 3-strike rule works correctly

---

### 4. ✅ Rescan Flag Checking (New - Working)

**File**: `cellular_man.c`

#### In CELL_ONLINE State (lines 2981-2986):
```c
// Check if a rescan has been requested (e.g., after blacklisting)
if (cellular_request_rescan) {
    PRINTF("[Cellular Connection - Rescan requested, initiating carrier scan]\r\n");
    cellular_request_rescan = false;  // Clear the flag
    cellular_state = CELL_SCAN_STOP_PPP;  // Start the scan sequence
    break;
}
```

**Status**: ✅ Flag checked during normal operation

#### In CELL_DISCONNECTED State (lines 3038-3045):
```c
// Check if a rescan has been requested
if (cellular_request_rescan) {
    PRINTF("[Cellular Connection - Rescan requested while disconnected, initiating carrier scan]\r\n");
    cellular_request_rescan = false;  // Clear the flag
    cellular_state = CELL_SCAN_STOP_PPP;  // Start the scan sequence
} else {
    cellular_state = CELL_INIT;
}
```

**Status**: ✅ Flag checked when disconnected

---

### 5. ❌ CRITICAL FLAW: Blacklist Cleared on Scan

**File**: `cellular_man.c` (line 3203)

```c
case CELL_SCAN_GET_OPERATORS:
    PRINTF("[Cellular Scan - State 3: Requesting operator list]\r\n");

    // CRITICAL FIX: Clear blacklist for fresh evaluation
    clear_blacklist_for_scan();  // ❌ THIS DEFEATS THE ENTIRE BLACKLIST!
    PRINTF("[Cellular Blacklist] Cleared for fresh carrier evaluation\n");

    // Send scan command (non-blocking)
    send_AT_command(cell_fd, "+COPS=?");
```

**Problem**: Every time a carrier scan runs (AT+COPS=?), the blacklist is **completely cleared**!

**Impact**:
1. Verizon fails with CME ERROR → Added to blacklist ✅
2. Rescan requested → Flag set ✅
3. State transitions to CELL_SCAN_STOP_PPP ✅
4. State advances to CELL_SCAN_GET_OPERATORS ✅
5. **Blacklist cleared!** ❌
6. AT+COPS=? returns operators including Verizon
7. Verizon is NO LONGER blacklisted
8. System selects Verizon again
9. **INFINITE LOOP**

**Why This Was Added**:
The comment says "Clear blacklist for fresh evaluation" - this suggests someone thought the blacklist should reset each scan. But this is fundamentally wrong for our use case.

---

## What Should Happen Instead

The blacklist should be **time-based**, not scan-based:

1. Carrier fails → Added to blacklist with timestamp
2. Blacklist entry remains for 5 minutes (DEFAULT_BLACKLIST_TIME)
3. During this 5 minutes, carrier is skipped in ALL scans
4. After 5 minutes, entry expires and carrier can be tried again

**The timeout logic already exists** in `process_blacklist()` at lines 260-275:

```c
void process_blacklist(imx_time_t current_time)
{
    for (uint32_t i = 0; i < blacklist_count; i++)
    {
        if (blacklist[i].blacklisted == true)
        {
            // Check if blacklist time has expired
            if (imx_is_later(current_time, blacklist[i].blacklist_start_time +
                            blacklist[i].current_blacklist_time))
            {
                PRINTF("[Cellular Connection - Removing carrier %u from blacklist (timeout expired)]\r\n",
                       blacklist[i].carrier_id);
                blacklist[i].blacklisted = false;
            }
        }
    }
}
```

**This is the CORRECT approach** - time-based expiry, not scan-based clearing!

---

## The Fix Required

### Option 1: Remove the clear_blacklist_for_scan() Call (RECOMMENDED)

Simply remove or comment out line 3203:

```c
case CELL_SCAN_GET_OPERATORS:
    PRINTF("[Cellular Scan - State 3: Requesting operator list]\r\n");

    // REMOVED: Don't clear blacklist - use time-based expiry instead
    // clear_blacklist_for_scan();

    // Send scan command (non-blocking)
    send_AT_command(cell_fd, "+COPS=?");
```

**Rationale**: The time-based expiry in `process_blacklist()` already handles removing old entries.

### Option 2: Conditional Clearing

Only clear blacklist if explicitly requested (e.g., `cell clear` command):

```c
// Only clear if user manually requested it
if (manual_blacklist_clear_requested) {
    clear_blacklist_for_scan();
    manual_blacklist_clear_requested = false;
}
```

### Option 3: Clear Only Expired Entries

Modify `clear_blacklist_for_scan()` to only clear expired entries:

```c
void clear_blacklist_for_scan(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    imx_time_t current_time = (tv.tv_sec * 1000) + (tv.tv_usec / 1000);

    // Only remove expired entries
    process_blacklist(current_time);
}
```

---

## Recommendation

**OPTION 1** is strongly recommended:

1. **Remove** the `clear_blacklist_for_scan()` call at line 3203
2. Let the existing `process_blacklist()` handle time-based expiry
3. This maintains blacklist integrity across scans
4. Carriers automatically become available after timeout

---

## Test Scenario to Verify Fix

### Before Fix (Current Behavior):
```
1. Verizon fails → Blacklisted
2. Rescan triggered → Flag set
3. State → CELL_SCAN_STOP_PPP
4. State → CELL_SCAN_GET_OPERATORS
5. Blacklist CLEARED ❌
6. AT+COPS=? returns all operators
7. Verizon selected again
8. Fails again → Infinite loop
```

### After Fix (Expected Behavior):
```
1. Verizon fails → Blacklisted
2. Rescan triggered → Flag set
3. State → CELL_SCAN_STOP_PPP
4. State → CELL_SCAN_GET_OPERATORS
5. Blacklist PRESERVED ✅
6. AT+COPS=? returns all operators
7. Verizon skipped (blacklisted)
8. AT&T selected
9. Connection succeeds ✅
```

---

## Summary of Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Blacklist add logic | ✅ Working | Properly adds carriers |
| Blacklist check logic | ✅ Working | Checks blacklist flag |
| Operator skipping | ✅ Working | Skips blacklisted operators |
| CME ERROR detection | ✅ Working | ANY CME ERROR triggers blacklist |
| Script timeout counting | ✅ Working | 3-strike rule implemented |
| Rescan flag checking | ✅ Working | Checked in CELL_ONLINE/DISCONNECTED |
| State machine flow | ✅ Working | Transitions to CELL_SCAN_STOP_PPP |
| **Blacklist persistence** | ❌ **BROKEN** | **Cleared on every scan** |
| Time-based expiry | ✅ Working | But never used due to clearing |

---

## Files That Need Changes

1. **cellular_man.c** (line 3203)
   - Remove or comment out `clear_blacklist_for_scan()` call

2. **No other changes needed** - all other logic is correct!

---

## Why This Wasn't Caught Earlier

1. Focus was on "why isn't rescan happening" (fixed ✅)
2. Didn't trace through complete scan flow
3. The clear call is near the beginning of scan state
4. Comment suggested it was intentional ("fresh evaluation")
5. Test logs (net14-17) focused on blacklist adds, not persistence

---

## Next Steps

1. Remove `clear_blacklist_for_scan()` call from line 3203
2. Rebuild binary
3. Test complete flow:
   - Verify carrier gets blacklisted
   - Verify rescan executes
   - **Verify blacklist persists during scan**
   - Verify blacklisted carrier is skipped
   - Verify alternative carrier selected

---

**End of Comprehensive Review**