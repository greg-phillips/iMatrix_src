# Investigation Plan: CS Command Status Display Bug

**Date:** 2025-12-28
**Branch:** debug/investigate_status_display
**Original Branches:** iMatrix: Aptera_1_Clean, Fleet-Connect-1: Aptera_1_Clean
**Status:** Implementation Complete

---

## Problem Statement

The 'cs' app command is not displaying the correct status for the poll and sample due times.

## Root Cause Analysis

### Bug Location
**File:** `iMatrix/cs_ctrl/common_config.c`
**Function:** `imx_print_status_entry()` (line 305)

### The Bug

```c
// Line 305-310 - BUG: Uses poll_rate instead of sample_rate in condition
if ((float)csb[i].poll_rate - (((float)current_time - (float)csd[i].last_sample_time)) > 0)
{
    imx_cli_print(" %10.2f",
                  (float)(csb[i].sample_rate - (current_time - csd[i].last_sample_time)) / 1000.0);
}
```

### Issue Description
- **Line 305 condition:** Uses `poll_rate` to check if sample is due
- **Line 309 calculation:** Correctly uses `sample_rate` to compute remaining time
- **Result:** Mismatch causes incorrect "Due Now" display or wrong values when `poll_rate != sample_rate`

### Expected Behavior
The sample due time should be calculated using `sample_rate`, not `poll_rate`:
- When `sample_rate - elapsed_time > 0`: Show remaining seconds until next sample
- When `sample_rate - elapsed_time <= 0`: Show "Due Now"

## Fix Strategy

### Simple Fix
Change line 305 from:
```c
if ((float)csb[i].poll_rate - (((float)current_time - (float)csd[i].last_sample_time)) > 0)
```
To:
```c
if ((float)csb[i].sample_rate - (((float)current_time - (float)csd[i].last_sample_time)) > 0)
```

## Todo List

- [x] Update plan document with bug analysis and fix strategy
- [x] Fix poll_rate vs sample_rate bug in common_config.c line 305
- [x] Build and verify no compilation errors or warnings
- [x] Merge branch back to Aptera_1_Clean

## Implementation Summary

**Work Completed:** 2025-12-28

### Changes Made
1. Fixed `imx_print_status_entry()` in `iMatrix/cs_ctrl/common_config.c` (line 305)
   - Changed condition from `poll_rate` to `sample_rate` for sample due time calculation
   - This ensures the "Sample in S" column displays correctly when poll_rate differs from sample_rate

### Files Modified
- `iMatrix/cs_ctrl/common_config.c` (1 line changed)

### Build Verification
- Zero compilation errors
- Zero compilation warnings
- Build completed successfully

---

**Plan Created By:** Claude Code
**Source Specification:** docs/prompt_work/investigate_status_display.yaml
**Generated:** 2025-12-28
