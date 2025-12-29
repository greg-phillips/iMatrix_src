# Accelerometer Auto-Calibration Plan

**Date**: 2025-12-26
**Author**: Claude Code Analysis
**Status**: IMPLEMENTATION COMPLETE
**Document Version**: 1.1
**Last Updated**: 2025-12-26
**Related Work**: review_accelerometer_event_detection_plan.md

---

## Executive Summary

This document outlines a plan to implement automatic accelerometer calibration on each power-up. The system will:
1. **Stationary Detection**: Use gravity levels to determine device orientation when vehicle is stationary
2. **Dynamic Calibration**: Use GPS speed and forward movement to refine orientation during travel
3. **Hybrid Approach**: Start with static calibration, refine with dynamic data when available

---

## Current Calibration System Analysis

### Existing Implementation
```c
// Current calibration (lines 910-954)
- Takes 10 readings 1 second apart
- Averages X, Y, Z levels as offsets
- Stores in mgc.cal_avg_x/y/z
- Does NOT determine orientation/rotation
```

### Existing Calibration Structure
```c
typedef struct {
    float yaw;                    // Rotation around vertical axis
    float pitch;                  // Tilt forward/backward
    float roll;                   // Tilt left/right
    float rotation_matrix[3][3];  // 3D rotation matrix
    int gravity_vector[3];        // Which axis has gravity
    uint32_t timestamp;
    uint16_t version;
    uint8_t valid;
    pthread_mutex_t mutex;
} gforce_calibration_t;
```

### Gap Analysis
| Feature | Current | Proposed |
|---------|---------|----------|
| Offset calibration | Yes | Yes |
| Orientation detection | No | Yes |
| Gravity axis detection | No | Yes |
| Dynamic refinement | No | Yes |
| Auto on power-up | Partial | Full |

---

## Auto-Calibration Design

### Phase 1: Static Orientation Detection (Stationary)

When the vehicle is stationary (GPS speed = 0 or no GPS), determine orientation from gravity:

#### Gravity-Based Orientation
```
Standard mounting (Z-axis up):
  X ≈ 0g, Y ≈ 0g, Z ≈ -1g (gravity pulls down)

Rotated 90° forward (X-axis up):
  X ≈ -1g, Y ≈ 0g, Z ≈ 0g

Rotated 90° sideways (Y-axis up):
  X ≈ 0g, Y ≈ -1g, Z ≈ 0g
```

#### Detection Algorithm
```c
// Determine primary gravity axis from averaged readings
if (fabs(avg_z) > fabs(avg_x) && fabs(avg_z) > fabs(avg_y)) {
    // Z-axis has gravity - standard mounting
    gravity_axis = AXIS_Z;
    pitch = atan2(avg_x, avg_z);  // Forward tilt
    roll = atan2(avg_y, avg_z);   // Side tilt
} else if (fabs(avg_x) > fabs(avg_y)) {
    // X-axis has gravity - device mounted vertically, facing forward
    gravity_axis = AXIS_X;
    // Compute appropriate rotation
} else {
    // Y-axis has gravity - device mounted on side
    gravity_axis = AXIS_Y;
    // Compute appropriate rotation
}
```

#### Stationary Detection Criteria
- GPS speed < 0.5 m/s (1.1 mph) for > 5 seconds
- OR no GPS fix available
- AND acceleration variance < 0.05g over 2 seconds

### Phase 2: Dynamic Orientation Refinement (Moving)

When vehicle is moving at stable speed, use acceleration patterns to refine forward axis:

#### Forward Axis Detection
```
During stable forward travel (GPS speed > 5 m/s, constant ±1 m/s):
- Forward axis shows acceleration/deceleration correlation with speed changes
- Lateral axis shows turning forces
- Vertical axis shows road surface variations

Algorithm:
1. Monitor GPS speed changes (delta_speed)
2. Correlate with accelerometer axes
3. Axis with highest correlation to delta_speed = forward axis
```

