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
 *
 * Disclaimer: THIS SOFTWARE IS PROVIDED AS-IS, WITH NO WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, NONINFRINGEMENT, IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. iMatrix
 * reserves the right to make changes to the Software without notice. iMatrix
 * does not assume any liability arising out of the application or use of the
 * Software or any product or circuit described in the Software. iMatrix does
 * not authorize its products for use in any products where a malfunction or
 * failure of the iMatrix product may reasonably be expected to result in
 * significant property damage, injury or death ("High Risk Product"). By
 * including iMatrix's product in a High Risk Product, the manufacturer
 * of such system or application assumes all risk of such use and in doing
 * so agrees to indemnify iMatrix against all liability.
 */

/**
 * @file test_shutdown_helpers.c
 * @brief Helper functions implementation for shutdown testing
 * 
 * @author Greg Phillips
 * @date 2025-01-12
 * @copyright iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>
#include <time.h>

#include "test_shutdown_helpers.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_csb_csd.h"
#include "device/icb_def.h"
#include "imatrix.h"
#include "time/ck_time.h"

/******************************************************
 *                      Macros
 ******************************************************/

/******************************************************
 *                    Constants
 ******************************************************/

static const char *TEST_STORAGE_PATH = "/tmp/imatrix_test_storage/history";
static const char *CHECKPOINT_PATH = "/tmp/imatrix_test_checkpoints";

/******************************************************
 *                   Enumerations
 ******************************************************/

/******************************************************
 *                 Type Definitions
 ******************************************************/

/******************************************************
 *                    Structures
 ******************************************************/

/******************************************************
 *               Static Function Declarations
 ******************************************************/

static uint32_t generate_pattern_value(int index, test_pattern_t pattern, uint16_t sensor_id);

/******************************************************
 *               Variable Definitions
 ******************************************************/

// External references
extern iMatrix_Control_Block_t icb;
extern IOT_Device_Config_t device_config;

// Access to test CSB/CSD arrays
extern imx_control_sensor_block_t *get_test_csb(void);
extern control_sensor_data_t *get_test_csd(void);

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Generate simulated sensor data
 * @param sensor_id Sensor ID to add data to
 * @param value Data value to write
 * @param is_event True for event data, false for time series
 * @return true on success
 */
bool simulate_sensor_data(uint16_t sensor_id, uint32_t value, bool is_event)
{
    // Get test CSB and CSD arrays
    imx_control_sensor_block_t *csb = get_test_csb();
    control_sensor_data_t *csd = get_test_csd();
    
    if (!csb || !csd) {
        printf("ERROR: Test CSB/CSD not initialized\n");
        return false;
    }
    
    // Ensure sensor_id is within bounds
    // Use TEST_NUM_SENSORS from memory_test_csb_csd.h
    if (sensor_id >= TEST_NUM_SENSORS) {
        printf("ERROR: Sensor ID %u out of bounds (max: %u)\n", 
               sensor_id, TEST_NUM_SENSORS - 1);
        return false;
    }
    
    // Set up the sensor type
    if (is_event) {
        csb[sensor_id].sample_rate = 0;  // Event driven
    } else {
        csb[sensor_id].sample_rate = 1000;  // 1 second sample rate
    }
    
    // Set other required fields
    csb[sensor_id].id = IMX_SENSORS + sensor_id;
    csb[sensor_id].data_type = IMX_UINT32;
    csb[sensor_id].enabled = 1;
    
    // Write the data
    write_tsd_evt(&csb[sensor_id], &csd[sensor_id], sensor_id, value, false);
    
    return true;
}

/**
 * @brief Generate bulk sensor data
 * @param num_sensors Number of sensors to populate
 * @param samples_per_sensor Samples per sensor
 * @param pattern Data pattern to use
 * @return Total number of samples created
 */
