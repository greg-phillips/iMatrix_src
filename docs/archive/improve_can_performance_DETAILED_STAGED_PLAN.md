# CAN Performance - Extremely Detailed Staged Implementation Plan

**Date**: November 7, 2025
**Branch**: feature/improve-can-performance
**Status**: 🚨 CRITICAL - Comprehensive plan with threading + async logging

---

## 🎯 Executive Summary

**Problem**: 90.5% packet drop rate (942,605 of 1,041,286 packets dropped)

**Root Causes**:
1. Buffers too small (500 messages, fills in 236ms at peak)
2. Processing in main loop (blocks on printf, signal extraction)
3. Synchronous logging in critical path (printf blocks on I/O)

**Solution Architecture** (4 Stages):
1. **Stage 1**: Increase buffers (immediate relief)
2. **Stage 2**: Async logging queue (eliminate printf blocking)
3. **Stage 3**: Separate processing thread (decouple from main loop)
4. **Stage 4**: Advanced optimizations (O(1) allocation, profiling)

**Expected Result**: Drop rate 90% → < 1%

---

## 🏗️ Proposed Architecture (After All Stages)

### Current Architecture (Problematic):
```
Main Loop (single thread):
    ↓
TCP Server Thread → canFrameHandler() → allocate → enqueue
    ↓ (blocks on printf!)
    ↓
Main Loop calls process_can_queues()
    ↓ dequeue → process → PRINTF() ← BLOCKS ON I/O!
    ↓ signal extraction
    ↓ MM2 writes
    ↓ return to pool
    ↓
Continue main loop (network, upload, etc.)
```

**Problems**:
- printf() in CAN threads blocks on I/O (terminal/file writes)
- Processing in main loop delays other critical tasks
- Single-threaded processing can't keep up with 2,117 fps

### Proposed Architecture (High Performance):
```
┌─────────────────────────────────────────────────────────────┐
│ TCP Server Thread (can_server.c)                            │
│   - Receives CAN frames from network                         │
│   - Parses ASCII format                                      │
│   - canFrameHandlerWithTimestamp()                          │
│   - Allocates from ring buffer                              │
│   - Enqueues to unified queue                               │
│   - NO PRINTF → Enqueues to log queue instead              │
└─────────────────────────────────────────────────────────────┘
                         ↓ CAN messages
┌─────────────────────────────────────────────────────────────┐
│ CAN Processing Thread (NEW - Stage 3)                       │
│   - Dedicated thread for CAN message processing            │
│   - Dequeues batches from unified queue                    │
│   - Extracts signals                                        │
│   - Writes to MM2                                           │
│   - Returns messages to ring buffer                         │
│   - NO PRINTF → Enqueues to log queue instead              │
└─────────────────────────────────────────────────────────────┘
                         ↓ Log messages
┌─────────────────────────────────────────────────────────────┐
│ Async Log Queue (NEW - Stage 2)                            │
│   - Lock-free ring buffer (or mutex-protected)             │
│   - Stores formatted log messages                           │
│   - Fixed size messages (256 bytes each)                    │
│   - 10,000 message capacity (2.5MB)                        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Main Loop / CLI Thread                                      │
│   - Dequeues log messages                                   │
│   - Prints to terminal/file asynchronously                  │
│   - No blocking of CAN threads                             │
│   - Continues other tasks (network, upload, etc.)           │
└─────────────────────────────────────────────────────────────┘
```

**Benefits**:
- ✅ CAN threads NEVER block on I/O
- ✅ Processing decoupled from main loop
- ✅ Logging is truly asynchronous
- ✅ Can handle 3,000+ fps bursts
- ✅ Main loop responsive for other tasks

---

## 📋 STAGE 1: Emergency Buffer Increase (IMMEDIATE)

**Goal**: Stop the bleeding - reduce drops from 90% to < 20%
**Time**: 30 minutes implementation + 1 hour testing
**Risk**: LOW (only constant changes)

### 1.1: Increase Ring Buffer Size

**File**: `iMatrix/canbus/can_utils.c`

**BEFORE (line 122)**:
```c
#define CAN_MSG_POOL_SIZE               500
```

**AFTER**:
```c
/*
 * CAN Message Pool Size
 *
 * Increased from 500 to 4000 to handle peak traffic of 2,117 fps.
 * At peak rate, buffer provides 1.9 seconds of headroom.
 * At normal rate (829 fps), buffer provides 4.8 seconds.
 *
 * Memory impact: 4000 × 24 bytes × 3 buses = 288KB (acceptable for 1GB RAM)
 *
 * Previous: 500 (causing 90% packet drops)
 * Current:  4000
 */
#define CAN_MSG_POOL_SIZE               4000
```

**Verification Steps**:
```bash
# 1. Check the change
grep "CAN_MSG_POOL_SIZE" canbus/can_utils.c
# Should show: #define CAN_MSG_POOL_SIZE  4000

# 2. Find all uses of this constant
grep -n "CAN_MSG_POOL_SIZE" canbus/*.c canbus/*.h
# Verify all locations make sense with 4000

# 3. Check array declarations
grep -n "can0_msg_pool\|can1_msg_pool\|can2_msg_pool" canbus/can_utils.c
# Should auto-size with CAN_MSG_POOL_SIZE

# 4. Check tracking arrays
grep -n "can0_in_use\|can1_in_use\|can2_in_use" canbus/can_utils.c
# Should auto-size with CAN_MSG_POOL_SIZE
```

