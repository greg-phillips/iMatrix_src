# Fleet Connect and iMatrix - Comprehensive Project Documentation

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Project Overview](#project-overview)
3. [Technical Architecture](#technical-architecture)
4. [Detailed Source File Documentation](#detailed-source-file-documentation)
   - [Fleet-Connect-1 Source Files](#fleet-connect-1-source-files)
   - [iMatrix Source Files](#imatrix-source-files)
5. [Core Components](#core-components)
6. [Implementation Details](#implementation-details)
7. [Security Analysis](#security-analysis)
8. [Recent Enhancements](#recent-enhancements)
9. [Integration Guide](#integration-guide)
10. [Development Guidelines](#development-guidelines)
11. [Current Status and Roadmap](#current-status-and-roadmap)

## Executive Summary

Fleet Connect is an enterprise-grade fleet management gateway system that combines vehicle diagnostics, telematics, and IoT connectivity. The system consists of two main components:

- **Fleet-Connect-1**: A specialized gateway application for vehicle data collection via CAN bus and OBD2 protocols
- **iMatrix**: A comprehensive IoT client framework providing wireless connectivity, data management, and cloud integration

The integrated system enables real-time vehicle monitoring, diagnostics, and data analytics for fleet management applications, supporting various vehicle types from light passenger vehicles to heavy-duty commercial trucks.

## Project Overview

### Fleet-Connect-1 Gateway

Fleet-Connect-1 serves as the primary interface between vehicles and the cloud, providing:

- **OBD2 Protocol Support**: Comprehensive implementation of OBD2 diagnostics including:
  - Mode 01: Current data (PIDs 0x00-0xDF)
  - Mode 09: Vehicle information
  - ISO-15765 CAN transport protocol
  - Multi-frame message handling
  - PID availability detection

- **CAN Bus Processing**: Advanced CAN message handling featuring:
  - Support for standard (11-bit) and extended (29-bit) CAN IDs
  - CAN FD compatibility (up to 64-byte frames)
  - Signal extraction and mapping
  - Multi-bus support (3 simultaneous CAN buses)
  - Ring buffer implementation for zero-allocation processing

- **Vehicle Configuration Support**:
  - Light vehicles (traditional ICE): 51 sensors
  - J1939 commercial/heavy-duty vehicles: 57 sensors
  - Horizon Motors electric wreckers: 43 sensors
  - X-macro based configuration for maintainability

### iMatrix IoT Framework

The iMatrix framework provides the connectivity and platform layer:

- **Multi-Platform Support**:
  - Linux Platform: For gateway devices (Laird IG60-BL654-LTE)
  - WICED Platform: For embedded systems (ISM43340 STM32F405)
  - Platform abstraction layer for code portability

- **Connectivity Options**:
  - WiFi with enterprise authentication
  - Bluetooth Low Energy (BLE) server and client
  - Cellular connectivity (PPP)
  - Ethernet support
  - Automatic network failover (eth0 → wlan0 → ppp0)

- **Data Management**:
  - Tiered storage system (RAM + disk overflow)
  - CoAP protocol for IoT communication
  - JSON data formatting
  - Secure data upload to cloud

### Command Line Interface

Fleet Connect supports command line options for configuration inspection and debugging:

**Command Line Options:**

- **-P**: Print configuration file details and exit
  - Locates the configuration file in `IMATRIX_STORAGE_PATH` (/etc/imatrix)
  - Displays comprehensive configuration information including:
    - Product ID, Organization ID, and Name
    - Control and Sensor block details (data types, poll rates, sample rates)
    - CAN bus configurations for all 3 buses (CAN0, CAN1, CAN-Ethernet)
    - **Network interface details** (name, mode, IP address, DHCP server status)
    - Internal sensor definitions
    - DBC signal settings and files
    - CAN bus hardware configurations
  - Useful for:
    - Verifying configuration before deployment
    - Troubleshooting configuration issues
    - Documenting system setup
    - Quick inspection without running the full gateway

**Example Usage:**
```bash
# Print configuration and exit
./Fleet-Connect -P

# Normal operation
./Fleet-Connect
```

**Configuration Statistics Output:**
```
================================================================================
                        CONFIGURATION STATISTICS
================================================================================
Product:                 Aptera Production Intent-1 (ID: 2201718576)
Control/Sensor Blocks:   1
CAN Messages:            113
  - CAN_BUS_0:           0
  - CAN_BUS_1:           0
  - CAN_BUS_ETH:         113
CAN Signals:             1071
Network Interfaces:      2
  - eth0                Mode: static   IP: 192.168.1.100   DHCP: No
  - wlan0               Mode: dhcp     IP: (none)          DHCP: Yes
Internal Sensors:        60
DBC Signal Settings:     1071
DBC Files:               2
CAN Bus HW Configs:      0
================================================================================
```

## Technical Architecture

### Directory Structure

```
/home/greg/iMatrix_src/
├── Fleet-Connect-1/
│   ├── OBD2/                    # OBD2 protocol implementation
│   │   ├── decode_mode_01_*.c   # PID decoders by range
│   │   ├── i15765.c             # ISO-15765 transport layer
│   │   └── process_obd2.c       # Main OBD2 processing
│   ├── can_process/             # CAN bus handling
│   │   ├── can_man.c            # CAN manager
│   │   └── vehicle_sensor_mappings.c
│   ├── cli/                     # Command line interface
│   ├── hal/                     # Hardware abstraction
│   ├── init/                    # Initialization and configs
│   │   ├── *_vehicle_config.c   # Vehicle-specific configs
│   │   └── imx_client_init.c    # iMatrix integration
│   ├── power/                   # Power management
│   ├── product/                 # Product-specific code
│   └── linux_gateway.c          # Main application
│
└── iMatrix/
    ├── IMX_Platform/            # Platform abstraction
    │   ├── LINUX_Platform/      # Linux implementation
    │   └── WICED_Platform/      # WICED implementation
    ├── ble/                     # Bluetooth Low Energy
    ├── canbus/                  # CAN integration
    │   ├── can_ring_buffer.c    # Zero-allocation buffers
    │   └── can_verify.c         # Signal verification
    ├── cli/                     # Extended CLI
    │   └── cli_memory_monitor.c # Memory monitoring
    ├── coap/                    # CoAP protocol
    ├── cs_ctrl/                 # Control system
    │   └── memory_manager*.c    # Tiered storage
    ├── device/                  # Device management
    ├── imatrix_upload/          # Cloud upload
    ├── location/                # GPS and geofencing
    ├── networking/              # Network management
    ├── ota_loader/              # OTA updates
    └── wifi/                    # WiFi management
```

### System Architecture Layers

```
┌─────────────────────────────────────────────────┐
│           Cloud Services (iMatrix)              │
├─────────────────────────────────────────────────┤
│         Application Layer (Fleet-Connect-1)      │
│  ┌─────────────┬──────────────┬──────────────┐ │
│  │   OBD2      │  CAN Process │     CLI      │ │
│  │  Protocol   │   Manager    │  Interface   │ │
│  └─────────────┴──────────────┴──────────────┘ │
├─────────────────────────────────────────────────┤
│         iMatrix Client Framework                 │
│  ┌──────────┬───────────┬────────────────────┐ │
│  │   CoAP   │    BLE    │   Network Manager  │ │
│  │ Protocol │  Server   │  (Failover Logic)  │ │
│  └──────────┴───────────┴────────────────────┘ │
├─────────────────────────────────────────────────┤
│      Platform Abstraction Layer (PAL)           │
│  ┌────────────────────┬──────────────────────┐ │
│  │   Linux Platform   │   WICED Platform     │ │
│  └────────────────────┴──────────────────────┘ │
├─────────────────────────────────────────────────┤
│         Hardware Layer                          │
│  ┌──────────┬──────────┬─────────┬──────────┐ │
│  │   CAN    │  WiFi/   │   GPS   │  Storage │ │
│  │   Bus    │   BLE    │         │  (Flash) │ │
│  └──────────┴──────────┴─────────┴──────────┘ │
└─────────────────────────────────────────────────┘
```

## Detailed Source File Documentation

### Fleet-Connect-1 Source Files

#### OBD2 Module (`/OBD2/`)

##### process_obd2.c/h
- **Purpose**: Main OBD2 state machine and PID processing engine
- **Key Functions**:
  - `init_obd2()` - Initialize OBD2 subsystem
  - `process_obd2()` - Main processing loop called periodically
  - `process_obd2_data()` - Process incoming OBD2 responses
  - `load_obd2_pids()` - Load supported PIDs from configuration
  - `get_pid_name()` - Convert PID number to human-readable name
- **State Machine States**:
  - `OBD2_INIT` - Initial state, prepare for operation
  - `OBD2_GET_AVAIL_PIDS` - Query available PIDs from vehicle
  - `OBD2_GET_VIN` - Retrieve Vehicle Identification Number
  - `OBD2_MONITOR` - Normal operation, cycle through PIDs
- **Integration**: Works with i15765.c for CAN transport, uploads data via iMatrix

##### i15765.c/h
- **Purpose**: ISO 15765-2 transport protocol implementation for OBD2 over CAN
- **Key Functions**:
  - `i15765_init()` - Initialize transport layer
  - `i15765_tx()` - Transmit OBD2 request
  - `i15765_rx_post()` - Post received CAN frame for processing
  - `i15765_rx_sf()` - Handle single frame reception
  - `i15765_rx_ff()` - Handle first frame of multi-frame
  - `i15765_rx_cf()` - Handle consecutive frames
  - `i15765_tx_fc()` - Transmit flow control frame
- **Data Structures**:
  - `i15765_t` - Main context structure
  - `i15765_msg_t` - Message buffer for assembly
- **Features**: Handles segmentation, flow control, timing, error recovery

##### decode_mode_01_pids_01_1F.c/h (and similar files for other ranges)
- **Purpose**: Decode OBD2 Mode 01 PIDs in range 0x01-0x1F
- **Key Functions**:
  - `decode_pid_01()` - Monitor status since DTCs cleared
  - `decode_pid_04()` - Calculated engine load
  - `decode_pid_05()` - Engine coolant temperature
  - `decode_pid_0C()` - Engine RPM
  - `decode_pid_0D()` - Vehicle speed
  - `decode_pid_10()` - MAF air flow rate
  - `decode_pid_11()` - Throttle position
- **Pattern**: Each function extracts raw bytes and applies PID-specific scaling
- **Integration**: Called by process_pid_data.c based on PID number

##### get_avail_pids.c/h
- **Purpose**: Query and parse available PIDs from vehicle
- **Key Functions**:
  - `get_avail_pids()` - Query ranges of supported PIDs
  - `update_avail_bitmap()` - Update bitmap of available PIDs
  - `is_pid_available()` - Check if specific PID is supported
- **Algorithm**: Uses PID 00, 20, 40, etc. to get 32-bit bitmaps
- **Integration**: Called during OBD2_GET_AVAIL_PIDS state

##### process_vehicle_info.c/h
- **Purpose**: Process vehicle information (VIN, ECU names, etc.)
- **Key Functions**:
  - `process_vin()` - Decode Vehicle Identification Number
  - `decode_ascii_vin()` - Convert VIN bytes to string
  - `validate_vin()` - Verify VIN checksum and format
- **Mode Support**: Handles OBD2 Mode 09 (vehicle information)

##### get_J1939_sensors.c/h
- **Purpose**: Support for J1939 commercial vehicle protocol
- **Key Functions**:
  - `get_j1939_sensor_value()` - Extract J1939 parameter
  - `j1939_pgn_to_pid()` - Map J1939 PGN to OBD2-style PID
- **Integration**: Allows unified handling of J1939 and OBD2 data

#### CAN Processing Module (`/can_process/`)

##### can_man.c/h
- **Purpose**: CAN message management and routing
- **Key Functions**:
  - `init_can_manager()` - Initialize CAN management subsystem
  - `process_can_message()` - Route incoming CAN messages
  - `can_message_filter()` - Apply message filtering rules
  - `update_can_statistics()` - Track message rates and errors
- **Data Structures**:
  - `can_manager_t` - Main manager context
  - `can_filter_t` - Message filter definition
- **Integration**: Receives from CAN hardware, routes to OBD2 or signal extraction

##### vehicle_sensor_mappings.c/h
- **Purpose**: Map CAN signals to iMatrix sensor IDs
- **Key Functions**:
  - `init_sensor_mappings()` - Load mapping configuration
  - `can_signal_to_sensor()` - Convert CAN signal to sensor ID
  - `get_sensor_scaling()` - Get scaling factors for conversion
  - `apply_sensor_transform()` - Apply offset, scaling, limits
- **Data Structures**:
  - `sensor_mapping_t` - Maps CAN ID/signal to sensor
  - `transform_params_t` - Scaling, offset, min/max
- **Configuration**: Loaded from vehicle-specific config files

##### test_can_obd2.c/h
- **Purpose**: Test utilities for CAN and OBD2 functionality
- **Key Functions**:
  - `test_can_loopback()` - Verify CAN hardware operation
  - `test_obd2_simulator()` - Simulate OBD2 responses
  - `verify_pid_decode()` - Test PID decoder functions
- **Usage**: Development and manufacturing testing

##### pid_to_imatrix_map.h
- **Purpose**: Static mapping of OBD2 PIDs to iMatrix sensor IDs
- **Content**: Large lookup table with entries like:
  ```c
  {0x04, IMX_CONTROLS_ENGINE_LOAD},
  {0x05, IMX_CONTROLS_ENGINE_COOLANT_TEMPERATURE},
  {0x0C, IMX_CONTROLS_ENGINE_SPEED},
  ```
- **Usage**: Enables automatic sensor ID assignment for OBD2 data

#### Initialization Module (`/init/`)

##### init.c/h
- **Purpose**: Main system initialization coordinator
- **Key Functions**:
  - `system_init()` - Top-level initialization
  - `init_hardware()` - Initialize hardware peripherals
  - `init_software()` - Initialize software subsystems
  - `init_communications()` - Set up network interfaces
  - `verify_init_status()` - Check initialization success
- **Initialization Order**:
  1. Hardware (GPIO, timers, watchdog)
  2. Storage and configuration
  3. Communication interfaces
  4. Application layer
- **Error Handling**: Returns detailed error codes for failures

##### imx_client_init.c/h
- **Purpose**: Initialize iMatrix client framework integration
- **Key Functions**:
  - `imx_client_init()` - Main initialization entry point
  - `load_device_config()` - Load device-specific settings
  - `init_cloud_connection()` - Establish cloud connectivity
  - `register_data_handlers()` - Set up data upload callbacks
  - `configure_sensors()` - Initialize sensor configurations
- **Configuration Loading**:
  - Device serial number and credentials
  - Cloud endpoint URLs
  - Upload intervals and thresholds
- **Security**: Certificate loading and validation (with noted issues)

##### light_vehicle_config.c
- **Purpose**: Configuration for standard passenger vehicles
- **Sensor Count**: 51 sensors
- **Key Sensors**:
  ```c
  LIGHT_VEHICLE_SENSORS_LIST(X) \
    X(IMX_CONTROLS_ENGINE_OIL_PRESSURE,        0x7001023E, "Engine Oil Pressure") \
    X(IMX_CONTROLS_ENGINE_SPEED,                0x7001001F, "Engine Speed") \
    X(IMX_CONTROLS_ENGINE_COOLANT_TEMPERATURE,  0x70010115, "Coolant Temperature") \
    X(IMX_CONTROLS_VEHICLE_SPEED,               0x70010028, "Vehicle Speed") \
    X(IMX_CONTROLS_THROTTLE_POSITION,           0x70010183, "Throttle Position") \
    // ... 46 more sensors
  ```
- **Features**: Standard OBD2 PIDs, fuel system, emissions, diagnostics

##### j1939_vehicle_config.c
- **Purpose**: Configuration for commercial/heavy-duty vehicles
- **Sensor Count**: 57 sensors
- **Key Sensors**:
  ```c
  J1939_VEHICLE_SENSORS_LIST(X) \
    X(IMX_CONTROLS_ENGINE_PERCENT_LOAD,         0x7001005C, "Engine Percent Load") \
    X(IMX_CONTROLS_ENGINE_OIL_PRESSURE,         0x7001023E, "Engine Oil Pressure") \
    X(IMX_CONTROLS_ENGINE_OIL_TEMPERATURE,      0x7001023D, "Engine Oil Temperature") \
    X(IMX_CONTROLS_TRANSMISSION_OIL_TEMP,       0x700100B1, "Transmission Temperature") \
    X(IMX_CONTROLS_ENGINE_HOURS,                0x700100F5, "Engine Hours") \
    // ... 52 more sensors
  ```
- **Features**: J1939 PGNs, extended diagnostics, fleet-specific data

##### hm_wrecker_config.c
- **Purpose**: Configuration for Horizon Motors electric wrecker vehicles
- **Sensor Count**: 43 sensors
- **Key Sensors**:
  ```c
  HM_WRECKER_SENSORS_LIST(X) \
    X(IMX_CONTROLS_BATTERY_VOLTAGE,             0x70010021, "Battery Voltage") \
    X(IMX_CONTROLS_BATTERY_CURRENT,             0x70010174, "Battery Current") \
    X(IMX_CONTROLS_BATTERY_SOC,                 0x7001002A, "Battery State of Charge") \
    X(IMX_CONTROLS_MOTOR_TEMPERATURE,           0x700101A0, "Motor Temperature") \
    X(IMX_CONTROLS_INVERTER_TEMPERATURE,        0x700101A1, "Inverter Temperature") \
    // ... 38 more sensors
  ```
- **Features**: EV-specific parameters, battery management, motor control

##### wrp_config.c/h
- **Purpose**: Wireless router platform configuration
- **Key Functions**:
  - `wrp_load_config()` - Load WRP-specific settings
  - `wrp_get_network_mode()` - Get active network interface
  - `wrp_set_failover_priority()` - Configure network priorities
- **Features**: Multi-WAN support, failover configuration

##### local_heap.c/h
- **Purpose**: Local heap management for initialization
- **Key Functions**:
  - `local_heap_init()` - Initialize local memory pool
  - `local_heap_alloc()` - Allocate from local pool
  - `local_heap_free()` - Return memory to pool
- **Usage**: Temporary allocations during initialization

#### CLI Module (`/cli/`)

##### fcgw_cli.c/h
- **Purpose**: Fleet Connect Gateway command-line interface
- **Key Functions**:
  - `fcgw_cli_init()` - Initialize CLI subsystem
  - `fcgw_cli_process()` - Process CLI input
  - `fcgw_register_commands()` - Register command handlers
- **Commands**:
  - `can` - CAN bus diagnostics and control
  - `obd2` - OBD2 diagnostics and testing
  - `vehicle` - Vehicle configuration management
  - `status` - System status display
- **Integration**: Provides debug access to all subsystems

##### app_messages.h
- **Purpose**: CLI message strings and help text
- **Content**: 
  ```c
  #define CLI_MSG_WELCOME "Fleet Connect Gateway v1.0\r\n"
  #define CLI_MSG_HELP    "Available commands: help, status, can, obd2\r\n"
  #define CLI_MSG_ERROR   "Error: Invalid command\r\n"
  ```
- **Usage**: Centralized message management for consistency

#### HAL Module (`/hal/`)

##### Fleet_Connect.h
- **Purpose**: Main hardware abstraction layer header
- **Definitions**:
  - Hardware pin mappings
  - Peripheral configurations
  - System constants
- **Platform Support**: Abstracts differences between hardware platforms

##### accel_process.c/h
- **Purpose**: Accelerometer data processing
- **Key Functions**:
  - `accel_init()` - Initialize accelerometer
  - `accel_read()` - Read acceleration data
  - `detect_motion_events()` - Detect harsh braking, acceleration
  - `calculate_g_force()` - Convert to g-force units
- **Events Detected**: Hard braking, rapid acceleration, impacts, rollovers

##### gpio.c/h
- **Purpose**: GPIO control abstraction
- **Key Functions**:
  - `gpio_init()` - Initialize GPIO subsystem
  - `gpio_set_pin()` - Set output pin state
  - `gpio_read_pin()` - Read input pin state
  - `gpio_set_interrupt()` - Configure pin interrupts
- **Usage**: LED control, button inputs, hardware control signals

##### hal_leds.c/h
- **Purpose**: LED control abstraction
- **Key Functions**:
  - `led_init()` - Initialize LED subsystem
  - `led_set()` - Set LED state (on/off)
  - `led_blink()` - Start LED blinking
  - `led_pattern()` - Display pattern (error codes, status)
- **LED Mappings**: Status LED, error LED, communication LED

##### product_structure.h
- **Purpose**: Product-specific structure definitions
- **Content**:
  ```c
  typedef struct {
      uint32_t product_id;
      uint32_t hardware_version;
      uint32_t firmware_version;
      char serial_number[32];
  } product_info_t;
  ```

##### can_controller.h
- **Purpose**: CAN controller hardware abstraction
- **Definitions**: CAN controller types, speeds, pin mappings

##### fleet_connect_controller.h
- **Purpose**: Main controller definitions
- **Content**: System capabilities, feature flags, limits

#### Power Module (`/power/`)

##### process_power.c/h
- **Purpose**: Power management and monitoring
- **Key Functions**:
  - `power_init()` - Initialize power management
  - `monitor_battery_voltage()` - Track supply voltage
  - `enter_low_power_mode()` - Reduce power consumption
  - `schedule_wakeup()` - Set wakeup timer
  - `handle_power_event()` - Process power state changes
- **Features**: Sleep modes, battery monitoring, graceful shutdown

#### Product Module (`/product/`)

##### product.c/h
- **Purpose**: Product-specific implementation
- **Key Functions**:
  - `product_init()` - Initialize product features
  - `get_product_info()` - Return product identification
  - `product_self_test()` - Manufacturing self-test
- **Customization**: Product-specific behavior and features

##### hal_functions.c/h
- **Purpose**: Hardware abstraction layer implementations
- **Key Functions**:
  - `hal_get_unique_id()` - Read unique hardware ID
  - `hal_get_reset_reason()` - Determine last reset cause
  - `hal_feed_watchdog()` - Reset watchdog timer
  - `imx_get_network_traffic()` - Monitor network statistics
- **Network Monitoring**: Tracks bytes/packets for all interfaces

##### controls_def.c
- **Purpose**: Define available control outputs
- **Content**: Array of control definitions with IDs and names
- **Usage**: Maps control IDs to human-readable names

##### sensors_def.c
- **Purpose**: Define available sensor inputs
- **Content**: Array of sensor definitions with IDs, names, units
- **Usage**: Central sensor registry for the system

##### variables_def.c
- **Purpose**: Define system variables
- **Content**: Configuration variables, runtime parameters
- **Usage**: Tunable parameters without recompilation

#### Main Application

##### linux_gateway.c
- **Purpose**: Main application entry point
- **Key Functions**:
  - `main()` - Program entry point
  - `gateway_init()` - Initialize all subsystems
  - `main_loop()` - Main processing loop
  - `handle_shutdown()` - Graceful shutdown handler
- **Program Flow**:
  1. Parse command-line arguments
  2. Initialize subsystems
  3. Enter main processing loop
  4. Handle shutdown signals gracefully

##### do_everything.c/h
- **Purpose**: Main processing coordinator
- **Key Functions**:
  - `do_everything()` - Called from main loop
  - `process_vehicle_data()` - Handle vehicle communications
  - `process_cloud_sync()` - Upload data to cloud
  - `handle_commands()` - Process remote commands
- **Timing**: Manages processing intervals for different subsystems

### iMatrix Source Files

#### Control System (`/cs_ctrl/`)

##### memory_manager.c/h
- **Purpose**: Core memory management with tiered storage
- **Key Functions**:
  - `init_memory_manager()` - Initialize memory subsystem
  - `imx_sat_init()` - Initialize Sector Allocation Table
  - `imx_get_free_sector()` - Allocate a free sector
  - `free_sector()` - Release a sector
  - `read_rs()/write_rs()` - Raw sector I/O
  - `read_rs_safe()/write_rs_safe()` - Bounds-checked I/O
  - `process_memory()` - Tiered storage state machine
- **Tiered Storage States**:
  - `TIERED_IDLE` - Waiting for work
  - `TIERED_CHECK_THRESHOLD` - Check if migration needed
  - `TIERED_PREPARE_MIGRATION` - Select sectors to migrate
  - `TIERED_MIGRATE_TSD` - Migrate time-series data
  - `TIERED_MIGRATE_EVT` - Migrate event data
  - `TIERED_CLEANUP` - Remove migrated data from RAM
- **Features**: Automatic RAM-to-disk migration at 80% threshold

##### memory_manager_core.c/h
- **Purpose**: Core memory operations shared across platforms
- **Key Functions**:
  - `validate_sector()` - Check sector validity
  - `calculate_checksum()` - Compute data integrity checksum
  - `find_free_sector()` - Search for available sector
  - `mark_sector_used()` - Update allocation table
- **Data Structures**:
  - `sector_header_t` - Metadata for each sector
  - `allocation_table_t` - Tracks sector usage

##### memory_manager_disk.c/h
- **Purpose**: Disk-based storage tier implementation
- **Key Functions**:
  - `disk_storage_init()` - Initialize disk subsystem
  - `write_sector_to_disk()` - Save sector to file
  - `read_sector_from_disk()` - Load sector from file
  - `disk_sector_exists()` - Check if sector on disk
  - `delete_disk_sector()` - Remove sector file
- **File Format**: Binary files named by sector number
- **Path**: `/usr/qk/etc/sv/FC-1/history/`

##### memory_manager_recovery.c/h
- **Purpose**: Power failure recovery mechanisms
- **Key Functions**:
  - `perform_power_failure_recovery()` - Main recovery entry
  - `scan_disk_sectors()` - Find all sector files
  - `validate_sector_file()` - Check file integrity
  - `rebuild_allocation_table()` - Reconstruct RAM state
  - `move_corrupted_files()` - Quarantine bad sectors
- **Recovery Process**:
  1. Scan disk for sector files
  2. Validate each file's checksum
  3. Rebuild allocation tables
  4. Load recent data back to RAM

##### memory_manager_stats.c/h
- **Purpose**: Memory usage statistics and monitoring
- **Key Functions**:
  - `imx_get_memory_statistics()` - Get current stats
  - `update_usage_stats()` - Track allocations/frees
  - `calculate_fragmentation()` - Measure memory fragmentation
  - `get_peak_usage()` - Historical maximum usage
- **Statistics Tracked**:
  - Current/peak usage
  - Allocation/deallocation counts
  - Fragmentation percentage
  - Migration statistics

##### controls.c/h
- **Purpose**: Manage control outputs and actuators
- **Key Functions**:
  - `controls_init()` - Initialize control subsystem
  - `set_control()` - Set control output value
  - `get_control()` - Read current control state
  - `register_control_handler()` - Add control callback
- **Control Types**: Digital outputs, PWM, analog outputs

##### sensors.c/h
- **Purpose**: Manage sensor inputs and data collection
- **Key Functions**:
  - `sensors_init()` - Initialize sensor subsystem
  - `read_sensor()` - Get current sensor value
  - `register_sensor()` - Add new sensor
  - `set_sensor_limits()` - Configure alarms
  - `sensor_data_ready()` - Check for new data
- **Sensor Types**: Analog, digital, frequency, protocol-based

##### cs_memory_mgt.c/h
- **Purpose**: High-level memory configuration
- **Key Functions**:
  - `cs_build_config()` - Build memory configuration
  - `cs_memory_init()` - Initialize CS memory
  - `allocate_control_memory()` - Reserve control buffers
  - `allocate_sensor_memory()` - Reserve sensor buffers

##### hal_event.c/h
- **Purpose**: Hardware abstraction for event logging
- **Key Functions**:
  - `hal_log_event()` - Log system event
  - `hal_get_event_buffer()` - Access event storage
  - `hal_flush_events()` - Force event write

##### hal_sample.c/h
- **Purpose**: Hardware abstraction for data sampling
- **Key Functions**:
  - `hal_start_sampling()` - Begin data collection
  - `hal_read_samples()` - Get collected data
  - `hal_set_sample_rate()` - Configure sampling

#### CAN Bus Integration (`/canbus/`)

##### can_ring_buffer.c/h
- **Purpose**: Zero-allocation ring buffer for CAN messages
- **Key Functions**:
  - `can_ring_buffer_init()` - Initialize ring buffer
  - `can_ring_buffer_push()` - Add message (lock-free)
  - `can_ring_buffer_pop()` - Remove message (lock-free)
  - `can_ring_buffer_is_full()` - Check if full
  - `can_ring_buffer_get_free_count()` - Available space
- **Implementation**:
  ```c
  typedef struct {
      can_msg_t messages[CAN_RING_BUFFER_SIZE];
      volatile uint32_t head;
      volatile uint32_t tail;
      volatile uint32_t free_count;
      can_ring_buffer_stats_t stats;
  } can_ring_buffer_t;
  ```
- **Features**: Lock-free atomic operations, statistics tracking

##### can_verify.c/h
- **Purpose**: Verify CAN signal to sensor mappings
- **Key Functions**:
  - `can_verify_configuration()` - Main verification entry
  - `verify_signal_mappings()` - Check signal→sensor maps
  - `find_duplicate_mappings()` - Detect conflicts
  - `find_orphaned_sensors()` - Sensors with no signals
  - `print_verification_report()` - Output results
- **Verification Checks**:
  1. All signals map to valid sensors
  2. No duplicate mappings
  3. No orphaned sensors
  4. Valid IMX IDs (not 0 or 0xFFFFFFFF)
  5. Reasonable value ranges

##### can_process.c/h
- **Purpose**: Core CAN message processing
- **Key Functions**:
  - `can_process_init()` - Initialize processor
  - `can_process_message()` - Process single message
  - `extract_signals()` - Extract signals from data
  - `update_sensor_values()` - Update sensor readings
- **Processing Flow**:
  1. Receive CAN message
  2. Match against configured messages
  3. Extract signals based on bit positions
  4. Apply scaling and offset
  5. Update sensor values

##### can_signal_extraction.c/h
- **Purpose**: Extract signals from CAN message data
- **Key Functions**:
  - `extract_signal()` - Extract single signal
  - `pack_signal()` - Pack signal into message
  - `apply_scaling()` - Apply factor and offset
  - `check_signal_bounds()` - Validate signal value
- **Bit Manipulation**: Handles Intel/Motorola byte order, bit packing

##### can_server.c/h
- **Purpose**: CAN bus server managing multiple interfaces
- **Key Functions**:
  - `can_server_init()` - Initialize server
  - `can_server_start()` - Start CAN threads
  - `can_server_rx_thread()` - Receive thread
  - `can_server_tx_thread()` - Transmit thread
  - `can_server_stop()` - Shutdown server
- **Interfaces Supported**: CAN0, CAN1, CAN-over-Ethernet

##### can_init.c/h
- **Purpose**: CAN subsystem initialization
- **Key Functions**:
  - `can_init()` - Initialize CAN hardware
  - `can_set_bitrate()` - Configure bus speed
  - `can_set_filters()` - Configure hardware filters
  - `can_enable()` - Enable CAN controller

##### can_utils.c/h
- **Purpose**: CAN utility functions
- **Key Functions**:
  - `can_id_to_string()` - Format CAN ID for display
  - `can_data_to_hex()` - Convert data to hex string
  - `calculate_can_dlc()` - Compute data length code
  - `validate_can_message()` - Check message validity

##### can_imx_upload.c/h
- **Purpose**: Upload CAN data to iMatrix cloud
- **Key Functions**:
  - `can_upload_init()` - Initialize uploader
  - `queue_can_data()` - Add data to upload queue
  - `process_upload_queue()` - Send queued data
  - `format_can_telemetry()` - Format for cloud

#### CLI Module (`/cli/`)

##### cli.c/h
- **Purpose**: Main CLI processing engine
- **Key Functions**:
  - `cli_init()` - Initialize CLI subsystem
  - `cli_process_ch()` - Process input character
  - `cli_execute_command()` - Run command handler
  - `cli_printf()` - Formatted output
  - `cli_register_command()` - Add new command
- **Features**: Command history, tab completion, help system

##### cli_memory_monitor.c/h
- **Purpose**: Interactive memory allocation monitor
- **Key Functions**:
  - `cli_memory_monitor()` - Main monitor entry
  - `display_allocations()` - Show current allocations
  - `update_display()` - Refresh screen
  - `handle_monitor_input()` - Process user commands
  - `search_allocations()` - Find specific allocations
- **Display Features**:
  - Color coding by age and size
  - File/line tracking
  - Navigation (page up/down)
  - Search functionality
  - Statistics display

##### cli_file_viewer.c/h
- **Purpose**: Browse file system from CLI
- **Key Functions**:
  - `cli_file_viewer()` - Main viewer entry
  - `list_directory()` - Show directory contents
  - `view_file()` - Display file contents
  - `navigate_filesystem()` - Change directories
  - `search_files()` - Find files by pattern
- **Features**: Tree view, hex dump, text view, file operations

##### cli_canbus.c/h
- **Purpose**: CAN bus diagnostics and control
- **Key Functions**:
  - `cli_can_status()` - Display CAN statistics
  - `cli_can_send()` - Transmit CAN message
  - `cli_can_monitor()` - Live message display
  - `cli_can_verify()` - Run configuration verification
  - `cli_can_filter()` - Configure filters
- **Subcommands**: status, send, monitor, verify, filter

##### cli_coap.c/h
- **Purpose**: CoAP protocol testing and diagnostics
- **Key Functions**:
  - `cli_coap_get()` - Send GET request
  - `cli_coap_post()` - Send POST request
  - `cli_coap_discover()` - Resource discovery
  - `cli_coap_observe()` - Subscribe to resource
- **Features**: Interactive CoAP client for testing

##### cli_debug.c/h
- **Purpose**: Debug commands and diagnostics
- **Key Functions**:
  - `cli_debug_memory()` - Memory diagnostics
  - `cli_debug_threads()` - Thread information
  - `cli_debug_stack()` - Stack usage analysis
  - `cli_debug_registers()` - CPU register dump
- **Usage**: Low-level system debugging

##### cli_status.c/h
- **Purpose**: System status display
- **Key Functions**:
  - `cli_status()` - Main status display
  - `show_system_info()` - Hardware/software versions
  - `show_network_status()` - Network interfaces
  - `show_memory_status()` - Memory usage
  - `show_uptime()` - System uptime
- **Information Displayed**: Comprehensive system overview

#### CoAP Protocol (`/coap/`)

##### coap.c/h
- **Purpose**: Core CoAP protocol implementation (RFC 7252)
- **Key Functions**:
  - `process_coap_msg()` - Process incoming message
  - `coap_store_response_header()` - Build response
  - `coap_msg_type()` - Get message type
  - `coap_response_code()` - Get response code
  - `add_coap_option()` - Add option to message
- **Message Types**: CON, NON, ACK, RST
- **Features**: Options, payloads, block transfer support

##### coap_recv.c/h
- **Purpose**: CoAP message reception and parsing
- **Key Functions**:
  - `coap_recv_init()` - Initialize receiver
  - `coap_recv_packet()` - Receive UDP packet
  - `parse_coap_message()` - Parse binary format
  - `validate_coap_message()` - Check validity
  - `dispatch_coap_message()` - Route to handler

##### coap_xmit.c/h
- **Purpose**: CoAP message transmission
- **Key Functions**:
  - `coap_xmit()` - Send CoAP message
  - `coap_send_ack()` - Send acknowledgment
  - `coap_send_reset()` - Send reset
  - `queue_retransmission()` - Handle retries
  - `calculate_backoff()` - Exponential backoff

##### imx_coap.c/h
- **Purpose**: iMatrix-specific CoAP extensions
- **Key Functions**:
  - `imx_coap_init()` - Initialize iMatrix CoAP
  - `register_imx_resources()` - Add iMatrix resources
  - `handle_sensor_get()` - GET sensor value
  - `handle_control_post()` - POST control command
  - `handle_config_put()` - PUT configuration
- **Resources**: /sensors/*, /controls/*, /config/*

##### coap_token.c/h
- **Purpose**: CoAP token management
- **Key Functions**:
  - `generate_token()` - Create unique token
  - `save_token_context()` - Store for matching
  - `find_token_context()` - Lookup by token
  - `cleanup_old_tokens()` - Remove expired
- **Usage**: Match requests with responses

##### coap_reliable_udp.c/h
- **Purpose**: Reliable transmission over UDP
- **Key Functions**:
  - `send_reliable()` - Send with retransmission
  - `handle_timeout()` - Retransmission timeout
  - `update_rtt()` - Round-trip time estimation
  - `congestion_control()` - Avoid overload
- **Algorithm**: RFC 7252 congestion control

##### imx_requests.c/h
- **Purpose**: Handle incoming CoAP requests
- **Key Functions**:
  - `process_get_request()` - Handle GET
  - `process_post_request()` - Handle POST
  - `process_put_request()` - Handle PUT
  - `process_delete_request()` - Handle DELETE
  - `send_response()` - Send CoAP response

##### imx_response_handler.c/h
- **Purpose**: Process CoAP responses
- **Key Functions**:
  - `handle_coap_response()` - Process response
  - `match_response_to_request()` - Token matching
  - `process_observe_notification()` - Handle updates
  - `handle_block_response()` - Block transfer

#### BLE Module (`/ble/`)

##### imx_ble_server.c/h
- **Purpose**: BLE GATT server implementation
- **Key Functions**:
  - `ble_server_init()` - Initialize GATT server
  - `ble_server_start()` - Start advertising
  - `handle_gatt_read()` - Process read requests
  - `handle_gatt_write()` - Process write requests
  - `send_notification()` - Push updates to clients
- **Services**: Device info, configuration, data transfer

##### imx_ble_connection_handler.c/h
- **Purpose**: Manage BLE connections
- **Key Functions**:
  - `on_connection()` - New connection handler
  - `on_disconnection()` - Disconnection handler
  - `manage_connection_params()` - Optimize parameters
  - `handle_security_request()` - Pairing/bonding
- **Connection Management**: Multiple simultaneous connections

##### imx_ble_device_utility.c/h
- **Purpose**: BLE device discovery and management
- **Key Functions**:
  - `start_ble_scan()` - Begin scanning
  - `process_advertisement()` - Parse ad data
  - `connect_to_device()` - Initiate connection
  - `read_device_info()` - Get device details
- **Device Types**: Beacons, sensors, controllers

##### cli_ble.c/h
- **Purpose**: BLE diagnostics via CLI
- **Key Functions**:
  - `cli_ble_scan()` - Scan for devices
  - `cli_ble_connect()` - Connect to device
  - `cli_ble_read()` - Read characteristic
  - `cli_ble_write()` - Write characteristic
  - `cli_ble_monitor()` - Monitor notifications

#### Networking Module (`/networking/`)

##### process_network.c (Linux Platform)
- **Purpose**: Network interface failover state machine
- **Key Functions**:
  - `process_network()` - Main state machine
  - `check_interface_status()` - Test connectivity
  - `execute_ping()` - Ping connectivity test
  - `switch_to_interface()` - Change active interface
  - `update_routing_table()` - Modify routes
- **State Machine**:
  - `CHECK_ETH0` - Test ethernet
  - `USE_ETH0` - Using ethernet
  - `CHECK_WLAN0` - Test WiFi
  - `USE_WLAN0` - Using WiFi
  - `CHECK_PPP0` - Test cellular
  - `USE_PPP0` - Using cellular
- **Security Issues**: Command injection vulnerabilities identified

##### utility.c/h
- **Purpose**: Network utility functions
- **Key Functions**:
  - `get_ip_address()` - Get interface IP
  - `get_mac_address()` - Get interface MAC
  - `resolve_hostname()` - DNS lookup
  - `check_port_open()` - TCP port check
  - `get_network_stats()` - Interface statistics

##### keep_alive.c/h
- **Purpose**: Network connection monitoring
- **Key Functions**:
  - `keepalive_init()` - Initialize monitoring
  - `send_keepalive()` - Send heartbeat
  - `check_keepalive_timeout()` - Detect disconnection
  - `handle_keepalive_response()` - Process response

#### WiFi Module (`/wifi/`)

##### imx_wifi.c/h
- **Purpose**: High-level WiFi management
- **Key Functions**:
  - `imx_wifi_init()` - Initialize WiFi subsystem
  - `imx_wifi_connect()` - Connect to access point
  - `imx_wifi_disconnect()` - Disconnect from AP
  - `imx_wifi_get_status()` - Connection status
  - `imx_set_setup_mode()` - Enter AP mode for setup
- **Features**: WPA/WPA2, Enterprise auth, multiple profiles

##### wifi_connect.c/h
- **Purpose**: WiFi connection management
- **Key Functions**:
  - `wifi_connect_to_ap()` - Connect to specific AP
  - `wifi_try_saved_networks()` - Auto-connect
  - `wifi_save_credentials()` - Store network info
  - `wifi_handle_auth_failure()` - Auth error handling

##### wifi_scan.c/h
- **Purpose**: WiFi network scanning
- **Key Functions**:
  - `wifi_start_scan()` - Initiate scan
  - `wifi_get_scan_results()` - Get found APs
  - `wifi_find_best_ap()` - Select optimal AP
  - `parse_scan_result()` - Extract AP info

##### enterprise_80211.c/h
- **Purpose**: WPA Enterprise authentication
- **Key Functions**:
  - `setup_enterprise_auth()` - Configure EAP
  - `load_certificates()` - Load client certs
  - `handle_eap_request()` - Process EAP
  - `validate_server_cert()` - Server validation
- **EAP Methods**: EAP-TLS, PEAP, EAP-TTLS

#### Device Configuration (`/device/`)

##### config.c/h
- **Purpose**: Device configuration management
- **Key Functions**:
  - `imatrix_load_config()` - Load from storage
  - `imatrix_save_config()` - Persist changes
  - `imx_config_read_item()` - Get config value
  - `imx_config_write_item()` - Set config value
  - `config_factory_reset()` - Restore defaults
- **Configuration Items**: Network settings, cloud endpoints, device identity

##### system_init.c/h
- **Purpose**: System initialization coordinator
- **Key Functions**:
  - `system_early_init()` - Pre-boot initialization
  - `system_init()` - Main initialization
  - `init_peripherals()` - Hardware setup
  - `load_system_config()` - Load configuration
  - `verify_system_ready()` - Check init success

##### hal_ble.c/h
- **Purpose**: BLE hardware abstraction
- **Key Functions**:
  - `hal_ble_init()` - Initialize BLE hardware
  - `hal_ble_set_tx_power()` - Set transmit power
  - `hal_ble_get_mac()` - Get BLE MAC address
  - `hal_ble_reset()` - Reset BLE subsystem

##### hal_wifi.c/h
- **Purpose**: WiFi hardware abstraction
- **Key Functions**:
  - `hal_wifi_init()` - Initialize WiFi hardware
  - `hal_wifi_set_mode()` - Set STA/AP mode
  - `hal_wifi_get_mac()` - Get WiFi MAC address
  - `hal_wifi_set_power_save()` - Configure power

#### Upload Module (`/imatrix_upload/`)

##### imatrix_upload.c/h
- **Purpose**: Main data upload coordinator
- **Key Functions**:
  - `start_imatrix()` - Start upload service
  - `imatrix_upload()` - Main upload loop
  - `queue_sensor_data()` - Add data to queue
  - `process_upload_queue()` - Send queued data
  - `handle_upload_response()` - Process cloud response
- **Upload Strategy**: Batch uploads, compression, retry logic

##### add_internal.c/h
- **Purpose**: Format internal data for upload
- **Key Functions**:
  - `add_sensor_reading()` - Add sensor data
  - `add_event_data()` - Add event record
  - `add_diagnostic_data()` - Add diagnostics
  - `format_upload_payload()` - Create upload packet
- **Data Types**: Time-series, events, diagnostics, logs

##### logging.c/h
- **Purpose**: Upload-specific logging
- **Key Functions**:
  - `log_upload_attempt()` - Record attempt
  - `log_upload_success()` - Record success
  - `log_upload_failure()` - Record failure
  - `get_upload_statistics()` - Get stats
- **Metrics**: Success rate, data volume, latency

#### Location Module (`/location/`)

##### location.c/h
- **Purpose**: Location services coordinator
- **Key Functions**:
  - `location_init()` - Initialize location services
  - `get_current_location()` - Get GPS position
  - `update_location()` - Process new GPS data
  - `calculate_distance()` - Distance between points
  - `location_subscribe()` - Register for updates

##### process_nmea.c/h
- **Purpose**: NMEA GPS sentence parsing
- **Key Functions**:
  - `parse_nmea_sentence()` - Parse NMEA string
  - `parse_gga()` - Parse GGA sentence
  - `parse_rmc()` - Parse RMC sentence
  - `validate_checksum()` - Verify NMEA checksum
- **Sentences**: GGA, RMC, GSA, GSV, VTG

##### geofence.c/h
- **Purpose**: Geofencing implementation
- **Key Functions**:
  - `geofence_init()` - Initialize geofencing
  - `add_geofence()` - Create new fence
  - `check_geofences()` - Test current position
  - `handle_fence_event()` - Process enter/exit
- **Fence Types**: Circular, polygonal, route-based

##### gps_stationary_detection.c/h
- **Purpose**: Detect when vehicle is stationary
- **Key Functions**:
  - `init_stationary_detection()` - Initialize detector
  - `update_position()` - Feed new GPS data
  - `is_stationary()` - Check if stopped
  - `get_stationary_duration()` - Time stopped
- **Algorithm**: Speed and position variance analysis

## Core Components

### 1. OBD2 Implementation

The OBD2 system provides comprehensive vehicle diagnostics:

**Key Features:**
- ISO-15765-2 compliant transport layer
- Multi-frame message segmentation and reassembly
- Flow control management
- Support for both 11-bit and 29-bit CAN addressing
- Automatic PID discovery and availability mapping
- Efficient binary search for supported PIDs

**Implementation Files:**
- `process_obd2.c`: Main state machine and processing logic
- `i15765.c`: ISO-15765 transport protocol
- `decode_mode_01_pids_*.c`: PID decoders organized by ranges (01-1F, 21-3F, etc.)
- `process_pid_data.c`: Generic PID data processing

### 2. CAN Bus Processing

Advanced CAN message handling with performance optimizations:

**Key Features:**
- Ring buffer implementation for zero-allocation operation
- Support for 3 simultaneous CAN buses
- Signal extraction from CAN frames
- Configurable message filtering
- CAN FD support (up to 64-byte frames)
- Real-time signal-to-sensor mapping

**Implementation:**
```c
// Ring buffer structure for efficient CAN message handling
typedef struct {
    can_msg_t messages[CAN_RING_BUFFER_SIZE];
    uint32_t head;
    uint32_t tail;
    uint32_t free_count;
    can_ring_buffer_stats_t stats;
} can_ring_buffer_t;
```

### 3. Memory Management System

Tiered storage system with automatic overflow to disk:

**Architecture:**
- **Tier 1**: RAM-based sectors for fast access
- **Tier 2**: Disk-based storage for overflow
- **Automatic Migration**: When RAM usage exceeds 80%
- **Power Failure Recovery**: Complete data recovery on startup

**Key Functions:**
- `process_memory()`: Background processing for tier management
- `write_tsd_evt()`: Write time-series data
- `read_tsd_evt()`: Read time-series data
- `imx_get_free_sector()`: Allocate storage sectors

### 4. Network Failover System

Sophisticated network management with automatic failover:

**State Machine:**
```
INIT → CHECK_ETH0 → USE_ETH0
  ↓        ↓           ↓
  └→ CHECK_WLAN0 → USE_WLAN0
         ↓           ↓
         └→ CHECK_PPP0 → USE_PPP0
```

**Features:**
- Ping-based connectivity testing
- Automatic interface switching
- DNS-based connectivity verification
- Configurable retry and timeout parameters

### 5. Security Framework

Comprehensive security measures throughout the system:

**Implemented Security Features:**
- Buffer overflow protection with bounds checking
- Input validation for all external data
- Secure string handling (strncpy, snprintf)
- Memory safety with NULL pointer checks
- Certificate-based authentication (pending fixes)
- Encrypted communication channels

## Implementation Details

### Vehicle Configuration System

Uses X-macro pattern for maintainable sensor definitions:

```c
// Example: Light vehicle configuration
#define LIGHT_VEHICLE_SENSORS_LIST(X) \
    X(IMX_CONTROLS_ENGINE_OIL_PRESSURE,        0x7001023E, "Engine Oil Pressure") \
    X(IMX_CONTROLS_ENGINE_SPEED,                0x7001001F, "Engine Speed") \
    X(IMX_CONTROLS_ENGINE_COOLANT_TEMPERATURE,  0x70010115, "Coolant Temperature") \
    // ... 48 more sensors

// Automatic array generation
light_vehicle_config_t light_vehicle_config = {
    .sensor_count = 51,
    .sensors = {
        LIGHT_VEHICLE_SENSORS_LIST(SENSOR_ENTRY)
    }
};
```

### CAN Signal Verification

Comprehensive verification system for configuration validation:

```c
// Verification process
can_verification_result_t verify_can_configuration(void) {
    // 1. Check all signals map to valid sensors
    // 2. Detect duplicate mappings
    // 3. Find orphaned sensors
    // 4. Validate IMX IDs
    // 5. Report ignored signals
    
    return (can_verification_result_t){
        .total_signals = count,
        .mapped_signals = mapped,
        .unmapped_signals = unmapped,
        .duplicate_mappings = duplicates,
        .orphaned_sensors = orphaned,
        .verification_passed = (unmapped == 0 && duplicates == 0)
    };
}
```

### Memory Monitor CLI

Interactive memory monitoring with real-time updates:

**Features:**
- Color-coded allocation display (age and size based)
- File/line tracking for leak detection
- Heap fragmentation analysis
- Search and navigation capabilities
- Memory pool statistics

**Usage:**
```bash
# Start memory monitor
> memory monitor

# Display shows:
# [Age] [Size] [Location] [Address]
# Where colors indicate:
# - Red: Large allocations (>10KB)
# - Yellow: Medium allocations (1-10KB)
# - Green: Small allocations (<1KB)
# - Cyan: Very recent (<1 second)
```

## Security Analysis

### Completed Security Fixes

1. **Buffer Overflow Vulnerabilities** (FIXED)
   - OBD2 processing: Replaced sprintf with snprintf
   - String operations: Added null termination guarantees
   - Memory operations: Comprehensive bounds checking

2. **Memory Safety Improvements** (IMPLEMENTED)
   - NULL pointer validation before all operations
   - Size validation for memory allocations
   - Safe string handling throughout

3. **Input Validation** (ENHANCED)
   - Network traffic parsing validation
   - CAN message length verification
   - Configuration parameter validation

### Pending Security Issues

1. **Critical: Command Injection in Network Code**
   - Location: `process_network.c`
   - Risk: Remote code execution via interface names
   - Status: Immediate patching required

2. **Critical: Certificate Validation Bypass**
   - Location: `enc_utils.c`
   - Risk: MITM attacks possible
   - Status: Awaiting implementation

3. **High: Debug Information Exposure**
   - Location: Build configuration
   - Risk: Credential exposure in logs
   - Status: Build system update needed

### Security Roadmap

**Phase 1** (Immediate - 24-48 hours):
- Fix command injection vulnerabilities
- Implement input validation framework
- Add buffer overflow protection

**Phase 2** (1 week):
- Fix certificate validation
- Remove debug information from production
- Thread safety improvements

**Phase 3** (2-4 weeks):
- Complete security architecture review
- Implement automated security testing
- Third-party security audit

## Recent Enhancements

### 2025-01-11: Memory Management Overhaul

**Problem Solved:** 1500+ allocations per second causing memory tracking overflow

**Solution Implemented:**
- Ring buffer system for CAN messages
- Zero-allocation design during normal operation
- Memory monitor for real-time tracking
- Comprehensive leak detection and fixing

**Results:**
- Memory allocations: 1500/sec → 0/sec
- Memory leaks fixed: 31 (~6KB recovered)
- System stability significantly improved

### 2025-07-01: Vehicle Configuration Refactoring

**Problem Solved:** Manual sensor counting prone to errors

**Solution Implemented:**
- X-macro pattern for all vehicle configurations
- Automatic array generation from macro lists
- Single source of truth for sensor definitions

**Results:**
- Eliminated manual counting errors
- Improved maintainability
- Easier sensor additions/removals

### 2025-07-02: Network Security Analysis

**Findings:**
- Critical command injection vulnerabilities
- Buffer overflow risks in network code
- Thread safety issues in failover system

**Impact:**
- Security risk level escalated to CRITICAL
- Immediate patching required before deployment

## Integration Guide

### Quick Start Integration

1. **System Initialization:**
```c
// Initialize platform
imx_platform_init();

// Initialize memory manager
init_memory_manager();

// Perform power failure recovery
perform_power_failure_recovery();

// Initialize vehicle configuration
init_vehicle_config(VEHICLE_TYPE_LIGHT);

// Start OBD2 processing
init_obd2_system();
```

2. **Main Processing Loop:**
```c
void main_loop(void) {
    imx_time_t current_time;
    
    while (system_running) {
        imx_time_get_time(&current_time);
        
        // Process memory management
        process_memory(current_time);
        
        // Process CAN messages
        process_can_messages();
        
        // Process OBD2 data
        process_obd2(current_time);
        
        // Handle network communication
        process_network_messages();
        
        imx_delay_milliseconds(10);
    }
}
```

3. **Shutdown Sequence:**
```c
void system_shutdown(void) {
    // Flush data to disk
    flush_all_to_disk();
    
    // Wait for completion
    while (get_pending_disk_write_count() > 0) {
        process_memory(current_time);
        imx_delay_milliseconds(100);
    }
    
    // Clean shutdown
    cleanup_can_system();
    cleanup_network();
}
```

### Configuration Examples

**CAN Bus Configuration:**
```c
can_config_t can_config = {
    .bus_count = 3,
    .buses = {
        {.speed = 500000, .type = CAN_STANDARD},
        {.speed = 250000, .type = CAN_STANDARD},
        {.speed = 125000, .type = CAN_J1939}
    }
};
```

**Network Configuration:**
```c
network_config_t net_config = {
    .primary_interface = "eth0",
    .fallback_interfaces = {"wlan0", "ppp0"},
    .ping_timeout_ms = 5000,
    .retry_count = 3
};
```

## Development Guidelines

### Coding Standards

1. **Memory Safety:**
   - Always use bounded string functions (strncpy, snprintf)
   - Validate all input parameters
   - Check allocation returns
   - Free resources in reverse allocation order

2. **Error Handling:**
   - Return explicit error codes
   - Log errors with context
   - Graceful degradation on failures
   - Never ignore error returns

3. **Documentation:**
   - Doxygen comments for all public functions
   - Inline comments for complex logic
   - Update documentation with code changes
   - Include usage examples

### Build System

**CMake Build Process:**
```bash
# Create build directory
mkdir build && cd build

# Configure build
cmake ..

# Build project
make -j$(nproc)

# Run tests
make test
```

**Build Options:**
- `CAN_PLATFORM`: Enable CAN functionality
- `DEBUG_BUILD`: Enable debug logging
- `PRODUCTION_BUILD`: Disable debug features

### Testing Requirements

1. **Unit Tests:**
   - All new functions must have tests
   - Edge case coverage required
   - Memory leak testing mandatory

2. **Integration Tests:**
   - CAN bus communication
   - Network failover scenarios
   - Power failure recovery

3. **Security Tests:**
   - Input fuzzing
   - Buffer overflow testing
   - Penetration testing

## Current Status and Roadmap

### Current Status (2025-01-17)

**Security Risk Level:** CRITICAL (due to network vulnerabilities)

**Completed:**
- ✅ Critical buffer overflow fixes
- ✅ Memory management overhaul
- ✅ Vehicle configuration refactoring
- ✅ CAN signal verification system
- ✅ Memory monitoring implementation

**Pending Critical Fixes:**
- ❌ Command injection in network code
- ❌ Certificate validation bypass
- ❌ Debug information exposure
- ❌ Thread safety issues

### Development Roadmap

**Q1 2025:**
- Complete critical security fixes
- Implement automated testing
- Third-party security audit
- Production deployment readiness

**Q2 2025:**
- Enhanced vehicle support
- Advanced diagnostics features
- Cloud analytics integration
- Performance optimizations

**Q3 2025:**
- Machine learning integration
- Predictive maintenance features
- Extended protocol support
- Mobile application development

**Q4 2025:**
- Full production rollout
- Multi-region deployment
- Advanced fleet analytics
- API ecosystem development

### Production Deployment Gates

1. **Gate 1:** Critical security vulnerabilities resolved ❌
2. **Gate 2:** Comprehensive testing completed ⏳
3. **Gate 3:** Security audit passed ⏳
4. **Gate 4:** Performance benchmarks met ⏳
5. **Gate 5:** Documentation complete ✅

## Conclusion

Fleet Connect represents a comprehensive, enterprise-grade fleet management solution combining robust vehicle diagnostics with modern IoT connectivity. While significant progress has been made in functionality and initial security hardening, critical security vulnerabilities in the network management system require immediate attention before production deployment.

The modular architecture, comprehensive platform support, and advanced features like tiered storage and zero-allocation CAN processing position Fleet Connect as a competitive solution in the fleet management market. With the completion of the security roadmap and planned enhancements, the system will provide a secure, scalable, and feature-rich platform for fleet operations.

### Key Strengths
- Comprehensive vehicle protocol support (OBD2, J1939)
- Multi-platform architecture (embedded and gateway)
- Advanced memory management with tiered storage
- Robust network failover capabilities
- Extensive diagnostic and monitoring tools

### Areas for Improvement
- Critical security vulnerabilities require immediate patching
- Thread safety needs comprehensive review
- Certificate validation must be properly implemented
- Production build hardening needed

### Recommended Next Steps
1. Execute emergency security patches (24-48 hours)
2. Complete security audit and penetration testing
3. Implement automated security testing in CI/CD
4. Prepare for production deployment with monitoring

---

*This document represents the current state of the Fleet Connect project as of January 17, 2025. For the latest updates, refer to the project repository and tracking documents.*