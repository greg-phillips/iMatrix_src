# Network Configuration Fix - Implementation TODO

**Date**: 2025-11-02
**Status**: READY TO IMPLEMENT
**Related**: See `network_config_fix_plan.md` for detailed analysis

---

## Implementation Order

Fixes must be done in this order to maintain system stability:

1. ✅ Analysis Complete (this document)
2. ⬜ Phase 1: DHCP Configuration Fixes (CRITICAL)
3. ⬜ Phase 2: Array Bounds Fixes
4. ⬜ Phase 3: Interface Count Fix
5. ⬜ Phase 4: Cleanup & Polish
6. ⬜ Phase 5: Testing & Validation

---

## PHASE 1: DHCP Configuration Fixes [CRITICAL]

### File: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

#### Task 1.1: Add Helper Functions
**Location**: After line 92 (before variable definitions)

- [ ] Add `find_interface_config()` helper:
```c
/**
 * @brief Find interface configuration in device_config
 *
 * @param interface Interface name (eth0, wlan0, etc.)
 * @return Pointer to interface config, or NULL if not found
 */
static network_interfaces_t* find_interface_config(const char *interface)
{
    int i;

    for (i = 0; i < IMX_INTERFACE_MAX; i++) {
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

- [ ] Add `validate_dhcp_config()` helper:
```c
/**
 * @brief Validate DHCP server configuration
 *
 * @param iface Interface configuration
 * @return true if valid, false otherwise
 */
static bool validate_dhcp_config(const network_interfaces_t *iface)
{
    if (!iface->use_dhcp_server) {
        DHCP_CONFIG_DEBUG(("Interface %s not configured for DHCP server\n", iface->name));
        return false;
    }

    if (strlen(iface->ip_address) == 0) {
        imx_printf("ERROR: Interface %s missing IP address\n", iface->name);
        return false;
    }

    if (strlen(iface->dhcp_start) == 0 || strlen(iface->dhcp_end) == 0) {
        imx_printf("ERROR: Interface %s missing DHCP range configuration\n", iface->name);
        return false;
    }

    if (strlen(iface->netmask) == 0) {
        imx_printf("ERROR: Interface %s missing netmask\n", iface->name);
        return false;
    }

    return true;
}
```

- [ ] Add `validate_subnet_match()` helper:
```c
/**
 * @brief Validate that DHCP range is in same subnet as interface IP
 *
 * @param ip Interface IP address
 * @param dhcp_start DHCP range start
 * @param dhcp_end DHCP range end
 * @param netmask Subnet mask
 * @return true if valid, false otherwise
 */
static bool validate_subnet_match(const char *ip, const char *dhcp_start,
                                   const char *dhcp_end, const char *netmask)
{
    uint8_t ip_octets[4], start_octets[4], end_octets[4], mask_octets[4];

    // Parse IP addresses
    if (sscanf(ip, "%hhu.%hhu.%hhu.%hhu",
               &ip_octets[0], &ip_octets[1], &ip_octets[2], &ip_octets[3]) != 4) {
        imx_printf("ERROR: Invalid IP address format: %s\n", ip);
        return false;
    }

    if (sscanf(dhcp_start, "%hhu.%hhu.%hhu.%hhu",
               &start_octets[0], &start_octets[1], &start_octets[2], &start_octets[3]) != 4) {
        imx_printf("ERROR: Invalid DHCP start address format: %s\n", dhcp_start);
        return false;
    }

    if (sscanf(dhcp_end, "%hhu.%hhu.%hhu.%hhu",
               &end_octets[0], &end_octets[1], &end_octets[2], &end_octets[3]) != 4) {
        imx_printf("ERROR: Invalid DHCP end address format: %s\n", dhcp_end);
        return false;
    }

    if (sscanf(netmask, "%hhu.%hhu.%hhu.%hhu",
               &mask_octets[0], &mask_octets[1], &mask_octets[2], &mask_octets[3]) != 4) {
        imx_printf("ERROR: Invalid netmask format: %s\n", netmask);
        return false;
    }

    // Apply netmask to each address and verify they match
    for (int i = 0; i < 4; i++) {
        uint8_t ip_masked = ip_octets[i] & mask_octets[i];
        uint8_t start_masked = start_octets[i] & mask_octets[i];
        uint8_t end_masked = end_octets[i] & mask_octets[i];

        if (ip_masked != start_masked || ip_masked != end_masked) {
            imx_printf("ERROR: DHCP range [%s - %s] not in same subnet as %s (mask %s)\n",
                       dhcp_start, dhcp_end, ip, netmask);
            return false;
        }
    }

    DHCP_CONFIG_DEBUG(("Subnet validation passed for %s\n", ip));
    return true;
}
```

#### Task 1.2: Remove Hardcoded Parameters
- [ ] Delete lines 99-106 (eth0_params structure)
- [ ] Delete lines 108-115 (wlan0_params structure)
- [ ] Update comments to reflect dynamic configuration

#### Task 1.3: Rewrite generate_dhcp_server_config()
**Location**: Lines 309-335

- [ ] Replace entire function with new implementation:
```c
/**
 * @brief Generate DHCP server configuration for an interface
 *
 * Reads interface configuration from device_config and generates
 * udhcpd configuration file with values from config (not hardcoded).
 *
 * @param interface Interface name (eth0 or wlan0)
 * @return 0 on success, negative error code on failure
 */
