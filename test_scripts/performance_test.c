/**
 * @file performance_test.c
 * @brief Performance and stress testing for iMatrix memory management
 * 
 * Comprehensive performance testing including stress scenarios, 
 * memory leak detection, and performance metrics analysis.
 * 
 * Copyright 2025, iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>

// Include iMatrix headers - following Fleet-Connect-1 pattern
#include "storage.h"
#include "cs_ctrl/memory_manager.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define STRESS_TEST_ITERATIONS      10000
#define LEAK_TEST_ITERATIONS        1000
#define PERFORMANCE_TEST_SECTORS    100
#define FRAGMENTATION_TEST_CYCLES   50
#define LARGE_ALLOCATION_COUNT      500

/******************************************************
 *                 Type Definitions
 ******************************************************/

typedef struct {
    uint32_t allocations;
    uint32_t deallocations;
    uint32_t failures;
    uint64_t total_time_us;
    uint32_t min_time_us;
    uint32_t max_time_us;
    double avg_time_us;
} performance_metrics_t;

typedef struct {
    uint32_t initial_free;
    uint32_t final_free;
    uint32_t max_allocated;
    uint32_t peak_usage_percent;
    uint32_t fragmentation_level;
} memory_health_t;

/******************************************************
 *                 Global Variables
 ******************************************************/

static performance_metrics_t g_alloc_metrics = {0};
static performance_metrics_t g_dealloc_metrics = {0};
static memory_health_t g_memory_health = {0};

/******************************************************
 *                 Utility Functions
 ******************************************************/

/**
 * @brief Get current time in microseconds
 * @return time in microseconds
 */
static uint64_t get_time_us(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000000 + tv.tv_usec;
}

/**
 * @brief Update performance metrics
 * @param metrics Metrics structure to update
 * @param operation_time_us Time taken for operation in microseconds
 * @param success True if operation was successful
 */
static void update_metrics(performance_metrics_t *metrics, uint32_t operation_time_us, bool success)
{
    if (success) {
        if (metrics->allocations == 0) {
            metrics->min_time_us = operation_time_us;
            metrics->max_time_us = operation_time_us;
        } else {
            if (operation_time_us < metrics->min_time_us) {
                metrics->min_time_us = operation_time_us;
            }
            if (operation_time_us > metrics->max_time_us) {
                metrics->max_time_us = operation_time_us;
            }
        }
        
        metrics->total_time_us += operation_time_us;
        if (metrics == &g_alloc_metrics) {
            metrics->allocations++;
        } else {
            metrics->deallocations++;
        }
    } else {
        metrics->failures++;
    }
}

/**
 * @brief Calculate average time for metrics
 * @param metrics Metrics structure to calculate average for
 */
static void calculate_averages(performance_metrics_t *metrics)
{
    uint32_t total_ops = metrics->allocations + metrics->deallocations;
    if (total_ops > 0) {
        metrics->avg_time_us = (double)metrics->total_time_us / total_ops;
    }
}

/**
 * @brief Print test header
 */
static void print_test_header(void)
{
    printf("==============================================\n");
    printf("      iMatrix Memory Performance Test\n");
    printf("==============================================\n");
    printf("Using current iMatrix API architecture\n");
    printf("Stress test iterations: %d\n", STRESS_TEST_ITERATIONS);
    printf("Leak test iterations: %d\n", LEAK_TEST_ITERATIONS);
    printf("Performance test sectors: %d\n", PERFORMANCE_TEST_SECTORS);
    printf("==============================================\n\n");
}

/******************************************************
 *                 Test Functions
 ******************************************************/

/**
 * @brief Test basic allocation/deallocation performance
 * @return true on success, false on failure
 */
