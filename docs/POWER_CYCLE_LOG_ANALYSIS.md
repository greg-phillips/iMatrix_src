# Power Cycle Log Analysis Report

**Date**: 2026-01-02
**Last Updated**: 2026-01-02 19:32
**Author**: Claude Code Analysis
**Status**: ✅ FIX IMPLEMENTED AND VERIFIED

---

## Executive Summary

**ORIGINAL FINDING**: No graceful shutdown occurred when `sv stop FC-1` was called. The SIGTERM signal was not handled, causing immediate process termination.

**RESOLUTION**: SIGTERM handler implemented in `Fleet-Connect-1/linux_gateway.c` that erases all data on shutdown for clean testing restarts.

| Issue | Original Status | Current Status |
|-------|-----------------|----------------|
| Graceful shutdown code exists | YES - in `process_power.c` | YES - plus new SIGTERM handler |
| SIGTERM signal handler registered | **NO - MISSING** | ✅ **IMPLEMENTED** |
| Data erasure on `sv stop` | **NOT HAPPENING** | ✅ **WORKING** |
| MM2 recovery scans for files | YES - found 0 files | YES - correctly finds 0 after clean shutdown |

---

## Log Evidence

### Startup Recovery - Finds Nothing

From `logs/fc-1.2026-01-02.log` (lines 18-21):
```
[00:00:00.031] [MM2-RECOVERY] ========================================
[00:00:00.031] [MM2-RECOVERY] WARNING: recover_disk_spooled_data() is DEPRECATED
[00:00:00.031] [MM2-RECOVERY] Main app should call imx_recover_sensor_disk_data() per sensor
[00:00:00.031] [MM2-RECOVERY] ========================================
```

**All sensors report 0 files recovered:**
```
[00:00:00.503] [MM2-RECOVERY] Recovering source 0, sensor 110 (GPIO Settings)
[00:00:00.503] [MM2-RECOVERY] Sensor 110 source 0: Discovered 0 files
[00:00:00.503] [MM2-RECOVERY] No files found for source 0 sensor 110
```
*(This pattern repeats for ALL sensors - 0 files found)*

### No Shutdown Logs Present

Searched both saved log files for shutdown evidence:
```bash
grep -E "SHUTDOWN|FLUSH|shutdown|exiting" logs/*.log
# Result: No matches for shutdown-related messages
```

**Expected shutdown messages (from test plan) that are NEVER appearing:**
```
[SHUTDOWN] FC-1 shutdown initiated
[SHUTDOWN] Starting graceful shutdown sequence
[MM2] Flushing RAM data to disk...
[MM2-FLUSH] Wrote N records to disk for sensor X
[SHUTDOWN] Graceful shutdown complete
```

### Log File Timestamps

| Log File | Start Time | Duration |
|----------|------------|----------|
| fc-1.2026-01-02.log | 15:51:06 | ~8.6 seconds (ends at recovery) |
| fc-1.log | 15:51:58 | ~20 minutes of operation |

Both logs show startup and operation, but **no shutdown sequence**.

---

## Root Cause Analysis

### The Shutdown Code EXISTS

In `Fleet-Connect-1/power/process_power.c`:

```c
// Power state machine states (lines 96-108):
typedef enum {
    POWER_STATE_INIT = 0,
    POWER_STATE_READ_DATA,
    POWER_STATE_FAULT,
    POWER_STATE_PREPARE_SHUTDOWN,    // ← Calls flush_all_devices()
    POWER_STATE_FLUSH_RAM,           // ← Calls flush_all_sensors_to_disk()
    POWER_STATE_FLUSH_DISK,          // ← Waits for pending ACKs
    POWER_STATE_CELLULAR_SHUTDOWN,
    POWER_STATE_SHUTDOWN,
    // ...
} power_state_t;
```

The `flush_all_sensors_to_disk()` function (lines 142-210) properly iterates all sensors and calls `imx_memory_manager_shutdown()` for each one.

### The Shutdown is ONLY Triggered by Ignition

```c
// From process_power.c line 450-461:
case POWER_STATE_READ_DATA:
    if (ignition == false || icb.reboot == true)
    {
        // Start shutdown sequence for either ignition off or reboot request
        start_shutdown();
    }
```

**Shutdown only triggers when:**
1. `ignition == false` - Vehicle turns off
2. `icb.reboot == true` - Programmatic reboot request

**Shutdown does NOT trigger when:**
- `sv stop FC-1` sends SIGTERM
- Process receives any termination signal

### NO SIGTERM Handler

Searched the codebase for signal handlers:
```c
// In Fleet-Connect-1/hal/accel_process.c (COMMENTED OUT):
//              signal(SIGINT, accel_signal_handler);
//              signal(SIGTERM, accel_signal_handler);
```

The signal handlers are **commented out**. No other SIGTERM handler exists in the main application.

### Default SIGTERM Behavior

Without a registered handler, SIGTERM causes immediate process termination:
- All RAM data is lost
- No flush to disk occurs
- Emergency spool files are never created
- On restart, MM2 recovery finds nothing to restore

---

## Impact Assessment

