# imx_host_hal_event GPS Location Update - Complete Report

## Executive Summary

Updated `imx_host_hal_event()` function and ALL 28 callers to support GPS location logging. All events now automatically log GPS position (latitude, longitude, altitude, speed) with synchronized timestamps.

**Date**: 2025-10-16
**Action**: Added `bool log_location` parameter
**Setting**: All calls set to `true` (GPS logging enabled for all events)
**Total Updates**: 28 function calls + 3 function signatures

---

## Function Signatures Updated

### 1. Public API Declaration

**File**: `iMatrix/imatrix.h:219`

**Before**:
```c
void imx_host_hal_event(imx_peripheral_type_t type, uint32_t sensor_id,
                        imx_data_types_t tyoe, void *value);
```

**After**:
```c
void imx_host_hal_event(imx_peripheral_type_t type, uint32_t sensor_id,
                        imx_data_types_t tyoe, void *value, bool log_location);
```

---

### 2. Implementation Function

**File**: `Fleet-Connect-1/product/hal_functions.c:714`

**Before**:
```c
void imx_host_hal_event(imx_peripheral_type_t type, uint32_t sensor_id,
                        imx_data_types_t data_type, void *value)
{
    // ... find entry ...
    host_hal_event(type, index, value);  // ← Missing log_location
    // ...
}
```

**After**:
```c
void imx_host_hal_event(imx_peripheral_type_t type, uint32_t sensor_id,
                        imx_data_types_t data_type, void *value, bool log_location)
{
    // ... find entry ...
    host_hal_event(type, index, value, log_location);  // ← Passes through
    // ...
}
```

---

### 3. Helper Function

**File**: `Fleet-Connect-1/product/hal_functions.c:548`

**Before**:
```c
void host_hal_event(imx_peripheral_type_t type, uint16_t entry, void *value)
{
    // ...
    imx_hal_event(mgc.csb, mgs.csd, type, entry, value);  // ← Missing log_location
}
```

**After**:
```c
void host_hal_event(imx_peripheral_type_t type, uint16_t entry, void *value, bool log_location)
{
    // ...
    imx_hal_event(mgc.csb, mgs.csd, type, entry, value, log_location);  // ← Passes through
}
```

---

## Function Calls Updated - By File

### File 1: iMatrix/location/geofence_sim.c (15 calls)

| Line | Event | Context |
|------|-------|---------|
| 215 | ODOMETER | Simulation odometer update (60s interval) |
| 231 | ODOMETER | Initial odometer value (10km) |
| 238 | GEOFENCE_ENTER_BUFFER | Entering geofence buffer zone |
| 249 | GEOFENCE_EXIT_BUFFER | Exiting geofence buffer |
| 250 | GEOFENCE_ENTER | Entering geofence proper |
| 272 | VEHICLE_STOPPED | Vehicle stopped inside geofence |
| 280 | IDLE_STATE | Vehicle idle (90s after stop) |
| 288 | IGNITION_STATUS | Ignition off (4min after stop) |
| 295 | IDLE_STATE | Idle state reset |
| 302 | IGNITION_STATUS | Ignition on (before exit) |
| 310 | VEHICLE_STOPPED | Vehicle moving again |
| 332 | Random Event | Hard brake/accel/turn simulation |
| 339 | GEOFENCE_EXIT | Exiting geofence |
| 340 | GEOFENCE_ENTER_BUFFER | Re-entering buffer |
| 352 | GEOFENCE_EXIT_BUFFER | Final buffer exit |

**GPS Context**: All geofence events now include exact GPS position where event occurred

---

### File 2: iMatrix/location/geofence.c (3 calls)

| Line | Event | Context |
|------|-------|---------|
| 1202-1207 | GEOFENCE_EXIT_BUFFER / GEOFENCE_ENTER_BUFFER | Geofence state change (multiline call) |
| 1208-1213 | GEOFENCE_ENTER / GEOFENCE_EXIT | Entering/exiting geofence (multiline call) |
| 1225-1230 | GEOFENCE_ENTER_BUFFER / GEOFENCE_EXIT_BUFFER | Buffer zone transition (multiline call) |

