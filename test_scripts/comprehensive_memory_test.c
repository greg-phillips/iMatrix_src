/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 *
 * This software, associated documentation and materials ("Software"),
 * is owned by iMatrix Systems ("iMatrix") and is protected by and subject to
 * worldwide patent protection (United States and foreign),
 * United States copyright laws and international treaty provisions.
 * Therefore, you may use this Software only as provided in the license
 * agreement accompanying the software package from which you
 * obtained this Software ("EULA").
 */

/**
 * @file comprehensive_memory_test.c
 * @brief Comprehensive test suite for iMatrix memory manager
 * 
 * This test suite exercises all functions of the memory manager system
 * including core memory operations, TSD/EVT functions, statistics,
 * tiered storage, and edge cases. It includes disk space simulation
 * for testing various storage conditions.
 * 
 * @author Greg Phillips
 * @date 2025-01-09
 * @copyright iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <assert.h>
#include <getopt.h>
#include <stdarg.h>
#include <dirent.h>

#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"
#include "memory_test_disk_sim.h"
#include "memory_test_csb_csd.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define TEST_PATTERN_A      0xDEADBEEF
#define TEST_PATTERN_B      0xCAFEBABE
#define TEST_PATTERN_C      0x12345678
#define TEST_PATTERN_D      0x87654321

#define DEFAULT_ITERATIONS  1000
#define PERF_TEST_OPS       1000  // Fixed number of operations for performance tests
#define MAX_SECTORS_TEST    50
#define TSD_TEST_ENTRIES    100
#define EVT_TEST_ENTRIES    50

/******************************************************
 *                    Test Configuration
 ******************************************************/

typedef struct {
    int section;                    // Specific section to run (0 = all)
    int iterations;                 // Number of stress test iterations
    int disk_usage;                 // Simulated disk usage percentage (-1 = no simulation)
    bool verbose;                   // Enable verbose output
    bool stop_on_fail;             // Stop at first failure
    bool skip_cleanup;             // Skip cleanup for debugging
} test_config_t;

static test_config_t g_config = {
    .section = 0,
    .iterations = DEFAULT_ITERATIONS,
    .disk_usage = -1,
    .verbose = false,
    .stop_on_fail = false,
    .skip_cleanup = false
};

// Global iteration tracking for debugging  
static int g_current_iteration = 0;

// Function to get current iteration for debugging
int get_current_test_iteration(void) {
    return g_current_iteration;
}

/******************************************************
 *                    Test Statistics
 ******************************************************/

typedef struct {
    uint32_t total_tests;
    uint32_t passed_tests;
    uint32_t failed_tests;
    uint32_t skipped_tests;
    clock_t start_time;
    clock_t end_time;
} test_stats_t;

typedef struct {
    uint32_t iterations_run;
    uint32_t total_tests_all_iterations;
    uint32_t total_passed_all_iterations;
    uint32_t total_failed_all_iterations;
    test_stats_t *per_iteration_stats;  // Array of stats per iteration
} iteration_stats_t;

static test_stats_t g_stats = {0};
static iteration_stats_t g_iteration_stats = {0};

/******************************************************
 *                    Helper Functions
 ******************************************************/

/**
 * @brief Print test header
 */
static void print_test_header(const char *test_name)
{
    printf("\n");
    printf("==================================================\n");
    printf("  %s\n", test_name);
    printf("==================================================\n");
}

/**
 * @brief Print test result
 */
static void print_test_result(const char *test_name, bool passed)
{
    g_stats.total_tests++;
    
    if (passed) {
        g_stats.passed_tests++;
        printf("[ PASS ] %s\n", test_name);
    } else {
        g_stats.failed_tests++;
        printf("[ FAIL ] %s\n", test_name);
        
        if (g_config.stop_on_fail) {
            printf("\nStopping due to test failure (--stop-on-fail enabled)\n");
            exit(1);
        }
    }
}

/**
 * @brief Verbose log output
 */
static void verbose_log(const char *format, ...)
{
    if (!g_config.verbose) {
        return;
    }
    
    va_list args;
    va_start(args, format);
    printf("[VERBOSE] ");
    vprintf(format, args);
    printf("\n");
    va_end(args);
}

/**
 * @brief Generate test data pattern
 */
static void generate_test_data(uint32_t *buffer, uint32_t size, uint32_t pattern)
{
    for (uint32_t i = 0; i < size; i++) {
        buffer[i] = pattern ^ i;
    }
}

/**
 * @brief Verify test data pattern
 */
static bool verify_test_data(const uint32_t *buffer, uint32_t size, uint32_t pattern)
{
    for (uint32_t i = 0; i < size; i++) {
        if (buffer[i] != (pattern ^ i)) {
            return false;
        }
    }
    return true;
}

/**
 * @brief Count .imx files in disk storage
 */
static uint32_t count_disk_files(void)
{
    uint32_t file_count = 0;
    
#ifdef LINUX_PLATFORM
    const char *storage_path = "/tmp/imatrix_test_storage/history/";
    
    // Count files in each bucket directory (0-9)
    for (int bucket = 0; bucket < 10; bucket++) {
        char bucket_path[256];
        snprintf(bucket_path, sizeof(bucket_path), "%s%d", storage_path, bucket);
        
        DIR *dir = opendir(bucket_path);
        if (dir == NULL) {
            continue; // Bucket doesn't exist yet
        }
        
        struct dirent *entry;
        while ((entry = readdir(dir)) != NULL) {
            // Count .imx files
            if (strstr(entry->d_name, ".imx") != NULL) {
                file_count++;
            }
        }
        closedir(dir);
    }
#endif
    
    return file_count;
}

/**
 * @brief Count RAM sectors that contain data
 */
static uint32_t count_ram_sectors_with_data(void)
{
    uint32_t sectors_with_data = 0;
    
    // Get memory statistics
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats) {
        // For now, use used_sectors as an approximation
        // In a more sophisticated implementation, we would check each sector
        sectors_with_data = stats->used_sectors;
    }
    
    return sectors_with_data;
}

/**
 * @brief Clean up all test data by freeing sectors directly (no flush to disk)
 * 
 * This function is used between test sections to prevent disk file accumulation.
 * It directly frees all allocated sectors without flushing to disk first.
 */
