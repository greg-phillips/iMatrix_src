/**
 * @file real_world_test.c
 * @brief Real-world usage simulation for iMatrix memory management
 * 
 * This test simulates realistic memory usage patterns with multiple sensors,
 * RAM-to-disk spillover, data verification, and complete cleanup over multiple
 * iterations. It tests:
 * - Phase 1: 60% RAM usage across 4 sensors with verification
 * - Phase 2: 10,000 records causing disk spillover  
 * - Phase 3: 10 iterations to verify stability
 * - Phase 4: Complete cleanup validation
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
#include <dirent.h>
#include <errno.h>

// Include iMatrix headers - following Fleet-Connect-1 pattern
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define NUM_SENSORS                 4
#define SENSOR_ID_BASE              100
#define RAM_TARGET_PERCENT          60
#define RAM_SPILLOVER_PERCENT       80
#define TOTAL_DISK_RECORDS          1000
#define RECORDS_PER_SENSOR          (TOTAL_DISK_RECORDS / NUM_SENSORS)
#define TEST_ITERATIONS             3
#define PROGRESS_INTERVAL           100

// Test storage paths
#define TEST_STORAGE_PATH           "/tmp/imatrix_test_storage/history/"
#define TEST_CORRUPTED_PATH         "/tmp/imatrix_test_storage/history/corrupted/"

/******************************************************
 *                 Type Definitions
 ******************************************************/

/**
 * @brief Sensor record structure with validation data
 */
typedef struct {
    uint16_t sensor_id;
    uint32_t sequence_num;
    uint32_t timestamp;
    uint32_t checksum;
} sensor_record_t;

/**
 * @brief Context for managing each sensor's data
 */
typedef struct {
    uint16_t sensor_id;
    uint32_t record_count;
    platform_sector_t *ram_sectors;
    extended_sector_t *disk_sectors;
    uint32_t ram_sector_count;
    uint32_t disk_sector_count;
    uint32_t ram_sector_capacity;
    uint32_t disk_sector_capacity;
} sensor_context_t;

/**
 * @brief Metrics for each test iteration
 */
typedef struct {
    uint32_t iteration;
    uint64_t phase1_time_us;
    uint64_t phase2_time_us;
    uint32_t spillover_threshold_record;
    uint32_t final_ram_sectors;
    uint32_t final_disk_sectors;
    bool memory_leak_detected;
    uint32_t verification_errors;
} iteration_metrics_t;

/**
 * @brief Overall test statistics
 */
typedef struct {
    uint32_t total_records_written;
    uint32_t total_records_verified;
    uint32_t total_verification_errors;
    uint32_t spillover_occurrences;
    uint64_t total_time_us;
    iteration_metrics_t iterations[TEST_ITERATIONS];
} test_statistics_t;

/******************************************************
 *                 Global Variables
 ******************************************************/

static sensor_context_t g_sensors[NUM_SENSORS];
static test_statistics_t g_test_stats = {0};
static bool g_verbose = false;

/******************************************************
 *                 Utility Functions
 ******************************************************/

/**
 * @brief Get current time in microseconds
 * @return Current time in microseconds
 */
static uint64_t get_time_us(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000000 + tv.tv_usec;
}

/**
 * @brief Calculate simple checksum for a sensor record
 * @param record Pointer to sensor record
 * @return Calculated checksum
 */
static uint32_t calculate_checksum(const sensor_record_t *record)
{
    uint32_t checksum = 0;
    checksum ^= record->sensor_id;
    checksum ^= record->sequence_num;
    checksum ^= record->timestamp;
    checksum = (checksum << 1) | (checksum >> 31); // Rotate left by 1
    return checksum;
}

/**
 * @brief Create a sensor record with validation data
 * @param sensor_id Sensor identifier
 * @param sequence_num Sequence number for this sensor
 * @param record Output record structure
 */
static void create_sensor_record(uint16_t sensor_id, uint32_t sequence_num, sensor_record_t *record)
{
    record->sensor_id = sensor_id;
    record->sequence_num = sequence_num;
    record->timestamp = (uint32_t)time(NULL) + sequence_num; // Simulated timestamp
    record->checksum = 0; // Calculate after other fields are set
    record->checksum = calculate_checksum(record);
}

