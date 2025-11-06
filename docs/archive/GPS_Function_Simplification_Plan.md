# GPS Function Simplification - Remove Redundant Parameters

## Overview

The `imx_write_event_with_gps()` function currently accepts lat/lon/speed sensor entry indices as parameters, but these are already configured in the `g_gps_config` array during initialization. This is redundant and makes the API more complex than necessary.

**Goal**: Simplify the function signature to use GPS sensor indices from the configuration structure.

---

## Current State (Redundant)

### Function Signature
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value,
    uint16_t lat_sensor_entry,      // ← REDUNDANT - already in g_gps_config
    uint16_t lon_sensor_entry,      // ← REDUNDANT - already in g_gps_config
    uint16_t speed_sensor_entry     // ← REDUNDANT - already in g_gps_config
);
```

### Configuration Structure
```c
static gps_source_config_t g_gps_config[IMX_UPLOAD_NO_SOURCES] = {
    [IMX_UPLOAD_GATEWAY] = {
        .csb_array = icb.i_scb,
        .csd_array = icb.i_sd,
        .lat_sensor_entry = 2,      // ← ALREADY CONFIGURED
        .lon_sensor_entry = 3,      // ← ALREADY CONFIGURED
        .speed_sensor_entry = 19,   // ← ALREADY CONFIGURED
        .no_sensors = 46
    },
    // ...
};
```

**Problem**: Caller must pass sensor indices that are already stored in the config!

---

## Proposed State (Simplified)

### New Function Signature
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value
    /* lat/lon/speed parameters REMOVED - read from g_gps_config instead */
);
```

### Usage Comparison

**Before** (complex):
```c
imx_write_event_with_gps(
    IMX_UPLOAD_GATEWAY,
    &csb[event_idx],
    &csd[event_idx],
    event_value,
    2,   /* lat - why repeat this? */
    3,   /* lon - why repeat this? */
    19   /* speed - why repeat this? */
);
```

**After** (simple):
```c
imx_write_event_with_gps(
    IMX_UPLOAD_GATEWAY,
    &csb[event_idx],
    &csd[event_idx],
    event_value
    /* GPS sensor indices automatically retrieved from g_gps_config */
);
```

**Benefits**:
- ✅ Simpler API - 4 parameters instead of 7
- ✅ Less error-prone - can't pass wrong indices
- ✅ Single source of truth - GPS config in one place
- ✅ Consistent with initialization pattern

---

## Implementation Plan

### Step 1: Update Function Signature in Header

**File**: `mm2_api.h`

**Current** (lines 151-164):
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value,
    uint16_t lat_sensor_entry,
    uint16_t lon_sensor_entry,
    uint16_t speed_sensor_entry
);
```

**New**:
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value
);
```

---

### Step 2: Update Function Implementation

**File**: `mm2_write.c` (lines 398-485)

**Current**:
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value,
    uint16_t lat_sensor_entry,      // ← REMOVE
    uint16_t lon_sensor_entry,      // ← REMOVE
    uint16_t speed_sensor_entry)    // ← REMOVE
{
    // ...
    /* Get CSB/CSD arrays for this upload source */
    imx_control_sensor_block_t* source_csb = g_gps_config[upload_source].csb_array;
    control_sensor_data_t* source_csd = g_gps_config[upload_source].csd_array;
    uint16_t source_no_sensors = g_gps_config[upload_source].no_sensors;

    /* Write latitude if sensor entry configured */
    if (lat_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&  // ← Use parameter
        lat_sensor_entry < source_no_sensors) {
        // ...
    }
}
```

**New**:
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value)
{
    // ...
    /* Get GPS configuration for this upload source */
    gps_source_config_t* gps_config = &g_gps_config[upload_source];

    /* Check if GPS configured */
    if (gps_config->csb_array == NULL || gps_config->csd_array == NULL) {
        return IMX_SUCCESS;  /* Not configured - skip GPS */
    }

    /* Write latitude if configured in initialization */
    if (gps_config->lat_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
        gps_config->lat_sensor_entry < gps_config->no_sensors) {

        imx_data_32_t lat_data;
        lat_data.float_32bit = latitude;

        imx_write_evt(upload_source,
                      &gps_config->csb_array[gps_config->lat_sensor_entry],
                      &gps_config->csd_array[gps_config->lat_sensor_entry],
                      lat_data,
                      event_time);
    }

    /* Same pattern for longitude and speed... */
}
```

---

### Step 3: Update Function Documentation

**File**: `mm2_api.h` (lines 127-154)

