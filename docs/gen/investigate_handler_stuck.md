<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/investigate_Handler stuck.yaml
Generated on: 2025-12-29
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: The FC-1 and iMatrix system has many logs to detect when the system is stuck in a loop.

**Date:** 2025-12-29
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

- iMatrix/CLAUDE.md
- Fleet-Connect-1/CLAUDE.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Generate a detailed plan to investigate the problem and fix it.
The command provided is "loopstatus" and it is used to detect when the system is stuck in a loop.
The output of the command is as follows:
```
==================== MAIN LOOP STATUS ====================
Handler Position:    Before imx_process() (0)
Time at Handler:     38218888 ms

imx_process() Pos:   50
Time at imx_proc:    38218888 ms

do_everything() Pos: EXIT (19)
Time at Position:    38218988 ms
Loop Executions:     39852

*** WARNING: Handler stuck at 'Before imx_process()' for 38218888 ms! ***
*** BLOCKING IN: imx_process() function (position 50) ***
==========================================================
```

Ask any questions you need to before starting.

### Analysis of the Problem

The `loopstatus` output reveals:
1. **Handler Position 0** - Stuck "Before imx_process()" for 38218888 ms (~10.6 hours)
2. **imx_process() Position 50** - The blocking is occurring inside `imx_process()` at position 50
3. **do_everything() Position 19 (EXIT)** - The FC-1 side completed normally
4. **39852 loop executions** before getting stuck

The investigation should focus on:
- What code executes at position 50 in `imx_process()`
- What could cause it to block indefinitely
- Whether this is related to networking, storage, or another subsystem

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/investigate_handler_stuck_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/investigate_Handler stuck.yaml
**Generated:** 2025-12-29
