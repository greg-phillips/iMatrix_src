# Vehicle Sensor Mappings Architecture Guide

**Date:** 2025-12-14
**Author:** Claude Code Analysis
**Document Version:** 1.0
**Status:** Complete
**Branch:** Aptera_1_Clean (both iMatrix and Fleet-Connect-1)

---

## Executive Summary

This document provides a comprehensive guide to the Fleet-Connect-1 vehicle sensor mapping architecture. It explains how sensor data flows from CAN bus sources to iMatrix sensors and provides step-by-step instructions for adding new vehicle types and sensor mappings.

---

## 1. Architecture Overview

### 1.1 High-Level Data Flow

```
CAN Bus/OBD2/J1939  →  Decoder  →  Sensor Mapping  →  iMatrix Sensor  →  Cloud Upload
      ↓                   ↓              ↓                   ↓
  Raw Message       Extract Signal   Find Handler      Update Value
                                          ↓
                                    Hash Table Lookup
                                       (O(1))
```

### 1.2 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `vehicle_sensor_mappings.c` | `Fleet-Connect-1/can_process/` | Main mapping logic with hash table |
| `vehicle_sensor_mappings.h` | `Fleet-Connect-1/can_process/` | Type definitions and API |
| `obd2_sensor_updates.c/h` | `Fleet-Connect-1/can_process/` | OBD2 protocol handlers |
| `j1939_sensor_updates.c/h` | `Fleet-Connect-1/can_process/` | J1939 protocol handlers |
| `can_signal_sensor_updates.c/h` | `Fleet-Connect-1/can_process/` | Generic CAN handlers |
| `pid_to_imatrix_map.h` | `Fleet-Connect-1/can_process/` | OBD2 PID mappings |

### 1.3 Supported Vehicle Types

| Vehicle Type | Product ID | Value | Protocol | Sensors |
|-------------|------------|-------|----------|---------|
| Light Vehicle (OBD2) | `IMX_LIGHT_VEHICLE` | 3116622498 | OBD2 PIDs | 7 standard |
| J1939 Vehicle | `IMX_J1939_VEHICLE` | 1234567890 | J1939 PGN/SPN | 7 standard |
| HM Wrecker (EV) | `IMX_HM_WRECKER` | 1235419592 | Proprietary CAN | 7 + EV-specific |

---

## 2. Core Data Structures

### 2.1 Sensor Type Enumeration

```c
typedef enum {
    VEHICLE_SENSOR_ODOMETER = 0,            // Odometer/Mileage
    VEHICLE_SENSOR_VEHICLE_SPEED,           // Vehicle Speed
    VEHICLE_SENSOR_FUEL_LEVEL,              // Fuel Level
    VEHICLE_SENSOR_ENGINE_RPM,              // Engine RPM
    VEHICLE_SENSOR_ENGINE_OIL_TEMPERATURE,  // Engine Oil Temperature
    VEHICLE_SENSOR_THROTTLE_POSITION,       // Throttle Position
    VEHICLE_SENSOR_ENGINE_COOLANT_TEMP,     // Engine Coolant Temperature
    VEHICLE_SENSOR_TOTAL_VOLTAGE,           // Total Voltage (EV specific)
    VEHICLE_SENSOR_TOTAL_CURRENT,           // Total Current (EV specific)
    VEHICLE_SENSOR_STATE_OF_CHARGE,         // State of Charge (EV specific)
    VEHICLE_SENSOR_TRIP_METER,              // Trip Meter (EV specific)
    VEHICLE_SENSOR_CHARGING_STATUS,         // Charging status (EV specific)
    VEHICLE_SENSOR_MAX                      // Maximum sensor count
} vehicle_sensor_type_t;
```

### 2.2 Sensor Mapping Entry Structure

```c
typedef struct {
    uint32_t sensor_id;                                 // CAN sensor ID (0 = not supported)
    sensor_update_func_t update_func;                   // Function to call for updates
    char name[VEHICLE_SENSOR_NAME_LENGTH];              // Human-readable sensor name
    sensor_source_type_t source_type;                   // Data source type
} vehicle_sensor_mapping_t;
```