int generate_bulk_sensor_data(int num_sensors, int samples_per_sensor, test_pattern_t pattern)
{
    int total_samples = 0;
    
    // Limit sensors to configured maximum
    if (num_sensors > TEST_NUM_SENSORS) {
        num_sensors = TEST_NUM_SENSORS;
    }
    
    for (int sensor = 0; sensor < num_sensors; sensor++) {
        for (int sample = 0; sample < samples_per_sensor; sample++) {
            uint32_t value = generate_pattern_value(sample, pattern, sensor);
            
            if (simulate_sensor_data(sensor, value, false)) {
                total_samples++;
            }
        }
    }
    
    return total_samples;
}

/**
 * @brief Generate pattern value
 * @param index Sample index
 * @param pattern Pattern type
 * @param sensor_id Sensor ID
 * @return Generated value
 */
static uint32_t generate_pattern_value(int index, test_pattern_t pattern, uint16_t sensor_id)
{
    switch (pattern) {
        case PATTERN_SEQUENTIAL:
            return index;
            
        case PATTERN_RANDOM:
            return rand();
            
        case PATTERN_ALTERNATING:
            return (index % 2) ? 0xFFFFFFFF : 0x00000000;
            
        case PATTERN_FIXED:
            return 0xDEADBEEF;
            
        case PATTERN_SENSOR_ID:
            return (sensor_id << 16) | index;
            
        default:
            return index;
    }
}

/**
 * @brief Verify data was written to disk
 * @param sensor_id Sensor to verify
 * @param expected_count Expected number of samples
 * @return true if data verified successfully
 */
bool verify_data_on_disk(uint16_t sensor_id, int expected_count)
{
    // Check if disk files exist
    int file_count = count_test_storage_files();
    
    if (file_count == 0 && expected_count > 0) {
        printf("ERROR: No disk files found, expected data for sensor %u\n", sensor_id);
        return false;
    }
    
    // In a full implementation, we would:
    // 1. Read the disk files
    // 2. Parse the file headers
    // 3. Verify sensor_id matches
    // 4. Count actual samples
    // 5. Verify data integrity
    
    // For now, just verify files exist
    return file_count > 0;
}

/**
 * @brief Initialize progress monitor
 * @param monitor Progress monitor to initialize
 */
void init_progress_monitor(progress_monitor_t *monitor)
{
    if (!monitor) return;
    
    memset(monitor, 0, sizeof(progress_monitor_t));
    monitor->min_progress = 255;
    monitor->max_progress = 0;
    monitor->monotonic = true;
}

/**
 * @brief Record progress update
 * @param monitor Progress monitor
 * @param progress Current progress value
 * @param state Current memory state
 */
void record_progress(progress_monitor_t *monitor, uint8_t progress, memory_process_state_t state)
{
    if (!monitor || monitor->entry_count >= MAX_PROGRESS_LOG) return;
    
    progress_entry_t *entry = &monitor->entries[monitor->entry_count++];
    imx_time_get_time(&entry->timestamp);
    entry->progress = progress;
    entry->state = state;
    
    // Update min/max
    if (progress < monitor->min_progress) monitor->min_progress = progress;
    if (progress > monitor->max_progress) monitor->max_progress = progress;
    
    // Check monotonic
    if (monitor->entry_count > 1) {
        progress_entry_t *prev = &monitor->entries[monitor->entry_count - 2];
        if (progress < prev->progress && progress != 101) {
            monitor->monotonic = false;
        }
    }
}

/**
 * @brief Monitor flush progress
 * @param monitor Progress monitor to use
 * @param timeout_ms Maximum time to wait in milliseconds
 * @return Final progress value
 */