**Expected Compilation**:
- ✅ Should compile without warnings
- ✅ Binary size increase: ~300KB (static arrays)
- ✅ Runtime memory: 288KB allocated at startup

### 1.2: Increase Unified Queue Size

**File**: `iMatrix/canbus/can_unified_queue.h`

**BEFORE (line 68)**:
```c
#define UNIFIED_QUEUE_SIZE          1500    /**< Total queue capacity (3 buses × 500) */
```

**AFTER**:
```c
/**
 * Unified Queue Size
 *
 * Total capacity for all CAN messages across all three buses.
 * Must be >= (CAN_MSG_POOL_SIZE × number_of_buses) to avoid
 * artificial queue bottleneck.
 *
 * Increased from 1500 to 12000 to match increased ring buffer size.
 * 3 buses × 4000 = 12000 total capacity.
 *
 * Memory impact: 12000 × 8 bytes (pointers) = 96KB
 *
 * Previous: 1500 (3 × 500)
 * Current:  12000 (3 × 4000)
 */
#define UNIFIED_QUEUE_SIZE          12000
```

**Verification Steps**:
```bash
# 1. Check malloc in unified_queue_init()
grep -A5 "malloc.*capacity.*sizeof" canbus/can_unified_queue.c
# Should handle 12000 × 8 = 96KB allocation

# 2. Verify no stack arrays of this size
grep -n "UNIFIED_QUEUE_SIZE\]" canbus/*.c
# Should only be used in malloc, not stack arrays

# 3. Check integer overflow
# 12000 fits in uint32_t ✓
```

### 1.3: Increase Batch Processing Size

**File**: `iMatrix/canbus/can_unified_queue.h`

**BEFORE (line 69)**:
```c
#define MAX_BATCH_SIZE              100     /**< Max messages dequeued per call */
```

**AFTER**:
```c
/**
 * Maximum Batch Size
 *
 * Number of messages dequeued and processed per call to process_can_queues().
 * Larger batches reduce mutex overhead and improve throughput.
 *
 * With 4000 message buffers, processing 200 per cycle provides:
 * - 20 cycles to drain full buffer
 * - Reduced lock/unlock overhead
 * - Better cache locality
 *
 * Previous: 100
 * Current:  200 (matches larger buffer size)
 */
#define MAX_BATCH_SIZE              200
```

**Verification Steps**:
```bash
# 1. Find stack array declarations
grep -n "batch\[MAX_BATCH_SIZE\]" canbus/*.c
# File: can_utils.c:697
# This is on stack - 200 × 8 bytes (pointers) = 1.6KB ← OK for stack

# 2. Check fairness limit scaling
# MAX_PER_BUS_PER_BATCH = 35 (per bus per batch)
# With 200 batch size: 35 × 3 buses = 105 messages
# 105 < 200 ✓ (leaves room for fairness)
```

### 1.4: Update Fairness Limit (Optional but Recommended)

**File**: `iMatrix/canbus/can_unified_queue.h`

**BEFORE (line 70)**:
```c
#define MAX_PER_BUS_PER_BATCH       35      /**< Fairness limit per bus per batch */
```

**AFTER**:
```c
/**
 * Fairness Limit Per Bus Per Batch
 *
 * Maximum messages from single bus in one batch dequeue.
 * Prevents one bus from monopolizing processing.
 *
 * Calculation: MAX_BATCH_SIZE / 3 buses = 200 / 3 ≈ 67 per bus
 * Set slightly lower to ensure fairness: 60 per bus
 *
 * Previous: 35 (for 100 batch size)
 * Current:  60 (for 200 batch size)
 */
#define MAX_PER_BUS_PER_BATCH       60
```

### 1.5: Build and Validate Stage 1

**Build Commands**:
```bash
cd /path/to/build
make clean
make -j$(nproc)

# Check for warnings
echo $?  # Should be 0

# Check binary size
ls -lh imatrix_gateway
# Should be ~300KB larger
```

**Deploy and Test**:
```bash
# Stop running instance
killall imatrix_gateway

# Start with monitoring
./imatrix_gateway > logs/stage1_test.txt 2>&1 &
PID=$!

# Wait for CAN traffic
sleep 60

# Check statistics
echo "can server" | nc localhost <cli_port>

# Expected:
# - Dropped: Should grow slowly, not rapidly
# - Drop Rate: < 100 drops/sec (was 566)
# - Buffer: < 60% (was 92%)
```

**Success Criteria for Stage 1**:
- ✅ Drop rate < 20% (was 90%)
- ✅ Buffer usage < 70% (was 92%)
- ✅ System compiles and runs
- ✅ No functional regressions

**If Stage 1 Fails**:
- Drops still > 20% → Processing is too slow → Proceed to Stage 2
- Buffer still > 80% → Need even larger buffers (try 8000)
- System crashes → Memory exhaustion → Rollback

---

## 📋 STAGE 2: Asynchronous Logging Queue (PERFORMANCE)

**Goal**: Eliminate printf() blocking from CAN threads
**Time**: 4 hours implementation + 2 hours testing
**Risk**: MEDIUM (threading complexity)

### 2.1: Design Async Log Queue Structure

