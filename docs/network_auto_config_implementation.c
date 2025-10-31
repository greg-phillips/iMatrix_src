/*
 * Network Auto-Configuration Implementation
 *
 * This file contains the implementation code for automatic network
 * configuration application from the binary configuration file.
 *
 * Author: Greg Phillips
 * Date: 2025-10-31
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
#include <openssl/md5.h>

#include "imatrix.h"
#include "device/config.h"
#include "device/icb_def.h"
#include "network_mode_config.h"
#include "network_interface_writer.h"
#include "dhcp_server_config.h"

/******************************************************
 *                      Macros
 ******************************************************/
#define NETWORK_CONFIG_STATE_FILE    "/usr/qk/etc/sv/network_config.state"
#define NETWORK_REBOOT_FLAG_FILE     "/usr/qk/etc/sv/network_reboot.flag"
#define NETWORK_CONFIG_BACKUP_FILE   "/usr/qk/etc/sv/network_config.backup"
#define MAX_REBOOT_ATTEMPTS          3

/******************************************************
 *                    Constants
 ******************************************************/
static const uint32_t NETWORK_REBOOT_DELAY_MS = 5000;  // 5 seconds

/******************************************************
 *               Function Declarations
 ******************************************************/
static void calculate_network_config_hash(char *hash_out);
static int read_stored_network_hash(char *hash_out);
static int save_network_hash(const char *hash);
static int apply_network_configuration(void);
static int apply_eth0_config(network_interfaces_t *iface);
static int apply_wlan0_config(network_interfaces_t *iface);
static int apply_ppp0_config(network_interfaces_t *iface);
static void schedule_network_reboot(void);
static bool is_network_reboot(void);
static int get_reboot_attempt_count(void);
static void increment_reboot_attempt_count(void);
static void clear_reboot_attempt_count(void);
static bool validate_network_configuration(void);

/******************************************************
 *               Variable Definitions
 ******************************************************/
extern IOT_Device_Config_t device_config;
extern iMatrix_Control_Block_t icb;

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Calculate MD5 hash of current network configuration
 *
 * @param hash_out Buffer to store 33-byte hex string (32 chars + null)
 */
