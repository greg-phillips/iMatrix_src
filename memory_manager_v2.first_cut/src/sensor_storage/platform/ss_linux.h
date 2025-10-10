/**
 * @file ss_linux.h
 * @brief Linux platform-specific implementations for sensor storage
 *
 * Provides Linux-specific implementations including:
 * - pthread mutex implementation
 * - Disk persistence with atomic operations
 * - Memory management with virtual memory
 * - File I/O optimizations
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#ifndef SS_LINUX_H
#define SS_LINUX_H

#include "../core/ss_types.h"
#include "../utils/ss_mutex.h"
#include <pthread.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Linux-specific mutex implementation
 *
 * Uses pthread mutex with error checking enabled for debugging.
 * Includes timing statistics for performance monitoring.
 */
struct SsMutex {
    pthread_mutex_t handle;     /**< pthread mutex handle */
    uint32_t magic;             /**< Magic number for validation */

#ifdef SS_DEBUG_TIMING
    SsMutexStats stats;         /**< Performance statistics */
    struct timespec lock_time;  /**< When mutex was last locked */
#endif
};

/**
 * @brief Magic number for Linux mutex validation
 */
#define SS_LINUX_MUTEX_MAGIC 0x4C4E5558  /* "LNUX" */

/**
 * @brief Linux-specific sector pool configuration
 */
typedef struct {
    void *pool_base;            /**< Base address of sector pool */
    uint32_t sector_size;       /**< Size of each sector */
    uint32_t total_sectors;     /**< Total sectors in pool */
    uint32_t free_sectors;      /**< Currently available sectors */
    uint32_t *free_list;        /**< Free sector indices */
    uint32_t free_head;         /**< Head of free list */
    SsMutex *pool_mutex;        /**< Pool allocation mutex */
} SsLinuxPool;

/**
 * @brief Linux disk file management
 */
typedef struct {
    char data_path[256];        /**< Full path to .dat file */
    char meta_path[256];        /**< Full path to .meta file */
    char temp_path[256];        /**< Temporary file for atomic updates */
    int data_fd;                /**< Data file descriptor */
    int meta_fd;                /**< Metadata file descriptor */
    uint64_t file_size;         /**< Current data file size */
    uint64_t disk_quota;        /**< Maximum allowed disk usage */
} SsLinuxDisk;

/**
 * @brief Linux-specific system configuration
 */
typedef struct {
    SsLinuxPool ram_pool;       /**< RAM sector pool */
    const char *base_path;      /**< Base directory for data files */
    bool sync_enabled;          /**< Force fsync after writes */
    uint32_t worker_threads;    /**< Number of disk worker threads */
    uint32_t flush_batch_size;  /**< Sectors per flush operation */
} SsLinuxConfig;

/**
 * @brief Initialize Linux platform support
 * @param config Platform-specific configuration
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_init(const SsLinuxConfig *config);

/**
 * @brief Shutdown Linux platform support
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_shutdown(void);

/**
 * @brief Allocate sector from Linux RAM pool
 * @param sector_size Size of sector to allocate
 * @param sector Pointer to store allocated sector
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_alloc_sector(uint32_t sector_size, Sector **sector);

/**
 * @brief Free sector back to Linux RAM pool
 * @param sector Sector to free
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_free_sector(Sector *sector);

/**
 * @brief Get Linux RAM pool usage statistics
 * @param total_sectors Pointer to store total sector count
 * @param free_sectors Pointer to store free sector count
 * @param usage_pct Pointer to store usage percentage
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_pool_stats(uint32_t *total_sectors, uint32_t *free_sectors, uint32_t *usage_pct);

/**
 * @brief Initialize disk files for a sensor
 * @param sensor_id Sensor identifier
 * @param source Data source category
 * @param disk Structure to initialize
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_init(uint32_t sensor_id, DataSource source, SsLinuxDisk *disk);

/**
 * @brief Write sector to disk atomically
 * @param disk Disk management structure
 * @param sector Sector to write
 * @param sector_size Size of sector
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_write_sector(SsLinuxDisk *disk, const Sector *sector, uint32_t sector_size);

/**
 * @brief Read sector from disk
 * @param disk Disk management structure
 * @param offset File offset to read from
 * @param sector Buffer to store sector data
 * @param sector_size Size of sector
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_read_sector(SsLinuxDisk *disk, uint64_t offset, Sector *sector, uint32_t sector_size);

/**
 * @brief Update metadata file atomically
 * @param disk Disk management structure
 * @param head_idx Head record index
 * @param pending_idx Pending record index
 * @param tail_idx Tail record index
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_update_meta(SsLinuxDisk *disk, uint64_t head_idx, uint64_t pending_idx, uint64_t tail_idx);

/**
 * @brief Scan disk file and rebuild sector index
 * @param disk Disk management structure
 * @param sectors Array to store sector pointers
 * @param max_sectors Maximum sectors to scan
 * @param sector_count Pointer to store actual sector count
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_scan(SsLinuxDisk *disk, Sector **sectors, uint32_t max_sectors, uint32_t *sector_count);

/**
 * @brief Enforce disk quota by dropping old sectors
 * @param disk Disk management structure
 * @param target_usage Target usage percentage
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_enforce_quota(SsLinuxDisk *disk, uint32_t target_usage);

/**
 * @brief Close and cleanup disk files
 * @param disk Disk management structure
 * @return SS_OK on success, error code on failure
 */
SsError ss_linux_disk_close(SsLinuxDisk *disk);

/**
 * @brief Get current timestamp in milliseconds
 * @param utc_time If true, return UTC time; if false, return monotonic time
 * @return Timestamp in milliseconds
 */
uint64_t ss_linux_get_timestamp_ms(bool utc_time);

/**
 * @brief Sleep for specified milliseconds
 * @param ms Milliseconds to sleep
 */
void ss_linux_sleep_ms(uint32_t ms);

/**
 * @brief Get high-resolution timer for performance measurement
 * @return Microseconds since system start
 */
uint64_t ss_linux_get_timer_us(void);

#ifdef __cplusplus
}
#endif

#endif /* SS_LINUX_H */