**Current**:
```c
/**
 * @brief Write event with GPS location using synchronized timestamp
 *
 * @param upload_source Upload source for all sensors
 * @param event_csb Primary event sensor configuration
 * @param event_csd Primary event sensor data
 * @param event_value Primary event value
 * @param lat_sensor_entry Latitude sensor entry index (IMX_INVALID_SENSOR_ENTRY to skip)
 * @param lon_sensor_entry Longitude sensor entry index (IMX_INVALID_SENSOR_ENTRY to skip)
 * @param speed_sensor_entry Speed sensor entry index (IMX_INVALID_SENSOR_ENTRY to skip)
 * @return IMX_SUCCESS if event written, error code on failure
 */
```

**New**:
```c
/**
 * @brief Write event with GPS location using synchronized timestamp
 *
 * GPS sensor indices are retrieved from the configuration set by
 * imx_init_gps_config_for_source(). If GPS not configured for the
 * upload source, only the primary event is written (GPS writes skipped).
 *
 * @param upload_source Upload source (determines which GPS config to use)
 * @param event_csb Primary event sensor configuration
 * @param event_csd Primary event sensor data
 * @param event_value Primary event value
 * @return IMX_SUCCESS if event written, error code on failure
 *
 * @note GPS sensor indices must be configured via imx_init_gps_config_for_source()
 *       before calling this function, otherwise GPS writes are skipped.
 *
 * @see imx_init_gps_config_for_source()
 */
```

---

### Step 4: Update All Callers

**File**: `hal_event.c` (line 224)

**Current**:
```c
imx_write_event_with_gps(
    IMX_UPLOAD_CAN_DEVICE,
    &csb[entry],
    &csd[entry],
    csd[entry].last_raw_value,
    IMX_INVALID_SENSOR_ENTRY,  // ← REMOVE
    IMX_INVALID_SENSOR_ENTRY,  // ← REMOVE
    IMX_INVALID_SENSOR_ENTRY   // ← REMOVE
);
```

**New**:
```c
imx_write_event_with_gps(
    IMX_UPLOAD_CAN_DEVICE,
    &csb[entry],
    &csd[entry],
    csd[entry].last_raw_value
    /* GPS sensor indices retrieved from g_gps_config[IMX_UPLOAD_CAN_DEVICE] */
);
```

**Note**: This is currently the ONLY caller of this function

---

### Step 5: Update Test Code (if any)

**Search for**: All calls to `imx_write_event_with_gps` in test suite

**Current pattern**:
```c
imx_write_event_with_gps(source, csb, csd, value, lat, lon, speed);
```

**New pattern**:
```c
imx_write_event_with_gps(source, csb, csd, value);
```

---

## Implementation Checklist

### Code Changes

- [ ] **Step 1**: Update signature in `mm2_api.h` (remove 3 parameters)
- [ ] **Step 2**: Update implementation in `mm2_write.c`:
  - [ ] Remove parameters from function signature
  - [ ] Change `lat_sensor_entry` parameter to `gps_config->lat_sensor_entry`
  - [ ] Change `lon_sensor_entry` parameter to `gps_config->lon_sensor_entry`
  - [ ] Change `speed_sensor_entry` parameter to `gps_config->speed_sensor_entry`
- [ ] **Step 3**: Update documentation in `mm2_api.h`
- [ ] **Step 4**: Update caller in `hal_event.c` (remove 3 arguments)
- [ ] **Step 5**: Search for and update any test code callers

### Validation

- [ ] Code compiles without errors
- [ ] No warnings about parameter mismatch
- [ ] Existing tests still pass
- [ ] GPS writes work when configured
- [ ] GPS writes skipped when not configured

---

## Benefits of Simplification

### API Simplicity
**Before**: 7 parameters
**After**: 4 parameters

**Reduction**: 43% fewer parameters

### Single Source of Truth
**Before**: GPS sensor indices passed at call site AND stored in config
**After**: GPS sensor indices ONLY in config (one place)

### Error Prevention
**Before**: Caller could pass wrong indices that don't match config
**After**: Impossible to pass wrong indices (read from config)

### Consistency
**Before**: Different callers might pass different GPS sensor indices
**After**: All callers use same GPS sensors (from config)

---

## Migration Impact

### Breaking Change

**Yes** - This removes parameters from public API function

**Affected**:
- Any code calling `imx_write_event_with_gps()` directly
- Currently only 1 caller: `hal_event.c`

