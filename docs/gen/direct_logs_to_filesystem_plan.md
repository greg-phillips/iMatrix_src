# Direct All Logs to Filesystem - Implementation Plan

**Date Created:** 2025-12-30
**Last Updated:** 2025-12-30
**Document Version:** 1.0
**Status:** Awaiting Approval
**Author:** Claude Code
**Branch:** feature/filesystem-logging

---

## 1. Executive Summary

This document outlines the implementation plan for directing all FC-1 logs from the buffered console system to the filesystem with automatic rotation and retention management.

### Current State
- Logs are currently output to console via `imx_cli_log_printf()` in `interface.c`
- Existing `debug save <filename>` command provides basic file redirection
- No log rotation, size limits, or retention policy exists

### Target State
- All logs automatically written to `/var/log/fc-1.log`
- Automatic log rotation (daily OR on application restart)
- Maximum file size: 10MB
- Retention: Last 5 days OR maximum 100MB total

---

## 2. Current Branch Information

| Repository | Current Branch | New Branch |
|------------|---------------|------------|
| iMatrix | `Aptera_1_Clean` | `feature/filesystem-logging` |
| Fleet-Connect-1 | `Aptera_1_Clean` | `feature/filesystem-logging` |

---

## 3. Technical Analysis

### 3.1 Current Logging Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Code                          │
│    (PRINTF macros, imx_cli_log_printf() calls)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               imx_cli_log_printf() [interface.c]            │
│  - Adds timestamps                                           │
│  - Routes to async queue (if console)                        │
│  - Routes to debug file (if debug save active)              │
│  - Routes to file viewer temp (if file viewer active)       │
│  - Routes to console/telnet/BLE UART                        │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
        ┌──────────────┐        ┌──────────────┐
        │ Console/TTY  │        │ Debug File   │
        │ (active_dev) │        │ (cli_debug)  │
        └──────────────┘        └──────────────┘
```

### 3.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Code                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               imx_cli_log_printf() [interface.c]            │
│  - Adds timestamps                                           │
│  - [NEW] Always writes to filesystem logger                  │
│  - Routes to console/telnet/BLE UART (unchanged)            │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
    │ Console/TTY  │ │ Debug File   │ │ Filesystem Logger│
    │ (unchanged)  │ │ (unchanged)  │ │ (NEW)            │
    └──────────────┘ └──────────────┘ └──────────────────┘
                                              │
                                              ▼
                                      ┌──────────────────┐
                                      │ /var/log/fc-1.log│
                                      │ + rotation       │
                                      │ + size mgmt      │
                                      │ + retention      │
                                      └──────────────────┘
```

### 3.3 Key Files to Modify

| File | Modifications |
|------|--------------|
| `iMatrix/cli/interface.c` | Add call to filesystem logger in `imx_cli_log_printf()` |
| `iMatrix/cli/interface.h` | Add function declarations for filesystem logger |
| **NEW**: `iMatrix/cli/filesystem_logger.c` | Main implementation |
| **NEW**: `iMatrix/cli/filesystem_logger.h` | Header file |
| `iMatrix/CMakeLists.txt` | Add new source file |
| `Fleet-Connect-1/init/linux_gateway.c` | Initialize/shutdown filesystem logger |

---

## 4. Implementation Design

### 4.1 New Module: filesystem_logger

#### 4.1.1 Data Structures

```c
/**
 * @brief Configuration for filesystem logging
 */
typedef struct {
    char log_directory[128];       /**< Log directory path */
    char log_filename[64];         /**< Base log filename */
    size_t max_file_size;          /**< Maximum size per log file (bytes) */
    size_t max_total_size;         /**< Maximum total log storage (bytes) */
    uint32_t max_retention_days;   /**< Maximum days to keep logs */
    bool enabled;                  /**< Logging enabled flag */
} fs_logger_config_t;

/**
 * @brief Runtime state for filesystem logger
 */
typedef struct {
    FILE *current_log_file;        /**< Current log file handle */
    char current_log_path[256];    /**< Current log file path */
    size_t current_file_size;      /**< Current file size */
    uint32_t current_day;          /**< Day of year for rotation check */
    imx_mutex_t log_mutex;         /**< Thread safety mutex */
    bool initialized;              /**< Initialization flag */

    /* Async rotation support */
    FILE *pending_rotate_file;     /**< File handle awaiting rotation */
    char pending_rotate_path[256]; /**< Path of file to rotate */
    bool rotation_pending;         /**< Flag: rotation task should run */
    pthread_t rotation_thread;     /**< Background rotation thread */
    pthread_cond_t rotation_cond;  /**< Condition variable to wake thread */
    pthread_mutex_t rotation_mutex;/**< Mutex for condition variable */
    bool shutdown_requested;       /**< Flag to terminate rotation thread */
} fs_logger_state_t;
```

