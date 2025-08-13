/**
 * @file minimal_test.c
 * @brief Minimal test to isolate memory issues
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// Include iMatrix headers
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"

int main(void)
{
    printf("Starting minimal memory test...\n");
    
    // Initialize memory test environment
    printf("Initializing test environment...\n");
    if (initialize_memory_test_environment() != IMX_SUCCESS) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }
    printf("Test environment initialized\n");
    
    // Try to get memory statistics
    printf("Getting memory statistics...\n");
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats) {
        printf("Total sectors: %u\n", stats->total_sectors);
        printf("Free sectors: %u\n", stats->free_sectors);
        printf("Used sectors: %u\n", stats->used_sectors);
    }
    
    // Try a simple allocation
    printf("\nTesting simple allocation...\n");
    platform_sector_t sector = imx_get_free_sector();
    if (sector != PLATFORM_INVALID_SECTOR) {
        printf("Allocated sector: %u\n", sector);
        
        // Write some data
        uint32_t test_data = 0xDEADBEEF;
        write_rs(sector, 0, &test_data, 1);  // Write 1 uint32_t value
        printf("Wrote test data to sector\n");
        
        // Read it back
        uint32_t read_data = 0;
        read_rs(sector, 0, &read_data, 1);  // Read 1 uint32_t value
        printf("Read data: 0x%08X\n", read_data);
        
        // Free the sector
        free_sector(sector);
        printf("Freed sector\n");
    }
    
    // Cleanup
    cleanup_memory_test_environment();
    
    printf("\nTest completed successfully\n");
    return 0;
}