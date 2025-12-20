<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/wlan0_failure.yaml
Generated on: 2025-12-17
Schema version: 1.0
Complexity level: moderate
Auto-populated sections: project, hardware, user, guidelines, references

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: WLAN 0 Failure analysis and fix

**Date:** 2025-12-17
**Branch:** debug/wlan0_failure
**Objective:** Analyze and fix WLAN0 failure in network manager

---

## Code Structure:

**iMatrix (Core Library):** Contains all core telematics functionality (data logging, comms, peripherals).

**Fleet-Connect-1 (Main Application):** Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH.
The wifi communications uses a combination Wi-Fi/Bluetooth chipset.
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following:

- docs/Network_Manager_Architecture.md - Network manager design and state machine documentation
- logs/net_fail1.txt - Log file showing the WLAN0 failure (NOTE: referenced as net_failure.txt in spec but actual file is net_fail1.txt)
- iMatrix/IMX_Platform/LINUX_Platform/networking/ - Network manager implementation directory

use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Network Manager Key Points (from CLAUDE.md)

Multi-interface network management with state machine control:
- Supports Ethernet, WiFi, Cellular (PPP), and more
- Opportunistic discovery for new interfaces
- DHCP client management with PID tracking
- Cooldown periods for interface stability

### Common Network Issues to Check

1. **Stuck States**: Check state transition validation
2. **IP Persistence**: Ensure DHCP clients killed with PID files
3. **Missing Interfaces**: Verify opportunistic discovery
4. **Segfaults**: Add bounds checking for INVALID_INTERFACE
5. **First Run Failures**: Check apply_interface_effects() deferral
6. **False Interface Failures**: Add test routes for non-default
7. **DHCP Status Wrong**: Check udhcpc not udhcpd

## Task

1. Review docs/Network_Manager_Architecture.md to understand network manager design
2. Review the log file logs/net_fail1.txt to understand the failure scenario
3. Review the code in iMatrix/IMX_Platform/LINUX_Platform/networking/ directory
4. Identify the root cause of the WLAN0 failure
5. Fix the failure
6. Detail the fix in the plan document
7. Ask any questions needed for clarification

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/wlan0_failure_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/wlan0_failure.yaml
**Generated:** 2025-12-17
**Auto-populated:** 5 sections
