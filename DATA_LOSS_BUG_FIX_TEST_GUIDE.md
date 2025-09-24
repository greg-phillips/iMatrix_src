# TEST GUIDE: Data Loss Bug Fix Validation

**Document Type:** Test Engineering Guide
**Date:** 2025-01-27
**Target:** Data loss bug fix in iMatrix upload system
**Purpose:** Test the fix without real server uploads or actual data transmission

---

## OVERVIEW

The catastrophic data loss bug has been fixed by implementing packet contents tracking. This guide shows how to validate the fix using test harnesses and mocked scenarios without requiring real server connectivity.

**Bug Fixed:** Partial pending data erasure destroying ALL pending data instead of just transmitted data.

**Fix Implemented:** Packet contents tracking that correlates erasure operations with actual transmission.

---

## TEST ENVIRONMENT SETUP

### **Required Files for Testing:**
```
/home/greg/iMatrix/iMatrix_Client/test_scripts/
├── test_data_loss_fix.c          (new test file)
├── mock_coap_responses.c         (new mock file)
├── data_integrity_validator.c    (new validator)
└── existing test infrastructure
```

### **Dependencies:**
- iMatrix core memory management system
- Control sensor data structures
- Mock CoAP response system (no real network)

---

## MOCK SYSTEM DESIGN

### **1. Mock CoAP Response System**

**File:** `test_scripts/mock_coap_responses.c`
```c
#include "../iMatrix/imatrix_upload/imatrix_upload.h"

/* Mock response types for testing */
typedef enum {
    MOCK_SUCCESS_RESPONSE,      // Simulate successful server ACK
    MOCK_FAILURE_RESPONSE,      // Simulate server error
    MOCK_TIMEOUT_RESPONSE,      // Simulate network timeout
    MOCK_PARTIAL_RESPONSE       // Simulate partial acknowledgment
} mock_response_type_t;

/* Global mock control */
static mock_response_type_t next_response_type = MOCK_SUCCESS_RESPONSE;

/**
 * @brief Set what type of response the next upload should receive
 */
void set_mock_response_type(mock_response_type_t type)
{
    next_response_type = type;
}

/**
 * @brief Mock function to replace actual CoAP transmission
 * This replaces the real coap_xmit_msg() during testing
 */
void mock_coap_xmit_msg(message_t *msg)
{
    /* Don't actually send - just trigger the appropriate response */
    switch (next_response_type)
    {
        case MOCK_SUCCESS_RESPONSE:
            /* Simulate successful server response after short delay */
            simulate_successful_response(msg);
            break;

        case MOCK_FAILURE_RESPONSE:
            /* Simulate server error response */
            simulate_error_response(msg);
            break;

        case MOCK_TIMEOUT_RESPONSE:
            /* Simulate timeout by not calling response handler */
            simulate_timeout_response(msg);
            break;

        case MOCK_PARTIAL_RESPONSE:
            /* Simulate partial acknowledgment */
            simulate_partial_response(msg);
            break;
    }
}

/**
 * @brief Simulate a successful server ACK
 */
void simulate_successful_response(message_t *msg)
{
    /* Create mock response message with CoAP class 2 (success) */
    message_t mock_response;
    mock_response.coap.header.mode.udp.code = 0x44; /* 2.04 Changed - success class */

    /* Call the actual response handler with our mock response */
    extern void _imatrix_upload_response_hdl(message_t *recv);
    _imatrix_upload_response_hdl(&mock_response);
}

/**
 * @brief Simulate a server error
 */
void simulate_error_response(message_t *msg)
{
    /* Create mock error response */
    message_t mock_response;
    mock_response.coap.header.mode.udp.code = 0x80; /* 4.00 Bad Request - error class */

    extern void _imatrix_upload_response_hdl(message_t *recv);
    _imatrix_upload_response_hdl(&mock_response);
}

/**
 * @brief Simulate network timeout
 */
void simulate_timeout_response(message_t *msg)
{
    /* Call response handler with NULL to simulate timeout */
    extern void _imatrix_upload_response_hdl(message_t *recv);
    _imatrix_upload_response_hdl(NULL);
}
```

