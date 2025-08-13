/**
 * @file imatrix_stubs.c
 * @brief Stub implementations for external iMatrix dependencies
 * 
 * This file provides stub implementations ONLY for functions that are
 * external to the memory manager modules but required for linking the
 * test executables. It does NOT define any global variables that are
 * already defined in the memory manager modules.
 * 
 * @author Greg Phillips
 * @date 2025-01-08
 * @copyright iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

// Include headers for type definitions
#include "storage.h"
#include "cs_ctrl/memory_manager.h"
#include "cs_ctrl/memory_manager_internal.h"
#include "device/icb_def.h"
#include "imatrix.h"

/******************************************************
 *                 Console Output Stubs
 ******************************************************/

/**
 * @brief Printf implementation for iMatrix
 */
void imx_printf(char *format, ...) {
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
}

/**
 * @brief CLI print implementation
 */
void imx_cli_print(char *format, ...) {
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
}

/**
 * @brief CLI log printf implementation
 */
void imx_cli_log_printf(char *format, ...) {
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
}

/******************************************************
 *                 Configuration Stubs
 ******************************************************/

/**
 * @brief Save configuration stub
 */
void imatrix_save_config(void) { 
    // No-op for testing
}

/**
 * @brief Initialize configuration stub
 */
void imx_imatrix_init_config(void) { 
    // No-op for testing
}

// Default data stubs (empty arrays to avoid linking errors)
const int imx_controls_defaults[1] = {0};
const int imx_sensors_defaults[1] = {0};
const int imx_variables_defaults[1] = {0};

// Time-related globals for ck_time.c
int _daylight = 0;  // Daylight saving time flag
long _dstbias = 0;  // DST bias in seconds

/******************************************************
 *                    Time Stubs
 ******************************************************/

/**
 * @brief Get time stub - deprecated function
 */
void imx_get_time(void *time) { 
    // Deprecated - use imx_time_get_time
}

// imx_system_time_syncd is implemented in iMatrix/time/ck_time.c

/**
 * @brief Delay for specified milliseconds
 */
void imx_delay_milliseconds(uint32_t ms) { 
    usleep(ms * 1000); 
}

// imx_is_later is implemented in iMatrix/time/ck_time.c

/**
 * @brief Get current time in iMatrix format
 */
imx_result_t imx_time_get_time(imx_time_t *time_ptr) {
    if (time_ptr) {
        *time_ptr = (imx_time_t)time(NULL) * 1000; // Convert to milliseconds
    }
    return IMX_SUCCESS;
}

/**
 * @brief Get UTC time
 */
imx_result_t imx_time_get_utc_time(imx_utc_time_t *utc_time) { 
    if (utc_time) {
        *utc_time = (imx_utc_time_t)time(NULL); // Unix timestamp
    }
    return IMX_SUCCESS; 
}

/******************************************************
 *                    GPS Stubs
 ******************************************************/

/**
 * @brief Get GPS latitude
 */
float imx_get_latitude(void) { 
    return 40.7128f;  // New York City latitude
}

/**
 * @brief Get GPS longitude
 */
float imx_get_longitude(void) { 
    return -74.0060f; // New York City longitude
}

/**
 * @brief Get GPS altitude
 */
float imx_get_altitude(void) { 
    return 10.0f;     // 10 meters
}

/******************************************************
 *             CAN Bus Interface Stubs
 ******************************************************/

/**
 * @brief Get host sensor data pointer
 * Required by memory manager for sensor data access
 */
control_sensor_data_t *get_host_sd(void) {
    static control_sensor_data_t dummy_sd = {0};
    return &dummy_sd;
}

/**
 * @brief Get host sensor block pointer
 * Required by memory manager for sensor block access
 */
imx_control_sensor_block_t *get_host_sb(void) {
    static imx_control_sensor_block_t dummy_sb = {0};
    return &dummy_sb;
}

/**
 * @brief Get number of host sensors
 * Required by memory manager for sensor enumeration
 */
uint16_t get_host_no_sensors(void) {
    return 0; // No sensors for testing
}

/**
 * @brief Get number of host controls
 * Required by memory manager for control enumeration
 */
uint16_t get_host_no_controls(void) {
    return 0; // No controls for testing
}

/**
 * @brief Get host control data pointer
 * Required by memory manager for control data access
 */
control_sensor_data_t *get_host_cd(void) {
    static control_sensor_data_t dummy_cd = {0};
    return &dummy_cd;
}

/******************************************************
 *          Additional Required Function Stubs
 ******************************************************/

// Note: scan_disk_files is now implemented in memory_manager.c
// so we don't need a stub for it anymore

/**
 * @brief Get current test iteration number (weak implementation)
 * 
 * This is a weak default implementation that returns 0.
 * Tests that need iteration tracking (like comprehensive_memory_test)
 * can override this with their own implementation.
 * 
 * @return Always returns 0 for tests that don't track iterations
 */
__attribute__((weak)) int get_current_test_iteration(void)
{
    return 0;
}

/******************************************************
 *             Shutdown Test Support Functions
 ******************************************************/

// Note: Use imx_time_get_time() to get current time
// It's declared in imatrix.h and implemented in platform code

/**
 * @brief Allocate memory with calloc behavior
 * 
 * This is a wrapper around calloc used by iMatrix
 * 
 * @param size Size to allocate
 * @return Pointer to allocated memory or NULL
 */
void *imx_calloc_internal(size_t size)
{
    return calloc(1, size);
}

// imx_is_later is implemented in iMatrix/time/ck_time.c

// Note: The following functions are declared in memory_manager.h
// and implemented in memory_manager_tiered.c:
// - process_memory()
// - flush_all_to_disk()
// - get_flush_progress()
// - is_all_ram_empty()
// - cancel_memory_flush()

/******************************************************
 *             CAN Bus Related Stubs
 ******************************************************/

/**
 * @brief Check if CAN bus is registered
 * @return false for test environment
 */
bool canbus_registered(void) {
    return false; // No CAN bus in test environment
}

/**
 * @brief Get number of CAN controls
 * @return 0 for test environment
 */
uint16_t get_can_no_controls(void) {
    return 0;
}

/**
 * @brief Get number of CAN sensors
 * @return 0 for test environment
 */
uint16_t get_can_no_sensors(void) {
    return 0;
}

/**
 * @brief Get CAN control data pointer
 * @return NULL for test environment
 */
control_sensor_data_t *get_can_cd(void) {
    return NULL;
}

/**
 * @brief Get CAN sensor data pointer
 * @return NULL for test environment
 */
control_sensor_data_t *get_can_sd(void) {
    return NULL;
}