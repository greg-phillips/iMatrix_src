<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/investigate_Handler_stuck.yaml
Generated on: 2026-01-01 20:02 UTC
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Investigate FC-1 Handler Stuck in Loop - 24 Hour Stability Test

**Date:** 2026-01-01
**Branch:** debug/investigate_handler_stuck

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

- /home/greg/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md
- /home/greg/iMatrix/iMatrix_Client/docs/ssh_access_to_Fleet_Connect.md
- /home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

This is a stability validation test, not a development task.
Document results at each 4-hour interval.
Final deliverable: PASS (24hr clean) or FAIL (with stuck details)

## Task

Monitor the FC-1/iMatrix system for 24 continuous hours to verify the handler
does not become stuck in a loop.

**Connection:**
1. Connect via SSH (see ssh_access_to_Fleet_Connect.md)
2. Connect to CLI using minicom to the console symlink

**Verification Commands:**
- Main CLI (>) "s" command - verify MAIN_IMATRIX_NORMAL state
- Main CLI (>) "threads" or "threads -v" - check for stuck warnings
- App CLI (app>) "s" command - verify CAN controller registered
- App CLI (app>) "loopstatus" - detect loop conditions

**CLI Mode Switching:**
- Type "app" to enter app CLI mode (prompt changes to "app>")
- Type "exit" or press <tab> to return to main CLI

**Monitoring Schedule:**
Check status every 4 hours (6 checks total over 24 hours)

**Success Criteria:**
- No "WARNING: Handler stuck" messages
- No "BLOCKING IN:" messages  
- Timer status not showing persistent OVERRUN
- Boot count unchanged (no unexpected reboots)

**Failure Indicators:**
- "WARNING: Handler stuck at 'Before imx_process()' for XXXXX ms!"
- "BLOCKING IN: imatrix_upload() (position 50)"
- "GPS Nema serial data processing failure" (frequent occurrences)

**If Stuck Detected:** Document handler position, time stuck, blocking function,
and timestamp. Test is FAILED.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/investigate_handler_stuck.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/investigate_Handler_stuck.yaml
**Generated:** 2026-01-01 20:02 UTC