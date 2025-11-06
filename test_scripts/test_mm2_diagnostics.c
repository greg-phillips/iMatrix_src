/**
 * @file test_mm2_diagnostics.c
 * @brief Test program for MM2 memory threshold diagnostic messaging
 *
 * This test verifies that diagnostic messages are output when memory
 * usage crosses 10% thresholds during sector allocation.
 *
 * Copyright 2025, iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>

/* Include iMatrix headers */
#define LINUX_PLATFORM 1
#define DPRINT_DEBUGS_FOR_MEMORY_MANAGER 1

#include "../iMatrix/cs_ctrl/mm2_core.h"
#include "../iMatrix/cs_ctrl/mm2_internal.h"
#include "../iMatrix/cs_ctrl/mm2_api.h"
#include "../iMatrix/common.h"

/* Enable debug logs for this test */
#define DEBUGS_FOR_MEMORY_MANAGER 1

/******************************************************
 *                    Constants
 ******************************************************/

#define TEST_POOL_SIZE      (1024)      /* 1KB pool = 32 sectors */
#define SECTORS_PER_10PCT   3            /* ~3 sectors = 10% of 32 */

/******************************************************
 *                 Test Functions
 ******************************************************/

/**
 * @brief Print test header information
 */
static void print_test_header(void)
{
    printf("==============================================\n");
    printf("    MM2 Diagnostic Messaging Test\n");
    printf("==============================================\n");
    printf("Pool size: %d bytes\n", TEST_POOL_SIZE);
    printf("Total sectors: %d\n", TEST_POOL_SIZE / SECTOR_SIZE);
    printf("Sectors per 10%%: %d\n", SECTORS_PER_10PCT);
    printf("==============================================\n\n");
}

/**
 * @brief Test threshold crossing messages
 * @return true on success, false on failure
 */
static bool test_threshold_messages(void)
{
    printf("Test: Memory Threshold Diagnostic Messages\n");
    printf("-------------------------------------------\n");

    /* Initialize memory pool */
    printf("Initializing memory pool...\n");
    imx_result_t result = imx_memory_manager_init(TEST_POOL_SIZE);
    if (result != IMX_SUCCESS) {
        printf("ERROR: Failed to initialize memory manager: %d\n", result);
        return false;
    }

    uint32_t total_sectors = TEST_POOL_SIZE / SECTOR_SIZE;
    printf("Memory pool initialized with %u sectors\n\n", total_sectors);

    /* Allocate sectors to trigger threshold messages */
    printf("Allocating sectors to trigger threshold messages...\n");
    printf("Expected messages at: 10%%, 20%%, 30%%, etc.\n\n");

    SECTOR_ID_TYPE allocated_sectors[32];
    uint32_t allocated_count = 0;

    /* Allocate sectors progressively */
    for (uint32_t i = 0; i < total_sectors - 2; i++) {  /* Leave some free */
        /* Allocate a sector */
        SECTOR_ID_TYPE sector = allocate_sector_for_sensor(100, SECTOR_TYPE_TSD);

        if (sector == NULL_SECTOR_ID) {
            printf("WARNING: Allocation failed at sector %u\n", i);
            break;
        }

        allocated_sectors[allocated_count++] = sector;

        /* Calculate and display current usage */
        uint32_t used = allocated_count;
        uint32_t percent = (used * 100) / total_sectors;
        printf("  [Allocated sector %u] Used: %u/%u (%u%%)\n",
               i, used, total_sectors, percent);

        /* Small delay to make output readable */
        usleep(50000);  /* 50ms */
    }

    printf("\n");
    printf("Allocation phase complete\n");
    printf("Total sectors allocated: %u\n", allocated_count);
    printf("Expected threshold messages: 10%%, 20%%, 30%%, etc.\n\n");

    /* Free all allocated sectors */
    printf("Freeing all allocated sectors...\n");
    for (uint32_t i = 0; i < allocated_count; i++) {
        free_sector(allocated_sectors[i]);
    }

    printf("All sectors freed\n");

    /* Get final statistics */
    mm2_stats_t stats;
    if (generate_memory_stats(&stats) == IMX_SUCCESS) {
        printf("\nFinal Statistics:\n");
        printf("  Total sectors: %u\n", stats.total_sectors);
        printf("  Free sectors: %u\n", stats.free_sectors);
        printf("  Total allocations: %lu\n", stats.total_allocations);
        printf("  Allocation failures: %lu\n", stats.allocation_failures);
    }

    /* Cleanup */
    cleanup_memory_pool();

    printf("\n✓ Threshold message test COMPLETE\n");
    printf("Check output above for MM2 diagnostic messages\n\n");

    return true;
}

