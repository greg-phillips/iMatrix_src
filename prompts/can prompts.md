Add a new sub command to the can command to the cli.
the sub command is send the arguments to the command are as follows <can device> <node id> <data>.
Where can device is can0, can1, caneth, the node is the node id, data is up to 8 bytes of data seperated by spaces  both the node an data entries are in hexadecimal, in either case. Typical command would look like

can send can0 18ff4df 01 02 03 0f AA CC

The data is then sent to the routine 

void canFrameHandler(CanDrvInterface quake_canbus, uint32_t canId, uint8_t *buf, uint8_t bufLen)

quake_canbus values are can0 = 0, can1 = 1, caneth = 2


wtite an addition to the imx_can_process routine. The routine needs to check a flag to see if the routine should process a file upload procedure. store the flag in the cb.cbs structure. the purpose of the flag it to tell the imx_can_process routine if it needs to process a file upload. 
use a cli can command start the process the command has two forms.
1. can send_file <can device> <filename> 
2. can send_debug_file <can device> <filename>

Where can device is can0, can1, caneth
quake_canbus values are can0 = 0, can1 = 1, caneth = 2
if the canbus argument is missing assume can0

The file is a standard PCAN trace file. 


create a new source file can_file_send.c to place these routines.

there needs a to be a separate flag in the cb.cbs structure to indicate if this is a debug send mode.

The command will set the flag to process the file upload. the command will also load the filename into a local variable in the can_send_file.c file. when the command sets the filename it should set a local state machine to CAN_FILE_UPLOAD_INIT.

When the imx_can_process routine is called is check if the can_send_file flag is set and then calls the routine in the file can_send_file.c that operates a state machine. the rouine is passed the current_time as passed to the imx_can_process routine. during the CAN_FILE_UPLOAD_INIT state the routine will attempt to open the filename that was save during the cli command. if it can not open the file then use the imx_cli_print command to issue an error. if it opens then store the current_time locally, then progess to the next step of reading the file. the first line of data of the file includes a time stamp. All action will now be relative to this time stamp. if the command used was can send_file then check to make sure that the time of the record plus the starting time offset has passed before sending that data to the canFrameHandler routine. if the command used was can send_debug_file then send each frame regardless of the logged time in the file one second apart. use the imx_is_later helper routine to determine if the time is correct to send the next frame. once the file has been sent close the file and reset the processing flag. in debug mode print the contents of the message before calling canFrameHandler. make sure the design is fully defined before starting to code.


***

Add a new sub commands to the can command to the cli.
the sub command will display the signals of one or all the can bus nodes. the format of the command is:
can nodes <canbus> <node_id> 

Where can device is can0, can1, caneth

if the <node_id> is missing display all the nodes on the selected canbus
if the canbus argument is missing assume can0

use the functionality of the cli_capture_open to save the results and display them in the cli instead of just printing the output to the terminal. Review the functionality in the source Fleet-Connect-1/cli/fcgw.c


***

Add a new sub commands to the can command to the cli.
the sub command will display the mappings of the vehicle mappings. the sub command is mapping this will call a new routine in vehicle_sensor_mappings.c file that will display a list of the mapping details.

***

We need a set of fuctions to update the internal sensor data like those in the file Fleet-Connect-1/OBD2/get_J1939.c for the IMX_HM_WRECKER product id. The sensors that the IMX_HM_WRECKER can update are define in this structure:

typedef struct hm_truck_variables_
{
    uint32_t odometer_entry;
    uint32_t vehicle_speed_entry;
    uint32_t battery_voltage;
    uint32_t battery_current;
    uint32_t battery_state_of_charge;
    unsigned int odometer_valid : 1;
    unsigned int vehicle_speed_valid : 1;
    unsigned int battery_voltage_vaild : 1;
    unsigned int battery_current_vaild : 1;
    unsigned int battery_state_of_charge_vaild : 1;
} mh_truck_variables_t; 

use this as guidelines to create the boiler plate for the get_hm_truck.c file. Complete as much details as you can and I will fill in the rest. These new functions will link from the 

***
The system needs to be built and run on different arhcitecture platforms the Fleet-Connect-1 is built on a Ubuntu Linux VM using compliers and tools for an iMX-6. The CAN_DM program needs to be built on either a WSL-2 or Apple MAC. Do not change the Make Files for Fleet-Connect-1 or iMatrix that will cause them issues when building on the Linux VM for the embedded sytem.
Update the build makefiles for the CAN_DM program to run on WSL-2 and Apple MAC systems. Create plan the highlights these steps and changes needed to support this system.

***


