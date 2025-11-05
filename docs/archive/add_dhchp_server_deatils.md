# Add DHCP Server display to net command

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read all iMatrix/IMX_Platform/LINUX_Platform/networking source files

## Overview the net command currently displays network interface details
The current display is focused on displaying client status.
The output looks like the following
>net
+=====================================================================================================+
|                                        NETWORK MANAGER STATE                                        |
+=====================================================================================================+
| Status: OFFLINE | State: NET_SELECT_INTERFACE  | Interface: NONE  | Duration: 16:25:06 | DTLS: INIT |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDR | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+---------+-------------------+
| eth0      | NO      | NO      | NO      |     0 |       0 | NONE      | VALID   | NONE              |
| wlan0     | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
+=====================================================================================================+
|                                        INTERFACE LINK STATUS                                        |
+=====================================================================================================+
| eth0      | INACTIVE - Link up (100Mb/s)                                                              |
| wlan0     | INACTIVE - SCANNING                                                                       |
| ppp0      | INACTIVE - Daemon not running                                                             |
+=====================================================================================================+
|                                            CONFIGURATION                                            |
+=====================================================================================================+
| ETH0 Cooldown: 010.000 s | WIFI Cooldown: 010.000 s | Max State: 010.000 s | Online Check: 010.000 s|
| Min Score: 3            | Good Score: 7            | Max WLAN Retries: 3   | PPP Retries: 0         |
| WiFi Reassoc: Enabled  | Method: wpa_cli         | Scan Wait: 2000   ms                             |
+=====================================================================================================+
|                                            SYSTEM STATUS                                            |
+=====================================================================================================+
| ETH0 DHCP: STOPPED  | ETH0 Enabled: NO     | WLAN Retries: 0   | First Run: YES                     |
| WiFi Enabled: YES    | Cellular: NOT_READY | Test Attempted: NO     | Last Link Up: NO              |
+=====================================================================================================+
|                                              DNS CACHE                                              |
+=====================================================================================================+
| Status: NOT_PRIMED  | IP: NONE              | Age: N/A         | Valid: NO                          |
+=====================================================================================================+
|                                       BEST INTERFACE ANALYSIS                                       |
+=====================================================================================================+
| Interface: NONE     | Score: N/A | Latency: N/A                                                      |
+=====================================================================================================+
|                                            RESULT STATUS                                            |
+=====================================================================================================+
| Last Result: SETTING_UP                                                                             |
+=====================================================================================================+
| Network traffic: ETH0: TX: 5.07 KB     | WLAN0 TX: 0 Bytes     | PPP0 TX: 4.00 GB                   |
|                        RX: 2.51 MB     |       RX: 0 Bytes     |      RX: 4.00 GB                   |
| Network rates  : ETH0: TX: 0 Bytes/s     | WLAN0 TX: 0 Bytes/s     | PPP0 TX: 0 Bytes/s             |
|                        RX: 56 Bytes/s    |       RX: 0 Bytes/s     |      RX: 0 Bytes/s             |
+=====================================================================================================+

In the file process_network.c the function imx_network_connection_status is used to generate this display.

update the "net" command to recognize when the interfaces are in dhcp_server mode and provide correct details including a list of clients that have leases 

Provide a full plan and example output of an interface operating in dhcp server mode.
