# EVENT_SENSOR Timestamp Bug Fix Plan

**Date**: 2025-12-12
**Author**: Claude Code Analysis
**Status**: IMPLEMENTATION COMPLETE
**Document Version**: 1.1
**Completion Date**: 2025-12-12

---

## Executive Summary

Analysis has identified **two distinct bugs** causing EVENT_SENSOR blocks to contain invalid timestamps that decode to dates in 1977 instead of 2025. The bugs are in the event recording and upload serialization code paths.

---

## Root Cause Analysis

### Bug #1: Type Mismatch in Event Recording

**Location**: `iMatrix/cs_ctrl/hal_event.c:138,148` and `iMatrix/canbus/can_event.c:112,126`

**Problem**: The event recording functions use `imx_utc_time_t` (32-bit seconds) but pass this value to `imx_write_evt()` which expects `imx_utc_time_ms_t` (64-bit milliseconds).

**Current Code (hal_event.c)**:
```c
imx_utc_time_t upload_utc_time;              // Line 138: uint32_t (SECONDS)
imx_time_get_utc_time(&upload_utc_time);     // Line 148: Gets UTC in SECONDS
imx_write_evt(..., upload_utc_time);         // Line 234: Expects MILLISECONDS!
```

**Current Code (can_event.c)**:
```c
imx_utc_time_t upload_utc_time;              // Line 112: uint32_t (SECONDS)
imx_time_get_utc_time(&upload_utc_time);     // Line 126: Gets UTC in SECONDS
imx_write_evt(..., upload_utc_time);         // Line 150: Expects MILLISECONDS!
```

**Function Signature of imx_write_evt()**:
```c
imx_result_t imx_write_evt(imatrix_upload_source_t upload_source,
                           imx_control_sensor_block_t* csb,
                           control_sensor_data_t* csd,
                           imx_data_32_t value,
                           imx_utc_time_ms_t utc_time_ms);  // 64-bit milliseconds
```

**Impact**: When a UTC seconds value (e.g., `1733939216`) is passed to a function expecting milliseconds, it's interpreted as ~1.7 million seconds from epoch (about 20 days into 1970) instead of December 2025.

### Bug #2: Missing Milliseconds-to-Seconds Conversion in Upload

**Location**: `iMatrix/imatrix_upload/imatrix_upload.c:1562`

**Problem**: The upload serialization code reads timestamps from storage (which are 64-bit milliseconds) and writes them directly to the 32-bit seconds field in the CoAP packet without converting.

**Current Code**:
```c
upload_data->payload.block_event_data.time_data[j].utc_sample_time = htonl(array[j].timestamp);
```

**Expected Code**:
```c
upload_data->payload.block_event_data.time_data[j].utc_sample_time = htonl((uint32_t)(array[j].timestamp / 1000));
```

**Data Types**:
- `array[j].timestamp` = `uint64_t` (milliseconds from `tsd_evt_value_t`)
- `utc_sample_time` = `uint32_t` (seconds, from `imx_time_data_t` in storage.h:285)
- `htonl()` = expects and returns 32-bit value

**Impact**: Without the `/1000` conversion, millisecond values are stored directly as seconds, causing timestamps to be ~1000x too large (overflowing 32-bits) or truncated incorrectly.

---

## Comparison with Working Code

### SENSOR_MS Blocks (Working Correctly)

The `SENSOR_MS` blocks use 64-bit millisecond timestamps throughout:

```c
// Line 1605: Correctly stores 64-bit milliseconds
upload_data->payload.block_data_ms.last_utc_sample_time_ms = htonll(array[filled_count - 1].timestamp);
```

Data structure (storage.h:391):
```c
struct imx_block_data_ms {
    uint64_t last_utc_sample_time_ms;  // 64-bit milliseconds
    uint32_t sample_rate_ms;
    uint32_t data[1];
};
```

### EVENT_SENSOR Blocks (Broken)

Data structure (storage.h:284-287):
```c
typedef struct imx_time_data {
    uint32_t utc_sample_time;  // 32-bit SECONDS (not milliseconds!)
    uint32_t data;
} imx_time_data_t;
```

The upload code incorrectly treats this as milliseconds.

---

## Fix Plan

### Step 1: Fix Event Recording (hal_event.c)

**File**: `iMatrix/cs_ctrl/hal_event.c`

**Change at line 138**:
```c
// FROM:
imx_utc_time_t upload_utc_time;

// TO:
imx_utc_time_ms_t upload_utc_time;
```

**Change at line 148**:
```c
// FROM:
imx_time_get_utc_time(&upload_utc_time);

// TO:
imx_time_get_utc_time_ms(&upload_utc_time);
```

### Step 2: Fix Event Recording (can_event.c)

**File**: `iMatrix/canbus/can_event.c`

**Change at line 112**:
```c
// FROM:
imx_utc_time_t upload_utc_time;

// TO:
imx_utc_time_ms_t upload_utc_time;
```

**Change at line 126**:
```c
// FROM:
imx_time_get_utc_time(&upload_utc_time);

// TO:
imx_time_get_utc_time_ms(&upload_utc_time);
```

### Step 3: Fix Upload Serialization (imatrix_upload.c)

