# Option B Implementation Plan: All Startup Messages to Log File

**Date**: 2026-01-03
**Author**: Claude Code
**Status**: DRAFT
**Branch**: feature/debug_initialization (iMatrix and Fleet-Connect-1)

---

## Executive Summary

This plan converts ALL startup messages to use the filesystem logging system, ensuring no messages appear on stdout during normal operation. The key innovation is an **early message buffer** that captures messages generated before the filesystem logger is initialized, then flushes them to the log file once initialization completes.

## Problem Statement

The current system has multiple message output paths that bypass the logging system:

| Category | Count | Files Affected |
|----------|-------|----------------|
| `printf()` in Fleet-Connect-1/init/ | ~204 | 8 files |
| `imx_cli_print()` in Fleet-Connect-1/init/ | ~158 | 4 files |
| `printf()` in iMatrix/cli/ | ~291 | 27 files |
| `printf()` in iMatrix/device/ | ~80 | 6 files |
| `printf()` in filesystem_logger.c | ~26 | 1 file |
| Early init `printf()` in imatrix_interface.c | ~100+ | 1 file |

**Root Cause**: Messages generated before `fs_logger_init()` completes cannot use the logging system.

## Solution Architecture

### 1. Early Message Buffer

A static ring buffer that captures all startup messages before the filesystem logger is ready. Once the logger initializes, the buffer is flushed to the log file.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MESSAGE FLOW DIAGRAM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BEFORE fs_logger_init()        AFTER fs_logger_init()              │
│  ─────────────────────          ────────────────────                │
│                                                                      │
│  imx_startup_log()              imx_startup_log()                   │
│        │                              │                              │
│        ▼                              ▼                              │
│  ┌─────────────┐               ┌─────────────────┐                  │
│  │ Early       │               │ fs_logger_is_   │                  │
│  │ Message     │               │ active() ?      │                  │
│  │ Buffer      │               └────────┬────────┘                  │
│  │ (ring buf)  │                   yes  │  no                       │
│  └─────────────┘                        │   │                       │
│        │                                ▼   ▼                       │
│        │                        ┌───────────────┐  ┌─────────────┐  │
│        │                        │ fs_logger_    │  │ Early       │  │
│        │                        │ write()       │  │ Buffer      │  │
│        │                        │ (to file)     │  │ (fallback)  │  │
│        │                        └───────────────┘  └─────────────┘  │
│        │                                                            │
│        │  ON fs_logger_init() SUCCESS:                              │
│        │  ────────────────────────────                              │
│        └──────────────────▶ Flush buffer ──▶ fs_logger_write()      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. New API Functions

#### `imx_startup_log(bool print_time, const char *format, ...)`

A new function specifically for startup messages that:
1. Checks if filesystem logger is active
2. If YES: Calls `imx_cli_log_printf()` (writes to file)
3. If NO: Buffers message in early message buffer

#### `imx_startup_log_flush()`

Called once immediately after `fs_logger_init()` succeeds:
1. Writes all buffered messages to the log file
2. Clears the buffer
3. Sets a flag indicating early buffer is no longer needed

### 3. Initialization Sequence

```c
void imatrix_start(void)
{
    // 1. Initialize early buffer (static, no malloc needed)
    early_buffer_init();  // Optional - static init is fine

    // 2. Initialize async log queue
    if (init_global_log_queue() != 0) {
        imx_startup_log(true, "WARNING: Failed to init async log queue\r\n");
    } else {
        imx_startup_log(true, "Async log queue initialized\r\n");
    }

    // 3. Initialize filesystem logger
    if (fs_logger_init() != IMX_SUCCESS) {
        imx_startup_log(true, "WARNING: Failed to init filesystem logger\r\n");
    } else {
        // 4. FLUSH EARLY BUFFER - Critical step!
        imx_startup_log_flush();  // Writes all buffered messages to file

        imx_cli_log_printf(true, "Filesystem logger initialized\r\n");
    }

    // 5. All subsequent messages use imx_cli_log_printf()
    imx_cli_log_printf(true, "Lock acquired successfully...\r\n");
}
```

