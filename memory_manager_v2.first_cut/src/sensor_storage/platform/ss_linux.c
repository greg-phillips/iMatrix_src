/**
 * @file ss_linux.c
 * @brief Linux platform-specific implementations for sensor storage
 *
 * Implements Linux-specific features including pthread mutexes,
 * memory management, and disk persistence operations.
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#include "ss_linux.h"
#include "../core/ss_pool.h"
#include "../utils/ss_crc.h"
#include "../utils/ss_mutex.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <errno.h>
#include <time.h>

/**
 * @brief Linux pool implementation structure
 */
struct SsPool {
    SsPoolType type;                /**< Pool type identifier */
    uint32_t magic;                 /**< Magic number for validation */
    uint32_t sector_size;           /**< Size of each sector */
    uint32_t total_sectors;         /**< Total sectors in pool */
    uint32_t free_sectors;          /**< Currently available sectors */

    SsMutex *mutex;                 /**< Pool protection mutex */

    /* Memory management */
    void *pool_memory;              /**< Base address of pool memory */
    bool own_memory;                /**< Whether we allocated the memory */

    /* Free list management */
    uint32_t *free_list;            /**< Array of free sector indices */
    uint32_t free_head;             /**< Head index in free list */

    /* Statistics */
    SsPoolStats stats;              /**< Pool statistics */

    /* Pressure monitoring */
    uint32_t pressure_threshold;    /**< Threshold for pressure callback */
    SsPoolPressureCallback pressure_callback; /**< Pressure callback function */
    void *pressure_user_data;       /**< User data for pressure callback */

#ifdef SS_DEBUG_TIMING
    struct timespec last_alloc_time; /**< Timing for performance measurement */
#endif
};

/**
 * @brief Magic number for Linux pool validation
 */
#define SS_LINUX_POOL_MAGIC 0x4C505554  /* "LPUT" */

/**
 * @brief Calculate memory size needed for pool
 */
static size_t calculate_pool_memory_size(uint32_t sector_size, uint32_t sector_count)
{
    size_t sector_memory = (size_t)sector_size * sector_count;
    size_t free_list_memory = sizeof(uint32_t) * sector_count;
    return sector_memory + free_list_memory;
}

/**
 * @brief Initialize free list with all sectors available
 */
static void init_free_list(SsPool *pool)
{
    for (uint32_t i = 0; i < pool->total_sectors; i++) {
        pool->free_list[i] = i;
    }
    pool->free_head = 0;
    pool->free_sectors = pool->total_sectors;
}

/**
 * @brief Get sector pointer by index
 */
static Sector *get_sector_by_index(const SsPool *pool, uint32_t index)
{
    if (index >= pool->total_sectors) {
        return NULL;
    }

    uint8_t *base = (uint8_t *)pool->pool_memory;
    return (Sector *)(base + (size_t)index * pool->sector_size);
}

/**
 * @brief Update pool statistics after allocation
 */
static void update_alloc_stats(SsPool *pool, uint64_t alloc_time_us)
{
    pool->stats.total_allocs++;
    pool->stats.used_sectors = pool->total_sectors - pool->free_sectors;
    pool->stats.usage_percent = (pool->stats.used_sectors * 100) / pool->total_sectors;

    if (pool->stats.usage_percent > pool->stats.peak_usage) {
        pool->stats.peak_usage = pool->stats.usage_percent;
    }

#ifdef SS_DEBUG_TIMING
    pool->stats.avg_alloc_time_us =
        (pool->stats.avg_alloc_time_us * (pool->stats.total_allocs - 1) + alloc_time_us) /
        pool->stats.total_allocs;

    if (alloc_time_us > pool->stats.max_alloc_time_us) {
        pool->stats.max_alloc_time_us = alloc_time_us;
    }
#endif
}

/**
 * @brief Update pool statistics after free
 */
static void update_free_stats(SsPool *pool, uint64_t free_time_us)
{
    pool->stats.total_frees++;
    pool->stats.used_sectors = pool->total_sectors - pool->free_sectors;
    pool->stats.usage_percent = (pool->stats.used_sectors * 100) / pool->total_sectors;

#ifdef SS_DEBUG_TIMING
    pool->stats.avg_free_time_us =
        (pool->stats.avg_free_time_us * (pool->stats.total_frees - 1) + free_time_us) /
        pool->stats.total_frees;

    if (free_time_us > pool->stats.max_free_time_us) {
        pool->stats.max_free_time_us = free_time_us;
    }
#endif
}

