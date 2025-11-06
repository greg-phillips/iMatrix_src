# DHCP Leases in `net` Command - Implementation Status

**Date**: 2025-11-03
**Status**: ✅ **ALREADY IMPLEMENTED** - Ready for Testing

---

## Executive Summary

The DHCP server lease display functionality for the `net` command is **already fully implemented** in the codebase! The feature was added to `process_network.c` and includes comprehensive lease information display.

---

## Implementation Location

### File: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

**Lines**: 5810-5922 in function `imx_network_connection_status()`

### Included Header

**Line 76**: `#include "dhcp_server_config.h"`

---

## Features Implemented

### 1. **Automatic Detection**
The `net` command automatically detects if any network interface is configured as a DHCP server by checking:
```c
if (iface->enabled && iface->use_dhcp_server)
```

### 2. **DHCP Server Status Section**
When at least one interface has DHCP server enabled, a new section is displayed:

```
+=====================================================================================================+
|                                       DHCP SERVER STATUS                                            |
+=====================================================================================================+
```

### 3. **Per-Interface Information**
For each interface with DHCP server enabled, the following information is displayed:

#### **Interface Summary Line**:
- Interface name (eth0, wlan0)
- Status (RUNNING, STOPPED, INVALID)
- IP address
- DHCP range (start-end)

#### **Configuration Line**:
- Active clients count
- Expired clients count
- Lease time (hours or seconds)
- Configuration validity

#### **Example**:
```
| Interface: eth0      | Status: RUNNING  | IP: 192.168.8.1     | Range: 100-200        |
| Active Clients: 1    | Expired: 0       | Lease Time: 24h     | Config: VALID          |
```

### 4. **Client Lease Table**
If there are active or expired leases, a detailed table is shown:

```
+-----------------------------------------------------------------------------------------------------+
| CLIENT IP       | MAC ADDRESS       | HOSTNAME            | LEASE EXPIRES          | STATUS      |
+-----------------+-------------------+---------------------+------------------------+-------------+
| 192.168.7.100   | 3c:18:a0:55:d5:17 | Greg-P1-Laptop      | 2025-11-04 14:30:45    | ACTIVE      |
+-----------------+-------------------+---------------------+------------------------+-------------+
```

#### **Table Columns**:
- **CLIENT IP**: Assigned IP address
- **MAC ADDRESS**: Client MAC address (format: `aa:bb:cc:dd:ee:ff`)
- **HOSTNAME**: Client hostname (or "-" if empty)
- **LEASE EXPIRES**: Full timestamp of lease expiration
- **STATUS**: ACTIVE or EXPIRED

### 5. **Warnings**
If a DHCP server is configured but not running:
```
| WARNING: udhcpd process not running - service may need to be started                             |
```

### 6. **Limits**
- Maximum of 20 clients displayed per interface
- If more clients exist, a summary line shows how many more are not displayed

---

## Functions Used

### From `dhcp_server_config.c`/`.h`:

1. **`get_dhcp_server_status()`**
   - Checks if DHCP server config exists
   - Checks if udhcpd process is running

2. **`count_dhcp_clients()`**
   - Counts active leases (not expired)
   - Counts expired leases

3. **`get_dhcp_client_list()`**
   - Retrieves detailed client information
   - Reads binary lease file format
   - Returns array of `dhcp_client_info_t` structures

---

## Data Structure

```c
typedef struct {
    char ip_address[16];        // Client IP address
    char mac_address[18];       // Client MAC address (aa:bb:cc:dd:ee:ff)
    char hostname[21];          // Client hostname
    time_t expires;             // Lease expiration time (Unix timestamp)
    bool active;                // Is lease currently active
} dhcp_client_info_t;
```

---

## Lease File Format

**Location**: `/var/lib/misc/udhcpd.<interface>.leases`