static bool test_basic_performance(void)
{
    printf("Test 1: Basic Allocation/Deallocation Performance\n");
    printf("------------------------------------------------\n");
    
    // Reset metrics
    memset(&g_alloc_metrics, 0, sizeof(g_alloc_metrics));
    memset(&g_dealloc_metrics, 0, sizeof(g_dealloc_metrics));
    
    platform_sector_t sectors[PERFORMANCE_TEST_SECTORS];
    
    printf("Testing allocation performance (%d sectors)...\n", PERFORMANCE_TEST_SECTORS);
    
    // Test allocations
    for (uint32_t i = 0; i < PERFORMANCE_TEST_SECTORS; i++) {
        uint64_t start_time = get_time_us();
        platform_sector_t sector = imx_get_free_sector();
        uint64_t end_time = get_time_us();
        
        uint32_t operation_time = (uint32_t)(end_time - start_time);
        bool success = (sector != PLATFORM_INVALID_SECTOR);
        
        if (success) {
            sectors[i] = sector;
        }
        
        update_metrics(&g_alloc_metrics, operation_time, success);
    }
    
    printf("Testing deallocation performance...\n");
    
    // Test deallocations
    for (uint32_t i = 0; i < g_alloc_metrics.allocations; i++) {
        uint64_t start_time = get_time_us();
        free_sector(sectors[i]);
        uint64_t end_time = get_time_us();
        
        uint32_t operation_time = (uint32_t)(end_time - start_time);
        update_metrics(&g_dealloc_metrics, operation_time, true);
    }
    
    // Calculate averages
    calculate_averages(&g_alloc_metrics);
    calculate_averages(&g_dealloc_metrics);
    
    printf("\nAllocation Performance:\n");
    printf("  Successful: %u/%d\n", g_alloc_metrics.allocations, PERFORMANCE_TEST_SECTORS);
    printf("  Failures: %u\n", g_alloc_metrics.failures);
    printf("  Min time: %u µs\n", g_alloc_metrics.min_time_us);
    printf("  Max time: %u µs\n", g_alloc_metrics.max_time_us);
    printf("  Avg time: %.2f µs\n", g_alloc_metrics.avg_time_us);
    
    printf("\nDeallocation Performance:\n");
    printf("  Operations: %u\n", g_dealloc_metrics.deallocations);
    printf("  Min time: %u µs\n", g_dealloc_metrics.min_time_us);
    printf("  Max time: %u µs\n", g_dealloc_metrics.max_time_us);
    printf("  Avg time: %.2f µs\n", g_dealloc_metrics.avg_time_us);
    
    bool test_passed = (g_alloc_metrics.allocations > 0) && 
                       (g_alloc_metrics.allocations == g_dealloc_metrics.deallocations);
    
    if (test_passed) {
        printf("✓ Basic performance test PASSED\n\n");
    } else {
        printf("✗ Basic performance test FAILED\n\n");
    }
    
    return test_passed;
}

/**
 * @brief Test memory leak detection
 * @return true on success, false on failure
 */
static bool test_memory_leak_detection(void)
{
    printf("Test 2: Memory Leak Detection\n");
    printf("-----------------------------\n");
    
    // Get initial memory statistics
    imx_update_memory_statistics();
    imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
    if (!initial_stats) {
        printf("ERROR: Failed to get initial statistics\n");
        return false;
    }
    
    uint32_t initial_used = initial_stats->used_sectors;
    uint32_t initial_alloc_count = initial_stats->allocation_count;
    uint32_t initial_dealloc_count = initial_stats->deallocation_count;
    
    printf("Initial state:\n");
    printf("  Used sectors: %u\n", initial_used);
    printf("  Allocations: %u\n", initial_alloc_count);
    printf("  Deallocations: %u\n", initial_dealloc_count);
    
    printf("Running %d allocation/deallocation cycles...\n", LEAK_TEST_ITERATIONS);
    
    // Perform many allocation/deallocation cycles
    for (uint32_t i = 0; i < LEAK_TEST_ITERATIONS; i++) {
        platform_sector_signed_t sector = imx_get_free_sector();
        if (sector >= 0) {
            // Write some data to ensure the sector is used
            uint32_t test_data = i + 0x12345678;
            write_rs(sector, 0, &test_data, 1);
            
            // Immediately free it
            free_sector(sector);
        }
        
        // Progress indicator
        if ((i + 1) % 100 == 0) {
            printf("  Completed %u cycles\n", i + 1);
        }
    }
    
    // Get final statistics
    imx_update_memory_statistics();
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    
    uint32_t final_used = final_stats->used_sectors;
    uint32_t final_alloc_count = final_stats->allocation_count;
    uint32_t final_dealloc_count = final_stats->deallocation_count;
    
    printf("\nFinal state:\n");
    printf("  Used sectors: %u\n", final_used);
    printf("  Allocations: %u\n", final_alloc_count);
    printf("  Deallocations: %u\n", final_dealloc_count);
    
    printf("\nLeak detection analysis:\n");
    printf("  Sector difference: %d\n", (int32_t)final_used - (int32_t)initial_used);
    printf("  New allocations: %u\n", final_alloc_count - initial_alloc_count);
    printf("  New deallocations: %u\n", final_dealloc_count - initial_dealloc_count);
    printf("  Allocation/deallocation balance: %d\n", 
           (int32_t)(final_alloc_count - initial_alloc_count) - 
           (int32_t)(final_dealloc_count - initial_dealloc_count));
    
    // Check for leaks (allow small variance due to system overhead)
    int32_t sector_diff = (int32_t)final_used - (int32_t)initial_used;
    bool no_major_leaks = (abs(sector_diff) <= 2); // Allow 2 sector variance
    
    if (no_major_leaks) {
        printf("✓ No significant memory leaks detected\n");
        printf("✓ Memory leak detection test PASSED\n\n");
    } else {
        printf("✗ Potential memory leak detected!\n");
        printf("✗ Memory leak detection test FAILED\n\n");
    }
    
    return no_major_leaks;
}