**New File**: `iMatrix/cli/async_log_queue.h`

```c
/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 */

/**
 * @file async_log_queue.h
 * @brief Asynchronous logging queue for non-blocking diagnostic output
 * @date November 7, 2025
 * @author Greg Phillips
 *
 * This module implements a lock-free (or mutex-protected) ring buffer
 * for log messages. Critical threads (CAN processing, network) enqueue
 * messages without blocking on I/O. The CLI thread dequeues and prints
 * asynchronously.
 *
 * Architecture:
 *   CAN Thread     ─┐
 *   Network Thread ─┼─→ Log Queue ─→ CLI Thread → printf()
 *   MM2 Thread     ─┘
 *
 * Benefits:
 * - Zero I/O blocking in critical paths
 * - Diagnostic messages never slow down processing
 * - Prevents printf() serialization bottleneck
 * - Queue depth indicates logging pressure
 */

#ifndef ASYNC_LOG_QUEUE_H
#define ASYNC_LOG_QUEUE_H

#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <time.h>

/******************************************************
 *                    Constants
 ******************************************************/

#define LOG_MSG_MAX_LENGTH          256     /**< Max length of single log message */
#define LOG_QUEUE_CAPACITY          10000   /**< Number of log messages (2.5MB) */

/******************************************************
 *                    Structures
 ******************************************************/

/**
 * @brief Single log message entry
 */
typedef struct {
    struct timespec timestamp;              /**< When message was logged */
    uint8_t severity;                       /**< 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR */
    char message[LOG_MSG_MAX_LENGTH];       /**< Pre-formatted message */
} log_message_t;

/**
 * @brief Async log queue structure
 *
 * Ring buffer for log messages. Can be lock-free (atomics) or
 * mutex-protected depending on platform support.
 */
typedef struct {
    log_message_t *messages;                /**< Ring buffer of messages */
    uint32_t capacity;                      /**< Total capacity */

    /* Ring buffer indices */
    volatile uint32_t head;                 /**< Write index (producer) */
    volatile uint32_t tail;                 /**< Read index (consumer) */
    volatile uint32_t count;                /**< Current message count */

    /* Synchronization */
    pthread_mutex_t mutex;                  /**< Mutex for thread safety */

    /* Statistics */
    uint64_t total_enqueued;                /**< Total messages enqueued */
    uint64_t total_dequeued;                /**< Total messages dequeued */
    uint64_t total_dropped;                 /**< Messages dropped (queue full) */
    uint32_t max_depth;                     /**< Peak queue depth */

    /* Overflow handling */
    unsigned int drop_on_overflow : 1;      /**< Drop oldest or newest on overflow */
} async_log_queue_t;

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Initialize async log queue
 *
 * @param queue Pointer to queue structure
 * @param capacity Number of log messages to buffer
 * @return IMX_SUCCESS or error code
 */
imx_result_t async_log_queue_init(async_log_queue_t *queue, uint32_t capacity);

/**
 * @brief Enqueue a log message (non-blocking)
 *
 * Formats message with vsnprintf and adds to queue.
 * If queue is full, drops message and increments drop counter.
 * NEVER BLOCKS ON I/O.
 *
 * @param queue Pointer to queue
 * @param severity Message severity (0-3)
 * @param format Printf-style format string
 * @param args Variable argument list
 * @return IMX_SUCCESS or IMX_QUEUE_FULL
 */
imx_result_t async_log_enqueue(async_log_queue_t *queue,
                                uint8_t severity,
                                const char *format,
                                va_list args);

/**
 * @brief Dequeue and print log messages (blocking OK)
 *
 * Called from CLI thread. Prints up to max_count messages.
 * Can block on printf() since this runs in CLI thread.
 *
 * @param queue Pointer to queue
 * @param max_count Maximum messages to print (0 = all available)
 * @return Number of messages printed
 */
uint32_t async_log_flush(async_log_queue_t *queue, uint32_t max_count);

/**
 * @brief Get queue statistics
 *
 * @param queue Pointer to queue
 * @param depth [out] Current depth
 * @param dropped [out] Total dropped
 * @return None
 */
void async_log_get_stats(async_log_queue_t *queue,
                         uint32_t *depth,
                         uint64_t *dropped);

/**
 * @brief Destroy async log queue
 *
 * @param queue Pointer to queue
 * @return None
 */
void async_log_destroy(async_log_queue_t *queue);

#endif /* ASYNC_LOG_QUEUE_H */
```

### 2.2: Implement Async Log Queue

**New File**: `iMatrix/cli/async_log_queue.c`