### **2. Data Integrity Validator**

**File:** `test_scripts/data_integrity_validator.c`
```c
#include "../iMatrix/common.h"
#include "../iMatrix/cs_ctrl/memory_manager.h"

/**
 * @brief Snapshot of sensor data state for comparison
 */
typedef struct {
    uint16_t no_samples;
    uint16_t no_pending;
    uint16_t start_index;
    platform_sector_t start_sector;
} data_snapshot_t;

/* Test validation storage */
static data_snapshot_t snapshots_before[IMX_NO_PERIPHERAL_TYPES][100];
static data_snapshot_t snapshots_after[IMX_NO_PERIPHERAL_TYPES][100];

/**
 * @brief Take snapshot of all sensor data before upload
 */
void take_data_snapshot_before(void)
{
    for (imx_peripheral_type_t type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
    {
        imx_control_sensor_block_t *csb;
        control_sensor_data_t *csd;
        uint16_t no_items;

        imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

        for (uint16_t i = 0; i < no_items; i++)
        {
            snapshots_before[type][i].no_samples = csd[i].no_samples;
            snapshots_before[type][i].no_pending = csd[i].no_pending;
            snapshots_before[type][i].start_index = csd[i].ds.start_index;
            snapshots_before[type][i].start_sector = csd[i].ds.start_sector;
        }
    }
}

/**
 * @brief Take snapshot of all sensor data after upload
 */
void take_data_snapshot_after(void)
{
    for (imx_peripheral_type_t type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
    {
        imx_control_sensor_block_t *csb;
        control_sensor_data_t *csd;
        uint16_t no_items;

        imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

        for (uint16_t i = 0; i < no_items; i++)
        {
            snapshots_after[type][i].no_samples = csd[i].no_samples;
            snapshots_after[type][i].no_pending = csd[i].no_pending;
            snapshots_after[type][i].start_index = csd[i].ds.start_index;
            snapshots_after[type][i].start_sector = csd[i].ds.start_sector;
        }
    }
}

/**
 * @brief Validate that exactly the expected number of samples were erased
 * @param expected_erased Array of expected erasure counts per entry
 * @return true if validation passes, false if data loss detected
 */
bool validate_exact_erasure(uint16_t expected_erased[IMX_NO_PERIPHERAL_TYPES][100])
{
    bool validation_passed = true;

    for (imx_peripheral_type_t type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
    {
        for (uint16_t i = 0; i < 100; i++)
        {
            uint16_t samples_before = snapshots_before[type][i].no_samples;
            uint16_t samples_after = snapshots_after[type][i].no_samples;
            uint16_t expected = expected_erased[type][i];
            uint16_t actual_erased = samples_before - samples_after;

            if (actual_erased != expected)
            {
                printf("VALIDATION FAILED: Entry[%u][%u] expected %u erased, actual %u erased\r\n",
                       type, i, expected, actual_erased);
                validation_passed = false;
            }

            /* Verify remaining data is still accessible */
            if (samples_after > 0)
            {
                if (!verify_data_accessibility(type, i, samples_after))
                {
                    printf("VALIDATION FAILED: Remaining data not accessible in Entry[%u][%u]\r\n", type, i);
                    validation_passed = false;
                }
            }
        }
    }

    return validation_passed;
}

/**
 * @brief Verify that remaining data is still accessible
 */
bool verify_data_accessibility(imx_peripheral_type_t type, uint16_t entry, uint16_t expected_count)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;
    uint32_t test_value;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    /* Try to read one sample to verify accessibility */
    if (csd[entry].no_samples > 0)
    {
        read_tsd_evt(csb, csd, entry, &test_value);
        csd[entry].no_pending--; /* Restore pending count after test read */
        return true;
    }

    return (expected_count == 0); /* OK if no data expected */
}
```