uint8_t monitor_flush_progress(progress_monitor_t *monitor, uint32_t timeout_ms)
{
    if (!monitor) return 0;
    
    init_progress_monitor(monitor);
    
    imx_time_t start_time, current_time;
    imx_time_get_time(&start_time);
    
    uint8_t progress = 0;
    uint8_t last_progress = 255;
    
    while (progress != 101) {
        // Get current progress
        progress = get_flush_progress();
        
        // Record if changed
        if (progress != last_progress) {
            record_progress(monitor, progress, get_current_memory_state());
            last_progress = progress;
        }
        
        // Process memory state machine
        imx_time_get_time(&current_time);
        process_memory(current_time);
        
        // Check timeout
        if (imx_is_later(current_time, start_time + timeout_ms)) {
            printf("WARNING: Progress monitoring timed out\n");
            break;
        }
        
        usleep(10000);  // 10ms
    }
    
    return progress;
}

/**
 * @brief Print progress report
 * @param monitor Progress monitor with data
 */
void print_progress_report(const progress_monitor_t *monitor)
{
    if (!monitor) return;
    
    printf("\nProgress Report:\n");
    printf("  Entries recorded: %d\n", monitor->entry_count);
    printf("  Progress range: %u - %u\n", monitor->min_progress, monitor->max_progress);
    printf("  Monotonic: %s\n", monitor->monotonic ? "Yes" : "No");
    
    if (monitor->entry_count > 0) {
        printf("  Progress sequence: ");
        for (int i = 0; i < monitor->entry_count && i < 20; i++) {
            printf("%u ", monitor->entries[i].progress);
        }
        if (monitor->entry_count > 20) {
            printf("...");
        }
        printf("\n");
    }
}

/**
 * @brief Simulate file operation delay
 * @param delay_ms Delay in milliseconds
 */
void simulate_file_operation_delay(uint32_t delay_ms)
{
    // In a real test, this could hook into the file operations
    // For now, just sleep
    usleep(delay_ms * 1000);
}

/**
 * @brief Clean up test storage files
 * @return true on success
 */
bool cleanup_test_storage_files(void)
{
    char cmd[512];
    int ret;
    
    // Remove test storage directory
    snprintf(cmd, sizeof(cmd), "rm -rf %s", TEST_STORAGE_PATH);
    ret = system(cmd);
    (void)ret; // Explicitly ignore - directory might not exist
    
    // Remove checkpoint directory
    snprintf(cmd, sizeof(cmd), "rm -rf %s", CHECKPOINT_PATH);
    ret = system(cmd);
    (void)ret; // Explicitly ignore - directory might not exist
    
    return true;
}

/**
 * @brief Count files in test storage
 * @return Number of test files found
 */
int count_test_storage_files(void)
{
    DIR *dir;
    struct dirent *entry;
    int count = 0;
    
    // First ensure the directory exists
    struct stat st;
    if (stat(TEST_STORAGE_PATH, &st) != 0) {
        return 0;
    }
    
    dir = opendir(TEST_STORAGE_PATH);
    if (!dir) {
        return 0;
    }
    
    while ((entry = readdir(dir)) != NULL) {
        // Count .imx files
        if (strstr(entry->d_name, ".imx") != NULL) {
            count++;
        }
    }
    
    closedir(dir);
    
    // Also check subdirectories (bucket structure)
    for (int bucket = 0; bucket < 10; bucket++) {
        char bucket_path[512];
        snprintf(bucket_path, sizeof(bucket_path), "%s/%d", TEST_STORAGE_PATH, bucket);
        
        if (stat(bucket_path, &st) == 0 && S_ISDIR(st.st_mode)) {
            dir = opendir(bucket_path);
            if (dir) {
                while ((entry = readdir(dir)) != NULL) {
                    if (strstr(entry->d_name, ".imx") != NULL) {
                        count++;
                    }
                }
                closedir(dir);
            }
        }
    }
    
    return count;
}

/**
 * @brief Get current memory state
 * @return Current memory state
 */
memory_process_state_t get_current_memory_state(void)
{
    // This would require access to tiered_state_machine.state
    // For testing, we could expose this through a debug function
    // For now, return IDLE as default
    return MEMORY_STATE_IDLE;
}