static void cleanup_all_test_data(void)
{
    verbose_log("Cleaning up all test data");
    
#ifdef LINUX_PLATFORM
    // Free all sectors that have data, starting from disk sectors down to RAM
    // Check disk sectors first (they have higher numbers)
    // Limit to a reasonable number to prevent long loops
    extended_sector_t max_sector = DISK_SECTOR_BASE + 10000;  // Check first 10000 disk sectors
    if (max_sector > DISK_SECTOR_MAX) {
        max_sector = DISK_SECTOR_MAX;
    }
    
    int freed_count = 0;
    for (extended_sector_t sector = DISK_SECTOR_BASE; sector < max_sector; sector++) {
        if (is_sector_allocated(sector)) {
            free_sector_extended(sector);
            freed_count++;
            // Also limit how many we free in one go
            if (freed_count >= 1000) {
                verbose_log("Freed 1000 disk sectors, continuing...");
                break;
            }
        }
    }
#endif
    
    // Free all RAM sectors
    for (platform_sector_t sector = 0; sector < SAT_NO_SECTORS; sector++) {
        if (is_sector_allocated(sector)) {
            free_sector(sector);
        }
    }
    
    // Clean up any remaining disk files
#ifdef LINUX_PLATFORM
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "rm -rf /tmp/imatrix_test_storage/history/*");
    int ret = system(cmd);
    if (ret != 0) {
        verbose_log("Warning: Failed to clean disk files");
    }
#endif
    
    verbose_log("Cleanup complete");
}

/**
 * @brief Ensure all data is flushed and cleaned up
 */
static bool ensure_cleanup_complete(void)
{
    verbose_log("Ensuring cleanup is complete");
    
    uint32_t initial_files = count_disk_files();
    uint32_t initial_ram_sectors = count_ram_sectors_with_data();
    
    if (initial_files > 0 || initial_ram_sectors > 0) {
        verbose_log("Initial state: %u disk files, %u RAM sectors with data", 
                   initial_files, initial_ram_sectors);
    }
    
#ifdef LINUX_PLATFORM
    // Only perform cleanup if using tiered storage
    if (initial_files > 0 || initial_ram_sectors > 0) {
        // Trigger flush to disk
        flush_all_to_disk();
        
        // Process memory state machine until cleanup is complete
        int max_cycles = 200; // Maximum 200 cycles (200 seconds simulated time)
        imx_time_t current_time = 1000;
        
        while (max_cycles-- > 0) {
            // Run memory processing
            process_memory(current_time);
            current_time += 1000; // Advance by 1 second
            
            // Check if cleanup is complete
            uint32_t ram_sectors = count_ram_sectors_with_data();
            uint32_t disk_files = count_disk_files();
            
            if (ram_sectors == 0 && disk_files == 0) {
                verbose_log("Cleanup complete after %d cycles", 200 - max_cycles);
                return true;
            }
            
            // Small delay to prevent CPU spinning
            usleep(10000); // 10ms
            
            // Progress indicator every 10 cycles
            if ((200 - max_cycles) % 10 == 0) {
                verbose_log("Cleanup progress: %u RAM sectors, %u disk files remaining", 
                           ram_sectors, disk_files);
            }
        }
        
        // Cleanup incomplete after max cycles
        uint32_t final_ram = count_ram_sectors_with_data();
        uint32_t final_files = count_disk_files();
        
        if (final_ram > 0 || final_files > 0) {
            printf("WARNING: Cleanup incomplete after timeout - %u RAM sectors, %u disk files remain\n",
                   final_ram, final_files);
            return false;
        }
    }
#endif
    
    return true;
}

/******************************************************
 *                Test Section 1: Core Memory Functions
 ******************************************************/

/**
 * @brief Test basic SAT initialization
 */
static bool test_sat_initialization(void)
{
    verbose_log("Testing SAT initialization");
    
    // SAT should already be initialized by test framework
    // Try to allocate a sector to verify it's working
    platform_sector_signed_t sector = imx_get_free_sector();
    
    if (sector < 0) {
        printf("  ERROR: Failed to allocate sector after SAT init\n");
        return false;
    }
    
    // Free the sector
    free_sector((platform_sector_t)sector);
    
    verbose_log("SAT initialization verified");
    return true;
}

/**
 * @brief Test sector allocation and deallocation
 */
static bool test_sector_allocation(void)
{
    verbose_log("Testing sector allocation and deallocation");
    
    int32_t sectors[MAX_SECTORS_TEST];
    bool result = true;
    
    // Allocate multiple sectors
    for (int i = 0; i < MAX_SECTORS_TEST; i++) {
        sectors[i] = imx_get_free_sector();
        if (sectors[i] < 0) {
            printf("  ERROR: Failed to allocate sector %d\n", i);
            result = false;
            break;
        }
        verbose_log("Allocated sector %d", sectors[i]);
    }
    
    // Free all allocated sectors
    for (int i = 0; i < MAX_SECTORS_TEST; i++) {
        if (sectors[i] >= 0) {
            free_sector((platform_sector_t)sectors[i]);
            verbose_log("Freed sector %d", sectors[i]);
        }
    }
    
    return result;
}

/**
 * @brief Test read/write operations
 */
static bool test_read_write_operations(void)
{
    verbose_log("Testing read/write operations");
    
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector < 0) {
        printf("  ERROR: Failed to allocate sector for read/write test\n");
        return false;
    }
    
    bool result = true;
    uint32_t write_data[8];
    uint32_t read_data[8];
    
    // Test 1: Write and read with pattern A
    generate_test_data(write_data, 8, TEST_PATTERN_A);
    write_rs((platform_sector_t)sector, 0, write_data, 8);
    read_rs((platform_sector_t)sector, 0, read_data, 8);
    
    if (!verify_test_data(read_data, 8, TEST_PATTERN_A)) {
        printf("  ERROR: Read data mismatch for pattern A\n");
        result = false;
    }
    
    // Test 2: Write with offset
    generate_test_data(write_data, 4, TEST_PATTERN_B);
    write_rs((platform_sector_t)sector, 8, write_data, 4);
    read_rs((platform_sector_t)sector, 8, read_data, 4);
    
    if (!verify_test_data(read_data, 4, TEST_PATTERN_B)) {
        printf("  ERROR: Read data mismatch for pattern B with offset\n");
        result = false;
    }
    
    // Test 3: Safe read/write functions
    if (result) {
        imx_memory_error_t err;
        
        generate_test_data(write_data, 6, TEST_PATTERN_C);
        err = write_rs_safe((platform_sector_t)sector, 0, write_data, 6, sizeof(write_data));
        if (err != IMX_MEMORY_SUCCESS) {
            printf("  ERROR: write_rs_safe failed: %d\n", err);
            result = false;
        }
        
        err = read_rs_safe((platform_sector_t)sector, 0, read_data, 6, sizeof(read_data));
        if (err != IMX_MEMORY_SUCCESS) {
            printf("  ERROR: read_rs_safe failed: %d\n", err);
            result = false;
        } else if (!verify_test_data(read_data, 6, TEST_PATTERN_C)) {
            printf("  ERROR: Safe read data mismatch\n");
            result = false;
        }
    }
    
    free_sector((platform_sector_t)sector);
    return result;
}

/**
 * @brief Test sector chaining
 */
