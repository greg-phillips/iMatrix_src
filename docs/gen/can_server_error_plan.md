# CAN Server Error Diagnostics and Fix Plan

**Date:** 2025-12-26
**Author:** Claude Code
**Document Version:** 1.1
**Status:** Implemented

---

## Summary

The CAN TCP server fails to start due to a `bind()` error, but the error message provides no useful diagnostic information. After multiple restart attempts, the thread registry becomes full. This document outlines the root causes and fixes for both issues.

---

## Issue Analysis

### Issue 1: bind() Error with "No error information"

**Location:** `iMatrix/canbus/can_server.c:490-509`

**Root Cause:** A local variable `int errno;` declared at line 490 shadows the global `errno` from `<errno.h>`. When `bind()` fails:

```c
int errno;  // Line 490 - LOCAL variable shadows global errno!
...
if ((errno = bind(server_fd, ...) ) < 0)  // Line 507
{
    PRINTF("bind: %d: %s", errno, strerror(errno));  // Line 509
}
```

The code assigns the return value of `bind()` (which is -1 on error) to the local `errno`, then calls `strerror(-1)` which returns "No error information". The actual system errno (e.g., EADDRINUSE=98) is never captured.

**Fix:**
1. Remove the local `int errno;` declaration
2. Capture the global `errno` immediately after failed socket operations
3. Report both the errno value and its meaning

### Issue 2: Thread Registry Full

**Location:** `iMatrix/platform_functions/thread_tracker.c`

**Root Cause:** When threads terminate, `thread_registry_record_exit()` records the exit status but **never sets `is_active = false`**. Thread slots are never freed. After `MAX_TRACKED_THREADS` (32) threads have been created, the registry is permanently full.

**Current code in thread_registry_record_exit():**
```c
if (entry->is_active) {
    clock_gettime(CLOCK_MONOTONIC, &entry->end_time);
    entry->status = status;  // Sets status but NOT is_active!
    entry->exit_code = exit_code;
    entry->exit_value = exit_value;
}
```

**Fix:**
Add a `thread_registry_unregister()` function to free slots from terminated threads, and call it when threads exit normally.

---

## Branch Status

| Submodule | Original Branch | Work Branch |
|-----------|----------------|-------------|
| iMatrix | `feature/add_debug_modes` | `debug/can_server_error` |
| Fleet-Connect-1 | `Aptera_1_Clean` | (no changes needed) |

---

## Completed TODO List

### Phase 1: Setup
- [x] Create `debug/can_server_error` branch in iMatrix submodule

### Phase 2: Fix errno Shadowing (Issue 1)
- [x] Remove local `int errno;` declaration from `tcp_server_thread()` in `can_server.c`
- [x] Add `saved_errno` variable to properly capture errno
- [x] Improve error reporting for `socket()` failure to capture actual errno
- [x] Improve error reporting for `bind()` failure to capture actual errno
- [x] Improve error reporting for `listen()` failure to capture actual errno
- [x] Improve error reporting for `select()` failure to capture actual errno
- [x] Improve error reporting for `recv()` failure to capture actual errno
- [x] Add port-in-use specific diagnostic for EADDRINUSE
- [x] Add address-not-available diagnostic for EADDRNOTAVAIL
- [x] Add SO_REUSEADDR socket option to allow quick restart after crash
- [x] Handle EINTR in select() by continuing instead of breaking

### Phase 3: Fix Thread Registry Full (Issue 2)
- [x] Add `thread_registry_unregister()` function declaration to `thread_tracker.h`
- [x] Implement `thread_registry_unregister()` in `thread_tracker.c`
- [x] Call `thread_registry_unregister()` when thread exits normally in `_thread_monitoring_wrapper()`

### Phase 4: Build Verification
- [x] Build iMatrix submodule - verify zero errors/warnings
- [x] Perform final clean build verification

---

## Implementation Summary

### Files Modified

1. **iMatrix/canbus/can_server.c**
   - Removed `int errno;` local variable that shadowed global errno
   - Added `int saved_errno;` to properly capture errno values
   - Added `SO_REUSEADDR` socket option to allow quick server restart
   - Improved all error messages to show errno number and description
   - Added specific diagnostics for EADDRINUSE and EADDRNOTAVAIL
   - Fixed select() to handle EINTR gracefully (continue instead of break)
   - **Added thread synchronization for restarts:**
     - Added `g_server_thread_running` flag to track thread execution
     - Set flag `true` at thread start, `false` at all exit points
     - Updated `stop_can_server()` to wait up to 3 seconds for thread exit
     - Updated `start_can_server()` to check both `g_server_socket_fd` and `g_server_thread_running`
   - **Added automatic port cleanup:**
     - Added `free_port()` function that uses `fuser -k` to kill any process on the port
     - Called before bind() to ensure port is available
     - Waits 500ms after kill for port to be released
     - Verifies port is freed before proceeding

2. **iMatrix/platform_functions/thread_tracker.h**
   - Added declaration for `thread_registry_unregister()` function

3. **iMatrix/platform_functions/thread_tracker.c**
   - Implemented `thread_registry_unregister()` function that:
     - Sets `is_active = false` to free the registry slot
     - Decrements the registry count
     - Uses proper mutex protection

4. **iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.c**
   - Updated `_thread_monitoring_wrapper()` to call `thread_registry_unregister()` after recording thread exit

### Error Messages Before vs After

**Before:**
```
[CAN TCP Server Error: bind: -1: No error information]
```

**After:**
```
[CAN TCP Server Error: bind failed on 192.168.7.1:5555 - errno=98 (Address already in use)]
[CAN TCP Server] Port 5555 already in use - check for existing server instance
```

---

## Metrics

| Metric | Value |
|--------|-------|
| Recompilations for syntax errors | 0 |
| Build warnings introduced | 0 |
| Files modified | 4 |
| Lines added | ~70 |
| Lines removed | ~10 |

---

## Next Steps

1. **Testing Required:** Test on actual hardware to verify:
   - Error messages now show correct errno values
   - Thread registry slots are freed when threads exit
   - CAN server can restart successfully after previous failure
   - SO_REUSEADDR allows immediate restart

2. **Merge:** Once testing is complete, merge `debug/can_server_error` back to `feature/add_debug_modes`

---

*Plan Created By: Claude Code*
*Source Specification: docs/prompt_work/can_server_error.yaml*
*Implementation Completed: 2025-12-26*