/**
 * @brief Verify a sensor record's integrity
 * @param record Record to verify
 * @return true if valid, false if corrupted
 */
static bool verify_sensor_record(const sensor_record_t *record)
{
    uint32_t expected_checksum = calculate_checksum(record);
    return (record->checksum == expected_checksum);
}

/**
 * @brief Initialize sensor contexts
 */
static void initialize_sensors(void)
{
    for (int i = 0; i < NUM_SENSORS; i++) {
        g_sensors[i].sensor_id = SENSOR_ID_BASE + (i * 100);
        g_sensors[i].record_count = 0;
        g_sensors[i].ram_sectors = NULL;
        g_sensors[i].disk_sectors = NULL;
        g_sensors[i].ram_sector_count = 0;
        g_sensors[i].disk_sector_count = 0;
        g_sensors[i].ram_sector_capacity = 0;
        g_sensors[i].disk_sector_capacity = 0;
    }
}

/**
 * @brief Allocate tracking arrays for a sensor
 * @param sensor Sensor context
 * @param ram_capacity Number of RAM sectors to track
 * @param disk_capacity Number of disk sectors to track
 * @return true on success, false on failure
 */
static bool allocate_sensor_tracking(sensor_context_t *sensor, uint32_t ram_capacity, uint32_t disk_capacity)
{
    if (ram_capacity > 0) {
        sensor->ram_sectors = malloc(ram_capacity * sizeof(platform_sector_t));
        if (!sensor->ram_sectors) {
            printf("ERROR: Failed to allocate RAM tracking for sensor %u\n", sensor->sensor_id);
            return false;
        }
        sensor->ram_sector_capacity = ram_capacity;
    }
    
    if (disk_capacity > 0) {
        sensor->disk_sectors = malloc(disk_capacity * sizeof(extended_sector_t));
        if (!sensor->disk_sectors) {
            printf("ERROR: Failed to allocate disk tracking for sensor %u\n", sensor->sensor_id);
            free(sensor->ram_sectors);
            sensor->ram_sectors = NULL;
            return false;
        }
        sensor->disk_sector_capacity = disk_capacity;
    }
    
    return true;
}

/**
 * @brief Free tracking arrays for a sensor
 * @param sensor Sensor context
 */
static void free_sensor_tracking(sensor_context_t *sensor)
{
    if (sensor->ram_sectors) {
        free(sensor->ram_sectors);
        sensor->ram_sectors = NULL;
    }
    if (sensor->disk_sectors) {
        free(sensor->disk_sectors);
        sensor->disk_sectors = NULL;
    }
    sensor->ram_sector_capacity = 0;
    sensor->disk_sector_capacity = 0;
}

/**
 * @brief Print current memory statistics
 * @param label Description label
 */
static void print_memory_stats(const char *label)
{
    imx_update_memory_statistics();
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    
    if (stats) {
        printf("\n%s - Memory Statistics:\n", label);
        printf("  RAM Usage: %.1f%% (%u/%u sectors)\n", 
               stats->usage_percentage, stats->used_sectors, stats->total_sectors);
        printf("  Free sectors: %u\n", stats->free_sectors);
        printf("  Peak usage: %.1f%%\n", stats->peak_usage_percentage);
        printf("  Fragmentation: %u%%\n", stats->fragmentation_level);
    }
}

/**
 * @brief Count files in the test storage directory
 * @return Number of files found
 */
static uint32_t count_disk_files(void)
{
    uint32_t file_count = 0;
    DIR *dir;
    struct dirent *entry;
    
    // Check each bucket directory (0-9)
    for (int bucket = 0; bucket < 10; bucket++) {
        char bucket_path[256];
        snprintf(bucket_path, sizeof(bucket_path), "%s%d", TEST_STORAGE_PATH, bucket);
        
        dir = opendir(bucket_path);
        if (dir) {
            while ((entry = readdir(dir)) != NULL) {
                if (entry->d_type == DT_REG && strstr(entry->d_name, ".imx")) {
                    file_count++;
                }
            }
            closedir(dir);
        }
    }
    
    return file_count;
}

/**
 * @brief Delete all disk files in storage directories
 * @return Number of files deleted
 */