/**
 * @brief Test fragmentation behavior
 * @return true on success, false on failure
 */
static bool test_fragmentation_behavior(void)
{
    printf("Test 3: Memory Fragmentation Behavior\n");
    printf("-------------------------------------\n");
    
    // Get initial fragmentation level
    imx_update_memory_statistics();
    imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
    uint32_t initial_fragmentation = initial_stats->fragmentation_level;
    
    printf("Initial fragmentation level: %u%%\n", initial_fragmentation);
    
    // Create fragmentation by alternating allocation and deallocation
    platform_sector_t sectors[LARGE_ALLOCATION_COUNT];
    uint32_t allocated_count = 0;
    
    printf("Creating fragmentation pattern...\n");
    
    // Phase 1: Allocate many sectors
    for (uint32_t i = 0; i < LARGE_ALLOCATION_COUNT; i++) {
        platform_sector_t sector = imx_get_free_sector();
        if (sector != PLATFORM_INVALID_SECTOR) {
            sectors[allocated_count] = sector;
            allocated_count++;
        }
    }
    
    printf("  Allocated %u sectors\n", allocated_count);
    
    // Phase 2: Free every other sector to create holes
    uint32_t freed_count = 0;
    for (uint32_t i = 0; i < allocated_count; i += 2) {
        free_sector(sectors[i]);
        freed_count++;
    }
    
    printf("  Freed %u sectors (every other one)\n", freed_count);
    
    // Check fragmentation after creating holes
    imx_update_memory_statistics();
    imx_memory_statistics_t *fragmented_stats = imx_get_memory_statistics();
    uint32_t fragmented_level = fragmented_stats->fragmentation_level;
    
    printf("  Fragmentation after creating holes: %u%%\n", fragmented_level);
    
    // Phase 3: Try to allocate in the holes
    uint32_t hole_allocations = 0;
    for (uint32_t i = 0; i < freed_count; i++) {
        platform_sector_t sector = imx_get_free_sector();
        if (sector != PLATFORM_INVALID_SECTOR) {
            hole_allocations++;
            // Free immediately to test allocation in fragmented space
            free_sector(sector);
        }
    }
    
    printf("  Successfully allocated in %u holes\n", hole_allocations);
    
    // Phase 4: Clean up remaining sectors
    for (uint32_t i = 1; i < allocated_count; i += 2) {
        free_sector(sectors[i]);
    }
    
    // Final fragmentation check
    imx_update_memory_statistics();
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    uint32_t final_fragmentation = final_stats->fragmentation_level;
    
    printf("  Final fragmentation level: %u%%\n", final_fragmentation);
    
    printf("\nFragmentation analysis:\n");
    printf("  Initial: %u%% → Fragmented: %u%% → Final: %u%%\n", 
           initial_fragmentation, fragmented_level, final_fragmentation);
    
    // Test passes if fragmentation is handled reasonably
    bool fragmentation_handled = (hole_allocations > 0) && 
                                (final_fragmentation <= fragmented_level + 10);
    
    if (fragmentation_handled) {
        printf("✓ Fragmentation behavior test PASSED\n\n");
    } else {
        printf("✗ Fragmentation behavior test FAILED\n\n");
    }
    
    return fragmentation_handled;
}

/**
 * @brief Test stress scenarios
 * @return true on success, false on failure
 */
