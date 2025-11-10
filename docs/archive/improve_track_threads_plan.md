# Thread and Timer Tracking Enhancement - Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding comprehensive thread and timer tracking capabilities to the iMatrix ecosystem (iMatrix core library and Fleet-Connect-1 application). The system will track all threads created during runtime, monitor periodic timer callbacks, detect crashes/terminations, and provide diagnostic tools through a unified CLI command.

**Target Platforms:** Linux only (pthread-based)
**Scope:** Both iMatrix and Fleet-Connect-1 codebases
**Approach:**
- Enhance existing `imx_thread_create()` abstraction and migrate all direct `pthread_create()` calls
- Wrap `imx_run_loop_register_app_handler()` to track periodic timer callbacks

---

## 1. Current State Analysis

### 1.1 Existing Thread Abstraction

The iMatrix platform already has a thread abstraction layer:
- **Location:** `iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.c`
- **API Function:** `imx_thread_create()`
- **Features:** Thread naming, detached thread creation
- **Problem:** Not used consistently - most code calls `pthread_create()` directly

### 1.2 Thread Inventory

**iMatrix Threads (11 total):**
1. **CAN TCP Server** - `can_server.c:705` - TCP server for CAN data distribution
2. **CAN Bus 0 Processing** - `can_utils.c:310` - CAN interface 0 message processing
3. **CAN Bus 1 Processing** - `can_utils.c:376` - CAN interface 1 message processing
4. **UBX GPS Reader** - `ubx_gps.c:777` - UBX protocol GPS data reader
5. **CAN Simulate File 1** - `simulate_can.c:305` - CAN trace file playback (bus 0)
6. **CAN Simulate File 2** - `simulate_can.c:335` - CAN trace file playback (bus 1)
7. **CAN Simulate File 3** - `simulate_can.c:367` - CAN trace file playback (bus 2)
8. **GPS Serial Reader** - `quake_gps.c:801` - NMEA GPS data reader
9. **CAN File Send** - `can_file_send.c:355` - CAN message file transmission
10. **CAN Processing** - `can_processing_thread.c:159` - Dedicated CAN message processor
11. **Network Manager** - Uses `imx_thread_create()` (already abstracted)

**Fleet-Connect-1 Threads (2 total):**
1. **Accelerometer Processing** - `accel_process.c:907` - G-force data processing
2. **i15765 OBD2 Service** - `process_obd2.c:429` - ISO 15765-2 protocol handler

**Total Direct pthread_create() Calls:** 12 (need migration to tracked wrapper)

### 1.3 Timer/Callback Inventory

**Critical Timer Callbacks (1 primary):**
1. **Main Application Handler** - `linux_gateway.c:162` - `imx_process_handler()`
   - **Interval:** 100ms
   - **Function:** Core application processing loop
   - **Critical:** YES - Processes CoAP, CLI, provisioning, network management
   - **Calls:** `imx_process()` and `do_everything()`
   - **Impact if stopped:** Entire application freezes

**Implementation Details:**
- Uses btstack_run_loop timer system
- Registered via `imx_run_loop_register_app_handler(imx_process_handler, IMX_PROCESS_INTERVAL)`
- Runs in main thread context (not a separate thread)
- Must execute every 100ms for system health

**Why Timer Tracking is Critical:**
- If this timer stops, the application is effectively frozen
- No user-facing indication if timer is delayed or blocked
- More critical than some threads since it's the main execution path
- Need to detect if handler is taking too long (blocking other operations)
- Need to detect missed executions (handler not called on schedule)

---

## 2. Design Architecture

### 2.1 Thread Registry Structure

```c
typedef struct {
    pthread_t thread_id;           // System thread ID
    char name[32];                 // Thread name (user-provided)
    char creator_function[64];     // Function that created thread
    char creator_file[128];        // Source file that created thread
    int creator_line;              // Line number in source file

    // Timing information
    struct timespec created_time;  // When thread was created
    struct timespec start_time;    // When thread started executing
    struct timespec end_time;      // When thread terminated (if applicable)

    // Status tracking
    enum {
        THREAD_STARTING,
        THREAD_RUNNING,
        THREAD_TERMINATED_NORMAL,
        THREAD_TERMINATED_ERROR,
        THREAD_CRASHED
    } status;

    int exit_code;                 // Thread exit code (if terminated)
    void *exit_value;              // Thread return value

    // Resource usage (via pthread_getaffinity, /proc/self/task/[tid]/stat)
    uint64_t cpu_time_user_ns;    // User CPU time in nanoseconds
    uint64_t cpu_time_system_ns;  // System CPU time in nanoseconds
    size_t stack_size;             // Thread stack size

    // Function pointers
    imx_thread_function_t thread_function;
    void *thread_arg;

    // Flags
    bool is_active;                // Thread entry is valid
    bool is_detached;              // Thread is detached
} thread_registry_entry_t;

#define MAX_TRACKED_THREADS 32

typedef struct {
    thread_registry_entry_t entries[MAX_TRACKED_THREADS];
    int count;
    pthread_mutex_t registry_mutex;
} thread_registry_t;
```

