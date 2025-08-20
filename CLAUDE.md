# CLAUDE.md - iMatrix Source Repository Guide

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in the iMatrix ecosystem.

## Repository Overview

The iMatrix_src repository is the master development environment containing three critical submodules for the iMatrix IoT platform:

- **Fleet-Connect-1**: Gateway application for vehicle connectivity and OBD2/CAN bus processing
- **iMatrix**: Core embedded system with memory management, networking, BLE, and cloud connectivity
- **CAN_DM**: CAN bus Device Manager for processing DBC files and generating device configurations

## Submodule Management

This repository uses Git submodules to manage the three main components:

```bash
# Current submodule configuration
[submodule "CAN_DM"]
    path = CAN_DM
    url = https://github.com/sierratelecom/CAN_DM.git
[submodule "iMatrix"]
    path = iMatrix
    url = https://github.com/sierratelecom/iMatrix-WICED-6.6-Client.git
    branch = feature/network-mode-switching
[submodule "Fleet-Connect-1"]
    path = Fleet-Connect-1
    url = https://github.com/sierratelecom/Fleet-Connect-1.git
    branch = QConnect-Updates
```

### Working with Submodules

```bash
# Clone with submodules
git clone --recurse-submodules <repository-url>

# Update all submodules
git submodule update --init --recursive

# Pull latest changes in submodules
git submodule update --remote

# Work in a specific submodule
cd Fleet-Connect-1
git checkout <branch>
git pull origin <branch>
```

## Common Development Workflow

### Implementation Guidelines

1. **Think and Plan First**: Read the codebase for relevant files and write a plan to projectplan.md
2. **Create Todo Lists**: Break down tasks into manageable items that can be checked off
3. **Get Verification**: Check with the user before beginning major work
4. **Work Incrementally**: Complete todo items one at a time, marking as complete
5. **Provide Updates**: Give high-level explanations of changes at each step
6. **Keep It Simple**: Make minimal, focused changes that impact as little code as possible
7. **Document Thoroughly**: Use extensive Doxygen comments for all routines
8. **Explain Code Flow**: Add comments to clarify logic and flow
9. **Use Templates**: For C files, use blank.h and blank.c as templates
10. **Optimize for Embedded**: This is an embedded system requiring optimal efficiency

### Tracking Guidelines

1. **Update projectplan.md** as the project advances
2. **Update progress.md** with each step completed
3. **Update project_todo.md** with all major issues found
4. **Ask Questions** when unclear and add answers to projectplan.md
5. **Add Review Section** to projectplan.md with summary of changes

### File Structure Best Practices

- Use Doxygen comment structure for all functions
- Follow existing code conventions in each module
- Add new source files to CMakeLists.txt
- Keep architecture consistent with existing patterns

## Fleet-Connect-1 Submodule

### Overview
Gateway application for vehicle connectivity, integrating OBD2 protocols, CAN bus processing, and iMatrix cloud platform.

