# OBD-II Additional Modes Implementation Plan

**Date:** 2025-12-13
**Status:** Implemented
**Author:** Claude Code Analysis
**Branch:** feature/obd2-additional-modes

---

## Executive Summary

This document provides a detailed implementation plan for adding missing OBD-II modes to the Fleet-Connect-1 OBD2 subsystem. The implementation follows the existing architecture patterns established in the codebase, specifically the function pointer dispatch table and decoder function signature conventions.

**Modes to Implement:**
| Mode | Name | Priority | Complexity |
|------|------|----------|------------|
| 0x03 | Get Stored DTCs | HIGH | Medium |
| 0x07 | Get Pending DTCs | HIGH | Low (reuses Mode 03 decoder) |
| 0x04 | Clear DTCs & Reset Monitors | MEDIUM | Low |
| 0x02 | Freeze Frame Data | MEDIUM | Medium |
| 0x06 | On-board Monitoring Tests | LOW | High |

---

## 1. Architecture Overview

### 1.1 Existing Architecture Pattern

The Fleet-Connect-1 OBD2 subsystem uses a **function pointer dispatch table** architecture:

**File Structure:**
```
Fleet-Connect-1/OBD2/
├── decode_table.c          # Function pointer dispatch table
├── decode_table.h          # Common type definitions
├── decode_mode_01_pids_*.c # Mode 01 PID decoders (by range)
├── decode_mode_09_pids_*.c # Mode 09 PID decoders
├── process_obd2.c          # Main OBD2 state machine
└── process_obd2.h          # Status structures and constants
```

**Decoder Function Signature (from decode_table.h:65):**
```c
typedef void (*pid_decode_func_t)(uint8_t sa, uint8_t pid, const uint8_t *data, uint16_t len);
```

**Function Pointer Table Pattern (from decode_table.c):**
```c
pid_decode_func_t mode_01_decodeFunc[NO_MODE_01_PID];
#define SET_MODE_01_DECODE(pid, func) mode_01_decodeFunc[(pid)] = (pid_decode_func_t)func
```

### 1.2 New Files Required

| File | Purpose |
|------|---------|
| `decode_mode_03_dtc.c` | DTC parsing for Mode 03 and Mode 07 |
| `decode_mode_03_dtc.h` | Header for DTC functions |
| `decode_mode_02_freeze_frame.c` | Freeze frame data decoder |
| `decode_mode_02_freeze_frame.h` | Header for freeze frame functions |
| `decode_mode_04_clear_dtc.c` | DTC clearing response handler |
| `decode_mode_04_clear_dtc.h` | Header for clear DTC functions |

---

## 2. Mode 03 - Get Stored DTCs (Confirmed DTCs)

### 2.1 SAE J1979 Specification

**Request:** `03` (no PID required)
**Response:** `43 [num_dtcs] [DTC1_high] [DTC1_low] [DTC2_high] [DTC2_low] ...`

Each DTC is 2 bytes encoded as follows:

```
Byte 0 (High):
  Bits 7-6: System type (00=P, 01=C, 10=B, 11=U)
  Bits 5-4: First digit (0-3)
  Bits 3-0: Second digit (0-F)

Byte 1 (Low):
  Bits 7-4: Third digit (0-F)
  Bits 3-0: Fourth digit (0-F)
```

**Example:** Bytes `0x01 0x33` = P0133 (O2 Sensor Circuit Slow Response)

### 2.2 python-OBD Reference Implementation

**File:** `/home/greg/iMatrix/iMatrix_Client/python-OBD/obd/decoders.py:391-436`

```python
def parse_dtc(_bytes):
    """ converts 2 bytes into a DTC code """

    # check validity (also ignores padding that the ELM returns)
    if (len(_bytes) != 2) or (_bytes == (0, 0)):
        return None

    # BYTES: (16,      35      )
    # HEX:    4   1    2   3
    # BIN:    01000001 00100011
    #         [][][  in hex   ]
    #         | / /
    # DTC:    C0123

    dtc = ['P', 'C', 'B', 'U'][_bytes[0] >> 6]  # the last 2 bits of the first byte
    dtc += str((_bytes[0] >> 4) & 0b0011)       # the next pair of 2 bits
    dtc += bytes_to_hex(_bytes)[1:4]            # remaining 3 hex digits

    # pull a description if we have one
    return (dtc, DTC.get(dtc, ""))

def dtc(messages):
    """ converts a frame of 2-byte DTCs into a list of DTCs """
    codes = []
    d = []
    for message in messages:
        d += message.data[2:]  # remove the mode and DTC_count bytes

    # look at data in pairs of bytes
    for n in range(1, len(d), 2):
        dtc = parse_dtc((d[n - 1], d[n]))
        if dtc is not None:
            codes.append(dtc)

    return codes
```

### 2.3 iMatrix C Implementation

**File:** `Fleet-Connect-1/OBD2/decode_mode_03_dtc.h`

