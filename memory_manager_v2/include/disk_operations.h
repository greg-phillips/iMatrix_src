/**
 * @file disk_operations.h
 * @brief Disk Operations for Hybrid RAM/Disk Memory Management
 *
 * Provides disk I/O operations for the hybrid memory manager,
 * enabling automatic RAM-to-disk overflow and recovery.
 * LINUX_PLATFORM only.
 */

#ifndef DISK_OPERATIONS_H
#define DISK_OPERATIONS_H

#include "platform_config.h"
#include "unified_state.h"
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef LINUX_PLATFORM

/******************************************************
 *              Mode Management Functions
 ******************************************************/

/**
 * @brief Determine current operation mode based on state
 * @param state Unified sensor state
 * @return Current operation mode
 */
operation_mode_t determine_operation_mode(unified_sensor_state_t *state);

/**
 * @brief Switch from RAM mode to disk mode
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t switch_to_disk_mode(unified_sensor_state_t *state);

/**
 * @brief Switch from disk mode back to RAM mode
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t switch_to_ram_mode(unified_sensor_state_t *state);

/**
 * @brief Calculate RAM usage percentage across all CSDs
 * @param states Array of 3 CSD states
 * @return RAM usage percentage (0-100)
 */
uint32_t calculate_ram_usage_percent(unified_sensor_state_t *states[3]);

/**
 * @brief Check if flush to disk should be triggered
 * @param states Array of 3 CSD states
 * @return true if any CSD reached 80% threshold
 */
bool should_trigger_flush(unified_sensor_state_t *states[3]);

/**
 * @brief Check if consumption reached current disk sector
 * @param state Unified sensor state
 * @return true if ready to switch back to RAM mode
 */
bool consumption_reached_current_sector(unified_sensor_state_t *state);

/**
 * @brief Find the oldest disk file across all CSD directories
 * @param oldest_file_path Buffer to store path of oldest file
 * @param path_size Size of the path buffer
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t find_oldest_disk_file(char *oldest_file_path, size_t path_size);

/**
 * @brief Consume data from the oldest disk file
 * @param buffer Buffer to read data into
 * @param buffer_size Size of the buffer
 * @param records_consumed Number of records consumed
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t consume_from_disk(void *buffer, size_t buffer_size, uint32_t *records_consumed);

/**
 * @brief Check if any disk data is available for consumption
 * @return true if disk files exist
 */
bool has_disk_data_available(void);

/**
 * @brief Calculate total disk usage across all CSD directories
 * @param base_path Base path for storage
 * @return Total bytes used
 */
uint64_t calculate_total_disk_usage(const char *base_path);

/**
 * @brief Enforce the 256MB disk size limit
 * @param base_path Base path for storage
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t enforce_disk_size_limit(const char *base_path);

/**
 * @brief Register a CSD state for global monitoring
 * @param state CSD state to register
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t register_csd_for_monitoring(unified_sensor_state_t *state);

/**
 * @brief Check RAM usage and trigger flush if needed
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t check_and_trigger_flush(void);

/******************************************************
 *              Disk I/O Operations
 ******************************************************/

/**
 * @brief Flush all RAM data to disk for all CSDs
 * @param states Array of 3 CSD states
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t flush_all_to_disk(unified_sensor_state_t *states[3]);

/**
 * @brief Flush single CSD data from RAM to disk
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t flush_csd_to_disk(unified_sensor_state_t *state);

/**
 * @brief Write sector data to disk file
 * @param path Directory path for CSD type
 * @param sector_num Sector number for filename
 * @param data Sector data to write
 * @param size Size of data in bytes
 * @param meta Metadata to write atomically
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t write_sector_to_disk(const char *path, uint32_t sector_num,
                                   const void *data, size_t size,
                                   disk_sector_metadata_t *meta);

/**
 * @brief Read sector data from disk file
 * @param path Directory path for CSD type
 * @param sector_num Sector number for filename
 * @param data Buffer to read data into
 * @param size Size of buffer
 * @param meta Metadata to read
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t read_sector_from_disk(const char *path, uint32_t sector_num,
                                    void *data, size_t size,
                                    disk_sector_metadata_t *meta);

/**
 * @brief Delete oldest disk sector when disk is full
 * @param path Directory path for CSD type
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t delete_oldest_disk_sector(const char *path);

/**
 * @brief Allocate new sector from disk storage
 * @param state Unified sensor state
 * @return Sector number or INVALID_SECTOR on failure
 */
platform_sector_t allocate_disk_sector(unified_sensor_state_t *state);

/******************************************************
 *              Metadata Management
 ******************************************************/

