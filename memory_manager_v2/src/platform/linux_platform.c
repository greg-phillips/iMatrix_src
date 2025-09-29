/**
 * @file linux_platform.c
 * @brief LINUX Platform Implementation
 *
 * Platform-specific implementation for LINUX environment
 */

#include "platform_config.h"
#include <stdio.h>
#include <stdlib.h>

/******************************************************
 *              Platform Capabilities
 ******************************************************/

static const platform_capabilities_t linux_capabilities = {
    .platform_name = "LINUX",
    .max_sectors = MAX_SECTORS,
    .sector_size = SECTOR_SIZE,
    .memory_budget = MEMORY_FOOTPRINT_BUDGET,
    .disk_overflow_supported = true,
    .extended_validation_enabled = true,
    .file_operations_available = true,
    .max_records_per_sector = MAX_RECORDS_PER_SECTOR,
    .max_event_records_per_sector = MAX_EVENT_RECORDS_PER_SECTOR
};

/******************************************************
 *            Function Implementations
 ******************************************************/

const platform_capabilities_t *get_platform_capabilities(void)
{
    return &linux_capabilities;
}

memory_error_t init_platform_systems(void)
{
    printf("Initializing LINUX platform systems...\n");
    printf("  Extended sector addressing: ENABLED\n");
    printf("  Disk overflow support: ENABLED\n");
    printf("  Memory budget: %u KB\n", MEMORY_FOOTPRINT_BUDGET / 1024);
    printf("  File operations: AVAILABLE\n");
    printf("LINUX platform initialization: SUCCESS\n");

    return MEMORY_SUCCESS;
}

bool validate_platform_requirements(void)
{
    printf("Validating LINUX platform requirements...\n");

    // Check memory availability
    uint32_t available_memory = MEMORY_FOOTPRINT_BUDGET;
    if (available_memory < (2 * 1024)) {  // 2KB minimum for test environment
        printf("ERROR: Insufficient memory (%u KB) for LINUX platform\n", available_memory / 1024);
        return false;
    }

    // Check sector support
    if (MAX_SECTORS < 1000) {
        printf("ERROR: Insufficient sector support (%u) for LINUX platform\n", MAX_SECTORS);
        return false;
    }

    printf("LINUX platform requirements: VALIDATED\n");
    return true;
}

uint32_t get_platform_memory_limit(void)
{
    return MEMORY_FOOTPRINT_BUDGET;
}

bool platform_supports_disk_overflow(void)
{
    return DISK_OVERFLOW_SUPPORT;
}

bool platform_supports_extended_validation(void)
{
    return EXTENDED_VALIDATION;
}

bool platform_supports_file_operations(void)
{
    return FILE_OPERATIONS_SUPPORT;
}

// Platform-specific logging (will integrate with real iMatrix functions)
void platform_log_info(const char *message)
{
    printf("[LINUX-INFO] %s\n", message);
}

void platform_log_error(const char *message)
{
    printf("[LINUX-ERROR] %s\n", message);
}

void platform_log_debug(const char *message)
{
    printf("[LINUX-DEBUG] %s\n", message);
}

// Placeholder implementations for sector allocation
platform_sector_t platform_allocate_sector(void)
{
    static platform_sector_t next_sector = 1;
    if (next_sector >= MAX_SECTORS) {
        return INVALID_SECTOR;
    }
    return next_sector++;
}

memory_error_t platform_free_sector(platform_sector_t sector)
{
    if (sector == INVALID_SECTOR || sector >= MAX_SECTORS) {
        return MEMORY_ERROR_INVALID_PARAMETER;
    }
    printf("[LINUX] Freed sector: %u\n", sector);
    return MEMORY_SUCCESS;
}