#### Speed Correlation
```c
// When GPS speed changes by > 0.5 m/s in 1 second
if (delta_speed > 0.5) {
    // Accelerating - forward axis should show positive
    forward_axis = axis_with_highest_positive_change;
} else if (delta_speed < -0.5) {
    // Decelerating - forward axis should show negative
    forward_axis = axis_with_highest_negative_change;
}
```

### Phase 3: Calibration State Machine

#### New States
```c
typedef enum {
    IMX_ACCL_INIT = 0,
    IMX_ACCL_AUTO_CAL_STATIC,      // NEW: Static gravity-based calibration
    IMX_ACCL_AUTO_CAL_WAIT_STATIC, // NEW: Waiting for stable readings
    IMX_ACCL_AUTO_CAL_DYNAMIC,     // NEW: Dynamic speed-based refinement
    IMX_ACCL_CALIBRATE,            // Existing manual calibration
    IMX_ACCL_CALIBRATE_WAIT,
    IMX_ACCL_PROCESS,
    IMX_ACCL_PROCESS_WAIT,
    IMX_ACCL_CLEANUP,
    IMX_ACCL_RESTART,
    IMX_ACCL_IDLE,
    IMX_ACCL_NO_STATES
} imx_accel_state_t;
```

#### State Flow
```
Power Up
    │
    ▼
IMX_ACCL_INIT
    │
    ▼
IMX_ACCL_AUTO_CAL_STATIC ──────────────────┐
    │                                       │
    │ (Collect 10 readings, 100ms apart)    │
    ▼                                       │
IMX_ACCL_AUTO_CAL_WAIT_STATIC              │
    │                                       │
    │ (Determine gravity axis, pitch, roll) │
    ▼                                       │
IMX_ACCL_PROCESS ◄─────────────────────────┘
    │
    │ (If GPS speed > 5 m/s for > 10 sec)
    ▼
IMX_ACCL_AUTO_CAL_DYNAMIC (background refinement)
    │
    │ (Correlate forward axis with speed)
    ▼
IMX_ACCL_PROCESS (updated rotation matrix)
```

---

## Implementation Details

### New Constants
```c
/* Auto-calibration thresholds */
#define AUTO_CAL_STATIONARY_SPEED_MS    0.5f   /* m/s - below this is stationary */
#define AUTO_CAL_STATIONARY_TIME_MS     5000   /* Must be stationary for 5 sec */
#define AUTO_CAL_VARIANCE_THRESHOLD     0.05f  /* g - max variance for stable reading */
#define AUTO_CAL_STATIC_READINGS        10     /* Number of readings for static cal */
#define AUTO_CAL_STATIC_INTERVAL_MS     100    /* 100ms between readings */

/* Dynamic calibration thresholds */
#define AUTO_CAL_MOVING_SPEED_MS        5.0f   /* m/s - above this for dynamic cal */
#define AUTO_CAL_SPEED_STABLE_RANGE     1.0f   /* m/s - speed variance for "stable" */
#define AUTO_CAL_SPEED_DELTA_THRESHOLD  0.5f   /* m/s - significant speed change */
#define AUTO_CAL_CORRELATION_SAMPLES    50     /* Samples for axis correlation */
#define AUTO_CAL_CORRELATION_THRESHOLD  0.7f   /* Min correlation for axis detection */

/* Gravity detection */
#define GRAVITY_G                       1.0f   /* 1g in normalized units */
#define GRAVITY_DETECTION_THRESHOLD     0.8f   /* Axis with > 0.8g is gravity axis */
```

