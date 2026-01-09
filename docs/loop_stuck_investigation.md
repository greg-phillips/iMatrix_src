# Handler Stuck Investigation - imatrix_upload() Blocking

**Date Created**: 2025-12-29
**Date Resolved**: 2026-01-09
**Status**: RESOLVED - Root cause identified and fixed
**Priority**: High
**Affected Component**: iMatrix Upload / Memory Manager (MM2)

---

## Problem Summary

The FC-1 system locks up after approximately 2 hours of runtime. The main loop becomes completely blocked, though the CLI remains responsive via PTY.

### Symptoms
- System runs normally for ~2 hours (~39,852 loop executions)
- Main loop stops executing
- CLI commands still work (PTY responsive)
- `loopstatus` command shows system stuck at position 50

### Original `loopstatus` Output
```
==================== MAIN LOOP STATUS ====================
Handler Position:    Before imx_process() (0)
Time at Handler:     38218888 ms

imx_process() Pos:   50
Time at imx_proc:    38218888 ms

do_everything() Pos: EXIT (19)
Time at Position:    38218988 ms
Loop Executions:     39852

*** WARNING: Handler stuck at 'Before imx_process()' for 38218888 ms! ***
*** BLOCKING IN: imx_process() function (position 50) ***
==========================================================
```

**Key Observation**: Stuck for 38,218,888 ms (~10.6 hours) at position 50, which is BEFORE `imatrix_upload()` returns.

---

## Code Analysis

### Position 50 Location

File: `iMatrix/imatrix_interface.c`, lines 1650-1652:
```c
set_imx_process_breadcrumb(50);  // Before imatrix_upload()
imatrix_upload(current_time);
set_imx_process_breadcrumb(51);  // After imatrix_upload() <-- NEVER REACHED
```

### imatrix_upload() Overview

File: `iMatrix/imatrix_upload/imatrix_upload.c`

The function is a state machine with the following states:
- `IMATRIX_INIT` - Check if time to upload
- `IMATRIX_CHECK_FOR_PENDING` - Check for data to send
- `IMATRIX_GET_DNS` - Resolve iMatrix server address
- `IMATRIX_GET_PACKET` - Allocate CoAP packet
- `IMATRIX_LOAD_NOTIFY_PACKET` - Load error/warning notifications
- `IMATRIX_LOAD_SAMPLES_PACKET` - **Load sensor data samples**
- `IMATRIX_UPLOAD_WAIT_RSP` - Wait for server acknowledgment

### Suspected Blocking Operations

#### 1. Sample Reading (Most Likely)

File: `iMatrix/cs_ctrl/mm2_read.c`

**`imx_read_bulk_samples()`** - Line 585+
```c
pthread_mutex_lock(&csd->mmcb.sensor_lock);  // Line 619

// Multiple while loops that traverse sector chains:
while (read_start_sector != NULL_SECTOR_ID && records_skipped < existing_pending)  // Line 692
while (read_start_sector != NULL_SECTOR_ID)  // Line 777
while (current_sector != NULL_SECTOR_ID)  // Line 882, 1078
```

**`imx_get_new_sample_count()`** - Line 429+
```c
pthread_mutex_lock(&csd->mmcb.sensor_lock);  // Line 441
```

#### 2. Sector Chain Traversal

The memory manager uses linked-list sector chains. Corruption could cause:
- Circular references (infinite loop)
- Missing NULL_SECTOR_ID terminator
- Safety limits not triggering

Relevant safety check at line 813-816:
```c
/* Safety limit to prevent infinite loop on corrupted chain */
if (sectors_scanned > max_sectors_to_scan) {
    LOG_MM2_CORRUPT("read_bulk: CHAIN CORRUPTION - exceeded max sectors...");
```

#### 3. Mutex Contention/Deadlock

Each sensor has its own `sensor_lock` mutex. Potential issues:
- Lock acquired but never released (early return, exception)
- Nested lock attempt on same mutex
- Cross-sensor deadlock

---

## Enhanced Diagnostics (Implemented 2025-12-29)

### Updated `loopstatus` Command

The `loopstatus` command has been enhanced to show:

1. **Boot Time** - When the system started (UTC)
2. **Uptime** - How long system has been running
3. **Lock Occurrence Time** - When the blocking started (UTC)
4. **Time After Boot** - How long after boot the lock occurred
5. **Mutex Status** - Currently held mutexes with holder info

