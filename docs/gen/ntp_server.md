<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/ntp_server.yaml
Generated on: 2026-01-09
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Investigation Fleet-Connect-1 NTP Server options

**Date:** 2026-01-09
**Branch:** feature/ntp_server

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

- /home/greg/iMatrix/iMatrix_Client/docs/ssh_access_to_Fleet_Connect.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Connect to the Fleet-Connect-1 board using SSH and check the NTP server options.
Detail the commands in the plan.

**Target:** The FC-1 Gateway board.

**Problem:** The NTP server is not working.

**Objective:** Using the SSH connection, determine the missing configuration files.

## Questions

Ask any questions needed to clarify the task before proceeding.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/ntp_server_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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

**Additional Deliverable:**
Report on how to configure the NTP server on the Fleet-Connect-1 board.
This needs to be done using the code on startup assuming the system is a virgin installation without any configuration for NTP Server.

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/ntp_server.yaml
**Generated:** 2026-01-09