### 2.3 Sensor Source Types

```c
typedef enum {
    SENSOR_SOURCE_J1939,        // J1939 PGN/SPN source
    SENSOR_SOURCE_OBD2,         // OBD2 PID source
    SENSOR_SOURCE_CAN_SIGNAL,   // Generic CAN signal source
    SENSOR_SOURCE_GPS,          // GPS calculated source
    SENSOR_SOURCE_UNKNOWN       // Unknown/undefined source
} sensor_source_type_t;
```

### 2.4 Update Function Signature

```c
typedef imx_result_t (*sensor_update_func_t)(double value);
```

All update functions must:
- Accept a `double value` parameter
- Return `imx_result_t` (IMX_SUCCESS on success)
- Handle unit conversions internally
- Call the appropriate iMatrix sensor API

---

## 3. Existing Vehicle Mappings

### 3.1 OBD2 Light Vehicle Mapping

```c
static const vehicle_sensor_mapping_t light_vehicle_mappings[VEHICLE_SENSOR_MAX] = {
    [VEHICLE_SENSOR_ODOMETER]               = {MAP_TO_ODOMETER, update_odometer_from_obd2, "Odometer (OBD2)", SENSOR_SOURCE_OBD2},
    [VEHICLE_SENSOR_VEHICLE_SPEED]          = {MAP_TO_VEHICLE_SPEED, update_vehicle_speed_from_obd2, "Vehicle Speed (OBD2)", SENSOR_SOURCE_OBD2},
    [VEHICLE_SENSOR_FUEL_LEVEL]             = {MAP_TO_FUEL_LEVEL, update_fuel_level_from_obd2, "Fuel Level (OBD2)", SENSOR_SOURCE_OBD2},
    [VEHICLE_SENSOR_ENGINE_RPM]             = {MAP_TO_ENGINE_RPM, update_engine_rpm_from_obd2, "Engine RPM (OBD2)", SENSOR_SOURCE_OBD2},
    [VEHICLE_SENSOR_ENGINE_OIL_TEMPERATURE] = {MAP_TO_ENGINE_OIL_TEMPERATURE, update_engine_oil_temperature_from_obd2, "Engine Oil Temperature (OBD2)", SENSOR_SOURCE_OBD2},
    [VEHICLE_SENSOR_THROTTLE_POSITION]      = {MAP_TO_THROTTLE_POSITION, update_throttle_position_from_obd2, "Throttle Position (OBD2)", SENSOR_SOURCE_OBD2},
    [VEHICLE_SENSOR_ENGINE_COOLANT_TEMP]    = {MAP_TO_ENGINE_COOLANT_TEMPERATURE, update_engine_coolant_temperature_from_obd2, "Engine Coolant Temp (OBD2)", SENSOR_SOURCE_OBD2},
    // EV sensors not supported
    [VEHICLE_SENSOR_TOTAL_VOLTAGE]          = {0, NULL, "Not Supported", SENSOR_SOURCE_UNKNOWN},
    ...
};
```

### 3.2 J1939 Vehicle Mapping

```c
static const vehicle_sensor_mapping_t j1939_vehicle_mappings[VEHICLE_SENSOR_MAX] = {
    [VEHICLE_SENSOR_ODOMETER]               = {J1939_ODOMETER_ID, update_odometer_from_j1939, "Odometer (J1939)", SENSOR_SOURCE_J1939},
    [VEHICLE_SENSOR_VEHICLE_SPEED]          = {J1939_VEHICLE_SPEED_ID, update_vehicle_speed_from_j1939, "Vehicle Speed (J1939)", SENSOR_SOURCE_J1939},
    // ... etc
};
```

### 3.3 HM Wrecker Mapping (Runtime Initialized)

The HM Wrecker uses a **runtime initialization** pattern because its sensor IDs come from a generated header file:

