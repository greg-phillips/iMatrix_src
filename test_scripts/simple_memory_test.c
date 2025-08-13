/**
 * @file simple_memory_test.c
 * @brief Simple memory manager test using current iMatrix API
 * 
 * Tests basic memory allocation, deallocation, and statistics functionality
 * using the current iMatrix memory management API.
 * 
 * Copyright 2025, iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>

// Include iMatrix headers - following Fleet-Connect-1 pattern
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define TEST_ITERATIONS     100
#define MAX_TEST_SECTORS    10
#define TEST_DATA_PATTERN   0xDEADBEEF

/******************************************************
 *                 Global Variables
 ******************************************************/

static bool test_running = true;
static int32_t test_sectors[MAX_TEST_SECTORS];  // Use signed to handle -1 errors
static uint32_t allocated_sectors = 0;

/******************************************************
 *                 Test Functions
 ******************************************************/

/**
 * @brief Print test header information
 */
static void print_test_header(void)
{
    printf("==============================================\n");
    printf("        iMatrix Simple Memory Test\n");
    printf("==============================================\n");
    printf("Using current iMatrix API architecture\n");
    printf("Test iterations: %d\n", TEST_ITERATIONS);
    printf("Max test sectors: %d\n", MAX_TEST_SECTORS);
    printf("==============================================\n\n");
}

/**
 * @brief Test basic sector allocation and deallocation
 * @return true on success, false on failure
 */
static bool test_basic_allocation(void)
{
    printf("Test 1: Basic Sector Allocation/Deallocation\n");
    printf("---------------------------------------------\n");
    
    // Clear sector array
    memset(test_sectors, 0, sizeof(test_sectors));
    allocated_sectors = 0;
    
    // Allocate sectors
    for (uint32_t i = 0; i < MAX_TEST_SECTORS; i++) {
        platform_sector_signed_t sector = imx_get_free_sector();
        if (sector < 0) {
            printf("ERROR: Failed to allocate sector %u (result: %d)\n", i, sector);
            return false;
        }
        
        test_sectors[i] = sector;
        allocated_sectors++;
        printf("  Allocated sector %u: %d\n", i, test_sectors[i]);
    }
    
    printf("  Successfully allocated %u sectors\n", allocated_sectors);
    
    // Deallocate sectors
    for (uint32_t i = 0; i < allocated_sectors; i++) {
        free_sector(test_sectors[i]);
        printf("  Freed sector %u: %d\n", i, test_sectors[i]);
    }
    
    printf("  All sectors freed\n");
    printf("✓ Basic allocation test PASSED\n\n");
    return true;
}

/**
 * @brief Test memory read/write operations
 * @return true on success, false on failure
 */
static bool test_memory_operations(void)
{
    printf("Test 2: Memory Read/Write Operations\n");
    printf("------------------------------------\n");
    
    // Allocate a sector
    #ifdef LINUX_PLATFORM
    int32_t sector = imx_get_free_sector();
    #else
    int16_t sector = imx_get_free_sector();
    #endif
    if (sector < 0) {
        printf("ERROR: Failed to allocate test sector\n");
        return false;
    }
    
    printf("  Allocated test sector: %d\n", sector);
    
    // Test data pattern
    uint32_t test_data[4] = {TEST_DATA_PATTERN, TEST_DATA_PATTERN + 1, 
                             TEST_DATA_PATTERN + 2, TEST_DATA_PATTERN + 3};
    uint32_t read_data[4] = {0};
    
    // Write data (length is in uint32_t units, not bytes)
    write_rs(sector, 0, test_data, 4);
    printf("  Written test pattern to sector %d\n", sector);
    
    // Read data back (length is in uint32_t units, not bytes)
    read_rs(sector, 0, read_data, 4);
    printf("  Read data back from sector %d\n", sector);
    
    // Verify data
    bool data_match = true;
    for (int32_t i = 0; i < 4; i++) {
        if (read_data[i] != test_data[i]) {
            printf("ERROR: Data mismatch at index %d: expected 0x%08X, got 0x%08X\n", 
                   i, test_data[i], read_data[i]);
            data_match = false;
        }
    }
    
    if (data_match) {
        printf("  Data verification successful\n");
    }
    
    // Free the sector
    free_sector(sector);
    printf("  Test sector freed\n");
    
    if (data_match) {
        printf("✓ Memory operations test PASSED\n\n");
    } else {
        printf("✗ Memory operations test FAILED\n\n");
    }
    
    return data_match;
}