#### 4.1.2 Default Configuration Values

```c
#define FS_LOG_DIRECTORY        "/var/log"
#define FS_LOG_FILENAME         "fc-1.log"
#define FS_LOG_MAX_FILE_SIZE    (10 * 1024 * 1024)   /* 10 MB */
#define FS_LOG_MAX_TOTAL_SIZE   (100 * 1024 * 1024)  /* 100 MB */
#define FS_LOG_MAX_RETENTION    5                     /* 5 days */
```

#### 4.1.3 API Functions

```c
/**
 * @brief Initialize filesystem logging
 * @note Creates rotation thread and opens initial log file
 * @return IMX_SUCCESS on success, error code otherwise
 */
imx_result_t fs_logger_init(void);

/**
 * @brief Shutdown filesystem logging
 * @note Signals rotation thread to exit, waits for completion
 */
void fs_logger_shutdown(void);

/**
 * @brief Write a log message to the filesystem
 * @param message Pre-formatted message to write
 * @note Non-blocking: triggers async rotation if needed
 * @return IMX_SUCCESS on success, error code otherwise
 */
imx_result_t fs_logger_write(const char *message);

/**
 * @brief Force log rotation (async)
 * @note Signals background thread to perform rotation
 * @return IMX_SUCCESS on success, error code otherwise
 */
imx_result_t fs_logger_rotate(void);

/**
 * @brief Check and enforce retention policy
 * @note Called by rotation thread after each rotation
 */
void fs_logger_enforce_retention(void);

/**
 * @brief Get current log file path
 * @return Current log file path or NULL
 */
const char* fs_logger_get_current_path(void);

/**
 * @brief Check if filesystem logging is active
 * @return true if active, false otherwise
 */
bool fs_logger_is_active(void);
```

#### 4.1.4 Internal Functions

```c
/**
 * @brief Background rotation thread entry point
 * @param arg Unused
 * @return NULL
 * @note Waits on condition variable, performs rotation when signaled
 */
static void* fs_logger_rotation_thread(void *arg);

/**
 * @brief Check if rotation is needed
 * @return true if rotation needed (day changed or size exceeded)
 */
static bool fs_logger_check_rotation_needed(void);

/**
 * @brief Generate rotated log filename with date
 * @param buffer Output buffer for filename
 * @param size Buffer size
 * @param base_path Base log file path
 */
static void fs_logger_generate_rotated_name(char *buffer, size_t size, const char *base_path);
```

### 4.2 Log Rotation Strategy

#### 4.2.1 Rotation Triggers
1. **Application Restart**: Rotate on `fs_logger_init()` if existing log file found
2. **Daily**: Check day-of-year on each write, rotate if changed
3. **Size Limit**: Rotate if current file exceeds 10MB

#### 4.2.2 Rotation Naming Convention
```
fc-1.log              <- Current active log
fc-1.2025-12-30.log   <- Rotated log from Dec 30, 2025
fc-1.2025-12-30.1.log <- Second rotation same day (if needed)
```

#### 4.2.3 Async Rotation Design

**Problem**: File operations (close, rename, directory scan) can block for 10-100ms on embedded flash, which would delay CAN processing threads.

**Solution**: Two-phase rotation with background thread.