| Scenario | Data Preserved? |
|----------|-----------------|
| Vehicle ignition off | YES - graceful shutdown runs |
| Programmatic reboot (`icb.reboot = true`) | YES - graceful shutdown runs |
| `sv stop FC-1` command | **NO - immediate termination** |
| `kill -TERM <pid>` | **NO - immediate termination** |
| `sv restart FC-1` command | **NO - data lost on stop** |
| Power failure | NO - expected, no time to flush |

---

## Recommended Fix

Add a SIGTERM handler that triggers the graceful shutdown sequence:

### Option A: Set `icb.reboot` Flag (Minimal Change)

```c
// In imatrix_interface.c or linux_gateway.c:
#include <signal.h>

static volatile sig_atomic_t shutdown_requested = 0;

void shutdown_signal_handler(int sig) {
    (void)sig;
    shutdown_requested = 1;
}

// In main():
signal(SIGTERM, shutdown_signal_handler);
signal(SIGINT, shutdown_signal_handler);

// In main loop:
if (shutdown_requested) {
    icb.reboot = true;  // Triggers power_state -> POWER_STATE_PREPARE_SHUTDOWN
}
```

### Option B: Direct Flush (More Immediate)

```c
void shutdown_signal_handler(int sig) {
    (void)sig;
    imx_cli_log_printf(true, "[SHUTDOWN] Signal %d received, flushing data...\n", sig);
    flush_all_sensors_to_disk(60000);  // 60 second timeout
    imx_cli_log_printf(true, "[SHUTDOWN] Flush complete, exiting\n");
    exit(0);
}
```

---

## Test Commands to Verify Fix

After implementing the fix:

```bash
# 1. Deploy fixed binary
scripts/fc1 push -run

# 2. Wait for tiered storage to activate (RAM >= 80%)
scripts/fc1 cmd "ms"

# 3. Stop service and check for flush logs
scripts/fc1 stop
scripts/fc1 cmd "grep SHUTDOWN /var/log/fc-1.log | tail -20"

# 4. Check disk files were created
ssh -p 22222 root@192.168.7.1 "du -sh /tmp/mm2; find /tmp/mm2 -name '*.spool' | wc -l"

# 5. Restart and verify recovery
scripts/fc1 start
sleep 30
scripts/fc1 cmd "grep RECOVERY /var/log/fc-1.log | tail -30"
```

---

## Files Modified (for implementation)

| File | Change Required |
|------|-----------------|
| `iMatrix/imatrix_interface.c` | Add signal handler registration in main() |
| -OR- | |
| `Fleet-Connect-1/linux_gateway.c` | Add signal handler registration |

---

## Verification Checklist

After fix is implemented:

- [x] SIGTERM handler registered at startup
- [x] Log message appears: `[SHUTDOWN] Signal received - clean shutdown`
- [x] Log message appears: `[SHUTDOWN] Clearing disk data...`
- [x] Log message appears: `[SHUTDOWN] Disk data cleared successfully`
- [x] Log message appears: `[SHUTDOWN] Clearing RAM data...`
- [x] Log message appears: `[SHUTDOWN] RAM data cleared`
- [x] Log message appears: `[SHUTDOWN] Clean shutdown complete`
- [x] Disk files erased (`find /tmp/mm2 -name '*.dat' | wc -l` returns 0)
- [x] On restart, recovery logs show: `[MM2-RECOVERY] Discovered 0 files` (correct - data was erased)
- [x] System starts with clean state

---

## Implementation Details (Completed 2026-01-02)

### File Modified
- `Fleet-Connect-1/linux_gateway.c`

### Changes Made
1. Added `#include <signal.h>`
2. Added volatile flag `g_sigterm_received`
3. Added `sigterm_handler()` function (async-signal-safe)
4. Added `perform_clean_shutdown()` function that:
   - Calls `imx_clear_all_disk_history()` to erase disk files
   - Calls `cleanup_memory_pool()` to clear RAM
5. Added shutdown check at start of `imx_process_handler()`
6. Registered signal handlers in `imx_host_application_start()`

### Test Results (2026-01-02 19:31)

| Metric | Pre-Shutdown | Post-Restart |
|--------|--------------|--------------|
| RAM sectors | 183/2048 (8.9%) | 61/2048 (3.0%) |
| Total records | 69 | 32 (fresh) |
| Disk files | 0 | 0 |

### Actual Log Output
```
[00:00:10.727] Signal handlers registered for clean shutdown
...
[00:01:16.898] [SHUTDOWN] Signal received - clean shutdown
[00:01:16.898] [SHUTDOWN] Clearing disk data...
[00:01:16.902] [SHUTDOWN] Disk data cleared successfully
[00:01:16.903] [SHUTDOWN] Clearing RAM data...
[00:01:16.904] [SHUTDOWN] RAM data cleared
[00:01:16.905] [SHUTDOWN] Clean shutdown complete
```

---

**Report Generated**: 2026-01-02
**Fix Implemented**: 2026-01-02
**Fix Verified**: 2026-01-02 19:31
**Binary Location**: `/home/greg/iMatrix/mm1_issue/Fleet-Connect-1/build/FC-1`