### 2.2 Timer Registry Structure

```c
typedef struct {
    char name[64];                      // Timer name
    char handler_name[64];              // Handler function name
    uint32_t interval_ms;               // Expected interval in milliseconds
    void (*handler)(void);              // Handler function pointer

    // Registration tracking
    struct timespec registration_time;  // When timer was registered
    char creator_file[128];             // File that registered timer
    int creator_line;                   // Line number
    char creator_function[64];          // Function that registered timer

    // Execution tracking
    struct timespec last_execution;     // Last time handler ran
    struct timespec prev_execution;     // Previous execution (for interval calc)
    uint64_t execution_count;           // Number of times executed

    // Performance tracking
    uint64_t total_execution_time_us;   // Total time spent in handler
    uint32_t avg_execution_time_us;     // Average execution time
    uint32_t max_execution_time_us;     // Maximum execution time
    uint32_t min_execution_time_us;     // Minimum execution time
    uint32_t last_execution_time_us;    // Most recent execution time

    // Health tracking
    uint32_t missed_count;              // Detected missed executions
    uint32_t late_count;                // Executions that started late
    uint32_t max_delay_ms;              // Max delay from expected time
    uint32_t min_interval_ms;           // Shortest observed interval
    uint32_t max_interval_ms;           // Longest observed interval

    // Status
    enum {
        TIMER_REGISTERED,
        TIMER_RUNNING,
        TIMER_STALLED,                  // Not executed recently
        TIMER_OVERRUN                   // Taking longer than interval
    } status;

    bool is_active;                     // Timer is registered and firing
    bool is_critical;                   // Critical timer (main app handler)
} timer_registry_entry_t;

#define MAX_TRACKED_TIMERS 16

typedef struct {
    timer_registry_entry_t entries[MAX_TRACKED_TIMERS];
    int count;
    pthread_mutex_t registry_mutex;
} timer_registry_t;
```

### 2.3 Enhanced Thread Wrapper

The existing `imx_thread_create()` will be enhanced to:
1. Register thread in global registry before creation
2. Wrap the user's thread function with monitoring wrapper
3. Track thread lifecycle (start, run, terminate)
4. Capture resource usage periodically
5. Detect abnormal terminations

```c
// Enhanced API with tracking metadata
imx_result_t imx_thread_create_tracked(
    imx_thread_t *thread_ptr,
    const char *name,
    size_t stack_size,
    imx_thread_function_t thread_function,
    void *arg,
    const char *creator_file,
    int creator_line,
    const char *creator_function
);

// Macro for easy use with automatic file/line/function capture
#define imx_thread_create(thread, name, stack, func, arg) \
    imx_thread_create_tracked(thread, name, stack, func, arg, \
                               __FILE__, __LINE__, __func__)
```

### 2.3 Thread Monitoring Wrapper

```c
static void *thread_monitoring_wrapper(void *arg)
{
    thread_wrapper_context_t *ctx = (thread_wrapper_context_t *)arg;

    // 1. Mark thread as RUNNING
    thread_registry_update_status(ctx->registry_index, THREAD_RUNNING);
    thread_registry_record_start_time(ctx->registry_index);

    // 2. Set thread name
    pthread_setname_np(pthread_self(), ctx->name);

    // 3. Execute user thread function
    void *result = NULL;
    int exit_code = 0;

    // Install signal handlers for crash detection
    signal(SIGSEGV, thread_crash_handler);
    signal(SIGABRT, thread_crash_handler);

    result = ctx->user_function(ctx->user_arg);

    // 4. Record completion
    thread_registry_record_exit(ctx->registry_index, THREAD_TERMINATED_NORMAL,
                                 exit_code, result);

    free(ctx);
    return result;
}
```

### 2.4 Crash Detection

Use signal handlers to detect thread crashes:
```c
static void thread_crash_handler(int sig)
{
    pthread_t self = pthread_self();
    int registry_index = thread_registry_find_by_pthread(self);

    if (registry_index >= 0) {
        thread_registry_update_status(registry_index, THREAD_CRASHED);
        thread_registry_record_signal(registry_index, sig);
    }

    // Log crash
    imx_cli_log_printf(true, "[THREAD CRASH] Thread crashed with signal %d\r\n", sig);

    // Re-raise signal for default handling
    signal(sig, SIG_DFL);
    raise(sig);
}
```

### 2.5 Timer Wrapper and Tracking

Wrap `imx_run_loop_register_app_handler()` to intercept timer registration and execution:

```c
// Enhanced timer registration with tracking
void imx_run_loop_register_app_handler_tracked(
    void (*handler)(void),
    uint32_t interval_ms,
    const char *name,
    const char *creator_file,
    int creator_line,
    const char *creator_function
);

// Macro for automatic metadata capture
#define imx_run_loop_register_app_handler(handler, interval) \
    imx_run_loop_register_app_handler_tracked(handler, interval, \
                                               #handler, __FILE__, __LINE__, __func__)

// Timer monitoring wrapper
static void timer_monitoring_wrapper(void)
{
    int registry_index = /* get index from context */;
    struct timespec start_time, end_time;

    // 1. Record start time
    clock_gettime(CLOCK_MONOTONIC, &start_time);

    // 2. Check if late (compare to expected time based on interval)
    timer_registry_check_timeliness(registry_index, &start_time);

    // 3. Call actual user handler
    void (*user_handler)(void) = timer_registry_get_handler(registry_index);
    user_handler();

    // 4. Record end time and update statistics
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    timer_registry_record_execution(registry_index, &start_time, &end_time);

    // 5. Check for overrun (execution time > interval)
    uint32_t execution_time_us = timespec_diff_us(&end_time, &start_time);
    uint32_t interval_us = timer_registry_get_interval_us(registry_index);

    if (execution_time_us > interval_us) {
        timer_registry_record_overrun(registry_index, execution_time_us);
        imx_cli_log_printf(true, "[TIMER] WARNING: Handler took %uus (interval: %uus)\r\n",
                           execution_time_us, interval_us);
    }
}
```

### 2.6 Timer Health Monitoring

Detect stalled or problematic timers:

```c
// Periodic health check (called from background thread or existing timer)
void timer_registry_health_check(void)
{
    struct timespec current_time;
    clock_gettime(CLOCK_MONOTONIC, &current_time);

    for (int i = 0; i < timer_registry.count; i++) {
        timer_registry_entry_t *entry = &timer_registry.entries[i];

        if (!entry->is_active) continue;

        // Calculate time since last execution
        uint64_t elapsed_ms = timespec_diff_ms(&current_time, &entry->last_execution);

        // Check if timer is stalled (not executed in 3x expected interval)
        if (elapsed_ms > (entry->interval_ms * 3)) {
            entry->status = TIMER_STALLED;
            entry->missed_count++;

            imx_cli_log_printf(true,
                "[TIMER] WARNING: Timer '%s' stalled! Last execution %llu ms ago (expected: %u ms)\r\n",
                entry->name, elapsed_ms, entry->interval_ms);
        }

        // Check for overrun condition
        if (entry->last_execution_time_us > (entry->interval_ms * 1000)) {
            entry->status = TIMER_OVERRUN;

            if (entry->is_critical) {
                imx_cli_log_printf(true,
                    "[TIMER] CRITICAL: Timer '%s' overrunning! Execution: %u us, Interval: %u us\r\n",
                    entry->name, entry->last_execution_time_us, entry->interval_ms * 1000);
            }
        }
    }
}
```

---

## 3. Implementation Components

### 3.1 New Files

**iMatrix/platform_functions/thread_tracker.h**
- Thread registry structure definitions
- Timer registry structure definitions
- API function prototypes
- Thread and timer status enumerations

**iMatrix/platform_functions/thread_tracker.c**
- Thread registry implementation
- Timer registry implementation
- Thread wrapper functions
- Timer wrapper functions
- Resource usage collection
- Crash detection handlers
- Timer health monitoring

**iMatrix/cli/cli_threads.h**
- CLI command prototypes

**iMatrix/cli/cli_threads.c**
- `threads` CLI command implementation
- Thread and timer status display functions
- Support for table, detail, and JSON output modes
- Support for filtering (threads-only, timers-only, or both)

### 3.2 Modified Files

**iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.h**
- Add tracking metadata parameters to `imx_thread_create()`
- Add macro for automatic file/line/function capture

**iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.c**
- Enhance `imx_thread_create()` to call thread tracker registration
- Add monitoring wrapper integration

**iMatrix/imatrix_interface.h**
- Add tracking metadata parameters to `imx_run_loop_register_app_handler()`
- Add macro for automatic file/line/function capture

**iMatrix/imatrix_interface.c**
- Enhance `imx_run_loop_register_app_handler()` to call timer tracker registration
- Add timer monitoring wrapper integration

**iMatrix/cli/cli.c**
- Add `threads` command to command table

**All files with pthread_create() calls (12 files):**
- Replace `pthread_create()` with `imx_thread_create()`
- Update thread structures to use `imx_thread_t`

### 3.3 Build System Changes

**iMatrix/CMakeLists.txt**
- Add `platform_functions/thread_tracker.c`
- Add `cli/cli_threads.c`

---

## 4. CLI Command Specification

### 4.1 Command Syntax

```
threads [options]
```

