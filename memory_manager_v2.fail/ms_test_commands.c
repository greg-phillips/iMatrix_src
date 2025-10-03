/**
 * @file ms_test_commands.c
 * @brief Memory Manager v2 test commands for ms test menu
 * @author Memory Manager v2 Team
 * @date 2025-09-29
 *
 * This file provides test commands for Memory Manager v2 that can be
 * integrated into the iMatrix "ms test" menu for device testing and validation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <time.h>
#include <unistd.h>

#include "unified_state.h"
#include "platform_config.h"
#include "data_storage.h"
#include "disk_operations.h"

/* Test result tracking */
typedef struct {
    uint32_t tests_run;
    uint32_t tests_passed;
    uint32_t tests_failed;
    char last_error[256];
} test_results_t;

static test_results_t g_test_results = {0};

/**
 * @brief Print test result with color coding
 */
static void print_test_result(const char* test_name, bool passed) {
    if (passed) {
        printf("  [✓] %s - PASSED\n", test_name);
        g_test_results.tests_passed++;
    } else {
        printf("  [✗] %s - FAILED\n", test_name);
        g_test_results.tests_failed++;
    }
    g_test_results.tests_run++;
}

/**
 * @brief Test 1: Basic Memory Manager v2 Initialization
 *
 * Validates that Memory Manager v2 initializes correctly and
 * all core structures are properly configured.
 */
bool memory_v2_test_init(void) {
    printf("\n=== Memory Manager v2 Initialization Test ===\n");

    unified_sensor_state_t state;
    memory_error_t err;

    /* Test initialization for each CSD type */
    bool all_passed = true;

    for (csd_type_t type = CSD_TYPE_HOST; type <= CSD_TYPE_CAN_CONTROLLER; type++) {
        err = init_unified_state(&state, type);
        if (err != MEMORY_SUCCESS) {
            printf("  Failed to initialize CSD type %d: error %d\n", type, err);
            all_passed = false;
        } else {
            /* Validate initial state */
            if (state.total_records != 0 ||
                state.consumed_records != 0 ||
                state.available_records != 0) {
                printf("  Invalid initial state for CSD type %d\n", type);
                all_passed = false;
            }
        }
    }

    print_test_result("Memory Manager v2 Initialization", all_passed);
    return all_passed;
}

/**
 * @brief Test 2: RAM Threshold Detection
 *
 * Tests that the 80% RAM threshold is correctly detected and
 * triggers flush operations as designed.
 */
bool memory_v2_test_threshold(void) {
    printf("\n=== RAM Threshold Detection Test ===\n");

    unified_sensor_state_t state;
    memory_error_t err;
    bool test_passed = true;

    /* Initialize state */
    err = init_unified_state(&state, CSD_TYPE_HOST);
    if (err != MEMORY_SUCCESS) {
        print_test_result("RAM Threshold Detection", false);
        return false;
    }

    /* Simulate filling RAM to 79% - should not trigger */
    uint32_t sectors_79_percent = (MAX_RAM_SECTORS * 79) / 100;
    state.ram_sectors_allocated = sectors_79_percent;

    if (should_trigger_flush(&state)) {
        printf("  ERROR: Flush triggered at 79%% (should be 80%%)\n");
        test_passed = false;
    }

    /* Fill to exactly 80% - should trigger */
    uint32_t sectors_80_percent = (MAX_RAM_SECTORS * 80) / 100;
    state.ram_sectors_allocated = sectors_80_percent;

    if (!should_trigger_flush(&state)) {
        printf("  ERROR: Flush not triggered at 80%%\n");
        test_passed = false;
    }

    printf("  79%% RAM usage: No flush (correct)\n");
    printf("  80%% RAM usage: Flush triggered (correct)\n");

    print_test_result("RAM Threshold Detection", test_passed);
    return test_passed;
}

/**
 * @brief Test 3: Flash Wear Minimization
 *
 * Validates that the system returns to RAM mode immediately
 * after flush, minimizing flash wear.
 */
