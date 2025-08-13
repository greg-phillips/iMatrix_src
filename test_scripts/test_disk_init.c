/**
 * @file test_disk_init.c
 * @brief Test disk storage initialization debug
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"

// External variable we need to check
extern bool tiered_system_initialized;

int main(void)
{
    printf("=== Testing Disk Storage Initialization ===\n");
    
    // Check initial state
    printf("Initial tiered_system_initialized: %s\n", 
           tiered_system_initialized ? "true" : "false");
    
    // Initialize test environment
    printf("\nInitializing test environment...\n");
    if (initialize_memory_test_environment() != IMX_SUCCESS) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }
    
    // Check directories
    printf("\nChecking directory structure:\n");
    struct stat st;
    if (stat("/tmp/imatrix_test_storage", &st) == 0) {
        printf("✓ /tmp/imatrix_test_storage exists\n");
    } else {
        printf("✗ /tmp/imatrix_test_storage does NOT exist\n");
    }
    
    if (stat("/tmp/imatrix_test_storage/history", &st) == 0) {
        printf("✓ /tmp/imatrix_test_storage/history exists\n");
    } else {
        printf("✗ /tmp/imatrix_test_storage/history does NOT exist\n");
    }
    
    // Initialize disk storage
    printf("\nInitializing disk storage system...\n");
    init_disk_storage_system();
    
    // Check after initialization
    printf("\nAfter init_disk_storage_system:\n");
    printf("tiered_system_initialized: %s\n", 
           tiered_system_initialized ? "true" : "false");
    
    // Try to allocate a disk sector
    if (tiered_system_initialized) {
        printf("\nAttempting to allocate disk sector...\n");
        extended_sector_t disk_sector = allocate_disk_sector(100);
        
        if (disk_sector > 0) {
            printf("SUCCESS: Allocated disk sector %u\n", disk_sector);
            free_sector_extended(disk_sector);
            printf("Freed disk sector\n");
        } else {
            printf("ERROR: Failed to allocate disk sector\n");
        }
    } else {
        printf("\nERROR: Tiered system not initialized, cannot test allocation\n");
    }
    
    // Cleanup
    printf("\nCleaning up...\n");
    cleanup_memory_test_environment();
    
    return 0;
}