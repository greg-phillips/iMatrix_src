# iMatrix Tiered Storage Memory Test

This directory contains the test programs and scripts for validating the iMatrix Tiered Storage System.

## Directory Structure

Following the iMatrix architecture:
- **iMatrix Client Library**: `../iMatrix/` - Contains the core iMatrix functionality
- **Application Code**: `./test_scripts/` - Contains test programs that use the iMatrix library

## Files

### Test Programs
- `test_tiered_storage.c` - Basic tiered storage test program
- `test_tiered_storage_advanced.c` - Advanced test with command-line options

### Build System
- `Makefile` - Build configuration for both test programs
- Includes proper paths to reference `../iMatrix/` library

### Test Scripts
- `run_tiered_storage_tests.sh` - Comprehensive test suite
- `monitor_tiered_storage.sh` - Real-time monitoring

## Build Instructions

```bash
# Build both test programs
make

# Build just basic test
make test_tiered_storage

# Build just advanced test  
make test_tiered_storage_advanced

# Clean build artifacts
make clean
```

## Usage

```bash
# Basic test
make run

# Advanced test with options
make run-advanced

# Or run directly
./test_tiered_storage
./test_tiered_storage_advanced -r 50000 -v
```

## Current Status

**✅ COMPLETED:**
- Directory restructure following iMatrix architecture
- Updated Makefile with correct include paths (`../iMatrix/`)
- Moved all test files to proper location
- Added mbedtls include path
- Fixed header include order (storage.h before memory_manager.h)
- Added missing `sram_init_status_t` typedef resolution
- Fixed `CCMSRAM` macro issue for Linux platform
- Made `write_rs` function public
- Created simplified test program (`simple_test.c`) 
- Updated Makefile to build working programs

**⚠️ REMAINING ISSUES:**
- Some compilation conflicts in memory_manager.c:
  - Function forward declaration conflicts 
  - Implicit function declaration warnings
  - Printf format string mismatches
- Original test programs still need extensive API updates
- These are deeper iMatrix codebase integration issues

**✅ WORKING:**
- Architecture is correctly structured
- Makefile builds correctly
- Include paths work properly
- Simple test demonstrates basic memory manager API usage

## Next Steps

1. **Update Test API Usage**: Modify test programs to use current iMatrix API
2. **Fix Structure Access**: Update `test_csb_tsd.sensor.id` to `test_csb_tsd.id`
3. **Add Missing Definitions**: Include proper headers for missing constants
4. **Test Build**: Verify compilation with updated API usage
5. **Validate Functionality**: Run tests to ensure tiered storage works correctly

## Development Notes

The iMatrix architecture separates:
- **Library Code** (`../iMatrix/`): Core functionality, hardware abstraction, protocols
- **Application Code** (`./memory_test/`): Application-specific implementations

This separation allows:
- Clean library boundaries
- Proper include path management
- Easier maintenance and testing
- Better code organization

## Dependencies

- GCC compiler with pthread support
- Linux platform
- iMatrix library (`../iMatrix/`)
- mbedtls library (`../mbedtls/`)
- Storage directory: `/usr/qk/etc/sv/FC-1/history/`