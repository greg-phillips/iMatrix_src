/**
 * @file cellular_man_additions.h
 * @brief Additional definitions for cellular_man.c to support PPP monitoring
 * @date 2025-11-22
 * @author Claude Code Implementation
 *
 * Add these definitions to cellular_man.h or create a new header
 */

#ifndef CELLULAR_MAN_ADDITIONS_H
#define CELLULAR_MAN_ADDITIONS_H

#include <stdbool.h>
#include <time.h>

/**
 * PPP Monitor Result codes
 */
typedef enum {
    PPP_NO_INTERFACE,    // No PPP interface found
    PPP_IN_PROGRESS,     // PPP coming up
    PPP_ESTABLISHED,     // PPP fully up with IP
    PPP_FAILED          // PPP establishment failed
} PPPMonitorResult;

/**
 * Network state additions
 */
typedef enum {
    NET_HANDLE_FAILURE = 100,  // Handle connection failures
    NET_RETRY_DELAY           // Wait before retry
} NetworkStateAdditions;

/**
 * @brief Global coordination flags between cellular and network managers
 *
 * These need to be accessible by both cellular_man.c and process_network.c
 */
extern bool cellular_request_rescan;    // Network manager requests rescan
extern bool cellular_scan_complete;     // Scan completed
extern bool cellular_ppp_ready;         // Cellular ready for PPP
extern bool network_ready_for_ppp;      // Network manager ready

/**
 * Function prototypes for PPP management
 */
PPPMonitorResult check_ppp_status(void);
void stop_ppp(void);
int start_ppp(void);
bool check_ppp_interface(void);
bool check_ppp_ip(void);
bool test_connectivity(void);

/**
 * Function prototypes for carrier management
 */
bool all_carriers_blacklisted(void);
void display_cellular_operators(void);
bool process_cellular_cli_command(const char* command);

/**
 * Function prototypes for blacklist status
 */
time_t get_blacklist_timeout_remaining(const char* mccmnc);
void get_blacklist_status_string(const char* mccmnc, char* buffer, size_t size);

/**
 * Enhanced logging function prototypes (from cellular_carrier_logging.h)
 */
void log_carrier_details(int index, int total, void* carrier);
void log_signal_test_results(void* carrier);
void log_scan_summary(void* carriers, int count);

#endif /* CELLULAR_MAN_ADDITIONS_H */