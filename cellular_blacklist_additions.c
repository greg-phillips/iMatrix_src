/**
 * @file cellular_blacklist_additions.c
 * @brief Additional functions for cellular_blacklist.c to support operator display
 * @date 2025-11-22
 * @author Claude Code Implementation
 *
 * Add these functions to cellular_blacklist.c
 */

#include "cellular_blacklist.h"
#include <time.h>
#include <string.h>

/**
 * @brief Get remaining timeout for a blacklisted carrier
 *
 * @param mccmnc The MCCMNC code to check
 * @return Remaining timeout in seconds, -1 if permanent, 0 if not blacklisted or expired
 */
time_t get_blacklist_timeout_remaining(const char* mccmnc)
{
    if (!mccmnc || strlen(mccmnc) == 0) {
        return 0;
    }

    /* Search blacklist for this carrier */
    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklist[i].mccmnc, mccmnc) == 0) {
            /* Check if permanent */
            if (blacklist[i].permanent) {
                return -1;  // Permanent blacklist
            }

            /* Calculate remaining time */
            time_t now = get_timestamp();
            time_t expiry = blacklist[i].timestamp + blacklist[i].timeout_ms;

            if (expiry > now) {
                /* Convert from milliseconds to seconds */
                return (expiry - now) / 1000;
            } else {
                /* Expired */
                return 0;
            }
        }
    }

    /* Not in blacklist */
    return 0;
}

/**
 * @brief Get pointer to blacklist entry for a carrier
 *
 * @param mccmnc The MCCMNC code to find
 * @return Pointer to blacklist entry or NULL if not found
 */
blacklist_entry_t* get_blacklist_entry(const char* mccmnc)
{
    if (!mccmnc || strlen(mccmnc) == 0) {
        return NULL;
    }

    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklist[i].mccmnc, mccmnc) == 0) {
            return &blacklist[i];
        }
    }

    return NULL;
}

/**
 * @brief Display detailed blacklist information
 *
 * Shows all blacklisted carriers with reasons and timeouts
 */
void display_blacklist(void)
{
    PRINTF("\n");
    PRINTF("=== Carrier Blacklist ===\n");
    PRINTF("\n");

    if (blacklist_count == 0) {
        PRINTF("No carriers currently blacklisted.\n");
        PRINTF("\n");
        return;
    }

    PRINTF("MCCMNC  | Reason              | Status    | Timeout    | Failures\n");
    PRINTF("--------+---------------------+-----------+------------+---------\n");

    time_t now = get_timestamp();

    for (int i = 0; i < blacklist_count; i++) {
        blacklist_entry_t *entry = &blacklist[i];

        /* Format timeout */
        char timeout_str[20];
        if (entry->permanent) {
            strcpy(timeout_str, "Permanent");
        } else {
            time_t remaining = (entry->timestamp + entry->timeout_ms - now) / 1000;
            if (remaining > 0) {
                if (remaining > 3600) {
                    snprintf(timeout_str, sizeof(timeout_str), "%ld hours", remaining / 3600);
                } else if (remaining > 60) {
                    snprintf(timeout_str, sizeof(timeout_str), "%ld min %ld sec",
                            remaining / 60, remaining % 60);
                } else {
                    snprintf(timeout_str, sizeof(timeout_str), "%ld seconds", remaining);
                }
            } else {
                strcpy(timeout_str, "Expired");
            }
        }

        /* Format reason (truncate if needed) */
        char reason[21];
        strncpy(reason, entry->reason, 20);
        reason[20] = '\0';

        /* Status */
        const char* status;
        if (entry->permanent) {
            status = "Permanent";
        } else if ((entry->timestamp + entry->timeout_ms) <= now) {
            status = "Expired";
        } else {
            status = "Active";
        }

        PRINTF("%-7s | %-19s | %-9s | %-10s | %d\n",
               entry->mccmnc, reason, status, timeout_str, entry->failure_count);
    }

    PRINTF("\n");

    /* Add statistics */
    int active = 0, expired = 0, permanent = 0;
    for (int i = 0; i < blacklist_count; i++) {
        if (blacklist[i].permanent) {
            permanent++;
        } else if ((blacklist[i].timestamp + blacklist[i].timeout_ms) > now) {
            active++;
        } else {
            expired++;
        }
    }

    PRINTF("Statistics:\n");
    PRINTF("  Total entries: %d/%d\n", blacklist_count, MAX_BLACKLIST_SIZE);
    PRINTF("  Active: %d\n", active);
    PRINTF("  Expired: %d (will be cleared on next operation)\n", expired);
    PRINTF("  Permanent: %d (for this session)\n", permanent);

    if (expired > 0) {
        PRINTF("\nRun 'cell retry' to clear expired entries and retry those carriers.\n");
    }

    if (blacklist_count == MAX_BLACKLIST_SIZE) {
        PRINTF("\n⚠️  Blacklist is full. Oldest entries will be replaced.\n");
    }

    PRINTF("\n");
}

