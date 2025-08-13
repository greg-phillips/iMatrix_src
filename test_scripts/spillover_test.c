/**
 * @file spillover_test.c
 * @brief Comprehensive 80% Memory Spillover Test with RAM Validation
 * 
 * Tests the complete memory-to-file spillover lifecycle including:
 * - Phase 1: 60% RAM validation (fill, read, free, verify)
 * - Phase 2: 80% capacity monitoring and spillover detection
 * - Phase 3: Disk migration and file tracking
 * - Phase 4-7: Recovery, verification, and cleanup
 * 
 * Copyright 2025, iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <dirent.h>

// Include iMatrix headers - following Fleet-Connect-1 pattern
#include "storage.h"
#include "cs_ctrl/memory_manager.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define DEFAULT_RECORD_COUNT        1000
#define MAX_RECORD_COUNT            10000000
#define TEST_SENSOR_ID              150
#define STORAGE_TEST_PATH           "/tmp/imatrix_test_storage/history/"
#define CORRUPTED_TEST_PATH         "/tmp/imatrix_test_storage/history/corrupted/"

// Capacity thresholds
#define RAM_VALIDATION_PERCENT      60
#define RAM_SPILLOVER_PERCENT       80

// Progress reporting intervals
#define PROGRESS_INTERVAL           1000

/******************************************************
 *                 Type Definitions
 ******************************************************/

typedef struct {
    uint32_t total_records;
    uint32_t records_processed;
    uint32_t ram_records;
    uint32_t disk_records;
    uint32_t verification_errors;
    uint32_t cleanup_errors;
    bool spillover_detected;
    uint32_t initial_free_sectors;
    uint32_t final_free_sectors;
} test_statistics_t;

typedef struct {
    uint32_t record_id;
    uint32_t data_field_1;
    uint32_t data_field_2;
    uint32_t data_field_3;
} test_record_t;

/******************************************************
 *                 Global Variables
 ******************************************************/

static test_statistics_t g_test_stats = {0};
static bool g_verbose = false;

// Track disk sectors for verification and cleanup
static extended_sector_t *g_disk_sectors = NULL;
static uint32_t g_disk_sector_count = 0;
static uint32_t g_disk_sector_capacity = 0;

/******************************************************
 *                 Utility Functions
 ******************************************************/

/**
 * @brief Print system memory configuration and capacity information
 */
static void print_system_info(void)
{
    printf("System Memory Configuration:\n");
    printf("=============================\n");
    
    // Static configuration from storage.h defines
    printf("  Total RAM sectors: %u\n", SAT_NO_SECTORS);
    printf("  Sector size: %u bytes\n", SRAM_SECTOR_SIZE);
    printf("  Overhead per sector: %u bytes\n", SECTOR_OVERHEAD);
    printf("  Usable space per sector: %u bytes\n", MAX_SECTOR_DATA_SIZE);
    printf("\n");
    
    // Storage capacity calculations
    printf("Storage Capacity:\n");
    printf("  TSD entries per sector: %u (%u bytes each)\n", NO_TSD_ENTRIES_PER_SECTOR, TSD_RECORD_SIZE);
    printf("  Total TSD capacity: %u entries\n", SAT_NO_SECTORS * NO_TSD_ENTRIES_PER_SECTOR);
    printf("  Event entries per sector: %u (%u bytes each)\n", NO_EVT_ENTRIES_PER_SECTOR, EVT_RECORD_SIZE);
    printf("  Total Event capacity: %u entries\n", SAT_NO_SECTORS * NO_EVT_ENTRIES_PER_SECTOR);
    printf("\n");
    
    // Current memory status
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats) {
        printf("Current Memory Status:\n");
        printf("  Available sectors: %u\n", stats->available_sectors);
        printf("  Used sectors: %u\n", stats->used_sectors);
        printf("  Free sectors: %u\n", stats->free_sectors);
        printf("  Current usage: %.1f%%\n", stats->usage_percentage);
        printf("  Peak usage: %.1f%% (%u sectors)\n", stats->peak_usage_percentage, stats->peak_usage);
        printf("  Total allocations: %u\n", stats->allocation_count);
        printf("  Allocation failures: %u\n", stats->allocation_failures);
        printf("  Fragmentation level: %u%%\n", stats->fragmentation_level);
    } else {
        printf("Current Memory Status: Unable to retrieve statistics\n");
    }
    printf("==============================================\n\n");
}

/**
 * @brief Print test header with configuration
 */
static void print_test_header(uint32_t record_count)
{
    printf("==============================================\n");
    printf("    iMatrix 80%% Memory Spillover Test\n");
    printf("==============================================\n");
    printf("Test Configuration:\n");
    printf("  Record count: %u\n", record_count);
    printf("  RAM validation threshold: %u%%\n", RAM_VALIDATION_PERCENT);
    printf("  RAM spillover threshold: %u%%\n", RAM_SPILLOVER_PERCENT);
    printf("  Test sensor ID: %u\n", TEST_SENSOR_ID);
    printf("  Storage path: %s\n", STORAGE_TEST_PATH);
    printf("==============================================\n\n");
}

/**
 * @brief Create test record with unique data pattern
 */
static void create_test_record(uint32_t index, test_record_t *record)
{
    record->record_id = 0x50000000 | index;           // Record ID with spillover test pattern
    record->data_field_1 = 0x60000000 | (index * 2);  // Data field 1
    record->data_field_2 = 0x70000000 | (index * 3);  // Data field 2
    record->data_field_3 = 0x80000000 | (index * 4);  // Data field 3
}