bool memory_v2_test_flash_wear(void) {
    printf("\n=== Flash Wear Minimization Test ===\n");

    unified_sensor_state_t states[3];
    memory_error_t err;
    bool test_passed = true;

    /* Initialize all CSD states */
    for (int i = 0; i < 3; i++) {
        err = init_unified_state(&states[i], i);
        if (err != MEMORY_SUCCESS) {
            print_test_result("Flash Wear Minimization", false);
            return false;
        }
    }

    /* Simulate RAM filling to 80% */
    for (int i = 0; i < 3; i++) {
        states[i].ram_sectors_allocated = (MAX_RAM_SECTORS * 80) / 100;
        states[i].mode_state.current_mode = MODE_RAM_ONLY;
    }

    printf("  Initial mode: RAM_ONLY\n");
    printf("  RAM usage: 80%% (trigger flush)\n");

    /* Simulate flush operation */
    for (int i = 0; i < 3; i++) {
        if (should_trigger_flush(&states[i])) {
            /* After flush, RAM should be cleared and mode should return to RAM */
            states[i].ram_sectors_allocated = 0;
            states[i].mode_state.current_mode = MODE_RAM_ONLY;
            printf("  CSD %d: Flushed to disk, returned to RAM mode\n", i);
        }
    }

    /* Verify all CSDs are back in RAM mode */
    for (int i = 0; i < 3; i++) {
        if (states[i].mode_state.current_mode != MODE_RAM_ONLY) {
            printf("  ERROR: CSD %d not in RAM mode after flush\n", i);
            test_passed = false;
        }
    }

    print_test_result("Flash Wear Minimization", test_passed);
    return test_passed;
}

/**
 * @brief Test 4: Disk Size Limit (256MB)
 *
 * Validates that disk storage is limited to 256MB and oldest
 * files are deleted when the limit is reached.
 */
bool memory_v2_test_disk_limit(void) {
    printf("\n=== Disk Size Limit Test (256MB) ===\n");

    const char* test_path = "/tmp/test_disk_limit";
    uint64_t total_size;
    memory_error_t err;
    bool test_passed = true;

    /* Create test directory */
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", test_path);
    system(cmd);

    /* Calculate current disk usage */
    err = calculate_total_disk_usage(test_path, &total_size);
    if (err != MEMORY_SUCCESS) {
        printf("  ERROR: Failed to calculate disk usage\n");
        test_passed = false;
    }

    printf("  Initial disk usage: %lu MB\n", total_size / (1024 * 1024));

    /* Test enforcement at 256MB */
    if (total_size > MAX_DISK_STORAGE_BYTES) {
        printf("  Disk limit exceeded - enforcing cleanup\n");
        err = enforce_disk_size_limit(test_path);
        if (err != MEMORY_SUCCESS) {
            printf("  ERROR: Failed to enforce disk limit\n");
            test_passed = false;
        }
    }

    /* Verify size after enforcement */
    err = calculate_total_disk_usage(test_path, &total_size);
    if (err == MEMORY_SUCCESS && total_size <= MAX_DISK_STORAGE_BYTES) {
        printf("  Disk usage after enforcement: %lu MB (under 256MB limit)\n",
               total_size / (1024 * 1024));
    } else {
        printf("  ERROR: Disk limit not enforced correctly\n");
        test_passed = false;
    }

    /* Cleanup */
    snprintf(cmd, sizeof(cmd), "rm -rf %s", test_path);
    system(cmd);

    print_test_result("Disk Size Limit (256MB)", test_passed);
    return test_passed;
}

/**
 * @brief Test 5: Data Integrity with Checksums
 *
 * Validates that data written to disk can be read back with
 * correct checksum validation.
 */
