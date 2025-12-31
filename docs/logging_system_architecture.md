# FC-1 Logging System Architecture

**Document Version**: 1.0
**Date**: 2025-12-30
**Author**: Claude Code
**Status**: Approved

## Overview

The FC-1 logging system is a multi-layered architecture designed to capture diagnostic output from all subsystems while maintaining real-time performance for critical operations like CAN bus processing. The system supports multiple output destinations and provides persistent storage with automatic rotation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION THREADS                                │
│                                                                             │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│   │   CAN    │   │ Network  │   │ Cellular │   │  Other   │               │
│   │ Process  │   │ Manager  │   │ Manager  │   │ Modules  │               │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│        │              │              │              │                      │
│        └──────────────┴──────────────┴──────────────┘                      │
│                              │                                              │
│                              ▼                                              │
│              ┌───────────────────────────────┐                             │
│              │    imx_cli_log_printf()       │                             │
│              │    (Central Entry Point)      │                             │
│              └───────────────┬───────────────┘                             │
│                              │                                              │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  FILESYSTEM     │  │  ASYNC LOG      │  │  SYNCHRONOUS    │
│  LOGGER         │  │  QUEUE          │  │  OUTPUT         │
│                 │  │                 │  │                 │
│ /var/log/fc-1.log │  │ Ring Buffer    │  │ - Console      │
│                 │  │ (10K messages)  │  │ - Telnet       │
│ - Always active │  │                 │  │ - BLE UART     │
│ - Thread-safe   │  │ CLI Thread      │  │ - TTY Device   │
│ - Auto-rotation │  │ dequeues &      │  │                 │
│                 │  │ prints          │  │                 │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Persistent     │  │  Console        │  │  Network/       │
│  Storage        │  │  (stdout)       │  │  Serial Output  │
│  (/var/log/)    │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Logging Layers

### Layer 1: Filesystem Logger (Primary - Always Active)

The filesystem logger captures **all** log output to persistent storage, regardless of other output modes.

**Location**: `iMatrix/cli/filesystem_logger.c`, `iMatrix/cli/filesystem_logger.h`

**Key Characteristics**:
- First check in `imx_cli_log_printf()` - executes before any other logging path
- Thread-safe with mutex protection
- Non-blocking writes
- Automatic rotation (daily, on restart, or at 10MB)
- Background rotation thread to avoid blocking callers
- Configurable retention policy (5 days / 100MB)

**Code Flow**:
```c
void imx_cli_log_printf(bool print_time, char *format, ...)
{
    // LAYER 1: Filesystem logging - ALWAYS runs first
    if (fs_logger_is_active()) {
        // Build timestamped message
        // Write to /var/log/fc-1.log
        fs_logger_write(fs_message);

        // In quiet mode, return here (no console output)
        if (!fs_logger_interactive_mode) {
            return;
        }
    }
    // Continue to Layer 2/3 for console output...
}
```

**Operating Modes**:

| Mode | Console Output | Filesystem Output | Use Case |
|------|---------------|-------------------|----------|
| Quiet (default) | No | Yes | Production |
| Interactive (-i) | Yes | Yes | Development/Debug |

### Layer 2: Async Log Queue (Performance Critical)

For console output, an asynchronous ring buffer decouples log generation from I/O operations.

**Location**: `iMatrix/cli/async_log_queue.c`, `iMatrix/cli/async_log_queue.h`

**Purpose**: Prevent `printf()` blocking in time-critical threads (CAN processing, network manager)

**Architecture**:
```
Producer Threads          Queue              Consumer
─────────────────────────────────────────────────────
CAN Thread      ─┐
Network Thread  ─┼──► Ring Buffer ──► CLI Thread ──► printf()
Cellular Thread ─┘    (10K msgs)
```

**Key Characteristics**:
- Lock-free enqueue for minimal latency
- 10,000 message capacity (~2.5MB)
- CLI thread drains queue and calls `printf()`
- Falls back to synchronous path if queue full

