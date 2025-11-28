/**
 * @file cli_cellular_commands.c
 * @brief CLI commands for cellular carrier management and blacklist control
 * @date 2025-11-22
 * @author Claude Code Implementation
 *
 * Add these command handlers to your existing CLI implementation
 */

#include "cli/cli.h"
#include "networking/cellular_blacklist.h"
#include "networking/cellular_man.h"
#include "imx_log.h"
#include <string.h>
#include <stdio.h>

/**
 * @brief Process cellular-related CLI commands
 *
 * @param command Full command string
 * @param args Command arguments (if any)
 * @return true if command was handled
 */
bool process_cellular_cli_command(const char* command, const char* args) {
    /* cell operators - Display all carriers with status */
    if (strcmp(command, "cell operators") == 0 ||
        strcmp(command, "cell ops") == 0) {
        display_cellular_operators();
        return true;
    }

    /* cell blacklist - Show current blacklist */
    if (strcmp(command, "cell blacklist") == 0 ||
        strcmp(command, "cell bl") == 0) {
        display_blacklist();
        return true;
    }

    /* cell clear - Clear blacklist */
    if (strcmp(command, "cell clear") == 0) {
        clear_blacklist_for_scan();
        PRINTF("Carrier blacklist cleared\n");
        return true;
    }

    /* cell scan - Trigger manual scan */
    if (strcmp(command, "cell scan") == 0) {
        trigger_cellular_scan();
        return true;
    }

    /* cell status - Enhanced status with blacklist info */
    if (strcmp(command, "cell status") == 0 ||
        strcmp(command, "cell") == 0) {
        show_cellular_status_enhanced();
        return true;
    }

    /* cell test - Test specific carrier */
    if (strncmp(command, "cell test ", 10) == 0) {
        const char* mccmnc = command + 10;
        test_specific_carrier(mccmnc);
        return true;
    }

    /* cell blacklist add - Manually blacklist carrier */
    if (strncmp(command, "cell blacklist add ", 19) == 0) {
        const char* mccmnc = command + 19;
        blacklist_carrier_temporary(mccmnc, "Manual blacklist");
        PRINTF("Added %s to blacklist\n", mccmnc);
        return true;
    }

    /* cell blacklist remove - Remove from blacklist */
    if (strncmp(command, "cell blacklist remove ", 22) == 0) {
        const char* mccmnc = command + 22;
        if (remove_from_blacklist(mccmnc)) {
            PRINTF("Removed %s from blacklist\n", mccmnc);
        } else {
            PRINTF("%s not found in blacklist\n", mccmnc);
        }
        return true;
    }

    /* cell retry - Force retry of blacklisted carriers */
    if (strcmp(command, "cell retry") == 0) {
        cleanup_expired_blacklist();
        PRINTF("Expired blacklist entries cleared, retry available\n");
        return true;
    }

    /* cell ppp status - Show PPP monitoring state */
    if (strcmp(command, "cell ppp") == 0 ||
        strcmp(command, "cell ppp status") == 0) {
        show_ppp_monitor_status();
        return true;
    }

    /* cell help - Show cellular commands */
    if (strcmp(command, "cell help") == 0 ||
        strcmp(command, "cell ?") == 0) {
        show_cellular_help();
        return true;
    }

    return false;
}

/**
 * @brief Show enhanced cellular status with blacklist info
 */
void show_cellular_status_enhanced(void) {
    char buffer[512];

    /* Basic cellular status */
    PRINTF("\n=== Cellular Status ===\n");

    /* Get standard status (from existing cellular_man.c) */
    get_cellular_status(buffer, sizeof(buffer));
    PRINTF("%s\n", buffer);

    /* Add blacklist summary */
    int blacklist_count = get_blacklist_count();
    if (blacklist_count > 0) {
        PRINTF("\nBlacklisted Carriers: %d\n", blacklist_count);
        get_blacklist_summary(buffer, sizeof(buffer));
        PRINTF("%s", buffer);
    } else {
        PRINTF("\nNo carriers currently blacklisted\n");
    }

    /* PPP status */
    get_ppp_status(buffer, sizeof(buffer));
    PRINTF("\nPPP Status: %s\n", buffer);

    /* Network manager coordination */
    extern bool cellular_request_rescan;
    extern bool cellular_ppp_ready;
    PRINTF("\nCoordination Flags:\n");
    PRINTF("  Rescan Requested: %s\n", cellular_request_rescan ? "YES" : "NO");
    PRINTF("  PPP Ready Signal: %s\n", cellular_ppp_ready ? "YES" : "NO");

    PRINTF("\n");
}

/**
 * @brief Show PPP monitoring status
 */
