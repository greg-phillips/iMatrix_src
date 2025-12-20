<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/fix_net_interface_link_status.yaml
Generated on: 2025-12-18
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Review net command output

**Date:** 2025-12-18
**Branch:** debug/fix_net_interface_link_status

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

- iMatrix/networking/ - Network management and connectivity
- iMatrix/cli/ - Command line interface implementation
- iMatrix/IMX_Platform/LINUX_Platform/ - Linux platform implementation

Use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

The net command output for the section INTERFACE LINK STATUS pauses after outputting the eth0 line for several seconds. It then shows as ACTIVE - Not configured.

This is incorrect as the interface is clearly active and has an IP address.

Determine why this is happening and fix it.

### Sample output:
```
+=============================================================================================================+
|                                            NETWORK MANAGER STATE                                            |
+=============================================================================================================+
| Status: ONLINE  | State: NET_ONLINE_CHECK_RESULTS | Interface: wlan0 | Duration: 24:51:24 | DTLS: OK           |
+=============================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDRESS      | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+-----------------+-------------------+
| eth0      | NO      | NO      | NO      |     0 |       0 | NONE      | 192.168.7.1     | NONE              |
| wlan0     | YES     | NO      | YES     |    10 |      49 | NONE      | 10.2.0.192      | 2990 ms ago       |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE            | NONE              |
+=============================================================================================================+
|                                            INTERFACE LINK STATUS                                            |
+=============================================================================================================+
| eth0      | INACTIVE - Link up (100Mb/s)                                                                    |
| wlan0     | ACTIVE - Not configured                                                                         |
| ppp0      | INACTIVE - Daemon not running                                                                   |
+=============================================================================================================+
```

### Issues to investigate:

1. **Pause after eth0 line**: Why does the output pause for several seconds after displaying eth0?
2. **wlan0 shows "ACTIVE - Not configured"**: This is incorrect - wlan0 is clearly active with IP 10.2.0.192 and LINK_UP=YES
3. **Inconsistency**: The top table shows wlan0 as active with proper configuration, but the INTERFACE LINK STATUS section shows contradictory information

Ask any questions you need to before starting.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/fix_net_interface_link_status_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/fix_net_interface_link_status.yaml
**Generated:** 2025-12-18