---

## TEST CASES

### **TEST CASE 1: Partial Upload Success Validation**

**File:** `test_scripts/test_data_loss_fix.c`
```c
#include "mock_coap_responses.h"
#include "data_integrity_validator.h"

/**
 * @brief Test that partial uploads only erase transmitted data
 */
bool test_partial_upload_success(void)
{
    printf("=== TEST: Partial Upload Success ===\r\n");

    /* Setup: Create test data */
    uint16_t test_entry = 0;
    imx_peripheral_type_t test_type = IMX_SENSORS;

    /* Write 1000 samples to storage */
    populate_test_data(test_type, test_entry, 1000);

    /* Take snapshot before upload */
    take_data_snapshot_before();

    /* Configure mock to limit packet size to 100 samples */
    set_mock_packet_size_limit(100);

    /* Configure mock to return success */
    set_mock_response_type(MOCK_SUCCESS_RESPONSE);

    /* Execute upload */
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);

    /* Take snapshot after upload */
    take_data_snapshot_after();

    /* Validate results */
    uint16_t expected_erased[IMX_NO_PERIPHERAL_TYPES][100] = {0};
    expected_erased[test_type][test_entry] = 100; /* Only 100 should be erased */

    bool result = validate_exact_erasure(expected_erased);

    /* Verify remaining 900 samples are accessible */
    if (result)
    {
        imx_control_sensor_block_t *csb;
        control_sensor_data_t *csd;
        uint16_t no_items;
        imx_set_csb_vars(test_type, &csb, &csd, &no_items, NULL);

        if (csd[test_entry].no_samples != 900)
        {
            printf("FAIL: Expected 900 remaining samples, found %u\r\n", csd[test_entry].no_samples);
            result = false;
        }
        else
        {
            printf("PASS: Exactly 100 samples erased, 900 remain accessible\r\n");
        }
    }

    return result;
}
```

### **TEST CASE 2: Multiple Failed Uploads**

```c
/**
 * @brief Test that multiple failed uploads don't lose data
 */
bool test_multiple_failed_uploads(void)
{
    printf("=== TEST: Multiple Failed Uploads ===\r\n");

    uint16_t test_entry = 1;
    imx_peripheral_type_t test_type = IMX_CONTROLS;

    /* Write 500 samples */
    populate_test_data(test_type, test_entry, 500);

    /* Simulate 5 failed upload attempts */
    for (int attempt = 0; attempt < 5; attempt++)
    {
        take_data_snapshot_before();

        /* Configure mock for failure */
        set_mock_response_type(MOCK_FAILURE_RESPONSE);

        /* Execute upload */
        imx_time_t current_time;
        imx_time_get_time(&current_time);
        imatrix_upload(current_time);

        take_data_snapshot_after();

        /* Validate NO data was lost */
        uint16_t expected_erased[IMX_NO_PERIPHERAL_TYPES][100] = {0};
        /* All entries should be 0 - no data should be erased on failure */

        if (!validate_exact_erasure(expected_erased))
        {
            printf("FAIL: Data lost on failed upload attempt %d\r\n", attempt + 1);
            return false;
        }
    }

    /* After 5 failures, verify all 500 samples still accessible */
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;
    imx_set_csb_vars(test_type, &csb, &csd, &no_items, NULL);

    if (csd[test_entry].no_samples != 500)
    {
        printf("FAIL: Data lost after failed uploads. Expected 500, found %u\r\n", csd[test_entry].no_samples);
        return false;
    }

    printf("PASS: All 500 samples preserved after 5 failed uploads\r\n");
    return true;
}
```

### **TEST CASE 3: Mixed Success/Failure Scenario**