**Options:**
- `(no args)` - Display table format showing both threads and timers (default)
- `-v` or `--verbose` - Detailed multi-line format
- `-j` or `--json` - JSON output
- `-a` or `--all` - Include terminated threads (default: active only)
- `-t` or `--threads-only` - Show only threads, hide timers
- `-T` or `--timers-only` - Show only timers, hide threads
- `-h` or `--help` - Display help

### 4.2 Output Formats

**Table Format (Default):**
```
THREADS:
TID      NAME                 STATUS      CREATED          CPU(us)  STACK   CREATOR
-------- -------------------- ----------- ---------------- -------- ------- ------------------
12345    can_process          RUNNING     12:34:56.789     1234567  64KB    can_utils.c:310
12346    gps_reader           RUNNING     12:34:57.123     234567   32KB    quake_gps.c:801
12347    tcp_server           RUNNING     12:35:00.456     456789   64KB    can_server.c:705

Total: 13 threads (13 active, 0 terminated)

TIMERS:
NAME                 INTERVAL STATUS      EXECUTIONS   AVG_TIME   MAX_TIME   LATE/MISS CREATOR
-------------------- -------- ----------- ------------ ---------- ---------- --------- ------------------
imx_process_handler  100ms    RUNNING     123456       1.2ms      15.3ms     0/0       linux_gateway.c:162

Total: 1 timers (1 active, 0 stalled)
```

**Detailed Format (-v):**
```
===== THREADS =====

Thread 1:
  TID:             12345
  Name:            can_process
  Status:          RUNNING
  Created:         2025-11-08 12:34:56.789
  Started:         2025-11-08 12:34:56.790
  Creator:         can_utils.c:310 (process_canbus)
  CPU Time:        User: 1.234s, System: 0.567s
  Stack Size:      65536 bytes
  Detached:        Yes

Thread 2:
  ...

===== TIMERS =====

Timer 1:
  Name:            imx_process_handler
  Status:          RUNNING
  Interval:        100 ms
  Registered:      2025-11-08 12:34:50.000
  Creator:         linux_gateway.c:162 (imx_host_application_start)

  Execution Stats:
    Total Executions:    123456
    Last Execution:      2025-11-08 14:30:15.789
    Execution Count:     123456

  Performance:
    Avg Time:           1.2 ms
    Min Time:           0.8 ms
    Max Time:           15.3 ms
    Last Time:          1.1 ms

  Health:
    Late Count:         3
    Missed Count:       0
    Max Delay:          5 ms
    Interval Range:     95-105 ms

  Critical:          Yes
```

**JSON Format (-j):**
```json
{
  "threads": [
    {
      "tid": 12345,
      "name": "can_process",
      "status": "RUNNING",
      "created_time": "2025-11-08T12:34:56.789Z",
      "started_time": "2025-11-08T12:34:56.790Z",
      "creator": {
        "file": "can_utils.c",
        "line": 310,
        "function": "process_canbus"
      },
      "cpu_time_us": 1234567,
      "stack_size": 65536,
      "is_detached": true
    }
  ],
  "timers": [
    {
      "name": "imx_process_handler",
      "status": "RUNNING",
      "interval_ms": 100,
      "registered_time": "2025-11-08T12:34:50.000Z",
      "creator": {
        "file": "linux_gateway.c",
        "line": 162,
        "function": "imx_host_application_start"
      },
      "execution_stats": {
        "total_executions": 123456,
        "last_execution_time": "2025-11-08T14:30:15.789Z",
        "avg_execution_time_us": 1200,
        "min_execution_time_us": 800,
        "max_execution_time_us": 15300,
        "last_execution_time_us": 1100
      },
      "health": {
        "late_count": 3,
        "missed_count": 0,
        "max_delay_ms": 5,
        "min_interval_ms": 95,
        "max_interval_ms": 105
      },
      "is_critical": true
    }
  ],
  "summary": {
    "total_threads": 13,
    "active_threads": 13,
    "terminated_threads": 0,
    "total_timers": 1,
    "active_timers": 1,
    "stalled_timers": 0
  }
}
```

---

## 5. Implementation Todo List

### Phase 1: Infrastructure (Foundation)

- [ ] **1.1** Create `iMatrix/platform_functions/thread_tracker.h`
  - Define `thread_registry_entry_t` structure
  - Define `thread_registry_t` structure
  - Define `timer_registry_entry_t` structure
  - Define `timer_registry_t` structure
  - Define thread and timer status enumerations
  - Declare API functions for both threads and timers

- [ ] **1.2** Create `iMatrix/platform_functions/thread_tracker.c`
  - Implement thread registry initialization
  - Implement timer registry initialization
  - Implement thread registration function
  - Implement timer registration function
  - Implement thread status update functions
  - Implement timer status update functions
  - Implement thread lookup functions
  - Implement timer lookup functions
  - Add registry mutex protection for both registries

- [ ] **1.3** Add build system support
  - Update `iMatrix/CMakeLists.txt` to include `thread_tracker.c`
  - Verify compilation with new files

