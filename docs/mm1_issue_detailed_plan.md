# Memory Manager Issue 1 - Detailed Analysis and Implementation Plan

**Date**: 2026-01-02
**Author**: Claude Code Analysis
**Status**: Ready for Implementation
**Document Version**: 1.0
**Branches**: feature/mm1-tiered-storage-fix (iMatrix and Fleet-Connect-1)

---

## Executive Summary

The memory manager disk spooling is not reducing memory pressure because **the current implementation contradicts the functional requirement**.

**Functional Requirement**: At 80%+ RAM utilization, allocate NEW sectors from disk directly.

**Current Implementation**: At 80%+ RAM utilization, attempt to migrate existing RAM data to disk.

This document provides complete analysis and implementation plan to fix this architectural mismatch.

---

## Part 1: Problem Analysis

### 1.1 Observed Behavior (from logs/mm1.log)

```
[00:07:08.459] MM2: Memory pressure 90% >= 80%, triggering disk spooling for ALL sources
[00:07:08.460] [SPOOL-INFO] Sensor 4294967295: Memory pressure detected (90%), starting spooling
[00:07:08.460] [SPOOL-INFO] Sensor 4294967295: Selected 7 sectors for spooling (checked 8)
...
[00:07:08.563] [SPOOL-INFO] Sensor 4294967295: Freed 7 RAM sectors (13 records moved to disk)
[00:07:08.563] [SPOOL-INFO] Sensor 4294967295: Still 90% utilized, continuing spooling
[00:07:08.563] [SPOOL-INFO] Sensor 4294967295: Selected 0 sectors for spooling (checked 0)
... repeats endlessly ...
```

**Key Observations**:
1. Memory pressure at 90% correctly detected
2. Initial spooling of 7 sectors succeeds
3. Memory stays at 90% despite freeing sectors
4. Subsequent spooling attempts find 0 eligible sectors
5. Sensor ID `4294967295` = `0xFFFFFFFF` = `NULL_SECTOR_ID` (bug in `get_sensor_id_from_csd()`)
6. Rapid state machine cycling (pressure detected → 0 sectors selected → repeat)

### 1.2 Root Cause Analysis

#### Issue 1: Fundamental Architecture Mismatch

**MM2_Functional_Clarification.md states** (emphasis mine):
> "The Memory Manager must operate using RAM based sectors for storage of control/sensor data until the RAM use reaches 80%. **At that point all new sectors are allocated from disk.**"
>
> "**Only spool RAM based sectors to disk when in shutdown mode.**"

**Current code does the OPPOSITE**:
- When RAM reaches 80%, it tries to MOVE existing RAM data to disk
- This is "spooling" during normal operation, which the spec explicitly forbids

#### Issue 2: Spooling State Machine per-Source, Not per-Sensor

The spool state machine is stored at `icb.per_source_disk[upload_source].spool_state`, which is **shared across all sensors** in that upload source. This causes:

1. Sensor A processes, transitions to SELECTING, finds sectors
2. Sensor A completes cycle, state returns to IDLE
3. Sensor B processes, state is IDLE, triggers SELECTING again
4. Sensor B has 0 eligible sectors, returns to IDLE
5. Rapid cycling through all sensors

**Location**: `mm2_api.c:754-762` and `mm2_disk_spooling.c`

#### Issue 3: Eligibility Check Too Restrictive

`is_sector_eligible_for_spooling()` excludes:
- `pending_ack` sectors (waiting for upload acknowledgment)
- Current write sector (`ram_end_sector_id`)

When uploads are backed up, most sectors are `pending_ack`, leaving nothing to spool.

**Location**: `mm2_disk_spooling.c:194-226`

#### Issue 4: Sensor ID Lookup Deprecated

`get_sensor_id_from_csd()` returns `UINT32_MAX` with comment:
```c
uint32_t get_sensor_id_from_csd(const control_sensor_data_t* csd) {
    (void)csd;
    return UINT32_MAX;  /* Always returns invalid - function deprecated */
}
```

**Location**: `mm2_pool.c:651-654`

### 1.3 Data Flow Analysis

**Current Write Path** (`imx_write_tsd()` / `imx_write_evt()`):
```
1. Check if sector needed
2. Call allocate_sector_for_sensor(sensor_id, type)
   - If RAM available: allocate from free list
   - If RAM full: return NULL_SECTOR_ID → IMX_OUT_OF_MEMORY
3. Write data to RAM sector
```

**Current Spooling Path** (`process_memory_manager()` phase 2):
```
1. Check if memory >= 80%
2. For each sensor: call process_normal_disk_spooling()
   a. IDLE: detect pressure → SELECTING
   b. SELECTING: walk THIS sensor's chain → WRITING
   c. WRITING: write to disk file → VERIFYING
   d. CLEANUP: free RAM sectors → check pressure → IDLE or SELECTING
```

**Required Write Path**:
```
1. Check if sector needed
2. Check RAM utilization
   - If < 80%: allocate from RAM (current behavior)
   - If >= 80%: write directly to disk file (NEW)
3. Track disk data location for upload
```

