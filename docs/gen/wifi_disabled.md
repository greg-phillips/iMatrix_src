<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/wifif_disabled.yaml
Generated on: 2025-12-14
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim During Testing of the Networking system I noticed that the WiFi is disabled after a period of time.

**Date:** 2025-12-14
**Branch:** debug/wifi_disabled

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

- iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c
- iMatrix/IMX_Platform/LINUX_Platform/CLAUDE.md
- docs/Network_Manager_Architecture.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Review the code in the iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c file and create a plan to fix the issue.
The logic should never permanently disable the WiFi.
The status screen shows the WiFi as Cooldown as expired.
The logic should reenable the WiFi after expirataion.
Review the code in the iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c file and describe the logic fault.

**Current Status Screen (showing issue):**
```
+======================================================================================================+
|                                        NETWORK MANAGER STATE                                         |
+=====================================================================================================+
| Status: ONLINE  | State: NET_ONLINE            | Interface: NONE  | Duration: 14:17:35 | DTLS: INIT |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDR | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+---------+-------------------+
| eth0      | NO      | NO      | NO      |     0 |       0 | NONE      | VALID   | NONE              |
| wlan0     | DISABLED | NO      | NO      |     0 |       0 | EXPIRED   | NONE    | 16486 ms ago     |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
```

**Key Observations:**
- wlan0 shows DISABLED status
- Cooldown shows EXPIRED
- Despite cooldown being expired, WiFi is not being re-enabled
- This indicates a logic fault where the interface is not being re-evaluated after cooldown expiration

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/wifi_disabled_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/wifif_disabled.yaml
**Generated:** 2025-12-14