/**
 * @brief Write metadata atomically using temp file
 * @param path Directory path for metadata
 * @param meta Metadata structure to write
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t write_metadata_atomic(const char *path,
                                    const disk_sector_metadata_t *meta);

/**
 * @brief Read metadata from disk
 * @param path Directory path for metadata
 * @param meta Metadata structure to populate
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t read_metadata(const char *path, disk_sector_metadata_t *meta);

/**
 * @brief Validate disk integrity using checksums
 * @param path Directory path to validate
 * @return MEMORY_SUCCESS if valid, error code if corrupt
 */
memory_error_t validate_disk_integrity(const char *path);

/**
 * @brief Calculate checksum for data
 * @param data Data to checksum
 * @param size Size of data
 * @return 32-bit checksum value
 */
uint32_t calculate_data_checksum(const void *data, size_t size);

/******************************************************
 *              Recovery Operations
 ******************************************************/

/**
 * @brief Scan disk for existing files on startup
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t scan_disk_for_recovery(unified_sensor_state_t *state);

/**
 * @brief Recover state from disk files
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t recover_from_disk(unified_sensor_state_t *state);

/**
 * @brief Reconstruct state from disk metadata
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t reconstruct_state_from_disk(unified_sensor_state_t *state);

/**
 * @brief Repair corrupted disk sectors
 * @param path Directory path for CSD type
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t repair_corrupted_sectors(const char *path);

/******************************************************
 *              Directory Management
 ******************************************************/

/**
 * @brief Create storage directories if they don't exist
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t create_storage_directories(void);

/**
 * @brief Validate storage paths are accessible
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t validate_storage_paths(void);

/**
 * @brief Get directory path for CSD type
 * @param csd_type CSD type (0=host, 1=mgc, 2=can)
 * @param buffer Buffer to store path
 * @param buffer_size Size of buffer
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t get_csd_directory(uint32_t csd_type, char *buffer, size_t buffer_size);

/**
 * @brief Build full file path for sector
 * @param csd_type CSD type
 * @param sector_num Sector number
 * @param buffer Buffer to store path
 * @param buffer_size Size of buffer
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t build_sector_filepath(uint32_t csd_type, uint32_t sector_num,
                                    char *buffer, size_t buffer_size);

/******************************************************
 *              Disk Space Management
 ******************************************************/

/**
 * @brief Get available disk space in bytes
 * @param path Directory path to check
 * @return Available space in bytes, 0 on error
 */
uint64_t get_disk_space_available(const char *path);

/**
 * @brief Handle disk full condition
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t handle_disk_full(unified_sensor_state_t *state);

/**
 * @brief Drop oldest data to recover space
 * @param state Unified sensor state
 * @param sectors_to_drop Number of sectors to drop
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t drop_oldest_sectors(unified_sensor_state_t *state, uint32_t sectors_to_drop);

/******************************************************
 *              Shutdown Operations
 ******************************************************/

/**
 * @brief Graceful shutdown hook
 * @param states Array of 3 CSD states
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t graceful_shutdown_hook(unified_sensor_state_t *states[3]);

/**
 * @brief Emergency flush to disk on unexpected shutdown
 * @param states Array of 3 CSD states
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t emergency_flush_to_disk(unified_sensor_state_t *states[3]);

/******************************************************
 *              Diagnostics
 ******************************************************/

/**
 * @brief Update system diagnostics
 * @param diagnostics System diagnostics structure
 * @param event_type Type of event to record
 */
void update_diagnostics(system_diagnostics_t *diagnostics, const char *event_type);

/**
 * @brief Get current system diagnostics
 * @param diagnostics Structure to populate
 */
void get_system_diagnostics(system_diagnostics_t *diagnostics);

/**
 * @brief Log disk operation for debugging
 * @param operation Operation type string
 * @param csd_type CSD type
 * @param sector_num Sector number
 * @param success Success/failure flag
 */
void log_disk_operation(const char *operation, uint32_t csd_type,
                        uint32_t sector_num, bool success);

#endif // LINUX_PLATFORM

/******************************************************
 *          Platform-Independent Functions
 ******************************************************/

/**
 * @brief Get free sector with mode awareness
 * @param state Unified sensor state
 * @return Sector number or INVALID_SECTOR
 */
platform_sector_t get_free_sector_adaptive(unified_sensor_state_t *state);

/**
 * @brief Allocate RAM sector
 * @param state Unified sensor state
 * @return Sector number or INVALID_SECTOR
 */
platform_sector_t allocate_ram_sector(unified_sensor_state_t *state);

#ifdef WICED_PLATFORM
/**
 * @brief Drop oldest sector when RAM is full (WICED only)
 * @param state Unified sensor state
 * @return MEMORY_SUCCESS or error code
 */
memory_error_t drop_oldest_sector(unified_sensor_state_t *state);

/**
 * @brief Check if RAM is full
 * @param state Unified sensor state
 * @return true if RAM is at 100% capacity
 */
bool ram_is_full(unified_sensor_state_t *state);
#endif

#endif /* DISK_OPERATIONS_H */