```c
/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 * [Standard license header - use blank.h template]
 */

/**
 * @file decode_mode_03_dtc.h
 * @brief OBD-II Mode 03/07 DTC (Diagnostic Trouble Code) parser
 *
 * Implements parsing of stored (Mode 03) and pending (Mode 07) diagnostic
 * trouble codes per SAE J1979 specification.
 *
 * @date 2025-12-13
 * @author Greg Phillips
 */

#ifndef DECODE_MODE_03_DTC_H_
#define DECODE_MODE_03_DTC_H_

#include <stdint.h>
#include <stdbool.h>

/******************************************************
 *                  Constants
 ******************************************************/
#define MAX_DTC_CODES       16      /**< Maximum DTCs to store per response */
#define DTC_CODE_LENGTH     6       /**< DTC string length including null (e.g., "P0133\0") */

/******************************************************
 *                  Type Definitions
 ******************************************************/

/**
 * @brief DTC system type enumeration
 */
typedef enum {
    DTC_POWERTRAIN = 0,     /**< P codes (Engine, Transmission) */
    DTC_CHASSIS    = 1,     /**< C codes (ABS, Steering) */
    DTC_BODY       = 2,     /**< B codes (Airbag, AC) */
    DTC_NETWORK    = 3      /**< U codes (CAN, LIN) */
} dtc_system_t;

/**
 * @brief Single DTC entry structure
 */
typedef struct {
    char code[DTC_CODE_LENGTH];     /**< DTC code string (e.g., "P0133") */
    dtc_system_t system;            /**< System type (P, C, B, U) */
    bool is_pending;                /**< True if from Mode 07 (pending) */
} dtc_entry_t;

/**
 * @brief DTC collection structure
 */
typedef struct {
    uint8_t count;                          /**< Number of valid DTCs */
    dtc_entry_t codes[MAX_DTC_CODES];       /**< Array of DTC entries */
    bool has_mil;                           /**< MIL (Check Engine Light) status */
} dtc_collection_t;

/******************************************************
 *                  Function Declarations
 ******************************************************/

/**
 * @brief Process Mode 03 response (stored/confirmed DTCs)
 *
 * Parses the response from a Mode 03 request and extracts all stored
 * diagnostic trouble codes. Results are stored in the global DTC collection.
 *
 * @param sa   Source address of responding ECU
 * @param data Pointer to response data (starts with mode byte 0x43)
 * @param len  Length of response data
 */
void process_mode_03_dtc(uint8_t sa, const uint8_t *data, uint16_t len);

/**
 * @brief Process Mode 07 response (pending DTCs)
 *
 * Parses the response from a Mode 07 request and extracts all pending
 * diagnostic trouble codes. Uses same parser as Mode 03.
 *
 * @param sa   Source address of responding ECU
 * @param data Pointer to response data (starts with mode byte 0x47)
 * @param len  Length of response data
 */
void process_mode_07_dtc(uint8_t sa, const uint8_t *data, uint16_t len);

/**
 * @brief Parse a single 2-byte DTC into a string
 *
 * Converts raw DTC bytes into human-readable format (e.g., "P0133").
 * Per SAE J1979 encoding:
 *   - Bits 15-14: System (P/C/B/U)
 *   - Bits 13-12: First digit (0-3)
 *   - Bits 11-0:  Three hex digits
 *
 * @param high_byte  First byte of DTC (contains system and first digit)
 * @param low_byte   Second byte of DTC (contains last two digits)
 * @param out_code   Output buffer (must be at least 6 bytes)
 * @return true if valid DTC parsed, false if padding/invalid
 */
bool parse_single_dtc(uint8_t high_byte, uint8_t low_byte, char *out_code);

/**
 * @brief Get pointer to current DTC collection
 *
 * @return Pointer to internal DTC collection structure
 */
const dtc_collection_t *get_dtc_collection(void);

/**
 * @brief Clear the DTC collection
 */
void clear_dtc_collection(void);

/**
 * @brief CLI command to display stored DTCs
 *
 * @param arg Unused command argument
 */
void obd2_cli_show_dtc(uint16_t arg);

#endif /* DECODE_MODE_03_DTC_H_ */
```

**File:** `Fleet-Connect-1/OBD2/decode_mode_03_dtc.c`