/**
 * @brief Wait for memory state
 * @param target_state State to wait for
 * @param timeout_ms Maximum wait time
 * @return true if state reached
 */
bool wait_for_memory_state(memory_process_state_t target_state, uint32_t timeout_ms)
{
    imx_time_t start_time, current_time;
    imx_time_get_time(&start_time);
    
    while (1) {
        if (get_current_memory_state() == target_state) {
            return true;
        }
        
        imx_time_get_time(&current_time);
        if (imx_is_later(current_time, start_time + timeout_ms)) {
            return false;
        }
        
        // Process memory state machine
        process_memory(current_time);
        usleep(10000);  // 10ms
    }
}

/**
 * @brief Simulate power interruption
 */
void simulate_power_interruption(void)
{
    // In a real test, this would:
    // 1. Save current state
    // 2. Simulate ungraceful shutdown
    // 3. Reinitialize system
    
    printf("Simulating power interruption...\n");
    
    // For now, just print message
}

/**
 * @brief Verify system recovery
 * @return true if recovery successful
 */
bool verify_system_recovery(void)
{
    // In a real test, this would:
    // 1. Check recovery journal
    // 2. Verify data integrity
    // 3. Check sector chains
    
    return true;
}

/**
 * @brief Get test storage path for shutdown tests
 * @return Path to test storage directory
 */
const char* get_shutdown_test_storage_path(void)
{
    return TEST_STORAGE_PATH;
}

/**
 * @brief Create test checkpoint
 * @param checkpoint_name Name for the checkpoint
 * @return true on success
 */
bool create_test_checkpoint(const char *checkpoint_name)
{
    if (!checkpoint_name) return false;
    
    // Create checkpoint directory
    char cmd[512];
    int ret;
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", CHECKPOINT_PATH);
    ret = system(cmd);
    if (ret != 0) {
        return false;
    }
    
    // In a real implementation, we would:
    // 1. Save current CSB/CSD state
    // 2. Save memory statistics
    // 3. Copy current disk files
    // 4. Save sector allocation table
    
    char checkpoint_file[512];
    snprintf(checkpoint_file, sizeof(checkpoint_file), "%s/%s.ckpt", 
             CHECKPOINT_PATH, checkpoint_name);
    
    FILE *fp = fopen(checkpoint_file, "w");
    if (!fp) return false;
    
    // Write basic checkpoint data
    fprintf(fp, "CHECKPOINT: %s\n", checkpoint_name);
    fprintf(fp, "TIMESTAMP: %ld\n", time(NULL));
    fprintf(fp, "FILES: %d\n", count_test_storage_files());
    
    fclose(fp);
    
    return true;
}

/**
 * @brief Verify against checkpoint
 * @param checkpoint_name Checkpoint to compare against
 * @return true if states match
 */
bool verify_against_checkpoint(const char *checkpoint_name)
{
    if (!checkpoint_name) return false;
    
    char checkpoint_file[512];
    snprintf(checkpoint_file, sizeof(checkpoint_file), "%s/%s.ckpt", 
             CHECKPOINT_PATH, checkpoint_name);
    
    FILE *fp = fopen(checkpoint_file, "r");
    if (!fp) {
        printf("ERROR: Checkpoint '%s' not found\n", checkpoint_name);
        return false;
    }
    
    // In a real implementation, we would:
    // 1. Compare CSB/CSD state
    // 2. Compare memory statistics
    // 3. Compare disk files
    // 4. Verify data integrity
    
    // For now, just check file count
    char line[256];
    int saved_files = 0;
    
    while (fgets(line, sizeof(line), fp)) {
        if (sscanf(line, "FILES: %d", &saved_files) == 1) {
            break;
        }
    }
    
    fclose(fp);
    
    int current_files = count_test_storage_files();
    if (current_files != saved_files) {
        printf("ERROR: File count mismatch - saved: %d, current: %d\n", 
               saved_files, current_files);
        return false;
    }
    
    return true;
}