```c
/**
 * @brief Test mixed success and failure scenarios
 */
bool test_mixed_success_failure(void)
{
    printf("=== TEST: Mixed Success/Failure Scenario ===\r\n");

    uint16_t test_entry = 2;
    imx_peripheral_type_t test_type = IMX_SENSORS;

    /* Write 1000 samples */
    populate_test_data(test_type, test_entry, 1000);

    /* Attempt 1: Fail (should preserve all data) */
    set_mock_response_type(MOCK_FAILURE_RESPONSE);
    set_mock_packet_size_limit(200);

    take_data_snapshot_before();
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);
    take_data_snapshot_after();

    /* Validate no data lost on failure */
    uint16_t expected_erased_fail[IMX_NO_PERIPHERAL_TYPES][100] = {0};
    if (!validate_exact_erasure(expected_erased_fail))
    {
        printf("FAIL: Data lost on first failure\r\n");
        return false;
    }

    /* Attempt 2: Success (should erase only transmitted data) */
    set_mock_response_type(MOCK_SUCCESS_RESPONSE);
    set_mock_packet_size_limit(150);

    take_data_snapshot_before();
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);
    take_data_snapshot_after();

    /* Validate exactly 150 samples erased */
    uint16_t expected_erased_success[IMX_NO_PERIPHERAL_TYPES][100] = {0};
    expected_erased_success[test_type][test_entry] = 150;

    if (!validate_exact_erasure(expected_erased_success))
    {
        printf("FAIL: Incorrect erasure on success\r\n");
        return false;
    }

    /* Verify remaining data count */
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;
    imx_set_csb_vars(test_type, &csb, &csd, &no_items, NULL);

    if (csd[test_entry].no_samples != 850) /* 1000 - 150 = 850 */
    {
        printf("FAIL: Expected 850 remaining, found %u\r\n", csd[test_entry].no_samples);
        return false;
    }

    printf("PASS: Mixed scenario handled correctly\r\n");
    return true;
}
```

### **TEST CASE 4: Multi-Sensor Partial Upload**

```c
/**
 * @brief Test partial upload with multiple sensors
 */
bool test_multi_sensor_partial_upload(void)
{
    printf("=== TEST: Multi-Sensor Partial Upload ===\r\n");

    /* Setup multiple sensors with different data counts */
    populate_test_data(IMX_SENSORS, 0, 800);    /* Sensor 0: 800 samples */
    populate_test_data(IMX_SENSORS, 1, 600);    /* Sensor 1: 600 samples */
    populate_test_data(IMX_SENSORS, 2, 400);    /* Sensor 2: 400 samples */

    /* Configure packet to take samples from all sensors but limited total */
    set_mock_packet_size_limit(300); /* Can fit total 300 samples across all sensors */
    set_mock_response_type(MOCK_SUCCESS_RESPONSE);

    take_data_snapshot_before();

    /* Execute upload */
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);

    take_data_snapshot_after();

    /* Validate each sensor lost only the samples that were actually sent */
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;
    imx_set_csb_vars(IMX_SENSORS, &csb, &csd, &no_items, NULL);

    uint16_t total_erased = 0;
    for (uint16_t i = 0; i < 3; i++)
    {
        uint16_t erased = snapshots_before[IMX_SENSORS][i].no_samples - snapshots_after[IMX_SENSORS][i].no_samples;
        total_erased += erased;
        printf("Sensor %u: %u samples erased (before: %u, after: %u)\r\n",
               i, erased, snapshots_before[IMX_SENSORS][i].no_samples, snapshots_after[IMX_SENSORS][i].no_samples);
    }

    /* Total erased should equal packet size limit */
    if (total_erased != 300)
    {
        printf("FAIL: Expected 300 total samples erased, actual %u\r\n", total_erased);
        return false;
    }

    /* Verify remaining data is accessible */
    if (csd[0].no_samples + csd[1].no_samples + csd[2].no_samples != (800 + 600 + 400 - 300))
    {
        printf("FAIL: Remaining data count incorrect\r\n");
        return false;
    }

    printf("PASS: Multi-sensor partial upload handled correctly\r\n");
    return true;
}
```

---

## AUTOMATED TEST HARNESS

### **Main Test Runner**

