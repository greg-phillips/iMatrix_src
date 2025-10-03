/**
 * @file persistent_state.h
 * @brief Atomic State Persistence for Power-Off Recovery
 *
 * Implements Fleet-Connect style atomic state persistence to ensure
 * all dynamic variables survive unexpected power-off scenarios.
 */

#ifndef PERSISTENT_STATE_H
#define PERSISTENT_STATE_H

#include "platform_config.h"
#include <stdint.h>
#include <stdbool.h>

// Include unified_state.h for proper type definitions
#include "unified_state.h"

/******************************************************
 *              Persistence Constants
 ******************************************************/

#define PERSISTENT_STATE_MAGIC      0x53544154  // "STAT" - state file magic
#define PERSISTENT_STATE_VERSION    2           // Format version
#define MAX_PERSISTENT_STATES       256         // Maximum sensor states to persist

// Fleet-Connect style persistence paths
#ifdef TEST_ENVIRONMENT
    #define PERSISTENT_STATE_PATH       "FC_filesystem/history/state/"
    #define PERSISTENT_STATE_BACKUP     "FC_filesystem/history/state_backup/"
#else
    #define PERSISTENT_STATE_PATH       "/usr/qk/etc/sv/FC-1/history/state/"
    #define PERSISTENT_STATE_BACKUP     "/usr/qk/etc/sv/FC-1/history/state_backup/"
#endif

/******************************************************
 *            Persistent State Structure
 ******************************************************/

/**
 * @brief Atomic state snapshot for power-off recovery
 *
 * This structure contains all dynamic variables that must survive
 * power failures to enable complete state reconstruction.
 */
typedef struct __attribute__((packed)) {
    // Header
    uint32_t magic_marker;            // 0x53544154 ("STAT")
    uint16_t version;                 // Format version
    uint16_t state_size;              // Structure size for validation

    // Core counters (32-bit for high-volume capacity)
    uint32_t total_records;           // Total records written (atomic snapshot)
    uint32_t consumed_records;        // Records processed (atomic snapshot)
    uint32_t operation_sequence;      // Operation counter (atomic snapshot)

    // Sector chain information
    platform_sector_t first_sector;  // Chain start sector
    platform_sector_t active_sector; // Current write sector
    uint16_t sector_count;            // Total sectors in chain
    uint16_t records_in_active;       // Records in current sector

    // Metadata
    uint32_t sensor_id;               // Associated sensor ID
    uint32_t last_write_timestamp;    // Last operation timestamp
    uint8_t is_event_data;            // TSD vs EVENT type
    uint8_t is_initialized;           // Initialization flag
    uint16_t reserved;                // Future use

    // Integrity validation
    uint32_t state_checksum;          // Internal state checksum
    uint32_t file_checksum;           // Entire file checksum
} persistent_state_t;

/******************************************************
 *              Function Declarations
 ******************************************************/

/**
 * @brief Save unified state atomically to flash
 * @param state Unified sensor state to persist
 * @return MEMORY_SUCCESS on success, error code on failure
 */
memory_error_t save_state_atomically(const unified_sensor_state_t *state);

/**
 * @brief Restore unified state from flash
 * @param state Unified sensor state to restore into
 * @return MEMORY_SUCCESS on success, error code on failure
 */
memory_error_t restore_state_from_flash(unified_sensor_state_t *state);

/**
 * @brief Check if persistent state exists for sensor
 * @param sensor_id Sensor ID to check
 * @return true if persistent state exists
 */
bool persistent_state_exists(uint32_t sensor_id);

/**
 * @brief Delete persistent state file
 * @param sensor_id Sensor ID to delete state for
 * @return MEMORY_SUCCESS on success, error code on failure
 */
memory_error_t delete_persistent_state(uint32_t sensor_id);

/**
 * @brief Initialize persistence system
 * @return MEMORY_SUCCESS on success, error code on failure
 */
memory_error_t init_persistence_system(void);

/**
 * @brief Shutdown persistence system
 */
void shutdown_persistence_system(void);

/**
 * @brief Validate persistent state file integrity
 * @param persistent Persistent state structure to validate
 * @return true if valid, false if corrupted
 */
bool validate_persistent_state(const persistent_state_t *persistent);

/**
 * @brief Calculate checksum for persistent state
 * @param persistent Persistent state structure
 * @return Calculated checksum
 */
uint32_t calculate_persistent_checksum(const persistent_state_t *persistent);

#endif /* PERSISTENT_STATE_H */