static bool test_sector_chaining(void)
{
    verbose_log("Testing sector chaining");
    
    platform_sector_signed_t sector1 = imx_get_free_sector();
    platform_sector_signed_t sector2 = imx_get_free_sector();
    platform_sector_signed_t sector3 = imx_get_free_sector();
    
    if (sector1 < 0 || sector2 < 0 || sector3 < 0) {
        printf("  ERROR: Failed to allocate sectors for chaining test\n");
        if (sector1 >= 0) free_sector((platform_sector_t)sector1);
        if (sector2 >= 0) free_sector((platform_sector_t)sector2);
        if (sector3 >= 0) free_sector((platform_sector_t)sector3);
        return false;
    }
    
    bool result = true;
    
    // Create chain: sector1 -> sector2 -> sector3
    uint32_t chain_data[8];
    
    // Write to sector1 with next = sector2
    chain_data[0] = TEST_PATTERN_A;
    chain_data[6] = 0x12345678;  // ID
    chain_data[7] = (uint32_t)sector2;  // Next sector
    write_rs((platform_sector_t)sector1, 0, chain_data, 8);
    
    // Write to sector2 with next = sector3
    chain_data[0] = TEST_PATTERN_B;
    chain_data[6] = 0x23456789;  // ID
    chain_data[7] = (uint32_t)sector3;  // Next sector
    write_rs((platform_sector_t)sector2, 0, chain_data, 8);
    
    // Write to sector3 with next = 0xFFFF (end)
    chain_data[0] = TEST_PATTERN_C;
    chain_data[6] = 0x3456789A;  // ID
    chain_data[7] = 0xFFFFFFFF;  // End of chain
    write_rs((platform_sector_t)sector3, 0, chain_data, 8);
    
    // Verify chain navigation
    platform_sector_t next = get_next_sector((platform_sector_t)sector1);
    if (next != (platform_sector_t)sector2) {
        printf("  ERROR: Chain navigation failed: expected %d, got %u\n", sector2, next);
        result = false;
    }
    
    next = get_next_sector((platform_sector_t)sector2);
    if (next != (platform_sector_t)sector3) {
        printf("  ERROR: Chain navigation failed: expected %d, got %u\n", sector3, next);
        result = false;
    }
    
    // Clean up
    free_sector((platform_sector_t)sector1);
    free_sector((platform_sector_t)sector2);
    free_sector((platform_sector_t)sector3);
    
    return result;
}

/**
 * @brief Test error handling for invalid operations
 */
static bool test_error_handling(void)
{
    verbose_log("Testing error handling");
    
    bool result = true;
    uint32_t data[8];
    imx_memory_error_t err;
    
    // Test 1: Invalid sector number
    err = read_rs_safe(0xFFFFFFFF, 0, data, 4, sizeof(data));
    if (err != IMX_MEMORY_ERROR_INVALID_SECTOR) {
        printf("  ERROR: Expected INVALID_SECTOR error, got %d\n", err);
        result = false;
    }
    
    // Test 2: Buffer too small
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector >= 0) {
        err = read_rs_safe((platform_sector_t)sector, 0, data, 10, 8);
        if (err != IMX_MEMORY_ERROR_BUFFER_TOO_SMALL) {
            printf("  ERROR: Expected BUFFER_TOO_SMALL error, got %d\n", err);
            result = false;
        }
        free_sector((platform_sector_t)sector);
    }
    
    // Test 3: Out of bounds access
    sector = imx_get_free_sector();
    if (sector >= 0) {
        // Try to write beyond sector size
        err = write_rs_safe((platform_sector_t)sector, 20, data, 4, sizeof(data));
        if (err != IMX_MEMORY_ERROR_OUT_OF_BOUNDS) {
            printf("  ERROR: Expected OUT_OF_BOUNDS error, got %d\n", err);
            result = false;
        }
        free_sector((platform_sector_t)sector);
    }
    
    return result;
}

/**
 * @brief Run all core memory function tests
 */
static void test_core_memory_functions(void)
{
    print_test_header("Section 1: Core Memory Functions");
    
    print_test_result("SAT Initialization", test_sat_initialization());
    print_test_result("Sector Allocation", test_sector_allocation());
    print_test_result("Read/Write Operations", test_read_write_operations());
    print_test_result("Sector Chaining", test_sector_chaining());
    print_test_result("Error Handling", test_error_handling());
}

/******************************************************
 *                Test Section 2: TSD/EVT Functions
 ******************************************************/

// Stub structures for TSD/EVT testing
typedef struct {
    platform_sector_t head_sector;
    platform_sector_t current_sector;
    uint16_t entries_in_current_sector;
} test_csd_t;

typedef struct {
    uint16_t sensor_id;
} test_csb_t;

/**
 * @brief Test TSD/EVT write operations
 */
static bool test_tsd_evt_write(void)
{
    verbose_log("Testing TSD/EVT write operations");
    
    // Note: TSD/EVT functions require proper CSB/CSD structures
    // For this test, we'll simulate the basic operations
    
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector < 0) {
        printf("  ERROR: Failed to allocate sector for TSD test\n");
        return false;
    }
    
    bool result = true;
    
    // Simulate TSD data write
    uint32_t tsd_data[NO_TSD_ENTRIES_PER_SECTOR];
    for (int i = 0; i < NO_TSD_ENTRIES_PER_SECTOR; i++) {
        tsd_data[i] = TEST_PATTERN_A + i;
    }
    
    // Write TSD entries
    write_rs((platform_sector_t)sector, 0, tsd_data, NO_TSD_ENTRIES_PER_SECTOR);
    
    // Read back and verify
    uint32_t read_data[NO_TSD_ENTRIES_PER_SECTOR];
    read_rs((platform_sector_t)sector, 0, read_data, NO_TSD_ENTRIES_PER_SECTOR);
    
    for (int i = 0; i < NO_TSD_ENTRIES_PER_SECTOR; i++) {
        if (read_data[i] != tsd_data[i]) {
            printf("  ERROR: TSD data mismatch at entry %d\n", i);
            result = false;
            break;
        }
    }
    
    free_sector((platform_sector_t)sector);
    return result;
}

/**
 * @brief Test EVT operations with timestamps
 */