```c
/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 * [Standard license header - use blank.c template]
 */

/**
 * @file decode_mode_03_dtc.c
 * @brief OBD-II Mode 03/07 DTC parser implementation
 *
 * Implements DTC parsing per SAE J1979 specification. The encoding uses
 * 2 bytes per DTC where:
 *   - Bits 15-14 of high byte: System type (00=P, 01=C, 10=B, 11=U)
 *   - Bits 13-12 of high byte: First digit (0-3)
 *   - Bits 11-8 of high byte: Second digit (hex)
 *   - Bits 7-4 of low byte: Third digit (hex)
 *   - Bits 3-0 of low byte: Fourth digit (hex)
 *
 * @date 2025-12-13
 * @author Greg Phillips
 * @version 1.0
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "imatrix.h"
#include "decode_mode_03_dtc.h"
#include "process_obd2.h"

/******************************************************
 *                      Macros
 ******************************************************/
#ifdef PRINT_DEBUGS_APP_OBD2
#undef PRINTF
#define PRINTF(...)                       \
    if (APP_LOGS_ENABLED(DEBUGS_APP_OBD2)) \
    {                                     \
        imx_cli_log_printf(true, __VA_ARGS__);  \
    }
#elif !defined PRINTF
#define PRINTF(...)
#endif

/******************************************************
 *                    Constants
 ******************************************************/
/** @brief System type characters indexed by bits 7-6 */
static const char DTC_SYSTEM_CHARS[] = {'P', 'C', 'B', 'U'};

/******************************************************
 *               Variable Definitions
 ******************************************************/
/** @brief Global DTC collection - stores all parsed DTCs */
static dtc_collection_t g_dtc_collection = {0};

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Parse a single 2-byte DTC into a string
 *
 * @param high_byte  First byte of DTC
 * @param low_byte   Second byte of DTC
 * @param out_code   Output buffer (minimum 6 bytes)
 * @return true if valid DTC, false if padding (0x00 0x00)
 */
bool parse_single_dtc(uint8_t high_byte, uint8_t low_byte, char *out_code)
{
    /*
     * Check for padding bytes (0x00 0x00 indicates no more DTCs)
     * This is commonly returned by ECUs to fill out the response
     */
    if (high_byte == 0x00 && low_byte == 0x00) {
        return false;
    }

    /*
     * Extract system type from bits 7-6 of high byte
     * 00 = Powertrain (P)
     * 01 = Chassis (C)
     * 10 = Body (B)
     * 11 = Network (U)
     */
    uint8_t system_type = (high_byte >> 6) & 0x03;

    /*
     * Extract first digit from bits 5-4 of high byte
     * This gives values 0-3 for the first numeric digit
     */
    uint8_t first_digit = (high_byte >> 4) & 0x03;

    /*
     * Extract second digit from bits 3-0 of high byte (hex digit 0-F)
     */
    uint8_t second_digit = high_byte & 0x0F;

    /*
     * Extract third digit from bits 7-4 of low byte (hex digit 0-F)
     */
    uint8_t third_digit = (low_byte >> 4) & 0x0F;

    /*
     * Extract fourth digit from bits 3-0 of low byte (hex digit 0-F)
     */
    uint8_t fourth_digit = low_byte & 0x0F;

    /*
     * Format the DTC code string
     * Example: P0133 = Powertrain, 0, 1, 3, 3
     */
    snprintf(out_code, DTC_CODE_LENGTH, "%c%d%X%X%X",
             DTC_SYSTEM_CHARS[system_type],
             first_digit,
             second_digit,
             third_digit,
             fourth_digit);

    return true;
}

/**
 * @brief Internal function to process DTC response (shared by Mode 03 and 07)
 *
 * @param sa          Source address of ECU
 * @param data        Response data buffer
 * @param len         Length of response
 * @param is_pending  True if Mode 07 (pending), false if Mode 03 (stored)
 */
static void process_dtc_response(uint8_t sa, const uint8_t *data, uint16_t len, bool is_pending)
{
    /*
     * Response format:
     *   Byte 0: Mode + 0x40 (0x43 for Mode 03, 0x47 for Mode 07)
     *   Byte 1: Number of DTCs (may not be present in all implementations)
     *   Bytes 2-3, 4-5, etc.: DTC pairs
     *
     * Note: Some ECUs don't include the count byte, so we parse all pairs
     */

    if (len < 2) {
        PRINTF("[DTC - ECU 0x%02X: Response too short (%u bytes)]\r\n", sa, len);
        return;
    }

    const char *mode_name = is_pending ? "Pending" : "Stored";
    uint8_t start_offset = 2;  /* Skip mode byte and count byte */

    PRINTF("[DTC - ECU 0x%02X: Processing %s DTCs, %u bytes]\r\n",
           sa, mode_name, len);

    /*
     * Parse DTC pairs starting from offset
     * Each DTC is 2 bytes, so we process in pairs
     */
    for (uint16_t i = start_offset; i + 1 < len; i += 2) {
        char dtc_code[DTC_CODE_LENGTH];

        if (parse_single_dtc(data[i], data[i + 1], dtc_code)) {
            /*
             * Valid DTC found - add to collection if space available
             */
            if (g_dtc_collection.count < MAX_DTC_CODES) {
                dtc_entry_t *entry = &g_dtc_collection.codes[g_dtc_collection.count];

                strncpy(entry->code, dtc_code, DTC_CODE_LENGTH);
                entry->system = (dtc_system_t)((data[i] >> 6) & 0x03);
                entry->is_pending = is_pending;

                g_dtc_collection.count++;

                imx_cli_log_printf(true, "[DTC - ECU 0x%02X: %s DTC: %s]\r\n",
                                   sa, mode_name, dtc_code);
            } else {
                PRINTF("[DTC - ECU 0x%02X: Collection full, DTC dropped]\r\n", sa);
            }
        }
    }

    PRINTF("[DTC - ECU 0x%02X: Total DTCs in collection: %u]\r\n",
           sa, g_dtc_collection.count);
}

/**
 * @brief Process Mode 03 response (stored/confirmed DTCs)
 */
void process_mode_03_dtc(uint8_t sa, const uint8_t *data, uint16_t len)
{
    process_dtc_response(sa, data, len, false);
}

/**
 * @brief Process Mode 07 response (pending DTCs)
 */
void process_mode_07_dtc(uint8_t sa, const uint8_t *data, uint16_t len)
{
    process_dtc_response(sa, data, len, true);
}

/**
 * @brief Get pointer to current DTC collection
 */
const dtc_collection_t *get_dtc_collection(void)
{
    return &g_dtc_collection;
}

/**
 * @brief Clear the DTC collection
 */
void clear_dtc_collection(void)
{
    memset(&g_dtc_collection, 0, sizeof(g_dtc_collection));
}

/**
 * @brief CLI command to display stored DTCs
 */
void obd2_cli_show_dtc(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    imx_cli_print("=== OBD-II Diagnostic Trouble Codes ===\r\n");
    imx_cli_print("Total DTCs: %u\r\n\r\n", g_dtc_collection.count);

    if (g_dtc_collection.count == 0) {
        imx_cli_print("No DTCs stored.\r\n");
        return;
    }

    imx_cli_print("%-8s %-10s %-10s\r\n", "Code", "System", "Status");
    imx_cli_print("--------------------------------------\r\n");

    for (uint8_t i = 0; i < g_dtc_collection.count; i++) {
        const dtc_entry_t *entry = &g_dtc_collection.codes[i];
        const char *system_name;

        switch (entry->system) {
            case DTC_POWERTRAIN: system_name = "Powertrain"; break;
            case DTC_CHASSIS:    system_name = "Chassis";    break;
            case DTC_BODY:       system_name = "Body";       break;
            case DTC_NETWORK:    system_name = "Network";    break;
            default:             system_name = "Unknown";    break;
        }

        imx_cli_print("%-8s %-10s %-10s\r\n",
                      entry->code,
                      system_name,
                      entry->is_pending ? "Pending" : "Confirmed");
    }

    imx_cli_print("\r\n");
}
```

### 2.4 Integration Steps

1. Add `decode_mode_03_dtc.c` to `CMakeLists.txt`
2. Add `#include "decode_mode_03_dtc.h"` to `decode_table.c`
3. Add mode dispatch in ISO-TP response handler (location TBD based on i15765 code review)
4. Register CLI command `dtc` in CLI initialization

---

## 3. Mode 07 - Get Pending DTCs

### 3.1 SAE J1979 Specification

