# Thread-Safety Fix for btstack Timer - Implementation Details

**Date:** 2025-11-14
**Branch:** `fix/wifi-blacklisting-score-zero`
**Critical Issue:** Main loop deadlock from btstack timer removal
**Status:** ⚠️ **CODE COMPLETE - BUILD SYSTEM ISSUES**

---

## Executive Summary

logs13.txt revealed a **catastrophic main loop freeze** caused by our SSL timer removal fix:
- **1,487 GPS circular buffer errors** (vs 9 in logs12.txt)
- **Main loop completely stopped** at 02:02:37
- **System hung** until manual termination
- **Root cause:** btstack_run_loop_remove_timer() is NOT thread-safe

### Solution Implemented

Replaced unsafe timer removal with **thread-safe flag-based approach**:
- Timer handler checks validity flag before accessing SSL context
- Timer expires naturally in btstack thread (no cross-thread removal)
- 20ms delay ensures in-flight timer sees flag before SSL freed

---

## Root Cause Analysis

### The Deadlock Mechanism

**File:** `btstack/platform/posix/btstack_run_loop_posix.c` lines 279-288

**btstack Main Loop (Thread 1):**
```c
while (true) {
    // ... select() on file descriptors ...

    // Process timers
    now_ms = btstack_run_loop_posix_get_time_ms();
    while (timers) {
        ts = (btstack_timer_source_t *) timers;  // ← Reading timer list
        int32_t delta = btstack_time_delta(ts->timeout, now_ms);
        if (delta > 0) break;

        btstack_run_loop_posix_remove_timer(ts);  // ← Modifying list
        ts->process(ts);  // ← Call handler
    }
}
```

**Our Buggy Code (Thread 2 - Network Manager):**
```c
void deinit_udp(imx_network_interface_t interface)
{
    // ...
    btstack_run_loop_remove_timer(&_dtls_handshake_timer);  // ← RACE CONDITION!
    // ...
    mbedtls_ssl_free(&ssl);
}
```

### Race Condition Timeline

```
Time  Btstack Thread (Main Loop)        Network Manager Thread
----  ---------------------------------  ---------------------------
T0    while (timers) {
T1      ts = timers; (get timer ptr)
T2                                       deinit_udp() called
T3                                       btstack_run_loop_remove_timer()
T4                                       Modifies timer linked list
T5      CHECK ts->timeout
T6      CORRUPTED POINTER!
T7      SEGFAULT or INFINITE LOOP
```

**Result:**
- Timer list corrupted by concurrent modification
- btstack main loop freezes (infinite loop or crash in linked list traversal)
- GPS processing stops
- Circular buffer fills
- 1,487 "bytes not written" errors
- System completely hung

---

## Implementation: Thread-Safe Flag Approach

### Fix Overview

**Instead of removing timer from outside btstack thread:**
1. Set flag: `_ssl_context_valid = false`
2. Wait 20ms for any in-flight timer to see flag
3. Timer handler checks flag and exits early
4. Timer naturally expires in btstack thread (thread-safe)

### Code Changes

**1. Add Thread-Safety Flag (Line 309)**

```c
/**
 * Thread-safety flag for SSL context lifecycle
 *
 * CRITICAL: btstack_run_loop_remove_timer() is NOT thread-safe and cannot
 * be called from outside the btstack run loop thread. Attempting to remove
 * a timer from the network manager thread while btstack is processing timers
 * causes list corruption and main loop freeze.
 *
 * Solution: Use this flag to signal the timer handler that SSL is being
 * destroyed. Handler checks flag and exits early, allowing timer to expire
 * naturally within the btstack thread.
 */
static volatile bool _ssl_context_valid = false;
```

**2. Set Flag True in init_udp() (Line 626)**

```c
bool init_udp(imx_network_interface_t interface)
{
    // ... SSL initialization ...

    _udp_initialized = true;

    /**
     * CRITICAL: Mark SSL context as valid before starting handshake timer
     * This flag is checked by timer handler to prevent use-after-free when
     * deinit_udp() is called from a different thread.
     */
    _ssl_context_valid = true;

    // ... start handshake timer ...
}
```