---

## Part 2: Solution Design

### 2.1 Architecture Decision

**Approach**: Tiered storage with automatic disk allocation at 80% threshold

**Key Principle**: NEW data goes to disk when RAM is full; existing RAM data stays in RAM until uploaded (or shutdown).

### 2.2 Component Changes

#### 2.2.1 Modify `allocate_sector_for_sensor()` (mm2_pool.c)

Add RAM utilization check before allocation:

```c
SECTOR_ID_TYPE allocate_sector_for_sensor(uint32_t sensor_id, uint8_t sector_type) {
    /* Check RAM utilization first */
    uint32_t utilization_percent =
        ((g_memory_pool.total_sectors - g_memory_pool.free_sectors) * 100) /
        g_memory_pool.total_sectors;

    if (utilization_percent >= TIERED_STORAGE_THRESHOLD_PERCENT) {
        /* Return special marker indicating disk allocation needed */
        return DISK_SECTOR_MARKER;  /* 0xFFFFFFFE */
    }

    /* Existing RAM allocation logic... */
}
```

Alternatively, return `NULL_SECTOR_ID` and let caller handle disk allocation (cleaner separation).

#### 2.2.2 Modify Write Functions (mm2_write.c)

Update `imx_write_tsd()` and `imx_write_evt()` to handle disk writes:

```c
imx_result_t imx_write_tsd(...) {
    /* ... existing validation ... */

    if (need_new_sector) {
        SECTOR_ID_TYPE new_sector = allocate_sector_for_sensor(sensor_id, SECTOR_TYPE_TSD);

        if (new_sector == NULL_SECTOR_ID) {
            #ifdef LINUX_PLATFORM
            /* RAM full - write directly to disk */
            return write_tsd_value_to_disk(upload_source, csb, csd, value);
            #else
            return IMX_OUT_OF_MEMORY;
            #endif
        }

        /* ... existing RAM write logic ... */
    }
}
```

#### 2.2.3 New Function: `write_tsd_value_to_disk()` (mm2_disk_spooling.c)

Create function to write individual TSD values to disk when RAM is full:

```c
imx_result_t write_tsd_value_to_disk(imatrix_upload_source_t upload_source,
                                     imx_control_sensor_block_t* csb,
                                     control_sensor_data_t* csd,
                                     imx_data_32_t value) {
    /*
     * Write directly to disk file in tiered storage format
     * Track in csd->mmcb for upload coordination
     */

    /* Open/create disk file if needed */
    /* Buffer values until sector full (6 values for TSD) */
    /* Write sector when full */
    /* Update total_disk_records */

    return IMX_SUCCESS;
}
```

#### 2.2.4 New Function: `write_evt_value_to_disk()` (mm2_disk_spooling.c)

Create parallel function for EVT data:

```c
imx_result_t write_evt_value_to_disk(imatrix_upload_source_t upload_source,
                                     imx_control_sensor_block_t* csb,
                                     control_sensor_data_t* csd,
                                     imx_data_32_t value,
                                     imx_utc_time_ms_t utc_time_ms);
```

#### 2.2.5 Disable Normal Spooling (mm2_api.c)

Comment out/remove the normal spooling in `process_memory_manager()` phase 2:

```c
case 2: /* Memory pressure check and disk spooling */
    #ifdef LINUX_PLATFORM
    {
        /*
         * DISABLED: Normal spooling removed per MM2_Functional_Clarification.md
         * "Only spool RAM based sectors to disk when in shutdown mode"
         *
         * New behavior: At 80%+ RAM, new writes go directly to disk.
         * RAM data stays in RAM until uploaded.
         */
        #if 0  /* DISABLED - was: normal disk spooling */
        if (memory_pressure_detected) {
            // ... old spooling code ...
        }
        #endif

        /* Move directly to phase 3 (GC) */
        spool_sensor_idx = 0;
        spool_source = 0;
        process_phase = 3;
    }
    #else
    process_phase = 3;
    #endif
    break;
```

#### 2.2.6 Track Disk State in MMCB (mm2_core.h)

Add fields to track disk-allocated data:

```c
typedef struct imx_mmcb_s {
    /* ... existing fields ... */

    #ifdef LINUX_PLATFORM
    /* Tiered storage: disk allocation tracking */
    uint8_t disk_write_active;           /* Currently writing to disk */
    uint8_t disk_sector_values_count;    /* Values buffered for current disk sector */
    uint64_t disk_sector_first_utc;      /* First UTC for current disk sector */
    uint32_t disk_sector_values[MAX_TSD_VALUES_PER_SECTOR];  /* Buffered values */
    #endif
} imx_mmcb_t;
```

#### 2.2.7 Fix Sensor ID Lookup (mm2_pool.c)

The function is deprecated because MM2 is stateless. Sensor ID should come from CSB:

```c
/* In spooling functions that need sensor_id, pass it explicitly from CSB */
/* Remove calls to get_sensor_id_from_csd() and use csb->id instead */
```

### 2.3 Upload Path Coordination