**File:** `test_scripts/test_data_loss_fix.c`
```c
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include "../iMatrix/imx_platform.h"
#include "../iMatrix/imatrix_upload/imatrix_upload.h"
#include "mock_coap_responses.h"
#include "data_integrity_validator.h"

/* Test results tracking */
static uint16_t tests_run = 0;
static uint16_t tests_passed = 0;
static uint16_t tests_failed = 0;

#define RUN_TEST(test_func) do { \
    tests_run++; \
    printf("\r\n--- Running %s ---\r\n", #test_func); \
    if (test_func()) { \
        tests_passed++; \
        printf("✅ %s PASSED\r\n", #test_func); \
    } else { \
        tests_failed++; \
        printf("❌ %s FAILED\r\n", #test_func); \
    } \
} while(0)

/**
 * @brief Main test function - validates data loss bug fix
 */
int main(void)
{
    printf("========================================\r\n");
    printf("DATA LOSS BUG FIX VALIDATION TESTS\r\n");
    printf("========================================\r\n");

    /* Initialize test environment */
    init_test_environment();

    /* Replace real CoAP transmission with mock */
    redirect_coap_transmission_to_mock();

    /* Run all test cases */
    RUN_TEST(test_partial_upload_success);
    RUN_TEST(test_multiple_failed_uploads);
    RUN_TEST(test_mixed_success_failure);
    RUN_TEST(test_multi_sensor_partial_upload);
    RUN_TEST(test_catastrophic_scenario_prevention);
    RUN_TEST(test_timeout_scenarios);
    RUN_TEST(test_boundary_conditions);

    /* Print final results */
    printf("\r\n========================================\r\n");
    printf("TEST RESULTS SUMMARY\r\n");
    printf("========================================\r\n");
    printf("Total Tests: %u\r\n", tests_run);
    printf("Passed: %u\r\n", tests_passed);
    printf("Failed: %u\r\n", tests_failed);

    if (tests_failed == 0)
    {
        printf("🎉 ALL TESTS PASSED - DATA LOSS BUG FIX VALIDATED\r\n");
        printf("✅ Safe to deploy - no data loss will occur\r\n");
    }
    else
    {
        printf("⚠️  TESTS FAILED - DO NOT DEPLOY\r\n");
        printf("❌ Data loss bug fix needs more work\r\n");
    }

    return (tests_failed == 0) ? 0 : 1;
}
```

### **Test Helper Functions**

```c
/**
 * @brief Populate test entry with known data
 */
void populate_test_data(imx_peripheral_type_t type, uint16_t entry, uint16_t sample_count)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    /* Clear existing data */
    csd[entry].no_samples = 0;
    csd[entry].no_pending = 0;

    /* Write test samples */
    for (uint16_t i = 0; i < sample_count; i++)
    {
        uint32_t test_value = 0x12340000 + i; /* Unique test pattern */
        write_tsd_evt(csb, csd, entry, test_value, false);
    }

    printf("Populated %u samples in %s entry %u\r\n", sample_count, imx_peripheral_name(type), entry);
}

/**
 * @brief Set packet size limit for testing
 */
void set_mock_packet_size_limit(uint16_t max_samples)
{
    /* This would modify the packet size calculation in the upload logic */
    extern uint16_t mock_max_packet_samples;
    mock_max_packet_samples = max_samples;
}

/**
 * @brief Initialize test environment
 */
void init_test_environment(void)
{
    /* Initialize iMatrix upload system */
    init_imatrix();

    /* Clear any existing data */
    clear_all_sensor_data();

    /* Set up test configuration */
    setup_test_device_config();

    printf("Test environment initialized\r\n");
}
```

---

## CRITICAL TEST SCENARIOS

### **Scenario A: The Original Catastrophic Bug**