SsError ss_pool_init(SsPoolType pool_type, uint32_t sector_size,
                     uint32_t sector_count, void *base_memory, SsPool **pool)
{
    if (!pool || sector_size == 0 || sector_count == 0) {
        return SS_ERROR_INVALID;
    }

    if (pool_type != SS_POOL_LINUX_RAM && pool_type != SS_POOL_LINUX_DISK) {
        return SS_ERROR_INVALID;
    }

    SsPool *new_pool = malloc(sizeof(SsPool));
    if (!new_pool) {
        return SS_ERROR_NOMEM;
    }

    memset(new_pool, 0, sizeof(SsPool));

    new_pool->type = pool_type;
    new_pool->magic = SS_LINUX_POOL_MAGIC;
    new_pool->sector_size = sector_size;
    new_pool->total_sectors = sector_count;

    /* Create pool mutex */
    SsError result = ss_mutex_create(&new_pool->mutex);
    if (result != SS_OK) {
        free(new_pool);
        return result;
    }

    /* Allocate or use provided memory */
    size_t total_memory = calculate_pool_memory_size(sector_size, sector_count);

    if (base_memory) {
        new_pool->pool_memory = base_memory;
        new_pool->own_memory = false;
    } else {
        new_pool->pool_memory = malloc(total_memory);
        if (!new_pool->pool_memory) {
            ss_mutex_destroy(&new_pool->mutex);
            free(new_pool);
            return SS_ERROR_NOMEM;
        }
        new_pool->own_memory = true;
    }

    /* Initialize free list (at end of pool memory) */
    uint8_t *pool_base = (uint8_t *)new_pool->pool_memory;
    size_t sector_memory = (size_t)sector_size * sector_count;
    new_pool->free_list = (uint32_t *)(pool_base + sector_memory);

    init_free_list(new_pool);

    /* Initialize statistics */
    memset(&new_pool->stats, 0, sizeof(new_pool->stats));
    new_pool->stats.total_sectors = sector_count;
    new_pool->stats.free_sectors = sector_count;

    *pool = new_pool;
    return SS_OK;
}

SsError ss_pool_destroy(SsPool **pool)
{
    if (!pool || !*pool) {
        return SS_ERROR_INVALID;
    }

    SsPool *p = *pool;

    if (p->magic != SS_LINUX_POOL_MAGIC) {
        return SS_ERROR_INVALID;
    }

    /* Check if all sectors are freed */
    if (p->free_sectors != p->total_sectors) {
        return SS_ERROR_BUSY;
    }

    /* Clean up mutex */
    if (p->mutex) {
        ss_mutex_destroy(&p->mutex);
    }

    /* Free memory if we own it */
    if (p->own_memory && p->pool_memory) {
        free(p->pool_memory);
    }

    /* Clear magic and free structure */
    p->magic = 0;
    free(p);
    *pool = NULL;

    return SS_OK;
}

SsError ss_pool_alloc_sector(SsPool *pool, Sector **sector)
{
    if (!pool || !sector || pool->magic != SS_LINUX_POOL_MAGIC) {
        return SS_ERROR_INVALID;
    }

#ifdef SS_DEBUG_TIMING
    uint64_t start_time = ss_linux_get_timer_us();
#endif

    SS_SCOPED_LOCK(pool->mutex);

    if (pool->free_sectors == 0) {
        pool->stats.alloc_failures++;
        return SS_ERROR_NOMEM;
    }

    /* Get next free sector index */
    uint32_t sector_index = pool->free_list[pool->free_head];
    pool->free_head++;
    pool->free_sectors--;

    /* Get sector pointer and initialize it */
    Sector *new_sector = get_sector_by_index(pool, sector_index);
    if (!new_sector) {
        return SS_ERROR_INVALID;
    }

    /* Initialize sector */
    memset(new_sector, 0, pool->sector_size);
    new_sector->sector_index = sector_index;

    /* Initialize header with default values */
    new_sector->header.magic = SS_SECTOR_MAGIC;
    new_sector->header.state = SECTOR_FREE;

#ifdef SS_DEBUG_TIMING
    uint64_t alloc_time = ss_linux_get_timer_us() - start_time;
    update_alloc_stats(pool, alloc_time);
#else
    update_alloc_stats(pool, 0);
#endif

    /* Check pressure threshold */
    if (pool->pressure_callback &&
        pool->stats.usage_percent >= pool->pressure_threshold) {
        pool->pressure_callback(pool, pool->stats.usage_percent, pool->pressure_user_data);
    }

    *sector = new_sector;
    return SS_OK;
}

SsError ss_pool_free_sector(SsPool *pool, Sector **sector)
{
    if (!pool || !sector || !*sector || pool->magic != SS_LINUX_POOL_MAGIC) {
        return SS_ERROR_INVALID;
    }

#ifdef SS_DEBUG_TIMING
    uint64_t start_time = ss_linux_get_timer_us();
#endif

    Sector *s = *sector;

    /* Validate sector belongs to this pool */
    if (!ss_pool_validate_sector(pool, s)) {
        return SS_ERROR_INVALID;
    }

    SS_SCOPED_LOCK(pool->mutex);

    uint32_t sector_index = s->sector_index;

    /* Reset sector to clean state */
    memset(s, 0, pool->sector_size);

    /* Add back to free list */
    if (pool->free_head == 0) {
        /* Free list is full, this shouldn't happen */
        return SS_ERROR_INVALID;
    }

    pool->free_head--;
    pool->free_list[pool->free_head] = sector_index;
    pool->free_sectors++;

#ifdef SS_DEBUG_TIMING
    uint64_t free_time = ss_linux_get_timer_us() - start_time;
    update_free_stats(pool, free_time);
#else
    update_free_stats(pool, 0);
#endif

    *sector = NULL;
    return SS_OK;
}