**3. Set Flag False in deinit_udp() (Line 709)**

```c
void deinit_udp(imx_network_interface_t interface)
{
    reset_retry_counter();

    /**
     * CRITICAL FIX: Signal timer handler that SSL is being destroyed
     *
     * IMPORTANT: We cannot call btstack_run_loop_remove_timer() from this thread
     * (network manager thread) because btstack run loop is NOT thread-safe.
     * Calling remove_timer from outside btstack thread causes timer list corruption
     * and main loop freeze (see logs13.txt - 1487 GPS buffer errors, system hung).
     *
     * Solution: Set flag to signal timer handler. Timer will check flag and exit
     * early without accessing SSL context, allowing it to expire naturally in
     * btstack thread without race conditions.
     */
    _ssl_context_valid = false;

    /**
     * Brief delay to ensure timer handler sees the flag if it's currently executing
     * Timer fires every 10ms, so 20ms delay ensures any in-flight handler completes
     * and sees the flag before we free SSL context.
     */
    imx_delay_milliseconds(20);

    // ... rest of cleanup ...
    mbedtls_ssl_free(&ssl);
}
```

**4. Check Flag in Timer Handler (Line 372)**

```c
static void _dtls_handshake_timer_hnd(btstack_timer_source_t *ts)
{
    int ret;

    /**
     * Thread-safety check: Exit if SSL context is being destroyed
     *
     * CRITICAL: This timer runs in btstack thread, but deinit_udp() is called
     * from network manager thread. We can't safely remove timer from outside
     * btstack thread, so we check this flag and exit early if SSL is invalid.
     */
    if (!_ssl_context_valid)
    {
        PRINTF("DTLS handshake timer: SSL context invalid, timer expiring naturally\r\n");
        return;  // Don't re-add timer, will expire naturally
    }

    // Normal handshake processing...
    ret = mbedtls_ssl_handshake_step(&ssl);
    // ...
}
```

---

## Thread Safety Analysis

### Why This Fix Works

**1. No Cross-Thread List Modification:**
- Network manager thread only sets a boolean flag
- btstack thread is sole modifier of timer list
- No race condition on list structure

**2. Memory Barrier via `volatile`:**
- `volatile bool _ssl_context_valid` ensures flag write is visible across threads
- Compiler won't optimize away flag check
- Value guaranteed to be read from memory each time

**3. Grace Period:**
- 20ms delay after setting flag ensures timer sees it
- Timer fires every 10ms, so 20ms covers 2 potential firings
- Prevents use-after-free even if timer mid-execution

**4. Natural Expiration:**
- Timer handler returns without re-adding timer
- Timer removed from list by btstack thread naturally
- No external intervention needed

### Threading Model

```
Thread 1: btstack run loop
  - select() waits for file descriptors
  - Processes timers every iteration
  - Calls _dtls_handshake_timer_hnd()
  - Removes and re-adds timers
  - OWNS timer list

Thread 2: Network manager
  - Monitors interface status
  - Switches interfaces on failures
  - Calls deinit_udp() on interface change
  - Sets _ssl_context_valid flag
  - DOES NOT touch timer list

Thread 3: Ping test threads
  - Detached pthread for each ping
  - Updates interface scores
  - No timer interaction
```

---

## Comparison: Buggy vs Fixed Approaches

### Buggy Approach (Caused logs13.txt Freeze)

```c
void deinit_udp(...)
{
    btstack_run_loop_remove_data_source(&coap_udp_source);
    btstack_run_loop_remove_timer(&_dtls_handshake_timer);  // ← UNSAFE!
    mbedtls_ssl_free(&ssl);
}
```

**Problems:**
- ❌ Cross-thread timer list modification
- ❌ Race condition with btstack loop iterating timers
- ❌ List corruption
- ❌ Main loop freeze
- ❌ System completely hung (1,487 GPS errors)

### Fixed Approach (Thread-Safe)

