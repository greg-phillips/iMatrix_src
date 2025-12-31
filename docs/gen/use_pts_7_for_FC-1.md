<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/use_pts_7_for_FC-1.yaml
Generated on: 2025-12-30
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Always use pts/7 for FC-1

**Date:** 2025-12-30
**Branch:** feature/use_pts_7_for_FC-1

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

**Documentation:**
- /home/greg/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md
- /home/greg/iMatrix/iMatrix_Client/docs/ssh_access_to_Fleet_Connect.md

**Source Files:**
- iMatrix/cli/interface.c (focus: logging system implementation)

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

- Use the microcom command to connect to the FC-1 application and verify that pts/7 is always used. if pts/7 is not available, delete the pts/7 entry as this applicaton only has one instance of the FC-1 application running.

## Task

## Objective
Always use pts/7 for FC-1.

## Requirements
1. Read and understand the CLI and Debug system from the documentation
2. Always use pts/7 for FC-1.
3. After implementation allow me to review before proceeding with testing.

## Verification
1. SSH into the FC-1 device (see ssh_access_to_Fleet_Connect.md)
2. Run the FC-1 application
3. Verify that pts/7 is available and always used for FC-1.
4. use the microcom command to connect to the FC-1 application and verify that pts/7 is always used.

**Files to Modify:**
- Fleet-Connect-1/init/imx_client_init.c

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/use_pts_7_for_FC-1_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/use_pts_7_for_FC-1.yaml
**Generated:** 2025-12-30