---

## Detailed Implementation Plan

### Phase 1: Early Message Buffer Implementation

**File**: `iMatrix/cli/early_message_buffer.c` (NEW)
**Header**: `iMatrix/cli/early_message_buffer.h` (NEW)

#### Data Structures

```c
/* Maximum messages before filesystem logger starts */
#define EARLY_BUFFER_CAPACITY 100

/* Maximum length per message (same as LOG_MSG_MAX_LENGTH) */
#define EARLY_MSG_MAX_LENGTH 512

/* Early message entry */
typedef struct {
    char message[EARLY_MSG_MAX_LENGTH];  /* Pre-formatted message with timestamp */
    bool valid;                           /* Entry contains valid data */
} early_message_t;

/* Early buffer state */
typedef struct {
    early_message_t messages[EARLY_BUFFER_CAPACITY];
    uint32_t head;              /* Next write position */
    uint32_t count;             /* Messages in buffer */
    uint32_t dropped;           /* Messages dropped due to overflow */
    bool flushed;               /* Buffer has been flushed to file */
} early_buffer_t;

/* Static instance - no malloc required */
static early_buffer_t g_early_buffer = {0};
```

#### Functions

| Function | Description |
|----------|-------------|
| `early_buffer_init()` | Initialize buffer (optional, zero-init works) |
| `early_buffer_add()` | Add message to buffer |
| `early_buffer_flush()` | Write all messages to filesystem logger |
| `early_buffer_get_stats()` | Get drop count and message count |
| `early_buffer_is_flushed()` | Check if buffer has been flushed |

#### Implementation

```c
/**
 * @brief Add message to early buffer
 *
 * Thread-safe (uses simple spin check, acceptable pre-init).
 * If buffer full, drops oldest message.
 *
 * @param[in] message Pre-formatted message string
 * @return true on success, false if dropped
 */
bool early_buffer_add(const char *message)
{
    if (g_early_buffer.flushed) {
        /* Buffer already flushed, shouldn't be calling this */
        return false;
    }

    if (g_early_buffer.count >= EARLY_BUFFER_CAPACITY) {
        /* Buffer full - drop oldest (overwrite at tail) */
        g_early_buffer.dropped++;
        /* Continue to overwrite oldest */
    }

    uint32_t idx = g_early_buffer.head % EARLY_BUFFER_CAPACITY;
    strncpy(g_early_buffer.messages[idx].message, message,
            EARLY_MSG_MAX_LENGTH - 1);
    g_early_buffer.messages[idx].message[EARLY_MSG_MAX_LENGTH - 1] = '\0';
    g_early_buffer.messages[idx].valid = true;

    g_early_buffer.head++;
    if (g_early_buffer.count < EARLY_BUFFER_CAPACITY) {
        g_early_buffer.count++;
    }

    return true;
}

/**
 * @brief Flush early buffer to filesystem logger
 *
 * Called once after fs_logger_init() succeeds.
 * Writes all buffered messages in order to log file.
 */
void early_buffer_flush(void)
{
    if (g_early_buffer.flushed) {
        return;  /* Already flushed */
    }

    /* Calculate starting index for in-order output */
    uint32_t start_idx;
    if (g_early_buffer.count >= EARLY_BUFFER_CAPACITY) {
        /* Buffer wrapped - start from oldest */
        start_idx = g_early_buffer.head % EARLY_BUFFER_CAPACITY;
    } else {
        /* Buffer didn't wrap - start from 0 */
        start_idx = 0;
    }

    /* Write to log header */
    fs_logger_write("[EARLY_BUFFER] === Startup messages captured before logger init ===\n");

    if (g_early_buffer.dropped > 0) {
        char drop_msg[128];
        snprintf(drop_msg, sizeof(drop_msg),
                "[EARLY_BUFFER] WARNING: %u messages dropped due to buffer overflow\n",
                g_early_buffer.dropped);
        fs_logger_write(drop_msg);
    }

    /* Write all buffered messages in order */
    for (uint32_t i = 0; i < g_early_buffer.count; i++) {
        uint32_t idx = (start_idx + i) % EARLY_BUFFER_CAPACITY;
        if (g_early_buffer.messages[idx].valid) {
            fs_logger_write(g_early_buffer.messages[idx].message);
        }
    }

    fs_logger_write("[EARLY_BUFFER] === End of startup messages ===\n");

    g_early_buffer.flushed = true;
}
```

