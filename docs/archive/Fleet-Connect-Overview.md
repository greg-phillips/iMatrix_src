# Fleet-Connect System Overview
**Developer Onboarding Guide**

*Last Updated: 2025-11-03 (v12 Migration Complete)*

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Repository Structure](#repository-structure)
4. [Core Components](#core-components)
5. [Key Design Elements](#key-design-elements)
6. [Development Environment](#development-environment)
7. [Getting Started](#getting-started)
8. [Common Development Patterns](#common-development-patterns)
9. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
10. [Further Resources](#further-resources)

---

## Introduction

Fleet-Connect is a comprehensive IoT gateway system for vehicle connectivity, integrating OBD2 protocols, CAN bus processing, and the iMatrix cloud platform. The system is designed as an embedded Linux application that provides real-time vehicle data collection, processing, and cloud synchronization.

### Key Capabilities

- **Multi-protocol Vehicle Interface**: OBD2, J1939, and modern EV CAN protocols
- **Real-time Data Processing**: 100ms-500ms sampling rates with efficient memory management
- **Cloud Integration**: Secure CoAP/DTLS communication with iMatrix cloud platform
- **Network Management**: Multi-interface support (Ethernet, WiFi, Cellular) with intelligent failover
- **Data Persistence**: Tiered storage system with RAM and disk spillover
- **Extensible Architecture**: Plugin-based vehicle profile system

### Target Platforms

- **Primary**: Linux-based gateways (QUAKE 1180-5002/5102)
- **Development**: x86/x64 Linux (Ubuntu, WSL)
- **Legacy Support**: WICED-based embedded systems

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Fleet-Connect Gateway                        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Vehicle    │  │   Network    │  │   iMatrix    │           │
│  │  Interface   │  │   Manager    │  │    Cloud     │           │
│  │  (CAN/OBD2)  │  │ (ETH/WIFI/4G)│  │   (CoAP)     │           │
│  └───────┬──────┘  └───────┬──────┘  └───────┬──────┘           │
│          │                 │                 │                  │
│          └────────────┬────┴─────────────────┘                  │
│                       │                                         │
│                ┌──────▼────────┐                                │
│                │   Main Loop   │                                │
│                │(do_everything)│                                │
│                └──────┬────────┘                                │
│                       │                                         │
│         ┌─────────────┼─────────────┐                           │
│         │             │             │                           │
│  ┌──────▼──────┐ ┌───▼────┐ ┌─────▼──────┐                      │
│  │   Memory    │ │ Storage│ │   Sensor   │                      │
│  │  Manager    │ │ Manager│ │  Sampling  │                      │
│  │   (MM2)     │ │        │ │            │                      │
│  └─────────────┘ └────────┘ └────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### Component Layers

1. **Application Layer** (Fleet-Connect-1)
   - Vehicle-specific adapters (OBD2, HM Truck, Aptera EV)
   - Business logic and trip management
   - User interface (CLI) and configuration

2. **Platform Layer** (iMatrix)
   - Core runtime and event loop
   - Network abstraction and management
   - Memory management (MM2)
   - Cloud communication (CoAP/DTLS)

3. **Hardware Abstraction Layer**
   - CAN bus drivers
   - Network interfaces
   - GPIO and peripherals
   - GPS and sensors

---

## Repository Structure

### Fleet-Connect-1 Directory

```
Fleet-Connect-1/
├── linux_gateway.c         # Main entry point
├── do_everything.c          # Core processing loop
├── structs.h                # Global data structures
├── system.h                 # System configuration
│
├── OBD2/                    # OBD2 protocol implementation
│   ├── process_obd2.c       # OBD2 request/response processing
│   ├── obd2_pids.h          # PID definitions
│   └── get_J1939_sensors.c  # J1939 heavy-duty protocol
│
├── can_process/             # CAN bus message processing
│   ├── can_state_machine.c  # Registration and startup states
│   └── can_sample.c         # Real-time CAN data processing
│
├── hm_truck/                # HM Wrecker vehicle profile
│   ├── hm_truck.c           # Main vehicle adapter
│   ├── hm_truck_helpers.c   # Utility functions
│   └── hm_can_definitions.c # CAN signal mappings
│
├── aptera/                  # Aptera EV vehicle profile
│   ├── aptera.c             # Aptera vehicle adapter
│   └── aptera_val_adapter.c # Value adaptation layer
│
├── energy/                  # Energy/efficiency tracking
│   ├── energy_manager.c     # Charging and energy monitoring
│   ├── carb_*.c             # CARB compliance metrics
│   └── charge_rate_calc.c   # Charging detection
│
├── driver_score/            # Driver behavior analytics
│   ├── driver_score.c       # Scoring algorithms
│   └── trip_file_manager.c  # Trip data persistence
│
├── init/                    # System initialization
│   ├── init.c               # Startup sequence
│   └── wrp_config.c         # Configuration file parsing
│
├── cli/                     # Command-line interface
│   ├── fcgw_cli.c           # Fleet-Connect commands
│   └── app_messages.h       # Application messages
│
├── hal/                     # Hardware abstraction
│   ├── gpio.c               # Digital I/O
│   ├── accel_process.c      # Accelerometer processing
│   └── hal_leds.c           # LED control
│
├── power/                   # Power management
│   └── process_power.c      # Power state monitoring
│
└── product/                 # Product configuration
    ├── product.c            # Product initialization
    ├── sensors_def.c        # Sensor definitions
    └── controls_def.c       # Control definitions
```

### iMatrix Directory

```
iMatrix/
├── imatrix.h                # Public API
├── common.h                 # Common definitions
├── storage.h                # Storage structures
├── imatrix_interface.c      # Main interface implementation
│
├── IMX_Platform/
│   └── LINUX_Platform/      # Linux-specific implementation
│       ├── imx_linux_platform.c
│       ├── imx_linux_network.c
│       └── imx_linux_ble.c
│
├── canbus/                  # CAN bus subsystem
│   ├── can_structs.h        # CAN data structures
│   ├── can_sample.c         # CAN message sampling
│   └── coap/                # CAN device registration
│       └── registration.c
│
├── networking/              # Network management
│   ├── process_network.c    # Network state machine
│   ├── network_interfaces.c # Interface management
│   └── dhcp_manager.c       # DHCP client management
│
├── cs_ctrl/                 # Memory management (MM2)
│   ├── mm2_api.c            # MM2 public API
│   ├── memory_manager_core.c       # Core memory operations
│   ├── memory_manager_tiered.c     # Tiered storage (RAM→Disk)
│   ├── memory_manager_disk.c       # Disk operations
│   ├── memory_manager_tsd_evt.c    # Time-series data handling
│   └── memory_manager_stats.c      # Memory statistics
│
├── cli/                     # Command-line interface
│   ├── cli.c                # CLI core
│   ├── cli_commands.c       # Command handlers
│   ├── cli_canbus.c         # CAN bus commands
│   ├── cli_network_mode.c   # Network commands
│   └── telnetd.c            # Telnet server
│
├── coap/                    # CoAP protocol
│   ├── coap.c               # CoAP message handling
│   └── coap_interface.c     # iMatrix CoAP integration
│
├── imatrix_upload/          # Cloud upload
│   ├── imatrix_transmit.c   # Data transmission
│   └── imatrix_packet.c     # Packet formatting
│
├── storage/                 # Flash storage
│   ├── storage.c            # Storage management
│   └── sflash.c             # Serial flash driver
│
├── location/                # GPS and location
│   ├── location.c           # GPS processing
│   └── geofence.c           # Geofencing logic
│
├── ble/                     # Bluetooth Low Energy
│   ├── ble_client/          # BLE client functionality
│   └── ble_manager/         # BLE device management
│
├── device/                  # Device configuration
│   ├── device.c             # Device initialization
│   └── system_init.c        # System setup
│
├── time/                    # Time management
│   ├── ck_time.c            # Clock and timekeeping
│   └── ntp.c                # NTP client
│
└── encryption/              # Security
    ├── enc_utils.c          # Encryption utilities
    └── dtls.c               # DTLS implementation
```

---

## Core Components

### 1. Main Application Flow

#### Entry Point: `linux_gateway.c`

```c
void imx_host_application_start()
{
    // Initialize version information
    imatrix_config.host_major_version = MajorVersion;
    imatrix_config.host_minor_version = MinorVersion;

    // Initialize the gateway
    if (linux_gateway_init() == true) {
        // Register main processing handler (100ms interval)
        imx_run_loop_register_app_handler(imx_process_handler, IMX_PROCESS_INTERVAL);

        // Execute the main loop (never returns)
        imx_run_loop_execute();
    }
}
```

#### Main Processing Loop: `do_everything.c`

Called every 100ms, handles:
- GPS data collection and upload
- GPIO pin monitoring
- Accelerometer processing
- Power state management
- Vehicle-specific data processing (OBD2/CAN)
- Trip and energy system processing

```c
void do_everything(imx_time_t current_time)
{
    // GPS events (speed-based: 1 second to 2 minutes)
    if (imx_generate_gps_event(current_time)) {
        imx_write_gps_location(IMX_UPLOAD_GATEWAY, current_time);
        imx_write_gps_location(IMX_UPLOAD_CAN_DEVICE, current_time);
    }

    // GPIO sampling (1 second intervals)
    if (imx_is_later(current_time, last_gpio_read_time + 1000)) {
        read_gpio_pins(force_update);
    }

    // Vehicle-specific processing
    if (cb.can_controller != NULL) {
        if (cb.can_controller->product_id == IMX_LIGHT_VEHICLE) {
            process_obd2(current_time);
        } else if (cb.can_controller->product_id == IMX_HM_WRECKER ||
                   cb.can_controller->product_id == IMX_APTERA) {
            ev_val_process(current_time);
        }
    }

    // Gateway sensor sampling
    gateway_sample(current_time);

    // Trip and energy tracking
    if (imx_system_time_syncd()) {
        process_trip_and_energy_systems(current_time);
    }
}
```

### 2. iMatrix Runtime System

#### Event Loop Architecture

The iMatrix core provides a lightweight event loop with periodic callbacks:

```c
// Register application handler
void imx_run_loop_register_app_handler(void (*handler)(void), uint32_t interval_ms);

// Execute main loop (never returns)
void imx_run_loop_execute(void);
```

#### State Machine: `imx_process()`

Returns system state:
- `IMX_INITIALIZING`: System startup
- `IMX_PROVISIONING_SETUP/ACTIVE`: Device configuration
- `IMX_PROVISIONED`: Ready for operation
- `IMX_CONNECTING_TO_AP`: Network connection in progress
- `IMX_ONLINE`: Connected and operational
- `IMX_OFFLINE`: Network unavailable

### 3. CAN Bus Subsystem

#### CAN State Machine

Located in `Fleet-Connect-1/can_process/`:

```c
typedef enum {
    CBS_INIT,                           // Initial state
    CBS_SETUP_CAN_BUS,                  // Configure CAN hardware
    CBS_SETUP_CAN_SERVER,               // Start CAN processing threads
    CBS_REGISTER_PRODUCT,               // Register with iMatrix cloud
    CBS_WAIT_FOR_REGISTRATION,          // Wait for cloud response
    CBS_PROCESS_REGISTRATION_PENDING,   // Registration in progress
    CBS_PROCESS_REGISTERED,             // Fully registered and operational
    WAIT_FOR_CAN_BUS,                   // Waiting for CAN activity
    CBS_RESTART_CAN_BUS,                // Recovery/restart state
} enum_can_bus_states_t;
```

**Critical Design Elements:**
- Non-blocking state transitions
- Parallel operation with network initialization
- Automatic recovery on failures
- VIN reading for applicable vehicles

#### CAN Message Processing

**Data Flow:**
1. Hardware driver receives CAN frame
2. Frame queued for processing
3. `can_sample.c` decodes using DBC-generated structures
4. Signal values extracted and scaled
5. Values written to sensor data structures
6. Memory manager handles persistence and upload

**Hash Table Lookup** (O(1) performance):
```c
can_node_t *node = can_hash_lookup(hash_table, can_id);
if (node) {
    extract_signals(node, can_data, csd_array);
}
```

### 4. Network Manager

#### Multi-Interface Management

The network manager in `iMatrix/networking/process_network.c` handles:

**Supported Interfaces:**
- `IMX_ETH0_INTERFACE`: Ethernet
- `IMX_STA_INTERFACE`: WiFi Station
- `IMX_AP_INTERFACE`: WiFi Access Point
- `IMX_PPP0_INTERFACE`: Cellular (PPP)

**Key Features:**
- Opportunistic interface discovery
- Priority-based selection (Ethernet > WiFi > Cellular)
- DHCP client management with PID file tracking
- Cooldown periods to prevent flapping
- Hysteresis control for stability

**State Machine:**
```
STARTUP → DISCOVER_INTERFACES → COMPUTE_BEST_INTERFACE
    ↓
CONFIGURE_INTERFACE → WAIT_FOR_CONNECTION → VERIFY_ONLINE
    ↓                                            ↓
ONLINE ←────────────────────────────────────────┘
    ↓
[Monitor for failures] → COOLDOWN → COMPUTE_BEST_INTERFACE
```

### 5. Memory Management System (MM2)

#### Tiered Storage Architecture

**Design Philosophy:**
- **RAM First**: High-speed in-memory buffers for recent data
- **Disk Spillover**: Automatic persistence when RAM fills
- **Upload Priority**: Always read from RAM before disk
- **Recovery**: Corruption detection and automatic repair

**Memory Hierarchy:**
```
Sensor Data → RAM Sectors (32 bytes each) → Disk Files (4KB sectors)
              ↑                              ↑
              |                              |
          Fast Access                   Persistent Storage
          (Recent data)                 (Historical data)
```

**API Functions:**
```c
// Write sensor data
imx_result_t mm2_write_sensor_data(
    upload_source, sensor_id, data_type,
    value, timestamp, add_location
);

// Read for upload
imx_result_t mm2_read_next_record(
    upload_source, sensor_id,
    record_out, location_out
);

// Acknowledge uploaded data
void mm2_acknowledge_records(
    upload_source, sensor_id, count
);
```

**Key Features:**
- Per-sensor memory pools
- Automatic RAM→Disk migration
- Thread-safe operations (Linux platform)
- Statistics and monitoring
- Power-down flush support

### 6. Vehicle Abstraction Layer (VAL)

#### Purpose

Provides a common interface for different vehicle types, abstracting the underlying protocol (OBD2, J1939, proprietary CAN).

#### Implemented Vehicle Profiles

**OBD2 Light Vehicles** (`IMX_LIGHT_VEHICLE`):
- Standard OBD2 protocol (ISO 15765-4)
- Mode 01: Live data PIDs
- Mode 09: Vehicle information
- Automatic VIN reading

**HM Wrecker** (`IMX_HM_WRECKER`):
- Heavy-duty truck platform
- Proprietary CAN protocol
- Battery monitoring and regeneration
- Energy tracking and CARB compliance
- Trip management

**Aptera EV** (`IMX_APTERA`):
- Three-wheeled solar electric vehicle
- Custom CAN protocol
- Advanced energy management
- Regenerative braking analytics

#### Common Interface Functions

```c
// Vehicle-specific initialization
void vehicle_init(void);

// Process vehicle data at specified interval
void vehicle_process(imx_time_t current_time);

// Get sensor value
float vehicle_get_sensor(uint32_t sensor_id);

// Set control value
void vehicle_set_control(uint32_t control_id, float value);
```

---

## Key Design Elements

### 1. State Machines

**Philosophy**: Non-blocking, timeout-based transitions

**Pattern:**
```c
switch (current_state) {
    case STATE_INIT:
        // Initialize resources
        if (init_success) {
            transition_to(STATE_READY);
        } else {
            transition_to(STATE_ERROR);
        }
        break;

    case STATE_READY:
        // Check for timeout
        if (imx_is_later(current_time, start_time + TIMEOUT)) {
            transition_to(STATE_TIMEOUT);
        }
        // Process work
        if (work_complete) {
            transition_to(STATE_DONE);
        }
        break;
}
```

**Important Rules:**
- Always include `break` statements
- Use named timeout constants
- Log all state transitions (for debugging)
- Implement recovery states

### 2. Memory Efficiency

**Embedded System Constraints:**
- Limited RAM (typically 256MB-1GB)
- No dynamic memory allocation in critical paths
- Fixed-size data structures
- Sector-based storage system

**Best Practices:**
```c
// Good: Static allocation
static uint8_t buffer[1024];

// Good: Stack allocation for temporary data
void process_data(void) {
    uint8_t temp[64];
    // Use temp
}

// Avoid: Dynamic allocation
void process_data(void) {
    uint8_t *temp = malloc(64);  // AVOID IN CRITICAL PATHS
    // ...
    free(temp);
}
```

### 3. Time Management

**Time Representation:**
```c
typedef uint32_t imx_time_t;          // Milliseconds since boot
typedef uint32_t imx_utc_time_t;      // Seconds since epoch (1970)
typedef uint64_t imx_utc_time_ms_t;   // Milliseconds since epoch
```

**Timeout Checking:**
```c
// Check if time1 is later than time2 (handles wraparound)
bool imx_is_later(imx_time_t time1, imx_time_t time2);

// Get time difference
imx_time_t imx_time_difference(imx_time_t latest, imx_time_t earliest);
```

**Example:**
```c
static imx_time_t last_sample_time = 0;

void periodic_task(imx_time_t current_time) {
    if (imx_is_later(current_time, last_sample_time + 1000)) {
        // Execute task every 1 second
        do_sampling();
        last_sample_time = current_time;
    }
}
```

### 4. Error Handling

**Error Code System:**
```c
typedef enum {
    IMX_SUCCESS = 0,
    IMX_INVALID_ENTRY,
    IMX_SENSOR_ERROR,
    IMX_OUT_OF_MEMORY,
    IMX_TIMEOUT,
    // ... (54 total error codes)
} imx_result_t;
```

**Error Handling Pattern:**
```c
imx_result_t result = imx_some_operation();
if (result != IMX_SUCCESS) {
    imx_cli_log_printf(true, "Operation failed: %s", imx_error(result));
    // Handle error appropriately
    return result;
}
```

### 5. Configuration System (v12)

**Binary Configuration Files:**
- Format: `.cfg.bin` (generated by CAN_DM v12+ tool)
- **Version**: v12 (Logical Bus Native) - **v11 NOT supported**
- Contains: Product definition, **logical CAN buses**, network config, sensors
- Versioned structure with CRC32 checksum validation
- **Breaking Change**: v12 uses dynamic logical bus arrays (not fixed 3-bus)

**Configuration API (v12):**
```c
// Detect version before reading
uint16_t detect_config_version(const char *filename);

// Read v12 configuration
config_v12_t *read_config_v12(const char *filename);

// Write v12 configuration
int write_config_v12(const char *filename, const config_v12_t *config);

// Cleanup
void free_config_v12(config_v12_t *config);
```

**v12 Structure Overview:**
```c
typedef struct config_v12 {
    can_controller_t *product;              // Product info (POINTER!)
    uint16_t num_logical_buses;             // Dynamic bus count
    logical_bus_config_t *logical_buses;    // Dynamic bus array
    network_config_t network;               // Network interfaces
    internal_sensors_config_t internal;     // Internal sensors
    file_dbc_signal_setting_t *dbc_settings;  // DBC settings (POINTER!)
    uint32_t dbc_settings_count;
    // ... additional fields
} config_v12_t;
```

**Logical Bus Architecture (NEW in v12):**
```c
typedef struct logical_bus_config {
    uint8_t physical_bus_id;    // 0=CAN0, 1=CAN1, 2=Ethernet
    char alias[33];             // Bus name (e.g., "PT", "IN")
    uint32_t node_count;        // Number of CAN nodes
    can_node_t *nodes;          // CAN nodes with signals
    // ... additional fields
} logical_bus_config_t;
```

**Key Features:**
- **Dynamic Bus Count**: Supports 1, 2, 3+ logical buses (not fixed 3)
- **Physical Bus Mapping**: Multiple logical buses can map to same physical bus
- **DBC File Association**: Each logical bus tracks its source DBC file
- **Runtime Mapping**: Logical buses aggregated to physical buses at init

**Configuration Sections (v12 format):**
1. Product information
2. Control/Sensor definitions
3. **Logical buses** (NEW - replaces fixed can[0/1/2] sections)
4. Network interface configuration
5. Internal sensors configuration
6. DBC signal settings
7. DBC files metadata
8. CAN bus hardware configuration
9. Ethernet CAN format

**For Detailed v12 Information:**
- See `Fleet-Connect-1/docs/NEW_DEVELOPER_GUIDE_V12.md` - Complete v12 guide
- See `iMatrix/canbus/can_structs.h` lines 733-782 - Structure definition
- See `Fleet-Connect-1/WRP_CONFIG_V12_IMPLEMENTATION_SUMMARY.md` - Migration details

### 6. Logging and Debugging

**Log Levels:**
```c
// Conditional logging
#ifdef PRINT_DEBUGS_APP_GENERAL
#define PRINTF(...) imx_cli_log_printf(true, __VA_ARGS__)
#else
#define PRINTF(...)
#endif
```

**Debug Flags:**
```bash
# Enable specific debug output
debug DEBUGS_APP_CAN
debug DEBUGS_FOR_ETH0_NETWORKING
debug DEBUGS_APP_ENERGY_MANAGER
```

**Logging Functions:**
```c
// With timestamp
imx_cli_log_printf(true, "Message with timestamp");

// Without timestamp
imx_cli_log_printf(false, "Raw message");

// Print to console only
imx_printf("Console message\n");
```

---

## Development Environment

### Prerequisites

**Required Tools:**
```bash
# Build tools
sudo apt-get install build-essential cmake git

# Libraries
sudo apt-get install libncurses5-dev libcurl4-openssl-dev

# Optional: For profiling and debugging
sudo apt-get install valgrind gdb
```

### Building the Project

**CMake Build:**
```bash
cd Fleet-Connect-1
mkdir -p build
cd build
cmake ..
make -j$(nproc)
```

**Build Outputs:**
- `Fleet-Connect`: Main gateway executable
- `*.cfg.bin`: Configuration files (if building with CAN_DM)

### Running the Application

**Basic Execution:**
```bash
# Normal operation (requires v12 config file)
./Fleet-Connect

# Print v12 configuration details and exit
./Fleet-Connect -P

# Print v12 configuration summary with logical buses and exit
./Fleet-Connect -S

# Display configuration version and summary and exit
./Fleet-Connect -I

# With specific config file
./Fleet-Connect -c /path/to/config.cfg.bin
```

**Command-Line Options (v12):**
- `-P`: Print configuration details and exit
  - Shows: Product ID (decimal + hex), logical buses, network, sensors
  - Example output: `Product ID: 2201718576 (0x83400A30)`
  - Requires v12 config file

- `-S`: Print configuration summary with logical bus breakdown and exit
  - Shows per-bus details: `Bus 0 (PT): PhysBus=2, Nodes=56`
  - Perfect for quick verification
  - Displays Product ID in both decimal and hexadecimal

- `-I`: Display configuration version and summary and exit
  - Shows file version (must be 12)
  - Displays logical bus architecture
  - Version compatibility check

**Version Compatibility:**
- ✅ **v12 files**: Fully supported (current)
- ❌ **v11 files**: NOT supported - regenerate with CAN_DM v12+
- All command-line options require v12 format

**For More Details:**
- See `Fleet-Connect-1/docs/command_line_options.md` - Complete reference
- See `Fleet-Connect-1/docs/NEW_DEVELOPER_GUIDE_V12.md` - v12 developer guide

### Development Workflow

1. **Make Changes**: Edit source files
2. **Build**: `cd build && make`
3. **Test**: Run with test configuration
4. **Debug**: Use GDB or add logging
5. **Commit**: Follow git workflow

**Recommended IDE Setup:**
- **VS Code**: With C/C++ extension
- **CLion**: Full CMake integration
- **Vim/Emacs**: With YouCompleteMe or LSP

---

## Getting Started

### First Steps

1. **Clone and Initialize**
   ```bash
   git clone --recurse-submodules <repository-url>
   cd iMatrix_Client
   git submodule update --init --recursive
   ```

2. **Read Key Documentation**
   - CLAUDE.md (development guidelines)
   - README.md (project overview)
   - This document (architecture)

3. **Explore the Code**
   ```bash
   # Main entry point
   less Fleet-Connect-1/linux_gateway.c

   # Core processing
   less Fleet-Connect-1/do_everything.c

   # CAN subsystem
   less iMatrix/canbus/can_sample.c

   # Network manager
   less iMatrix/networking/process_network.c
   ```

4. **Build and Run**
   ```bash
   cd Fleet-Connect-1
   mkdir build && cd build
   cmake ..
   make

   # Print config (if you have a .cfg.bin file)
   ./Fleet-Connect -P
   ```

### Understanding Data Flow

**Example: CAN Message Processing**

1. **CAN Frame Received** → Hardware driver
2. **Queued for Processing** → CAN thread
3. **Node Lookup** → Hash table O(1) lookup
4. **Signal Extraction** → DBC-generated code
5. **Value Scaling** → Apply scale/offset
6. **Memory Write** → MM2 system
7. **Cloud Upload** → iMatrix upload queue

**Example: Sensor Data Upload**

1. **Sensor Sampled** → `imx_sample_csd_data()`
2. **Data Written** → `mm2_write_sensor_data()`
3. **RAM Storage** → Memory sectors
4. **Spillover** → Disk files (if RAM full)
5. **Upload Read** → `mm2_read_next_record()`
6. **CoAP Packet** → `imatrix_transmit.c`
7. **Acknowledge** → `mm2_acknowledge_records()`

### Common Tasks

#### Adding a New Sensor

1. **Define Sensor ID** (in product JSON or internal_sensors_def.h)
   ```c
   #define IMX_INTERNAL_SENSOR_MY_SENSOR  (12345)
   ```

2. **Add to Configuration**
   ```c
   // In sensors_def.c
   imx_control_sensor_block_t my_sensor = {
       .name = "My Sensor",
       .id = IMX_INTERNAL_SENSOR_MY_SENSOR,
       .sample_rate = 5000,  // 5 seconds
       .poll_rate = 1000,     // 1 second
       .data_type = IMX_FLOAT,
       .enabled = 1,
   };
   ```

3. **Implement Sampling**
   ```c
   void sample_my_sensor(imx_time_t current_time, uint16_t entry) {
       float value = read_hardware();
       imx_set_control_sensor(IMX_SENSORS, entry, &value);
   }
   ```

4. **Add to Initialization**
   ```c
   // In init.c
   init_my_sensor();
   ```

#### Adding a New Vehicle Profile

1. **Create Vehicle Directory**
   ```bash
   mkdir Fleet-Connect-1/my_vehicle
   ```

2. **Implement Vehicle Interface**
   ```c
   // my_vehicle.h
   void my_vehicle_init(void);
   void my_vehicle_process(imx_time_t current_time);

   // my_vehicle.c
   void my_vehicle_init(void) {
       // Initialize vehicle-specific resources
   }

   void my_vehicle_process(imx_time_t current_time) {
       // Process vehicle data
   }
   ```

3. **Add to Main Loop**
   ```c
   // In do_everything.c
   if (cb.can_controller->product_id == IMX_MY_VEHICLE) {
       my_vehicle_process(current_time);
   }
   ```

4. **Update CMakeLists.txt**
   ```cmake
   set(MY_VEHICLE_SOURCES
       my_vehicle/my_vehicle.c
       my_vehicle/my_vehicle_helpers.c
   )
   target_sources(Fleet-Connect PRIVATE ${MY_VEHICLE_SOURCES})
   ```

---

## Common Development Patterns

### Pattern 1: Periodic Task

```c
void process_periodic_task(imx_time_t current_time) {
    static imx_time_t last_execution = 0;
    const uint32_t INTERVAL = 5000;  // 5 seconds

    if (imx_is_later(current_time, last_execution + INTERVAL)) {
        // Perform task
        do_work();

        last_execution = current_time;
    }
}
```

### Pattern 2: State Machine with Timeout

```c
typedef enum {
    STATE_IDLE,
    STATE_WORKING,
    STATE_COMPLETE,
    STATE_ERROR
} my_state_t;

void process_state_machine(imx_time_t current_time) {
    static my_state_t state = STATE_IDLE;
    static imx_time_t state_start_time = 0;
    const uint32_t TIMEOUT = 10000;  // 10 seconds

    switch (state) {
        case STATE_IDLE:
            if (should_start_work()) {
                state = STATE_WORKING;
                state_start_time = current_time;
            }
            break;

        case STATE_WORKING:
            // Check timeout
            if (imx_is_later(current_time, state_start_time + TIMEOUT)) {
                imx_printf("Timeout in STATE_WORKING\n");
                state = STATE_ERROR;
                break;
            }

            // Do work
            if (work_complete()) {
                state = STATE_COMPLETE;
            }
            break;

        case STATE_COMPLETE:
            // Reset to idle
            state = STATE_IDLE;
            break;

        case STATE_ERROR:
            // Handle error and retry
            if (can_retry()) {
                state = STATE_IDLE;
            }
            break;
    }
}
```

### Pattern 3: Safe Sensor Access

```c
float get_sensor_value_safe(uint16_t sensor_entry) {
    if (sensor_entry >= mgs.no_control_sensors) {
        imx_printf("Invalid sensor entry: %u\n", sensor_entry);
        return 0.0f;
    }

    if (!mgs.csd[sensor_entry].valid) {
        imx_printf("Sensor %u not valid yet\n", sensor_entry);
        return 0.0f;
    }

    return mgs.csd[sensor_entry].last_value.float_32bit;
}
```

### Pattern 4: Error Propagation

```c
imx_result_t multi_step_operation(void) {
    imx_result_t result;

    // Step 1
    result = step1();
    if (result != IMX_SUCCESS) {
        imx_printf("Step 1 failed: %s\n", imx_error(result));
        return result;
    }

    // Step 2
    result = step2();
    if (result != IMX_SUCCESS) {
        imx_printf("Step 2 failed: %s\n", imx_error(result));
        cleanup_step1();
        return result;
    }

    // Success
    return IMX_SUCCESS;
}
```

### Pattern 5: Memory Management

```c
void process_sensor_data(uint32_t sensor_id, float value) {
    imx_data_32_t data;
    data.float_32bit = value;

    imx_utc_time_ms_t timestamp;
    imx_time_get_utc_time_ms(&timestamp);

    imx_result_t result = mm2_write_sensor_data(
        IMX_UPLOAD_GATEWAY,    // Upload source
        sensor_id,             // Sensor ID
        IMX_FLOAT,             // Data type
        data,                  // Value
        timestamp,             // Timestamp
        false                  // Add GPS location
    );

    if (result != IMX_SUCCESS) {
        imx_printf("Failed to write sensor data: %s\n", imx_error(result));
    }
}
```

---

## Debugging and Troubleshooting

### Common Debug Techniques

#### 1. Enable Debug Logging

```c
// In source file
#define PRINT_DEBUGS_APP_GENERAL
#include "common.h"

#ifdef PRINT_DEBUGS_APP_GENERAL
#define PRINTF(...) imx_cli_log_printf(true, __VA_ARGS__)
#else
#define PRINTF(...)
#endif

void my_function(void) {
    PRINTF("Entering my_function\n");
    // ...
}
```

#### 2. Use CLI Debug Commands

```bash
# Enable CAN debug
debug DEBUGS_APP_CAN

# Enable network debug
debug DEBUGS_FOR_ETH0_NETWORKING

# Show all debug flags
debug show

# Disable all debug
debug none
```

#### 3. GDB Debugging

```bash
# Build with debug symbols
cmake -DCMAKE_BUILD_TYPE=Debug ..
make

# Run under GDB
gdb ./Fleet-Connect

# GDB commands
(gdb) break do_everything
(gdb) run
(gdb) print mgs.can_bus_profile_loaded
(gdb) backtrace
```

#### 4. Valgrind Memory Analysis

```bash
# Check for memory leaks
valgrind --leak-check=full --show-leak-kinds=all ./Fleet-Connect

# Track memory usage
valgrind --tool=massif ./Fleet-Connect
ms_print massif.out.*
```

### Common Issues and Solutions

#### Issue: CAN Bus Not Receiving Data

**Symptoms:**
- `mgs.last_can_msg` not updating
- No sensor data from vehicle

**Diagnosis:**
```bash
# Check CAN interface
ifconfig can0

# Check for CAN errors
candump can0
```

**Solutions:**
1. Verify CAN hardware configuration
2. Check baud rate setting (usually 500000 or 250000)
3. Ensure CAN bus is terminated
4. Check `can_stats` for errors

#### Issue: Network Manager Stuck

**Symptoms:**
- No network connectivity
- State not progressing

**Diagnosis:**
```bash
# Enable network debug
debug DEBUGS_APP_NETWORK_MANAGER

# Check interface status
ifconfig
ip route
```

**Solutions:**
1. Check DHCP client status: `ps aux | grep dhcp`
2. Verify interface is up: `ifconfig eth0 up`
3. Check cooldown period (default 30 seconds)
4. Review state transitions in logs

#### Issue: Memory Manager Errors

**Symptoms:**
- "Out of sectors" errors
- Data not being uploaded
- Memory corruption warnings

**Diagnosis:**
```bash
# Check memory statistics
mem stats

# Check disk usage
df -h /usr/qk/etc/sv/
```

**Solutions:**
1. Verify disk space available
2. Check for stuck pending data
3. Force acknowledge if upload is stalled
4. Consider increasing sector allocation

#### Issue: Configuration Not Loading

**Symptoms:**
- "Config file not found"
- "Invalid checksum"
- Missing sensors/controls

**Diagnosis:**
```bash
# Print configuration
./Fleet-Connect -P

# Check file integrity
file *.cfg.bin
ls -lh *.cfg.bin
```

**Solutions:**
1. Regenerate configuration with CAN_DM
2. Verify file path and permissions
3. Check configuration version compatibility
4. Validate product ID matches

---

## Further Resources

### v12 Configuration Migration (November 2025)

**Status**: ✅ **MIGRATION COMPLETE**

The configuration system was migrated from v11 to v12 in November 2025. This was a **breaking change** that introduced dynamic logical CAN bus support.

**Key Changes:**
- API functions renamed with `_v12` suffix
- Fixed 3-bus array → Dynamic logical bus array
- Structure field names differ from original migration docs (see corrections)
- Product ID now displayed in decimal AND hexadecimal: `2201718576 (0x83400A30)`

**⚠️ IMPORTANT for New Developers:**
- Original migration documentation has **INCORRECT field names**
- Always use `iMatrix/canbus/can_structs.h` as source of truth
- See `Fleet-Connect-1/docs/NEW_DEVELOPER_GUIDE_V12.md` for complete onboarding

**Migration Documentation:**
- **START HERE**: `Fleet-Connect-1/docs/NEW_DEVELOPER_GUIDE_V12.md` (Correct field names)
- `Fleet-Connect-1/WRP_CONFIG_V12_IMPLEMENTATION_SUMMARY.md` (Complete change log)
- `Fleet-Connect-1/docs/command_line_options.md` (Updated for v12)
- ⚠️ `Fleet-Connect-1/init/WRP_CONFIG_V12_MIGRATION.md` (Field names WRONG - has warnings)
- ⚠️ `Fleet-Connect-1/init/WRP_CONFIG_QUICK_REFERENCE.md` (Field names WRONG - has warnings)

**Actual Structure Definitions:**
- `iMatrix/canbus/can_structs.h` lines 733-782: `config_v12_t`
- `iMatrix/canbus/can_structs.h` lines 695-717: `logical_bus_config_t`

**Migration Branch**: `feature/wrp-config-v12-migration` (ready for merge)

---

### Documentation Files

- **CLAUDE.md**: Development workflow and guidelines (updated for v12)
- **README.md**: Project overview and quick start
- **NEW_DEVELOPER_GUIDE_V12.md**: **NEW** - Complete v12 onboarding guide
- **MM2_MIGRATION_PLAN.md**: Memory manager v2 migration guide
- **projectplan.md**: Current development plan
- **progress.md**: Development progress tracking
- **project_todo.md**: Known issues and planned improvements

### Key Header Files

- **imatrix.h**: Public API for iMatrix core
- **common.h**: Common types and definitions
- **storage.h**: Storage structures and configuration
- **can_structs.h**: CAN subsystem structures
- **mm2_api.h**: Memory manager API

### Code Templates

- **iMatrix/templates/blank.h**: Header file template
- **iMatrix/templates/blank.c**: Source file template

### External Resources

- **iMatrix Cloud API**: Documentation available from iMatrix Systems
- **CAN Bus Standards**: ISO 11898 (CAN), J1939 (heavy-duty)
- **OBD2 Specification**: ISO 15765-4
- **CoAP Protocol**: RFC 7252

### Contact and Support

- **Technical Lead**: greg.phillips@imatrixsystems.com
- **Project Repository**: Internal Git server
- **Issue Tracking**: GitHub Issues or internal tracker

---

## Appendix: Quick Reference

### Important Timing Intervals

| Task | Interval | Notes |
|------|----------|-------|
| Main Loop | 100ms | `IMX_PROCESS_INTERVAL` |
| GPS Events | 1s-2min | Speed-dependent |
| GPIO Sampling | 1s | Digital inputs |
| Accelerometer | 100ms | G-force monitoring |
| Power Monitoring | 100ms | Battery/charging |
| CAN Sampling | Real-time | Event-driven |
| Network Check | 10s | Connectivity verification |
| Memory Stats | 60s | Memory usage logging |

### Common File Locations

| Item | Path |
|------|------|
| Configuration | `/usr/qk/etc/sv/memory_test/*.cfg.bin` |
| Log Files | `/var/log/fleet-connect/` |
| Disk Storage | `/usr/qk/etc/sv/memory_test/spool/` |
| PID Files | `/var/run/` |

### CLI Commands

| Command | Purpose |
|---------|---------|
| `can status` | CAN bus status |
| `can unknown` | Unknown CAN IDs |
| `net status` | Network status |
| `net interfaces` | Interface details |
| `mem stats` | Memory statistics |
| `mem dump` | Memory contents |
| `debug <flag>` | Enable debug |
| `e carb` | CARB compliance |
| `e trip` | Trip report |
| `e theft` | Energy theft detection |

### Error Codes

| Code | Name | Meaning |
|------|------|---------|
| 0 | `IMX_SUCCESS` | Operation successful |
| 1 | `IMX_INVALID_ENTRY` | Invalid sensor/control entry |
| 14 | `IMX_OUT_OF_MEMORY` | Memory allocation failed |
| 40 | `IMX_TIMEOUT` | Operation timed out |
| 47 | `IMX_CAN_NODE_NOT_FOUND` | CAN node ID not in database |
| 53 | `IMX_FAIL_MEMORY_INIT` | Memory system initialization failed |

---

**End of Fleet-Connect System Overview**

This document is maintained in the repository and updated as the system evolves. Contributions and corrections are welcome!

