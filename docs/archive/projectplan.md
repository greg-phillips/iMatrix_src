# Network Configuration Diagnostic Messages Enhancement - Implementation Plan

**Project**: Add extensive diagnostic messages and backup functionality during network configuration
**Date**: 2025-11-01
**Status**: Planning Phase - Awaiting User Approval

---

## Table of Contents

1. [Background and Requirements](#background-and-requirements)
2. [Current System Analysis](#current-system-analysis)
3. [Implementation Approach](#implementation-approach)
4. [Detailed Changes by File](#detailed-changes-by-file)
5. [Testing Strategy](#testing-strategy)
6. [Review and Verification](#review-and-verification)

---

## Background and Requirements

### User Requirements (from plan_network_config_update.md)

The initialization sequence in `Fleet-Connect-1/init/imx_client_init.c` reads the configuration file and applies network settings. When the networking system initializes and determines that the network configuration has changed, we need to:

1. **Backup Configuration Files**: Before writing new configuration files, back them up with an incremented naming scheme (`-n.bak` where n is incremented based on existing backups)

2. **Extensive Diagnostics**: As functions write new network configurations, use `imx_cli_print()` to provide extensive details of the new configuration being written

### Example Network Configuration

```
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
  DHCP Range Start: 192.168.7.100
  DHCP Range End:   192.168.7.200
 Interface [1]:
  Name:             wlan0
  Mode:             dhcp_client
  IP Address:       (none)
  Netmask:          (none)
  Gateway:          (none)
  DHCP Server:      Disabled
  Provide Internet: No
```

---

## Current System Analysis

### Network Configuration Flow

```
Boot Sequence
    ↓
imx_apply_network_mode_from_config()  [network_auto_config.c]
    ↓
calculate_network_config_hash()       [Calculates MD5 hash]
    ↓
compare with stored hash              [Detects changes]
    ↓
apply_network_configuration()         [If changed]
    ↓
    ├── apply_eth0_config()           [Ethernet configuration]
    ├── apply_wlan0_config()          [WiFi configuration]
    ├── apply_ppp0_config()           [Cellular configuration]
    ↓
write_network_interfaces_file()       [network_interface_writer.c]
    ↓
    ├── write_eth0_interface()
    ├── write_wlan0_interface()
    └── write to /etc/network/interfaces
    ↓
generate_hostapd_config()             [If WiFi AP mode]
    └── write to /etc/network/hostapd.conf
    ↓
generate_dhcp_server_config()         [If DHCP server enabled]
    └── write to /etc/network/udhcpd.{interface}.conf
    ↓
update_network_blacklist()
    ↓
schedule_network_reboot()             [Reboot pending]
```

### Configuration Files Written

| File Path | Purpose | Current Backup | Writer Function |
|-----------|---------|----------------|-----------------|
| `/etc/network/interfaces` | Main network interfaces config | `.backup` | `write_network_interfaces_file()` |
| `/etc/network/hostapd.conf` | WiFi AP mode configuration | `.orig` (on remove) | `generate_hostapd_config()` |
| `/etc/network/udhcpd.eth0.conf` | DHCP server for eth0 | `.orig` (on remove) | `generate_dhcp_server_config()` |
| `/etc/network/udhcpd.wlan0.conf` | DHCP server for wlan0 | `.orig` (on remove) | `generate_dhcp_server_config()` |
| `/etc/sv/udhcpd/run` | Runit service script | None | `generate_udhcpd_run_script()` |

### Current Limitations

1. **Backup Strategy**:
   - Uses simple `.backup` or `.orig` extensions
   - Overwrites previous backups (no history)
   - Only backs up on removal, not before writing

2. **Diagnostic Messages**:
   - Minimal logging during configuration writing
   - No detailed display of configuration being applied
   - Limited visibility into what changed

---

## Implementation Approach

### Design Principles

1. **Minimal Code Impact**: Keep changes simple and focused
2. **Non-Breaking**: Maintain backward compatibility
3. **Reusable**: Create generic backup function for all files
4. **Verbose**: Provide extensive diagnostic output using `imx_cli_print()`
5. **Maintainable**: Follow existing code patterns and Doxygen documentation

### Key Components to Add

#### 1. Generic Backup Utility Function

Create a new utility module `network_config_backup.h/c` with:

```c
/**
 * @brief Create incremented backup of a configuration file
 *
 * Searches for existing backups (-1.bak, -2.bak, etc.) and creates
 * the next numbered backup. Example:
 * - If file.conf-1.bak and file.conf-2.bak exist
 * - Creates file.conf-3.bak
 *
 * @param filepath Path to file to backup
 * @param backup_path_out Buffer to store backup path (optional, can be NULL)
 * @param buffer_size Size of backup_path_out buffer
 * @return 0 on success, -1 on error
 */
int backup_config_file_incremental(const char *filepath,
                                   char *backup_path_out,
                                   size_t buffer_size);
```

#### 2. Diagnostic Message Templates

Create helper functions for consistent diagnostic output:

```c
/**
 * @brief Print network interface configuration details
 *
 * @param iface Pointer to interface configuration
 */
void print_interface_config_details(const network_interfaces_t *iface);

/**
 * @brief Print DHCP server configuration details
 *
 * @param interface Interface name
 * @param start_ip DHCP range start
 * @param end_ip DHCP range end
 * @param gateway Gateway address
 */
void print_dhcp_config_details(const char *interface,
                               const char *start_ip,
                               const char *end_ip,
                               const char *gateway);
```

---

## Detailed Changes by File

### File 1: Create `network_config_backup.h` (NEW)

**Location**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_config_backup.h`

**Purpose**: Header file for incremental backup functionality

**Content**:
```c
/*
 * Copyright header...
 */

/** @file network_config_backup.h
 *
 *  Network Configuration File Backup Utilities
 *
 *  Created on: 2025-11-01
 *      Author: greg.phillips
 *
 *  @brief Utilities for backing up network configuration files
 *
 *  Provides incremental backup functionality for network configuration files.
 *  Backups are numbered sequentially (-1.bak, -2.bak, etc.) to preserve history.
 */

#ifndef NETWORK_CONFIG_BACKUP_H_
#define NETWORK_CONFIG_BACKUP_H_

#ifdef LINUX_PLATFORM

#include <stdint.h>
#include <stdbool.h>

/******************************************************
 *                    Constants
 ******************************************************/
#define MAX_BACKUP_NUMBER    99     /* Maximum backup number to search for */
#define BACKUP_EXTENSION     ".bak" /* Backup file extension */

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Create incremented backup of a configuration file
 *
 * Searches for existing backups with pattern: filename-N.bak (where N is 1, 2, 3, etc.)
 * and creates the next numbered backup. Preserves file permissions.
 *
 * Example: If /etc/network/interfaces-1.bak and -2.bak exist,
 *          creates /etc/network/interfaces-3.bak
 *
 * @param filepath          Path to file to backup
 * @param backup_path_out   Buffer to store created backup path (optional, can be NULL)
 * @param buffer_size       Size of backup_path_out buffer
 *
 * @return   0  Success - backup created
 * @return  -1  Error - file doesn't exist or backup failed
 *
 * @note If filepath doesn't exist, returns -1 (not an error for first boot)
 * @note Logs backup creation using imx_cli_print()
 */
int backup_config_file_incremental(const char *filepath,
                                   char *backup_path_out,
                                   size_t buffer_size);

/**
 * @brief Find the next available backup number for a file
 *
 * Searches for existing backup files with pattern filename-N.bak
 * and returns the next available number.
 *
 * @param filepath  Path to original file
 *
 * @return  Next backup number (1 if no backups exist, 2 if -1.bak exists, etc.)
 * @return  -1 if maximum backup number exceeded
 *
 * @note Checks up to MAX_BACKUP_NUMBER (99)
 */
int find_next_backup_number(const char *filepath);

#endif /* LINUX_PLATFORM */

#endif /* NETWORK_CONFIG_BACKUP_H_ */
```

### File 2: Create `network_config_backup.c` (NEW)

**Location**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_config_backup.c`

**Purpose**: Implementation of incremental backup functionality

**Key Functions**:
1. `find_next_backup_number()` - Scans for existing -N.bak files
2. `backup_config_file_incremental()` - Creates next numbered backup

**Implementation Details**:
- Uses `stat()` to check for existing backup files
- Uses `cp -p` to preserve permissions (BusyBox compatible)
- Logs backup creation with `imx_cli_print()`
- Returns -1 if file doesn't exist (normal for first boot)

### File 3: Modify `network_interface_writer.c`

**Location**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_interface_writer.c`

**Changes**:

#### A. Add header include
```c
#include "network_config_backup.h"
```

#### B. Enhance `backup_network_interfaces()` function
**Current** (line 242):
```c
int backup_network_interfaces(void)
{
    char cmd[256];
    int ret;

    NETWORK_WRITER_DEBUG(("Backing up network interfaces file\n"));

    // Use cp to preserve permissions
    snprintf(cmd, sizeof(cmd), "cp -p %s %s 2>/dev/null",
             NETWORK_INTERFACES_FILE, NETWORK_INTERFACES_BACKUP);

    ret = system(cmd);
    if (ret != 0) {
        // File might not exist on first run
        NETWORK_WRITER_DEBUG(("No existing interfaces file to backup\n"));
        return 0;
    }

    return 0;
}
```

**Modified**:
```c
int backup_network_interfaces(void)
{
    char backup_path[512];

    imx_cli_print("=== Backing Up Network Interfaces Configuration ===\n");

    // Create incremental backup
    if (backup_config_file_incremental(NETWORK_INTERFACES_FILE,
                                       backup_path,
                                       sizeof(backup_path)) == 0) {
        imx_cli_print("  Backup created: %s\n", backup_path);
    } else {
        imx_cli_print("  No existing file to backup (first boot)\n");
    }

    return 0;
}
```

#### C. Enhance `write_network_interfaces_file()` function
Add diagnostic messages before writing each interface:

```c
int write_network_interfaces_file(void)
{
    FILE *fp;
    int ret = 0;

    imx_cli_print("\n");
    imx_cli_print("=======================================================\n");
    imx_cli_print("   WRITING NETWORK INTERFACES CONFIGURATION\n");
    imx_cli_print("   File: %s\n", NETWORK_INTERFACES_FILE);
    imx_cli_print("=======================================================\n");

    // Create backup of existing file
    backup_network_interfaces();

    // ... existing code ...

    // Before write_eth0_interface():
    imx_cli_print("\n--- Ethernet Interface (eth0) ---\n");

    // Before write_wlan0_interface():
    imx_cli_print("\n--- Wireless Interface (wlan0) ---\n");

    // After successful write:
    imx_cli_print("\n");
    imx_cli_print("=== Network Interfaces File Written Successfully ===\n");
    imx_cli_print("\n");

    // ... rest of existing code ...
}
```

#### D. Enhance `write_eth0_interface()` function
Add detailed diagnostic output:

```c
static int write_eth0_interface(FILE *fp)
{
    interface_mode_t mode;
    bool sharing;
    network_interfaces_t *iface = NULL;

    // Find the eth0 interface in device_config
    for (int i = 0; i < device_config.no_interfaces && i < IMX_INTERFACE_MAX; i++) {
        if (strcmp(device_config.network_interfaces[i].name, "eth0") == 0) {
            iface = &device_config.network_interfaces[i];
            break;
        }
    }

    get_interface_config("eth0", &mode, &sharing);

    // Print configuration details
    imx_cli_print("  Interface:        eth0\n");
    imx_cli_print("  Mode:             %s\n",
                  mode == IMX_IF_MODE_SERVER ? "static (server)" : "dhcp (client)");

    if (mode == IMX_IF_MODE_SERVER && iface) {
        imx_cli_print("  IP Address:       %s\n", iface->ip_address);
        imx_cli_print("  Netmask:          %s\n", iface->netmask);
        imx_cli_print("  Gateway:          %s\n", iface->gateway);
        if (iface->use_dhcp_server) {
            imx_cli_print("  DHCP Server:      Enabled\n");
            imx_cli_print("  DHCP Start:       %s\n", iface->dhcp_start);
            imx_cli_print("  DHCP End:         %s\n", iface->dhcp_end);
        } else {
            imx_cli_print("  DHCP Server:      Disabled\n");
        }
        imx_cli_print("  Internet Sharing: %s\n", sharing ? "Yes" : "No");
    } else {
        imx_cli_print("  IP Assignment:    DHCP Client\n");
    }

    // ... existing fprintf() code ...
}
```

#### E. Enhance `write_wlan0_interface()` function
Similar detailed diagnostic output as eth0

#### F. Enhance `generate_hostapd_config()` function
Add backup and diagnostics:

```c
int generate_hostapd_config(void)
{
    FILE *fp;
    char hostname[64];
    char backup_path[512];
    // ... existing variable declarations ...

    imx_cli_print("\n");
    imx_cli_print("=======================================================\n");
    imx_cli_print("   WRITING WIFI ACCESS POINT CONFIGURATION\n");
    imx_cli_print("   File: %s\n", HOSTAPD_CONFIG_FILE);
    imx_cli_print("=======================================================\n");

    // Backup existing config if it exists
    if (backup_config_file_incremental(HOSTAPD_CONFIG_FILE,
                                       backup_path,
                                       sizeof(backup_path)) == 0) {
        imx_cli_print("  Backup created: %s\n", backup_path);
    }

    // ... existing code to get hostname ...

    // Print configuration details
    imx_cli_print("\n--- WiFi Access Point Settings ---\n");
    imx_cli_print("  Interface:        wlan0\n");
    imx_cli_print("  SSID:             %s\n", hostname);
    imx_cli_print("  Security:         WPA2-PSK\n");
    imx_cli_print("  Password:         %s\n", device_config.wifi.ap_passphrase);
    imx_cli_print("  Channel:          6\n");
    imx_cli_print("  Mode:             802.11n (2.4GHz)\n");
    imx_cli_print("  Country Code:     US\n");
    imx_cli_print("  Control Interface: /var/run/hostapd\n");

    // ... existing fprintf() code ...

    imx_cli_print("\n=== WiFi Access Point Configuration Written Successfully ===\n");
    imx_cli_print("\n");

    // ... rest of existing code ...
}
```

### File 4: Modify `dhcp_server_config.c`

**Location**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

**Changes**:

#### A. Add header include
```c
#include "network_config_backup.h"
```

#### B. Enhance `write_dhcp_config_file()` function
Add backup and diagnostics:

```c
static int write_dhcp_config_file(const char *interface, const dhcp_config_params_t *params)
{
    char config_path[256];
    char temp_path[256];
    char backup_path[512];
    // ... existing declarations ...

    // Create config file paths
    snprintf(config_path, sizeof(config_path), "%s/udhcpd.%s.conf", DHCP_CONFIG_DIR, interface);
    snprintf(temp_path, sizeof(temp_path), "%s/udhcpd.%s.conf.tmp", DHCP_CONFIG_DIR, interface);

    imx_cli_print("\n");
    imx_cli_print("=======================================================\n");
    imx_cli_print("   WRITING DHCP SERVER CONFIGURATION\n");
    imx_cli_print("   Interface: %s\n", interface);
    imx_cli_print("   File: %s\n", config_path);
    imx_cli_print("=======================================================\n");

    // Backup existing config if it exists
    if (backup_config_file_incremental(config_path, backup_path, sizeof(backup_path)) == 0) {
        imx_cli_print("  Backup created: %s\n", backup_path);
    }

    // ... existing DNS server retrieval code ...

    // Print configuration details
    imx_cli_print("\n--- DHCP Server Settings ---\n");
    imx_cli_print("  Interface:        %s\n", interface);
    imx_cli_print("  IP Range Start:   %s\n", params->ip_start);
    imx_cli_print("  IP Range End:     %s\n", params->ip_end);
    imx_cli_print("  Subnet Mask:      %s\n", params->subnet);
    imx_cli_print("  Gateway/Router:   %s\n", params->router);
    imx_cli_print("  DNS Servers:      %s\n", dns_servers);
    imx_cli_print("  Lease Time:       86400 seconds (24 hours)\n");
    imx_cli_print("  Max Leases:       101\n");

    // ... existing fprintf() code ...

    imx_cli_print("\n=== DHCP Server Configuration Written Successfully ===\n");
    imx_cli_print("\n");

    // ... rest of existing code ...
}
```

### File 5: Modify `network_auto_config.c`

**Location**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`

**Changes**:

#### A. Add header include
```c
#include "network_config_backup.h"
```

#### B. Enhance `apply_network_configuration()` function
Add summary diagnostics:

```c
static int apply_network_configuration(void)
{
    int changes_made = 0;

    imx_cli_print("\n");
    imx_cli_print("*******************************************************\n");
    imx_cli_print("*                                                     *\n");
    imx_cli_print("*   APPLYING NETWORK CONFIGURATION CHANGES            *\n");
    imx_cli_print("*                                                     *\n");
    imx_cli_print("*******************************************************\n");
    imx_cli_print("\n");
    imx_cli_print("Network Configuration Source: Binary config file\n");
    imx_cli_print("Number of Interfaces:         %d\n", device_config.no_interfaces);
    imx_cli_print("\n");

    // Process each interface in device_config
    for (int i = 0; i < device_config.no_interfaces && i < IMX_INTERFACE_MAX; i++) {
        network_interfaces_t *iface = &device_config.network_interfaces[i];

        if (!iface->enabled || strlen(iface->name) == 0) {
            imx_cli_print("Interface %d: %s (Disabled - Skipping)\n",
                         i, strlen(iface->name) > 0 ? iface->name : "(unnamed)");
            continue;
        }

        imx_cli_print("=== Processing Interface %d: %s ===\n", i, iface->name);
        imx_cli_print("  Enabled:          Yes\n");
        imx_cli_print("  Mode:             %s\n",
                     iface->mode == IMX_IF_MODE_SERVER ? "server" : "client");

        // Apply configuration based on interface
        if (strcmp(iface->name, "eth0") == 0) {
            changes_made |= apply_eth0_config(iface);
        } else if (strcmp(iface->name, "wlan0") == 0) {
            changes_made |= apply_wlan0_config(iface);
        } else if (strcmp(iface->name, "ppp0") == 0) {
            changes_made |= apply_ppp0_config(iface);
        }

        imx_cli_print("\n");
    }

    if (changes_made) {
        imx_cli_print("=== Writing Master Network Interfaces File ===\n");

        // Generate network interfaces file
        if (write_network_interfaces_file() != 0) {
            imx_cli_print("ERROR: Failed to write network interfaces file\n");
        }

        // Update blacklist configuration
        imx_cli_print("=== Updating Network Blacklist ===\n");
        if (update_network_blacklist() != 0) {
            imx_cli_print("WARNING: Failed to update network blacklist\n");
        }

        imx_cli_print("\n");
        imx_cli_print("*******************************************************\n");
        imx_cli_print("*   NETWORK CONFIGURATION CHANGES COMPLETE            *\n");
        imx_cli_print("*   Total changes applied: %d\n", changes_made);
        imx_cli_print("*******************************************************\n");
        imx_cli_print("\n");
    } else {
        imx_cli_print("No configuration changes required\n");
    }

    return changes_made;
}
```

### File 6: Update CMakeLists.txt

**Location**: `iMatrix/CMakeLists.txt` (or appropriate CMakeLists.txt for networking module)

**Changes**:
Add new source files to build:

```cmake
# Network platform sources
set(NETWORK_SOURCES
    # ... existing files ...
    IMX_Platform/LINUX_Platform/networking/network_config_backup.c  # NEW
    # ... rest of existing files ...
)
```

---

## Testing Strategy

### Test Environment Setup

1. **Test Configuration Files**:
   - Prepare test binary config files with different network settings
   - Test scenarios: eth0 server, wlan0 client, both modes, etc.

2. **Test Script**: Create `test_network_config_diagnostics.sh`

```bash
#!/bin/bash
# Test network configuration diagnostic messages

echo "=== Network Configuration Diagnostic Test ==="

# Test 1: First boot (no existing configs)
echo "Test 1: First boot scenario"
rm -f /etc/network/interfaces*
rm -f /etc/network/hostapd.conf*
rm -f /etc/network/udhcpd.*
./Fleet-Connect -P

# Test 2: Configuration change (should create -1.bak)
echo "Test 2: First configuration change"
# Modify config file
./Fleet-Connect -P

# Test 3: Another change (should create -2.bak)
echo "Test 3: Second configuration change"
# Modify config again
./Fleet-Connect -P

# Verify backups created
echo "Checking backup files:"
ls -la /etc/network/*bak 2>/dev/null || echo "No backups found"
```

### Test Cases

| Test ID | Scenario | Expected Behavior | Verification |
|---------|----------|-------------------|--------------|
| TC-1 | First boot | No backups created, full diagnostics shown | Check logs, no .bak files |
| TC-2 | Config change #1 | Creates -1.bak files, diagnostics shown | Verify -1.bak exists |
| TC-3 | Config change #2 | Creates -2.bak files, diagnostics shown | Verify -2.bak exists |
| TC-4 | No config change | No new backups, "unchanged" message | No new .bak files |
| TC-5 | eth0 server mode | Full eth0 diagnostics, DHCP config shown | Check log output |
| TC-6 | wlan0 AP mode | Full wlan0 diagnostics, hostapd shown | Check log output |
| TC-7 | Multiple interfaces | Both interface diagnostics shown | Check log output |

### Expected Diagnostic Output Example

```
*******************************************************
*                                                     *
*   APPLYING NETWORK CONFIGURATION CHANGES            *
*                                                     *
*******************************************************

Network Configuration Source: Binary config file
Number of Interfaces:         2

=== Processing Interface 0: eth0 ===
  Enabled:          Yes
  Mode:             server

=======================================================
   WRITING NETWORK INTERFACES CONFIGURATION
   File: /etc/network/interfaces
=======================================================

=== Backing Up Network Interfaces Configuration ===
  Backup created: /etc/network/interfaces-1.bak

--- Ethernet Interface (eth0) ---
  Interface:        eth0
  Mode:             static (server)
  IP Address:       192.168.7.1
  Netmask:          255.255.255.0
  Gateway:          192.168.7.1
  DHCP Server:      Enabled
  DHCP Start:       192.168.7.100
  DHCP End:         192.168.7.200
  Internet Sharing: No

=======================================================
   WRITING DHCP SERVER CONFIGURATION
   Interface: eth0
   File: /etc/network/udhcpd.eth0.conf
=======================================================

  Backup created: /etc/network/udhcpd.eth0.conf-1.bak

--- DHCP Server Settings ---
  Interface:        eth0
  IP Range Start:   192.168.7.100
  IP Range End:     192.168.7.200
  Subnet Mask:      255.255.255.0
  Gateway/Router:   192.168.7.1
  DNS Servers:      8.8.8.8 8.8.4.4
  Lease Time:       86400 seconds (24 hours)
  Max Leases:       101

=== DHCP Server Configuration Written Successfully ===

... (similar output for wlan0 if configured) ...

*******************************************************
*   NETWORK CONFIGURATION CHANGES COMPLETE            *
*   Total changes applied: 2
*******************************************************

======================================
NETWORK CONFIGURATION CHANGED
System will reboot in 5 seconds
======================================
```

---

## Review and Verification

### Pre-Implementation Checklist

- [ ] User has reviewed and approved this plan
- [ ] All required functions identified
- [ ] File locations confirmed
- [ ] Backup strategy validated
- [ ] Diagnostic message format approved

### Implementation Checklist

- [ ] Create network_config_backup.h
- [ ] Create network_config_backup.c
- [ ] Modify network_interface_writer.c
- [ ] Modify dhcp_server_config.c
- [ ] Modify network_auto_config.c
- [ ] Update CMakeLists.txt
- [ ] Build and verify compilation
- [ ] Test on development system
- [ ] Verify backup file creation
- [ ] Verify diagnostic output

### Post-Implementation Verification

- [ ] All configuration changes logged with imx_cli_print()
- [ ] Incremental backups created (-1.bak, -2.bak, etc.)
- [ ] No regression in existing network functionality
- [ ] Diagnostic output matches expected format
- [ ] Code follows existing patterns and style
- [ ] Doxygen comments complete and accurate
- [ ] No compilation warnings
- [ ] Memory leaks checked (if applicable)

---

## Questions for User

Before proceeding with implementation, please confirm:

1. **Backup Naming**: Is the `-N.bak` naming scheme acceptable? (e.g., `interfaces-1.bak`, `interfaces-2.bak`)
   - Alternative: `.bak.N` (e.g., `interfaces.bak.1`)

2. **Backup Limit**: Should we limit the number of backups kept? (e.g., keep last 10 only)
   - Current plan: No limit, let them accumulate

3. **Diagnostic Verbosity**: Is the level of diagnostic output in the examples above appropriate?
   - Too verbose?
   - Need more detail?

4. **Backup Timing**: Should we backup:
   - Only when configuration changes (current plan)
   - On every boot regardless of changes

5. **Additional Files**: Are there any other configuration files that should be backed up?
   - Current: interfaces, hostapd.conf, udhcpd.*.conf
   - Others: wpa_supplicant.conf, etc.?

---

## Next Steps

Upon approval of this plan:

1. Create todo list with implementation tasks
2. Implement changes file by file
3. Test each component incrementally
4. Integration testing
5. Final review and documentation update

---

**Status**: ✅ Plan Complete - Awaiting User Review and Approval

**Author**: Claude Code
**Date**: 2025-11-01
**Version**: 1.0