### Phase 2: imx_startup_log() Implementation

**File**: `iMatrix/cli/interface.c` (MODIFY)

#### Function Implementation

```c
/**
 * @brief Log startup message (before or after filesystem logger init)
 *
 * This function should be used for ALL startup messages instead of printf().
 * It automatically handles the pre-init case by buffering messages.
 *
 * @param[in] print_time If true, prepend timestamp to message
 * @param[in] format Printf-style format string
 * @param[in] ... Format arguments
 */
void imx_startup_log(bool print_time, const char *format, ...)
{
    char buffer[512];
    va_list args;

    va_start(args, format);
    vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);

    if (fs_logger_is_active()) {
        /* Filesystem logger is ready - use normal logging */
        if (print_time) {
            imx_cli_log_printf(true, "%s", buffer);
        } else {
            imx_cli_log_printf(false, "%s", buffer);
        }
    } else {
        /* Filesystem logger not ready - buffer the message */
        char timestamped[600];

        if (print_time) {
            /* Add timestamp prefix */
            uint32_t uptime_ms = imx_get_system_uptime_ms();
            uint32_t hours = (uptime_ms / 3600000) % 24;
            uint32_t mins = (uptime_ms / 60000) % 60;
            uint32_t secs = (uptime_ms / 1000) % 60;
            uint32_t msecs = uptime_ms % 1000;

            snprintf(timestamped, sizeof(timestamped), "[%02u:%02u:%02u.%03u] %s",
                    hours, mins, secs, msecs, buffer);
        } else {
            strncpy(timestamped, buffer, sizeof(timestamped) - 1);
            timestamped[sizeof(timestamped) - 1] = '\0';
        }

        early_buffer_add(timestamped);
    }
}

/**
 * @brief Flush early startup buffer to filesystem log
 *
 * Must be called immediately after fs_logger_init() succeeds.
 */
void imx_startup_log_flush(void)
{
    early_buffer_flush();
}
```

### Phase 3: Convert filesystem_logger.c printf() Calls

**File**: `iMatrix/cli/filesystem_logger.c`

The filesystem logger itself cannot use the logging system (circular dependency). Instead, convert its printf() calls to use `imx_startup_log()` for pre-init messages and remove post-init console output.

#### Changes Required

