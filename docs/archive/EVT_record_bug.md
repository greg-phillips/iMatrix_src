# EVT/TSD Sector Type Mismatch Bug

**Date**: 2025-12-13
**Status**: Fixed
**Bug Type**: Data Corruption / Read Failure
**Severity**: High
**Affected Components**: Memory Manager (MM2), Sensor Upload

---

## 1. Executive Summary

This document describes a critical bug where sensor data uploads fail with `IMX_NO_DATA` (error code 34) despite the system reporting data is available. The root cause is a **sector type mismatch** caused by sensors being written via two different code paths that use incompatible data formats (TSD vs EVT).

**Key Symptom**: `imx_get_new_sample_count()` reports N records available, but `imx_read_bulk_samples()` returns 0 records.

---

## 2. Bug Symptoms

### 2.1 Error Log Patterns

When this bug occurs, you will see error messages like:

```
[00:05:00.864] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 11, received: 0
[00:05:10.873] IMX_UPLOAD: ERROR: Upload Source: GatewayFailed to read all event data for: Latitude, result: 34:NO DATA, requested: 9, received: 0
[00:05:10.875] IMX_UPLOAD: ERROR: Upload Source: GatewayFailed to read all event data for: Longitude, result: 34:NO DATA, requested: 9, received: 0
```

**Key indicators:**
- `result: 34:NO DATA` - The read function returns IMX_NO_DATA
- `requested: N, received: 0` - System thinks data exists but can't read any
- Multiple sensors affected, especially GPS sensors (Latitude, Longitude, Altitude, Speed)
- Errors occur periodically (every 5-10 minutes typically)

### 2.2 Affected Sensors

This bug primarily affects:
- **GPS Sensors**: GPS_Latitude, GPS_Longitude, GPS_Altitude, GPS_Speed
- **Any sensor written via multiple code paths**

---

## 3. Technical Background

### 3.1 Memory Manager Data Formats

The Memory Manager (MM2) supports two data formats:

| Format | Sector Type | Structure | Use Case |
|--------|-------------|-----------|----------|
| **TSD** (Time Series Data) | `SECTOR_TYPE_TSD` | `[first_UTC:8][value0:4][value1:4]...` | Periodic sampling with calculated timestamps |
| **EVT** (Event Data) | `SECTOR_TYPE_EVT` | `[value:4][UTC:8][value:4][UTC:8]` | Irregular events with individual timestamps |

**Critical Rule**: A sector's type is set when allocated and MUST match the data format written to it.

### 3.2 How Sectors Are Allocated

When `imx_write_tsd()` or `imx_write_evt()` needs a new sector:

1. Check if current sector exists and has space
2. If new sector needed, call `allocate_sector_for_sensor(sensor_id, SECTOR_TYPE_xxx)`
3. Sector is marked with the appropriate type in the chain table

### 3.3 How Data Is Read

During upload, `imx_read_bulk_samples()`:

1. Gets the sector chain entry
2. Checks `entry->sector_type`
3. Calls `read_tsd_from_sector()` or `read_evt_from_sector()` based on type
4. **If data format doesn't match sector type, read fails with IMX_NO_DATA**

---

## 4. Root Cause: The Dual-Write Problem

### 4.1 The Problem

GPS sensors are written by **two different code paths**:

#### Path 1: Correct (EVT format)
```
do_everything.c → imx_write_gps_location() → imx_write_evt()
                                           ↓
                              Allocates SECTOR_TYPE_EVT
                              Writes [value:4][UTC:8] pairs
```

#### Path 2: Incorrect (TSD format)
```
hal_sample.c → imx_sample_csd_data() → imx_write_tsd()
                                     ↓
                        Reuses existing sector (EVT type!)
                        Writes [first_UTC:8][values...] format
```

### 4.2 The Failure Sequence