/**
 * @brief Test safe memory operations
 * @return true on success, false on failure
 */
static bool test_safe_operations(void)
{
    printf("Test 3: Safe Memory Operations\n");
    printf("------------------------------\n");
    
    // Allocate a sector using safe function
    platform_sector_signed_t sector = imx_get_free_sector_safe();
    if (sector < 0) {
        printf("ERROR: Failed to allocate test sector safely\n");
        return false;
    }
    
    printf("  Allocated test sector safely: %d\n", sector);
    
    // Test data
    uint32_t test_data[2] = {0x12345678, 0x9ABCDEF0};
    uint32_t read_data[2] = {0};
    
    // Test safe write (assuming length is in uint32_t units like regular read/write)
    imx_memory_error_t result = write_rs_safe(sector, 0, test_data, 2, 2 * sizeof(uint32_t));
    if (result != IMX_MEMORY_SUCCESS) {
        printf("ERROR: Safe write failed with error %d\n", result);
        free_sector_safe(sector);
        return false;
    }
    printf("  Safe write completed successfully\n");
    
    // Test safe read (assuming length is in uint32_t units like regular read/write)
    result = read_rs_safe(sector, 0, read_data, 2, 2 * sizeof(uint32_t));
    if (result != IMX_MEMORY_SUCCESS) {
        printf("ERROR: Safe read failed with error %d\n", result);
        free_sector_safe(sector);
        return false;
    }
    printf("  Safe read completed successfully\n");
    
    // Verify data
    bool data_match = (read_data[0] == test_data[0] && read_data[1] == test_data[1]);
    if (data_match) {
        printf("  Safe operation data verification successful\n");
    } else {
        printf("ERROR: Safe operation data mismatch\n");
    }
    
    // Free sector safely
    result = free_sector_safe(sector);
    if (result != IMX_MEMORY_SUCCESS) {
        printf("ERROR: Safe free failed with error %d\n", result);
        return false;
    }
    printf("  Test sector freed safely\n");
    
    if (data_match) {
        printf("✓ Safe operations test PASSED\n\n");
    } else {
        printf("✗ Safe operations test FAILED\n\n");
    }
    
    return data_match;
}

/**
 * @brief Test memory statistics functionality
 * @return true on success, false on failure
 */
static bool test_memory_statistics(void)
{
    printf("Test 4: Memory Statistics\n");
    printf("-------------------------\n");
    
    // Initialize and update statistics
    imx_init_memory_statistics();
    imx_update_memory_statistics();
    
    // Get current statistics
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (!stats) {
        printf("ERROR: Failed to get memory statistics\n");
        return false;
    }
    
    printf("  Memory Statistics:\n");
    printf("    Total sectors: %u\n", stats->total_sectors);
    printf("    Available sectors: %u\n", stats->available_sectors);
    printf("    Used sectors: %u\n", stats->used_sectors);
    printf("    Free sectors: %u\n", stats->free_sectors);
    printf("    Peak usage: %u sectors (%.1f%%)\n", 
           stats->peak_usage, stats->peak_usage_percentage);
    printf("    Current usage: %.1f%%\n", stats->usage_percentage);
    printf("    Allocations: %u\n", stats->allocation_count);
    printf("    Deallocations: %u\n", stats->deallocation_count);
    printf("    Allocation failures: %u\n", stats->allocation_failures);
    printf("    Fragmentation level: %u%%\n", stats->fragmentation_level);
    
    // Basic sanity checks
    bool stats_valid = true;
    
    if (stats->total_sectors == 0) {
        printf("ERROR: Total sectors should not be zero\n");
        stats_valid = false;
    }
    
    if (stats->used_sectors + stats->free_sectors > stats->total_sectors) {
        printf("ERROR: Used + free sectors exceeds total\n");
        stats_valid = false;
    }
    
    if (stats_valid) {
        printf("  Statistics validation successful\n");
        printf("✓ Memory statistics test PASSED\n\n");
    } else {
        printf("✗ Memory statistics test FAILED\n\n");
    }
    
    return stats_valid;
}

