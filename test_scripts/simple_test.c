/*
 * simple_test.c
 * 
 * Simplified test program for iMatrix memory manager basic functionality
 * Tests core memory allocation, read/write, and statistics functions
 * 
 * Copyright 2025, iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>
#include <time.h>

// Include basic iMatrix headers
#include "../iMatrix/imatrix.h"
#include "../iMatrix/storage.h"
#include "../iMatrix/cs_ctrl/memory_manager.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define TEST_ITERATIONS     1000
#define TEST_DATA_PATTERN   0xDEADBEEF

/******************************************************
 *                    Global Variables
 ******************************************************/

static bool test_running = true;

/******************************************************
 *                    Functions
 ******************************************************/

/**
 * @brief Test basic sector allocation and deallocation
 */
static bool test_sector_allocation(void)
{
    printf("=== Testing Sector Allocation ===\n");
    
    int16_t sectors[10];
    int32_t allocated_count = 0;
    
    // Allocate several sectors
    for (int32_t i = 0; i < 10; i++) {
        sectors[i] = imx_get_free_sector();
        if (sectors[i] >= 0) {
            allocated_count++;
            printf("Allocated sector %d\n", sectors[i]);
        } else {
            printf("Failed to allocate sector %d\n", i);
            break;
        }
    }
    
    printf("Successfully allocated %d sectors\n", allocated_count);
    
    // Free the allocated sectors
    for (int32_t i = 0; i < allocated_count; i++) {
        free_sector(sectors[i]);
        printf("Freed sector %d\n", sectors[i]);
    }
    
    return allocated_count > 0;
}

/**
 * @brief Test basic read/write operations
 */
static bool test_read_write_operations(void)
{
    printf("=== Testing Read/Write Operations ===\n");
    
    // Allocate a sector
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector < 0) {
        printf("ERROR: Failed to allocate sector for read/write test\n");
        return false;
    }
    
    printf("Using sector %d for read/write test\n", sector);
    
    // Test data
    uint32_t test_data = TEST_DATA_PATTERN;
    uint32_t read_data = 0;
    
    // Write data
    write_rs(sector, 0, &test_data, sizeof(test_data));
    printf("Wrote data: 0x%08X\n", test_data);
    
    // Read data back
    read_rs(sector, 0, &read_data, sizeof(read_data));
    printf("Read data:  0x%08X\n", read_data);
    
    // Verify data
    bool success = (test_data == read_data);
    if (success) {
        printf("✓ Read/Write test PASSED\n");
    } else {
        printf("✗ Read/Write test FAILED\n");
    }
    
    // Free the sector
    free_sector(sector);
    
    return success;
}

/**
 * @brief Test secure functions if available
 */
static bool test_secure_functions(void)
{
    printf("=== Testing Secure Functions ===\n");
    
    // Test secure sector allocation
    platform_sector_signed_t sector = imx_get_free_sector_safe();
    if (sector < 0) {
        printf("Secure allocation not available or failed\n");
        return false;
    }
    
    printf("Allocated sector %d using secure function\n", sector);
    
    // Test secure read/write
    uint32_t test_data = 0x12345678;
    uint32_t read_data = 0;
    
    imx_memory_error_t write_result = write_rs_safe(sector, 0, &test_data, 
                                                   sizeof(test_data), sizeof(test_data));
    if (write_result != IMX_MEMORY_SUCCESS) {
        printf("Secure write failed: %d\n", write_result);
        free_sector_safe(sector);
        return false;
    }
    
    imx_memory_error_t read_result = read_rs_safe(sector, 0, &read_data, 
                                                 sizeof(read_data), sizeof(read_data));
    if (read_result != IMX_MEMORY_SUCCESS) {
        printf("Secure read failed: %d\n", read_result);
        free_sector_safe(sector);
        return false;
    }
    
    printf("Secure write: 0x%08X\n", test_data);
    printf("Secure read:  0x%08X\n", read_data);
    
    bool success = (test_data == read_data);
    if (success) {
        printf("✓ Secure functions test PASSED\n");
    } else {
        printf("✗ Secure functions test FAILED\n");
    }
    
    // Free using secure function
    free_sector_safe(sector);
    
    return success;
}

