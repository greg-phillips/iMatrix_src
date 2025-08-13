/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 *
 * This software, associated documentation and materials ("Software"),
 * is owned by iMatrix Systems ("iMatrix") and is protected by and subject to
 * worldwide patent protection (United States and foreign),
 * United States copyright laws and international treaty provisions.
 * Therefore, you may use this Software only as provided in the license
 * agreement accompanying the software package from which you
 * obtained this Software ("EULA").
 */

/**
 * @file memory_test_disk_sim.c
 * @brief Implementation of disk space simulation facility
 * 
 * Provides configurable disk space simulation for testing memory manager
 * behavior under various storage conditions.
 * 
 * @author Greg Phillips
 * @date 2025-01-09
 * @copyright iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include "memory_test_disk_sim.h"

/******************************************************
 *                    Constants
 ******************************************************/

/** Maximum log message length */
#define MAX_LOG_MSG_LEN     256

/******************************************************
 *               Static Variables
 ******************************************************/

/** Global simulation configuration */
static disk_sim_config_t g_sim_config = {
    .enabled = false,
    .mode = DISK_SIM_MODE_NORMAL,
    .total_bytes = DEFAULT_SIMULATED_DISK_SIZE,
    .available_bytes = DEFAULT_SIMULATED_DISK_SIZE,
    .usage_percentage = 0,
    .fail_after_count = 0,
    .gradual_fill_rate = 0,
    .log_operations = false
};

/** Global simulation statistics */
static disk_sim_stats_t g_sim_stats = {0};

/** Mutex for thread-safe operations */
static pthread_mutex_t g_sim_mutex = PTHREAD_MUTEX_INITIALIZER;

/** Operation counter for fail-after mode */
static uint32_t g_operation_count = 0;

/** Current available bytes for gradual fill mode */
static uint64_t g_gradual_available = 0;

/******************************************************
 *               Helper Functions
 ******************************************************/

/**
 * @brief Log simulation operation if logging enabled
 * 
 * @param format Printf-style format string
 * @param ... Variable arguments
 */
static void sim_log(const char *format, ...)
{
    if (!g_sim_config.log_operations) {
        return;
    }
    
    va_list args;
    va_start(args, format);
    
    printf("[DISK_SIM] ");
    vprintf(format, args);
    printf("\n");
    
    va_end(args);
}

/**
 * @brief Calculate available bytes from usage percentage
 * 
 * @param total Total bytes
 * @param usage_percent Usage percentage (0-100)
 * @return Available bytes
 */
static uint64_t calculate_available_from_percentage(uint64_t total, uint32_t usage_percent)
{
    if (usage_percent >= 100) {
        return 0;
    }
    
    uint64_t used = (total * usage_percent) / 100;
    return total - used;
}

/******************************************************
 *               Public Functions
 ******************************************************/

/**
 * @brief Initialize disk space simulation facility
 */
void disk_sim_init(void)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    // Reset configuration to defaults
    g_sim_config.enabled = false;
    g_sim_config.mode = DISK_SIM_MODE_NORMAL;
    g_sim_config.total_bytes = DEFAULT_SIMULATED_DISK_SIZE;
    g_sim_config.available_bytes = DEFAULT_SIMULATED_DISK_SIZE;
    g_sim_config.usage_percentage = 0;
    g_sim_config.fail_after_count = 0;
    g_sim_config.gradual_fill_rate = 0;
    g_sim_config.log_operations = false;
    
    // Reset statistics
    memset(&g_sim_stats, 0, sizeof(g_sim_stats));
    
    // Reset counters
    g_operation_count = 0;
    g_gradual_available = DEFAULT_SIMULATED_DISK_SIZE;
    
    pthread_mutex_unlock(&g_sim_mutex);
    
    sim_log("Disk simulation initialized");
}

/**
 * @brief Cleanup disk space simulation facility
 */
void disk_sim_cleanup(void)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_config.enabled = false;
    sim_log("Disk simulation cleaned up");
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Enable or disable disk space simulation
 */
void disk_sim_enable(bool enable)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_config.enabled = enable;
    sim_log("Disk simulation %s", enable ? "enabled" : "disabled");
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Check if disk simulation is enabled
 */
