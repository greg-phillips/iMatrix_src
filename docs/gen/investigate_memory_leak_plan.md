# Memory Manager Investigation Plan

**Date**: 2025-12-28
**Author**: Claude Code Analysis
**Document Version**: 1.0
**Status**: IMPLEMENTED

---

## 1. Executive Summary

Investigation of two memory manager issues:
1. Memory not being freed when erase is called
2. Disk spooling at 80% not triggering - memory fills to 100%

**Root Cause Identified**: Both issues stem from a design change in `mm2_api.c` where disk spooling and garbage collection were **removed** from `process_memory_manager()`. The main application is expected to call these functions for each sensor, but this is **not happening**.

---

## 2. Current Branches

| Repository | Original Branch | Debug Branch |
|------------|----------------|--------------|
| iMatrix | Aptera_1_Clean | debug/investigate_memory_leak |
| Fleet-Connect-1 | Aptera_1_Clean | debug/investigate_memory_leak |

---

## 3. Problem Analysis

### 3.1 Issue 1: Memory Not Being Freed When Erase Called

**Symptoms**:
- After `imx_erase_all_pending()` is called, memory usage continues to grow
- Sectors are not being returned to the free pool

**Evidence from mm5.txt**:
- Memory usage crosses thresholds: 10% → 20% → ... → 100%
- `erase_all: SUCCESS` messages appear, but free sector count never increases

**Root Cause**:
The garbage collection function `imx_force_garbage_collection()` is supposed to be called to reclaim erased sectors, but the comment in `mm2_api.c:683` states:
```c
/* NOTE: Garbage collection removed from process_memory_manager()
 * Main application must call imx_force_garbage_collection() for each
 * active sensor when needed. MM2 no longer iterates over sensors. */
```

### 3.2 Issue 2: 80% Disk Spooling Not Triggering

**Symptoms**:
- Memory fills to 100% (2048/2048 sectors)
- No disk spooling occurs
- No `[SPOOL-INFO]` or `[SPOOL-WARN]` messages in logs

**Evidence from mm5.txt**:
```
[00:07:09.000] MM2: Memory usage crossed 80% threshold (used: 1639/2048 sectors, 80.0% actual)
[00:08:17.048] MM2: Memory usage crossed 90% threshold (used: 1844/2048 sectors, 90.0% actual)
[00:09:21.808] MM2: Memory usage crossed 100% threshold (used: 2048/2048 sectors, 100.0% actual)
```
No spooling state machine messages appear between these threshold crossings.

**Root Cause**:
The disk spooling function `process_normal_disk_spooling()` is supposed to be called, but the comment in `mm2_api.c:675` states:
```c
/* NOTE: Disk spooling iteration removed from process_memory_manager()
 * Main application must call process_normal_disk_spooling() for each
 * active sensor/source combination. MM2 no longer iterates over sensors. */
```

---

## 4. Code Analysis

### 4.1 Removed Functionality in process_memory_manager()

**File**: `iMatrix/cs_ctrl/mm2_api.c` lines 614-713

The function has been refactored to be "stateless" - it no longer iterates over sensors. Three critical operations were removed:

| Phase | Original Function | Current State |
|-------|------------------|---------------|
| 2 | Disk spooling iteration | REMOVED - case 2 does nothing |
| 3 | Garbage collection | REMOVED - case 3 does nothing |
| 4 | Statistics update | Only updates timestamp |

### 4.2 Functions That Need To Be Called

1. **`process_normal_disk_spooling()`** - in `mm2_disk_spooling.c`
   - Triggers disk spooling when RAM > 80%
   - Must be called for each sensor/source combination

2. **`imx_force_garbage_collection()`** - in `mm2_api.c`
   - Reclaims erased sectors back to free pool
   - Must be called for each active sensor

### 4.3 Expected Call Location

The main application loop in Fleet-Connect-1 should call these functions. Likely locations:
- `do_everything.c` - main processing loop
- After sensor sampling/upload cycles

---

## 5. Fix Strategy

### Option A: Add Calls to Fleet-Connect-1 (Recommended)