### Phase 2: Thread Wrapper Enhancement

- [ ] **2.1** Enhance `imx_linux_platform.h`
  - Add `imx_thread_create_tracked()` prototype
  - Add macro for `imx_thread_create()` with auto file/line/func capture
  - Add wrapper context structure

- [ ] **2.2** Enhance `imx_linux_platform.c`
  - Implement `imx_thread_create_tracked()`
  - Implement thread monitoring wrapper function
  - Integrate with thread registry
  - Add resource usage tracking
  - Add signal handlers for crash detection

- [ ] **2.3** Test enhanced wrapper
  - Create simple test program
  - Verify thread tracking works
  - Verify crash detection works

### Phase 3: Migrate pthread_create() Calls

**iMatrix Migration (10 files):**

- [ ] **3.1** `iMatrix/canbus/can_server.c:705`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test CAN TCP server still works

- [ ] **3.2** `iMatrix/canbus/can_utils.c:310` (CAN bus 0)
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test CAN bus 0 processing

- [ ] **3.3** `iMatrix/canbus/can_utils.c:376` (CAN bus 1)
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test CAN bus 1 processing

- [ ] **3.4** `iMatrix/quake/ubx_gps.c:777`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test UBX GPS reader

- [ ] **3.5** `iMatrix/canbus/simulate_can.c:305,335,367` (3 threads)
  - Replace all 3 pthread_create calls with imx_thread_create
  - Update thread variables to imx_thread_t
  - Test CAN simulation

- [ ] **3.6** `iMatrix/quake/quake_gps.c:801`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test GPS serial reader

- [ ] **3.7** `iMatrix/canbus/can_file_send.c:355`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test CAN file send

- [ ] **3.8** `iMatrix/canbus/can_processing_thread.c:159`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test CAN processing thread

**Fleet-Connect-1 Migration (2 files):**

- [ ] **3.9** `Fleet-Connect-1/hal/accel_process.c:907`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test accelerometer processing

- [ ] **3.10** `Fleet-Connect-1/OBD2/process_obd2.c:429`
  - Replace pthread_create with imx_thread_create
  - Update thread variable to imx_thread_t
  - Test OBD2 processing

### Phase 3b: Timer Tracking Implementation

- [ ] **3b.1** Enhance `iMatrix/imatrix_interface.h`
  - Add `imx_run_loop_register_app_handler_tracked()` prototype
  - Add macro for automatic file/line/function capture
  - Add timer tracking function prototypes

- [ ] **3b.2** Enhance `iMatrix/imatrix_interface.c`
  - Implement `imx_run_loop_register_app_handler_tracked()`
  - Create timer monitoring wrapper function
  - Integrate with timer registry
  - Add performance tracking (execution time measurement)
  - Add health checking (detect late/missed executions)

- [ ] **3b.3** Migrate timer registration in Fleet-Connect-1
  - `Fleet-Connect-1/linux_gateway.c:162` - Already uses macro, will automatically use new wrapper
  - Verify timer tracking works
  - Mark as critical timer

- [ ] **3b.4** Test timer tracking
  - Verify timer registered in registry
  - Verify execution statistics collected
  - Verify performance tracking (avg/min/max times)
  - Test overrun detection (slow handler)
  - Test stall detection (stopped timer)

### Phase 4: CLI Command Implementation

- [ ] **4.1** Create `iMatrix/cli/cli_threads.h`
  - Declare `cli_threads()` function
  - Add any helper function prototypes

- [ ] **4.2** Create `iMatrix/cli/cli_threads.c`
  - Implement argument parsing (no args, -v, -j, -a, -t, -T, -h)
  - Implement table format display for threads
  - Implement table format display for timers
  - Implement detailed format display for threads
  - Implement detailed format display for timers
  - Implement JSON format display (threads and timers)
  - Add filtering (active vs all, threads-only, timers-only)
  - Add Doxygen comments

- [ ] **4.3** Register command in CLI
  - Add `#include "cli_threads.h"` to `cli.c`
  - Add entry to command[] array in `cli.c`
  - Update CMakeLists.txt to include `cli_threads.c`

- [ ] **4.4** Test CLI command
  - Test default table output (both threads and timers)
  - Test `-v` detailed output (both threads and timers)
  - Test `-j` JSON output (both threads and timers)
  - Test `-a` all threads (including terminated)
  - Test `-t` threads-only filter
  - Test `-T` timers-only filter
  - Test `-h` help

### Phase 5: Resource Usage Tracking

- [ ] **5.1** Implement CPU time collection
  - Use `/proc/self/task/[tid]/stat` parsing
  - Parse utime and stime fields
  - Convert to microseconds
  - Update registry periodically

- [ ] **5.2** Implement stack usage tracking
  - Get stack size from pthread attributes
  - Store in registry
  - Display in CLI