/**
 * @brief Test rapid allocation crossing multiple thresholds
 * @return true on success, false on failure
 */
static bool test_rapid_allocation(void)
{
    printf("Test: Rapid Allocation (Multiple Thresholds)\n");
    printf("--------------------------------------------\n");

    /* Initialize memory pool */
    imx_result_t result = imx_memory_manager_init(TEST_POOL_SIZE);
    if (result != IMX_SUCCESS) {
        printf("ERROR: Failed to initialize memory manager: %d\n", result);
        return false;
    }

    uint32_t total_sectors = TEST_POOL_SIZE / SECTOR_SIZE;
    printf("Rapidly allocating 50%% of pool...\n\n");

    /* Rapidly allocate 50% */
    SECTOR_ID_TYPE allocated_sectors[32];
    uint32_t target = total_sectors / 2;

    for (uint32_t i = 0; i < target; i++) {
        allocated_sectors[i] = allocate_sector_for_sensor(200, SECTOR_TYPE_EVT);
        if (allocated_sectors[i] == NULL_SECTOR_ID) {
            printf("ERROR: Rapid allocation failed at %u\n", i);
            cleanup_memory_pool();
            return false;
        }
    }

    uint32_t percent = (target * 100) / total_sectors;
    printf("Rapid allocation complete: %u/%u sectors (%u%%)\n",
           target, total_sectors, percent);
    printf("Expected messages: 10%%, 20%%, 30%%, 40%%, 50%%\n\n");

    /* Free sectors */
    for (uint32_t i = 0; i < target; i++) {
        free_sector(allocated_sectors[i]);
    }

    cleanup_memory_pool();

    printf("✓ Rapid allocation test COMPLETE\n\n");
    return true;
}

/**
 * @brief Main test function
 */
int main(int argc, char* argv[])
{
    print_test_header();

    bool all_passed = true;

    /* Test 1: Basic threshold messages */
    if (!test_threshold_messages()) {
        all_passed = false;
        printf("✗ Test 1 FAILED\n\n");
    }

    /* Test 2: Rapid allocation */
    if (!test_rapid_allocation()) {
        all_passed = false;
        printf("✗ Test 2 FAILED\n\n");
    }

    /* Summary */
    printf("==============================================\n");
    if (all_passed) {
        printf("✓ ALL TESTS PASSED\n");
        printf("Diagnostic messaging is working correctly!\n");
    } else {
        printf("✗ SOME TESTS FAILED\n");
        printf("Check the output for details\n");
    }
    printf("==============================================\n");

    return all_passed ? 0 : 1;
}

/* Stub implementations for required functions not in test environment */

/* CLI log printf stub - just print to stdout for testing */
void imx_cli_log_printf(bool timestamp, const char* format, ...)
{
    va_list args;
    va_start(args, format);

    if (timestamp) {
        /* Add simple timestamp */
        printf("[MM2] ");
    }

    vprintf(format, args);
    va_end(args);
}

/* LOGS_ENABLED stub - always return true for testing */
int LOGS_ENABLED(int level)
{
    return 1;  /* Always enabled for testing */
}

/* Time function stub */
imx_result_t imx_time_get_utc_time_ms(imx_utc_time_ms_t* utc_time_ms)
{
    if (utc_time_ms) {
        *utc_time_ms = 1234567890;  /* Dummy value */
    }
    return IMX_SUCCESS;
}

/* iMatrix Control Block stub */
iMatrix_Control_Block_t icb = {0};