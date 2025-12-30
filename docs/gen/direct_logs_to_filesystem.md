<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/direct_all_logs_to_filesystem.yaml
Generated on: 2025-12-30
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Direct All Logs to Filesystem

**Date:** 2025-12-30
**Branch:** feature/filesystem-logging

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

Source files to review:
- iMatrix/cli/interface.c - focus: logging system implementation

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

Additional notes:
- Use the CLI debug flags to enable verbose logging during testing
- Consider existing log rotation libraries if available in the codebase
- Ensure thread-safe file operations for concurrent logging

## Task

## Objective
Modify the FC-1 logging system to direct all logs from the buffered system to the filesystem.

## Requirements
1. Read and understand the CLI and Debug system from the documentation
2. Analyze the current logging implementation in iMatrix/cli/interface.c
3. Implement filesystem logging with the following specifications:
   - Log directory: /var/log/
   - Log filename: fc-1.log
   - Rotation trigger: Daily OR on FC-1 application restart
   - Maximum file size: 10MB
   - Retention: Last 5 days OR maximum 100MB total

## Verification
1. SSH into the FC-1 device (see ssh_access_to_Fleet_Connect.md)
2. Run the FC-1 application
3. Verify logs are written to /var/log/fc-1.log
4. Test log rotation by restarting the application
5. Verify size limits and retention policy work correctly

Files to modify:
- iMatrix/cli/interface.c

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/direct_logs_to_filesystem_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/direct_all_logs_to_filesystem.yaml
**Generated:** 2025-12-30
