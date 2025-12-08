# Upload Source Switching Bug Fix Plan

**Date**: 2025-12-08
**Author**: Claude Code
**Status**: Analysis Complete - Ready for Implementation
**Affects**: iMatrix Upload System, CAN Platform

## Executive Summary

Analysis of `imatrix_upload.c` and `imatrix_interface.c` revealed multiple bugs in the upload source rotation logic that can cause:
1. CAN devices being skipped during upload cycles
2. Inefficient/confusing code structure in `imx_set_csb_vars()`

## Bugs Identified

### Bug 1: Missing `can_imx_upload_init()` Call (CRITICAL)

**Location**: `imatrix_upload.c:913-916`

**Problem**: When transitioning from `IMX_HOSTED_DEVICE` to `IMX_UPLOAD_CAN_DEVICE`, the `can_imx_upload_init()` function is NOT called, but it IS called when transitioning from `IMX_UPLOAD_BLE_DEVICE` to `IMX_UPLOAD_CAN_DEVICE`.

**Current Code**:
```c
// Line 907-916: HOSTED_DEVICE transition - MISSING init call!
else if (imatrix.upload_source == IMX_HOSTED_DEVICE)
{
    if (device_config.ble_scan == true)
    {
        imatrix.upload_source = IMX_UPLOAD_BLE_DEVICE;
    }
    else if (canbus_registered() == true)
    {
        imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;  // BUG: Missing can_imx_upload_init()!
    }
    ...
}

// Line 927-933: BLE_DEVICE transition - HAS init call
else if (imatrix.upload_source == IMX_UPLOAD_BLE_DEVICE)
{
    if (canbus_registered() == true)
    {
        can_imx_upload_init();  // Correctly initializes cs_index = 0
        imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;
    }
    ...
}
```

**Impact**:
- When BLE is disabled, the transition path is: GATEWAY → HOSTED_DEVICE → CAN_DEVICE
- `can_imx_upload_init()` sets `cs_index = 0` to start from the first CAN device
- Without this call, `cs_index` retains its previous value from the last cycle
- CAN devices may be skipped or processed out of order

**Fix**: Add `can_imx_upload_init()` call before transitioning to CAN_DEVICE from HOSTED_DEVICE:
```c
else if (canbus_registered() == true)
{
    can_imx_upload_init();  // ADD THIS LINE
    imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;
}
```

### Bug 2: Redundant Gateway Data Setting in `imx_set_csb_vars()` (MINOR)

**Location**: `imatrix_interface.c:2138-2140`

**Problem**: The function unconditionally sets csb/csd to Gateway data BEFORE checking the upload_source parameter. This is then overwritten for non-Gateway sources inside the conditional block.

**Current Code**:
```c
void imx_set_csb_vars(imatrix_upload_source_t upload_source, ...)
{
    /* Initialize outputs to safe defaults */
    if (csb) *csb = NULL;
    if (csd) *csd = NULL;
    if (no_items) *no_items = 0;

    /* Basic case - always set csb and csd for gateway */  // MISLEADING COMMENT
    if (csb) *csb = imx_get_csb(type);  // Unconditional gateway data
    if (csd) *csd = imx_get_csd(type);  // Unconditional gateway data

    /* Extended functionality only when needed */
    if (no_items || device_updates) {
        if (upload_source == IMX_UPLOAD_GATEWAY) {
            // Uses gateway data (already set above - redundant)
        }
        else if (upload_source == IMX_HOSTED_DEVICE) {
            // Overwrites with host data
            if (csb) *csb = get_host_cb();
            ...
        }
        ...
    }
}
```

**Impact**:
- Wastes CPU cycles setting gateway data that gets immediately overwritten
- Misleading comment suggests intent but is factually incorrect
- If caller passes NULL for both `no_items` and `device_updates`, function returns Gateway data regardless of `upload_source`

**Fix**: Restructure to only set appropriate data based on upload_source:
```c
void imx_set_csb_vars(imatrix_upload_source_t upload_source, ...)
{
    /* Initialize outputs to safe defaults */
    if (csb) *csb = NULL;
    if (csd) *csd = NULL;
    if (no_items) *no_items = 0;

#ifdef CAN_PLATFORM
    if (upload_source == IMX_UPLOAD_GATEWAY) {
        if (csb) *csb = imx_get_csb(type);
        if (csd) *csd = imx_get_csd(type);
        if (no_items) *no_items = imx_peripheral_no_items(type);
        if (device_updates) {
            device_updates->check_in_period = device_config.check_in_period;
            device_updates->last_sent_time = icb.last_sent_time;
            device_updates->send_batch = icb.send_batch;
        }
    }
    else if (upload_source == IMX_HOSTED_DEVICE) {
        // Set host data based on type
        ...
    }
    else if (upload_source == IMX_UPLOAD_CAN_DEVICE) {
        // Set CAN data based on type
        ...
    }
#else
    // Non-CAN platforms only have gateway
    if (csb) *csb = imx_get_csb(type);
    if (csd) *csd = imx_get_csd(type);
    if (no_items) *no_items = imx_peripheral_no_items(type);
    ...
#endif
}
```

## Implementation Plan

### Phase 1: Critical Fix (Bug 1)

1. **File**: `iMatrix/imatrix_upload/imatrix_upload.c`
2. **Location**: Line ~915 (inside `IMX_HOSTED_DEVICE` transition block)
3. **Change**: Add `can_imx_upload_init();` before setting `imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;`

```c
else if (imatrix.upload_source == IMX_HOSTED_DEVICE)
{
    if (device_config.ble_scan == true)
    {
        imatrix.upload_source = IMX_UPLOAD_BLE_DEVICE;
    }
    else if (canbus_registered() == true)
    {
        can_imx_upload_init();  // ADD: Initialize CAN upload state
        imatrix.upload_source = IMX_UPLOAD_CAN_DEVICE;
    }
    else
    {
        imatrix.upload_source = IMX_UPLOAD_GATEWAY;
    }
}
```

### Phase 2: Code Cleanup (Bug 2) - Optional

1. **File**: `iMatrix/imatrix_interface.c`
2. **Location**: `imx_set_csb_vars()` function (~line 2127)
3. **Change**: Restructure to eliminate redundant gateway data setting

This is a larger refactor and can be deferred if desired.

## Testing Requirements

1. **Test with BLE disabled**:
   - Verify GATEWAY → HOSTED_DEVICE → CAN_DEVICE transition
   - Confirm CAN devices are processed from index 0 each cycle

2. **Test with BLE enabled**:
   - Verify GATEWAY → HOSTED_DEVICE → BLE_DEVICE → CAN_DEVICE transition
   - Confirm no regression in existing behavior

3. **Log verification**:
   - Add debug logging to confirm `can_imx_upload_init()` is called
   - Verify `cs_index` is reset to 0 on each CAN upload cycle

## Risk Assessment

- **Bug 1 Fix**: Low risk - adds a single function call that was already present in similar code path
- **Bug 2 Fix**: Medium risk - restructures function used throughout codebase; recommend deferring until more testing

## References

- `iMatrix/imatrix_upload/imatrix_upload.c:887-976` - Upload source rotation logic
- `iMatrix/imatrix_interface.c:2127-2232` - `imx_set_csb_vars()` implementation
- `iMatrix/canbus/can_imx_upload.c:258-260` - `can_imx_upload_init()` implementation
- `docs/archive/MM2_Upload_Source_Mismatch_Bug_Fix.md` - Previous MM2 upload fixes