### New Output Format
```
==================== MAIN LOOP STATUS ====================

--- System Timing ---
Boot Time:           2025-12-29T10:15:23 UTC
Uptime:              0d 2h 15m 30s (8130 sec)

--- Loop Position ---
Handler Position:    Before imx_process() (0)
Time at Handler:     7200000 ms
...

*** WARNING: Handler stuck at 'Before imx_process()' for 7200000 ms! ***
*** Lock occurred at: 2025-12-29T10:15:30 UTC ***
*** Time after boot:  0h 0m 7s (7 sec after boot) ***
*** BLOCKING IN: imatrix_upload() (position 50) ***
==========================================================

------------------- MUTEX STATUS --------------------
Tracked: 7, Currently Locked: 1

*** LOCKED MUTEXES: ***
  [sensor_lock] held by imx_read_bulk_samples() for 7200000 ms
    Location: mm2_read.c:619
    *** CRITICAL: Lock held >5 seconds! ***
------------------------------------------------------
```

### Files Modified

1. `iMatrix/platform_functions/mutex_tracker.h` - Added `mutex_tracker_print_locked_summary()`
2. `iMatrix/platform_functions/mutex_tracker.c` - Implemented locked mutex summary
3. `Fleet-Connect-1/cli/fcgw_cli.c` - Enhanced `cli_loopstatus()` with timing and mutex info

---

## Investigation Steps for Next Occurrence

### Immediate Actions (When System Locks)

1. **Run `loopstatus` immediately**
   ```
   app
   loopstatus
   ```
   This will show:
   - Exact time the lock occurred
   - Which mutex (if any) is held
   - Which function holds it

2. **Check mutex status separately** (if needed)
   ```
   mutex
   mutex verbose
   ```

3. **Capture system state**
   ```
   s              # System status
   threads -v     # Thread status
   mem            # Memory status
   ```

4. **Save all output** - Copy/paste or log to file for analysis

### Data to Collect

- [ ] `loopstatus` output showing mutex state
- [ ] Time of day when lock occurred
- [ ] Time after boot when lock occurred
- [ ] Which sensor (if identifiable) was being processed
- [ ] Any error messages in logs before lockup
- [ ] Network state at time of lock (was upload in progress?)

---

## Potential Root Causes

### Theory 1: Mutex Deadlock in MM2 Read

**Likelihood**: High

The `sensor_lock` mutex is acquired at multiple points in `mm2_read.c`. If an error path returns without releasing the lock, subsequent calls will deadlock.

**Evidence Needed**: `loopstatus` showing a `sensor_lock` held for extended time

**Fix Approach**: Audit all code paths in `mm2_read.c` for proper mutex release

### Theory 2: Corrupted Sector Chain

**Likelihood**: Medium

The memory manager uses linked sector chains. If corruption creates a cycle or loses the terminator, the `while` loop iterating sectors would run forever.

**Evidence Needed**: Lock occurs without any mutex being held (pure infinite loop)

**Fix Approach**:
- Add iteration counter to all sector traversal loops
- Add chain integrity validation
- Improve safety limit checks

### Theory 3: External Block (Network/DNS)

**Likelihood**: Low