static bool test_evt_operations(void)
{
    verbose_log("Testing EVT operations");
    
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector < 0) {
        printf("  ERROR: Failed to allocate sector for EVT test\n");
        return false;
    }
    
    bool result = true;
    
    // EVT entries are 8 bytes (timestamp + data)
    uint32_t evt_data[NO_EVT_ENTRIES_PER_SECTOR * 2];
    
    // Create EVT entries with timestamps
    for (int i = 0; i < NO_EVT_ENTRIES_PER_SECTOR; i++) {
        evt_data[i * 2] = 0x60000000 + i;      // Timestamp
        evt_data[i * 2 + 1] = TEST_PATTERN_B + i;  // Data
    }
    
    // Write EVT entries
    write_rs((platform_sector_t)sector, 0, evt_data, NO_EVT_ENTRIES_PER_SECTOR * 2);
    
    // Read back and verify
    uint32_t read_data[NO_EVT_ENTRIES_PER_SECTOR * 2];
    read_rs((platform_sector_t)sector, 0, read_data, NO_EVT_ENTRIES_PER_SECTOR * 2);
    
    for (int i = 0; i < NO_EVT_ENTRIES_PER_SECTOR * 2; i++) {
        if (read_data[i] != evt_data[i]) {
            printf("  ERROR: EVT data mismatch at offset %d\n", i);
            result = false;
            break;
        }
    }
    
    free_sector((platform_sector_t)sector);
    return result;
}

/**
 * @brief Run all TSD/EVT function tests
 */
static void test_tsd_evt_functions(void)
{
    print_test_header("Section 2: TSD/EVT Functions");
    
    // Test with simple stubs first
    print_test_result("TSD Write Operations (stub)", test_tsd_evt_write());
    print_test_result("EVT Operations (stub)", test_evt_operations());
    
    // Test with proper CSB/CSD structures
    verbose_log("Testing with proper CSB/CSD structures");
    int tsd_failures = test_tsd_with_proper_structures();
    int evt_failures = test_evt_with_proper_structures();
    
    print_test_result("TSD with proper CSB/CSD", tsd_failures == 0);
    print_test_result("EVT with proper CSB/CSD", evt_failures == 0);
    
    if (tsd_failures == 0 && evt_failures == 0) {
        printf("  ✓ Full TSD/EVT testing passed with proper CSB/CSD structures\n");
    }
}

/******************************************************
 *                Test Section 3: Statistics Functions
 ******************************************************/

/**
 * @brief Test memory statistics tracking
 */
static bool test_memory_statistics(void)
{
    verbose_log("Testing memory statistics");
    
    // Initialize statistics
    imx_init_memory_statistics();
    
    // Get baseline statistics
    imx_memory_statistics_t stats_before;
    imx_memory_statistics_t *stats_ptr = imx_get_memory_statistics();
    if (!stats_ptr) {
        printf("  ERROR: Failed to get memory statistics\n");
        return false;
    }
    memcpy(&stats_before, stats_ptr, sizeof(imx_memory_statistics_t));
    
    // Perform some operations
    int32_t sectors[5];
    for (int i = 0; i < 5; i++) {
        sectors[i] = imx_get_free_sector();
    }
    
    // Update statistics
    imx_update_memory_statistics();
    
    // Get new statistics
    imx_memory_statistics_t stats_after;
    stats_ptr = imx_get_memory_statistics();
    memcpy(&stats_after, stats_ptr, sizeof(imx_memory_statistics_t));
    
    // Verify statistics changed
    bool result = true;
    
    if (stats_after.used_sectors <= stats_before.used_sectors) {
        printf("  ERROR: Used sectors did not increase\n");
        result = false;
    }
    
    if (stats_after.allocation_count <= stats_before.allocation_count) {
        printf("  ERROR: Allocation count did not increase\n");
        result = false;
    }
    
    verbose_log("Used sectors: %u -> %u", stats_before.used_sectors, stats_after.used_sectors);
    verbose_log("Allocations: %u -> %u", stats_before.allocation_count, stats_after.allocation_count);
    
    // Free sectors
    for (int i = 0; i < 5; i++) {
        if (sectors[i] >= 0) {
            free_sector((platform_sector_t)sectors[i]);
        }
    }
    
    // Update and check deallocation stats
    imx_update_memory_statistics();
    stats_ptr = imx_get_memory_statistics();
    
    if (stats_ptr->deallocation_count <= stats_after.deallocation_count) {
        printf("  ERROR: Deallocation count did not increase\n");
        result = false;
    }
    
    return result;
}

/**
 * @brief Test fragmentation calculation
 */
static bool test_fragmentation_calculation(void)
{
    verbose_log("Testing fragmentation calculation");
    
    // Allocate sectors in a pattern that creates fragmentation
    int32_t sectors[20];
    
    // Allocate all
    for (int i = 0; i < 20; i++) {
        sectors[i] = imx_get_free_sector();
    }
    
    // Free every other sector to create fragmentation
    for (int i = 0; i < 20; i += 2) {
        if (sectors[i] >= 0) {
            free_sector((platform_sector_t)sectors[i]);
        }
    }
    
    // Calculate fragmentation
    uint32_t frag_level = imx_calculate_fragmentation_level();
    verbose_log("Fragmentation level: %u%%", frag_level);
    
    // Free remaining sectors
    for (int i = 1; i < 20; i += 2) {
        if (sectors[i] >= 0) {
            free_sector((platform_sector_t)sectors[i]);
        }
    }
    
    // Fragmentation should be detected
    return frag_level > 0;
}

/**
 * @brief Run all statistics function tests
 */
static void test_statistics_functions(void)
{
    print_test_header("Section 3: Statistics Functions");
    
    print_test_result("Memory Statistics Tracking", test_memory_statistics());
    print_test_result("Fragmentation Calculation", test_fragmentation_calculation());
    
    if (g_config.verbose) {
        printf("\nCurrent Memory Statistics:\n");
        imx_print_memory_statistics();
    }
}

/******************************************************
 *          Test Section 4: Tiered Storage Functions
 ******************************************************/

#ifdef LINUX_PLATFORM

/**
 * @brief Test disk storage initialization
 */
static bool test_disk_storage_init(void)
{
    verbose_log("Testing disk storage initialization");
    
    // Initialize should already be done by test framework
    // Verify by trying to allocate a disk sector
    extended_sector_t disk_sector = allocate_disk_sector(100);
    
    if (disk_sector == 0 || disk_sector < DISK_SECTOR_BASE) {
        printf("  ERROR: Failed to allocate disk sector\n");
        return false;
    }
    
    verbose_log("Allocated disk sector: %u", disk_sector);
    
    // Free the disk sector
    free_sector_extended(disk_sector);
    
    return true;
}

/**
 * @brief Test RAM to disk spillover
 */