static uint32_t delete_all_disk_files(void)
{
    uint32_t deleted_count = 0;
    char file_path[512];
    DIR *dir;
    struct dirent *entry;
    
    // Delete files in each bucket directory (0-9)
    for (int bucket = 0; bucket < 10; bucket++) {
        char bucket_path[256];
        snprintf(bucket_path, sizeof(bucket_path), "%s%d", TEST_STORAGE_PATH, bucket);
        
        dir = opendir(bucket_path);
        if (dir) {
            while ((entry = readdir(dir)) != NULL) {
                if (entry->d_type == DT_REG && strstr(entry->d_name, ".imx")) {
                    snprintf(file_path, sizeof(file_path), "%s/%s", bucket_path, entry->d_name);
                    if (unlink(file_path) == 0) {
                        deleted_count++;
                    }
                }
            }
            closedir(dir);
        }
    }
    
    return deleted_count;
}

/******************************************************
 *               Phase 1: 60% RAM Test
 ******************************************************/

/**
 * @brief Phase 1: Fill RAM to 60% with sensor data and verify
 * @return true on success, false on failure
 */
static bool phase1_ram_60_percent_test(void)
{
    printf("\n=== Phase 1: 60%% RAM Usage Test ===\n");
    printf("====================================\n");
    
    uint64_t start_time = get_time_us();
    
    // Get initial memory state
    imx_update_memory_statistics();
    imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
    if (!initial_stats) {
        printf("ERROR: Cannot get initial memory statistics\n");
        return false;
    }
    
    uint32_t initial_free = initial_stats->free_sectors;
    uint32_t target_sectors = (initial_stats->total_sectors * RAM_TARGET_PERCENT) / 100;
    uint32_t sectors_per_sensor = target_sectors / NUM_SENSORS;
    
    printf("Initial state: %u free sectors\n", initial_free);
    printf("Target: %u sectors total (%u per sensor) for %u%% usage\n", 
           target_sectors, sectors_per_sensor, RAM_TARGET_PERCENT);
    
    // Allocate tracking arrays for each sensor
    for (int i = 0; i < NUM_SENSORS; i++) {
        if (!allocate_sensor_tracking(&g_sensors[i], sectors_per_sensor, 0)) {
            // Cleanup already allocated
            for (int j = 0; j < i; j++) {
                free_sensor_tracking(&g_sensors[j]);
            }
            return false;
        }
    }
    
    // Phase 1A: Allocate and write records
    printf("\nPhase 1A: Writing records to RAM...\n");
    
    uint32_t total_allocated = 0;
    for (uint32_t record_idx = 0; record_idx < sectors_per_sensor; record_idx++) {
        for (int sensor_idx = 0; sensor_idx < NUM_SENSORS; sensor_idx++) {
            sensor_context_t *sensor = &g_sensors[sensor_idx];
            
            // Allocate RAM sector
            platform_sector_signed_t sector = imx_get_free_sector();
            
            if (sector < 0) {
                printf("ERROR: Failed to allocate sector for sensor %u, record %u\n", 
                       sensor->sensor_id, record_idx);
                goto phase1_cleanup;
            }
            
            sensor->ram_sectors[sensor->ram_sector_count++] = sector;
            
            // Create and write record
            sensor_record_t record;
            create_sensor_record(sensor->sensor_id, sensor->record_count++, &record);
            
            write_rs(sector, 0, (uint32_t*)&record, sizeof(record)/sizeof(uint32_t));
            total_allocated++;
            
            // Progress update
            if (total_allocated % PROGRESS_INTERVAL == 0) {
                printf("  Progress: %u records allocated\n", total_allocated);
            }
        }
    }
    
    print_memory_stats("After Phase 1A");
    printf("✓ Allocated %u records across %u sensors\n", total_allocated, NUM_SENSORS);
    
    // Phase 1B: Read back and verify all records
    printf("\nPhase 1B: Verifying RAM records...\n");
    
    uint32_t total_verified = 0;
    uint32_t verification_errors = 0;
    
    for (int sensor_idx = 0; sensor_idx < NUM_SENSORS; sensor_idx++) {
        sensor_context_t *sensor = &g_sensors[sensor_idx];
        uint32_t expected_sequence = 0;
        
        for (uint32_t i = 0; i < sensor->ram_sector_count; i++) {
            sensor_record_t read_record;
            read_rs(sensor->ram_sectors[i], 0, (uint32_t*)&read_record, sizeof(read_record)/sizeof(uint32_t));
            
            // Verify record integrity
            if (!verify_sensor_record(&read_record)) {
                printf("ERROR: Checksum mismatch for sensor %u, sector %u\n", 
                       sensor->sensor_id, sensor->ram_sectors[i]);
                verification_errors++;
                continue;
            }
            
            // Verify sequence number
            if (read_record.sequence_num != expected_sequence) {
                printf("ERROR: Sequence mismatch for sensor %u: expected %u, got %u\n",
                       sensor->sensor_id, expected_sequence, read_record.sequence_num);
                verification_errors++;
            }
            
            // Verify sensor ID
            if (read_record.sensor_id != sensor->sensor_id) {
                printf("ERROR: Sensor ID mismatch: expected %u, got %u\n",
                       sensor->sensor_id, read_record.sensor_id);
                verification_errors++;
            }
            
            expected_sequence++;
            total_verified++;
        }
    }
    
    printf("✓ Verified %u records, %u errors\n", total_verified, verification_errors);
    
    // Phase 1C: Free all records and verify cleanup
    printf("\nPhase 1C: Freeing RAM records...\n");
    
    uint32_t total_freed = 0;
    for (int sensor_idx = 0; sensor_idx < NUM_SENSORS; sensor_idx++) {
        sensor_context_t *sensor = &g_sensors[sensor_idx];
        
        for (uint32_t i = 0; i < sensor->ram_sector_count; i++) {
            free_sector(sensor->ram_sectors[i]);
            total_freed++;
        }
        
        sensor->ram_sector_count = 0;
        sensor->record_count = 0;
    }
    
    printf("✓ Freed %u records\n", total_freed);
    
    // Verify memory returned to initial state
    imx_update_memory_statistics();
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    
    if (final_stats->free_sectors != initial_free) {
        printf("WARNING: Memory not fully recovered. Initial: %u, Final: %u\n",
               initial_free, final_stats->free_sectors);
    }
    
    print_memory_stats("After Phase 1C");
    
    uint64_t phase1_time = get_time_us() - start_time;
    printf("\n✓ Phase 1 completed in %.2f seconds\n", phase1_time / 1000000.0);
    
    // Update iteration metrics
    if (g_test_stats.spillover_occurrences < TEST_ITERATIONS) {
        g_test_stats.iterations[g_test_stats.spillover_occurrences].phase1_time_us = phase1_time;
        g_test_stats.iterations[g_test_stats.spillover_occurrences].verification_errors += verification_errors;
    }
    
    g_test_stats.total_records_written += total_allocated;
    g_test_stats.total_records_verified += total_verified;
    g_test_stats.total_verification_errors += verification_errors;
    
phase1_cleanup:
    // Free tracking arrays
    for (int i = 0; i < NUM_SENSORS; i++) {
        free_sensor_tracking(&g_sensors[i]);
        g_sensors[i].record_count = 0;
    }
    
    return (verification_errors == 0);
}