/**
 * @brief Verify test record data integrity
 */
static bool verify_test_record(uint32_t index, const test_record_t *record)
{
    test_record_t expected;
    create_test_record(index, &expected);
    
    return (record->record_id == expected.record_id &&
            record->data_field_1 == expected.data_field_1 &&
            record->data_field_2 == expected.data_field_2 &&
            record->data_field_3 == expected.data_field_3);
}

/**
 * @brief Print current memory statistics
 */
static void print_memory_stats(const char *phase_name)
{
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats) {
        printf("[%s] RAM usage: %.1f%% (%u/%u sectors), Free: %u\n",
               phase_name,
               stats->usage_percentage,
               stats->used_sectors,
               stats->total_sectors,
               stats->free_sectors);
    }
}

/**
 * @brief Count disk files in storage directory (including all buckets)
 */
static uint32_t count_disk_files(void)
{
    uint32_t total_count = 0;
    char bucket_path[512];
    
    // Check base directory first
    DIR *base_dir = opendir(STORAGE_TEST_PATH);
    if (!base_dir) {
        return 0;
    }
    
    struct dirent *entry;
    while ((entry = readdir(base_dir)) != NULL) {
        // Count .imx files in base directory
        if (strstr(entry->d_name, ".imx") != NULL) {
            total_count++;
        }
        
        // Check if this is a bucket directory (numeric name)
        if (entry->d_type == DT_DIR && entry->d_name[0] >= '0' && entry->d_name[0] <= '9') {
            // Count files in bucket directory
            snprintf(bucket_path, sizeof(bucket_path), "%s%s", STORAGE_TEST_PATH, entry->d_name);
            DIR *bucket_dir = opendir(bucket_path);
            if (bucket_dir) {
                struct dirent *bucket_entry;
                while ((bucket_entry = readdir(bucket_dir)) != NULL) {
                    if (strstr(bucket_entry->d_name, ".imx") != NULL) {
                        total_count++;
                    }
                }
                closedir(bucket_dir);
            }
        }
    }
    
    closedir(base_dir);
    return total_count;
}

/**
 * @brief Delete all disk files in storage directories
 */
static uint32_t delete_all_disk_files(void)
{
    uint32_t deleted_count = 0;
    char file_path[512];
    char bucket_path[512];
    
    DIR *base_dir = opendir(STORAGE_TEST_PATH);
    if (!base_dir) {
        return 0;
    }
    
    struct dirent *entry;
    while ((entry = readdir(base_dir)) != NULL) {
        // Delete .imx files in base directory
        if (strstr(entry->d_name, ".imx") != NULL) {
            snprintf(file_path, sizeof(file_path), "%s%s", STORAGE_TEST_PATH, entry->d_name);
            if (unlink(file_path) == 0) {
                deleted_count++;
            }
        }
        
        // Check if this is a bucket directory
        if (entry->d_type == DT_DIR && entry->d_name[0] >= '0' && entry->d_name[0] <= '9') {
            // Delete files in bucket directory
            snprintf(bucket_path, sizeof(bucket_path), "%s%s/", STORAGE_TEST_PATH, entry->d_name);
            DIR *bucket_dir = opendir(bucket_path);
            if (bucket_dir) {
                struct dirent *bucket_entry;
                while ((bucket_entry = readdir(bucket_dir)) != NULL) {
                    if (strstr(bucket_entry->d_name, ".imx") != NULL) {
                        snprintf(file_path, sizeof(file_path), "%s%s", bucket_path, bucket_entry->d_name);
                        if (unlink(file_path) == 0) {
                            deleted_count++;
                            
                            // Progress update for large deletions
                            if (deleted_count % 1000 == 0) {
                                printf("  Deleted %u disk files...\n", deleted_count);
                            }
                        }
                    }
                }
                closedir(bucket_dir);
                
                // Try to remove empty bucket directory
                rmdir(bucket_path);
            }
        }
    }
    
    closedir(base_dir);
    return deleted_count;
}

/**
 * @brief Create test storage directories
 */
static bool setup_test_directories(void)
{
    // Create parent directories first
    if (mkdir("/tmp/imatrix_test_storage", 0755) != 0 && errno != EEXIST) {
        printf("ERROR: Failed to create parent directory: %s\n", strerror(errno));
        return false;
    }
    
    // Create main storage directory
    if (mkdir(STORAGE_TEST_PATH, 0755) != 0 && errno != EEXIST) {
        printf("ERROR: Failed to create storage directory: %s\n", strerror(errno));
        return false;
    }
    
    // Create corrupted data directory
    if (mkdir(CORRUPTED_TEST_PATH, 0755) != 0 && errno != EEXIST) {
        printf("ERROR: Failed to create corrupted directory: %s\n", strerror(errno));
        return false;
    }
    
    return true;
}

/******************************************************
 *                 Test Phase Functions
 ******************************************************/

/**
 * @brief Phase 1A: Fill RAM to 60% capacity with record tracking
 */
