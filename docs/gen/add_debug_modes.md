<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/add_debug _modes.yaml
Generated on: 2025-12-26
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Add a new debug sub commands to the CLI to allow adding several flags at the same time.

**Date:** 2025-12-26
**Branch:** feature/add_debug_modes

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

- docs/CLI_and_Debug_System_Complete_Guide.md
- iMatrix/cli/ (CLI subsystem)
- iMatrix/debug/ (Debug system if present)

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Read docs/CLI_and_Debug_System_Complete_Guide.md and understand the debug system.

when the user types "debug can" add all the flags associated with the can subsystem.
0x0000020000000000 - Debugs for CAN Bus
0x0000040000000000 - Debugs for CAN Bus Data
0x0000080000000000 - Debugs for CAN Bus Sample
0x0000100000000000 - Debugs for CAN Bus Event
0x0000200000000000 - Debugs for CAN Registration
0x0000400000000000 - Debugs for CAN Decode
0x0000800000000000 - Debugs for CAN Decode Errors
0x0001000000000000 - Debugs for CAN TCP Server
0x0002000000000000 - Debugs for CAN Ethernet Frame parsing

when the user types "debug network" add all the flags associated with the network subsystem.
0x0000000000020000 - Debugs for Wi Fi Connections
0x0000000000040000 - Debugs for ETH0 Networking
0x0000000000080000 - Debugs for WIFI0 Networking
0x0000000000100000 - Debugs for PPP0 Networking
0x0000000000200000 - Debugs for Networking Switch
0x0000000800000000 - Debugs for Cellular

when the user types "debug coap" add all the flags associated with the coap subsystem.
0x0000000000000002 - Debugs For CoAP Xmit
0x0000000000000004 - Debugs For CoAP Recv
0x0000000000000008 - Debugs For CoAP Support Routines
0x0000000000000010 - Debugs for UDP transport

Ask any questions you need to before starting.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/add_debug_modes_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/add_debug _modes.yaml
**Generated:** 2025-12-26
