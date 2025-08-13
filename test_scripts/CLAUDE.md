## User Development Workflow Guide - implementation

1. First think through the problem, read the codebase for relevant files, and write a plan to projectplan.md.
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. Please every step of the way just give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. Always use extensive doxygen comment structre for all routines.
8. Add extensive comments to explain the flow of the code.
9. For C language implementations always use blank.h and blank.c as the templates for new source code files
10. This is an embedded system that must use optimal efficiency

## User Development Project Source Code direcories
Use the following directoies for all source code
/home/greg/Fleet-Connect-1
/home/greg/iMatrix

The iMatrix directory contains the iMatrix Client that is used by several projects.
This project uses the Fleet-Connect-1 directory as the main base of the project.

## Project Initialization

### Codebase Structure


#### iMatrix Components:
- **IMX_Platform/**: Platform-specific implementations (Linux/WICED)
  - **LINUX_Platform/**: Linux platform support with networking and BLE
  - **WICED_Platform/**: WICED platform support
- **ble/**: Bluetooth Low Energy implementation
  - **ble_client/**: BLE client functionality
  - **ble_manager/**: BLE device management and known devices
- **canbus/**: CAN bus processing and signal extraction
- **cli/**: Comprehensive command line interface
- **coap/**: CoAP protocol implementation
- **coap_interface/**: CoAP interface definitions
- **device/**: Device configuration and initialization
- **imatrix_upload/**: Data upload to iMatrix platform
- **location/**: GPS and geofencing functionality
- **networking/**: Network utilities and connection management
- **ota_loader/**: Over-the-air update functionality
- **wifi/**: WiFi connection and management
- **json/**: JSON parsing utilities
- **time/**: Time management and NTP
- **storage/**: Data storage and flash memory management
- **encryption/**: Security and encryption utilities

### Build System
- Uses CMake build system (CMakeLists.txt)
- Build output goes to build/ directory

### Development Templates
- Use **blank.h** and **blank.c** as templates for new C source files
- Follow existing doxygen comment structure for all routines

## User Development Workflow Guide - tracking
1. Create and update the projectplan.md as the project advances.
2. Create and update the progress.md with each step as the project advances.
3. Create and update the project_todo.md with all major issues found during review of the project.
4. Ask me any additional questions that are not clear and then add the answers to the projectplan.md
5. Finally, add a review section to the projectplan.md file with a summary of the changes you made and any other relevant information.
