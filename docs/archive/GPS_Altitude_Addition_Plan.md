# GPS Altitude Addition Plan - Ultra-Detailed Analysis

## Current State Analysis

### Existing GPS Data Points (3)
Currently, `imx_write_event_with_gps()` writes:
1. **Latitude** - Retrieved via `imx_get_latitude()` → degrees
2. **Longitude** - Retrieved via `imx_get_longitude()` → degrees
3. **Speed** - Retrieved via `imx_get_speed()` → m/s

### Missing GPS Data Point
4. **Altitude/Elevation** - NOT currently written, but:
   - ✅ `imx_get_altitude()` function exists
   - ✅ Altitude sensor defined: `IMX_INTERNAL_SENSOR_GPS_ALTITUDE` (ID: 4)
   - ✅ Altitude tracked in `icb.gps_altitude` (float, meters)

---

## Critical Questions

### Question 1: Terminology - "Altitude" vs "Elevation"

**System uses BOTH terms**:
- **Altitude**: Used in sensor name (`GPS_Altitude`), API function (`imx_get_altitude()`), data structure (`icb.gps_altitude`)
- **Elevation**: Used in satellite data structures (satellite elevation angle), some configs

**Question**: Which term should we use for the GPS height above sea level?

**Recommendation**: Use **"Altitude"** for consistency with:
- Existing sensor: `IMX_INTERNAL_SENSOR_GPS_ALTITUDE`
- Existing function: `imx_get_altitude()`
- GPS terminology standard: "Altitude" for height above sea level

**Elevation** typically means satellite angle in GPS context.

**Proposed**: Add `altitude_sensor_entry` (not `elevation_sensor_entry`)

---

### Question 2: Should Altitude Be Optional or Always Included?

**Option A - Optional (Separate from Lat/Lon/Speed)**:
```c
typedef struct {
    uint16_t lat_sensor_entry;
    uint16_t lon_sensor_entry;
    uint16_t speed_sensor_entry;
    uint16_t altitude_sensor_entry;  /* NEW - can be IMX_INVALID_SENSOR_ENTRY */
} gps_source_config_t;
```
**Pros**: Flexible, can omit if altitude not needed
**Cons**: More complexity

**Option B - Always Included with Lat/Lon**:
```c
/* Treat altitude as essential GPS coordinate (like lat/lon) */
```
**Pros**: Complete GPS position = lat/lon/altitude
**Cons**: Less flexible

**Question**: Should altitude be optional or required when GPS logging enabled?

**Recommendation**: **Optional** - Same pattern as speed. Some use cases may not need altitude (flat terrain, 2D mapping).

---

### Question 3: Parameter Naming Convention

Current GPS config has:
- `lat_sensor_entry`
- `lon_sensor_entry`
- `speed_sensor_entry`

**Options for altitude**:
- **A**: `altitude_sensor_entry` (full word, matches `imx_get_altitude()`)
- **B**: `alt_sensor_entry` (abbreviated, matches some GPS specs)
- **C**: `elevation_sensor_entry` (matches satellite terminology)

**Question**: Which naming convention?

**Recommendation**: **`altitude_sensor_entry`** - Matches existing `imx_get_altitude()` function and GPS sensor name.

---

### Question 4: Integration Order in Structure

**Current order**:
```c
typedef struct {
    uint16_t lat_sensor_entry;
    uint16_t lon_sensor_entry;
    uint16_t speed_sensor_entry;
} gps_source_config_t;
```

**Where to add altitude**?

**Option A - After speed (current order)**:
```c
uint16_t lat_sensor_entry;
uint16_t lon_sensor_entry;
uint16_t speed_sensor_entry;
uint16_t altitude_sensor_entry;  /* NEW */
```

**Option B - After lon, before speed (logical GPS coordinates grouping)**:
```c
uint16_t lat_sensor_entry;
uint16_t lon_sensor_entry;
uint16_t altitude_sensor_entry;  /* NEW - completes 3D position */
uint16_t speed_sensor_entry;     /* Separate from position */
```

**Question**: Where should altitude appear in the structure?

**Recommendation**: **Option B** - Altitude completes the 3D position (lat, lon, alt). Speed is motion data, separate concept.

---

### Question 5: Function Signature Update

**Current**:
```c
imx_result_t imx_init_gps_config_for_source(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb_array,
    control_sensor_data_t* csd_array,
    uint16_t no_sensors,
    uint16_t lat_entry,
    uint16_t lon_entry,
    uint16_t speed_entry
);
```

**Proposed**:
```c
imx_result_t imx_init_gps_config_for_source(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb_array,
    control_sensor_data_t* csd_array,
    uint16_t no_sensors,
    uint16_t lat_entry,
    uint16_t lon_entry,
    uint16_t altitude_entry,  /* NEW */
    uint16_t speed_entry
);
```

