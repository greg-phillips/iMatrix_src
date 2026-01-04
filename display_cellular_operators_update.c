/**
 * @file display_cellular_operators_update.c
 * @brief Updated display_cellular_operators function for existing structure
 * @date 2025-11-22
 * @author Claude Code Implementation
 *
 * This implementation works with the existing operator_info_t structure
 * Add this function to cli_cellular_commands.c or cellular_man.c
 */

#include <stdio.h>
#include <string.h>
#include <time.h>
#include "networking/cellular_blacklist.h"
#include "imx_log.h"

/* External references from cellular_man.c */
extern operator_info_t scan_operators[];
extern int scan_operator_count;
extern Operator_t operators[];
extern int operator_count;
extern int selected_operator;

/**
 * @brief Display cellular operators with tested and blacklist status
 *
 * This version works with the existing operator_info_t structure:
 * - operator_id: Numeric ID
 * - operator_name: Carrier name
 * - signal_strength: CSQ value
 * - blacklisted: Local blacklist flag
 * - tested: Whether tested
 */
void display_cellular_operators(void)
{
    PRINTF("\r\n");
    PRINTF("================================================================================\r\n");
    PRINTF(" Cellular Operators Status\r\n");
    PRINTF("================================================================================\r\n");
    PRINTF("Idx | Carrier Name         | MCCMNC  | CSQ  | RSSI     | Tested | Blacklist\r\n");
    PRINTF("----+----------------------+---------+------+----------+--------+-------------\r\n");

    /* First check scan_operators if available (from recent scan) */
    if (scan_operator_count > 0) {
        PRINTF("Recent Scan Results:\r\n");
        PRINTF("----+----------------------+---------+------+----------+--------+-------------\r\n");

        for (int i = 0; i < scan_operator_count; i++) {
            operator_info_t *op = &scan_operators[i];

            /* Index with selection marker */
            char idx_str[8];
            snprintf(idx_str, sizeof(idx_str), "%2d%s", i + 1,
                    (i == scan_current_index) ? "*" : " ");

            /* Carrier name (truncate if needed) */
            char name[22];
            strncpy(name, op->operator_name, 21);
            name[21] = '\0';

            /* MCCMNC from operator_id */
            char mccmnc[10] = "-";
            if (strlen(op->operator_id) > 0) {
                strncpy(mccmnc, op->operator_id, 9);
                mccmnc[9] = '\0';
            }

            /* CSQ and RSSI */
            char csq_str[6];
            char rssi_str[11];

            if (op->tested) {
                if (op->signal_strength >= 0 && op->signal_strength <= 31) {
                    snprintf(csq_str, sizeof(csq_str), "%2d", op->signal_strength);
                    int rssi = -113 + (op->signal_strength * 2);
                    snprintf(rssi_str, sizeof(rssi_str), "%d dBm", rssi);
                } else if (op->signal_strength == 99) {
                    strcpy(csq_str, "??");
                    strcpy(rssi_str, "Unknown");
                } else {
                    strcpy(csq_str, "-");
                    strcpy(rssi_str, "No signal");
                }
            } else {
                strcpy(csq_str, "-");
                strcpy(rssi_str, "Not tested");
            }

            /* Tested status */
            const char* tested_str = op->tested ? "Yes" : "No";

            /* Blacklist status - check both local flag and global blacklist */
            char blacklist_str[14];
            if (op->blacklisted) {
                strcpy(blacklist_str, "Local");
            } else if (is_carrier_blacklisted(op->operator_id)) {
                /* Get timeout if available */
                blacklist_entry_t* entry = get_blacklist_entry(op->operator_id);
                if (entry && entry->permanent) {
                    strcpy(blacklist_str, "Permanent");
                } else if (entry) {
                    time_t now = time(NULL) * 1000;  // Convert to milliseconds
                    time_t remaining = (entry->timestamp + entry->timeout_ms - now) / 1000;
                    if (remaining > 0) {
                        if (remaining > 60) {
                            snprintf(blacklist_str, sizeof(blacklist_str), "%ldm", remaining / 60);
                        } else {
                            snprintf(blacklist_str, sizeof(blacklist_str), "%lds", remaining);
                        }
                    } else {
                        strcpy(blacklist_str, "Expiring");
                    }
                } else {
                    strcpy(blacklist_str, "Yes");
                }
            } else {
                strcpy(blacklist_str, "-");
            }

            /* Print row */
            PRINTF("%s | %-20s | %-7s | %4s | %-8s | %-6s | %s\r\n",
                   idx_str, name, mccmnc, csq_str, rssi_str, tested_str, blacklist_str);
        }
    }

    /* Also show operators from last successful connection if different */
    if (operator_count > 0) {
        PRINTF("\r\n");
        PRINTF("Available Operators (from last AT+COPS query):\r\n");
        PRINTF("----+----------------------+---------+------+----------+--------+-------------\r\n");

        for (int i = 0; i < operator_count; i++) {
            Operator_t *op = &operators[i];

            /* Index with selection marker */
            char idx_str[8];
            snprintf(idx_str, sizeof(idx_str), "%2d%s", i + 1,
                    (i == selected_operator) ? ">" : " ");

            /* Carrier name */
            char name[22];
            strncpy(name, op->longAlphanumeric, 21);
            name[21] = '\0';

            /* MCCMNC */
            char mccmnc[10];
            snprintf(mccmnc, sizeof(mccmnc), "%06u", op->numeric);

            /* Check if this was tested in scan */
            bool was_tested = false;
            int signal_strength = -1;

            for (int j = 0; j < scan_operator_count; j++) {
                if (strcmp(scan_operators[j].operator_id, mccmnc) == 0) {
                    was_tested = scan_operators[j].tested;
                    signal_strength = scan_operators[j].signal_strength;
                    break;
                }
            }

            /* CSQ and RSSI */
            char csq_str[6];
            char rssi_str[11];

            if (was_tested && signal_strength >= 0) {
                snprintf(csq_str, sizeof(csq_str), "%2d", signal_strength);
                int rssi = -113 + (signal_strength * 2);
                snprintf(rssi_str, sizeof(rssi_str), "%d dBm", rssi);
            } else if (op->rssi != 0) {
                /* Use stored RSSI if available */
                int csq = (op->rssi + 113) / 2;
                snprintf(csq_str, sizeof(csq_str), "%2d", csq);
                snprintf(rssi_str, sizeof(rssi_str), "%d dBm", op->rssi);
            } else {
                strcpy(csq_str, "-");
                strcpy(rssi_str, "Not tested");
            }

            /* Status */
            const char* status_str = "";
            switch (op->status) {
                case 0: status_str = "Unknown"; break;
                case 1: status_str = "Available"; break;
                case 2: status_str = "Current"; break;
                case 3: status_str = "Forbidden"; break;
            }

            /* Tested status */
            const char* tested_str = was_tested ? "Yes" : "No";

            /* Blacklist status */
            char blacklist_str[14];
            if (op->bad_operator) {
                strcpy(blacklist_str, "Bad");
            } else if (is_carrier_blacklisted(mccmnc)) {
                blacklist_entry_t* entry = get_blacklist_entry(mccmnc);
                if (entry && entry->permanent) {
                    strcpy(blacklist_str, "Permanent");
                } else {
                    strcpy(blacklist_str, "Temporary");
                }
            } else {
                strcpy(blacklist_str, "-");
            }

            /* Print row */
            PRINTF("%s | %-20s | %-7s | %4s | %-8s | %-6s | %s %s\r\n",
                   idx_str, name, mccmnc, csq_str, rssi_str, tested_str,
                   blacklist_str, status_str);
        }
    }

    /* If no operators at all */
    if (scan_operator_count == 0 && operator_count == 0) {
        PRINTF("No operators found. Run 'cell scan' to search for carriers.\r\n");
    }

    PRINTF("================================================================================\r\n");

    /* Add summary */
    PRINTF("\nSummary:\r\n");

    if (scan_operator_count > 0) {
        int tested = 0, blacklisted = 0;
        int best_signal = -1;
        char best_carrier[64] = "None";

        for (int i = 0; i < scan_operator_count; i++) {
            if (scan_operators[i].tested) tested++;
            if (scan_operators[i].blacklisted ||
                is_carrier_blacklisted(scan_operators[i].operator_id)) blacklisted++;

            if (scan_operators[i].tested &&
                scan_operators[i].signal_strength > best_signal &&
                scan_operators[i].signal_strength != 99) {
                best_signal = scan_operators[i].signal_strength;
                strncpy(best_carrier, scan_operators[i].operator_name, 63);
            }
        }

        PRINTF("  Carriers found: %d\r\n", scan_operator_count);
        PRINTF("  Tested: %d/%d\r\n", tested, scan_operator_count);
        PRINTF("  Blacklisted: %d\r\n", blacklisted);

        if (best_signal > 0) {
            PRINTF("  Best signal: %s (CSQ:%d)\r\n", best_carrier, best_signal);
        }

        /* Warnings */
        if (blacklisted == scan_operator_count && scan_operator_count > 0) {
            PRINTF("\n⚠️  WARNING: All carriers are blacklisted!\r\n");
            PRINTF("   Run 'cell clear' to reset blacklist\r\n");
        } else if (tested == 0 && scan_operator_count > 0) {
            PRINTF("\n⚠️  No carriers have been tested\r\n");
            PRINTF("   Run 'cell scan' to test signal strength\r\n");
        }
    }

    /* Legend */
    PRINTF("\nLegend:\r\n");
    PRINTF("  * = Currently testing this carrier\r\n");
    PRINTF("  > = Currently selected carrier\r\n");
    PRINTF("  CSQ: 0-31 (higher is better), 99=unknown\r\n");
    PRINTF("  Blacklist times: m=minutes, s=seconds\r\n");
    PRINTF("\nCommands:\r\n");
    PRINTF("  cell scan  - Test all carriers\r\n");
    PRINTF("  cell clear - Clear blacklist\r\n");
    PRINTF("  cell test <mccmnc> - Test specific carrier\r\n");

    PRINTF("\r\n");
}