### Key Components
- **OBD2/**: OBD2 protocol implementation with PID decoding
- **can_process/**: CAN bus message processing and state management
- **cli/**: Command line interface
- **hal/**: Hardware abstraction layer
- **init/**: System initialization
- **power/**: Power management
- **product/**: Product-specific configurations

### Main Files
- **linux_gateway.c**: Main gateway application entry point
- **do_everything.c**: Core processing logic and state machine

### CAN Subsystem State Machine
The CAN processing uses a state machine with critical states:
- `CBS_INITIAL`: Starting state
- `CBS_SETUP_CAN_SERVER`: Initialize CAN server
- `CBS_START_CAN_SERVER`: Start server operations
- `WAIT_FOR_CAN_BUS`: Wait for CAN availability
- `CBS_CAN_BUS_REGISTRATION`: Vehicle registration process
- `CBS_RESTART_CAN_BUS`: Recovery state

### Common Issues and Solutions

#### State Machine Patterns
- **Missing Break Statements**: Always verify case termination
- **State Name Mismatches**: Ensure consistency between enums and usage
- **Unimplemented States**: Never leave empty case statements
- **Timer Discrepancies**: Use named constants for timer values

#### Registration Flow
- **Blocking Operations**: Restructure to allow concurrent operations
- **Vehicle Type Handling**: Audit all vehicle type requirements
- **VIN Requirements**: HM_WRECKER and LIGHT_VEHICLE need VIN

## iMatrix Core Submodule

### Overview
Core embedded system functionality providing the foundation for all iMatrix products.

### Architecture

#### Platform Support
- **IMX_Platform/LINUX_Platform/**: Linux platform implementation
  - Networking subsystem with multi-interface support
  - BLE integration
  - Platform-specific drivers
- **IMX_Platform/WICED_Platform/**: WICED platform support

#### Core Components
- **ble/**: Bluetooth Low Energy with client and manager
- **canbus/**: CAN bus processing and signal extraction
- **cli/**: Comprehensive command line interface
- **coap/**: CoAP protocol implementation
- **device/**: Device configuration and initialization
- **imatrix_upload/**: Cloud platform data upload
- **location/**: GPS and geofencing
- **networking/**: Network management and connectivity
- **storage/**: Flash memory and data storage
- **encryption/**: Security and cryptography
- **cs_ctrl/**: Memory management subsystem

### Network Manager
Multi-interface network management with state machine control:
- Supports Ethernet, WiFi, Cellular (PPP), and more
- Opportunistic discovery for new interfaces
- DHCP client management with PID tracking
- Cooldown periods for interface stability

### Memory Management
- Tiered storage system with RAM and disk spillover
- Custom memory pools for efficient allocation
- Recovery mechanisms for corruption
- Statistics and monitoring

## CAN_DM Submodule

### Overview
Standalone tool for processing DBC files and generating iMatrix device configurations from CAN bus definitions.

### Build System
```bash
# Primary build (macOS/WSL/Linux)
./build_macos.sh

# Manual CMake build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

### Usage
```bash
# Basic usage with DBC files
./build/CAN_DM -u username -p password -0 powertrain.dbc -1 bodycontrols.dbc

# With product name
./build/CAN_DM -u username -p password -0 file.dbc -n product_name

# Debug mode
./build/CAN_DM -D -u username -p password -0 file.dbc
```

### Core Processing Pipeline
1. **DBC Parsing** (process_dbc.c): State machine parser
2. **Signal Processing** (process_sg.c, process_bo.c): Extract messages/signals
3. **Configuration Generation** (config_gen.c): Create device configs
4. **iMatrix Integration** (imatrix_api.c): Cloud platform upload
5. **Code Generation** (add_include_file.c): Generate C headers

### Multi-Bus Support
- **CAN Bus 0** (-0): Primary powertrain/engine
- **CAN Bus 1** (-1): Body controls and comfort
- **CAN Bus 2** (-2): Ethernet/high-speed data

## Cross-Module Integration

### Shared Components
- **iMatrix Core** is used by both Fleet-Connect-1 and test_scripts
- **Memory Management** from iMatrix/cs_ctrl is shared across projects
- **Platform Abstraction** allows code reuse between Linux and WICED

### Build Dependencies
```bash
# Fleet-Connect-1 depends on iMatrix
cd Fleet-Connect-1
cmake -DiMatrix_DIR=../iMatrix ...

# CAN_DM uses iMatrix memory implementation
cd CAN_DM
cmake -DIMATRIX_DIR=../iMatrix ...
```

### Testing Integration
The test_scripts directory provides comprehensive testing for:
- Memory management (from iMatrix/cs_ctrl)
- Network manager functionality
- Platform-specific implementations

## Debugging Patterns and Lessons Learned

### Network Manager Debugging

#### Test File Analysis Process
1. Review test logs (e.g., nt_11.txt) for state transitions
2. Identify stuck states or invalid transitions
3. Search for patterns with grep
4. Trace state machine flow in process_network.c
5. Test fixes against multiple scenarios

#### Key Debugging Patterns
- Look for "State transition blocked" messages
- Check COMPUTE_BEST output for interface selection
- Monitor "opportunistic" discovery messages
- Verify DHCP clients with PID files
- Track cooldown periods

#### Common Network Issues
1. **Stuck States**: Check state transition validation
2. **IP Persistence**: Ensure DHCP clients killed with PID files
3. **Missing Interfaces**: Verify opportunistic discovery
4. **Segfaults**: Add bounds checking for INVALID_INTERFACE
5. **First Run Failures**: Check apply_interface_effects() deferral
6. **False Interface Failures**: Add test routes for non-default
7. **DHCP Status Wrong**: Check udhcpc not udhcpd

### CAN Subsystem Debugging

#### State Machine Issues
- **Missing Break Statements**: Falls through to next case
- **State Name Mismatches**: Transitions fail or go undefined
- **Unimplemented States**: System stuck with no transitions
- **Timer Discrepancies**: Delays don't match requirements

#### Registration Flow Issues
- **Blocking Operations**: System stops during prerequisites
- **Vehicle Type Handling**: Inconsistent requirements
- **VIN Requirements**: Some vehicles need VIN, others don't

### General Debugging Techniques
1. **State Transition Logging**: Add logging for every state change
2. **Flow Analysis**: Trace execution through state machines
3. **Pattern Recognition**: Find similar issues across codebase
4. **Incremental Testing**: Fix one issue at a time with verification

## Build Systems Overview

### Fleet-Connect-1 & iMatrix
- CMake-based build system
- Add new files to CMakeLists.txt
- Build output in build/ directory

### CAN_DM
- Standalone CMake configuration
- Cross-platform support (macOS, WSL, Linux)
- Automated dependency detection

### Test Scripts
```bash
cd test_scripts
cmake .
make
./run_tiered_storage_tests.sh
```

## Additional Resources

### Other Directories (Not Submodules)
- **btstack/**: Bluetooth stack (if present)
- **mbedtls/**: TLS and cryptography library
- **test_scripts/**: Comprehensive test suite
- **docs/**: Project documentation
- **scripts/**: Build and utility scripts

### External Dependencies
- ncurses (TUI support)
- cURL (HTTP/HTTPS)
- cJSON (JSON parsing)
- MariaDB client (database)

## Important Notes

1. **This is an embedded system** - optimize for efficiency
2. **Follow existing patterns** - maintain consistency
3. **Test thoroughly** - use provided test scripts
4. **Document everything** - Doxygen and inline comments
5. **Keep changes minimal** - simplicity is key

---

*Last Updated: 2025-08-20*
*This guide consolidates information from all submodule CLAUDE.md files and project documentation.*