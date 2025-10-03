/**
 * @file ms_test_commands.h
 * @brief Memory Manager v2 test commands header for ms test integration
 * @author Memory Manager v2 Team
 * @date 2025-09-29
 */

#ifndef MS_TEST_COMMANDS_H
#define MS_TEST_COMMANDS_H

#include <stdbool.h>

/**
 * @brief Main entry point for Memory Manager v2 testing
 *
 * This function should be integrated into the ms test menu.
 * It provides an interactive menu for device testing and validation.
 *
 * Usage in ms test menu:
 *   When user selects "v2" or "memory v2" option
 */
void cli_memory_v2_test(void);

/**
 * @brief Quick validation test for production devices
 *
 * Runs a subset of critical tests for quick device validation.
 * Suitable for production line testing or field diagnostics.
 *
 * @return true if all critical tests pass, false otherwise
 */
bool memory_v2_quick_validation(void);

/**
 * @brief Individual test functions (for direct access if needed)
 */
bool memory_v2_test_init(void);
bool memory_v2_test_threshold(void);
bool memory_v2_test_flash_wear(void);
bool memory_v2_test_disk_limit(void);
bool memory_v2_test_data_integrity(void);
bool memory_v2_test_recovery(void);
bool memory_v2_test_performance(void);

/**
 * @brief Run complete test suite
 *
 * Executes all Memory Manager v2 tests in sequence and
 * provides a comprehensive report.
 *
 * @return true if all tests pass, false if any test fails
 */
bool run_all_memory_v2_tests(void);

/**
 * @brief Display test results summary
 *
 * Shows current test statistics including pass/fail counts
 * and success rate.
 */
void show_test_summary(void);

/**
 * @brief Display the interactive test menu
 *
 * Shows available test options for user selection.
 */
void display_memory_v2_test_menu(void);

#endif /* MS_TEST_COMMANDS_H */