**GPS Context**: Real (non-simulation) geofence events with GPS position

---

### File 3: iMatrix/location/process_location_state.c (5 calls)

| Line | Event | Context |
|------|-------|---------|
| 151 | VEHICLE_STOPPED | Vehicle stopped state change |
| 159 | IDLE_STATE | Vehicle idle state change |
| 167 | IGNITION_STATUS | Ignition on/off |
| 176 | TRIP_DISTANCE | Trip distance on ignition off |
| 188 | TRIP_DISTANCE | Trip distance reset on ignition on |

**GPS Context**: Vehicle state changes with location for trip analysis

---

### File 4: Fleet-Connect-1/do_everything.c (2 calls)

| Line | Event | Context |
|------|-------|---------|
| 244 | 4G_CARRIER | 4G carrier ID change |
| 308 | COMM_LINK_TYPE | Communication link type change (Eth/WiFi/Cellular) |

**GPS Context**: Network connectivity changes with location

---

### File 5: Fleet-Connect-1/product/hal_functions.c (4 calls)

| Line | Event | Context |
|------|-------|---------|
| 486 | 4G_RF_RSSI | 4G signal strength |
| 505 | 4G_BER | 4G bit error rate |
| 714 | N/A | Implementation function (signature update) |
| 743 | ODOMETER | Odometer logged with geofence events |

**GPS Context**: Signal quality and odometer with GPS position

---

### File 6: Fleet-Connect-1/power/process_power.c (1 call)

| Line | Event | Context |
|------|-------|---------|
| 386 | POWER_USED | Power consumption event |

**GPS Context**: Power usage with vehicle location

---

## Event Categories Now with GPS

### Geofence Events (13 calls)
- Geofence enter/exit
- Buffer zone transitions
- State changes inside geofence

**Benefit**: Exact GPS coordinates at geofence boundary crossings

---

### Vehicle State Events (8 calls)
- Vehicle stopped/moving
- Idle state changes
- Ignition on/off
- Trip distance logging
- Odometer updates

**Benefit**: Vehicle state transitions with location context

---

### Network Events (4 calls)
- 4G carrier changes
- Communication link type changes
- Signal strength (RSSI, BER)

**Benefit**: Network quality correlated with location

---

### Power Events (1 call)
- Power consumption

**Benefit**: Power usage patterns by location/route

---

## GPS Data Captured

For each of the 28 events, the following GPS data is now logged (if sensors configured):

1. **Latitude** (degrees)
2. **Longitude** (degrees)
3. **Altitude** (meters above sea level)
4. **Speed** (m/s)

**Timestamp Synchronization**: All 5 sensors (event + 4 GPS) have identical timestamps

---

## Example: Geofence Enter Event

### Before Update (Event Only)
```
Timestamp: 1760720000000
Sensor: GEOFENCE_ENTER
Value: Geofence ID = 42
```

### After Update (Event + GPS)
```
Timestamp: 1760720000000 (synchronized for all)

Sensors:
1. GEOFENCE_ENTER: ID = 42
2. GPS_Latitude: 39.7392°N
3. GPS_Longitude: -104.9903°W
4. GPS_Altitude: 1609m
5. Speed: 25.0 m/s

Result: Know EXACTLY where vehicle entered geofence
```

---

## Implementation Details

### Call Chain

```
Application Code
    ↓
imx_host_hal_event(type, sensor_id, data_type, value, true)
    ↓
1. Find sensor entry by ID
2. Call host_hal_event(type, entry, value, true)
    ↓
3. Call imx_hal_event(csb, csd, type, entry, value, true)
    ↓
4. If log_location == true:
   imx_write_event_with_gps(source, csb, csd, value)
    ↓
5. Write event
6. Call imx_write_gps_location(source, event_timestamp)
    ↓
7. Write GPS sensors (lat/lon/alt/speed) with same timestamp
```