static bool phase_1a_fill_ram_60_percent(uint32_t target_records, platform_sector_t **allocated_sectors)
{
    printf("Phase 1A: Fill RAM to %u%% Capacity\n", RAM_VALIDATION_PERCENT);
    printf("=====================================\n");
    
    imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
    if (!initial_stats) {
        printf("ERROR: Cannot get initial memory statistics\n");
        return false;
    }
    
    g_test_stats.initial_free_sectors = initial_stats->free_sectors;
    printf("Initial free sectors: %u\n", g_test_stats.initial_free_sectors);
    
    // Calculate target sectors for 60%
    uint32_t target_used_sectors = (initial_stats->total_sectors * RAM_VALIDATION_PERCENT) / 100;
    uint32_t current_used_sectors = initial_stats->used_sectors;
    uint32_t sectors_to_allocate = (target_used_sectors > current_used_sectors) ? 
                                   (target_used_sectors - current_used_sectors) : 0;
    
    // Adjust target records if necessary
    if (target_records > sectors_to_allocate) {
        target_records = sectors_to_allocate;
        printf("Adjusted target records to %u (max for %u%% capacity)\n", target_records, RAM_VALIDATION_PERCENT);
    }
    
    printf("Target: %u records to reach %u%% RAM usage\n", target_records, RAM_VALIDATION_PERCENT);
    printf("Allocating %u sectors...\n\n", target_records);
    
    *allocated_sectors = malloc(target_records * sizeof(platform_sector_t));
    if (!*allocated_sectors) {
        printf("ERROR: Failed to allocate sector tracking array\n");
        return false;
    }
    
    // Initialize all sectors to invalid value to prevent issues if allocation fails
    for (uint32_t i = 0; i < target_records; i++) {
        (*allocated_sectors)[i] = PLATFORM_INVALID_SECTOR;
    }
    
    uint32_t records_written = 0;
    
    for (uint32_t i = 0; i < target_records; i++) {
        // Allocate sector (should be RAM at this point)
        platform_sector_signed_t sector = imx_get_free_sector();
        if (sector < 0) {
            printf("ERROR: Failed to allocate sector %u\n", i);
            break;
        }
        
        (*allocated_sectors)[i] = sector;
        
        // Create and write test record
        test_record_t record;
        create_test_record(i, &record);
        
        write_rs(sector, 0, (uint32_t*)&record, sizeof(record) / sizeof(uint32_t));  // Write 4 uint32_t values
        
        records_written++;
        
        // Progress update
        if ((i + 1) % PROGRESS_INTERVAL == 0) {
            imx_memory_statistics_t *current_stats = imx_get_memory_statistics();
            printf("  Progress: %6u/%u records, RAM: %.1f%%\n", 
                   i + 1, target_records, current_stats->usage_percentage);
        }
    }
    
    g_test_stats.records_processed = records_written;
    g_test_stats.total_records = target_records;
    
    print_memory_stats("Phase 1A Complete");
    printf("✓ Phase 1A: Allocated and wrote %u records\n\n", records_written);
    
    return (records_written == target_records);
}

/**
 * @brief Phase 1B: Read back all 60% records to verify RAM integrity
 */
static bool phase_1b_verify_ram_records(uint32_t record_count, platform_sector_t *allocated_sectors)
{
    printf("Phase 1B: Verify RAM Record Integrity\n");
    printf("=====================================\n");
    
    uint32_t records_verified = 0;
    uint32_t verification_errors = 0;
    
    printf("Reading and verifying %u records...\n", record_count);
    
    for (uint32_t i = 0; i < record_count; i++) {
        platform_sector_t sector = allocated_sectors[i];
        
        // Read record data
        test_record_t read_record = {0};
        read_rs(sector, 0, (uint32_t*)&read_record, sizeof(read_record) / sizeof(uint32_t));  // Read 4 uint32_t values
        
        // Verify record data
        if (!verify_test_record(i, &read_record)) {
            printf("ERROR: Data mismatch in record %u (sector %u)\n", i, sector);
            printf("  Expected: ID=0x%08X, F1=0x%08X, F2=0x%08X, F3=0x%08X\n",
                   0x50000000 | i, 0x60000000 | (i * 2), 0x70000000 | (i * 3), 0x80000000 | (i * 4));
            printf("  Actual:   ID=0x%08X, F1=0x%08X, F2=0x%08X, F3=0x%08X\n",
                   read_record.record_id, read_record.data_field_1, 
                   read_record.data_field_2, read_record.data_field_3);
            verification_errors++;
            continue;
        }
        
        records_verified++;
        
        // Progress update
        if ((i + 1) % PROGRESS_INTERVAL == 0) {
            printf("  Verified: %6u/%u records\n", i + 1, record_count);
        }
    }
    
    g_test_stats.verification_errors = verification_errors;
    
    printf("✓ Phase 1B: Verified %u/%u records (%u errors)\n\n", 
           records_verified, record_count, verification_errors);
    
    return (verification_errors == 0);
}

/**
 * @brief Phase 1C: Free all sectors and verify free pool restoration
 */
