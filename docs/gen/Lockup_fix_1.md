<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/fix_lockup.yaml
Generated on: 2026-01-06T15:30:00
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Develop a plan to fix the lockup issue

**Date:** 2026-01-06
**Branch:** feature/Lockup_fix_plan_1

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

- /home/greg/iMatrix/iMatrix_Client/docs/fc1_script_reference.md - FC-1 remote control script for service management, deployment, and CLI command execution
- /home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md - SSH connection methods and helpers for the FC-1 device
- /home/greg/iMatrix/iMatrix_Client/docs/logging_system_use.md - Filesystem logging system documentation, log locations, and access methods
- /home/greg/iMatrix/iMatrix_Client/docs/loop_stuck_investigation.md - Previous investigation into the handler stuck issue with detailed analysis

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

The software has been deployed using the fc1 script. see: /home/greg/iMatrix/iMatrix_Client/docs/fc1_script_reference.md

The host device is on address: **10.2.0.169**

Use SSH to connect to the host device and review the logs. see: /home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md

The program has generated log files that are on the system. see: /home/greg/iMatrix/iMatrix_Client/docs/logging_system_use.md

This current investigation has been documented in /home/greg/iMatrix/iMatrix_Client/docs/loop_stuck_investigation.md

**Develop a plan investigating the issue and provide a detailed plan to fix it.**

### Current Output from Device

```
app>loopstatus

==================== MAIN LOOP STATUS ====================

--- System Timing ---
Boot Time:           2026-01-06T04:17:12 UTC
Uptime:              0d 9h 44m 37s (35077 sec)

--- Loop Position ---
Handler Position:    Before imx_process() (0)
Time at Handler:     27710021 ms

imx_process() Pos:   50
Time at imx_proc:    27710021 ms

do_everything() Pos: EXIT (19)
Time at Position:    27710121 ms
Loop Executions:     48228

*** WARNING: Handler stuck at 'Before imx_process()' for 27710021 ms! ***
*** Lock occurred at: 2026-01-06T06:19:59 UTC ***
*** Time after boot:  2h 2m 47s (7367 sec after boot) ***
*** BLOCKING IN: imatrix_upload() (position 50) ***
==========================================================

app>
Switched to CLI mode
>threads

THREADS:
TID      NAME                 STATUS      CREATED          CPU(us)  STACK   CREATOR
-------- -------------------- ----------- ---------------- -------- ------- ------------------
2797424004 tty_input            RUNNING     05:04:36.014     0        128    K imx_linux_btstack.c:344
2797280644 nmea_gps             RUNNING     05:04:39.734     0        128    K quake_gps.c:808
2797038980 can_process          RUNNING     05:04:42.887     0        128    K can_processing_thread.c:172
2796895620 can_tcp_srv          RUNNING     05:04:43.008     0        128    K can_server.c:908
2796608900 accel_proc           RUNNING     05:04:48.045     0        128    K accel_process.c:1457

Total: 5 threads (5 active, 0 terminated)

TIMERS:
NAME                 INTERVAL STATUS      EXECUTIONS   AVG_TIME   MAX_TIME   LATE/MISS CREATOR
-------------------- -------- ----------- ------------ ---------- ---------- --------- ------------------
imx_process_handler  100ms    RUNNING     48228        51.0ms     6646.8ms   7520/0    linux_gateway.c:271 [CRITICAL]

Total: 1 timers (1 active, 0 stalled)

>threads -v

===== THREADS =====

Thread 1:
  TID:             2797424004
  Name:            tty_input
  Status:          RUNNING
  Created:         10 hr 14 min ago
  Started:         10 hr 14 min ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/imx_linux_btstack.c:344 (imx_btstack_init)
  Stack Size:      131072 bytes
  Detached:        Yes

Thread 2:
  TID:             2797280644
  Name:            nmea_gps
  Status:          RUNNING
  Created:         10 hr 14 min ago
  Started:         10 hr 14 min ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/iMatrix/quake/quake_gps.c:808 (quake_gps_init)
  Stack Size:      131072 bytes
  Detached:        Yes

Thread 3:
  TID:             2797038980
  Name:            can_process
  Status:          RUNNING
  Created:         10 hr 14 min ago
  Started:         10 hr 14 min ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/iMatrix/canbus/can_processing_thread.c:172 (start_can_processing_thread)
  Stack Size:      131072 bytes
  Detached:        Yes

Thread 4:
  TID:             2796895620
  Name:            can_tcp_srv
  Status:          RUNNING
  Created:         10 hr 14 min ago
  Started:         10 hr 14 min ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/iMatrix/canbus/can_server.c:908 (start_can_server)
  Stack Size:      131072 bytes
  Detached:        Yes

Thread 5:
  TID:             2796608900
  Name:            accel_proc
  Status:          RUNNING
  Created:         10 hr 14 min ago
  Started:         10 hr 14 min ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/hal/accel_process.c:1457 (process_accel)
  Stack Size:      131072 bytes
  Detached:        Yes


===== TIMERS =====

Timer 1:
  Name:            imx_process_handler
  Status:          RUNNING
  Interval:        100 ms
  Registered:      10 hr 14 min ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/linux_gateway.c:271 (imx_host_application_start)

  Execution Stats:
    Total Executions:    48228
    Last Execution:      8 hr 11 min ago

  Performance:
    Avg Time:           51.018 ms
    Min Time:           0.606 ms
    Max Time:           6646.811 ms
    Last Time:          11.673 ms

  Health:
    Late Count:         7520
    Missed Count:       0
    Max Delay:          6646 ms
    Interval Range:     99-6746 ms

  Critical:          Yes

>
```

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/Lockup_fix_1_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/fix_lockup.yaml
**Generated:** 2026-01-06T15:30:00
