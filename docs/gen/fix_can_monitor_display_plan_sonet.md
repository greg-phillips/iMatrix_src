<!--
AUTO-GENERATED PROMPT
Generated from: specs/dev/display_fix_prompt.md
Generated on: 2025-11-19
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Fix CAN monitor display

**Date:** 2025-11-19
**Branch:** bugfix/can-monitor-truncation

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

- Fleet-Connect-1/CLAUDE.md - Project-specific development guidelines
- iMatrix/CLAUDE.md - Core library documentation
- iMatrix/cli/cli_can_monitor.c - CAN monitor CLI implementation (PRIMARY FILE TO FIX)

use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Additional Notes

- Issue reported with Ethernet CAN BUS logical bus display truncation
- Current display shows only 37 of potential 68 lines
- The display is being cut off prematurely

## Task

Fix the truncation of the "can monitor" command.
Currently display is truncated - display full output of the command

Steps:
1. Review current output:
```
+--------------------------- CAN Bus Monitor ---------------------------+
| Last Updated: 20:27:21.534                                              |
+-----------------------------------------------------------------------+
+-----------------------------------------------------------------------+
| Physical Buses                                                        |
+-----------------------------------------------------------------------+
+-----------------------------------+-----------------------------------+
| CAN 0                             | CAN 1                             |
+-----------------------------------+-----------------------------------+
| Status:      Closed               | Status:      Closed               |
| RX:              0 fps (-)        | RX:              0 fps (-)        |
| TX:              0 fps (-)        | TX:              0 fps (-)        |
| RX Rate:            0 B/s         | RX Rate:            0 B/s         |
| TX Rate:            0 B/s         | TX Rate:            0 B/s         |
| RX Total:             0 B         | RX Total:             0 B         |
| TX Total:             0 B         | TX Total:             0 B         |
| Errors:               0           | Errors:               0           |
| Drops:                0           | Drops:                0           |
| Buffer:      [----------]   0%    | Buffer:      [----------]   0%    |
| Peak Buf:      0% (0/4000)        | Peak Buf:      0% (0/4000)        |
+-----------------------------------+-----------------------------------+
+-----------------------------------------------------------------------+
| Ethernet CAN Server (Bus 2)                                           |
+-----------------------------------------------------------------------+
+-----------------------------------+-----------------------------------+
| Status:      Running              | Format:      APTERA               |
| Connection:  Open                 | Virt Buses:  2                    |
| RX:            829 fps (^)        | TX:              0 fps (-)        |
| RX Rate:        6.17 KB/s         | TX Rate:            0 B/s         |
| RX Total:         7.37 MB         | TX Total:             0 B         |
| Errors:               0           | Malformed:            0           |
| Drops:           0 (0/s)          | Buffer:      [----------]   0%    |
| Peak Buf:      0% (2/4000)        |                                   |
+-----------------------------------+-----------------------------------+
+-----------------------------------------------------------------------+
| Logical Buses on Ethernet                                             |
+-----------------------------------------------------------------------+

Lines 1-37 of 68 | RUNNING | Press '?' for help, 'q' to quit
```

2. Note only 37 of potential 68 lines are being displayed
3. Do not display blank lines - just generate output without unnecessary blank lines
4. Ensure full output is shown without truncation

### Files to Modify:
- iMatrix/cli/cli_can_monitor.c

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, ***docs/gen/fix_can_monitor_display_plan.md***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** specs/dev/display_fix_prompt.md
**Generated:** 2025-11-19
