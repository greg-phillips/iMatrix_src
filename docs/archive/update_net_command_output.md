# Update net command output for dhcp server mode

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read all iMatrix/IMX_Platform/LINUX_Platform/networking source files

## the net command is not  show the leases

root@iMatrix:FC-1:0131557250:~# dumpleases -f /var/lib/misc/udhcpd.eth0.leases
Mac Address       IP Address      Host Name           Expires in
3c:18:a0:55:d5:17 192.168.7.100   Greg-P1-Laptop      23:55:38


Actual output

+=====================================================================================================+
|                                        NETWORK MANAGER STATE                                        |
+=====================================================================================================+
| Status: OFFLINE | State: NET_WAIT_RESULTS      | Interface: NONE  | Duration: 00:12    | DTLS: INIT |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDR | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+---------+-------------------+
| eth0      | NO      | NO      | NO      |     0 |       0 | NONE      | VALID   | NONE              |
| wlan0     | YES     | YES     | NO      |     0 |       0 | NONE      | VALID   | RUN 189 ms        |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
+=====================================================================================================+
|                                        INTERFACE LINK STATUS                                        |
+=====================================================================================================+
| eth0      | INACTIVE - Link up (100Mb/s)                                                              |
| wlan0     | NO LINK - Associated (SierraTelecom)                                                      |
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
| WiFi Enabled: YES    | Cellular: NOT_READY | Test Attempted: YES    | Last Link Up: NO              |
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
| Network traffic: ETH0: TX: 501.18 KB   | WLAN0 TX: 44.25 KB    | PPP0 TX: 4.00 GB                   |
|                        RX: 25.35 MB    |       RX: 406.51 KB   |      RX: 4.00 GB                   |
| Network rates  : ETH0: TX: 0 Bytes/s     | WLAN0 TX: 0 Bytes/s     | PPP0 TX: 0 Bytes/s             |
|                        RX: 0 Bytes/s     |       RX: 0 Bytes/s     |      RX: 0 Bytes/s             |
+=====================================================================================================+ 
Provide a full plan and example output of an interface operating in dhcp server mode.