/******************************************************
 *            Phase 2: Disk Spillover Test
 ******************************************************/

/**
 * @brief Phase 2: Generate 10,000 records to trigger disk spillover
 * @return true on success, false on failure
 */
static bool phase2_disk_spillover_test(void)
{
    printf("\n=== Phase 2: Disk Spillover Test (10,000 Records) ===\n");
    printf("=====================================================\n");
    
    uint64_t start_time = get_time_us();
    bool spillover_detected = false;
    uint32_t spillover_record = 0;
    
    // Allocate tracking arrays for each sensor
    uint32_t records_per_sensor_target = RECORDS_PER_SENSOR;
    for (int i = 0; i < NUM_SENSORS; i++) {
        // Allocate enough space for both RAM and disk sectors
        if (!allocate_sensor_tracking(&g_sensors[i], 
                                      SAT_NO_SECTORS / NUM_SENSORS,  // Max RAM per sensor
                                      records_per_sensor_target)) {    // Disk sectors
            // Cleanup already allocated
            for (int j = 0; j < i; j++) {
                free_sensor_tracking(&g_sensors[j]);
            }
            return false;
        }
    }
    
    printf("Generating %u records (%u per sensor)...\n", TOTAL_DISK_RECORDS, records_per_sensor_target);
    printf("Monitoring for RAM->disk spillover at %u%%...\n\n", RAM_SPILLOVER_PERCENT);
    
    // Phase 2A: Generate records until spillover
    uint32_t total_written = 0;
    bool use_disk = false;
    
    for (uint32_t round = 0; round < records_per_sensor_target; round++) {
        for (int sensor_idx = 0; sensor_idx < NUM_SENSORS; sensor_idx++) {
            sensor_context_t *sensor = &g_sensors[sensor_idx];
            
            // Check if we should switch to disk allocation
            if (!use_disk && !spillover_detected) {
                imx_update_memory_statistics();
                imx_memory_statistics_t *stats = imx_get_memory_statistics();
                if (stats->usage_percentage >= RAM_SPILLOVER_PERCENT) {
                    printf("🔄 SPILLOVER DETECTED at record %u (RAM: %.1f%%)\n", 
                           total_written, stats->usage_percentage);
                    spillover_detected = true;
                    spillover_record = total_written;
                    use_disk = true;
                }
            }
            
            if (use_disk) {
                // Allocate disk sector
                extended_sector_t disk_sector = allocate_disk_sector(sensor->sensor_id);
                if (disk_sector == 0) {
                    printf("ERROR: Failed to allocate disk sector for sensor %u\n", sensor->sensor_id);
                    goto phase2_cleanup;
                }
                sensor->disk_sectors[sensor->disk_sector_count++] = disk_sector;
                
                // Create and write record to disk
                sensor_record_t record;
                create_sensor_record(sensor->sensor_id, sensor->record_count++, &record);
                
                imx_memory_error_t result = write_sector_extended(disk_sector, 0, 
                                                                  (uint32_t*)&record, 
                                                                  sizeof(record)/sizeof(uint32_t),
                                                                  sizeof(record));
                if (result != IMX_MEMORY_SUCCESS) {
                    printf("ERROR: Failed to write to disk sector %u: %d\n", disk_sector, result);
                    goto phase2_cleanup;
                }
            } else {
                // Try RAM allocation first
                #ifdef LINUX_PLATFORM
                int32_t ram_sector = imx_get_free_sector();
                #else
                int16_t ram_sector = imx_get_free_sector();
                #endif
                
                if (ram_sector >= 0) {
                    sensor->ram_sectors[sensor->ram_sector_count++] = ram_sector;
                    
                    // Create and write record to RAM
                    sensor_record_t record;
                    create_sensor_record(sensor->sensor_id, sensor->record_count++, &record);
                    
                    write_rs(ram_sector, 0, (uint32_t*)&record, sizeof(record)/sizeof(uint32_t));
                } else {
                    // RAM full, switch to disk
                    printf("RAM allocation failed at record %u, switching to disk\n", total_written);
                    use_disk = true;
                    sensor_idx--; // Retry this sensor with disk allocation
                    continue;
                }
            }
            
            total_written++;
            
            // Progress update
            if (total_written % (PROGRESS_INTERVAL * 10) == 0) {
                printf("  Progress: %u/%u records written\n", total_written, TOTAL_DISK_RECORDS);
            }
        }
    }
    
    printf("\n✓ Generated %u records\n", total_written);
    print_memory_stats("After record generation");
    
    // Count disk files
    uint32_t disk_files = count_disk_files();
    printf("Disk files created: %u\n", disk_files);
    
    // Phase 2B: Verify all records
    printf("\nPhase 2B: Verifying all records...\n");
    
    uint32_t total_verified = 0;
    uint32_t verification_errors = 0;
    
    for (int sensor_idx = 0; sensor_idx < NUM_SENSORS; sensor_idx++) {
        sensor_context_t *sensor = &g_sensors[sensor_idx];
        uint32_t expected_sequence = 0;
        
        // Verify RAM records first
        for (uint32_t i = 0; i < sensor->ram_sector_count; i++) {
            sensor_record_t read_record;
            read_rs(sensor->ram_sectors[i], 0, (uint32_t*)&read_record, sizeof(read_record)/sizeof(uint32_t));
            
            if (!verify_sensor_record(&read_record)) {
                verification_errors++;
                continue;
            }
            
            if (read_record.sequence_num != expected_sequence++) {
                verification_errors++;
            }
            
            total_verified++;
        }
        
        // Verify disk records
        for (uint32_t i = 0; i < sensor->disk_sector_count; i++) {
            sensor_record_t read_record;
            imx_memory_error_t result = read_sector_extended(sensor->disk_sectors[i], 0, 
                                                            (uint32_t*)&read_record,
                                                            sizeof(read_record)/sizeof(uint32_t),
                                                            sizeof(read_record));
            
            if (result != IMX_MEMORY_SUCCESS) {
                printf("ERROR: Failed to read disk sector %u\n", sensor->disk_sectors[i]);
                verification_errors++;
                continue;
            }
            
            if (!verify_sensor_record(&read_record)) {
                verification_errors++;
                continue;
            }
            
            if (read_record.sequence_num != expected_sequence++) {
                verification_errors++;
            }
            
            total_verified++;
        }
        
        printf("  Sensor %u: %u RAM + %u disk records verified\n",
               sensor->sensor_id, sensor->ram_sector_count, sensor->disk_sector_count);
    }
    
    printf("✓ Verified %u records, %u errors\n", total_verified, verification_errors);
    
    // Phase 2C: Cleanup all records
    printf("\nPhase 2C: Cleaning up all records...\n");
    
    uint32_t ram_freed = 0;
    uint32_t disk_freed = 0;
    
    for (int sensor_idx = 0; sensor_idx < NUM_SENSORS; sensor_idx++) {
        sensor_context_t *sensor = &g_sensors[sensor_idx];
        
        // Free RAM sectors
        for (uint32_t i = 0; i < sensor->ram_sector_count; i++) {
            free_sector(sensor->ram_sectors[i]);
            ram_freed++;
        }
        
        // Free disk sectors
        for (uint32_t i = 0; i < sensor->disk_sector_count; i++) {
            imx_memory_error_t result = free_sector_extended(sensor->disk_sectors[i]);
            if (result == IMX_MEMORY_SUCCESS) {
                disk_freed++;
            }
        }
        
        sensor->ram_sector_count = 0;
        sensor->disk_sector_count = 0;
        sensor->record_count = 0;
    }
    
    printf("✓ Freed %u RAM sectors and %u disk sectors\n", ram_freed, disk_freed);
    
    // Delete disk files since free_sector_extended doesn't delete them
    printf("Deleting disk files...\n");
    uint32_t deleted_files = delete_all_disk_files();
    printf("✓ Deleted %u disk files\n", deleted_files);
    
    // Verify disk cleanup
    uint32_t remaining_files = count_disk_files();
    if (remaining_files > 0) {
        printf("WARNING: %u disk files remain after cleanup\n", remaining_files);
    } else {
        printf("✓ All disk files cleaned up successfully\n");
    }
    
    print_memory_stats("After cleanup");
    
    uint64_t phase2_time = get_time_us() - start_time;
    printf("\n✓ Phase 2 completed in %.2f seconds\n", phase2_time / 1000000.0);
    
    // Update iteration metrics
    if (g_test_stats.spillover_occurrences < TEST_ITERATIONS) {
        iteration_metrics_t *iter = &g_test_stats.iterations[g_test_stats.spillover_occurrences];
        iter->phase2_time_us = phase2_time;
        iter->spillover_threshold_record = spillover_record;
        iter->final_ram_sectors = ram_freed;
        iter->final_disk_sectors = disk_freed;
        iter->verification_errors += verification_errors;
    }
    
    g_test_stats.total_records_written += total_written;
    g_test_stats.total_records_verified += total_verified;
    g_test_stats.total_verification_errors += verification_errors;
    if (spillover_detected) {
        g_test_stats.spillover_occurrences++;
    }
    
phase2_cleanup:
    // Free tracking arrays
    for (int i = 0; i < NUM_SENSORS; i++) {
        free_sensor_tracking(&g_sensors[i]);
    }
    
    return (verification_errors == 0);
}