- [ ] **5.3** Add periodic update mechanism
  - Create background thread or use existing timer
  - Update resource stats every N seconds
  - Add mutex protection for registry updates

- [ ] **5.4** Implement timer health monitoring
  - Add periodic health check function
  - Detect stalled timers (not executed recently)
  - Detect overrun conditions (execution > interval)
  - Log warnings for critical timer issues
  - Update timer status based on health check

### Phase 6: Crash Detection Enhancement

- [ ] **6.1** Implement signal handlers
  - Handle SIGSEGV (segmentation fault)
  - Handle SIGABRT (abort)
  - Handle SIGILL (illegal instruction)
  - Handle SIGFPE (floating point exception)

- [ ] **6.2** Record crash information
  - Store signal number
  - Store crash timestamp
  - Update thread status to CRASHED
  - Log crash to system log

- [ ] **6.3** Test crash detection
  - Create test thread that crashes
  - Verify status updated to CRASHED
  - Verify crash logged
  - Verify `threads` command shows crash

### Phase 7: Testing & Validation

- [ ] **7.1** Unit testing
  - Test thread registration
  - Test thread status updates
  - Test registry lookup functions
  - Test resource usage collection

- [ ] **7.2** Integration testing
  - Build full iMatrix with all threads
  - Verify all threads tracked
  - Run for extended period
  - Check for memory leaks
  - Verify no performance degradation

- [ ] **7.3** System testing
  - Test with Fleet-Connect-1 full application
  - Verify CAN bus threads tracked
  - Verify OBD2 threads tracked
  - Test CLI command in real system
  - Test crash detection with intentional crashes

### Phase 8: Documentation & Completion

- [ ] **8.1** Update documentation
  - Add thread tracking to architecture docs
  - Document CLI command usage
  - Add examples to developer guide

- [ ] **8.2** Code review and cleanup
  - Review all modified files
  - Check Doxygen comments complete
  - Verify coding standards
  - Remove any debug code

- [ ] **8.3** Final testing
  - Run full regression tests
  - Verify no regressions introduced
  - Test on target hardware if available

- [ ] **8.4** Prepare for merge
  - Ensure all todos checked off
  - Commit all changes
  - Test branch builds cleanly
  - Prepare merge request

---

## 6. Technical Considerations

### 6.1 Thread Safety

- **Registry Mutex:** All registry operations protected by mutex (separate mutexes for thread and timer registries)
- **Signal Handler Safety:** Signal handlers use async-signal-safe functions only
- **Resource Collection:** Periodic updates use mutex to protect registry
- **Timer Wrapper Thread Safety:** Wrapper executes in main thread context, no concurrency issues

### 6.2 Performance Impact

- **Thread Creation Overhead:** Minimal (~10-20 microseconds per thread)
- **Timer Registration Overhead:** Minimal (~5-10 microseconds per timer)
- **Timer Execution Overhead:** ~2-3 microseconds per timer callback (timestamp collection)
- **Runtime Overhead:** Negligible (only updates on state changes)
- **Memory Overhead:**
  - ~400 bytes per tracked thread (max 32 threads = 12.8KB)
  - ~350 bytes per tracked timer (max 16 timers = 5.6KB)
  - **Total:** ~18.4KB maximum

### 6.3 Platform Limitations

- **Linux-specific:** Uses `/proc` filesystem for resource stats
- **pthread-only:** Not compatible with WICED platform (as specified)
- **Signal limitations:** Some crashes may not be catchable (SIGKILL, etc.)

### 6.4 Error Handling

- **Registry full:** Log error, thread still created but not tracked
- **Mutex errors:** Log error, attempt best-effort tracking
- **Resource collection errors:** Log error, skip that update cycle

---

## 7. Testing Strategy

### 7.1 Unit Tests

Create dedicated test program `test_thread_tracking.c`:
- Test thread registry initialization
- Test timer registry initialization
- Test thread registration/deregistration
- Test timer registration
- Test thread status updates
- Test timer execution tracking
- Test crash detection
- Test resource collection
- Test timer health monitoring
- Test overrun detection
- Test stall detection

### 7.2 Integration Tests

- Build iMatrix with tracking enabled
- Create test script that exercises all thread types
- Create test script that exercises timer callbacks
- Verify tracking for all threads
- Verify tracking for timers
- Test CLI command outputs (threads and timers)
- Test timer performance tracking
- Monitor for memory leaks

### 7.3 Stress Tests

- Create/destroy threads rapidly
- Verify registry handles churn
- Check for race conditions
- Monitor performance impact

---

## 8. Rollback Plan

If issues arise:
1. Keep `feature/thread-tracking` branches separate
2. Can revert to original `Aptera_1` branches
3. Thread tracking is non-critical feature
4. Existing code continues to work without tracking

---

## 9. Future Enhancements (Out of Scope)