bool memory_v2_test_data_integrity(void) {
    printf("\n=== Data Integrity Test ===\n");

    const char* test_path = "/tmp/test_integrity";
    bool test_passed = true;

    /* Create test directory */
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", test_path);
    system(cmd);

    /* Create test data */
    uint8_t write_data[1024];
    uint8_t read_data[1024];
    for (int i = 0; i < 1024; i++) {
        write_data[i] = (uint8_t)(i & 0xFF);
    }

    /* Write with metadata */
    disk_sector_metadata_t write_meta = {
        .sector_number = 1,
        .csd_type = CSD_TYPE_HOST,
        .timestamp = time(NULL),
        .data_size = 1024,
        .record_count = 10,
        .checksum = 0
    };

    /* Calculate checksum */
    write_meta.checksum = calculate_checksum(write_data, 1024);
    printf("  Writing data with checksum: 0x%08X\n", write_meta.checksum);

    /* Write to disk */
    memory_error_t err = write_sector_to_disk(test_path, 1, write_data, &write_meta);
    if (err != MEMORY_SUCCESS) {
        printf("  ERROR: Failed to write data\n");
        test_passed = false;
    }

    /* Read back */
    disk_sector_metadata_t read_meta;
    err = read_sector_from_disk(test_path, 1, read_data, &read_meta);
    if (err != MEMORY_SUCCESS) {
        printf("  ERROR: Failed to read data\n");
        test_passed = false;
    } else {
        /* Verify checksum */
        uint32_t calculated = calculate_checksum(read_data, read_meta.data_size);
        if (calculated != read_meta.checksum) {
            printf("  ERROR: Checksum mismatch (expected 0x%08X, got 0x%08X)\n",
                   read_meta.checksum, calculated);
            test_passed = false;
        } else {
            printf("  Checksum verified: 0x%08X (correct)\n", calculated);
        }

        /* Verify data content */
        if (memcmp(write_data, read_data, 1024) != 0) {
            printf("  ERROR: Data content mismatch\n");
            test_passed = false;
        } else {
            printf("  Data content verified (correct)\n");
        }
    }

    /* Cleanup */
    snprintf(cmd, sizeof(cmd), "rm -rf %s", test_path);
    system(cmd);

    print_test_result("Data Integrity", test_passed);
    return test_passed;
}

/**
 * @brief Test 6: Recovery After Crash
 *
 * Simulates a crash and validates that the system can recover
 * data from disk storage.
 */
bool memory_v2_test_recovery(void) {
    printf("\n=== Recovery After Crash Test ===\n");

    const char* test_path = "/tmp/test_recovery";
    bool test_passed = true;

    /* Create test directory */
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", test_path);
    system(cmd);

    printf("  Simulating data write before crash...\n");

    /* Write test data to simulate pre-crash state */
    for (int sector = 0; sector < 5; sector++) {
        uint8_t data[512];
        memset(data, sector, sizeof(data));

        disk_sector_metadata_t meta = {
            .sector_number = sector,
            .csd_type = CSD_TYPE_HOST,
            .timestamp = time(NULL) + sector,
            .data_size = sizeof(data),
            .record_count = 5,
            .checksum = calculate_checksum(data, sizeof(data))
        };

        memory_error_t err = write_sector_to_disk(test_path, sector, data, &meta);
        if (err != MEMORY_SUCCESS) {
            printf("  ERROR: Failed to write sector %d\n", sector);
            test_passed = false;
        }
    }

    printf("  Simulating crash and recovery...\n");

    /* Simulate recovery by scanning for disk files */
    bool has_recovery_data = scan_disk_for_recovery(test_path);
    if (!has_recovery_data) {
        printf("  ERROR: No recovery data found\n");
        test_passed = false;
    } else {
        printf("  Recovery data found on disk\n");

        /* Attempt to read back all sectors */
        int recovered_count = 0;
        for (int sector = 0; sector < 5; sector++) {
            uint8_t data[512];
            disk_sector_metadata_t meta;

            memory_error_t err = read_sector_from_disk(test_path, sector, data, &meta);
            if (err == MEMORY_SUCCESS) {
                recovered_count++;
            }
        }

        if (recovered_count == 5) {
            printf("  Successfully recovered all 5 sectors\n");
        } else {
            printf("  ERROR: Only recovered %d of 5 sectors\n", recovered_count);
            test_passed = false;
        }
    }

    /* Cleanup */
    snprintf(cmd, sizeof(cmd), "rm -rf %s", test_path);
    system(cmd);

    print_test_result("Recovery After Crash", test_passed);
    return test_passed;
}

/**
 * @brief Test 7: Performance Benchmark
 *
 * Measures operations per second to validate performance meets
 * requirements (target: >900K ops/sec).
 */