```c
static vehicle_sensor_mapping_t hm_wrecker_mappings[VEHICLE_SENSOR_MAX];

static void init_hm_wrecker_mappings(void)
{
    static bool initialized = false;
    if (initialized) return;

    memset(hm_wrecker_mappings, 0, sizeof(hm_wrecker_mappings));

    // Odometer
    sensor_id = hm_get_total_mileage_signal_id();
    if (sensor_id > 0 && sensor_id < SENSOR_ID_RESERVED_START) {
        hm_wrecker_mappings[VEHICLE_SENSOR_ODOMETER].sensor_id = sensor_id;
        hm_wrecker_mappings[VEHICLE_SENSOR_ODOMETER].update_func = update_odometer_from_can_signal;
        strncpy(hm_wrecker_mappings[VEHICLE_SENSOR_ODOMETER].name, "Total Mileage (CAN)", ...);
        hm_wrecker_mappings[VEHICLE_SENSOR_ODOMETER].source_type = SENSOR_SOURCE_CAN_SIGNAL;
    }
    // ... repeat for each sensor

    initialized = true;
}
```

---

## 4. Hash Table Lookup System

### 4.1 Purpose

The hash table provides **O(1) average-case** sensor lookups instead of O(n) linear search. This is critical for real-time embedded systems processing CAN data.

### 4.2 Configuration

```c
#define SENSOR_HASH_TABLE_SIZE  256     // Hash bucket count
#define HASH_EMPTY_SLOT         0       // Empty slot marker
#define MAX_SENSOR_ID           0xFFFFFFF0  // Maximum valid sensor ID
#define SENSOR_ID_RESERVED_START 0xFFFFFFF0 // Reserved range start
```

### 4.3 Hash Function

```c
static uint16_t hash_sensor_id(uint32_t sensor_id)
{
    return (uint16_t)(sensor_id % SENSOR_HASH_TABLE_SIZE);
}
```

### 4.4 Collision Handling

Uses **chaining** - each bucket can have a linked list of entries with the same hash value.

```c
typedef struct sensor_hash_entry {
    uint32_t sensor_id;
    uint16_t mapping_index;
    struct sensor_hash_entry *next;  // Collision chain
} sensor_hash_entry_t;
```

---

## 5. Adding a New Vehicle Type

### 5.1 Step-by-Step Process

#### Step 1: Define Product ID

Add the new product ID in `iMatrix/canbus/can_structs.h`:

```c
#define IMX_NEW_VEHICLE  (YOUR_PRODUCT_ID_VALUE)
```

Product IDs are typically CRC32 hashes or assigned values.

#### Step 2: Choose Mapping Pattern

**Option A: Static Mapping (for standard protocols)**
- Use when sensor IDs are known at compile time
- Best for OBD2 or J1939 vehicles using standard PIDs/SPNs

**Option B: Runtime Mapping (for proprietary CAN)**
- Use when sensor IDs come from DBC files or generated headers
- Best for custom CAN protocols

#### Step 3: Create Sensor Mapping Array

**Static Pattern Example:**
```c
static const vehicle_sensor_mapping_t new_vehicle_mappings[VEHICLE_SENSOR_MAX] = {
    [VEHICLE_SENSOR_ODOMETER] = {
        NEW_VEHICLE_ODOMETER_ID,           // Sensor ID constant
        update_odometer_from_new_vehicle,   // Update function
        "Odometer (New Vehicle)",           // Display name
        SENSOR_SOURCE_CAN_SIGNAL            // Source type
    },
    [VEHICLE_SENSOR_VEHICLE_SPEED] = {
        NEW_VEHICLE_SPEED_ID,
        update_vehicle_speed_from_new_vehicle,
        "Vehicle Speed (New Vehicle)",
        SENSOR_SOURCE_CAN_SIGNAL
    },
    // Mark unsupported sensors
    [VEHICLE_SENSOR_ENGINE_RPM] = {0, NULL, "Not Supported", SENSOR_SOURCE_UNKNOWN},
    // ... continue for all VEHICLE_SENSOR_MAX entries
};
```