**Code Flow**:
```c
// In imx_cli_log_printf(), after filesystem logging:
async_log_queue_t *log_queue = get_global_log_queue();
if (log_queue != NULL && active_device == CONSOLE_OUTPUT) {
    // Fast path: enqueue without blocking
    int result = async_log_enqueue_string(log_queue, severity, print_time, message);
    if (result == 0) {
        return;  // Success - message will be printed by CLI thread
    }
    // Fall through to synchronous if queue full
}
```

### Layer 3: Synchronous Output (Fallback/Legacy)

Direct output to various devices when async queue is unavailable or for special cases.

**Output Devices** (defined in `interface.h`):
```c
typedef enum {
    CONSOLE_OUTPUT,      // stdout via printf()
    TELNET_OUTPUT,       // Network telnet session
    BLE_UART_OUTPUT,     // Bluetooth LE serial
    TTY_DEVICE_OUTPUT    // Physical TTY device
} output_device_t;
```

**Additional Output Paths**:
- **Debug File Logging**: `imx_debug_is_file_logging_active()` - redirects to debug file
- **CLI File Viewer**: `cli_file_viewer_is_active()` - captures to temp file for review

## Integration Points

### Entry Point: imx_cli_log_printf()

**File**: `iMatrix/cli/interface.c:182`

**Signature**:
```c
void imx_cli_log_printf(bool print_time, char *format, ...);
```

**Parameters**:
- `print_time`: If true, prepends timestamp `[HH:MM:SS.mmm]`
- `format`: printf-style format string
- `...`: Variable arguments

**Processing Order**:
1. **Filesystem Logger** - Always write to `/var/log/fc-1.log`
2. **Interactive Mode Check** - Return early if quiet mode
3. **Async Queue** - Enqueue for non-blocking console output
4. **Debug File** - Redirect if debug file logging active
5. **CLI File Viewer** - Capture if file viewer active
6. **Synchronous Output** - Direct printf() to active device

### Initialization

**File**: `iMatrix/imatrix_interface.c`

```c
// In imatrix_start():
if (fs_logger_init() != IMX_SUCCESS) {
    printf("WARNING: Failed to initialize filesystem logger\r\n");
} else {
    printf("Filesystem logger initialized (%s/%s)\r\n",
           FS_LOG_DIRECTORY, FS_LOG_FILENAME);
}
```

**Command Line Parsing**:
```c
// -i flag enables interactive mode
if (strcmp(argv[i], "-i") == 0) {
    fs_logger_interactive_mode = true;
    // Continue normal startup
}
```

### Shutdown

```c
// In imatrix_shutdown():
fs_logger_shutdown();  // Flush buffers, stop rotation thread, close file
```

## Thread Safety

### Mutex Protection

| Component | Mutex | Protected Operations |
|-----------|-------|---------------------|
| Filesystem Logger | `fs_log_mutex` | File writes, rotation |
| CLI Print | `imx_cli_print_mutex` | Console printf() |
| Async Queue | Internal locks | Enqueue/dequeue |

### Non-Blocking Design

Critical threads never block on I/O:

```
CAN Thread
    │
    ├──► fs_logger_write()     ← Mutex-protected, fast write to buffer
    │
    └──► async_log_enqueue()   ← Lock-free ring buffer insert

    Total time: < 100μs typical
```

## Log Message Format

### Timestamp Format
```
[HH:MM:SS.mmm] Message text
```

Example:
```
[00:01:39.386] [DEBUG] AT response state initialized
[00:01:39.490] [Cellular Connection - state changed to GET_RESPONSE]
```

### Session Header
Each FC-1 start writes:
```
=== FC-1 Log Started: 2025-12-30 23:44:06 ===
```

## File Locations

### Source Files

| File | Purpose |
|------|---------|
| `iMatrix/cli/interface.c` | Central logging entry point |
| `iMatrix/cli/interface.h` | Output device enumeration |
| `iMatrix/cli/filesystem_logger.c` | Persistent filesystem logging |
| `iMatrix/cli/filesystem_logger.h` | Filesystem logger API |
| `iMatrix/cli/async_log_queue.c` | Async console logging |
| `iMatrix/cli/async_log_queue.h` | Async queue API |
| `iMatrix/imatrix_interface.c` | Initialization and CLI parsing |