**Migration**:
```c
// Old call:
imx_write_event_with_gps(source, csb, csd, value, 2, 3, 19);

// New call:
imx_write_event_with_gps(source, csb, csd, value);

// GPS sensors 2, 3, 19 must now be configured via:
imx_init_gps_config_for_source(source, csb_array, csd_array, no_sensors, 2, 3, 19);
```

### Non-Breaking Alternative

If we want to maintain backward compatibility, we could:

**Option A**: Keep both versions
```c
/* New simplified version */
imx_result_t imx_write_event_with_gps(upload_source, csb, csd, value);

/* Legacy version for compatibility */
imx_result_t imx_write_event_with_gps_ex(upload_source, csb, csd, value,
                                         lat, lon, speed);  /* Override config */
```

**Option B**: Make parameters optional (not possible in C)

**Recommendation**: **Just remove the parameters** since there's only 1 caller and it's internal code we control.

---

## Detailed Code Changes

### Change 1: mm2_api.h Signature

**Location**: Lines 151-164

**Remove**:
```c
    uint16_t lat_sensor_entry,
    uint16_t lon_sensor_entry,
    uint16_t speed_sensor_entry
```

**Result**:
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value
);
```

---

### Change 2: mm2_write.c Implementation

**Location**: Lines 398-485

**Current**:
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value,
    uint16_t lat_sensor_entry,
    uint16_t lon_sensor_entry,
    uint16_t speed_sensor_entry)
{
    // ... write primary event ...

    /* Get GPS configuration */
    gps_source_config_t* gps_config = &g_gps_config[upload_source];

    if (gps_config->csb_array == NULL) {
        return IMX_SUCCESS;
    }

    /* Use PARAMETERS for sensor indices */
    if (lat_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
        lat_sensor_entry < gps_config->no_sensors) {
        // Write latitude using lat_sensor_entry parameter
    }
}
```

**New**:
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value)
{
    // ... write primary event ...

    /* Get GPS configuration */
    gps_source_config_t* gps_config = &g_gps_config[upload_source];

    if (gps_config->csb_array == NULL) {
        return IMX_SUCCESS;
    }

    /* Use CONFIG for sensor indices */
    if (gps_config->lat_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
        gps_config->lat_sensor_entry < gps_config->no_sensors) {
        // Write latitude using gps_config->lat_sensor_entry
        imx_write_evt(upload_source,
                      &gps_config->csb_array[gps_config->lat_sensor_entry],
                      &gps_config->csd_array[gps_config->lat_sensor_entry],
                      lat_data,
                      event_time);
    }

    /* Same for longitude and speed */
}
```

---

### Change 3: hal_event.c Caller

**Location**: Lines 224-232

**Current**:
```c
imx_write_event_with_gps(
    IMX_UPLOAD_CAN_DEVICE,
    &csb[entry],
    &csd[entry],
    csd[entry].last_raw_value,
    IMX_INVALID_SENSOR_ENTRY,  // ← REMOVE
    IMX_INVALID_SENSOR_ENTRY,  // ← REMOVE
    IMX_INVALID_SENSOR_ENTRY   // ← REMOVE
);
```

**New**:
```c
imx_write_event_with_gps(
    IMX_UPLOAD_CAN_DEVICE,
    &csb[entry],
    &csd[entry],
    csd[entry].last_raw_value
);
```

---

### Change 4: Documentation Updates

**File**: `mm2_api.h` (lines 127-154)

**Update**:
- Remove parameter descriptions for lat/lon/speed
- Add note about configuration requirement
- Add reference to `imx_init_gps_config_for_source()`

**Example**:
```c
/**
 * @brief Write event with GPS location using synchronized timestamp
 *
 * GPS sensor indices (latitude, longitude, speed) are retrieved from the
 * configuration set by imx_init_gps_config_for_source() for the specified
 * upload source.
 *
 * If GPS is not configured for the upload source, only the primary event
 * is written (GPS sensor writes are skipped).
 *
 * USE CASES:
 * - Hard braking events with location context
 * - Collision/impact events with exact location
 * - Geofence violations with entry/exit coordinates
 * - Vehicle state changes (stopped, idle) with position
 *
 * @param upload_source Upload source (determines GPS config and CSB/CSD arrays)
 * @param event_csb Primary event sensor configuration
 * @param event_csd Primary event sensor data
 * @param event_value Primary event value
 * @return IMX_SUCCESS if event written, error code on failure
 *
 * @note GPS sensor indices must be configured via imx_init_gps_config_for_source()
 *       before calling this function. If not configured, GPS writes are skipped.
 *
 * @see imx_init_gps_config_for_source() - Configure GPS sensors per upload source
 */