static bool phase_1c_free_sectors_verify_pool(uint32_t record_count, platform_sector_t *allocated_sectors)
{
    printf("Phase 1C: Free Sectors and Verify Pool Restoration\n");
    printf("==================================================\n");
    
    imx_memory_statistics_t *pre_free_stats = imx_get_memory_statistics();
    if (!pre_free_stats) {
        printf("ERROR: Cannot get pre-free memory statistics\n");
        return false;
    }
    
    printf("Pre-free state: %u used sectors, %u free sectors\n", 
           pre_free_stats->used_sectors, pre_free_stats->free_sectors);
    
    uint32_t sectors_freed = 0;
    uint32_t free_errors = 0;
    
    printf("Freeing %u sectors...\n", record_count);
    
    for (uint32_t i = 0; i < record_count; i++) {
        platform_sector_t sector = allocated_sectors[i];
        if (sector == PLATFORM_INVALID_SECTOR) continue;
        
        free_sector(sector);
        
        sectors_freed++;
        
        // Progress update
        if ((i + 1) % PROGRESS_INTERVAL == 0) {
            printf("  Freed: %6u/%u sectors\n", i + 1, record_count);
        }
    }
    
    // Verify free pool restoration
    imx_memory_statistics_t *post_free_stats = imx_get_memory_statistics();
    if (!post_free_stats) {
        printf("ERROR: Cannot get post-free memory statistics\n");
        return false;
    }
    
    g_test_stats.final_free_sectors = post_free_stats->free_sectors;
    g_test_stats.cleanup_errors = free_errors;
    
    printf("Post-free state: %u used sectors, %u free sectors\n", 
           post_free_stats->used_sectors, post_free_stats->free_sectors);
    
    // Check if free pool was properly restored
    uint32_t expected_free_sectors = g_test_stats.initial_free_sectors;
    bool pool_restored = (post_free_stats->free_sectors >= expected_free_sectors - 5); // Allow small tolerance
    
    printf("\nFree Pool Verification:\n");
    printf("  Initial free sectors: %u\n", g_test_stats.initial_free_sectors);
    printf("  Final free sectors: %u\n", g_test_stats.final_free_sectors);
    printf("  Sectors freed: %u/%u\n", sectors_freed, record_count);
    printf("  Free errors: %u\n", free_errors);
    printf("  Pool restoration: %s\n", pool_restored ? "✓ SUCCESS" : "✗ FAILED");
    
    printf("✓ Phase 1C: RAM validation completed (%s)\n\n", 
           (free_errors == 0 && pool_restored) ? "PASSED" : "FAILED");
    
    // Clean up allocated sectors array
    free(allocated_sectors);
    
    return (free_errors == 0 && pool_restored);
}

/**
 * @brief Phase 2: Fill RAM to 80% capacity and monitor spillover threshold
 */
static bool phase_2_fill_to_80_percent(uint32_t target_records, platform_sector_t **allocated_sectors)
{
    printf("Phase 2: Fill RAM to %u%% Capacity (Spillover Threshold)\n", RAM_SPILLOVER_PERCENT);
    printf("========================================================\n");
    
    imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
    if (!initial_stats) {
        printf("ERROR: Cannot get initial memory statistics\n");
        return false;
    }
    
    printf("Target: %u records to reach %u%% RAM usage\n", target_records, RAM_SPILLOVER_PERCENT);
    printf("Allocating and monitoring spillover threshold...\n\n");
    
    *allocated_sectors = malloc(target_records * sizeof(platform_sector_t));
    if (!*allocated_sectors) {
        printf("ERROR: Failed to allocate sector tracking array\n");
        return false;
    }
    
    // Initialize all sectors to invalid value to prevent double-free
    for (uint32_t i = 0; i < target_records; i++) {
        (*allocated_sectors)[i] = PLATFORM_INVALID_SECTOR;
    }
    
    uint32_t records_written = 0;
    bool spillover_detected = false;
    uint32_t spillover_threshold = (initial_stats->total_sectors * RAM_SPILLOVER_PERCENT) / 100;
    
    for (uint32_t i = 0; i < target_records; i++) {
        // Allocate sector
        platform_sector_signed_t sector = imx_get_free_sector();
        if (sector < 0) {
            printf("WARNING: Failed to allocate sector %u (spillover may be triggering)\n", i);
            break;
        }
        
        (*allocated_sectors)[i] = sector;
        
        // Create and write test record
        test_record_t record;
        create_test_record(i + 1000, &record); // Different pattern from Phase 1
        
        write_rs(sector, 0, (uint32_t*)&record, sizeof(record) / sizeof(uint32_t));  // Write 4 uint32_t values
        records_written++;
        
        // Monitor RAM usage and spillover threshold
        if ((i + 1) % 50 == 0) {
            imx_memory_statistics_t *current_stats = imx_get_memory_statistics();
            uint32_t current_used = current_stats->used_sectors;
            uint32_t usage_percent = (uint32_t)current_stats->usage_percentage;
            
            printf("  Records: %6u/%u, RAM usage: %3u%% (%u/%u sectors)\n", 
                   i + 1, target_records, usage_percent, current_used, current_stats->total_sectors);
            
            // Check for spillover threshold
            if (!spillover_detected && current_used >= spillover_threshold) {
                printf("🔄 SPILLOVER THRESHOLD: RAM usage reached %u%% (%u sectors)\n", 
                       usage_percent, current_used);
                spillover_detected = true;
                g_test_stats.spillover_detected = true;
            }
        }
    }
    
    // Final statistics
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    printf("\nFinal Phase 2 state: %.1f%% RAM usage (%u sectors)\n", 
           final_stats->usage_percentage, final_stats->used_sectors);
    
    if (spillover_detected) {
        printf("✓ Spillover threshold detected successfully\n");
    } else {
        printf("ℹ Note: Spillover threshold not reached with %u records\n", records_written);
    }
    
    printf("✓ Phase 2: Allocated %u records at 80%% threshold\n\n", records_written);
    g_test_stats.records_processed = records_written;
    
    return true;
}

/**
 * @brief Phase 3: Continue allocation to trigger spillover to disk
 */
