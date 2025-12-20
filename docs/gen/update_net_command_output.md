<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/update_net_command_output.yaml.yaml
Generated on: 2025-12-14
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Update the net command output format

**Date:** 2025-12-14
**Branch:** bugfix/update_net_command_output

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
- iMatrix/IMX_Platform/LINUX_Platform/CLAUDE.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

The current net command output format is as follows:
```
+=====================================================================================================+
|                                        NETWORK MANAGER STATE                                        |
+=====================================================================================================+
| Status: ONLINE  | State: NET_SELECT_INTERFACE  | Interface: NONE  | Duration: 01:23    | DTLS: INIT |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDR | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+---------+-------------------+
| eth0      | NO      | NO      | NO      |     0 |       0 | NONE      | VALID   | NONE              |
| wlan0     | REASSOC | NO      | NO      |     0 |       0 | NONE      | NONE    | 72489 ms ago      |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
+=====================================================================================================+
|                                        INTERFACE LINK STATUS                                        |
+=====================================================================================================+
| eth0      | INACTIVE - Link up (100Mb/s)                                                            |
| wlan0     | REASSOC - Associated (SierraTelecom)                                                    |
| ppp0      | INACTIVE - Daemon not running                                                           |
+=====================================================================================================+
|                                            CONFIGURATION                                            |
+=====================================================================================================+
| ETH0 Cooldown: 010.000 s | WIFI Cooldown: 010.000 s | Max State: 010.000 s | Online Check: 010.000 s|
| Min Score: 3            | Good Score: 7            | Max WLAN Retries: 3   | PPP Retries: 0         |
| WiFi Reassoc: Enabled  | Method: wpa_cli         | Scan Wait: 2000   ms                             |
+=====================================================================================================+
|                                            SYSTEM STATUS                                            |
+=====================================================================================================+
| ETH0 DHCP: STOPPED  | ETH0 Enabled: NO     | WLAN Retries: 0   | First Run: NO                      |
| WiFi Enabled: YES    | Cellular: NOT_READY | Test Attempted: NO     | Last Link Up: YES             |
+=====================================================================================================+
|                                              DNS CACHE                                              |
+=====================================================================================================+
| Status: PRIMED      | IP: 34.94.71.128      | Age: 83840       ms | Valid: YES                         |
+=====================================================================================================+
|                                       BEST INTERFACE ANALYSIS                                       |
+=====================================================================================================+
| Interface: NONE     | Score: N/A | Latency: N/A                                                      |
+=====================================================================================================+
|                                            RESULT STATUS                                            |
+=====================================================================================================+
| Last Result: ONLINE                                                                                 |
+=====================================================================================================+
| Network traffic: ETH0: TX: 1.66 MB     | WLAN0 TX: 306.74 KB   | PPP0 TX: 4.00 GB                   |
|                        RX: 4.67 MB     |       RX: 12.17 MB    |      RX: 4.00 GB                   |
| Network rates  : ETH0: TX: 0 Bytes/s     | WLAN0 TX: 0 Bytes/s     | PPP0 TX: 0 Bytes/s             |
|                        RX: 0 Bytes/s     |       RX: 0 Bytes/s     |      RX: 0 Bytes/s             |
+=====================================================================================================+
|                                       DHCP SERVER STATUS                                            |
+=====================================================================================================+
| Interface: eth0     | Status: RUNNING  | IP: 192.168.7.1     | Range: 0        -9         |
| Active Clients: 1   | Expired: 0        | Lease Time: 24h     | Config: VALID                   |
+-----------------------------------------------------------------------------------------------------+
| CLIENT IP       | MAC ADDRESS       | HOSTNAME            | LEASE EXPIRES          | STATUS      |
+-----------------+-------------------+---------------------+------------------------+-------------+
| 60.24.160.85    | 00:00:00:00:69:3f | eg-P1-Laptop        | 2030-10-03 12:43:01    | ACTIVE      |
+=====================================================================================================+
```

**Issues to update:**

1. In the output of the interface information the column IP Address should display the IP address of the interface if valid.
2. If the interface is not valid, the column IP Address should display the string "NONE".
3. The output is not formatted correctly. All vertical bars must be aligned on the right.
4. The Network Traffic tables should align consistently.
5. Use fixed width columns for the output to ensure the output is formatted correctly.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/update_net_command_output_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/update_net_command_output.yaml.yaml
**Generated:** 2025-12-14
