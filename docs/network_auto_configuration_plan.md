# Network Auto-Configuration Implementation Plan

## Executive Summary
Implement automatic network configuration application from the binary configuration file at system boot, with intelligent change detection and controlled reboot for clean network environment establishment.

## Current State Analysis

### Existing Components
1. **Configuration Loading** (`imx_client_init.c`)
   - Binary `.cfg.bin` file loaded into `device_config` structure
   - Network settings present but NOT applied

2. **Network Mode Configuration** (`network_mode_config.c`)
   - Has staging/apply mechanism via CLI
   - `network_mode_apply_staged()` - writes Linux config files
   - `imx_apply_network_mode_from_config()` - currently only logs

3. **Network Interface Writer** (`network_interface_writer.c`)
   - Generates `/etc/network/interfaces`
   - Generates hostapd configurations
   - Generates DHCP server configurations

4. **Network Manager** (`process_network.c`)
   - Opportunistic discovery model
   - Only uses enable/disable and timing from config

## Implementation Strategy

### Phase 1: Configuration State Tracking
Create a persistent state file to track applied network configuration:
- `/usr/qk/etc/sv/network_config.state`
- Contains MD5 hash of last applied configuration
- Allows detection of configuration changes

### Phase 2: Enhanced Auto-Apply Function
Transform `imx_apply_network_mode_from_config()` from logging to active application:

```c
int imx_apply_network_mode_from_config(void)
{
    bool config_changed = false;
    char current_hash[33];
    char stored_hash[33];

    // 1. Calculate hash of current network configuration
    calculate_network_config_hash(current_hash);

    // 2. Read stored hash from state file
    if (read_stored_network_hash(stored_hash) != 0) {
        // First boot or state file missing
        config_changed = true;
    } else {
        // Compare hashes
        config_changed = (strcmp(current_hash, stored_hash) != 0);
    }

    if (config_changed) {
        // 3. Apply configuration
        int result = apply_network_configuration();

        if (result == 0) {
            // 4. Save new hash
            save_network_hash(current_hash);

            // 5. Schedule system reboot
            schedule_network_reboot();
            return 1; // Indicates reboot pending
        }
    }

    return 0; // No changes or error
}
```

### Phase 3: Configuration Application Logic

```c
static int apply_network_configuration(void)
{
    int changes_made = 0;

    // Process each interface in device_config
    for (int i = 0; i < device_config.no_interfaces && i < IMX_INTERFACE_MAX; i++) {
        network_interfaces_t *iface = &device_config.network_interfaces[i];

        if (!iface->enabled || strlen(iface->name) == 0) {
            continue;
        }

        // Apply configuration based on interface
        if (strcmp(iface->name, "eth0") == 0) {
            changes_made |= apply_eth0_config(iface);
        } else if (strcmp(iface->name, "wlan0") == 0) {
            changes_made |= apply_wlan0_config(iface);
        } else if (strcmp(iface->name, "ppp0") == 0) {
            changes_made |= apply_ppp0_config(iface);
        }
    }

    if (changes_made) {
        // Generate all configuration files
        write_network_interfaces_file();

        // Generate DHCP server configs if needed
        for (int i = 0; i < device_config.no_interfaces; i++) {
            if (device_config.network_interfaces[i].mode == IMX_IF_MODE_SERVER) {
                generate_dhcp_server_config(device_config.network_interfaces[i].name);

                if (strcmp(device_config.network_interfaces[i].name, "wlan0") == 0) {
                    generate_hostapd_config();
                }
            }
        }
    }

    return changes_made;
}
```

### Phase 4: Configuration Hash Calculation

```c
static void calculate_network_config_hash(char *hash_out)
{
    MD5_CTX ctx;
    unsigned char md5_hash[MD5_DIGEST_LENGTH];

    MD5_Init(&ctx);

    // Hash all network interface configurations
    for (int i = 0; i < device_config.no_interfaces; i++) {
        network_interfaces_t *iface = &device_config.network_interfaces[i];

        // Hash interface properties
        MD5_Update(&ctx, &iface->enabled, sizeof(iface->enabled));
        MD5_Update(&ctx, iface->name, strlen(iface->name));
        MD5_Update(&ctx, &iface->mode, sizeof(iface->mode));
        MD5_Update(&ctx, iface->ip_address, strlen(iface->ip_address));
        MD5_Update(&ctx, iface->netmask, strlen(iface->netmask));
        MD5_Update(&ctx, iface->gateway, strlen(iface->gateway));
        MD5_Update(&ctx, &iface->use_dhcp_server, sizeof(iface->use_dhcp_server));
        MD5_Update(&ctx, &iface->use_connection_sharing, sizeof(iface->use_connection_sharing));

        // Hash DHCP server settings if applicable
        if (iface->use_dhcp_server) {
            MD5_Update(&ctx, iface->dhcp_start, strlen(iface->dhcp_start));
            MD5_Update(&ctx, iface->dhcp_end, strlen(iface->dhcp_end));
            MD5_Update(&ctx, &iface->dhcp_lease_time, sizeof(iface->dhcp_lease_time));
        }
    }

    // Hash WiFi configuration
    MD5_Update(&ctx, device_config.wifi.st_ssid, strlen(device_config.wifi.st_ssid));
    MD5_Update(&ctx, device_config.wifi.st_security_key, strlen(device_config.wifi.st_security_key));
    MD5_Update(&ctx, device_config.wifi.ap_ssid, strlen(device_config.wifi.ap_ssid));
    MD5_Update(&ctx, device_config.wifi.ap_security_key, strlen(device_config.wifi.ap_security_key));

    MD5_Final(md5_hash, &ctx);

    // Convert to hex string
    for (int i = 0; i < MD5_DIGEST_LENGTH; i++) {
        sprintf(&hash_out[i*2], "%02x", md5_hash[i]);
    }
    hash_out[32] = '\0';
}
```