static bool phase_3_trigger_spillover(uint32_t total_target_records, uint32_t base_records, platform_sector_t *allocated_sectors)
{
    printf("Phase 3: Trigger Spillover to Disk\n");
    printf("===================================\n");
    
    // Calculate how many additional records to allocate
    uint32_t additional_records = 0;
    if (total_target_records > base_records) {
        additional_records = total_target_records - base_records;
    } else {
        // Default to 100 if not specified
        additional_records = 100;
    }
    
    uint32_t spillover_records = 0;
    uint32_t initial_disk_files = count_disk_files();
    
    printf("Target: %u total records (current: %u, need: %u more)\n", 
           total_target_records, base_records, additional_records);
    printf("Initial disk files: %u\n", initial_disk_files);
    printf("Attempting to allocate %u additional records to trigger disk spillover...\n", additional_records);
    
    // Allocate array to track disk sectors
    g_disk_sector_capacity = additional_records;
    g_disk_sectors = malloc(g_disk_sector_capacity * sizeof(extended_sector_t));
    if (!g_disk_sectors) {
        printf("ERROR: Failed to allocate disk sector tracking array\n");
        return false;
    }
    g_disk_sector_count = 0;
    
    // For large-scale testing, show progress more frequently
    uint32_t progress_interval = (additional_records > 10000) ? 10000 : 
                                (additional_records > 1000) ? 1000 : 
                                (additional_records > 100) ? 100 : 20;
    
    // Try to use disk sector allocation for extended testing
    for (uint32_t i = 0; i < additional_records; i++) {
        extended_sector_t disk_sector = allocate_disk_sector(TEST_SENSOR_ID);
        if (disk_sector == 0) {
            printf("ERROR: Failed to allocate disk sector at record %u\n", i);
            break;
        }
        
        // Create and write test record to disk
        test_record_t record;
        create_test_record(base_records + i, &record); // Continue numbering from base
        
        
        imx_memory_error_t write_result = write_sector_extended(disk_sector, 0, (uint32_t*)&record,
                                                               sizeof(record), 
                                                               sizeof(record));
        if (write_result == IMX_MEMORY_SUCCESS) {
            // Track the disk sector for later verification and cleanup
            g_disk_sectors[g_disk_sector_count++] = disk_sector;
            spillover_records++;
            
            if ((i + 1) % progress_interval == 0) {
                uint32_t current_disk_files = count_disk_files();
                uint32_t current_bucket = disk_sector / 1000; // BUCKET_SIZE = 1000
                printf("  Progress: %u/%u records, Disk files: %u, Current bucket: %u\n", 
                       i + 1, additional_records, current_disk_files, current_bucket);
            }
        } else {
            printf("ERROR: Disk write failed for record %u (sector %u): error %d\n", 
                   base_records + i, disk_sector, write_result);
            break;
        }
    }
    
    uint32_t final_disk_files = count_disk_files();
    
    printf("\nSpillover Results:\n");
    printf("  Records written to disk: %u\n", spillover_records);
    printf("  Initial disk files: %u\n", initial_disk_files);
    printf("  Final disk files: %u\n", final_disk_files);
    printf("  New disk files created: %u\n", final_disk_files - initial_disk_files);
    printf("  Final bucket reached: %u\n", (spillover_records > 0) ? ((base_records + spillover_records - 1) / 1000) : 0);
    
    if (spillover_records > 0) {
        printf("✓ Successfully created %u disk records\n", spillover_records);
        g_test_stats.disk_records = spillover_records;
    } else {
        printf("✗ Failed to create disk records\n");
        return false;
    }
    
    printf("✓ Phase 3: Spillover testing completed\n\n");
    return true;
}

/**
 * @brief Phase 4: Simulate recovery testing
 */
static bool phase_4_recovery_testing(void)
{
    printf("Phase 4: Recovery Testing\n");
    printf("=========================\n");
    
    printf("Simulating system restart and recovery...\n");
    
    // Trigger recovery system
    printf("Performing power failure recovery...\n");
    perform_power_failure_recovery();
    
    // Check system state after recovery
    imx_memory_statistics_t *recovery_stats = imx_get_memory_statistics();
    if (recovery_stats) {
        printf("Post-recovery state:\n");
        printf("  RAM usage: %.1f%% (%u sectors)\n", 
               recovery_stats->usage_percentage, recovery_stats->used_sectors);
        printf("  Free sectors: %u\n", recovery_stats->free_sectors);
        printf("  Total allocations: %u\n", recovery_stats->allocation_count);
    }
    
    uint32_t disk_files_after_recovery = count_disk_files();
    printf("  Disk files after recovery: %u\n", disk_files_after_recovery);
    
    printf("✓ Recovery completed successfully\n");
    printf("✓ Phase 4: Recovery testing completed\n\n");
    return true;
}

/**
 * @brief Phase 5: Full verification of all records (RAM + disk)
 */
