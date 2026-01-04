# Memory Manager Issue 1 - Disk Spooling Fix Plan

**Date**: 2026-01-01
**Author**: Claude Code Analysis
**Status**: In Progress
**Build Branch**: feature/mm1-disk-spooling-fix

## Problem Summary

Memory manager disk spooling is not effectively reducing memory pressure despite being triggered at 80% utilization. Log analysis shows:

1. Memory pressure detected at 90%+ utilization
2. Spooling triggers but only processes 7-14 sectors before cycling rapidly
3. Sensor ID reported as `4294967295` (0xFFFFFFFF = NULL_SECTOR_ID)
4. Most spooling attempts show "Selected 0 sectors for spooling"
5. Memory stays at 89-95% despite spooling being active

## Root Cause Analysis

### Issue 1: Architectural Bug - Shared State Machine

The spool state machine is **per-upload-source** (`icb.per_source_disk[upload_source].spool_state`), but `process_memory_manager()` iterates through individual sensors and calls `process_normal_disk_spooling()` for each.

**Current Flow (Broken):**
```
process_memory_manager() phase 2:
  for each sensor in source:
    process_normal_disk_spooling(sensor, source)  // Uses shared state!

Result:
- Sensor 0: IDLE → SELECTING → finds 7 sectors → WRITING → VERIFYING → CLEANUP
- Sensor 1: Now in IDLE (after cleanup), detects pressure → SELECTING → 0 sectors → IDLE
- Sensor 2: IDLE → pressure → SELECTING → 0 sectors → IDLE
- ... rapid cycling continues
```

**Location**: `mm2_api.c:754-762` and `mm2_disk_spooling.c:282-314`

### Issue 2: Sector Selection Only Checks Current Sensor's Chain

`select_sectors_for_spooling()` only walks the chain for the single sensor passed to it:

```c
SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;  // Only THIS sensor's chain
```

Most sensors have 0-1 sectors in their chain, so "Selected 0 sectors" is common.

**Location**: `mm2_disk_spooling.c:289`

### Issue 3: Sensor ID Lookup Returns Invalid Value

`get_sensor_id_from_csd()` returns `0xFFFFFFFF`, indicating the lookup is failing.

**Location**: Need to investigate `mm2_internal.h` or implementation file

## Solution Design

### Fix 1: Change to Cross-Sensor Selection (Preferred)

Instead of selecting sectors from one sensor at a time, scan ALL sensors for eligible sectors when memory pressure is detected.

**New Flow:**
```
process_memory_manager() phase 2:
  if memory_pressure_detected:
    select_sectors_across_all_sensors(upload_source)  // NEW: Scans all sensors
    process_spooling_state_machine(upload_source)      // Process shared state
```

**Changes Required:**

1. **New function**: `select_sectors_across_all_sensors()` in `mm2_disk_spooling.c`
   - Iterate through all active sensors for the upload source
   - Collect eligible sectors from each sensor's chain
   - Store sector-to-sensor mapping for cleanup phase

2. **Modify**: `process_memory_manager()` in `mm2_api.c`
   - Call spooling once per source (not once per sensor)
   - Process state machine only when there are sectors to spool

3. **Add**: Sector-to-sensor mapping in spool state
   - Need to track which sensor owns each spooled sector for cleanup

### Fix 2: Track Sensor ID in Sector Chain Entry

The `sector_chain_entry_t` already has `sensor_id` field. Verify it's being set correctly during allocation.

**Check**: `allocate_sector()` in `mm2_pool.c`

### Fix 3: Fix get_sensor_id_from_csd()

Implement proper sensor ID lookup:
- Check if CSD has a back-pointer to CSB
- Or pass CSB along with CSD to spooling functions

## Implementation Steps

1. **Create feature branches** in iMatrix and Fleet-Connect-1
2. **Add cross-sensor selection function** (`select_sectors_across_all_sensors`)
3. **Modify process_memory_manager** to call spooling once per source
4. **Update cleanup_spooled_sectors** to handle multi-sensor sectors
5. **Fix sensor ID lookup** (pass sensor_id explicitly or fix lookup)
6. **Build and test**

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/cs_ctrl/mm2_disk_spooling.c` | Add cross-sensor selection, fix state machine |
| `iMatrix/cs_ctrl/mm2_api.c` | Change phase 2 to call spooling once per source |
| `iMatrix/cs_ctrl/mm2_disk.h` | Add new function declarations, sensor mapping struct |
| `iMatrix/cs_ctrl/mm2_internal.h` | Add sensor ID helper if needed |

## Testing

1. Build with no warnings/errors
2. Run memory manager test suite
3. Verify disk spooling reduces memory pressure below 80%
4. Verify spool files are created correctly with valid sensor IDs
5. Verify cleanup properly frees sectors and updates sensor chains

## Questions for User (Before Implementation)

1. Should pending sectors (`pending_ack == 1`) ever be spooled to disk?
   - Currently they're excluded, which may prevent spooling when uploads are backed up

2. Is there a maximum number of sectors to spool per cycle?
   - Current limit is 10 selected, 5 written per cycle

3. Should spooling be disabled when uploads are failing?
   - To prevent filling disk with data that will never upload

---

*Plan created by Claude Code - ready for implementation after review*