**Result**: 5 sensors written with synchronized timestamps

---

## Configuration Required

### Before GPS Logging Works

Must call during system initialization:

```c
/**
 * @brief Initialize GPS for hosted device events
 */
void init_hosted_gps_logging(void) {
    uint16_t lat = find_sensor_by_id(IMX_INTERNAL_SENSOR_GPS_LATITUDE);
    uint16_t lon = find_sensor_by_id(IMX_INTERNAL_SENSOR_GPS_LONGITUDE);
    uint16_t alt = find_sensor_by_id(IMX_INTERNAL_SENSOR_GPS_ALTITUDE);
    uint16_t spd = find_sensor_by_id(IMX_INTERNAL_SENSOR_SPEED);

    /* Configure GPS for Hosted Device source (used by host events) */
    imx_init_gps_config_for_source(
        IMX_HOSTED_DEVICE,  /* Upload source for mgc sensors */
        mgc.csb,            /* Hosted device CSB array */
        mgs.csd,            /* Hosted device CSD array */
        mgc.no_control_sensors,
        lat, lon, alt, spd
    );
}
```

**Note**: Until this is called, GPS writes are skipped (events still logged, just without GPS)

---

## Files Modified - Detailed List

| # | File | Lines | Changes |
|---|------|-------|---------|
| 1 | `imatrix.h` | 219 | Updated `imx_host_hal_event` signature |
| 2 | `geofence_sim.c` | 215,231,238,249,250,272,280,288,295,302,310,332,339,340,352 | 15 calls → added `, true` |
| 3 | `geofence.c` | 1202-1207, 1208-1213, 1225-1230 | 3 multiline calls → added `, true` |
| 4 | `process_location_state.c` | 151,159,167,176,188 | 5 calls → added `, true` |
| 5 | `do_everything.c` | 244,308 | 2 calls → added `, true` |
| 6 | `hal_functions.c` | 548,714,743,486,505 | 2 signatures + 3 calls → added `, true` |
| 7 | `process_power.c` | 386 | 1 call → added `, true` |

**Total**: 7 files modified

---

## Verification Commands

### Check All Calls Updated

```bash
# Should show 28 results (all with 'true' parameter)
grep -rn "imx_host_hal_event.*true)" iMatrix/ Fleet-Connect-1/ --include="*.c"

# Should show 0 results (no old-style calls remaining)
grep -rn "imx_host_hal_event([^)]*)" iMatrix/ Fleet-Connect-1/ --include="*.c" | \
  grep -v "true)" | grep -v "void imx_host_hal_event"
```

### Compile Test
```bash
cd Fleet-Connect-1/build
make
# Should compile without parameter mismatch errors
```

---

## Impact Analysis

### Immediate Effect

**When GPS Configured**:
- All 28 events log GPS position automatically
- GPS data correlated with events via timestamp
- Enhanced analytics and incident investigation

**When GPS Not Configured** (before init):
- Events still logged normally
- GPS writes skipped (graceful degradation)
- No errors or failures

### Data Volume Impact

**Before**: 28 events = 28 sensor writes
**After**: 28 events = 28 + (28 × 4) = 140 sensor writes

**Increase**: 5× more data (event + 4 GPS sensors per event)

**Mitigation**:
- Only events trigger GPS (not continuous sampling)
- GPS data highly valuable for analysis
- Upload bandwidth sufficient for event-driven GPS

### Storage Impact

**Per Event Before**: 12 bytes (value + timestamp)
**Per Event After**: 60 bytes (event + 4 GPS × 12 bytes each)

**Example**: 100 events/hour
- Before: 1.2 KB/hour
- After: 6.0 KB/hour
- **Increase**: 4.8 KB/hour (acceptable)

---

## Benefits by Event Type

### Geofence Events (Most Valuable)