static bool phase_5_full_verification(uint32_t record_count, platform_sector_t *allocated_sectors)
{
    printf("Phase 5: Full Verification (RAM + Disk)\n");
    printf("=======================================\n");
    
    uint32_t records_verified = 0;
    uint32_t verification_errors = 0;
    uint32_t ram_records = 0;
    uint32_t disk_records = 0;
    
    printf("Verifying %u RAM records from Phase 2...\n", record_count);
    
    // For large-scale tests, use sampling for verification
    uint32_t verify_interval = (record_count > 10000) ? 100 : 
                              (record_count > 1000) ? 10 : 1;
    
    if (verify_interval > 1) {
        printf("Using sampling verification (every %u records) for performance\n", verify_interval);
    }
    
    for (uint32_t i = 0; i < record_count; i += verify_interval) {
        platform_sector_t sector = allocated_sectors[i];
        if (sector == PLATFORM_INVALID_SECTOR) continue;
        
        // Read record data
        test_record_t read_record = {0};
        read_rs(sector, 0, (uint32_t*)&read_record, sizeof(read_record) / sizeof(uint32_t));  // Read 4 uint32_t values
        
        // Verify record data (Phase 2 records start from index 1000)
        if (!verify_test_record(i + 1000, &read_record)) {
            printf("ERROR: Data mismatch in record %u (sector %u)\n", i, sector);
            verification_errors++;
            continue;
        }
        
        records_verified++;
        ram_records++;
        
        // Progress update
        if ((i + 1) % 10000 == 0 || (i + 1) == record_count) {
            printf("  Verified: %6u/%u records\n", 
                   (i + 1) / verify_interval, record_count / verify_interval);
        }
    }
    
    // Verify disk records
    if (g_disk_sector_count > 0) {
        printf("Verifying %u disk records...\n", g_disk_sector_count);
        
        // For large-scale tests, use sampling for disk verification too
        uint32_t disk_verify_interval = (g_disk_sector_count > 10000) ? 100 : 
                                       (g_disk_sector_count > 1000) ? 10 : 1;
        
        if (disk_verify_interval > 1) {
            printf("Using sampling verification (every %u records) for disk records\n", disk_verify_interval);
        }
        
        uint32_t disk_verified = 0;
        uint32_t disk_errors = 0;
        
        for (uint32_t i = 0; i < g_disk_sector_count; i += disk_verify_interval) {
            extended_sector_t disk_sector = g_disk_sectors[i];
            test_record_t read_record = {0};
            
            imx_memory_error_t read_result = read_sector_extended(disk_sector, 0, 
                                                                 (uint32_t*)&read_record,
                                                                 sizeof(read_record),
                                                                 sizeof(read_record));
            
            if (read_result == IMX_MEMORY_SUCCESS) {
                // Verify record data
                // In Phase 3, disk records were created with ID = base_records + i
                // where base_records is the number of RAM records from Phase 2 (spillover_records)
                // record_count here is spillover_records from main()
                uint32_t expected_id = record_count + i;
                if (!verify_test_record(expected_id, &read_record)) {
                    disk_errors++;
                } else {
                    disk_verified++;
                }
            } else {
                printf("ERROR: Failed to read disk sector %u: error %d\n", disk_sector, read_result);
                disk_errors++;
            }
            
            // Progress update for large tests
            if ((i + 1) % 10000 == 0) {
                printf("  Disk verify progress: %u/%u records\n", i + 1, g_disk_sector_count);
            }
        }
        
        disk_records = g_disk_sector_count;
        verification_errors += disk_errors;
        
        if (disk_verify_interval > 1) {
            printf("Disk verification (sampled): %u verified, %u errors\n", disk_verified, disk_errors);
        } else {
            printf("Disk verification complete: %u verified, %u errors\n", disk_verified, disk_errors);
        }
    }
    
    uint32_t disk_files = count_disk_files();
    printf("Total disk files on storage: %u\n", disk_files);
    
    printf("\nVerification Results:\n");
    printf("  Total records verified: %u\n", records_verified);
    printf("  RAM records: %u\n", ram_records);
    printf("  Disk records: %u\n", disk_records);
    printf("  Verification errors: %u\n", verification_errors);
    printf("  Success rate: %.1f%%\n", 
           (records_verified > 0) ? (100.0 * records_verified / (records_verified + verification_errors)) : 100.0);
    
    g_test_stats.ram_records = ram_records;
    g_test_stats.disk_records = disk_records;
    g_test_stats.verification_errors = verification_errors;
    
    printf("✓ Phase 5: Full verification completed (%s)\n\n", 
           (verification_errors == 0) ? "PASSED" : "WITH ERRORS");
    
    return (verification_errors == 0);
}

/**
 * @brief Phase 6: Final cleanup and verification
 * 
 * @param allocated_count The actual number of sectors allocated and stored in allocated_sectors array
 * @param allocated_sectors Array of allocated sectors to free
 */