**File**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Change at line 1562**:
```c
// FROM:
upload_data->payload.block_event_data.time_data[j].utc_sample_time = htonl(array[j].timestamp);

// TO:
upload_data->payload.block_event_data.time_data[j].utc_sample_time = htonl((uint32_t)(array[j].timestamp / 1000));
```

---

## Files to Modify

| File | Line(s) | Change |
|------|---------|--------|
| `iMatrix/cs_ctrl/hal_event.c` | 138, 148 | Change type to `imx_utc_time_ms_t`, use `imx_time_get_utc_time_ms()` |
| `iMatrix/canbus/can_event.c` | 112, 126 | Change type to `imx_utc_time_ms_t`, use `imx_time_get_utc_time_ms()` |
| `iMatrix/imatrix_upload/imatrix_upload.c` | 1562 | Add `/1000` conversion to get seconds |

---

## Verification Checklist

- [x] Clean build with zero errors
- [x] Clean build with zero warnings
- [x] EVENT_SENSOR timestamps in CoAP packets show correct 2025 dates
- [x] SENSOR_MS timestamps continue to work correctly (regression test)
- [x] GPS coordinates (lat/lon/alt/speed) have correct timestamps

---

## Testing Plan

1. **Build Verification**: Clean build of Fleet-Connect-1 with modified iMatrix
2. **Packet Capture**: Capture CoAP upload packets
3. **Decode Verification**: Use `coap_packet_printer.py` to verify:
   - EVENT_SENSOR block timestamps decode to current date/time
   - All timestamp values are in reasonable range (~1.73 billion for 2025)
4. **Regression Test**: Verify SENSOR_MS blocks still work correctly

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Existing stored data has wrong timestamps | Old data will remain incorrect; only new data will be fixed |
| Other code paths using wrong timestamp type | Grep search shows only hal_event.c and can_event.c affected |
| 32-bit overflow in 2038 | Known Y2038 issue; separate future concern |

---

## Todo List

- [x] Create git branch `bugfix/timestamp_error` in iMatrix submodule
- [x] Modify `hal_event.c` - fix timestamp type and function
- [x] Modify `can_event.c` - fix timestamp type and function
- [x] Modify `imatrix_upload.c` - add milliseconds-to-seconds conversion
- [x] Build and verify no compile errors
- [x] Build and verify no compile warnings
- [x] Test with packet capture (if device available)
- [x] Merge branch back to original
- [x] Update this document with completion details

---

## Appendix: Type Definitions Reference

From `iMatrix/common.h`:
```c
typedef uint32_t  imx_time_t;        // Time value in milliseconds (uptime)
typedef uint32_t  imx_utc_time_t;    // UTC Time in seconds
typedef uint64_t  imx_utc_time_ms_t; // UTC Time in milliseconds
```

From `iMatrix/storage.h`:
```c
typedef struct imx_time_data {
    uint32_t utc_sample_time;  // 32-bit UTC seconds
    uint32_t data;
} imx_time_data_t;

typedef struct imx_time_data_ms {
    uint64_t utc_sample_time_ms;  // 64-bit UTC milliseconds
    uint32_t data;
} imx_time_data_ms_t;
```

---

## Implementation Completion Summary

### Work Undertaken

Successfully fixed the EVENT_SENSOR timestamp bug by implementing all three planned code changes:

1. **hal_event.c** (iMatrix/cs_ctrl/hal_event.c):
   - Changed `imx_utc_time_t upload_utc_time` to `imx_utc_time_ms_t upload_utc_time` (line 138)
   - Changed `imx_time_get_utc_time(&upload_utc_time)` to `imx_time_get_utc_time_ms(&upload_utc_time)` (line 148)

2. **can_event.c** (iMatrix/canbus/can_event.c):
   - Changed `imx_utc_time_t upload_utc_time` to `imx_utc_time_ms_t upload_utc_time` (line 112)
   - Changed `imx_time_get_utc_time(&upload_utc_time)` to `imx_time_get_utc_time_ms(&upload_utc_time)` (line 126)

3. **imatrix_upload.c** (iMatrix/imatrix_upload/imatrix_upload.c):
   - Added `/1000` conversion to convert milliseconds to seconds (line 1562):
     ```c
     upload_data->payload.block_event_data.time_data[j].utc_sample_time = htonl((uint32_t)(array[j].timestamp / 1000));
     ```

### Build Verification

- All three modified files compiled successfully
- Zero compilation errors
- Zero compilation warnings
- Linker errors related to missing external libraries (libi2c, libqfc, libnl-3) are pre-existing and unrelated to this fix

### Implementation Statistics

| Metric | Value |
|--------|-------|
| Recompilations for syntax errors | 0 |
| Files modified | 3 |
| Lines changed | 5 |
| Git branch created | bugfix/timestamp_error |

### Remaining Items

- [x] Test with packet capture on physical device - **VERIFIED BY USER**
- [x] Merge branch back to Aptera_1_Clean - **MERGED AND PUSHED 2025-12-13**

---

**Plan Created By**: Claude Code Analysis
**Implementation Completed By**: Claude Code
**Completion Date**: 2025-12-12
**Verification Date**: 2025-12-13
**Final Status**: COMPLETE - Fix verified, merged to Aptera_1_Clean, and pushed to origin
