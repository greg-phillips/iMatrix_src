/**
 * @file cli_cellular_operators_display.c
 * @brief Enhanced display_cellular_operators function with tested and blacklist status
 * @date 2025-11-22
 * @author Claude Code Implementation
 *
 * This function should be added to cli_cellular_commands.c or integrated
 * with the existing cellular CLI implementation
 */

#include <stdio.h>
#include <string.h>
#include <time.h>
#include "networking/cellular_blacklist.h"
#include "networking/cellular_man.h"
#include "imx_log.h"

/* External references to operator data from cellular_man.c */
extern operator_info_t scan_operators[];
extern int scan_operator_count;
extern int selected_operator;

/**
 * @brief Display all cellular operators with comprehensive status
 *
 * Shows:
 * - Carrier name and MCCMNC
 * - Current/available/forbidden status
 * - Signal strength (if tested)
 * - Whether carrier has been tested
 * - Blacklist status and remaining timeout
 * - Currently selected carrier
 */
void display_cellular_operators(void)
{
    PRINTF("\r\n");
    PRINTF("┌────┬─────────────────────┬─────────┬────────────┬──────┬──────┬──────────┬─────────┬────────────┐\r\n");
    PRINTF("│Idx │ Carrier Name        │ MCCMNC  │ Status     │ Tech │ CSQ  │ RSSI     │ Tested  │ Blacklist  │\r\n");
    PRINTF("├────┼─────────────────────┼─────────┼────────────┼──────┼──────┼──────────┼─────────┼────────────┤\r\n");

    /* Check if we have any operators */
    if (scan_operator_count == 0) {
        PRINTF("│    │ No operators discovered. Run 'cell scan' to search for carriers.                          │\r\n");
        PRINTF("└────┴─────────────────────┴─────────┴────────────┴──────┴──────┴──────────┴─────────┴────────────┘\r\n");
        return;
    }

    /* Status text mappings */
    const char* status_text[] = {
        "Unknown",
        "Available",
        "Current",
        "Forbidden"
    };

    /* Technology text mappings */
    const char* tech_text[] = {
        "GSM",     // 0
        "GSM-C",   // 1
        "UTRAN",   // 2
        "GSM-E",   // 3
        "UTRAN-H", // 4
        "GSM-E-H", // 5
        "UTRAN-H", // 6
        "E-UTRAN", // 7 (LTE)
        "EC-GSM",  // 8
        "E-UTRAN-N" // 9 (5G NSA)
    };

    /* Display each operator */
    for (int i = 0; i < scan_operator_count; i++) {
        operator_info_t *op = &scan_operators[i];

        /* Format basic info */
        char idx_str[8];
        if (i == selected_operator) {
            snprintf(idx_str, sizeof(idx_str), "%d*", i + 1);  // Mark selected with *
        } else {
            snprintf(idx_str, sizeof(idx_str), "%d", i + 1);
        }

        /* Get carrier name (truncate if too long) */
        char name[21];
        strncpy(name, op->operator_name, 20);
        name[20] = '\0';

        /* Format MCCMNC */
        char mccmnc[10];
        snprintf(mccmnc, sizeof(mccmnc), "%06lu", op->numeric);

        /* Get status */
        const char* status = (op->status >= 0 && op->status < 4) ?
                           status_text[op->status] : "Unknown";

        /* Get technology */
        const char* tech = (op->networkAccessTechnology >= 0 && op->networkAccessTechnology <= 9) ?
                         tech_text[op->networkAccessTechnology] : "?";

        /* Format CSQ and RSSI */
        char csq_str[6];
        char rssi_str[10];

        if (op->tested) {
            if (op->signal_strength == 99) {
                strcpy(csq_str, "??");
                strcpy(rssi_str, "Unknown");
            } else if (op->signal_strength == 0) {
                strcpy(csq_str, "0");
                strcpy(rssi_str, "No signal");
            } else {
                snprintf(csq_str, sizeof(csq_str), "%d", op->signal_strength);
                int rssi = -113 + (op->signal_strength * 2);
                snprintf(rssi_str, sizeof(rssi_str), "%d dBm", rssi);
            }
        } else {
            strcpy(csq_str, "-");
            strcpy(rssi_str, "Not tested");
        }

        /* Get tested status */
        const char* tested = op->tested ? "Yes" : "No";

        /* Check if carrier is running/current */
        if (op->status == 2) {
            tested = "Current";  // Currently connected
        }

        /* Get blacklist status */
        char blacklist_str[13];
        if (is_carrier_blacklisted(mccmnc)) {
            /* Get remaining timeout */
            time_t remaining = get_blacklist_timeout(mccmnc);
            if (remaining == -1) {
                strcpy(blacklist_str, "Permanent");
            } else if (remaining > 0) {
                int minutes = remaining / 60;
                int seconds = remaining % 60;
                if (minutes > 0) {
                    snprintf(blacklist_str, sizeof(blacklist_str), "%dm %ds", minutes, seconds);
                } else {
                    snprintf(blacklist_str, sizeof(blacklist_str), "%ds", seconds);
                }
            } else {
                strcpy(blacklist_str, "Expired");
            }
        } else if (op->blacklisted) {
            /* Local blacklist flag in operator struct */
            strcpy(blacklist_str, "Yes");
        } else {
            strcpy(blacklist_str, "-");
        }

        /* Print row */
        PRINTF("│%-4s│ %-19s │ %-7s │ %-10s │ %-4s │ %-4s │ %-8s │ %-7s │ %-10s │\r\n",
               idx_str, name, mccmnc, status, tech, csq_str, rssi_str, tested, blacklist_str);
    }

    PRINTF("└────┴─────────────────────┴─────────┴────────────┴──────┴──────┴──────────┴─────────┴────────────┘\r\n");

    /* Add legend */
    PRINTF("\r\n");
    PRINTF("Legend:\r\n");
    PRINTF("  * = Currently selected carrier\r\n");
    PRINTF("  Status: Available/Current/Forbidden\r\n");
    PRINTF("  Tech: GSM/UTRAN/E-UTRAN(LTE)/E-UTRAN-N(5G)\r\n");
    PRINTF("  CSQ: 0-31 (higher is better), 99=unknown\r\n");
    PRINTF("  RSSI: Received Signal Strength in dBm\r\n");
    PRINTF("  Tested: Whether signal strength has been measured\r\n");
    PRINTF("  Blacklist: Timeout remaining or permanent block\r\n");

    /* Add summary statistics */
    int total = scan_operator_count;
    int tested = 0;
    int blacklisted = 0;
    int available = 0;
    int forbidden = 0;

    for (int i = 0; i < scan_operator_count; i++) {
        operator_info_t *op = &scan_operators[i];
        if (op->tested) tested++;
        if (op->blacklisted || is_carrier_blacklisted_by_index(op->numeric)) blacklisted++;
        if (op->status == 1) available++;
        if (op->status == 3) forbidden++;
    }

    PRINTF("\r\n");
    PRINTF("Summary:\r\n");
    PRINTF("  Total carriers: %d\r\n", total);
    PRINTF("  Tested: %d/%d (%.0f%%)\r\n", tested, total, total > 0 ? (tested * 100.0 / total) : 0);
    PRINTF("  Available: %d\r\n", available);
    PRINTF("  Forbidden: %d\r\n", forbidden);
    PRINTF("  Blacklisted: %d\r\n", blacklisted);

    /* Add recommendations if issues detected */
    if (blacklisted == total && total > 0) {
        PRINTF("\r\n");
        PRINTF("⚠️  WARNING: All carriers are blacklisted!\r\n");
        PRINTF("   Run 'cell clear' to reset blacklist and retry\r\n");
    } else if (tested == 0 && total > 0) {
        PRINTF("\r\n");
        PRINTF("ℹ️  No carriers have been tested yet.\r\n");
        PRINTF("   Run 'cell scan' to test signal strength\r\n");
    } else if (blacklisted > 0) {
        PRINTF("\r\n");
        PRINTF("ℹ️  Some carriers are blacklisted.\r\n");
        PRINTF("   They will be retried when timeout expires or on next scan\r\n");
    }

    /* Show if scan is in progress */
    extern int cellular_state;
    extern const char* cellular_state_names[];

    if (cellular_state >= CELL_SCAN_GET_OPERATORS &&
        cellular_state <= CELL_SCAN_COMPLETE) {
        PRINTF("\r\n");
        PRINTF("🔄 Scan in progress: %s\r\n", cellular_state_names[cellular_state]);
    }

    PRINTF("\r\n");
}

