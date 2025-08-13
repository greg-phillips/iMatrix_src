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
 * @file memory_test_disk_sim.h
 * @brief Disk space simulation facility for memory manager testing
 * 
 * This module provides functions to simulate various disk space conditions
 * for testing the memory manager's behavior under different storage scenarios
 * without requiring actual disk space constraints.
 * 
 * @author Greg Phillips
 * @date 2025-01-09
 * @copyright iMatrix Systems, Inc.
 */

#ifndef MEMORY_TEST_DISK_SIM_H_
#define MEMORY_TEST_DISK_SIM_H_

#include <stdint.h>
#include <stdbool.h>
#include <sys/statvfs.h>

/******************************************************
 *                    Constants
 ******************************************************/

/** Default simulated disk size (10GB) */
#define DEFAULT_SIMULATED_DISK_SIZE     (10ULL * 1024 * 1024 * 1024)

/** Default simulated block size */
#define DEFAULT_SIMULATED_BLOCK_SIZE    (4096)

/******************************************************
 *                    Enumerations
 ******************************************************/

/**
 * @brief Disk simulation modes
 */
typedef enum {
    DISK_SIM_MODE_NORMAL = 0,       /**< Normal operation (no simulation) */
    DISK_SIM_MODE_PERCENTAGE,       /**< Simulate specific usage percentage */
    DISK_SIM_MODE_EXACT_BYTES,      /**< Simulate exact byte values */
    DISK_SIM_MODE_GRADUAL_FILL,     /**< Gradually increase usage */
    DISK_SIM_MODE_FAIL_AFTER_N      /**< Fail after N operations */
} disk_sim_mode_t;

/******************************************************
 *                    Structures
 ******************************************************/

/**
 * @brief Disk simulation statistics
 */
typedef struct {
    uint32_t statvfs_calls;         /**< Number of statvfs calls */
    uint32_t simulated_calls;       /**< Number of simulated responses */
    uint32_t allocation_attempts;   /**< Number of allocation attempts */
    uint32_t forced_failures;       /**< Number of forced failures */
    disk_sim_mode_t current_mode;   /**< Current simulation mode */
    uint32_t usage_percentage;      /**< Current simulated usage % */
} disk_sim_stats_t;

/**
 * @brief Disk simulation configuration
 */
typedef struct {
    bool enabled;                   /**< Simulation enabled flag */
    disk_sim_mode_t mode;          /**< Simulation mode */
    uint64_t total_bytes;          /**< Total disk space in bytes */
    uint64_t available_bytes;      /**< Available disk space in bytes */
    uint32_t usage_percentage;     /**< Target usage percentage (0-100) */
    uint32_t fail_after_count;     /**< Fail after N operations */
    uint32_t gradual_fill_rate;    /**< Bytes to consume per operation */
    bool log_operations;           /**< Log simulation operations */
} disk_sim_config_t;

/******************************************************
 *                Function Declarations
 ******************************************************/

/**
 * @brief Initialize disk space simulation facility
 * 
 * Sets up the simulation system with default values.
 * Must be called before using any other simulation functions.
 */
void disk_sim_init(void);

/**
 * @brief Cleanup disk space simulation facility
 * 
 * Releases resources and disables simulation.
 */
void disk_sim_cleanup(void);

/**
 * @brief Enable or disable disk space simulation
 * 
 * @param enable true to enable simulation, false to disable
 */
void disk_sim_enable(bool enable);

/**
 * @brief Check if disk simulation is enabled
 * 
 * @return true if simulation is enabled
 */
bool disk_sim_is_enabled(void);

/**
 * @brief Set simulated disk usage percentage
 * 
 * Configures simulation to report specified disk usage percentage.
 * 
 * @param percentage Disk usage percentage (0-100)
 * @return true on success, false on invalid percentage
 */
bool disk_sim_set_usage_percentage(uint32_t percentage);

/**
 * @brief Set exact simulated disk space values
 * 
 * Configures simulation to report exact byte values.
 * 
 * @param total_bytes Total disk space in bytes
 * @param available_bytes Available disk space in bytes
 * @return true on success, false on invalid values
 */
bool disk_sim_set_exact_bytes(uint64_t total_bytes, uint64_t available_bytes);

/**
 * @brief Configure simulation to fail after N operations
 * 
 * After the specified number of statvfs calls, simulation will
 * report disk full condition.
 * 
 * @param count Number of operations before failure (0 to disable)
 */
void disk_sim_set_fail_after(uint32_t count);

/**
 * @brief Configure gradual disk fill simulation
 * 
 * Each operation will consume the specified number of bytes,
 * gradually filling the disk.
 * 
 * @param bytes_per_operation Bytes to consume per operation
 * @param initial_usage_percentage Starting disk usage percentage
 */
void disk_sim_set_gradual_fill(uint32_t bytes_per_operation, 
                               uint32_t initial_usage_percentage);

/**
 * @brief Reset disk simulation to default state
 * 
 * Resets all simulation parameters and statistics.
 */
void disk_sim_reset(void);

/**
 * @brief Get current simulation statistics
 * 
 * @param stats Pointer to structure to receive statistics
 */
void disk_sim_get_stats(disk_sim_stats_t *stats);

/**
 * @brief Print simulation statistics
 * 
 * Outputs current simulation configuration and statistics.
 */
void disk_sim_print_stats(void);

/**
 * @brief Enable/disable operation logging
 * 
 * @param enable true to enable logging
 */
void disk_sim_set_logging(bool enable);

/**
 * @brief Simulated statvfs function
 * 
 * This function can be used to replace statvfs calls in test code.
 * It returns simulated values based on current configuration.
 * 
 * @param path File system path (ignored in simulation)
 * @param buf Buffer to receive simulated statistics
 * @return 0 on success, -1 on error (sets errno)
 */
int disk_sim_statvfs(const char *path, struct statvfs *buf);

/**
 * @brief Hook function for memory manager integration
 * 
 * This function should be called from get_available_disk_space()
 * and similar functions to enable simulation.
 * 
 * @param real_statvfs_result Result from real statvfs call
 * @param stat Pointer to statvfs structure to modify
 * @return true if simulation modified the values
 */
bool disk_sim_hook_statvfs(int real_statvfs_result, struct statvfs *stat);

/**
 * @brief Simulate a disk write operation
 * 
 * Updates simulation state as if bytes were written to disk.
 * 
 * @param bytes Number of bytes written
 */
void disk_sim_write_occurred(uint64_t bytes);

/**
 * @brief Simulate a disk delete operation
 * 
 * Updates simulation state as if bytes were freed from disk.
 * 
 * @param bytes Number of bytes freed
 */
void disk_sim_delete_occurred(uint64_t bytes);

/**
 * @brief Load simulation configuration from environment
 * 
 * Checks for environment variables:
 * - IMX_TEST_DISK_USAGE: Set usage percentage (0-100)
 * - IMX_TEST_DISK_SIZE: Set total disk size in MB
 * - IMX_TEST_DISK_MODE: Set simulation mode
 */
void disk_sim_load_env_config(void);

#endif /* MEMORY_TEST_DISK_SIM_H_ */