static void calculate_network_config_hash(char *hash_out)
{
    MD5_CTX ctx;
    unsigned char md5_hash[MD5_DIGEST_LENGTH];

    MD5_Init(&ctx);

    // Hash all network interface configurations
    for (int i = 0; i < device_config.no_interfaces && i < IMX_INTERFACE_MAX; i++) {
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

    // Hash network timing configuration
    MD5_Update(&ctx, &device_config.netmgr_timing, sizeof(device_config.netmgr_timing));

    MD5_Final(md5_hash, &ctx);

    // Convert to hex string
    for (int i = 0; i < MD5_DIGEST_LENGTH; i++) {
        sprintf(&hash_out[i*2], "%02x", md5_hash[i]);
    }
    hash_out[32] = '\0';
}

/**
 * @brief Read stored network configuration hash from state file
 *
 * @param hash_out Buffer to store 33-byte hex string
 * @return 0 on success, -1 on error
 */
static int read_stored_network_hash(char *hash_out)
{
    FILE *fp = fopen(NETWORK_CONFIG_STATE_FILE, "r");
    if (fp == NULL) {
        return -1;
    }

    if (fgets(hash_out, 33, fp) == NULL) {
        fclose(fp);
        return -1;
    }

    fclose(fp);

    // Validate hash format
    if (strlen(hash_out) != 32) {
        return -1;
    }

    for (int i = 0; i < 32; i++) {
        if (!isxdigit(hash_out[i])) {
            return -1;
        }
    }

    return 0;
}

/**
 * @brief Save network configuration hash to state file
 *
 * @param hash Hash string to save
 * @return 0 on success, -1 on error
 */
static int save_network_hash(const char *hash)
{
    FILE *fp = fopen(NETWORK_CONFIG_STATE_FILE, "w");
    if (fp == NULL) {
        imx_cli_log_printf(true, "Error: Failed to open state file for writing: %s\n",
                          NETWORK_CONFIG_STATE_FILE);
        return -1;
    }

    fprintf(fp, "%s\n", hash);
    fclose(fp);

    // Set proper permissions
    chmod(NETWORK_CONFIG_STATE_FILE, 0600);

    return 0;
}

/**
 * @brief Apply eth0 interface configuration
 *
 * @param iface Interface configuration
 * @return 1 if changes made, 0 otherwise
 */
static int apply_eth0_config(network_interfaces_t *iface)
{
    int changes_made = 0;

    imx_cli_log_printf(true, "Applying eth0 configuration: mode=%s, IP=%s\n",
                      iface->mode == IMX_IF_MODE_SERVER ? "server" : "client",
                      iface->mode == IMX_IF_MODE_SERVER ? iface->ip_address : "DHCP");

    if (iface->mode == IMX_IF_MODE_SERVER) {
        // Server mode - generate DHCP server config
        if (generate_dhcp_server_config("eth0") == 0) {
            changes_made = 1;
        }

        // Apply static IP configuration
        if (strlen(iface->ip_address) > 0 && strlen(iface->netmask) > 0) {
            char cmd[256];
            snprintf(cmd, sizeof(cmd),
                    "ifconfig eth0 %s netmask %s up 2>/dev/null",
                    iface->ip_address, iface->netmask);
            system(cmd);
        }
    } else {
        // Client mode - remove DHCP server config
        if (remove_dhcp_server_config("eth0") == 0) {
            changes_made = 1;
        }
    }

    return changes_made;
}

/**
 * @brief Apply wlan0 interface configuration
 *
 * @param iface Interface configuration
 * @return 1 if changes made, 0 otherwise
 */
static int apply_wlan0_config(network_interfaces_t *iface)
{
    int changes_made = 0;

    imx_cli_log_printf(true, "Applying wlan0 configuration: mode=%s\n",
                      iface->mode == IMX_IF_MODE_SERVER ? "AP" : "client");

    if (iface->mode == IMX_IF_MODE_SERVER) {
        // AP mode - generate hostapd and DHCP configs
        if (generate_hostapd_config() == 0) {
            changes_made = 1;
        }

        if (generate_dhcp_server_config("wlan0") == 0) {
            changes_made = 1;
        }

        // Stop wpa_supplicant if running
        system("killall wpa_supplicant 2>/dev/null");
    } else {
        // Client mode - remove AP configs
        if (remove_hostapd_config() == 0) {
            changes_made = 1;
        }

        if (remove_dhcp_server_config("wlan0") == 0) {
            changes_made = 1;
        }

        // Stop hostapd if running
        system("killall hostapd 2>/dev/null");
    }

    return changes_made;
}

/**
 * @brief Apply ppp0 interface configuration
 *
 * @param iface Interface configuration
 * @return 1 if changes made, 0 otherwise
 */
static int apply_ppp0_config(network_interfaces_t *iface)
{
    imx_cli_log_printf(true, "PPP0 configuration: enabled=%d\n", iface->enabled);

    // PPP is handled by the cellular manager
    // Just ensure enabled state is correct
    return 0;
}

/**
 * @brief Apply network configuration from device_config
 *
 * @return Number of changes made
 */
static int apply_network_configuration(void)
{
    int changes_made = 0;

    imx_cli_log_printf(true, "Applying network configuration from device_config\n");

    // Process each interface in device_config
    for (int i = 0; i < device_config.no_interfaces && i < IMX_INTERFACE_MAX; i++) {
        network_interfaces_t *iface = &device_config.network_interfaces[i];

        if (!iface->enabled || strlen(iface->name) == 0) {
            continue;
        }

        imx_cli_log_printf(true, "Processing interface %s (enabled=%d, mode=%d)\n",
                          iface->name, iface->enabled, iface->mode);

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
        // Generate network interfaces file
        imx_cli_log_printf(true, "Writing network interfaces file\n");
        if (write_network_interfaces_file() != 0) {
            imx_cli_log_printf(true, "Error: Failed to write network interfaces file\n");
        }

        // Update blacklist configuration
        if (update_network_blacklist() != 0) {
            imx_cli_log_printf(true, "Warning: Failed to update network blacklist\n");
        }

        // Restart network services
        imx_cli_log_printf(true, "Restarting network services\n");
        system("sv restart networking 2>/dev/null");
    }

    return changes_made;
}

/**
 * @brief Schedule a system reboot for network configuration changes
 */
static void schedule_network_reboot(void)
{
    imx_cli_log_printf(true, "======================================\n");
    imx_cli_log_printf(true, "NETWORK CONFIGURATION CHANGED\n");
    imx_cli_log_printf(true, "System will reboot in %d seconds\n", NETWORK_REBOOT_DELAY_MS/1000);
    imx_cli_log_printf(true, "======================================\n");

    // Set reboot flag and time
    icb.network_config_reboot = true;
    imx_time_get_time(&icb.network_reboot_time);
    icb.network_reboot_time += NETWORK_REBOOT_DELAY_MS;

    // Save a marker file to indicate clean reboot
    FILE *fp = fopen(NETWORK_REBOOT_FLAG_FILE, "w");
    if (fp) {
        fprintf(fp, "Network configuration change reboot\n");
        fprintf(fp, "Timestamp: %lu\n", (unsigned long)time(NULL));
        fclose(fp);
        chmod(NETWORK_REBOOT_FLAG_FILE, 0600);
    }

    // Increment reboot attempt counter
    increment_reboot_attempt_count();
}

/**
 * @brief Check if this boot is from a network configuration change
 *
 * @return true if network reboot, false otherwise
 */
static bool is_network_reboot(void)
{
    struct stat st;
    if (stat(NETWORK_REBOOT_FLAG_FILE, &st) == 0) {
        // Remove flag and return true
        unlink(NETWORK_REBOOT_FLAG_FILE);
        return true;
    }
    return false;
}

/**
 * @brief Get the current reboot attempt count
 *
 * @return Reboot attempt count
 */
static int get_reboot_attempt_count(void)
{
    FILE *fp = fopen("/usr/qk/etc/sv/reboot_count", "r");
    if (fp == NULL) {
        return 0;
    }

    int count = 0;
    fscanf(fp, "%d", &count);
    fclose(fp);

    return count;
}

/**
 * @brief Increment the reboot attempt counter
 */
static void increment_reboot_attempt_count(void)
{
    int count = get_reboot_attempt_count();
    count++;

    FILE *fp = fopen("/usr/qk/etc/sv/reboot_count", "w");
    if (fp) {
        fprintf(fp, "%d\n", count);
        fclose(fp);
    }
}

/**
 * @brief Clear the reboot attempt counter
 */
static void clear_reboot_attempt_count(void)
{
    unlink("/usr/qk/etc/sv/reboot_count");
}

/**
 * @brief Validate network configuration for sanity
 *
 * @return true if valid, false otherwise
 */
static bool validate_network_configuration(void)
{
    bool has_valid_interface = false;

    // Check for at least one enabled interface
    for (int i = 0; i < device_config.no_interfaces && i < IMX_INTERFACE_MAX; i++) {
        if (device_config.network_interfaces[i].enabled) {
            has_valid_interface = true;

            // Validate IP addresses if in server mode
            if (device_config.network_interfaces[i].mode == IMX_IF_MODE_SERVER) {
                if (strlen(device_config.network_interfaces[i].ip_address) == 0) {
                    imx_cli_log_printf(true, "Error: Server mode interface %s has no IP address\n",
                                      device_config.network_interfaces[i].name);
                    return false;
                }
            }
        }
    }

    if (!has_valid_interface) {
        imx_cli_log_printf(true, "Error: No enabled network interfaces found\n");
        return false;
    }

    return true;
}

/**
 * @brief Main function to apply network configuration from config file
 *
 * This is the enhanced version that actually applies configuration
 * rather than just logging it.
 *
 * @return 0 if no changes, 1 if reboot pending, -1 on error
 */
int imx_apply_network_mode_from_config(void)
{
    bool config_changed = false;
    char current_hash[33];
    char stored_hash[33];

    imx_cli_log_printf(true, "Checking network configuration...\n");

    // Check if we're in a reboot loop
    int reboot_attempts = get_reboot_attempt_count();
    if (reboot_attempts >= MAX_REBOOT_ATTEMPTS) {
        imx_cli_log_printf(true, "ERROR: Maximum reboot attempts (%d) exceeded!\n",
                          MAX_REBOOT_ATTEMPTS);
        imx_cli_log_printf(true, "Falling back to default configuration\n");

        // Clear the attempt counter
        clear_reboot_attempt_count();

        // Remove state file to force reconfiguration on next normal boot
        unlink(NETWORK_CONFIG_STATE_FILE);

        return -1;
    }

    // Check if this was a network configuration reboot
    if (is_network_reboot()) {
        imx_cli_log_printf(true, "System rebooted for network configuration changes\n");
        // Clear reboot counter on successful reboot
        clear_reboot_attempt_count();
    }

    // Validate configuration before applying
    if (!validate_network_configuration()) {
        imx_cli_log_printf(true, "Error: Invalid network configuration\n");
        return -1;
    }

    // Calculate hash of current network configuration
    calculate_network_config_hash(current_hash);
    imx_cli_log_printf(true, "Current config hash: %s\n", current_hash);

    // Read stored hash from state file
    if (read_stored_network_hash(stored_hash) != 0) {
        // First boot or state file missing
        imx_cli_log_printf(true, "No stored configuration hash found (first boot)\n");
        config_changed = true;
    } else {
        imx_cli_log_printf(true, "Stored config hash: %s\n", stored_hash);
        // Compare hashes
        config_changed = (strcmp(current_hash, stored_hash) != 0);
    }

    if (config_changed) {
        imx_cli_log_printf(true, "Network configuration has changed\n");

        // Backup current configuration
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "cp %s %s 2>/dev/null",
                NETWORK_CONFIG_STATE_FILE, NETWORK_CONFIG_BACKUP_FILE);
        system(cmd);

        // Apply configuration
        int changes_applied = apply_network_configuration();

        if (changes_applied > 0) {
            imx_cli_log_printf(true, "Applied %d network configuration changes\n",
                              changes_applied);

            // Save new hash
            if (save_network_hash(current_hash) != 0) {
                imx_cli_log_printf(true, "Warning: Failed to save configuration hash\n");
            }

            // Schedule system reboot
            schedule_network_reboot();
            return 1; // Indicates reboot pending
        } else {
            imx_cli_log_printf(true, "No actual changes applied\n");
            // Save hash anyway to prevent repeated attempts
            save_network_hash(current_hash);
        }
    } else {
        imx_cli_log_printf(true, "Network configuration unchanged\n");
    }

    return 0; // No changes or error
}

/**
 * @brief Handle the network configuration reboot state
 *
 * This function should be called from the main process loop
 * when in MAIN_IMATRIX_NETWORK_REBOOT_PENDING state
 *
 * @param current_time Current system time
 * @return true if reboot is pending, false otherwise
 */
bool imx_handle_network_reboot_pending(imx_time_t current_time)
{
    if (!icb.network_config_reboot) {
        return false;
    }

    if (imx_is_later(current_time, icb.network_reboot_time)) {
        imx_cli_log_printf(true, "Executing network configuration reboot...\n");

        // Sync filesystem buffers
        sync();
        sync();
        sync();

        // Perform reboot
        imx_platform_reboot();

        // Should not reach here
        return true;
    }

    // Show countdown
    uint32_t remaining_ms = icb.network_reboot_time - current_time;
    uint32_t remaining_sec = (remaining_ms + 999) / 1000;  // Round up

    static uint32_t last_displayed_sec = 0;
    if (remaining_sec != last_displayed_sec) {
        imx_cli_log_printf(true, "Rebooting in %u seconds...\n", remaining_sec);
        last_displayed_sec = remaining_sec;
    }

    return true;
}