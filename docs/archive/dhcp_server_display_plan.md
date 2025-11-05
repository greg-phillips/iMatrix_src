# DHCP Server Display Implementation Plan

## Overview
Add DHCP server status display to the `net` command to show when interfaces are operating in DHCP server mode, including client lease information.

## Background
- The current `net` command displays network interface details focused on client mode
- DHCP server functionality is managed by udhcpd (BusyBox DHCP server)
- Configuration files are stored in `/etc/network/udhcpd.{interface}.conf`
- Lease files are stored in `/var/lib/misc/udhcpd.{interface}.leases`
- The `network_interfaces_t` structure contains `use_dhcp_server` flag

## Detection Logic
1. Check if interface has `use_dhcp_server` flag set in `device_config.network_interfaces[]`
2. Verify udhcpd configuration file exists: `/etc/network/udhcpd.{interface}.conf`
3. Check if udhcpd process is running for the interface

## Lease File Format
The udhcpd lease file format (from BusyBox udhcpd):
```c
struct dhcpOfferedAddr {
    uint8_t chaddr[16];         // Client MAC address
    uint32_t yiaddr;            // Assigned IP address (network byte order)
    uint32_t expires;           // Lease expiration time (Unix timestamp)
    uint8_t hostname[20];       // Client hostname (optional)
};
```

## Implementation Components

### 1. New Helper Functions (in dhcp_server_config.c)

#### Function: `get_dhcp_server_status()`
```c
/**
 * @brief Get DHCP server status for an interface
 *
 * @param interface Interface name (eth0 or wlan0)
 * @param[out] is_configured Set to true if config exists
 * @param[out] is_running Set to true if udhcpd process is running
 * @return 0 on success, negative on error
 */
int get_dhcp_server_status(const char *interface, bool *is_configured, bool *is_running);
```

#### Function: `count_dhcp_clients()`
```c
/**
 * @brief Count active DHCP clients from lease file
 *
 * @param interface Interface name (eth0 or wlan0)
 * @param[out] active_count Number of active leases
 * @param[out] expired_count Number of expired leases
 * @return 0 on success, negative on error
 */
int count_dhcp_clients(const char *interface, int *active_count, int *expired_count);
```

#### Function: `get_dhcp_client_list()`
```c
/**
 * @brief Get list of DHCP clients with lease details
 *
 * @param interface Interface name (eth0 or wlan0)
 * @param[out] clients Array to fill with client info
 * @param max_clients Maximum clients to return
 * @return Number of clients returned, negative on error
 */
typedef struct {
    char ip_address[16];        // Client IP
    char mac_address[18];       // Client MAC (aa:bb:cc:dd:ee:ff)
    char hostname[21];          // Client hostname
    time_t expires;             // Lease expiration time
    bool active;                // Is lease currently active
} dhcp_client_info_t;

int get_dhcp_client_list(const char *interface, dhcp_client_info_t *clients, int max_clients);
```

#### Function: `is_udhcpd_running()`
```c
/**
 * @brief Check if udhcpd is running for an interface
 *
 * Checks for udhcpd process with the interface's config file
 *
 * @param interface Interface name (eth0 or wlan0)
 * @return true if running, false otherwise
 */
bool is_udhcpd_running(const char *interface);
```

### 2. Modified Function (in process_network.c)

Update `imx_network_connection_status()` to include DHCP server section after the traffic statistics section.

## Example Output

### Scenario 1: eth0 as DHCP Server, wlan0 as Client