**Request:** `07` (no PID required)
**Response:** `47 [num_dtcs] [DTC pairs...]`

Mode 07 uses identical encoding to Mode 03. The only difference is:
- Mode 03 returns **stored/confirmed** DTCs (Check Engine Light is on)
- Mode 07 returns **pending** DTCs (fault detected but not yet confirmed)

### 3.2 Implementation

Mode 07 reuses the `process_dtc_response()` internal function from Mode 03:

```c
void process_mode_07_dtc(uint8_t sa, const uint8_t *data, uint16_t len)
{
    process_dtc_response(sa, data, len, true);  /* true = pending */
}
```

No additional files needed - implemented in `decode_mode_03_dtc.c`.

---

## 4. Mode 04 - Clear DTCs and Reset Monitors

### 4.1 SAE J1979 Specification

**Request:** `04` (no PID required)
**Response:** `44` (single byte acknowledgment)

This mode:
1. Clears all stored DTCs
2. Resets the MIL (Malfunction Indicator Lamp)
3. Resets all readiness monitors to "incomplete" status
4. Clears freeze frame data

**WARNING:** This command should only be executed upon explicit user request, as it affects emissions testing readiness.

### 4.2 python-OBD Reference

python-OBD defines this as a simple "drop" command (no response data needed):

```python
# From commands.py
OBDCommand("CLEAR_DTC", "Clear DTCs and Freeze data", b"04", 0, drop, ECU.ALL, True),
```

### 4.3 iMatrix C Implementation

**File:** `Fleet-Connect-1/OBD2/decode_mode_04_clear_dtc.h`

```c
/**
 * @file decode_mode_04_clear_dtc.h
 * @brief OBD-II Mode 04 - Clear DTCs and Reset Monitors
 * @date 2025-12-13
 */

#ifndef DECODE_MODE_04_CLEAR_DTC_H_
#define DECODE_MODE_04_CLEAR_DTC_H_

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Process Mode 04 response (DTC clear acknowledgment)
 *
 * @param sa   Source address of responding ECU
 * @param data Pointer to response data (0x44)
 * @param len  Length of response
 */
void process_mode_04_clear_dtc(uint8_t sa, const uint8_t *data, uint16_t len);

/**
 * @brief Request DTC clear from vehicle
 *
 * Sends Mode 04 request to all ECUs. This will:
 * - Clear all stored DTCs
 * - Turn off MIL (Check Engine Light)
 * - Reset readiness monitors
 *
 * @return true if request sent successfully
 * @warning This affects emissions testing readiness!
 */
bool request_clear_dtc(void);

/**
 * @brief CLI command to clear DTCs
 *
 * @param arg Unused
 */
void obd2_cli_clear_dtc(uint16_t arg);

#endif /* DECODE_MODE_04_CLEAR_DTC_H_ */
```

**File:** `Fleet-Connect-1/OBD2/decode_mode_04_clear_dtc.c`

```c
/**
 * @file decode_mode_04_clear_dtc.c
 * @brief OBD-II Mode 04 - Clear DTCs implementation
 * @date 2025-12-13
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "imatrix.h"
#include "decode_mode_04_clear_dtc.h"
#include "decode_mode_03_dtc.h"  /* For clear_dtc_collection() */
#include "i15765.h"
#include "process_obd2.h"

/******************************************************
 *               Variable Definitions
 ******************************************************/
static bool g_clear_dtc_pending = false;
static bool g_clear_dtc_success = false;

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Process Mode 04 response
 */
void process_mode_04_clear_dtc(uint8_t sa, const uint8_t *data, uint16_t len)
{
    /*
     * Response is simply 0x44 to acknowledge the clear request
     */
    if (len >= 1 && data[0] == 0x44) {
        g_clear_dtc_success = true;
        g_clear_dtc_pending = false;

        /* Clear our local DTC collection as well */
        clear_dtc_collection();

        imx_cli_log_printf(true, "[DTC Clear - ECU 0x%02X: DTCs cleared successfully]\r\n", sa);
    } else {
        imx_cli_log_printf(true, "[DTC Clear - ECU 0x%02X: Unexpected response]\r\n", sa);
    }
}

/**
 * @brief Request DTC clear from vehicle
 */
bool request_clear_dtc(void)
{
    /*
     * Mode 04 request is simply the byte 0x04
     * Sent as broadcast to all ECUs
     */
    uint8_t request[1] = {0x04};

    g_clear_dtc_pending = true;
    g_clear_dtc_success = false;

    /* TODO: Call i15765 transmit function with Mode 04 request */
    /* i15765_transmit(OBD2_BROADCAST_ADDR, request, 1); */

    imx_cli_log_printf(true, "[DTC Clear - Request sent]\r\n");
    return true;
}

/**
 * @brief CLI command to clear DTCs
 */
void obd2_cli_clear_dtc(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    imx_cli_print("WARNING: Clearing DTCs will:\r\n");
    imx_cli_print("  - Turn off Check Engine Light\r\n");
    imx_cli_print("  - Reset all readiness monitors\r\n");
    imx_cli_print("  - Clear freeze frame data\r\n");
    imx_cli_print("  - Affect emissions testing readiness\r\n\r\n");

    /* Note: In production, add confirmation prompt */
    if (request_clear_dtc()) {
        imx_cli_print("DTC clear request sent.\r\n");
    } else {
        imx_cli_print("Failed to send DTC clear request.\r\n");
    }
}
```

---

## 5. Mode 02 - Freeze Frame Data

### 5.1 SAE J1979 Specification

**Request:** `02 [PID] [Frame#]`
**Response:** `42 [PID] [Frame#] [Data...]`

Freeze frame data captures a "snapshot" of vehicle parameters at the moment a DTC was detected. The PIDs available in freeze frame are the same as Mode 01, but the request includes a frame number.

### 5.2 python-OBD Reference

python-OBD implements freeze frame by reusing Mode 01 decoders:

```python
# From commands.py - FREEZE_DTC definition
OBDCommand("FREEZE_DTC", "DTC that triggered the freeze frame", b"0202", 4, single_dtc, ECU.ALL, True),
```

### 5.3 iMatrix C Implementation

**File:** `Fleet-Connect-1/OBD2/decode_mode_02_freeze_frame.h`

```c
/**
 * @file decode_mode_02_freeze_frame.h
 * @brief OBD-II Mode 02 - Freeze Frame Data
 * @date 2025-12-13
 */

#ifndef DECODE_MODE_02_FREEZE_FRAME_H_
#define DECODE_MODE_02_FREEZE_FRAME_H_

#include <stdint.h>
#include <stdbool.h>

/******************************************************
 *                  Constants
 ******************************************************/
#define MAX_FREEZE_FRAMES   4   /**< Maximum freeze frames to store */

/******************************************************
 *                  Type Definitions
 ******************************************************/

/**
 * @brief Freeze frame snapshot data
 */
typedef struct {
    bool valid;                     /**< True if frame contains valid data */
    char trigger_dtc[6];            /**< DTC that triggered the freeze (e.g., "P0133") */
    uint8_t frame_number;           /**< Frame number (0-255) */
    /* Key parameters captured at DTC time */
    float engine_load;              /**< Engine load % (PID 0x04) */
    int16_t coolant_temp;           /**< Coolant temp C (PID 0x05) */
    float fuel_trim_short;          /**< Short term fuel trim % (PID 0x06) */
    float fuel_trim_long;           /**< Long term fuel trim % (PID 0x07) */
    uint16_t rpm;                   /**< Engine RPM (PID 0x0C) */
    uint8_t vehicle_speed;          /**< Vehicle speed km/h (PID 0x0D) */
    int16_t intake_temp;            /**< Intake air temp C (PID 0x0F) */
    float maf_rate;                 /**< MAF g/s (PID 0x10) */
    float throttle_pos;             /**< Throttle position % (PID 0x11) */
} freeze_frame_t;

/******************************************************
 *                  Function Declarations
 ******************************************************/

/**
 * @brief Process Mode 02 freeze frame response
 *
 * @param sa    Source address of ECU
 * @param pid   PID that was requested
 * @param data  Response data buffer
 * @param len   Length of response
 */
void process_mode_02_freeze_frame(uint8_t sa, uint8_t pid, const uint8_t *data, uint16_t len);

/**
 * @brief Request freeze frame data
 *
 * @param frame_number Frame number to request (typically 0)
 * @return true if request sent successfully
 */
bool request_freeze_frame(uint8_t frame_number);

/**
 * @brief Get freeze frame data
 *
 * @param frame_number Frame number to retrieve
 * @return Pointer to freeze frame data, or NULL if not available
 */
const freeze_frame_t *get_freeze_frame(uint8_t frame_number);

/**
 * @brief CLI command to display freeze frame data
 *
 * @param arg Frame number to display (0 = all frames)
 */
void obd2_cli_show_freeze_frame(uint16_t arg);

#endif /* DECODE_MODE_02_FREEZE_FRAME_H_ */
```

**Implementation Note:** Mode 02 reuses Mode 01 PID decoders. The freeze frame response format is:

```
Response: 42 [PID] [Frame#] [Data bytes same as Mode 01]
```

The implementation should:
1. Extract PID and frame number from response
2. Route to existing Mode 01 decoder for that PID
3. Store result in freeze_frame_t structure instead of live data

---

## 6. DTC Data Storage and CLI Commands

### 6.1 Overview

The DTC subsystem provides persistent storage of diagnostic trouble codes and CLI commands for viewing and managing the local DTC list. This is separate from the vehicle's DTC storage - we maintain our own copy for:
- Historical tracking across power cycles
- Upload to iMatrix cloud platform
- Local diagnostics without re-querying the vehicle

### 6.2 DTC Storage Structure

**Enhanced Header File:** `Fleet-Connect-1/OBD2/decode_mode_03_dtc.h`

Add timestamp and ECU source tracking to the DTC entry:

```c
/**
 * @brief Single DTC entry structure with storage metadata
 */
typedef struct {
    char code[DTC_CODE_LENGTH];     /**< DTC code string (e.g., "P0133") */
    dtc_system_t system;            /**< System type (P, C, B, U) */
    bool is_pending;                /**< True if from Mode 07 (pending) */
    uint8_t ecu_address;            /**< Source ECU address (0x00-0xFF) */
    uint32_t first_seen;            /**< Timestamp when first detected (epoch seconds) */
    uint32_t last_seen;             /**< Timestamp when last confirmed (epoch seconds) */
    uint8_t occurrence_count;       /**< Number of times this DTC has been seen */
} dtc_entry_t;

/**
 * @brief DTC collection structure with storage metadata
 */
typedef struct {
    uint8_t count;                          /**< Number of valid DTCs */
    dtc_entry_t codes[MAX_DTC_CODES];       /**< Array of DTC entries */
    bool has_mil;                           /**< MIL (Check Engine Light) status */
    uint32_t last_query_time;               /**< Last time DTCs were queried from vehicle */
    uint32_t last_clear_time;               /**< Last time DTCs were cleared */
    char vin[18];                           /**< VIN associated with these DTCs */
} dtc_collection_t;
```

### 6.3 Storage Persistence

DTCs are saved to flash storage for persistence across power cycles:

**File:** `Fleet-Connect-1/OBD2/decode_mode_03_dtc.c`

