# iMatrix Developer Onboarding Guide

## Welcome to iMatrix Development

This guide will help you get up to speed with the iMatrix ecosystem, understand the codebase architecture, and prepare you for productive development. Read this document thoroughly before starting any development work.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Development Environment Setup](#development-environment-setup)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Key Concepts & Terminology](#key-concepts--terminology)
5. [Code Organization](#code-organization)
6. [Common Development Tasks](#common-development-tasks)
7. [Build Systems](#build-systems)
8. [Testing & Debugging](#testing--debugging)
9. [Best Practices & Guidelines](#best-practices--guidelines)
10. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
11. [Resources & Getting Help](#resources--getting-help)

---

## 1. System Overview

### What is iMatrix?

iMatrix is a sophisticated IoT telemetry platform designed for vehicle and industrial monitoring. It consists of:

- **Core Library (iMatrix)**: Embedded system functionality for data collection, storage, and transmission
- **Gateway Application (Fleet-Connect-1)**: Vehicle connectivity gateway managing OBD2/CAN bus data
- **CAN Device Manager (CAN_DM)**: Tool for processing DBC files and generating device configurations

### Target Platforms

The system runs on two vastly different platforms:

| Platform | Hardware | Constraints | Use Case |
|----------|----------|-------------|----------|
| **STM32** | ARM Cortex-M MCU | 256KB RAM, 2MB Flash | Embedded vehicle devices |
| **Linux** | iMX6 processor | 1GB RAM, 8GB storage | Gateway units |

**CRITICAL**: Code must be optimized for BOTH platforms. STM32 constraints drive design decisions.

### System Architecture

```
┌────────────────────────────────────────┐
│         Cloud Platform (iMatrix)        │
│            REST API / CoAP               │
└────────────────────────────────────────┘
                    ↑
                    │ HTTPS/CoAP
                    │
┌────────────────────────────────────────┐
│        Fleet-Connect-1 Gateway          │
│   ┌──────────────────────────────┐      │
│   │    iMatrix Core Library       │      │
│   │  (Memory, Network, Storage)   │      │
│   └──────────────────────────────┘      │
│   ┌──────────────────────────────┐      │
│   │   CAN/OBD2 Processing         │      │
│   └──────────────────────────────┘      │
└────────────────────────────────────────┘
                    ↑
                    │ CAN/OBD2
                    │
        ┌───────────┴──────────┐
        │                      │
    Vehicle CAN           OBD2 Port
```

---

## 2. Development Environment Setup

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    gcc-arm-none-eabi \  # For STM32 cross-compilation
    libncurses-dev \      # For TUI support
    libcurl4-openssl-dev \# For HTTP/HTTPS
    mariadb-client \      # For database connectivity
    valgrind \            # For memory debugging
    gdb                   # For debugging
```

### Repository Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/your-org/iMatrix_Client.git
cd iMatrix_Client

# Update submodules to correct branches
git submodule update --init --recursive

# Checkout feature branches
cd Fleet-Connect-1
git checkout QConnect-Updates
cd ../iMatrix
git checkout feature/network-mode-switching
cd ..
```

### Build Environment Configuration

Create a local build configuration file:

```bash
# Create .env.local (not tracked by git)
cat > .env.local << EOF
# Platform target (LINUX or STM32)
PLATFORM=LINUX

# Debug level (0-5, higher = more verbose)
DEBUG_LEVEL=3

# Enable memory tracking
ENABLE_MEMORY_TRACKING=1

# Path to STM32 toolchain (if building for STM32)
STM32_TOOLCHAIN=/opt/gcc-arm-none-eabi/bin/

# iMatrix API credentials (for CAN_DM)
IMATRIX_USERNAME=your_username
IMATRIX_PASSWORD=your_password
EOF
```

### IDE Setup (VS Code Recommended)

```bash
# Install recommended extensions
code --install-extension ms-vscode.cpptools
code --install-extension ms-vscode.cmake-tools
code --install-extension marus25.cortex-debug  # For STM32 debugging
```

Create `.vscode/c_cpp_properties.json`:

```json
{
    "configurations": [
        {
            "name": "Linux",
            "includePath": [
                "${workspaceFolder}/**",
                "${workspaceFolder}/iMatrix",
                "${workspaceFolder}/Fleet-Connect-1"
            ],
            "defines": ["LINUX_PLATFORM"],
            "compilerPath": "/usr/bin/gcc",
            "cStandard": "c11",
            "intelliSenseMode": "gcc-x64"
        },
        {
            "name": "STM32",
            "includePath": [
                "${workspaceFolder}/**",
                "${workspaceFolder}/iMatrix"
            ],
            "defines": ["STM32_PLATFORM"],
            "compilerPath": "/opt/gcc-arm-none-eabi/bin/arm-none-eabi-gcc",
            "cStandard": "c11",
            "intelliSenseMode": "gcc-arm"
        }
    ]
}
```

---

## 3. Architecture Deep Dive

### Memory Management Architecture

The memory system is THE most critical component. It uses a tiered approach:

```
Application Layer
    ↓ Write APIs (imx_write_tsd, imx_write_evt)
MM2 API Layer
    ↓ Pool allocation
MM2 Core (Memory pools, 128-byte sectors)
    ↓ Pressure threshold
Platform Layer
    ├─ STM32: Flash storage only
    └─ Linux: RAM + Disk spillover
```

**Key Points:**
- Fixed 128-byte sectors for efficiency
- 75% space utilization target
- Per-sensor, per-upload-source isolation
- Power-safe on both platforms

### Network Architecture (Linux Only)

```
Network Manager State Machine
    ├─ Interface Discovery (Ethernet, WiFi, Cellular)
    ├─ DHCP Management
    ├─ Failover Logic
    └─ Connection Monitoring
```

**Key States:**
- `IDLE`: No network activity
- `DISCOVERING`: Finding interfaces
- `CONNECTING`: Establishing connection
- `CONNECTED`: Active data transmission
- `FAILED`: Connection lost, initiating failover

### CAN/OBD2 Processing

```
CAN Bus → CAN Server → Signal Extraction → Memory Manager → Upload Queue
                ↓
         DBC Processing
                ↓
         Signal Mapping
```

---

## 4. Key Concepts & Terminology

### Core Terms You Must Know

| Term | Definition | Context |
|------|------------|---------|
| **CSB** | Control Sensor Block | Configuration for a sensor |
| **CSD** | Control Sensor Data | Runtime data for a sensor |
| **TSD** | Time Series Data | Regular interval sensor data |
| **EVT** | Event Data | Irregular event-based data |
| **MMCB** | Memory Manager Control Block | Per-sensor memory state |
| **Upload Source** | Data destination identifier | Gateway, BLE, CAN device |
| **Sector** | 128-byte memory unit | Basic allocation unit |
| **Chain** | Linked list of sectors | How data is organized |
| **Spillover** | RAM→Disk transition | Linux memory pressure handling |

### Platform Macros

```c
#ifdef LINUX_PLATFORM
    // Linux-specific code
#else
    // STM32 code (default)
#endif
```

**RULE**: Never use platform-specific APIs without guards!

### Error Codes

```c
typedef enum {
    IMX_SUCCESS = 0,
    IMX_INVALID_PARAMETER = -1,
    IMX_NO_MEMORY = -2,
    IMX_NO_DATA = -3,
    IMX_TIMEOUT = -4,
    // ... see common.h for complete list
} imx_result_t;
```

---

## 5. Code Organization

### Directory Structure

```
iMatrix_Client/
├── Fleet-Connect-1/          # Gateway application
│   ├── linux_gateway.c       # Main entry point
│   ├── do_everything.c       # Core processing loop
│   ├── can_process/          # CAN bus handling
│   ├── obd2/                 # OBD2 protocols
│   └── cli/                  # Command interface
│
├── iMatrix/                  # Core library
│   ├── cs_ctrl/              # Memory management (MM2)
│   │   ├── mm2_api.h         # Public API
│   │   ├── mm2_core.c        # Core implementation
│   │   └── mm2_disk.c        # Linux disk spillover
│   ├── IMX_Platform/         # Platform abstraction
│   │   ├── LINUX_Platform/   # Linux-specific
│   │   └── STM32_Platform/   # STM32-specific
│   ├── networking/           # Network management
│   ├── storage/              # Flash/disk storage
│   ├── canbus/               # CAN processing
│   └── cli/                  # CLI framework
│
├── CAN_DM/                   # DBC processor
│   ├── process_dbc.c         # DBC parser
│   ├── config_gen.c          # Config generator
│   └── imatrix_api.c         # Cloud upload
│
├── test_scripts/             # Test harness
│   ├── memory_test/          # Memory subsystem tests
│   └── network_test/         # Network tests
│
└── docs/                     # Documentation
    ├── CLAUDE.md             # AI assistant guide
    └── *.md                  # Various docs
```

### File Naming Conventions

- **Platform-specific**: `imx_linux_*.c`, `imx_stm32_*.c`
- **Subsystems**: `{subsystem}_{function}.c` (e.g., `can_init.c`)
- **Headers**: Match source files exactly
- **Tests**: `test_{component}.c`

---

## 6. Common Development Tasks

### Task 1: Adding a New Sensor Type

```c
// 1. Define sensor in device_config.h
#define SENSOR_TYPE_NEW_SENSOR 0x50

// 2. Add to control blocks (storage.h)
typedef struct {
    uint16_t sensor_id;
    uint16_t sample_rate;  // 0 for EVT, >0 for TSD
    // ... other config
} new_sensor_config_t;

// 3. Initialize in device initialization
imx_control_sensor_block_t* csb = &icb.i_scb[sensor_index];
control_sensor_data_t* csd = &icb.i_sd[sensor_index];

csb->sensor_id = SENSOR_TYPE_NEW_SENSOR;
csb->sample_rate = 1000;  // 1Hz for TSD

// 4. Write data
imx_data_32_t value = {.value = sensor_reading};
imx_write_tsd(IMX_UPLOAD_GATEWAY, csb, csd, value);
```

### Task 2: Adding Platform-Specific Code

```c
// WRONG - Will break STM32 build
#include <pthread.h>
pthread_mutex_t my_mutex;

// CORRECT - Platform abstraction
#ifdef LINUX_PLATFORM
#include <pthread.h>
typedef pthread_mutex_t platform_mutex_t;
#else
typedef uint32_t platform_mutex_t;  // Or RTOS-specific
#endif

// In implementation file
#ifdef LINUX_PLATFORM
void platform_mutex_lock(platform_mutex_t* mutex) {
    pthread_mutex_lock(mutex);
}
#else
void platform_mutex_lock(platform_mutex_t* mutex) {
    // Disable interrupts or use RTOS primitive
    __disable_irq();
}
#endif
```

### Task 3: Memory-Efficient String Handling

```c
// WRONG - Stack overflow risk on STM32
void process_message(const char* msg) {
    char buffer[1024];  // Too large!
    strcpy(buffer, msg);  // Unsafe!
}

// CORRECT - Bounded and efficient
#define MAX_MSG_SIZE 128  // Platform-appropriate

void process_message(const char* msg) {
    static char buffer[MAX_MSG_SIZE];  // Static to save stack

    size_t len = strlen(msg);
    if (len >= MAX_MSG_SIZE) {
        return IMX_INVALID_PARAMETER;
    }

    strncpy(buffer, msg, MAX_MSG_SIZE - 1);
    buffer[MAX_MSG_SIZE - 1] = '\0';
}
```

### Task 4: Adding a CLI Command

```c
// 1. Add command definition (cli_commands.h)
#define CLI_CMD_MY_COMMAND "mycmd"

// 2. Implement handler (cli_commands.c)
void cli_handle_my_command(char* args) {
    imx_cli_print("Executing my command with args: %s\r\n", args);
    // Implementation
}

// 3. Register in command table (cli.c)
static const cli_command_t commands[] = {
    {CLI_CMD_MY_COMMAND, cli_handle_my_command, "My command description"},
    // ...
};
```

### Task 5: Debugging Memory Issues

```bash
# 1. Enable memory tracking
export ENABLE_MEMORY_TRACKING=1
cmake -DENABLE_MEMORY_TRACKING=ON ..

# 2. Run with valgrind (Linux only)
valgrind --leak-check=full --show-leak-kinds=all ./Fleet-Connect-1

# 3. Use built-in CLI commands
> memory status       # Show current usage
> memory allocations  # List active allocations
> memory test        # Run memory tests
```

---

## 7. Build Systems

### Building for Linux

```bash
cd Fleet-Connect-1
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug -DiMatrix_DIR=../../iMatrix ..
make -j$(nproc)
```

### Building for STM32

```bash
cd iMatrix
mkdir -p build_stm32
cd build_stm32
cmake -DCMAKE_TOOLCHAIN_FILE=../cmake/stm32_toolchain.cmake \
      -DPLATFORM=STM32 \
      -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

### Building CAN_DM Tool

```bash
cd CAN_DM
./build_macos.sh  # Or build_linux.sh
# Or manually:
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

### CMake Best Practices

Always add new source files to CMakeLists.txt:

```cmake
# Add platform-specific sources
if(LINUX_PLATFORM)
    list(APPEND SOURCES
        platform/linux/my_linux_file.c
    )
else()
    list(APPEND SOURCES
        platform/stm32/my_stm32_file.c
    )
endif()
```

---

## 8. Testing & Debugging

### Unit Testing

```bash
# Run memory subsystem tests
cd test_scripts
./run_tiered_storage_tests.sh

# Run specific test
./build/test_memory_basic
```

### Integration Testing

```bash
# Test CAN processing
./test_can_processing.sh sample_data.dbc

# Test network failover
./test_network_failover.sh
```

### Debugging Techniques

#### GDB for Linux

```bash
gdb ./Fleet-Connect-1
(gdb) break main
(gdb) run
(gdb) bt  # Backtrace on crash
```

#### STM32 Debugging

```bash
# Start OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg

# In another terminal
arm-none-eabi-gdb firmware.elf
(gdb) target remote localhost:3333
(gdb) monitor reset halt
(gdb) break main
(gdb) continue
```

#### Memory Debugging

```c
// Add debug prints
#ifdef DEBUG_MEMORY
#define MEM_DEBUG(fmt, ...) printf("[MEM] " fmt "\n", ##__VA_ARGS__)
#else
#define MEM_DEBUG(fmt, ...)
#endif

// Use in code
MEM_DEBUG("Allocating %zu bytes", size);
```

---

## 9. Best Practices & Guidelines

### Memory Management Rules

1. **No Dynamic Allocation on STM32**: Use static buffers or MM2 pools
2. **Check All Allocations**: Never assume malloc succeeds
3. **Free on Error Paths**: Use goto cleanup pattern
4. **Minimize Stack Usage**: <1KB per function on STM32
5. **Use Memory Pools**: For frequent allocations

### Platform Abstraction Rules

1. **Always Guard Platform Code**: Use `#ifdef LINUX_PLATFORM`
2. **Create Abstraction Layers**: Don't scatter #ifdefs
3. **Test Both Platforms**: Changes must work on both
4. **Document Platform Differences**: In function headers

### Error Handling Rules

1. **Check All Returns**: Every function that can fail
2. **Use Standard Error Codes**: From imx_result_t
3. **Clean Up Resources**: On error paths
4. **Log Errors**: But don't flood logs
5. **Fail Fast**: Don't continue with bad state

### Thread Safety Rules (Linux)

1. **Protect Shared State**: Use mutexes consistently
2. **Avoid Deadlocks**: Always lock in same order
3. **Minimize Lock Scope**: Don't hold locks long
4. **Use Read-Write Locks**: When appropriate
5. **Document Threading Model**: In headers

### Code Style Rules

```c
// Function naming: module_action_object
void can_process_message(can_message_t* msg);

// Constants: ALL_CAPS_WITH_UNDERSCORE
#define MAX_BUFFER_SIZE 256

// Types: snake_case_with_t
typedef struct {
    uint32_t field;
} my_struct_t;

// Indentation: 4 spaces, no tabs
if (condition) {
    do_something();
}
```

---

## 10. Common Pitfalls & Solutions

### Pitfall 1: Platform API Misuse

**Problem**: Using Linux APIs without guards
```c
// WRONG
#include <sys/socket.h>  // Breaks STM32 build
```

**Solution**: Always check platform
```c
#ifdef LINUX_PLATFORM
#include <sys/socket.h>
#endif
```

### Pitfall 2: Stack Overflow on STM32

**Problem**: Large local arrays
```c
void process() {
    char huge_buffer[8192];  // Stack overflow!
}
```

**Solution**: Use static or heap (carefully)
```c
void process() {
    static char buffer[512];  // Static storage
    // Or use MM2 pools
}
```

### Pitfall 3: Memory Leaks

**Problem**: Not freeing on error paths
```c
void* ptr = malloc(size);
if (some_operation() != SUCCESS) {
    return ERROR;  // Leak!
}
```

**Solution**: Use cleanup pattern
```c
void* ptr = malloc(size);
if (!ptr) return IMX_NO_MEMORY;

if (some_operation() != SUCCESS) {
    free(ptr);
    return ERROR;
}
```

### Pitfall 4: Race Conditions

**Problem**: Unprotected shared state
```c
global_counter++;  // Not atomic!
```

**Solution**: Use synchronization
```c
#ifdef LINUX_PLATFORM
pthread_mutex_lock(&mutex);
#endif
global_counter++;
#ifdef LINUX_PLATFORM
pthread_mutex_unlock(&mutex);
#endif
```

### Pitfall 5: Buffer Overflows

**Problem**: Unsafe string operations
```c
strcpy(dest, src);  // No bounds check!
```

**Solution**: Use safe variants
```c
strncpy(dest, src, sizeof(dest) - 1);
dest[sizeof(dest) - 1] = '\0';
```

---

## 11. Resources & Getting Help

### Documentation

- **CLAUDE.md**: AI assistant integration guide
- **Code Review Report**: `docs/comprehensive_code_review_report.md`
- **API Documentation**: Generated with Doxygen
- **Design Documents**: In `docs/` directory

### Key Files to Study

1. **Memory System**: `iMatrix/cs_ctrl/mm2_api.h`
2. **Platform Abstraction**: `iMatrix/IMX_Platform/*/`
3. **Main Loop**: `Fleet-Connect-1/linux_gateway.c`
4. **Network State Machine**: `iMatrix/networking/process_network.c`

### Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/your-feature`
2. **Make Changes**: Follow guidelines above
3. **Test Locally**: Both platforms if possible
4. **Run Tests**: `./run_all_tests.sh`
5. **Code Review**: Submit PR with detailed description
6. **CI/CD**: Automated tests must pass

### Getting Help

- **Team Chat**: #imatrix-dev on Slack
- **Wiki**: Internal wiki for detailed specs
- **Issue Tracker**: GitHub Issues for bugs/features
- **Code Owners**: See CODEOWNERS file

### Debugging Checklist

When something doesn't work:

- [ ] Check platform compilation flags
- [ ] Verify memory allocation succeeded
- [ ] Check error return codes
- [ ] Look for stack overflow (STM32)
- [ ] Verify thread safety (Linux)
- [ ] Check CLI commands for diagnostics
- [ ] Review recent commits for changes
- [ ] Test on both platforms

### Performance Profiling

```bash
# CPU profiling (Linux)
perf record -g ./Fleet-Connect-1
perf report

# Memory profiling
valgrind --tool=massif ./Fleet-Connect-1
ms_print massif.out.*

# System calls
strace -c ./Fleet-Connect-1
```

---

## Quick Reference Card

### Essential Commands

```bash
# Build for current platform
make clean && make -j$(nproc)

# Run with debug output
DEBUG_LEVEL=5 ./Fleet-Connect-1

# Check memory leaks
valgrind --leak-check=full ./Fleet-Connect-1

# Monitor system resources
top -p $(pgrep Fleet-Connect)

# View logs
tail -f /var/log/imatrix.log

# CLI access
telnet localhost 2323  # Or configured port
```

### Emergency Fixes

```bash
# System hang
killall -9 Fleet-Connect-1
rm /var/run/imatrix.pid
systemctl restart imatrix

# Memory corruption
rm -rf /usr/qk/var/mm2/*
./Fleet-Connect-1 --recovery

# Network issues
ip link set eth0 down && ip link set eth0 up
systemctl restart networking
```

---

## Your First Week Tasks

### Day 1-2: Environment Setup
- [ ] Set up development environment
- [ ] Build all three components successfully
- [ ] Run basic tests

### Day 3-4: Code Familiarization
- [ ] Read CLAUDE.md and this guide
- [ ] Study memory management (MM2) API
- [ ] Understand platform abstraction

### Day 5-7: First Contribution
- [ ] Fix a "good first issue" from tracker
- [ ] Add unit test for your fix
- [ ] Submit first PR

---

## Summary

The iMatrix system is complex but well-structured. Focus on understanding:

1. **Platform differences** (Linux vs STM32)
2. **Memory management** (MM2 system)
3. **Error handling** patterns
4. **Thread safety** requirements

Always remember: This code runs on severely constrained embedded systems. Every byte matters, every cycle counts.

Welcome to the team! 🚀

---

*Last Updated: 2025-11-05*
*Version: 1.0*
*Maintainer: iMatrix Development Team*