**Runtime Pattern Example:**
```c
static vehicle_sensor_mapping_t new_vehicle_mappings[VEHICLE_SENSOR_MAX];

static void init_new_vehicle_mappings(void)
{
    static bool initialized = false;
    if (initialized) return;

    memset(new_vehicle_mappings, 0, sizeof(new_vehicle_mappings));

    uint32_t sensor_id = get_new_vehicle_odometer_signal_id();
    if (sensor_id > 0 && sensor_id < SENSOR_ID_RESERVED_START) {
        new_vehicle_mappings[VEHICLE_SENSOR_ODOMETER].sensor_id = sensor_id;
        new_vehicle_mappings[VEHICLE_SENSOR_ODOMETER].update_func = update_odometer_from_can_signal;
        strncpy(new_vehicle_mappings[VEHICLE_SENSOR_ODOMETER].name,
                "Odometer (New)", VEHICLE_SENSOR_NAME_LENGTH - 1);
        new_vehicle_mappings[VEHICLE_SENSOR_ODOMETER].source_type = SENSOR_SOURCE_CAN_SIGNAL;
    }

    // ... repeat for each sensor

    initialized = true;
}
```

#### Step 4: Register in Vehicle Configuration Table

Add entry to `vehicle_configs[]` array:

```c
static const vehicle_config_t vehicle_configs[] = {
    // ... existing entries ...
    {
        .product_id = IMX_NEW_VEHICLE,
        .vehicle_name = "New Vehicle Type",
        .sensors = {[0 ... VEHICLE_SENSOR_MAX-1] = {0}}
    }
};
```

#### Step 5: Update Initialization Function

Modify `init_vehicle_sensor_mappings()`:

```c
void init_vehicle_sensor_mappings(void)
{
    switch (mgc.product_id) {
        // ... existing cases ...

        case IMX_NEW_VEHICLE:
            // For runtime initialization:
            init_new_vehicle_mappings();
            active_vehicle_mappings = new_vehicle_mappings;
            // OR for static initialization:
            // active_vehicle_mappings = new_vehicle_mappings;
            imx_cli_print("Initialized New Vehicle sensor mappings\r\n");
            break;

        default:
            active_vehicle_mappings = NULL;
            break;
    }

    if (active_vehicle_mappings != NULL) {
        build_sensor_hash_table(active_vehicle_mappings);
    }
}
```

#### Step 6: Update Display and Statistics Functions

Add cases to `get_vehicle_sensor_stats()` and `display_vehicle_sensor_mappings()`:

```c
switch (mgc.product_id) {
    // ... existing cases ...
    case IMX_NEW_VEHICLE:
        mappings = new_vehicle_mappings;
        vehicle_name = "New Vehicle Type";
        break;
}
```

---

## 6. Creating Update Functions

### 6.1 Update Function Template

```c
/**
 * @brief Update [sensor_name] sensor value from [source] data source
 *
 * This function updates the [sensor_name] using [source] data.
 * [Additional details about unit conversion, source PID/PGN, etc.]
 *
 * @param[in] value [Description of expected units]
 * @return IMX_SUCCESS if successful, error code otherwise
 */
imx_result_t update_[sensor_name]_from_[source](double value)
{
    /* Perform any required unit conversion */
    float converted_value = (float)value;  // Or apply conversion

    /* Call the appropriate iMatrix API */
    return imx_set_[target_sensor](converted_value);
}
```

### 6.2 Example: OBD2 Update Function

```c
imx_result_t update_vehicle_speed_from_obd2(double value)
{
    /* OBD2 PID 0x0D provides speed in km/h */
    /* imx_set_j1939_speed handles km/h to m/s conversion */
    return imx_set_j1939_speed((float)value);
}
```

### 6.3 Example: CAN Signal Update Function

```c
imx_result_t update_vehicle_speed_from_can_signal(double value)
{
    /* Generic CAN signal speed, typically in km/h */
    /* HM-specific function handles km/h to m/s conversion */
    return imx_set_hm_truck_speed((float)value);
}
```