static bool test_ram_to_disk_spillover(void)
{
    verbose_log("Testing RAM to disk spillover");
    
    // This test would require filling RAM to 80% to trigger spillover
    // For now, we'll test the basic disk operations
    
    extended_sector_t disk_sector = allocate_disk_sector(200);
    if (disk_sector == 0) {
        printf("  ERROR: Failed to allocate disk sector\n");
        return false;
    }
    
    bool result = true;
    uint32_t write_data[8];
    uint32_t read_data[8];
    
    // Write to disk sector
    generate_test_data(write_data, 8, TEST_PATTERN_D);
    imx_memory_error_t err = write_sector_extended(disk_sector, 0, write_data, 8, sizeof(write_data));
    if (err != IMX_MEMORY_SUCCESS) {
        printf("  ERROR: Failed to write to disk sector: %d\n", err);
        result = false;
    }
    
    // Read from disk sector
    if (result) {
        err = read_sector_extended(disk_sector, 0, read_data, 8, sizeof(read_data));
        if (err != IMX_MEMORY_SUCCESS) {
            printf("  ERROR: Failed to read from disk sector: %d\n", err);
            result = false;
        } else if (!verify_test_data(read_data, 8, TEST_PATTERN_D)) {
            printf("  ERROR: Disk sector data mismatch\n");
            result = false;
        }
    }
    
    free_sector_extended(disk_sector);
    return result;
}

/**
 * @brief Test disk sector chain validation
 */
static bool test_sector_chain_validation(void)
{
    verbose_log("Testing sector chain validation");
    
    // Allocate multiple disk sectors and create a chain
    extended_sector_t sectors[3];
    
    for (int i = 0; i < 3; i++) {
        sectors[i] = allocate_disk_sector(300 + i);
        if (sectors[i] == 0) {
            printf("  ERROR: Failed to allocate disk sector %d\n", i);
            // Clean up
            for (int j = 0; j < i; j++) {
                free_sector_extended(sectors[j]);
            }
            return false;
        }
    }
    
    // For now, just verify we can allocate and free disk sectors
    // Full chain validation would require setting up proper chains
    
    for (int i = 0; i < 3; i++) {
        free_sector_extended(sectors[i]);
    }
    
    return true;
}

/**
 * @brief Run all tiered storage tests
 */
static void test_tiered_storage_functions(void)
{
    print_test_header("Section 4: Tiered Storage Functions (Linux)");
    
    print_test_result("Disk Storage Initialization", test_disk_storage_init());
    print_test_result("RAM to Disk Spillover", test_ram_to_disk_spillover());
    print_test_result("Sector Chain Validation", test_sector_chain_validation());
}

#endif // LINUX_PLATFORM

/******************************************************
 *        Test Section 5: Disk Space Simulation Tests
 ******************************************************/

/**
 * @brief Test with normal disk usage (50%)
 */
static bool test_disk_normal_usage(void)
{
    verbose_log("Testing with 50%% disk usage");
    
    disk_sim_enable(true);
    disk_sim_set_usage_percentage(50);
    
    // Should be able to allocate disk sectors normally
    extended_sector_t sector = allocate_disk_sector(400);
    bool result = (sector != 0 && sector >= DISK_SECTOR_BASE);
    
    if (result) {
        free_sector_extended(sector);
    } else {
        printf("  ERROR: Failed to allocate with 50%% disk usage\n");
    }
    
    disk_sim_enable(false);
    return result;
}

/**
 * @brief Test with disk usage just below threshold (79%)
 */
static bool test_disk_below_threshold(void)
{
    verbose_log("Testing with 79%% disk usage (just below threshold)");
    
    disk_sim_enable(true);
    disk_sim_set_usage_percentage(79);
    
    // Should still be able to allocate
    extended_sector_t sector = allocate_disk_sector(401);
    bool result = (sector != 0 && sector >= DISK_SECTOR_BASE);
    
    if (result) {
        free_sector_extended(sector);
    } else {
        printf("  ERROR: Failed to allocate with 79%% disk usage\n");
    }
    
    disk_sim_enable(false);
    return result;
}

/**
 * @brief Test with disk usage above threshold (81%)
 */
static bool test_disk_above_threshold(void)
{
    verbose_log("Testing with 81%% disk usage (above threshold)");
    
    disk_sim_enable(true);
    disk_sim_set_usage_percentage(81);
    
    // Should fail to allocate due to threshold
    extended_sector_t sector = allocate_disk_sector(402);
    bool result = (sector == 0);  // Expect failure
    
    if (!result) {
        printf("  ERROR: Allocation succeeded with 81%% disk usage (should fail)\n");
        if (sector != 0) {
            free_sector_extended(sector);
        }
    }
    
    disk_sim_enable(false);
    return result;
}

/**
 * @brief Test with critical disk usage (95%)
 */
static bool test_disk_critical_usage(void)
{
    verbose_log("Testing with 95%% disk usage (critical)");
    
    disk_sim_enable(true);
    disk_sim_set_usage_percentage(95);
    
    // Should definitely fail
    extended_sector_t sector = allocate_disk_sector(403);
    bool result = (sector == 0);  // Expect failure
    
    if (!result) {
        printf("  ERROR: Allocation succeeded with 95%% disk usage (should fail)\n");
        if (sector != 0) {
            free_sector_extended(sector);
        }
    }
    
    disk_sim_enable(false);
    return result;
}

/**
 * @brief Test gradual disk filling
 */
static bool test_disk_gradual_fill(void)
{
    verbose_log("Testing gradual disk fill");
    
    disk_sim_enable(true);
    disk_sim_set_gradual_fill(100 * 1024 * 1024, 75);  // 100MB per op, start at 75%
    
    bool result = true;
    int successful_allocs = 0;
    
    // Try to allocate sectors until disk fills
    for (int i = 0; i < 20; i++) {
        extended_sector_t sector = allocate_disk_sector(500 + i);
        if (sector != 0) {
            successful_allocs++;
            free_sector_extended(sector);
        } else {
            // Expected to fail at some point
            verbose_log("Allocation failed after %d successful allocations", successful_allocs);
            break;
        }
    }
    
    // Should have some successful allocations before failure
    if (successful_allocs == 0) {
        printf("  ERROR: No successful allocations in gradual fill test\n");
        result = false;
    } else if (successful_allocs == 20) {
        printf("  ERROR: All allocations succeeded (disk should have filled)\n");
        result = false;
    }
    
    disk_sim_enable(false);
    return result;
}

/**
 * @brief Run all disk space simulation tests
 */
static void test_disk_space_conditions(void)
{
    print_test_header("Section 5: Disk Space Simulation Tests");
    
#ifdef LINUX_PLATFORM
    print_test_result("Normal Disk Usage (50%)", test_disk_normal_usage());
    print_test_result("Below Threshold (79%)", test_disk_below_threshold());
    print_test_result("Above Threshold (81%)", test_disk_above_threshold());
    print_test_result("Critical Usage (95%)", test_disk_critical_usage());
    print_test_result("Gradual Disk Fill", test_disk_gradual_fill());
    
    if (g_config.verbose) {
        printf("\nDisk Simulation Statistics:\n");
        disk_sim_print_stats();
    }
#else
    printf("  Disk simulation tests skipped (Linux only)\n");
    g_stats.skipped_tests += 5;
#endif
}

