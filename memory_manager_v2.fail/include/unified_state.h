/**
 * @file unified_state.h
 * @brief Unified Sensor State Management
 *
 * Corruption-proof state management with mathematical invariants
 * and platform-adaptive implementation.
 */

#ifndef UNIFIED_STATE_H
#define UNIFIED_STATE_H

#include "platform_config.h"
#include <stdint.h>
#include <stdbool.h>

/******************************************************
 *              Core State Structure
 ******************************************************/

/**
 * @brief Unified sensor state structure (corruption-proof by design)
 *
 * This structure replaces the problematic separate counter system
 * with a mathematically consistent unified approach.
 */
typedef struct {
    // ATOMIC COUNTER GROUP (Single source of truth) - 32-bit for high-volume capacity
    uint32_t total_records;             // Total records written (monotonic, never decreases) - 4.3B capacity
    uint32_t consumed_records;          // Records confirmed processed and erasable - 4.3B capacity
    uint32_t operation_sequence;        // Rolling operation counter for ordering

    // DERIVED VALUES (Calculated from atomic counters)
    // available_records = total_records - consumed_records
    // read_position = consumed_records
    // pending_records = (external tracking only, not stored)

    // PLATFORM-ADAPTIVE STORAGE
    #ifdef LINUX_PLATFORM
        platform_sector_t first_sector;     // Start of sector chain
        platform_sector_t active_sector;    // Current write sector
        uint16_t sector_count;               // Sectors in chain
        uint16_t records_in_active;          // Records in current sector

        // DISK FILE TRACKING (for complete lifecycle management)
        char disk_files[100][256];           // Track disk overflow files
        uint16_t disk_file_count;            // Number of disk files created
        uint32_t disk_records_total;         // Total records in all disk files
        uint16_t current_disk_file_index;    // Current file being read/erased
        uint32_t current_disk_record_pos;    // Position in current disk file
        uint16_t records_per_disk_file;      // Records per disk file (16384)

        // HYBRID MODE TRACKING
        mode_state_t mode_state;             // Current mode and transition tracking
        char disk_base_path[256];            // Base path for disk storage
        uint32_t disk_sector_count;          // Total sectors on disk
        uint32_t current_consumption_sector; // Sector currently being consumed
        bool disk_files_exist;               // Disk files detected on startup
        uint32_t ram_sectors_allocated;      // Current RAM sectors in use
        uint32_t max_ram_sectors;            // Maximum RAM sectors before flush
        uint64_t last_mode_switch_time;      // Timestamp of last mode change
        uint32_t csd_type;                   // CSD type (0=host, 1=mgc, 2=can)
    #else // WICED_PLATFORM
        platform_sector_t sector_number;    // Single sector (circular buffer)
        uint16_t sector_capacity;            // Max records in sector
        uint16_t write_position;             // Write position in sector
    #endif

    // CONSISTENCY VALIDATION
    uint16_t state_checksum;            // CRC-16 checksum of all counters
    uint32_t last_write_timestamp;      // Timestamp of last operation
    uint32_t sensor_id;                 // Sensor ID for validation

    // COMPACT FLAGS (Single byte)
    union {
        uint8_t flags_byte;
        struct {
            uint8_t is_event_data      : 1;    // TSD vs EVENT type
            uint8_t is_initialized     : 1;    // Proper initialization completed
            uint8_t needs_cleanup      : 1;    // Cleanup required flag
            uint8_t is_circular        : 1;    // Circular buffer mode (WICED)
            uint8_t corruption_detected: 1;    // Corruption history flag
            uint8_t reserved           : 3;    // Future expansion
        } flags;
    };

} unified_sensor_state_t;

/******************************************************
 *            Mathematical Invariants
 ******************************************************/

/**
 * @brief Validate mathematical invariants (corruption impossible by design)
 */