**Question**: Is this parameter order acceptable? (Altitude between lon and speed)

**Alternative - At end for backward compat**:
```c
    uint16_t lat_entry,
    uint16_t lon_entry,
    uint16_t speed_entry,
    uint16_t altitude_entry  /* NEW - at end */
```

**Recommendation**: **Between lon and speed** - Logical grouping (3D position, then motion). Since function is brand new (no existing callers in production yet), we can use logical order.

---

## Proposed Implementation Plan

### Phase 1: Update GPS Configuration Structure

**File**: `mm2_write.c` (lines 83-90)

**Current**:
```c
typedef struct {
    imx_control_sensor_block_t* csb_array;
    control_sensor_data_t* csd_array;
    uint16_t lat_sensor_entry;
    uint16_t lon_sensor_entry;
    uint16_t speed_sensor_entry;
    uint16_t no_sensors;
} gps_source_config_t;
```

**Proposed**:
```c
typedef struct {
    imx_control_sensor_block_t* csb_array;
    control_sensor_data_t* csd_array;
    uint16_t lat_sensor_entry;         /* Latitude (degrees) */
    uint16_t lon_sensor_entry;         /* Longitude (degrees) */
    uint16_t altitude_sensor_entry;    /* NEW: Altitude/height above sea level (meters) */
    uint16_t speed_sensor_entry;       /* Speed/velocity (m/s) */
    uint16_t no_sensors;
} gps_source_config_t;
```

---

### Phase 2: Update Initialization Array

**File**: `mm2_write.c` (lines 95-103)

**Current**:
```c
static gps_source_config_t g_gps_config[IMX_UPLOAD_NO_SOURCES] = {
    [IMX_UPLOAD_GATEWAY] = {NULL, NULL, IMX_INVALID_SENSOR_ENTRY, IMX_INVALID_SENSOR_ENTRY, IMX_INVALID_SENSOR_ENTRY, 0},
    // ...
};
```

**Proposed**:
```c
static gps_source_config_t g_gps_config[IMX_UPLOAD_NO_SOURCES] = {
    [IMX_UPLOAD_GATEWAY] = {
        .csb_array = NULL,
        .csd_array = NULL,
        .lat_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .lon_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .altitude_sensor_entry = IMX_INVALID_SENSOR_ENTRY,  /* NEW */
        .speed_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .no_sensors = 0
    },
    [IMX_HOSTED_DEVICE] = {
        .csb_array = NULL,
        .csd_array = NULL,
        .lat_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .lon_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .altitude_sensor_entry = IMX_INVALID_SENSOR_ENTRY,  /* NEW */
        .speed_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .no_sensors = 0
    },
    [IMX_UPLOAD_BLE_DEVICE] = {
        .csb_array = NULL,
        .csd_array = NULL,
        .lat_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .lon_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .altitude_sensor_entry = IMX_INVALID_SENSOR_ENTRY,  /* NEW */
        .speed_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .no_sensors = 0
    },
#ifdef CAN_PLATFORM
    [IMX_UPLOAD_CAN_DEVICE] = {
        .csb_array = NULL,
        .csd_array = NULL,
        .lat_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .lon_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .altitude_sensor_entry = IMX_INVALID_SENSOR_ENTRY,  /* NEW */
        .speed_sensor_entry = IMX_INVALID_SENSOR_ENTRY,
        .no_sensors = 0
    },
#endif
};
```

**Note**: Using designated initializers for clarity

---

### Phase 3: Update Initialization Function

**File**: `mm2_write.c` (lines 120-144), `mm2_api.h` (lines 561-567)

**Current Signature**:
```c
imx_result_t imx_init_gps_config_for_source(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb_array,
    control_sensor_data_t* csd_array,
    uint16_t no_sensors,
    uint16_t lat_entry,
    uint16_t lon_entry,
    uint16_t speed_entry
);
```

**Proposed Signature**:
```c
imx_result_t imx_init_gps_config_for_source(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb_array,
    control_sensor_data_t* csd_array,
    uint16_t no_sensors,
    uint16_t lat_entry,
    uint16_t lon_entry,
    uint16_t altitude_entry,  /* NEW - between lon and speed (3D position) */
    uint16_t speed_entry
);
```

**Implementation Update**:
```c
imx_result_t imx_init_gps_config_for_source(..., uint16_t altitude_entry, ...) {
    // ... existing validation ...

    g_gps_config[upload_source].csb_array = csb_array;
    g_gps_config[upload_source].csd_array = csd_array;
    g_gps_config[upload_source].lat_sensor_entry = lat_entry;
    g_gps_config[upload_source].lon_sensor_entry = lon_entry;
    g_gps_config[upload_source].altitude_sensor_entry = altitude_entry;  /* NEW */
    g_gps_config[upload_source].speed_sensor_entry = speed_entry;
    g_gps_config[upload_source].no_sensors = no_sensors;

    return IMX_SUCCESS;
}
```

