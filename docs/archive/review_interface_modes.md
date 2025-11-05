# Review the settings and configuration changes for the wlan0 and eth0 interfaces

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read all iMatrix/IMX_Platform/LINUX_Platform/networking source files
read Fleet-Connect-1/init/imx_client_init.c

## During the intialization the system reads the details of the interaces from the configuration file.
Review how these settings are applied to the confifuration for system and how the the network processing code handles this. 
review the networking code and processing the wlan0 and eth0 interface if they are set to dhcp server. I think there is a bug. if they are running in server mode the code should not change the settings I think it is resetting the interface.
Make sure the settings in the configuraiton file are correctly appiled to the process_network.c routines and network_mode_config.c routines.

Review process_network.c and related files and generate a report 

Provide a full plan and example output of an interface operating in dhcp server mode.
