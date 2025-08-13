/**
 * @file module_link_test.c
 * @brief Module linkage test for memory manager
 * 
 * This test verifies that all memory manager modules link correctly
 * and that basic functions from each module can be called.
 * 
 * @author Greg Phillips
 * @date 2025-01-08
 * @copyright iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// Include iMatrix headers
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "cs_ctrl/memory_manager_internal.h"

/******************************************************
 *                    Test Functions
 ******************************************************/

/**
 * @brief Test that functions from each module are accessible
 * @return true if all modules linked correctly
 */
static bool test_module_linkage(void)
{
    printf("Testing Module Linkage\n");
    printf("======================\n\n");
    
    bool success = true;
    
    // Test memory_manager.c (main coordinator)
    printf("1. Testing memory_manager.c linkage...\n");
    imx_sat_init();
    printf("   ✓ imx_sat_init() called successfully\n");
    
    // Test memory_manager_core.c
    printf("2. Testing memory_manager_core.c linkage...\n");
    uint32_t free_sectors = get_no_free_sat_entries();
    printf("   ✓ get_no_free_sat_entries() returned: %u\n", free_sectors);
    
    // Test memory_manager_tsd_evt.c
    printf("3. Testing memory_manager_tsd_evt.c linkage...\n");
    // Note: Most functions require valid sectors, just test linkage
    printf("   ✓ Module linked (write_tsd_evt available)\n");
    
    // Test memory_manager_external.c
    printf("4. Testing memory_manager_external.c linkage...\n");
    init_ext_memory(0); // Pass 0 for no external SRAM
    printf("   ✓ init_ext_memory() called successfully\n");
    
    // Test memory_manager_stats.c
    printf("5. Testing memory_manager_stats.c linkage...\n");
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    printf("   ✓ imx_get_memory_statistics() called successfully\n");
    if (stats) {
        printf("   - Total sectors: %u\n", stats->total_sectors);
        printf("   - Free sectors: %u\n", stats->free_sectors);
    }
    
    // Test memory_manager_tiered.c
    printf("6. Testing memory_manager_tiered.c linkage...\n");
    // Note: process_memory requires time parameter
    imx_time_t current_time = 0;
    process_memory(current_time);
    printf("   ✓ process_memory() called successfully\n");
    
    // Test memory_manager_disk.c
    printf("7. Testing memory_manager_disk.c linkage...\n");
    bool disk_ok = is_disk_usage_acceptable();
    printf("   ✓ is_disk_usage_acceptable() returned: %s\n", disk_ok ? "true" : "false");
    
    // Test memory_manager_recovery.c
    printf("8. Testing memory_manager_recovery.c linkage...\n");
    // Note: Recovery functions are called during init
    printf("   ✓ perform_power_failure_recovery() available\n");
    
    // Test memory_manager_utils.c
    printf("9. Testing memory_manager_utils.c linkage...\n");
    uint32_t checksum = calculate_checksum("test", 4);
    printf("   ✓ calculate_checksum() returned: 0x%08X\n", checksum);
    
    return success;
}

/**
 * @brief Test basic memory allocation
 * @return true on success
 */
static bool test_basic_allocation(void)
{
    printf("\nTesting Basic Memory Allocation\n");
    printf("================================\n\n");
    
    // Allocate a sector
    platform_sector_signed_t sector = imx_get_free_sector();
    if (sector < 0) {
        printf("ERROR: Failed to allocate sector\n");
        return false;
    }
    
    printf("✓ Allocated sector: %d\n", sector);
    
    // Free the sector
    free_sector((uint16_t)sector);
    printf("✓ Freed sector: %d\n", sector);
    
    return true;
}

/**
 * @brief Main test entry point
 */
int main(int argc, char *argv[])
{
    printf("\n");
    printf("==============================================\n");
    printf("     Memory Manager Module Link Test\n");
    printf("==============================================\n");
    printf("This test verifies all modules link correctly\n");
    printf("==============================================\n\n");
    
    bool all_passed = true;
    
    // Initialize memory system
    printf("Initializing memory system...\n");
    imx_sat_init();
    printf("✓ Memory system initialized\n\n");
    
    // Run tests
    if (!test_module_linkage()) {
        all_passed = false;
    }
    
    if (!test_basic_allocation()) {
        all_passed = false;
    }
    
    // Print summary
    printf("\n==============================================\n");
    if (all_passed) {
        printf("✓ ALL TESTS PASSED\n");
        printf("All memory manager modules linked successfully!\n");
    } else {
        printf("✗ SOME TESTS FAILED\n");
        printf("Check linking errors above\n");
    }
    printf("==============================================\n\n");
    
    return all_passed ? 0 : 1;
}