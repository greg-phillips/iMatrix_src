
## Aim Debug Network Interface selection
Validate correct network interface selection.

Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md
docs/comprehensive_code_review_report.md


read all source files in iMatrix/IMX_Platform/networking/ special focus on interface selection related functions

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

The system is built on a VM. Perform Linting on all generated code and then leave it to me to build and test.

The system constantly monitors link connectivity and switches between interfaces to ensure a reliable connection to the iMatrix Cloud Servers.
The priority is Ethernet->WLAN->Cellular (ppp0).
If a interface is operating as a DHCP Server then the interface should not be used. It has client devices connected and is not a route to the Internet and iMatrix Cloud.

## Task
Review log files to ensure ocrrect operation.
I will provide log files as we investigate and make any changes need.
The log files are large. Process the log files in sections.

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/debug_network_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken and the number of tokens used, time taken in both eplased and actual work time  to complete the fearure.
5. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

