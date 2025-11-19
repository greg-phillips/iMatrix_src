
## Aim clean up and make the cli help easier to read
The current output from the ? command is messy

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

1. The current output from the cli "?" command is:
>?

iMatrix CLI Commands
Note: Use 'app' for Application CLI mode, 'exit' to return to normal mode
Lines beginning with '!' will be ignored

Command            Description                                                                                             Command            Description                                                                                           
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
?                  - Print this help                                                                                         mem_active         - Display active memory allocations                                                                     
b                  - BLE manager status                                                                                      mem_leaks          - Check for memory leaks                                                                                
bind               - Send MAC and SN to Manufacturing server                                                                 mem_stats          - Display iMatrix memory tracking statistics                                                            
bk                 - Display known BLE Device ID's                                                                           mm                 - Live memory monitor - displays real-time heap status                                                  
bm                 - BLE monitor add - 'bm <model_number> <serial_number> <mac_address>' - Add device to monitoring list     ms                 - Memory statistics - 'ms' (summary), 'ms ram', 'ms disk', 'ms use', 'ms all', 'ms test' - Use 'ms ?'   
                                                                                                                                                                          for all options                                                                 
bm_cfg_sn          - BLE config update - 'bm_cfg_sn <serial_number>' - Force configuration download for specific device      net                - Network commands - 'net' (status), 'net mode' (configure interfaces), 'net cell' (cellular status)    
bm_get             - Request list of devices to monitor                                                                      netmgr_set_timing  - Set network timing <parameter> <value>                                                                
bm_ota_sn          - BLE OTA update - 'bm_ota_sn <serial_number>' or 'bm_ota_sn all' - Force OTA update for specific or      netmgr_timing      - Display network manager timing configuration                                                          
                                           all devices                                                                       
bms                - BLE monitor status - 'bms [columns]' - Display monitored devices, optionally set display columns (1-4)  ntp                - NTP time sync - 'ntp' (force sync now), 'ntp status' (show sync status), 'ntp server <ip>' (set       
                                                                                                                                                                          server)                                                                         
bmr_all            - Remove all managed Devices from monitor_list                                                            online             - Network online mode - 'online on' (enable network), 'online off' (disable network), 'online' (show    
                                                                                                                                                                          status)                                                                         
bmr_mac            - BLE remove by MAC - 'bmr_mac <mac_address>' - Remove device from monitoring list by MAC address         mutex              - Mutex status - 'mutex' (show locked mutexes), 'mutex verbose' (show all mutexes with statistics)      
bmr_pid            - BLE remove by model - 'bmr_pid <model_number>' - Remove device from monitoring list by model number     org                - org - <Organization ID>                                                                               
bmr_sn             - BLE remove by SN - 'bmr_sn <serial_number>' - Remove device from monitoring list by serial number       q                  - Queue status - Display all message queues, pending messages, and queue statistics                     
boot               - Boot control - 'boot <n>' where n: 2=Factory Reset, 3=OTA App, 5=APP0, 6=APP1                           qr                 - Enter QR Code to set MAC and SN                                                                       
c                  - Configuration display - Show all device configuration parameters, settings, and operational values      quit               - Exit the iMatrix application and return to OS                                                         
can                - CAN bus - 'can' (status), 'all', 'sim', 'unknown', 'verify', 'extended', 'nodes', 'mapping',            rbc                - Reset Boot counter                                                                                    
                                           'hm_sensors', 'send', 'send_file', 'send_debug_file', 'send_test_file',           
                                           'send_file_stop' - Type 'can' for full help                                       
canstats           - CAN statistics monitor - Live display of CAN bus traffic, dropped frames, and buffer utilization        reboot             - System reboot - 'reboot' (normal restart), 'reboot reset' (reset boot counter before reboot)          
                                           (updates 1Hz)                                                                     
cell               - Cellular control - 'cell' (status), 'cell scan' (network scan), 'cell info' (detailed info)             reset              - Factory reset immediate - Clear all settings and restore factory defaults immediately (requires       
                                                                                                                                                                          confirmation)                                                                   