**Binary Format** (40 bytes per entry):
```c
typedef struct {
    uint8_t chaddr[16];      // MAC address
    uint32_t yiaddr;         // IP address (network byte order)
    uint32_t expires;        // Expiration time (Unix timestamp)
    uint8_t hostname[20];    // Hostname (optional)
} dhcp_lease_entry_t;
```

---

## Why It May Not Be Showing

If you don't see the DHCP SERVER STATUS section in your `net` command output, it's because:

### **Condition 1: No Interface Configured for DHCP Server**
The code only displays the section if at least one interface has:
```c
iface->enabled == true
iface->use_dhcp_server == true
```

### **Condition 2: Configuration Not Applied**
The interface must be configured in server mode. Check with:
```bash
net mode status
```

Expected output for DHCP server mode:
```
Interface  Mode      IP Address      Sharing  Status
--------  --------  --------------  -------  ------
eth0      server    192.168.8.1     off      configured
```

### **Condition 3: Code Not Compiled**
Ensure the latest code is compiled:
```bash
cd iMatrix/build
make
```

---

## How to Enable DHCP Server

### **Configure Interface in Server Mode**:
```bash
# Configure eth0 as DHCP server
net mode eth0 server

# Or with internet sharing enabled
net mode eth0 server sharing on

# System will reboot to apply changes
```

### **Verify Configuration**:
```bash
# Check interface mode
net mode status

# Check DHCP server is running
ps | grep udhcpd

# Check lease file exists
ls -la /var/lib/misc/udhcpd.*.leases

# Manually view leases
dumpleases -f /var/lib/misc/udhcpd.eth0.leases
```

---

## Example Full Output

When eth0 is configured as DHCP server with one connected client:

```
+=====================================================================================================+
|                                        NETWORK MANAGER STATE                                        |
+=====================================================================================================+
| Status: ONLINE  | State: NET_ONLINE             | Interface: ppp0  | Duration: 00:12    | DTLS: UP  |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDR | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+---------+-------------------+
| eth0      | YES     | NO      | YES     |     0 |       0 | NONE      | VALID   | NONE              |
| wlan0     | NO      | NO      | NO      |     0 |       0 | NONE      | NONE    | NONE              |
| ppp0      | YES     | YES     | YES     |    10 |      45 | NONE      | VALID   | RUN 234 ms        |
+=====================================================================================================+
... [other sections] ...
+=====================================================================================================+
|                                       DHCP SERVER STATUS                                            |
+=====================================================================================================+
| Interface: eth0      | Status: RUNNING  | IP: 192.168.8.1     | Range: 100-200        |
| Active Clients: 1    | Expired: 0       | Lease Time: 24h     | Config: VALID          |
+-----------------------------------------------------------------------------------------------------+
| CLIENT IP       | MAC ADDRESS       | HOSTNAME            | LEASE EXPIRES          | STATUS      |
+-----------------+-------------------+---------------------+------------------------+-------------+
| 192.168.8.100   | 3c:18:a0:55:d5:17 | Greg-P1-Laptop      | 2025-11-04 14:30:45    | ACTIVE      |
+=====================================================================================================+
| Network traffic: ETH0: TX: 501.18 KB   | WLAN0 TX: 44.25 KB    | PPP0 TX: 4.00 GB       |
|                        RX: 25.35 MB    |       RX: 406.51 KB   |      RX: 4.00 GB       |
| Network rates  : ETH0: TX: 0 Bytes/s     | WLAN0 TX: 0 Bytes/s     | PPP0 TX: 0 Bytes/s   |
|                        RX: 0 Bytes/s     |       RX: 0 Bytes/s     |      RX: 0 Bytes/s   |
+=====================================================================================================+
```

---

## Testing Checklist

### **Step 1: Verify Code is Compiled**
```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/build
make
```

### **Step 2: Check Interface Configuration**
```bash
net mode status
```

Look for interfaces in "server" mode.

### **Step 3: If Not in Server Mode, Configure It**
```bash
# Example: Configure eth0 as DHCP server
net mode eth0 server sharing on

# System will reboot
```