---

### Phase 4: Update imx_write_event_with_gps() Implementation

**File**: `mm2_write.c` (lines 430-482)

**Current Code**:
```c
/* Get current GPS location and speed */
float latitude = imx_get_latitude();
float longitude = imx_get_longitude();
float speed_ms = imx_get_speed();

/* Write latitude, longitude, speed... */
```

**Proposed Code**:
```c
/* Get current GPS location, altitude, and speed */
float latitude = imx_get_latitude();
float longitude = imx_get_longitude();
float altitude = imx_get_altitude();    /* NEW */
float speed_ms = imx_get_speed();

/* Write latitude */
if (gps_config->lat_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
    gps_config->lat_sensor_entry < gps_config->no_sensors) {
    // ... existing latitude write ...
}

/* Write longitude */
if (gps_config->lon_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
    gps_config->lon_sensor_entry < gps_config->no_sensors) {
    // ... existing longitude write ...
}

/* Write altitude - NEW */
if (gps_config->altitude_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
    gps_config->altitude_sensor_entry < gps_config->no_sensors) {

    imx_data_32_t alt_data;
    alt_data.float_32bit = altitude;

    imx_write_evt(upload_source,
                  &gps_config->csb_array[gps_config->altitude_sensor_entry],
                  &gps_config->csd_array[gps_config->altitude_sensor_entry],
                  alt_data,
                  event_time);  /* SAME timestamp as primary event */
}

/* Write speed */
if (gps_config->speed_sensor_entry != IMX_INVALID_SENSOR_ENTRY &&
    gps_config->speed_sensor_entry < gps_config->no_sensors) {
    // ... existing speed write ...
}
```

**Location**: Insert after longitude write, before speed write

---

### Phase 5: Update Documentation

**Files to Update**:
1. `mm2_api.h` - Update `imx_write_event_with_gps()` documentation
2. `mm2_api.h` - Update `imx_init_gps_config_for_source()` documentation
3. `GPS_Event_Logging_System.md` - Add altitude to examples
4. `GPS_Simplification_Complete.md` - Update to show 4 GPS data points

**Documentation Changes**:

**Before**:
```c
/**
 * GPS data is retrieved at time of call using:
 * - imx_get_latitude()  → Latitude sensor (degrees)
 * - imx_get_longitude() → Longitude sensor (degrees)
 * - imx_get_speed()     → Speed sensor (m/s)
 */
```

**After**:
```c
/**
 * GPS data is retrieved at time of call using:
 * - imx_get_latitude()  → Latitude sensor (degrees)
 * - imx_get_longitude() → Longitude sensor (degrees)
 * - imx_get_altitude()  → Altitude sensor (meters above sea level)
 * - imx_get_speed()     → Speed sensor (m/s)
 */
```

---

## Implementation Details

### Structure Changes

**Before**:
```c
typedef struct {
    imx_control_sensor_block_t* csb_array;
    control_sensor_data_t* csd_array;
    uint16_t lat_sensor_entry;       // Index 0
    uint16_t lon_sensor_entry;       // Index 1
    uint16_t speed_sensor_entry;     // Index 2
    uint16_t no_sensors;             // Index 3
} gps_source_config_t;  // 4 members (excluding pointers)
```

**After**:
```c
typedef struct {
    imx_control_sensor_block_t* csb_array;
    control_sensor_data_t* csd_array;
    uint16_t lat_sensor_entry;       // Index 0
    uint16_t lon_sensor_entry;       // Index 1
    uint16_t altitude_sensor_entry;  // Index 2 - NEW
    uint16_t speed_sensor_entry;     // Index 3 (moved from 2)
    uint16_t no_sensors;             // Index 4 (moved from 3)
} gps_source_config_t;  // 5 members (excluding pointers)
```

**Memory Impact**: +2 bytes per upload source (uint16_t)
**Total Additional Memory**: 2 bytes × 4 sources = 8 bytes (negligible)

---

### Example Usage

**Initialization**:
```c
/* Find GPS sensor indices */
uint16_t lat_idx = find_sensor_by_id(IMX_INTERNAL_SENSOR_GPS_LATITUDE);    // ID: 2
uint16_t lon_idx = find_sensor_by_id(IMX_INTERNAL_SENSOR_GPS_LONGITUDE);   // ID: 3
uint16_t alt_idx = find_sensor_by_id(IMX_INTERNAL_SENSOR_GPS_ALTITUDE);    // ID: 4  ← NEW
uint16_t spd_idx = find_sensor_by_id(IMX_INTERNAL_SENSOR_SPEED);           // ID: 142

/* Configure GPS with altitude */
imx_init_gps_config_for_source(
    IMX_UPLOAD_GATEWAY,
    icb.i_scb,
    icb.i_sd,
    device_config.no_sensors,
    lat_idx,    // Latitude
    lon_idx,    // Longitude
    alt_idx,    // Altitude  ← NEW
    spd_idx     // Speed
);
```