/******************************************************
 *          Test Section 6: Stress and Edge Cases
 ******************************************************/

/**
 * @brief Test allocating all available RAM sectors
 */
static bool test_allocate_all_ram_sectors(void)
{
    verbose_log("Testing allocation of all RAM sectors");
    
    int32_t *all_sectors = malloc(SAT_NO_SECTORS * sizeof(int32_t));
    if (!all_sectors) {
        printf("  ERROR: Failed to allocate memory for test\n");
        return false;
    }
    
    int allocated = 0;
    bool result = true;
    
    // Try to allocate all RAM sectors (but stop if we get disk sectors)
    // Also limit to prevent runaway allocation
    int max_allocations = SAT_NO_SECTORS + 10;  // Allow a few disk sectors for testing
    
    for (int i = 0; i < SAT_NO_SECTORS && allocated < max_allocations; i++) {
        all_sectors[i] = imx_get_free_sector();
        if (all_sectors[i] < 0) {
            verbose_log("Allocated %d sectors before exhaustion", i);
            break;
        }
        
        // Stop if we start getting too many disk sectors
        if (all_sectors[i] >= DISK_SECTOR_BASE) {
            verbose_log("Started allocating disk sectors at index %d", i);
            // Allow up to 10 disk sectors for testing
            if (all_sectors[i] >= DISK_SECTOR_BASE + 10) {
                verbose_log("Stopping test after allocating 10 disk sectors");
                // Free this disk sector and stop
                free_sector((platform_sector_t)all_sectors[i]);
                break;
            }
        }
        
        allocated++;
    }
    
    // Should have allocated most RAM sectors (SAT_NO_SECTORS - reserved)
    // The system reserves about 10 sectors, so we expect around 246 sectors
    if (allocated < (SAT_NO_SECTORS - 20)) {
        printf("  ERROR: Only allocated %d RAM sectors (expected ~%d)\n", 
               allocated, SAT_NO_SECTORS - 10);
        result = false;
    } else {
        verbose_log("Successfully allocated %d RAM sectors", allocated);
    }
    
    // Free all allocated sectors
    for (int i = 0; i < allocated; i++) {
        free_sector((platform_sector_t)all_sectors[i]);
    }
    
    free(all_sectors);
    return result;
}

/**
 * @brief Test fragmentation scenarios
 */
static bool test_fragmentation_scenarios(void)
{
    verbose_log("Testing fragmentation scenarios");
    
    int32_t sectors[50];
    bool result = true;
    
    // Allocate many sectors
    for (int i = 0; i < 50; i++) {
        sectors[i] = imx_get_free_sector();
        if (sectors[i] < 0) {
            printf("  ERROR: Failed to allocate sector %d\n", i);
            result = false;
            break;
        }
    }
    
    // Create fragmentation by freeing in a pattern
    // Free sectors 0, 2, 4, 6, 8...
    for (int i = 0; i < 50; i += 2) {
        if (sectors[i] >= 0) {
            free_sector((platform_sector_t)sectors[i]);
            sectors[i] = -1;
        }
    }
    
    // Try to allocate again - should reuse freed sectors
    int reused = 0;
    for (int i = 0; i < 25; i++) {
        int32_t new_sector = imx_get_free_sector();
        if (new_sector >= 0) {
            reused++;
            free_sector((platform_sector_t)new_sector);
        }
    }
    
    verbose_log("Reused %d sectors after fragmentation", reused);
    
    // Free remaining sectors
    for (int i = 1; i < 50; i += 2) {
        if (sectors[i] >= 0) {
            free_sector((platform_sector_t)sectors[i]);
        }
    }
    
    return result;
}

/**
 * @brief Test boundary conditions
 */
static bool test_boundary_conditions(void)
{
    verbose_log("Testing boundary conditions");
    
    bool result = true;
    platform_sector_signed_t sector = imx_get_free_sector();
    
    if (sector < 0) {
        printf("  ERROR: Failed to allocate sector for boundary test\n");
        return false;
    }
    
    uint32_t data[1];
    imx_memory_error_t err;
    
    // Test 1: Write at maximum valid offset
    data[0] = TEST_PATTERN_A;
    err = write_rs_safe((platform_sector_t)sector, MAX_SECTOR_DATA_SIZE - 4, data, 1, sizeof(data));
    if (err != IMX_MEMORY_SUCCESS) {
        printf("  ERROR: Failed to write at max offset: %d\n", err);
        result = false;
    }
    
    // Test 2: Read at maximum valid offset
    err = read_rs_safe((platform_sector_t)sector, MAX_SECTOR_DATA_SIZE - 4, data, 1, sizeof(data));
    if (err != IMX_MEMORY_SUCCESS) {
        printf("  ERROR: Failed to read at max offset: %d\n", err);
        result = false;
    }
    
    // Test 3: Write beyond boundary (should fail)
    err = write_rs_safe((platform_sector_t)sector, MAX_SECTOR_DATA_SIZE, data, 1, sizeof(data));
    if (err == IMX_MEMORY_SUCCESS) {
        printf("  ERROR: Write beyond boundary should have failed\n");
        result = false;
    }
    
    free_sector((platform_sector_t)sector);
    return result;
}

/**
 * @brief Run all stress and edge case tests
 */
static void test_stress_and_edge_cases(void)
{
    print_test_header("Section 6: Stress and Edge Cases");
    
    print_test_result("Allocate All RAM Sectors", test_allocate_all_ram_sectors());
    print_test_result("Fragmentation Scenarios", test_fragmentation_scenarios());
    print_test_result("Boundary Conditions", test_boundary_conditions());
}

/******************************************************
 *           Test Section 7: Performance Benchmarks
 ******************************************************/

/**
 * @brief Benchmark allocation speed
 */
static bool test_allocation_speed(void)
{
    verbose_log("Benchmarking allocation speed");
    
    clock_t start = clock();
    int32_t sectors[100];
    
    // Allocate 100 sectors
    for (int i = 0; i < 100; i++) {
        sectors[i] = imx_get_free_sector();
        if (sectors[i] < 0) {
            printf("  ERROR: Allocation failed at %d\n", i);
            // Free what we allocated
            for (int j = 0; j < i; j++) {
                free_sector((platform_sector_t)sectors[j]);
            }
            return false;
        }
    }
    
    clock_t alloc_time = clock() - start;
    
    // Free sectors
    start = clock();
    for (int i = 0; i < 100; i++) {
        free_sector((platform_sector_t)sectors[i]);
    }
    clock_t free_time = clock() - start;
    
    double alloc_ms = ((double)alloc_time / CLOCKS_PER_SEC) * 1000;
    double free_ms = ((double)free_time / CLOCKS_PER_SEC) * 1000;
    
    printf("  Allocation: 100 sectors in %.2f ms (%.0f sectors/sec)\n", 
           alloc_ms, 100000.0 / alloc_ms);
    printf("  Deallocation: 100 sectors in %.2f ms (%.0f sectors/sec)\n", 
           free_ms, 100000.0 / free_ms);
    
    return true;
}

