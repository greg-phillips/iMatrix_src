/**
 * @file data_storage.h
 * @brief Data Storage Structure Definitions
 *
 * Defines sector data layouts, record formats, and storage structures
 * for the unified memory manager with platform optimizations.
 */

#ifndef DATA_STORAGE_H
#define DATA_STORAGE_H

#include "platform_config.h"
#include <stdint.h>
#include <stdbool.h>

// Forward declaration (actual definition in unified_state.h)
struct unified_sensor_state;

/******************************************************
 *                Storage Constants
 ******************************************************/

// Record format constants
#define TSD_RECORD_DATA_SIZE        4          // TSD data payload size
#define EVT_RECORD_DATA_SIZE        4          // Event data payload size
#define EVT_RECORD_TIMESTAMP_SIZE   4          // Event timestamp size
#define RECORD_ALIGNMENT            4          // Memory alignment for records

// Sector layout constants
#define SECTOR_HEADER_SIZE          8          // Sector metadata size
#define SECTOR_DATA_SIZE           (SECTOR_SIZE - SECTOR_HEADER_SIZE)  // Available data space
#define SECTOR_CHECKSUM_SIZE        2          // Sector data integrity checksum

// Platform-specific record limits
#ifdef LINUX_PLATFORM
    #define MAX_TSD_RECORDS_PER_SECTOR  ((SECTOR_DATA_SIZE) / TSD_RECORD_SIZE)      // 6 records
    #define MAX_EVT_RECORDS_PER_SECTOR  ((SECTOR_DATA_SIZE) / EVT_RECORD_SIZE)      // 3 records
#else // WICED_PLATFORM
    #define MAX_TSD_RECORDS_PER_SECTOR  ((SECTOR_DATA_SIZE) / TSD_RECORD_SIZE)      // 6 records
    #define MAX_EVT_RECORDS_PER_SECTOR  ((SECTOR_DATA_SIZE) / EVT_RECORD_SIZE)      // 3 records
#endif

/******************************************************
 *              Record Structures
 ******************************************************/

/**
 * @brief Time Series Data (TSD) record format
 */
typedef struct __attribute__((packed)) {
    uint32_t data;                 // Sensor data value (4 bytes)
} tsd_record_t;

/**
 * @brief Event Data (EVT) record format
 */
typedef struct __attribute__((packed)) {
    uint32_t timestamp;            // UTC timestamp (4 bytes)
    uint32_t data;                 // Event data value (4 bytes)
} evt_record_t;

/**
 * @brief Generic data record union
 */
typedef union {
    tsd_record_t tsd;              // TSD format
    evt_record_t evt;              // EVENT format
    uint8_t raw_bytes[EVT_RECORD_SIZE];  // Raw byte access
} data_record_t;

/******************************************************
 *              Sector Structures
 ******************************************************/

/**
 * @brief Sector header for metadata and validation
 */
typedef struct __attribute__((packed)) {
    uint32_t sensor_id;            // Sensor ID for validation
    platform_sector_t next_sector; // Next sector in chain (platform-adaptive)
    uint16_t record_count;         // Number of records in this sector
    uint8_t record_type;           // TSD or EVENT type
    uint8_t flags;                 // Sector flags (full, corrupted, etc.)
} sector_header_t;

/**
 * @brief Complete sector structure with data
 */
typedef struct __attribute__((packed)) {
    sector_header_t header;        // Sector metadata
    uint8_t data[SECTOR_DATA_SIZE]; // Record data area
    uint16_t data_checksum;        // Data integrity checksum
} storage_sector_t;

/******************************************************
 *            Platform-Specific Optimizations
 ******************************************************/

#ifdef LINUX_PLATFORM
/**
 * @brief LINUX-specific sector chain structure
 */
typedef struct {
    platform_sector_t first_sector;    // Chain start
    platform_sector_t last_sector;     // Chain end
    uint32_t total_sectors;             // Sectors in chain
    uint32_t total_records;             // Records across all sectors
    uint64_t total_bytes;               // Total data bytes
    bool disk_overflow_active;          // Using disk storage
    char disk_filename[256];            // Disk file path
} linux_storage_chain_t;

#else // WICED_PLATFORM
/**
 * @brief WICED-specific circular buffer structure
 */
