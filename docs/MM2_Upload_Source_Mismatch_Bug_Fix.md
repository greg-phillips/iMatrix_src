# MM2 Upload Source Mismatch Bug Fix

**Date**: 2025-12-07
**Author**: Claude Code
**Status**: Implemented and Tested
**Affects**: Memory Manager v2.8, Host Sensor Data Upload

## Executive Summary

Fixed a critical bug where host sensor data (4G RSSI, trip meter, etc.) was not being freed from MM2 RAM sectors after successful CoAP upload acknowledgements. The root cause was a mismatch between the `upload_source` used during write operations and the `upload_source` used during upload/read operations.

## Problem Description

### Symptoms
- RAM memory continuously growing during operation
- Sectors allocated for host sensor data never freed
- Log messages showing "NO RAM CHAIN" for sensors that had data written
- GPS sensors worked correctly while other host sensors did not

### Observed Behavior (from mm8.txt analysis)
```
[MM2-ALLOC] Allocated sector 845 for sensor "4G RSSI"
...
[MM2-READ] Sensor "4G_RF_RSSI" - NO RAM CHAIN - checking disk
```

The sensor "4G RSSI" had data allocated to sector 845, but during upload the code couldn't find it because it was looking in the wrong pending tracking slot.

## Root Cause Analysis

### The Upload Source Architecture

MM2 tracks pending data separately for each upload source using:
```c
csd->mmcb.pending_by_source[upload_source]
```

This allows different upload paths (gateway, hosted device, CAN device) to independently track what data has been sent and acknowledged.

### The Bug

In `hal_event.c`, the `imx_hal_event()` function was hardcoded to use `IMX_UPLOAD_CAN_DEVICE` for all event writes:

```c
// BEFORE (broken)
imx_write_evt(IMX_UPLOAD_CAN_DEVICE, &csb[entry], &csd[entry], ...);
```

However, during upload:
- When `imatrix.upload_source == IMX_HOSTED_DEVICE`:
  - Uses `mgs.csd[]` array (correct)
  - BUT checks `pending_by_source[IMX_HOSTED_DEVICE]` (EMPTY!)

- When `imatrix.upload_source == IMX_UPLOAD_CAN_DEVICE`:
  - Uses `mgs.can_csd[]` array (WRONG - this is the CAN sensor array)

### Why GPS Worked

GPS sensors are written via `hal_sample()` which correctly uses:
```c
imx_write_tsd(sample_status.upload_source, &csb[*active], &csd[*active], data);
```

The `sample_status.upload_source` is set to `IMX_UPLOAD_GATEWAY`, and during gateway upload, the code looks in `pending_by_source[IMX_UPLOAD_GATEWAY]` - matching correctly.

## The Fix

### Approach

Added `upload_source` parameter to `imx_hal_event()` so each caller can specify the correct upload source:
- `hal_event()` (for gateway sensors) → passes `IMX_UPLOAD_GATEWAY`
- `host_hal_event()` (for host sensors) → passes `IMX_HOSTED_DEVICE`

### Files Modified

#### iMatrix Submodule

| File | Change |
|------|--------|
| `imatrix.h:239` | Added `imatrix_upload_source_t upload_source` as first parameter to `imx_hal_event()` |
| `cs_ctrl/hal_event.h:65` | Updated function declaration to match |
| `cs_ctrl/hal_event.c:120-134` | Updated `imx_hal_event()` signature and documentation |
| `cs_ctrl/hal_event.c:118` | `hal_event()` now passes `IMX_UPLOAD_GATEWAY` |
| `cs_ctrl/hal_event.c:225-234` | Changed hardcoded `IMX_UPLOAD_CAN_DEVICE` to use passed `upload_source` |

#### Fleet-Connect-1 Submodule

| File | Change |
|------|--------|
| `product/hal_functions.c:577` | `host_hal_event()` now passes `IMX_HOSTED_DEVICE` |
| `energy/energy_manager.c:776` | Updated `imx_hal_event()` call to pass `IMX_HOSTED_DEVICE` |
| `energy/energy_manager.c:1100` | Updated `imx_hal_event()` call to pass `IMX_HOSTED_DEVICE` |

### Code Changes Detail

#### imatrix.h (declaration)
```c
// BEFORE
void imx_hal_event(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   imx_peripheral_type_t type, uint16_t entry, void *value,
                   bool log_location);

// AFTER
void imx_hal_event(imatrix_upload_source_t upload_source,
                   imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   imx_peripheral_type_t type, uint16_t entry, void *value,
                   bool log_location);
```

#### hal_event.c (implementation)
```c
// hal_event() for gateway sensors
void hal_event(imx_peripheral_type_t type, uint16_t entry, void *value, bool log_location)
{
    ...
    csb = imx_get_csb(type);
    csd = imx_get_csd(type);
    imx_hal_event(IMX_UPLOAD_GATEWAY, csb, csd, type, entry, value, log_location);
}

// imx_hal_event() now uses passed upload_source
void imx_hal_event(imatrix_upload_source_t upload_source, ...)
{
    ...
    if (log_location) {
        imx_write_event_with_gps(upload_source, &csb[entry], &csd[entry], ...);
    } else {
        imx_write_evt(upload_source, &csb[entry], &csd[entry], ...);
    }
}
```

#### hal_functions.c (host sensor path)
```c
// BEFORE
void host_hal_event(imx_peripheral_type_t type, uint16_t entry, void *value, bool log_location)
{
    ...
    imx_hal_event(mgc.csb, mgs.csd, type, entry, value, log_location);
}

// AFTER
void host_hal_event(imx_peripheral_type_t type, uint16_t entry, void *value, bool log_location)
{
    ...
    imx_hal_event(IMX_HOSTED_DEVICE, mgc.csb, mgs.csd, type, entry, value, log_location);
}
```

## Related Fixes in This Session

### 1. RAM Data Incorrectly Marked as Disk-Only (mm2_read.c)

When reading the last record from a sector, `current_sector` becomes `NULL_SECTOR_ID`, causing position comparison to fail and RAM data to be incorrectly marked as "disk-only".

**Fix**: Added `bool did_read_from_ram` flag to explicitly track RAM reads instead of relying on position comparison.

### 2. Async Log Queue print_time Parameter (async_log_queue.c/h)

The `print_time` parameter wasn't being respected - Unix timestamps were always printed.

**Fix**: Added `print_time` field to `log_message_t` structure and check it during `async_log_flush()`.

## Testing Verification

After applying the fix:
1. Host sensor data (4G RSSI, etc.) now shows "from RAM" during upload
2. Sectors are properly freed after CoAP acknowledgements
3. RAM memory stabilizes instead of continuously growing
4. All sensor types now work consistently

## Lessons Learned

1. **Upload source consistency**: When writing data with MM2, the `upload_source` parameter must match what the upload code will use when reading/acknowledging data.

2. **Separate pending tracking**: MM2's per-upload-source pending tracking is powerful but requires careful coordination between write and read paths.

3. **Hardcoded values**: Avoid hardcoding upload source values in shared functions - pass them as parameters to maintain flexibility.

## References

- MM2 Developer Guide: `iMatrix/cs_ctrl/MM2_Developer_Guide.md`
- Memory Manager Technical Reference: `docs/memory_manager_technical_reference.md`
- Test logs: `logs/mm5.txt` through `logs/mm8.txt`