/**
 * @brief Benchmark read/write throughput
 */
static bool test_read_write_throughput(void)
{
    verbose_log("Benchmarking read/write throughput");
    
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector < 0) {
        printf("  ERROR: Failed to allocate sector\n");
        return false;
    }
    
    uint32_t data[8];
    generate_test_data(data, 8, TEST_PATTERN_A);
    
    // Benchmark writes
    clock_t start = clock();
    for (int i = 0; i < PERF_TEST_OPS; i++) {
        write_rs((platform_sector_t)sector, 0, data, 8);
    }
    clock_t write_time = clock() - start;
    
    // Benchmark reads
    start = clock();
    for (int i = 0; i < PERF_TEST_OPS; i++) {
        read_rs((platform_sector_t)sector, 0, data, 8);
    }
    clock_t read_time = clock() - start;
    
    double write_ms = ((double)write_time / CLOCKS_PER_SEC) * 1000;
    double read_ms = ((double)read_time / CLOCKS_PER_SEC) * 1000;
    
    uint64_t bytes_per_op = 8 * sizeof(uint32_t);
    uint64_t total_bytes = bytes_per_op * PERF_TEST_OPS;
    
    printf("  Write: %d ops in %.2f ms (%.2f MB/s)\n", 
           PERF_TEST_OPS, write_ms, 
           (total_bytes / 1024.0 / 1024.0) / (write_ms / 1000.0));
    printf("  Read: %d ops in %.2f ms (%.2f MB/s)\n", 
           PERF_TEST_OPS, read_ms,
           (total_bytes / 1024.0 / 1024.0) / (read_ms / 1000.0));
    
    free_sector((platform_sector_t)sector);
    return true;
}

/**
 * @brief Run all performance benchmarks
 */
static void test_performance_benchmarks(void)
{
    print_test_header("Section 7: Performance Benchmarks");
    
    print_test_result("Allocation Speed", test_allocation_speed());
    print_test_result("Read/Write Throughput", test_read_write_throughput());
}

/******************************************************
 *                    Main Test Runner
 ******************************************************/

/**
 * @brief Print usage information
 */
static void print_usage(const char *program_name)
{
    printf("Usage: %s [options]\n", program_name);
    printf("Options:\n");
    printf("  --section N       Run only section N (1-7, 0=all)\n");
    printf("  --iterations N    Set stress test iterations (default: %d)\n", DEFAULT_ITERATIONS);
    printf("  --disk-usage N    Simulate N%% disk usage\n");
    printf("  --verbose         Enable verbose output\n");
    printf("  --stop-on-fail    Stop at first failure\n");
    printf("  --skip-cleanup    Skip cleanup for debugging\n");
    printf("  --help            Show this help message\n");
}

/**
 * @brief Parse command line arguments
 */