**Implementation** (using template structure):
```c
/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 */

/**
 * @file async_log_queue.c
 * @brief Asynchronous logging queue implementation
 * @date November 7, 2025
 * @author Greg Phillips
 *
 * Implements non-blocking log message queuing to prevent I/O blocking
 * in critical performance paths (CAN processing, network handling).
 *
 * @version 1.0
 * @bug None known
 * @todo Performance testing under load
 * @warning Queue drops messages when full - monitor drop count
 */

#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <time.h>

#include "async_log_queue.h"
#include "common.h"

/******************************************************
 *               Global Variables
 ******************************************************/

/* Single global log queue instance */
static async_log_queue_t g_log_queue;
static bool g_log_queue_initialized = false;

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Initialize async log queue
 *
 * Allocates ring buffer and initializes synchronization primitives.
 *
 * @param queue Pointer to queue structure
 * @param capacity Number of log messages to buffer
 * @return IMX_SUCCESS or IMX_ERROR
 */
imx_result_t async_log_queue_init(async_log_queue_t *queue, uint32_t capacity)
{
    if (queue == NULL || capacity == 0) {
        return IMX_ERROR;
    }

    /* Allocate message buffer */
    queue->messages = (log_message_t *)malloc(capacity * sizeof(log_message_t));
    if (queue->messages == NULL) {
        return IMX_ERROR;
    }

    /* Initialize mutex */
    if (pthread_mutex_init(&queue->mutex, NULL) != 0) {
        free(queue->messages);
        return IMX_ERROR;
    }

    /* Initialize queue state */
    queue->capacity = capacity;
    queue->head = 0;
    queue->tail = 0;
    queue->count = 0;

    /* Initialize statistics */
    queue->total_enqueued = 0;
    queue->total_dequeued = 0;
    queue->total_dropped = 0;
    queue->max_depth = 0;
    queue->drop_on_overflow = 1;  /* Drop oldest on overflow */

    return IMX_SUCCESS;
}

/**
 * @brief Enqueue a log message (non-blocking, fast)
 *
 * Formats message and adds to queue. If queue is full, drops message.
 * Uses mutex for thread safety - very brief lock (just update indices).
 *
 * @param queue Pointer to queue
 * @param severity Message severity
 * @param format Printf-style format
 * @param args Variable args
 * @return IMX_SUCCESS or IMX_QUEUE_FULL
 */
imx_result_t async_log_enqueue(async_log_queue_t *queue,
                                uint8_t severity,
                                const char *format,
                                va_list args)
{
    if (queue == NULL || format == NULL) {
        return IMX_ERROR;
    }

    /* Pre-format message (before lock) */
    char formatted[LOG_MSG_MAX_LENGTH];
    vsnprintf(formatted, sizeof(formatted), format, args);

    /* Get timestamp (before lock) */
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);

    pthread_mutex_lock(&queue->mutex);

    /* Check if queue is full */
    if (queue->count >= queue->capacity) {
        /* Queue overflow - drop message */
        queue->total_dropped++;
        pthread_mutex_unlock(&queue->mutex);
        return IMX_QUEUE_FULL;
    }

    /* Add to queue */
    log_message_t *entry = &queue->messages[queue->head];
    entry->timestamp = ts;
    entry->severity = severity;
    strncpy(entry->message, formatted, sizeof(entry->message) - 1);
    entry->message[sizeof(entry->message) - 1] = '\0';

    /* Update indices */
    queue->head = (queue->head + 1) % queue->capacity;
    queue->count++;
    queue->total_enqueued++;

    /* Track peak */
    if (queue->count > queue->max_depth) {
        queue->max_depth = queue->count;
    }

    pthread_mutex_unlock(&queue->mutex);

    return IMX_SUCCESS;
}

/**
 * @brief Dequeue and print log messages
 *
 * Called from CLI thread. Can block on printf() since this is
 * the intended I/O thread.
 *
 * @param queue Pointer to queue
 * @param max_count Max messages to print (0 = all)
 * @return Number printed
 */
uint32_t async_log_flush(async_log_queue_t *queue, uint32_t max_count)
{
    if (queue == NULL) {
        return 0;
    }

    uint32_t printed = 0;
    uint32_t target = (max_count == 0) ? queue->capacity : max_count;

    while (printed < target) {
        pthread_mutex_lock(&queue->mutex);

        /* Check if empty */
        if (queue->count == 0) {
            pthread_mutex_unlock(&queue->mutex);
            break;
        }

        /* Dequeue message */
        log_message_t entry = queue->messages[queue->tail];  /* Copy */
        queue->tail = (queue->tail + 1) % queue->capacity;
        queue->count--;
        queue->total_dequeued++;

        pthread_mutex_unlock(&queue->mutex);

        /* Print (outside lock - can block) */
        printf("[%ld.%03ld] %s",
               (long)entry.timestamp.tv_sec,
               entry.timestamp.tv_nsec / 1000000,
               entry.message);

        printed++;
    }

    return printed;
}

/**
 * @brief Get queue statistics
 */
void async_log_get_stats(async_log_queue_t *queue,
                         uint32_t *depth,
                         uint64_t *dropped)
{
    if (queue == NULL) {
        return;
    }

    pthread_mutex_lock(&queue->mutex);

    if (depth) *depth = queue->count;
    if (dropped) *dropped = queue->total_dropped;

    pthread_mutex_unlock(&queue->mutex);
}

/**
 * @brief Initialize global log queue (called at startup)
 */
imx_result_t init_global_log_queue(void)
{
    if (g_log_queue_initialized) {
        return IMX_SUCCESS;  /* Already initialized */
    }

    imx_result_t result = async_log_queue_init(&g_log_queue, LOG_QUEUE_CAPACITY);
    if (result == IMX_SUCCESS) {
        g_log_queue_initialized = true;
    }

    return result;
}

/**
 * @brief Get global log queue instance
 */
async_log_queue_t* get_global_log_queue(void)
{
    return g_log_queue_initialized ? &g_log_queue : NULL;
}
```

### 2.3: Modify imx_cli_log_printf to Use Queue

