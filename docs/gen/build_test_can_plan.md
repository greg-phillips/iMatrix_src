# CAN Test Program Build Plan

**Date:** 2025-12-15
**Author:** Claude Code
**Status:** Complete

---

## Overview

Create a standalone CMakeLists.txt to build the `test_system/can_test.c` program for CAN bus testing on the iMX6 embedded target.

## Analysis

### Source Dependencies

The `can_test.c` file requires:
1. **HostTypes.h** - From iMatrix/quake (basic type definitions)
2. **drivers/CanEvents.h** - From iMatrix/quake/drivers (CAN driver interface)
3. **pthread** - For mutex support
4. **Standard C libraries** - stdio, stdint, getopt, string, time

### Library Dependencies

1. **iMatrix library** - Contains CanEvents implementation (pre-built from Fleet-Connect-1)
2. **mbedtls libraries** - TLS support required by iMatrix
3. **libqfc** - Quake Fleet Connect library from `/qfc/arm_musl/libs`
4. **pthread, c, m, rt** - Standard system libraries
5. **i2c** - I2C support required by libqfc
6. **nl-3, nl-route-3** - Netlink libraries for networking
7. **bluetooth** - BlueZ library for BLE support

### Build Requirements

1. Cross-compilation for ARM (iMX6) using `/opt/qconnect_sdk_musl` toolchain
2. Same compiler flags as Fleet-Connect-1 for platform compatibility
3. Link against pre-built libraries from Fleet-Connect-1 build
4. Include paths for iMatrix headers

## Implementation

### CMakeLists.txt Structure

```
test_system/
  CMakeLists.txt    <- Created
  can_test.c        <- Existing source
  build/            <- Build output directory
    can_test        <- Built executable
```

### Key Configuration

1. **Minimum CMake version**: 3.10.0 (matches Fleet-Connect-1)
2. **Project name**: CAN_Test
3. **Executable name**: can_test
4. **Platform defines**: LINUX_PLATFORM, CAN_PLATFORM, IMX_FLASH=, CCMSRAM=
5. **Include directories**: iMatrix/quake for headers
6. **Pre-built libraries**: Uses Fleet-Connect-1/build output
7. **Link libraries**: imatrix, mbedtls, mbedx509, mbedcrypto, pthread, c, m, rt, i2c, qfc, nl-3, nl-route-3, bluetooth

### Build Commands

```bash
# Prerequisite: Fleet-Connect-1 must be built first

# Build can_test
cd test_system
mkdir build && cd build
CC=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
CXX=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
cmake -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot ..
make
```

### Issues Resolved

1. **stdbool.h missing**: Added `-include stdbool.h` compiler flag
2. **TRUE/FALSE undefined**: Added `-DTRUE=true -DFALSE=false` definitions
3. **i2c_smbus functions missing**: Added `i2c` library to link dependencies

## Todo List

- [x] Create plan document
- [x] Create CMakeLists.txt for test_system
- [x] Build and verify zero errors/warnings

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| test_system/CMakeLists.txt | Created | Build configuration for can_test |
| docs/gen/build_test_can_plan.md | Created | This plan document |

---

## Work Completion Summary

**Completed:** 2025-12-15

### Summary

Successfully created a CMakeLists.txt build configuration for the standalone CAN test program (`test_system/can_test.c`). The build system:

- Uses pre-built libraries from Fleet-Connect-1 build (iMatrix, mbedtls)
- Cross-compiles for ARM iMX6 target using musl toolchain
- Links against libqfc and system libraries
- Builds with zero errors and zero warnings

### Output

- **Executable**: `test_system/build/can_test`
- **Size**: ~196KB
- **Format**: ELF 32-bit ARM, dynamically linked with musl libc

### Build Metrics

- **Recompilations for syntax errors**: 3 (stdbool.h, TRUE/FALSE, i2c library)
- **Final build status**: Zero errors, zero warnings