bool disk_sim_is_enabled(void)
{
    bool enabled;
    
    pthread_mutex_lock(&g_sim_mutex);
    enabled = g_sim_config.enabled;
    pthread_mutex_unlock(&g_sim_mutex);
    
    return enabled;
}

/**
 * @brief Set simulated disk usage percentage
 */
bool disk_sim_set_usage_percentage(uint32_t percentage)
{
    if (percentage > 100) {
        return false;
    }
    
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_config.mode = DISK_SIM_MODE_PERCENTAGE;
    g_sim_config.usage_percentage = percentage;
    g_sim_config.available_bytes = calculate_available_from_percentage(
        g_sim_config.total_bytes, percentage);
    
    g_sim_stats.usage_percentage = percentage;
    
    sim_log("Set disk usage to %u%% (available: %llu bytes)", 
            percentage, (unsigned long long)g_sim_config.available_bytes);
    
    pthread_mutex_unlock(&g_sim_mutex);
    
    return true;
}

/**
 * @brief Set exact simulated disk space values
 */
bool disk_sim_set_exact_bytes(uint64_t total_bytes, uint64_t available_bytes)
{
    if (available_bytes > total_bytes) {
        return false;
    }
    
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_config.mode = DISK_SIM_MODE_EXACT_BYTES;
    g_sim_config.total_bytes = total_bytes;
    g_sim_config.available_bytes = available_bytes;
    
    // Calculate percentage for stats
    if (total_bytes > 0) {
        uint64_t used = total_bytes - available_bytes;
        g_sim_config.usage_percentage = (uint32_t)((used * 100) / total_bytes);
        g_sim_stats.usage_percentage = g_sim_config.usage_percentage;
    }
    
    sim_log("Set exact disk space: total=%llu, available=%llu (%u%% used)",
            (unsigned long long)total_bytes,
            (unsigned long long)available_bytes,
            g_sim_config.usage_percentage);
    
    pthread_mutex_unlock(&g_sim_mutex);
    
    return true;
}

/**
 * @brief Configure simulation to fail after N operations
 */
void disk_sim_set_fail_after(uint32_t count)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_config.mode = DISK_SIM_MODE_FAIL_AFTER_N;
    g_sim_config.fail_after_count = count;
    g_operation_count = 0;
    
    sim_log("Set to fail after %u operations", count);
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Configure gradual disk fill simulation
 */
void disk_sim_set_gradual_fill(uint32_t bytes_per_operation, 
                               uint32_t initial_usage_percentage)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_config.mode = DISK_SIM_MODE_GRADUAL_FILL;
    g_sim_config.gradual_fill_rate = bytes_per_operation;
    g_sim_config.usage_percentage = initial_usage_percentage;
    
    g_gradual_available = calculate_available_from_percentage(
        g_sim_config.total_bytes, initial_usage_percentage);
    g_sim_config.available_bytes = g_gradual_available;
    
    sim_log("Set gradual fill: %u bytes/op, starting at %u%% usage",
            bytes_per_operation, initial_usage_percentage);
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Reset disk simulation to default state
 */
void disk_sim_reset(void)
{
    disk_sim_init();
}

/**
 * @brief Get current simulation statistics
 */