/**
 * @brief Get blacklist timeout for a specific carrier
 *
 * @param mccmnc Carrier MCCMNC code
 * @return Remaining timeout in seconds, -1 for permanent, 0 if expired
 */
time_t get_blacklist_timeout(const char* mccmnc)
{
    /* This function needs to be added to cellular_blacklist.c */
    /* For now, return a placeholder */

    extern blacklist_entry_t blacklist[];
    extern int blacklist_count;

    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklist[i].mccmnc, mccmnc) == 0) {
            if (blacklist[i].permanent) {
                return -1;  // Permanent blacklist
            }

            time_t now = time(NULL);
            time_t expiry = blacklist[i].timestamp + blacklist[i].timeout_ms / 1000;

            if (expiry > now) {
                return expiry - now;  // Remaining seconds
            } else {
                return 0;  // Expired
            }
        }
    }

    return 0;  // Not blacklisted
}

/**
 * @brief Check if a carrier is blacklisted by its numeric ID
 *
 * @param numeric Carrier numeric ID
 * @return true if blacklisted
 */
bool is_carrier_blacklisted_by_index(unsigned long numeric)
{
    char mccmnc[16];
    snprintf(mccmnc, sizeof(mccmnc), "%06lu", numeric);
    return is_carrier_blacklisted(mccmnc);
}

