# Required Code Modifications for Network Auto-Configuration

## 1. Modify `device/icb_def.h`

Add these fields to `iMatrix_Control_Block_t` structure:

```c
typedef struct {
    // ... existing fields ...

    // Network configuration reboot management
    bool network_config_reboot;        // Flag indicating network config reboot pending
    imx_time_t network_reboot_time;    // Time when reboot should occur

    // ... rest of structure ...
} iMatrix_Control_Block_t;
```

## 2. Modify `device/icb_def.h` - Add new state

Add to the `main_state_t` enum:

```c
typedef enum {
    // ... existing states ...
    MAIN_IMATRIX_CHECK_TO_RESTART_WIFI,
    MAIN_IMATRIX_NETWORK_REBOOT_PENDING,  // New state for network reboot
    MAIN_IMATRIX_POST_MFG_LOAD_1,
    // ... rest of states ...
} main_state_t;
```

## 3. Modify `network_mode_config.h`

Change function signature and add new declarations:

```c
// Change return type from void to int
int imx_apply_network_mode_from_config(void);

// Add new function declarations
bool imx_handle_network_reboot_pending(imx_time_t current_time);
bool imx_is_network_configuration_changed(void);
int imx_backup_network_configuration(void);
int imx_restore_network_configuration(void);
```

## 4. Modify `imatrix_interface.c` - Initialization

Replace lines 805-807 with:

```c
#ifdef LINUX_PLATFORM
    network_manager_init();

    // Apply network interface configuration from saved settings
    int network_config_result = imx_apply_network_mode_from_config();
    if (network_config_result > 0) {
        imx_cli_log_printf(true, "Network configuration will be applied after reboot\n");
        // Skip further initialization if reboot pending
        icb.state = MAIN_IMATRIX_NETWORK_REBOOT_PENDING;
        break;
    } else if (network_config_result < 0) {
        imx_cli_log_printf(true, "Warning: Failed to apply network configuration\n");
        // Continue with default configuration
    }
#endif
```

## 5. Modify `imatrix_interface.c` - Main Process Loop

Add new case in the main switch statement (around line 689):

```c
case MAIN_IMATRIX_NETWORK_REBOOT_PENDING:
    /*
     * Handle pending network configuration reboot
     */
    if (imx_handle_network_reboot_pending(current_time)) {
        // Reboot is pending, stay in this state
        processing_complete = false;

        // Update display to show reboot countdown
        uint32_t remaining = (icb.network_reboot_time - current_time) / 1000;
        imx_set_display(IMX_DISPLAY_REBOOT_COUNTDOWN, false);
    } else {
        // Reboot cancelled or error
        icb.state = MAIN_IMATRIX_SETUP;
    }
    break;
```

## 6. Update state name array in `imatrix_interface.c`

Around line 1135, add the new state name:

```c
char *icb_states[MAIN_NO_STATES] = {
    "MAIN_IMATRIX_SETUP",
    // ... existing states ...
    "MAIN_IMATRIX_CHECK_TO_RESTART_WIFI",
    "MAIN_IMATRIX_NETWORK_REBOOT_PENDING",    // Add this
    "MAIN_IMATRIX_POST_MFG_LOAD_1",
    // ... rest of states ...
};
```

## 7. Create new file: `network_auto_config.c`

Place the implementation code from `network_auto_config_implementation.c` into:
`/home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`

## 8. Create new file: `network_auto_config.h`

```c
/*
 * Network Auto-Configuration Header
 */

#ifndef NETWORK_AUTO_CONFIG_H
#define NETWORK_AUTO_CONFIG_H

#include <stdbool.h>
#include "imatrix.h"

/**
 * @brief Apply network configuration from config file
 *
 * @return 0 if no changes, 1 if reboot pending, -1 on error
 */
int imx_apply_network_mode_from_config(void);

/**
 * @brief Handle network configuration reboot state
 *
 * @param current_time Current system time
 * @return true if reboot is pending
 */
bool imx_handle_network_reboot_pending(imx_time_t current_time);

/**
 * @brief Check if network configuration has changed
 *
 * @return true if configuration changed
 */
bool imx_is_network_configuration_changed(void);

/**
 * @brief Backup current network configuration
 *
 * @return 0 on success, -1 on error
 */
int imx_backup_network_configuration(void);

/**
 * @brief Restore network configuration from backup
 *
 * @return 0 on success, -1 on error
 */
int imx_restore_network_configuration(void);

#endif /* NETWORK_AUTO_CONFIG_H */
```

## 9. Update CMakeLists.txt

Add the new source file to the iMatrix build:

```cmake
# In iMatrix/IMX_Platform/LINUX_Platform/CMakeLists.txt
set(LINUX_PLATFORM_SOURCES
    # ... existing sources ...
    ${CMAKE_CURRENT_SOURCE_DIR}/networking/network_auto_config.c
    # ... rest of sources ...
)
```

## 10. Add Display State for Reboot Countdown

In `device/imx_leds.h`, add:

```c
typedef enum {
    // ... existing display states ...
    IMX_DISPLAY_REBOOT_COUNTDOWN,
    // ... rest of states ...
} imx_display_state_t;
```

## 11. Implement Display Handler

In the display handler function, add case:

```c
case IMX_DISPLAY_REBOOT_COUNTDOWN:
    // Flash RED/GREEN alternately to indicate reboot
    if ((current_time / 500) % 2 == 0) {
        set_led(LED_RED, LED_ON);
        set_led(LED_GREEN, LED_OFF);
    } else {
        set_led(LED_RED, LED_OFF);
        set_led(LED_GREEN, LED_ON);
    }
    break;
```

## 12. Add OpenSSL Dependency

Update CMakeLists.txt to link OpenSSL for MD5:

```cmake
# Find OpenSSL
find_package(OpenSSL REQUIRED)

# Add to target link libraries
target_link_libraries(imatrix
    # ... existing libraries ...
    OpenSSL::Crypto
)
```

## Integration Testing Checklist

### Pre-Integration Tests
- [ ] Verify all header files compile without errors
- [ ] Check for circular dependencies
- [ ] Validate state machine transitions

### Post-Integration Tests
- [ ] Boot with unchanged configuration - verify no reboot
- [ ] Change eth0 from DHCP to static - verify reboot and application
- [ ] Change wlan0 from client to AP - verify reboot and application
- [ ] Corrupt state file - verify recovery
- [ ] Test reboot loop prevention (3 attempts max)
- [ ] Verify CLI commands still work
- [ ] Test with missing configuration file
- [ ] Test with invalid IP addresses

### Performance Tests
- [ ] Measure boot time impact
- [ ] Check hash calculation time
- [ ] Verify file I/O operations
- [ ] Monitor CPU usage during configuration

### Edge Cases
- [ ] Power loss during reboot
- [ ] Configuration file corruption
- [ ] Simultaneous CLI and auto-config
- [ ] Network cable unplugged during config