int generate_dhcp_server_config(const char *interface)
{
    network_interfaces_t *iface;
    dhcp_config_params_t params;
    char dns_servers[128];

    DHCP_CONFIG_DEBUG(("Generating DHCP server config for %s\n", interface));

    // Find interface configuration
    iface = find_interface_config(interface);
    if (iface == NULL) {
        imx_printf("Error: Interface %s not found in device configuration\n", interface);
        return -1;
    }

    // Validate DHCP configuration
    if (!validate_dhcp_config(iface)) {
        imx_printf("Error: Invalid DHCP configuration for %s\n", interface);
        return -1;
    }

    // Validate subnet consistency
    if (!validate_subnet_match(iface->ip_address, iface->dhcp_start,
                                iface->dhcp_end, iface->netmask)) {
        imx_printf("Error: DHCP range not in correct subnet for %s\n", interface);
        return -1;
    }

    // Build parameters from device_config
    params.interface = interface;
    params.ip_start = iface->dhcp_start;      // From config, not hardcoded!
    params.ip_end = iface->dhcp_end;          // From config, not hardcoded!
    params.subnet = iface->netmask;           // From config, not hardcoded!
    params.router = iface->ip_address;        // Gateway = interface IP

    // Get DNS servers from ppp0 if available, else use defaults
    if (get_ppp0_dns_servers(dns_servers, sizeof(dns_servers)) != 0) {
        // No ppp0 DNS, use public DNS as fallback
        strncpy(dns_servers, "8.8.8.8 8.8.4.4", sizeof(dns_servers) - 1);
        dns_servers[sizeof(dns_servers) - 1] = '\0';
    }
    params.dns_servers = dns_servers;

    DHCP_CONFIG_DEBUG(("DHCP params: start=%s, end=%s, router=%s\n",
                       params.ip_start, params.ip_end, params.router));

    // Write configuration file
    if (write_dhcp_config_file(interface, &params) != 0) {
        return -1;
    }

    DHCP_CONFIG_DEBUG(("DHCP server config generated successfully for %s\n", interface));
    return 0;
}
```

#### Task 1.4: Fix generate_udhcpd_run_script()
**Location**: Lines 400-531

- [ ] Line 453: Replace hardcoded `192.168.8.1` with dynamic IP:
```c
// OLD:
fprintf(fp, "ifconfig eth0 192.168.8.1\n");

// NEW:
network_interfaces_t *eth0 = find_interface_config("eth0");
if (eth0 && strlen(eth0->ip_address) > 0) {
    fprintf(fp, "ifconfig eth0 %s\n", eth0->ip_address);
} else {
    fprintf(fp, "echo \"ERROR: eth0 IP not configured\"\n");
    fprintf(fp, "exit 1\n");
}
```

- [ ] Line 473: Replace hardcoded `192.168.7.1` with dynamic IP:
```c
// OLD:
fprintf(fp, "ifconfig wlan0 192.168.7.1\n");

// NEW:
network_interfaces_t *wlan0 = find_interface_config("wlan0");
if (wlan0 && strlen(wlan0->ip_address) > 0) {
    fprintf(fp, "ifconfig wlan0 %s\n", wlan0->ip_address);
} else {
    fprintf(fp, "echo \"ERROR: wlan0 IP not configured\"\n");
    fprintf(fp, "exit 1\n");
}
```

- [ ] Line 503: Replace hardcoded `192.168.8.1` with dynamic IP:
```c
// OLD:
fprintf(fp, "run_dhcp eth0 192.168.8.1 /etc/network/udhcpd.eth0.conf &\n");

// NEW (use eth0 pointer from above):
fprintf(fp, "run_dhcp eth0 %s /etc/network/udhcpd.eth0.conf &\n", eth0->ip_address);
```

- [ ] Line 509: Replace hardcoded `192.168.7.1` with dynamic IP:
```c
// OLD:
fprintf(fp, "exec run_dhcp wlan0 192.168.7.1 /etc/network/udhcpd.wlan0.conf\n");

