
## Aim debug can sample issues.
The CAN sample routine does not see to be sampling the data 

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


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/canbus pay particlular focus to ~/iMatrix/iMatrix_Client/iMatrix/cabus/can_sample.c
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/ARM_CROSS_COMPILE_DETAILS.md
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md
read ~/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

code runds on embedded system from: /home directory

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

● User answered Claude's questions:
  ⎿  · Do you have test logs or data showing the current CAN performance issues and packet drops? → the logging is shown with the can monitor command
     · What is the target frames per second (fps) rate you want to achieve without packet loss? → 10,000 fps (as specified in prompt)
     · Can you describe the '100% packet drops after buffer fills' issue? Is this still occurring with the current code? → Issue still occurs
     · What platform/hardware will this be running on for testing? → iMX6 (512MB RAM) as described

---

## COMPLETION STATUS - 2025-11-14

### ✅ COMPLETED - Bug Fixed and Verified

**Root Cause Found:** Message leak in `unified_queue_enqueue()` error handling
- Messages allocated from ring buffer but not freed on `IMX_ERROR` returns
- Only `IMX_OUT_OF_MEMORY` errors properly freed messages
- Resulted in ~4,000 message leak → buffer exhaustion → 100% drop deadlock

**Fix Implemented:** Modified `iMatrix/canbus/can_utils.c:722-733`
- Now returns messages to pool on ALL enqueue failures
- Added self-healing recovery mechanism in ring buffer allocation
- Comprehensive diagnostics added (disabled in production for performance)

**Results:**
- **1,800 fps sustained with 0% packet drops** (limited by test equipment)
- **2.25x improvement** over 800 fps failure point
- **0% buffer utilization** (processing faster than input)
- **System stable indefinitely** - no deadlock

**Branches Merged:**
- iMatrix: `feature/canbus-performance-10k` → `Aptera_1_Clean`
- Fleet-Connect-1: `feature/canbus-performance-10k` → `Aptera_1_Clean`

**See:** `docs/debug _canbus_performance_plan_2.md` for complete analysis and implementation details.