### 6.4 Available iMatrix Sensor APIs

| Function | Purpose | Units |
|----------|---------|-------|
| `imx_set_odometer(float)` | Set odometer value | km |
| `imx_set_j1939_speed(float)` | Set speed (converts km/h to m/s) | km/h |
| `imx_set_fuel_level(float)` | Set fuel level | % (0-100) |
| `imx_set_engine_rpm(uint32_t)` | Set engine RPM | RPM |
| `imx_set_engine_oil_temperature(float)` | Set oil temperature | Celsius |
| `imx_set_throttle_position(float)` | Set throttle position | % (0-100) |
| `imx_set_engine_coolant_temperature(float)` | Set coolant temp | Celsius |
| `imx_set_hm_truck_battery_voltage(float)` | Set battery voltage | Volts |
| `imx_set_hm_truck_battery_current(float)` | Set battery current | Amperes |
| `imx_set_hm_truck_battery_soc(float)` | Set state of charge | % (0-100) |
| `imx_set_hm_truck_charging_status(uint32_t)` | Set charging status | 0-15 state |

---

## 7. Adding New Sensor Types

### 7.1 Extend the Enumeration

Add new sensor type to `vehicle_sensor_type_t` in `vehicle_sensor_mappings.h`:

```c
typedef enum {
    // ... existing sensors ...
    VEHICLE_SENSOR_CHARGING_STATUS,
    VEHICLE_SENSOR_NEW_SENSOR_TYPE,    // Add your new sensor
    VEHICLE_SENSOR_MAX
} vehicle_sensor_type_t;
```

### 7.2 Update Display Arrays

Add entry to `sensor_type_names[]` in `display_vehicle_sensor_mappings()`:

```c
const char *sensor_type_names[VEHICLE_SENSOR_MAX] = {
    // ... existing names ...
    "CHARGING_STATUS",
    "NEW_SENSOR_TYPE"
};
```

### 7.3 Implement Update Functions

Create update functions for each protocol that supports the sensor.

### 7.4 Add to Vehicle Mappings

Add entries to each vehicle mapping array where the sensor is supported.

---

## 8. Debugging and Testing

### 8.1 CLI Commands

| Command | Purpose |
|---------|---------|
| `can mappings` | Display vehicle sensor mappings |
| `can hashstats` | Display hash table statistics |
| `can hashlookup` | Test hash table lookups |

### 8.2 Debug Flags

Enable debug logging with:
```c
debug DEBUGS_APP_MAPPINGS
```

### 8.3 Test Hash Table Function

```c
void test_vehicle_sensor_lookups(void);
```

This function tests all configured sensors and reports:
- Configured sensor count
- Found in hash table count
- Verification status
- Any lookup errors

### 8.4 Hash Table Statistics

```c
void display_hash_table_stats(void);
```

Reports:
- Total entries
- Used/empty buckets
- Collision rate
- Maximum chain length
- Performance recommendations

---

## 9. Best Practices

### 9.1 Sensor ID Management

- Use unique sensor IDs across all vehicle types
- OBD2 uses CRC32 hash of sensor name (`MAP_TO_*` constants)
- J1939 uses internal sensor IDs (e.g., `IMX_INTERNAL_SENSOR_*`)
- CAN signals use IDs from DBC-generated headers

### 9.2 Unsupported Sensors

Always explicitly mark unsupported sensors:

```c
[VEHICLE_SENSOR_ENGINE_RPM] = {0, NULL, "Not Supported", SENSOR_SOURCE_UNKNOWN},
```

### 9.3 Unit Conventions

| Measurement | Internal Unit | Notes |
|-------------|---------------|-------|
| Speed | m/s | Convert from km/h in update function |
| Distance | km | - |
| Temperature | Celsius | OBD2 may need offset adjustment |
| Percentage | 0-100 | Fuel level, SOC, throttle |
| Voltage | Volts | - |
| Current | Amperes | - |
| RPM | RPM | Use uint32_t |

### 9.4 Error Handling