// NEW (use wlan0 pointer from above):
fprintf(fp, "exec run_dhcp wlan0 %s /etc/network/udhcpd.wlan0.conf\n", wlan0->ip_address);
```

- [ ] Add error handling if IPs not found

#### Task 1.5: Add Includes
- [ ] Ensure `device/config.h` is included for `network_interfaces_t` type
- [ ] Add `extern IOT_Device_Config_t device_config;` declaration

---

## PHASE 2: Array Bounds Fixes [HIGH PRIORITY]

### File: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_blacklist_manager.c`

#### Task 2.1: Add Helper Function
**Location**: After line 87 (Function Declarations section)

- [ ] Add declaration:
```c
static bool is_interface_configured(int index);
```

- [ ] Add implementation before `any_interface_in_server_mode()`:
```c
/**
 * @brief Check if interface at given index is configured
 *
 * @param index Array index to check
 * @return true if configured and enabled
 */
static bool is_interface_configured(int index)
{
    if (index < 0 || index >= IMX_INTERFACE_MAX) {
        return false;
    }

    return (device_config.network_interfaces[index].enabled &&
            strlen(device_config.network_interfaces[index].name) > 0);
}
```

#### Task 2.2: Fix dump_all_interfaces()
**Location**: Lines 441-453

- [ ] Replace entire function:
```c
/**
 * @brief Dump all interface configurations for debugging
 */
static void dump_all_interfaces(void)
{
    int i;
    int configured_count = 0;

    // Count configured interfaces
    for (i = 0; i < IMX_INTERFACE_MAX; i++) {
        if (is_interface_configured(i)) {
            configured_count++;
        }
    }

    imx_printf("[BLACKLIST-DIAG] Dumping %d configured interfaces (max %d):\n",
               configured_count, IMX_INTERFACE_MAX);

    // Only dump configured interfaces
    for (i = 0; i < IMX_INTERFACE_MAX; i++) {
        if (is_interface_configured(i)) {
            imx_printf("[BLACKLIST-DIAG] Index %d: enabled=%d, name='%s', mode=%d\n",
                       i,
                       device_config.network_interfaces[i].enabled,
                       device_config.network_interfaces[i].name,
                       device_config.network_interfaces[i].mode);
        }
    }
}
```

#### Task 2.3: Verify Other Functions
- [ ] Check `any_interface_in_server_mode()` (lines 231-275)
  - Already uses specific indices (IMX_ETH0_INTERFACE, IMX_STA_INTERFACE)
  - Should be OK, but verify it doesn't rely on device_config.no_interfaces

- [ ] Check `wlan0_in_server_mode()` (lines 282-301)
  - Already uses IMX_STA_INTERFACE
  - Should be OK

---

## PHASE 3: Interface Count Fix [HIGH PRIORITY]

### File: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_mode_config.c`

#### Task 3.1: Add Helper Function
**Location**: After line 82 (Function Declarations section)

- [ ] Add declaration:
```c
static int count_configured_interfaces(void);
```

- [ ] Add implementation before `update_device_config()`:
```c
/**
 * @brief Count actually configured interfaces in device_config
 *
 * @return Number of enabled interfaces with valid names
 */
static int count_configured_interfaces(void)
{
    int count = 0;
    int i;

    for (i = 0; i < IMX_INTERFACE_MAX; i++) {
        if (device_config.network_interfaces[i].enabled &&
            strlen(device_config.network_interfaces[i].name) > 0) {
            count++;
        }
    }

    return count;
}
```

#### Task 3.2: Fix update_device_config()
**Location**: Line 217

- [ ] Replace line 217:
```c
// OLD:
device_config.no_interfaces = IMX_INTERFACE_MAX;

// NEW:
device_config.no_interfaces = count_configured_interfaces();

imx_printf("[CONFIG-DIAG] Set interface count to %d (max %d)\n",
           device_config.no_interfaces, IMX_INTERFACE_MAX);
```

#### Task 3.3: Add Diagnostic Output
- [ ] After setting interface count, add:
```c
// Verify and log configured interfaces
for (int i = 0; i < IMX_INTERFACE_MAX; i++) {
    if (device_config.network_interfaces[i].enabled &&
        strlen(device_config.network_interfaces[i].name) > 0) {
        imx_printf("[CONFIG-DIAG] Interface %d (%s): mode=%d, IP=%s\n",
                   i,
                   device_config.network_interfaces[i].name,
                   device_config.network_interfaces[i].mode,
                   device_config.network_interfaces[i].ip_address);
    }
}
```

---

## PHASE 4: Cleanup & Polish [MEDIUM PRIORITY]

### File: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_interface_writer.c`

#### Task 4.1: Fix Fallback Default IP
**Location**: Lines 210-213

- [ ] Replace hardcoded default:
```c
// OLD:
fprintf(fp, "    address 192.168.8.1\n");
fprintf(fp, "    netmask 255.255.255.0\n");
imx_cli_print("  IP Address:       192.168.8.1 (default)\n");

// NEW (match Aptera config default):
fprintf(fp, "    address 192.168.7.1\n");
fprintf(fp, "    netmask 255.255.255.0\n");
imx_cli_print("  IP Address:       192.168.7.1 (default)\n");
imx_cli_print("  WARNING:          Using fallback default IP\n");
```

