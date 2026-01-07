<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/udhcp_issues_2.yaml
Generated on: 2026-01-06
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Continuing the investigation of the udhcp issue

**Date:** 2026-01-06
**Branch:** feature/udhcp_issues_2

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

Read and understand the following references:

### Primary Issue Documents:
- `/home/greg/iMatrix/iMatrix_Client/docs/gen/fix_the_udhcp_issue.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/prompt_work/fix_udhcp_issue.yaml`
- `/home/greg/iMatrix/iMatrix_Client/docs/prompt_work/udhcp_issues_2.yaml`

### Root Cause Analysis:
- `/home/greg/iMatrix/iMatrix_Client/monitoring/udhcpc_root_cause_analysis.md`
- `/home/greg/iMatrix/iMatrix_Client/monitoring/critical_findings.md`
- `/home/greg/iMatrix/iMatrix_Client/monitoring/network_analysis.md`

### udhcpd Implementation Docs:
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/udhcpd_implementation_plan.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/implementation_summary.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/dhcp_shutdown_integration_plan.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/network_reboot_kiss_fix.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/udhcp_prompt_1.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/udhcpd_gpt5.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/udhcpd_gemini.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/udhcpd/udhcpd_perplexity.md`

### Archived Related Docs:
- `/home/greg/iMatrix/iMatrix_Client/docs/archive/add_check_for_udhcpd_plan.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/archive/add_check_for_udhcpd_prompt.md`

### Source Code Files:
- `/home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`
- `/home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.h`
- `/home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
- `/home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/networking/network_provisioning.c`

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Developer Debugging Guide

Use the `fc1` script and methods documented in: `/home/greg/iMatrix/iMatrix_Client/docs/Developer_Debugging_Guide.md`

**Key Commands:**
```bash
# Connect to device (default: 192.168.7.1)
./scripts/fc1 ssh

# Check running processes
ps | grep udhcpc

# View application logs
tail -f /var/log/fc-1.log

# Check network status
./scripts/fc1 cmd "net"
```

## Task

The udhcp issue has been investigated and fixes applied however the issue is still occurring.

**Problem Statement:**
- Multiple udhcpc processes are still being created
- The network is not stable
- Previous fixes have not resolved the issue

**Investigation Steps:**
1. Use the same tools and methods as used in the previous investigation
2. Use the `fc1` script and details in the Developer Debugging Guide
3. Review all referenced documents above
4. Connect to device under test at: **192.168.7.1**
5. Use the `ps` command to review the processes running on the device
6. Create a plan to fix the issue

### Previous Investigation Summary (from Root Cause Analysis)

The root cause analysis identified:
1. **TOCTOU Race Condition** - Time-Of-Check-to-Time-Of-Use bug in WiFi recovery state machine
2. **No Mutual Exclusion** - 5 separate uncoordinated code paths spawn udhcpc
3. **Insufficient Process Cleanup** - 500ms timeout too short
4. **PID File Overwrite** - Multiple processes use same PID file
5. **No Process Count Enforcement** - Code counts but doesn't limit processes

**Entry Points Identified:**
| Entry Point | Location | Trigger |
|------------|----------|---------|
| WiFi Recovery | Line 7599 | WiFi reconnection |
| DHCP Renewal | Line 3082 | DHCP lease expiry |
| ETH0 Restart | Line 5135 | Ethernet carrier detection |
| Interface Reconnect | Line 4730 | Link state changes |
| External ifplugd | System daemon | Interface plug events |

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/udhcp_issues_2_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/udhcp_issues_2.yaml
**Generated:** 2026-01-06