```
+=====================================================================================================+
|                                        NETWORK MANAGER STATE                                        |
+=====================================================================================================+
| Status: ONLINE  | State: NET_ONLINE             | Interface: wlan0 | Duration: 01:23:45 | DTLS: UP |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDR | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+---------+-------------------+
| eth0      | YES     | NO      | YES     |     0 |       0 | NONE      | VALID   | NONE              |
| wlan0     | YES     | NO      | YES     |    10 |      15 | NONE      | VALID   | 1234 ms ago       |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
+=====================================================================================================+
|                                        INTERFACE LINK STATUS                                        |
+=====================================================================================================+
| eth0      | ACTIVE - DHCP SERVER MODE (192.168.100.1)                                             |
| wlan0     | ACTIVE - Connected to "OfficeWiFi" (192.168.1.100)                                    |
| ppp0      | INACTIVE - Daemon not running                                                         |
+=====================================================================================================+
|                                            CONFIGURATION                                            |
+=====================================================================================================+
| ETH0 Cooldown: 010.000 s | WIFI Cooldown: 010.000 s | Max State: 010.000 s | Online Check: 010.000 s|
| Min Score: 3            | Good Score: 7            | Max WLAN Retries: 3   | PPP Retries: 0         |
| WiFi Reassoc: Enabled  | Method: wpa_cli         | Scan Wait: 2000   ms                             |
+=====================================================================================================+
|                                            SYSTEM STATUS                                            |
+=====================================================================================================+
| ETH0 DHCP: STOPPED  | ETH0 Enabled: YES    | WLAN Retries: 0   | First Run: NO                      |
| WiFi Enabled: YES    | Cellular: NOT_READY | Test Attempted: YES    | Last Link Up: YES             |
+=====================================================================================================+
|                                              DNS CACHE                                              |
+=====================================================================================================+
| Status: PRIMED      | IP: 8.8.8.8          | Age: 1234       ms | Valid: YES                         |
+=====================================================================================================+
|                                       BEST INTERFACE ANALYSIS                                       |
+=====================================================================================================+
| Interface: wlan0    | Score: 10  | Latency: 15     ms                                               |
+=====================================================================================================+
|                                            RESULT STATUS                                            |
+=====================================================================================================+
| Last Result: ONLINE                                                                                 |
+=====================================================================================================+
| Network traffic: ETH0: TX: 5.07 KB     | WLAN0 TX: 45.2 MB     | PPP0 TX: 0 Bytes                   |
|                        RX: 2.51 MB     |       RX: 123 MB      |      RX: 0 Bytes                   |
| Network rates  : ETH0: TX: 125 Bytes/s   | WLAN0 TX: 1.2 KB/s    | PPP0 TX: 0 Bytes/s               |
|                        RX: 567 Bytes/s   |       RX: 45 KB/s     |      RX: 0 Bytes/s               |
+=====================================================================================================+
|                                       DHCP SERVER STATUS                                            |
+=====================================================================================================+
| Interface: eth0     | Status: RUNNING  | IP: 192.168.100.1   | Range: 192.168.100.100-200         |
| Active Clients: 3   | Expired: 1       | Lease Time: 24h     | Config: VALID                      |
+-----------------------------------------------------------------------------------------------------+
| CLIENT IP       | MAC ADDRESS       | HOSTNAME            | LEASE EXPIRES          | STATUS      |
+-----------------+-------------------+---------------------+------------------------+-------------+
| 192.168.100.101 | aa:bb:cc:dd:ee:01 | laptop              | 2025-01-06 15:23:45    | ACTIVE      |
| 192.168.100.102 | aa:bb:cc:dd:ee:02 | phone               | 2025-01-06 16:45:12    | ACTIVE      |
| 192.168.100.103 | aa:bb:cc:dd:ee:03 | tablet              | 2025-01-06 14:30:00    | ACTIVE      |
| 192.168.100.104 | aa:bb:cc:dd:ee:04 | printer             | 2025-01-05 10:15:23    | EXPIRED     |
+=====================================================================================================+
```

### Scenario 2: Both eth0 and wlan0 as DHCP Servers (Dual Interface Mode)

```
+=====================================================================================================+
|                                       DHCP SERVER STATUS                                            |
+=====================================================================================================+
| Interface: eth0     | Status: RUNNING  | IP: 192.168.100.1   | Range: 192.168.100.100-200         |
| Active Clients: 5   | Expired: 0       | Lease Time: 24h     | Config: VALID                      |
+-----------------------------------------------------------------------------------------------------+
| CLIENT IP       | MAC ADDRESS       | HOSTNAME            | LEASE EXPIRES          | STATUS      |
+-----------------+-------------------+---------------------+------------------------+-------------+
| 192.168.100.101 | aa:bb:cc:dd:ee:01 | desktop             | 2025-01-06 15:23:45    | ACTIVE      |
| 192.168.100.102 | aa:bb:cc:dd:ee:02 | laptop              | 2025-01-06 16:45:12    | ACTIVE      |
| 192.168.100.103 | aa:bb:cc:dd:ee:03 | server              | 2025-01-06 14:30:00    | ACTIVE      |
| 192.168.100.104 | aa:bb:cc:dd:ee:04 | camera1             | 2025-01-06 18:00:00    | ACTIVE      |
| 192.168.100.105 | aa:bb:cc:dd:ee:05 | camera2             | 2025-01-06 18:15:00    | ACTIVE      |
+=====================================================================================================+
| Interface: wlan0    | Status: RUNNING  | IP: 10.42.0.1       | Range: 10.42.0.100-200             |
| Active Clients: 2   | Expired: 0       | Lease Time: 24h     | Config: VALID                      |
+-----------------------------------------------------------------------------------------------------+
| CLIENT IP       | MAC ADDRESS       | HOSTNAME            | LEASE EXPIRES          | STATUS      |
+-----------------+-------------------+---------------------+------------------------+-------------+
| 10.42.0.101     | bb:cc:dd:ee:ff:01 | phone               | 2025-01-06 14:20:30    | ACTIVE      |
| 10.42.0.102     | bb:cc:dd:ee:ff:02 | tablet              | 2025-01-06 15:45:00    | ACTIVE      |
+=====================================================================================================+
```