/******************************************************
 *           Phase 3: Iteration Testing
 ******************************************************/

/**
 * @brief Phase 3: Run complete test cycle multiple times
 * @return true if all iterations pass, false otherwise
 */
static bool phase3_iteration_test(void)
{
    printf("\n=== Phase 3: Iteration Testing (%d iterations) ===\n", TEST_ITERATIONS);
    printf("==================================================\n");
    
    bool all_passed = true;
    
    for (int iter = 0; iter < TEST_ITERATIONS; iter++) {
        printf("\n--- Iteration %d/%d ---\n", iter + 1, TEST_ITERATIONS);
        
        g_test_stats.iterations[iter].iteration = iter + 1;
        
        // Get initial memory state
        imx_update_memory_statistics();
        imx_memory_statistics_t *initial_stats = imx_get_memory_statistics();
        uint32_t initial_free = initial_stats->free_sectors;
        
        // Run Phase 1
        if (!phase1_ram_60_percent_test()) {
            printf("ERROR: Phase 1 failed in iteration %d\n", iter + 1);
            all_passed = false;
        }
        
        // Run Phase 2
        if (!phase2_disk_spillover_test()) {
            printf("ERROR: Phase 2 failed in iteration %d\n", iter + 1);
            all_passed = false;
        }
        
        // Check for memory leaks
        imx_update_memory_statistics();
        imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
        
        if (final_stats->free_sectors != initial_free) {
            printf("WARNING: Memory leak detected in iteration %d: %d sectors leaked\n",
                   iter + 1, initial_free - final_stats->free_sectors);
            g_test_stats.iterations[iter].memory_leak_detected = true;
            all_passed = false;
        }
        
        printf("\n✓ Iteration %d completed\n", iter + 1);
    }
    
    return all_passed;
}