| Line | Current | Change To |
|------|---------|-----------|
| 177 | `printf(FS_LOG_PREFIX "Failed to initialize log mutex\n");` | `imx_startup_log(true, FS_LOG_PREFIX "Failed to initialize log mutex\n");` |
| 183 | `printf(FS_LOG_PREFIX "Failed to initialize rotation mutex: %d\n", result);` | `imx_startup_log(true, FS_LOG_PREFIX "Failed to initialize rotation mutex: %d\n", result);` |
| 189 | `printf(FS_LOG_PREFIX "Failed to initialize rotation condition: %d\n", result);` | `imx_startup_log(true, FS_LOG_PREFIX "Failed to initialize rotation condition: %d\n", result);` |
| 198-199 | `printf(FS_LOG_PREFIX "Failed to create log directory...");` | `imx_startup_log(true, FS_LOG_PREFIX "Failed to create log directory...");` |
| 217 | `printf(FS_LOG_PREFIX "Rotated existing log to %s\n", rotated_name);` | Write directly to file (internal) |
| 219 | `printf(FS_LOG_PREFIX "Warning: Failed to rotate...");` | Write directly to file (internal) |
| 226 | `printf(FS_LOG_PREFIX "Failed to open log file...");` | `imx_startup_log(true, FS_LOG_PREFIX "Failed to open log file...");` |
| 254 | `printf(FS_LOG_PREFIX "Failed to create rotation thread: %d\n", result);` | `imx_startup_log(true, FS_LOG_PREFIX "Failed to create rotation thread: %d\n", result);` |
| 264 | `printf(FS_LOG_PREFIX "Initialized - logging to %s\n", full_path);` | REMOVE (log to file instead) |
| 284 | `printf(FS_LOG_PREFIX "Shutting down...\n");` | Log to file via `fs_logger_write()` |
| 323 | `printf(FS_LOG_PREFIX "Shutdown complete\n");` | REMOVE or log to file |

**Key Principle**: After initialization succeeds, the filesystem logger should NOT output to console - all its internal status messages should go to the log file.

### Phase 4: Convert imatrix_interface.c Early printf() Calls

**File**: `iMatrix/imatrix_interface.c`

#### Changes Required (Lines ~599-620)

```c
/* BEFORE */
if (init_global_log_queue() != 0) {
    printf("WARNING: Failed to initialize async log queue\r\r\n");
} else {
    printf("Async log queue initialized (%u message capacity)\r\r\n", LOG_QUEUE_CAPACITY);
}

if (fs_logger_init() != IMX_SUCCESS) {
    printf("WARNING: Failed to initialize filesystem logger\r\r\n");
}

/* AFTER */
if (init_global_log_queue() != 0) {
    imx_startup_log(true, "WARNING: Failed to initialize async log queue\r\n");
} else {
    imx_startup_log(true, "Async log queue initialized (%u message capacity)\r\n", LOG_QUEUE_CAPACITY);
}

if (fs_logger_init() != IMX_SUCCESS) {
    imx_startup_log(true, "WARNING: Failed to initialize filesystem logger\r\n");
} else {
    /* FLUSH EARLY BUFFER - All buffered messages now go to file */
    imx_startup_log_flush();

    imx_cli_log_printf(true, "Filesystem logger initialized (%s/%s)\r\n",
           FS_LOG_DIRECTORY, FS_LOG_FILENAME);
    // ... rest of init messages
}
```

### Phase 5: Convert imx_cli_print() to Use Logging System

**File**: `iMatrix/cli/interface.c`

The current `imx_cli_print()` function unconditionally outputs to stdout when `active_device == CONSOLE_OUTPUT && cli_enabled`. This needs to respect the quiet mode flag.

#### Current Implementation (Problem)

```c
if( active_device == CONSOLE_OUTPUT && cli_enabled == true )
    vprintf( (char *) format, args );  // ALWAYS outputs to stdout!
```

#### Modified Implementation

```c
if (active_device == CONSOLE_OUTPUT && cli_enabled == true) {
    /* Build message first */
    char message[512];
    va_list args_copy;
    va_copy(args_copy, args);
    vsnprintf(message, sizeof(message), format, args_copy);
    va_end(args_copy);

    /* Route through logging system */
    if (fs_logger_is_active()) {
        /* Write to filesystem log */
        fs_logger_write(message);

        /* Only output to console if in interactive mode */
        if (fs_logger_interactive_mode) {
            vprintf(format, args);
        }
    } else {
        /* Filesystem logger not ready - buffer the message */
        early_buffer_add(message);
    }
}
```

**Alternative Approach**: Change all startup `imx_cli_print()` calls to `imx_cli_log_printf()`. This is more surgical but requires identifying all ~158 calls in Fleet-Connect-1/init/.