```c
#include "storage.h"

/** @brief Storage key for DTC collection */
#define DTC_STORAGE_KEY     "obd2_dtc_collection"
#define DTC_STORAGE_VERSION 1

/**
 * @brief Save DTC collection to persistent storage
 *
 * Saves the current DTC collection to flash storage. Called after
 * receiving new DTCs from the vehicle or after clearing.
 *
 * @return true if save successful
 */
bool dtc_save_to_storage(void)
{
    /*
     * Save DTC collection to flash storage using iMatrix storage API
     * Format: [version:1][count:1][dtc_entries:variable]
     */
    uint8_t buffer[sizeof(uint8_t) + sizeof(dtc_collection_t)];
    uint16_t offset = 0;

    buffer[offset++] = DTC_STORAGE_VERSION;
    memcpy(&buffer[offset], &g_dtc_collection, sizeof(dtc_collection_t));
    offset += sizeof(dtc_collection_t);

    if (imx_storage_write(DTC_STORAGE_KEY, buffer, offset) == IMX_SUCCESS) {
        PRINTF("[DTC Storage - Saved %u DTCs to flash]\r\n", g_dtc_collection.count);
        return true;
    }

    PRINTF("[DTC Storage - Failed to save to flash]\r\n");
    return false;
}

/**
 * @brief Load DTC collection from persistent storage
 *
 * Restores the DTC collection from flash storage on startup.
 * Called during OBD2 initialization.
 *
 * @return true if load successful, false if no data or version mismatch
 */
bool dtc_load_from_storage(void)
{
    uint8_t buffer[sizeof(uint8_t) + sizeof(dtc_collection_t)];
    uint16_t len = sizeof(buffer);

    if (imx_storage_read(DTC_STORAGE_KEY, buffer, &len) != IMX_SUCCESS) {
        PRINTF("[DTC Storage - No saved DTCs found]\r\n");
        return false;
    }

    /* Check version */
    if (buffer[0] != DTC_STORAGE_VERSION) {
        PRINTF("[DTC Storage - Version mismatch, clearing]\r\n");
        clear_dtc_collection();
        return false;
    }

    memcpy(&g_dtc_collection, &buffer[1], sizeof(dtc_collection_t));
    PRINTF("[DTC Storage - Loaded %u DTCs from flash]\r\n", g_dtc_collection.count);
    return true;
}

/**
 * @brief Initialize DTC storage on startup
 *
 * Called during OBD2 initialization to restore saved DTCs.
 */
void dtc_storage_init(void)
{
    dtc_load_from_storage();
}
```

### 6.4 OBD2 CLI Commands

Add the following commands to the OBD2 CLI command group:

**Command Registration Pattern:**

Based on existing CLI patterns in Fleet-Connect-1, add to CLI initialization:

```c
/* OBD2 DTC commands - registered under "obd2" command group */
static const cli_command_t obd2_dtc_commands[] = {
    {"dtc",       obd2_cli_dtc_show,  "Show stored DTCs"},
    {"dtc list",  obd2_cli_dtc_list,  "List all DTCs with details"},
    {"dtc clear", obd2_cli_dtc_clear_local, "Clear local DTC list (not vehicle)"},
    {"dtc query", obd2_cli_dtc_query, "Query DTCs from vehicle"},
    {NULL, NULL, NULL}
};
```

### 6.5 CLI Command Implementations

**File:** `Fleet-Connect-1/OBD2/decode_mode_03_dtc.c`

```c
/**
 * @brief CLI command: obd2 dtc
 *
 * Shows summary of stored DTCs with count and MIL status.
 *
 * @param arg Unused
 */
void obd2_cli_dtc_show(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    imx_cli_print("\r\n=== OBD2 DTC Summary ===\r\n");
    imx_cli_print("Total DTCs: %u\r\n", g_dtc_collection.count);
    imx_cli_print("MIL Status: %s\r\n", g_dtc_collection.has_mil ? "ON" : "OFF");

    if (g_dtc_collection.last_query_time > 0) {
        imx_cli_print("Last Query: %s", ctime((time_t *)&g_dtc_collection.last_query_time));
    }

    if (g_dtc_collection.count > 0) {
        imx_cli_print("\r\nStored Codes:\r\n");
        for (uint8_t i = 0; i < g_dtc_collection.count; i++) {
            const dtc_entry_t *entry = &g_dtc_collection.codes[i];
            imx_cli_print("  %s (%s)\r\n",
                          entry->code,
                          entry->is_pending ? "Pending" : "Confirmed");
        }
    }

    imx_cli_print("\r\nUse 'obd2 dtc list' for detailed view\r\n");
    imx_cli_print("Use 'obd2 dtc clear' to clear local list\r\n");
    imx_cli_print("Use 'obd2 dtc query' to refresh from vehicle\r\n");
}

/**
 * @brief CLI command: obd2 dtc list
 *
 * Shows detailed list of all stored DTCs with timestamps and ECU info.
 *
 * @param arg Unused
 */
void obd2_cli_dtc_list(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    imx_cli_print("\r\n=== OBD2 Diagnostic Trouble Codes ===\r\n");

    if (g_dtc_collection.vin[0] != '\0') {
        imx_cli_print("VIN: %s\r\n", g_dtc_collection.vin);
    }

    imx_cli_print("Total DTCs: %u\r\n", g_dtc_collection.count);
    imx_cli_print("MIL (Check Engine): %s\r\n\r\n",
                  g_dtc_collection.has_mil ? "ON" : "OFF");

    if (g_dtc_collection.count == 0) {
        imx_cli_print("No DTCs stored.\r\n");
        return;
    }

    /* Print header */
    imx_cli_print("%-6s %-10s %-10s %-6s %-6s\r\n",
                  "Code", "System", "Status", "ECU", "Count");
    imx_cli_print("----------------------------------------------\r\n");

    /* Print each DTC */
    for (uint8_t i = 0; i < g_dtc_collection.count; i++) {
        const dtc_entry_t *entry = &g_dtc_collection.codes[i];
        const char *system_name;

        switch (entry->system) {
            case DTC_POWERTRAIN: system_name = "Powertrain"; break;
            case DTC_CHASSIS:    system_name = "Chassis";    break;
            case DTC_BODY:       system_name = "Body";       break;
            case DTC_NETWORK:    system_name = "Network";    break;
            default:             system_name = "Unknown";    break;
        }

        imx_cli_print("%-6s %-10s %-10s 0x%02X   %u\r\n",
                      entry->code,
                      system_name,
                      entry->is_pending ? "Pending" : "Confirmed",
                      entry->ecu_address,
                      entry->occurrence_count);
    }

    imx_cli_print("\r\n");

    /* Print timestamps */
    if (g_dtc_collection.last_query_time > 0) {
        imx_cli_print("Last vehicle query: %s",
                      ctime((time_t *)&g_dtc_collection.last_query_time));
    }
    if (g_dtc_collection.last_clear_time > 0) {
        imx_cli_print("Last cleared: %s",
                      ctime((time_t *)&g_dtc_collection.last_clear_time));
    }
}

/**
 * @brief CLI command: obd2 dtc clear
 *
 * Clears the LOCAL DTC list. Does NOT clear DTCs from the vehicle.
 * Use Mode 04 (vehicle clear) to clear vehicle DTCs.
 *
 * @param arg Unused
 */
void obd2_cli_dtc_clear_local(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    uint8_t previous_count = g_dtc_collection.count;

    /* Clear the collection */
    clear_dtc_collection();

    /* Update clear timestamp */
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    g_dtc_collection.last_clear_time = (uint32_t)(current_time / 1000);

    /* Save to storage */
    dtc_save_to_storage();

    imx_cli_print("\r\nLocal DTC list cleared.\r\n");
    imx_cli_print("Removed %u DTC(s) from local storage.\r\n", previous_count);
    imx_cli_print("\r\nNote: This does NOT clear DTCs from the vehicle.\r\n");
    imx_cli_print("To clear vehicle DTCs, use Mode 04 (obd2 vehicle clear).\r\n");
}

/**
 * @brief CLI command: obd2 dtc query
 *
 * Requests fresh DTC data from the vehicle (Mode 03 and Mode 07).
 *
 * @param arg Unused
 */
void obd2_cli_dtc_query(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    imx_cli_print("\r\nQuerying vehicle for DTCs...\r\n");
    imx_cli_print("  - Mode 03: Stored/Confirmed DTCs\r\n");
    imx_cli_print("  - Mode 07: Pending DTCs\r\n\r\n");

    /* TODO: Trigger Mode 03 and Mode 07 requests */
    /* This should queue requests to the OBD2 state machine */

    imx_cli_print("DTC query initiated. Results will be displayed when received.\r\n");
    imx_cli_print("Use 'obd2 dtc list' to view results.\r\n");
}
```

