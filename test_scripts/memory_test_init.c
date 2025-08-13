/**
 * @file memory_test_init.c
 * @brief Memory test initialization functions
 * 
 * This file provides initialization functions for memory tests that
 * properly set up the test environment to match the iMatrix system
 * initialization sequence without modifying production code.
 * 
 * @author Greg Phillips
 * @date 2025-01-08
 * @copyright iMatrix Systems, Inc.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>

// Include iMatrix headers
#include "storage.h"
#include "device/icb_def.h"
#include "imatrix.h"
#include "cs_ctrl/memory_manager.h"
#include "memory_test_init.h"
#include "memory_test_csb_csd.h"

/******************************************************
 *                    Constants
 ******************************************************/

#define CCM_POOL_LENGTH     (14 * 1024)    // Variable data allocated to this space
#define VAR_POOL_SIZE       (64 * 1024)    // Variable pool size for tests

/******************************************************
 *               External Variables
 ******************************************************/

// These are defined in storage.c and used by memory manager
extern iMatrix_Control_Block_t icb;
extern IOT_Device_Config_t device_config;

/******************************************************
 *               Static Variables
 ******************************************************/

// Memory pools for testing
static uint8_t test_ccm_pool_area[CCM_POOL_LENGTH];
static uint8_t *test_var_pool_data = NULL;

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Initialize test ICB structure
 * 
 * Sets up the iMatrix Control Block with test values
 * that match what the memory manager expects.
 */
static void initialize_test_icb(void)
{
    // Clear the ICB structure
    memset(&icb, 0, sizeof(iMatrix_Control_Block_t));
    
    // Set basic required fields
    icb.using_ccmsram = false;  // Not using CCM RAM in tests
    icb.ext_sram_failed = false;
    
    // Initialize SAT (will be properly set by imx_sat_init)
    memset(&icb.sat, 0, sizeof(sector_assignment_table_t));
}

/**
 * @brief Initialize test device configuration
 * 
 * Sets up the device configuration structure with
 * appropriate test values.
 */
static void initialize_test_device_config(void)
{
    // Clear the device config structure
    memset(&device_config, 0, sizeof(IOT_Device_Config_t));
    
    // Set test configuration values
    device_config.log_messages = 0;
    device_config.ext_sram_size = 0;  // No external SRAM by default
    device_config.slave_processor = false;
    
    // Set device identifiers
    strcpy(device_config.device_name, "MemoryTest");
    
    // Set other required fields
    device_config.no_controls = 0;
    device_config.no_sensors = 0;
}

/**
 * @brief Initialize memory pools
 * 
 * Allocates and initializes the variable data pool
 * used for dynamic memory allocation.
 */
static imx_status_t initialize_memory_pools(void)
{
    // Allocate variable pool
    test_var_pool_data = (uint8_t *)malloc(VAR_POOL_SIZE);
    if (test_var_pool_data == NULL) {
        printf("ERROR: Failed to allocate variable pool\n");
        return IMX_GENERAL_FAILURE;
    }
    
    // Clear the pools
    memset(test_var_pool_data, 0, VAR_POOL_SIZE);
    memset(test_ccm_pool_area, 0, CCM_POOL_LENGTH);
    
    // Set pool size info
    icb.var_pool_size = VAR_POOL_SIZE;
    
    return IMX_SUCCESS;
}

/**
 * @brief Create test storage directories (Linux only)
 * 
 * Creates the directory structure needed for tiered
 * storage testing on Linux platform.
 */
#ifdef LINUX_PLATFORM
static void create_test_storage_directories(void)
{
    int ret;
    
    // Create base storage directory
    ret = system("mkdir -p /tmp/imatrix_test_storage");
    (void)ret; // Explicitly ignore return value
    
    // Create history directory for disk storage (hierarchical buckets)
    ret = system("mkdir -p /tmp/imatrix_test_storage/history");
    (void)ret;
    
    // Create bucket directories (0-9) for hierarchical storage
    for (int i = 0; i < 10; i++) {
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "mkdir -p /tmp/imatrix_test_storage/history/%d", i);
        ret = system(cmd);
        (void)ret;
    }
    
    // Create subdirectories for hierarchical storage (legacy format)
    ret = system("mkdir -p /tmp/imatrix_test_storage/sensor_0000");
    (void)ret;
    ret = system("mkdir -p /tmp/imatrix_test_storage/sensor_0001");
    (void)ret;
    ret = system("mkdir -p /tmp/imatrix_test_storage/sensor_0002");
    (void)ret;
    ret = system("mkdir -p /tmp/imatrix_test_storage/sensor_0003");
    (void)ret;
    
    // Create corrupted data directories
    ret = system("mkdir -p /tmp/imatrix_test_storage/corrupted");
    (void)ret;
    ret = system("mkdir -p /tmp/imatrix_test_storage/history/corrupted");
    (void)ret;
    
    printf("Created test storage directories\n");
}
#endif

