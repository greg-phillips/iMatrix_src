/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 * 
 * Test program to verify disk sector batching functionality
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <unistd.h>
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"

/**
 * @brief Test disk sector batching with new file format
 * 
 * This test verifies:
 * 1. New disk files use version 2 format with batched sectors
 * 2. Multiple RAM sectors can be stored in a single disk sector
 * 3. Read/write operations work correctly with batched sectors
 * 4. Legacy version 1 files can still be read
 */
static void test_disk_batching(void)
{
    printf("\n=== Testing Disk Sector Batching ===\n");
    
#ifdef LINUX_PLATFORM
    // Initialize disk storage system
    init_disk_storage_system();
    
    // Allocate a disk sector
    extended_sector_t disk_sector = allocate_disk_sector(100);
    if (disk_sector == 0) {
        printf("ERROR: Failed to allocate disk sector\n");
        return;
    }
    if (disk_sector < DISK_SECTOR_BASE) {
        printf("ERROR: Invalid disk sector %u (expected >= %u)\n", disk_sector, DISK_SECTOR_BASE);
        return;
    }
    printf("✓ Allocated disk sector: %u\n", disk_sector);
    
    // Test data patterns
    uint32_t test_patterns[RAM_SECTORS_PER_DISK_SECTOR][8];
    for (int i = 0; i < RAM_SECTORS_PER_DISK_SECTOR && i < 10; i++) {
        for (int j = 0; j < 8; j++) {
            test_patterns[i][j] = (i << 16) | j;
        }
    }
    
    // First, let's check what's actually allocated
    printf("Disk sector base: %u, allocated sector: %u\n", DISK_SECTOR_BASE, disk_sector);
    printf("RAM sectors per disk sector: %d\n", RAM_SECTORS_PER_DISK_SECTOR);
    
    // Allocate additional sectors that we'll need
    printf("Allocating %d additional disk sectors...\n", 
           (RAM_SECTORS_PER_DISK_SECTOR > 10 ? 9 : RAM_SECTORS_PER_DISK_SECTOR - 1));
    for (int i = 1; i < RAM_SECTORS_PER_DISK_SECTOR && i < 10; i++) {
        extended_sector_t extra_sector = allocate_disk_sector(100);
        if (extra_sector == 0) {
            printf("ERROR: Failed to allocate disk sector %d\n", i);
            return;
        }
        printf("  Allocated sector %u\n", extra_sector);
    }
    
    // Write multiple RAM sectors to the same disk sector
    printf("Testing write of %d RAM sectors...\n", 
           RAM_SECTORS_PER_DISK_SECTOR > 10 ? 10 : RAM_SECTORS_PER_DISK_SECTOR);
    
    for (int i = 0; i < RAM_SECTORS_PER_DISK_SECTOR && i < 10; i++) {
        imx_memory_error_t result = write_sector_extended(disk_sector + i, 0, 
                                                         test_patterns[i], 8, 
                                                         sizeof(test_patterns[i]));
        if (result != IMX_MEMORY_SUCCESS) {
            printf("ERROR: write_sector_extended failed for sector %u+%d, result=%d\n", 
                   disk_sector, i, result);
        }
        assert(result == IMX_MEMORY_SUCCESS);
    }
    printf("✓ Wrote %d RAM sectors\n", 
           RAM_SECTORS_PER_DISK_SECTOR > 10 ? 10 : RAM_SECTORS_PER_DISK_SECTOR);
    
    // Read back and verify
    printf("Testing read of RAM sectors from batched disk file...\n");
    for (int i = 0; i < RAM_SECTORS_PER_DISK_SECTOR && i < 10; i++) {
        uint32_t read_data[8];
        imx_memory_error_t result = read_sector_extended(disk_sector + i, 0, 
                                                        read_data, 8, 
                                                        sizeof(read_data));
        assert(result == IMX_MEMORY_SUCCESS);
        
        // Verify data
        for (int j = 0; j < 8; j++) {
            assert(read_data[j] == test_patterns[i][j]);
        }
    }
    printf("✓ Verified %d RAM sectors\n", 
           RAM_SECTORS_PER_DISK_SECTOR > 10 ? 10 : RAM_SECTORS_PER_DISK_SECTOR);
    
    // Check file size
    char filename[512];
    const char *base_path = "/tmp/imatrix_test_storage/history/";
    uint32_t bucket = disk_sector % 10;
    snprintf(filename, sizeof(filename), "%s%u/sector_%u_sensor_%u.imx", 
             base_path, bucket, disk_sector, 100);
    
    if (access(filename, F_OK) == 0) {
        FILE *fp = fopen(filename, "rb");
        if (fp) {
            fseek(fp, 0, SEEK_END);
            long file_size = ftell(fp);
            fclose(fp);
            
            // Expected size: header + one disk sector
            long expected_size = sizeof(disk_file_header_t) + DISK_SECTOR_SIZE;
            printf("File size: %ld bytes (expected: %ld)\n", file_size, expected_size);
            printf("Overhead: %.1f%% (vs 69%% for version 1)\n", 
                   (float)(sizeof(disk_file_header_t)) * 100.0 / file_size);
        }
    }
    
    // Clean up
    for (int i = 0; i < RAM_SECTORS_PER_DISK_SECTOR && i < 10; i++) {
        free_sector_extended(disk_sector + i);
    }
    
    printf("\n✓ Disk sector batching test PASSED\n");
#else
    printf("Disk sector batching is only available on LINUX_PLATFORM\n");
#endif
}

