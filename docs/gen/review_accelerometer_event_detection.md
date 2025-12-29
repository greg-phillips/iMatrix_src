<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/update_app_cli_order.yaml
Generated on: 2025-12-26
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Review Accelerometer event detection code

**Date:** 2025-12-26
**Branch:** feature/review-accelerometer-event-detection

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

- Fleet-Connect-1/hal/accel_process.c
- Fleet-Connect-1/docs/1180-3007_C_QConnect__Developer_Guide.pdf (accelerometer section, page 41+)

Use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. Keep it simple and maintainable.**

## Task

Read Fleet-Connect-1/hal/accel_process.c
Read Fleet-Connect-1/docs/1180-3007_C_QConnect__Developer_Guide.pdf and understand the accelerometer event detection code, starts on page 41

Propose best plan to monitor and manage the accelerometer event detection and sample rate code.

Ask any questions you need to before starting.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/review_accelerometer_event_detection_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/update_app_cli_order.yaml
**Generated:** 2025-12-26


Additions
  Observations/Potential Issues

  1. Duplicate #define SAMPLE_RATE_HZ at lines 86 and 95
  2. Bug in calibration (line 877): cal_z += max_filtered_x should be max_filtered_z
  3. Thread safety: Mutex lock/unlock patterns could be improved
  4. Vehicle thresholds hardcoded with placeholder get_vehicle_weight() returning 5000.0
  5. Missing hardware integration with QConnect's sysfs interface per documentation

 running this process in a separate thread to improve performance. Review current thresholds and sampling time to ensure best in class for telematics solution 
