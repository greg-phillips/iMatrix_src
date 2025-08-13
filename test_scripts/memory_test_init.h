/**
 * @file memory_test_init.h
 * @brief Memory test initialization header
 * 
 * This header defines the initialization functions for memory tests.
 * 
 * @author Greg Phillips
 * @date 2025-01-08
 * @copyright iMatrix Systems, Inc.
 */

#ifndef MEMORY_TEST_INIT_H_
#define MEMORY_TEST_INIT_H_

#include <stdint.h>
#include <stdbool.h>
#include "imatrix.h"

/******************************************************
 *                    Constants
 ******************************************************/

// Test storage path override
#ifdef LINUX_PLATFORM
#define TEST_STORAGE_PATH "/tmp/imatrix_test_storage/"
#else
#define TEST_STORAGE_PATH "./test_storage/"
#endif

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Initialize memory test environment
 * 
 * Main initialization function that sets up the complete
 * test environment for memory manager testing.
 * 
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t initialize_memory_test_environment(void);

/**
 * @brief Initialize memory test with external SRAM
 * 
 * Initializes the test environment with external SRAM
 * configuration for testing external memory features.
 * 
 * @param ext_sram_size Size of external SRAM in bytes
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t initialize_memory_test_with_ext_sram(uint32_t ext_sram_size);

/**
 * @brief Cleanup memory test environment
 * 
 * Cleans up all allocated resources and resets the
 * test environment.
 */
void cleanup_memory_test_environment(void);

/**
 * @brief Get current test iteration for debugging
 * 
 * Returns the current iteration number being executed.
 * This is useful for debugging and tracking issues.
 * 
 * @return Current iteration number (1-based)
 */
int get_current_test_iteration(void);

/**
 * @brief Get test storage path
 * 
 * Returns the path to use for test storage operations.
 * This overrides the production storage path.
 * 
 * @return Pointer to test storage path string
 */
const char* get_test_storage_path(void);

/**
 * @brief Initialize test storage
 * 
 * Simple wrapper for initializing test storage environment.
 * Calls initialize_memory_test_environment internally.
 * 
 * @return 0 on success, non-zero on failure
 */
int init_test_storage(void);

/**
 * @brief Cleanup test storage
 * 
 * Simple wrapper for cleaning up test storage environment.
 * Calls cleanup_memory_test_environment internally.
 */
void cleanup_test_storage(void);

#endif /* MEMORY_TEST_INIT_H_ */