```
1. GPS sensor configured with sample_rate > 0

2. First write via imx_write_gps_location():
   - Allocates sector 7 with SECTOR_TYPE_EVT
   - Writes EVT-formatted data (value + timestamp pairs)
   - Sector 7 chain entry: { in_use: true, sector_type: EVT }

3. Later write via imx_sample_csd_data():
   - GPS sensor matches condition (sample_rate > 0, enabled)
   - imx_write_tsd() is called
   - Sees ram_end_sector_id = 7 (existing sector)
   - Does NOT allocate new sector (sector has space)
   - Writes TSD-formatted data to EVT sector!
   - Sector 7 now contains: [EVT data][TSD data] - CORRUPTED

4. Read during upload:
   - imx_read_bulk_samples() called
   - Gets sector 7, sees sector_type = EVT
   - Calls read_evt_from_sector()
   - Tries to parse TSD data as EVT format
   - Returns IMX_NO_DATA (error 34)
```

### 4.3 Why This Happens

The `imx_write_tsd()` function (before fix):
```c
if (csd->mmcb.ram_end_sector_id == NULL_SECTOR_ID ||
    values_in_sector >= MAX_TSD_VALUES_PER_SECTOR) {
    // Only allocates new sector if:
    // - No current sector exists, OR
    // - Current sector is full
    new_sector = allocate_sector_for_sensor(id, SECTOR_TYPE_TSD);
}
// Otherwise, reuses existing sector WITHOUT checking its type!
```

**The Bug**: No validation that existing sector type matches write format.

---

## 5. How to Diagnose This Bug

### 5.1 Quick Diagnostic Checklist

1. **Check error pattern**: Look for `result: 34:NO DATA, requested: N, received: 0`
2. **Identify affected sensors**: Are they GPS sensors or sensors with multiple write paths?
3. **Check sample_rate**: Do affected sensors have `sample_rate > 0`?
4. **Look for write logs**: Are there both `write_tsd` and `write_evt` logs for same sensor?

### 5.2 Detailed Debug Logs

Enable MM2 debug output and look for:

```
# TSD write to GPS sensor (WRONG - should not happen)
[MM2] write_tsd: sensor=GPS_Latitude, upload_src=3, value=0x421B9B75

# EVT write to GPS sensor (CORRECT)
[MM2] write_evt: sensor=GPS_Latitude, upload_src=3, value=0x421B9B75

# Sector type mismatch warning (if defensive fix is active)
[MM2-WR] WARNING: Sector type mismatch for sensor GPS_Latitude - expected TSD, got 1
```

### 5.3 Verification: Check GPS Sensor Configuration

Look for GPS sensors being polled in sampling logs:
```
Polling Sensor: XX, ID: 0x00000002 - Time: ..., Sample Rate: XXXX
```

If `GPS_Latitude` (ID 0x00000002) or other GPS sensors appear with `Sample Rate > 0`, the dual-write condition exists.

---

## 6. The Fix

### 6.1 Primary Fix: Skip GPS Sensors in Sampling Path

**File**: `iMatrix/cs_ctrl/hal_sample.c`
**Location**: Inside `imx_sample_csd_data()`, before `imx_write_tsd()` call

```c
/**
 * Skip GPS sensors - they are handled by imx_write_gps_location() as EVT
 *
 * GPS sensors should NOT be written via imx_write_tsd() as this causes
 * sector type mismatch (EVT sectors receiving TSD data), which results
 * in read failures with IMX_NO_DATA (error 34).
 */
if (csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_LATITUDE ||
    csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_LONGITUDE ||
    csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_ALTITUDE ||
    csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_SPEED) {
    PRINTF("[HAL_SAMPLE] Skipping GPS sensor %s - handled by imx_write_gps_location()\r\n",
           csb[cs_index].name);
    return;  /* GPS is written via imx_write_gps_location() as EVT */
}
```

**Why this fix works**:
- GPS sensors are correctly handled by `imx_write_gps_location()` as EVT
- This prevents the dual-write that causes sector type mismatch
- Matches the pattern already used in `hal_event.c` (lines 218-222)

### 6.2 Defensive Fix: Sector Type Validation