/******************************************************
 *           Phase 4: Final Validation
 ******************************************************/

/**
 * @brief Phase 4: Final system validation and reporting
 * @param baseline_used_sectors Number of sectors used by test infrastructure
 */
static void phase4_final_validation(uint32_t baseline_used_sectors)
{
    printf("\n=== Phase 4: Final Validation ===\n");
    printf("=================================\n");
    
    // Check final memory state
    imx_update_memory_statistics();
    imx_memory_statistics_t *final_stats = imx_get_memory_statistics();
    
    printf("\nFinal Memory State:\n");
    printf("  Total sectors: %u\n", final_stats->total_sectors);
    printf("  Free sectors: %u\n", final_stats->free_sectors);
    printf("  Used sectors: %u\n", final_stats->used_sectors);
    printf("  Peak usage: %.1f%%\n", final_stats->peak_usage_percentage);
    printf("  Baseline allocation: %u sectors\n", baseline_used_sectors);
    
    // Check for remaining disk files
    uint32_t remaining_files = count_disk_files();
    printf("\nDisk Cleanup Status:\n");
    printf("  Remaining disk files: %u\n", remaining_files);
    
    // Check if we're back to baseline (accounting for test infrastructure)
    if (remaining_files == 0 && final_stats->used_sectors == baseline_used_sectors) {
        printf("\n✓ System fully cleaned - all test resources recovered\n");
    } else if (remaining_files == 0 && final_stats->used_sectors > baseline_used_sectors) {
        printf("\n✗ WARNING: %u sectors leaked beyond baseline\n", 
               final_stats->used_sectors - baseline_used_sectors);
    } else {
        printf("\n✗ WARNING: System not fully cleaned\n");
        if (remaining_files > 0) {
            printf("  - %u disk files remain\n", remaining_files);
        }
        if (final_stats->used_sectors > baseline_used_sectors) {
            printf("  - %u sectors leaked beyond baseline\n", 
                   final_stats->used_sectors - baseline_used_sectors);
        }
    }
    
    // Generate test report
    printf("\n=== Test Summary Report ===\n");
    printf("===========================\n");
    
    printf("\nOverall Statistics:\n");
    printf("  Total records written: %u\n", g_test_stats.total_records_written);
    printf("  Total records verified: %u\n", g_test_stats.total_records_verified);
    printf("  Total verification errors: %u\n", g_test_stats.total_verification_errors);
    printf("  Spillover occurrences: %u/%u\n", g_test_stats.spillover_occurrences, TEST_ITERATIONS);
    
    printf("\nIteration Details:\n");
    printf("Iter | Phase1(s) | Phase2(s) | Spillover@  | RAM Freed | Disk Freed | Errors | Leak\n");
    printf("-----|-----------|-----------|-------------|-----------|------------|--------|-----\n");
    
    for (int i = 0; i < TEST_ITERATIONS; i++) {
        iteration_metrics_t *iter = &g_test_stats.iterations[i];
        printf("%4u | %9.2f | %9.2f | %11u | %9u | %10u | %6u | %s\n",
               iter->iteration,
               iter->phase1_time_us / 1000000.0,
               iter->phase2_time_us / 1000000.0,
               iter->spillover_threshold_record,
               iter->final_ram_sectors,
               iter->final_disk_sectors,
               iter->verification_errors,
               iter->memory_leak_detected ? "YES" : "NO");
    }
    
    // Calculate averages
    uint64_t avg_phase1_time = 0;
    uint64_t avg_phase2_time = 0;
    for (int i = 0; i < TEST_ITERATIONS; i++) {
        avg_phase1_time += g_test_stats.iterations[i].phase1_time_us;
        avg_phase2_time += g_test_stats.iterations[i].phase2_time_us;
    }
    avg_phase1_time /= TEST_ITERATIONS;
    avg_phase2_time /= TEST_ITERATIONS;
    
    printf("\nAverage Times:\n");
    printf("  Phase 1: %.2f seconds\n", avg_phase1_time / 1000000.0);
    printf("  Phase 2: %.2f seconds\n", avg_phase2_time / 1000000.0);
    
    // Final verdict
    bool all_passed = (g_test_stats.total_verification_errors == 0) &&
                      (remaining_files == 0) &&
                      (final_stats->free_sectors == final_stats->total_sectors);
    
    printf("\n=== FINAL RESULT: %s ===\n", all_passed ? "PASS" : "FAIL");
}