```
┌──────────────────────────────────────────────────────────────────┐
│                     fs_logger_write() - FAST PATH                │
│  1. Check if rotation needed (day change or size limit)         │
│  2. If YES:                                                      │
│     - Save current file handle to pending_rotate_file           │
│     - Open NEW log file immediately (~1-5ms)                    │
│     - Set rotation_pending = true                               │
│     - Signal rotation_cond (wake background thread)             │
│  3. Write message to current_log_file                           │
│  4. Return immediately                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ pthread_cond_signal()
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│           fs_logger_rotation_thread() - BACKGROUND               │
│  Loop:                                                           │
│    1. Wait on rotation_cond (blocks until signaled)             │
│    2. When signaled:                                            │
│       - fclose(pending_rotate_file)                             │
│       - Generate dated filename                                 │
│       - rename() old file to dated name                         │
│       - Scan directory for old logs                             │
│       - Delete logs older than 5 days                           │
│       - Delete oldest logs if total > 100MB                     │
│       - Set rotation_pending = false                            │
│    3. Check shutdown_requested, exit if true                    │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.2.4 Write Path Timing

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| Check rotation needed | <1µs | Compare integers |
| fopen() new file | 1-5ms | One-time on rotation |
| fputs() to file | 10-100µs | Buffered write |
| Signal condition | <1µs | Non-blocking |
| **Total write path** | **~100µs typical** | Fast, non-blocking |

#### 4.2.5 Background Thread Operations

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| fclose() old file | 5-50ms | Flush buffers to flash |
| rename() | 1-10ms | Filesystem metadata |
| Directory scan | 10-50ms | List /var/log contents |
| unlink() per file | 5-20ms | Delete old logs |
| **Total rotation** | **50-200ms** | Done in background |

#### 4.2.6 Rotation Algorithm (Background Thread)
```c
1. Wait on condition variable
2. When signaled:
   a. Close pending_rotate_file (slow - flushes to disk)
   b. Generate rotated filename with date
   c. If filename exists, append sequence number
   d. Rename pending_rotate_path to rotated name
   e. Enforce retention policy (scan & delete old logs)
   f. Clear rotation_pending flag