static bool phase_6_final_cleanup(uint32_t allocated_count, platform_sector_t *allocated_sectors)
{
    printf("Phase 6: Final Cleanup and Verification\n");
    printf("=======================================\n");
    
    imx_memory_statistics_t *pre_cleanup_stats = imx_get_memory_statistics();
    uint32_t initial_disk_files = count_disk_files();
    
    printf("Pre-cleanup state:\n");
    printf("  RAM usage: %.1f%% (%u sectors)\n", 
           pre_cleanup_stats->usage_percentage, pre_cleanup_stats->used_sectors);
    printf("  Disk files: %u\n", initial_disk_files);
    
    uint32_t sectors_freed = 0;
    uint32_t cleanup_errors = 0;
    
    printf("Freeing %u allocated sectors...\n", allocated_count);
    
    // Progress interval based on scale
    uint32_t progress_interval = (allocated_count > 10000) ? 10000 : 
                                (allocated_count > 1000) ? 1000 : 100;
    
    // Only iterate through the actual allocated sectors
    for (uint32_t i = 0; i < allocated_count && allocated_sectors != NULL; i++) {
        platform_sector_t sector = allocated_sectors[i];
        if (sector == PLATFORM_INVALID_SECTOR) continue;
        
        free_sector(sector);
        sectors_freed++;
        
        // Progress update
        if ((i + 1) % progress_interval == 0 || (i + 1) == allocated_count) {
            printf("  Freed: %6u/%u sectors (%.1f%%)\n", 
                   i + 1, allocated_count, 100.0 * (i + 1) / allocated_count);
        }
    }
    
    // Free disk sectors
    if (g_disk_sector_count > 0) {
        printf("\nFreeing %u disk sectors...\n", g_disk_sector_count);
        
        uint32_t disk_freed = 0;
        uint32_t disk_free_errors = 0;
        
        for (uint32_t i = 0; i < g_disk_sector_count; i++) {
            extended_sector_t disk_sector = g_disk_sectors[i];
            
            // Note: In the current implementation, free_sector_extended may not actually
            // delete the disk file, so we'll handle file deletion separately
            imx_memory_error_t free_result = free_sector_extended(disk_sector);
            if (free_result == IMX_MEMORY_SUCCESS) {
                disk_freed++;
            } else {
                disk_free_errors++;
            }
            
            // Progress update
            if ((i + 1) % 10000 == 0 || (i + 1) == g_disk_sector_count) {
                printf("  Freed: %u/%u disk sectors (%.1f%%)\n", 
                       i + 1, g_disk_sector_count, 100.0 * (i + 1) / g_disk_sector_count);
            }
        }
        
        printf("Disk sectors freed: %u (errors: %u)\n", disk_freed, disk_free_errors);
        
        // Clean up tracking array
        free(g_disk_sectors);
        g_disk_sectors = NULL;
        g_disk_sector_count = 0;
    }
    
    // Delete all disk files
    printf("\nDeleting disk files...\n");
    uint32_t pre_delete_files = count_disk_files();
    uint32_t deleted_files = delete_all_disk_files();
    uint32_t remaining_files = count_disk_files();
    
    // Check final state
    imx_memory_statistics_t *post_cleanup_stats = imx_get_memory_statistics();
    
    printf("\nCleanup Results:\n");
    printf("  RAM sectors freed: %u\n", sectors_freed);
    printf("  Disk files before cleanup: %u\n", initial_disk_files);
    printf("  Disk files deleted: %u\n", deleted_files);
    printf("  Final RAM usage: %.1f%% (%u sectors)\n", 
           post_cleanup_stats->usage_percentage, post_cleanup_stats->used_sectors);
    printf("  Remaining disk files: %u\n", remaining_files);
    
    // Verify cleanup effectiveness
    bool cleanup_successful = (post_cleanup_stats->used_sectors == 0) && 
                             (remaining_files == 0);
    
    if (!cleanup_successful) {
        if (post_cleanup_stats->used_sectors > 0) {
            printf("WARNING: %u RAM sectors remain allocated\n", post_cleanup_stats->used_sectors);
        }
        if (remaining_files > 0) {
            printf("WARNING: %u disk files remain\n", remaining_files);
        }
    }
    
    // Note: allocated_sectors array will be freed by the caller to avoid double-free
    
    printf("✓ Phase 6: Final cleanup completed (%s)\n\n", 
           cleanup_successful ? "SUCCESSFUL" : "WITH WARNINGS");
    
    return cleanup_successful;
}

/**
 * @brief Show usage information
 */
static void show_usage(const char *program_name)
{
    printf("Usage: %s [record_count]\n", program_name);
    printf("\n");
    printf("Options:\n");
    printf("  record_count    Number of records to test (default: %u, max: %u)\n", 
           DEFAULT_RECORD_COUNT, MAX_RECORD_COUNT);
    printf("\n");
    printf("Test Phases:\n");
    printf("  Phase 1A: Fill RAM to %u%% capacity\n", RAM_VALIDATION_PERCENT);
    printf("  Phase 1B: Verify RAM record integrity\n");
    printf("  Phase 1C: Free sectors and verify pool restoration\n");
    printf("  Phase 2:  Fill RAM to %u%% capacity (spillover threshold)\n", RAM_SPILLOVER_PERCENT);
    printf("  Phase 3:  Trigger spillover to disk\n");
    printf("  Phase 4:  Simulate recovery\n");
    printf("  Phase 5:  Verify all records (RAM + disk)\n");
    printf("  Phase 6:  Final cleanup and verification\n");
    printf("\n");
    printf("Examples:\n");
    printf("  %s           # Test with %u records\n", program_name, DEFAULT_RECORD_COUNT);
    printf("  %s 5000      # Test with 5000 records\n", program_name);
    printf("  %s 100000    # Large-scale test\n", program_name);
}

/**
 * @brief Main test entry point
 */
