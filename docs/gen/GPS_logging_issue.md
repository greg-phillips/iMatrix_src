<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/GPS_logging_issue.yaml
Generated on: 2026-01-04
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: During testing the GPS logging is not working correctly

**Date:** 2026-01-04
**Branch:** feature/GPS_logging_issue

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

- iMatrix/location/get_location.c
- iMatrix/location/process_nmea.c

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

During testing we have found the logging of the GPS data is generating many invalid values.

Review this file: `/home/greg/iMatrix/iMatrix_Client/tools/142994297_2_3_20260102.json`

From my analysis I see the following:

### Data Quality & Anomalies

While most coordinates appear to center around 38.90° N, 119.96° W (near Lake Tahoe, Nevada/California border), there are several significant data integrity issues:

### 1. Extreme Outliers & Measurement Errors

The statistics reveal physical impossibilities for coordinate data:

- **Latitude Max (1974)**: Latitude cannot exceed 90°. This value is likely a transmission error or a different data type accidentally logged in this field.
- **Latitude Min (-119.9626)**: This value is numerically identical to the standard Longitude for this set, suggesting a "flip" where longitude data was recorded in the latitude column.
- **Longitude Max (38.9019)**: Similarly, this matches the standard Latitude for this set, indicating another column-flip error.

### 2. Zero-Value Clusters

There are numerous instances where both Latitude and Longitude drop to 0.0 simultaneously (e.g., at 12:39:51Z on Jan 2nd).

**Impact**: This usually indicates a loss of GPS fix or a sensor "warm-up" period where valid data was not yet acquired.

### 3. Precision Shifts

Towards the end of the log (starting around 2026-01-03T15:12:53Z), the latitude values shift to extremely small scientific notations (e.g., 9.1835e-41) while Longitude stays at exactly 0.

This suggests a sensor failure or a software bug in the data export process.

### Key Observations

- **Primary Location**: When the sensor is stable, the device is located at approximately 38.9018° N, 119.9625° W.
- **Data Reliability**: The data is highly unstable. Of the 7,329 points, a significant portion contains either zeros, column-swapped values, or impossible outliers (1974).

### Files to Review

1. `/home/greg/iMatrix/iMatrix_Client/iMatrix/location/get_location.c`
2. `/home/greg/iMatrix/iMatrix_Client/iMatrix/location/process_nmea.c`

Find the issue and fix it.

**Ask any questions you need to before starting the work.**

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/GPS_logging_issue_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/GPS_logging_issue.yaml
**Generated:** 2026-01-04

---

## ✅ IMPLEMENTATION COMPLETE

**Completed:** 2026-01-04
**Commit:** `e1d5800a`
**Branch:** Merged to `Aptera_1_Clean` and pushed to remote

### Files Changed:
- `iMatrix/location/process_nmea.c` (+207/-51 lines)
- `iMatrix/location/process_nmea.h` (+1 line)
- `iMatrix/location/get_location.c` (+1 line)

### Solution:
Added multi-layer GPS coordinate validation to prevent invalid data from being stored/uploaded:
1. Coordinate range validation (lat: -90 to 90, lon: -180 to 180)
2. Direction indicator validation (N/S, E/W)
3. Fix quality gating (minimum quality = 1)
4. Raw NMEA format validation
5. Empty field rejection
6. Rejected coordinate counter (viewable via `loc` CLI command)

**See detailed plan:** `docs/gen/GPS_logging_issue_plan.md`
