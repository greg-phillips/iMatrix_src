
## Aim Create a plan to debug canbus processing performance and increase to support at least 10000 fps
The CAN BUS processing operatins in its own thread, can_processing_thread_func, and process frames that are added by tcp_server_thread and CAN0 and CAN1 processing routines.

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

The user's name is Greg

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/canbus
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/ARM_CROSS_COMPILE_DETAILS.md
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md
read ~/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task
Conduct this functionality in two phases. Phase 1 find and fix packet drops, Phase 2 increase perfomance to prevent any packet loss.

Review current code base and add enhanced statistics collection regarding the time take to process each frame.
There is a logic where 100% of frames are dropped after the buffer fills to 100% find and fix this issue
Determine how to force the the CPU intensive task to higher priority to consume more CPU time so no frames are dropped.

provide a document with the findings and issues with the dropped frames. Once that is fixed move on to phase 2 increasing performance

If needed add more diagnostic messages.

## Deliveralbles
1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/debug _canbus_performance_plan_2.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
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

## ASK ANY QUESIONS needed to verify work requirements.
