/**
 * @file ss_mutex.h
 * @brief Platform-agnostic mutex abstraction for sensor storage
 *
 * Provides thread-safe synchronization primitives that work across
 * STM32 and Linux platforms. The implementation adapts to the
 * available threading model on each platform.
 *
 * Platform Support:
 * - STM32: Critical sections, FreeRTOS mutexes, or simple disable/enable IRQ
 * - Linux: pthread mutexes with error checking
 * - Common interface for all sensor storage components
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#ifndef SS_MUTEX_H
#define SS_MUTEX_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Platform-specific mutex handle
 *
 * The actual structure varies by platform and is defined in
 * platform-specific implementation files.
 */
typedef struct SsMutex SsMutex;

/**
 * @brief Mutex initialization result codes
 */
typedef enum {
    SS_MUTEX_OK = 0,        /**< Success */
    SS_MUTEX_ERROR = -1,    /**< General error */
    SS_MUTEX_NOMEM = -2,    /**< Out of memory */
    SS_MUTEX_BUSY = -3,     /**< Resource busy */
    SS_MUTEX_TIMEOUT = -4   /**< Operation timed out */
} SsMutexResult;

/**
 * @brief Initialize the mutex subsystem
 *
 * Platform-specific initialization of mutex management.
 * Must be called once during system startup.
 *
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_init_system(void);

/**
 * @brief Create and initialize a new mutex
 *
 * Allocates and initializes a mutex for use in sensor storage.
 * The mutex is created in unlocked state.
 *
 * @param mutex Pointer to store allocated mutex handle
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_create(SsMutex **mutex);

/**
 * @brief Destroy a mutex and free resources
 *
 * Destroys the mutex and releases associated resources.
 * The mutex should be unlocked before calling this function.
 *
 * @param mutex Mutex to destroy (will be set to NULL)
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_destroy(SsMutex **mutex);

/**
 * @brief Lock a mutex (blocking)
 *
 * Acquire exclusive lock on the mutex. If the mutex is already
 * locked by another thread, this function blocks until available.
 *
 * @param mutex Mutex to lock
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_lock(SsMutex *mutex);

/**
 * @brief Try to lock a mutex (non-blocking)
 *
 * Attempt to acquire exclusive lock on the mutex. If the mutex
 * is already locked, returns immediately with SS_MUTEX_BUSY.
 *
 * @param mutex Mutex to try locking
 * @return SS_MUTEX_OK if locked, SS_MUTEX_BUSY if unavailable, error code on failure
 */
SsMutexResult ss_mutex_trylock(SsMutex *mutex);

/**
 * @brief Lock a mutex with timeout
 *
 * Attempt to acquire exclusive lock with a maximum wait time.
 * If timeout expires, returns SS_MUTEX_TIMEOUT.
 *
 * @param mutex Mutex to lock
 * @param timeout_ms Maximum time to wait in milliseconds
 * @return SS_MUTEX_OK if locked, SS_MUTEX_TIMEOUT if expired, error code on failure
 */
SsMutexResult ss_mutex_lock_timeout(SsMutex *mutex, uint32_t timeout_ms);

/**
 * @brief Unlock a mutex
 *
 * Release exclusive lock on the mutex. The calling thread must
 * currently hold the lock.
 *
 * @param mutex Mutex to unlock
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_unlock(SsMutex *mutex);

/**
 * @brief Check if mutex is currently locked
 *
 * Non-blocking check of mutex state. Note that the state may
 * change immediately after this function returns.
 *
 * @param mutex Mutex to check
 * @return true if locked, false if available
 */
bool ss_mutex_is_locked(const SsMutex *mutex);

/**
 * @brief Get platform-specific mutex information
 *
 * Returns platform-specific information about the mutex for
 * debugging and diagnostics.
 *
 * @param mutex Mutex to query
 * @param info_buffer Buffer to store information string
 * @param buffer_size Size of info_buffer
 * @return Number of characters written, 0 on error
 */
uint32_t ss_mutex_get_info(const SsMutex *mutex, char *info_buffer, uint32_t buffer_size);

/**
 * @brief Scoped mutex lock for automatic unlocking
 *
 * RAII-style mutex management using compiler cleanup attribute.
 * The mutex is automatically unlocked when the variable goes out of scope.
 *
 * Usage:
 * {
 *     SS_SCOPED_LOCK(my_mutex);
 *     // Critical section - mutex is locked
 *     // ... do work ...
 * } // Mutex is automatically unlocked here
 */
typedef struct {
    SsMutex *mutex;
} SsScopedLock;

/**
 * @brief Initialize scoped lock
 * @param lock Scoped lock structure
 * @param mutex Mutex to manage
 */
static inline void ss_scoped_lock_init(SsScopedLock *lock, SsMutex *mutex) {
    lock->mutex = mutex;
    if (mutex) {
        ss_mutex_lock(mutex);
    }
}

/**
 * @brief Cleanup function for scoped lock
 * @param lock Scoped lock structure
 */
static inline void ss_scoped_lock_cleanup(SsScopedLock *lock) {
    if (lock && lock->mutex) {
        ss_mutex_unlock(lock->mutex);
        lock->mutex = NULL;
    }
}

/**
 * @brief Macro for scoped mutex locking
 */
#define SS_SCOPED_LOCK(mutex) \
    SsScopedLock __attribute__((cleanup(ss_scoped_lock_cleanup))) \
    _scoped_lock_##__LINE__ = {0}; \
    ss_scoped_lock_init(&_scoped_lock_##__LINE__, (mutex))

/**
 * @brief Simple lock/unlock macros for convenience
 */
#define SS_LOCK(mutex) ss_mutex_lock(mutex)
#define SS_UNLOCK(mutex) ss_mutex_unlock(mutex)
#define SS_TRYLOCK(mutex) ss_mutex_trylock(mutex)

/**
 * @brief Critical section timing measurement
 *
 * For performance optimization, measure time spent in critical sections.
 * Only enabled in debug builds to avoid overhead in production.
 */
#ifdef SS_DEBUG_TIMING
typedef struct {
    uint32_t lock_count;
    uint32_t total_time_us;
    uint32_t max_time_us;
    uint32_t contention_count;
} SsMutexStats;

/**
 * @brief Get mutex timing statistics
 * @param mutex Mutex to query
 * @param stats Structure to fill with statistics
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_get_stats(const SsMutex *mutex, SsMutexStats *stats);

/**
 * @brief Reset mutex timing statistics
 * @param mutex Mutex to reset
 * @return SS_MUTEX_OK on success, error code on failure
 */
SsMutexResult ss_mutex_reset_stats(SsMutex *mutex);
#endif /* SS_DEBUG_TIMING */

#ifdef __cplusplus
}
#endif

#endif /* SS_MUTEX_H */