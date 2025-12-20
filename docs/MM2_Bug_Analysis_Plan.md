# MM2 Bug Analysis: GPS_Latitude Read Failure

**Date**: 2025-12-07
**Status**: Root Cause Identified - Fix Proposed
**Log File**: logs/mm1.txt
**Error**: `IMX_UPLOAD: ERROR: Failed to read all event data for: GPS_Latitude, result: 34:NO DATA, requested: N, received: 0`

---

## 1. Bug Summary

The Memory Manager v2.8 fails to read GPS_Latitude sensor data due to a **sector type mismatch**. GPS sensors are being written via two different code paths that use incompatible data formats.

**Error pattern from logs:**
```
[MM2] write_tsd: sensor=GPS_Latitude, upload_src=3, value=0x421B9B75
[MM2-WR] Write SUCCESS: sensor=GPS_Latitude, sector=7, offset=32
...
[MM2-PEND] erase_all: sector 7 - erased 2 EVT pairs (index 0 to 1)
```

**Key Observation:** Sector 7 is written via `write_tsd` (TSD format) but marked as `SECTOR_TYPE_EVT` in the chain table!

---

## 2. Root Cause Analysis

### The Dual-Write Problem

GPS sensors (GPS_Latitude, GPS_Longitude, GPS_Altitude, GPS_Speed) are being written by **two separate code paths**:

1. **imx_write_gps_location()** (do_everything.c:255-256)
   - Calls `imx_write_evt()` for GPS sensors
   - Allocates sectors as `SECTOR_TYPE_EVT`
   - This is the CORRECT path for GPS data

2. **imx_sample_csd_data()** (do_everything.c:435)
   - Iterates over ALL sensors with `sample_rate > 0`
   - Calls `imx_write_tsd()` for matching sensors
   - Writes TSD-formatted data to existing sector chain

### Execution Flow

1. **First GPS write** via `imx_write_gps_location()`:
   - Allocates sector 7 with `SECTOR_TYPE_EVT`
   - Writes EVT-formatted data (value + timestamp pairs)

2. **Subsequent write** via `imx_sample_csd_data()`:
   - GPS_Latitude has `sample_rate > 0` (configured for periodic sampling)
   - `imx_write_tsd()` is called
   - Sees existing sector chain (`ram_end_sector_id != NULL_SECTOR_ID`)
   - **Does NOT allocate new sector** - uses existing EVT sector
   - Writes TSD-formatted data (value only, no individual timestamp)

3. **Read operation** via `imx_read_bulk()`:
   - Checks `entry->sector_type` which is `SECTOR_TYPE_EVT`
   - Calls `read_evt_from_sector()` expecting EVT format
   - **Data is in TSD format - interpretation fails**
   - Returns `IMX_NO_DATA` (error code 34)

### Why This Happens

Looking at `imx_write_tsd()` in mm2_write.c (lines 248-256):
```c
if (csd->mmcb.ram_end_sector_id == NULL_SECTOR_ID ||
    values_in_sector >= MAX_TSD_VALUES_PER_SECTOR) {
    // Only allocates new sector if chain is empty or sector is full
    SECTOR_ID_TYPE new_sector_id = allocate_sector_for_sensor(sensor_id, SECTOR_TYPE_TSD);
```

The function only allocates a new sector if:
- No current sector exists, OR
- Current sector is full

**It does NOT validate that the existing sector type matches the write format!**

---

## 3. Evidence from Logs

### GPS_Latitude Written as TSD
```
[1765126675.581] [MM2] write_tsd: sensor=GPS_Latitude, upload_src=3, value=0x421B9B75
[1765126675.581] [MM2-WR] Write SUCCESS: sensor=GPS_Latitude, sector=7, offset=32
```

### But Sector Type is EVT
```
[1765126685.344] [MM2-PEND] erase_all: sector 7 - erased 2 EVT pairs (index 0 to 1)
```

### Read Fails
```
[1765126684.066] [MM2] read_bulk: no pending data, starting from sector=7, offset=0
[1765126684.066] [MM2-READ-DEBUG] Last attempted: sector=4294967295, offset=8, result=34
```

- `sector=4294967295` = NULL_SECTOR_ID - chain traversal ended
- `offset=8` = TSD_FIRST_UTC_SIZE - read function detected TSD format mismatch
- `result=34` = IMX_NO_DATA

---