**File**: `iMatrix/cs_ctrl/mm2_write.c`
**Location**: In both `imx_write_tsd()` and `imx_write_evt()`

```c
/**
 * DEFENSIVE CHECK: Validate sector type matches write format
 */
if (csd->mmcb.ram_end_sector_id != NULL_SECTOR_ID) {
    sector_chain_entry_t* entry = get_sector_chain_entry(csd->mmcb.ram_end_sector_id);
    if (entry && entry->sector_type != SECTOR_TYPE_TSD) {  // or SECTOR_TYPE_EVT
        PRINTF("[MM2-WR] WARNING: Sector type mismatch for sensor %s\r\n", csb->name);
        need_new_sector_due_to_type_mismatch = true;
    }
}

if (need_new_sector_due_to_type_mismatch) {
    // Allocate new sector with correct type instead of corrupting existing
}
```

**Why this fix works**:
- Detects sector type mismatch before writing
- Allocates a new sector with correct type instead of corrupting data
- Provides warning log for debugging
- Prevents data loss even if primary fix is bypassed

---

## 7. Verification After Fix

### 7.1 Expected Behavior

After applying the fix:

1. **No more `NO DATA` errors** for GPS sensors in upload logs
2. **Debug log shows skip message**:
   ```
   [HAL_SAMPLE] Skipping GPS sensor GPS_Latitude - handled by imx_write_gps_location()
   ```
3. **GPS data uploads successfully** with all requested records returned

### 7.2 Test Cases

| Test | Expected Result |
|------|-----------------|
| GPS sensor with sample_rate > 0 | Skipped in hal_sample, written only via imx_write_gps_location |
| Upload GPS sensor data | All requested records returned, no IMX_NO_DATA |
| Sector type mismatch (defensive) | Warning logged, new sector allocated, no corruption |
| Non-GPS TSD sensors | Continue working normally |
| Non-GPS EVT sensors | Continue working normally |

---

## 8. Related Files

| File | Purpose |
|------|---------|
| `iMatrix/cs_ctrl/hal_sample.c` | Sampling loop, calls `imx_write_tsd()` |
| `iMatrix/cs_ctrl/hal_event.c` | Event handling, has GPS skip pattern (reference) |
| `iMatrix/cs_ctrl/mm2_write.c` | TSD/EVT write functions |
| `iMatrix/cs_ctrl/mm2_read.c` | Bulk read function |
| `Fleet-Connect-1/do_everything.c` | Calls `imx_write_gps_location()` |
| `docs/MM2_Bug_Analysis_Plan.md` | Original bug analysis |
| `docs/gen/tsd_record_fault_plan.md` | Detailed fix plan |

---

## 9. Future Prevention

### 9.1 Code Review Checklist

When adding new sensor write paths:
- [ ] Does the sensor already have a write path?
- [ ] What sector type does the existing path use?
- [ ] Is the new write using the same format (TSD vs EVT)?
- [ ] Should this sensor be skipped in one of the paths?

### 9.2 Architecture Recommendation

For sensors that need special handling:
1. Document which code path "owns" the sensor writes
2. Add skip checks in all other paths
3. Use the defensive sector type validation as a safety net

---

## 10. Appendix: Sensor ID Reference

| Sensor | ID | Correct Write Function |
|--------|----|-----------------------|
| GPS_Latitude | 2 | `imx_write_gps_location()` → EVT |
| GPS_Longitude | 3 | `imx_write_gps_location()` → EVT |
| GPS_Altitude | 4 | `imx_write_gps_location()` → EVT |
| GPS_Speed | 47 | `imx_write_gps_location()` → EVT |

These constants are defined via X-macro in `internal_sensors_def.h` and expanded in `common.h`:
```c
#define X(name, value, string) IMX_INTERNAL_SENSOR_##name = value,
```

---

*Document created by Claude Code*
*Date: 2025-12-13*
*For questions, see the original analysis in docs/MM2_Bug_Analysis_Plan.md*