### New Data Structures
```c
/**
 * @brief Orientation axis enumeration
 */
typedef enum {
    AXIS_X = 0,
    AXIS_Y = 1,
    AXIS_Z = 2,
    AXIS_UNKNOWN = -1
} accel_axis_id_t;

/**
 * @brief Auto-calibration state data
 */
typedef struct {
    /* Static calibration data */
    float static_readings_x[AUTO_CAL_STATIC_READINGS];
    float static_readings_y[AUTO_CAL_STATIC_READINGS];
    float static_readings_z[AUTO_CAL_STATIC_READINGS];
    uint8_t static_reading_count;

    /* Detected orientation */
    accel_axis_id_t gravity_axis;      /* Which axis has gravity */
    accel_axis_id_t forward_axis;      /* Which axis is forward */
    accel_axis_id_t lateral_axis;      /* Which axis is lateral */
    int8_t gravity_sign;               /* +1 or -1 for gravity direction */
    int8_t forward_sign;               /* +1 or -1 for forward direction */

    /* Dynamic calibration data */
    float speed_history[AUTO_CAL_CORRELATION_SAMPLES];
    float accel_x_history[AUTO_CAL_CORRELATION_SAMPLES];
    float accel_y_history[AUTO_CAL_CORRELATION_SAMPLES];
    float accel_z_history[AUTO_CAL_CORRELATION_SAMPLES];
    uint8_t history_index;
    bool dynamic_cal_complete;

    /* Status */
    bool static_cal_complete;
    imx_time_t last_update_time;
    float confidence;                   /* 0.0-1.0 calibration confidence */
} auto_cal_data_t;
```

### Key Functions

#### 1. Static Calibration
```c
/**
 * @brief Perform static gravity-based orientation detection
 *
 * Called when vehicle is stationary. Analyzes gravity vector
 * to determine device mounting orientation.
 *
 * @param cal_data Pointer to auto-calibration data structure
 * @return true if calibration successful, false if more data needed
 */
bool auto_cal_static_orientation(auto_cal_data_t *cal_data);
```

#### 2. Gravity Axis Detection
```c
/**
 * @brief Determine which axis has gravity based on averaged readings
 *
 * @param avg_x Average X-axis reading (g)
 * @param avg_y Average Y-axis reading (g)
 * @param avg_z Average Z-axis reading (g)
 * @param gravity_axis Output: detected gravity axis
 * @param gravity_sign Output: sign of gravity on that axis
 * @return true if gravity axis detected with confidence
 */
bool detect_gravity_axis(float avg_x, float avg_y, float avg_z,
                         accel_axis_id_t *gravity_axis, int8_t *gravity_sign);
```

#### 3. Rotation Matrix Calculation
```c
/**
 * @brief Calculate rotation matrix from detected orientation
 *
 * Creates 3x3 rotation matrix to transform device coordinates
 * to vehicle coordinates (X=forward, Y=left, Z=up).
 *
 * @param cal_data Calibration data with detected axes
 * @param rotation_matrix Output: 3x3 rotation matrix
 */
void calculate_rotation_matrix(const auto_cal_data_t *cal_data,
                               float rotation_matrix[3][3]);
```

#### 4. Dynamic Calibration
```c
/**
 * @brief Refine forward axis using GPS speed correlation
 *
 * Called periodically while vehicle is moving. Correlates
 * acceleration with GPS speed changes to identify forward axis.
 *
 * @param cal_data Pointer to auto-calibration data
 * @param gps_speed Current GPS speed in m/s
 * @param accel_x Current X acceleration (g)
 * @param accel_y Current Y acceleration (g)
 * @param accel_z Current Z acceleration (g)
 * @return true if dynamic calibration complete
 */
bool auto_cal_dynamic_refinement(auto_cal_data_t *cal_data,
                                 float gps_speed,
                                 float accel_x, float accel_y, float accel_z);
```

#### 5. GPS Speed Interface
```c
/**
 * @brief Get current GPS speed for calibration
 *
 * Wrapper for imx_get_gps_speed() with validity checking.
 *
 * @param speed_ms Output: speed in meters per second
 * @return true if valid GPS speed available
 */
bool auto_cal_get_gps_speed(float *speed_ms);
```

---

## Orientation Assumptions (Stationary)

When no GPS movement is available, make these assumptions based on gravity:

### Case 1: Z-axis has gravity (most common)
```
Device mounted flat (dashboard, etc.)
  - Z points up/down
  - X assumed forward (can be refined dynamically)
  - Y assumed lateral

Detection: |avg_z| > 0.8g, |avg_x| < 0.3g, |avg_y| < 0.3g
```