### Scenario 3: No DHCP Server Running (Current Behavior - No Changes)

```
[Standard output as shown in the original docs/add_dhchp_server_deatils.md - no DHCP server section]
```

### Scenario 4: DHCP Server Configured But Not Running

```
+=====================================================================================================+
|                                       DHCP SERVER STATUS                                            |
+=====================================================================================================+
| Interface: eth0     | Status: STOPPED  | IP: 192.168.100.1   | Range: 192.168.100.100-200         |
| Active Clients: 0   | Expired: 0       | Lease Time: 24h     | Config: VALID                      |
| ERROR: udhcpd process not running - service may need to be started                                |
+=====================================================================================================+
```

## Implementation Steps

1. **Add helper functions to dhcp_server_config.c:**
   - `is_udhcpd_running()` - Check if udhcpd process is active
   - `count_dhcp_clients()` - Count active/expired leases
   - `get_dhcp_client_list()` - Parse lease file and return client details

2. **Update dhcp_server_config.h:**
   - Add function declarations
   - Add `dhcp_client_info_t` structure definition

3. **Update process_network.c:**
   - Add DHCP server status section after traffic statistics
   - Iterate through interfaces checking `use_dhcp_server` flag
   - Display server status and client list for each DHCP server interface

4. **Update get_interface_status_string():**
   - Add "DHCP SERVER MODE" status when interface is in server mode
   - Show server IP address in status line

## Technical Details

### Lease File Location
- Path: `/var/lib/misc/udhcpd.{interface}.leases`
- Format: Binary file with fixed-size records
- Record size: 40 bytes (16 MAC + 4 IP + 4 expires + 16 reserved/hostname)

### Process Detection
- Check for udhcpd process: `ps | grep "udhcpd.*{interface}"`
- Or check PID file: `/var/run/udhcpd.{interface}.pid`

### Configuration Reading
- Parse `/etc/network/udhcpd.{interface}.conf`
- Extract: start IP, end IP, lease time, interface name

## Error Handling

1. **Lease file doesn't exist:** Show "No clients" message
2. **Lease file corrupted:** Show error message, skip client list
3. **udhcpd not running but configured:** Show warning message
4. **Configuration file missing:** Don't show DHCP section for that interface

## Testing Scenarios

1. Single interface (eth0) as DHCP server with multiple clients
2. Dual interface mode (eth0 + wlan0) both as DHCP servers
3. DHCP server configured but process not running
4. No DHCP servers configured (backward compatibility)
5. Lease file with expired entries
6. Empty lease file (no clients)
7. Large number of clients (>20) - test pagination/truncation

## Files to Modify

1. `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.h`
2. `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`
3. `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
4. `iMatrix/IMX_Platform/LINUX_Platform/networking/network_status.c` (if status string needs update)

## Backward Compatibility

- If no interfaces have DHCP server enabled, no DHCP section is shown
- Existing `net` command output remains unchanged for client-only configurations
- New section only appears when at least one interface is in DHCP server mode

## Future Enhancements

1. Add CLI command to release/renew specific client leases
2. Add statistics: total leases issued, DHCP request rate
3. Add hostname resolution for MAC addresses
4. Add option to export lease data to JSON format
5. Add DHCP server restart/reload command

---

**Status:** Design Complete - Ready for Implementation
**Created:** 2025-01-03
**Last Updated:** 2025-01-03
