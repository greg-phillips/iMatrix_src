<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/TSD_record_fault.yaml
Generated on: 2025-12-13
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Bug: TSD record fault.

**Date:** 2025-12-13
**Branch:** bugfix/tsd_record_fault

---

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The wifi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following

- iMatrix/cs_ctrl/memory_manager.c
- iMatrix/cs_ctrl/mm2_write.c
- iMatrix/cs_ctrl/mm2_read.c
- iMatrix/cs_ctrl/hal_sample.c
- iMatrix/cs_ctrl/hal_event.c
- iMatrix/imatrix_upload/imx_upload.c
- docs/MM2_Bug_Analysis_Plan.md (similar bug previously fixed)

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

A similar issue was previously detected and fixed. The plan that was used to successfully fix the issue is documented in: **docs/MM2_Bug_Analysis_Plan.md**. This plan should be reviewed as the current issue may have a similar root cause (sector type mismatch, dual-write problem, etc.).

## Task

The following error is being reported:
```
[00:05:00.864] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 11, received: 0
[00:05:10.873] IMX_UPLOAD: ERROR: Upload Source: GatewayFailed to read all event data for: Latitude, result: 34:NO DATA, requested: 9, received: 0
[00:05:10.875] IMX_UPLOAD: ERROR: Upload Source: GatewayFailed to read all event data for: Longitude, result: 34:NO DATA, requested: 9, received: 0
[00:05:10.877] IMX_UPLOAD: ERROR: Upload Source: GatewayFailed to read all event data for: Altitude, result: 34:NO DATA, requested: 9, received: 0
[00:05:10.880] IMX_UPLOAD: ERROR: Upload Source: GatewayFailed to read all event data for: Speed, result: 34:NO DATA, requested: 9, received: 0
[00:15:02.263] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 20, received: 0
[00:25:04.118] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 24, received: 0
[00:35:04.758] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 27, received: 0
[00:50:14.630] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 11, received: 0
[01:00:06.540] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 21, received: 0
[01:06:01.109] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Cellular RX Data Bps, result: 34:NO DATA, requested: 5, received: 0
[01:10:08.173] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 19, received: 0
[01:16:03.324] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Cellular RX Data Bps, result: 34:NO DATA, requested: 5, received: 0
[01:40:10.204] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 4, received: 0
[01:45:10.212] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 4, received: 0
[01:50:10.428] IMX_UPLOAD: ERROR: Failed to read all TSD data for: Vehicle_Speed, result: 34:NO DATA, requested: 8, received: 0
```

### Key Observations

1. **Error code 34 = IMX_NO_DATA** - The memory manager reports no data available
2. **Multiple sensors affected**: Vehicle_Speed, Latitude, Longitude, Altitude, Speed, Cellular RX Data Bps
3. **Data is being requested** (11, 9, 20, etc. records requested) **but 0 received**
4. **Both TSD and EVT types failing** - "Failed to read all TSD data" and "Failed to read all event data"

### Similar Previous Bug

Review **docs/MM2_Bug_Analysis_Plan.md** which documents a similar GPS_Latitude read failure. The root cause was:

- **Sector type mismatch**: Sensors written via two different code paths (TSD vs EVT)
- **Dual-write problem**: GPS sensors were being written by both `imx_write_gps_location()` (EVT) and `imx_sample_csd_data()` (TSD)
- **Result**: Sector allocated as EVT but data written as TSD, causing read failures

### Investigation Steps

1. Determine if Vehicle_Speed is being written via multiple code paths
2. Check if there's a sector type mismatch for affected sensors
3. Verify the sensor configuration (sample_rate, poll_rate, enabled flags)
4. Review the write and read paths for TSD data
5. Check if a similar skip pattern is needed for Vehicle_Speed and other CAN sensors

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/tsd_record_fault_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.
8. Merge the branch back into the original branch.
9. Update all documents with relevant details

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/TSD_record_fault.yaml
**Generated:** 2025-12-13