**File**: Find current implementation first

**Search for**: `imx_cli_log_printf` implementation

**Current Implementation** (likely in `cli/interface.c` or similar):
```c
void imx_cli_log_printf(bool add_time, const char *format, ...)
{
    va_list args;
    va_start(args, format);

    if (add_time) {
        /* Add timestamp */
        imx_time_t current_time;
        imx_time_get_time(&current_time);
        printf("[%0.4f] ", (float)current_time / 1000.0);
    }

    vprintf(format, args);  ← BLOCKS ON I/O!
    va_end(args);
}
```

**AFTER (Modified)**:
```c
/**
 * @brief Log message with optional timestamp (ASYNC version)
 *
 * CRITICAL CHANGE: Instead of printing directly, enqueues message
 * to async log queue. CLI thread dequeues and prints asynchronously.
 *
 * This prevents I/O blocking in performance-critical threads.
 *
 * @param add_time Whether to include timestamp (queue adds its own)
 * @param format Printf-style format string
 * @param ... Variable arguments
 * @return None
 */
void imx_cli_log_printf(bool add_time, const char *format, ...)
{
    /* Check if async logging is enabled */
    extern async_log_queue_t* get_global_log_queue(void);
    async_log_queue_t *log_queue = get_global_log_queue();

    if (log_queue != NULL) {
        /* ASYNC PATH: Enqueue to log queue (non-blocking) */
        va_list args;
        va_start(args, format);

        /* Enqueue handles formatting and timestamps internally */
        async_log_enqueue(log_queue, 1, format, args);  /* severity=1 (INFO) */

        va_end(args);
    } else {
        /* FALLBACK: Direct print if queue not initialized yet */
        va_list args;
        va_start(args, format);

        if (add_time) {
            imx_time_t current_time;
            imx_time_get_time(&current_time);
            printf("[%0.4f] ", (float)current_time / 1000.0);
        }

        vprintf(format, args);
        va_end(args);
    }
}
```

**Compatibility**:
- ✅ No API changes (same function signature)
- ✅ Fallback to direct print if queue not ready
- ✅ All existing PRINTF() macros work unchanged

### 2.4: Add Log Queue Processing to Main Loop

**File**: Location where main loop processes CLI (likely `iMatrix/imatrix_interface.c` or Fleet-Connect-1)

**Add to main loop** (every cycle or every 100ms):
```c
void main_loop_iteration(void)
{
    /* ... existing main loop code ... */

    /* Process network */
    process_network();

    /* Process uploads */
    imatrix_upload(current_time);

    /* NEW: Flush async log queue (print up to 100 messages per cycle) */
    extern async_log_queue_t* get_global_log_queue(void);
    async_log_queue_t *log_queue = get_global_log_queue();
    if (log_queue != NULL) {
        async_log_flush(log_queue, 100);  /* Print up to 100 logs per cycle */
    }

    /* ... rest of main loop ... */
}
```

**Considerations**:
- Flush 100 messages per cycle (adjust based on cycle time)
- If log queue fills, messages drop (monitored via stats)
- Can add warning if queue depth > 80%

### 2.5: Initialize Log Queue at Startup

**File**: `iMatrix/imatrix_interface.c` (in `imatrix_start()`)

```c
void imatrix_start(void)
{
    /* ... existing initialization ... */

    /* NEW: Initialize async log queue EARLY (before other subsystems) */
    extern imx_result_t init_global_log_queue(void);
    if (init_global_log_queue() != IMX_SUCCESS) {
        printf("WARNING: Failed to initialize async log queue - using direct logging\r\n");
        /* Continue anyway - will fall back to direct printing */
    } else {
        printf("Async log queue initialized (%u message capacity)\r\n", LOG_QUEUE_CAPACITY);
    }

    /* ... rest of initialization ... */
}
```

### 2.6: Build and Test Stage 2

**Build**:
```bash
make clean
make -j$(nproc)
```

**Test Async Logging**:
```bash
./imatrix_gateway > logs/stage2_test.txt 2>&1 &

# Generate CAN traffic
# Watch for:
# 1. Logs still appear (async printing works)
# 2. No "WARNING: Log queue full" (unless extreme load)
# 3. CAN performance improved (no printf blocking)

# Check log queue stats (add CLI command):
> logstats
# Should show:
#   Depth: < 1000 (queue not filling up)
#   Dropped: 0 (no log drops)
```

**Success Criteria for Stage 2**:
- ✅ Logs print asynchronously (appear with slight delay OK)
- ✅ CAN drop rate further reduced (printf no longer blocking)
- ✅ Log queue depth < 50%
- ✅ Zero log messages dropped

---

## 📋 STAGE 3: Dedicated CAN Processing Thread (DECOUPLING)

**Goal**: Remove CAN processing from main loop entirely
**Time**: 6 hours implementation + 3 hours testing
**Risk**: MEDIUM-HIGH (threading, synchronization)

### 3.1: Design Thread Architecture

**New Threads**:
1. **TCP Server Thread** (already exists in can_server.c)
   - Receives CAN frames from network
   - Parses and enqueues

2. **CAN Processing Thread** (NEW)
   - Dedicated thread for dequeuing and processing
   - Runs continuously in while loop
   - No main loop dependency

3. **Main Loop Thread** (existing)
   - Network, uploads, other tasks
   - Flushes log queue
   - No CAN processing

