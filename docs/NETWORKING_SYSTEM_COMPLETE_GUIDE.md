# iMatrix Networking System - Complete Comprehensive Guide

**Version**: 2.0 (Post-2025-11-02 Fixes)
**Author**: Network Configuration System Documentation
**Date**: 2025-11-02
**Status**: Complete reference implementation with all critical fixes

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Binary Configuration File Format](#binary-configuration-file-format)
3. [Initialization Sequence](#initialization-sequence)
4. [Array Architecture](#array-architecture)
5. [Configuration Update & Hash Detection](#configuration-update--hash-detection)
6. [Network Configuration Application](#network-configuration-application)
7. [Service Management & Blacklist](#service-management--blacklist)
8. [DHCP Server Configuration](#dhcp-server-configuration)
9. [Interface Modes](#interface-modes)
10. [Command Line Options](#command-line-options)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Critical Bugs Fixed (2025-11-02)](#critical-bugs-fixed-2025-11-02)

---

## System Overview

### Purpose

The iMatrix networking system provides automatic network interface configuration from binary configuration files with:
- **Automatic change detection** using MD5 hashing
- **Multi-interface support** (Ethernet, WiFi, Cellular)
- **Server and client modes** for each interface
- **DHCP server capabilities** with dynamic range configuration
- **Service management** via blacklist for BusyBox runit
- **Automatic reboot** to apply configuration changes

### Key Design Principles

1. **Single Source of Truth**: All configuration from binary config file
2. **Hash-Based Detection**: Only apply changes when configuration actually changed
3. **Sparse Array Architecture**: Interfaces indexed by type, not sequentially
4. **No Hardcoded Values**: All IPs, ranges, etc. read from configuration
5. **Defensive Programming**: Extensive validation and error checking
6. **Automatic Recovery**: System reboots to apply changes cleanly

### Architecture Components

```
Binary Config File (xxx_cfg.bin)
        ↓ (wrp_config.c - read_config())
config_t Structure (in-memory)
        ↓ (imx_client_init.c - index mapping)
device_config.network_interfaces[] (sparse array)
        ↓ (network_auto_config.c - hash detection)
Apply Configuration? (yes if hash changed or -R option)
        ↓
Generate Config Files (/etc/network/*)
        ↓
Update Service Blacklist (/usr/qk/blacklist)
        ↓
Reboot System (5 second countdown)
        ↓
Linux Init System Applies Configuration
```

---

## Binary Configuration File Format

### File Structure

**Format**: Binary file created by CAN_DM utility
**Extension**: `*_cfg.bin`
**Location**: `/usr/qk/etc/sv/` or `IMATRIX_STORAGE_PATH`

**Header** (Version 3+):
```
Offset  Size  Field
------  ----  -----
0x00    4     Signature (0xCAFEBABE little-endian)
0x04    2     Version number (uint16_t little-endian)
0x06    2     Number of sections
...     ...   Section index (version 4+)
```

### Network Section (Version 3+)

**Structure**:
```
Field                Size    Description
-----                ----    -----------
interface_count      2       Number of network interfaces (uint16_t)

For each interface:
  name               32      Interface name ("eth0", "wlan0", "ppp0")
  mode               32      Mode string ("static", "dhcp_client", "server", "dhcp_server")
  ip                 16      IP address (if static/server)
  netmask            16      Subnet mask
  gateway            16      Gateway IP
  dhcp_server        1       DHCP server enabled flag (0=no, 1=yes)
  provide_internet   1       Internet sharing flag (0=no, 1=yes)
  dhcp_server_start  16      DHCP range start (version 10+)
  dhcp_server_end    16      DHCP range end (version 10+)
```

**Example Binary Config**:
```
interface_count = 2

interfaces[0]:
  name = "eth0"
  mode = "static"
  ip = "192.168.7.1"
  netmask = "255.255.255.0"
  gateway = "192.168.7.1"
  dhcp_server = 1
  provide_internet = 0
  dhcp_server_start = "192.168.7.100"
  dhcp_server_end = "192.168.7.199"

interfaces[1]:
  name = "wlan0"
  mode = "dhcp_client"
  ip = ""
  netmask = ""
  gateway = ""
  dhcp_server = 0
  provide_internet = 0
  dhcp_server_start = ""
  dhcp_server_end = ""
```

### Reading Binary Config

**File**: `Fleet-Connect-1/init/wrp_config.c`
**Function**: `read_config()` (line 466)

**Process**:
1. Opens binary file for reading
2. Validates signature and version
3. Reads section index (v4+)
4. Reads each section sequentially
5. For network section (v3+):
   - Reads interface count
   - Reads each interface sequentially into `config->network.interfaces[i]`
   - Stores in SEQUENTIAL array [0], [1], [2], etc.

**Key Point**: Binary file stores interfaces **SEQUENTIALLY** with no index mapping.

---

## Initialization Sequence

### Call Chain

```
main() [linux_gateway.c]
  ↓
linux_gateway_init() [init/init.c]
  ↓
imx_init(&imatrix_config) [iMatrix/imatrix.c]
  ↓
imx_client_init() [Fleet-Connect-1/init/imx_client_init.c]
  │
  ├─→ find_cfg_file() - Locate binary config file
  ├─→ read_config() - Read binary config into config_t
  └─→ Copy network config to device_config (INDEX MAPPING CRITICAL!)
  ↓
imatrix_start() [iMatrix/imatrix_interface.c]
  ↓
MAIN_IMATRIX_SETUP state
  │
  ├─→ network_manager_init() - Initialize network manager
  └─→ imx_apply_network_mode_from_config() - Apply network configuration
      │
      ├─→ Hash detection (has config changed?)
      ├─→ apply_network_configuration() - Generate config files
      ├─→ update_network_blacklist() - Manage services
      └─→ schedule_network_reboot() - Reboot to apply
```

### Detailed Flow

#### Step 1: Binary Config File Location

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Function**: `find_cfg_file()` (line 779)

```c
// Searches IMATRIX_STORAGE_PATH for *_cfg.bin files
char *config_file = find_cfg_file(IMATRIX_STORAGE_PATH);

// Example: "/usr/qk/etc/sv/aptera_cfg.bin"
```

#### Step 2: Read Binary Config

**File**: `Fleet-Connect-1/init/wrp_config.c`
**Function**: `read_config()` (line 466)

```c
config_t *dev_config = read_config(config_file);

// Reads all sections including network interfaces
// dev_config->network.interface_count = 2
// dev_config->network.interfaces[0] = eth0 data
// dev_config->network.interfaces[1] = wlan0 data
```

**Data Structure**:
```c
typedef struct config {
    can_controller_t *product;
    can_node_data_t can[NO_CAN_BUS];
    network_config_t network;  // ← Network configuration here
    // ... other sections ...
} config_t;

typedef struct network_config {
    uint16_t interface_count;  // 2
    network_interface_t interfaces[MAX_NETWORK_INTERFACES];  // Sequential array
} network_config_t;
```

#### Step 3: Index Mapping to device_config (CRITICAL!)

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Function**: `imx_client_init()` (lines 445-554)

**CRITICAL SECTION** - This is where index mapping happens:

```c
if (dev_config->network.interface_count > 0) {
    imx_cli_print("Loading %u network interface(s) from configuration file\r\n",
                  dev_config->network.interface_count);

    /* First, clear all interface slots to ensure clean state */
    for (uint16_t i = 0; i < IMX_INTERFACE_MAX; i++) {
        device_config.network_interfaces[i].enabled = 0;
        device_config.network_interfaces[i].name[0] = '\0';
    }

    /* Map interfaces by NAME to correct logical indices (not sequential!) */
    for (uint16_t i = 0; i < dev_config->network.interface_count; i++) {
        network_interface_t *src = &dev_config->network.interfaces[i];
        int target_idx = -1;

        /* Determine target index based on interface name */
        if (strcmp(src->name, "eth0") == 0) {
            target_idx = IMX_ETH0_INTERFACE;  /* Index 2 */
        } else if (strcmp(src->name, "wlan0") == 0) {
            target_idx = IMX_STA_INTERFACE;   /* Index 0 */
        } else if (strcmp(src->name, "ppp0") == 0) {
            target_idx = IMX_PPP0_INTERFACE;  /* Index 3 */
        }

        /* Copy to CORRECT index, not sequential */
        network_interfaces_t *dst = &device_config.network_interfaces[target_idx];

        /* Copy all data */
        strncpy(dst->name, src->name, IMX_MAX_INTERFACE_NAME_LENGTH);

        /* Map mode string to enum */
        if (strcmp(src->mode, "static") == 0 ||
            strcmp(src->mode, "server") == 0 ||
            strcmp(src->mode, "dhcp_server") == 0) {
            dst->mode = IMX_IF_MODE_SERVER;  /* 0 */
        } else {
            dst->mode = IMX_IF_MODE_CLIENT;   /* 1 */
        }

        /* Copy IP settings */
        strncpy(dst->ip_address, src->ip, sizeof(dst->ip_address) - 1);
        strncpy(dst->netmask, src->netmask, sizeof(dst->netmask) - 1);
        strncpy(dst->gateway, src->gateway, sizeof(dst->gateway) - 1);

        /* Copy DHCP settings */
        dst->use_dhcp_server = src->dhcp_server;
        dst->use_connection_sharing = src->provide_internet;

        /* Copy DHCP range (v11+) */
        if (dst->use_dhcp_server && strlen(src->dhcp_server_start) > 0) {
            strncpy(dst->dhcp_start, src->dhcp_server_start, sizeof(dst->dhcp_start) - 1);
            strncpy(dst->dhcp_end, src->dhcp_server_end, sizeof(dst->dhcp_end) - 1);
            dst->dhcp_lease_time = 86400;  // 24 hours
        }

        /* Enable the interface */
        dst->enabled = 1;
    }

    /* Count actually configured interfaces (not binary config count!) */
    uint16_t configured_count = 0;
    for (uint16_t i = 0; i < IMX_INTERFACE_MAX; i++) {
        if (device_config.network_interfaces[i].enabled &&
            strlen(device_config.network_interfaces[i].name) > 0) {
            configured_count++;
        }
    }
    device_config.no_interfaces = configured_count;
}
```

**Key Points**:
1. **Clears all slots first** - ensures no stale data
2. **Maps by interface NAME** - not by binary config index
3. **Uses logical indices** - IMX_STA_INTERFACE, IMX_ETH0_INTERFACE, etc.
4. **Counts configured** - actual count, not binary file count

**Example Mapping**:
```
Binary Config:      device_config Array:
[0] eth0      →     [0] wlan0 (IMX_STA_INTERFACE)
[1] wlan0     →     [1] EMPTY (IMX_AP_INTERFACE)
                    [2] eth0  (IMX_ETH0_INTERFACE)
                    [3] EMPTY (IMX_PPP0_INTERFACE)
```

#### Step 4: Device Config Loaded

At this point, `device_config` contains:
- `device_config.no_interfaces = 2`
- `device_config.network_interfaces[0]` = wlan0 configuration
- `device_config.network_interfaces[1]` = empty
- `device_config.network_interfaces[2]` = eth0 configuration
- `device_config.network_interfaces[3]` = empty

#### Step 5: iMatrix System Starts

**File**: `iMatrix/imatrix_interface.c`
**Function**: `imatrix_start()` → state machine → `MAIN_IMATRIX_SETUP`

**Code** (line 1010):
```c
case MAIN_IMATRIX_SETUP:
#ifdef LINUX_PLATFORM
    network_manager_init();  // Initialize network manager

    // Apply network interface configuration from saved settings
    int network_config_result = imx_apply_network_mode_from_config();
    if (network_config_result > 0) {
        // Configuration changed, reboot pending
        icb.state = MAIN_IMATRIX_NETWORK_REBOOT_PENDING;
        break;
    }
#endif
```

---

## Array Architecture

### The Sparse Array Design

**Structure**: `IOT_Device_Config_t.network_interfaces[IMX_INTERFACE_MAX]`

**Indices** (from `imx_linux_platform.h` line 294-304):
```c
typedef enum {
    IMX_STA_INTERFACE,      // 0 - wlan0 in Station (client) mode
    IMX_AP_INTERFACE,       // 1 - wlan0 in Access Point (server) mode
    IMX_ETH0_INTERFACE,     // 2 - eth0 (Ethernet)
    IMX_PPP0_INTERFACE,     // 3 - ppp0 (Cellular/PPP)

    IMX_INTERFACE_MAX,      // 4 - Array size (not a valid index)
} imx_network_interface_t;
```

### Why Sparse?

**Logical Grouping**: Each interface type has a dedicated index:
- **wlan0** can be in TWO modes:
  - Index 0 (IMX_STA_INTERFACE): Station/Client mode
  - Index 1 (IMX_AP_INTERFACE): Access Point/Server mode
  - Only ONE active at a time

- **eth0** always at Index 2 (IMX_ETH0_INTERFACE)
- **ppp0** always at Index 3 (IMX_PPP0_INTERFACE)

**Not all indices are always populated!**

### Example Configurations

#### Configuration A: eth0 server, wlan0 client
```
device_config.network_interfaces[]:
  [0] = { enabled: 1, name: "wlan0", mode: CLIENT }  ← STA
  [1] = { enabled: 0, name: "" }                     ← AP (disabled)
  [2] = { enabled: 1, name: "eth0", mode: SERVER }   ← eth0
  [3] = { enabled: 0, name: "" }                     ← ppp0 (not configured)

device_config.no_interfaces = 2
```

#### Configuration B: eth0 client, wlan0 AP
```
device_config.network_interfaces[]:
  [0] = { enabled: 0, name: "" }                     ← STA (disabled)
  [1] = { enabled: 1, name: "wlan0", mode: SERVER }  ← AP
  [2] = { enabled: 1, name: "eth0", mode: CLIENT }   ← eth0
  [3] = { enabled: 0, name: "" }                     ← ppp0 (not configured)

device_config.no_interfaces = 2
```

### Critical Iteration Pattern

**WRONG** (Sequential - misses interfaces at non-sequential indices):
```c
for (int i = 0; i < device_config.no_interfaces; i++) {
    // If no_interfaces=2, only processes i=0,1
    // MISSES index 2 where eth0 might be!
}
```

**CORRECT** (Full array with skip):
```c
for (int i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (!device_config.network_interfaces[i].enabled ||
        strlen(device_config.network_interfaces[i].name) == 0) {
        continue;  // Skip empty slots
    }
    // Process interface at index i
}
```

**All code MUST use the CORRECT pattern** to handle sparse arrays!

---

## Configuration Update & Hash Detection

### Overview

The system uses **MD5 hashing** to detect configuration changes and avoid unnecessary reboots.

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`
**Main Function**: `imx_apply_network_mode_from_config()` (line 689)

### Hash Calculation

**Function**: `calculate_network_config_hash()` (line 136)

**Hashes All Network Configuration**:
- All interface settings (name, mode, IP, netmask, gateway)
- DHCP server settings (if enabled)
- WiFi SSIDs and passphrases (AP and STA)
- Network manager timing configuration

**Code**:
```c
static void calculate_network_config_hash(char *hash_out)
{
    mbedtls_md5_context ctx;
    unsigned char md5_hash[16];

    mbedtls_md5_init(&ctx);
    mbedtls_md5_starts(&ctx);

    // Hash all network interface configurations
    // IMPORTANT: Iterate ALL indices since array is SPARSE
    for (int i = 0; i < IMX_INTERFACE_MAX; i++) {
        network_interfaces_t *iface = &device_config.network_interfaces[i];

        // Skip empty/disabled slots
        if (!iface->enabled || strlen(iface->name) == 0) {
            continue;
        }

        // Hash all fields
        mbedtls_md5_update(&ctx, (const unsigned char *)iface->name, strlen(iface->name));
        mbedtls_md5_update(&ctx, (const unsigned char *)&iface->mode, sizeof(iface->mode));
        mbedtls_md5_update(&ctx, (const unsigned char *)iface->ip_address, strlen(iface->ip_address));
        // ... all other fields ...
    }

    // Hash WiFi configuration
    mbedtls_md5_update(&ctx, (const unsigned char *)device_config.wifi.st_ssid, ...);
    // ... WiFi fields ...

    mbedtls_md5_finish(&ctx, md5_hash);

    // Convert to 32-character hex string
    for (int i = 0; i < 16; i++) {
        sprintf(&hash_out[i*2], "%02x", md5_hash[i]);
    }
    hash_out[32] = '\0';
}
```

**Output**: 32-character hex string (e.g., "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d")

### Hash Storage

**State File**: `/usr/qk/etc/sv/network_config.state`

**Contains**: Single line with 32-character MD5 hash

**Purpose**: Marks the "last applied" configuration

### Change Detection Logic

**Function**: `imx_apply_network_mode_from_config()` (line 689)

```c
int imx_apply_network_mode_from_config(void)
{
    bool config_changed = false;
    char current_hash[33];
    char stored_hash[33];

    // Calculate hash of current configuration
    calculate_network_config_hash(current_hash);
    imx_cli_log_printf(true, "Current config hash: %s\n", current_hash);

    // Read previously applied hash
    if (read_stored_network_hash(stored_hash) != 0) {
        // First boot - no stored hash
        imx_cli_log_printf(true, "No stored configuration hash found (first boot)\n");
        config_changed = true;
    } else {
        imx_cli_log_printf(true, "Stored config hash: %s\n", stored_hash);

        // Check if forced reconfiguration requested via -R option
        if (g_force_network_reconfig) {
            imx_cli_log_printf(true, "FORCED reconfiguration requested (-R option)\n");
            config_changed = true;
            g_force_network_reconfig = false;
        } else {
            // Normal operation: Compare hashes
            config_changed = (strcmp(current_hash, stored_hash) != 0);
        }
    }

    if (config_changed) {
        // Apply configuration
        int changes_applied = apply_network_configuration();

        if (changes_applied > 0) {
            // Save new hash
            save_network_hash(current_hash);

            // Schedule reboot
            schedule_network_reboot();
            return 1;  // Reboot pending
        }
    } else {
        imx_cli_log_printf(true, "Network configuration unchanged\n");
    }

    return 0;  // No changes
}
```

### Reboot Loop Prevention

**Mechanism**: Attempt counter prevents infinite reboot loops

**Files**:
- `/usr/qk/etc/sv/reboot_count` - Tracks consecutive reboots
- `/usr/qk/etc/sv/network_reboot.flag` - Marks network config reboot

**Logic**:
```c
int reboot_attempts = get_reboot_attempt_count();
if (reboot_attempts >= MAX_REBOOT_ATTEMPTS) {  // 3 attempts
    // Too many reboots, fall back to defaults
    clear_reboot_attempt_count();
    unlink(NETWORK_CONFIG_STATE_FILE);
    return -1;
}

// Increment counter before reboot
increment_reboot_attempt_count();

// Clear counter after successful boot
if (is_network_reboot()) {
    clear_reboot_attempt_count();
}
```

---

## Network Configuration Application

### Main Application Function

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`
**Function**: `apply_network_configuration()` (line 398)

### Process Flow

```
1. Print header banner
2. Iterate through ALL interface indices (0-3)
3. For each ENABLED interface:
   │
   ├─ If eth0: → apply_eth0_config()
   ├─ If wlan0: → apply_wlan0_config()
   └─ If ppp0: → apply_ppp0_config()
4. Generate /etc/network/interfaces file
5. Update service blacklist
6. Print completion summary
```

### Interface Processing (SPARSE ARRAY!)

**CRITICAL CODE** (line 421):
```c
/* Process each interface in device_config
 * IMPORTANT: Iterate through ALL indices since array is SPARSE
 * (interfaces at indices 0, 2 for wlan0, eth0 - not sequential!)
 */
for (int i = 0; i < IMX_INTERFACE_MAX; i++) {
    network_interfaces_t *iface = &device_config.network_interfaces[i];

    if (!iface->enabled || strlen(iface->name) == 0) {
        /* Skip empty/disabled slots (expected for sparse array) */
        continue;
    }

    imx_cli_print("=== Processing Interface %d: %s ===\n", i, iface->name);
    imx_cli_print("  Enabled:          Yes\n");
    imx_cli_print("  Mode:             %s\n",
                 iface->mode == IMX_IF_MODE_SERVER ? "server" : "client");

    /* Apply configuration based on interface */
    if (strcmp(iface->name, "eth0") == 0) {
        changes_made |= apply_eth0_config(iface);
    } else if (strcmp(iface->name, "wlan0") == 0) {
        changes_made |= apply_wlan0_config(iface);
    } else if (strcmp(iface->name, "ppp0") == 0) {
        changes_made |= apply_ppp0_config(iface);
    }
}
```

**Why This Pattern is CRITICAL**:
- Processes index 0 (wlan0) ✓
- Skips index 1 (empty) ✓
- Processes index 2 (eth0) ✓ **Would be MISSED by sequential iteration!**
- Skips index 3 (empty) ✓

### eth0 Configuration Application

**Function**: `apply_eth0_config()` (line 281)

```c
static int apply_eth0_config(network_interfaces_t *iface)
{
    imx_cli_log_printf(true, "Applying eth0 configuration: mode=%s, IP=%s\n",
                      iface->mode == IMX_IF_MODE_SERVER ? "server" : "client",
                      iface->mode == IMX_IF_MODE_SERVER ? iface->ip_address : "DHCP");

    if (iface->mode == IMX_IF_MODE_SERVER) {
        // Server mode - generate DHCP server config
        if (generate_dhcp_server_config("eth0") == 0) {
            changes_made = 1;
        }
    } else {
        // Client mode - remove DHCP server config
        if (remove_dhcp_server_config("eth0") == 0) {
            changes_made = 1;
        }
    }

    return changes_made;
}
```

### wlan0 Configuration Application

**Function**: `apply_wlan0_config()` (line 322)

```c
static int apply_wlan0_config(network_interfaces_t *iface)
{
    if (iface->mode == IMX_IF_MODE_SERVER) {
        // AP mode - generate hostapd and DHCP configs
        generate_hostapd_config();
        generate_dhcp_server_config("wlan0");
        system("killall wpa_supplicant 2>/dev/null");
    } else {
        // Client mode - remove AP configs
        remove_hostapd_config();
        remove_dhcp_server_config("wlan0");
        system("killall hostapd 2>/dev/null");
    }

    return changes_made;
}
```

### Network Interfaces File Generation

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_interface_writer.c`
**Function**: `write_network_interfaces_file()` (line 419)

**Generates**: `/etc/network/interfaces`

**Process**:
1. Backup existing file (incremental numbered backup)
2. Write loopback interface
3. Write eth0 configuration (searches for eth0 in array)
4. Write wlan0 configuration (searches for wlan0 in array)
5. Atomic file replacement

**Key Functions**:
- `write_eth0_interface()` - Searches array for eth0, writes config
- `write_wlan0_interface()` - Searches array for wlan0, writes config

**Search Pattern** (MUST iterate ALL indices):
```c
/* Find eth0 interface in device_config for detailed info */
// Iterate ALL indices since array is SPARSE
for (i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (strcmp(device_config.network_interfaces[i].name, "eth0") == 0) {
        iface = &device_config.network_interfaces[i];
        break;
    }
}
```

**Example Output** (`/etc/network/interfaces`):
```ini
# Network interface configuration
# Generated by iMatrix network mode configuration

# Loopback interface
auto lo
iface lo inet loopback

# Ethernet interface
auto eth0
iface eth0 inet static
    address 192.168.7.1
    netmask 255.255.255.0

# Wireless interface
auto wlan0
iface wlan0 inet dhcp
    wpa-driver nl80211
    wpa-conf /etc/network/wpa_supplicant.conf
```

---

## Service Management & Blacklist

### Blacklist System Overview

**Purpose**: Control which runit services start on boot

**Blacklist File**: `/usr/qk/blacklist`

**Mechanism**: BusyBox runit reads this file and doesn't start blacklisted services

**Services Managed**:
- `udhcpd` - DHCP server (enabled when interface in server mode)
- `hostapd` - WiFi Access Point (enabled when wlan0 in server mode)
- `wpa` - WPA supplicant (enabled when wlan0 in client mode)

### Blacklist Logic

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_blacklist_manager.c`
**Function**: `update_network_blacklist()` (line 460)

**Decision Tree**:
```
1. Check if ANY interface in server mode
   └─→ YES: Remove udhcpd from blacklist
   └─→ NO:  Add udhcpd to blacklist

2. Check if wlan0 in server mode
   ├─→ YES: Remove hostapd, Add wpa
   └─→ NO:  Add hostapd, Remove wpa
```

**Implementation**:
```c
int update_network_blacklist(void)
{
    bool any_server = any_interface_in_server_mode();
    bool wlan0_server = wlan0_in_server_mode();

    imx_printf("[BLACKLIST] Any interface in server mode: %s\n",
               any_server ? "yes" : "no");

    // Update udhcpd blacklist status
    if (any_server) {
        remove_from_blacklist("udhcpd");
    } else {
        add_to_blacklist("udhcpd");
    }

    // Update hostapd/wpa blacklist status
    if (wlan0_server) {
        remove_from_blacklist("hostapd");
        add_to_blacklist("wpa");
    } else {
        add_to_blacklist("hostapd");
        remove_from_blacklist("wpa");
    }

    return 0;
}
```

### Server Mode Detection

**Function**: `any_interface_in_server_mode()` (line 231)

**CRITICAL**: Checks specific logical indices, not sequential!

```c
static bool any_interface_in_server_mode(void)
{
    bool eth0_server = false;
    bool wlan0_server = false;

    // Check eth0 at its LOGICAL index (2, not sequential!)
    if (device_config.network_interfaces[IMX_ETH0_INTERFACE].enabled &&
        strcmp(device_config.network_interfaces[IMX_ETH0_INTERFACE].name, "eth0") == 0 &&
        device_config.network_interfaces[IMX_ETH0_INTERFACE].mode == IMX_IF_MODE_SERVER) {
        eth0_server = true;
    }

    // Check wlan0 at its LOGICAL index (0 for STA, 1 for AP)
    if (device_config.network_interfaces[IMX_STA_INTERFACE].enabled &&
        strcmp(device_config.network_interfaces[IMX_STA_INTERFACE].name, "wlan0") == 0 &&
        device_config.network_interfaces[IMX_STA_INTERFACE].mode == IMX_IF_MODE_SERVER) {
        wlan0_server = true;
    }

    return eth0_server || wlan0_server;
}
```

**Why Checking Specific Indices Works**:
- eth0 is ALWAYS at IMX_ETH0_INTERFACE (2) if present
- wlan0 is at IMX_STA_INTERFACE (0) or IMX_AP_INTERFACE (1) depending on mode
- Checking these specific indices is correct!

**Why It Failed Before Fix #5**:
- Before index mapping fix, eth0 was at index 0, not 2
- Checking index 2 found stale/wrong data
- Made wrong decision

---

## DHCP Server Configuration

### DHCP Generation System

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

**Main Function**: `generate_dhcp_server_config()` (line 434)

### Configuration Process

**Critical**: Reads ALL parameters from device_config, NO hardcoded values!

```c
int generate_dhcp_server_config(const char *interface)
{
    network_interfaces_t *iface;
    dhcp_config_params_t params;
    char dns_servers[128];

    // Find interface in device_config (searches ALL indices)
    iface = find_interface_config(interface);
    if (iface == NULL) {
        imx_printf("Error: Interface %s not found in device configuration\n", interface);
        return -1;
    }

    imx_printf("[DHCP-CONFIG] Found %s: IP=%s, DHCP range=%s to %s\n",
               interface, iface->ip_address, iface->dhcp_start, iface->dhcp_end);

    // Validate DHCP configuration
    if (!validate_dhcp_config(iface)) {
        return -1;
    }

    // Validate subnet consistency
    if (!validate_subnet_match(iface->ip_address, iface->dhcp_start,
                                iface->dhcp_end, iface->netmask)) {
        imx_printf("Error: DHCP range not in correct subnet for %s\n", interface);
        return -1;
    }

    // Build parameters from device_config (NOT hardcoded!)
    params.interface = interface;
    params.ip_start = iface->dhcp_start;      // From config!
    params.ip_end = iface->dhcp_end;          // From config!
    params.subnet = iface->netmask;           // From config!
    params.router = iface->ip_address;        // Gateway = interface IP

    // Write configuration file
    return write_dhcp_config_file(interface, &params);
}
```

### Helper Functions

#### find_interface_config()
```c
static network_interfaces_t* find_interface_config(const char *interface)
{
    // Search ALL indices (sparse array!)
    for (int i = 0; i < IMX_INTERFACE_MAX; i++) {
        network_interfaces_t *iface = &device_config.network_interfaces[i];

        if (iface->enabled &&
            strlen(iface->name) > 0 &&
            strcmp(iface->name, interface) == 0) {
            return iface;
        }
    }
    return NULL;
}
```

#### validate_subnet_match()
```c
static bool validate_subnet_match(const char *ip, const char *dhcp_start,
                                   const char *dhcp_end, const char *netmask)
{
    uint8_t ip_octets[4], start_octets[4], end_octets[4], mask_octets[4];

    // Parse all IPs
    sscanf(ip, "%hhu.%hhu.%hhu.%hhu", ...);
    sscanf(dhcp_start, "%hhu.%hhu.%hhu.%hhu", ...);
    sscanf(dhcp_end, "%hhu.%hhu.%hhu.%hhu", ...);
    sscanf(netmask, "%hhu.%hhu.%hhu.%hhu", ...);

    // Apply netmask and verify all match
    for (int i = 0; i < 4; i++) {
        if ((ip_octets[i] & mask_octets[i]) != (start_octets[i] & mask_octets[i])) {
            imx_printf("ERROR: DHCP range not in same subnet as interface IP\n");
            return false;
        }
    }

    return true;
}
```

**This validation prevents the bug where DHCP range was in wrong subnet!**

### Generated Configuration Files

#### /etc/network/udhcpd.eth0.conf
```ini
# udhcpd configuration for eth0
# Generated by iMatrix network mode configuration

start 192.168.7.100
end 192.168.7.199

interface eth0

lease_file /var/lib/misc/udhcpd.eth0.leases

option subnet 255.255.255.0
option router 192.168.7.1
option dns 127.0.0.1 10.2.0.1
option lease 86400

# Additional options
max_leases 101
auto_time 30
decline_time 3600
conflict_time 3600
offer_time 60
min_lease 60
```

#### /etc/sv/udhcpd/run
```bash
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin

echo "Start udhcpd for eth0..."

# Wait for eth0
while ! ifconfig eth0 >/dev/null 2>&1; do
    sleep 0.5
done

# Set IP (from device config: 192.168.7.1)
ifconfig eth0 192.168.7.1

# Create lease file if needed
mkdir -p /var/lib/misc
touch /var/lib/misc/udhcpd.eth0.leases

exec udhcpd -f /etc/network/udhcpd.eth0.conf
```

**Note**: IP addresses read from device_config, not hardcoded!

---

## Interface Modes

### Mode Types

```c
typedef enum {
    IMX_IF_MODE_SERVER = 0,  // Static IP, optionally runs DHCP server
    IMX_IF_MODE_CLIENT = 1,  // DHCP client mode
} interface_mode_t;
```

### Mode String Mapping

**From Binary Config**:
```
"static"       → IMX_IF_MODE_SERVER (0)
"server"       → IMX_IF_MODE_SERVER (0)
"dhcp_server"  → IMX_IF_MODE_SERVER (0)
"dhcp_client"  → IMX_IF_MODE_CLIENT (1)
"client"       → IMX_IF_MODE_CLIENT (1)
(anything else)→ IMX_IF_MODE_CLIENT (1)
```

### Server Mode Behavior

**eth0 in server mode**:
- Static IP address assigned (e.g., 192.168.7.1)
- Netmask and gateway configured
- Optional DHCP server enabled
- Optional internet sharing (NAT/forwarding)

**Generated**:
- `/etc/network/interfaces` - eth0 static configuration
- `/etc/network/udhcpd.eth0.conf` - DHCP server config (if enabled)
- `/etc/sv/udhcpd/run` - runit run script

**Services**:
- `udhcpd` removed from blacklist (allowed to run)

### Client Mode Behavior

**eth0 in client mode**:
- DHCP client requests IP from network
- No static IP
- No DHCP server
- No services managed

**Generated**:
- `/etc/network/interfaces` - eth0 dhcp configuration

**Services**:
- `udhcpd` added to blacklist (blocked)

---

## Command Line Options

### -P: Print Configuration (Verbose)

**Usage**: `./Fleet-Connect-1 -P`

**Purpose**: Display complete configuration details

**Behavior**:
- Locates binary config file
- Reads all sections
- Prints complete statistics
- **Exits immediately** (does not start gateway)

**Output**: Full configuration dump with all sensors, CAN buses, network interfaces, etc.

### -S: Print Configuration Summary

**Usage**: `./Fleet-Connect-1 -S`

**Purpose**: Quick configuration verification

**Behavior**:
- Locates binary config file
- Reads all sections
- Prints concise summary
- **Exits immediately**

**Output Example**:
```
=== Configuration Summary ===
Product: Aptera Production Intent-1 (ID: 2201718576)
Organization ID: 250007060

Sections Present:
- Network: 2 interface(s) configured
  [0] eth0 - mode: static, ip: 192.168.7.1, DHCP: [192.168.7.100-192.168.7.199]
  [1] wlan0 - mode: dhcp_client
- CAN Bus 2 (Ethernet): 113 nodes, 1071 signals
- Internal Sensors: 60 configured
```

### -I: Display File Index

**Usage**: `./Fleet-Connect-1 -I`

**Purpose**: Show binary file structure (v4+ files)

**Behavior**:
- Reads file signature and version
- Displays section index with offsets
- Shows configuration summary
- **Exits immediately**

**Use Cases**: File corruption debugging, version validation

### -R: Reset Network Configuration (NEW!)

**Usage**: `./Fleet-Connect-1 -R`

**Purpose**: Force network configuration regeneration regardless of hash

**Behavior**:
- Sets force reconfiguration flag
- Displays informational banner
- **Continues with normal startup** (doesn't exit)
- When network config checked, bypasses hash comparison
- Forces configuration rewrite
- Saves new hash
- Reboots system

**Use Cases**:
- Recover from deleted configuration files
- Regenerate corrupted configuration
- Force reapplication for testing

**Example Output**:
```
=======================================================
   NETWORK CONFIGURATION RESET (-R)
=======================================================

This option forces regeneration of network configuration
files regardless of whether the configuration has changed.

Network reconfiguration has been scheduled.
The system will:
  1. Bypass hash check
  2. Regenerate all network configuration files
  3. Automatically reboot to apply changes

Starting system with forced network reconfiguration...
=======================================================

[... normal boot continues ...]

Checking network configuration...
FORCED reconfiguration requested (-R option)
Bypassing hash check and forcing configuration rewrite
```

---

## Troubleshooting Guide

### Issue: DHCP Clients Get Wrong Subnet IPs

**Symptom**: Clients receive 192.168.8.x instead of 192.168.7.x

**Cause**: Hardcoded DHCP parameters (Bug #1 - FIXED 2025-11-02)

**Check**:
```bash
cat /etc/network/udhcpd.eth0.conf

# Should show:
start 192.168.7.100    # NOT 192.168.8.100
end 192.168.7.199      # NOT 192.168.8.200
option router 192.168.7.1  # NOT 192.168.8.1
```

**Diagnostic**:
```
[DHCP-CONFIG] Found eth0: IP=192.168.7.1, DHCP range=192.168.7.100 to 192.168.7.199
```

**Fix**: Ensure code reads from device_config, not hardcoded params

---

### Issue: DHCP Server Not Running

**Symptom**: `sv status udhcpd` shows "down" or blocked

**Possible Causes**:

#### Cause 1: Service Blacklisted
```bash
cat /usr/qk/blacklist | grep udhcpd

# If found, udhcpd is blocked
```

**Check Logs**:
```
[BLACKLIST] Added udhcpd to blacklist (no interfaces in server mode)
```

**Root Cause**: Blacklist not detecting interface in server mode

**Diagnostic**:
```
[BLACKLIST-DIAG] Checking eth0 at index 2:
[BLACKLIST-DIAG]   enabled=1, name='eth0', mode=? (SERVER=0)
```

If mode != 0, eth0 not recognized as server.

**Fix**: Ensure eth0 at correct index (2) with correct mode (0)

#### Cause 2: eth0 Not Processed

**Check Logs**:
```
=== Processing Interface 0: wlan0 ===
(Missing: "Processing Interface 2: eth0")
```

**Root Cause**: Loop doesn't iterate to index 2 (Bug #6 - FIXED 2025-11-02)

**Fix**: Ensure loop iterates ALL indices (`i < IMX_INTERFACE_MAX`)

#### Cause 3: Configuration Files Missing

**Check**:
```bash
ls -l /etc/network/udhcpd.eth0.conf
ls -l /etc/sv/udhcpd/run
```

**Fix**: Run with `-R` option to force regeneration

---

### Issue: Array Shows 4 Interfaces When Only 2 Configured

**Symptom**:
```
[BLACKLIST-DIAG] Dumping 4 configured interfaces (max 4):
```

**Cause**: Array bounds violation (Bug #2 - FIXED 2025-11-02)

**Check Code**: Ensure dump function only iterates configured:
```c
for (i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (is_interface_configured(i)) {
        // Only dump configured
    }
}
```

---

### Issue: Duplicate Interface Data

**Symptom**:
```
Index 0: name='eth0'
Index 2: name='eth0'  ← Duplicate!
```

**Cause**: Sequential copy instead of name mapping (Bug #5 - FIXED 2025-11-02)

**Check**: Ensure imx_client_init.c maps by interface name:
```c
if (strcmp(src->name, "eth0") == 0) {
    target_idx = IMX_ETH0_INTERFACE;  // 2, not i!
}
```

---

### Issue: Configuration Files Deleted

**Symptom**: Network doesn't work, files missing

**Solution**: Use `-R` option

```bash
./Fleet-Connect-1 -R

# Forces regeneration of all config files
# System will reboot to apply
```

---

### Issue: Hash Prevents Reconfiguration

**Symptom**: Config files manually deleted, but not regenerated

**Cause**: Hash matches, system thinks nothing changed

**Solution**: Use `-R` option to bypass hash check

---

### Debug Output Analysis

#### Healthy System Log

```
Loading 2 network interface(s) from configuration file
  Mapping eth0 from config[0] to device_config[2]    ✓ Index mapping
  Mapping wlan0 from config[1] to device_config[0]   ✓ Index mapping
Total interfaces configured: 2 (max 4)

Checking network configuration...
Current config hash: 1a2b3c4d...
Stored config hash: 1a2b3c4d...
Network configuration unchanged                      ✓ No changes

=== Processing Interface 0: wlan0 ===                ✓ Processed
=== Processing Interface 2: eth0 ===                 ✓ Processed
[DHCP-CONFIG] Generating DHCP server config for eth0 ✓ DHCP generated

[BLACKLIST-DIAG] Dumping 2 configured interfaces    ✓ Correct count
[BLACKLIST-DIAG] Index 0: name='wlan0', mode=1       ✓ Correct
[BLACKLIST-DIAG] Index 2: name='eth0', mode=0        ✓ Correct mode

[BLACKLIST] Any interface in server mode: yes        ✓ Detected
[BLACKLIST] Removed udhcpd from blacklist            ✓ DHCP allowed
```

#### Problematic System Log

**Problem: eth0 not processed**
```
=== Processing Interface 0: wlan0 ===
(Missing: "Processing Interface 2: eth0")            ❌ eth0 skipped

--- Ethernet Interface (eth0) ---
  Mode:             dhcp (client)                    ❌ Wrong mode
```

**Cause**: Sparse array iteration bug

**Problem: DHCP blacklisted**
```
[BLACKLIST] Added udhcpd to blacklist                ❌ DHCP blocked
```

**Cause**: eth0 not detected as server mode

**Problem: Wrong subnet**
```
IP Range Start:   192.168.8.100                      ❌ Wrong subnet
```

**Cause**: Hardcoded DHCP parameters

---

## Critical Bugs Fixed (2025-11-02)

### Complete Bug List

| # | Bug | File | Lines | Impact |
|---|-----|------|-------|--------|
| 1 | DHCP subnet mismatch | dhcp_server_config.c | 99-115, 309-335 | DHCP clients wrong subnet |
| 2 | Array bounds violation | network_blacklist_manager.c | 446 | Undefined behavior |
| 3 | Wrong interface count | network_mode_config.c | 217 | Causes Bug #2 |
| 4 | Unsafe fallbacks | network_interface_writer.c | 209-215 | Silent failures |
| 5 | Sequential copy bug | imx_client_init.c | 444-499 | Wrong array indices |
| 6 | Sparse array iteration | 3 files, 8 loops | Multiple | Skips interfaces |

### Bug #1: DHCP Subnet Mismatch

**Before**:
```c
static const dhcp_config_params_t eth0_params = {
    .ip_start = "192.168.8.100",  // HARDCODED WRONG!
    .ip_end = "192.168.8.200",
    .router = "192.168.8.1",
};

// Used hardcoded params
params = &eth0_params;
```

**After**:
```c
// Find interface in device_config
iface = find_interface_config("eth0");

// Read from config (NOT hardcoded!)
params.ip_start = iface->dhcp_start;  // "192.168.7.100"
params.ip_end = iface->dhcp_end;      // "192.168.7.199"
params.router = iface->ip_address;    // "192.168.7.1"
```

### Bug #2: Array Bounds Violation

**Before**:
```c
for (i = 0; i < IMX_INTERFACE_MAX; i++) {
    // Reads ALL 4 slots including uninitialized!
    imx_printf("Index %d: %s\n", i, device_config.network_interfaces[i].name);
}
```

**After**:
```c
// Count configured first
for (i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (is_interface_configured(i)) {
        configured_count++;
    }
}

// Only dump configured
for (i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (is_interface_configured(i)) {
        imx_printf("Index %d: %s\n", i, ...);
    }
}
```

### Bug #3: Wrong Interface Count

**Before**:
```c
device_config.no_interfaces = IMX_INTERFACE_MAX;  // Always 4!
```

**After**:
```c
// Count by iterating (Option B)
device_config.no_interfaces = count_configured_interfaces();
// Returns actual count (e.g., 2)
```

### Bug #4: Unsafe Fallbacks

**Before**:
```c
if (iface != NULL && strlen(iface->ip_address) > 0) {
    fprintf(fp, "address %s\n", iface->ip_address);
} else {
    // Fallback to default!
    fprintf(fp, "address 192.168.7.1\n");  // WRONG if config expects different IP
}
```

**After**:
```c
if (iface == NULL || strlen(iface->ip_address) == 0) {
    // ERROR - no fallback!
    imx_printf("ERROR: Interface missing IP address\n");
    return -1;
}

// Only use configured value
fprintf(fp, "address %s\n", iface->ip_address);
```

### Bug #5: Sequential Copy Bug (ROOT CAUSE)

**Before**:
```c
for (uint16_t i = 0; i < device_config.no_interfaces; i++) {
    network_interface_t *src = &dev_config->network.interfaces[i];  // [0], [1]
    network_interfaces_t *dst = &device_config.network_interfaces[i];  // [0], [1]
    // Copies sequentially: [0]→[0], [1]→[1]
}

Result:
  device_config[0] = eth0 (should be at [2]!)
  device_config[1] = wlan0 (should be at [0]!)
```

**After**:
```c
// Clear all slots first
for (i = 0; i < IMX_INTERFACE_MAX; i++) {
    device_config.network_interfaces[i].enabled = 0;
    device_config.network_interfaces[i].name[0] = '\0';
}

// Map by interface NAME to correct index
for (i = 0; i < dev_config->network.interface_count; i++) {
    network_interface_t *src = &dev_config->network.interfaces[i];

    if (strcmp(src->name, "eth0") == 0) {
        target_idx = IMX_ETH0_INTERFACE;  // 2
    } else if (strcmp(src->name, "wlan0") == 0) {
        target_idx = IMX_STA_INTERFACE;   // 0
    }

    device_config.network_interfaces[target_idx] = ... // Copy to CORRECT index
}

Result:
  device_config[0] = wlan0 (correct!)
  device_config[1] = empty
  device_config[2] = eth0 (correct!)
  device_config[3] = empty
```

### Bug #6: Sparse Array Iteration Bug (ROOT CAUSE)

**Before**:
```c
for (int i = 0; i < device_config.no_interfaces; i++) {
    // If no_interfaces=2, processes i=0,1 only
    // MISSES index 2 where eth0 is!
}
```

**After**:
```c
for (int i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (!enabled || name empty) continue;
    // Processes ALL configured interfaces regardless of index
}
```

**8 Loops Fixed** across 3 files to handle sparse arrays correctly.

---

## Configuration Data Structures

### In-Memory Structures

#### network_interface_t (Binary Config)
```c
typedef struct network_interface {
    char name[32];                  // "eth0", "wlan0", "ppp0"
    char mode[32];                  // "static", "dhcp_client", etc.
    char ip[16];                    // "192.168.7.1"
    char netmask[16];              // "255.255.255.0"
    char gateway[16];              // "192.168.7.1"
    uint8_t dhcp_server;           // 0 or 1
    uint8_t provide_internet;      // 0 or 1
    char dhcp_server_start[16];    // "192.168.7.100"
    char dhcp_server_end[16];      // "192.168.7.199"
} network_interface_t;
```

#### network_interfaces_t (device_config)
```c
typedef struct {
    char name[IMX_MAX_INTERFACE_NAME_LENGTH + 1];  // Interface name
    interface_mode_t mode;                         // SERVER (0) or CLIENT (1)
    char ip_address[16];                           // IP address
    char netmask[16];                              // Netmask
    char gateway[16];                              // Gateway
    char dhcp_start[16];                           // DHCP range start
    char dhcp_end[16];                             // DHCP range end
    uint32_t dhcp_lease_time;                      // Lease time in seconds
    uint8_t enabled : 1;                           // Enabled flag
    uint8_t use_dhcp_server : 1;                   // DHCP server enabled
    uint8_t use_connection_sharing : 1;            // Internet sharing
} network_interfaces_t;
```

#### IOT_Device_Config_t (Global Config)
```c
typedef struct {
    // ... many other fields ...

    uint16_t no_interfaces;  // Number of configured interfaces (NOT max!)
    network_interfaces_t network_interfaces[IMX_INTERFACE_MAX];  // Sparse array

    // ... many other fields ...
} IOT_Device_Config_t;
```

---

## State Files

### /usr/qk/etc/sv/network_config.state
**Purpose**: Stores MD5 hash of last applied configuration
**Format**: Single line, 32 hex characters
**Example**: `1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d`

### /usr/qk/etc/sv/network_reboot.flag
**Purpose**: Marker for network configuration reboot
**Created**: When reboot scheduled
**Deleted**: After reboot detected
**Format**: Text file with timestamp

### /usr/qk/etc/sv/reboot_count
**Purpose**: Tracks consecutive reboot attempts
**Format**: Integer count
**Max**: 3 attempts before fallback

### /usr/qk/blacklist
**Purpose**: Lists services that should NOT start
**Format**: One service name per line
**Managed**: Automatically by network config system

---

## Best Practices

### For Developers

1. **Always iterate sparse arrays correctly**:
   ```c
   for (i = 0; i < IMX_INTERFACE_MAX; i++) {
       if (!configured) continue;
       // Process
   }
   ```

2. **Never use hardcoded IPs** - always read from device_config

3. **Always validate configuration** before using

4. **Use helper functions** for interface lookup:
   - `find_interface_config()`
   - `is_interface_configured()`
   - `count_configured_interfaces()`

5. **Add diagnostic output** for debugging

### For Operators

1. **Use -S option** to verify configuration before deployment

2. **Use -R option** to recover from configuration issues

3. **Check blacklist file** if services not starting

4. **Monitor reboot count** to detect configuration problems

5. **Backup configuration files** before updates

---

## Example Configurations

### Configuration 1: Edge Gateway (eth0 server, wlan0 client)

**Binary Config**:
```
interfaces[0]:
  name = "eth0"
  mode = "static"
  ip = "192.168.7.1"
  dhcp_server = 1
  dhcp_start = "192.168.7.100"
  dhcp_end = "192.168.7.199"

interfaces[1]:
  name = "wlan0"
  mode = "dhcp_client"
```

**device_config Array**:
```
[0] = wlan0 (CLIENT mode)
[1] = empty
[2] = eth0 (SERVER mode, DHCP enabled)
[3] = empty
```

**Generated Files**:
- `/etc/network/interfaces` - eth0 static 192.168.7.1, wlan0 dhcp
- `/etc/network/udhcpd.eth0.conf` - DHCP server config
- `/etc/sv/udhcpd/run` - DHCP service script

**Services**:
- `udhcpd` - Running (DHCP server on eth0)
- `wpa` - Running (WiFi client on wlan0)
- `hostapd` - Blacklisted (wlan0 not AP)

**Use Case**: Gateway provides network to connected devices via eth0, accesses internet via wlan0

---

### Configuration 2: WiFi Access Point (wlan0 AP, eth0 client)

**Binary Config**:
```
interfaces[0]:
  name = "wlan0"
  mode = "server"
  ip = "192.168.7.1"
  dhcp_server = 1
  dhcp_start = "192.168.7.100"
  dhcp_end = "192.168.7.200"

interfaces[1]:
  name = "eth0"
  mode = "dhcp_client"
```

**device_config Array**:
```
[0] = empty (STA disabled)
[1] = wlan0 (SERVER/AP mode)
[2] = eth0 (CLIENT mode)
[3] = empty
```

**Generated Files**:
- `/etc/network/interfaces` - wlan0 static, eth0 dhcp
- `/etc/network/hostapd.conf` - WiFi AP config
- `/etc/network/udhcpd.wlan0.conf` - DHCP server config

**Services**:
- `hostapd` - Running (WiFi AP on wlan0)
- `udhcpd` - Running (DHCP server on wlan0)
- `wpa` - Blacklisted (wlan0 not client)

**Use Case**: Device acts as WiFi hotspot, connects to network via eth0

---

## Advanced Topics

### Dual Interface DHCP Server

**Scenario**: Both eth0 and wlan0 in server mode with DHCP

**Configuration**:
```
device_config[0] = empty (STA disabled)
device_config[1] = wlan0 (SERVER, DHCP: 192.168.7.100-200)
device_config[2] = eth0 (SERVER, DHCP: 192.168.8.100-200)
device_config[3] = empty
```

**Generated**:
- Two DHCP configs: `udhcpd.eth0.conf`, `udhcpd.wlan0.conf`
- Single run script manages both interfaces
- Both subnets isolated (192.168.7.x vs 192.168.8.x)

**Run Script** (`/etc/sv/udhcpd/run`):
```bash
# Function to run udhcpd for an interface
run_dhcp() {
    iface=$1
    ip=$2
    conf=$3

    while ! ifconfig $iface >/dev/null 2>&1; do
        sleep 0.5
    done

    ifconfig $iface $ip
    udhcpd -f $conf
}

# Start eth0 DHCP in background
run_dhcp eth0 192.168.8.1 /etc/network/udhcpd.eth0.conf &

# Start wlan0 DHCP in foreground
exec run_dhcp wlan0 192.168.7.1 /etc/network/udhcpd.wlan0.conf
```

### Connection Sharing (Internet Gateway)

**Purpose**: Share internet connection from one interface to others

**Example**: wlan0 (client) provides internet to eth0 (server)

**Configuration**:
```
eth0:
  mode = "server"
  ip = "192.168.7.1"
  use_connection_sharing = 1  ← Enable sharing

wlan0:
  mode = "client"  ← Internet source
```

**Implementation**:
- IP forwarding enabled: `echo 1 > /proc/sys/net/ipv4/ip_forward`
- NAT rules configured: `iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE`
- DHCP server provides wlan0 DNS servers to clients

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/connection_sharing.c`

---

## Diagnostic Output Reference

### Configuration Loading Diagnostics

```
Loading 2 network interface(s) from configuration file
  Mapping eth0 from config[0] to device_config[2]
  Config[0] → device_config[2]: eth0, mode=server, IP=192.168.7.1
    DHCP range: 192.168.7.100 - 192.168.7.199
  Mapping wlan0 from config[1] to device_config[0]
  Config[1] → device_config[0]: wlan0, mode=client, IP=DHCP
Network configuration loaded successfully
Total interfaces configured: 2 (max 4)
```

**What to check**:
- ✓ Mapping messages show correct indices
- ✓ Total configured matches expectation
- ✓ Mode and IP correct for each

### DHCP Generation Diagnostics

```
[DHCP-CONFIG] Generating DHCP server config for eth0 from device_config
[DHCP-CONFIG] Found eth0: IP=192.168.7.1, DHCP range=192.168.7.100 to 192.168.7.199

=======================================================
   WRITING DHCP SERVER CONFIGURATION
   Interface: eth0
   File: /etc/network/udhcpd.eth0.conf
=======================================================

--- DHCP Server Settings ---
  Interface:        eth0
  IP Range Start:   192.168.7.100
  IP Range End:     192.168.7.199
  Subnet Mask:      255.255.255.0
  Gateway/Router:   192.168.7.1
  DNS Servers:      127.0.0.1 10.2.0.1
```

**What to check**:
- ✓ IP and DHCP range in SAME subnet
- ✓ Gateway = interface IP
- ✓ Values match binary config

### Blacklist Decision Diagnostics

```
[BLACKLIST] Updating network service blacklist
[BLACKLIST-DIAG] Mode values: IMX_IF_MODE_SERVER=0, IMX_IF_MODE_CLIENT=1
[BLACKLIST-DIAG] Dumping 2 configured interfaces (max 4):
[BLACKLIST-DIAG] Index 0: enabled=1, name='wlan0', mode=1
[BLACKLIST-DIAG] Index 2: enabled=1, name='eth0', mode=0
[BLACKLIST-DIAG] Checking eth0 at index 2:
[BLACKLIST-DIAG]   enabled=1, name='eth0', mode=0 (SERVER=0)
[BLACKLIST-DIAG] Result: eth0_server=1, wlan0_server=0
[BLACKLIST] Any interface in server mode: yes
[BLACKLIST] Removed udhcpd from blacklist (interface(s) in server mode)
```

**What to check**:
- ✓ Only configured interfaces dumped (not 4!)
- ✓ Each interface at correct index
- ✓ Mode values correct (SERVER=0, CLIENT=1)
- ✓ Detection result matches expectation
- ✓ Blacklist action correct (Remove vs Add)

---

## Complete File Reference

### Source Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| Fleet-Connect-1/init/wrp_config.c | Binary file reading | read_config() |
| Fleet-Connect-1/init/imx_client_init.c | Index mapping | imx_client_init() |
| iMatrix/imatrix_interface.c | Main entry point | main(), imatrix_start() |
| iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c | Hash detection & application | imx_apply_network_mode_from_config() |
| iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c | DHCP generation | generate_dhcp_server_config() |
| iMatrix/IMX_Platform/LINUX_Platform/networking/network_interface_writer.c | /etc/network/interfaces | write_network_interfaces_file() |
| iMatrix/IMX_Platform/LINUX_Platform/networking/network_blacklist_manager.c | Service management | update_network_blacklist() |

### Generated Files

| File | Purpose | Generated By |
|------|---------|--------------|
| /etc/network/interfaces | Main network config | network_interface_writer.c |
| /etc/network/udhcpd.eth0.conf | eth0 DHCP server | dhcp_server_config.c |
| /etc/network/udhcpd.wlan0.conf | wlan0 DHCP server | dhcp_server_config.c |
| /etc/network/hostapd.conf | WiFi AP config | network_interface_writer.c |
| /etc/network/wpa_supplicant.conf | WiFi client config | (user-provided) |
| /etc/sv/udhcpd/run | DHCP service script | dhcp_server_config.c |
| /usr/qk/blacklist | Service blacklist | network_blacklist_manager.c |

### State Files

| File | Purpose | Format |
|------|---------|--------|
| /usr/qk/etc/sv/network_config.state | Applied config hash | 32 hex chars |
| /usr/qk/etc/sv/network_reboot.flag | Reboot marker | Text timestamp |
| /usr/qk/etc/sv/reboot_count | Attempt counter | Integer |

---

## Testing & Validation

### Pre-Deployment Checks

```bash
# 1. Verify configuration file
./Fleet-Connect-1 -S

# Check output for:
# - Correct number of interfaces
# - Correct IP addresses
# - Correct DHCP ranges
# - Correct modes

# 2. Check for known issues
./Fleet-Connect-1 2>&1 | grep -i "error\|warning"

# 3. Verify binary file format
./Fleet-Connect-1 -I

# Check file version and structure
```

### Post-Deployment Checks

```bash
# 1. Check generated files
cat /etc/network/interfaces
cat /etc/network/udhcpd.eth0.conf

# Verify correct IPs and ranges

# 2. Check blacklist
cat /usr/qk/blacklist

# Verify udhcpd NOT blacklisted if server mode

# 3. Check service status
sv status udhcpd
sv status hostapd
sv status wpa

# 4. Test DHCP functionality
# Connect client, verify IP assignment
# Ping gateway

# 5. Check logs
tail -f /var/log/messages
```

---

## Summary

This comprehensive guide documents the complete iMatrix networking system including:
- Binary configuration file format and reading
- Initialization sequence and call chain
- Sparse array architecture and iteration patterns
- Hash-based change detection
- Network configuration application
- Service management via blacklist
- DHCP server configuration
- All command line options
- Complete troubleshooting guide
- All 6 critical bugs fixed in 2025-11-02

**Key Takeaway**: The system uses a **SPARSE ARRAY** architecture where interfaces are indexed by TYPE, not sequentially. All code must iterate through ALL indices and skip empty slots to handle this correctly.

---

*End of Comprehensive Guide*