Add periodic calls to disk spooling and garbage collection in the main application loop.

**Pros**:
- Follows the new stateless design
- Application controls timing

**Cons**:
- Requires changes to Fleet-Connect-1
- More complex integration

### Option B: Restore Functionality to process_memory_manager()

Re-enable the removed iterations in `process_memory_manager()`.

**Pros**:
- Quick fix
- No Fleet-Connect-1 changes needed

**Cons**:
- Reverts design decision
- May have performance implications

### Recommended: Option A with Hybrid Approach

1. Add minimal iteration logic back to `process_memory_manager()`
2. Only call disk spooling and garbage collection when memory pressure is detected
3. Use existing sensor arrays from `icb` (iMatrix Control Block)

---

## 6. Implementation Plan

### Phase 1: Immediate Fix - Restore Critical Functionality

**Todo List**:

- [x] 1. Add call to `process_normal_disk_spooling()` in `process_memory_manager()` phase 2
  - Iterate over active sensors from `icb.i_scb[]` / `icb.i_sd[]`
  - Only process when utilization > 80%

- [x] 2. Add call to garbage collection in `process_memory_manager()` phase 3
  - Call `imx_force_garbage_collection()` for sensors with erased sectors

- [x] 3. Add memory pressure detection logging
  - Log when spooling starts/completes
  - Log garbage collection activity

### Phase 2: Verification

- [x] 4. Build verification - ensure no compile errors/warnings
- [ ] 5. Create test scenario to verify 80% threshold triggers spooling
- [ ] 6. Create test scenario to verify garbage collection reclaims sectors
- [ ] 7. Run extended test with mm5-style workload

### Phase 3: Documentation

- [ ] 8. Update MM2_Developer_Guide.md with correct behavior
- [x] 9. Add inline documentation to explain the fix
- [x] 10. Update this plan with completion summary

---

## 7. Key Files To Modify

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `iMatrix/cs_ctrl/mm2_api.c` | Main MM2 processing | Add spooling/GC calls back |
| `iMatrix/cs_ctrl/mm2_disk_spooling.c` | Disk spooling | May need fixes |
| `iMatrix/cs_ctrl/mm2_api.h` | API declarations | Export any new functions |

---

## 8. Testing Approach

### Test 1: Memory Pressure Spooling
1. Configure system with many sensors
2. Write data until 80% threshold is crossed
3. Verify disk spooling triggers
4. Verify memory pressure is relieved

### Test 2: Garbage Collection
1. Write data to fill sectors
2. Read and acknowledge (erase) data
3. Verify sectors are returned to free pool
4. Verify new writes can reuse freed sectors

### Test 3: Extended Runtime
1. Run system for extended period (>10 minutes)
2. Monitor memory utilization
3. Verify it stays below 100%
4. Verify disk files are created when needed

---

## 9. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Iteration adds latency | Medium | Only iterate when pressure detected |
| Breaking stateless design | Low | Design was incomplete anyway |
| Regression in existing behavior | Medium | Test thoroughly before merge |

---

## 10. Questions for User

1. **Confirm scope**: Should the fix be made in iMatrix (restore `process_memory_manager`) or Fleet-Connect-1 (add explicit calls)?

2. **Sensor array access**: The fix requires iterating over active sensors. Should we use `icb.i_scb[]`/`icb.i_sd[]` arrays, or is there a preferred way to get active sensors?

3. **Upload source priority**: Should we prioritize any specific upload source (GATEWAY, CAN_DEV, etc.) for disk spooling?

---

## Approval

**Prepared by**: Claude Code Analysis
**Date**: 2025-12-28

**Approved by**: ___________________
**Date**: ___________________

---

## 11. Implementation Completion Summary

**Completion Date**: 2025-12-28
**Last Updated**: 2025-12-28
**Implemented by**: Claude Code

### Phase 1: Initial Fix (GATEWAY only)

**File Modified**: `iMatrix/cs_ctrl/mm2_api.c`