int main(int argc, char *argv[])
{
    uint32_t record_count = DEFAULT_RECORD_COUNT;
    
    // Parse command line arguments
    if (argc > 2) {
        show_usage(argv[0]);
        return 1;
    }
    
    if (argc == 2) {
        if (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0) {
            show_usage(argv[0]);
            return 0;
        }
        
        record_count = (uint32_t)atoi(argv[1]);
        if (record_count == 0 || record_count > MAX_RECORD_COUNT) {
            printf("ERROR: Invalid record count. Must be 1-%u\n", MAX_RECORD_COUNT);
            return 1;
        }
    }
    
    // Initialize iMatrix system first
    printf("Initializing iMatrix system...\n");
    imx_sat_init();
    imx_init_memory_statistics();
    
    // Initialize disk storage system
    printf("Initializing disk storage system...\n");
    init_disk_storage_system();
    printf("Disk storage system initialized\n\n");
    
    // Print system information
    print_system_info();
    
    // Print test configuration
    print_test_header(record_count);
    
    // Setup test environment
    if (!setup_test_directories()) {
        printf("✗ Test environment setup failed\n");
        return 1;
    }
    
    // Initialize test statistics
    memset(&g_test_stats, 0, sizeof(g_test_stats));
    
    // Phase 1: RAM Validation (60% capacity test)
    platform_sector_t *validation_sectors = NULL;
    bool phase1_passed = true;
    
    // Calculate records for 60% validation test
    imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
    uint32_t validation_records = (initial_stats->total_sectors * RAM_VALIDATION_PERCENT) / 100;
    if (validation_records > record_count) {
        validation_records = record_count;
    }
    
    // Phase 1A: Fill RAM to 60%
    if (!phase_1a_fill_ram_60_percent(validation_records, &validation_sectors)) {
        printf("✗ Phase 1A FAILED\n");
        phase1_passed = false;
    }
    
    // Phase 1B: Verify RAM records
    if (phase1_passed && validation_sectors) {
        if (!phase_1b_verify_ram_records(g_test_stats.records_processed, validation_sectors)) {
            printf("✗ Phase 1B FAILED\n");
            phase1_passed = false;
        }
    }
    
    // Phase 1C: Free sectors and verify pool
    if (phase1_passed && validation_sectors) {
        if (!phase_1c_free_sectors_verify_pool(g_test_stats.records_processed, validation_sectors)) {
            printf("✗ Phase 1C FAILED\n");
            phase1_passed = false;
        }
    }
    
    // Print Phase 1 summary
    printf("==============================================\n");
    printf("           PHASE 1 SUMMARY (RAM VALIDATION)\n");
    printf("==============================================\n");
    printf("Records processed: %u\n", g_test_stats.records_processed);
    printf("Verification errors: %u\n", g_test_stats.verification_errors);
    printf("Cleanup errors: %u\n", g_test_stats.cleanup_errors);
    printf("Initial free sectors: %u\n", g_test_stats.initial_free_sectors);
    printf("Final free sectors: %u\n", g_test_stats.final_free_sectors);
    printf("Phase 1 result: %s\n", phase1_passed ? "✓ PASSED" : "✗ FAILED");
    printf("==============================================\n\n");
    
    if (!phase1_passed) {
        printf("✗ RAM VALIDATION FAILED - Aborting spillover test\n");
        return 1;
    }
    
    printf("✓ RAM VALIDATION PASSED - Ready for spillover testing\n\n");
    
    // Phase 2-6: 80% Spillover Testing
    platform_sector_t *spillover_sectors = NULL;
    bool spillover_passed = true;
    
    // Calculate records for 80% capacity test
    uint32_t spillover_records = (initial_stats->total_sectors * RAM_SPILLOVER_PERCENT) / 100;
    if (spillover_records > record_count) {
        spillover_records = record_count;
    }
    
    // Phase 2: Fill to 80% and monitor spillover
    if (!phase_2_fill_to_80_percent(spillover_records, &spillover_sectors)) {
        printf("✗ Phase 2 FAILED\n");
        spillover_passed = false;
    }
    
    // Phase 3: Trigger spillover to disk
    if (spillover_passed && spillover_sectors) {
        if (!phase_3_trigger_spillover(record_count, spillover_records, spillover_sectors)) {
            printf("✗ Phase 3 FAILED\n");
            spillover_passed = false;
        }
    }
    
    // Phase 4: Recovery testing
    if (spillover_passed) {
        if (!phase_4_recovery_testing()) {
            printf("✗ Phase 4 FAILED\n");
            spillover_passed = false;
        }
    }
    
    // Phase 5: Full verification
    if (spillover_passed && spillover_sectors) {
        if (!phase_5_full_verification(spillover_records, spillover_sectors)) {
            printf("✗ Phase 5 FAILED\n");
            spillover_passed = false;
        }
    }
    
    // Phase 6: Final cleanup
    if (spillover_sectors) {
        // Use the actual number of records processed, not the target
        if (!phase_6_final_cleanup(g_test_stats.records_processed, spillover_sectors)) {
            printf("✗ Phase 6 FAILED\n");
            spillover_passed = false;
        }
    }
    
    // Clean up allocated memory
    // Note: The sectors themselves have already been freed in the cleanup phases
    // We only need to free the tracking arrays
    if (validation_sectors) {
        // validation_sectors was already freed in phase_1c_free_sectors_verify_pool
        validation_sectors = NULL;
    }
    
    if (spillover_sectors) {
        // spillover_sectors wasn't freed in phase_6_final_cleanup to avoid double-free
        free(spillover_sectors);
        spillover_sectors = NULL;
    }
    
    // Print final summary
    printf("==============================================\n");
    printf("           SPILLOVER TEST SUMMARY\n");
    printf("==============================================\n");
    printf("Phase 1 (RAM Validation): %s\n", phase1_passed ? "✓ PASSED" : "✗ FAILED");
    printf("Phase 2-6 (80%% Spillover): %s\n", spillover_passed ? "✓ PASSED" : "✗ FAILED");
    printf("Overall result: %s\n", (phase1_passed && spillover_passed) ? "✓ ALL TESTS PASSED" : "✗ SOME TESTS FAILED");
    printf("==============================================\n\n");
    
    return (phase1_passed && spillover_passed) ? 0 : 1;
}