certs              - Print SFLASH Certs                                                                                      reset_reboot       - Factory reset on reboot - Clear all settings and restore factory defaults on next system reboot       
coap               - CoAP messaging - 'coap <IP> <URI> [JSON] [port] [get|post|put|delete] [con|non]' - Use 'coap ?' for     s                  - System status - Display system state, uptime, connectivity, and operational parameters                
                                           details                                                                           
config             - Configuration - 'config <item> <value>' - Items: upload_url, ota_url, device_id, org_id, interval,      set_mac            - Set the MAC address <MAC>                                                                             
                                           boot_delay                                                                        
core               - Display a list of the well know core URIs                                                               set_serial         - Set the serial number of a unit <serial number>                                                       
cs                 - Control/Sensor status - Display all control and sensor values, states, and configurations               set_time           - Set the device local time <unix_time>                                                                 
csr                - Create a CSR                                                                                            set_wifi           - Set Wi-Fi interface enable/disable <enable|disable>                                                   
debug              - Debug control - 'debug on/off' (global), 'debug <flag>' (specific flag) - Use 'debug ?' for flag list   ss                 - Sensor status - Display all sensor readings, states, thresholds, and alarm conditions                 
diags              - Runtime Diagnostics <on> | <off>                                                                        ssid               - WiFi credentials - 'ssid <name> <password> [security]' - security: WPA2PSK (default), WPA3, OPEN      
ecdh               - ecdh <Remote Public Key>                                                                                stack              - Stack usage - Display thread stack usage, high water marks, and available stack space                 
get_latest         - OTA firmware update - 'get_latest <type>' - Types: master, slave, sflash, beta_master, beta_slave,      t                  - TTY test mode - shows input characters and tests TTY functions                                        
                                           factory                                                                           
get_mac            - Get MAC and SN from Manufacturing server                                                                test_capture       - Test file capture and viewing functionality                                                           
imx                - iMatrix client - 'imx' (status), 'imx flush' (clear statistics), 'imx stats' (detailed statistics),     thing              - Thing info - Display IoT thing name, type, attributes, shadow state, and cloud connection status      
                                           'imx pause' (pause upload), 'imx resume' (resume upload)                          
l_get              - Request list of devices [0-CFG, 1-OTA, 2-CAL]                                                           threads            - Thread/Timer tracking - 'threads' (table), 'threads -v' (detailed), 'threads -j' (JSON), 'threads -h' 
                                                                                                                                                                          (help)                                                                          
led                - LED control - 'off' (all LEDs off), 'test' (test pattern), 'wifi' (WiFi status), 'display <0-5>'        txp                - Set Wi-Fi TX Power (0-31)                                                                             
                                           (specific state)                                                                  
loc                - Location info - 'loc' (current GPS position), 'loc history' (location log), 'loc geofence' (fence       v                  - Version info - Display firmware version, build date, hardware revision, and bootloader version        
                                           status)                                                                           
log                - Logging control - 'log on' (enable logging), 'log off' (disable), 'log status' (show state)             wifi               - WiFi control - 'st_start' (station mode), 'ap_start' (AP mode), 'off' (shutdown), 'status' (current   
                                                                                                                                                                          state)                                                                          
mem                - Memory status - Display heap usage, stack usage, free memory, and fragmentation statistics              wifi_scan          - WiFi scan - 'wifi_scan' (scan now), 'wifi_scan show' (cached results), 'wifi_scan status' (auto-scan  
             


## Task
The output is too wide. Make the total output of both columns to be 200 characters, 100 characters for each column.
generate the output dynamically.
Determine the width of the largest command and the add 2 to the value. this is **command width**
All command must display in **command width**.
Then print the description up to the total width of 96 characters.
descriptions tha exceed this will wrap any text to the next line starting again at the **command width**
Do not break any words. add  padding to wrapped line to maintain the alignment of both columns.

## Deliveralbles
1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/cleanup_cli_ help_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
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
9. Update all documents with relevant details

## ASK ANY QUESIONS needed to verify work requirements.
