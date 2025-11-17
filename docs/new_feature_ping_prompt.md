
## Aim Add a new command to the cli "ping"
Provide a linux style ping command to the command line processing

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

read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/Fleet-Connect-1_Developer_Overview.md
read ~/iMatrix/iMatrix_Client/iMatrix/docs/imatrix_api.md
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/ARM_CROSS_COMPILE_DETAILS.md
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md
read ~/iMatrix/iMatrix_Client/Fleet-Connect-1/docs/VSCODE_CMAKE_SETUP.md
read ~/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

code runds on embedded system from: /home directory

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

Additional information.

1. This is LINUX_PLATFORM only command
2. Use same functionality that existing ping in ~/iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c does
3. Use Ping Rate: 1 ping per second (matches standard ping)
4. AAdd an option for limited count (e.g., ping -c 4 8.8.8.8)?
5. Blocking DNS resolution at command start is acceptable
6. The ping command must check the state of the network before starting. If there is no active interface abort immediately with an error message
7. The process_network runs many ping tests. use a helper function to set a flag to prevent process_network running ping tests while this command is executing.
8. In process_network in the state NET_ONLINE check the ping command flag. 
   if set then 
     store the current_time
     call a helper function to get the expected duration of the ping command and store that time
     transition to a new state WAIT_FOR_CLI_PING_TO_END.
9. the process_network state WAIT_FOR_CLI_PING_TO_END will check for the ping command flag to clear or the expected duration of the ping test has been exceeded and then return the NET_ONLINE state.
   Use a helper function to terminate the ping command background execution.
10. use a helper function to stall the starting of the ping command until the process_network is in the WAIT_FOR_CLI_PING_TO_END. Notifiy user every second until flag is clear
11. When the ping test completes use a helper function to clear the flag to allow the process_network to contine to run.
12. Use a default count of 4 ping attempts.
13. Calculate the expected duration of the command and provide a helper function for network_process to call so it can terminaate if the ping comamnd runs too long.
14. provide a helper function for netwwork_process to call that will cleanly terminate the process and log a message about running too long.

Log files will be stored ~/iMatrix/iMatrix_Client/logs
## Task
Add a new command "ping" this accepts as an argument either a FQDN or IPV4 address.
The function must run in non blocking mode. refer to how the command "can monitor" works within the main loop
Output a staring message with the destionation FQDN if provided and the IP address of the destionation. "Pinging: <FQDN>:<destioation>"
Track the **sequence number**
provide standard timeout of 2 seconds, if no reply the add a message **"sequence number** Ping Timeout"
provide a sub command "cancel" to abort the ping test.
use typical output format
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=113 time=20.3 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=113 time=18.4 ms
<User Aborted>
--- 8.8.8.8 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1080ms
rtt min/avg/max/mdev = 18.373/19.345/20.317/0.972 ms


## Deliveralbles
1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/new_feature_ping_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
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

## ASK ANY QUESIONS needed to verify work requirements.

 Before I begin implementation, please provide guidance on:

  1. Ping Interface: Always use current active interface, or support -I <interface> flag?
  2. Waiting Timeout: If network manager doesn't acknowledge in 10s, abort or keep waiting?
  3. Concurrent Pings: Allow only one ping at a time, or support multiple?
  4. Statistics Logging: Display only, or also log to system log/file?
  5. Packet Size: Fixed 56 bytes, or support -s <size> flag?
  6. Extended Features: Add flood ping or interval customization, or keep simple?
  7. Timeout Duration: Current calculation is (count × 3000ms) + 5000ms. Acceptable?

  Answers
  1. support -I <interface> flag?
  2.  Waiting Timeout: If network manager doesn't acknowledge in 10s, abort 
  3. Allow only one ping at a time
  4. statistics only
  5. support -s <size> flag
  6. keep simple
  7. yes