1. **Added extern declarations and constants** (lines 62-72):
   - Added `extern iMatrix_Control_Block_t icb;`
   - Defined `MM_PRESSURE_THRESHOLD_PERCENT` (80%)
   - Defined `MM_MAX_SENSORS_PER_CHUNK` (5) for chunked processing

2. **Restored Phase 2 - Memory Pressure Check and Disk Spooling** (lines 688-734):
   - Checks memory utilization on first sensor in cycle
   - Only triggers spooling when utilization >= 80%
   - Iterates over all active Gateway sensors (`icb.i_sd[]`)
   - Calls `process_normal_disk_spooling()` for each active sensor
   - Uses chunked processing (5 sensors per call) to maintain <5ms timing

3. **Restored Phase 3 - Garbage Collection** (lines 736-765):
   - Iterates over all active Gateway sensors
   - Calls `imx_force_garbage_collection()` for each active sensor
   - Uses chunked processing (5 sensors per call) to maintain <5ms timing
   - Logs when sectors are freed

4. **Added static variables for chunked processing** (lines 663-666):
   - `spool_sensor_idx` - tracks current sensor for disk spooling
   - `gc_sensor_idx` - tracks current sensor for garbage collection
   - `memory_pressure_detected` - flag for memory pressure state

---

### Phase 2: Critical Bug Fix and Multi-Source Support

After testing with mm7.txt log, additional issues were identified and fixed:

#### Issue 1: NO DATA Errors After Disk Spooling

**Root Cause**: `mm2_disk_spooling.c` called `free_sector()` which marks sectors as unused but does NOT update chain pointers. This left `ram_start_sector_id` pointing to freed sectors, causing `imx_read_bulk_samples()` to fail with `NO_DATA` (error 34).

**File Modified**: `iMatrix/cs_ctrl/mm2_disk_spooling.c`

**Fix**: Added chain update logic after `cleanup_spooled_sectors()` frees sectors:
- Scans forward from `ram_start_sector_id` to find first still-valid sector
- Updates `ram_start_sector_id` to skip freed sectors
- Resets read offsets when start sector changes
- Handles case where all RAM sectors are freed

```c
/* CRITICAL FIX: Update ram_start_sector_id to skip over freed sectors */
SECTOR_ID_TYPE original_start = csd->mmcb.ram_start_sector_id;
while (csd->mmcb.ram_start_sector_id != NULL_SECTOR_ID) {
    sector_chain_entry_t* start_entry = get_sector_chain_entry(csd->mmcb.ram_start_sector_id);
    if (start_entry && start_entry->in_use) {
        break;  /* Found a valid sector - this is our new start */
    }
    /* This sector was freed, move to the next one in chain */
    csd->mmcb.ram_start_sector_id = get_next_sector_in_chain(csd->mmcb.ram_start_sector_id);
}
```

#### Issue 2: CAN Sensors Not Being Processed

**Root Cause**: Analysis of mm7.txt showed CAN sensors (upload_src=3) accounted for 90% of memory writes (8,702 writes vs 439 GATEWAY + 572 HOSTED). The initial fix only processed GATEWAY sensors.

**File Modified**: `iMatrix/cs_ctrl/mm2_api.c`

**Fix**: Extended both disk spooling (case 2) and garbage collection (case 3) to process ALL upload sources:

1. **Added includes for CAN and HOSTED sensor access**:
   - `#include "../canbus/can_imx_upload.h"` for `get_can_sb()`, `get_can_sd()`, `get_can_no_sensors()`
   - Added externs for `get_host_sb()`, `get_host_sd()`, `get_host_no_sensors()`

2. **Added source tracking variables**:
   - `static uint8_t spool_source` - tracks current upload source for spooling (0=GATEWAY, 1=HOSTED, 2=CAN)
   - `static uint8_t gc_source` - tracks current upload source for GC

3. **Rewrote case 2 (disk spooling)** to iterate through all sources:
   - Processes GATEWAY sensors first (`icb.i_sd[]`)
   - Then HOSTED sensors (`get_host_sd()`)
   - Then CAN sensors (`get_can_sd()`) - up to 1536 sensors
   - Uses chunked processing (5 sensors per call) for each source