typedef struct {
    platform_sector_t sector_number;   // Single sector
    uint16_t write_offset;              // Current write position
    uint16_t read_offset;               // Current read position
    uint16_t record_count;              // Records in buffer
    uint16_t capacity;                  // Maximum records
    bool is_full;                       // Buffer full flag
    bool wraparound_enabled;            // Circular operation
} wiced_circular_buffer_t;
#endif

/******************************************************
 *              Storage Operations
 ******************************************************/

/**
 * @brief Storage operation result structure
 */
typedef struct {
    memory_error_t error;          // Operation result
    uint32_t bytes_processed;      // Data processed
    platform_sector_t sector_used; // Sector involved
    uint16_t records_affected;     // Records modified
} storage_operation_result_t;

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Initialize storage subsystem
 */
memory_error_t init_storage_system(void);

/**
 * @brief Shutdown storage subsystem
 */
memory_error_t shutdown_storage_system(void);

/**
 * @brief Allocate sector for storage
 */
storage_operation_result_t allocate_storage_sector(uint32_t sensor_id, bool is_event_data);

/**
 * @brief Free storage sector
 */
memory_error_t free_storage_sector(platform_sector_t sector);

/**
 * @brief Write data record to storage
 */
storage_operation_result_t write_data_record(platform_sector_t sector, uint16_t offset,
                                           const data_record_t *record, bool is_event_data);

/**
 * @brief Read data record from storage
 */
storage_operation_result_t read_data_record(platform_sector_t sector, uint16_t offset,
                                          data_record_t *record, bool is_event_data);

/**
 * @brief Validate sector data integrity
 */
bool validate_sector_integrity(platform_sector_t sector);

/**
 * @brief Calculate sector data checksum
 */
uint16_t calculate_sector_checksum(const storage_sector_t *sector);

/**
 * @brief Update sector metadata
 */
memory_error_t update_sector_metadata(platform_sector_t sector, const sector_header_t *header);

/**
 * @brief Get sector metadata
 */
memory_error_t get_sector_metadata(platform_sector_t sector, sector_header_t *header);

/******************************************************
 *          Platform-Specific Functions
 ******************************************************/

#ifdef LINUX_PLATFORM
/**
 * @brief Initialize LINUX storage chain
 */
memory_error_t init_linux_storage_chain(linux_storage_chain_t *chain, uint32_t sensor_id);

/**
 * @brief Extend LINUX storage chain
 */
memory_error_t extend_linux_storage_chain(linux_storage_chain_t *chain);

/**
 * @brief Cleanup LINUX storage chain
 */
memory_error_t cleanup_linux_storage_chain(linux_storage_chain_t *chain);

#else // WICED_PLATFORM
/**
 * @brief Initialize WICED circular buffer
 */
memory_error_t init_wiced_circular_buffer(wiced_circular_buffer_t *buffer, uint32_t sensor_id);

/**
 * @brief Write to WICED circular buffer
 */
memory_error_t write_wiced_circular_buffer(wiced_circular_buffer_t *buffer, const data_record_t *record);

/**
 * @brief Read from WICED circular buffer
 */
memory_error_t read_wiced_circular_buffer(wiced_circular_buffer_t *buffer, data_record_t *record);
#endif

/**
 * @brief Platform-adaptive storage operations
 */
memory_error_t platform_write_record(const struct unified_sensor_state *state, const data_record_t *record);
memory_error_t platform_read_record(const struct unified_sensor_state *state, data_record_t *record, uint16_t position);
memory_error_t platform_erase_records(const struct unified_sensor_state *state, uint16_t count);

/******************************************************
 *              Validation Functions
 ******************************************************/

/**
 * @brief Validate record format
 */
bool validate_record_format(const data_record_t *record, bool is_event_data);

/**
 * @brief Validate storage consistency
 */
bool validate_storage_consistency(platform_sector_t sector);

/**
 * @brief Detect and repair storage corruption
 */
memory_error_t repair_storage_corruption(platform_sector_t sector);

/**
 * @brief Dump storage state for debugging
 */
void dump_storage_state(platform_sector_t sector, const char *label);

#endif /* DATA_STORAGE_H */