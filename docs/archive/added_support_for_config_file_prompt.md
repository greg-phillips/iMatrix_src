
## Aim add support for new config file entries
Configuration file entries for the entries ethernet_can_format have been updated with new helper functions. 
New entry for support_obd2 has been added. 

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


read all source files in ~/iMatrix/iMatrix_Client/Fleet-Connect-1/init
read source file in ~/iMatrix/iMatrix_Client/iMatrix/canbus/can_structs.h
read ~/iMatrix/iMatrix_Client/CAN_DM/docs/CONFIG_V13_FORMAT_GUIDE.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style


## Task
Use the settings from the configuration file to set the variables in the cb variable
entries:
ethernet_can_format
process_obd2_frames
For reference here is the key structure

typedef struct canbus_product
{
    product_details_t *can_controller;
    CANBusSpeed_t can0_speed;
    CANBusSpeed_t can1_speed;
    imx_status_t (*can_msg_process)(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg);
    void (*set_can_sensor)(uint32_t imx_id, double value);
    can_stats_t can0_stats;
    can_stats_t can1_stats;
    can_stats_t can_eth_stats;
    uint32_t can_eth_malformed_frames;
    can_bus_status_t cbs;
    ethernet_can_format_t ethernet_can_format;  /**< Ethernet CAN format */
    uint32_t dbc_files_count;                   /**< Number of DBC files for Ethernet CAN (bus 2) */
    file_dbc_config_t *dbc_files;               /**< Array of DBC file configurations for Ethernet CAN */
    can_parse_line_fp parse_line_handler;       /**< Function pointer for CAN line parsing (selected based on ethernet_can_format) */
    unsigned int use_ethernet_server    : 1;    /**< Flag to enable/disable Ethernet CAN server (runtime only, not persisted) */
    unsigned int process_obd2_frames    : 1;    /**< Flag to enable/disable OBD2 frame processing */
} canbus_product_t;

Review entire source for references to ethernet_can_format and provide a list of any thatn may need to be recoded to corretly use the enumerated types.

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/added_support_for_config_file_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. After every code change run the linter and build the system to ensure there are not compile errors. If compile errors are found fix them.
5. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number or recompilation required for syntax errors, time taken in both eplased and actual work time, time waiting on user responses  to complete the fearure.
6. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