Add support for reading the network interface settings from the product JSON file. The format of the settings is shown in the following json text.
{
  "interfaces": [
    {
      "name": "eth0",
      "mode": "dhcp_client",
      "ip": null,
      "netmask": null,
      "gateway": null,
      "dhcp_server": false,
      "provide_internet": true
    },
    {
      "name": "eth1",
      "mode": "static",
      "ip": "192.168.1.10",
      "netmask": "255.255.255.0",
      "gateway": "192.168.1.1",
      "dhcp_server": true,
      "provide_internet": false
    },
    {
      "name": "eth2",
      "mode": "dhcp_server",
      "ip": "10.0.0.1",
      "netmask": "255.255.255.0",
      "gateway": null,
      "dhcp_server": true,
      "provide_internet": false
    }
  ]
}
the network interfaces section is mandatory.
the interfaces defined in the JSON file are for eth0 and wifi0.
add details for these fields to the configuration that is use to generate the profile data for the Fleet-Connect-1 application.
Add these details to the routine read_config and write_config in the file Fleet-Connect-1/init/wrp_config.c
Add the details to the end of the configuration so that the file structure for verison 1 and 2 is compatiable.
Create a document defining all the entries in the JSON file as a guide for users.
The details on how to process the network interface configurations will be the subject of another task.

***

Add functionality to the the routine Fleet-Connect-1/init/imx_client_init.c after line 658 to procees the network configuration.
If the network configuration changes from the configuration in the device_config structure make the changes to the settings. making these changes will be similar to how the cli commmand iMatrix/cli/cli_network_mode.c processes these settings. Making these changes may force a reboot of the device. As long as the configuration does not change between reboots the system should only reboot once if the network configuration is chanaged.
Include diagnostic message regarding the settings.
review changes needed to support static addresses including currrent data structure elements and if changes are needed.

***