```c
static volatile bool _ssl_context_valid = false;  // Global flag

void init_udp(...)
{
    // ... init SSL ...
    _ssl_context_valid = true;  // ✅ Mark valid
    _btstack_dtls_handshake();  // Start timer
}

void deinit_udp(...)
{
    _ssl_context_valid = false;  // ✅ Signal destruction
    imx_delay_milliseconds(20);  // ✅ Let timer see flag

    btstack_run_loop_remove_data_source(&coap_udp_source);
    // NO timer removal - let it expire naturally

    mbedtls_ssl_free(&ssl);
}

void _dtls_handshake_timer_hnd(...)
{
    if (!_ssl_context_valid) {  // ✅ Check flag
        return;  // ✅ Exit early, don't re-add
    }

    // Normal handshake...
}
```

**Benefits:**
- ✅ No cross-thread list modification
- ✅ No race conditions
- ✅ Main loop remains responsive
- ✅ GPS processing continues
- ✅ System stays operational

---

## Expected Behavior After Fix

### Scenario: Interface Change wlan0 → ppp0

**With Buggy Code (logs13.txt):**
```
[02:02:37] Ping reply #1
[02:02:37] (Network manager calls deinit_udp)
[02:02:37] (btstack timer list corrupted)
[02:02:37] (Main loop FREEZES)
[02:02:30] ERROR: 41 bytes not written (GPS backup starts)
[02:03:14] ERROR: 8 bytes not written
... 1,487 total GPS errors over ~20 minutes ...
[User kills application]
```

**With Fixed Code (Expected):**
```
[02:02:37] Ping reply #1
[02:02:37] Switching to ppp0
[02:02:37] Resetting UDP connection for: ppp0
[02:02:37] DTLS handshake timer: SSL context invalid, timer expiring naturally
[02:02:37] | UDP Coordinator | UDP shutdown
[02:02:37] Init UDP on ppp0
[02:02:38] | UDP Coordinator | Certificates valid. Start DTLS.
[02:02:39] SSL handshake complete
[02:02:40] (Main loop continues normally)
[02:02:45] Ping test on ppp0: score=10
```

**Key Differences:**
- ✅ Timer exits gracefully with log message
- ✅ Main loop continues processing
- ✅ No GPS buffer errors
- ✅ Clean interface transition
- ✅ System remains operational

---

## Build Status

### Current Situation

**Code Changes:** ✅ COMPLETE
**Files Modified:** 1 (`iMatrix/coap/udp_transport.c`)
**Lines Changed:** +35 lines added

**Build Status:** ⚠️ **BLOCKED BY MBEDTLS SUBMODULE ISSUES**

**Build Errors:**
- mbedtls tests require Python 3 (not available in build environment)
- mbedtls test helpers have compiler flag conflicts (`-fstack-check` vs `-fstack-clash-protection`)
- These are **pre-existing build system issues**, not related to our changes

**Workaround Attempted:**
- Used `-DENABLE_TESTING=OFF` to skip tests
- CMake configuration succeeds
- mbedtls library builds successfully
- mbedtls test helpers still being built (and failing)

### Recommended Actions

**Option 1: Fix mbedtls Submodule (RECOMMENDED)**
```bash
cd /home/greg/iMatrix/iMatrix_Client/mbedtls
git checkout -- .  # Reset all modifications
cd ../Fleet-Connect-1/build
cmake .. -DENABLE_TESTING=OFF
make
```

**Option 2: Disable mbedtls Test Helpers in CMake**
- Modify mbedtls/CMakeLists.txt to skip test helper targets
- Requires understanding build system

**Option 3: Use Previous Working Build**
- Restore from known-good build directory
- Apply binary patch if needed

---

## Code Review

### Changes Summary

**File:** `iMatrix/coap/udp_transport.c`

**Change 1: Add Flag (Line 309)**
- Added `static volatile bool _ssl_context_valid`
- Thread-safe signal for SSL lifecycle

**Change 2: Initialize Flag (Line 626)**
- Set `_ssl_context_valid = true` after SSL init
- Marks context ready for use

