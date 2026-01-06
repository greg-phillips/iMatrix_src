<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/program_not_running.yaml
Generated on: 2026-01-05
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Review the why the program is not running and provide a plan to fix it

**Date:** 2026-01-05
**Branch:** feature/review_program_not_running

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

- /home/greg/iMatrix/iMatrix_Client/docs/fc1_script_reference.md - FC-1 remote control script reference
- /home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md - SSH connection methods

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

The software has been deployed using the fc1 script. see: /home/greg/iMatrix/iMatrix_Client/docs/fc1_script_reference.md

The host device is on address: **10.2.0.169**

Use SSH to connect to the host device and review the logs. see: /home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md

The program is not running.

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/review_program_not_running_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/program_not_running.yaml
**Generated:** 2026-01-05