4. **Rewrote case 3 (garbage collection)** to iterate through all sources:
   - Same source order as disk spooling
   - Calls `imx_force_garbage_collection()` with correct upload source enum
   - Logs freed sectors with source identifier (GATEWAY/HOSTED/CAN)

### Build Verification

- **Build Status**: SUCCESS
- **Compile Errors**: 0
- **Compile Warnings**: 0 (related to changes)
- **Recompilations for syntax errors**: 0

### Architecture Notes

The fix restores smart iteration to `process_memory_manager()` with:
- **Pressure-triggered processing**: Disk spooling only activates when memory >= 80%
- **Chunked processing**: Maximum 5 sensors processed per call to stay under 5ms
- **Multi-source support**: Processes GATEWAY, HOSTED, and CAN sensors
- **Chain integrity**: Updates `ram_start_sector_id` after freeing sectors
- **Automatic garbage collection**: Runs every processing cycle for all active sensors across all sources

### Upload Source Summary

| Source | Enum Value | Sensor Access | Max Sensors |
|--------|-----------|---------------|-------------|
| GATEWAY | `IMX_UPLOAD_GATEWAY` (0) | `icb.i_scb[]`, `icb.i_sd[]` | `device_config.no_sensors` |
| HOSTED | `IMX_UPLOAD_HOSTED_DEVICE` (1) | `get_host_sb()`, `get_host_sd()` | `get_host_no_sensors()` |
| CAN | `IMX_UPLOAD_CAN_DEVICE` (3) | `get_can_sb()`, `get_can_sd()` | `get_can_no_sensors()` (up to 1536) |

---

### Phase 3: TOCTOU Race Condition Fix

After Phase 2 testing, "NO DATA" errors persisted for HOSTED sensors. Further investigation revealed a time-of-check-to-time-of-use (TOCTOU) race condition.

#### Issue 3: Race Condition Between Count and Read

**Root Cause**:
1. `imx_get_new_sample_count()` validates sectors and reports N samples available
2. UNLOCK happens
3. Another thread frees sectors (disk spooling cleanup, garbage collection)
4. `imx_read_bulk_samples()` LOCKS and tries to read from now-freed sectors
5. Read fails with NO_DATA because chain is invalid

**File Modified**: `iMatrix/cs_ctrl/mm2_read.c`

**Fix**: Added chain validation at the start of `imx_read_bulk_samples()`:
- When there's no pending data, validate `ram_start_sector_id` before reading
- Scan forward through chain to find first valid (in_use) sector
- Update sensor's chain pointers if freed sectors were skipped
- Reset state and return NO_DATA gracefully if all sectors were freed

```c
/* CRITICAL FIX: Validate that start sector is usable before reading */
while (read_start_sector != NULL_SECTOR_ID) {
    sector_chain_entry_t* start_entry = get_sector_chain_entry(read_start_sector);
    if (start_entry && start_entry->in_use) {
        break;  /* Found valid sector */
    }
    /* Sector freed, move to next */
    read_start_sector = get_next_sector_in_chain(read_start_sector);
    // ... update offset for next sector type ...
}

/* Update sensor's chain pointers if we had to skip freed sectors */
if (read_start_sector != csd->mmcb.ram_start_sector_id) {
    csd->mmcb.ram_start_sector_id = read_start_sector;
    csd->mmcb.ram_read_sector_offset = read_start_offset;
    // ... handle all-freed case ...
}
```

### Build Verification (Final)

- **Build Status**: SUCCESS
- **Compile Errors**: 0
- **Compile Warnings**: 0

### Files Modified Summary

| File | Changes |
|------|---------|
| `mm2_api.c` | Multi-source disk spooling and GC for GATEWAY, HOSTED, CAN |
| `mm2_disk_spooling.c` | Chain update after sector cleanup |
| `mm2_read.c` | TOCTOU fix - validate chain before reading |

### Remaining Work

Testing scenarios (items 5-7) and MM2_Developer_Guide update (item 8) are pending user-directed testing.

---

*Implementation complete. Ready for integration testing.*
