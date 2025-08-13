/*
 * Test program to demonstrate network configuration display functionality
 */

#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "imatrix.h"
#include "common.h"
#include "device_app_dct.h"
#include "IMX_Platform/LINUX_Platform/networking/process_network.h"
#include "IMX_Platform/LINUX_Platform/networking/wifi_reassociate.h"

// External device config
extern IOT_Device_Config_t device_config;

// Mock CLI print function
void imx_cli_print(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
}

int main(int argc, char *argv[])
{
    printf("=== Network Configuration Display Test ===\n\n");
    
    // Initialize some test data
    device_config.no_interfaces = 3;
    
    // Configure WiFi interface
    strcpy(device_config.network_interfaces[IMX_STA_INTERFACE].name, "wlan0");
    device_config.network_interfaces[IMX_STA_INTERFACE].enabled = true;
    device_config.network_interfaces[IMX_STA_INTERFACE].mode = IMX_IF_MODE_CLIENT;
    strcpy(device_config.wifi.st_ssid, "TestNetwork");
    device_config.wifi.use_static_ip = false;
    
    // Configure Ethernet interface
    strcpy(device_config.network_interfaces[IMX_ETH0_INTERFACE].name, "eth0");
    device_config.network_interfaces[IMX_ETH0_INTERFACE].enabled = true;
    device_config.network_interfaces[IMX_ETH0_INTERFACE].mode = IMX_IF_MODE_CLIENT;
    device_config.eth0.use_dhcp = false;
    device_config.eth0.static_ip_address[0] = 192;
    device_config.eth0.static_ip_address[1] = 168;
    device_config.eth0.static_ip_address[2] = 1;
    device_config.eth0.static_ip_address[3] = 100;
    device_config.eth0.static_netmask[0] = 255;
    device_config.eth0.static_netmask[1] = 255;
    device_config.eth0.static_netmask[2] = 255;
    device_config.eth0.static_netmask[3] = 0;
    device_config.eth0.static_gateway[0] = 192;
    device_config.eth0.static_gateway[1] = 168;
    device_config.eth0.static_gateway[2] = 1;
    device_config.eth0.static_gateway[3] = 1;
    
    // Configure PPP interface
    strcpy(device_config.network_interfaces[IMX_PPP0_INTERFACE].name, "ppp0");
    device_config.network_interfaces[IMX_PPP0_INTERFACE].enabled = false;
    device_config.network_interfaces[IMX_PPP0_INTERFACE].mode = IMX_IF_MODE_CLIENT;
    strcpy(device_config.ppp0.apn, "hologram");
    
    // Display network configuration
    printf("1. Testing network configuration display:\n");
    printf("----------------------------------------\n");
    imx_get_network_config_display();
    
    printf("\n2. Testing WiFi reassociation config access:\n");
    printf("--------------------------------------------\n");
    
    bool wifi_reassoc_enabled;
    int wifi_reassoc_method;
    uint32_t wifi_scan_wait_ms;
    
    imx_get_wifi_reassoc_config(&wifi_reassoc_enabled, &wifi_reassoc_method, &wifi_scan_wait_ms);
    
    printf("WiFi Reassociation: %s\n", wifi_reassoc_enabled ? "Enabled" : "Disabled");
    printf("Method: %s\n", wifi_reassoc_method_name((wifi_reassoc_method_t)wifi_reassoc_method));
    printf("Scan Wait: %u ms\n", wifi_scan_wait_ms);
    
    printf("\n=== Test Complete ===\n");
    
    return 0;
}