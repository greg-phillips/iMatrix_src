# Memory Manager Shutdown Test Suite

## Overview

The shutdown test suite provides comprehensive testing of the memory manager's shutdown functionality, including data flushing, progress tracking, cancellation, and recovery mechanisms.

## Test Files

### Core Test Files
- `test_shutdown.c` - Main test suite with all shutdown-related tests
- `test_shutdown_helpers.c/h` - Common utility functions for testing
- `test_shutdown_performance.c` - Performance benchmarking (planned)
- `test_shutdown_stress.c` - Stress testing (planned)

### Test Categories

#### 1. Basic Shutdown Tests
- **flush_all_empty** - Tests flushing when no data exists
- **flush_all_with_data** - Tests flushing with various amounts of data
- **flush_progress** - Verifies progress tracking from 0 to 101
- **ram_empty_check** - Tests RAM empty detection in various states

#### 2. Cancellation Tests
- **cancel_immediate** - Cancel before file operations start
- **cancel_during_op** - Cancel during active file write
- **cancel_timeout** - Test timeout mechanism in CANCELLING state
- **multiple_cancels** - Test repeated cancel/restart scenarios

#### 3. State Machine Tests
- **state_transitions** - Verify all state transitions work correctly
- **cancelling_state** - Test MEMORY_STATE_CANCELLING_FLUSH behavior
- **file_op_tracking** - Verify file operation state tracking

#### 4. Edge Case Tests
- **flush_full_disk** - Test behavior when disk is full
- **flush_corrupted** - Test handling of corrupted sectors
- **concurrent_ops** - Test shutdown during normal operations

#### 5. Integration Tests
- **power_cycle** - Simulate power on/off cycles
- **recovery_cancel** - Test system recovery after cancellation
- **data_integrity** - Verify no data loss during operations

## Building the Tests

From the memory_test directory:

```bash
mkdir -p build
cd build
cmake ..
make test_shutdown
```

## Running the Tests

### Run all shutdown tests:
```bash
./test_shutdown
```

### Run with verbose output:
```bash
./test_shutdown -v
```

### Using CMake targets:
```bash
make run_shutdown
```

## Test Output Format

Each test reports:
- **Test name and description**
- **Setup conditions**
- **Actions performed**
- **Expected results**
- **Actual results**
- **PASS/FAIL status**
- **Cleanup status**

Example output:
```
=== Test: flush_all_with_data ===
Description: Test flushing with various amounts of data
Setup: Creating 10 sensors with 50 samples each
Actions: Monitoring flush progress...
  Progress: 10%
  Progress: 25%
  Progress: 50%
  Progress: 75%
  Progress: 90%
Expected: All data flushed to disk
Actual: Flush completed with progress = 101
Result: PASS
```

## Test Coverage Matrix

| Functionality | Test Coverage | Notes |
|--------------|---------------|-------|
| flush_all_to_disk() | ✓ Complete | Tests empty and with data |
| get_flush_progress() | ✓ Complete | Verifies 0-100 then 101 |
| is_all_ram_empty() | ✓ Complete | Tests all states |
| cancel_memory_flush() | ✓ Complete | Multiple scenarios |
| CANCELLING_FLUSH state | ✓ Basic | Full testing requires internal access |
| File operation tracking | ✓ Basic | Enhanced with internal access |
| Disk full handling | ✓ Complete | Uses disk simulation |
| Power cycle recovery | ✓ Complete | Simulates ignition cycles |
| Data integrity | ✓ Complete | Verifies no data loss |

## Common Failure Modes

### 1. Timeout Failures
- **Symptom**: Progress monitoring times out
- **Cause**: State machine not advancing
- **Debug**: Check process_memory() is being called

### 2. RAM Not Empty
- **Symptom**: is_all_ram_empty() returns false after flush
- **Cause**: Data still in RAM sectors
- **Debug**: Check flush completion and sector chains

### 3. Progress Not Advancing
- **Symptom**: Progress stays at 0 or doesn't reach 101
- **Cause**: No sectors to flush or state machine stuck
- **Debug**: Verify data was added and state transitions

### 4. Cancellation Failures
- **Symptom**: System doesn't recover after cancel
- **Cause**: State not properly reset
- **Debug**: Check state machine transitions

## Debugging Tips

### Enable Verbose Output
Use `-v` flag to see detailed progress and state information.

### Check Test Storage
Test files are created in `/tmp/imatrix_test_storage/history/`

### Monitor State Transitions
The verbose output shows state machine transitions.

### File Operation Tracking
Look for file operation states in verbose output when debugging cancellation.

## Extending the Tests

### Adding New Test Cases

1. Add test function declaration in test_shutdown.c
2. Implement the test function following the pattern:
   ```c
   static bool test_new_feature(void)
   {
       print_test_header("new_feature", "Description");
       setup_test_environment();
       
       // Test implementation
       
       cleanup_test_environment();
       print_test_result(passed);
       return passed;
   }
   ```
3. Add to test_cases array

### Adding Helper Functions

Add new helpers to test_shutdown_helpers.c/h for reusable functionality.

### Performance Testing

Use the progress_monitor_t structure to track and analyze performance metrics.

## Integration with CI/CD

The test returns:
- 0 on success (all tests pass)
- 1 on failure (any test fails)

This makes it suitable for CI/CD pipelines.

## Known Limitations

1. **Internal State Access**: Some tests are limited without access to internal state machine variables
2. **File System Dependencies**: Tests require write access to /tmp
3. **Timing Sensitivity**: Some tests depend on timing and may need adjustment for different systems
4. **Disk Space**: Tests assume sufficient disk space in /tmp

## Future Enhancements

1. **Performance Benchmarks**: Add dedicated performance test suite
2. **Stress Testing**: Add long-running stress tests
3. **Fault Injection**: Add tests that inject failures
4. **Memory Leak Detection**: Integrate with valgrind
5. **Coverage Analysis**: Add code coverage reporting