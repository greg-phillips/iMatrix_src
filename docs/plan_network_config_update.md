# Provide detailed diagnostic messages during Network re configuration event

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read Fleet-Connect-1/init/imx_client_init.c
Read all iMatrix/IMX_Platform/LINUX_Platform/networking source files

## Overview
The initialization squence in the source file Fleet-Connect-1/init/imx_client_init.c reads the configuration file and aplies the settings from the newwork An example of typical settings are
=== Network Configuration ===
Network Interfaces: 2
 Interface [0]:
  Name:             eth0
  Mode:             static
  IP Address:       192.168.7.1
  Netmask:          255.255.255.0
  Gateway:          192.168.7.1
  DHCP Server:      Enabled
  Provide Internet: No
  DHCP Range Start: 0.0.0.0
  DHCP Range End:   0.0.0.0
 Interface [1]:
  Name:             wlan0
  Mode:             dhcp_client
  IP Address:       (none)
  Netmask:          (none)
  Gateway:          (none)
  DHCP Server:      Disabled
  Provide Internet: No

## Extenesive diagnotics and backup

When the networking system initializes it determines if the network configuraton has changed and if so it writes new configuration files.
Before writing the new configuraton files back them up to a -n.bak where n is incremeted based on any other backups.
As the functions write new network configurations use the imx_cli_print function to provide extensive details of the new configuraton being written.

### 1. Deliveralbles
1. Create a plan document to implement this enhancements
2. Allow me to review before proceeding.