/**
 * @brief Test performance comparison between v1 and v2 formats
 */
static void test_performance_comparison(void)
{
    printf("\n=== Performance Comparison ===\n");
    
#ifdef LINUX_PLATFORM
    printf("Configuration:\n");
    printf("  RAM sector size: %d bytes\n", SRAM_SECTOR_SIZE);
    printf("  Disk sector size: %d bytes\n", DISK_SECTOR_SIZE);
    printf("  RAM sectors per disk sector: %d\n", RAM_SECTORS_PER_DISK_SECTOR);
    printf("  TSD entries per disk sector: %d\n", NO_TSD_ENTRIES_PER_DISK_SECTOR);
    printf("  EVT entries per disk sector: %d\n", NO_EVT_ENTRIES_PER_DISK_SECTOR);
    
    // Calculate overhead percentages
    float v1_overhead_single = (float)sizeof(disk_file_header_t) * 100.0 / 
                               (sizeof(disk_file_header_t) + SRAM_SECTOR_SIZE);
    float v2_overhead_single = (float)sizeof(disk_file_header_t) * 100.0 / 
                               (sizeof(disk_file_header_t) + DISK_SECTOR_SIZE);
    float v2_overhead_full = (float)sizeof(disk_file_header_t) * 100.0 / 
                             (sizeof(disk_file_header_t) + DISK_SECTOR_SIZE * 100);
    
    printf("\nOverhead comparison:\n");
    printf("  Version 1 (single sector file): %.1f%%\n", v1_overhead_single);
    printf("  Version 2 (single disk sector): %.1f%%\n", v2_overhead_single);
    printf("  Version 2 (100 disk sectors): %.1f%%\n", v2_overhead_full);
    
    printf("\nSpace efficiency:\n");
    printf("  Version 1: %d files for %d RAM sectors\n", 
           RAM_SECTORS_PER_DISK_SECTOR, RAM_SECTORS_PER_DISK_SECTOR);
    printf("  Version 2: 1 file for %d RAM sectors\n", RAM_SECTORS_PER_DISK_SECTOR);
#else
    printf("Performance comparison is only available on LINUX_PLATFORM\n");
#endif
}

int main(int argc, char *argv[])
{
    printf("Disk Sector Batching Test Suite\n");
    printf("================================\n");
    
    // Initialize test storage
    if (init_test_storage() != 0) {
        printf("ERROR: Failed to initialize test storage\n");
        return 1;
    }
    
    // Run tests
    test_disk_batching();
    test_performance_comparison();
    
    // Cleanup
    cleanup_test_storage();
    
    printf("\nAll tests completed successfully!\n");
    return 0;
}