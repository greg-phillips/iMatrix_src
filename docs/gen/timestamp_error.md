<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/timestamp_error.yaml
Generated on: 2025-12-12
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: During development of the python script to decode debug CoAP output data we discovered that the timestamp is not correct.

**Date:** 2025-12-12
**Branch:** bugfix/timestamp_error

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

Read and understand the following:

- `docs/EVENT_SENSOR_Timestamp_Bug_Report.md` - Bug report detailing the timestamp issue
- `iMatrix/storage.h` - Data structures including event_data_t
- `iMatrix/cs_ctrl/memory_manager*.c` - Event storage code
- `iMatrix/time/ck_time.c` - Time functions
- `iMatrix/cs_ctrl/mms_write.c` - Contains imx_write_gps_location
- `iMatrix/imatrix_upload/` - Upload serialization code

Use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Review the report docs/EVENT_SENSOR_Timestamp_Bug_Report.md and create a plan to fix the issue.
Specifically review all event generation code and the code that writes the event to the CoAP packet.
Look at the iMatrix/cs_ctrl/mms_write.c and the routine imx_write_gps_location
Generate a report of the issue and the proposed fix.

### Key Investigation Areas

1. **Search for Event Timestamp Assignment**
   ```bash
   grep -rn "utc_sample_time" iMatrix/
   grep -rn "event_data_t" iMatrix/
   grep -rn "EVENT_SENSOR\|EVENT_CONTROL" iMatrix/
   ```

2. **Check Time Source in Event Recording**
   - Verify code that populates `event_data_t.utc_sample_time` uses `ck_time_get_utc()` (correct)
   - NOT `imx_get_uptime_ms()` or similar uptime functions

3. **Compare with TSD_MS Implementation**
   - SENSOR_MS blocks work correctly with 64-bit `imx_utc_time_ms_t`
   - Compare how timestamps are set in working vs broken paths

### Bug Summary (from report)

- EVENT_SENSOR blocks contain invalid timestamps decoding to 1977 instead of 2025
- Raw value (~243 million) represents ~7.7 years of seconds (device uptime)
- SENSOR_MS blocks in same packet use correct 64-bit UTC timestamps
- Affected block types: EVENT_SENSOR (11), EVENT_CONTROL (10)
- Working block types: SENSOR_MS (12), CONTROL_MS (15)

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/timestamp_error_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/timestamp_error.yaml
**Generated:** 2025-12-12