/**
 * @brief Initialize memory test environment
 * 
 * Main initialization function that sets up the complete
 * test environment for memory manager testing.
 * 
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t initialize_memory_test_environment(void)
{
    printf("=== Initializing Memory Test Environment ===\n");
    
    // Step 1: Initialize global structures
    printf("1. Initializing test structures...\n");
    initialize_test_icb();
    initialize_test_device_config();
    
    // Step 2: Initialize memory pools
    printf("2. Initializing memory pools...\n");
    if (initialize_memory_pools() != IMX_SUCCESS) {
        return IMX_GENERAL_FAILURE;
    }
    
    // Step 3: Platform-specific setup
#ifdef LINUX_PLATFORM
    printf("3. Creating test storage directories...\n");
    create_test_storage_directories();
#endif
    
    // Step 4: Initialize memory management system
    printf("4. Initializing memory manager...\n");
    // init_ext_memory internally calls imx_sat_init()
    init_ext_memory(device_config.ext_sram_size);
    
    // Step 5: Initialize tiered storage system (Linux)
#ifdef LINUX_PLATFORM
    printf("5. Initializing tiered storage system...\n");
    init_disk_storage_system();
    printf("   - Disk storage initialized\n");
#endif
    
    // Step 6: Initialize test CSB/CSD structures
    printf("6. Initializing test CSB/CSD structures...\n");
    if (init_test_sensors(&icb) == IMX_SUCCESS) {
        printf("   - Initialized %d test sensors\n", TEST_NUM_SENSORS);
    }
    
    if (init_test_controls(&icb) == IMX_SUCCESS) {
        printf("   - Initialized %d test controls\n", TEST_NUM_CONTROLS);
    }
    
    // Step 7: Verify initialization
    printf("7. Verifying initialization...\n");
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats) {
        printf("   - Total sectors: %u\n", stats->total_sectors);
        printf("   - Free sectors: %u\n", stats->free_sectors);
        printf("   - SAT initialized successfully\n");
    } else {
        printf("ERROR: Failed to get memory statistics\n");
        return IMX_GENERAL_FAILURE;
    }
    
    printf("=== Memory Test Environment Ready ===\n\n");
    return IMX_SUCCESS;
}

/**
 * @brief Initialize memory test with external SRAM
 * 
 * Initializes the test environment with external SRAM
 * configuration for testing external memory features.
 * 
 * @param ext_sram_size Size of external SRAM in bytes
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t initialize_memory_test_with_ext_sram(uint32_t ext_sram_size)
{
    // Set external SRAM size before initialization
    device_config.ext_sram_size = ext_sram_size;
    
    // Run standard initialization
    return initialize_memory_test_environment();
}

/**
 * @brief Cleanup memory test environment
 * 
 * Cleans up all allocated resources and resets the
 * test environment.
 */
void cleanup_memory_test_environment(void)
{
    printf("\n=== Cleaning Up Memory Test Environment ===\n");
    
    // Cleanup CSB/CSD structures
    cleanup_test_csb_csd();
    
    // Free allocated memory
    if (test_var_pool_data) {
        free(test_var_pool_data);
        test_var_pool_data = NULL;
    }
    
#ifdef LINUX_PLATFORM
    // Cleanup disk sector recycling
    cleanup_disk_sector_recycling();
    
    // Remove test directories
    int ret = system("rm -rf /tmp/imatrix_test_storage");
    (void)ret; // Explicitly ignore return value
    printf("Removed test storage directories\n");
#endif
    
    printf("=== Cleanup Complete ===\n");
}

/**
 * @brief Get test storage path
 * 
 * Returns the path to use for test storage operations.
 * This overrides the production storage path.
 * 
 * @return Pointer to test storage path string
 */
const char* get_test_storage_path(void)
{
#ifdef LINUX_PLATFORM
    return "/tmp/imatrix_test_storage/";
#else
    return "./test_storage/";
#endif
}

/**
 * @brief Initialize test storage
 * 
 * Simple wrapper for initializing test storage environment.
 * 
 * @return 0 on success, non-zero on failure
 */
int init_test_storage(void)
{
    return (initialize_memory_test_environment() == IMX_SUCCESS) ? 0 : -1;
}

/**
 * @brief Cleanup test storage
 * 
 * Simple wrapper for cleaning up test storage environment.
 */
void cleanup_test_storage(void)
{
    cleanup_memory_test_environment();
}