### 3.2: Create CAN Processing Thread

**New Function**: `iMatrix/canbus/can_process.c` (or new file `can_processing_thread.c`)

```c
/**
 * @brief CAN processing thread entry point
 *
 * Dedicated thread for continuous CAN message processing.
 * Runs independently of main loop to prevent CAN bursts from
 * blocking other critical tasks.
 *
 * @param arg Thread argument (unused)
 * @return NULL
 */
static void* can_processing_thread_func(void *arg)
{
    UNUSED_PARAMETER(arg);

    /* Thread setup */
    pthread_setname_np(pthread_self(), "can_process");

    /* Processing loop */
    while (!g_can_shutdown_flag) {
        imx_time_t current_time;
        imx_time_get_time(&current_time);

        /* Process CAN queues (dequeue + process + return) */
        process_can_queues(current_time);

        /* Update CAN statistics */
        imx_update_can_statistics(current_time);

        /* Sleep briefly to avoid burning CPU */
        struct timespec sleep_time = {0, 1000000};  /* 1ms */
        nanosleep(&sleep_time, NULL);
    }

    return NULL;
}

/**
 * @brief Start CAN processing thread
 *
 * Creates dedicated thread for CAN message processing.
 *
 * @return true if successful, false on error
 */
bool start_can_processing_thread(void)
{
    static pthread_t can_process_thread;

    g_can_shutdown_flag = false;

    if (pthread_create(&can_process_thread, NULL, can_processing_thread_func, NULL) != 0) {
        PRINTF("[CAN PROC] Failed to create processing thread\r\n");
        return false;
    }

    PRINTF("[CAN PROC] Processing thread started\r\n");
    return true;
}

/**
 * @brief Stop CAN processing thread
 *
 * Signals thread to exit and waits for completion.
 *
 * @return None
 */
void stop_can_processing_thread(void)
{
    g_can_shutdown_flag = true;
    /* Thread will exit on next iteration */
}
```

### 3.3: Remove CAN Processing from Main Loop

**File**: Search for where `process_can_queues()` is currently called

**BEFORE**:
```c
void main_loop_iteration(void)
{
    /* ... */

    /* Process CAN queues */
    process_can_queues(current_time);  ← REMOVE THIS!
    imx_update_can_statistics(current_time);  ← REMOVE THIS!

    /* ... */
}
```

**AFTER**:
```c
void main_loop_iteration(void)
{
    /* ... */

    /* CAN processing now runs in dedicated thread - removed from here */
    /* (CAN thread calls process_can_queues() continuously) */

    /* ... */
}
```

### 3.4: Start Thread in CAN Initialization

**File**: `iMatrix/canbus/can_utils.c` or `can_process.c`

**In `setup_can_bus()` or after CAN initialization**:
```c
bool setup_can_bus(void) {
    /* ... existing setup ... */

    /* Initialize ring buffers */
    can_ring_buffer_init(&can0_ring, ...);
    can_ring_buffer_init(&can1_ring, ...);
    can_ring_buffer_init(&can2_ring, ...);

    /* Initialize unified queue */
    unified_queue_init(&unified_queue, UNIFIED_QUEUE_SIZE);

    /* NEW: Start dedicated CAN processing thread */
    if (!start_can_processing_thread()) {
        PRINTF("[CAN] ERROR: Failed to start processing thread\r\n");
        return false;
    }

    /* ... */
    return true;
}
```

### 3.5: Test Stage 3

**Verification**:
```bash
# Check threads are running
ps -T -p $(pidof imatrix_gateway)
# Should show multiple threads including "can_process"

# Check CPU usage per thread
top -H -p $(pidof imatrix_gateway)
# can_process thread should show CPU usage

# Monitor CAN performance
> can server
# Should show:
# - Drop rate < 5%
# - Processing completely decoupled
```

**Success Criteria for Stage 3**:
- ✅ CAN thread runs independently
- ✅ Main loop no longer blocked by CAN bursts
- ✅ Drop rate < 5%
- ✅ Other subsystems (network, upload) remain responsive

---

## 📋 STAGE 4: Advanced Optimizations (IF NEEDED)

**Goal**: Achieve < 1% drops, handle 3,000+ fps
**Time**: 8 hours implementation + 4 hours testing
**Risk**: HIGH (algorithmic changes)

### 4.1: O(1) Ring Buffer Allocation

**Problem**: Current `can_ring_buffer_alloc()` uses O(n) linear search

**File**: `iMatrix/canbus/can_ring_buffer.h`

**BEFORE**:
```c
typedef struct {
    uint16_t head;
    uint16_t tail;
    uint16_t free_count;
    uint16_t max_size;
    can_msg_t *pool;
    bool *in_use;
} can_ring_buffer_t;
```

**AFTER**:
```c
typedef struct {
    uint16_t head;
    uint16_t tail;
    uint16_t free_count;
    uint16_t max_size;
    can_msg_t *pool;
    bool *in_use;

    /* NEW: Free list for O(1) allocation */
    uint16_t *free_list;      /**< Stack of free indices */
    uint16_t free_list_top;   /**< Top of free stack (next to pop) */
} can_ring_buffer_t;
```

**File**: `iMatrix/canbus/can_ring_buffer.c`

