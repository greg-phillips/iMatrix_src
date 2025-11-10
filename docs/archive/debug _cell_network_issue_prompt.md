
## Aim Create a plan to debug and fix Cellular connection failures
The celluar driver and network process work together to allow the system to use cellular network if wlan0 or eth0 are not available.

Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

The user's name is Greg

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md
memory_manager_technical_reference.md


read all source files in iMatrix/IMX_Platform/networking/process_network.c
read all source files in iMatrix/IMX_Platform/networking/cell_man.c

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style


## Task
Use the Plan agent to Review the log files logs/cell_1.txt

Create a document that provides a guide to the entire network and cellular interaction and operation.
Note that the cellular code is scanning and connecting to celular networks but the network process never activates the PPP0 request to provide a connection to test.
Review state machines of both and determine root cause faulure.
Network process should also be telling the wlan0 to rescan for available wifi access points
If needed add more diagnostic messages.

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/debug _cell_network_issue__plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. After every code change run the linter and build the system to ensure there are not compile errors. If compile errors are found fix them.
5. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number or recompilation required for syntax errors, time taken in both eplased and actual work time, time waiting on user responses  to complete the fearure.
6. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

Questions

 ● What is the expected behavior when both eth0 and wlan0 are unavailable - should ppp0 automatically activate, or does it require manual intervention?
   → The ppp0 activastion should be automatic. When the cellular driver has connectted to a carrier it sets the flag retruned by imx_is_cellular_now_ready. if this has transistioned from false to true then the network 
   process should start a new ppp0 connection and wait to see if a connection is possible. If the connection does not come up in a suitable time them the celluar driver should flag this carrier as blacklisted and move to a 
   new non blackliested carrier
 ● Are there any known working scenarios where ppp0 successfully connects, or has it never worked in this codebase?
   → Works sometimes
 ● What is the current test environment - are you testing with an actual cellular modem or simulated conditions?
   → Real hardware
 ● Should wlan0 WiFi scanning be continuous or triggered only when the current connection fails?
   → On-failure only