SsError ss_pool_get_stats(const SsPool *pool, SsPoolStats *stats)
{
    if (!pool || !stats || pool->magic != SS_LINUX_POOL_MAGIC) {
        return SS_ERROR_INVALID;
    }

    SS_SCOPED_LOCK(pool->mutex);
    *stats = pool->stats;

    return SS_OK;
}

SsError ss_pool_reset_stats(SsPool *pool)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC) {
        return SS_ERROR_INVALID;
    }

    SS_SCOPED_LOCK(pool->mutex);

    /* Preserve current allocation state */
    uint32_t total_sectors = pool->stats.total_sectors;
    uint32_t free_sectors = pool->stats.free_sectors;
    uint32_t used_sectors = pool->stats.used_sectors;
    uint32_t usage_percent = pool->stats.usage_percent;

    memset(&pool->stats, 0, sizeof(pool->stats));

    pool->stats.total_sectors = total_sectors;
    pool->stats.free_sectors = free_sectors;
    pool->stats.used_sectors = used_sectors;
    pool->stats.usage_percent = usage_percent;

    return SS_OK;
}

bool ss_pool_usage_exceeds(const SsPool *pool, uint32_t threshold_percent)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC || threshold_percent > 100) {
        return false;
    }

    return pool->stats.usage_percent >= threshold_percent;
}

uint32_t ss_pool_get_sector_size(const SsPool *pool)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC) {
        return 0;
    }

    return pool->sector_size;
}

uint32_t ss_pool_get_capacity(const SsPool *pool)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC) {
        return 0;
    }

    return pool->total_sectors;
}

uint32_t ss_pool_get_available(const SsPool *pool)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC) {
        return 0;
    }

    return pool->free_sectors;
}

bool ss_pool_validate_sector(const SsPool *pool, const Sector *sector)
{
    if (!pool || !sector || pool->magic != SS_LINUX_POOL_MAGIC) {
        return false;
    }

    uint8_t *pool_start = (uint8_t *)pool->pool_memory;
    uint8_t *pool_end = pool_start + ((size_t)pool->sector_size * pool->total_sectors);
    uint8_t *sector_ptr = (uint8_t *)sector;

    /* Check if sector is within pool bounds */
    if (sector_ptr < pool_start || sector_ptr >= pool_end) {
        return false;
    }

    /* Check if sector is properly aligned */
    size_t offset = sector_ptr - pool_start;
    if (offset % pool->sector_size != 0) {
        return false;
    }

    return true;
}

uint32_t ss_pool_get_sector_index(const SsPool *pool, const Sector *sector)
{
    if (!ss_pool_validate_sector(pool, sector)) {
        return UINT32_MAX;
    }

    uint8_t *pool_start = (uint8_t *)pool->pool_memory;
    uint8_t *sector_ptr = (uint8_t *)sector;
    size_t offset = sector_ptr - pool_start;

    return (uint32_t)(offset / pool->sector_size);
}

Sector *ss_pool_get_sector_by_index(const SsPool *pool, uint32_t index)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC) {
        return NULL;
    }

    return get_sector_by_index(pool, index);
}

SsError ss_pool_set_pressure_callback(SsPool *pool, uint32_t threshold_percent,
                                      SsPoolPressureCallback callback, void *user_data)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC || threshold_percent > 100) {
        return SS_ERROR_INVALID;
    }

    SS_SCOPED_LOCK(pool->mutex);

    pool->pressure_threshold = threshold_percent;
    pool->pressure_callback = callback;
    pool->pressure_user_data = user_data;

    return SS_OK;
}

SsError ss_pool_maintenance(SsPool *pool)
{
    if (!pool || pool->magic != SS_LINUX_POOL_MAGIC) {
        return SS_ERROR_INVALID;
    }

    /* Update current statistics */
    SS_SCOPED_LOCK(pool->mutex);

    pool->stats.used_sectors = pool->total_sectors - pool->free_sectors;
    pool->stats.usage_percent = (pool->stats.used_sectors * 100) / pool->total_sectors;

    /* Check pressure threshold */
    if (pool->pressure_callback &&
        pool->stats.usage_percent >= pool->pressure_threshold) {
        pool->pressure_callback(pool, pool->stats.usage_percent, pool->pressure_user_data);
    }

    return SS_OK;
}

uint64_t ss_linux_get_timestamp_ms(bool utc_time)
{
    struct timespec ts;

    if (utc_time) {
        clock_gettime(CLOCK_REALTIME, &ts);
    } else {
        clock_gettime(CLOCK_MONOTONIC, &ts);
    }

    return (uint64_t)ts.tv_sec * 1000ULL + (uint64_t)ts.tv_nsec / 1000000ULL;
}

void ss_linux_sleep_ms(uint32_t ms)
{
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000;
    nanosleep(&ts, NULL);
}

uint64_t ss_linux_get_timer_us(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)ts.tv_nsec / 1000ULL;
}