<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/can_server_error.yaml
Generated on: 2025-12-26
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: When starting the CAN server, it sometimes fails to start if there are any errors, log them to the console.

**Date:** 2025-12-26
**Branch:** debug/can_server_error

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

- iMatrix/canbus/can_server.c - CAN TCP server implementation
- iMatrix/canbus/can_server.h - CAN server header
- Fleet-Connect-1/can_process/ - CAN bus message processing
- CLAUDE.md - Project guidelines and patterns

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Read the code in iMatrix/canbus/can_server.c and understand the code.

When the CAN server fails to start these are the errors. The system fails. Add more diagnostics and fix issue.
After some time the Registry is full. Find and fix the issue.

**Error Log:**
```
[1766796796.073] [00:01:53.329] [CAN TCP Server: Using APTERA format parser]
[1766796796.074] [00:01:53.329] [CAN TCP Server thread started.]
[1766796796.084] [00:01:53.340] [CAN TCP Server Error: bind: -1: No error information]
[1766796796.085] [00:01:53.340] [CAN Server Failure - Restarting in 5 seconds]
[1766796801.305] [00:01:58.561] [CAN TCP Server: Using APTERA format parser]
[1766796801.305] [00:01:58.561] [CAN TCP Server thread started.]
[1766796801.312] [00:01:58.568] [CAN TCP Server Error: bind: -1: No error information]
[1766796801.312] [00:01:58.568] [CAN Server Failure - Restarting in 5 seconds]
[1766796806.375] [00:02:03.631] [CAN TCP Server: Using APTERA format parser]
[1766796806.375] [00:02:03.631] [CAN TCP Server thread started.]
[1766796806.378] [00:02:03.634] [CAN TCP Server Error: bind: -1: No error information]
[1766796806.378] [00:02:03.634] [CAN Server Failure - Restarting in 5 seconds]
[1766796811.396] [00:02:08.651] [CAN TCP Server: Using APTERA format parser]
[1766796811.396] [00:02:08.652] [CAN TCP Server thread started.]
[1766796811.399] [00:02:08.655] [CAN TCP Server Error: bind: -1: No error information]
[1766796811.399] [00:02:08.655] [CAN Server Failure - Restarting in 5 seconds]
[1766796816.415] [00:02:13.671] [CAN TCP Server: Using APTERA format parser]
[1766796816.416] [00:02:13.672] [CAN TCP Server thread started.]
[1766796816.421] [00:02:13.676] [CAN TCP Server Error: bind: -1: No error information]
[1766796816.421] [00:02:13.676] [CAN Server Failure - Restarting in 5 seconds]
[1766796821.435] [00:02:18.691] [CAN TCP Server: Using APTERA format parser]
[1766796821.436] [00:02:18.691] [CAN TCP Server thread started.]
[1766796821.438] [00:02:18.694] [CAN TCP Server Error: bind: -1: No error information]
[1766796821.439] [00:02:18.694] [CAN Server Failure - Restarting in 5 seconds]
[1766796826.462] [00:02:23.718] [CAN TCP Server: Using APTERA format parser]
[1766796826.463] [00:02:23.718] [CAN TCP Server thread started.]
[1766796826.467] [00:02:23.722] [CAN TCP Server Error: bind: -1: No error information]
[1766796826.467] [00:02:23.723] [CAN Server Failure - Restarting in 5 seconds]
[1766796831.750] [00:02:29.006] [CAN TCP Server: Using APTERA format parser]
[1766796831.751] [00:02:29.007] [CAN TCP Server thread started.]
[1766796831.755] [00:02:29.010] [CAN TCP Server Error: bind: -1: No error information]
[1766796831.755] [00:02:29.011] [CAN Server Failure - Restarting in 5 seconds]
[1766796837.037] [00:02:34.293] [CAN TCP Server: Using APTERA format parser]
[1766796837.038] [00:02:34.294] [CAN TCP Server thread started.]
[1766796837.042] [00:02:34.298] [THREAD TRACKER] ERROR: Registry full, cannot track thread 'can_tcp_srv'
[1766796837.043] [00:02:34.298] [CAN TCP Server Error: bind: -1: No error information]
[1766796837.043] [00:02:34.299] [CAN Server Failure - Restarting in 5 seconds]
[1766796842.393] [00:02:39.648] [CAN TCP Server: Using APTERA format parser]
[1766796842.393] [00:02:39.649] [CAN TCP Server thread started.]
```

**Key Issues to Investigate:**

1. **bind() error with no error information** - The error message shows "bind: -1: No error information" which suggests errno is not being captured correctly. Improve the error reporting to show the actual errno value and its meaning (e.g., EADDRINUSE, EACCES, etc.)

2. **Thread Registry Full** - After multiple restart attempts, the thread tracker registry becomes full. This indicates threads are not being properly unregistered when the CAN server fails. The thread cleanup on failure needs to be reviewed.

3. **Restart Loop** - The server is stuck in a restart loop every 5 seconds. Need to understand why bind() is failing and implement proper recovery.

Ask any questions you need to before starting.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/can_server_error_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/can_server_error.yaml
**Generated:** 2025-12-26