### 6.6 Updated Function Declarations

Add these to the header file:

```c
/**
 * @brief Initialize DTC storage subsystem
 *
 * Loads saved DTCs from flash storage. Called during OBD2 init.
 */
void dtc_storage_init(void);

/**
 * @brief Save DTC collection to persistent storage
 *
 * @return true if successful
 */
bool dtc_save_to_storage(void);

/**
 * @brief Load DTC collection from persistent storage
 *
 * @return true if successful
 */
bool dtc_load_from_storage(void);

/**
 * @brief CLI command: obd2 dtc (summary)
 */
void obd2_cli_dtc_show(uint16_t arg);

/**
 * @brief CLI command: obd2 dtc list (detailed)
 */
void obd2_cli_dtc_list(uint16_t arg);

/**
 * @brief CLI command: obd2 dtc clear (local clear only)
 */
void obd2_cli_dtc_clear_local(uint16_t arg);

/**
 * @brief CLI command: obd2 dtc query (refresh from vehicle)
 */
void obd2_cli_dtc_query(uint16_t arg);
```

### 6.7 CLI Command Summary

| Command | Function | Description |
|---------|----------|-------------|
| `obd2 dtc` | `obd2_cli_dtc_show()` | Show DTC summary (count, MIL status, codes) |
| `obd2 dtc list` | `obd2_cli_dtc_list()` | Detailed DTC list with ECU, timestamps |
| `obd2 dtc clear` | `obd2_cli_dtc_clear_local()` | Clear LOCAL list (not vehicle) |
| `obd2 dtc query` | `obd2_cli_dtc_query()` | Request fresh DTCs from vehicle |

**Important Distinction:**
- `obd2 dtc clear` - Clears the **local** DTC storage only
- Mode 04 vehicle clear - Clears DTCs **from the vehicle ECU**

---

## 7. Mode 06 - On-board Monitoring Tests (Low Priority)

### 7.1 Overview

Mode 06 provides detailed test results from the on-board monitoring system. This is primarily used for emissions certification and advanced diagnostics.

**Complexity:** HIGH - Requires implementing UAS (Units and Scaling) table with 100+ test definitions.

### 7.2 Recommendation

Defer Mode 06 implementation until Modes 02, 03, 04, and 07 are complete and tested. Mode 06 is primarily useful for:
- Emissions testing facilities
- Advanced diagnostic applications
- CARB compliance verification

---

## 8. Implementation Checklist

### 8.1 Phase 1: DTC Support (Mode 03/07)

- [x] Create `decode_mode_03_dtc.h`
- [x] Create `decode_mode_03_dtc.c`
- [x] Add files to CMakeLists.txt
- [x] Add mode dispatch in ISO-TP response handler
- [x] Implement request_stored_dtc() using i15765_tx_app()
- [x] Implement request_pending_dtc() using i15765_tx_app()
- [ ] Implement DTC storage persistence (flash save/load)
- [x] Register `obd2 dtc` CLI commands
- [ ] Register `obd2 dtc list` CLI command
- [ ] Register `obd2 dtc clear` CLI command (local clear)
- [x] Implement `obd2 dtc query` CLI command (calls request functions)
- [ ] Test with real vehicle
- [x] Update documentation

### 8.2 Phase 2: Clear DTC (Mode 04)