- WICED platform support (would require RTOS-specific implementation)
- Thread priority tracking and adjustment
- Thread affinity management
- Deadlock detection
- Thread pool management
- Historical thread statistics
- Alert on thread crashes
- Auto-restart crashed threads

---

## 10. Branch Information

**Created Branches:**
- `iMatrix`: `feature/thread-tracking` (from `Aptera_1`)
- `Fleet-Connect-1`: `feature/thread-tracking` (from `Aptera_1`)

**Original Branches:**
- `iMatrix`: `Aptera_1`
- `Fleet-Connect-1`: `Aptera_1`

**Merge Target:**
- After testing and approval, merge back to respective original branches

---

## 11. Estimated Effort

Based on the detailed todo list:

| Phase | Tasks | Estimated Hours |
|-------|-------|----------------|
| Phase 1: Infrastructure | 3 tasks | 5 hours |
| Phase 2: Wrapper Enhancement | 3 tasks | 6 hours |
| Phase 3: Thread Migration | 10 tasks | 10 hours |
| Phase 3b: Timer Tracking | 4 tasks | 5 hours |
| Phase 4: CLI Command | 4 tasks | 8 hours |
| Phase 5: Resource Usage | 4 tasks | 5 hours |
| Phase 6: Crash Detection | 3 tasks | 4 hours |
| Phase 7: Testing | 3 tasks | 8 hours |
| Phase 8: Documentation | 4 tasks | 4 hours |
| **TOTAL** | **38 tasks** | **55 hours** |

**Note:** This is development time estimate. Actual elapsed time will depend on testing cycles and review feedback. Timer tracking adds ~11 hours to original estimate.

---

## 12. Success Criteria

Implementation is complete when:

**Thread Tracking:**
✓ All pthread_create() calls replaced with imx_thread_create()
✓ All threads tracked in registry
✓ Crash detection working and verified
✓ Resource usage accurately reported (CPU time, stack size)

**Timer Tracking:**
✓ Timer registration wrapper implemented
✓ All timers tracked in registry
✓ Timer performance metrics collected (avg/min/max execution time)
✓ Timer health monitoring working (stall/overrun detection)
✓ Critical timer flagged correctly

**CLI Command:**
✓ CLI `threads` command working with all output formats
✓ Table format displays both threads and timers
✓ Detailed format displays both threads and timers
✓ JSON format includes both threads and timers
✓ Filtering options working (-t, -T, -a)

**Quality:**
✓ No memory leaks introduced
✓ No performance degradation (<3us overhead per timer callback)
✓ All tests passing (unit, integration, stress)
✓ Documentation complete
✓ Code reviewed and approved

---

## Questions for User Review

Before implementation begins, please confirm:

**Answered:**
1. ✓ Is Linux-only implementation acceptable? (ANSWERED: Yes)
2. ✓ Should all pthread_create() calls be migrated? (ANSWERED: Yes, replace all)
3. ✓ Are the tracking fields sufficient? (ANSWERED: Yes - basic info, resource usage, crash detection, parent tracking)
4. ✓ Should timers be included in tracking? (ANSWERED: Yes, option 2 - include in same system)

**Please Confirm:**
5. Is 32 max tracked threads sufficient? (Or specify different limit)
6. Is 16 max tracked timers sufficient? (Or specify different limit)
7. Are there any specific threads that should NOT be tracked?
8. Are there any specific timers that should NOT be tracked?
9. Should thread/timer tracking be enabled by default or require configuration?
10. Any specific logging requirements for thread/timer events?
11. Should timer health monitoring warnings be logged to system log or just CLI?

---

---

## 13. Implementation Summary

**Plan Status:** ✓ IMPLEMENTATION COMPLETE

**Created:** 2025-11-08
**Implementation Completed:** 2025-11-08
**Author:** Claude Code (Sonnet 4.5)

### Implementation Phases Completed

✓ **Phase 1: Infrastructure** - Created thread_tracker.h/c with registries
✓ **Phase 2: Thread Wrapper** - Enhanced imx_thread_create with tracking
✓ **Phase 3: Thread Migration** - Migrated 12 pthread_create calls to tracked wrapper
✓ **Phase 3b: Timer Tracking** - Implemented timer monitoring for imx_run_loop_register_app_handler
✓ **Phase 4: CLI Command** - Created 'threads' command with table, verbose, JSON modes
✓ **Phase 5: Resource Usage** - Implemented CPU time tracking via /proc filesystem
✓ **Phase 6: Crash Detection** - Added signal handlers for SIGSEGV, SIGABRT, SIGILL, SIGFPE

### Files Created (4 new files)

1. **iMatrix/platform_functions/thread_tracker.h** - 394 lines
   - Thread and timer registry structures
   - Status enumerations
   - API function declarations

2. **iMatrix/platform_functions/thread_tracker.c** - 495 lines
   - Registry implementation
   - Resource tracking (/proc/self/task/[tid]/stat parsing)
   - Timer health monitoring