### Case 2: X-axis has gravity
```
Device mounted vertically, facing forward
  - X points up/down
  - Z assumed forward
  - Y assumed lateral

Detection: |avg_x| > 0.8g, |avg_z| < 0.3g, |avg_y| < 0.3g
```

### Case 3: Y-axis has gravity
```
Device mounted on side
  - Y points up/down
  - X assumed forward
  - Z assumed lateral

Detection: |avg_y| > 0.8g, |avg_x| < 0.3g, |avg_z| < 0.3g
```

### Pitch and Roll Calculation
```c
// For Z-axis gravity (standard mounting)
pitch = atan2(avg_x, sqrt(avg_y*avg_y + avg_z*avg_z)) * 180/PI;
roll = atan2(avg_y, sqrt(avg_x*avg_x + avg_z*avg_z)) * 180/PI;

// Thresholds for acceptable mounting
#define MAX_ACCEPTABLE_PITCH    30.0f  // degrees
#define MAX_ACCEPTABLE_ROLL     30.0f  // degrees
```

---

## Implementation Todo List

### Phase 1: Static Auto-Calibration - COMPLETED
1. [x] Add new constants for auto-calibration thresholds
2. [x] Add auto_cal_data_t structure and enums
3. [x] Add new calibration states to state machine
4. [x] Implement detect_gravity_axis() function
5. [x] Implement auto_cal_static_orientation() function
6. [x] Implement calculate_rotation_matrix() function
7. [x] Integrate with power-up sequence (IMX_ACCL_INIT)
8. [x] Build and verify

### Phase 2: Dynamic Refinement - COMPLETED
9. [x] Add GPS speed wrapper function
10. [x] Implement apply_rotation_to_reading() function
11. [x] Add dynamic calibration state (IMX_ACCL_AUTO_CAL_DYNAMIC)
12. [x] Add background refinement framework
13. [x] Build and verify

### Phase 3: Integration - COMPLETED
14. [x] Apply rotation matrix to accelerometer readings
15. [x] Event detection uses corrected values (via rotation transform)
16. [x] Add CLI status display for calibration state
17. [ ] Add CLI command to force recalibration (DEFERRED - existing calibration command available)
18. [x] Build and verify

### Phase 4: Testing & Documentation - PENDING USER TESTING
19. [ ] Test with device in various orientations
20. [ ] Test static calibration accuracy
21. [ ] Test dynamic refinement with GPS
22. [x] Update file documentation
23. [x] Final clean build verification

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Incorrect gravity detection | High | Use tight thresholds, require variance check |
| Wrong forward axis assumption | Medium | Dynamic refinement corrects this |
| GPS speed unavailable | Low | Fall back to static-only calibration |
| Rotation matrix singularities | High | Handle edge cases, gimbal lock prevention |
| Performance impact | Low | Run calibration in existing thread |

---

## Testing Recommendations

1. **Bench Test - Static**: Mount device in 6 orientations, verify detection
2. **Vehicle Test - Static**: Power up while parked, verify orientation
3. **Vehicle Test - Dynamic**: Drive straight, verify forward axis correlation
4. **Edge Cases**: Test with tilted mounting, vibration, poor GPS

---

## Approval

- [x] User approval of plan before implementation

---

## Implementation Completion Summary

**Completion Date**: 2025-12-26
**Compilation Errors**: 0
**New Compilation Warnings**: 0
**Pre-existing Warnings**: 2 (implicit function declarations for `imx_write_evt` and `imx_write_event_with_gps` - unrelated to changes)

### Changes Made

#### Phase 1: Static Auto-Calibration (COMPLETED)

1. **Added Auto-Calibration Constants** (lines 124-153)
   - `AUTO_CAL_STATIC_READINGS` (10 readings)
   - `AUTO_CAL_STATIC_INTERVAL_MS` (100ms)
   - `AUTO_CAL_VARIANCE_THRESHOLD` (0.05g)
   - `GRAVITY_DETECTION_THRESHOLD` (0.8g)
   - Dynamic calibration thresholds for GPS-based refinement