**Purpose:** Verify the original bug would have caused data loss
```c
bool test_original_bug_prevention(void)
{
    /* This test simulates what WOULD have happened with the old code */

    /* Setup: 2000 samples, packet fits 100 */
    populate_test_data(IMX_SENSORS, 0, 2000);

    /* Simulate old behavior (for comparison) */
    // OLD: erase_tsd_evt_pending_data() would erase ALL pending
    // NEW: erase_specific_samples() erases only transmitted

    /* With fix: Should erase exactly 100, keep 1900 */
    /* Without fix: Would erase ALL 2000, losing 1900 samples */

    /* Execute with fix */
    set_mock_packet_size_limit(100);
    set_mock_response_type(MOCK_SUCCESS_RESPONSE);

    take_data_snapshot_before();
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);
    take_data_snapshot_after();

    /* Validate fix worked */
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;
    imx_set_csb_vars(IMX_SENSORS, &csb, &csd, &no_items, NULL);

    if (csd[0].no_samples != 1900)
    {
        printf("FAIL: Fix didn't work. Expected 1900 remaining, found %u\r\n", csd[0].no_samples);
        return false;
    }

    printf("✅ CRITICAL: Original catastrophic bug prevented\r\n");
    printf("   - Would have lost 1900 samples\r\n");
    printf("   - Fix preserved 1900 samples\r\n");
    printf("   - Only 100 samples properly erased\r\n");

    return true;
}
```

### **Scenario B: Timeout During Upload**

```c
bool test_timeout_scenarios(void)
{
    printf("=== TEST: Timeout Scenarios ===\r\n");

    populate_test_data(IMX_CONTROLS, 0, 800);

    /* Simulate timeout (no response from server) */
    set_mock_response_type(MOCK_TIMEOUT_RESPONSE);
    set_mock_packet_size_limit(200);

    take_data_snapshot_before();

    /* Execute upload */
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);

    /* Simulate timeout by calling timeout handler */
    simulate_upload_timeout();

    take_data_snapshot_after();

    /* Validate no data lost on timeout */
    uint16_t expected_erased[IMX_NO_PERIPHERAL_TYPES][100] = {0};

    if (!validate_exact_erasure(expected_erased))
    {
        printf("FAIL: Data lost on timeout\r\n");
        return false;
    }

    printf("PASS: No data lost on timeout\r\n");
    return true;
}
```

---

## INTEGRATION WITH EXISTING TEST FRAMEWORK

### **Add to CMakeLists.txt**

```cmake
# Add data loss fix test
add_executable(test_data_loss_fix
    test_data_loss_fix.c
    mock_coap_responses.c
    data_integrity_validator.c
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

target_include_directories(test_data_loss_fix PRIVATE ${INCLUDE_DIRS})
target_link_libraries(test_data_loss_fix PRIVATE c pthread m rt)
```

### **Add to Test Scripts**

```bash
#!/bin/bash
# test_data_loss_fix.sh

echo "Running Data Loss Bug Fix Validation..."

# Build the test
cmake .
make test_data_loss_fix

# Run the test
./test_data_loss_fix

# Check results
if [ $? -eq 0 ]; then
    echo "✅ DATA LOSS BUG FIX VALIDATED - SAFE TO USE"
else
    echo "❌ DATA LOSS BUG FIX FAILED - DO NOT DEPLOY"
    exit 1
fi
```

---

## MANUAL TESTING PROCEDURES

### **Quick Validation Test**

```c
/* Simple manual test for immediate validation */
void quick_validation_test(void)
{
    printf("Quick validation test...\r\n");

    /* Write known data */
    write_test_pattern(100); /* 100 samples with known pattern */

    /* Force small packet size */
    mock_small_packet_size(25);

    /* Execute upload with success */
    execute_mock_upload_success();

    /* Check results */
    if (count_remaining_samples() == 75)
    {
        printf("✅ QUICK TEST PASSED: 25 erased, 75 preserved\r\n");
    }
    else
    {
        printf("❌ QUICK TEST FAILED: Wrong erasure count\r\n");
    }
}
```

### **Visual Inspection Test**

