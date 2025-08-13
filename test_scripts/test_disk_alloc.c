/**
 * @file test_disk_alloc.c
 * @brief Simple test to verify disk allocation works
 */
#include <stdio.h>
#include <stdlib.h>
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"

int main(void)
{
    printf("=== Testing Disk Allocation ===\n");
    
    // Initialize test environment
    if (initialize_memory_test_environment() \!= IMX_SUCCESS) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }
    
    // Initialize disk storage
    printf("Initializing disk storage...\n");
    init_disk_storage_system();
    
    // Try to allocate a disk sector
    printf("Attempting to allocate disk sector...\n");
    extended_sector_t disk_sector = allocate_disk_sector(100);
    
    if (disk_sector > 0) {
        printf("SUCCESS: Allocated disk sector %u\n", disk_sector);
        
        // Try to write some data
        uint32_t test_data[4] = {0x12345678, 0x9ABCDEF0, 0xFEDCBA98, 0x87654321};
        imx_memory_error_t result = write_sector_extended(disk_sector, 0, test_data, 4, sizeof(test_data));
        
        if (result == IMX_MEMORY_SUCCESS) {
            printf("SUCCESS: Wrote data to disk sector\n");
        } else {
            printf("ERROR: Failed to write to disk sector: %d\n", result);
        }
        
        // Free the sector
        free_sector_extended(disk_sector);
        printf("Freed disk sector\n");
    } else {
        printf("ERROR: Failed to allocate disk sector\n");
    }
    
    // Check directory structure
    printf("\nChecking directory structure:\n");
    system("ls -la /tmp/imatrix_test_storage/");
    system("ls -la /tmp/imatrix_test_storage/history/");
    
    // Cleanup
    cleanup_memory_test_environment();
    
    return 0;
}
EOF < /dev/null