#### Task 4.2: Consider Removing Fallbacks
- [ ] Evaluate: Should code error out instead of using defaults?
- [ ] Add configuration validation on boot to catch missing IPs early?

---

## PHASE 5: Testing & Validation [CRITICAL]

### Pre-Build Checks
- [ ] Review all changed code for typos
- [ ] Verify all includes are present
- [ ] Check for any missed hardcoded IPs (grep for "192.168.8")
- [ ] Verify extern declarations for device_config

### Build
- [ ] Clean build directory
- [ ] Run cmake configuration
- [ ] Build with all warnings enabled
- [ ] Fix any compilation errors
- [ ] Fix any compilation warnings

### Static Analysis
- [ ] Run grep to find any remaining "192.168.8" strings
- [ ] Verify no array access without bounds checking
- [ ] Check for any hardcoded interface indices

### Configuration File Test
- [ ] Run with `-S` option
- [ ] Verify output shows correct configuration:
  - [ ] Network interfaces: 2 (not 4)
  - [ ] eth0: 192.168.7.1
  - [ ] DHCP range: 192.168.7.100-192.168.7.199

### Generated Files Test
- [ ] Check `/etc/network/interfaces`:
  - [ ] eth0 address = 192.168.7.1 (not 192.168.8.1)

- [ ] Check `/etc/network/udhcpd.eth0.conf`:
  - [ ] start = 192.168.7.100 (not 192.168.8.100)
  - [ ] end = 192.168.7.199 (not 192.168.8.200)
  - [ ] option router = 192.168.7.1 (not 192.168.8.1)

- [ ] Check `/etc/sv/udhcpd/run`:
  - [ ] ifconfig eth0 192.168.7.1 (not 192.168.8.1)
  - [ ] No hardcoded IPs, all from config

### Diagnostic Output Test
- [ ] Verify DHCP Server Settings output shows:
  ```
  IP Range Start:   192.168.7.100
  IP Range End:     192.168.7.199
  Gateway/Router:   192.168.7.1
  ```

- [ ] Verify blacklist diagnostic shows:
  ```
  [BLACKLIST-DIAG] Dumping 2 configured interfaces (max 4):
  [BLACKLIST-DIAG] Index 0: enabled=1, name='wlan0', mode=1
  [BLACKLIST-DIAG] Index 2: enabled=1, name='eth0', mode=0
  ```
  (No index 1 or 3!)

### On-Device Testing
- [ ] Deploy to device
- [ ] Boot and verify no errors
- [ ] Check services:
  - [ ] `sv status udhcpd` - should be running
  - [ ] `sv status hostapd` - check expected state
  - [ ] `sv status wpa` - check expected state

- [ ] Test DHCP functionality:
  - [ ] Connect DHCP client to eth0
  - [ ] Verify client gets IP in 192.168.7.100-199 range
  - [ ] Verify client can ping 192.168.7.1 (gateway)
  - [ ] Check routing table on client

- [ ] Test wlan0 client mode:
  - [ ] Verify wlan0 gets DHCP from WiFi AP
  - [ ] Verify internet connectivity through wlan0

### Stress Testing
- [ ] Multiple DHCP clients on eth0
- [ ] Switch network modes (client ↔ server)
- [ ] Reboot with different configurations
- [ ] Test edge cases (empty config, invalid IPs, etc.)

---

## Success Criteria

All of these must be TRUE:

- [ ] Code compiles without errors or warnings
- [ ] Configuration file correctly read and parsed
- [ ] DHCP configuration uses IPs from config, not hardcoded
- [ ] All generated files contain correct IP addresses
- [ ] Interface count matches actual configured interfaces (2, not 4)
- [ ] No array bounds violations in diagnostic output
- [ ] DHCP clients receive IPs in correct subnet
- [ ] DHCP clients can reach gateway
- [ ] Services start/stop correctly based on configuration
- [ ] System stable after reboot

---

## Risk Mitigation

- [ ] Create git branch for this work: `git checkout -b fix/network-dhcp-config`
- [ ] Commit after each phase
- [ ] Keep backup of working configuration
- [ ] Document any issues encountered
- [ ] Be prepared to rollback if critical issues found

---

## Completion Checklist

- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 tasks complete
- [ ] All Phase 3 tasks complete
- [ ] All Phase 4 tasks complete
- [ ] All Phase 5 testing complete
- [ ] All success criteria met
- [ ] Documentation updated
- [ ] Changes committed to git
- [ ] Pull request created (if needed)

---

## Notes & Issues

_Use this section to document any problems encountered during implementation_

-
-
-

---

**END OF TODO LIST**