/**
 * @brief Enhanced display with signal quality bars
 *
 * Alternative compact display format
 */
void display_cellular_operators_compact(void)
{
    PRINTF("\n=== Cellular Carriers ===\n\r\n");

    if (scan_operator_count == 0) {
        PRINTF("No carriers found. Run 'cell scan' to search.\r\n");
        return;
    }

    for (int i = 0; i < scan_operator_count; i++) {
        operator_info_t *op = &scan_operators[i];

        /* Selected marker */
        const char* marker = (i == selected_operator) ? "→ " : "  ";

        /* Format MCCMNC */
        char mccmnc[10];
        snprintf(mccmnc, sizeof(mccmnc), "%06lu", op->numeric);

        /* Signal bar visualization */
        char signal_bar[12] = "[----------]";
        if (op->tested && op->signal_strength != 99) {
            int bars = (op->signal_strength * 10) / 31;  // Convert to 0-10 scale
            for (int j = 0; j < bars && j < 10; j++) {
                signal_bar[j + 1] = '█';
            }
        }

        /* Status indicators */
        char status_indicators[32] = "";
        if (op->status == 2) strcat(status_indicators, "[CURRENT] ");
        if (op->status == 3) strcat(status_indicators, "[FORBIDDEN] ");
        if (!op->tested) strcat(status_indicators, "[NOT TESTED] ");
        if (is_carrier_blacklisted(mccmnc)) {
            time_t timeout = get_blacklist_timeout(mccmnc);
            if (timeout == -1) {
                strcat(status_indicators, "[BLACKLISTED-PERM] ");
            } else if (timeout > 0) {
                char bl_str[32];
                snprintf(bl_str, sizeof(bl_str), "[BLACKLISTED-%ldm] ", timeout/60);
                strcat(status_indicators, bl_str);
            }
        }

        /* Print carrier info */
        PRINTF("%s%2d. %-20s (%s) CSQ:%-2d %s %s\r\n",
               marker,
               i + 1,
               op->operator_name,
               mccmnc,
               op->tested ? op->signal_strength : -1,
               op->tested ? signal_bar : "[  NO DATA  ]",
               status_indicators);
    }

    PRINTF("\r\n");
}

/**
 * @brief Display operators in JSON format for scripting
 *
 * Useful for automated monitoring or integration with other tools
 */
void display_cellular_operators_json(void)
{
    PRINTF("{\r\n");
    PRINTF("  \"carriers\": [\r\n");

    for (int i = 0; i < scan_operator_count; i++) {
        operator_info_t *op = &scan_operators[i];
        char mccmnc[10];
        snprintf(mccmnc, sizeof(mccmnc), "%06lu", op->numeric);

        PRINTF("    {\r\n");
        PRINTF("      \"index\": %d,\r\n", i);
        PRINTF("      \"name\": \"%s\",\r\n", op->operator_name);
        PRINTF("      \"mccmnc\": \"%s\",\r\n", mccmnc);
        PRINTF("      \"status\": %d,\r\n", op->status);
        PRINTF("      \"technology\": %d,\r\n", op->networkAccessTechnology);
        PRINTF("      \"tested\": %s,\r\n", op->tested ? "true" : "false");
        PRINTF("      \"signal_strength\": %d,\r\n", op->signal_strength);
        PRINTF("      \"rssi_dbm\": %d,\r\n", op->tested ? -113 + (op->signal_strength * 2) : 0);
        PRINTF("      \"blacklisted\": %s,\r\n", is_carrier_blacklisted(mccmnc) ? "true" : "false");
        PRINTF("      \"selected\": %s\r\n", (i == selected_operator) ? "true" : "false");
        PRINTF("    }%s\r\n", (i < scan_operator_count - 1) ? "," : "");
    }

    PRINTF("  ],\r\n");
    PRINTF("  \"count\": %d,\r\n", scan_operator_count);
    PRINTF("  \"selected_index\": %d\r\n", selected_operator);
    PRINTF("}\r\n");
}