### Phase 6: Convert Fleet-Connect-1/init/ printf() and imx_cli_print() Calls

**Scope**: ~362 calls across 8+ files

#### Files Requiring Changes

| File | printf | imx_cli_print | Total |
|------|--------|---------------|-------|
| `imx_client_init.c` | 21 | 140 | 161 |
| `config_print.c` | 134 | 0 | 134 |
| `init.c` | 27 | 13 | 40 |
| `local_heap.c` | 0 | 3 | 3 |
| `wrp_config.c` | 1 | 2 | 3 |
| Others (docs, headers) | 21 | 0 | 21 |

#### Conversion Strategy

**For startup messages** (displayed during initialization):
- Convert `printf()` → `imx_cli_log_printf(true, ...)`
- Convert `imx_cli_print()` → `imx_cli_log_printf(true, ...)`

**For option-triggered output** (like `-P` print config):
- Keep console output but also log to file
- Use `imx_cli_log_printf()` with `fs_logger_interactive_mode = true` for these cases

**Implementation Script** (semi-automated):
```bash
# Find and review all printf/imx_cli_print calls in startup path
grep -n "printf\|imx_cli_print" Fleet-Connect-1/init/*.c

# Use sed for bulk conversion (with manual review):
# sed -i 's/printf(/imx_cli_log_printf(true, /g' file.c
# sed -i 's/imx_cli_print(/imx_cli_log_printf(true, /g' file.c
```

---

## Testing Plan

### Unit Tests

1. **Early Buffer Tests**
   - Verify messages are stored correctly
   - Verify buffer doesn't overflow (drops oldest when full)
   - Verify flush writes all messages in correct order
   - Verify dropped count is accurate

2. **imx_startup_log() Tests**
   - Verify routing to buffer when logger not ready
   - Verify routing to file when logger is ready
   - Verify timestamps are correct

### Integration Tests

1. **Startup Sequence Test**
   ```bash
   # Start FC-1 with quiet mode (default)
   ./FC-1

   # Verify:
   # - No messages on stdout
   # - All messages in /var/log/fc-1.log
   # - Timestamps present on all messages
   # - Early buffer header present in log
   ```

2. **Interactive Mode Test**
   ```bash
   # Start FC-1 with interactive mode
   ./FC-1 -i

   # Verify:
   # - Messages appear on stdout
   # - Messages also in /var/log/fc-1.log
   ```

3. **Early Buffer Overflow Test**
   - Add 150 messages before fs_logger_init()
   - Verify only 100 messages are logged (capacity)
   - Verify drop count is logged (50 dropped)

4. **Crash Recovery Test**
   - Force crash during startup
   - Restart and verify log file intact
   - Verify no corruption

### Target Device Tests

Execute on actual iMX6 target via `fc1` script:

```bash
# Deploy and restart
fc1 deploy && fc1 restart

# Check log file
fc1 cmd "cat /var/log/fc-1.log | head -100"

# Verify no console output in service log
fc1 cmd "sv status FC-1"
```

---

## File Changes Summary

### New Files

| File | Description |
|------|-------------|
| `iMatrix/cli/early_message_buffer.c` | Early buffer implementation |
| `iMatrix/cli/early_message_buffer.h` | Early buffer API header |

### Modified Files

| File | Change Type | Estimated Changes |
|------|-------------|-------------------|
| `iMatrix/cli/interface.c` | Add imx_startup_log(), modify imx_cli_print() | +50 lines |
| `iMatrix/cli/interface.h` | Add imx_startup_log() prototype | +5 lines |
| `iMatrix/cli/filesystem_logger.c` | Convert printf() calls | ~20 changes |
| `iMatrix/imatrix_interface.c` | Convert early printf() calls | ~10 changes |
| `Fleet-Connect-1/init/imx_client_init.c` | Convert 161 calls | ~161 changes |
| `Fleet-Connect-1/init/config_print.c` | Convert 134 printf() calls | ~134 changes |
| `Fleet-Connect-1/init/init.c` | Convert 40 calls | ~40 changes |
| `Fleet-Connect-1/init/local_heap.c` | Convert 3 calls | ~3 changes |
| `Fleet-Connect-1/init/wrp_config.c` | Convert 3 calls | ~3 changes |
| `Fleet-Connect-1/CMakeLists.txt` | Add early_message_buffer.c | ~1 change |

