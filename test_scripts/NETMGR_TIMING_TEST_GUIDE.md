# Network Manager Timing Configuration Test Guide

## Overview
This guide describes how to test the network manager timing configuration feature that stores timing parameters in the device configuration instead of using environment variables.

## Key Features Implemented
1. **Persistent Storage**: Network timing parameters are stored in the device configuration using 32 bytes of the spare[34] array
2. **Default Initialization**: On first boot or when configuration is invalid, default values are automatically set
3. **CLI Commands**: Two new commands for viewing and modifying timing parameters
4. **No Environment Variables**: Configuration is loaded from persistent storage, not environment variables

## Configuration Structure
The timing configuration uses a compact structure that fits in 32 bytes:
```c
typedef struct __attribute__((packed)) {
    uint16_t magic;                     // 0x4E54 = "NT" for validation
    uint16_t eth0_cooldown_s;           // Ethernet cooldown (seconds)
    uint16_t wifi_cooldown_s;           // WiFi cooldown (seconds)
    uint16_t ppp_cooldown_s;            // PPP cooldown (seconds)
    uint16_t ppp_wait_connection_s;     // PPP wait time (seconds)
    uint16_t max_state_duration_s;      // Max state duration (seconds)
    uint16_t online_check_time_s;       // Online check interval (seconds)
    uint16_t ping_interval_s;           // Ping interval (seconds)
    uint16_t ping_timeout_ms;           // Ping timeout (milliseconds)
    uint8_t  ping_count;                // Number of pings
    uint8_t  hysteresis_switch_limit;   // Max switches in window
    uint16_t hysteresis_window_s;       // Hysteresis window (seconds)
    uint16_t hysteresis_cooldown_s;     // Hysteresis cooldown (seconds)
    uint16_t wifi_scan_wait_ms;         // WiFi scan wait (milliseconds)
    uint16_t wifi_dhcp_wait_s;          // WiFi DHCP wait (seconds)
    uint16_t reserved;                  // Reserved for alignment
} netmgr_timing_config_t;
```

## CLI Commands

### 1. View Configuration: `netmgr_timing`
Displays the current network manager timing configuration.

Example output:
```
Network Manager Timing Configuration:
=====================================

Interface Cooldown Times:
  Ethernet (eth0):     30 seconds
  WiFi (wlan0):        30 seconds
  Cellular (ppp0):     30 seconds

State Machine Timing:
  Max state duration:  20 seconds
  Online check time:   10 seconds
  PPP wait connection: 60 seconds

Ping Configuration:
  Ping interval:       5 seconds
  Ping timeout:        1000 ms
  Ping count:          3

Hysteresis Configuration:
  Window duration:     60 seconds
  Switch limit:        3 switches
  Cooldown time:       30 seconds

WiFi Specific Timing:
  Scan wait time:      2000 ms
  DHCP wait time:      5 seconds
```

### 2. Modify Parameter: `netmgr_set_timing <parameter> <value>`
Sets a specific timing parameter and saves the configuration.

Parameters:
- `eth0_cooldown` - Ethernet cooldown time (1-3600 seconds)
- `wifi_cooldown` - WiFi cooldown time (1-3600 seconds)
- `ppp_cooldown` - PPP cooldown time (1-3600 seconds)
- `ppp_wait` - PPP wait for connection (10-300 seconds)
- `max_state` - Max state duration (5-120 seconds)
- `online_check` - Online check interval (5-300 seconds)
- `ping_interval` - Ping interval (1-60 seconds)
- `ping_timeout` - Ping timeout (100-5000 ms)
- `ping_count` - Number of pings (1-10)
- `hysteresis_switches` - Max switches in window (1-10)
- `hysteresis_window` - Hysteresis window (10-600 seconds)
- `hysteresis_cooldown` - Hysteresis cooldown (5-300 seconds)
- `wifi_scan_wait` - WiFi scan wait (500-10000 ms)
- `wifi_dhcp_wait` - WiFi DHCP wait (1-30 seconds)

Example:
```
> netmgr_set_timing eth0_cooldown 45
Parameter 'eth0_cooldown' set to 45 and saved
Changes will take effect on next network manager cycle
```

## Test Procedures

### Test 1: Initial Configuration
1. Build and flash the application with a clean configuration
2. Boot the device and connect via CLI
3. Run `netmgr_timing`
4. Verify that default values are displayed
5. Check logs for "Network timing config invalid (magic: 0x0000), initializing defaults"

### Test 2: Modify Single Parameter
1. Run `netmgr_set_timing eth0_cooldown 45`
2. Verify message "Parameter 'eth0_cooldown' set to 45 and saved"
3. Run `netmgr_timing`
4. Verify "Ethernet (eth0): 45 seconds" is displayed

### Test 3: Modify Multiple Parameters
1. Set multiple parameters:
   ```
   netmgr_set_timing wifi_cooldown 20
   netmgr_set_timing ping_count 5
   netmgr_set_timing hysteresis_window 90
   ```
2. Run `netmgr_timing` and verify all changes are reflected

### Test 4: Parameter Validation
1. Try invalid values:
   ```
   netmgr_set_timing eth0_cooldown 5000  # Too large
   netmgr_set_timing ping_count 15       # Too large
   netmgr_set_timing max_state 2         # Too small
   ```
2. Verify appropriate error messages are displayed

### Test 5: Persistence Across Reboot
1. Set custom values for several parameters
2. Note the values using `netmgr_timing`
3. Reboot the device
4. Run `netmgr_timing` again
5. Verify all custom values are preserved

### Test 6: Network Manager Behavior
1. Set `eth0_cooldown` to 10 seconds
2. Disconnect ethernet cable
3. Verify in logs that network manager waits 10 seconds before retrying eth0
4. Verify WiFi or cellular is used as fallback

### Test 7: Hysteresis Testing
1. Set hysteresis parameters:
   ```
   netmgr_set_timing hysteresis_window 30
   netmgr_set_timing hysteresis_switches 2
   netmgr_set_timing hysteresis_cooldown 15
   ```
2. Force rapid interface switches by connecting/disconnecting ethernet
3. Verify hysteresis blocks excessive switching after 2 switches in 30 seconds
4. Verify 15-second cooldown is enforced

## Expected Results
- Configuration initializes with defaults on first boot
- All parameters can be viewed and modified via CLI
- Parameter changes take effect immediately in network manager
- Configuration persists across reboots
- Invalid parameters are rejected with appropriate error messages
- Network manager uses configured values for all timing operations

## Troubleshooting
- If configuration shows as "not initialized", reboot to trigger initialization
- If changes don't persist, check that `imatrix_save_config()` succeeds
- Use network manager status command (`net`) to see current timing in action
- Check system logs for "Network timing config invalid" messages

## Integration Notes
- The configuration is stored in the `device_config.netmgr_timing` structure
- The spare[34] bytes in IOT_Device_Config_t are used via a union for backward compatibility
- Environment variables (NETMGR_*) are no longer used
- The network_timing_config.c/h files can be removed as they're replaced by this implementation