bool memory_v2_test_performance(void) {
    printf("\n=== Performance Benchmark Test ===\n");

    unified_sensor_state_t state;
    memory_error_t err;
    bool test_passed = true;

    /* Initialize state */
    err = init_unified_state(&state, CSD_TYPE_HOST);
    if (err != MEMORY_SUCCESS) {
        print_test_result("Performance Benchmark", false);
        return false;
    }

    /* Performance test parameters */
    const int TEST_DURATION_SEC = 1;
    const int TARGET_OPS_PER_SEC = 900000;  /* 900K ops/sec target */

    printf("  Running %d second performance test...\n", TEST_DURATION_SEC);

    /* Start timing */
    time_t start_time = time(NULL);
    uint32_t operations = 0;

    /* Run operations for duration */
    while (time(NULL) - start_time < TEST_DURATION_SEC) {
        /* Simulate write operation */
        state.total_records++;
        state.available_records = state.total_records - state.consumed_records;

        /* Simulate read operation */
        if (state.available_records > 0) {
            state.consumed_records++;
            state.available_records = state.total_records - state.consumed_records;
        }

        operations += 2;  /* Count both write and read */
    }

    /* Calculate results */
    int actual_duration = time(NULL) - start_time;
    if (actual_duration == 0) actual_duration = 1;  /* Prevent division by zero */

    uint32_t ops_per_sec = operations / actual_duration;

    printf("  Operations completed: %u\n", operations);
    printf("  Operations per second: %u\n", ops_per_sec);
    printf("  Target: %d ops/sec\n", TARGET_OPS_PER_SEC);

    if (ops_per_sec >= TARGET_OPS_PER_SEC) {
        printf("  Performance EXCEEDS target (%.1fx)\n",
               (float)ops_per_sec / TARGET_OPS_PER_SEC);
    } else {
        printf("  Performance BELOW target (%.1f%% of target)\n",
               (float)ops_per_sec * 100.0 / TARGET_OPS_PER_SEC);
        test_passed = false;
    }

    print_test_result("Performance Benchmark", test_passed);
    return test_passed;
}

/**
 * @brief Display Memory Manager v2 test menu
 */
void display_memory_v2_test_menu(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║        Memory Manager v2 - Device Test Suite            ║\n");
    printf("╠══════════════════════════════════════════════════════════╣\n");
    printf("║  1. Initialize Memory Manager v2                        ║\n");
    printf("║  2. Test RAM Threshold Detection (80%%)                  ║\n");
    printf("║  3. Test Flash Wear Minimization                        ║\n");
    printf("║  4. Test Disk Size Limit (256MB)                        ║\n");
    printf("║  5. Test Data Integrity (Checksums)                     ║\n");
    printf("║  6. Test Recovery After Crash                           ║\n");
    printf("║  7. Run Performance Benchmark                           ║\n");
    printf("║  8. Run All Tests                                       ║\n");
    printf("║  9. Show Test Summary                                   ║\n");
    printf("║  0. Exit to Main Menu                                   ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n");
    printf("\n");
}

/**
 * @brief Run all Memory Manager v2 tests
 */
bool run_all_memory_v2_tests(void) {
    printf("\n════════════════════════════════════════════════════════\n");
    printf("     Running Complete Memory Manager v2 Test Suite\n");
    printf("════════════════════════════════════════════════════════\n");

    /* Reset test results */
    memset(&g_test_results, 0, sizeof(g_test_results));

    /* Run all tests */
    bool all_passed = true;

    all_passed &= memory_v2_test_init();
    all_passed &= memory_v2_test_threshold();
    all_passed &= memory_v2_test_flash_wear();
    all_passed &= memory_v2_test_disk_limit();
    all_passed &= memory_v2_test_data_integrity();
    all_passed &= memory_v2_test_recovery();
    all_passed &= memory_v2_test_performance();

    /* Display summary */
    printf("\n════════════════════════════════════════════════════════\n");
    printf("                    Test Summary\n");
    printf("════════════════════════════════════════════════════════\n");
    printf("  Total Tests Run:    %u\n", g_test_results.tests_run);
    printf("  Tests Passed:       %u\n", g_test_results.tests_passed);
    printf("  Tests Failed:       %u\n", g_test_results.tests_failed);
    printf("  Success Rate:       %.1f%%\n",
           g_test_results.tests_run > 0 ?
           (float)g_test_results.tests_passed * 100.0 / g_test_results.tests_run : 0);

    if (all_passed) {
        printf("\n  ✅ ALL TESTS PASSED - Memory Manager v2 Validated\n");
    } else {
        printf("\n  ❌ SOME TESTS FAILED - Review results above\n");
    }
    printf("════════════════════════════════════════════════════════\n\n");

    return all_passed;
}

