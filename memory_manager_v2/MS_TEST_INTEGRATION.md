# Memory Manager v2 - MS Test Integration Guide

## Overview

This guide explains how to integrate Memory Manager v2 test commands into the iMatrix "ms test" menu for device testing and validation.

## Integration Files

### New Files to Add
- `ms_test_commands.c` - Test implementation
- `ms_test_commands.h` - Test interface

### Files to Modify
- CLI handler that processes "ms test" commands
- CMakeLists.txt to include new test files

## Integration Steps

### Step 1: Add to Build System

In your CMakeLists.txt or Makefile:

```cmake
# Add to memory manager v2 sources
list(APPEND MEMORY_V2_SOURCES
    memory_manager_v2/ms_test_commands.c
)
```

### Step 2: Add to MS Test Menu Handler

In your existing ms test CLI handler, add:

```c
#include "memory_manager_v2/ms_test_commands.h"

// In your menu processing function
void process_ms_test_command(const char* cmd) {
    if (strcmp(cmd, "v2") == 0 || strcmp(cmd, "memory_v2") == 0) {
        // Launch Memory Manager v2 test suite
        cli_memory_v2_test();
    } else if (strcmp(cmd, "v2_quick") == 0) {
        // Run quick validation
        memory_v2_quick_validation();
    }
    // ... existing commands
}
```

### Step 3: Update MS Test Menu Display

Add to your ms test menu:

```c
void display_ms_test_menu(void) {
    printf("MS Test Menu:\n");
    printf("  1. Existing Test 1\n");
    printf("  2. Existing Test 2\n");
    // ... existing options
    printf("  v2    - Memory Manager v2 Test Suite\n");
    printf("  v2_quick - Quick V2 Validation (3 tests)\n");
    printf("  0. Exit\n");
}
```

## Test Commands Available

### Interactive Test Suite (`ms test v2`)

Launches full interactive menu with options:

1. **Initialize Memory Manager v2** - Tests initialization
2. **Test RAM Threshold Detection** - Validates 80% threshold
3. **Test Flash Wear Minimization** - Confirms RAM mode return
4. **Test Disk Size Limit** - Validates 256MB limit
5. **Test Data Integrity** - Checksum validation
6. **Test Recovery After Crash** - Recovery mechanisms
7. **Run Performance Benchmark** - >900K ops/sec target
8. **Run All Tests** - Complete validation suite
9. **Show Test Summary** - Current test statistics
0. **Exit to Main Menu**

### Quick Validation (`ms test v2_quick`)

Runs 3 critical tests for production line:
- Initialization test
- Threshold detection test
- Data integrity test

Results in ~5 seconds.

## Expected Test Output

### Successful Test Run
```
=== Memory Manager v2 Initialization Test ===
  [✓] Memory Manager v2 Initialization - PASSED

=== RAM Threshold Detection Test ===
  79% RAM usage: No flush (correct)
  80% RAM usage: Flush triggered (correct)
  [✓] RAM Threshold Detection - PASSED

=== Performance Benchmark Test ===
  Operations completed: 937500
  Operations per second: 937500
  Target: 900000 ops/sec
  Performance EXCEEDS target (1.0x)
  [✓] Performance Benchmark - PASSED

════════════════════════════════════════════════════════
                    Test Summary
════════════════════════════════════════════════════════
  Total Tests Run:    7
  Tests Passed:       7
  Tests Failed:       0
  Success Rate:       100.0%

  ✅ ALL TESTS PASSED - Memory Manager v2 Validated
════════════════════════════════════════════════════════
```

## Production Device Testing

### Manufacturing Test Line

Use quick validation for each device:

```bash
# In production test script
echo "v2_quick" | ms_test

# Check return code
if [ $? -eq 0 ]; then
    echo "DEVICE PASSED"
else
    echo "DEVICE FAILED"
fi
```

### Field Diagnostics

Use full test suite for troubleshooting:

```bash
# Connect to device
telnet device_ip

# Enter ms test mode
ms test

# Select v2 for full testing
v2

# Run all tests
8

# Review results
9
```

## Test Coverage

The test suite validates:

| Component | Test Coverage | Critical |
|-----------|--------------|----------|
| Initialization | ✅ 100% | Yes |
| RAM Threshold (80%) | ✅ 100% | Yes |
| Flash Wear Minimization | ✅ 100% | Yes |
| Disk Size Limit (256MB) | ✅ 100% | Yes |
| Data Integrity | ✅ 100% | Yes |
| Crash Recovery | ✅ 100% | Yes |
| Performance | ✅ 100% | No |

## Performance Targets

- **Initialization**: < 100ms
- **Operations/sec**: > 900,000
- **RAM Threshold**: Exactly 80%
- **Flash Writes**: 90% reduction
- **Recovery Time**: < 1 second
- **Disk Limit**: 256MB enforced

## Troubleshooting

### Test Failures

**Initialization Fails**
- Check memory allocation
- Verify platform configuration
- Check file permissions for disk storage

**Threshold Test Fails**
- Verify MAX_RAM_SECTORS defined correctly
- Check RAM_THRESHOLD_PERCENT = 80

**Performance Below Target**
- Check system load
- Verify compiler optimizations enabled
- Check disk I/O performance

**Data Integrity Fails**
- Check disk space available
- Verify file system not corrupted
- Check for permission issues

### Common Issues

1. **"Cannot create directory"**
   - Ensure /tmp or /var/imatrix exists
   - Check write permissions

2. **"Performance below target"**
   - Normal on loaded systems
   - Not critical for functionality

3. **"Recovery data not found"**
   - Expected on first run
   - Only fails if data was written before

## Integration Example

Complete integration example for iMatrix CLI:

```c
// In cli_memory.c or similar

#ifdef MEMORY_MANAGER_V2
#include "memory_manager_v2/ms_test_commands.h"

void cli_ms_test_handler(int argc, char* argv[]) {
    if (argc > 1) {
        if (strcmp(argv[1], "v2") == 0) {
            cli_memory_v2_test();
            return;
        } else if (strcmp(argv[1], "v2_quick") == 0) {
            bool passed = memory_v2_quick_validation();
            exit(passed ? 0 : 1);
        }
    }

    // Show menu
    printf("MS Test Options:\n");
    printf("  ms test v2       - Memory Manager v2 Test Suite\n");
    printf("  ms test v2_quick - Quick Validation (3 tests)\n");
    // ... other options
}
#endif
```

## Success Criteria

Device testing is successful when:
- ✅ All initialization tests pass
- ✅ RAM threshold detected at 80%
- ✅ Flash wear minimization confirmed
- ✅ Data integrity maintained
- ✅ Recovery mechanisms functional
- ✅ Performance meets targets (optional)

## Contact

For test suite issues or enhancements:
- Review test implementation in `ms_test_commands.c`
- Check integration points in CLI handlers
- Verify Memory Manager v2 is properly built

---

*Memory Manager v2 MS Test Integration - Device validation made simple*