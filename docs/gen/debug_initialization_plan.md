# Debug Initialization - Convert printf to imx_cli_log_printf Plan

**Date**: 2026-01-02
**Branch**: feature/debug_initialization
**Author**: Claude Code
**Status**: COMPLETED
**Completion Date**: 2026-01-03

## Overview

This task converts all startup printf/imx_printf statements to use `imx_cli_log_printf()` so messages are properly logged to the filesystem log instead of just going to console.

## Original Branch Information

| Submodule | Original Branch | Feature Branch |
|-----------|-----------------|----------------|
| iMatrix | Aptera_1_Clean | feature/debug_initialization |
| Fleet-Connect-1 | Aptera_1_Clean | feature/debug_initialization |

## Problem Statement

The startup sequence outputs messages using `printf()` and `imx_printf()` which:
1. Don't get logged to the filesystem log file (/var/log/fc-1.log)
2. Don't include timestamps
3. May cause issues when the CLI system isn't fully initialized

## Files Requiring Changes

### iMatrix Core Files

| File | Line(s) | Current Function | Change To |
|------|---------|------------------|-----------|
| `IMX_Platform/LINUX_Platform/check_process.c` | 107, 112, 123, 141, 149, 157, 169, 179, 188 | printf() | imx_cli_log_printf() |
| `device/config.c` | 226, 230, 261 | printf() | imx_cli_log_printf() |
| `device/system_init.c` | 232, 249, 254, 275, 279, 296, 299, 328, 340, 343, 351, 362 | imx_printf() | imx_cli_log_printf() |
| `device/set_serial.c` | 149, 159 | imx_printf() | imx_cli_log_printf() |
| `coap/que_manager.c` | 301, 368, 380 | imx_printf() | imx_cli_log_printf() |
| `device/var_data.c` | 103 | imx_printf() | imx_cli_log_printf() |
| `memory/imx_memory.c` | 111 | imx_cli_print() | imx_cli_log_printf() |
| `cli/cli.c` | 444 | imx_cli_print() | imx_cli_log_printf() |

## Conversion Pattern

**From printf:**
```c
printf("Message text\r\n");
```

**To imx_cli_log_printf:**
```c
imx_cli_log_printf(true, "Message text\r\n");
```

**From imx_printf:**
```c
imx_printf("Message text: %d\r\n", value);
```

**To imx_cli_log_printf:**
```c
imx_cli_log_printf(true, "Message text: %d\r\n", value);
```

The first parameter `true` adds a timestamp to the log message.

## Implementation Checklist

- [x] Convert check_process.c (9 statements)
- [x] Convert config.c (3 statements)
- [x] Convert system_init.c (12 statements)
- [x] Convert set_serial.c (2 statements)
- [x] Convert que_manager.c (5 statements)
- [x] Convert var_data.c (3 statements)
- [x] Convert imx_memory.c (1 statement)
- [x] Convert cli.c (2 statements)
- [x] Build verification after changes
- [x] Final clean build verification
- [ ] Test on target device

## Notes

- The logging system is initialized early in `imatrix_start()` so `imx_cli_log_printf()` should be safe to use for all startup messages
- Messages in `check_process.c` need the include for `cli/interface.h` added
- Some messages in error paths may still use printf() as fallback - this is acceptable

## Build Commands

```bash
# Build Fleet-Connect-1 (includes iMatrix)
cd Fleet-Connect-1 && mkdir -p build && cd build && cmake .. && make -j$(nproc)
```

---

## Implementation Results

### Changes Made

**Total Statements Converted: 38**

| File | Statements Changed | Notes |
|------|-------------------|-------|
| `check_process.c` | 9 | Added `#include <stdbool.h>` and `#include <stdint.h>` |
| `config.c` | 3 | Already had interface.h include |
| `system_init.c` | 12 | All imx_printf statements converted |
| `set_serial.c` | 2 | Both imx_printf statements converted |
| `que_manager.c` | 5 | More statements found than initially estimated |
| `var_data.c` | 3 | More statements found than initially estimated |
| `imx_memory.c` | 1 | imx_cli_print converted to imx_cli_log_printf |
| `cli.c` | 2 | Both imx_cli_print and imx_printf converted |

### Build Status

- **Initial Build**: Failed due to missing includes in check_process.c
- **Fix Applied**: Added `<stdbool.h>` and `<stdint.h>` to check_process.c
- **Final Build**: SUCCESS - 100% compiled, FC-1 binary created

### Test Results

*(Pending - to be tested on target device)*

**Test Plan Document**: [debug_initialization_test_plan.md](debug_initialization_test_plan.md)

### Notes

1. The actual count of statements was higher than the original estimate (38 vs ~32)
2. One header fix was required: check_process.c needed stdbool.h and stdint.h
3. The cast `(unsigned long)cli_handler` was added in cli.c for format specifier compatibility

---

*Document created: 2026-01-02*
*Implementation completed: 2026-01-03*
