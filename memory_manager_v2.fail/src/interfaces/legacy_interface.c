/**
 * @file legacy_interface.c
 * @brief Legacy Interface Compatibility Wrappers
 *
 * Provides backward compatibility with existing iMatrix memory management API
 * by wrapping the new unified corruption-proof implementation.
 */

#include "unified_state.h"
#include "data_storage.h"
#include "platform_config.h"
#include <stdio.h>
#include <string.h>

// Forward declarations for iMatrix types (simplified for testing)
typedef struct {
    uint16_t no_samples;
    uint16_t no_pending;
    // Simplified structure for testing
} control_sensor_data_t;

typedef struct {
    uint16_t id;
    // Simplified structure for testing
} imx_control_sensor_block_t;

// Global state storage for legacy compatibility
// In real integration, this would be managed differently
static unified_sensor_state_t legacy_states[256];
static bool legacy_states_initialized[256];

/******************************************************
 *            Legacy Function Implementations
 ******************************************************/

/**
 * @brief Initialize legacy state for a given entry
 */
static memory_error_t ensure_legacy_state_initialized(uint16_t entry)
{
    if (entry >= 256) {
        return MEMORY_ERROR_INVALID_PARAMETER;
    }

    if (!legacy_states_initialized[entry]) {
        memory_error_t result = init_unified_state_with_storage(&legacy_states[entry], false, 0x1000 + entry);
        if (result == MEMORY_SUCCESS) {
            legacy_states_initialized[entry] = true;
        }
        return result;
    }

    return MEMORY_SUCCESS;
}

/**
 * @brief Write TSD or EVT data to memory (legacy interface)
 */
void write_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry, uint32_t value, bool add_gps_location)
{
    (void)csb; // Unused parameter
    (void)add_gps_location; // Unused parameter

    if (!csd || entry >= 256) {
        platform_log_error("write_tsd_evt: Invalid parameters");
        return;
    }

    // Initialize state if needed
    if (ensure_legacy_state_initialized(entry) != MEMORY_SUCCESS) {
        platform_log_error("write_tsd_evt: Failed to initialize state");
        return;
    }

    // Get current UTC time (simplified for testing)
    uint32_t timestamp = 1704067200; // 2024-01-01 00:00:00 UTC

    // Call unified write operation
    memory_error_t result = write_tsd_evt_unified(&legacy_states[entry], value, timestamp);

    if (result == MEMORY_SUCCESS) {
        // Update legacy structure (simulate original behavior)
        csd->no_samples++;
        if (csd->no_pending > 0) {
            csd->no_pending--;
        }
    } else {
        platform_log_error("write_tsd_evt: Unified write failed");
    }
}

/**
 * @brief Read TSD or EVT data from memory (legacy interface)
 */
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value)
{
    (void)csb; // Unused parameter

    if (!csd || !value || entry >= 256) {
        platform_log_error("read_tsd_evt: Invalid parameters");
        if (value) *value = 0;
        return;
    }

    // Initialize state if needed
    if (ensure_legacy_state_initialized(entry) != MEMORY_SUCCESS) {
        platform_log_error("read_tsd_evt: Failed to initialize state");
        *value = 0;
        return;
    }

    // Call unified read operation
    uint32_t timestamp;
    memory_error_t result = read_tsd_evt_unified(&legacy_states[entry], value, &timestamp);

    if (result != MEMORY_SUCCESS) {
        platform_log_error("read_tsd_evt: Unified read failed");
        *value = 0;
    }
}

/**
 * @brief Erase TSD or EVT data entry (legacy interface)
 */
void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry)
{
    (void)csb; // Unused parameter

    if (!csd || entry >= 256) {
        platform_log_error("erase_tsd_evt: Invalid parameters");
        return;
    }

    // Initialize state if needed
    if (ensure_legacy_state_initialized(entry) != MEMORY_SUCCESS) {
        platform_log_error("erase_tsd_evt: Failed to initialize state");
        return;
    }

    // Call unified erase operation
    memory_error_t result = atomic_erase_records(&legacy_states[entry], 1);

    if (result == MEMORY_SUCCESS) {
        // Update legacy structure (simulate original behavior)
        if (csd->no_samples > 0) {
            csd->no_samples--;
        }
        csd->no_pending++;
    } else {
        platform_log_error("erase_tsd_evt: Unified erase failed");
    }
}