#define VALIDATE_STATE_INVARIANTS(state) \
    ((state)->total_records >= (state)->consumed_records && \
     (state)->state_checksum == calculate_state_checksum(state) && \
     (state)->flags.is_initialized == 1)

/**
 * @brief Calculate available records (derived value)
 */
#define GET_AVAILABLE_RECORDS(state) \
    ((state)->total_records - (state)->consumed_records)

/**
 * @brief Calculate current read position (derived value)
 */
#define GET_READ_POSITION(state) \
    ((state)->consumed_records)

/**
 * @brief Check if read operation is valid
 */
#define CAN_READ_RECORDS(state, count) \
    (GET_AVAILABLE_RECORDS(state) >= (count))

/**
 * @brief Check if erase operation is valid
 */
#define CAN_ERASE_RECORDS(state, count) \
    (GET_AVAILABLE_RECORDS(state) >= (count))

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Initialize unified sensor state to clean, consistent state
 */
memory_error_t init_unified_state(unified_sensor_state_t *state, bool is_event_data);

/**
 * @brief Initialize unified sensor state with storage integration
 */
memory_error_t init_unified_state_with_storage(unified_sensor_state_t *state, bool is_event_data, uint32_t sensor_id);

/**
 * @brief Reset unified sensor state to initial conditions
 */
memory_error_t reset_unified_state(unified_sensor_state_t *state);

/**
 * @brief Validate unified sensor state consistency
 */
bool validate_unified_state(const unified_sensor_state_t *state);

/**
 * @brief Calculate state checksum for validation
 */
uint16_t calculate_state_checksum(const unified_sensor_state_t *state);

/**
 * @brief Update state checksum after modifications
 */
void update_state_checksum(unified_sensor_state_t *state);

/**
 * @brief Atomic write operation (increment total_records)
 */
memory_error_t atomic_write_record(unified_sensor_state_t *state);

/**
 * @brief Unified write operation (main implementation)
 */
memory_error_t write_tsd_evt_unified(unified_sensor_state_t *state, uint32_t data_value, uint32_t timestamp);

/**
 * @brief Unified read operation with bounds validation
 */
memory_error_t read_tsd_evt_unified(unified_sensor_state_t *state, uint32_t *data_value, uint32_t *timestamp);

#ifdef LINUX_PLATFORM
/**
 * @brief Read record from disk file when RAM is empty
 */
memory_error_t read_from_disk_file(unified_sensor_state_t *state, uint32_t *data_value, uint32_t *timestamp);
#endif

/**
 * @brief Atomic erase operation (increment consumed_records)
 */
memory_error_t atomic_erase_records(unified_sensor_state_t *state, uint16_t count);

/**
 * @brief Get current state information (read-only)
 */
void get_state_info(const unified_sensor_state_t *state,
                   uint32_t *total, uint32_t *available, uint32_t *consumed, uint32_t *position);

/**
 * @brief Detect and repair state corruption
 */
memory_error_t repair_state_corruption(unified_sensor_state_t *state);

/**
 * @brief Dump state for debugging
 */
void dump_unified_state(const unified_sensor_state_t *state, const char *label);

/******************************************************
 *              Platform-Adaptive Functions
 ******************************************************/

/**
 * @brief Platform-specific state initialization
 */
#ifdef LINUX_PLATFORM
    memory_error_t init_linux_state_storage(unified_sensor_state_t *state);
    memory_error_t cleanup_linux_state_storage(unified_sensor_state_t *state);
#else // WICED_PLATFORM
    memory_error_t init_wiced_state_storage(unified_sensor_state_t *state);
    memory_error_t cleanup_wiced_state_storage(unified_sensor_state_t *state);
#endif

/**
 * @brief Platform-specific storage operations
 */
memory_error_t platform_write_data(unified_sensor_state_t *state, const uint32_t *data, uint16_t size);
memory_error_t platform_read_data(unified_sensor_state_t *state, uint32_t *data, uint16_t size);

#endif /* UNIFIED_STATE_H */