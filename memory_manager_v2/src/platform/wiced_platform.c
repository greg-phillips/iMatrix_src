/**
 * @file wiced_platform.c
 * @brief WICED Platform Implementation
 *
 * Platform-specific implementation for WICED embedded environment
 */

#include "platform_config.h"
#include <stdio.h>
#include <stdlib.h>

/******************************************************
 *              Platform Capabilities
 ******************************************************/

static const platform_capabilities_t wiced_capabilities = {
    .platform_name = "WICED",
    .max_sectors = MAX_SECTORS,
    .sector_size = SECTOR_SIZE,
    .memory_budget = MEMORY_FOOTPRINT_BUDGET,
    .disk_overflow_supported = false,
    .extended_validation_enabled = false,
    .file_operations_available = false,
    .max_records_per_sector = MAX_RECORDS_PER_SECTOR,
    .max_event_records_per_sector = MAX_EVENT_RECORDS_PER_SECTOR
};

/******************************************************
 *            Function Implementations
 ******************************************************/

const platform_capabilities_t *get_platform_capabilities(void)
{
    return &wiced_capabilities;
}

memory_error_t init_platform_systems(void)
{
    printf("Initializing WICED platform systems...\n");
    printf("  Compact sector addressing: ENABLED\n");
    printf("  Memory budget: %u KB\n", MEMORY_FOOTPRINT_BUDGET / 1024);
    printf("  Minimal validation: ENABLED\n");
    printf("  File operations: NOT AVAILABLE\n");
    printf("WICED platform initialization: SUCCESS\n");

    return MEMORY_SUCCESS;
}

bool validate_platform_requirements(void)
{
    printf("Validating WICED platform requirements...\n");

    // Check memory constraints
    uint32_t available_memory = MEMORY_FOOTPRINT_BUDGET;
    if (available_memory > (32 * 1024)) {
        printf("WARNING: Memory budget (%u KB) exceeds typical WICED constraints\n",
               available_memory / 1024);
    }

    // Check sector limits
    if (MAX_SECTORS > 2048) {
        printf("ERROR: Sector count (%u) exceeds WICED 16-bit addressing\n", MAX_SECTORS);
        return false;
    }

    printf("WICED platform requirements: VALIDATED\n");
    return true;
}

uint32_t get_platform_memory_limit(void)
{
    return MEMORY_FOOTPRINT_BUDGET;
}

bool platform_supports_disk_overflow(void)
{
    return false; // WICED has no disk
}

bool platform_supports_extended_validation(void)
{
    return false; // Minimal validation only
}

bool platform_supports_file_operations(void)
{
    return false; // No file I/O on WICED
}

// Platform-specific logging for WICED
void platform_log_info(const char *message)
{
    printf("[WICED-INFO] %s\n", message);
}

void platform_log_error(const char *message)
{
    printf("[WICED-ERROR] %s\n", message);
}

void platform_log_debug(const char *message)
{
    // Debug logging may be disabled on WICED for performance
    #ifdef DEBUG
    printf("[WICED-DEBUG] %s\n", message);
    #else
    (void)message; // Suppress unused parameter warning
    #endif
}

// WICED-specific sector allocation (circular buffer model)
platform_sector_t platform_allocate_sector(void)
{
    static platform_sector_t next_sector = 1;
    if (next_sector >= MAX_SECTORS) {
        next_sector = 1; // Wraparound for circular allocation
    }
    return next_sector++;
}

memory_error_t platform_free_sector(platform_sector_t sector)
{
    if (sector == INVALID_SECTOR || sector >= MAX_SECTORS) {
        return MEMORY_ERROR_INVALID_PARAMETER;
    }
    // WICED typically doesn't log routine operations for performance
    return MEMORY_SUCCESS;
}