/**
 * @brief Test memory statistics
 */
static bool test_memory_statistics(void)
{
    printf("=== Testing Memory Statistics ===\n");
    
    // Initialize statistics
    imx_init_memory_statistics();
    
    // Update and get statistics
    imx_update_memory_statistics();
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    
    if (stats == NULL) {
        printf("ERROR: Failed to get memory statistics\n");
        return false;
    }
    
    printf("Memory Statistics:\n");
    printf("  Total sectors: %u\n", stats->total_sectors);
    printf("  Available sectors: %u\n", stats->available_sectors);
    printf("  Used sectors: %u\n", stats->used_sectors);
    printf("  Free sectors: %u\n", stats->free_sectors);
    printf("  Usage percentage: %.1f%%\n", stats->usage_percentage);
    printf("  Peak usage: %u sectors (%.1f%%)\n", 
           stats->peak_usage, stats->peak_usage_percentage);
    printf("  Allocations: %u\n", stats->allocation_count);
    printf("  Deallocations: %u\n", stats->deallocation_count);
    printf("  Failures: %u\n", stats->allocation_failures);
    printf("  Fragmentation: %u%%\n", stats->fragmentation_level);
    
    return true;
}

/**
 * @brief Test performance with multiple allocations
 */
static bool test_performance(void)
{
    printf("=== Testing Performance ===\n");
    
    clock_t start = clock();
    
    int16_t sectors[TEST_ITERATIONS];
    int32_t allocated = 0;
    int32_t failed = 0;
    
    // Allocate many sectors
    for (int32_t i = 0; i < TEST_ITERATIONS; i++) {
        sectors[i] = imx_get_free_sector();
        if (sectors[i] >= 0) {
            allocated++;
        } else {
            failed++;
            sectors[i] = -1; // Mark as invalid
        }
    }
    
    clock_t mid = clock();
    
    // Free allocated sectors
    for (int32_t i = 0; i < TEST_ITERATIONS; i++) {
        if (sectors[i] >= 0) {
            free_sector(sectors[i]);
        }
    }
    
    clock_t end = clock();
    
    double alloc_time = ((double)(mid - start)) / CLOCKS_PER_SEC;
    double free_time = ((double)(end - mid)) / CLOCKS_PER_SEC;
    double total_time = ((double)(end - start)) / CLOCKS_PER_SEC;
    
    printf("Performance Results:\n");
    printf("  Allocated: %d sectors\n", allocated);
    printf("  Failed: %d allocations\n", failed);
    printf("  Allocation time: %.3f seconds\n", alloc_time);
    printf("  Free time: %.3f seconds\n", free_time);
    printf("  Total time: %.3f seconds\n", total_time);
    
    if (allocated > 0) {
        printf("  Allocation rate: %.0f sectors/sec\n", allocated / alloc_time);
        printf("  Free rate: %.0f sectors/sec\n", allocated / free_time);
    }
    
    return allocated > 0;
}

/**
 * @brief Main test function
 */
int main(int argc, char *argv[])
{
    (void)argc;  // Suppress unused parameter warning
    (void)argv;
    
    printf("iMatrix Memory Manager Simple Test\n");
    printf("==================================\n\n");
    
    int32_t passed = 0;
    int32_t total = 0;
    
    // Initialize the memory system
    printf("Initializing memory system...\n");
    imx_sat_init();
    printf("Memory system initialized\n\n");
    
    // Run tests
    total++; if (test_sector_allocation()) passed++;
    printf("\n");
    
    total++; if (test_read_write_operations()) passed++;
    printf("\n");
    
    total++; if (test_secure_functions()) passed++;
    printf("\n");
    
    total++; if (test_memory_statistics()) passed++;
    printf("\n");
    
    total++; if (test_performance()) passed++;
    printf("\n");
    
    // Final summary
    printf("=== TEST SUMMARY ===\n");
    printf("Tests passed: %d/%d\n", passed, total);
    
    if (passed == total) {
        printf("✓ ALL TESTS PASSED\n");
        return 0;
    } else {
        printf("✗ SOME TESTS FAILED\n");
        return 1;
    }
}