## 4. Resolution Plan

### Fix 1: Skip GPS Sensors in imx_sample_csd_data (RECOMMENDED)

**File:** `iMatrix/cs_ctrl/hal_sample.c`
**Location:** After line 486 (sample_rate > 0 check)

Add check to skip GPS sensors (same pattern as hal_event.c:217-221):

```c
void imx_sample_csd_data(imatrix_upload_source_t upload_source, imx_time_t current_time,
                         uint16_t cs_index, imx_control_sensor_block_t *csb,
                         control_sensor_data_t *csd, device_updates_t *check_in)
{
    if ((csb[cs_index].enabled == true) && (csb[cs_index].sample_rate > 0) &&
        (csd[cs_index].sensor_auto_updated == true) &&
        (imx_is_later(current_time, csd[cs_index].last_poll_time + csb[cs_index].poll_rate)))
    {
        /* Skip GPS sensors - they are handled by imx_write_gps_location() as EVT */
        if (csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_LATITUDE ||
            csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_LONGITUDE ||
            csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_ALTITUDE ||
            csb[cs_index].id == IMX_INTERNAL_SENSOR_GPS_SPEED) {
            return;  /* GPS is written via imx_write_gps_location() as EVT */
        }

        // ... rest of function
```

**Why this fix:**
- GPS sensors are already correctly handled by `imx_write_gps_location()` as EVT
- This prevents the dual-write conflict
- Minimal code change with clear intent
- Consistent with hal_event.c approach

### Fix 2: Add Sector Type Validation (DEFENSIVE)

**File:** `iMatrix/cs_ctrl/mm2_write.c`
**Location:** In both `imx_write_tsd()` and `imx_write_evt()`

Add validation when reusing existing sector:

```c
/* When not allocating new sector, validate type matches */
if (csd->mmcb.ram_end_sector_id != NULL_SECTOR_ID) {
    sector_chain_entry_t* entry = get_sector_chain_entry(csd->mmcb.ram_end_sector_id);
    if (entry && entry->sector_type != SECTOR_TYPE_TSD) {  /* or SECTOR_TYPE_EVT */
        PRINTF("[MM2] ERROR: Sector type mismatch for sensor %s\r\n", csb->name);
        return IMX_INVALID_ENTRY;
    }
}
```

---

## 5. Why hal_event.c Works But hal_sample.c Doesn't

**hal_event.c (lines 217-221)** already skips GPS sensors:
```c
if (csb[entry].id == IMX_INTERNAL_SENSOR_GPS_LATITUDE ||
    csb[entry].id == IMX_INTERNAL_SENSOR_GPS_LONGITUDE ||
    csb[entry].id == IMX_INTERNAL_SENSOR_GPS_ALTITUDE ||
    csb[entry].id == IMX_INTERNAL_SENSOR_GPS_SPEED) {
    return;  /* Skip GPS - handled elsewhere */
}
```

**hal_sample.c** lacks this check, so GPS sensors with `sample_rate > 0` are processed as TSD sensors.

---

## 6. Testing Plan

### Unit Tests
1. Write GPS data via `imx_write_gps_location()`, verify sector is EVT
2. Call `imx_sample_csd_data()` for GPS sensor, verify it returns early (no write)
3. Read GPS data back, verify all records retrieved successfully

### Integration Tests
1. Run system with GPS_Latitude generating data
2. Monitor that only `imx_write_gps_location()` writes GPS (no `write_tsd` logs for GPS)
3. Verify upload successfully reads all GPS records

### Regression Tests
1. Non-GPS TSD sensors still work correctly
2. Non-GPS EVT sensors still work correctly
3. Existing GPS functionality (location tracking) unaffected

---

## 7. Files to Modify

| File | Change |
|------|--------|
| `iMatrix/cs_ctrl/hal_sample.c` | Add GPS sensor skip check after line 486 |

---

## 8. Quick Verification

To verify this is the issue, check if GPS_Latitude has `sample_rate > 0`:

From logs:
```
Polling Sensor: XX, ID: 0x00000002 - Time: ..., Sample Rate: XXXX
```

If GPS_Latitude (ID 0x00000002) appears in polling logs with Sample Rate > 0, this confirms the bug.

---

*Document created by Claude Code Analysis*
*Updated: 2025-12-07 - Revised root cause from TSD offset issue to dual-write sector type mismatch*