```

---

## Code Search Required

### Find All Callers

**Command**:
```bash
grep -rn "imx_write_event_with_gps\s*(" --include="*.c" --include="*.h"
```

**Expected Results**:
1. `mm2_api.h` - Function declaration
2. `mm2_write.c` - Function implementation
3. `hal_event.c` - Function call (current only caller)
4. Documentation files - Examples (not real code)
5. Test files - If any test code exists

**Action for each**: Update to remove 3 parameters

---

## Testing Plan

### Unit Tests

**Test 1**: GPS Configured, Event with GPS
```c
// Setup
imx_init_gps_config_for_source(IMX_UPLOAD_GATEWAY, icb.i_scb, icb.i_sd, 46, 2, 3, 19);

// Execute
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[5], &csd[5], event_value);

// Verify
assert(event sensor has 1 sample);
assert(latitude sensor has 1 sample);
assert(longitude sensor has 1 sample);
assert(speed sensor has 1 sample);
assert(all timestamps match);
```

**Test 2**: GPS Not Configured
```c
// Setup - DON'T call init (g_gps_config remains NULL)

// Execute
imx_write_event_with_gps(IMX_UPLOAD_BLE_DEVICE, &csb[5], &csd[5], event_value);

// Verify
assert(event sensor has 1 sample);
assert(GPS sensors unchanged);  // No GPS writes
```

**Test 3**: Partial GPS Configuration
```c
// Setup - only latitude, no longitude/speed
imx_init_gps_config_for_source(IMX_UPLOAD_GATEWAY, icb.i_scb, icb.i_sd, 46,
                                2,  /* lat */
                                IMX_INVALID_SENSOR_ENTRY,  /* no lon */
                                IMX_INVALID_SENSOR_ENTRY); /* no speed */

// Execute
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[5], &csd[5], event_value);

// Verify
assert(event sensor has 1 sample);
assert(latitude sensor has 1 sample);
assert(longitude sensor unchanged);
assert(speed sensor unchanged);
```

---

## Implementation Order

### Phase 1: Code Changes (30 minutes)
1. Update `mm2_api.h` signature
2. Update `mm2_write.c` implementation
3. Update `hal_event.c` caller
4. Update documentation

### Phase 2: Build and Test (15 minutes)
5. Compile code - verify no errors
6. Run existing tests - verify no regressions
7. Test with GPS configured
8. Test with GPS not configured

### Phase 3: Documentation (15 minutes)
9. Update code comments
10. Update API documentation
11. Update examples in docs
12. Create migration guide

**Total Estimated Time**: 1 hour

---

## Risks and Mitigation

### Risk 1: Breaking External Callers

**Likelihood**: LOW - only 1 known caller (internal)

**Mitigation**:
- Search entire codebase for callers
- Update all found callers
- Grep test to confirm none missed

### Risk 2: Tests Calling Old Signature

**Likelihood**: MEDIUM - test code might call directly

**Mitigation**:
- Search test files for function calls
- Update test code signatures
- Run full test suite

### Risk 3: Documentation Examples

**Likelihood**: HIGH - docs contain code examples

**Mitigation**:
- Update all code examples in markdown files
- Mark old examples as deprecated

---

## Expected Outcomes

### Before Simplification
```c
/* Hard to use - must pass GPS indices every time */
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[i], &csd[i], value, 2, 3, 19);
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[j], &csd[j], value, 2, 3, 19);
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[k], &csd[k], value, 2, 3, 19);
/* What if someone types wrong index? Bug! */
```

### After Simplification
```c
/* Configure once at startup */
imx_init_gps_config_for_source(IMX_UPLOAD_GATEWAY, icb.i_scb, icb.i_sd, 46, 2, 3, 19);

/* Use everywhere - simple and safe */
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[i], &csd[i], value);
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[j], &csd[j], value);
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY, &csb[k], &csd[k], value);
/* GPS sensors always correct - from config */
```

---

## Conclusion

**Recommendation**: **Proceed with simplification**

**Reason**:
- Only 1 known caller (we control it)
- Significantly improves API usability
- Reduces error potential
- Aligns with "configure once, use many" pattern

**Timeline**: 1 hour implementation + testing

**Risk**: LOW - internal change, well-isolated

---

*Plan Created: 2025-10-16*
*Estimated Effort: 1 hour*
*Recommendation: PROCEED*