/**
 * @brief Test performance under load
 * @return true on success, false on failure
 */
static bool test_performance(void)
{
    printf("Test 5: Performance Under Load\n");
    printf("------------------------------\n");
    
    uint32_t successful_allocations = 0;
    uint32_t successful_deallocations = 0;
    uint32_t allocation_failures = 0;
    
    printf("  Running %d allocation/deallocation cycles...\n", TEST_ITERATIONS);
    
    for (uint32_t i = 0; i < TEST_ITERATIONS; i++) {
        // Allocate
        platform_sector_signed_t sector = imx_get_free_sector();
        if (sector >= 0) {
            successful_allocations++;
            
            // Write some data (length is in uint32_t units)
            uint32_t test_value = i + TEST_DATA_PATTERN;
            write_rs(sector, 0, &test_value, 1);
            
            // Read it back (length is in uint32_t units)
            uint32_t read_value = 0;
            read_rs(sector, 0, &read_value, 1);
            
            // Verify
            if (read_value != test_value) {
                printf("WARNING: Data mismatch in iteration %u\n", i);
            }
            
            // Free
            free_sector(sector);
            successful_deallocations++;
        } else {
            allocation_failures++;
        }
        
        // Progress update every 100 iterations
        if ((i + 1) % 100 == 0) {
            printf("    Completed %u iterations\n", i + 1);
        }
    }
    
    printf("  Performance Results:\n");
    printf("    Successful allocations: %u/%u\n", successful_allocations, TEST_ITERATIONS);
    printf("    Successful deallocations: %u\n", successful_deallocations);
    printf("    Allocation failures: %u\n", allocation_failures);
    
    // Update final statistics
    imx_update_memory_statistics();
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    if (final_stats) {
        printf("    Final peak usage: %.1f%%\n", final_stats->peak_usage_percentage);
        printf("    Total allocations tracked: %u\n", final_stats->allocation_count);
        printf("    Total deallocations tracked: %u\n", final_stats->deallocation_count);
    }
    
    bool performance_ok = (allocation_failures == 0 && 
                          successful_allocations == successful_deallocations);
    
    if (performance_ok) {
        printf("✓ Performance test PASSED\n\n");
    } else {
        printf("✗ Performance test FAILED\n\n");
    }
    
    return performance_ok;
}

/**
 * @brief Print test summary
 */
static void print_test_summary(int32_t passed_tests, int32_t total_tests)
{
    printf("==============================================\n");
    printf("              TEST SUMMARY\n");
    printf("==============================================\n");
    printf("Tests passed: %d/%d\n", passed_tests, total_tests);
    
    if (passed_tests == total_tests) {
        printf("Result: ✓ ALL TESTS PASSED\n");
        printf("Memory manager is functioning correctly!\n");
    } else {
        printf("Result: ✗ SOME TESTS FAILED\n");
        printf("Memory manager needs attention.\n");
    }
    printf("==============================================\n");
}

/**
 * @brief Main test entry point
 */
int main(void)
{
    print_test_header();
    
    // Initialize memory test environment
    printf("Initializing memory test environment...\n");
    if (initialize_memory_test_environment() != IMX_SUCCESS) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }
    printf("Test environment initialized\n\n");
    
    // Run all tests
    int32_t passed_tests = 0;
    int32_t total_tests = 5;
    
    if (test_basic_allocation()) passed_tests++;
    if (test_memory_operations()) passed_tests++;
    if (test_safe_operations()) passed_tests++;
    if (test_memory_statistics()) passed_tests++;
    if (test_performance()) passed_tests++;
    
    // Print summary
    print_test_summary(passed_tests, total_tests);
    
    // Cleanup test environment
    cleanup_memory_test_environment();
    
    return (passed_tests == total_tests) ? 0 : 1;
}