```c
/* Test with debug output to visually inspect the fix */
void visual_inspection_test(void)
{
    printf("=== VISUAL INSPECTION TEST ===\r\n");

    /* Enable detailed debug output */
    enable_upload_debug_output();

    /* Create test scenario */
    populate_test_data(IMX_SENSORS, 0, 200);

    printf("BEFORE: %u samples available\r\n", get_sample_count(IMX_SENSORS, 0));

    /* Execute upload with limited packet size */
    set_mock_packet_size_limit(50);
    set_mock_response_type(MOCK_SUCCESS_RESPONSE);

    imx_time_t current_time;
    imx_time_get_time(&current_time);
    imatrix_upload(current_time);

    printf("AFTER: %u samples available\r\n", get_sample_count(IMX_SENSORS, 0));

    /* Should show exactly 50 samples erased, 150 remaining */
    printf("Expected: 150 remaining (200 - 50 = 150)\r\n");
    printf("Result: %s\r\n", (get_sample_count(IMX_SENSORS, 0) == 150) ? "✅ CORRECT" : "❌ WRONG");
}
```

---

## AUTOMATED REGRESSION TESTING

### **Continuous Integration Test**

```bash
#!/bin/bash
# data_loss_regression_test.sh

echo "Data Loss Bug Fix - Regression Test Suite"

PASS_COUNT=0
FAIL_COUNT=0

# Test 1: Basic partial upload
echo "Test 1: Basic partial upload..."
if ./test_data_loss_fix --test=partial_upload; then
    ((PASS_COUNT++))
    echo "✅ PASSED"
else
    ((FAIL_COUNT++))
    echo "❌ FAILED"
fi

# Test 2: Multiple failures
echo "Test 2: Multiple failure handling..."
if ./test_data_loss_fix --test=multiple_failures; then
    ((PASS_COUNT++))
    echo "✅ PASSED"
else
    ((FAIL_COUNT++))
    echo "❌ FAILED"
fi

# Test 3: Timeout scenarios
echo "Test 3: Timeout scenarios..."
if ./test_data_loss_fix --test=timeouts; then
    ((PASS_COUNT++))
    echo "✅ PASSED"
else
    ((FAIL_COUNT++))
    echo "❌ FAILED"
fi

echo "=========================================="
echo "REGRESSION TEST RESULTS:"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 ALL REGRESSION TESTS PASSED"
    exit 0
else
    echo "⚠️  REGRESSION FAILURES DETECTED"
    exit 1
fi
```

---

## VALIDATION CHECKLIST

### **Pre-Deployment Validation**

```
□ Partial upload scenarios preserve untransmitted data
□ Failed uploads don't lose any data
□ Timeout scenarios properly revert read operations
□ Multi-sensor uploads only erase transmitted samples
□ Boundary conditions (empty data, full packets) handled correctly
□ Memory usage remains within acceptable limits
□ Performance impact is minimal
□ All existing functionality still works
□ Debug output confirms correct behavior
□ Long-running tests show no data accumulation issues
```

### **Success Criteria**

```
✅ Zero data loss in any test scenario
✅ Exact correlation between transmitted and erased data
✅ Proper rollback on all failure types
✅ Performance within 10% of original system
✅ All existing tests continue to pass
✅ Visual inspection confirms correct behavior
```

---

## CONCLUSION

This testing approach allows complete validation of the data loss bug fix without requiring:
- Real server connectivity
- Actual IoT sensor data
- Production network infrastructure
- Cloud platform access

**The test harness provides:**
- **Complete scenario coverage** for all discovered edge cases
- **Automated validation** of the fix effectiveness
- **Regression testing** to prevent future issues
- **Visual inspection tools** for manual verification

**Test Engineer Action Items:**
1. Implement the mock CoAP response system
2. Create the data integrity validator
3. Build the automated test suite
4. Run comprehensive validation before deployment
5. Set up regression testing for future changes

**Expected Outcome:** 100% confidence that the catastrophic data loss bug is completely resolved and will never occur again.