- [x] Create `decode_mode_04_clear_dtc.h`
- [x] Create `decode_mode_04_clear_dtc.c`
- [x] Add files to CMakeLists.txt
- [x] Add mode dispatch in ISO-TP response handler
- [x] Add request function using i15765_tx_app()
- [x] Register `obd2 vehicle clear` CLI command (clears vehicle DTCs)
- [ ] Test with real vehicle (carefully!)
- [x] Update documentation

### 8.3 Phase 3: Freeze Frame (Mode 02)

- [x] Create `decode_mode_02_freeze_frame.h`
- [x] Create `decode_mode_02_freeze_frame.c`
- [x] Add files to CMakeLists.txt
- [x] Add mode dispatch in ISO-TP response handler
- [x] Implement request_freeze_frame() using i15765_tx_app()
- [ ] Implement PID routing to Mode 01 decoders
- [x] Register `obd2 freeze` CLI command
- [ ] Test with real vehicle
- [x] Update documentation

### 8.4 Phase 4: Mode 06 (Future)

- [ ] Define UAS table structure
- [ ] Implement test result parsing
- [ ] Add CLI display functions
- [ ] Test with real vehicle

---

## 9. Integration Points

### 9.1 ISO-TP Response Handler

The ISO 15765-2 layer needs mode dispatch added. Location to modify:

**File:** `Fleet-Connect-1/OBD2/i15765app.c` (or similar)

Add switch cases for new modes:

```c
switch (mode) {
    case 0x41:  /* Mode 01 + 0x40 */
        /* Existing Mode 01 handling */
        break;
    case 0x43:  /* Mode 03 + 0x40 */
        process_mode_03_dtc(sa, data, len);
        break;
    case 0x44:  /* Mode 04 + 0x40 */
        process_mode_04_clear_dtc(sa, data, len);
        break;
    case 0x47:  /* Mode 07 + 0x40 */
        process_mode_07_dtc(sa, data, len);
        break;
    case 0x42:  /* Mode 02 + 0x40 */
        /* Extract PID and route to decoder */
        break;
    case 0x49:  /* Mode 09 + 0x40 */
        /* Existing Mode 09 handling */
        break;
}
```

### 9.2 CMakeLists.txt Updates

Add new source files:

```cmake
set(OBD2_SOURCES
    OBD2/decode_mode_03_dtc.c
    OBD2/decode_mode_04_clear_dtc.c
    OBD2/decode_mode_02_freeze_frame.c
    # ... existing files ...
)
```

### 9.3 CLI Command Registration

Add to CLI initialization (location TBD):

```c
/* DTC commands */
register_cli_command("dtc", obd2_cli_show_dtc, "Show diagnostic trouble codes");
register_cli_command("dtc clear", obd2_cli_clear_dtc, "Clear DTCs (use with caution)");
register_cli_command("freeze", obd2_cli_show_freeze_frame, "Show freeze frame data");
```

---

## 10. Testing Plan

### 10.1 Unit Testing

For each mode, test with known byte sequences:

**Mode 03 Test Vectors:**
```c
/* P0133 - O2 Sensor Slow Response */
uint8_t test1[] = {0x43, 0x01, 0x01, 0x33};
/* Expected output: P0133 */

/* Multiple DTCs: P0133, P0420 */
uint8_t test2[] = {0x43, 0x02, 0x01, 0x33, 0x04, 0x20};
/* Expected output: P0133, P0420 */

/* No DTCs (padding only) */
uint8_t test3[] = {0x43, 0x00, 0x00, 0x00};
/* Expected output: (empty) */
```

### 10.2 Vehicle Testing

1. Connect to test vehicle with known DTCs
2. Request Mode 03, verify correct codes displayed
3. Request Mode 07, verify pending codes if any
4. Request freeze frame for each DTC
5. Test Mode 04 clear (on test vehicle only!)
6. Verify MIL extinguishes and codes cleared

---

## 11. References

### 11.1 SAE Standards
- SAE J1979 - OBD-II Diagnostic Test Modes
- SAE J2012 - Diagnostic Trouble Code Definitions
- ISO 15765-2 - Transport Protocol (ISO-TP)

### 11.2 python-OBD Source Files
- `/home/greg/iMatrix/iMatrix_Client/python-OBD/obd/decoders.py` - Decoder implementations
- `/home/greg/iMatrix/iMatrix_Client/python-OBD/obd/commands.py` - Command definitions
- `/home/greg/iMatrix/iMatrix_Client/python-OBD/obd/codes.py` - DTC code database

### 11.3 Fleet-Connect-1 Source Files
- `Fleet-Connect-1/OBD2/decode_table.c` - Function pointer dispatch pattern
- `Fleet-Connect-1/OBD2/decode_mode_01_pids_*.c` - Mode 01 decoder examples
- `Fleet-Connect-1/OBD2/decode_mode_09_pids_01_0D.c` - Mode 09 decoder examples
- `Fleet-Connect-1/OBD2/process_obd2.c` - Main OBD2 state machine

---

**Plan Created By:** Claude Code
**Date:** 2025-12-13
**Implementation Date:** 2025-12-13
**Status:** Implemented - Core decoders complete, testing pending

### Implementation Notes
- All decoder files created and compiling successfully
- Mode dispatch integrated into i15765app.c
- CLI commands registered: `dtc`, `ff`, `cleardtc`
- Build verified: FC-1 binary compiles with all new modules
- **i15765 Transmit Integration (2025-12-13):**
  - All request functions now use i15765_tx_app() for CAN transmission
  - request_stored_dtc() - Sends Mode 03 request
  - request_pending_dtc() - Sends Mode 07 request
  - request_clear_dtc() - Sends Mode 04 request
  - request_freeze_frame() - Sends Mode 02 requests for all freeze frame PIDs
  - All functions use I15765_TAT_NF11 (Normal Functional 11-bit) for broadcast to 0x7DF
- Remaining work: Flash persistence, additional CLI subcommands, vehicle testing
- **See also:** docs/obd2_next_steps.md for comprehensive developer guide