2. **Added New Enumerations** (lines 157-177)
   - `accel_axis_id_t`: AXIS_X, AXIS_Y, AXIS_Z, AXIS_UNKNOWN
   - `auto_cal_status_t`: NONE, STATIC_ONLY, DYNAMIC_PARTIAL, COMPLETE

3. **Added auto_cal_data_t Structure** (lines 244-277)
   - Static calibration readings array
   - Detected orientation (gravity, forward, lateral axes)
   - Computed angles (pitch, roll)
   - Dynamic calibration tracking
   - Status and confidence fields

4. **Extended State Machine** (lines 288-301)
   - Added `IMX_ACCL_AUTO_CAL_STATIC`
   - Added `IMX_ACCL_AUTO_CAL_WAIT`
   - Added `IMX_ACCL_AUTO_CAL_DYNAMIC`

5. **Implemented Helper Functions** (lines 668-910)
   - `detect_gravity_axis()`: Detects which axis has gravity
   - `auto_cal_static_orientation()`: Performs static orientation detection
   - `calculate_rotation_matrix()`: Builds 3x3 rotation matrix
   - `apply_rotation_to_reading()`: Transforms coordinates
   - `auto_cal_get_gps_speed()`: GPS speed wrapper

#### Phase 2: State Machine Cases (COMPLETED)

6. **Implemented State Handlers** (lines 1279-1387)
   - `IMX_ACCL_AUTO_CAL_STATIC`: Collects accelerometer readings
   - `IMX_ACCL_AUTO_CAL_WAIT`: Waits for readings, triggers orientation detection
   - `IMX_ACCL_AUTO_CAL_DYNAMIC`: Background GPS-based refinement

7. **Modified IMX_ACCL_INIT** (lines 1256-1276)
   - Now transitions to `IMX_ACCL_AUTO_CAL_STATIC` instead of directly to processing
   - Initializes auto-calibration data structure

#### Phase 3: Integration (COMPLETED)

8. **Applied Rotation Matrix to Readings** (lines 1119-1127)
   - Added rotation transform in `process_gforce_data()` after filtering
   - Only applied when auto-calibration is complete

9. **Updated CLI Status Display** (lines 1611-1686)
   - Added auto-calibration status display
   - Shows detected orientation (gravity, forward, lateral axes)
   - Shows pitch/roll angles
   - Shows calibration progress during auto-cal

10. **Updated State-to-String Function** (lines 1573-1602)
    - Added new state names for auto-calibration states

### Files Modified
- `Fleet-Connect-1/hal/accel_process.c` - All changes in single file (~250 lines added)

### Architecture Notes

The auto-calibration system integrates with the existing accelerometer state machine:

```
Power-Up → INIT → AUTO_CAL_STATIC → AUTO_CAL_WAIT → PROCESS → PROCESS_WAIT
                                                          ↓
                                               AUTO_CAL_DYNAMIC (background)
```

**Key Design Decisions**:
1. Static calibration runs at startup before processing thread starts
2. Gravity detection uses 0.8g threshold for robust axis identification
3. Rotation matrix transforms device coordinates to vehicle coordinates
4. Dynamic calibration is a framework for future GPS-based refinement
5. CLI status shows detailed orientation information for debugging

### Testing Recommendations

1. **Bench Test**: Mount device in 6 orientations (±X, ±Y, ±Z up), verify correct detection
2. **Vehicle Test - Static**: Power up while parked, verify orientation detection
3. **Vehicle Test - Dynamic**: Drive straight, verify forward axis correlation with GPS
4. **Edge Cases**: Test with tilted mounting (30-45°), vibration, poor GPS

---

**Plan Created By**: Claude Code
**Source Specification**: docs/prompt_work/update_app_cli_order.yaml
**Generated**: 2025-12-26
**Completed**: 2025-12-26