void disk_sim_get_stats(disk_sim_stats_t *stats)
{
    if (!stats) {
        return;
    }
    
    pthread_mutex_lock(&g_sim_mutex);
    
    memcpy(stats, &g_sim_stats, sizeof(disk_sim_stats_t));
    stats->current_mode = g_sim_config.mode;
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Print simulation statistics
 */
void disk_sim_print_stats(void)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    printf("\n=== Disk Simulation Statistics ===\n");
    printf("Enabled:            %s\n", g_sim_config.enabled ? "Yes" : "No");
    printf("Mode:               ");
    
    switch (g_sim_config.mode) {
        case DISK_SIM_MODE_NORMAL:
            printf("Normal (no simulation)\n");
            break;
        case DISK_SIM_MODE_PERCENTAGE:
            printf("Percentage (%u%%)\n", g_sim_config.usage_percentage);
            break;
        case DISK_SIM_MODE_EXACT_BYTES:
            printf("Exact bytes\n");
            break;
        case DISK_SIM_MODE_GRADUAL_FILL:
            printf("Gradual fill (%u bytes/op)\n", g_sim_config.gradual_fill_rate);
            break;
        case DISK_SIM_MODE_FAIL_AFTER_N:
            printf("Fail after %u ops\n", g_sim_config.fail_after_count);
            break;
    }
    
    printf("Total space:        %llu MB\n", 
           (unsigned long long)(g_sim_config.total_bytes / (1024 * 1024)));
    printf("Available space:    %llu MB\n", 
           (unsigned long long)(g_sim_config.available_bytes / (1024 * 1024)));
    printf("Usage:              %u%%\n", g_sim_stats.usage_percentage);
    printf("statvfs calls:      %u\n", g_sim_stats.statvfs_calls);
    printf("Simulated calls:    %u\n", g_sim_stats.simulated_calls);
    printf("Allocation attempts:%u\n", g_sim_stats.allocation_attempts);
    printf("Forced failures:    %u\n", g_sim_stats.forced_failures);
    printf("=================================\n\n");
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Enable/disable operation logging
 */
void disk_sim_set_logging(bool enable)
{
    pthread_mutex_lock(&g_sim_mutex);
    g_sim_config.log_operations = enable;
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Simulated statvfs function
 */
int disk_sim_statvfs(const char *path, struct statvfs *buf)
{
    if (!buf) {
        errno = EINVAL;
        return -1;
    }
    
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_stats.statvfs_calls++;
    
    if (!g_sim_config.enabled) {
        pthread_mutex_unlock(&g_sim_mutex);
        // Fall back to real statvfs
        return statvfs(path, buf);
    }
    
    g_sim_stats.simulated_calls++;
    
    // Fill in simulated values
    memset(buf, 0, sizeof(struct statvfs));
    
    buf->f_bsize = DEFAULT_SIMULATED_BLOCK_SIZE;    // Block size
    buf->f_frsize = DEFAULT_SIMULATED_BLOCK_SIZE;   // Fragment size
    buf->f_blocks = g_sim_config.total_bytes / DEFAULT_SIMULATED_BLOCK_SIZE;
    buf->f_bfree = g_sim_config.available_bytes / DEFAULT_SIMULATED_BLOCK_SIZE;
    buf->f_bavail = buf->f_bfree;  // Available to non-privileged users
    buf->f_files = 1000000;         // Total inodes
    buf->f_ffree = 999000;          // Free inodes
    buf->f_favail = 999000;         // Available inodes
    buf->f_fsid = 0x12345678;       // File system ID
    buf->f_flag = 0;                // Mount flags
    buf->f_namemax = 255;           // Maximum filename length
    
    // Handle special modes
    switch (g_sim_config.mode) {
        case DISK_SIM_MODE_FAIL_AFTER_N:
            g_operation_count++;
            if (g_operation_count > g_sim_config.fail_after_count) {
                buf->f_bavail = 0;
                buf->f_bfree = 0;
                g_sim_stats.forced_failures++;
                sim_log("Forcing disk full after %u operations", g_operation_count);
            }
            break;
            
        case DISK_SIM_MODE_GRADUAL_FILL:
            if (g_gradual_available > g_sim_config.gradual_fill_rate) {
                g_gradual_available -= g_sim_config.gradual_fill_rate;
            } else {
                g_gradual_available = 0;
            }
            buf->f_bavail = g_gradual_available / DEFAULT_SIMULATED_BLOCK_SIZE;
            buf->f_bfree = buf->f_bavail;
            
            // Update usage percentage
            uint64_t used = g_sim_config.total_bytes - g_gradual_available;
            g_sim_stats.usage_percentage = (uint32_t)((used * 100) / g_sim_config.total_bytes);
            sim_log("Gradual fill: now at %u%% usage", g_sim_stats.usage_percentage);
            break;
            
        default:
            // Normal percentage or exact bytes mode - values already set
            break;
    }
    
    sim_log("statvfs returning: total=%llu MB, available=%llu MB",
            (unsigned long long)(buf->f_blocks * buf->f_frsize / (1024 * 1024)),
            (unsigned long long)(buf->f_bavail * buf->f_frsize / (1024 * 1024)));
    
    pthread_mutex_unlock(&g_sim_mutex);
    
    return 0;
}

/**
 * @brief Hook function for memory manager integration
 */
bool disk_sim_hook_statvfs(int real_statvfs_result, struct statvfs *stat)
{
    if (!g_sim_config.enabled || !stat) {
        return false;
    }
    
    // If real statvfs failed, don't modify
    if (real_statvfs_result != 0) {
        return false;
    }
    
    // Use our simulated statvfs
    disk_sim_statvfs("simulated", stat);
    return true;
}

/**
 * @brief Simulate a disk write operation
 */
void disk_sim_write_occurred(uint64_t bytes)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    g_sim_stats.allocation_attempts++;
    
    if (g_sim_config.mode == DISK_SIM_MODE_EXACT_BYTES) {
        if (g_sim_config.available_bytes >= bytes) {
            g_sim_config.available_bytes -= bytes;
            
            // Update usage percentage
            uint64_t used = g_sim_config.total_bytes - g_sim_config.available_bytes;
            g_sim_stats.usage_percentage = (uint32_t)((used * 100) / g_sim_config.total_bytes);
            
            sim_log("Write occurred: %llu bytes (available now: %llu)",
                    (unsigned long long)bytes,
                    (unsigned long long)g_sim_config.available_bytes);
        }
    }
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Simulate a disk delete operation
 */
void disk_sim_delete_occurred(uint64_t bytes)
{
    pthread_mutex_lock(&g_sim_mutex);
    
    if (g_sim_config.mode == DISK_SIM_MODE_EXACT_BYTES) {
        g_sim_config.available_bytes += bytes;
        if (g_sim_config.available_bytes > g_sim_config.total_bytes) {
            g_sim_config.available_bytes = g_sim_config.total_bytes;
        }
        
        // Update usage percentage
        uint64_t used = g_sim_config.total_bytes - g_sim_config.available_bytes;
        g_sim_stats.usage_percentage = (uint32_t)((used * 100) / g_sim_config.total_bytes);
        
        sim_log("Delete occurred: %llu bytes (available now: %llu)",
                (unsigned long long)bytes,
                (unsigned long long)g_sim_config.available_bytes);
    }
    
    pthread_mutex_unlock(&g_sim_mutex);
}

/**
 * @brief Load simulation configuration from environment
 */
void disk_sim_load_env_config(void)
{
    const char *env_val;
    
    // Check for usage percentage
    env_val = getenv("IMX_TEST_DISK_USAGE");
    if (env_val) {
        uint32_t usage = (uint32_t)atoi(env_val);
        if (usage <= 100) {
            disk_sim_set_usage_percentage(usage);
            disk_sim_enable(true);
            printf("Disk simulation: Set usage to %u%% from environment\n", usage);
        }
    }
    
    // Check for disk size in MB
    env_val = getenv("IMX_TEST_DISK_SIZE");
    if (env_val) {
        uint64_t size_mb = (uint64_t)atoll(env_val);
        if (size_mb > 0) {
            uint64_t total_bytes = size_mb * 1024 * 1024;
            uint64_t available = calculate_available_from_percentage(
                total_bytes, g_sim_config.usage_percentage);
            disk_sim_set_exact_bytes(total_bytes, available);
            printf("Disk simulation: Set size to %llu MB from environment\n",
                   (unsigned long long)size_mb);
        }
    }
    
    // Check for simulation mode
    env_val = getenv("IMX_TEST_DISK_MODE");
    if (env_val) {
        if (strcmp(env_val, "gradual") == 0) {
            disk_sim_set_gradual_fill(1024 * 1024, 50); // 1MB per op, start at 50%
            disk_sim_enable(true);
            printf("Disk simulation: Gradual fill mode from environment\n");
        } else if (strcmp(env_val, "fail5") == 0) {
            disk_sim_set_fail_after(5);
            disk_sim_enable(true);
            printf("Disk simulation: Fail after 5 operations from environment\n");
        }
    }
    
    // Check for logging
    env_val = getenv("IMX_TEST_DISK_LOG");
    if (env_val && atoi(env_val) > 0) {
        disk_sim_set_logging(true);
        printf("Disk simulation: Logging enabled from environment\n");
    }
}