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
 * @file test_shutdown_helpers.h
 * @brief Helper functions for shutdown testing
 * 
 * This module provides common utilities used by shutdown tests including
 * data generation, verification, progress monitoring, and test environment
 * management.
 * 
 * @author Greg Phillips
 * @date 2025-01-12
 * @copyright iMatrix Systems, Inc.
 */

#ifndef TEST_SHUTDOWN_HELPERS_H_
#define TEST_SHUTDOWN_HELPERS_H_

#include <stdint.h>
#include <stdbool.h>
#include "storage.h"
#include "cs_ctrl/memory_manager.h"

/******************************************************
 *                      Macros
 ******************************************************/

/******************************************************
 *                    Constants
 ******************************************************/

#define MAX_TEST_FILENAME   256
#define MAX_PROGRESS_LOG    1000

/******************************************************
 *                   Enumerations
 ******************************************************/

/**
 * @brief Test data patterns for verification
 */
typedef enum {
    PATTERN_SEQUENTIAL,     /**< Sequential incrementing values */
    PATTERN_RANDOM,        /**< Random values */
    PATTERN_ALTERNATING,   /**< Alternating pattern */
    PATTERN_FIXED,         /**< Fixed value */
    PATTERN_SENSOR_ID      /**< Based on sensor ID */
} test_pattern_t;

/******************************************************
 *                 Type Definitions
 ******************************************************/

/**
 * @brief Progress tracking entry
 */
typedef struct {
    imx_time_t timestamp;
    uint8_t progress;
    memory_process_state_t state;
} progress_entry_t;

/**
 * @brief Progress monitor structure
 */
typedef struct {
    progress_entry_t entries[MAX_PROGRESS_LOG];
    int entry_count;
    uint8_t min_progress;
    uint8_t max_progress;
    bool monotonic;  /**< True if progress only increases */
} progress_monitor_t;

/******************************************************
 *                    Structures
 ******************************************************/

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Generate simulated sensor data
 * 
 * Creates test data for a specific sensor with various patterns
 * 
 * @param sensor_id Sensor ID to add data to
 * @param value Data value to write
 * @param is_event True for event data, false for time series
 * @return true on success
 */
bool simulate_sensor_data(uint16_t sensor_id, uint32_t value, bool is_event);

/**
 * @brief Generate bulk sensor data
 * 
 * Creates large amounts of test data across multiple sensors
 * 
 * @param num_sensors Number of sensors to populate
 * @param samples_per_sensor Samples per sensor
 * @param pattern Data pattern to use
 * @return Total number of samples created
 */
int generate_bulk_sensor_data(int num_sensors, int samples_per_sensor, test_pattern_t pattern);

/**
 * @brief Verify data was written to disk
 * 
 * Checks that sensor data was correctly persisted to disk storage
 * 
 * @param sensor_id Sensor to verify
 * @param expected_count Expected number of samples
 * @return true if data verified successfully
 */
bool verify_data_on_disk(uint16_t sensor_id, int expected_count);

/**
 * @brief Initialize progress monitor
 * 
 * @param monitor Progress monitor to initialize
 */
void init_progress_monitor(progress_monitor_t *monitor);

/**
 * @brief Record progress update
 * 
 * @param monitor Progress monitor
 * @param progress Current progress value
 * @param state Current memory state
 */
void record_progress(progress_monitor_t *monitor, uint8_t progress, memory_process_state_t state);

/**
 * @brief Monitor flush progress
 * 
 * Tracks and logs flush progress over time
 * 
 * @param monitor Progress monitor to use
 * @param timeout_ms Maximum time to wait in milliseconds
 * @return Final progress value
 */
uint8_t monitor_flush_progress(progress_monitor_t *monitor, uint32_t timeout_ms);

/**
 * @brief Print progress report
 * 
 * @param monitor Progress monitor with data
 */
void print_progress_report(const progress_monitor_t *monitor);

/**
 * @brief Simulate file operation delay
 * 
 * Introduces artificial delays to simulate slow file operations
 * 
 * @param delay_ms Delay in milliseconds
 */
void simulate_file_operation_delay(uint32_t delay_ms);

/**
 * @brief Clean up test storage files
 * 
 * Removes all test files and directories
 * 
 * @return true on success
 */
bool cleanup_test_storage_files(void);

/**
 * @brief Count files in test storage
 * 
 * @return Number of test files found
 */
int count_test_storage_files(void);

/**
 * @brief Get current memory state
 * 
 * Returns the current state of the memory state machine
 * Note: This may require access to internal state
 * 
 * @return Current memory state
 */
memory_process_state_t get_current_memory_state(void);

/**
 * @brief Wait for memory state
 * 
 * Waits for memory state machine to reach a specific state
 * 
 * @param target_state State to wait for
 * @param timeout_ms Maximum wait time
 * @return true if state reached
 */
bool wait_for_memory_state(memory_process_state_t target_state, uint32_t timeout_ms);

/**
 * @brief Simulate power interruption
 * 
 * Simulates a power failure during operation
 */
void simulate_power_interruption(void);

/**
 * @brief Verify system recovery
 * 
 * Checks that system recovered properly after interruption
 * 
 * @return true if recovery successful
 */
bool verify_system_recovery(void);

/**
 * @brief Get test storage path for shutdown tests
 * 
 * @return Path to test storage directory
 */
const char* get_shutdown_test_storage_path(void);

/**
 * @brief Create test checkpoint
 * 
 * Creates a checkpoint of current system state for comparison
 * 
 * @param checkpoint_name Name for the checkpoint
 * @return true on success
 */
bool create_test_checkpoint(const char *checkpoint_name);

/**
 * @brief Verify against checkpoint
 * 
 * Compares current state against a saved checkpoint
 * 
 * @param checkpoint_name Checkpoint to compare against
 * @return true if states match
 */
bool verify_against_checkpoint(const char *checkpoint_name);

#endif /* TEST_SHUTDOWN_HELPERS_H_ */