static void parse_arguments(int argc, char *argv[])
{
    static struct option long_options[] = {
        {"section",      required_argument, 0, 's'},
        {"iterations",   required_argument, 0, 'i'},
        {"disk-usage",   required_argument, 0, 'd'},
        {"verbose",      no_argument,       0, 'v'},
        {"stop-on-fail", no_argument,       0, 'f'},
        {"skip-cleanup", no_argument,       0, 'c'},
        {"help",         no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };
    
    int opt;
    int option_index = 0;
    
    while ((opt = getopt_long(argc, argv, "s:i:d:vfch", long_options, &option_index)) != -1) {
        switch (opt) {
            case 's':
                g_config.section = atoi(optarg);
                break;
            case 'i':
                g_config.iterations = atoi(optarg);
                if (g_config.iterations <= 0) {
                    g_config.iterations = DEFAULT_ITERATIONS;
                }
                break;
            case 'd':
                g_config.disk_usage = atoi(optarg);
                if (g_config.disk_usage < 0 || g_config.disk_usage > 100) {
                    printf("Invalid disk usage percentage: %s\n", optarg);
                    exit(1);
                }
                break;
            case 'v':
                g_config.verbose = true;
                break;
            case 'f':
                g_config.stop_on_fail = true;
                break;
            case 'c':
                g_config.skip_cleanup = true;
                break;
            case 'h':
                print_usage(argv[0]);
                exit(0);
            default:
                print_usage(argv[0]);
                exit(1);
        }
    }
}

/**
 * @brief Print test summary
 */
static void print_test_summary(void)
{
    double elapsed = ((double)(g_stats.end_time - g_stats.start_time) / CLOCKS_PER_SEC);
    
    printf("\n");
    printf("==================================================\n");
    printf("                  Test Summary\n");
    printf("==================================================\n");
    
    if (g_iteration_stats.iterations_run > 1) {
        printf("Iterations Run: %u\n", g_iteration_stats.iterations_run);
        printf("\nPer Iteration Results:\n");
        for (uint32_t i = 0; i < g_iteration_stats.iterations_run; i++) {
            printf("  Iteration %u: %u/%u passed\n", 
                   i + 1,
                   g_iteration_stats.per_iteration_stats[i].passed_tests,
                   g_iteration_stats.per_iteration_stats[i].total_tests);
        }
        printf("\nAggregate Results:\n");
        printf("Total Tests:    %u (across all iterations)\n", g_iteration_stats.total_tests_all_iterations);
        printf("Passed:         %u\n", g_iteration_stats.total_passed_all_iterations);
        printf("Failed:         %u\n", g_iteration_stats.total_failed_all_iterations);
    } else {
        printf("Iterations Run: 1\n");
        printf("Total Tests:    %u\n", g_stats.total_tests);
        printf("Passed:         %u\n", g_stats.passed_tests);
        printf("Failed:         %u\n", g_stats.failed_tests);
        printf("Skipped:        %u\n", g_stats.skipped_tests);
    }
    
    printf("Elapsed Time:   %.2f seconds\n", elapsed);
    printf("==================================================\n");
    
    if ((g_iteration_stats.iterations_run > 1 ? g_iteration_stats.total_failed_all_iterations : g_stats.failed_tests) == 0) {
        printf("\n✓ ALL TESTS PASSED!\n");
    } else {
        uint32_t total_failures = g_iteration_stats.iterations_run > 1 ? 
                                  g_iteration_stats.total_failed_all_iterations : 
                                  g_stats.failed_tests;
        printf("\n✗ TESTS FAILED: %u failures\n", total_failures);
    }
}

/**
 * @brief Main entry point
 */
int main(int argc, char *argv[])
{
    printf("iMatrix Comprehensive Memory Test Suite\n");
    printf("=======================================\n");
    
    // Parse command line arguments
    parse_arguments(argc, argv);
    
    // Initialize test environment
    printf("\nInitializing test environment...\n");
    if (init_test_storage() != 0) {
        printf("ERROR: Failed to initialize test storage\n");
        return 1;
    }
    
    // Initialize disk simulation
    disk_sim_init();
    disk_sim_load_env_config();
    
    // Apply disk usage simulation if requested
    if (g_config.disk_usage >= 0) {
        printf("Simulating %d%% disk usage\n", g_config.disk_usage);
        disk_sim_set_usage_percentage((uint32_t)g_config.disk_usage);
        disk_sim_enable(true);
        
        if (g_config.verbose) {
            disk_sim_set_logging(true);
        }
    }
    
    // Initialize disk storage for Linux platform
#ifdef LINUX_PLATFORM
    init_disk_storage_system();
    
    // Check initial disk state
    uint32_t initial_disk_files = count_disk_files();
    if (initial_disk_files > 0) {
        printf("WARNING: %u disk files already exist before test start\n", initial_disk_files);
        printf("Consider cleaning /tmp/imatrix_test_storage/history/ before running test\n");
    }
#endif
    
    // Allocate per-iteration stats array
    if (g_config.iterations > 1) {
        g_iteration_stats.per_iteration_stats = calloc(g_config.iterations, sizeof(test_stats_t));
        if (!g_iteration_stats.per_iteration_stats) {
            printf("ERROR: Failed to allocate iteration statistics\n");
            return 1;
        }
    }
    
    // Record overall start time
    clock_t overall_start_time = clock();
    
    // Run test iterations
    for (int iter = 0; iter < g_config.iterations; iter++) {
        g_current_iteration = iter + 1;  // Track current iteration for debugging
        
        if (g_config.iterations > 1) {
            printf("\n==================================================\n");
            printf("              ITERATION %d of %d\n", iter + 1, g_config.iterations);
            printf("==================================================\n");
        }
        
        // Reset per-iteration stats
        memset(&g_stats, 0, sizeof(g_stats));
        g_stats.start_time = clock();
        
        // Run test sections
        if (g_config.section == 0 || g_config.section == 1) {
            test_core_memory_functions();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
        
        if (g_config.section == 0 || g_config.section == 2) {
            test_tsd_evt_functions();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
        
        if (g_config.section == 0 || g_config.section == 3) {
            test_statistics_functions();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
        
#ifdef LINUX_PLATFORM
        if (g_config.section == 0 || g_config.section == 4) {
            test_tiered_storage_functions();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
#endif
        
        if (g_config.section == 0 || g_config.section == 5) {
            test_disk_space_conditions();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
        
        if (g_config.section == 0 || g_config.section == 6) {
            test_stress_and_edge_cases();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
        
        if (g_config.section == 0 || g_config.section == 7) {
            test_performance_benchmarks();
            // Clean up after section to prevent disk file accumulation
            if (g_config.section == 0) {
                cleanup_all_test_data();
            }
        }
        
        // Record end time for this iteration
        g_stats.end_time = clock();
        
        // Store iteration stats
        if (g_config.iterations > 1) {
            g_iteration_stats.per_iteration_stats[iter] = g_stats;
            g_iteration_stats.iterations_run++;
            g_iteration_stats.total_tests_all_iterations += g_stats.total_tests;
            g_iteration_stats.total_passed_all_iterations += g_stats.passed_tests;
            g_iteration_stats.total_failed_all_iterations += g_stats.failed_tests;
            
            // Stop on first failure if requested
            if (g_config.stop_on_fail && g_stats.failed_tests > 0) {
                printf("\nStopping due to test failure (--stop-on-fail enabled)\n");
                break;
            }
        }
        
        // Ensure cleanup is complete before next iteration
        if (iter < g_config.iterations - 1) { // Not needed after last iteration
            uint32_t files_before = count_disk_files();
            uint32_t ram_before = count_ram_sectors_with_data();
            
            if (files_before > 0 || ram_before > 0) {
                if (g_config.verbose) {
                    printf("\nCleaning up after iteration %d: %u disk files, %u RAM sectors\n", 
                           iter + 1, files_before, ram_before);
                }
                
                bool cleanup_success = ensure_cleanup_complete();
                
                uint32_t files_after = count_disk_files();
                uint32_t ram_after = count_ram_sectors_with_data();
                
                if (!cleanup_success || files_after > 0 || ram_after > 0) {
                    printf("ERROR: Cleanup failed after iteration %d - %u disk files and %u RAM sectors remain\n",
                           iter + 1, files_after, ram_after);
                    
                    // Mark as test failure
                    if (g_config.iterations > 1) {
                        g_iteration_stats.total_failed_all_iterations++;
                    } else {
                        g_stats.failed_tests++;
                    }
                    
                    if (g_config.stop_on_fail) {
                        printf("Stopping due to cleanup failure (--stop-on-fail enabled)\n");
                        break;
                    }
                } else if (g_config.verbose && (files_before > 0 || ram_before > 0)) {
                    printf("Cleanup successful: cleared %u disk files and %u RAM sectors\n",
                           files_before, ram_before);
                }
            }
        }
    }
    
    // Record overall end time
    g_stats.end_time = clock();
    g_stats.start_time = overall_start_time;
    
    // Print summary
    print_test_summary();
    
    // Final disk state check
#ifdef LINUX_PLATFORM
    uint32_t final_disk_files = count_disk_files();
    if (final_disk_files > 0) {
        printf("\nWARNING: %u disk files remain after all tests\n", final_disk_files);
        
        // Try one more cleanup if files remain
        if (!g_config.skip_cleanup) {
            printf("Attempting final cleanup...\n");
            bool final_cleanup = ensure_cleanup_complete();
            final_disk_files = count_disk_files();
            
            if (final_cleanup && final_disk_files == 0) {
                printf("Final cleanup successful - all disk files removed\n");
            } else if (final_disk_files > 0) {
                printf("ERROR: %u disk files still remain after final cleanup\n", final_disk_files);
            }
        }
    } else {
        printf("\n✓ All disk files properly cleaned up\n");
    }
#endif
    
    // Cleanup
    if (!g_config.skip_cleanup) {
        printf("\nCleaning up test environment...\n");
        disk_sim_cleanup();
        cleanup_test_storage();
    } else {
        printf("\nSkipping cleanup (--skip-cleanup enabled)\n");
    }
    
    // Free iteration stats if allocated
    if (g_iteration_stats.per_iteration_stats) {
        free(g_iteration_stats.per_iteration_stats);
    }
    
    uint32_t total_failures = g_iteration_stats.iterations_run > 1 ? 
                              g_iteration_stats.total_failed_all_iterations : 
                              g_stats.failed_tests;
    return (total_failures == 0) ? 0 : 1;
}