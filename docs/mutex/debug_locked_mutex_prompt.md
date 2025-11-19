
## Aim debug and diagnose locked up code due to mutex issues.
When the CAN Server is running the system frequent stops. The expectation is this is a mutex issue between threads

Think ultrahard as you read and implement the following.
Stop and ask questions if any failure to find Background material.

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The wifi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chips set is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/canbus pay particlular focus to ~/iMatrix/iMatrix_Client/
~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/ARM_CROSS_COMPILE_DETAILS.md and ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md
read ~/iMatrix/iMatrix_Client/CAN_DM/docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
~/iMatrix/iMatrix_Client/iMatrix/templates/blank.c
~/iMatrix/iMatrix_Client/iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task
Throughly revew all can bus releated mutex and queue handling.
Right now gdb’s basically blind inside musl on ARM. To fix that going forward:
Recompile the app with: -g -O0 -fno-omit-frame-pointer -fno-optimize-sibling-calls
Determine how to update gdb settings to use unstripped binaries on the host side
 

## Deliverables
1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/debug_locked_mutex.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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

## ASK ANY QUESTIONS needed to verify work requirements.

Questions

  1. Symptom Details: When the system "stops," does it:
    - Completely hang/freeze?
    - Become unresponsive to certain operations?
    - Show any error messages or logs before stopping?
    - Recover on its own or require restart?
  2. Reproduction:
    - Is this reproducible consistently or intermittent?
    - Are there specific operations that trigger it (e.g., high CAN bus traffic, specific commands)?
    - How long does it typically take to manifest after CAN Server starts?
  3. Current State:
    - Do you have any GDB backtraces or logs from when it's hung?
    - Are there any core dumps available?
    - What's the typical thread count when the system is running?
  4. Scope:
    - Should I focus only on the CAN bus subsystem mutexes, or also review mutexes in related systems (networking, BLE, etc. that might interact with CAN)?
    - Are there specific threads that you suspect are involved?
  5. Build Environment:
    - Are you building for the target ARM platform directly or cross-compiling?
    - What's your current GDB setup (local/remote debugging)?

    Answers
    1. Only the main process halts other processes continue to run. The code stops on instuction svc 0. with not useable stack history. Does not recover. Does not output any smoking gun message.
    2. reproducably soon after CAN data is received on the ethernet interface.
    3. GDB backtraces ane not helpful. Provide a list of items and next crash I will report them.
    4. For now focus on all can bus related functionality in iMatrix and Fleet-Connect-1
    5. The build system is on this WSL implementation wtih cross compile to run on targer. Using Remote GDB. Read Fleet-Connect-1/docs/ARM_CROSS_COMPILE_DETAILS.md and Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md

    ### 14.1 Questions for Greg

1. **Frequency:** Approximately how long after CAN data starts does the hang occur?
   - < 1 second
   - 1-10 seconds
   - 10-60 seconds
   - > 1 minute

2. **CAN Traffic Characteristics:**
   - What is the typical frame rate when crash occurs? (frames/second)
   - How many logical CAN buses are active?
   - Is it always the same bus or random?

3. **System State:**
   - Is the TCP server connection active when it hangs?
   - Are other threads (network, upload) still responsive?
   - Can you connect to CLI when hung?

4. **Previous Observations:**
   - Have you ever seen error messages before the hang?
   - Have you tried killing individual threads to unblock?
   - Any patterns in when it happens (time of day, specific CAN IDs)?

### 14.2 Questions to Investigate During Implementation

1. **Mutex Attributes:**
   - Should can_rx_mutex be recursive or non-recursive?
   - Are there any legitimate re-entrant call paths?

2. **Lock Granularity:**
   - Should each ring buffer have its own mutex, or one global ring buffer mutex?
   - Current plan: Per-buffer mutex (better concurrency, no contention between buses)

3. **Error Recovery:**
   - What should happen if ring buffer mutex lock fails?
   - Recommendation: Log error and drop CAN frame (data loss better than crash)

---
Answers from Greg
1. 10-60 seconds
2. 1000 fps
3. TCP Server continues to run. other threads are responsive. CLI is hung but PTY is functional.
4. Unknown

Looks very much like mutex issue