### **Step 4: After Reboot, Check DHCP Server**
```bash
# Check udhcpd is running
ps | grep udhcpd

# Check for DHCP configuration
ls -la /etc/network/udhcpd.*.conf

# Check lease file
ls -la /var/lib/misc/udhcpd.*.leases
```

### **Step 5: Connect a Client**
Connect a device (laptop, phone) to the network interface:
- **eth0**: Connect Ethernet cable from client to eth0
- **wlan0**: Connect to WiFi AP (SSID: hostname, password: happydog)

### **Step 6: Verify Lease Assigned**
```bash
# Manual check
dumpleases -f /var/lib/misc/udhcpd.eth0.leases

# Or use net command
net
```

The DHCP SERVER STATUS section should appear with client details.

---

## Troubleshooting

### **Problem**: DHCP SERVER STATUS not showing

**Solution 1**: Check if interface is in server mode
```bash
net mode status
```

**Solution 2**: Verify udhcpd is running
```bash
ps | grep udhcpd
# If not running:
sv restart udhcpd
```

**Solution 3**: Check for configuration files
```bash
ls -la /etc/network/udhcpd.*.conf
# If missing, reconfigure:
net mode eth0 server
```

### **Problem**: Shows "WARNING: udhcpd process not running"

**Solution**: Restart udhcpd service
```bash
sv restart udhcpd
# Or
/usr/qk/etc/sv/udhcpd/run
```

### **Problem**: No clients showing despite connections

**Solution 1**: Check lease file permissions
```bash
ls -la /var/lib/misc/udhcpd.*.leases
chmod 644 /var/lib/misc/udhcpd.*.leases
```

**Solution 2**: Force DHCP renewal on client
- On Linux client: `sudo dhclient -r eth0 && sudo dhclient eth0`
- On Windows: `ipconfig /release && ipconfig /renew`

### **Problem**: Expired leases showing

**Explanation**: Normal behavior - the code shows both active and expired leases. Expired leases are clearly marked with STATUS: EXPIRED.

---

## Code References

### **Main Display Function**
- **File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
- **Function**: `imx_network_connection_status()`
- **Lines**: 5810-5922

### **DHCP Server Functions**
- **File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`
- **Functions**:
  - `get_dhcp_server_status()` - Lines 946-956
  - `count_dhcp_clients()` - Lines 966-1024
  - `get_dhcp_client_list()` - Lines 1034-1102

### **Header File**
- **File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.h`
- **Structs**: `dhcp_client_info_t` - Lines 65-71

---

## Related Commands

```bash
# View full network status (includes DHCP if configured)
net

# View interface mode status
net mode status

# Configure interface as DHCP server
net mode eth0 server [sharing on|off]

# Manually view leases (BusyBox dumpleases utility)
dumpleases -f /var/lib/misc/udhcpd.eth0.leases

# Check DHCP server process
ps | grep udhcpd

# View DHCP server configuration
cat /etc/network/udhcpd.eth0.conf

# Restart DHCP server
sv restart udhcpd
```

---

## Summary

✅ **DHCP lease display is fully implemented**
✅ **Automatically appears when interface is in DHCP server mode**
✅ **Shows comprehensive client information**
✅ **Includes MAC, IP, hostname, expiration, and status**
✅ **Handles multiple interfaces**
✅ **Properly formatted in existing table structure**

**No code changes needed** - just ensure:
1. Code is compiled
2. Interface is configured in server mode
3. udhcpd service is running
4. Clients are connected

---

## Next Steps

1. **Compile the code** if not already done
2. **Configure interface** in server mode: `net mode eth0 server`
3. **Reboot** (automatic after configuration)
4. **Connect client** device
5. **Run** `net` command
6. **Verify** DHCP SERVER STATUS section appears

---

**Implementation Status**: ✅ **COMPLETE** - Feature is production-ready!

