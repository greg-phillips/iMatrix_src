# read_rs Memory Corruption Fix Summary

## Overview
Fixed critical memory corruption issues in the `read_rs` function usage where code was incorrectly passing byte sizes instead of uint32_t counts for the length parameter, causing 4x buffer overruns.

## Root Cause
The `read_rs` function signature:
```c
void read_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)
```

The `length` parameter expects the **number of uint32_t values** to read, not the number of bytes. However, multiple locations were passing byte constants like `TIME_RECORD_SIZE` (4) and `TSD_RECORD_SIZE` (4) instead of 1.

## Files Fixed

### 1. imatrix_upload.c
- **Line 1579**: Changed `uint16_t sector` to `platform_sector_t sector`
- **Line 1830**: Changed `read_rs(sector, index, &value.uint_32bit, TIME_RECORD_SIZE)` to `read_rs(sector, index, &value.uint_32bit, 1)`
- **Line 1833**: Changed `read_rs(sector, index + TIME_RECORD_SIZE, &value.uint_32bit, TSD_RECORD_SIZE)` to `read_rs(sector, index + TIME_RECORD_SIZE, &value.uint_32bit, 1)`
- **Line 1876**: Changed `read_rs(sector, index, &value.uint_32bit, TSD_RECORD_SIZE)` to `read_rs(sector, index, &value.uint_32bit, 1)`

### 2. fcgw_cli.c
- **Line 375**: Changed `uint16_t sector` to `platform_sector_t sector`
- **Line 395**: Changed `read_rs(sector, index, &value.uint_32bit, TIME_RECORD_SIZE)` to `read_rs(sector, index, &value.uint_32bit, 1)`
- **Line 398**: Changed `read_rs(sector, index + TIME_RECORD_SIZE, &value.uint_32bit, TSD_RECORD_SIZE)` to `read_rs(sector, index + TIME_RECORD_SIZE, &value.uint_32bit, 1)`
- **Line 439**: Changed `read_rs(sector, index, &value.uint_32bit, TSD_RECORD_SIZE)` to `read_rs(sector, index, &value.uint_32bit, 1)`

## Documentation Improvements

### memory_manager_core.c
Added comprehensive documentation explaining:
- Length parameter is in uint32_t units, not bytes
- Common mistakes to avoid
- Example usage patterns

### memory_manager_core.h
- Updated all function documentation to clarify parameter meanings
- Added warnings about common errors
- Fixed incorrect documentation that said offset was in uint32_t units (it's in bytes)

## Helper Functions Added

Added inline helper functions in memory_manager_core.h for common patterns:
- `read_single_uint32()` - Read a single value
- `read_time_and_value()` - Read timestamp/value pairs
- `write_single_uint32()` - Write a single value

## Debug Validation Added

Added runtime checks in DEBUG builds to detect common misuse:
- Warning when length equals TIME_RECORD_SIZE, TSD_RECORD_SIZE, or EVT_RECORD_SIZE
- Error detection for reads/writes beyond sector boundaries

## Impact

These changes prevent memory corruption that occurred when reading sensor data, particularly in:
- iMatrix status display commands
- Fleet Connect CLI status display
- Any code reading time-series or event-driven sensor data

## Recommendations

1. **Code Review**: Search for all other uses of `read_rs` and `write_rs` to ensure correct usage
2. **Migration**: Consider using the new helper functions for clearer, safer code
3. **Testing**: Run comprehensive tests on both Linux (32-bit sectors) and embedded (16-bit sectors) platforms
4. **Documentation**: Update developer guides to highlight this common pitfall

## Platform Considerations

The fixes properly handle platform differences:
- Linux: `platform_sector_t` is `uint32_t` (supports extended sectors)
- Embedded: `platform_sector_t` is `uint16_t` (memory constrained)

This ensures the code works correctly on both platforms without hardcoding sector number sizes.