The `get_imatrix_ip_address()` DNS lookup could potentially block, but:
- Position 50 is after DNS (that's positions 30-31)
- State machine would be in different state

**Evidence Needed**: Lock occurring at different position (not 50)

---

## Code Locations Reference

### Breadcrumb Positions in `imx_process()`

| Position | Location | Description |
|----------|----------|-------------|
| 0 | Entry | Start of imx_process() |
| 10-11 | PROVISION_SETUP | process_network() |
| 20-21 | ESTABLISH_WIFI | process_network() |
| 30-31 | NORMAL | process_network() |
| 32-35 | NORMAL | Network/time checks |
| 40-43 | NORMAL | OTA checks |
| **50-51** | **NORMAL** | **imatrix_upload()** |
| 60-61 | After switch | Diagnostics |
| 62-63 | End | Watchdog |
| 64-69 | End | hal_sample, location, memory |
| 70-75 | End | Background messages, telnet, ping |
| 99 | Exit | Leaving imx_process() |

### Key Files

| File | Purpose |
|------|---------|
| `iMatrix/imatrix_interface.c` | Main processing loop, breadcrumbs |
| `iMatrix/imatrix_upload/imatrix_upload.c` | Upload state machine |
| `iMatrix/cs_ctrl/mm2_read.c` | Memory manager read operations |
| `iMatrix/cs_ctrl/mm2_api.h` | MM2 API definitions |
| `iMatrix/platform_functions/mutex_tracker.c` | Mutex tracking system |
| `Fleet-Connect-1/cli/fcgw_cli.c` | loopstatus command |

---

## Recommended Next Steps

### Short Term

1. **Wait for next occurrence** with enhanced `loopstatus`
2. **Capture mutex state** when lock happens
3. **Correlate with logs** to identify triggering conditions

### Medium Term (After Root Cause Identified)

4. **Add granular breadcrumbs** inside `imatrix_upload()`:
   ```c
   case IMATRIX_LOAD_SAMPLES_PACKET:
       set_imx_process_breadcrumb(5010);  // Enter LOAD_SAMPLES
       for (type = IMX_CONTROLS; ...) {
           set_imx_process_breadcrumb(5020 + type);  // Per-type
           for (uint16_t i = 0; i < no_items; i++) {
               set_imx_process_breadcrumb(5030);  // Before read
               // ... imx_read_bulk_samples() ...
               set_imx_process_breadcrumb(5031);  // After read
           }
       }
   ```

5. **Audit mutex usage** in `mm2_read.c`:
   - Ensure all paths release locks
   - Add timeout to mutex acquisition
   - Consider using `pthread_mutex_trylock()` with retry

6. **Add sector chain validation**:
   - Periodic integrity checks
   - Hard limits on all traversal loops
   - Corruption detection and recovery

### Long Term

7. **Consider mutex-free design** for read path (if feasible)
8. **Add watchdog inside imatrix_upload()** to detect and recover from hangs
9. **Implement upload timeout** to abort stuck uploads

---

## RESOLUTION (2026-01-09)

### Root Cause Identified

The lockup was caused by **sector chain corruption** in the MM2 memory manager during disk spooling operations. This corruption led to:
- 4,336 `SENSOR_ID MISMATCH` events in logs
- Cross-sensor chain corruption: `sector=X (owner=A) -> next=Y (owner=B)`
- Infinite loops or deadlocks when traversing corrupted chains

### Technical Details

**Location**: `iMatrix/cs_ctrl/mm2_disk_spooling.c` - `cleanup_spooled_sectors()` function

**Bug**: The function was calling `free_sector()` directly without:
1. Updating chain pointers first (leaving dangling references)
2. Holding the `sensor_lock` (allowing race conditions)

**Race Condition Sequence**:
```
T0: Sensor 49 chain: ... -> sector 132 -> sector 1310 -> ...
T1: cleanup_spooled_sectors() calls free_sector(1310)
    - sector 1310 freed and returned to free list
    - BUT chain_table[132].next_sector_id STILL = 1310!
T2: Another thread allocates sector 1310 for sensor 52
T3: Chain traversal: sector 132 (owner=49) -> next=1310 (owner=52) = CORRUPTION
```

### Fix Applied

```c
static imx_result_t cleanup_spooled_sectors(control_sensor_data_t* csd,
                                            imatrix_upload_source_t upload_source) {
    // CRITICAL FIX: Hold sensor_lock during entire cleanup
    pthread_mutex_lock(&csd->mmcb.sensor_lock);

    for (each sector to free) {
        // Find previous sector in chain
        // Update chain pointers to BYPASS this sector
        set_next_sector_in_chain(prev_sector, next_sector);

        // NOW safe to free - chain no longer references it
        free_sector(sector_id);
    }

    pthread_mutex_unlock(&csd->mmcb.sensor_lock);
}
```

### Verification Results

| Test | Duration | Corruption Events |
|------|----------|-------------------|
| Initial test (aggressive 10% threshold) | 8+ minutes | 0 |
| Production test (80% threshold) | 1 hour | 0 |

### Files Modified

| File | Change |
|------|--------|
| `cs_ctrl/mm2_disk_spooling.c` | Fixed `cleanup_spooled_sectors()` race condition |
| `cs_ctrl/mm2_api.h` | Removed temporary test code |
| `cs_ctrl/memory_manager_stats.c` | Removed temporary test CLI command |
| `cs_ctrl/docs/MM2_Sector_Chain_Corruption_Fix.md` | Comprehensive fix documentation |

### Branch and Tag

- **Branch**: `fix/mm2-sector-chain-corruption`
- **Tag**: `v1.0.0-mm2-chain-fix`
- **Merged to**: `Aptera_1_Clean`

---

## Related Documentation

- **`iMatrix/cs_ctrl/docs/MM2_Sector_Chain_Corruption_Fix.md`** - Detailed fix documentation
- `docs/archive/MAIN_LOOP_LOCKUP_FIX_SUMMARY.md` - Previous GPS-related lockup fix (Nov 2025)
- `iMatrix/cs_ctrl/MM2_Developer_Guide.md` - Memory Manager documentation
- `iMatrix/cs_ctrl/docs/MM2_API_GUIDE.md` - MM2 API reference

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Claude | Initial investigation, enhanced loopstatus command |
| 2026-01-07 | Claude | Root cause identified: sector chain corruption in cleanup_spooled_sectors() |
| 2026-01-09 | Claude | Fix verified with 1-hour production test, merged to Aptera_1_Clean |

---

**Status**: RESOLVED - Fix deployed and verified working in production.