**Runtime Behavior**:
```c
/* Hard braking event */
hal_event(IMX_SENSORS, HARD_BRAKING, &data, true);

/* Internally writes 5 sensors with synchronized timestamp:
 * 1. Hard braking event value
 * 2. Current latitude
 * 3. Current longitude
 * 4. Current altitude     ← NEW
 * 5. Current speed
 * All with SAME timestamp for perfect correlation
 */
```

---

## Use Cases for Altitude

### 1. Incident Context
**Scenario**: Hard braking on mountain road
```
Event: Hard braking (0.9g)
Location: 39.7392°N, 104.9903°W, 1609m altitude
Context: High altitude (Denver) - thinner air affects braking
```

### 2. Geofence Violations
**Scenario**: Unauthorized mining site entry
```
Event: Geofence entry
Location: 40.1234°N, 105.6789°W, 2800m altitude
Context: High-altitude restricted area
```

### 3. Vehicle Performance Analysis
**Scenario**: Engine performance monitoring
```
Event: Engine temperature warning
Location: 35.1234°N, 115.6789°W, 50m altitude (Death Valley)
Context: Low altitude, high temperature environment
```

### 4. Terrain Analysis
**Scenario**: Route optimization
```
Event: Route completion
Altitude profile: Start 100m → Peak 1500m → End 200m
Context: Significant elevation change affects fuel consumption
```

---

## Potential Issues and Solutions

### Issue 1: Altitude Sensor Might Not Exist

**Problem**: Some GPS modules don't provide altitude (2D fix)

**Solution**: Already handled - `altitude_sensor_entry = IMX_INVALID_SENSOR_ENTRY`
```c
if (gps_config->altitude_sensor_entry != IMX_INVALID_SENSOR_ENTRY) {
    // Write altitude
}
/* If invalid, altitude write is skipped - no problem */
```

### Issue 2: Altitude Might Be Inaccurate

**Problem**: GPS altitude less accurate than lat/lon

**Solution**: This is a data quality issue, not API issue. Caller decides if altitude is useful.

### Issue 3: Backward Compatibility

**Problem**: Existing init calls don't pass altitude parameter

**Solution**: This function was just added (no production callers yet), so we can change signature freely.

---

## Implementation Checklist

### Code Changes
- [ ] Update `gps_source_config_t` structure (add `altitude_sensor_entry`)
- [ ] Update static initialization array (add altitude field to all sources)
- [ ] Update `imx_init_gps_config_for_source()` signature (add `altitude_entry` param)
- [ ] Update `imx_init_gps_config_for_source()` body (store altitude entry)
- [ ] Update `imx_write_event_with_gps()` implementation (add altitude write block)
- [ ] Update `mm2_api.h` documentation (add altitude to function docs)
- [ ] Update `mm2_write.c` documentation (add altitude to comments)

### Documentation Updates
- [ ] Update `GPS_Event_Logging_System.md` - Add altitude to all examples
- [ ] Update `GPS_Simplification_Complete.md` - Show 4 GPS data points
- [ ] Update `mm2_api.h` - Altitude in API docs
- [ ] Add comments explaining altitude optional usage

### Testing
- [ ] Test with altitude configured
- [ ] Test with altitude = IMX_INVALID_SENSOR_ENTRY (skipped)
- [ ] Verify timestamp synchronization includes altitude
- [ ] Verify 3D position data (lat, lon, alt) all written

---

## Final Questions for Confirmation

Before implementing, please confirm:

1. **Terminology**: Use "altitude" (not "elevation") for GPS height? ✓ Recommended
2. **Optional**: Altitude is optional (can be IMX_INVALID_SENSOR_ENTRY)? ✓ Recommended
3. **Parameter Name**: `altitude_sensor_entry` (full word)? ✓ Recommended
4. **Structure Order**: lat, lon, altitude, speed (3D position, then motion)? ✓ Recommended
5. **Function Parameter Order**: Same as structure (altitude between lon and speed)? ✓ Recommended

**Alternative Consideration**: If you prefer altitude at END (after speed) for any reason, that's also acceptable.

---

## Summary

**Impact**: LOW - Clean addition, follows existing pattern exactly

**Complexity**: LOW - Copy/paste longitude block, change to altitude

**Risk**: MINIMAL - New field, doesn't affect existing GPS writes

**Estimated Time**: 30 minutes implementation + testing

**Recommendation**: **PROCEED** with altitude addition using proposed plan

---

*Plan Created: 2025-10-16*
*Status: READY FOR IMPLEMENTATION*
*Awaiting Confirmation on Questions 1-5*