static bool test_stress_scenarios(void)
{
    printf("Test 4: Stress Test Scenarios\n");
    printf("-----------------------------\n");
    
    uint32_t stress_allocations = 0;
    uint32_t stress_deallocations = 0;
    uint32_t stress_failures = 0;
    
    printf("Running %d stress test iterations...\n", STRESS_TEST_ITERATIONS);
    
    // Stress test with random allocation patterns
    srand((unsigned int)time(NULL));
    
    platform_sector_t active_sectors[100];
    uint32_t active_count = 0;
    
    for (uint32_t i = 0; i < STRESS_TEST_ITERATIONS; i++) {
        // Randomly decide to allocate or deallocate
        bool should_allocate = (rand() % 100) < 60; // 60% allocation bias
        
        if (should_allocate && active_count < 100) {
            // Try to allocate
            platform_sector_t sector = imx_get_free_sector();
            if (sector != PLATFORM_INVALID_SECTOR) {
                active_sectors[active_count] = sector;
                active_count++;
                stress_allocations++;
                
                // Write test data
                uint32_t test_data = i + 0xABCDEF00;
                write_rs(sector, 0, &test_data, 1);  // Write 1 uint32_t value
            } else {
                stress_failures++;
            }
        } else if (active_count > 0) {
            // Deallocate a random sector
            uint32_t index = rand() % active_count;
            free_sector(active_sectors[index]);
            
            // Move last sector to this position
            active_sectors[index] = active_sectors[active_count - 1];
            active_count--;
            stress_deallocations++;
        }
        
        // Progress update
        if ((i + 1) % 1000 == 0) {
            printf("  Iteration %u: Active=%u, Alloc=%u, Dealloc=%u, Fail=%u\n", 
                   i + 1, active_count, stress_allocations, stress_deallocations, stress_failures);
        }
    }
    
    // Clean up remaining sectors
    printf("Cleaning up %u remaining sectors...\n", active_count);
    for (uint32_t i = 0; i < active_count; i++) {
        free_sector(active_sectors[i]);
        stress_deallocations++;
    }
    
    printf("\nStress test results:\n");
    printf("  Total allocations: %u\n", stress_allocations);
    printf("  Total deallocations: %u\n", stress_deallocations);
    printf("  Allocation failures: %u\n", stress_failures);
    printf("  Failure rate: %.2f%%\n", 
           stress_failures > 0 ? (100.0 * stress_failures) / (stress_allocations + stress_failures) : 0.0);
    
    // Get final memory state
    imx_update_memory_statistics();
    imx_memory_statistics_t *stress_stats = imx_get_memory_statistics();
    
    printf("  Final memory usage: %.1f%%\n", stress_stats->usage_percentage);
    printf("  Peak usage during test: %.1f%%\n", stress_stats->peak_usage_percentage);
    
    bool stress_passed = (stress_allocations > 0) && 
                        (stress_allocations == stress_deallocations) &&
                        (stress_stats->usage_percentage < 50.0); // Memory should be mostly free
    
    if (stress_passed) {
        printf("✓ Stress test PASSED\n\n");
    } else {
        printf("✗ Stress test FAILED\n\n");
    }
    
    return stress_passed;
}

/**
 * @brief Print comprehensive test summary
 */
static void print_test_summary(int32_t passed_tests, int32_t total_tests)
{
    printf("==============================================\n");
    printf("            PERFORMANCE TEST SUMMARY\n");
    printf("==============================================\n");
    printf("Tests passed: %d/%d\n", passed_tests, total_tests);
    
    if (passed_tests == total_tests) {
        printf("Result: ✓ ALL PERFORMANCE TESTS PASSED\n");
        printf("Memory system demonstrates excellent performance!\n");
    } else {
        printf("Result: ✗ SOME PERFORMANCE TESTS FAILED\n");
        printf("Memory system performance needs optimization.\n");
    }
    
    // Final comprehensive statistics
    imx_update_memory_statistics();
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    if (final_stats) {
        printf("\nFinal System Performance Summary:\n");
        printf("  Total sectors: %u\n", final_stats->total_sectors);
        printf("  Peak usage: %.1f%% (%u sectors)\n",
               final_stats->peak_usage_percentage, final_stats->peak_usage);
        printf("  Current usage: %.1f%% (%u sectors)\n",
               final_stats->usage_percentage, final_stats->used_sectors);
        printf("  Total allocations processed: %u\n", final_stats->allocation_count);
        printf("  Total deallocations processed: %u\n", final_stats->deallocation_count);
        printf("  Allocation failures: %u\n", final_stats->allocation_failures);
        printf("  Current fragmentation: %u%%\n", final_stats->fragmentation_level);
        
        if (final_stats->allocation_count > 0) {
            double success_rate = 100.0 * (final_stats->allocation_count) / 
                                 (final_stats->allocation_count + final_stats->allocation_failures);
            printf("  Overall allocation success rate: %.2f%%\n", success_rate);
        }
    }
    
    printf("==============================================\n");
}

/**
 * @brief Main test entry point
 */
int main(void)
{
    print_test_header();
    
    // Initialize iMatrix system
    printf("Initializing iMatrix system...\n");
    imx_sat_init();
    printf("System initialized\n\n");
    
    // Initialize memory statistics
    imx_init_memory_statistics();
    
    // Run all performance tests
    int32_t passed_tests = 0;
    int32_t total_tests = 4;
    
    if (test_basic_performance()) passed_tests++;
    if (test_memory_leak_detection()) passed_tests++;
    if (test_fragmentation_behavior()) passed_tests++;
    if (test_stress_scenarios()) passed_tests++;
    
    // Print comprehensive summary
    print_test_summary(passed_tests, total_tests);
    
    return (passed_tests == total_tests) ? 0 : 1;
}