/**
 * @file ss_mutex.c
 * @brief Platform-agnostic mutex implementation for sensor storage
 *
 * Provides mutex operations that adapt to the target platform.
 * This implementation focuses on Linux pthread support.
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#include "ss_mutex.h"
#include "../platform/ss_linux.h"
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <sys/time.h>

#ifdef SS_DEBUG_TIMING
/**
 * @brief Get current time in microseconds
 * @return Current time in microseconds
 */
static uint64_t get_time_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)ts.tv_nsec / 1000ULL;
}
#endif

SsMutexResult ss_mutex_init_system(void)
{
    return SS_MUTEX_OK;
}

SsMutexResult ss_mutex_create(SsMutex **mutex)
{
    if (!mutex) {
        return SS_MUTEX_ERROR;
    }

    SsMutex *new_mutex = malloc(sizeof(SsMutex));
    if (!new_mutex) {
        return SS_MUTEX_NOMEM;
    }

    memset(new_mutex, 0, sizeof(SsMutex));

    pthread_mutexattr_t attr;
    int result = pthread_mutexattr_init(&attr);
    if (result != 0) {
        free(new_mutex);
        return SS_MUTEX_ERROR;
    }

    result = pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ERRORCHECK);
    if (result != 0) {
        pthread_mutexattr_destroy(&attr);
        free(new_mutex);
        return SS_MUTEX_ERROR;
    }

    result = pthread_mutex_init(&new_mutex->handle, &attr);
    pthread_mutexattr_destroy(&attr);

    if (result != 0) {
        free(new_mutex);
        return SS_MUTEX_ERROR;
    }

    new_mutex->magic = SS_LINUX_MUTEX_MAGIC;

#ifdef SS_DEBUG_TIMING
    memset(&new_mutex->stats, 0, sizeof(new_mutex->stats));
#endif

    *mutex = new_mutex;
    return SS_MUTEX_OK;
}

SsMutexResult ss_mutex_destroy(SsMutex **mutex)
{
    if (!mutex || !*mutex) {
        return SS_MUTEX_ERROR;
    }

    SsMutex *m = *mutex;

    if (m->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

    int result = pthread_mutex_destroy(&m->handle);
    if (result != 0) {
        return SS_MUTEX_ERROR;
    }

    m->magic = 0;
    free(m);
    *mutex = NULL;

    return SS_MUTEX_OK;
}

SsMutexResult ss_mutex_lock(SsMutex *mutex)
{
    if (!mutex || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

#ifdef SS_DEBUG_TIMING
    uint64_t start_time = get_time_us();

    int try_result = pthread_mutex_trylock(&mutex->handle);
    if (try_result == EBUSY) {
        mutex->stats.contention_count++;
    }

    if (try_result != 0) {
        int result = pthread_mutex_lock(&mutex->handle);
        if (result != 0) {
            return SS_MUTEX_ERROR;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &mutex->lock_time);

    uint64_t lock_time = get_time_us() - start_time;
    mutex->stats.lock_count++;
    mutex->stats.total_time_us += lock_time;
    if (lock_time > mutex->stats.max_time_us) {
        mutex->stats.max_time_us = lock_time;
    }
#else
    int result = pthread_mutex_lock(&mutex->handle);
    if (result != 0) {
        return SS_MUTEX_ERROR;
    }
#endif

    return SS_MUTEX_OK;
}

SsMutexResult ss_mutex_trylock(SsMutex *mutex)
{
    if (!mutex || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

    int result = pthread_mutex_trylock(&mutex->handle);

    if (result == 0) {
#ifdef SS_DEBUG_TIMING
        clock_gettime(CLOCK_MONOTONIC, &mutex->lock_time);
        mutex->stats.lock_count++;
#endif
        return SS_MUTEX_OK;
    } else if (result == EBUSY) {
#ifdef SS_DEBUG_TIMING
        mutex->stats.contention_count++;
#endif
        return SS_MUTEX_BUSY;
    } else {
        return SS_MUTEX_ERROR;
    }
}

SsMutexResult ss_mutex_lock_timeout(SsMutex *mutex, uint32_t timeout_ms)
{
    if (!mutex || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

    struct timespec abs_timeout;
    clock_gettime(CLOCK_REALTIME, &abs_timeout);

    abs_timeout.tv_sec += timeout_ms / 1000;
    abs_timeout.tv_nsec += (timeout_ms % 1000) * 1000000;

    if (abs_timeout.tv_nsec >= 1000000000) {
        abs_timeout.tv_sec++;
        abs_timeout.tv_nsec -= 1000000000;
    }

#ifdef SS_DEBUG_TIMING
    uint64_t start_time = get_time_us();
#endif

    int result = pthread_mutex_timedlock(&mutex->handle, &abs_timeout);

    if (result == 0) {
#ifdef SS_DEBUG_TIMING
        clock_gettime(CLOCK_MONOTONIC, &mutex->lock_time);
        uint64_t lock_time = get_time_us() - start_time;
        mutex->stats.lock_count++;
        mutex->stats.total_time_us += lock_time;
        if (lock_time > mutex->stats.max_time_us) {
            mutex->stats.max_time_us = lock_time;
        }
#endif
        return SS_MUTEX_OK;
    } else if (result == ETIMEDOUT) {
        return SS_MUTEX_TIMEOUT;
    } else {
        return SS_MUTEX_ERROR;
    }
}

SsMutexResult ss_mutex_unlock(SsMutex *mutex)
{
    if (!mutex || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

    int result = pthread_mutex_unlock(&mutex->handle);
    if (result != 0) {
        return SS_MUTEX_ERROR;
    }

    return SS_MUTEX_OK;
}

bool ss_mutex_is_locked(const SsMutex *mutex)
{
    if (!mutex || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return false;
    }

    int result = pthread_mutex_trylock(&mutex->handle);

    if (result == 0) {
        pthread_mutex_unlock(&mutex->handle);
        return false;
    } else if (result == EBUSY) {
        return true;
    } else {
        return false;
    }
}

uint32_t ss_mutex_get_info(const SsMutex *mutex, char *info_buffer, uint32_t buffer_size)
{
    if (!mutex || !info_buffer || buffer_size == 0) {
        return 0;
    }

    if (mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return snprintf(info_buffer, buffer_size, "Invalid mutex (magic=0x%08X)", mutex->magic);
    }

#ifdef SS_DEBUG_TIMING
    return snprintf(info_buffer, buffer_size,
                   "pthread mutex: locks=%u, contentions=%u, total_time=%u us, max_time=%u us",
                   mutex->stats.lock_count,
                   mutex->stats.contention_count,
                   mutex->stats.total_time_us,
                   mutex->stats.max_time_us);
#else
    return snprintf(info_buffer, buffer_size, "pthread mutex: timing disabled");
#endif
}

#ifdef SS_DEBUG_TIMING
SsMutexResult ss_mutex_get_stats(const SsMutex *mutex, SsMutexStats *stats)
{
    if (!mutex || !stats || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

    *stats = mutex->stats;
    return SS_MUTEX_OK;
}

SsMutexResult ss_mutex_reset_stats(SsMutex *mutex)
{
    if (!mutex || mutex->magic != SS_LINUX_MUTEX_MAGIC) {
        return SS_MUTEX_ERROR;
    }

    memset(&mutex->stats, 0, sizeof(mutex->stats));
    return SS_MUTEX_OK;
}
#endif /* SS_DEBUG_TIMING */