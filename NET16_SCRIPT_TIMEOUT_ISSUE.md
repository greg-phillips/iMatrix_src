# net16.txt Analysis - Script Timeout Loop Issue

**Date**: 2025-11-24
**Time**: 06:40
**Build**: Nov 24 2025 @ 06:33:41 (WITH blacklist fixes)
**Issue**: 30 script timeouts with same carrier, no blacklisting
**Status**: ⚠️ **DESIGN LIMITATION IDENTIFIED**

---

## Executive Summary

The blacklist fixes ARE working correctly, but there's a design limitation:

1. ✅ Blacklist code is present and functional
2. ✅ CME ERROR failures WOULD be blacklisted
3. ⚠️ Script timeouts (exit code 0x3) don't trigger blacklisting
4. ❌ System retries same carrier 30 times without trying alternatives

---

## The Problem

### What's Happening:

1. **Verizon (311480)** is already selected
2. PPP connection attempts fail with **script timeout** (exit code 0x3)
3. System cleans up and retries
4. **30 failures** with the same carrier
5. Never tries AT&T, T-Mobile, or others
6. No blacklisting occurs (by design)

### Evidence from net16.txt:

```
Line 5: Fleet Connect built on Nov 24 2025 @ 06:33:41  ← Has our fixes
Line 478: +COPS: 1,2,"311480",7  ← Verizon selected
Line 580: DETECTED script bug/timeout (exit code 0x3)  ← NOT CME ERROR
Line 581: Cleaning up failed PPP processes (bug workaround, not carrier issue)
Line 791: Blacklist Status: No blacklisted carriers found  ← Empty blacklist
```

**30 occurrences** of script timeout, all handled as "not carrier issue"

---

## Why This Is A Problem

### Current Design Logic:

```c
// cellular_man.c line 2036-2038
else if (script_bug_0x3) {
    // Script bug - don't blacklist carrier
    // Assumption: script bug affects ALL carriers equally
}
```

### The Flawed Assumption:

The code assumes script timeouts are universal (our bug), but they can be carrier-specific:

1. **Carrier-specific APNs** - Wrong APN for Verizon might work for AT&T
2. **Authentication methods** - PAP vs CHAP requirements differ
3. **Network responses** - Some carriers timeout, others reject cleanly
4. **Signal quality** - Weak signal causes timeouts, not CME ERROR

### Real-World Impact:

- Verizon might have script timeout due to wrong APN
- AT&T might work fine with same script
- System never tries AT&T because it doesn't blacklist on timeout
- User stuck with no connection when alternatives exist

---

## Proposed Solution

### Option 1: Blacklist After N Script Timeouts (Recommended)

Add a counter for consecutive script timeouts with same carrier:

```c
// Add to cellular_man.c
static int script_timeout_count = 0;
static uint32_t script_timeout_carrier = 0;

else if (script_bug_0x3) {
    uint32_t current_carrier = imx_get_4G_operator_id();

    if (current_carrier == script_timeout_carrier) {
        script_timeout_count++;
    } else {
        script_timeout_count = 1;
        script_timeout_carrier = current_carrier;
    }

    if (script_timeout_count >= 3) {  // After 3 failures
        PRINTF("[Cellular Connection - Multiple script timeouts with carrier %u, blacklisting]\r\n",
               current_carrier);

        struct timeval tv;
        gettimeofday(&tv, NULL);
        imx_time_t current_time = (tv.tv_sec * 1000) + (tv.tv_usec / 1000);
        blacklist_current_carrier(current_time);

        script_timeout_count = 0;  // Reset counter
    }
}
```

### Option 2: Trigger Rescan After N Failures

Force a carrier rescan after repeated failures:

```c
if (script_timeout_count >= 5) {
    PRINTF("[Cellular Connection - Too many failures, forcing carrier rescan]\r\n");
    cellular_request_rescan = true;
    cellular_state = CELL_SCAN_GET_OPERATORS;
}
```

### Option 3: Temporary Blacklist for Script Timeout

Create a separate, shorter blacklist for script timeouts:

```c
blacklist_carrier_temporary(current_carrier, 60000);  // 1 minute blacklist
```

---

## Implementation Recommendation

### Quick Fix (Option 1):

```c
// In handle_chat_script_failure() around line 2036
else if (script_bug_0x3) {
    static int consecutive_timeouts = 0;
    static uint32_t timeout_carrier = 0;

    uint32_t current = imx_get_4G_operator_id();

    // Track consecutive failures with same carrier
    if (current == timeout_carrier) {
        consecutive_timeouts++;
    } else {
        consecutive_timeouts = 1;
        timeout_carrier = current;
    }

    PRINTF("[Cellular Connection - Script timeout #%d with carrier %u]\r\n",
           consecutive_timeouts, current);

    // Blacklist after 3 consecutive timeouts
    if (consecutive_timeouts >= 3 && current != OPERATOR_UNKNOWN) {
        PRINTF("[Cellular Connection - Blacklisting carrier %u after %d script timeouts]\r\n",
               current, consecutive_timeouts);

        struct timeval tv;
        gettimeofday(&tv, NULL);
        imx_time_t current_time = (tv.tv_sec * 1000) + (tv.tv_usec / 1000);
        blacklist_current_carrier(current_time);

        // Force rescan to try other carriers
        cellular_request_rescan = true;
        consecutive_timeouts = 0;
    }

    PRINTF("[Cellular Connection - Cleaning up failed PPP processes]\r\n");
}
```

---

## Testing the Current Blacklist

### To Verify Blacklist Works (Force CME ERROR):

```bash
# 1. Connect to modem AT port
minicom -D /dev/ttyUSB2

# 2. Force wrong APN (causes CME ERROR)
AT+CGDCONT=1,"IP","wrong.apn.invalid"

# 3. Watch logs
tail -f /var/log/FC-1.log | grep -i blacklist

# Should see:
# "New carrier added to blacklist: 311480 (total: 1)"
```

### What Currently Happens:

1. Script timeout → No blacklist
2. Retry same carrier → Script timeout
3. Repeat 30 times → Still no blacklist
4. Never tries other carriers

### What Should Happen:

1. Script timeout #1 → Retry
2. Script timeout #2 → Retry
3. Script timeout #3 → Blacklist carrier
4. Scan for alternatives → Try AT&T/T-Mobile
5. If they fail too → Real script problem
6. If they work → Carrier-specific issue

---

## Conclusion

### Current Status:

✅ **Blacklist implementation is correct**
✅ **Works for CME ERROR (carrier rejection)**
⚠️ **Doesn't handle repeated script timeouts**
❌ **Can get stuck with one carrier**

### Recommendation:

Implement **Option 1** - Blacklist after 3 consecutive script timeouts with same carrier. This maintains the distinction between carrier issues and script bugs while preventing infinite loops with problematic carriers.

### Files to Modify:

1. `cellular_man.c` line ~2036 - Add timeout counting and conditional blacklist
2. No changes needed to blacklist system itself (working correctly)

---

**End of Analysis**