Add support for reading the internal sensor list from the product JSON file. The format of the settings is shown in the following json text.
{
  "predefined": [
    { "id": "IMX_INTERNAL_SENSOR_GPS_LATITUDE", "name": "Latitude", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_GPS_LONGITUDE", "name": "Longitude", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_GPS_ALTITUDE", "name": "Altitude", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_WIFI_RF_CHANNEL", "name": "Wi-FI Rf Channel", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_WIFI_RF_RSSI", "name": "Wi-FI Rf Rssi", "poll_time": 0, "sample_time": 0, "type": "IMX_INT32" },
    { "id": "IMX_INTERNAL_SENSOR_WIFI_RF_NOISE", "name": "Wi-FI Rf Noise", "poll_time": 0, "sample_time": 0, "type": "IMX_INT32" },
    { "id": "IMX_INTERNAL_SENSOR_BATTERY_LEVEL", "name": "Battery Level", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_SOFTWARE_VERSION", "name": "Software Version", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_BOOT_COUNT", "name": "Boot Count", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_4G_RF_RSSI", "name": "4G Rf RSSI", "poll_time": 0, "sample_time": 0, "type": "IMX_INT32" },
    { "id": "IMX_INTERNAL_SENSOR_4G_CARRIER", "name": "4G Carrier", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_IMEI", "name": "IMEI", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_SIM_CARD_STATE", "name": "Sim Card State", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_SIM_CARD_IMSI", "name": "Sim Card Imsi", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_SIM_CARD_ICCID", "name": "Sim Card Iccid", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_4G_NETWORK_TYPE", "name": "4G Network Type", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_GEOFENCE_ENTER", "name": "Geofence Enter", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_GEOFENCE_EXIT", "name": "Geofence Leave", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_GEOFENCE_ENTER_BUFFER", "name": "Geofence Enter Buffer", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_GEOFENCE_EXIT_BUFFER", "name": "Geofence Leave Buffer", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_GEOFENCE_IN", "name": "In Geofence", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_HOST_CONTROLLER", "name": "Host Controller", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_4G_BER", "name": "4G Ber", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },

    { "id": "IMX_INTERNAL_SENSOR_VEHICLE_SPEED", "name": "Speed", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_DIRECTION", "name": "Direction", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_IDLE_STATE", "name": "Idle State", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_VEHICLE_STOPPED", "name": "Vehicle Stopped", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_HARD_BRAKE", "name": "Hard Break", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_HARD_ACCELERATION", "name": "Hard Acceleration", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_HARD_TURN", "name": "Hard Turn", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_HARD_BUMP", "name": "Hard Bump", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_HARD_POTHOLE", "name": "Hard Pothole", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_HARD_IMPACT", "name": "Hard Impact", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },

    { "id": "IMX_INTERNAL_SENSOR_DAILY_HOURS_OF_OPERATION", "name": "Daily Hours Of Operation", "poll_time": 0, "sample_time": 0, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_ODOMETER", "name": "Odometer", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_IGNITION_STATUS", "name": "Ignition Status", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },

    { "id": "IMX_INTERNAL_SENSOR_COMM_LINK_TYPE", "name": "Link Status", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_CANBUS_STATUS", "name": "CAN Bus Status", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_CAN_0_SPEED", "name": "CAN 0 Speed", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_CAN_1_SPEED", "name": "CAN 1 Speed", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },

    { "id": "IMX_INTERNAL_SENSOR_BATTERY_STATE_OF_CHARGE", "name": "Battery State of Charge", "poll_time": 100, "sample_time": 10000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_BATTERY_VOLTAGE", "name": "Battery Voltage", "poll_time": 100, "sample_time": 10000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_BATTERY_CURRENT", "name": "Battery Current", "poll_time": 100, "sample_time": 10000, "type": "IMX_FLOAT" },

    { "id": "IMX_INTERNAL_SENSOR_CUMULATIVE_THROUGHPUT", "name": "Cumulative Throughput", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_CHARGE_RATE", "name": "Charge Rate", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_ESTIMATED_RANGE", "name": "Estimated Range", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_BATTERY_STATE_OF_HEALTH", "name": "Battery State of Health", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_TRIP_DISTANCE", "name": "Trip Distance", "poll_time": 1000, "sample_time": 60000, "type": "IMX_FLOAT" },
    { "id": "IMX_INTERNAL_SENSOR_CHARGING_STATUS", "name": "Charging Status", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" },
    { "id": "IMX_INTERNAL_SENSOR_TRIP_METER", "name": "Trip Meter", "poll_time": 0, "sample_time": 0, "type": "IMX_UINT32" }
  ]
}

create a data structure to hold this information.
Add a cli command "predfined" to display the list of entries.
Keep the order from the json file intack during the process.
save this information into the config file. Update wrp_config.c to support writing and reading  these entries.
Keep this as version 3 as we have not released any updates to the field.

***

Write a python script to generate a default JSON file for the iMatrix Settings for all the signals in a DBC file.

The command line should accept options from 0 to 9 and include a filename to process, for example

pythion3 gen_default_json.py -0 file1.dbc -0 file2.dbc -1 file3.dbc

the enties should be an array with the name "dbc_signals"

The entry for each signal should follow the format shown below:

{
  "name": "TX Data Rate",
  "defaultValue": 0,
  "iconUrl": "https://storage.googleapis.com/imatrix-files/a3e5d012-93f4-4c35-9827-b52a8afaac93-Sensor%20General.svg",
  "thresholdQualificationTime": 0,
  "minAdvisoryEnabled": false,
  "minAdvisory": 0,
  "minWarningEnabled": false,
  "minWarning": 0,
  "minAlarmEnabled": false,
  "minAlarm": 0,
  "maxAdvisoryEnabled": false,
  "maxAdvisory": 0,
  "maxWarningEnabled": false,
  "maxWarning": 0,
  "maxAlarmEnabled": false,
  "maxAlarm": 0,
  "calibrationMode": none,
  "calibrateValue1": 0,
  "calibrateValue2": 0,
  "calibrateValue3": 0,
  "calibrationRef1": 0,
  "calibrationRef2": 0,
  "calibrationRef3": 0
  "visible" : true,
  "enabled" : true,
  "send_to_imatrix" : true
}

the name is generated from three items. The format is:
<CAN BUS No.>:<CAN BUS Node ID>:<name>

The CAN BUS No is the number of the can bus as passed on the command line, for example the -0 <dbc filename> is CAN BUS 0.
The CAN BUS Node ID is the decimal value of the BO_ associated with the signals.
The name is the DBC File Signal name (SG_).



***

Add Add support for reading the default sensor settings from the product JSON file. The format of the settings is shown in the following snip of json text.

{
  "dbc_signals": [
    {
      "name": "0:419368144:Vehicle_status",
      "defaultValue": 0,
      "iconUrl": "https://storage.googleapis.com/imatrix-files/a3e5d012-93f4-4c35-9827-b52a8afaac93-Sensor%20General.svg",
      "thresholdQualificationTime": 0,
      "minAdvisoryEnabled": false,
      "minAdvisory": 0,
      "minWarningEnabled": false,
      "minWarning": 0,
      "minAlarmEnabled": false,
      "minAlarm": 0,
      "maxAdvisoryEnabled": false,
      "maxAdvisory": 0,
      "maxWarningEnabled": false,
      "maxWarning": 0,
      "maxAlarmEnabled": false,
      "maxAlarm": 0,
      "calibrationMode": "none",
      "calibrateValue1": 0,
      "calibrateValue2": 0,
      "calibrateValue3": 0,
      "calibrationRef1": 0,
      "calibrationRef2": 0,
      "calibrationRef3": 0,
      "visible": true,
      "enabled": true,
      "send_to_imatrix": true
    },

modify the routine convert_to_imatrx in the source file convert_imatrix.c to use helper functions for the settings of the sensor values. Currently many of the sensor values are hard coded. match the entries in the dbc_signals JSON file to the hard coded entries. create helper routines for the setting of each sensor. If the name of the cds.can_bus_node[can_bus_entry].control_sensors[cs_index].name matches the name of an entry in the dbc_signals JSON then use the value from the JSON otherwise use the value that the sensor is currently initialized to. ask any questions needed to fully define this plan

***

add support to write the dbc_signals out to the config file. Output the data as binary structure. Do not include the name. subsitute the name with the imx_id (32 bit unsigned int) for the sensor. If there is no corresponding imx_id for the name of the signal abort with an error. the process to associate the imx_id with the name should be done prior to the saving of the config file.
Add support to the print config to print all the entries. print the entries as a table and only print the name, imx_id, visible, enabled and send_to_imatrix flagas. ask any questions needed to develop a plan for this implemenation.

***