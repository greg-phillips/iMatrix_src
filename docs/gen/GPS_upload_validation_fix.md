# GPS Upload Layer Validation Fix

**Date:** 2026-01-05
**Author:** Claude Code Analysis
**Status:** COMPLETE
**Related:** GPS_logging_issue_plan.md (NMEA layer fix)

---

## Problem

Analysis of `142994297-1767554644733.geojson` revealed **158 instances** of corrupt GPS data:
```json
"coordinates": [0, 9.183549615799121e-41]
```

The value `9.183549615799121e-41` is a **subnormal float** from uninitialized memory.

### Why Existing Validation Failed

| Check | Value | Result |
|-------|-------|--------|
| Range: -90 to 90 | 9.18e-41 | **PASS** (within range!) |
| Non-zero: `!= 0` | 9.18e-41 | **PASS** (not exactly 0) |

The value passed range validation because it's technically between -90 and 90.

---

## Solution: Upload Layer Validation

Added validation in `add_gps()` as the **final gate** before cloud transmission.

### File Modified

`iMatrix/imatrix_upload/add_internal.c`

### Changes

1. **Added `#include <math.h>`** for `isfinite()` and `fabsf()`

2. **Added validation checks:**

| Check | Catches |
|-------|---------|
| `fix_quality < 1` | No GPS fix |
| `!isfinite(lat/lon)` | NaN, Infinity |
| `fabsf() < 0.0001` | Subnormal garbage like `9.18e-41` |
| Range check | lat outside -90..90, lon outside -180..180 |
| `lat == 0 && lon == 0` | Both coordinates zero |

3. **Fixed pre-existing bug:** Added missing `coap->msg_length += block_length;`

### Key Validation Code

```c
/* Check for subnormal/garbage values (like 9.18e-41) */
#define GPS_COORD_MIN_ABSOLUTE  (0.0001f)
if ((fabsf(lat) < GPS_COORD_MIN_ABSOLUTE && lat != 0.0f) ||
    (fabsf(lon) < GPS_COORD_MIN_ABSOLUTE && lon != 0.0f)) {
    PRINTF("[GPS UPLOAD - Subnormal coordinates, skipping]\r\n");
    return false;
}
```

The threshold `0.0001` (~11 meters at equator) catches subnormal floats while allowing valid coordinates near the equator/prime meridian.

---

## Log Messages

When invalid GPS is skipped:
- `[GPS UPLOAD - No fix (quality=0), skipping]`
- `[GPS UPLOAD - NaN/Inf coordinates, skipping]`
- `[GPS UPLOAD - Subnormal coordinates (lat=..., lon=...), skipping]`
- `[GPS UPLOAD - Out of range (lat=..., lon=...), skipping]`
- `[GPS UPLOAD - Zero coordinates, skipping]`

---

## Defense in Depth

| Layer | Status | Purpose |
|-------|--------|---------|
| 1. NMEA Parsing | Done (prior fix) | Reject at source |
| 5. Upload | **Done (this fix)** | Final gate before cloud |

Middle layers (setters, getters, event gen) not needed - if Layer 1 catches it, data never enters system. Layer 5 catches anything that slips through or occurs after parsing.

---

## Build Verification

- **Compilation:** Zero errors
- **Warnings:** Zero warnings
- **Build status:** SUCCESS

---

## Lines Changed

- `iMatrix/imatrix_upload/add_internal.c`: +45 lines
