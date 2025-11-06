/**
 * @file sensor_storage.h
 * @brief Public API for sensor storage system
 *
 * This is the main public interface for the sensor storage system as specified
 * in the original requirements. Provides thread-safe, platform-agnostic
 * storage for time-series and event-driven sensor data.
 *
 * Key Features:
 * - Hundreds of sensors support
 * - Time-series (4B) and Event (12B) record types
 * - Thread-safe operations with per-sensor mutexes
 * - Platform support: STM32 (RAM-only) and Linux (RAM+disk)
 * - Upload integration with pending/unsent semantics
 * - CRC32C integrity checking
 * - Configurable thresholds and policies
 *
 * Performance Targets:
 * - STM32: ≤20µs per add operation, ≤32KB RAM total
 * - Linux: ≤5µs per add operation, configurable RAM/disk quotas
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#ifndef SENSOR_STORAGE_H
#define SENSOR_STORAGE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Sensor data types
 */
typedef enum {
    SENSOR_TS = 1,      /**< Time-Series: value-only samples (4 bytes) */
    SENSOR_EVT = 2      /**< Event-Driven: value + 64-bit timestamp (12 bytes) */
} SensorType;

/**
 * @brief Data source categories (Linux disk organization)
 */
typedef enum {
    SOURCE_HOST = 1,        /**< Host system sensors */
    SOURCE_APPLICATION = 2, /**< Application-level sensors */
    SOURCE_CAN = 3          /**< CAN bus sensors */
} DataSource;

/**
 * @brief System configuration structure
 *
 * Platform-specific configuration for initializing the sensor storage system.
 * Use ss_init_config_defaults() to get platform-appropriate defaults.
 */
typedef struct {
    /* Platform identification */
    uint32_t platform;              /**< 1=STM32, 2=Linux */

    /* Memory configuration */
    uint32_t ram_sector_size;       /**< STM32: 256B, Linux: 4KB */
    uint32_t ram_pool_sectors;      /**< Number of RAM sectors */
    uint32_t ram_threshold_pct;     /**< Linux: RAM flush threshold (80%) */

    /* Linux disk configuration */
    uint32_t disk_sector_size;      /**< Linux: 64KB disk sectors */
    uint64_t disk_quota_bytes;      /**< Per-sensor disk quota */
    const char *disk_base_path;     /**< Base directory for sensor files */

    /* Performance and timing */
    uint32_t manager_tick_ms;       /**< Maintenance interval (100ms) */
    uint32_t force_seal_ms;         /**< Force seal interval (5000ms) */

    /* Features */
    bool enable_crc;                /**< Enable CRC32C validation */
    bool enable_disk_sync;          /**< Force fsync on disk writes */

} SsInitCfg;

/**
 * @brief Opaque sensor store handle
 *
 * Represents an individual sensor's storage. Obtained from ss_sensor_init()
 * and used in all sensor-specific operations.
 */
typedef struct SensorStore SensorStore;

/**
 * @brief Error codes
 */
typedef enum {
    SS_OK = 0,              /**< Success */
    SS_ERROR_INVALID = -1,  /**< Invalid parameter */
    SS_ERROR_NOMEM = -2,    /**< Out of memory/sectors */
    SS_ERROR_IO = -3,       /**< Disk I/O error */
    SS_ERROR_CORRUPT = -4,  /**< Data corruption detected */
    SS_ERROR_QUOTA = -5,    /**< Disk quota exceeded */
    SS_ERROR_BUSY = -6,     /**< Resource temporarily unavailable */
    SS_ERROR_NOTFOUND = -7, /**< Sensor/record not found */
    SS_ERROR_FULL = -8,     /**< Storage full, cannot accept new data */
    SS_ERROR_SHUTDOWN = -9  /**< System in shutdown mode */
} SsError;

/**
 * @brief System-wide statistics
 */
typedef struct {
    /* Memory pool statistics */
    uint32_t ram_sectors_total;
    uint32_t ram_sectors_used;
    uint32_t ram_sectors_free;
    uint32_t ram_usage_pct;

    /* Sensor statistics */
    uint32_t sensors_active;
    uint64_t total_records_stored;
    uint64_t total_records_written;
    uint64_t total_records_consumed;

    /* Performance metrics */
    uint32_t avg_write_time_us;
    uint32_t max_write_time_us;

    /* Error counters */
    uint32_t crc_errors;
    uint32_t allocation_failures;
    uint32_t quota_violations;

} SsSystemStats;

/* ========================================================================= */
/*                            CORE API FUNCTIONS                            */
/* ========================================================================= */

/**
 * @brief Initialize the sensor storage system
 *
 * Initializes platform-specific pools, mutexes, and disk management.
 * Must be called once during system startup before any other operations.
 *
 * @param cfg System configuration (use ss_init_config_defaults() for defaults)
 * @return SS_OK on success, error code on failure
 */
int ss_init_system(const SsInitCfg *cfg);

/**
 * @brief Initialize storage for a specific sensor
 *
 * Creates a new sensor storage instance with specified type and source.
 * Allocates initial sector and sets up per-sensor mutex.
 *
 * @param sensor_id Unique sensor identifier
 * @param type Sensor type (SENSOR_TS or SENSOR_EVT)
 * @param source Data source category (for Linux disk organization)
 * @param out Pointer to store sensor storage handle
 * @return SS_OK on success, error code on failure
 */
int ss_sensor_init(uint32_t sensor_id, SensorType type, DataSource source, SensorStore **out);

/**
 * @brief Add time-series record
 *
 * Adds a time-series record (value only) to the specified sensor.
 * Automatically manages sector allocation and ring buffer growth.
 *
 * Performance target: ≤20µs (STM32), ≤5µs (Linux)
 *
 * @param s Sensor storage handle
 * @param value 32-bit unsigned sensor value
 * @return SS_OK on success, error code on failure
 */