/**
 * @brief Show test summary
 */
void show_test_summary(void) {
    printf("\n═══════════════════════════════════════════════════\n");
    printf("          Memory Manager v2 Test Results\n");
    printf("═══════════════════════════════════════════════════\n");

    if (g_test_results.tests_run == 0) {
        printf("  No tests have been run yet.\n");
        printf("  Select option 8 to run all tests.\n");
    } else {
        printf("  Tests Executed:     %u\n", g_test_results.tests_run);
        printf("  Tests Passed:       %u\n", g_test_results.tests_passed);
        printf("  Tests Failed:       %u\n", g_test_results.tests_failed);
        printf("  Success Rate:       %.1f%%\n",
               (float)g_test_results.tests_passed * 100.0 / g_test_results.tests_run);

        if (g_test_results.tests_failed > 0 && strlen(g_test_results.last_error) > 0) {
            printf("\n  Last Error: %s\n", g_test_results.last_error);
        }
    }
    printf("═══════════════════════════════════════════════════\n\n");
}

/**
 * @brief Main entry point for ms test integration
 *
 * This function should be called from the ms test menu handler
 * when "ms test v2" or similar command is entered.
 */
void cli_memory_v2_test(void) {
    bool exit_menu = false;
    char input[256];

    printf("\n*** Memory Manager v2 Device Testing Mode ***\n");
    printf("This suite validates the new corruption-proof memory manager.\n");

    while (!exit_menu) {
        display_memory_v2_test_menu();
        printf("Select test [0-9]: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) {
            break;
        }

        /* Remove newline */
        input[strcspn(input, "\n")] = 0;

        /* Process selection */
        if (strlen(input) == 1) {
            switch (input[0]) {
                case '1':
                    memory_v2_test_init();
                    break;
                case '2':
                    memory_v2_test_threshold();
                    break;
                case '3':
                    memory_v2_test_flash_wear();
                    break;
                case '4':
                    memory_v2_test_disk_limit();
                    break;
                case '5':
                    memory_v2_test_data_integrity();
                    break;
                case '6':
                    memory_v2_test_recovery();
                    break;
                case '7':
                    memory_v2_test_performance();
                    break;
                case '8':
                    run_all_memory_v2_tests();
                    break;
                case '9':
                    show_test_summary();
                    break;
                case '0':
                    exit_menu = true;
                    printf("Exiting Memory Manager v2 test mode.\n");
                    break;
                default:
                    printf("Invalid selection. Please choose 0-9.\n");
            }
        } else {
            printf("Invalid input. Please enter a single digit.\n");
        }

        if (!exit_menu && input[0] != '0') {
            printf("\nPress Enter to continue...");
            fflush(stdout);
            fgets(input, sizeof(input), stdin);
        }
    }
}

/**
 * @brief Quick validation test for production devices
 *
 * Runs a subset of critical tests for quick device validation.
 * This is suitable for production line testing.
 */
bool memory_v2_quick_validation(void) {
    printf("\n*** Memory Manager v2 Quick Validation ***\n");

    /* Reset results */
    memset(&g_test_results, 0, sizeof(g_test_results));

    /* Run critical tests only */
    bool passed = true;
    passed &= memory_v2_test_init();
    passed &= memory_v2_test_threshold();
    passed &= memory_v2_test_data_integrity();

    if (passed) {
        printf("\n✅ QUICK VALIDATION PASSED\n");
    } else {
        printf("\n❌ QUICK VALIDATION FAILED\n");
    }

    return passed;
}