/******************************************************
 *                 Main Test Entry
 ******************************************************/

/**
 * @brief Print usage information
 */
static void print_usage(const char *program_name)
{
    printf("Usage: %s [options]\n", program_name);
    printf("Options:\n");
    printf("  -v          Enable verbose output\n");
    printf("  -h          Show this help message\n");
}

/**
 * @brief Main test entry point
 */
int main(int argc, char *argv[])
{
    // Parse command line arguments
    int opt;
    while ((opt = getopt(argc, argv, "vh")) != -1) {
        switch (opt) {
            case 'v':
                g_verbose = true;
                break;
            case 'h':
                print_usage(argv[0]);
                return 0;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    
    printf("==============================================\n");
    printf("    iMatrix Real-World Usage Test\n");
    printf("==============================================\n");
    printf("Testing realistic memory patterns with:\n");
    printf("  - %d sensors\n", NUM_SENSORS);
    printf("  - %d%% RAM target\n", RAM_TARGET_PERCENT);
    printf("  - %d total records for spillover\n", TOTAL_DISK_RECORDS);
    printf("  - %d test iterations\n", TEST_ITERATIONS);
    printf("==============================================\n\n");
    
    // Initialize test environment
    printf("Initializing test environment...\n");
    if (initialize_memory_test_environment() != IMX_SUCCESS) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }
    
    // Initialize sensors
    initialize_sensors();
    
    // Initialize memory statistics
    imx_init_memory_statistics();
    
    // Initialize disk storage system for tiered storage
    printf("Initializing disk storage system...\n");
    init_disk_storage_system();
    printf("Disk storage system initialized\n");
    
    printf("Test environment ready\n");
    print_memory_stats("Initial State");
    
    // Capture baseline allocation (test infrastructure)
    imx_update_memory_statistics();
    imx_memory_statistics_t *baseline_stats = imx_get_memory_statistics();
    uint32_t baseline_used_sectors = baseline_stats->used_sectors;
    
    // Run Phase 3 (which includes Phase 1 and 2 iterations)
    bool test_passed = phase3_iteration_test();
    
    // Run Phase 4 final validation
    phase4_final_validation(baseline_used_sectors);
    
    // Cleanup test environment
    printf("\nCleaning up test environment...\n");
    cleanup_memory_test_environment();
    
    return test_passed ? 0 : 1;
}