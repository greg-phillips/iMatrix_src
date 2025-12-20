# Fleet-Connect-1 Architecture Documentation

**Document Version**: 1.0
**Date**: 2025-12-08
**Status**: Reference Documentation
**Codebase Size**: ~68,738 lines of C code
**Platform**: Linux-based embedded systems (ARM/x86)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Directory Structure](#3-directory-structure)
4. [Main Entry Points and Initialization](#4-main-entry-points-and-initialization)
5. [State Machines](#5-state-machines)
6. [Module Structure](#6-module-structure)
7. [Communication Subsystems](#7-communication-subsystems)
8. [Memory Management (MM2)](#8-memory-management-mm2)
9. [Cloud Upload System](#9-cloud-upload-system)
10. [Data Structures](#10-data-structures)
11. [Key APIs and Interfaces](#11-key-apis-and-interfaces)
12. [Configuration System](#12-configuration-system)
13. [Debugging and Diagnostics](#13-debugging-and-diagnostics)
14. [Vehicle Support](#14-vehicle-support)
15. [Build System](#15-build-system)

---

## 1. Executive Summary

### 1.1 System Purpose

Fleet-Connect-1 is a comprehensive vehicular telematics gateway platform designed for:

- **Vehicle Data Collection**: Real-time acquisition of CAN bus messages, OBD2 diagnostics, and J1939 heavy vehicle data
- **Sensor Integration**: BLE (Bluetooth Low Energy) sensor connectivity for environmental and auxiliary monitoring
- **Multi-Interface Communication**: Intelligent failover across 4G cellular, WiFi, and Ethernet networks
- **Cloud Connectivity**: Secure data upload to the iMatrix IoT platform via CoAP protocol
- **Driver Analytics**: Behavior scoring, trip tracking, and energy management
- **Regulatory Compliance**: CARB (California Air Resources Board) energy tracking for electric vehicles

### 1.2 Key Features

| Feature | Description |
|---------|-------------|
| **CAN Bus Processing** | Multi-bus support (CAN0, CAN1, Ethernet CAN), DBC-based signal extraction |
| **OBD2 Diagnostics** | ISO 15765-2 transport, Mode 01/09 PIDs, multi-ECU discovery |
| **BLE Sensors** | GATT client, sensor discovery, Kalman-filtered RSSI tracking |
| **Network Manager** | Intelligent interface selection with scoring and hysteresis |
| **Memory Manager** | Tiered RAM/disk storage with 75% space efficiency |
| **Cloud Upload** | CoAP protocol, batched data transmission, hash validation |
| **Energy Tracking** | EV battery monitoring, charging session tracking, CARB compliance |
| **Driver Scoring** | Trip segmentation, behavior analysis, feedback generation |

### 1.3 Target Platforms

- **Primary**: QConnect ARM-based gateways (musl libc)
- **Development**: Linux x86/x64 (glibc)
- **Supported Hardware**: CAN controllers, cellular modems, WiFi/BLE radios, GPS receivers

### 1.4 Key Metrics

- **Main Loop Frequency**: 100ms (10 Hz)
- **CAN Hash Lookup**: O(1) with 256-bucket hash table
- **Memory Efficiency**: 75% (24 data bytes per 32-byte sector)
- **Interface Scoring**: 0-10 scale with ping-based verification

---

## 2. System Architecture Overview

### 2.1 High-Level Block Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLEET-CONNECT-1 GATEWAY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     MAIN PROCESSING LOOP (100ms)                     │    │
│  │                        do_everything.c                               │    │
│  │   ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐    │    │
│  │   │ Reboot  │  GPS    │  GPIO   │ Accel   │ Power   │  CAN    │    │    │
│  │   │ Check   │ Event   │  Read   │ Process │ Process │ Product │    │    │
│  │   └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬────┘    │    │
│  │        │         │         │         │         │         │          │    │
│  │   ┌────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┐    │    │
│  │   │  OBD2   │  EV     │ Gateway │  Trip   │  CAN    │  CLI    │    │    │
│  │   │ Process │  Val    │ Sample  │ Energy  │ Debug   │ Monitor │    │    │
│  │   └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    SENSOR DATABASE (mgs.csd[])                        │   │
│  │              Control Sensor Block Arrays - Central Storage            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│           │              │              │              │                     │
│           ▼              ▼              ▼              ▼                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │    CAN     │  │    BLE     │  │   OBD2     │  │    GPS     │            │
│  │  Subsystem │  │  Subsystem │  │  Subsystem │  │  Subsystem │            │
│  │            │  │            │  │            │  │            │            │
│  │ ┌────────┐ │  │ ┌────────┐ │  │ ┌────────┐ │  │ ┌────────┐ │            │
│  │ │ CAN0   │ │  │ │ GATT   │ │  │ │ISO15765│ │  │ │  NMEA  │ │            │
│  │ │ CAN1   │ │  │ │ Client │ │  │ │  PIDs  │ │  │ │ Parser │ │            │
│  │ │CAN_ETH │ │  │ │ Server │ │  │ │  VIN   │ │  │ │Geofence│ │            │
│  │ └────────┘ │  │ └────────┘ │  │ └────────┘ │  │ └────────┘ │            │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘            │
│           │              │              │              │                     │
│           └──────────────┴──────────────┴──────────────┘                     │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     MEMORY MANAGER (MM2 v2.8)                         │   │
│  │              ┌─────────────────┬─────────────────┐                    │   │
│  │              │   RAM TIER      │   DISK TIER     │                    │   │
│  │              │   (64KB Pool)   │  (Spillover)    │                    │   │
│  │              │                 │                  │                    │   │
│  │              │  TSD Records    │  TSD Records    │                    │   │
│  │              │  EVT Records    │  EVT Records    │                    │   │
│  │              └─────────────────┴─────────────────┘                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    IMATRIX UPLOAD SYSTEM                              │   │
│  │                                                                        │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐   │   │
│  │  │   CoAP      │───▶│   Message   │───▶│    NETWORK MANAGER      │   │   │
│  │  │  Protocol   │    │   Queue     │    │                         │   │   │
│  │  │  RFC 7252   │    │             │    │  ┌─────┬─────┬─────┐   │   │   │
│  │  └─────────────┘    └─────────────┘    │  │ETH0 │WLAN0│PPP0 │   │   │   │
│  │                                         │  │ 1st │ 2nd │ 3rd │   │   │   │
│  │                                         │  └─────┴─────┴─────┘   │   │   │
│  │                                         └─────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │   iMATRIX CLOUD        │
                          │  coap.imatrixsys.com   │
                          │       Port 5683        │
                          └────────────────────────┘
```

### 2.2 Component Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FLEET-CONNECT-1 APPLICATION                       │
│                                                                       │
│  linux_gateway.c ──────▶ do_everything.c (main loop)                 │
│         │                       │                                     │
│         │                       ├──▶ OBD2 Module                     │
│         │                       ├──▶ CAN Processing                  │
│         │                       ├──▶ Energy Management               │
│         │                       ├──▶ Driver Score                    │
│         │                       └──▶ CLI Interface                   │
│         │                                                             │
│         ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                     iMATRIX CORE LIBRARY                     │     │
│  │                                                               │     │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │     │
│  │  │   Networking  │  │  Memory Mgr   │  │    CAN Bus    │    │     │
│  │  │   (process_   │  │    (MM2)      │  │  Processing   │    │     │
│  │  │   network.c)  │  │   (cs_ctrl/)  │  │  (canbus/)    │    │     │
│  │  └───────────────┘  └───────────────┘  └───────────────┘    │     │
│  │                                                               │     │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │     │
│  │  │     BLE       │  │    CoAP       │  │   Location    │    │     │
│  │  │   (ble/)      │  │   (coap/)     │  │  (location/)  │    │     │
│  │  └───────────────┘  └───────────────┘  └───────────────┘    │     │
│  │                                                               │     │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │     │
│  │  │   Device      │  │  Encryption   │  │    Upload     │    │     │
│  │  │  (device/)    │  │ (encryption/) │  │(imatrix_up/)  │    │     │
│  │  └───────────────┘  └───────────────┘  └───────────────┘    │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                              │                                        │
│                              ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                   PLATFORM ABSTRACTION                       │     │
│  │              IMX_Platform/LINUX_Platform/                    │     │
│  │                                                               │     │
│  │   imx_linux_platform.c  │  imx_linux_networking.c           │     │
│  │   imx_linux_btstack.c   │  imx_linux_sflash.c               │     │
│  └─────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow Summary

**Sensor Data Path**:
```
Vehicle CAN Bus → CAN Driver → Signal Extraction → Sensor Database (mgs.csd[])
                                                            │
BLE Sensor → GATT Read/Notify → Sensor Database ────────────┤
                                                            │
OBD2 PID → ISO 15765-2 → Decode → Sensor Database ──────────┤
                                                            │
GPS → NMEA Parser → Location Data → Sensor Database ────────┘
                                                            │
                                                            ▼
                                              Memory Manager (MM2)
                                                            │
                                                            ▼
                                              CoAP Message Batching
                                                            │
                                                            ▼
                                              Network Interface Selection
                                                            │
                                                            ▼
                                              iMatrix Cloud Platform
```

---

## 3. Directory Structure

### 3.1 Repository Layout

```
iMatrix_Client/                      # Master development repository
├── Fleet-Connect-1/                 # Gateway application (this document)
├── iMatrix/                         # Core platform library
├── mbedtls/                         # TLS/cryptography library
├── btstack/                         # Bluetooth stack
├── docs/                            # Documentation
├── test_scripts/                    # Test suites
└── tools/                           # Development utilities
```

### 3.2 Fleet-Connect-1 Module Structure

```
Fleet-Connect-1/                     # ~68,738 lines of C code
│
├── linux_gateway.c                  # Main entry point
├── do_everything.c                  # Core processing loop (100ms)
├── fc_sensors.c                     # Sensor definitions
├── ev_val_interface.c               # EV validation interface
├── ev_vehicle_factory.c             # Vehicle type factory
├── structs.h                        # Primary data structures
│
├── OBD2/                            # OBD2 Protocol Implementation
│   ├── process_obd2.c/h             # Main OBD2 state machine
│   ├── i15765app.c/h                # ISO 15765-2 transport layer
│   ├── i15765.c/h                   # ISO 15765 protocol engine
│   ├── decode_table.c/h             # PID to sensor mapping
│   ├── decode_mode_01_pids_*.c/h    # Mode 01 PIDs (01-DF)
│   ├── decode_mode_09_pids_*.c/h    # Mode 09 (vehicle info) PIDs
│   ├── process_pid_data.c/h         # Decoded value processing
│   ├── process_vehicle_info.c/h     # VIN retrieval
│   ├── get_J1939_sensors.c/h        # J1939 heavy vehicle support
│   └── coap/reg_obd2.c/h            # Cloud registration
│
├── can_process/                     # CAN Message Processing
│   ├── can_man.c/h                  # CAN message management
│   ├── can_signal_sensor_updates.c  # Generic signal decoding
│   ├── obd2_sensor_updates.c/h      # OBD2-specific handling
│   ├── j1939_sensor_updates.c/h     # J1939 handling
│   ├── vehicle_sensor_mappings.c/h  # Vehicle type mappings
│   ├── odometer_validation.c/h      # Odometer data validation
│   └── test_can_obd2.c/h            # CAN testing utilities
│
├── cli/                             # Command Line Interface
│   ├── fcgw_cli.c/h                 # Fleet Connect CLI
│   ├── app_messages.h               # CLI message definitions
│   └── async_log_queue.h            # Non-blocking logging
│
├── hal/                             # Hardware Abstraction Layer
│   ├── gpio.c/h                     # Digital I/O (8 inputs, 2 analog)
│   ├── accel_process.c/h            # Accelerometer processing
│   ├── hal_leds.c/h                 # LED control state machine
│   ├── can_controller.h             # CAN controller interface
│   ├── can_sensor_ids.h             # Sensor ID definitions
│   └── product_structure.h          # Hardware configuration
│
├── init/                            # System Initialization
│   ├── imx_client_init.c/h          # Main initialization
│   └── wrp_config.c/h               # Configuration file reading
│
├── power/                           # Power Management
│   └── process_power.c/h            # Power state machine
│
├── product/                         # Product Definitions
│   ├── product.c/h                  # Product initialization
│   ├── sensors_def.c/h              # Sensor configuration (generated)
│   ├── controls_def.c/h             # Control configuration (generated)
│   ├── variables_def.c/h            # Variable definitions (generated)
│   └── hal_functions.c/h            # Hardware-specific functions
│
├── driver_score/                    # Driver Behavior Analysis
│   ├── driver_score.c/h             # Core scoring logic
│   ├── driver_score_algorithms.c/h  # Calculation algorithms
│   ├── driver_score_events.c/h      # Event tracking
│   ├── driver_score_feedback.c/h    # Driver feedback
│   ├── driver_score_upload.c/h      # Cloud upload
│   ├── trip_file_manager.c/h        # Trip persistence
│   └── trip_file_cli.c/h            # Trip CLI commands
│
├── energy/                          # Energy Management & CARB
│   ├── energy_trip_manager.c/h      # Trip-based energy
│   ├── carb_integration.c/h         # CARB compliance system
│   ├── carb_segments.c/h            # Discharge/regen segments
│   ├── carb_sessions.c/h            # Charging sessions (max 10)
│   ├── carb_metrics.c/h             # CARB calculations
│   ├── carb_processor.c/h           # Event processing
│   ├── charge_rate_calc.c/h         # Charge/regen detection
│   └── energy_display.c/h           # Display formatting
│
├── hm_truck/                        # Horizon Motors Support
│   ├── hm_truck.c/h                 # HM truck processing
│   ├── hm_can_definitions.c/h       # CAN signal definitions
│   ├── HM_Wrecker_can_definitions.h # Wrecker signals
│   ├── sensor_access_helpers.c/h    # Direct sensor access
│   └── hm_temp.c/h                  # Temperature handling
│
├── aptera/                          # Aptera EV Support
│   ├── aptera.c/h                   # Aptera processing
│   ├── aptera_helpers.c/h           # Helper functions
│   └── Aptera_PI-1_can_definitions.h # CAN definitions
│
├── debug/                           # Debugging Utilities
│   ├── debug_routines.c/h           # Debug utilities
│   └── debug_display_state.c/h      # State display
│
├── imatrix_upload/                  # Cloud Integration
│   └── host_imx_upload.c            # Upload processor
│
└── config_files/                    # Binary Configuration
    └── *.bin                        # v12 format configs
```

### 3.3 iMatrix Core Structure

```
iMatrix/                             # Core Platform Library
│
├── IMX_Platform/                    # Platform Abstraction
│   ├── LINUX_Platform/              # Linux implementation
│   │   ├── imx_linux_platform.c/h   # Main platform abstraction
│   │   ├── imx_linux_networking.c   # Network implementation
│   │   ├── imx_linux_btstack.c      # BTStack integration
│   │   ├── imx_linux_config.c       # Configuration loading
│   │   ├── imx_linux_sflash.c       # Flash memory abstraction
│   │   ├── imx_linux_tty.c          # Serial communication
│   │   ├── imx_linux_telnetd.c      # Telnet server
│   │   └── networking/              # Network subsystem
│   │       ├── process_network.c    # Network state machine (7,761 lines)
│   │       ├── cellular_man.c       # Cellular management (234 KB)
│   │       ├── cellular_blacklist.c # Carrier rotation
│   │       ├── wifi_connect.c       # WiFi connection
│   │       ├── wifi_reassociate.c   # WiFi recovery
│   │       └── network_security.c   # TLS/encryption
│   └── WICED_Platform/              # WICED platform support
│
├── cs_ctrl/                         # Memory Manager MM2 v2.8
│   ├── mm2_core.h                   # Core structures
│   ├── mm2_api.h                    # Public API
│   ├── mm2_read.c                   # Read operations (71 KB)
│   ├── mm2_write.c                  # Write operations
│   ├── mm2_disk.c                   # Disk spillover
│   ├── mm2_startup_recovery.c       # Recovery mechanisms
│   └── memory_manager_stats.c       # Statistics
│
├── ble/                             # Bluetooth Low Energy
│   ├── ble_client/                  # BLE client functionality
│   │   └── ble_client.c/h           # Client implementation
│   ├── ble_manager/                 # Connection management
│   │   ├── ble_mgr.h                # Manager interface
│   │   └── known_ble_devices.h      # Known device profiles
│   ├── imx_ble_server.c             # GATT server (66 KB)
│   ├── imx_ble_config_managment.c   # Configuration (44 KB)
│   ├── imx_ble_connection_handler.c # Connection lifecycle
│   └── imx_ble_dfu.c                # Device Firmware Update
│
├── canbus/                          # CAN Bus Processing
│   ├── can_structs.h                # Data structures (43 KB)
│   ├── can_process.c                # Main processing
│   ├── can_server.c                 # CAN server interface
│   ├── can_utils.c                  # Utilities (93 KB)
│   └── can_signal_extraction.c/h    # Signal parsing
│
├── coap/                            # CoAP Protocol (RFC 7252)
│   ├── coap.c/h                     # Core protocol (19 KB header)
│   ├── coap_recv.c                  # Message reception
│   ├── coap_xmit.c                  # Message transmission
│   ├── que_manager.c                # Message queue (35 KB)
│   ├── coap_token.c                 # Token management
│   └── coap_packet_printer.c        # Debug/logging (27 KB)
│
├── imatrix_upload/                  # Cloud Upload System
│   ├── imatrix_upload.c             # Main engine (113 KB)
│   └── imatrix_upload.h             # API and structures
│
├── location/                        # GPS & Geofencing
│   ├── get_location.c               # GPS data acquisition
│   ├── process_nmea.c               # NMEA parser (85 KB)
│   ├── geofence.c                   # Geofence engine (57 KB)
│   └── gps_stationary_detection.c   # Movement detection
│
├── device/                          # Device Configuration
│   ├── config.c                     # Configuration engine (57 KB)
│   ├── icb_def.h                    # iMatrix Control Block (31 KB)
│   └── system_init.c                # System initialization
│
├── encryption/                      # Security
│   └── enc_utils.c/h                # Encryption utilities
│
├── cli/                             # Core CLI
│   ├── cli.c                        # CLI implementation (43 KB)
│   ├── cli_canbus.c                 # CAN commands
│   ├── cli_can_monitor.c            # CAN monitoring (31 KB)
│   ├── cli_network_mode.c           # Network commands
│   └── async_log_queue.c            # Non-blocking logging
│
└── json/                            # JSON Utilities
    └── cjson integration
```

---

## 4. Main Entry Points and Initialization

### 4.1 Entry Point: linux_gateway.c

**File**: `Fleet-Connect-1/linux_gateway.c`

The main entry point initializes the iMatrix platform and starts the processing loop.

```c
int main(int argc, char *argv[])
{
    // 1. Parse command-line arguments
    //    -P: Print full configuration
    //    -S: Print configuration summary
    //    -I: Display config version

    // 2. Initialize logging and iMatrix platform
    imx_imatrix_init_config_t init_config;
    imx_init(&init_config, override_config, run_in_background);

    // 3. Call Fleet-Connect-1 initialization
    linux_gateway_init();

    // 4. Start main processing loop
    // imx_process_handler() called every IMX_PROCESS_INTERVAL (100ms)

    return 0;
}
```

### 4.2 Core Processing Loop: do_everything.c

**File**: `Fleet-Connect-1/do_everything.c`

The main loop executes every 100ms with breadcrumb tracking for lockup detection.

```c
void do_everything(imx_time_t current_time)
{
    // Breadcrumb tracking for lockup diagnosis
    // 20 positions tracked throughout the loop

    UPDATE_LOOP_POSITION(LOOP_POS_ENTRY);

    // 1. Reboot check
    UPDATE_LOOP_POSITION(LOOP_POS_REBOOT_CHECK);
    if (reboot_requested) {
        // Execute reboot with 5-second delay
    }

    // 2. Control sensor configuration check
    UPDATE_LOOP_POSITION(LOOP_POS_CS_CONFIG_CHECK);

    // 3. GPS event processing
    UPDATE_LOOP_POSITION(LOOP_POS_GPS_EVENT_CHECK);
    UPDATE_LOOP_POSITION(LOOP_POS_GPS_WRITE);

    // 4. GPIO reading (digital/analog inputs)
    UPDATE_LOOP_POSITION(LOOP_POS_GPIO_READ);

    // 5. Accelerometer processing (G-force)
    UPDATE_LOOP_POSITION(LOOP_POS_ACCEL_PROCESS);
    process_accel(current_time);

    // 6. Power management
    UPDATE_LOOP_POSITION(LOOP_POS_POWER_PROCESS);
    process_power(current_time);

    // 7. CAN product availability check
    UPDATE_LOOP_POSITION(LOOP_POS_CAN_PRODUCT_CHECK);

    // 8. OBD2 processing
    UPDATE_LOOP_POSITION(LOOP_POS_OBD2_PROCESS);
    process_obd2(current_time);

    // 9. EV validation processing
    UPDATE_LOOP_POSITION(LOOP_POS_EV_VAL_PROCESS);
    ev_val_process(current_time);

    // 10. Gateway data sampling
    UPDATE_LOOP_POSITION(LOOP_POS_GATEWAY_SAMPLE);
    gateway_sample(current_time);

    // 11-12. Trip/Energy initialization and processing
    UPDATE_LOOP_POSITION(LOOP_POS_TRIP_ENERGY_INIT_CHECK);
    UPDATE_LOOP_POSITION(LOOP_POS_TRIP_ENERGY_PROCESS);

    // 13. CAN debug display
    UPDATE_LOOP_POSITION(LOOP_POS_CAN_DEBUG_DISPLAY);

    // 14-16. CLI monitoring
    UPDATE_LOOP_POSITION(LOOP_POS_CLI_MONITOR_CHECK);
    UPDATE_LOOP_POSITION(LOOP_POS_CLI_MEMORY_MONITOR);
    UPDATE_LOOP_POSITION(LOOP_POS_CLI_CAN_MONITOR);

    // 17. Async log flush
    UPDATE_LOOP_POSITION(LOOP_POS_ASYNC_LOG_FLUSH);

    UPDATE_LOOP_POSITION(LOOP_POS_EXIT);
}
```

### 4.3 Initialization Sequence

**File**: `Fleet-Connect-1/init/imx_client_init.c`

```
┌─────────────────────────────────────────────────────────────┐
│                  INITIALIZATION SEQUENCE                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. linux_gateway_init()                                      │
│    - Entry point for Fleet-Connect-1 initialization         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Load Configuration (wrp_config.c)                         │
│    - find_cfg_file() - Locate v12 binary config             │
│    - read_config_v12() - Parse configuration                │
│    - Populate Mobile_Gateway_Config_t (mgc)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Initialize Control Sensors                                │
│    - Build control sensor blocks (CSB)                      │
│    - Initialize mgs.csd[] array                             │
│    - Initialize mgs.can_csd[] array                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Initialize CAN Structures                                 │
│    - Configure physical buses (CAN0, CAN1)                  │
│    - Configure Ethernet logical buses                       │
│    - init_can_node_hash_tables() - O(1) lookup              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Initialize Subsystems                                     │
│    - init_product() - Product-specific setup                │
│    - init_obd2() - OBD2 module                              │
│    - init_hm_truck() - HM truck module                      │
│    - init_power() - Power management                        │
│    - init_accel() - Accelerometer                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Register Process Handler                                  │
│    - do_everything() registered for 100ms callback          │
│    - Main loop begins                                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Configuration Loading

**File**: `Fleet-Connect-1/init/wrp_config.c`

The v12 binary configuration format contains:

```c
// Configuration file structure (simplified)
typedef struct {
    uint32_t version;                    // Format version (12)
    uint32_t product_id;                 // Vehicle type identifier
    char name[MAX_PRODUCT_NAME];         // Product name

    // Logical bus definitions
    uint32_t no_logical_buses;
    logical_bus_def_t logical_buses[];

    // Sensor definitions
    uint32_t no_sensors;
    sensor_def_t sensors[];

    // Control definitions
    uint32_t no_controls;
    control_def_t controls[];

    // DBC file references
    dbc_reference_t dbc_refs[];
} config_v12_t;
```

---

## 5. State Machines

### 5.1 Main Processing Loop Breadcrumbs

**File**: `Fleet-Connect-1/do_everything.c`

The main loop uses a 20-position breadcrumb system for lockup detection:

```c
typedef enum {
    LOOP_POS_ENTRY = 0,           // Loop entry
    LOOP_POS_REBOOT_CHECK,        // Reboot request check
    LOOP_POS_CS_CONFIG_CHECK,     // Control sensor config
    LOOP_POS_GPS_EVENT_CHECK,     // GPS event check
    LOOP_POS_GPS_WRITE,           // GPS write to sensor
    LOOP_POS_GPIO_READ,           // GPIO digital/analog read
    LOOP_POS_ACCEL_PROCESS,       // Accelerometer processing
    LOOP_POS_POWER_PROCESS,       // Power management
    LOOP_POS_CAN_PRODUCT_CHECK,   // CAN product availability
    LOOP_POS_OBD2_PROCESS,        // OBD2 diagnostic processing
    LOOP_POS_EV_VAL_PROCESS,      // EV validation
    LOOP_POS_GATEWAY_SAMPLE,      // Gateway data sampling
    LOOP_POS_TRIP_ENERGY_INIT_CHECK,  // Trip/energy init
    LOOP_POS_TRIP_ENERGY_PROCESS, // Trip/energy processing
    LOOP_POS_CAN_DEBUG_DISPLAY,   // CAN debug output
    LOOP_POS_CLI_MONITOR_CHECK,   // CLI monitor commands
    LOOP_POS_CLI_MEMORY_MONITOR,  // Memory statistics
    LOOP_POS_CLI_CAN_MONITOR,     // CAN diagnostics
    LOOP_POS_ASYNC_LOG_FLUSH,     // Async log queue flush
    LOOP_POS_EXIT                 // Loop exit
} loop_position_t;
```

**Breadcrumb Flow Diagram**:
```
ENTRY ──▶ REBOOT ──▶ CS_CONFIG ──▶ GPS_EVENT ──▶ GPS_WRITE ──▶ GPIO
  │                                                              │
  │    ┌──────────────────────────────────────────────────────────┘
  │    ▼
  │  ACCEL ──▶ POWER ──▶ CAN_PRODUCT ──▶ OBD2 ──▶ EV_VAL
  │                                                   │
  │    ┌──────────────────────────────────────────────┘
  │    ▼
  │  GATEWAY_SAMPLE ──▶ TRIP_INIT ──▶ TRIP_PROCESS ──▶ CAN_DEBUG
  │                                                        │
  │    ┌───────────────────────────────────────────────────┘
  │    ▼
  └──▶ CLI_MONITOR ──▶ CLI_MEMORY ──▶ CLI_CAN ──▶ ASYNC_LOG ──▶ EXIT
```

### 5.2 CAN Bus State Machine

**File**: `Fleet-Connect-1/can_process/can_man.c` (integrated with iMatrix canbus/)

#### State Definitions

```c
typedef enum {
    CBS_INIT,                         // Initial startup state
    CBS_SETUP_CAN_SERVER,             // Initialize CAN server
    CBS_START_CAN_SERVER,             // Start server operations
    CBS_PROCESS_REGISTRATION_PENDING, // Process CAN while awaiting reg
    CBS_REGISTER_PRODUCT,             // Initiate cloud registration
    CBS_WAIT_FOR_REGISTRATION,        // Wait for registration response
    CBS_PROCESS_REGISTERED,           // Normal operational processing
    WAIT_FOR_CAN_BUS,                 // Error recovery wait state
    CBS_RESTART_CAN_BUS               // Restart server after failure
} enum_can_bus_states_t;
```

#### State Transition Diagram

```
                              ┌─────────────────┐
                              │    CBS_INIT     │
                              │   (Startup)     │
                              └────────┬────────┘
                                       │ Config loaded
                                       ▼
                              ┌─────────────────┐
                              │ CBS_SETUP_CAN_  │
                              │    SERVER       │
                              └────────┬────────┘
                                       │ Hardware init OK
                                       ▼
                              ┌─────────────────┐
                              │ CBS_START_CAN_  │
                              │    SERVER       │
                              └────────┬────────┘
                                       │ Server started
                                       ▼
                        ┌──────────────────────────────┐
                        │ CBS_PROCESS_REGISTRATION_    │◀──────────────┐
                        │        PENDING               │               │
                        │   (Processing CAN data)      │               │
                        └──────────────┬───────────────┘               │
                                       │ Prerequisites met             │
                                       │ (VIN obtained, etc.)          │
                                       ▼                               │
                        ┌──────────────────────────────┐               │
                        │   CBS_REGISTER_PRODUCT       │               │
                        │   (Send registration)        │               │
                        └──────────────┬───────────────┘               │
                                       │ Request sent                  │
                                       ▼                               │
                        ┌──────────────────────────────┐               │
                        │ CBS_WAIT_FOR_REGISTRATION    │               │
                        │   (Await cloud response)     │───────────────┘
                        └──────────────┬───────────────┘  Timeout/retry
                                       │ Registration OK
                                       ▼
┌──────────────┐        ┌──────────────────────────────┐
│ WAIT_FOR_    │◀───────│   CBS_PROCESS_REGISTERED     │
│  CAN_BUS     │ Error  │   (Normal operation)         │
│  (Recovery)  │        │   - Process CAN messages     │
└──────┬───────┘        │   - Update sensors           │
       │                │   - Cloud uploads active     │
       │                └──────────────────────────────┘
       │                               ▲
       │                               │ Recovered
       ▼                               │
┌──────────────┐                       │
│ CBS_RESTART_ │───────────────────────┘
│   CAN_BUS    │
└──────────────┘
```

#### State Transition Table

| Current State | Event | Next State | Action |
|--------------|-------|------------|--------|
| CBS_INIT | Config loaded | CBS_SETUP_CAN_SERVER | Load DBC definitions |
| CBS_SETUP_CAN_SERVER | Hardware OK | CBS_START_CAN_SERVER | Initialize CAN0/CAN1 |
| CBS_START_CAN_SERVER | Server started | CBS_PROCESS_REGISTRATION_PENDING | Begin message processing |
| CBS_PROCESS_REGISTRATION_PENDING | VIN obtained | CBS_REGISTER_PRODUCT | Send registration request |
| CBS_REGISTER_PRODUCT | Request sent | CBS_WAIT_FOR_REGISTRATION | Start timeout timer |
| CBS_WAIT_FOR_REGISTRATION | Success | CBS_PROCESS_REGISTERED | Enable full uploads |
| CBS_WAIT_FOR_REGISTRATION | Timeout | CBS_PROCESS_REGISTRATION_PENDING | Retry registration |
| CBS_PROCESS_REGISTERED | CAN error | WAIT_FOR_CAN_BUS | Start recovery timer |
| WAIT_FOR_CAN_BUS | Timer expires | CBS_RESTART_CAN_BUS | Attempt restart |
| CBS_RESTART_CAN_BUS | Restart OK | CBS_PROCESS_REGISTERED | Resume operation |

### 5.3 Network Manager State Machine

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

#### State Definitions

```c
typedef enum {
    NET_INIT,                  // Initialize network manager
    NET_SELECT_INTERFACE,      // Test all interfaces
    NET_WAIT_RESULTS,          // Wait for ping results
    NET_REVIEW_SCORE,          // Evaluate interface quality
    NET_ONLINE,                // Selected interface active
    NET_ONLINE_CHECK_RESULTS,  // Verify ongoing connectivity
    NET_ONLINE_VERIFY_RESULTS  // Confirm interface stability
} netmgr_state_t;
```

#### State Transition Diagram

```
                              ┌─────────────────┐
                              │    NET_INIT     │
                              │  (Initialize)   │
                              └────────┬────────┘
                                       │ Init complete
                                       ▼
              ┌───────────────────────────────────────────────┐
              │              NET_SELECT_INTERFACE              │
              │                                                │
              │  ┌─────────┐   ┌─────────┐   ┌─────────┐      │
              │  │  ETH0   │   │  WLAN0  │   │  PPP0   │      │
              │  │ Thread  │   │ Thread  │   │ Thread  │      │
              │  │  Ping   │   │  Ping   │   │  Ping   │      │
              │  └─────────┘   └─────────┘   └─────────┘      │
              └───────────────────────┬───────────────────────┘
                                      │ Threads launched
                                      ▼
              ┌───────────────────────────────────────────────┐
              │              NET_WAIT_RESULTS                  │
              │         (Wait for all ping threads)            │
              │              Timeout: 5 seconds                │
              └───────────────────────┬───────────────────────┘
                                      │ Results collected
                                      ▼
              ┌───────────────────────────────────────────────┐
              │              NET_REVIEW_SCORE                  │
              │                                                │
              │   Interface Selection Logic:                   │
              │   1. Score >= 7: Good (use this interface)    │
              │   2. Score 3-7: Acceptable (look for better)  │
              │   3. Score < 3: Failed (skip interface)       │
              │                                                │
              │   Priority: ETH0 > WLAN0 > PPP0               │
              └───────────────────────┬───────────────────────┘
                                      │ Best interface selected
                                      ▼
              ┌───────────────────────────────────────────────┐
              │                NET_ONLINE                      │◀─────────┐
              │         (Active on selected interface)         │          │
              │                                                │          │
              │   - Default route set                          │          │
              │   - DNS configured                             │          │
              │   - Cloud uploads enabled                      │          │
              └───────────────────────┬───────────────────────┘          │
                                      │ Check interval elapsed           │
                                      ▼                                  │
              ┌───────────────────────────────────────────────┐          │
              │           NET_ONLINE_CHECK_RESULTS             │          │
              │              (Verify connectivity)             │          │
              └───────────────────────┬───────────────────────┘          │
                                      │ Ping result received             │
                                      ▼                                  │
              ┌───────────────────────────────────────────────┐          │
              │          NET_ONLINE_VERIFY_RESULTS             │──────────┘
              │             (Confirm stability)                │  Score OK
              │                                                │
              │   Score < 3 ──────▶ NET_SELECT_INTERFACE       │
              │   (Interface failed, try another)              │
              └────────────────────────────────────────────────┘
```

#### Interface Scoring System

```c
#define MIN_ACCEPTABLE_SCORE   3   // Minimum viable score
#define GOOD_SCORE_AVAILABLE   7   // Prefer this or better

// Scoring based on ping results (10 pings sent)
// Score = (successful_pings / 10) * 10
//
// Examples:
//   10/10 success = Score 10 (Excellent)
//    7/10 success = Score 7  (Good)
//    3/10 success = Score 3  (Minimum acceptable)
//    2/10 success = Score 2  (Failed - try another)
```

#### Hysteresis Protection

```c
typedef struct {
    imx_time_t last_interface_switch_time;  // Last switch timestamp
    uint32_t interface_switch_count;        // Switches in window
    bool hysteresis_active;                 // Prevents rapid switching
} netmgr_hysteresis_t;

// Prevents interface flapping:
// - Tracks time since last switch
// - Counts switches within time window
// - Blocks switching if too frequent
```

### 5.4 OBD2 State Machine

**File**: `Fleet-Connect-1/OBD2/process_obd2.c`

#### State Transition Diagram

```
┌─────────────────┐
│   OBD2_INIT     │
│  (Initialize)   │
└────────┬────────┘
         │ ISO 15765 ready
         ▼
┌─────────────────┐
│  DISCOVER_ECUS  │◀────────────────────┐
│ (Enumerate ECUs)│                     │
└────────┬────────┘                     │
         │ ECUs found                   │
         ▼                              │
┌─────────────────┐                     │
│ GET_SUPPORTED_  │                     │
│     PIDS        │                     │
│ (Mode 01 + 09)  │                     │
└────────┬────────┘                     │
         │ PID map built                │
         ▼                              │
┌─────────────────┐                     │
│    GET_VIN      │                     │
│ (Mode 09 PID 02)│                     │
└────────┬────────┘                     │
         │ VIN obtained                 │
         ▼                              │
┌─────────────────────────────────────┐ │
│       COLLECT_DATA                   │ │
│  (Continuous PID collection)         │ │
│                                      │ │
│  For each supported PID:             │ │
│  1. Request PID from ECU             │ │
│  2. Decode response                  │ │
│  3. Update sensor value              │ │
│  4. Move to next PID                 │ │
└────────┬────────────────────────────┘ │
         │ Error or timeout             │
         └──────────────────────────────┘
```

#### PID Support Tracking

```c
typedef struct {
    // Mode 01 supported PIDs (7 ranges × 32 PIDs = 224 PIDs)
    uint32_t mode_01_supported[7];  // Bitmap: PIDs 01-DF

    // Mode 09 supported PIDs
    uint32_t mode_09_supported[7];  // Vehicle info PIDs

    // Per-ECU status
    struct {
        bool valid;
        bool processed;
        uint8_t ecu_id;
    } ecu_status[NO_ECU_ENTRIES];

    // VIN data
    char vin[18];                   // 17-char VIN + null
    bool vin_valid;
} obd2_status_t;
```

### 5.5 Cellular Connection State Machine

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

#### State Transition Diagram

```
┌─────────────────┐
│      IDLE       │
│ (Waiting for    │
│   trigger)      │
└────────┬────────┘
         │ WiFi/ETH failed
         ▼
┌─────────────────┐
│    SCANNING     │◀─────────────────────┐
│ (Search for     │                      │
│   carriers)     │                      │
└────────┬────────┘                      │
         │ Carriers found                │
         ▼                               │
┌─────────────────┐                      │
│  REGISTERING    │                      │
│ (Network reg)   │                      │
└────────┬────────┘                      │
         │ Registered                    │
         ▼                               │
┌─────────────────┐                      │
│   CONNECTING    │                      │
│ (PPP session)   │                      │
│                 │                      │
│ start_pppd()    │                      │
└────────┬────────┘                      │
         │ IP obtained                   │
         ▼                               │
┌─────────────────┐                      │
│   CONNECTED     │                      │
│ (Active)        │                      │
│                 │                      │
│ imx_is_4G_      │                      │
│ connected()=true│                      │
└────────┬────────┘                      │
         │ Connection lost               │
         ▼                               │
┌─────────────────┐                      │
│ DISCONNECTING   │                      │
│                 │                      │
│ stop_pppd()     │                      │
└────────┬────────┘                      │
         │                               │
         ├─────────────────────────────▶│
         │ Retry                         │
         ▼                               │
┌─────────────────┐                      │
│     FAILED      │                      │
│                 │                      │
│ Backoff:        │                      │
│ 5s → 60s → 300s │──────────────────────┘
└─────────────────┘  Rate-limited rescan
```

#### Carrier Blacklisting

```c
// After repeated failures, carriers are blacklisted:
// - Tracks failure count per carrier
// - Rotates to next carrier after threshold
// - Resets blacklist after successful connection
// - Exponential backoff: 5s → 60s → 300s
```

### 5.6 DHCP Renewal State Machine

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

```c
typedef enum {
    DHCP_IDLE,              // No renewal needed
    DHCP_SIGNAL_RENEW,      // Signal renewal request
    DHCP_KILLING_GRACEFUL,  // Send SIGTERM to udhcpc
    DHCP_KILLING_FORCE,     // Send SIGKILL if needed
    DHCP_CLEANUP_PID,       // Remove PID file
    DHCP_STARTING,          // Start new udhcpc
    DHCP_COMPLETE           // Renewal complete
} dhcp_state_t;
```

```
┌──────────────┐
│  DHCP_IDLE   │
└──────┬───────┘
       │ Renewal needed
       ▼
┌──────────────┐
│DHCP_SIGNAL_  │
│   RENEW      │
└──────┬───────┘
       │ Signal sent
       ▼
┌──────────────┐
│DHCP_KILLING_ │
│  GRACEFUL    │──────▶ (SIGTERM to udhcpc)
└──────┬───────┘
       │ Not responding
       ▼
┌──────────────┐
│DHCP_KILLING_ │
│    FORCE     │──────▶ (SIGKILL)
└──────┬───────┘
       │ Process killed
       ▼
┌──────────────┐
│DHCP_CLEANUP_ │
│     PID      │──────▶ (Remove /var/run/udhcpc.*.pid)
└──────┬───────┘
       │ Cleanup done
       ▼
┌──────────────┐
│DHCP_STARTING │──────▶ (Start new udhcpc)
└──────┬───────┘
       │ Started
       ▼
┌──────────────┐
│DHCP_COMPLETE │
└──────────────┘
```

### 5.7 WiFi Reassociation State Machine

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/wifi_reassociate.c`

```c
typedef enum {
    NETMGR_WIFI_REASSOC_IDLE,        // No operation
    NETMGR_WIFI_REASSOC_DISCONNECT,  // Issue disconnect
    NETMGR_WIFI_REASSOC_WAIT,        // 200ms wait
    NETMGR_WIFI_REASSOC_RECONNECT,   // Issue reconnect
    NETMGR_WIFI_REASSOC_COMPLETE     // Done
} wifi_reassoc_state_t;
```

```
┌────────────────────┐
│ WIFI_REASSOC_IDLE  │
└─────────┬──────────┘
          │ Reassociation triggered
          ▼
┌────────────────────┐
│WIFI_REASSOC_       │
│  DISCONNECT        │──────▶ wpa_cli disconnect
└─────────┬──────────┘
          │ Disconnected
          ▼
┌────────────────────┐
│WIFI_REASSOC_WAIT   │──────▶ 200ms delay
└─────────┬──────────┘
          │ Wait complete
          ▼
┌────────────────────┐
│WIFI_REASSOC_       │
│  RECONNECT         │──────▶ wpa_cli reconnect
└─────────┬──────────┘
          │ Reconnected
          ▼
┌────────────────────┐
│WIFI_REASSOC_       │
│  COMPLETE          │
└────────────────────┘
```

---

## 6. Module Structure

### 6.1 Fleet-Connect-1 Modules

#### OBD2 Module (`OBD2/`)

**Purpose**: Vehicle diagnostics via OBD2 protocol (ISO 15765-2)

| File | Lines | Purpose |
|------|-------|---------|
| `process_obd2.c/h` | ~2,500 | Main OBD2 state machine |
| `i15765app.c/h` | ~1,800 | ISO 15765-2 application layer |
| `i15765.c/h` | ~1,200 | ISO 15765 protocol engine |
| `decode_table.c/h` | ~800 | PID to sensor mapping |
| `decode_mode_01_pids_*.c` | ~3,000 | Mode 01 PIDs (01-DF) |
| `decode_mode_09_pids_*.c` | ~1,500 | Mode 09 PIDs (vehicle info) |
| `get_J1939_sensors.c/h` | ~600 | J1939 heavy vehicle support |

**Key Functions**:
```c
void init_obd2(void);                    // Initialize OBD2 module
void process_obd2(imx_time_t current);   // Main processing (100ms)
void decode_obd2_pid(uint8_t pid, ...);  // Decode PID response
bool get_vin(char *vin_buffer);          // Retrieve VIN
```

#### CAN Processing Module (`can_process/`)

**Purpose**: Decoding CAN messages and updating sensor values

| File | Lines | Purpose |
|------|-------|---------|
| `can_man.c/h` | ~1,500 | CAN message management |
| `can_signal_sensor_updates.c` | ~800 | Generic signal decoding |
| `obd2_sensor_updates.c/h` | ~600 | OBD2-specific handling |
| `j1939_sensor_updates.c/h` | ~700 | J1939 handling |
| `vehicle_sensor_mappings.c/h` | ~400 | Vehicle type mappings |
| `odometer_validation.c/h` | ~300 | Odometer validation |

**Key Functions**:
```c
void can_msg_process(can_bus_t bus, imx_time_t time, can_msg_t *msg);
void decode_can_message(const can_msg_t *msg, const can_node_t *node);
void imx_set_can_sensor(uint32_t sensor_id, imx_data_32_t value);
void init_can_node_hash_tables(void);    // O(1) lookup optimization
```

#### Hardware Abstraction Layer (`hal/`)

**Purpose**: Low-level hardware interfacing

| File | Purpose |
|------|---------|
| `gpio.c/h` | Digital I/O (8 inputs, 2 analog) |
| `accel_process.c/h` | G-force/accelerometer with calibration |
| `hal_leds.c/h` | LED control state machine |
| `can_controller.h` | CAN controller interface |
| `can_sensor_ids.h` | Sensor ID definitions |
| `product_structure.h` | Physical hardware configuration |

**Sensor Input Types**:
```c
enum_gforce_readings_t;    // X, Y, Z accelerometer readings
enum_digital_readings_t;   // 8 digital inputs + key switch
enum_analog_readings_t;    // 2 analog inputs
```

#### Driver Score Module (`driver_score/`)

**Purpose**: Driver behavior analysis and trip scoring

| Component | Purpose |
|-----------|---------|
| Core scoring | Behavior analysis algorithms |
| Event tracking | Acceleration, braking, cornering events |
| Trip management | Trip segmentation and persistence |
| Feedback | Driver feedback generation |
| Cloud upload | Score transmission to iMatrix |

#### Energy Management (`energy/`)

**Purpose**: EV energy tracking and CARB compliance

| Component | Purpose |
|-----------|---------|
| Trip energy | Trip-based energy aggregation |
| CARB integration | Regulatory compliance tracking |
| Segments | Discharge/regeneration tracking |
| Sessions | Charging session management (max 10) |
| Metrics | MPGe, kWh/100km calculations |

**Event Rates**:
- 100ms events: Real-time power sampling
- 500ms events: Energy integration
- 15-minute window: Session folding for trips

#### HM Truck Module (`hm_truck/`)

**Purpose**: Horizon Motors truck-specific CAN processing

**Direct Sensor Access Pattern**:
```c
// Preferred for real-time (100ms) operations - zero latency
float voltage = mgs.csd[hm_truck_variables.battery_voltage_entry].last_value.float_32bit;
float current = mgs.csd[hm_truck_variables.battery_current_entry].last_value.float_32bit;

// Helper functions for cross-module access
float hm_truck_get_direct_battery_voltage(void);
float hm_truck_get_direct_battery_current(void);
float hm_truck_get_direct_battery_soc(void);
float hm_truck_get_direct_vehicle_speed(void);
float hm_truck_get_direct_odometer(void);
bool  hm_truck_is_battery_voltage_valid(void);
```

### 6.2 iMatrix Core Modules

#### Network Manager (`networking/`)

**File**: `process_network.c` (7,761 lines)

**Features**:
- Multi-interface support (ETH0, WLAN0, PPP0)
- Ping-based interface scoring
- Hysteresis protection against flapping
- Non-blocking state machine
- DHCP client management
- DNS caching (5-minute TTL)

#### Memory Manager MM2 (`cs_ctrl/`)

**Version**: 2.8 with 75% space efficiency

**Key Files**:
| File | Size | Purpose |
|------|------|---------|
| `mm2_core.h` | ~2KB | Core structures |
| `mm2_api.h` | ~1KB | Public API |
| `mm2_read.c` | 71KB | Read operations |
| `mm2_write.c` | ~20KB | Write operations |
| `mm2_disk.c` | ~15KB | Disk spillover |

#### BLE Module (`ble/`)

**Components**:
- `ble_client/` - Client functionality
- `ble_manager/` - Connection management
- GATT server (66 KB)
- Device Firmware Update (DFU)

#### CAN Bus Module (`canbus/`)

**Key Files**:
| File | Size | Purpose |
|------|------|---------|
| `can_structs.h` | 43KB | Data structures |
| `can_utils.c` | 93KB | Utilities |
| `can_process.c` | ~15KB | Main processing |
| `can_signal_extraction.c` | ~8KB | Signal parsing |

#### CoAP Module (`coap/`)

**Features**:
- RFC 7252 compliant
- Message queue management (35 KB)
- Token tracking
- Retransmission with exponential backoff

#### Location Module (`location/`)

**Key Files**:
| File | Size | Purpose |
|------|------|---------|
| `process_nmea.c` | 85KB | NMEA sentence parsing |
| `geofence.c` | 57KB | Geofence engine |
| `gps_stationary_detection.c` | ~5KB | Movement detection |

---

## 7. Communication Subsystems

### 7.1 CAN Bus Communication

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAN BUS SUBSYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Physical Buses              Logical Processing                 │
│   ┌─────────────┐            ┌─────────────────────────────┐    │
│   │   CAN0      │───────────▶│                             │    │
│   │ (Powertrain)│            │    CAN Message Router       │    │
│   └─────────────┘            │                             │    │
│                              │    can_msg_process()        │    │
│   ┌─────────────┐            │                             │    │
│   │   CAN1      │───────────▶│    ┌───────────────────┐   │    │
│   │   (Body)    │            │    │  Hash Table       │   │    │
│   └─────────────┘            │    │  256 buckets      │   │    │
│                              │    │  O(1) lookup      │   │    │
│   ┌─────────────┐            │    └───────────────────┘   │    │
│   │  CAN_ETH    │───────────▶│                             │    │
│   │(Ethernet)   │            └─────────────────────────────┘    │
│   └─────────────┘                          │                    │
│                                            ▼                    │
│                              ┌─────────────────────────────┐    │
│                              │    Signal Extraction        │    │
│                              │                             │    │
│                              │  decode_can_message()       │    │
│                              │  - Bit position extraction  │    │
│                              │  - Byte order handling      │    │
│                              │  - Scale/offset applied     │    │
│                              │  - Range validation         │    │
│                              └─────────────────────────────┘    │
│                                            │                    │
│                                            ▼                    │
│                              ┌─────────────────────────────┐    │
│                              │    Sensor Database          │    │
│                              │    mgs.can_csd[]            │    │
│                              └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

#### CAN Message Structure

```c
typedef struct can_msg {
    uint16_t can_bus;                    // Bus ID (CAN_BUS_0, CAN_BUS_1, CAN_BUS_ETH)
    imx_utc_time_t can_utc_time;         // UTC timestamp
    uint32_t can_id;                     // Message ID (11-bit or 29-bit)
    uint8_t can_data[MAX_CAN_FRAME_LENGTH];  // 8 bytes payload
    uint8_t can_dlc;                     // Data length code (0-8)
} can_msg_t;
```

#### Signal Extraction Pipeline

```
CAN Frame (8 bytes)
       │
       ▼
┌──────────────────────────────────┐
│ 1. Message ID Lookup             │
│    - Hash table: O(1)            │
│    - Find can_node_t definition  │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 2. For Each Signal in Message    │
│    - Start bit position          │
│    - Bit length                  │
│    - Byte order (Intel/Motorola) │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 3. Bit Extraction                │
│    extract_signal_bits()         │
│    - Handle multi-byte signals   │
│    - Sign extension if needed    │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 4. Apply Scaling                 │
│    physical = (raw × scale)      │
│              + offset            │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 5. Range Validation              │
│    - Check min/max bounds        │
│    - Track out-of-range events   │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 6. Update Sensor                 │
│    imx_set_can_sensor()          │
│    - Store in mgs.can_csd[]      │
└──────────────────────────────────┘
```

#### Hash Table Configuration

```c
#define CAN_HASH_BUCKETS    256     // Power-of-2 for fast modulo
#define CAN_MAX_NODES       2048    // Maximum nodes per bus

// Hash function: node_id % 256
// Collision handling: linked list chaining
// Performance: O(1) average, O(n) worst case
```

### 7.2 BLE Sensor Communication

#### GATT Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BLE SUBSYSTEM                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐        ┌─────────────────────────────┐        │
│   │  BLE Radio  │◀──────▶│      BTStack Integration    │        │
│   │             │        │      imx_linux_btstack.c    │        │
│   └─────────────┘        └─────────────────────────────┘        │
│                                       │                         │
│                          ┌────────────┴────────────┐            │
│                          ▼                         ▼            │
│                 ┌─────────────────┐      ┌─────────────────┐    │
│                 │   BLE Client    │      │   BLE Manager   │    │
│                 │   ble_client.c  │      │   ble_mgr.c     │    │
│                 │                 │      │                 │    │
│                 │ - Scanning      │      │ - Connection    │    │
│                 │ - Discovery     │      │   management    │    │
│                 │ - Read/Write    │      │ - Known devices │    │
│                 │ - Notifications │      │ - Pairing       │    │
│                 └─────────────────┘      └─────────────────┘    │
│                          │                         │            │
│                          └────────────┬────────────┘            │
│                                       ▼                         │
│                          ┌─────────────────────────┐            │
│                          │     GATT Server         │            │
│                          │   imx_ble_server.c      │            │
│                          │                         │            │
│                          │ - Service definitions   │            │
│                          │ - Characteristic R/W    │            │
│                          │ - Notify/Indicate       │            │
│                          └─────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

#### BLE Device Tracking

```c
typedef struct {
    uint8_t vendor_name[MAX_MAC_VENDOR_NAME_LENGTH];  // MAC vendor OUI
    wiced_bt_device_address_t remote_bd_addr;         // Device address
    uint8_t ble_addr_type;                            // Public/Random
    int8_t rssi_raw_value;                            // Raw RSSI (-127 to 0)
    float rssi_calculated;                            // Kalman-filtered RSSI
    kalman_filter_t kalman_rssi;                      // RSSI filter state
    imx_time_t last_seen;                             // Last advertisement
    imx_time_t last_sent;                             // Last upload
    uint8_t flag;                                     // Device flags
} ble_results_t;
```

#### Discovery Process

```
1. Active Scanning
   └─▶ Device initiates SCAN_REQ

2. Advertisement Reception
   └─▶ Collect ADV_IND packets

3. Vendor Identification
   └─▶ MAC OUI lookup (first 3 bytes)

4. RSSI Filtering
   └─▶ Kalman filter for signal smoothing

5. GATT Discovery
   └─▶ Service and characteristic enumeration

6. Data Collection
   └─▶ Read characteristics / Subscribe to notifications
```

### 7.3 Cellular/4G (PPP)

#### PPP Connection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  CELLULAR SUBSYSTEM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐        ┌─────────────────────────────┐        │
│   │   Modem     │◀──────▶│     Cellular Manager        │        │
│   │  (4G LTE)   │  AT    │     cellular_man.c          │        │
│   │             │ cmds   │                             │        │
│   └─────────────┘        │  - Carrier scanning         │        │
│                          │  - Registration             │        │
│                          │  - Signal monitoring        │        │
│                          │  - Blacklist management     │        │
│                          └─────────────────────────────┘        │
│                                       │                         │
│                                       ▼                         │
│                          ┌─────────────────────────────┐        │
│                          │       PPP Daemon            │        │
│                          │         (pppd)              │        │
│                          │                             │        │
│                          │  - Connection negotiation   │        │
│                          │  - IPCP (IP assignment)     │        │
│                          │  - Keep-alive               │        │
│                          └─────────────────────────────┘        │
│                                       │                         │
│                                       ▼                         │
│                          ┌─────────────────────────────┐        │
│                          │       ppp0 Interface        │        │
│                          │                             │        │
│                          │  IP: Assigned by carrier    │        │
│                          │  Route: Default gateway     │        │
│                          └─────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

#### Modem Information API

```c
uint32_t imx_get_4G_rssi(void);           // Signal strength (-120 to -25 dBm)
uint32_t imx_get_4G_ber(void);            // Bit error rate
uint32_t imx_get_4G_operator_id(void);    // MCC/MNC
char *imx_get_imei(void);                 // International Equipment ID
char *imx_get_imsi(void);                 // International Mobile Subscriber ID
char *imx_get_ccid(void);                 // SIM card ID
void imx_set_esim(char *esim);            // Set eSIM identifier
```

#### Failure Recovery

```c
// Carrier blacklisting after repeated failures:
// 1. Track failure count per carrier
// 2. Rotate to next carrier after threshold (3 failures)
// 3. Reset blacklist after successful connection
//
// Exponential backoff:
// - Initial delay: 5 seconds
// - Second retry: 60 seconds
// - Subsequent: 300 seconds
```

### 7.4 WiFi

#### WiFi Modes

```c
typedef enum {
    IMX_WIFI_MODE_OFF,     // WiFi disabled
    IMX_WIFI_MODE_STA,     // Station mode (client)
    IMX_WIFI_MODE_AP       // Access Point mode
} imx_wifi_mode_t;
```

#### WiFi Management

```
┌─────────────────────────────────────────────────────────────────┐
│                    WIFI SUBSYSTEM                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Station Mode (STA)                 Access Point Mode (AP)     │
│   ┌─────────────────────┐           ┌─────────────────────┐    │
│   │  - Connect to AP    │           │  - Create network   │    │
│   │  - DHCP client      │           │  - DHCP server      │    │
│   │  - Scan for APs     │           │  - Accept clients   │    │
│   │  - Reassociation    │           │                     │    │
│   └─────────────────────┘           └─────────────────────┘    │
│                                                                  │
│   SSID Management:                                               │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ set_wifi_st_ssid(ssid, pass, security, eap, restart)    │   │
│   │ set_wifi_ap_ssid(ssid, pass, security, channel)         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   Security Types:                                                │
│   - Open (no encryption)                                         │
│   - WEP (deprecated)                                             │
│   - WPA/WPA2 (AES)                                              │
│   - WPA3 (if supported)                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5 Ethernet

#### Ethernet Management

```
┌─────────────────────────────────────────────────────────────────┐
│                   ETHERNET SUBSYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐        ┌─────────────────────────────┐        │
│   │   eth0      │◀──────▶│     Interface Monitor       │        │
│   │ Interface   │        │                             │        │
│   └─────────────┘        │  - Carrier detection        │        │
│                          │  - Link up/down events      │        │
│                          │  - IP address monitoring    │        │
│                          └─────────────────────────────┘        │
│                                       │                         │
│                                       ▼                         │
│                          ┌─────────────────────────────┐        │
│                          │      DHCP Client            │        │
│                          │       (udhcpc)              │        │
│                          │                             │        │
│                          │  PID: /var/run/udhcpc.      │        │
│                          │       eth0.pid              │        │
│                          └─────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 7.6 Interface Prioritization

#### Priority System

```
┌─────────────────────────────────────────────────────────────────┐
│               INTERFACE PRIORITY ORDER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Priority 1: ETHERNET (eth0)                                   │
│   ├─ Fastest, most reliable                                     │
│   ├─ Lowest latency                                             │
│   └─ Preferred when available                                   │
│                                                                  │
│   Priority 2: WIFI (wlan0)                                      │
│   ├─ Good bandwidth                                             │
│   ├─ Used when Ethernet unavailable                             │
│   └─ Background reassociation after 5 min down                  │
│                                                                  │
│   Priority 3: CELLULAR (ppp0)                                   │
│   ├─ Fallback interface                                         │
│   ├─ Variable latency                                           │
│   └─ Used when WiFi unavailable                                 │
│                                                                  │
│   Scoring (0-10):                                                │
│   ├─ 10 pings sent to coap.imatrixsys.com                       │
│   ├─ Score = (successful / 10) × 10                             │
│   ├─ Score >= 7: Good (prefer this)                             │
│   ├─ Score 3-6: Acceptable (look for better)                    │
│   └─ Score < 3: Failed (switch interface)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Memory Management (MM2)

### 8.1 Overview

**Version**: Memory Manager v2.8
**Efficiency**: 75% (24 data bytes per 32-byte sector)

### 8.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 MEMORY MANAGER MM2 v2.8                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌───────────────────────────────────────────────────────┐     │
│   │                   RAM TIER (Primary)                   │     │
│   │                                                        │     │
│   │   Pool Size: 64KB (Linux) / 4KB (STM32)               │     │
│   │                                                        │     │
│   │   ┌──────────┬──────────┬──────────┬──────────┐       │     │
│   │   │ Sector 0 │ Sector 1 │ Sector 2 │   ...    │       │     │
│   │   │ 32 bytes │ 32 bytes │ 32 bytes │          │       │     │
│   │   └──────────┴──────────┴──────────┴──────────┘       │     │
│   │                                                        │     │
│   │   When RAM pressure > threshold ───────────────────▶  │     │
│   └───────────────────────────────────────────────────────┘     │
│                              │                                   │
│                              ▼                                   │
│   ┌───────────────────────────────────────────────────────┐     │
│   │               DISK TIER (Spillover)                    │     │
│   │                                                        │     │
│   │   Upload Source Directories:                           │     │
│   │   ├─ IMX_UPLOAD_GATEWAY/                               │     │
│   │   ├─ IMX_HOSTED_DEVICE/                                │     │
│   │   ├─ IMX_UPLOAD_LOCAL_STORAGE/                         │     │
│   │   └─ IMX_UPLOAD_CANBUS/                                │     │
│   │                                                        │     │
│   │   Features:                                            │     │
│   │   ├─ Automatic activation on RAM pressure             │     │
│   │   ├─ Per-source isolation                              │     │
│   │   └─ Recovery on corruption                            │     │
│   └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Sector Format

```c
#define SECTOR_SIZE              32    // bytes
#define TSD_FIRST_UTC_SIZE       8     // uint64_t
#define TSD_AVAILABLE_DATA_SIZE  24    // 3 × uint32_t values

// Sector efficiency: 24/32 = 75%
```

#### TSD (Time Series Data) Format

```
┌────────────────────────────────────────────────────────────────┐
│                    TSD SECTOR (32 bytes)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Byte 0-7:   first_UTC (uint64_t) - Timestamp                 │
│   Byte 8-11:  value_0 (uint32_t/float)                         │
│   Byte 12-15: value_1 (uint32_t/float)                         │
│   Byte 16-19: value_2 (uint32_t/float)                         │
│   Byte 20-23: value_3 (uint32_t/float)                         │
│   Byte 24-27: value_4 (uint32_t/float)                         │
│   Byte 28-31: value_5 (uint32_t/float)                         │
│                                                                 │
│   Maximum: 6 values per sector                                  │
│   Efficiency: 24 data bytes / 32 total = 75%                   │
└────────────────────────────────────────────────────────────────┘
```

#### EVT (Event) Format

```
┌────────────────────────────────────────────────────────────────┐
│                    EVT SECTOR (32 bytes)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Byte 0-3:   value_0 (uint32_t/float)                         │
│   Byte 4-11:  UTC_0 (uint64_t) - Timestamp for value_0         │
│   Byte 12-15: value_1 (uint32_t/float)                         │
│   Byte 16-23: UTC_1 (uint64_t) - Timestamp for value_1         │
│   Byte 24-31: padding                                           │
│                                                                 │
│   Maximum: 2 event pairs per sector                             │
└────────────────────────────────────────────────────────────────┘
```

### 8.4 API

```c
// Initialization
imx_result_t imx_memory_manager_init(uint32_t pool_size);
int imx_memory_manager_ready(void);
imx_result_t imx_memory_manager_shutdown(void);

// Write operations
imx_result_t imx_write_tsd(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value
);

imx_result_t imx_write_evt(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value,
    imx_utc_time_ms_t utc_time_ms
);

imx_result_t imx_write_evt_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value,
    imx_utc_time_ms_t utc_time_ms,
    float latitude,
    float longitude
);
```

### 8.5 Power-Down Protection

```
┌─────────────────────────────────────────────────────────────────┐
│                POWER-DOWN PROTECTION                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Shutdown Sequence (60-second grace period):                   │
│                                                                  │
│   1. Power loss detected                                         │
│   2. Shutdown signal received                                    │
│   3. RAM data flushed to disk                                   │
│   4. Sector chains preserved                                     │
│   5. Metadata written                                            │
│   6. Safe shutdown complete                                      │
│                                                                  │
│   Recovery on Startup:                                           │
│   1. Validate disk spillover files                               │
│   2. Recover incomplete sectors                                  │
│   3. Rebuild chain tables                                        │
│   4. Resume normal operation                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Cloud Upload System

### 9.1 CoAP Protocol

**Standard**: RFC 7252 - Constrained Application Protocol

```c
// CoAP Configuration
#define COAP_HEADER_LENGTH      4
#define MAX_MSG_LENGTH          1152
#define MAX_PAYLOAD_LENGTH      1024
#define DEFAULT_COAP_PORT       5683
#define MAX_TOKEN_LENGTH        8

// Message Types
#define CONFIRMABLE             0    // CON - requires ACK
#define NON_CONFIRMABLE         1    // NON - no ACK needed
#define ACKNOWLEDGEMENT         2    // ACK
#define RESET                   3    // RST

// Message Classes
#define REQUEST                 0
#define SUCCESS_RESPONSE        2
#define CLIENT_ERROR            4
#define SERVER_ERROR            5
```

### 9.2 Upload Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  IMATRIX UPLOAD SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              Upload Sources                            │     │
│   │                                                        │     │
│   │   ┌─────────┬─────────┬─────────┬─────────┐          │     │
│   │   │ Gateway │ Hosted  │ Local   │ CAN Bus │          │     │
│   │   │         │ Device  │ Storage │         │          │     │
│   │   └────┬────┴────┬────┴────┬────┴────┬────┘          │     │
│   │        │         │         │         │                │     │
│   │        └─────────┴─────────┴─────────┘                │     │
│   │                         │                              │     │
│   └─────────────────────────┼──────────────────────────────┘     │
│                             ▼                                    │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              Data Batching                             │     │
│   │                                                        │     │
│   │   - Collect sensor values                              │     │
│   │   - Group by upload source                             │     │
│   │   - Add timestamps                                     │     │
│   └───────────────────────────────────────────────────────┘     │
│                             │                                    │
│                             ▼                                    │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              CoAP Message Composition                  │     │
│   │                                                        │     │
│   │   - Build CoAP header                                  │     │
│   │   - Add options (URI-Path, Content-Format)            │     │
│   │   - Serialize payload                                  │     │
│   │   - Generate token                                     │     │
│   └───────────────────────────────────────────────────────┘     │
│                             │                                    │
│                             ▼                                    │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              Message Queue                             │     │
│   │              que_manager.c                             │     │
│   │                                                        │     │
│   │   - Pending messages                                   │     │
│   │   - Retransmission tracking                            │     │
│   │   - Acknowledgment handling                            │     │
│   └───────────────────────────────────────────────────────┘     │
│                             │                                    │
│                             ▼                                    │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              Network Transmission                      │     │
│   │                                                        │     │
│   │   UDP Socket ──▶ Network Manager ──▶ Selected Interface│     │
│   └───────────────────────────────────────────────────────┘     │
│                             │                                    │
│                             ▼                                    │
│                    coap.imatrixsys.com:5683                     │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Upload Data Structure

```c
typedef struct imatrix_data {
    imatrix_upload_source_t upload_source;  // Data source
    uint16_t active_ble_device;             // Active BLE connection
    uint8_t *data_ptr;                      // Payload pointer
    uint16_t state;                         // Current state
    uint16_t sensor_no;                     // Sensor index
    uint16_t notify_cs, notify_entry;       // Notification indices
    uint32_t no_imx_uploads;                // Upload count
    imx_utc_time_ms_t upload_utc_ms_time;   // Upload timestamp
    imx_time_t last_upload_time;            // Last upload time
    imx_time_t last_dns_time;               // DNS cache time
    message_t *msg;                         // CoAP message

    // Status flags
    unsigned int imatrix_dns_failed   : 1;  // DNS lookup failed
    unsigned int imx_error            : 1;  // Error occurred
    unsigned int imx_warning          : 1;  // Warning occurred
    unsigned int imx_send_available   : 1;  // Ready to send
    unsigned int printed_error        : 1;  // Error printed
    unsigned int imatrix_active       : 1;  // Upload active
    unsigned int cli_disabled         : 1;  // CLI disabled
    unsigned int imatrix_upload_paused: 1;  // User pause
} imatrix_data_t;
```

### 9.4 Upload Sources

```c
typedef enum {
    IMX_UPLOAD_GATEWAY,        // Gateway/edge device data
    IMX_HOSTED_DEVICE,         // Cloud-hosted sensor data
    IMX_UPLOAD_LOCAL_STORAGE,  // Local storage cache
    IMX_UPLOAD_CANBUS,         // CAN bus data
    // ... additional sources
} imatrix_upload_source_t;
```

### 9.5 Authentication

```
┌─────────────────────────────────────────────────────────────────┐
│                  AUTHENTICATION FLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Device Identification:                                         │
│   ├─ Serial number                                               │
│   ├─ MAC address binding                                         │
│   └─ Organization ID (org)                                       │
│                                                                  │
│   Message Validation:                                            │
│   ├─ Transmission hash                                           │
│   └─ TLS/DTLS encryption (if enabled)                           │
│                                                                  │
│   Functions:                                                     │
│   void imx_report_firmware_version(void);                        │
│   void update_transmission_hash(char (*p)[TRANSMISSION_HASH_LENGTH]);│
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Data Structures

### 10.1 Primary Structures

#### Mobile_Gateway_Status_t (Runtime State)

**File**: `Fleet-Connect-1/structs.h`

```c
typedef struct {
    // Counters and timestamps
    uint32_t no_check_ins;           // Device check-in counter
    imx_time_t last_can_msg;         // Last CAN message timestamp
    float on_board_temperature;       // Internal temperature
    device_updates_t check_in;        // Device update bitmask

    // Sensor data arrays
    control_sensor_data_t *csd;       // Host sensor values
    control_sensor_data_t *can_csd;   // CAN-based sensor values

    // CAN bus data
    can_node_data_t can[2];           // Physical bus data (CAN0, CAN1)
    uint16_t no_ethernet_can_buses;   // Ethernet bus count
    can_node_data_t *ethernet_can_buses;  // Dynamic Ethernet buses
    canbus_hw_config_t *canbus_hw_config; // Hardware configuration
} Mobile_Gateway_Status_t;

// Global instance
extern Mobile_Gateway_Status_t mgs;
```

#### Mobile_Gateway_Config_t (Configuration)

```c
typedef struct {
    // Product identification
    uint32_t product_id;              // Vehicle type identifier
    char name[MAX_PRODUCT_NAME];      // Product name

    // Sensor configuration
    uint32_t no_sensors;              // Total sensor count
    uint32_t no_can_sensors;          // CAN-based sensors
    imx_control_sensor_block_t csb[]; // Host sensor definitions
    imx_control_sensor_block_t can_csb[];  // CAN sensor definitions

    // Vehicle configuration
    hm_truck_config_t vehicle_config.hm_truck;

    // Registration status
    unsigned can_controller_registered : 1;
    unsigned vin_registered : 1;
} Mobile_Gateway_Config_t;

// Global instance
extern Mobile_Gateway_Config_t mgc;
```

#### netmgr_ctx_t (Network Manager Context)

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

```c
typedef struct {
    netmgr_state_t state;             // Current state
    uint32_t current_interface;       // Active interface index
    iface_state_t states[IFACE_COUNT]; // Per-interface state
    netmgr_config_t config;           // Configuration parameters
    imx_time_t last_interface_switch_time;  // Switch tracking
    uint32_t interface_switch_count;  // Hysteresis counter
    bool hysteresis_active;           // Flapping protection
} netmgr_ctx_t;
```

#### iface_state_t (Per-Interface State)

```c
typedef struct {
    pthread_t thread;                 // Ping thread
    imx_time_t last_spawn;            // Thread spawn time
    imx_time_t start_time;            // Interface start time
    bool link_up;                     // Link operational
    uint16_t latency;                 // Latency in ms
    uint16_t score;                   // Quality (0-10)
    imx_time_t cooldown_until;        // Failure cooldown
    pthread_mutex_t mutex;            // Thread safety

    // Ping statistics
    uint32_t total_pings_sent;
    uint32_t total_pings_success;
    uint32_t total_pings_failed;
    uint32_t consecutive_failures;
    imx_time_t last_ping_time;
    uint32_t avg_latency_ms;

    // WiFi reassociation
    bool reassociating;
    imx_time_t reassoc_start_time;
} iface_state_t;
```

### 10.2 CAN Structures

#### can_msg_t (CAN Message)

**File**: `iMatrix/canbus/can_structs.h`

```c
typedef struct can_msg {
    uint16_t can_bus;                 // Bus ID
    imx_utc_time_t can_utc_time;      // UTC timestamp
    uint32_t can_id;                  // Message ID
    uint8_t can_data[8];              // Payload (8 bytes)
    uint8_t can_dlc;                  // Data length (0-8)
} can_msg_t;
```

#### can_node_t (ECU/Node Definition)

```c
typedef struct can_node {
    uint32_t node_id;                 // CAN message ID
    char node_name[CAN_NODE_NAME_LENGTH];  // ECU name
    can_signal_t signals[MAX_SIGNALS]; // Signals in message
    uint16_t signal_count;            // Number of signals
    struct can_node *next;            // Hash chain link
} can_node_t;
```

#### can_signal_t (Signal Definition)

```c
typedef struct can_signal {
    char signal_name[MAX_SIGNAL_NAME_LENGTH];
    uint8_t start_bit;                // Bit position (0-63)
    uint8_t length;                   // Signal width in bits
    uint8_t byte_order;               // 0=Motorola, 1=Intel
    double scale;                     // Scaling factor
    double offset;                    // Offset value
    double min_value;                 // Minimum valid value
    double max_value;                 // Maximum valid value
    uint32_t imatrix_sensor_id;       // Target sensor ID
} can_signal_t;
```

#### canbus_hw_config_t (Hardware Configuration)

```c
typedef struct canbus_hw_config {
    uint8_t bus;                      // Bus ID (0, 1, ETH)
    uint32_t speed;                   // Baud rate
    char type[32];                    // "internal", "ethernet", etc.
    uint16_t port;                    // Optional port
    bool enabled;                     // Active flag
    struct canbus_hw_config *next;    // Linked list
} canbus_hw_config_t;
```

### 10.3 BLE Structures

#### ble_results_t (Device Tracking)

**File**: `iMatrix/ble/ble_manager/ble_mgr.h`

```c
typedef struct {
    uint8_t vendor_name[MAX_MAC_VENDOR_NAME_LENGTH];
    wiced_bt_device_address_t remote_bd_addr;
    uint8_t ble_addr_type;
    int8_t rssi_raw_value;
    float rssi_calculated;
    kalman_filter_t kalman_rssi;
    imx_time_t last_seen;
    imx_time_t last_sent;
    uint8_t flag;
} ble_results_t;
```

#### gatt_device_t (GATT Connection)

```c
typedef struct gatt_device {
    wiced_bt_device_address_t ble_address;
    uint16_t conn_id;
    wiced_bt_gatt_discovery_result_t discovery_result[NO_GATT_DISCOVERY_RESULTS];
    unsigned int characteristics_discovered : 1;
} gatt_device_t;
```

---

## 11. Key APIs and Interfaces

### 11.1 iMatrix Core API

**File**: `iMatrix/imatrix.h`

```c
// Lifecycle
imx_status_t imx_init(
    imx_imatrix_init_config_t *init_config,
    bool override_config,
    bool run_in_background
);
imx_states_t imx_process(bool process_sensors);
imx_status_t imx_deinit(void);

// Network status
bool imx_network_connected(void);
imx_result_t imx_notify_pppd_stopped(bool cellular_reset);
void set_online_mode(bool online_mode);

// Watchdog
void imx_init_watchdog(void);
void imx_kick_watchdog(void);

// OTA Updates
imx_result_t imx_get_latest(imx_image_type_t imx_image_type);
bool imx_reboot_to_image(uint16_t image_no, bool now);

// Device information
char *imx_get_device_serial_number(void);
imx_wifi_mode_t imx_get_wifi_mode(void);

// Sensor access
imx_control_sensor_block_t *imx_get_control_sensor(uint32_t sensor_id);
imx_result_t imx_set_control_sensor(uint32_t sensor_id, imx_data_32_t value);

// Time
imx_time_t imx_time_get_time(void);
imx_utc_time_ms_t imx_get_utc_time_ms(void);
```

### 11.2 Memory Manager API

**File**: `iMatrix/cs_ctrl/mm2_api.h`

```c
// Initialization
imx_result_t imx_memory_manager_init(uint32_t pool_size);
int imx_memory_manager_ready(void);
imx_result_t imx_memory_manager_shutdown(void);

// TSD write
imx_result_t imx_write_tsd(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t *csb,
    control_sensor_data_t *csd,
    imx_data_32_t value
);

// Event write
imx_result_t imx_write_evt(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t *csb,
    control_sensor_data_t *csd,
    imx_data_32_t value,
    imx_utc_time_ms_t utc_time_ms
);

// Event with GPS
imx_result_t imx_write_evt_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t *csb,
    control_sensor_data_t *csd,
    imx_data_32_t value,
    imx_utc_time_ms_t utc_time_ms,
    float latitude,
    float longitude
);

// Statistics
void imx_memory_manager_get_stats(mm2_stats_t *stats);
```

### 11.3 Network Manager API

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.h`

```c
// Main processing
imx_result_t process_network(imx_time_t current_time);

// Status
bool imx_network_up(void);
uint32_t imx_get_current_interface(void);

// Interface control
bool imx_use_eth0(void);
bool imx_use_wifi0(void);
void imx_set_eth0_enabled(bool enabled);
void imx_set_wifi0_enabled(bool enabled);

// Callbacks
void imx_set_notify_link_type_set(
    void (*link_type_set)(imx_network_interface_t link_type)
);

// Cellular
void start_pppd(void);
void stop_pppd(bool cellular_reset);
bool imx_is_4G_connected(void);
```

### 11.4 CAN Processing API

**File**: `Fleet-Connect-1/can_process/can_man.h`

```c
// Initialization
void init_can_node_hash_tables(void);

// Message processing
void can_msg_process(
    can_bus_t canbus,
    imx_time_t current_time,
    can_msg_t *msg
);

// Signal extraction
void decode_can_message(
    const can_msg_t *msg,
    const can_node_t *can_node
);

// Sensor update
void imx_set_can_sensor(
    uint32_t sensor_id,
    imx_data_32_t value
);
```

---

## 12. Configuration System

### 12.1 Configuration File Format

**Format**: v12 Binary

**Location**: `Fleet-Connect-1/config_files/*.bin`

```c
// Configuration structure (simplified)
typedef struct {
    uint32_t version;                 // Format version (12)
    uint32_t product_id;              // Vehicle type (decimal/hex)
    char name[MAX_PRODUCT_NAME];      // Product name

    // Logical bus definitions
    struct {
        uint8_t logical_bus_id;
        uint8_t physical_bus_id;      // CAN0, CAN1, or ETH
        uint32_t speed;
        char type[32];
    } logical_buses[];

    // Sensor definitions
    struct {
        uint32_t sensor_id;
        char name[MAX_SENSOR_NAME];
        uint8_t data_type;
        // ... additional fields
    } sensors[];

    // Control definitions
    // Variable definitions
    // DBC references
} config_v12_t;
```

### 12.2 Loading Process

**File**: `Fleet-Connect-1/init/wrp_config.c`

```
1. find_cfg_file()
   └─▶ Locate configuration binary in /etc/imatrix/

2. read_config_v12()
   └─▶ Parse binary format

3. Populate Mobile_Gateway_Config_t (mgc)
   └─▶ Set product_id, name, etc.

4. Build control sensor blocks
   └─▶ Create csb[] and can_csb[] arrays

5. Initialize CAN node structures
   └─▶ Set up message definitions
```

### 12.3 Command-Line Options

```bash
./FC-1 -P    # Print full configuration details
./FC-1 -S    # Print configuration summary (with logical buses)
./FC-1 -I    # Display config version and summary
./FC-1       # Normal operation
```

### 12.4 Product Identifiers

```c
// Known product IDs (decimal = hex)
#define IMX_LIGHT_VEHICLE     3116622498    // 0xB9D34E22
#define IMX_J1939_VEHICLE     1234567890    // 0x499602D2
#define IMX_HM_WRECKER        1235419592    // 0x49A54DC8
#define IMX_APTERA            2201718576    // 0x83400A30
```

---

## 13. Debugging and Diagnostics

### 13.1 Breadcrumb System

Fleet-Connect-1 uses a three-level breadcrumb system for lockup detection:

```
Level 1: Main Loop (do_everything.c)
├─ 20 positions tracked
├─ Updated at each processing step
└─ Identifies which step locked up

Level 2: Handler (imx_process_handler)
├─ Process handler position tracking
└─ Network manager state tracking

Level 3: imx_process()
├─ Internal processing position
└─ Subsystem state tracking
```

### 13.2 Debug Flags

**File**: Various source files

```c
// Application debug flags
DEBUGS_APP_GENERAL              // General application debug
DEBUGS_APP_CARB                 // CARB compliance debug
DEBUGS_CHARGE_RATE              // Charging detection debug
DEBUGS_APP_ENERGY_MANAGER       // Energy manager debug
DEBUGS_APP_HM_TRUCK             // HM truck debug
DEBUGS_APP_DRIVER_SCORE         // Driver scoring debug

// Networking debug flags
DEBUGS_FOR_ETH0_NETWORKING      // Ethernet interface debug
DEBUGS_FOR_WIFI0_NETWORKING     // WiFi interface debug
DEBUGS_FOR_PPP0_NETWORKING      // Cellular PPP debug
DEBUGS_FOR_NETWORKING_SWITCH    // Interface switching debug

// CAN debug flags
DEBUGS_APP_CAN_CTRL             // CAN control debug
DEBUGS_APP_CAN_DATA             // CAN data debug
```

### 13.3 CLI Commands

#### Energy Management Commands
```bash
e carb           # CARB tracking status
e segments       # Segment energy tracking
e sessions       # Charging session history
e trip           # Trip energy report
e theft          # Energy theft detection
e metric         # Switch to metric units
e imperial       # Switch to imperial units
e help           # Energy command help
```

#### CAN Diagnostics Commands
```bash
can status       # CAN bus statistics
can unknown      # Show detected unknown CAN IDs (decimal and hex)
can monitor      # Real-time CAN monitoring
```

#### Memory and System Commands
```bash
memory stats     # Memory allocation tracking
version          # Build version and date
config           # Configuration display
```

#### Network Commands
```bash
network          # Network manager state
network score    # Interface scores
cell             # Cellular modem status
wifi             # WiFi connection status
```

### 13.4 Async Logging

**File**: `Fleet-Connect-1/cli/async_log_queue.h`

Non-blocking logging for performance-critical operations:

```c
// Add message to async queue
void async_log_enqueue(const char *format, ...);

// Flush queue (called in main loop)
void async_log_flush(void);

// Features:
// - Non-blocking enqueue
// - Batched dequeue in main loop
// - Prevents I/O delays in real-time processing
```

---

## 14. Vehicle Support

### 14.1 Support Matrix

| Feature | Light Vehicle (OBD2) | J1939 Heavy | HM Wrecker | Aptera |
|---------|---------------------|-------------|------------|--------|
| **CAN Protocol** | ISO/OBD2 | SAE J1939 | Custom DBC | Custom |
| **VIN Retrieval** | Mode 09 PID 02 | N/A | Custom signal | Custom |
| **Registration** | VIN Hash | Device SN | VIN Hash | Custom |
| **Energy Tracking** | Hybrid | Limited | Full (V/I/SOC) | Full |
| **Battery Monitoring** | OBD2 | Limited | Real-time | Real-time |
| **CARB Support** | Planned | No | Yes | Yes |
| **Driver Scoring** | Yes | Yes | Yes | Yes |

### 14.2 Vehicle Type Detection

```c
// Vehicle type determined by product_id in configuration
switch (mgc.product_id) {
    case IMX_LIGHT_VEHICLE:
        // OBD2 PIDs via Mode 01/09
        // VIN-based registration
        break;

    case IMX_J1939_VEHICLE:
        // J1939 protocol-specific signals
        // Extended addressing
        break;

    case IMX_HM_WRECKER:
        // Custom CAN signal definitions
        // Battery monitoring (V/I/SOC)
        // Real-time energy tracking
        break;

    case IMX_APTERA:
        // Aptera-specific protocol
        // EV-specific sensors
        break;
}
```

### 14.3 OBD2 PID Coverage

```
Mode 01 (Live Data):
├─ PIDs 01-1F: Engine, coolant, fuel, timing
├─ PIDs 20-3F: Air flow, throttle, O2 sensors
├─ PIDs 40-5F: Catalyst, fuel system
├─ PIDs 60-7F: Hybrid/EV specific
├─ PIDs 80-9F: Additional sensors
├─ PIDs A0-BF: NOx, particulate
└─ PIDs C0-DF: Extended parameters

Mode 09 (Vehicle Information):
├─ PID 02: VIN (17 characters)
├─ PID 04: Calibration ID
├─ PID 06: CVN
├─ PID 08: In-use performance tracking
└─ PID 0A: ECU name
```

---

## 15. Build System

### 15.1 CMake Configuration

**File**: `Fleet-Connect-1/CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.10.0)
project(Fleet_Connect)

set(APP_NAME FC-1)
set(IMATRIX_DIR ../iMatrix)
set(MBEDTLS_DIR ../mbedtls)

# Build types
# - Release: Optimized (-O2)
# - Debug: Debug symbols (-g)
# - DebugGDB: Full debug, no optimization (-O0 -g3)

# Compiler flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DLINUX_PLATFORM")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wno-unused-function")
```

### 15.2 Dependencies

| Dependency | Purpose |
|------------|---------|
| iMatrix | Core platform library |
| mbedTLS | TLS/cryptography |
| ncurses | Terminal UI (optional) |
| cJSON | JSON parsing |
| pthread | Threading |
| rt | Real-time extensions |

### 15.3 Build Commands

```bash
# Configure
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..

# Build
make -j$(nproc)

# Debug build
cmake -DCMAKE_BUILD_TYPE=DebugGDB ..
make

# Cross-compile for ARM
cmake -DCMAKE_TOOLCHAIN_FILE=arm_toolchain.cmake ..
make
```

### 15.4 Build Output

```
build/
├── FC-1                    # Main executable
├── CMakeCache.txt          # CMake cache
└── CMakeFiles/             # Build intermediates

# Binary sizes (approximate):
# - Release: ~800KB
# - Debug: ~2MB
# - DebugGDB: ~18MB
```

---

## Appendix A: Quick Reference

### A.1 Key File Locations

| Component | File |
|-----------|------|
| Main entry | `Fleet-Connect-1/linux_gateway.c` |
| Main loop | `Fleet-Connect-1/do_everything.c` |
| Initialization | `Fleet-Connect-1/init/imx_client_init.c` |
| Data structures | `Fleet-Connect-1/structs.h` |
| Network manager | `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` |
| Memory manager | `iMatrix/cs_ctrl/mm2_*.c` |
| CAN processing | `Fleet-Connect-1/can_process/can_man.c` |
| OBD2 processing | `Fleet-Connect-1/OBD2/process_obd2.c` |
| Cloud upload | `iMatrix/imatrix_upload/imatrix_upload.c` |

### A.2 Global Variables

| Variable | Type | Purpose |
|----------|------|---------|
| `mgs` | `Mobile_Gateway_Status_t` | Runtime state |
| `mgc` | `Mobile_Gateway_Config_t` | Configuration |

### A.3 Important Constants

```c
// Timing
#define IMX_PROCESS_INTERVAL    100     // Main loop interval (ms)
#define PING_TIMEOUT            5000    // Ping timeout (ms)
#define DNS_CACHE_TIMEOUT       300000  // DNS cache TTL (ms)

// Memory
#define SECTOR_SIZE             32      // MM2 sector size (bytes)
#define RAM_POOL_SIZE           65536   // RAM pool (bytes)

// Network
#define MIN_ACCEPTABLE_SCORE    3       // Minimum interface score
#define GOOD_SCORE_AVAILABLE    7       // Preferred score

// CAN
#define CAN_HASH_BUCKETS        256     // Hash table size
#define MAX_CAN_NODES           2048    // Maximum nodes per bus
```

---

**Document End**

*Last Updated: 2025-12-08*
*Version: 1.0*
*Codebase: Fleet-Connect-1 + iMatrix Core*
