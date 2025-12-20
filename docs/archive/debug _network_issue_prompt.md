
## Aim Create a plan to debug and fix Netwrork connection failures
The process network continues to reassociate with wlan0 and sometimes fails evne though the signal is very good and stable.


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


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/networking focus on /process_network.c and cell_man.c
read all source files in ~/iMatrix/iMatrix_Client/docs/Network_Manager_Architecture.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style


## Task
Use the Plan agent to Review the log files ~/iMatrix/iMatrix_Client/logs/net5.txt

Review log to understand any issues with the wlan0 testing phases

If needed add more diagnostic messages.

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/debug_network_issue_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. After every code change run the linter and build the system to ensure there are not compile errors. If compile errors are found fix them.
5. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number or recompilation required for syntax errors, time taken in both eplased and actual work time, time waiting on user responses  to complete the fearure.
6. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

