# CAN Ethernet Server - System Reference Guide

**Companion Document to:** [CAN_Server_Ethernet_Improvement_Plan.md](CAN_Server_Ethernet_Improvement_Plan.md)
**Project:** iMatrix CAN Bus Subsystem
**Date:** 2025-10-17
**Author:** System Architecture Documentation
**Purpose:** Provide complete system context for successful implementation

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture Overview](#system-architecture-overview)
3. [Configuration System](#configuration-system)
4. [Memory Management](#memory-management)
5. [Queue System](#queue-system)
6. [Threading and Synchronization](#threading-and-synchronization)
7. [CLI System Integration](#cli-system-integration)
8. [Network Interface System](#network-interface-system)
9. [Build System](#build-system)
10. [Code Patterns and Conventions](#code-patterns-and-conventions)
11. [Error Handling Standards](#error-handling-standards)
12. [Testing Infrastructure](#testing-infrastructure)
13. [Platform Differences](#platform-differences)
14. [Quick Reference](#quick-reference)

---

## Introduction

This document provides all necessary system-level details required to successfully implement the CAN Ethernet Server improvements outlined in **[CAN_Server_Ethernet_Improvement_Plan.md](CAN_Server_Ethernet_Improvement_Plan.md)**.

### Key Goals

- Explain iMatrix-specific APIs and conventions
- Document data structures and their relationships
- Clarify threading models and synchronization
- Provide working code examples
- Identify common pitfalls and solutions

### Who Should Read This

- Developers implementing the improvement plan
- Code reviewers
- Maintainers of the CAN subsystem

---

## System Architecture Overview

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Fleet      │  │    OBD2    │  │ CAN Signal │            │
│  │ Connect    │  │  Protocol  │  │ Processing │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAN Bus Subsystem                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ CAN Server │◄─┤ CAN Process│◄─┤ CAN Sample │            │
│  │ (Ethernet) │  │ (State Mgt)│  │  (Upload)  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         ▲               ▲                ▲                   │
│         │               │                │                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ CAN Utils  │  │   Ring     │  │  Signal    │            │
│  │  (Queues)  │  │  Buffer    │  │ Extraction │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Platform Layer                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Network   │  │   Memory   │  │    CLI     │            │
│  │  Manager   │  │  Manager   │  │  Interface │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Operating System (Linux)                        │
│           Sockets | Threads | POSIX APIs                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Data Flow Paths

#### 1. CAN Frame Reception (Ethernet)
```
TCP Client → can_server.c (parse ASCII) → canFrameHandler()
           → Ring Buffer Alloc → Queue Push → process_can_queues()
           → Signal Extraction → Memory Manager → Upload
```

#### 2. CAN Frame Reception (Physical CAN)
```
Hardware CAN → Quake Driver → canFrameHandler()
            → Ring Buffer Alloc → Queue Push → process_can_queues()
            → Signal Extraction → Memory Manager → Upload
```

#### 3. Configuration Loading
```
Storage (Flash/Disk) → imatrix_load_config()
                     → IOT_Device_Config_t (global)
                     → Subsystem init functions
```

---

## Configuration System

### Core Configuration Structure

**File:** [iMatrix/storage.h:589-748](../iMatrix/storage.h#L589-L748)

```c
typedef struct IOT_Device_Config
{
    // ... hundreds of fields ...

#ifdef CAN_PLATFORM
    canbus_config_t canbus;  // Line 728
#endif

    union {
        uint8_t spare[34];
        struct {
            netmgr_timing_config_t netmgr_timing;
            uint8_t spare_remaining[2];
        };
    };

    // ... more fields ...
} IOT_Device_Config_t;
```

### CAN Bus Configuration Structure

**File:** [iMatrix/storage.h:552-559](../iMatrix/storage.h#L552-L559)

**Current Definition:**
```c
typedef struct canbus_config_ {
    uint32_t can_controller_sn;
    char vin[VIN_LENGTH + 1];
    unsigned int can_controller_registered : 1;
    unsigned int vin_registered            : 1;
    unsigned int use_ethernet_server       : 1;
    unsigned int reserved_spare_1          : 27;
} canbus_config_t;
```

**Extended Definition (Per Improvement Plan):**
```c
typedef struct canbus_config_ {
    uint32_t can_controller_sn;
    char vin[VIN_LENGTH + 1];
    unsigned int can_controller_registered : 1;
    unsigned int vin_registered            : 1;
    unsigned int use_ethernet_server       : 1;
    unsigned int reserved_spare_1          : 27;

    // NEW: Ethernet server configuration
    char eth_server_ip[16];
    uint16_t eth_server_port;
    uint16_t eth_server_max_clients;
    uint32_t eth_server_rate_limit;
    uint16_t eth_server_idle_timeout;
    uint16_t eth_server_buffer_size;
    uint16_t eth_server_max_line_length;
    uint8_t eth_server_validate_frames;
    uint8_t eth_server_reserved[3];
} canbus_config_t;
```

### Global Configuration Instance

**Declaration (Everywhere):**
```c
extern IOT_Device_Config_t device_config;
```

**Definition:** [iMatrix/storage.c](../iMatrix/storage.c) (actual location)

### Accessing Configuration

**Example:**
```c
#include "storage.h"

extern IOT_Device_Config_t device_config;

void my_function(void)
{
    // Access CAN server IP
    const char *server_ip = device_config.canbus.eth_server_ip;

    // Access server port
    uint16_t port = device_config.canbus.eth_server_port;

    // Check if ethernet server is enabled
    if (device_config.canbus.use_ethernet_server) {
        // Start server
    }
}
```

### Configuration Persistence

**Loading Configuration:**
```c
// File: iMatrix/device/config.c or similar

imx_result_t imatrix_load_config(bool override_config)
{
    // Reads from flash/disk into device_config
    // Returns IMX_SUCCESS on success
}
```

**Saving Configuration:**
```c
imx_result_t imatrix_save_config(void)
{
    // Writes device_config to persistent storage
    // Returns IMX_SUCCESS on success
}
```

**Usage Example:**
```c
// Modify configuration
device_config.canbus.eth_server_port = 7777;

// Save to persistent storage
if (imatrix_save_config() != IMX_SUCCESS) {
    imx_cli_log_printf(true, "Failed to save configuration\r\n");
}
```

### Configuration Initialization Pattern

**Typical Pattern:**
```c
void init_canbus_eth_server_defaults(canbus_config_t *config)
{
    if (config == NULL) {
        return;
    }

    // Set defaults
    strncpy(config->eth_server_ip, "192.168.7.1",
            sizeof(config->eth_server_ip) - 1);
    config->eth_server_port = 5555;
    config->eth_server_rate_limit = 1000;
    // ...
}

// Called during system init
void system_init(void)
{
    // Load config from storage
    imatrix_load_config(false);

    // If first boot or invalid, set defaults
    if (device_config.canbus.eth_server_port == 0) {
        init_canbus_eth_server_defaults(&device_config.canbus);
        imatrix_save_config();
    }
}
```

---

## Memory Management

### iMatrix Memory API

**File:** [iMatrix/memory/imx_memory.h](../iMatrix/memory/imx_memory.h)

**DO NOT USE:** Standard library functions directly
```c
// ❌ NEVER DO THIS
void *ptr = malloc(100);
void *ptr = calloc(10, sizeof(int));
free(ptr);
```

**ALWAYS USE:** iMatrix wrappers
```c
// ✅ ALWAYS DO THIS
void *ptr = imx_malloc(100);
void *ptr = imx_calloc(10, sizeof(int));
imx_free(ptr);
```

### Memory API Functions

**File:** [iMatrix/memory/imx_memory.h](../iMatrix/memory/imx_memory.h)

```c
/**
 * @brief Allocate memory (zero-initialized)
 * @param count Number of elements
 * @param size Size of each element
 * @return Pointer to allocated memory or NULL on failure
 */
void *imx_calloc(size_t count, size_t size);

/**
 * @brief Allocate memory (uninitialized)
 * @param size Size in bytes
 * @return Pointer to allocated memory or NULL on failure
 */
void *imx_malloc(size_t size);

/**
 * @brief Free allocated memory
 * @param ptr Pointer to free
 */
void imx_free(void *ptr);

/**
 * @brief Reallocate memory
 * @param ptr Existing pointer
 * @param size New size
 * @return Pointer to reallocated memory or NULL on failure
 */
void *imx_realloc(void *ptr, size_t size);
```

### Memory Tracking

The iMatrix memory system automatically tracks:
- Allocation source file and line number
- Allocation size and timestamp
- Peak memory usage
- Memory leaks

**Get Memory Statistics:**
```c
void imx_memory_get_stats(imx_memory_stats_t *stats);

// Example usage
imx_memory_stats_t stats;
imx_memory_get_stats(&stats);

imx_cli_print("Memory Usage: %zu bytes\r\n", stats.current_usage);
imx_cli_print("Peak Usage: %zu bytes\r\n", stats.peak_usage);
imx_cli_print("Active Allocations: %u\r\n", stats.active_count);
```

### Common Pattern: Dynamic Buffer Allocation

**Example from can_server.c improvement plan:**

```c
void *tcp_server_thread(void *arg)
{
    extern IOT_Device_Config_t device_config;

    // Get buffer size from configuration
    size_t buffer_size = device_config.canbus.eth_server_buffer_size;

    // Allocate buffer using iMatrix API
    char *rx_buf = imx_malloc(buffer_size);
    if (rx_buf == NULL) {
        imx_cli_log_printf(true, "Failed to allocate receive buffer\r\n");
        return NULL;
    }

    // Use buffer...

    // Always free before returning
    imx_free(rx_buf);
    return NULL;
}
```

### Memory Allocation Error Handling

**Standard Pattern:**
```c
void *ptr = imx_malloc(size);
if (ptr == NULL) {
    imx_cli_log_printf(true, "Memory allocation failed: %zu bytes\r\n", size);
    // Clean up any partial allocations
    // Return error
    return IMX_ERROR_NO_MEMORY;
}

// Use ptr...

// Clean up
imx_free(ptr);
```

---

## Queue System

### Queue Types

**Platform-Specific Implementation:**

#### Linux Platform
**File:** [iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.c](../iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.c)

```c
// Linux uses POSIX message queues
typedef mqd_t imx_queue_t;
```

#### WICED Platform
**File:** [iMatrix/IMX_Platform/WICED_Platform/imx_wiced_platform.h](../iMatrix/IMX_Platform/WICED_Platform/imx_wiced_platform.h)

```c
// WICED uses custom queue implementation
typedef wiced_queue_t imx_queue_t;
```

### Queue API Functions

**Header:** [iMatrix/imatrix.h](../iMatrix/imatrix.h) or platform headers

```c
/**
 * @brief Create a queue
 * @param queue Pointer to queue structure
 * @param name Queue name (for POSIX)
 * @param message_size Size of each message
 * @param depth Maximum number of messages
 * @return IMX_SUCCESS or error code
 */
imx_result_t imx_queue_create(imx_queue_t *queue, const char *name,
                               size_t message_size, uint32_t depth);

/**
 * @brief Push message to queue
 * @param queue Pointer to queue
 * @param message Pointer to message data
 * @param timeout_ms Timeout in milliseconds (0 = no wait)
 * @return IMX_SUCCESS or error code
 */
imx_result_t imx_queue_push(imx_queue_t *queue, void *message, uint32_t timeout_ms);

/**
 * @brief Pop message from queue
 * @param queue Pointer to queue
 * @param message Pointer to receive message
 * @param timeout_ms Timeout in milliseconds (0 = no wait)
 * @return IMX_SUCCESS or error code
 */
imx_result_t imx_queue_pop(imx_queue_t *queue, void *message, uint32_t timeout_ms);

/**
 * @brief Delete queue
 * @param queue Pointer to queue
 * @return IMX_SUCCESS or error code
 */
imx_result_t imx_queue_delete(imx_queue_t *queue);
```

### CAN Queue Usage Example

**File:** [iMatrix/canbus/can_utils.c](../iMatrix/canbus/can_utils.c)

```c
// Global queues (declared static in can_utils.c)
static imx_queue_t can0_queue, can1_queue, can2_queue;

// Initialize queue
bool init_can_queues(void)
{
    imx_result_t result;

    // Create CAN0 queue
    result = imx_queue_create(&can0_queue, CAN_0_QUEUE_NAME,
                              sizeof(can_msg_t*), 100);
    if (result != IMX_SUCCESS) {
        imx_cli_log_printf(true, "Failed to create CAN0 queue\r\n");
        return false;
    }

    // Similar for can1_queue, can2_queue...

    return true;
}

// Push to queue
void canFrameHandler(uint32_t bus, uint32_t can_id, uint8_t *buf, uint8_t len)
{
    can_msg_t *msg = can_ring_buffer_alloc(&can0_ring);
    if (msg == NULL) {
        // No free messages
        return;
    }

    msg->can_id = can_id;
    msg->can_dlc = len;
    memcpy(msg->can_data, buf, len);

    // Push pointer to message onto queue
    imx_result_t result = imx_queue_push(&can0_queue, &msg, 0);
    if (result != IMX_SUCCESS) {
        imx_cli_log_printf(true, "Queue push failed\r\n");
        can_ring_buffer_free(&can0_ring, msg);
    }
}

// Pop from queue
void process_can_queues(void)
{
    can_msg_t *msg;
    imx_result_t result;

    result = imx_queue_pop(&can0_queue, &msg, 0);
    if (result == IMX_SUCCESS) {
        // Process message
        process_rx_can_msg(CAN_BUS_0, current_time, msg);

        // Return to ring buffer
        can_ring_buffer_free(&can0_ring, msg);
    }
}
```

### Queue Error Handling

**Result Codes:**
```c
typedef enum {
    IMX_SUCCESS = 0,
    IMX_ERROR_TIMEOUT,
    IMX_ERROR_QUEUE_FULL,
    IMX_ERROR_QUEUE_EMPTY,
    IMX_ERROR_INVALID_PARAMETER,
    // ... more error codes
} imx_result_t;
```

**Check Results:**
```c
imx_result_t result = imx_queue_push(&queue, &data, 100);
if (result == IMX_ERROR_TIMEOUT) {
    imx_cli_log_printf(true, "Queue push timeout\r\n");
} else if (result == IMX_ERROR_QUEUE_FULL) {
    imx_cli_log_printf(true, "Queue full\r\n");
} else if (result != IMX_SUCCESS) {
    imx_cli_log_printf(true, "Queue push failed: %d\r\n", result);
}
```

---

## Threading and Synchronization

### Thread Creation

**Standard Pattern:**
```c
#include <pthread.h>

static pthread_t my_thread_id;

void *my_thread_func(void *arg)
{
    // Thread main loop
    while (!shutdown_flag) {
        // Do work
    }

    return NULL;
}

bool start_my_thread(void)
{
    int result = pthread_create(&my_thread_id, NULL, my_thread_func, NULL);
    if (result != 0) {
        imx_cli_log_printf(true, "Failed to create thread: %d\r\n", result);
        return false;
    }

    return true;
}

void stop_my_thread(void)
{
    shutdown_flag = 1;
    pthread_join(my_thread_id, NULL);
}
```

### Mutex Usage

**CAN Server Example:**
```c
static pthread_mutex_t can_rx_mutex;

// Initialize (once at startup)
void init_mutexes(void)
{
    pthread_mutex_init(&can_rx_mutex, NULL);
}

// Use mutex to protect shared data
void canFrameHandler(uint32_t bus, uint32_t id, uint8_t *data, uint8_t len)
{
    // Lock
    if (pthread_mutex_lock(&can_rx_mutex) != 0) {
        imx_cli_log_printf(true, "Mutex lock failed\r\n");
        return;
    }

    // Critical section - access shared resources
    can_stats.rx_frames++;
    imx_queue_push(&can_queue, &msg, 0);

    // Unlock
    if (pthread_mutex_unlock(&can_rx_mutex) != 0) {
        imx_cli_log_printf(true, "Mutex unlock failed\r\n");
    }
}
```

### Common Synchronization Patterns

#### Pattern 1: Shutdown Flag
```c
static volatile int g_shutdown_flag = 0;

void *worker_thread(void *arg)
{
    while (!g_shutdown_flag) {
        // Do work with timeout
        select(..., timeout=1sec);
    }
    return NULL;
}

void stop_worker(void)
{
    g_shutdown_flag = 1;
    pthread_join(worker_tid, NULL);
}
```

#### Pattern 2: Signal-Based Shutdown (Better)
```c
static volatile int g_shutdown_flag = 0;
static pthread_t worker_tid;

void shutdown_handler(int sig)
{
    // Empty handler - just interrupt syscalls
}

void *worker_thread(void *arg)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = shutdown_handler;
    sigaction(SIGUSR1, &sa, NULL);

    while (!g_shutdown_flag) {
        int ret = select(...);
        if (ret < 0 && errno == EINTR) {
            // Interrupted by signal, check shutdown flag
            continue;
        }
    }
    return NULL;
}

void stop_worker(void)
{
    g_shutdown_flag = 1;
    pthread_kill(worker_tid, SIGUSR1);  // Interrupt select()
    pthread_join(worker_tid, NULL);
}
```

---

## CLI System Integration

### CLI Output Functions

**File:** [iMatrix/cli/interface.h](../iMatrix/cli/interface.h)

```c
/**
 * @brief Print to CLI without timestamp
 * @param format Printf-style format string
 * @param ... Variable arguments
 */
void imx_cli_print(char *format, ...);

/**
 * @brief Print to CLI with optional timestamp and logging
 * @param print_time true to prepend timestamp
 * @param format Printf-style format string
 * @param ... Variable arguments
 */
void imx_cli_log_printf(bool print_time, char *format, ...);

/**
 * @brief General printf (may go to log file or CLI)
 * @param format Printf-style format string
 * @param ... Variable arguments
 */
void imx_printf(char *format, ...);
```

### Usage Examples

```c
// Simple CLI output (no timestamp)
imx_cli_print("CAN Server started on %s:%d\r\n", ip, port);

// CLI output with timestamp
imx_cli_log_printf(true, "[CAN] Connection from %s\r\n", client_ip);

// Error message (always with timestamp)
imx_cli_log_printf(true, "[ERROR] Failed to bind socket: %s\r\n",
                   strerror(errno));

// Status display (no timestamp)
imx_cli_print("| RX Frames  | %lu\r\n", stats.rx_frames);
```

### Output Formatting

**Line Endings:**
- Always use `\r\n` (not just `\n`)
- Ensures proper display on all terminal types

**Formatting Conventions:**
```c
// Status tables
imx_cli_print("| Field Name      | Value\r\n");
imx_cli_print("|-----------------|----------\r\n");
imx_cli_print("| Server IP       | %s\r\n", ip);

// Section headers
imx_cli_print("\n=== Configuration ===\r\n");
// ...
imx_cli_print("=====================\r\n\n");

// Error messages
imx_cli_log_printf(true, "[CAN TCP Server Error: %s]\r\n", error_msg);

// Debug messages (conditional)
if (device_config.print_debugs) {
    imx_cli_log_printf(true, "[DEBUG] Frame ID=0x%X\r\n", id);
}
```

### CLI Command Registration

**Pattern (typically in cli/ directory files):**

```c
// File: iMatrix/cli/cli_canbus.c or similar

/**
 * @brief CLI command: Display CAN server configuration
 * @param arg Command argument (often unused)
 */
void cli_can_server_config(uint16_t arg)
{
    extern IOT_Device_Config_t device_config;

    imx_cli_print("\n=== CAN Ethernet Server Config ===\r\n");
    imx_cli_print("Server IP:    %s\r\n", device_config.canbus.eth_server_ip);
    imx_cli_print("Server Port:  %u\r\n", device_config.canbus.eth_server_port);
    // ...
    imx_cli_print("==================================\r\n\n");
}

/**
 * @brief CLI command: Set CAN server IP
 * @param arg Pointer to IP string
 */
void cli_can_server_set_ip(uint16_t arg)
{
    char *ip_str = (char *)arg;

    // Validate IP
    struct in_addr addr;
    if (inet_pton(AF_INET, ip_str, &addr) != 1) {
        imx_cli_print("Error: Invalid IP address\r\n");
        return;
    }

    // Set in config
    extern IOT_Device_Config_t device_config;
    strncpy(device_config.canbus.eth_server_ip, ip_str,
            sizeof(device_config.canbus.eth_server_ip) - 1);

    // Save
    imatrix_save_config();

    imx_cli_print("CAN server IP set to %s\r\n", ip_str);
}
```

**Command Registration:** Varies by platform/product, typically in cli initialization file.

---

## Network Interface System

### Getting Interface IP Address

**File:** [iMatrix/IMX_Platform/LINUX_Platform/networking/network_utils.h](../iMatrix/IMX_Platform/LINUX_Platform/networking/network_utils.h)

**New Function (to be added per improvement plan):**
```c
/**
 * @brief Get IP address of a network interface
 * @param interface Interface name (e.g., "eth0", "wlan0")
 * @param ip_buffer Buffer to store IP address string
 * @param buffer_size Size of ip_buffer (must be >= 16)
 * @return true if IP retrieved, false otherwise
 */
bool get_interface_ip_address(const char *interface, char *ip_buffer,
                               size_t buffer_size);
```

**Implementation Example:**
```c
// File: iMatrix/IMX_Platform/LINUX_Platform/networking/network_utils.c

#include <sys/ioctl.h>
#include <net/if.h>
#include <arpa/inet.h>

bool get_interface_ip_address(const char *interface, char *ip_buffer,
                               size_t buffer_size)
{
    if (!interface || !ip_buffer || buffer_size < 16) {
        return false;
    }

    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        return false;
    }

    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    ifr.ifr_addr.sa_family = AF_INET;
    strncpy(ifr.ifr_name, interface, IFNAMSIZ - 1);

    if (ioctl(fd, SIOCGIFADDR, &ifr) < 0) {
        close(fd);
        return false;
    }

    struct sockaddr_in *addr = (struct sockaddr_in *)&ifr.ifr_addr;
    const char *ip_str = inet_ntoa(addr->sin_addr);

    if (ip_str) {
        strncpy(ip_buffer, ip_str, buffer_size - 1);
        ip_buffer[buffer_size - 1] = '\0';
        close(fd);
        return true;
    }

    close(fd);
    return false;
}
```

**Usage:**
```c
char eth0_ip[16];
if (get_interface_ip_address("eth0", eth0_ip, sizeof(eth0_ip))) {
    imx_cli_print("eth0 IP: %s\r\n", eth0_ip);
} else {
    imx_cli_print("eth0 not configured\r\n");
}
```

### Network Interface Configuration

**File:** [iMatrix/storage.h:649-652](../iMatrix/storage.h#L649-L652)

```c
#ifdef LINUX_PLATFORM
    uint16_t no_interfaces;
    network_interfaces_t network_interfaces[IMX_INTERFACE_MAX];
    ethernet_control_t eth0;
    ppp_control_t ppp0;
#endif
```

---

## Build System

### CMake Integration

**File:** [iMatrix/CMakeLists.txt](../iMatrix/CMakeLists.txt)

**Adding New Source Files:**

```cmake
# Find the IMATRIX_SOURCES section (around line 27)
set(IMATRIX_SOURCES
    # ... existing files ...

    canbus/can_event.c
    canbus/can_file_send.c
    canbus/can_init.c
    canbus/can_imx_upload.c
    canbus/can_process.c
    canbus/can_sample.c
    canbus/can_server.c           # Existing
    canbus/can_utils.c
    canbus/can_ring_buffer.c
    canbus/simulate_can.c
    canbus/can_signal_extraction.c
    canbus/can_verify.c
    canbus/coap/registration.c

    # ADD NEW FILES HERE:
    canbus/can_frame_validate.c   # New validation module
    canbus/can_config.c            # New config management (optional)

    # ... rest of files ...
)
```

**Build Commands:**
```bash
# Configure
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug

# Build
cmake --build build

# Or use traditional make
cd build
make

# Clean build
cmake --build build --target clean
```

### Compilation Flags

**Platform Defines:**
```c
#ifdef LINUX_PLATFORM
    // Linux-specific code
#endif

#ifdef CAN_PLATFORM
    // CAN-enabled build
#endif

#ifdef WICED_PLATFORM
    // WICED-specific code
#endif
```

### Include Paths

**Standard Includes:**
```c
// iMatrix core
#include "imatrix.h"
#include "storage.h"

// Subsystem headers
#include "can_structs.h"
#include "can_process.h"

// Platform headers
#include "imx_platform.h"

// CLI headers
#include "../cli/interface.h"
#include "../cli/messages.h"

// Memory headers
#include "../memory/imx_memory.h"

// Network headers
#include "../IMX_Platform/LINUX_Platform/networking/network_utils.h"
```

---

## Code Patterns and Conventions

### File Header Template

**Use this template for all new .c and .h files:**

```c
/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 *
 * This software, associated documentation and materials ("Software"),
 * is owned by iMatrix Systems ("iMatrix") and is protected by and subject to
 * worldwide patent protection (United States and foreign),
 * United States copyright laws and international treaty provisions.
 * Therefore, you may use this Software only as provided in the license
 * agreement accompanying the software package from which you
 * obtained this Software ("EULA").
 *
 * Disclaimer: THIS SOFTWARE IS PROVIDED AS-IS, WITH NO WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, NONINFRINGEMENT, IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. iMatrix
 * reserves the right to make changes to the Software without notice. iMatrix
 * does not assume any liability arising out of the application or use of the
 * Software or any product or circuit described in the Software. iMatrix does
 * not authorize its products for use in any products where a malfunction or
 * failure of the iMatrix product may reasonably be expected to result in
 * significant property damage, injury or death ("High Risk Product"). By
 * including iMatrix's product in a High Risk Product, the manufacturer
 * of such system or application assumes all risk of such use and in doing
 * so agrees to indemnify iMatrix against all liability.
 */

/**
 * @file filename.c
 * @brief Brief description of file purpose
 * @author Your Name
 * @date 2025-10-17
 *
 * Detailed description of what this file does.
 * Can span multiple lines.
 *
 * @version 1.0
 */

#include <standard_headers.h>
#include "imatrix.h"
#include "local_headers.h"

/******************************************************
 *                      Macros
 ******************************************************/

/******************************************************
 *                    Constants
 ******************************************************/

/******************************************************
 *                   Enumerations
 ******************************************************/

/******************************************************
 *                 Type Definitions
 ******************************************************/

/******************************************************
 *                    Structures
 ******************************************************/

/******************************************************
 *               Function Declarations
 ******************************************************/

/******************************************************
 *               Variable Definitions
 ******************************************************/

/******************************************************
 *               Function Definitions
 ******************************************************/
```

### Function Documentation (Doxygen)

**Always use Doxygen format:**
```c
/**
 * @brief Brief one-line description of function
 *
 * Detailed description of what the function does.
 * Can include multiple paragraphs, algorithm notes, etc.
 *
 * @param[in] input_param Description of input parameter
 * @param[out] output_param Description of output parameter
 * @param[in,out] io_param Description of input/output parameter
 * @return Description of return value
 * @retval IMX_SUCCESS On success
 * @retval IMX_ERROR_INVALID_PARAMETER If parameters are invalid
 *
 * @note Important notes about usage
 * @warning Critical warnings
 * @see related_function()
 *
 * Example:
 * @code
 * int result = my_function(10, &output);
 * if (result == IMX_SUCCESS) {
 *     // Success
 * }
 * @endcode
 */
int my_function(int input_param, int *output_param);
```

### Naming Conventions

**Functions:**
```c
// Module prefix + descriptive name + verb
imx_can_init()
imx_can_process()
can_validate_frame()
check_rate_limit()
```

**Variables:**
```c
// Snake case for local variables
int frame_count;
char *server_ip;

// Descriptive names, not abbreviations
unsigned int can_id;        // Good
unsigned int id;            // Too generic
```

**Constants:**
```c
// ALL_CAPS with underscores
#define MAX_CAN_FRAME_LENGTH    8
#define SERVER_PORT             5555
```

**Structures:**
```c
// Type suffix _t
typedef struct can_stats {
    uint32_t rx_frames;
} can_stats_t;
```

### Error Handling Pattern

**Standard Pattern:**
```c
imx_result_t my_function(void)
{
    // Validate parameters
    if (param == NULL) {
        imx_cli_log_printf(true, "[ERROR] NULL parameter\r\n");
        return IMX_ERROR_INVALID_PARAMETER;
    }

    // Allocate resources
    void *ptr = imx_malloc(size);
    if (ptr == NULL) {
        imx_cli_log_printf(true, "[ERROR] Memory allocation failed\r\n");
        return IMX_ERROR_NO_MEMORY;
    }

    // Perform operation
    int result = operation();
    if (result < 0) {
        imx_cli_log_printf(true, "[ERROR] Operation failed: %s\r\n",
                          strerror(errno));
        imx_free(ptr);
        return IMX_ERROR_OPERATION_FAILED;
    }

    // Clean up
    imx_free(ptr);
    return IMX_SUCCESS;
}
```

---

## Error Handling Standards

### Result Codes

**File:** [iMatrix/imatrix.h](../iMatrix/imatrix.h) or similar

```c
typedef enum {
    IMX_SUCCESS = 0,
    IMX_ERROR_TIMEOUT,
    IMX_ERROR_INVALID_PARAMETER,
    IMX_ERROR_NO_MEMORY,
    IMX_ERROR_OPERATION_FAILED,
    IMX_ERROR_NOT_FOUND,
    IMX_ERROR_ALREADY_EXISTS,
    IMX_ERROR_QUEUE_FULL,
    IMX_ERROR_QUEUE_EMPTY,
    // ... more codes
} imx_result_t;
```

### System Error Handling

**Using errno:**
```c
#include <errno.h>
#include <string.h>

// After system call failure
if (socket_fd < 0) {
    imx_cli_log_printf(true, "socket() failed: %s\r\n", strerror(errno));
    return IMX_ERROR_OPERATION_FAILED;
}

// DO NOT shadow errno!
// ❌ WRONG:
int errno;  // Local variable shadows global!

// ✅ CORRECT:
// Just use the global errno directly
```

### Logging Levels

**Convention:**
```c
// ERROR - Always logged, always with timestamp
imx_cli_log_printf(true, "[ERROR] Critical error: %s\r\n", msg);

// WARNING - Always logged, always with timestamp
imx_cli_log_printf(true, "[WARNING] Potential issue: %s\r\n", msg);

// INFO - Logged, with timestamp
imx_cli_log_printf(true, "[INFO] Status update: %s\r\n", msg);

// DEBUG - Conditional, with timestamp
if (device_config.print_debugs) {
    imx_cli_log_printf(true, "[DEBUG] Detailed info: %s\r\n", msg);
}
```

---

## Testing Infrastructure

### Unit Testing Pattern

**File:** `test_scripts/test_module.c`

```c
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../iMatrix/module.h"

// Test function signature
void test_function_name(void)
{
    // Arrange
    setup_test_data();

    // Act
    int result = function_under_test(input);

    // Assert
    assert(result == expected_value);
    assert(output_param == expected_output);
}

// Main test runner
int main(void)
{
    printf("Running module tests...\n");

    test_function_1();
    test_function_2();
    test_function_3();

    printf("All tests passed!\n");
    return 0;
}
```

### Integration Testing

**Shell Script Pattern:**
```bash
#!/bin/bash
# File: test_scripts/test_can_server.sh

echo "=== CAN Server Integration Test ==="

# Test 1: Server starts
echo "Test 1: Starting server..."
./build/imatrix &
IMX_PID=$!
sleep 2

if ps -p $IMX_PID > /dev/null; then
    echo "✓ Server started"
else
    echo "✗ Server failed to start"
    exit 1
fi

# Test 2: Can connect
echo "Test 2: Connecting to server..."
timeout 2 nc -zv 192.168.7.1 5555
if [ $? -eq 0 ]; then
    echo "✓ Connection successful"
else
    echo "✗ Connection failed"
    kill $IMX_PID
    exit 1
fi

# Test 3: Send CAN frame
echo "Test 3: Sending CAN frame..."
echo "6D3#006E020700000000" | nc 192.168.7.1 5555 &
sleep 1
echo "✓ Frame sent"

# Cleanup
kill $IMX_PID
echo "=== Tests Complete ==="
```

---

## Platform Differences

### Linux vs WICED

**Queue Implementation:**
```c
#ifdef LINUX_PLATFORM
    // Uses POSIX message queues
    typedef mqd_t imx_queue_t;
#endif

#ifdef WICED_PLATFORM
    // Uses WICED RTOS queues
    typedef wiced_queue_t imx_queue_t;
#endif
```

**Networking:**
```c
#ifdef LINUX_PLATFORM
    #include <sys/socket.h>
    #include <netinet/in.h>
    // Standard Berkeley sockets
#endif

#ifdef WICED_PLATFORM
    #include "wiced_network.h"
    // WICED network API
#endif
```

**Threading:**
```c
#ifdef LINUX_PLATFORM
    #include <pthread.h>
    // POSIX threads
#endif

#ifdef WICED_PLATFORM
    #include "wiced_rtos.h"
    // WICED RTOS threads
#endif
```

### Conditional Compilation

**Pattern:**
```c
void platform_specific_function(void)
{
#ifdef LINUX_PLATFORM
    // Linux implementation
    pthread_create(...);
#elif defined(WICED_PLATFORM)
    // WICED implementation
    wiced_rtos_create_thread(...);
#else
    #error "Unsupported platform"
#endif
}
```

---

## Quick Reference

### Cheat Sheet

#### Configuration Access
```c
extern IOT_Device_Config_t device_config;
const char *ip = device_config.canbus.eth_server_ip;
uint16_t port = device_config.canbus.eth_server_port;
```

#### Memory Allocation
```c
void *ptr = imx_malloc(size);          // Allocate
void *ptr = imx_calloc(count, size);   // Allocate + zero
imx_free(ptr);                         // Free
```

#### CLI Output
```c
imx_cli_print("Message\r\n");                    // No timestamp
imx_cli_log_printf(true, "Message\r\n");         // With timestamp
imx_cli_log_printf(true, "[ERROR] %s\r\n", msg); // Error
```

#### Queue Operations
```c
imx_queue_create(&queue, name, msg_size, depth);
imx_queue_push(&queue, &msg, timeout_ms);
imx_queue_pop(&queue, &msg, timeout_ms);
```

#### Threading
```c
pthread_t tid;
pthread_create(&tid, NULL, thread_func, arg);
pthread_join(tid, NULL);
```

#### Error Handling
```c
if (result < 0) {
    imx_cli_log_printf(true, "Error: %s\r\n", strerror(errno));
    return IMX_ERROR_OPERATION_FAILED;
}
```

### Common Pitfalls

| Pitfall | Wrong | Right |
|---------|-------|-------|
| Line endings | `\n` | `\r\n` |
| Memory | `malloc()` | `imx_malloc()` |
| errno | `int errno;` | Use global `errno` |
| NULL checks | Assume not NULL | Always check |
| Mutex unlock | Forget unlock | Always unlock |
| Config save | Don't save | Call `imatrix_save_config()` |

### Key Files Quick Reference

| Purpose | File |
|---------|------|
| Configuration | [iMatrix/storage.h](../iMatrix/storage.h) |
| Memory API | [iMatrix/memory/imx_memory.h](../iMatrix/memory/imx_memory.h) |
| CLI Output | [iMatrix/cli/interface.h](../iMatrix/cli/interface.h) |
| CAN Structures | [iMatrix/canbus/can_structs.h](../iMatrix/canbus/can_structs.h) |
| CAN Server | [iMatrix/canbus/can_server.c](../iMatrix/canbus/can_server.c) |
| Network Utils | [iMatrix/IMX_Platform/LINUX_Platform/networking/network_utils.h](../iMatrix/IMX_Platform/LINUX_Platform/networking/network_utils.h) |
| Build Config | [iMatrix/CMakeLists.txt](../iMatrix/CMakeLists.txt) |

---

## Appendix: Complete Example

### Example: Adding a New CLI Command

**Step 1: Define the function**

File: `iMatrix/canbus/cli_can_server.c` (new file)

```c
#include <stdint.h>
#include <string.h>
#include "storage.h"
#include "../cli/interface.h"

extern IOT_Device_Config_t device_config;

/**
 * @brief Display CAN ethernet server configuration
 * @param arg Unused
 */
void cli_can_server_config(uint16_t arg)
{
    (void)arg;  // Unused

    imx_cli_print("\n=== CAN Ethernet Server Configuration ===\r\n");
    imx_cli_print("Server IP:       %s\r\n",
                  device_config.canbus.eth_server_ip);
    imx_cli_print("Server Port:     %u\r\n",
                  device_config.canbus.eth_server_port);
    imx_cli_print("Max Clients:     %u\r\n",
                  device_config.canbus.eth_server_max_clients);
    imx_cli_print("Rate Limit:      %u frames/sec\r\n",
                  device_config.canbus.eth_server_rate_limit);
    imx_cli_print("Idle Timeout:    %u seconds\r\n",
                  device_config.canbus.eth_server_idle_timeout);
    imx_cli_print("Buffer Size:     %u bytes\r\n",
                  device_config.canbus.eth_server_buffer_size);
    imx_cli_print("Validate Frames: %s\r\n",
                  device_config.canbus.eth_server_validate_frames ? "Yes" : "No");
    imx_cli_print("==========================================\r\n\n");
}
```

**Step 2: Add to CMakeLists.txt**

```cmake
set(IMATRIX_SOURCES
    # ...
    cli/cli_canbus.c
    canbus/cli_can_server.c    # ADD THIS LINE
    # ...
)
```

**Step 3: Register command** (product-specific, location varies)

```c
// In appropriate CLI initialization file
register_cli_command("canserver", "Show CAN server config",
                     cli_can_server_config);
```

**Step 4: Build and test**

```bash
cmake --build build
./build/imatrix
> canserver
```

---

## Support and Resources

### Where to Find Help

1. **Existing Code:** Look for similar patterns in the codebase
2. **Comments:** Many functions have detailed Doxygen comments
3. **Git History:** Check commit history for context
4. **CLAUDE.md:** See [CLAUDE.md](../CLAUDE.md) for high-level architecture

### Common Questions

**Q: How do I debug memory leaks?**
A: Use the built-in memory tracking:
```c
imx_memory_print_allocations();
```

**Q: How do I add compile-time debugging?**
A: Use conditional compilation:
```c
#ifdef DEBUG_CAN_SERVER
    imx_cli_log_printf(true, "[DEBUG] Frame: 0x%X\r\n", id);
#endif
```

**Q: How do I test without hardware?**
A: Use simulation mode or mock interfaces. See `can_file_send.c` for examples.

---

**End of System Reference Guide**

This document should be read in conjunction with:
- [CAN_Server_Ethernet_Improvement_Plan.md](CAN_Server_Ethernet_Improvement_Plan.md)
- [CLAUDE.md](../CLAUDE.md)
- Source code comments and headers