Update functions should:
- Validate sensor IDs before use
- Return appropriate error codes
- Not crash on invalid data

### 9.5 Memory Efficiency

- Use static allocation for embedded systems
- Hash table uses pre-allocated entries array
- Avoid dynamic memory allocation

---

## 10. Example: Adding a New EV Type

### Scenario

Add support for "Aptera" electric vehicle with:
- Vehicle Speed
- Battery SOC
- Battery Voltage
- Battery Current
- Odometer
- Charging Status

### Implementation Steps

1. **Define Product ID** (in `can_structs.h`):
   ```c
   #define IMX_APTERA  (YOUR_APTERA_PRODUCT_ID)
   ```

2. **Create Signal ID Accessor Functions** (if using DBC):
   ```c
   // In aptera/get_aptera_signals.h
   uint32_t aptera_get_vehicle_speed_signal_id(void);
   uint32_t aptera_get_soc_signal_id(void);
   // ... etc
   ```

3. **Create Mapping Array**:
   ```c
   static vehicle_sensor_mapping_t aptera_mappings[VEHICLE_SENSOR_MAX];

   static void init_aptera_mappings(void)
   {
       // Initialize as shown in Section 5.1 Step 3
   }
   ```

4. **Update Initialization**:
   ```c
   case IMX_APTERA:
       init_aptera_mappings();
       active_vehicle_mappings = aptera_mappings;
       break;
   ```

5. **Build and Test**:
   - Run `cmake --build build`
   - Use `can mappings` to verify
   - Use `can hashlookup` to test lookups

---

## 11. File Structure Reference

```
Fleet-Connect-1/can_process/
├── can_man.c/h                    - Core CAN message management
├── can_signal_sensor_updates.c/h  - Generic CAN signal handlers
├── j1939_sensor_updates.c/h       - J1939 protocol handlers
├── obd2_sensor_updates.c/h        - OBD2 protocol handlers
├── odometer_validation.c/h        - Odometer validation logic
├── pid_to_imatrix_map.h           - OBD2 PID to sensor ID map
├── test_can_obd2.c/h              - Testing interface
└── vehicle_sensor_mappings.c/h    - Main mapping system

Fleet-Connect-1/hm_truck/
├── hm_truck.c/h                   - HM truck processing
├── hm_truck_sensors_def.h         - X-macro sensor definitions
├── get_hm_truck.c/h               - HM truck sensor accessors
└── HM_Wrecker_can_definitions.h   - Auto-generated signal IDs

iMatrix/canbus/
├── can_structs.h                  - Product ID definitions
└── can_process.c                  - CAN processing integration
```

---

## 12. Todo Checklist for New Vehicle Integration

- [ ] Define product ID in `can_structs.h`
- [ ] Choose mapping pattern (static vs runtime)
- [ ] Create/generate signal ID accessor functions (if CAN-based)
- [ ] Create sensor mapping array
- [ ] Create update functions (or reuse existing)
- [ ] Register in `vehicle_configs[]` array
- [ ] Update `init_vehicle_sensor_mappings()`
- [ ] Update `get_vehicle_sensor_stats()`
- [ ] Update `display_vehicle_sensor_mappings()`
- [ ] Update `test_vehicle_sensor_lookups()`
- [ ] Add to CMakeLists.txt (if new source files)
- [ ] Build and verify no warnings/errors
- [ ] Test with `can mappings` command
- [ ] Test with `can hashlookup` command
- [ ] Document new vehicle type

---

## Summary

The vehicle sensor mapping system provides a flexible, efficient architecture for supporting multiple vehicle types with different CAN protocols. Key features:

1. **Hash table lookup** for O(1) sensor matching
2. **Protocol abstraction** via update functions
3. **Static/runtime mapping** options for different scenarios
4. **Extensible design** for adding new vehicles and sensors
5. **Built-in diagnostics** for debugging and validation

Follow the patterns and examples in this guide to add support for new vehicles while maintaining code consistency and embedded system efficiency.

---

**Document Completed:** 2025-12-14
**No implementation changes required** - this is a documentation task.