The existing `imx_read_bulk_samples()` already handles multi-source reading. After RAM data is exhausted, it should read from disk:

```c
/* In mm2_read.c - existing function */
imx_result_t imx_read_bulk_samples(...) {
    /* 1. Read from RAM sectors first */
    /* 2. When RAM exhausted, read from disk files */
    /* 3. Upload source handles coordination */
}
```

The existing `read_record_from_disk()` function can be used for disk reading.

### 2.4 State Transition Summary

**Before Fix**:
```
RAM < 80%: Write to RAM
RAM >= 80%: Try to spool RAM→disk (fails) → IMX_OUT_OF_MEMORY
```

**After Fix**:
```
RAM < 80%: Write to RAM
RAM >= 80%: Write to disk directly
Shutdown: Spool remaining RAM→disk (emergency path unchanged)
Upload: RAM first, then disk
```

---

## Part 3: Implementation Steps

### Step 1: Create Feature Branches
```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix
git checkout -b feature/mm1-tiered-storage-fix

cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
git checkout -b feature/mm1-tiered-storage-fix
```

### Step 2: Add Disk Write Functions (mm2_disk_spooling.c)
- Implement `write_tsd_value_to_disk()`
- Implement `write_evt_value_to_disk()`
- Add disk sector buffering logic
- Add file management (open, rotate, close)

### Step 3: Modify Write Functions (mm2_write.c)
- Update `imx_write_tsd()` to call disk write when RAM full
- Update `imx_write_evt()` to call disk write when RAM full
- Update `imx_write_gps_location()` (uses imx_write_evt internally - no change needed)

### Step 4: Disable Normal Spooling (mm2_api.c)
- Comment out `process_normal_disk_spooling()` calls in phase 2
- Add documentation explaining the change
- Keep emergency/shutdown spooling intact

### Step 5: Update MMCB Structure (mm2_core.h)
- Add disk write tracking fields
- Update initialization in `init_sensor_control_block()`

### Step 6: Update Header (mm2_disk.h)
- Add function declarations
- Add new constants if needed

### Step 7: Build and Test
- Build both iMatrix and Fleet-Connect-1
- Run memory manager test suite
- Verify tiered storage behavior

---

## Part 4: Testing Plan

### Test 1: RAM Below Threshold
- Fill RAM to 79%
- Verify all writes go to RAM
- Verify no disk files created

### Test 2: RAM Above Threshold
- Fill RAM to 80%
- Continue writing data
- Verify new data goes to disk
- Verify disk files created with correct format

### Test 3: Upload Path
- Fill RAM then disk
- Trigger upload
- Verify RAM data uploaded first
- Verify disk data uploaded after

### Test 4: Shutdown Path
- Fill RAM with data
- Trigger shutdown
- Verify emergency spooling still works
- Verify data preserved

### Test 5: Recovery
- Create disk files
- Restart system
- Verify disk files discovered and tracked

---

## Part 5: Files to Modify

| File | Changes |
|------|---------|
| `mm2_disk_spooling.c` | Add `write_tsd_value_to_disk()`, `write_evt_value_to_disk()` |
| `mm2_write.c` | Modify `imx_write_tsd()`, `imx_write_evt()` to use disk when RAM full |
| `mm2_api.c` | Disable normal spooling in `process_memory_manager()` phase 2 |
| `mm2_core.h` | Add disk write tracking fields to `imx_mmcb_t` |
| `mm2_disk.h` | Add new function declarations |
| `mm2_pool.c` | Minor: could add RAM utilization check constant |

---

## Part 6: Risk Assessment

### Low Risk
- Disk write functions are additions, not modifications to existing code
- Normal spooling disabled by commenting, easily reversible
- Existing emergency spooling unchanged

### Medium Risk
- MMCB structure changes may affect memory layout
- File format must match existing disk sector header
- Upload path must correctly switch from RAM to disk

### Mitigation
- Thorough testing with both RAM and disk data
- Verify file format with hexdump
- Test upload path with mixed RAM/disk data

---

## Part 7: Open Questions (Resolved)

### Q1: Should pending sectors be spooled?
**A**: No - per spec, only shutdown mode spools RAM→disk. Pending data stays in RAM.

### Q2: Maximum disk sectors to write per call?
**A**: Follow existing pattern - buffer values until sector full (6 for TSD, 2 for EVT), then write.

### Q3: What happens when disk is full?
**A**: Return `IMX_OUT_OF_MEMORY` - same as current RAM full behavior. Space management via 256MB limit.

---

## Appendix A: Key Code Locations

| Concept | File | Line |
|---------|------|------|
| RAM allocation | mm2_pool.c | 376 |
| TSD write | mm2_write.c | 201 |
| EVT write | mm2_write.c | 352 |
| Normal spooling trigger | mm2_api.c | 721 |
| Spooling state machine | mm2_disk_spooling.c | 1029 |
| Sector eligibility | mm2_disk_spooling.c | 194 |
| Disk sector header | mm2_disk.h | 148 |

---

*Plan ready for implementation. Proceed?*