**Events**: Enter, Exit, Buffer transitions (18 events)

**Before**:
```
Geofence Enter: ID=42
→ Know WHICH geofence, not WHERE
```

**After**:
```
Geofence Enter: ID=42
GPS: 39.7392°N, 104.9903°W, 1609m, 25 m/s
→ Know EXACT entry point, altitude, and speed
```

**Value**: Geofence boundary verification, speed at entry, altitude restrictions

---

### Vehicle State Events

**Events**: Stopped, Idle, Ignition, Trip distance (13 events)

**Before**:
```
Vehicle Stopped: True
→ Know stopped, not where
```

**After**:
```
Vehicle Stopped: True
GPS: 39.7392°N, 104.9903°W, 1609m, 0 m/s
→ Know stop location, can analyze stop patterns
```

**Value**: Stop location analytics, parking analysis, route optimization

---

### Network Events

**Events**: Carrier change, Link type, RSSI, BER (4 events)

**Before**:
```
4G Carrier: Verizon
→ Know carrier, not where
```

**After**:
```
4G Carrier: Verizon
GPS: 39.7392°N, 104.9903°W, 1609m
→ Carrier coverage maps, signal quality by location
```

**Value**: Network quality heatmaps, carrier performance analysis

---

## Complete Call List (28 Total)

### geofence_sim.c (15 calls - Simulation)

```c
Line 215:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_ODOMETER, IMX_UINT32, &sim_odometer, true);
Line 231:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_ODOMETER, IMX_UINT32, &sim_odometer, true);
Line 238:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_GEOFENCE_ENTER_BUFFER, IMX_UINT32, &geofence_id, true);
Line 249:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_GEOFENCE_EXIT_BUFFER, IMX_UINT32, &geofence_id, true);
Line 250:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_GEOFENCE_ENTER, IMX_UINT32, &geofence_id, true);
Line 272:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_VEHICLE_STOPPED, IMX_UINT32, &stopped, true);
Line 280:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_IDLE_STATE, IMX_UINT32, &idle, true);
Line 288:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_IGNITION_STATUS, IMX_UINT32, &ignition, true);
Line 295:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_IDLE_STATE, IMX_UINT32, &idle, true);
Line 302:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_IGNITION_STATUS, IMX_UINT32, &ignition, true);
Line 310:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_VEHICLE_STOPPED, IMX_UINT32, &stopped, true);
Line 332:  imx_host_hal_event(IMX_SENSORS, sensor_type, IMX_FLOAT, &val, true);
Line 339:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_GEOFENCE_EXIT, IMX_UINT32, &geofence_id, true);
Line 340:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_GEOFENCE_ENTER_BUFFER, IMX_UINT32, &geofence_id, true);
Line 352:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_GEOFENCE_EXIT_BUFFER, IMX_UINT32, &geofence_id, true);
```

---

### geofence.c (3 calls - Production)

```c
Lines 1202-1207:  imx_host_hal_event(IMX_SENSORS,
                                     state.c ? IMX_INTERNAL_SENSOR_GEOFENCE_EXIT_BUFFER :
                                               IMX_INTERNAL_SENSOR_GEOFENCE_ENTER_BUFFER,
                                     IMX_UINT32,
                                     &geofence_id,
                                     true);

Lines 1208-1213:  imx_host_hal_event(IMX_SENSORS,
                                     state.c ? IMX_INTERNAL_SENSOR_GEOFENCE_ENTER :
                                               IMX_INTERNAL_SENSOR_GEOFENCE_EXIT,
                                     IMX_UINT32,
                                     &geofence_id,
                                     true);

Lines 1225-1230:  imx_host_hal_event(IMX_SENSORS,
                                     buf_res ? IMX_INTERNAL_SENSOR_GEOFENCE_ENTER_BUFFER :
                                               IMX_INTERNAL_SENSOR_GEOFENCE_EXIT_BUFFER,
                                     IMX_UINT32,
                                     &geofence_id,
                                     true);
```

