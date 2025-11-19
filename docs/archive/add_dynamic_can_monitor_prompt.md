
## Aim add dynamic display off CAN BUS including Server statistics
The CAN Server receives data from Physical CAN BUS devices and over the Ethernet connection.

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


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/canbus pay particlular focus to ~/iMatrix/iMatrix_Client/iMatrix/canbus/can_server.c and ~/iMatrix/iMatrix_Client/iMatrix/canbus/can_structs.h
read ~/iMatrix/iMatrix_Client/CAN_DM/docs/CONFIG_V13_FORMAT_GUIDE.md
read ~/iMatrix/iMatrix_Client/CAN_DM/docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. Remove dead code, keep it simple and maintainable.**

## Task
Add a dynamically updating display, once per second, that shows the current CAN BUS statistics similar to the can server command but also shows the physical CAN 0 and CAN 1 buses.
This routine needs run like the memory monitor allowing other processes to continue while it displays updates

## Deliverables
1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/add_dynamic_can_monitor_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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


  Questions for Clarification

  1. Statistics Granularity: Should we track statistics for:
    - Only logical buses on CAN Ethernet (bus 2+), since CAN 0 and CAN 1 are 1:1 mapped?
    - OR all logical buses including CAN 0 and CAN 1 (which would just duplicate the physical bus stats)?
  2. Display Format: For the canstats command, should we:
    - Show a summary table with all logical buses side-by-side?
    - Group by physical bus (e.g., "CAN 0", "CAN 1", then "Ethernet: PT, IN, etc.")?
    - Show both physical bus totals AND per-logical bus breakdowns?
  3. Backward Compatibility: Should we:
    - Keep the existing physical bus stats (can0_stats, can1_stats, can_eth_stats) for overall totals?
    - Add new per-logical bus stats arrays?
    - OR replace physical bus stats with logical bus stats?
  4. Statistics Tracked: Should we track the same comprehensive stats for each logical bus as we do for physical buses (RX/TX frames/bytes, rates, peaks, buffer utilization), or just basic frame/byte counts?
  5. Storage Location: Where should logical bus stats be stored:
    - In the logical_bus_config_t structure itself?
    - In a new array in the canbus_product_t (cb) structure?
    - In a separate global stats structure?

    Answers.
    1. Yes - Only logical buses on CAN Ethernet (bus 2+), since CAN 0 and CAN 1 are 1:1 mapped.
    2. All
    3. Keep the existing physical bus stats (can0_stats, can1_stats, can_eth_stats) for overall totals
    - Add new per-logical bus stats arrays
    4. Yes
    5. Most effecient, I think most likely In the logical_bus_config_t structure itself