### Phase 5: Controlled Reboot Implementation

```c
static void schedule_network_reboot(void)
{
    imx_cli_log_printf(true, "Network configuration changed - scheduling system reboot in 5 seconds\n");
    imx_cli_log_printf(true, "To cancel reboot, power cycle the device now\n");

    // Set reboot flag and time
    icb.network_config_reboot = true;
    imx_time_get_time(&icb.network_reboot_time);
    icb.network_reboot_time += 5000; // 5 seconds from now

    // Save a marker file to indicate clean reboot
    FILE *fp = fopen("/usr/qk/etc/sv/network_reboot.flag", "w");
    if (fp) {
        fprintf(fp, "Network configuration change reboot\n");
        fclose(fp);
    }
}
```

## Integration Points

### 1. Initialization Sequence (imatrix_interface.c)
```c
// Line 805-807 - Modify to:
#ifdef LINUX_PLATFORM
    network_manager_init();

    // Apply network interface configuration from saved settings
    int reboot_pending = imx_apply_network_mode_from_config();
    if (reboot_pending) {
        imx_cli_log_printf(true, "Network configuration will be applied after reboot\n");
        // Skip further initialization if reboot pending
        icb.state = MAIN_IMATRIX_NETWORK_REBOOT_PENDING;
        break;
    }
#endif
```

### 2. Main Process Loop (imatrix_interface.c)
Add new state for pending network reboot:
```c
case MAIN_IMATRIX_NETWORK_REBOOT_PENDING:
    if (icb.network_config_reboot) {
        if (imx_is_later(current_time, icb.network_reboot_time)) {
            // Clean reboot for network changes
            sync(); // Flush filesystem buffers
            imx_platform_reboot();
        }
        // Show countdown
        uint32_t remaining = (icb.network_reboot_time - current_time) / 1000;
        imx_set_display(IMX_DISPLAY_REBOOT_COUNTDOWN, remaining);
    }
    processing_complete = false; // Stay in this state
    break;
```

### 3. First Boot Detection
Check for clean reboot marker:
```c
static bool is_network_reboot(void)
{
    struct stat st;
    if (stat("/usr/qk/etc/sv/network_reboot.flag", &st) == 0) {
        // Remove flag and return true
        unlink("/usr/qk/etc/sv/network_reboot.flag");
        return true;
    }
    return false;
}
```

## File Modifications Required

### 1. `network_mode_config.c`
- Replace passive `imx_apply_network_mode_from_config()` with active implementation
- Add `calculate_network_config_hash()`
- Add `read_stored_network_hash()` and `save_network_hash()`
- Add `apply_network_configuration()`

### 2. `network_mode_config.h`
- Change return type: `int imx_apply_network_mode_from_config(void)`
- Add new function declarations

### 3. `imatrix_interface.c`
- Modify initialization sequence to check return value
- Add `MAIN_IMATRIX_NETWORK_REBOOT_PENDING` state
- Handle reboot countdown

### 4. `device/icb_def.h`
- Add fields to `iMatrix_Control_Block_t`:
  ```c
  bool network_config_reboot;
  imx_time_t network_reboot_time;
  ```

### 5. `device/config.h`
- Ensure all network configuration fields are properly defined in `network_interfaces_t`

## Testing Strategy

### 1. Configuration Change Tests
- Change eth0 from DHCP to static IP
- Change wlan0 from client to server mode
- Enable/disable interfaces
- Modify DHCP server ranges

### 2. State Persistence Tests
- Verify hash file creation and updates
- Test with corrupted state file
- Test with missing state file

### 3. Reboot Behavior Tests
- Verify clean reboot on configuration change
- Verify no reboot when configuration unchanged
- Test reboot cancellation window

### 4. Network Functionality Tests
- Verify interfaces come up with new configuration
- Test DHCP server operation
- Test AP mode functionality
- Verify connectivity on all interfaces

## Risk Mitigation

### 1. Reboot Loops
- Implement maximum reboot counter (3 attempts)
- Fall back to default configuration after failures
- Log all reboot attempts

### 2. Configuration Corruption
- Validate configuration before applying
- Keep backup of last known good configuration
- Implement configuration sanity checks

### 3. Network Isolation
- Ensure at least one interface remains accessible
- Implement emergency recovery mode (hold button on boot)
- Provide serial console access

## Implementation Timeline

1. **Day 1-2**: Implement configuration hash and state tracking
2. **Day 3-4**: Implement auto-apply logic
3. **Day 5**: Implement controlled reboot mechanism
4. **Day 6-7**: Testing and validation
5. **Day 8**: Documentation and code review

## Success Criteria

1. ✅ Network configuration automatically applied from config file at boot
2. ✅ Changes detected via hash comparison
3. ✅ System reboots cleanly when configuration changes
4. ✅ All interfaces configured correctly after reboot
5. ✅ No manual intervention required for network setup
6. ✅ Failsafe mechanisms prevent reboot loops

## Notes

- The implementation maintains backward compatibility
- CLI commands remain functional for manual override
- Configuration can still be staged and applied manually
- System logs all automatic configuration changes
- Recovery mode available via serial console