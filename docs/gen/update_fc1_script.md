<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/udpdate_fc1_script.yaml
Generated on: 2025-12-29
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: The fc1 script provides the ability to start/stop/restart the FC-1 application with the runsv service.

**Date:** 2025-12-29
**Branch:** feature/update_fc1_script

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

- scripts/fc1 - Host-side remote control script
- scripts/fc1_service.sh - Target-side service control script

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Current Implementation Notes

The fc1 script currently supports the following commands:
- `start` - Start FC-1 service on target
- `stop` - Stop FC-1 service on target
- `restart` - Restart FC-1 service
- `status` - Show service status
- `run [opts]` - Run FC-1 in foreground on target
- `log` - Show recent logs
- `deploy` - Deploy service script to target
- `ssh` - Open SSH session to target

The service uses runsv (runit supervision) at:
- Service directory: `/usr/qk/etc/sv/FC-1`
- Run script: `/usr/qk/etc/sv/FC-1/run`
- Log directory: `/var/log/FC-1/current`

## Task

Update the script to provide the ability to remove and add the FC-1 application to the runsv service.

Ask any questions you need to before starting.

### Files to Modify

- `scripts/fc1` - Host-side script (add new commands)
- `scripts/fc1_service.sh` - Target-side script (add service enable/disable logic)

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/update_fc1_script_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/udpdate_fc1_script.yaml
**Generated:** 2025-12-29