int ss_ts_add(SensorStore *s, uint32_t value);

/**
 * @brief Add event record
 *
 * Adds an event record (value + timestamp) to the specified sensor.
 * Timestamp interpretation (UTC vs monotonic) is left to consumer.
 *
 * Performance target: ≤20µs (STM32), ≤5µs (Linux)
 *
 * @param s Sensor storage handle
 * @param value 32-bit unsigned sensor value
 * @param ts_ms 64-bit timestamp in milliseconds
 * @return SS_OK on success, error code on failure
 */
int ss_evt_add(SensorStore *s, uint32_t value, uint64_t ts_ms);

/**
 * @brief Get total records currently retained
 *
 * Returns the total number of records currently stored for this sensor,
 * including both unsent and pending records.
 *
 * @param s Sensor storage handle
 * @param out_total_current Pointer to store total record count
 * @return SS_OK on success, error code on failure
 */
int ss_get_total_records(const SensorStore *s, uint64_t *out_total_current);

/**
 * @brief Get count of unsent records
 *
 * Returns the number of records awaiting upload (not yet consumed).
 * This is the count available for ss_consume_next() operations.
 *
 * @param s Sensor storage handle
 * @param out_unsent Pointer to store unsent record count
 * @return SS_OK on success, error code on failure
 */
int ss_get_unsent_count(const SensorStore *s, uint64_t *out_unsent);

/**
 * @brief Read record by offset for diagnostics
 *
 * Reads a record at specified offset from the start of stored data.
 * This is for diagnostics only and does not affect upload cursors.
 *
 * @param s Sensor storage handle
 * @param offset Record offset from start (0-based)
 * @param out_rec Buffer to store record (TS: uint32_t*, EVT: EventRecord*)
 * @return SS_OK on success, error code on failure
 */
int ss_diag_read_at(const SensorStore *s, uint64_t offset, void *out_rec);

/**
 * @brief Consume next unsent record
 *
 * Retrieves the next unsent record and marks it as pending (uploaded but
 * not yet acknowledged). Used by upload system to get data for transmission.
 *
 * @param s Sensor storage handle
 * @param out_rec Buffer to store record data
 * @return SS_OK on success, error code on failure
 */
int ss_consume_next(SensorStore *s, void *out_rec);

/**
 * @brief Consume batch of unsent records
 *
 * Higher performance version that retrieves multiple records in one operation.
 * All returned records are marked as pending.
 *
 * @param s Sensor storage handle
 * @param out_buf Buffer to store record data
 * @param max_records Maximum number of records to retrieve
 * @param out_n Pointer to store actual number of records retrieved
 * @return SS_OK on success, error code on failure
 */
int ss_consume_batch(SensorStore *s, void *out_buf, uint32_t max_records, uint32_t *out_n);

/**
 * @brief Erase all pending records
 *
 * Erases all pending records after successful cloud acknowledgment.
 * This advances the head cursor and frees sectors where applicable.
 *
 * @param s Sensor storage handle
 * @return SS_OK on success, error code on failure
 */
int ss_erase_all_pending(SensorStore *s);

/* ========================================================================= */
/*                          SYSTEM MANAGEMENT                               */
/* ========================================================================= */

/**
 * @brief Periodic system maintenance
 *
 * Performs system-wide maintenance including sector sealing, disk flushing,
 * quota enforcement, and health monitoring. Should be called every ~100ms.
 */
void ss_manager_tick(void);

/**
 * @brief Set system shutdown mode
 *
 * Signals the system to begin shutdown procedures including forced sector
 * sealing and disk flushing. Data sources should stop adding new data.
 *
 * @param in_progress true to begin shutdown, false to cancel
 */
void ss_set_shutdown(bool in_progress);

/**
 * @brief Get system-wide statistics
 *
 * Retrieves comprehensive system statistics for monitoring and debugging.
 *
 * @param stats Structure to fill with statistics
 * @return SS_OK on success, error code on failure
 */
int ss_get_system_stats(SsSystemStats *stats);

/* ========================================================================= */
/*                            UTILITY FUNCTIONS                             */
/* ========================================================================= */

/**
 * @brief Get platform-appropriate default configuration
 *
 * Fills configuration structure with sensible defaults for the target platform.
 * Automatically detects platform and sets appropriate values.
 *
 * @param cfg Configuration structure to fill
 * @return SS_OK on success, error code on failure
 */
int ss_init_config_defaults(SsInitCfg *cfg);

/**
 * @brief Convert error code to human-readable string
 *
 * @param error_code Error code from sensor storage API
 * @return Pointer to static error string
 */
const char *ss_error_string(int error_code);

/**
 * @brief Get version information
 *
 * @return Pointer to static version string
 */
const char *ss_get_version(void);

/* ========================================================================= */
/*                             DEBUG/TESTING                                */
/* ========================================================================= */

/**
 * @brief Dump sensor state for debugging
 *
 * Outputs detailed sensor state for debugging and analysis.
 *
 * @param s Sensor storage handle
 * @param buffer Buffer to store output string
 * @param buffer_size Size of output buffer
 * @return Number of characters written
 */
uint32_t ss_dump_sensor_state(const SensorStore *s, char *buffer, uint32_t buffer_size);

/**
 * @brief Validate sensor integrity
 *
 * Performs comprehensive integrity checks on sensor storage.
 *
 * @param s Sensor storage handle
 * @return SS_OK if valid, error code describing issue
 */
int ss_validate_sensor_integrity(const SensorStore *s);

#ifdef __cplusplus
}
#endif

#endif /* SENSOR_STORAGE_H */