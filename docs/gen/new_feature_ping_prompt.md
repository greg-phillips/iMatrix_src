<!--
AUTO-GENERATED PROMPT
Generated from: specs/examples/moderate/ping_command.yaml
Generated on: 2025-11-17 09:22:38
Schema version: 1.0
Complexity level: moderate

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Add new ping command to CLI
Implement Linux-style ping command for network diagnostics

Think ultrahard as you read and implement the following.
Stop and ask questions if any failure to find Background material

**Date:** 2025-11-17
**Branch:** feature/cli-ping-command
**Objective:** Implement Linux-style ping command for network diagnostics

## Code Structure:

iMatrix (Core Library): iMatrix - Contains all core telematics functionality

Fleet-Connect-1 (Main Application): Fleet-Connect-1 - Main system management logic

This feature adds network diagnostic capabilities directly to the CLI,
allowing field technicians to troubleshoot connectivity without shell access.


## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The wifi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

- Limited to LINUX_PLATFORM only

The user's name is Greg

Read and understand the following

docs/CLI_and_Debug_System_Complete_Guide.md
iMatrix/cli/cli_commands.c
iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c

**Source files to review:**

- iMatrix/cli
  Focus on: cli_commands.c, cli_handler.h

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

code runs on embedded system from: /home directory

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Implement ping command with standard Linux-style output format

**Requirements:**

- Support -c <count> flag for packet count (default: 4)
- Support -I <interface> flag for specific interface selection
- Support -s <size> flag for packet size (default: 56 bytes)
- Check network state before starting - abort if no active interface
- Ping rate: 1 ping per second (matches standard ping)
- Standard timeout of 2 seconds per ping attempt
- Provide 'cancel' sub-command to abort running ping test

**Implementation Notes:**

- Use existing ping functionality from process_network.c as reference
- Function must run in non-blocking mode (refer to 'can monitor' command)
- Coordinate with network manager state machine
- Add WAIT_FOR_CLI_PING_TO_END state to process_network
- Use helper function to prevent process_network running ping tests
- Calculate expected duration: (count × 3000ms) + 5000ms

## Detailed Specifications

### Output Format

PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=113 time=20.3 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=113 time=18.4 ms
<User Aborted>
--- 8.8.8.8 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1080ms
rtt min/avg/max/mdev = 18.373/19.345/20.317/0.972 ms


### State Machine Integration

- In process_network NET_ONLINE state, check ping command flag
- If set, store current_time and expected duration
- Transition to new state WAIT_FOR_CLI_PING_TO_END
- State checks for flag clear or timeout exceeded
- Use helper to terminate background execution on timeout
- Stall ping command start until process_network is in correct state
- Notify user every second while waiting


## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/new_feature_ping_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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

**Additional Steps:**
- Create integration tests for ping command
- Update CLI help documentation
- Test with various network states (connected, disconnected, switching)

## ASK ANY QUESTIONS needed to verify work requirements.

Before I begin implementation, please provide guidance on:

1. Ping Interface: Always use current active interface, or support -I <interface> flag?
2. Waiting Timeout: If network manager doesn't acknowledge in 10s, abort or keep waiting?
3. Concurrent Pings: Allow only one ping at a time, or support multiple?
4. Statistics Logging: Display only, or also log to system log/file?
5. Packet Size: Fixed 56 bytes, or support -s <size> flag?
6. Extended Features: Add flood ping or interval customization, or keep simple?
7. Timeout Duration: Current calculation is (count × 3000ms) + 5000ms. Acceptable?

Answers
1. support -I <interface> flag
2. If network manager doesn't acknowledge in 10s, abort
3. Allow only one ping at a time
4. statistics only
5. support -s <size> flag
6. keep simple
7. yes

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** specs/examples/moderate/ping_command.yaml
**Generated:** 2025-11-17 09:22:38