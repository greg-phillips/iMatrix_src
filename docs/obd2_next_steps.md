# OBD-II Additional Modes - Developer Next Steps Guide

**Date:** 2025-12-13
**Version:** 1.0
**Status:** Active Development
**Author:** Claude Code Analysis / Greg Phillips

---

## Table of Contents

1. [Overview](#1-overview)
2. [Current Implementation Status](#2-current-implementation-status)
3. [Source Code Reference](#3-source-code-reference)
4. [ISO-TP Transmit Layer](#4-iso-tp-transmit-layer)
5. [Remaining Tasks](#5-remaining-tasks)
6. [Testing Guide](#6-testing-guide)
7. [Code Patterns](#7-code-patterns)
8. [Build Instructions](#8-build-instructions)
9. [Related Documentation](#9-related-documentation)

---

## 1. Overview

This document provides comprehensive details for developers continuing work on the OBD-II additional modes implementation in Fleet-Connect-1. The core decoders for Modes 02, 03, 04, and 07 are complete and compiling. The ISO-TP transmit integration is complete.

### What's Been Implemented

| Mode | Description | Request | Response | Status |
|------|-------------|---------|----------|--------|
| 02 | Freeze Frame Data | `request_freeze_frame()` | `process_mode_02_freeze_frame()` | Complete |
| 03 | Stored DTCs | `request_stored_dtc()` | `process_mode_03_dtc()` | Complete |
| 04 | Clear DTCs | `request_clear_dtc()` | `process_mode_04_clear_dtc()` | Complete |
| 07 | Pending DTCs | `request_pending_dtc()` | `process_mode_07_dtc()` | Complete |

### What Remains

1. DTC persistent storage (flash save/load)
2. Additional CLI subcommand registration
3. Vehicle testing with real OBD-II responses
4. Mode 06 (On-board Monitoring) - Future

---

## 2. Current Implementation Status

### 2.1 Completed Items

- **Decoder Files Created:**
  - `decode_mode_02_freeze_frame.c/h` - Freeze frame data
  - `decode_mode_03_dtc.c/h` - DTC parsing (stored and pending)
  - `decode_mode_04_clear_dtc.c/h` - DTC clear handling

- **Mode Dispatch Integration:**
  - Response routing added to `i15765app.c`
  - All mode response bytes (0x42, 0x43, 0x44, 0x47) handled

- **ISO-TP Transmit Integration:**
  - All request functions use `i15765_tx_app()` for CAN transmission
  - Functional addressing (0x7DF broadcast) configured

- **CLI Commands Registered:**
  - `dtc` - DTC summary
  - `ff` - Freeze frame display
  - `cleardtc` - Vehicle DTC clear (Mode 04)

### 2.2 Not Yet Implemented

- DTC flash persistence (`imx_storage_write/read`)
- `dtc list` CLI subcommand registration
- `dtc clear` CLI subcommand (local clear)
- `ff request` CLI subcommand registration
- Vehicle testing validation

---

## 3. Source Code Reference

### 3.1 File Locations

```
Fleet-Connect-1/OBD2/
├── decode_mode_02_freeze_frame.c   # Mode 02 freeze frame decoder
├── decode_mode_02_freeze_frame.h   # Freeze frame structures/declarations
├── decode_mode_03_dtc.c            # Mode 03/07 DTC decoder + request functions
├── decode_mode_03_dtc.h            # DTC structures/declarations
├── decode_mode_04_clear_dtc.c      # Mode 04 clear DTC handler + request function
├── decode_mode_04_clear_dtc.h      # Clear DTC declarations
├── i15765.c                        # ISO-TP transport layer implementation
├── i15765.h                        # ISO-TP structures and declarations
├── i15765app.c                     # Application-level ISO-TP with mode dispatch
├── process_obd2.c                  # Main OBD2 state machine
└── process_obd2.h                  # OBD2 status structures
```

### 3.2 Key Data Structures

#### DTC Entry Structure (`decode_mode_03_dtc.h:97-105`)
```c
typedef struct {
    char code[DTC_CODE_LENGTH];     /**< DTC code string (e.g., "P0133") */
    dtc_system_t system;            /**< System type (P, C, B, U) */
    bool is_pending;                /**< True if from Mode 07 (pending) */
    uint8_t ecu_address;            /**< Source ECU address (0x00-0xFF) */
    uint32_t first_seen;            /**< Timestamp when first detected */
    uint32_t last_seen;             /**< Timestamp when last confirmed */
    uint8_t occurrence_count;       /**< Number of times this DTC has been seen */
} dtc_entry_t;
```

#### DTC Collection Structure (`decode_mode_03_dtc.h:110-117`)
```c
typedef struct {
    uint8_t count;                          /**< Number of valid DTCs */
    dtc_entry_t codes[MAX_DTC_CODES];       /**< Array of DTC entries */
    bool has_mil;                           /**< MIL (Check Engine Light) status */
    uint32_t last_query_time;               /**< Last time DTCs were queried */
    uint32_t last_clear_time;               /**< Last time DTCs were cleared */
    char vin[DTC_VIN_LENGTH];               /**< VIN associated with DTCs */
} dtc_collection_t;
```

#### Freeze Frame Structure (`decode_mode_02_freeze_frame.h:39-55`)
```c
typedef struct {
    bool valid;                     /**< True if frame contains valid data */
    char trigger_dtc[6];            /**< DTC that triggered the freeze */
    uint8_t frame_number;           /**< Frame number (0-255) */
    uint32_t capture_time;          /**< Time freeze frame was captured */
    float engine_load;              /**< Engine load % (PID 0x04) */
    int16_t coolant_temp;           /**< Coolant temp C (PID 0x05) */
    float fuel_trim_short_b1;       /**< Short term fuel trim % (PID 0x06) */
    float fuel_trim_long_b1;        /**< Long term fuel trim % (PID 0x07) */
    uint16_t rpm;                   /**< Engine RPM (PID 0x0C) */
    uint8_t vehicle_speed;          /**< Vehicle speed km/h (PID 0x0D) */
    int16_t intake_temp;            /**< Intake air temp C (PID 0x0F) */
    float maf_rate;                 /**< MAF g/s (PID 0x10) */
    float throttle_pos;             /**< Throttle position % (PID 0x11) */
} freeze_frame_t;
```

#### ISO-TP Message Structure (`i15765.h:56-66`)
```c
typedef struct {
    uint8_t sa;         /**< Source address */
    uint8_t ta;         /**< Target address */
    uint8_t ae;         /**< Address extension */
    uint8_t pri;        /**< Priority (0-7) */
    uint8_t tat;        /**< Target address type (see I15765_TAT_*) */
    uint8_t *buf;       /**< Pointer to data buffer */
    uint16_t buf_len;   /**< Size of data in bytes */
} i15765_t;
```

---

## 4. ISO-TP Transmit Layer

### 4.1 i15765_tx_app() Function

The ISO-TP transmit function is the key to sending OBD-II requests:

**Declaration:** `i15765.h:113`
```c
extern void i15765_tx_app(i15765_t *msg, uint8_t *status);
```

**Status Codes:** `i15765.h:31-33`
```c
#define I15765_SENT     (0)   // Transmission completed successfully
#define I15765_SENDING  (1)   // Transmission in progress
#define I15765_FAILED   (2)   // Transmission failed
```

**Address Types:** `i15765.h:40-47`
```c
#define I15765_TAT_NP11  (118)  // Normal Physical 11-bit (to specific ECU)
#define I15765_TAT_NF11  (119)  // Normal Functional 11-bit (broadcast 0x7DF)
#define I15765_TAT_NP29  (218)  // Normal Physical 29-bit
#define I15765_TAT_NF29  (219)  // Normal Functional 29-bit
```

### 4.2 Request Function Pattern

All OBD-II request functions follow this pattern:

```c
bool request_xxx(void)
{
    i15765_t msg;
    static uint8_t request_data[N] = { /* mode bytes */ };
    static uint8_t tx_status;

    /*
     * Configure ISO-TP message for OBD-II request
     * Use functional addressing (0x7DF) to broadcast to all ECUs
     */
    msg.ta = 0x00;              // Not used for functional addressing
    msg.tat = I15765_TAT_NF11;  // Normal Functional 11-bit
    msg.buf = request_data;
    msg.buf_len = N;
    msg.pri = 0;
    msg.ae = 0;

    i15765_tx_app(&msg, &tx_status);

    if (tx_status == I15765_FAILED) {
        return false;
    }

    return true;
}
```

### 4.3 Current Request Function Implementations

#### Mode 03 - Stored DTCs (`decode_mode_03_dtc.c:554-583`)
```c
bool request_stored_dtc(void)
{
    i15765_t msg;
    static uint8_t request_data[1] = {0x03};  // Mode 03 request
    static uint8_t tx_status;

    msg.ta = 0x00;
    msg.tat = I15765_TAT_NF11;
    msg.buf = request_data;
    msg.buf_len = 1;
    msg.pri = 0;
    msg.ae = 0;

    i15765_tx_app(&msg, &tx_status);
    return (tx_status != I15765_FAILED);
}
```

#### Mode 07 - Pending DTCs (`decode_mode_03_dtc.c:593-621`)
```c
bool request_pending_dtc(void)
{
    i15765_t msg;
    static uint8_t request_data[1] = {0x07};  // Mode 07 request
    static uint8_t tx_status;

    msg.ta = 0x00;
    msg.tat = I15765_TAT_NF11;
    msg.buf = request_data;
    msg.buf_len = 1;
    msg.pri = 0;
    msg.ae = 0;

    i15765_tx_app(&msg, &tx_status);
    return (tx_status != I15765_FAILED);
}
```

#### Mode 04 - Clear DTCs (`decode_mode_04_clear_dtc.c:141-176`)
```c
bool request_clear_dtc(void)
{
    i15765_t msg;
    static uint8_t request_data[1] = {0x04};  // Mode 04 request
    static uint8_t tx_status;

    g_clear_dtc_status = CLEAR_DTC_PENDING;

    msg.ta = 0x00;
    msg.tat = I15765_TAT_NF11;
    msg.buf = request_data;
    msg.buf_len = 1;
    msg.pri = 0;
    msg.ae = 0;

    i15765_tx_app(&msg, &tx_status);

    if (tx_status == I15765_FAILED) {
        g_clear_dtc_status = CLEAR_DTC_FAILED;
        return false;
    }

    return true;
}
```

#### Mode 02 - Freeze Frame (`decode_mode_02_freeze_frame.c:329-396`)
```c
// Mode 02 requires 3 bytes: [Mode] [PID] [Frame#]
static bool send_freeze_frame_pid_request(uint8_t pid, uint8_t frame_number)
{
    i15765_t msg;
    static uint8_t request_data[3];
    static uint8_t tx_status;

    request_data[0] = 0x02;         // Mode 02 request
    request_data[1] = pid;           // PID to request
    request_data[2] = frame_number;  // Frame number

    msg.ta = 0x00;
    msg.tat = I15765_TAT_NF11;
    msg.buf = request_data;
    msg.buf_len = 3;
    msg.pri = 0;
    msg.ae = 0;

    i15765_tx_app(&msg, &tx_status);
    return (tx_status != I15765_FAILED);
}

bool request_freeze_frame(uint8_t frame_number)
{
    // Requests multiple PIDs for the specified frame
    static const uint8_t pids[] = {0x02, 0x04, 0x05, 0x0C, 0x0D, 0x0F, 0x10, 0x11};

    for (uint8_t i = 0; i < sizeof(pids); i++) {
        send_freeze_frame_pid_request(pids[i], frame_number);
    }

    return true;
}
```

---

## 5. Remaining Tasks

### 5.1 HIGH Priority - DTC Storage Persistence

**Location:** `decode_mode_03_dtc.c:358-383`

Current implementation has stub functions. Need to implement using iMatrix storage API:

```c
bool dtc_save_to_storage(void)
{
    /*
     * TODO: Implement using iMatrix storage API
     *
     * Steps:
     * 1. Create buffer: [version:1][dtc_collection_t]
     * 2. Call imx_storage_write(DTC_STORAGE_KEY, buffer, len)
     * 3. Return success/failure
     *
     * Reference: iMatrix/storage.h for API details
     */
}

bool dtc_load_from_storage(void)
{
    /*
     * TODO: Implement using iMatrix storage API
     *
     * Steps:
     * 1. Call imx_storage_read(DTC_STORAGE_KEY, buffer, &len)
     * 2. Check version byte
     * 3. Copy to g_dtc_collection
     * 4. Return success/failure
     */
}
```

**Storage API Reference:**
- `imx_storage_write(const char *key, uint8_t *data, uint16_t len)`
- `imx_storage_read(const char *key, uint8_t *data, uint16_t *len)`

### 5.2 MEDIUM Priority - CLI Subcommand Registration

Need to register additional CLI commands in the CLI initialization code.

**Commands to Register:**

| Command | Function | Description |
|---------|----------|-------------|
| `dtc list` | `obd2_cli_dtc_list()` | Detailed DTC list |
| `dtc clear` | `obd2_cli_dtc_clear_local()` | Clear local list |
| `dtc query` | `obd2_cli_dtc_query()` | Query from vehicle |
| `ff request` | `obd2_cli_request_freeze_frame()` | Request freeze frame |

**CLI Registration Pattern:**
```c
// In CLI initialization (fcgw_cli.c or similar)
static const cli_cmd_t obd2_commands[] = {
    {"dtc",       obd2_cli_dtc_show,        "DTC summary"},
    {"dtc list",  obd2_cli_dtc_list,        "Detailed DTC list"},
    {"dtc clear", obd2_cli_dtc_clear_local, "Clear local DTCs"},
    {"dtc query", obd2_cli_dtc_query,       "Query vehicle DTCs"},
    {"ff",        obd2_cli_show_freeze_frame,    "Freeze frame display"},
    {"ff request", obd2_cli_request_freeze_frame, "Request freeze frame"},
    {"cleardtc",  obd2_cli_clear_vehicle_dtc,    "Clear VEHICLE DTCs"},
    {NULL, NULL, NULL}
};
```

### 5.3 LOW Priority - Mode 06 Implementation

Mode 06 (On-board Monitoring Tests) is deferred. When implementing:

1. Create `decode_mode_06_tests.c/h`
2. Implement UAS (Units and Scaling) lookup table
3. Parse test result responses
4. Add to `i15765app.c` mode dispatch (0x46 response)

---

## 6. Testing Guide

### 6.1 Unit Test Vectors

**DTC Parser Tests:**
```c
// Test 1: Single DTC - P0133 (O2 Sensor Slow Response)
uint8_t test1[] = {0x43, 0x01, 0x01, 0x33};
// Expected: P0133

// Test 2: Multiple DTCs - P0133, P0420
uint8_t test2[] = {0x43, 0x02, 0x01, 0x33, 0x04, 0x20};
// Expected: P0133, P0420

// Test 3: DTC types - B1234, C5678, U0ABC
uint8_t test3[] = {0x43, 0x03, 0x92, 0x34, 0x56, 0x78, 0xC0, 0xAB};
// Expected: B1234, C1678, U00AB

// Test 4: No DTCs (padding only)
uint8_t test4[] = {0x43, 0x00, 0x00, 0x00};
// Expected: (empty collection)
```

**DTC Code Encoding:**
```
Bits 15-14: System type
  00 = P (Powertrain)
  01 = C (Chassis)
  10 = B (Body)
  11 = U (Network)

Bits 13-12: First digit (0-3)
Bits 11-8:  Second digit (hex)
Bits 7-4:   Third digit (hex)
Bits 3-0:   Fourth digit (hex)

Example: 0x01 0x33
  0x01 = 0000 0001
         00 = P
         00 = 0
         0001 = 1
  0x33 = 0011 0011
         0011 = 3
         0011 = 3
  Result: P0133
```

### 6.2 Vehicle Testing Checklist

1. **DTC Query Test:**
   - Connect to vehicle with known DTCs
   - Run `dtc query` CLI command
   - Verify DTCs displayed match scan tool
   - Check pending vs confirmed status

2. **Freeze Frame Test:**
   - Vehicle must have at least one stored DTC
   - Run `ff request 0` CLI command
   - Verify freeze frame data populated
   - Compare with scan tool values

3. **DTC Clear Test (CAUTION!):**
   - Use test vehicle only
   - Run `cleardtc` CLI command
   - Verify MIL extinguishes
   - Verify DTCs cleared
   - Note: Resets readiness monitors!

### 6.3 Debug Logging

Enable OBD2 debug logging:
```
debug DEBUGS_APP_OBD2
```

Debug output format:
```
[DTC - ECU 0x7E8: Processing Stored DTCs, 8 bytes]
[DTC - ECU 0x7E8: New Stored DTC: P0133]
[DTC - ECU 0x7E8: Total DTCs in collection: 1]
```

---

## 7. Code Patterns

### 7.1 Response Handler Pattern

All response handlers follow this pattern:

```c
void process_mode_XX_response(uint8_t sa, const uint8_t *data, uint16_t len)
{
    /* Validate minimum length */
    if (len < MIN_RESPONSE_LEN) {
        PRINTF("[Mode XX - ECU 0x%02X: Response too short]\r\n", sa);
        return;
    }

    /* Verify mode byte */
    if (data[0] != EXPECTED_MODE_RESPONSE) {
        PRINTF("[Mode XX - ECU 0x%02X: Invalid mode byte]\r\n", sa);
        return;
    }

    /* Parse response data */
    // ...

    /* Update global state */
    // ...

    /* Log results */
    imx_cli_log_printf(true, "[Mode XX - ECU 0x%02X: Result]\r\n", sa);
}
```

### 7.2 CLI Command Pattern

```c
void obd2_cli_xxx(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    imx_cli_print("\r\n=== Header ===\r\n");

    /* Display data */
    // ...

    /* Provide user guidance */
    imx_cli_print("\r\nUse 'command' for more options.\r\n");
}
```

### 7.3 Debug Macro Pattern

```c
#ifdef PRINT_DEBUGS_APP_OBD2
#undef PRINTF
#define PRINTF(...)                             \
    if (APP_LOGS_ENABLED(DEBUGS_APP_OBD2))      \
    {                                           \
        imx_cli_log_printf(true, __VA_ARGS__);  \
    }
#elif !defined PRINTF
#define PRINTF(...)
#endif
```

---

## 8. Build Instructions

### 8.1 Build Command

```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
make -j4
```

### 8.2 CMakeLists.txt

New files are already added. If adding more files, update:

```cmake
# In Fleet-Connect-1/CMakeLists.txt
set(OBD2_SOURCES
    OBD2/decode_mode_02_freeze_frame.c
    OBD2/decode_mode_03_dtc.c
    OBD2/decode_mode_04_clear_dtc.c
    # Add new files here
)
```

### 8.3 Binary Location

```
Fleet-Connect-1/build/FC-1
```

---

## 9. Related Documentation

### 9.1 Project Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Implementation Plan | `docs/obd2_update.md` | Full implementation plan with checklist |
| CLAUDE.md | `CLAUDE.md` | Project development guidelines |
| OBD2 Architecture | (in code) | Inline documentation |

### 9.2 SAE Standards Reference

- **SAE J1979** - OBD-II Diagnostic Test Modes
- **SAE J2012** - Diagnostic Trouble Code Definitions
- **ISO 15765-2** - Transport Protocol (ISO-TP)

### 9.3 python-OBD Reference

The python-OBD library was used as reference for decoder formulas:

```
python-OBD/obd/decoders.py   - Decoder implementations
python-OBD/obd/commands.py   - Command definitions
python-OBD/obd/codes.py      - DTC code database
```

### 9.4 Contact

For questions about this implementation:
- Review code comments (extensive Doxygen documentation)
- Check `docs/obd2_update.md` for implementation history
- Review git commit history for changes

---

## Quick Reference Summary

### Request Functions
| Function | Mode | Bytes | Description |
|----------|------|-------|-------------|
| `request_stored_dtc()` | 03 | 1 | Query stored DTCs |
| `request_pending_dtc()` | 07 | 1 | Query pending DTCs |
| `request_clear_dtc()` | 04 | 1 | Clear all DTCs |
| `request_freeze_frame(n)` | 02 | 3 | Request freeze frame n |

### Response Handlers
| Function | Mode+0x40 | Description |
|----------|-----------|-------------|
| `process_mode_02_freeze_frame()` | 0x42 | Freeze frame data |
| `process_mode_03_dtc()` | 0x43 | Stored DTCs |
| `process_mode_04_clear_dtc()` | 0x44 | Clear acknowledgment |
| `process_mode_07_dtc()` | 0x47 | Pending DTCs |

### CLI Commands
| Command | Function |
|---------|----------|
| `dtc` | Show DTC summary |
| `dtc list` | Detailed DTC list |
| `dtc clear` | Clear local list |
| `dtc query` | Query from vehicle |
| `ff` | Show freeze frames |
| `ff request` | Request freeze frame |
| `cleardtc` | Clear VEHICLE DTCs |

---

**Document End**

*Last Updated: 2025-12-13*