### Output Files

| Location | Purpose |
|----------|---------|
| `/var/log/fc-1.log` | Current active log |
| `/var/log/fc-1.YYYY-MM-DD.log` | Rotated daily logs |

## Accessing Logs on Device

### SSH Connection
```bash
ssh -p 22222 root@<device-ip>
# Password: PasswordQConnect
```

### View Live Logs
```bash
# Real-time monitoring
tail -f /var/log/fc-1.log

# Last 100 lines
tail -100 /var/log/fc-1.log

# Search for patterns
grep "ERROR" /var/log/fc-1.log
grep "CAN" /var/log/fc-1.log
grep "NETMGR" /var/log/fc-1.log
```

### Download Logs
```bash
# Download current log
scp -P 22222 root@<device-ip>:/var/log/fc-1.log ./

# Download all logs
scp -P 22222 root@<device-ip>:/var/log/fc-1*.log ./
```

### List All Logs
```bash
ls -la /var/log/fc-1*.log
```

## Adding Logging to New Code

### Basic Usage
```c
#include "cli/interface.h"

// With timestamp
imx_cli_log_printf(true, "[MyModule] Status: %s\n", status_string);

// Without timestamp
imx_cli_log_printf(false, "    Detail: %d\n", value);
```

### Best Practices

1. **Always include module identifier**:
   ```c
   imx_cli_log_printf(true, "[MYMODULE] Message here\n");
   ```

2. **Use consistent severity prefixes**:
   ```c
   imx_cli_log_printf(true, "[MYMODULE-INFO] Normal operation\n");
   imx_cli_log_printf(true, "[MYMODULE-WARN] Warning condition\n");
   imx_cli_log_printf(true, "[MYMODULE-ERROR] Error occurred: %d\n", err);
   ```

3. **Include context in state transitions**:
   ```c
   imx_cli_log_printf(true, "[MYMODULE] State: %s -> %s | Reason: %s\n",
                      old_state_name, new_state_name, reason);
   ```

4. **Avoid excessive logging in hot paths**:
   ```c
   // BAD: Logs every CAN message (thousands/sec)
   imx_cli_log_printf(true, "CAN msg: 0x%X\n", msg_id);

   // GOOD: Log periodically or on state change
   if (msg_count % 1000 == 0) {
       imx_cli_log_printf(true, "[CAN] Processed %lu messages\n", msg_count);
   }
   ```

## Configuration Constants

**File**: `iMatrix/cli/filesystem_logger.h`

```c
#define FS_LOG_DIRECTORY        "/var/log"      // Log directory
#define FS_LOG_FILENAME         "fc-1.log"      // Base filename
#define FS_LOG_MAX_FILE_SIZE    (10*1024*1024)  // 10 MB rotation trigger
#define FS_LOG_MAX_TOTAL_SIZE   (100*1024*1024) // 100 MB total limit
#define FS_LOG_MAX_RETENTION    5               // Days to keep logs
```

**File**: `iMatrix/cli/async_log_queue.h`

```c
#define LOG_MSG_MAX_LENGTH      256             // Max message length
#define LOG_QUEUE_CAPACITY      10000           // Queue depth
```

## Performance Characteristics

| Operation | Typical Time | Blocking |
|-----------|-------------|----------|
| fs_logger_write() | < 50μs | No (mutex) |
| async_log_enqueue() | < 10μs | No (lock-free) |
| Synchronous printf() | 1-10ms | Yes |
| Log rotation | 50-200ms | Background thread |

## Troubleshooting

### No Logs Being Written
1. Check FC-1 is running: `sv status /usr/qk/etc/sv/FC-1`
2. Check disk space: `df -h /var/log`
3. Verify permissions: `ls -la /var/log/fc-1.log`

### Console Output Missing
1. Verify `-i` flag is passed for interactive mode
2. Check `device_config.cli_enabled` is true
3. Verify `active_device == CONSOLE_OUTPUT`

### Performance Issues
1. Monitor async queue depth for overflow
2. Check for excessive logging in hot paths
3. Verify background rotation thread is running

---

*Last Updated: 2025-12-30*
