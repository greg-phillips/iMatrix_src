
## Aim Create a plan to debug and fix Netwrork connection failures
The process network function is unreliable and cause Wi-Fi disconnections when not needed.
Cause failure to connect repeatedly to cellular netwrok ppp0 connection.
Is unstable and unworkable.
This task is to investigate with logging and resolve the issues for a stable networking system.
As part of the debugging we are also seeing lockup which we expect to be a mutex issue. 
We are debugging both
when we see this message in the log: "ERROR: 14 bytes not written to circular buffer" it means main loop is locked up
the output from the PTY threads command conifrms
===== TIMERS =====

Timer 1:
  Name:            imx_process_handler
  Status:          RUNNING
  Interval:        100 ms
  Registered:      15 min 13 sec ago
  Creator:         /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/linux_gateway.c:162 (imx_host_application_start)

  Execution Stats:
    Total Executions:    3487
    Last Execution:      7 min 32 sec ago

  Performance:
    Avg Time:           31.300 ms
    Min Time:           0.250 ms
    Max Time:           10601.440 ms
    Last Time:          0.346 ms

  Health:
    Late Count:         429
    Missed Count:       0
    Max Delay:          10601 ms
    Interval Range:     99-10701 ms

  Critical:          Yes

NOte Last Execution - this timer runs every 100mS


Think ultrahard as you read and implement the following.
Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
THe wifi communicatons uses a combination Wi-Fi/Bluetooth chipset
The Cellular chips set is a PLS62/63 from TELIT CINTERION using the AAT Command set.
The code is cross compiled for ARM and we manually transfer to the test system.

The user's name is Greg

Read and understand the following


~/iMatrix/iMatrix_Client/docs/comprehensive_code_review_report.md
~/iMatrix/iMatrix_Client/docs/developer_onboarding_guide.md
~/iMatrix/iMatrix_Client/Fleet-Connect-1/Fleet-Connect-1_Developer_Overview.md
~/iMatrix/iMatrix_Client/iMatrix/docs/imatrix_api.md
~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/ARM_CROSS_COMPILE_DETAILS.md
~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md
~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/VSCODE_CMAKE_SETUP.md
~/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md

read all source files in ~/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/networking focus on /process_network.c and cell_man.c


Debug flags currently in use: 
0x0000000000010000 - Debugs for Wi Fi Connections
0x0000000000020000 - Debugs for ETH0 Networking
0x0000000000040000 - Debugs for WIFI0 Networking
0x0000000000080000 - Debugs for PPP0 Networking
0x0000000000100000 - Debugs for Networking Switch
0x0000000800000000 - Debugs for Cellular

debug 0x00000008001F0000

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**
Additional infomaation:

Log files will be stored ~/iMatrix/iMatrix_Client/logs
use an agent to read this very long files: read net1.txt, net2.txt, net3.txt

## Additional Background

THe Cellular system uses AT commands to control the cellular radio.
The callular code initializes, if already connected keeps carrier. if not then scans for best and selects that.
The cellular code will set flags that the process_network monitors with helper functions. 
If the process_network can not connect on the ppp0 link it will black list the carrier. The cellular system is then responsible for connection to the next non blocklisted carrier.

## Task
Use the Plan agent to read in sections, it is long, and Review the log files

Review log to understand any issues with network testing phases

provide a document with the findings and issues with the operation from the log file.

If needed add more diagnostic messages.

## Deliveralbles
1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/debug_network_issue_plan_2.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature. number of test runs before completion.
8. Merge the branch back into the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

 Before I create the detailed plan, I need to clarify a few important aspects:

  1. Scope Priority

  The document mentions TWO separate but related issues:
  - A) Network connection instability (Wi-Fi disconnections, cellular ppp0 failures)
  - B) Mutex/lockup issue (main loop freezing, timer not executing)

     Should I:
  - Focus on both issues together (they may be related)?
  - Prioritize network stability first, then mutex issues?
  - Prioritize mutex/lockup first (as it blocks the main loop)?

  2. Log File Context

  - What specific test scenarios do net1.txt, net2.txt, and net3.txt represent?
  - Are these logs showing the lockup condition, or just network switching issues?
  - Do you have logs that show the "ERROR: 14 bytes not written to circular buffer" message?

  3. Testing Environment

  - Do you have a test setup where I can reproduce these issues after making fixes?
  - Should I focus on creating diagnostic-only changes first, or can I proceed with both diagnostics + fixes?

  4. Branch Naming

     What would you like the new branch named? Something like:
  - feature/network-mutex-debug
  - bugfix/network-stability
  - debug/network-lockup-investigation

  5. Mutex Investigation Scope

     The document mentions you're "debugging both" - do you already have suspicions about which mutexes might be problematic, or should the investigation be comprehensive across all networking-related mutexes?

  Please answer these questions so I can create the most effective and focused plan for you.

  Answers.

  1. Focus on both issues together (they may be related)?
  2. These are program start up to network conenction failues
  3. I run the tess on a embedded target and collect logs for review
  4. bugfix/network-stability
  5. I think they may be both related. 

  Additional Guidance.
  We have access to a PTY even when the main loop is locked.
  Start by adding to all the mutex references across the entire code base wrapper to set a flag in a structure and the calling routine that locks it. when unlocked clear the flag.
  Add a command "mutex" that prints the status of every mutex and if they are locked which functon established the lock. This will help us eliminate mutex issues.

Open Questions for User
Should mutex tracking be always-on or compile-time optional? (Recommend always-on for Linux)
What is the acceptable WiFi grace period? (Recommend 15 seconds)
Should we fix PPP connect script or investigate modem firmware?
Are there other mutexes beyond the 20 files found that need tracking?
Should we add mutex tracking to memory manager (mm2_api.c) even though it's high-volume?

Answers
1. compile-time optional with define in Makefile
2. 15 seconds
3.  fix PPP connect script 
4. unknown
5. add mutex tracking to memory manager 

Add the following functionality
Limit ping tests on eth0 and wlan0 interfaces to once per minute.
Before starting a ping test check using a helper routine what the state of the imatrix_upload function is. Only start a ping test if it is not actively sending packets. 
This is any state less than IMATRIX_GET_PACKET. Rewview ~/iMatrix/iMatrix_Client/iMatrix/imatrix_upload/imatrix_upload.c 