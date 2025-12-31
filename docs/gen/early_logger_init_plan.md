# Early Logger Initialization Plan

**Date**: 2025-12-31
**Status**: PROPOSED
**Author**: Claude Code
**Related**: docs/gen/logging_work_plan.md

## Problem Statement

Startup messages are not being captured in the filesystem log file because:
1. `fs_logger_init()` is called at line 646 in `imatrix_start()`
2. Important startup messages happen BEFORE this point (lines 590-594)
3. Messages to `imx_cli_log_printf()` are buffered in the async queue but not written to file until `fs_logger_init()` completes

## Current Initialization Order in imatrix_start()

```
Line 586: acquire_lock_and_maybe_kill()  ← uses printf() (pre-logging, OK)
Line 590: "Could not acquire lock..."    ← imx_cli_log_printf() - LOST
Line 594: "Lock acquired successfully"   ← imx_cli_log_printf() - LOST
Line 628: init_global_log_queue()        ← async queue starts
Line 632: "Async log queue initialized"  ← imx_cli_log_printf() - LOST
Line 646: fs_logger_init()               ← filesystem logging starts
Line 650: "Filesystem logger initialized"← imx_cli_log_printf() - captured
```

## Proposed Solution

Move BOTH `init_global_log_queue()` AND `fs_logger_init()` to the very top of `imatrix_start()`, immediately after the lock acquisition.

### New Order:

```
Line 586: acquire_lock_and_maybe_kill()  ← uses printf() (pre-logging, OK)
NEW:      init_global_log_queue()        ← async queue starts FIRST
NEW:      fs_logger_init()               ← filesystem logging starts SECOND
Line 590: "Could not acquire lock..."    ← NOW CAPTURED
Line 594: "Lock acquired successfully"   ← NOW CAPTURED
```

### Alternative: Move before lock acquisition

If we want to capture even the lock messages, we could move the logging init to before the lock:

```
NEW:      init_global_log_queue()        ← async queue starts FIRST
NEW:      fs_logger_init()               ← filesystem logging starts SECOND
Line 586: acquire_lock_and_maybe_kill()  ← uses printf() (still pre-logging)
Line 590: "Could not acquire lock..."    ← NOW CAPTURED
Line 594: "Lock acquired successfully"   ← NOW CAPTURED
```

## Implementation Steps

### Step 1: Move init_global_log_queue() earlier

Edit `iMatrix/imatrix_interface.c`:
- Remove lines 628-633 (current async queue init)
- Insert at line 587 (after lock acquisition, before lock messages)

### Step 2: Move fs_logger_init() earlier

Edit `iMatrix/imatrix_interface.c`:
- Remove lines 646-657 (current filesystem logger init)
- Insert at line 588 (after async queue init, before lock messages)

### Step 3: Update check_process.c (optional)

The `acquire_lock_and_maybe_kill()` function uses printf() at line 107. This could be converted to imx_cli_log_printf() IF logging is initialized before this point.

However, this would require moving logging init to before the lock, which may have ordering dependencies (e.g., lock file might be in the log directory).

**Recommendation**: Keep printf() for lock acquisition message. It runs once at startup and using printf() is safer at that early point.

## Code Changes

### imatrix_interface.c - New imatrix_start() beginning:

```c
void imatrix_start(void)
{
    uint16_t count;
#ifdef LINUX_PLATFORM
    const char *lockfile = IMATRIX_STORAGE_PATH "/iMatrix.lock";

    /*
     * EARLY LOGGING INITIALIZATION
     * Initialize logging subsystem FIRST so all startup messages are captured.
     * Order: 1) Async queue, 2) Filesystem logger
     */

    /* Initialize async log queue - enables non-blocking imx_cli_log_printf() */
    if (init_global_log_queue() != 0) {
        printf("WARNING: Failed to initialize async log queue - using direct logging\r\n");
    }

    /* Initialize filesystem logger - enables log file writing */
    if (fs_logger_init() != IMX_SUCCESS) {
        printf("WARNING: Failed to initialize filesystem logger\r\n");
    } else {
        imx_cli_log_printf(true, "Filesystem logger initialized (%s/%s)\r\n",
               FS_LOG_DIRECTORY, FS_LOG_FILENAME);
        if (fs_logger_interactive_mode) {
            imx_cli_log_printf(true, "  Interactive mode: logs to console AND filesystem\r\n");
        } else {
            imx_cli_log_printf(true, "  Quiet mode: logs to filesystem only\r\n");
        }
    }

    /* Now acquire lock - messages will be logged */
    int fd = acquire_lock_and_maybe_kill(lockfile);
    if (fd < 0) {
        imx_cli_log_printf(true, "Could not acquire lock or kill existing process. Presume it does not exist.\r\n");
    } else {
        imx_cli_log_printf(true, "Lock acquired successfully. No other instance is running now.\r\n");
    }
#endif
    // ... rest of function
```

## Dependencies to Check

1. **fs_logger_init() requires /var/log directory** - Should exist on target
2. **init_global_log_queue() has no dependencies** - Can be called early
3. **Lock file is in IMATRIX_STORAGE_PATH** - Different from log directory, no conflict

## Testing Plan

1. Build with changes
2. Deploy to gateway: `./scripts/fc1 push`
3. Start service: `./scripts/fc1 start`
4. Check log file: `grep "Lock acquired\|Filesystem logger" /var/log/fc-1.log`
5. Verify startup messages appear in log file

## Risks

- **Low**: Moving init earlier shouldn't break anything
- **Medium**: If filesystem isn't mounted, fs_logger_init() will fail gracefully
- **None**: Async queue has no external dependencies

## Estimated Changes

- Files modified: 1 (imatrix_interface.c)
- Lines changed: ~40 (move/reorder existing code)
- Build iterations: 1

---

## Implementation Results (December 31, 2025)

**Status**: COMPLETE - ALL TESTS PASSING

### Changes Made

1. **imatrix_interface.c** - Moved logging initialization to start of `imatrix_start()`:
   - `init_global_log_queue()` now called first (before lock acquisition)
   - `fs_logger_init()` called second (before lock acquisition)
   - Lock acquisition messages now captured in log file

2. **filesystem_logger.c** - Fixed critical flushing bug:
   - Changed from periodic flush (every 4096 bytes) to immediate flush
   - This ensures all log messages are written to disk immediately
   - Critical for capturing startup messages and crash recovery

### Test Results

Log file now shows complete startup sequence:
```
=== FC-1 Log Started: 2025-12-31 21:04:28 ===
[00:00:00.000] Filesystem logger initialized (/var/log/fc-1.log)
[00:00:00.000]   Quiet mode: logs to filesystem only
[00:00:00.004] Lock acquired successfully. No other instance is running now.
[00:00:00.005] Fleet Connect built on Dec 31 2025 @ 13:02:12
[00:00:00.005] Display setup finished
[00:00:00.007] Commencing iMatrix Initialization Phase 0.0
[00:00:00.007] Initialization Phase 0.1
```

### Key Fix Discovery

During testing, discovered that the original `fs_logger_write()` only flushed to disk
every 4096 bytes. This caused startup messages to remain in the write buffer and not
appear in the log file. The fix ensures immediate flushing after every write.

---

*Document created: 2025-12-31*
*Implementation completed: 2025-12-31*
