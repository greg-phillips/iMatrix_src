# IMX Command Output Issue - Implementation Plan

**Date**: 2026-01-01
**Document Version**: 1.1
**Status**: Implementation Complete - Ready for Testing
**Author**: Claude Code Analysis
**Branch**: feature/imx_command_output_issue

## Original Branches (Before Work)
- **iMatrix**: `feature/csr_process_fix`
- **Fleet-Connect-1**: `Aptera_1_Clean`

## Work Branches
- **iMatrix**: `feature/imx_command_output_issue`
- **Fleet-Connect-1**: `feature/imx_command_output_issue`

---

## 1. Problem Description

The `imx` CLI command outputs repeated sections of "Controls Parameters", "Sensors Parameters", and "Variables Parameters" headers, creating confusing duplicate output. The expected behavior is to show each device source's data once, but the actual output shows:

1. Gateway data (correct)
2. Multiple empty "Controls/Sensors/Variables Parameters" headers (BUG)
3. Gateway data appears to repeat
4. Host Device header
5. CAN Device header

## 2. Root Cause Analysis

### 2.1 Code Location
- **File**: `iMatrix/imatrix_upload/imatrix_upload.c`
- **Function**: `cli_imatrix()` (around lines 1950-2204)

### 2.2 Identified Issue: Missing BLE_DEVICE Handling in CLI

The `cli_imatrix()` function iterates through upload sources (GATEWAY, HOSTED_DEVICE, CAN_DEVICE) but does **not handle `IMX_UPLOAD_BLE_DEVICE`** (enum value 2).

#### Upload Source Enum (common.h:1202-1213):
```c
typedef enum imatrix_upload_source {
    IMX_UPLOAD_GATEWAY = 0,         // 0
    IMX_UPLOAD_HOSTED_DEVICE,        // 1
    IMX_UPLOAD_BLE_DEVICE,           // 2  <-- NOT HANDLED IN CLI!
#ifdef APPLIANCE_GATEWAY
    IMX_UPLOAD_APPLIANCE_DEVICE,
#endif
#ifdef CAN_PLATFORM
    IMX_UPLOAD_CAN_DEVICE,           // 3
#endif
    IMX_UPLOAD_NO_SOURCES,
} imatrix_upload_source_t;
```

#### CLI Source Handling (lines 2018-2042):
- Handles `IMX_UPLOAD_GATEWAY` - prints header, skip=false
- Handles `IMX_UPLOAD_HOSTED_DEVICE` (CAN_PLATFORM) - prints header, skip=true
- Handles `IMX_UPLOAD_CAN_DEVICE` (CAN_PLATFORM) - prints header, skip=true
- **Does NOT handle `IMX_UPLOAD_BLE_DEVICE`!**

#### CLI Source Transition (lines 2173-2200):
- GATEWAY → HOSTED_DEVICE
- HOSTED_DEVICE → CAN_DEVICE
- CAN_DEVICE → complete
- **No handling for BLE_DEVICE - would cause infinite loop!**

### 2.3 Impact Analysis

When the `cli_imatrix()` function encounters `IMX_UPLOAD_BLE_DEVICE` as the upload source:

1. **No matching condition** in the if/else chain → `skip` stays `false`
2. **Inner for loop runs** printing "Controls/Sensors/Variables Parameters" headers
3. **`imx_set_csb_vars()` returns `no_items = 0`** for BLE_DEVICE (not handled)
4. **Headers print but no items** because no_items = 0
5. **Transition doesn't match** any condition → `complete` stays `false`
6. **Loop continues** with same upload_source → repeated headers

### 2.4 Potential Race Condition

The variable `imatrix.upload_source` is a global variable used by both:
- The main upload state machine (which DOES handle BLE_DEVICE)
- The CLI function (which does NOT handle BLE_DEVICE)

If the CLI is called while the main upload process is active, a race condition could occur where the main upload modifies `imatrix.upload_source` during the CLI's iteration loop.

## 3. Proposed Fix

### 3.1 Option A: Add BLE_DEVICE Handling to CLI (Recommended)

Add proper handling for `IMX_UPLOAD_BLE_DEVICE` in both:
1. The source identification section (lines 2018-2042)
2. The source transition section (lines 2173-2200)

This aligns the CLI function with the main upload function's handling.

### 3.2 Option B: Skip BLE_DEVICE in CLI Transition

Add a fallback in the transition logic to skip BLE_DEVICE and proceed to the next source.

### 3.3 Option C: Add Fallback for Unhandled Sources

Add a default case that skips unhandled sources to prevent infinite loops.

## 4. Detailed Implementation (Option A)

### 4.1 Modify Source Identification (lines 2018-2042)

Add handling for BLE_DEVICE after HOSTED_DEVICE:

```c
#ifdef CAN_PLATFORM
        else if (imatrix.upload_source == IMX_UPLOAD_HOSTED_DEVICE)
        {
            snprintf(device_serial_number, IMX_DEVICE_SERIAL_NUMBER_LENGTH + 1, "%u", get_host_serial_no());
            imx_cli_print("Host Device %s Serial No: %s, Control/Sensor Data. Pending upload - (P):\r\n", get_host_name(), device_serial_number);
            skip = true;
        }
        else if (imatrix.upload_source == IMX_UPLOAD_BLE_DEVICE)
        {
            // BLE devices are displayed elsewhere or skip for now
            skip = true;
        }
        else if (imatrix.upload_source == IMX_UPLOAD_CAN_DEVICE)
        {
            // existing code...
        }
#endif
```

