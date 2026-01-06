<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/fix_console_messages.yaml
Generated on: 2026-01-04
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim While running the FC-1 application the console messages continue to show with errors

**Date:** 2026-01-04
**Branch:** feature/fix_console_messages

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
- /home/greg/iMatrix/iMatrix_Client/docs/fc1_script_reference.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Connect to the FC-1 application using the screen program.
the correct options are: screen /dev/ttyUSB0 115200
to exit the screen program press Ctrl+A then "\" then Y
Reset the FC-1 application by running the following command: scripts/fc1 restart
Monitor all the console messages and see if there are any errors.
If there are any errors, fix them by modifying the code in the FC-1 application.
If there are no errors, then the task is complete.

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/fix_console_messages_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/fix_console_messages.yaml
**Generated:** 2026-01-04