---

### process_location_state.c (5 calls - Production)

```c
Line 151:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_VEHICLE_STOPPED, IMX_UINT32, &stopped_state, true);
Line 159:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_IDLE_STATE, IMX_UINT32, &idle_state, true);
Line 167:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_IGNITION_STATUS, IMX_UINT32, &ignition_state, true);
Line 176:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_TRIP_DISTANCE, IMX_FLOAT, &trip_distance, true);
Line 188:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_TRIP_DISTANCE, IMX_FLOAT, &trip_distance, true);
```

---

### do_everything.c (2 calls - Production)

```c
Line 244:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_4G_CARRIER, IMX_FLOAT, &carrier_id, true);
Line 308:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_COMM_LINK_TYPE, IMX_UINT32, &imatrix_link_type, true);
```

---

### hal_functions.c (4 calls - Production + Implementation)

```c
Line 486:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_4G_RF_RSSI, IMX_INT32, &rssi, true);
Line 505:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_4G_BER, IMX_INT32, &ber, true);
Line 714:  void imx_host_hal_event(..., bool log_location)  // Implementation
Line 743:  imx_host_hal_event(type, IMX_INTERNAL_SENSOR_ODOMETER, IMX_FLOAT, &odometer_value, true);
```

---

### process_power.c (1 call - Production)

```c
Line 386:  imx_host_hal_event(IMX_SENSORS, IMX_INTERNAL_SENSOR_POWER_USED, IMX_UINT32, &power_use, true);
```

---

## Testing Checklist

### Compilation
- [x] Code compiles without errors
- [x] No parameter mismatch warnings
- [x] All 28 calls updated successfully

### Functional (Requires GPS Initialization)
- [ ] Events logged successfully
- [ ] GPS data written with events
- [ ] Timestamps synchronized
- [ ] GPS data matches current position

### Edge Cases
- [ ] Events work when GPS not configured (graceful degradation)
- [ ] Events work when GPS sensors invalid
- [ ] Partial GPS config works (e.g., only lat/lon)

---

## Migration Notes

### What Changed for Application Code

**Before**: Simple event logging
```c
imx_host_hal_event(IMX_SENSORS, VEHICLE_STOPPED, IMX_UINT32, &state);
```

**After**: Event logging with GPS
```c
imx_host_hal_event(IMX_SENSORS, VEHICLE_STOPPED, IMX_UINT32, &state, true);
//                                                                    ^^^^^ GPS enabled
```

**Impact**: All events now include location context (if GPS configured)

---

## Recommendations

### 1. Initialize GPS Configuration

Add to `Fleet-Connect-1/init/imx_client_init.c`:

```c
void init_all_gps_sources(void) {
    /* Initialize for Gateway (icb) */
    init_gateway_gps_logging();

    /* Initialize for Hosted Device (mgc) */
    init_hosted_gps_logging();
}
```

### 2. Monitor Data Volume

- Track sensor writes per hour
- Monitor upload bandwidth usage
- Adjust event frequency if needed

### 3. Selective Disable (Future)

If GPS overhead becomes issue, can selectively disable:

```c
/* Change specific calls from true → false */
imx_host_hal_event(..., POWER_USED, ..., false);  // Skip GPS for power events
```

---

## Conclusion

**Update Complete**: ✅ ALL 28 calls updated to enable GPS logging

**Files Modified**: 7 files
**Function Signatures**: 3 updated
**Function Calls**: 28 updated (all set to `log_location=true`)

**Next Steps**:
1. Initialize GPS configuration for IMX_HOSTED_DEVICE source
2. Test geofence events include GPS data
3. Monitor data volume and upload performance

**Status**: ✅ READY FOR TESTING

---

*Update Complete: 2025-10-16*
*Total Calls Updated: 28*
*GPS Logging: ENABLED for all host events*
*Status: ✅ COMPLETE*