3. **iMatrix/cli/cli_threads.h** - 83 lines
   - CLI command prototypes

4. **iMatrix/cli/cli_threads.c** - 452 lines
   - Table, verbose, and JSON display formats
   - Thread and timer filtering options
   - Comprehensive help text

### Files Modified (16 files)

**Core Platform:**
1. iMatrix/imx_platform.h - Added imx_thread_create_tracked declaration and macro
2. iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.h - Fixed imx_thread_function_t signature
3. iMatrix/IMX_Platform/LINUX_Platform/imx_linux_platform.c - Implemented tracking wrapper and crash detection
4. iMatrix/imatrix.h - Added timer tracking declarations and macro
5. iMatrix/imatrix_interface.c - Implemented timer monitoring wrapper
6. iMatrix/CMakeLists.txt - Added thread_tracker.c and cli_threads.c

**Thread Migrations (9 files):**
7. iMatrix/canbus/can_server.c - Migrated CAN TCP server thread
8. iMatrix/canbus/can_structs.h - Changed pthread_t to imx_thread_t
9. iMatrix/canbus/can_utils.c - Migrated 2 CAN bus threads + fixed bug (thread0→thread1, can_bus_0_open→can_bus_1_open)
10. iMatrix/quake/ubx_gps.c - Migrated UBX GPS thread
11. iMatrix/canbus/simulate_can.c - Migrated 3 simulation threads + fixed bug (added thread3 declaration)
12. iMatrix/quake/quake_gps.c - Migrated NMEA GPS thread
13. iMatrix/canbus/can_file_send.c - Migrated file send thread
14. iMatrix/canbus/can_processing_thread.c - Migrated CAN processing thread
15. Fleet-Connect-1/hal/accel_process.c - Migrated accelerometer thread
16. Fleet-Connect-1/OBD2/process_obd2.c - Migrated OBD2 i15765 thread

**CLI Integration:**
17. iMatrix/cli/cli.c - Added 'threads' command to command table

### Bugs Fixed During Implementation

1. **CAN Bus 1 Thread Bug** (can_utils.c:376,382)
   - Was using thread0 instead of thread1 for CAN bus 1
   - Was setting can_bus_0_open instead of can_bus_1_open
   - Fixed both issues

2. **CAN Simulate Thread Bug** (simulate_can.c:367)
   - Thread3 was not declared but referenced
   - Added thread3 to declarations
   - Fixed to use thread3 instead of thread1

3. **Thread Function Type Mismatch** (imx_linux_platform.h:141)
   - imx_thread_function_t was defined as void (*)(void*)
   - Should be void *(*)(void*) to match pthread signature
   - Fixed typedef

### Implementation Statistics

**Lines of Code Added:** ~1,424 lines
- Infrastructure: 889 lines (thread_tracker.h/c)
- CLI: 535 lines (cli_threads.h/c)

**Lines of Code Modified:** ~45 lines across 13 files

**Threads Tracked:** 13 threads total
- iMatrix: 11 threads
- Fleet-Connect-1: 2 threads

**Timers Tracked:** 1 critical timer
- Main application handler (100ms interval)

**Compile Status:** ✓ All modified files compile successfully

### Token Usage

**Total Tokens Used:** ~214,000 tokens
- Planning and analysis: ~70,000 tokens
- Implementation: ~144,000 tokens

**Time Taken:**
- Elapsed time: ~1 hour
- Active development time: ~1 hour (continuous)

### Next Steps

1. **User Testing Required:**
   - Build complete iMatrix and Fleet-Connect-1 system
   - Run application and verify threads tracked
   - Execute `threads` CLI command to verify output
   - Test crash detection (optional - create test that crashes)
   - Verify timer tracking shows main application handler

2. **Testing Recommendations:**
   ```bash
   # Build and run
   cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
   cmake . && make
   ./build/Fleet-Connect

   # In CLI:
   threads           # View all threads and timers
   threads -v        # Detailed view
   threads -j        # JSON output
   threads -T        # Timers only (check main handler stats)
   ```

3. **Validation Checklist:**
   - [ ] All 13 threads appear in `threads` output
   - [ ] Timer shows imx_process_handler with 100ms interval
   - [ ] Thread names are descriptive
   - [ ] Creator information is accurate (file:line)
   - [ ] Timer execution stats update (run for a few minutes)
   - [ ] No memory leaks (monitor with `mem` command)
   - [ ] No performance degradation

4. **If Issues Found:**
   - Check specific thread/timer in detail with `threads -v`
   - Verify registry initialization succeeded
   - Check for error messages in logs

**Implementation Status:** COMPLETE - Ready for Testing

**Branches Ready for Merge:** (after successful testing)
- `iMatrix`: `feature/thread-tracking`
- `Fleet-Connect-1`: `feature/thread-tracking`