### CMakeLists.txt Updates

```cmake
# Add to iMatrix source list:
set(IMATRIX_CLI_SOURCES
    ${IMATRIX_DIR}/cli/interface.c
    ${IMATRIX_DIR}/cli/filesystem_logger.c
    ${IMATRIX_DIR}/cli/early_message_buffer.c   # NEW
    # ... other sources
)
```

---

## Rollback Procedure

If issues are discovered after deployment:

1. **Revert Feature Branch**
   ```bash
   cd iMatrix
   git checkout Aptera_1_Clean

   cd ../Fleet-Connect-1
   git checkout Aptera_1_Clean
   ```

2. **Rebuild and Redeploy**
   ```bash
   cd Fleet-Connect-1/build
   cmake .. && make -j4
   fc1 deploy && fc1 restart
   ```

3. **Verify Rollback**
   ```bash
   fc1 cmd "cat /var/log/fc-1.log | tail -20"
   ```

---

## Implementation Order

### Step 1: Create Early Buffer (Day 1)
- [ ] Create `early_message_buffer.h`
- [ ] Create `early_message_buffer.c`
- [ ] Add to CMakeLists.txt
- [ ] Test compilation

### Step 2: Add imx_startup_log() (Day 1)
- [ ] Add `imx_startup_log()` to interface.c
- [ ] Add `imx_startup_log_flush()` to interface.c
- [ ] Add prototypes to interface.h
- [ ] Test compilation

### Step 3: Modify Initialization (Day 1)
- [ ] Update imatrix_interface.c to use imx_startup_log()
- [ ] Add imx_startup_log_flush() call after fs_logger_init()
- [ ] Test on target

### Step 4: Convert filesystem_logger.c (Day 2)
- [ ] Convert all printf() calls
- [ ] Remove console output after init
- [ ] Test initialization

### Step 5: Modify imx_cli_print() (Day 2)
- [ ] Add logging system routing
- [ ] Respect quiet mode flag
- [ ] Test CLI functionality

### Step 6: Convert Fleet-Connect-1/init/ (Day 2-3)
- [ ] Convert imx_client_init.c (161 calls)
- [ ] Convert config_print.c (134 calls)
- [ ] Convert init.c (40 calls)
- [ ] Convert smaller files (9 calls)
- [ ] Build and test

### Step 7: Final Testing (Day 3)
- [ ] Run full test suite on target
- [ ] Verify no stdout during quiet mode
- [ ] Verify all messages in log file
- [ ] Stress test with rapid restarts

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Early buffer overflow | Low | Medium | 100 message capacity should be sufficient; drops oldest |
| Circular dependency | Medium | High | Early buffer has no dependencies; careful include order |
| Missing message conversion | Medium | Low | Grep search to verify all conversions |
| Performance impact | Low | Low | Buffer is static; no malloc during startup |
| Thread safety issues | Low | High | Early buffer accessed before threads start |

---

## Success Criteria

1. **No stdout output** when started without `-i` flag
2. **All startup messages** appear in `/var/log/fc-1.log`
3. **All messages have timestamps** in `[HH:MM:SS.mmm]` format
4. **Early buffer messages** clearly marked in log file
5. **No lost messages** - every startup message captured
6. **Interactive mode works** - messages appear on both stdout and log file when `-i` used
7. **No performance regression** - startup time unchanged (within 5%)
8. **Build succeeds** on all platforms

---

*Document created: 2026-01-03*
*Last updated: 2026-01-03*