/**
 * @brief Get formatted blacklist summary for status display
 *
 * @param buffer Output buffer
 * @param size Buffer size
 * @return Number of blacklisted carriers
 */
int get_blacklist_summary(char* buffer, size_t size)
{
    if (!buffer || size == 0) {
        return blacklist_count;
    }

    buffer[0] = '\0';

    if (blacklist_count == 0) {
        snprintf(buffer, size, "No blacklisted carriers\n");
        return 0;
    }

    int active = 0;
    time_t now = get_timestamp();
    size_t offset = 0;

    for (int i = 0; i < blacklist_count && offset < size - 1; i++) {
        if (blacklist[i].permanent ||
            (blacklist[i].timestamp + blacklist[i].timeout_ms) > now) {
            active++;

            /* Add carrier to summary */
            int written = snprintf(buffer + offset, size - offset,
                                  "  %s: %s%s\n",
                                  blacklist[i].mccmnc,
                                  blacklist[i].reason,
                                  blacklist[i].permanent ? " [PERMANENT]" : "");

            if (written > 0) {
                offset += written;
            }
        }
    }

    return active;
}

/**
 * @brief Remove a specific carrier from blacklist
 *
 * @param mccmnc The MCCMNC to remove
 * @return true if removed, false if not found
 */
bool remove_from_blacklist(const char* mccmnc)
{
    if (!mccmnc || strlen(mccmnc) == 0) {
        return false;
    }

    /* Find the carrier in blacklist */
    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklist[i].mccmnc, mccmnc) == 0) {
            /* Remove by shifting remaining entries */
            for (int j = i; j < blacklist_count - 1; j++) {
                blacklist[j] = blacklist[j + 1];
            }
            blacklist_count--;

            PRINTF("[Cellular Blacklist] Removed %s from blacklist\n", mccmnc);
            return true;
        }
    }

    return false;
}

/**
 * @brief Check if a specific carrier should be retried
 *
 * Checks if enough time has passed since last failure
 *
 * @param mccmnc The MCCMNC to check
 * @return true if carrier can be retried
 */
bool should_retry_carrier(const char* mccmnc)
{
    blacklist_entry_t* entry = get_blacklist_entry(mccmnc);

    if (!entry) {
        /* Not blacklisted, can retry */
        return true;
    }

    if (entry->permanent) {
        /* Permanent blacklist, don't retry */
        return false;
    }

    /* Check if timeout has expired */
    time_t now = get_timestamp();
    return (entry->timestamp + entry->timeout_ms) <= now;
}

/**
 * @brief Get a formatted string describing blacklist status
 *
 * @param mccmnc The MCCMNC to check
 * @param buffer Output buffer
 * @param size Buffer size
 */
void get_blacklist_status_string(const char* mccmnc, char* buffer, size_t size)
{
    if (!buffer || size == 0) {
        return;
    }

    blacklist_entry_t* entry = get_blacklist_entry(mccmnc);

    if (!entry) {
        snprintf(buffer, size, "Not blacklisted");
        return;
    }

    if (entry->permanent) {
        snprintf(buffer, size, "Permanently blacklisted: %s", entry->reason);
        return;
    }

    time_t now = get_timestamp();
    time_t remaining = (entry->timestamp + entry->timeout_ms - now) / 1000;

    if (remaining > 0) {
        snprintf(buffer, size, "Blacklisted for %ld seconds: %s",
                remaining, entry->reason);
    } else {
        snprintf(buffer, size, "Blacklist expired, pending cleanup");
    }
}