**Modified Initialization**:
```c
void can_ring_buffer_init(can_ring_buffer_t *ring, can_msg_t *pool, bool *in_use, uint16_t size)
{
    /* ... existing init ... */

    /* NEW: Allocate and initialize free list */
    ring->free_list = (uint16_t *)malloc(size * sizeof(uint16_t));
    if (ring->free_list == NULL) {
        /* Handle error */
        return;
    }

    /* Push all indices to free list */
    for (uint16_t i = 0; i < size; i++) {
        ring->free_list[i] = i;
    }
    ring->free_list_top = size;  /* Stack grows down from top */
}
```

**Modified Allocation** (O(1)):
```c
can_msg_t* can_ring_buffer_alloc(can_ring_buffer_t *ring)
{
    if (ring == NULL || ring->free_list_top == 0) {
        return NULL;  /* No free messages */
    }

    /* Pop from free list - O(1) operation */
    uint16_t index = ring->free_list[--ring->free_list_top];

    /* Mark as in use */
    ring->in_use[index] = true;
    ring->free_count--;

    /* Clear message */
    memset(&ring->pool[index], 0, sizeof(can_msg_t));

    return &ring->pool[index];
}
```

**Modified Free** (O(1)):
```c
bool can_ring_buffer_free(can_ring_buffer_t *ring, can_msg_t *msg)
{
    /* ... existing validation ... */

    uint16_t index = (uint16_t)(msg - ring->pool);

    /* Check if already free */
    if (!ring->in_use[index]) {
        return false;
    }

    /* Mark as free */
    ring->in_use[index] = false;
    ring->free_count++;

    /* Push to free list - O(1) operation */
    ring->free_list[ring->free_list_top++] = index;

    return true;
}
```

**Impact**:
- Allocation: O(n) → O(1)
- Critical with 4000 message buffers
- Worst case current: 4000 iterations
- New: 1 operation

### 4.2: Add Performance Instrumentation

**File**: `iMatrix/canbus/can_utils.c`

**Modified process_can_queues()**:
```c
void process_can_queues(imx_time_t current_time)
{
    can_msg_t *batch[MAX_BATCH_SIZE];
    uint32_t count;

    if (cb.cbs.process_rx_can_queue == true) {
        /* TIMING START */
        struct timespec start_time, end_time;
        clock_gettime(CLOCK_MONOTONIC, &start_time);

        /* Dequeue batch */
        count = unified_queue_dequeue_batch(&unified_queue, batch, MAX_BATCH_SIZE);

        /* Process each message */
        for (uint32_t i = 0; i < count; i++) {
            can_msg_t *can_msg_ptr = batch[i];

            process_rx_can_msg(can_msg_ptr->can_bus, current_time, can_msg_ptr);

            if (!return_to_source_pool(can_msg_ptr)) {
                PRINTF("[CAN BUS - Error returning message to pool]\r\n");
            }
        }

        /* TIMING END */
        clock_gettime(CLOCK_MONOTONIC, &end_time);

        /* Calculate elapsed time */
        uint64_t elapsed_ns = (end_time.tv_sec - start_time.tv_sec) * 1000000000ULL +
                              (end_time.tv_nsec - start_time.tv_nsec);
        uint32_t elapsed_us = elapsed_ns / 1000;

        /* Track performance statistics */
        static uint64_t total_messages = 0;
        static uint64_t total_time_us = 0;
        static uint32_t slow_batch_count = 0;

        total_messages += count;
        total_time_us += elapsed_us;

        /* Log slow batches */
        if (count > 0 && elapsed_us > 50000) {  /* > 50ms threshold */
            PRINTF("[CAN PERF] SLOW: %u messages in %u us (%.1f msg/ms)\r\n",
                   count, elapsed_us, (float)count * 1000 / elapsed_us);
            slow_batch_count++;
        }

        /* Periodic summary */
        if (total_messages > 10000) {
            float avg_msg_per_ms = (float)total_messages * 1000 / total_time_us;
            PRINTF("[CAN PERF] Average: %.1f msg/ms over %llu messages (%u slow batches)\r\n",
                   avg_msg_per_ms, total_messages, slow_batch_count);
            total_messages = 0;
            total_time_us = 0;
            slow_batch_count = 0;
        }
    }
}
```

---

## 📋 STAGE 5: Final Optimizations and Tuning

### 5.1: Batch Signal Extraction (If Needed)

**Current**: Process messages one at a time
**Proposed**: Extract signals from entire batch before writing to MM2

```c
void process_batch_optimized(can_msg_t **batch, uint32_t count)
{
    /* Phase 1: Extract all signals (no MM2 locking) */
    struct signal_extraction_result {
        uint32_t sensor_id;
        double value;
        imx_utc_time_ms_t timestamp;
    } results[MAX_BATCH_SIZE * 10];  /* Assume avg 10 signals per message */

    uint32_t total_signals = 0;
    for (uint32_t i = 0; i < count; i++) {
        total_signals += extract_signals_to_buffer(batch[i], &results[total_signals]);
    }

    /* Phase 2: Batch write to MM2 (single lock per sensor) */
    batch_write_signals_to_mm2(results, total_signals);
}
```

**Impact**: Reduces MM2 lock/unlock overhead

### 5.2: Processing Thread Priority

