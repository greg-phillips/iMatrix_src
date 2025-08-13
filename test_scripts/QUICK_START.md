# iMatrix Memory Test Quick Start Guide

## Overview

This directory contains test programs and scripts for validating the iMatrix Memory Manager and Tiered Storage System. The setup supports both basic memory manager testing and full tiered storage validation.

## Test Programs Available

### 1. simple_test ✅ (Always Available)
- **Purpose**: Basic memory manager functionality test
- **Dependencies**: Minimal (built-in stubs)
- **Features**: Sector allocation, read/write operations, secure functions, statistics
- **Runtime**: ~1 second

### 2. test_tiered_storage ⚠️ (Requires Full Dependencies)
- **Purpose**: Complete tiered storage system test
- **Dependencies**: Full iMatrix codebase
- **Features**: RAM-to-disk migration, power failure recovery, data integrity
- **Runtime**: ~30-60 seconds

### 3. test_tiered_storage_advanced ⚠️ (Requires Full Dependencies)
- **Purpose**: Configurable tiered storage testing
- **Dependencies**: Full iMatrix codebase
- **Features**: Multi-sensor testing, performance analysis, stress testing
- **Runtime**: Configurable (5 seconds to 10+ minutes)

## Setup Scripts

### Option 1: Simple Setup (Recommended for Basic Testing)
```bash
./test_setup_simple.sh
```
**Features:**
- ✅ No sudo required
- ✅ Uses temporary storage (/tmp)
- ✅ Builds and tests simple_test
- ✅ Quick validation
- ❌ No persistent storage testing

### Option 2: Full Setup (For Complete Testing)
```bash
./test_setup.sh
```
**Features:**
- ⚠️ May require sudo for /usr/qk/etc/sv/FC-1/history
- ✅ Creates proper storage directories
- ✅ Builds all available test programs
- ✅ Full environment validation
- ✅ Persistent storage testing

## Running Tests

### Quick Basic Test
```bash
./simple_test
```

### Automated Test Suite
```bash
./run_tiered_storage_tests.sh
```
**What it does:**
- Detects available test programs
- Runs basic memory manager test (simple_test)
- Runs tiered storage tests if available
- Generates detailed report
- Saves logs to ./test_logs/

### Real-time Monitoring
```bash
./monitor_tiered_storage.sh
```
**Features:**
- Real-time storage directory monitoring
- File counts and sizes
- Disk usage statistics
- Sensor file distribution
- Updates every 2 seconds

## Build System

### Manual Building
```bash
# Build basic test (minimal dependencies)
make simple_test

# Build full tests (requires all dependencies)
make test_tiered_storage
make test_tiered_storage_advanced

# Build everything
make all-programs

# Clean everything
make clean
```

### Build Configurations
- **LINUX_PLATFORM**: Enables Linux-specific code paths
- **Cross-platform compatibility**: Uses explicit data types (int32_t, uint16_t, etc.)
- **Conditional compilation**: Platform-specific features automatically selected

## Storage Configuration

### Default Locations
- **Production**: `/usr/qk/etc/sv/FC-1/history/`
- **Corrupted**: `/usr/qk/etc/sv/FC-1/history/corrupted/`
- **Journals**: `/usr/qk/etc/sv/FC-1/history/recovery.journal*`

### Temporary Testing
- **Simple setup**: `/tmp/imatrix_test_storage/`
- **No persistence**: Data cleared on reboot
- **No sudo required**: Works in restricted environments

## Expected Results

### Simple Test Success
```
iMatrix Memory Manager Simple Test
==================================

=== Testing Sector Allocation ===
Successfully allocated 10 sectors
[sectors freed...]

=== Testing Read/Write Operations ===
✓ Read/Write test PASSED

=== Testing Secure Functions ===
✓ Secure functions test PASSED

=== Testing Memory Statistics ===
Memory Statistics:
  Total sectors: 256
  [statistics displayed...]

=== Testing Performance ===
Performance Results:
  [performance metrics...]

=== TEST SUMMARY ===
Tests passed: 5/5
✓ ALL TESTS PASSED
```

### Test Suite Success
```
iMatrix Tiered Storage Test Suite
=================================

[PASS] memory_manager_basic
  Metrics: Tests: 5/5

[INFO] test_tiered_storage not available, skipping...

======================================
        TEST SUITE SUMMARY
======================================
[PASS] All tests passed!
```

## Troubleshooting

### Permission Issues
```bash
# Use simple setup to avoid sudo
./test_setup_simple.sh

# Or manually create directories
sudo mkdir -p /usr/qk/etc/sv/FC-1/history/corrupted
sudo chown $USER:$USER /usr/qk/etc/sv/FC-1/history
```

### Build Failures
```bash
# Check prerequisites
./test_setup.sh --verbose

# Manual dependency check
ls ../iMatrix/  # Should exist
ls ../mbedtls/  # Should exist for some builds
```

### Test Failures
```bash
# Run with detailed output
./simple_test 2>&1 | tee test_output.log

# Check system logs
dmesg | tail -20

# Verify storage permissions
ls -la /usr/qk/etc/sv/FC-1/history/
```

## Architecture Notes

### Cross-Platform Compatibility
- **Code works on**: Desktop PC (x86-64) + iMX6 (ARM)
- **Data types**: Explicit sizing (int32_t, uint16_t, uint8_t)
- **Platform detection**: `#ifdef LINUX_PLATFORM`
- **Conditional compilation**: CCMSRAM, WICED features

### Memory Manager Features
- **Sector allocation**: 256 sectors by default
- **Read/Write operations**: 32-bit data units
- **Secure functions**: Enhanced error checking
- **Statistics tracking**: Usage, fragmentation, performance
- **Cross-platform**: Portable across architectures

## File Structure

```
test_scripts/
├── simple_test.c              # Basic test program (minimal deps)
├── test_tiered_storage.c      # Full test program (full deps)
├── test_tiered_storage_advanced.c  # Advanced test (full deps)
├── imatrix_stubs.c            # Stub functions for testing
├── Makefile                   # Build configuration
├── test_setup.sh              # Full environment setup
├── test_setup_simple.sh       # Simple setup (no sudo)
├── run_tiered_storage_tests.sh # Automated test suite
├── monitor_tiered_storage.sh  # Real-time monitoring
├── CROSS_PLATFORM_NOTES.md   # Technical details
├── QUICK_START.md             # This file
└── test_logs/                 # Generated test reports
```

## Next Steps

1. **Start Simple**: Run `./test_setup_simple.sh` for basic validation
2. **Run Basic Test**: Execute `./simple_test` to verify functionality
3. **Automated Testing**: Use `./run_tiered_storage_tests.sh` for comprehensive validation
4. **Full Setup**: Run `./test_setup.sh` when ready for complete testing
5. **Monitor**: Use `./monitor_tiered_storage.sh` during active testing

## Support

For additional information:
- **Technical Details**: See `CROSS_PLATFORM_NOTES.md`
- **Full Documentation**: See `../test_scripts.md`
- **Build Issues**: Check `Makefile` comments
- **Architecture**: Review iMatrix documentation