### 4.2 Modify Source Transition (lines 2173-2200)

Add BLE_DEVICE transition:

```c
#ifdef CAN_PLATFORM
        if (imatrix.upload_source == IMX_UPLOAD_GATEWAY)
        {
            imatrix.upload_source = IMX_UPLOAD_HOSTED_DEVICE;
        }
        else if (imatrix.upload_source == IMX_UPLOAD_HOSTED_DEVICE)
        {
            imatrix.upload_source = IMX_UPLOAD_BLE_DEVICE;  // Go through BLE first
        }
        else if (imatrix.upload_source == IMX_UPLOAD_BLE_DEVICE)
        {
            imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;
        }
        else if (imatrix.upload_source == IMX_UPLOAD_CAN_DEVICE)
        {
            complete = true;
        }
#endif
```

### 4.3 Alternative: Skip BLE in CLI (Simpler)

If BLE device details should not be shown in CLI:

```c
#ifdef CAN_PLATFORM
        if (imatrix.upload_source == IMX_UPLOAD_GATEWAY)
        {
            imatrix.upload_source = IMX_UPLOAD_HOSTED_DEVICE;
        }
        else if (imatrix.upload_source == IMX_UPLOAD_HOSTED_DEVICE ||
                 imatrix.upload_source == IMX_UPLOAD_BLE_DEVICE)  // Skip BLE
        {
            imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;
        }
        else if (imatrix.upload_source == IMX_UPLOAD_CAN_DEVICE)
        {
            complete = true;
        }
        else
        {
            // Fallback: unknown source, mark complete to prevent infinite loop
            complete = true;
        }
#endif
```

## 5. Todo List

- [x] 1. Confirm root cause with Greg
- [x] 2. Determine if BLE device data should be displayed in CLI (Answer: Skip silently)
- [x] 3. Implement chosen fix option (Option B+C: Skip BLE + Add fallback)
- [x] 4. Build and verify no compilation errors/warnings
- [ ] 5. Test on hardware using `imx` command
- [ ] 6. Verify fix resolves the repeated output issue
- [x] 7. Final clean build verification
- [ ] 8. Merge branch and update documentation

## 6. Questions for Greg

Before implementing, please confirm:

1. **Should BLE device data be displayed** in the `imx` CLI output? (Like Host Device and CAN Device show their headers)

2. **Is there concurrent access** to `imatrix.upload_source`? (CLI called from separate thread while upload is running?)

3. **Is `device_config.ble_scan` typically enabled** on the production gateway?

4. **Preferred fix approach**:
   - A) Full BLE_DEVICE handling in CLI (displays BLE info)
   - B) Skip BLE_DEVICE silently (just fix the loop)
   - C) Add general fallback for unhandled sources

---

## Build Commands

```bash
# Build Fleet-Connect-1
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
make -j4

# Deploy and test
cd /home/greg/iMatrix/iMatrix_Client/scripts
./fc1 push -run
```

## Test Procedure

Per `/home/greg/iMatrix/iMatrix_Client/docs/testing_fc_1_application.md`:

1. SSH to gateway: `ssh -p 22222 root@192.168.7.1`
2. Connect to CLI: `nc 192.168.7.1 23` or `microcom /usr/qk/etc/sv/FC-1/console`
3. Run: `imx`
4. Verify output shows:
   - Gateway header and data (once)
   - Host Device header (once)
   - CAN Device header (once)
   - NO repeated Controls/Sensors/Variables sections

---

## 7. Implementation Summary

### 7.1 Changes Made

**File Modified**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Change 1 - Source Identification Section (after line 2040)**:
Added fallback `else` block to set `skip = true` for unhandled upload sources:
```c
else
{
    /* Skip unhandled upload sources (e.g., BLE_DEVICE) to prevent repeated output */
    skip = true;
}
```

**Change 2 - Source Transition Section (lines 2188-2216)**:
Added fallback `else` blocks in all three conditional compilation branches:
- `#ifdef CAN_PLATFORM`: Fallback transitions to `IMX_UPLOAD_CAN_DEVICE`
- `#elif defined(APPLIANCE_GATEWAY)`: Fallback marks `complete = true`
- `#else`: Fallback marks `complete = true`

### 7.2 How The Fix Works

1. **Prevents Empty Headers**: When `IMX_UPLOAD_BLE_DEVICE` is encountered, `skip = true` prevents printing empty "Controls/Sensors/Variables Parameters" headers

2. **Prevents Infinite Loop**: The fallback `else` block in the transition section ensures the loop progresses to the next source or completes, rather than staying stuck on an unhandled source

### 7.3 Build Verification

- Clean build completed successfully
- Zero new compilation errors
- Zero new compilation warnings
- FC-1 binary built: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1`

### 7.4 Git Commit

- **Branch**: `feature/imx_command_output_issue`
- **Commit**: `8d31370e` - "Fix repeated Controls/Sensors/Variables output in imx CLI command"
- **Files Changed**: 1 file, 20 insertions

### 7.5 Pending

- Hardware testing on QConnect gateway
- Merge to original branches after successful hardware test

---

**Plan Created By**: Claude Code
**Date**: 2026-01-01
**Implementation Date**: 2026-01-01