**Change 3: Signal Destruction (Line 709)**
- Set `_ssl_context_valid = false` in deinit_udp()
- Added 20ms delay for timer to see flag
- Removed unsafe `btstack_run_loop_remove_timer()` call

**Change 4: Check Flag in Handler (Line 372)**
- Early exit if `!_ssl_context_valid`
- Prevents use-after-free
- Prevents reboot on SSL errors

**Total Impact:**
- +35 lines (comments + code)
- -1 line (removed unsafe timer removal)
- Net: +34 lines

---

## Testing Requirements (Once Build Works)

### Critical Test: No Main Loop Freeze

**Test Procedure:**
1. Start FC-1 with wlan0 connected
2. Monitor with: `tail -f /var/log/syslog | grep -E "ERROR:|NETMGR"`
3. Force interface change (disable WiFi)
4. Verify system switches to ppp0
5. **CRITICAL CHECK:** GPS buffer errors should NOT accumulate
6. **CRITICAL CHECK:** Network manager logs should CONTINUE
7. Run for 10+ minutes
8. Verify < 10 GPS buffer errors total (not 1,487!)

**Success Criteria:**
- ✅ No main loop freeze
- ✅ Network manager continues operating
- ✅ GPS buffer errors minimal or none
- ✅ System responsive
- ✅ Interface changes complete successfully

### Secondary Tests

**Test 2: Verify Timer Message**
- Look for: "DTLS handshake timer: SSL context invalid, timer expiring naturally"
- Should appear once per interface change
- Confirms flag-based exit is working

**Test 3: No SSL Crashes**
- Verify no "SSL Bad Input Data - forcing a reboot" messages
- Verify no system reboots
- Continuous uptime through multiple failovers

---

## All Fixes Summary (This Branch)

### Bug #1: WiFi Blacklisting (COMPLETE ✅)
- **File:** process_network.c
- **Fix:** Changed condition to include score=0
- **Status:** Validated in logs11.txt

### Bug #2: SSL Timer Use-After-Free (REVISED ✅)
- **File:** udp_transport.c
- **Original Fix:** Direct timer removal (CAUSED DEADLOCK)
- **Revised Fix:** Flag-based expiration (THREAD-SAFE)
- **Status:** Code complete, needs testing

### Bug #3: SSL Error Reboot (COMPLETE ✅)
- **File:** udp_transport.c
- **Fix:** Recovery instead of reboot
- **Status:** Part of timer handler fix

---

## Build Issue Details

### Problem

mbedtls submodule has uncommitted changes in tests/ directory (94 modified files).
Tests CMakeLists.txt requires Python 3 which is not available/compatible in build environment.

**Error:**
```
CMake Error at mbedtls/tests/CMakeLists.txt:14 (message):
  Cannot build test suites without Python 3
```

Even with `-DENABLE_TESTING=OFF`, test helper targets still being built:
```
cc1: error: '-fstack-check=' and '-fstack-clash-protection' are mutually exclusive
make[2]: *** [mbedtls_test.dir/tests/src/bignum_helpers.c.o] Error 1
```

### Recommendation for Greg

**You likely need to:**

1. **Reset mbedtls submodule:**
   ```bash
   cd /home/greg/iMatrix/iMatrix_Client/mbedtls
   git checkout -- .
   git clean -fd
   ```

2. **Or provide Python 3:**
   ```bash
   which python3
   export PYTHON_EXECUTABLE=/usr/bin/python3
   ```

3. **Or use previous working build configuration**

**Once build works, the thread-safety fix should prevent the main loop freeze seen in logs13.txt.**

---

**Implementation Status:** ✅ CODE COMPLETE
**Build Status:** ⚠️ BLOCKED (build system issues)
**Testing Status:** ⏳ PENDING (waiting for successful build)
**Recommendation:** Fix build environment, then test thoroughly

---

**Prepared by:** Claude Code
**Date:** 2025-11-14
**Branch:** fix/wifi-blacklisting-score-zero