/**
 * @brief Simple version for compact display
 */
void display_cellular_operators_simple(void)
{
    PRINTF("\nCarrier Status:\r\n");

    if (scan_operator_count == 0) {
        PRINTF("  No scan data available. Run 'cell scan'\r\n");
        return;
    }

    for (int i = 0; i < scan_operator_count; i++) {
        operator_info_t *op = &scan_operators[i];

        /* Signal strength bar */
        char bar[11] = "----------";
        if (op->tested && op->signal_strength >= 0 && op->signal_strength <= 31) {
            int filled = (op->signal_strength * 10) / 31;
            for (int j = 0; j < filled; j++) {
                bar[j] = '#';
            }
        }

        /* Status flags */
        char flags[64] = "";
        if (!op->tested) strcat(flags, "[NOT TESTED] ");
        if (op->blacklisted) strcat(flags, "[BLACKLISTED] ");
        if (is_carrier_blacklisted(op->operator_id)) strcat(flags, "[BLOCKED] ");

        PRINTF("  %2d. %-20s CSQ:%2d [%s] %s\r\n",
               i + 1,
               op->operator_name,
               op->tested ? op->signal_strength : -1,
               bar,
               flags);
    }

    PRINTF("\r\n");
}

/* Helper function to get blacklist entry (needs to be added to cellular_blacklist.c) */
blacklist_entry_t* get_blacklist_entry(const char* mccmnc)
{
    extern blacklist_entry_t blacklist[];
    extern int blacklist_count;

    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklist[i].mccmnc, mccmnc) == 0) {
            return &blacklist[i];
        }
    }
    return NULL;
}