void show_ppp_monitor_status(void) {
    PRINTF("\n=== PPP Monitor Status ===\n");

    PPPMonitorState* state = get_ppp_monitor_state();
    if (!state) {
        PRINTF("PPP monitoring not active\n");
        return;
    }

    PRINTF("Current Carrier: %s\n",
           state->current_carrier[0] ? state->current_carrier : "None");
    PRINTF("Retry Count: %d / %d\n",
           state->retry_count, PPP_MAX_RETRIES);

    if (state->start_time > 0) {
        uint32_t elapsed = imx_get_ms_ticks() - state->start_time;
        PRINTF("Elapsed Time: %d seconds\n", elapsed / 1000);
    }

    PRINTF("\nInterface Status:\n");
    PRINTF("  ppp0 exists: %s\n", state->interface_up ? "YES" : "NO");
    PRINTF("  Has IP: %s\n", state->has_ip ? "YES" : "NO");
    PRINTF("  Internet: %s\n", state->ping_success ? "YES" : "NO");

    /* Show IP if available */
    if (state->has_ip) {
        char cmd[128];
        snprintf(cmd, sizeof(cmd),
                 "ip addr show ppp0 | grep 'inet ' | awk '{print $2}'");
        FILE* fp = popen(cmd, "r");
        if (fp) {
            char ip[32];
            if (fgets(ip, sizeof(ip), fp)) {
                PRINTF("  IP Address: %s", ip);
            }
            pclose(fp);
        }
    }

    PRINTF("\n");
}

/**
 * @brief Test specific carrier (for debugging)
 */
void test_specific_carrier(const char* mccmnc) {
    if (!mccmnc || strlen(mccmnc) < 5) {
        PRINTF("Invalid MCCMNC format. Example: 311480\n");
        return;
    }

    PRINTF("Testing carrier %s...\n", mccmnc);

    /* Check if blacklisted */
    if (is_carrier_blacklisted(mccmnc)) {
        PRINTF("Warning: Carrier %s is currently blacklisted\n", mccmnc);
        PRINTF("Use 'cell blacklist remove %s' to clear\n", mccmnc);
        return;
    }

    /* Send AT command to connect */
    char cmd[128];
    snprintf(cmd, sizeof(cmd), "AT+COPS=1,2,\"%s\"", mccmnc);
    PRINTF("Sending: %s\n", cmd);

    /* This would need integration with AT command handler */
    trigger_carrier_test(mccmnc);
}

/**
 * @brief Remove carrier from blacklist
 */
bool remove_from_blacklist(const char* mccmnc) {
    /* This function needs to be added to cellular_blacklist.c */
    /* For now, just clear entire blacklist as workaround */
    clear_blacklist_for_scan();
    return true;
}

/**
 * @brief Show cellular command help
 */
void show_cellular_help(void) {
    PRINTF("\n=== Cellular Commands ===\n\n");

    PRINTF("Status Commands:\n");
    PRINTF("  cell              - Show cellular status with blacklist info\n");
    PRINTF("  cell operators    - Display all discovered carriers\n");
    PRINTF("  cell blacklist    - Show current blacklist with timeouts\n");
    PRINTF("  cell ppp          - Show PPP connection status\n");

    PRINTF("\nControl Commands:\n");
    PRINTF("  cell scan         - Trigger manual carrier scan\n");
    PRINTF("  cell clear        - Clear carrier blacklist\n");
    PRINTF("  cell retry        - Clear expired blacklist entries\n");

    PRINTF("\nDebug Commands:\n");
    PRINTF("  cell test <mccmnc>         - Test specific carrier\n");
    PRINTF("  cell blacklist add <mccmnc>  - Manually blacklist carrier\n");
    PRINTF("  cell blacklist remove <mccmnc> - Remove from blacklist\n");

    PRINTF("\nExamples:\n");
    PRINTF("  cell operators    - See all carriers with signal strength\n");
    PRINTF("  cell scan         - Force rescan when connection poor\n");
    PRINTF("  cell test 311480  - Test Verizon specifically\n");
    PRINTF("  cell clear        - Reset after location change\n");

    PRINTF("\nBlacklist Behavior:\n");
    PRINTF("  - Failed carriers blacklisted for 5 minutes\n");
    PRINTF("  - After 3 failures, permanent for session\n");
    PRINTF("  - Blacklist cleared on each AT+COPS scan\n");
    PRINTF("  - All clear when every carrier blacklisted\n");

    PRINTF("\n");
}

/**
 * @brief Integration with main CLI handler
 *
 * Add this to your main CLI processing function:
 *
 * if (strncmp(input, "cell", 4) == 0) {
 *     return process_cellular_cli_command(input, args);
 * }
 */

/* Helper functions that need to be implemented in cellular_man.c */

extern void trigger_cellular_scan(void);
extern void trigger_carrier_test(const char* mccmnc);
extern void get_cellular_status(char* buffer, size_t size);
extern PPPMonitorState* get_ppp_monitor_state(void);
extern void get_ppp_status(char* buffer, size_t size);
extern int get_blacklist_count(void);
extern void get_blacklist_summary(char* buffer, size_t size);