3. Loop back to wait (or exit if shutdown_requested)
```

### 4.3 Retention Policy

#### 4.3.1 Policy Rules
- Keep logs from the last 5 days
- Total log storage must not exceed 100MB
- If both limits are violated, delete oldest logs first

#### 4.3.2 Retention Algorithm
```c
1. Scan /var/log for fc-1.*.log files
2. Parse date from filename
3. Delete files older than 5 days
4. Calculate total size of remaining logs
5. If total > 100MB, delete oldest files until under limit
```

### 4.4 Integration with interface.c

Modify `imx_cli_log_printf()` to add filesystem logging:

```c
void imx_cli_log_printf(bool print_time, char *format, ...)
{
    char full_message[LOG_MSG_MAX_LENGTH];
    int offset = 0;

    /* Build timestamp if requested */
    if (print_time) {
        offset = build_timestamp(full_message, sizeof(full_message));
    }

    /* Format user message */
    va_list args;
    va_start(args, format);
    vsnprintf(full_message + offset, sizeof(full_message) - offset, format, args);
    va_end(args);

    /* [NEW] Write to filesystem logger (always) */
    if (fs_logger_is_active()) {
        fs_logger_write(full_message);
    }

    /* Existing console/device output logic... */
    /* (unchanged) */
}
```

### 4.5 Thread Safety

- All filesystem operations protected by `log_mutex`
- Non-blocking writes (buffer if file I/O slow)
- Graceful handling of file system errors

---

## 5. Implementation Tasks (Todo List)

### Phase 1: Setup and Preparation
- [ ] Create feature branches in iMatrix and Fleet-Connect-1
- [ ] Create filesystem_logger.h using blank.h template
- [ ] Create filesystem_logger.c using blank.c template

### Phase 2: Core Implementation
- [ ] Implement fs_logger_config_t and fs_logger_state_t structures
- [ ] Implement fs_logger_init() with directory/file creation
- [ ] Implement background rotation thread creation in fs_logger_init()
- [ ] Implement fs_logger_write() with async rotation triggering
- [ ] Implement fs_logger_shutdown() with thread join

### Phase 3: Rotation and Retention (Background Thread)
- [ ] Implement fs_logger_rotation_thread() main loop
- [ ] Implement rotation trigger detection (startup, daily, size)
- [ ] Implement fs_logger_rotate() to signal background thread
- [ ] Implement fs_logger_generate_rotated_name() with date/sequence
- [ ] Implement fs_logger_enforce_retention()
- [ ] Implement log file scanning and date parsing

### Phase 4: Integration
- [ ] Modify interface.c to call fs_logger_write()
- [ ] Modify linux_gateway.c to call fs_logger_init() and fs_logger_shutdown()
- [ ] Update CMakeLists.txt to include new source file
- [ ] Add CLI command: `log status` to show current log info (optional)

### Phase 5: Build and Test
- [ ] Run linter on new files
- [ ] Build system - fix any compilation errors
- [ ] Build system - fix any compilation warnings
- [ ] Final clean build verification

### Phase 6: Documentation and Merge
- [ ] Update this plan document with completion notes
- [ ] Merge branches back to Aptera_1_Clean
- [ ] Update CLI documentation if CLI commands added

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| File system full | Logs may fail to write | Check available space before write, graceful error handling |
| Permission denied | Cannot create/write logs | Ensure /var/log is writable, fall back to /tmp if needed |
| Performance impact | Slow file I/O blocks CAN | **Async rotation** - background thread handles slow operations |
| File corruption | Log data lost | fsync() on rotation, atomic rename |
| Embedded flash wear | NAND wear from frequent writes | Buffer writes, rotate less frequently |
| Rotation thread crash | Logs not rotated | Thread monitors own health, restarts if needed |
| Rapid rotation | Many files created | Rate-limit rotation to max once per minute |
| Thread deadlock | System hangs | Use timeout on mutex, avoid nested locks |

---

## 7. Testing Plan

### 7.1 Unit Tests (on development machine)
1. Test log file creation in /var/log/
2. Test log rotation on restart
3. Test log rotation at size limit
4. Test retention policy enforcement
5. Test thread safety with concurrent writes

### 7.2 Integration Tests (on FC-1 device)
1. SSH into FC-1: `ssh -p 22222 root@192.168.7.1`
2. Run FC-1 application: `sv restart FC-1`
3. Verify log file created: `ls -la /var/log/fc-1.log`
4. Tail log file: `tail -f /var/log/fc-1.log`
5. Restart FC-1 and verify rotation
6. Check disk usage: `df -h /var/log`

### 7.3 Verification Checklist
- [ ] Logs written to /var/log/fc-1.log
- [ ] Timestamps present in log entries
- [ ] Log rotates on FC-1 restart
- [ ] Log rotates at 10MB size limit
- [ ] Old logs deleted after 5 days
- [ ] Total log size stays under 100MB
- [ ] No performance degradation observed
- [ ] Console output still works normally

---

## 8. Estimated Effort

| Phase | Estimated Lines of Code |
|-------|-------------------------|
| filesystem_logger.h | ~100 lines |
| filesystem_logger.c | ~500 lines |
| - Core init/write/shutdown | ~150 lines |
| - Background rotation thread | ~150 lines |
| - Retention policy enforcement | ~100 lines |
| - Utility functions | ~100 lines |
| interface.c modifications | ~20 lines |
| linux_gateway.c modifications | ~10 lines |
| CMakeLists.txt modifications | ~5 lines |
| **Total** | **~635 lines** |

---

## 9. Approval Section

**Plan Approved By:** _________________________ **Date:** _____________

**Approval Notes:**

---

## 10. Implementation Notes

*(To be filled in after implementation is complete)*

---

## 11. Completion Summary

*(To be filled in after work is verified complete)*

| Metric | Value |
|--------|-------|
| Tokens Used | TBD |
| Recompilations for Syntax Errors | TBD |
| Elapsed Time | TBD |
| Actual Work Time | TBD |
| Time Waiting on User | TBD |

---

*Document Generated: 2025-12-30*
*Source Specification: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/direct_all_logs_to_filesystem.yaml*
