
## Aim add display off individual can server logical bus data counts
The CAN Server receives data from multiple logical can buses. Collect and display statistics for each.

Think ultrahard as you read and implement the following.
Stop and ask questions if any failure to find Background material.

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


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/canbus pay particlular focus to ~/iMatrix/iMatrix_Client/iMatrix/canbus/can_server.c and ~/iMatrix/iMatrix_Client/iMatrix/canbus/can_structs.h
read ~/iMatrix/iMatrix_Client/CAN_DM/docs/CONFIG_V13_FORMAT_GUIDE.md
read ~/iMatrix/iMatrix_Client/CAN_DM/docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style


## Task
all per logical can bus statisitcs for characters and frames.
display as part of can server and can canstats commands.
## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/add_per_logical_can_interface_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. After every code change run the linter and build the system to ensure there are not compile errors. If compile errors are found fix them.
5. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number or recompilation required for syntax errors, time taken in both eplased and actual work time, time waiting on user responses  to complete the fearure.
6. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.


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