**Set thread priority** for better scheduling:
```c
bool start_can_processing_thread(void)
{
    pthread_attr_t attr;
    struct sched_param param;

    pthread_attr_init(&attr);
    pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_JOINABLE);

    /* Set realtime priority (if permissions allow) */
    param.sched_priority = sched_get_priority_max(SCHED_FIFO) - 10;  /* High but not highest */
    pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
    pthread_attr_setschedparam(&attr, &param);

    int result = pthread_create(&can_process_thread, &attr, can_processing_thread_func, NULL);

    pthread_attr_destroy(&attr);

    if (result == EPERM) {
        /* No permission for realtime - use normal priority */
        result = pthread_create(&can_process_thread, NULL, can_processing_thread_func, NULL);
    }

    return (result == 0);
}
```

---

## 📊 DETAILED VERIFICATION PROCEDURES

### After Stage 1: Buffer Increase

**Immediate Checks** (< 5 minutes):
```bash
# 1. Verify build
ls -lh build/imatrix_gateway
# Should be ~300KB larger

# 2. Check memory usage
./imatrix_gateway &
PID=$!
sleep 5
ps aux | grep $PID | awk '{print $6}'  # RSS in KB
# Should be +300-400KB higher
kill $PID
```

**Runtime Checks** (10 minutes):
```bash
# Start system
./imatrix_gateway > logs/stage1.txt 2>&1 &
PID=$!

# Monitor for 10 minutes with CAN traffic
for i in {1..10}; do
    sleep 60
    echo "Minute $i:" >> logs/stage1_stats.txt
    echo "can server" | nc localhost 23232 >> logs/stage1_stats.txt
done

kill $PID

# Analyze
grep "Dropped" logs/stage1_stats.txt
grep "Drop Rate" logs/stage1_stats.txt
grep "In Use" logs/stage1_stats.txt

# Success if:
# - Drop rate decreasing over time
# - Buffer usage < 70%
# - System stable
```

**Validation Metrics**:
```
BEFORE Stage 1:
  Dropped: 942,605 (90.5%)
  Drop Rate: 566 drops/sec
  Buffer: 92% full

AFTER Stage 1 (Expected):
  Dropped: < 200,000 (< 20%)
  Drop Rate: < 150 drops/sec
  Buffer: < 60% full
```

### After Stage 2: Async Logging

**Check Log Queue Stats**:
```bash
# In CLI:
> logstats

# Expected output:
# Async Log Queue Statistics:
#   Capacity: 10,000 messages
#   Current Depth: 234 (2.3%)
#   Total Enqueued: 45,623
#   Total Dequeued: 45,389
#   Total Dropped: 0
#   Max Depth: 1,023 (10.2%)
```

**Validation**:
- ✅ Log depth < 50% (not filling up)
- ✅ Dropped = 0 (no log loss)
- ✅ CAN drop rate further reduced

### After Stage 3: Processing Thread

**Check Thread Stats**:
```bash
# Verify thread exists
ps -T -p $(pidof imatrix_gateway) | grep can_process
# Should show thread

# Check CPU per thread
top -H -p $(pidof imatrix_gateway)
# can_process should show 5-20% CPU

# Check context switches
pidstat -t -p $(pidof imatrix_gateway) 1 10
# Monitor voluntary/involuntary context switches
```

**Validation**:
- ✅ CAN thread running continuously
- ✅ Main loop not blocked by CAN
- ✅ Drop rate < 5%

---

## ⚠️ ROLLBACK PROCEDURES

### Rollback Stage 1:
```bash
cd iMatrix
git diff canbus/can_utils.c canbus/can_unified_queue.h

# If issues, revert constants:
# CAN_MSG_POOL_SIZE: 4000 → 500
# UNIFIED_QUEUE_SIZE: 12000 → 1500
# MAX_BATCH_SIZE: 200 → 100

git checkout canbus/can_utils.c canbus/can_unified_queue.h
make clean && make
```

### Rollback Stage 2:
```bash
# Revert async logging
git checkout cli/async_log_queue.c cli/async_log_queue.h cli/interface.c

# Or disable via flag:
# In init: skip init_global_log_queue()
# imx_cli_log_printf will fall back to direct print
```

### Rollback Stage 3:
```bash
# Don't start processing thread
# In setup_can_bus(), comment out:
// start_can_processing_thread();

# Restore process_can_queues() call to main loop
```

---

## 🎯 RECOMMENDED IMPLEMENTATION SEQUENCE

### Week 1: Critical Fix
- **Day 1**: Implement Stage 1 (buffer increase)
- **Day 2**: Test Stage 1, validate < 20% drops
- **Day 3**: Document Stage 1 results

### Week 2: Performance Enhancement
- **Day 1-2**: Implement Stage 2 (async logging)
- **Day 3**: Test Stage 2, validate no log loss
- **Day 4**: Implement Stage 3 (processing thread)
- **Day 5**: Test Stage 3, validate < 5% drops

### Week 3: Optimization (If Needed)
- **Day 1-2**: Implement Stage 4.1 (O(1) allocation)
- **Day 3**: Add instrumentation (Stage 4.2)
- **Day 4-5**: Test and tune

---

**Status**: Plan updated with threading and async logging architecture.

**Next**: Awaiting your approval to proceed with staged implementation.

**Recommendation**: Implement Stages 1+2 together (buffers + async logging) for maximum immediate impact.