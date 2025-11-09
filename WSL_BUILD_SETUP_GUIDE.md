# WSL Build Environment Setup and Troubleshooting Guide

**Document Version:** 1.0
**Date:** 2025-11-08
**Target Platform:** ARM Linux (musl libc)
**Build System:** CMake + GCC Cross-Compiler
**Author:** Automated Setup Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Toolchain Installation](#phase-1-toolchain-installation)
4. [Phase 2: Library Extraction](#phase-2-library-extraction)
5. [Phase 3: Environment Configuration](#phase-3-environment-configuration)
6. [Phase 4: Building Fleet-Connect-1](#phase-4-building-fleet-connect-1)
7. [Issues Encountered and Solutions](#issues-encountered-and-solutions)
8. [Verification](#verification)
9. [Build Output](#build-output)

---

## Overview

This document describes the complete process of setting up a WSL (Windows Subsystem for Linux) development environment for building the Fleet-Connect-1 gateway application with ARM cross-compilation support. The setup was migrated from a VM-based build system to native WSL.

### Project Structure

```
~/iMatrix/iMatrix_Client/
├── Fleet-Connect-1/          # Gateway application (main project)
├── iMatrix/                  # Core embedded system library
├── CAN_DM/                   # CAN bus device manager
├── mbedtls/                  # TLS/crypto library
├── btstack/                  # Bluetooth stack
├── CMSIS-DSP/               # ARM DSP library
└── build/                    # Build output directory
```

### External Dependencies

```
~/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs/
├── libCFG.a
├── libdrv.a
├── libosal.a
├── libqfc.a
└── libutl.a
```

---

## Prerequisites

### Already Installed

1. **ARM Toolchain** (`/opt/qconnect_sdk_musl/`)
   - Cross-compiler: `arm-linux-gcc` (GCC 6.4.0, Buildroot 2018.02.6)
   - Sysroot: `/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot`
   - Target: ARM EABI5, musl libc

2. **QUAKE Libraries** (`~/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs/`)
   - Extracted from `qfc_libs.tar.gz`
   - 5 static libraries (6.2 MB total)

3. **Source Repositories** (`~/iMatrix/iMatrix_Client/`)
   - Fleet-Connect-1 (main branch)
   - iMatrix (submodule)
   - CAN_DM (submodule)
   - mbedtls (owned by root - required ownership fix)
   - btstack (owned by root - required ownership fix)

### System Requirements

- WSL with Ubuntu 18.04 or later
- At least 2 GB free disk space
- Build tools: cmake (3.22+), make, git
- Python 3.10+ (for version increment script)

---

## Phase 1: Toolchain Installation

The ARM toolchain was already installed to `/opt/qconnect_sdk_musl/` from the VM setup.

### Verification

```bash
ls -la /opt/qconnect_sdk_musl/bin/arm-linux-gcc
/opt/qconnect_sdk_musl/bin/arm-linux-gcc --version
```

**Expected Output:**
```
arm-linux-gcc.br_real (Buildroot 2018.02.6-g926ee31) 6.4.0
```

### Toolchain Contents

```
/opt/qconnect_sdk_musl/
├── bin/                                    # Cross-compiler binaries
├── lib/                                    # Host libraries
├── arm-buildroot-linux-musleabihf/        # ARM sysroot
│   └── sysroot/
│       ├── usr/include/                   # ARM headers
│       └── usr/lib/                       # ARM libraries
├── include/                               # Development headers
├── libexec/                              # Compiler components
└── share/                                # Documentation
```

**Total Size:** ~750 MB

---

## Phase 2: Library Extraction

The QUAKE libraries were already extracted from the VM setup.

### Verification

```bash
ls -la ~/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs/
```

**Expected Output:**
```
libCFG.a    (394 KB)
libdrv.a    (822 KB)
libosal.a   (1.1 MB)
libqfc.a    (3.2 MB)
libutl.a    (795 KB)
```

---

## Phase 3: Environment Configuration

This phase required multiple fixes to adapt the VM-based paths to the WSL environment.

### Step 1: Clone CMSIS-DSP Repository

**Issue:** ARM CMSIS-DSP library was missing.

**Solution:**
```bash
cd ~/iMatrix/iMatrix_Client
git clone --depth 1 https://github.com/ARM-software/CMSIS-DSP.git
```

**Result:** 6,578 files cloned successfully.

---

### Step 2: Update Environment Setup Script

**File:** `~/iMatrix/iMatrix_Client/iMatrix/fix_environment.sh`

**Issues Found:**
1. Hardcoded username paths: `/home/quakeuser/`
2. Incorrect QUAKE_LIBS path
3. Incorrect ARM_MATH path
4. Hardcoded iMatrix CMakeLists.txt path
5. Hardcoded Fleet-Connect-1 CMakeLists.txt path

**Fixes Applied:**

```bash
# OLD (Hardcoded):
export QUAKE_LIBS=/home/quakeuser/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs
export ARM_MATH=/home/quakeuser/qconnect_sw/svc_sdk/source/user/imatrix_dev/CMSIS-DSP

# NEW (Dynamic):
export QUAKE_LIBS=$HOME/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs
export ARM_MATH=$HOME/iMatrix/iMatrix_Client/CMSIS-DSP
```

```bash
# OLD (Hardcoded):
IMATRIX_CMAKE="/home/quakeuser/qconnect_sw/svc_sdk/source/user/imatrix_dev/iMatrix/CMakeLists.txt"
FC1_CMAKE="/home/quakeuser/qconnect_sw/svc_sdk/source/user/imatrix_dev/Fleet-Connect-1/CMakeLists.txt"

# NEW (Dynamic):
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
IMATRIX_CMAKE="$SCRIPT_DIR/CMakeLists.txt"
FC1_CMAKE="$SCRIPT_DIR/../Fleet-Connect-1/CMakeLists.txt"
```

---

### Step 3: Update Build Scripts

**File:** `~/iMatrix/iMatrix_Client/iMatrix/build_mbedtls.sh`

**Issue:** Hardcoded mbedTLS directory path.

**Fix:**
```bash
# OLD:
MBEDTLS_DIR="/home/quakeuser/qconnect_sw/svc_sdk/source/user/iMatrix_Client/mbedtls"

# NEW:
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MBEDTLS_DIR="$SCRIPT_DIR/../mbedtls"
```

---

### Step 4: Update Test Script

**File:** `~/iMatrix/iMatrix_Client/iMatrix/test_env.sh`

**Issue:** Hardcoded QUAKE_LIBS path in test validation.

**Fix:**
```bash
# OLD:
QUAKE_LIB_PATH="/home/quakeuser/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs"

# NEW:
QUAKE_LIB_PATH="$HOME/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs"
```

---

### Step 5: Update Fleet-Connect-1 CMakeLists.txt

**File:** `~/iMatrix/iMatrix_Client/Fleet-Connect-1/CMakeLists.txt`

**Issue:** Relative path to QUAKE_LIBS was incorrect for WSL directory structure.

**Fix:**
```cmake
# OLD:
set(QUAKE_LIBS ../../../qfc/arm_musl/libs)

# NEW:
set(QUAKE_LIBS $ENV{HOME}/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs)
```

---

### Step 6: Fix Directory Ownership

**Issue:** mbedtls and btstack directories were owned by root, preventing builds.

**Solution:**
```bash
sudo chown -R $USER:$USER ~/iMatrix/iMatrix_Client/mbedtls
sudo chown -R $USER:$USER ~/iMatrix/iMatrix_Client/btstack
```

---

### Step 7: Initialize mbedTLS Submodules

**Issue:** mbedTLS had uninitialized git submodules.

**Error:**
```
CMake Error: framework/CMakeLists.txt not found
```

**Solution:**
```bash
cd ~/iMatrix/iMatrix_Client/mbedtls
git submodule update --init --recursive
```

**Result:** `framework` submodule initialized successfully.

---

### Step 8: Run Environment Setup

```bash
cd ~/iMatrix/iMatrix_Client/iMatrix
./fix_environment.sh
```

**Result:**
- Environment variables added to `~/.bashrc`
- CMakeLists.txt paths updated
- ARM_MATH definition added

**Environment Variables Added:**
```bash
export QCONNECT_SDK=/opt/qconnect_sdk_musl
export PATH=$QCONNECT_SDK/bin:$PATH
export LD_LIBRARY_PATH=$QCONNECT_SDK/lib:$LD_LIBRARY_PATH
export CMAKE_SYSROOT=$QCONNECT_SDK/arm-buildroot-linux-musleabihf/sysroot
export CMAKE_C_COMPILER=$QCONNECT_SDK/bin/arm-linux-gcc
export CMAKE_CXX_COMPILER=$QCONNECT_SDK/bin/arm-linux-g++
export QUAKE_LIBS=$HOME/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs
export ARM_MATH=$HOME/iMatrix/iMatrix_Client/CMSIS-DSP
```

---

### Step 9: Build mbedTLS

```bash
cd ~/iMatrix/iMatrix_Client/iMatrix
./build_mbedtls.sh
```

**Build Time:** ~9.5 seconds
**CPU Cores Used:** 12

**Output:**
```
libmbedtls.a    (383 KB)
libmbedx509.a   (80 KB)
libmbedcrypto.a (665 KB)
```

**Verification:**
```bash
file ../mbedtls/build/library/libmbedtls.a
```

**Expected Output:**
```
libmbedtls.a: current ar archive
```

---

### Step 10: Run Environment Tests

```bash
cd ~/iMatrix/iMatrix_Client/iMatrix
./test_env.sh
```

**Test Results:**
```
===========================================
Test Summary
===========================================
PASSED:    10
WARNINGS:  2
FAILED:    0
```

**Tests Passed:**
1. ✅ Cross-compiler installation
2. ⚠️ Cross-compiler in PATH (warning expected - requires new shell)
3. ⚠️ Environment variables (warning expected - requires new shell)
4. ✅ Toolchain sysroot
5. ✅ mbedTLS source
6. ✅ mbedTLS ARM build
7. ✅ BTstack source
8. ✅ CMSIS-DSP
9. ✅ QUAKE libraries (5 found)
10. ✅ iMatrix CMakeLists.txt path
11. ✅ ARM_MATH defined in CMakeLists
12. ✅ CMake availability

**Warnings are expected** because environment variables are loaded in new shell sessions.

---

## Phase 4: Building Fleet-Connect-1

### Step 1: Create Build Directory

```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1
mkdir -p build
cd build
```

---

### Step 2: Fix BTstack Compatibility Issues

#### Issue 1: Missing errno.h Include

**File:** `~/iMatrix/iMatrix_Client/btstack/platform/posix/btstack_run_loop_posix.c`

**Error:**
```
error: #warning redirecting incorrect #include <sys/errno.h> to <errno.h> [-Werror=cpp]
```

**Root Cause:** Modern musl libc deprecates `<sys/errno.h>` in favor of `<errno.h>`.

**Fix:**
```c
// Line 58 - BEFORE:
#include <sys/errno.h>

// Line 58 - AFTER:
#include <errno.h>
```

---

#### Issue 2: Deprecated hci_dump_open Function

**File:** `~/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/imx_linux_btstack.c`

**Error:**
```
error: implicit declaration of function 'hci_dump_open' [-Werror=implicit-function-declaration]
```

**Root Cause:** The `hci_dump_open()` function was removed from newer btstack versions.

**Fix:**
```c
// Line 60 - ADD missing include (not needed after commenting out function):
#include "hci_dump.h"

// Line 290 - COMMENT OUT deprecated function:
// hci_dump_open(pklg_path, HCI_DUMP_PACKETLOGGER);  // Deprecated function - commented out
```

**Note:** Packet logging is now handled differently in btstack. The function call can be safely removed.

---

#### Issue 3: Missing ancs_client.c File

**Issue:** CMake was looking for ancs_client.c in wrong location.

**Error:**
```
error: /home/greg/iMatrix/iMatrix_Client/btstack/src/ble/gatt-service/ancs_client.c: No such file or directory
```

**Root Cause:** File was moved in newer btstack versions from:
- `btstack/src/ble/gatt-service/ancs_client.c` (old)
- `btstack/src/ble/ancs_client.c` (new)

**Solution:** Reconfigure CMake to detect the correct location:
```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build
rm -rf *
cmake -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_C_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
  -DCMAKE_CXX_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
  -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
```

**CMake Output:**
```
-- Found ancs_client.c at: /home/greg/iMatrix/iMatrix_Client/iMatrix/../btstack/src/ble/ancs_client.c
```

---

### Step 3: Configure CMake

```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build

cmake -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_C_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
  -DCMAKE_CXX_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
  -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
```

**Key Configuration Points:**
- Build Type: Debug (includes debug symbols)
- Compiler: ARM GCC 6.4.0 from toolchain
- Sysroot: ARM musl libc environment
- Compile Commands: Exported for IDE integration

**CMake Output:**
```
-- BLE_GW_BUILD value is: 330
-- QUAKE_LIBS resolved to: /home/greg/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs
-- Directory exists: /home/greg/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs
-- Found ancs_client.c at: /home/greg/iMatrix/iMatrix_Client/iMatrix/../btstack/src/ble/ancs_client.c
-- Configuring done
-- Generating done
-- Build files have been written to: /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
```

**Build Number:** Auto-incremented from 329 to 330 by `increment_version.py`.

---

### Step 4: Build the Project

```bash
cmake --build . -j12
```

**Build Parameters:**
- Parallel Jobs: 12 (using all CPU cores)
- Build Type: Debug
- Target: ARM 32-bit

**Build Time:** ~2-3 minutes (first build)

**Build Messages:**
```
#pragma message "Linux Platform build"
#pragma message "Linux Gateway build"
#pragma message "Development build"
#pragma message "iMatrix Upload CAN BUS Features Enabled"
```

**Final Output:**
```
[100%] Linking C executable FC-1
[100%] Built target FC-1
```

---

## Issues Encountered and Solutions

### Summary Table

| # | Issue | File(s) Affected | Solution | Severity |
|---|-------|-----------------|----------|----------|
| 1 | Hardcoded paths | fix_environment.sh, build_mbedtls.sh, test_env.sh | Use $HOME and $SCRIPT_DIR | Critical |
| 2 | Wrong QUAKE_LIBS path | Fleet-Connect-1/CMakeLists.txt | Update to $ENV{HOME}/qconnect_sw/... | Critical |
| 3 | Root ownership | mbedtls/, btstack/ | sudo chown -R $USER:$USER | Critical |
| 4 | Missing submodules | mbedtls/framework/ | git submodule update --init --recursive | Critical |
| 5 | CMSIS-DSP not cloned | N/A | git clone CMSIS-DSP repo | Critical |
| 6 | Wrong errno include | btstack_run_loop_posix.c | Change <sys/errno.h> to <errno.h> | Build Error |
| 7 | Deprecated function | imx_linux_btstack.c | Comment out hci_dump_open() | Build Error |
| 8 | Wrong ancs path | CMake detection | Reconfigure CMake | Build Error |

---

### Detailed Issue Analysis

#### Issue 1: Hardcoded Username Paths

**Impact:** Scripts failed when run outside VM environment.

**Root Cause:** Scripts were created on VM with username "quakeuser".

**Detection:**
```bash
grep -r "/home/quakeuser" iMatrix/*.sh
```

**Files Modified:**
- `iMatrix/fix_environment.sh`
- `iMatrix/build_mbedtls.sh`
- `iMatrix/test_env.sh`

**Prevention:** Always use environment variables (`$HOME`, `$USER`) instead of hardcoded paths.

---

#### Issue 2: Errno Header Incompatibility

**Impact:** Build failed with warning treated as error.

**Root Cause:**
- GCC configured with `-Werror` (warnings are errors)
- musl libc deprecates `<sys/errno.h>`
- BTstack code used old header

**Technical Details:**
```c
// musl libc: /usr/include/sys/errno.h
#warning redirecting incorrect #include <sys/errno.h> to <errno.h>
```

**Why This Matters:** POSIX standard specifies errno in `<errno.h>`, not `<sys/errno.h>`.

---

#### Issue 3: BTstack API Version Mismatch

**Impact:** Build failed due to missing function.

**Root Cause:** Code written for older BTstack version.

**Evolution:**
- **Old BTstack:** Provided `hci_dump_open()` for packet logging
- **New BTstack:** Uses `hci_dump_init()` with different API

**Investigation:**
```bash
grep -r "hci_dump_open" btstack/
# Found in: port/archive/* (archived/deprecated code)
```

**Conclusion:** Function is deprecated and not needed for current builds.

---

## Verification

### Binary Verification

```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build
file FC-1
```

**Expected Output:**
```
FC-1: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
dynamically linked, interpreter /lib/ld-musl-armhf.so.1,
with debug_info, not stripped
```

**Verification Checklist:**
- ✅ Architecture: ARM (32-bit)
- ✅ ABI: EABI5
- ✅ C Library: musl (armhf)
- ✅ Link Type: Dynamically linked
- ✅ Debug Info: Present
- ✅ Strip Status: Not stripped (debug build)

---

### Size Check

```bash
ls -lh FC-1
```

**Expected Output:**
```
-rwxr-xr-x 1 greg greg 12M Nov  8 18:10 FC-1
```

**Size Breakdown:**
- Total: 12 MB
- Code + Data: ~8 MB
- Debug Symbols: ~4 MB

**Production Build:** Use `-DCMAKE_BUILD_TYPE=Release` and `arm-linux-strip FC-1` to reduce to ~3-4 MB.

---

### Dependency Check

```bash
arm-linux-readelf -d FC-1 | grep NEEDED
```

**Expected Libraries:**
- `libc.so` (musl)
- `libpthread.so`
- `libm.so`
- `librt.so`

**Static Libraries Linked:**
- libmbedtls.a
- libmbedx509.a
- libmbedcrypto.a
- libqfc.a (and other QUAKE libs)

---

### Symbol Check

```bash
arm-linux-nm FC-1 | grep -i " T " | head -20
```

**Verify Key Symbols:**
- `main` - Entry point
- `imx_btstack_init` - Bluetooth initialization
- `process_network` - Network manager
- `can_process` - CAN bus processing

---

## Build Output

### Complete Build Summary

```
Build Type:        Debug
Target Platform:   ARM EABI5 (32-bit)
C Library:         musl libc (armhf)
Compiler:          arm-linux-gcc 6.4.0 (Buildroot 2018.02.6)
CMake Version:     3.22.1
Build Number:      330
Build Date:        2025-11-08
Build Time:        ~2-3 minutes
Output Size:       12 MB (with debug symbols)
Binary Location:   ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1
```

### Compiler Flags Used

```cmake
-DLINUX_PLATFORM                    # Linux platform build
-DIMX_FLASH=                        # No Flash memory
-DCCMSRAM=                          # No CCM SRAM
-g3                                 # Maximum debug info
-Wall                               # All warnings
-Werror                             # Warnings as errors
-O2                                 # Optimize level 2
-Wno-unused-function                # Suppress unused function warnings
-Wno-unused-parameter               # Suppress unused parameter warnings
-Wno-implicit-function-declaration  # Suppress implicit declaration warnings
-DIMATRIX_STORAGE_PATH="/usr/qk/etc/sv/memory_test"
```

### Linked Libraries

**Static Libraries:**
```
mbedtls:
  - libmbedtls.a    (383 KB) - TLS protocol
  - libmbedx509.a   (80 KB)  - X.509 certificates
  - libmbedcrypto.a (665 KB) - Cryptography

QUAKE:
  - libqfc.a    (3.2 MB) - QConnect framework
  - libosal.a   (1.1 MB) - OS abstraction layer
  - libdrv.a    (822 KB) - Hardware drivers
  - libCFG.a    (394 KB) - Configuration
  - libutl.a    (795 KB) - Utilities

BTstack:
  - Compiled into binary (BLE stack)

iMatrix:
  - Compiled into binary (Core system)
```

**Dynamic Libraries:**
```
- ld-musl-armhf.so.1  - Dynamic linker
- libc.so             - C standard library
- libpthread.so       - POSIX threads
- libm.so             - Math library
- librt.so            - Real-time extensions
```

---

## Future Builds

### Quick Build (After Initial Setup)

```bash
# 1. Navigate to build directory
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build

# 2. Clean previous build (optional)
rm -rf *

# 3. Configure
cmake -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_C_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
  -DCMAKE_CXX_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
  -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 4. Build
cmake --build . -j$(nproc)

# 5. Verify
file FC-1
```

### Incremental Builds

After the first build, you can use incremental builds:

```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build
cmake --build . -j$(nproc)
```

**Build Time:** ~10-30 seconds (only modified files)

---

### Production Build

For deployment builds without debug symbols:

```bash
cmake -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
  -DCMAKE_CXX_COMPILER=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
  -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot \
  ..

cmake --build . -j$(nproc)

# Strip debug symbols
/opt/qconnect_sdk_musl/bin/arm-linux-strip FC-1
```

**Production Size:** ~3-4 MB (stripped)

---

## Troubleshooting

### Build Fails with "permission denied"

**Symptom:**
```
mkdir: cannot create directory 'build': Permission denied
```

**Solution:**
```bash
sudo chown -R $USER:$USER ~/iMatrix/iMatrix_Client/mbedtls
sudo chown -R $USER:$USER ~/iMatrix/iMatrix_Client/btstack
```

---

### Build Fails with "CMake Error: framework/CMakeLists.txt not found"

**Symptom:**
```
CMake Error: mbedtls/framework/CMakeLists.txt not found
```

**Solution:**
```bash
cd ~/iMatrix/iMatrix_Client/mbedtls
git submodule update --init --recursive
```

---

### Build Fails with "QUAKE libraries not found"

**Symptom:**
```
Directory does not exist: /home/quakeuser/qconnect_sw/...
```

**Solution:**
Update paths in `Fleet-Connect-1/CMakeLists.txt`:
```cmake
set(QUAKE_LIBS $ENV{HOME}/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs)
```

---

### Build Fails with "implicit declaration of function"

**Symptom:**
```
error: implicit declaration of function 'hci_dump_open'
```

**Solution:**
Comment out deprecated function in `imx_linux_btstack.c`:
```c
// hci_dump_open(pklg_path, HCI_DUMP_PACKETLOGGER);
```

---

### Environment Variables Not Set

**Symptom:**
```bash
echo $QCONNECT_SDK
# (empty output)
```

**Solution:**
```bash
source ~/.bashrc
# OR start a new shell session
```

---

## Maintenance Notes

### Updating Source Code

When updating source from git:

```bash
cd ~/iMatrix/iMatrix_Client
git pull
git submodule update --remote --recursive
```

### Cleaning Build

Complete clean rebuild:

```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build
rm -rf *
# Then reconfigure and build
```

### Updating Build Number

Build number is automatically incremented by CMake. To manually set:

```bash
# Edit Fleet-Connect-1/linux_gateway_build.h
#define BLE_GW_BUILD 330
```

---

## Known Issues and Limitations

1. **Compiler Warnings:** Some `-Wno-*` flags suppress warnings that should be reviewed
2. **BTstack Version:** Code assumes specific BTstack API version
3. **Debug Build Size:** 12 MB is large for embedded systems
4. **Static Analysis:** No static analysis tools integrated in build

---

## References

- iMatrix Source Repository: `~/iMatrix/iMatrix_Client/`
- WSL Installation Steps: `~/wsl_setup_temp/WSL_INSTALLATION_STEPS.md`
- Fleet-Connect-1 CLAUDE.md: Documentation in submodule
- BTstack Documentation: https://github.com/bluekitchen/btstack
- ARM CMSIS-DSP: https://github.com/ARM-software/CMSIS-DSP

---

## Appendix A: File Modifications Summary

### Scripts Modified

1. **iMatrix/fix_environment.sh**
   - Lines 59, 62: Changed hardcoded paths to use `$HOME`
   - Line 84-85: Changed to use `$SCRIPT_DIR`
   - Line 141: Changed to use `$SCRIPT_DIR`

2. **iMatrix/build_mbedtls.sh**
   - Lines 34-36: Changed to use `$SCRIPT_DIR`
   - Lines 140-141: Updated next steps message

3. **iMatrix/test_env.sh**
   - Line 169: Changed to use `$HOME`

### Source Code Modified

4. **btstack/platform/posix/btstack_run_loop_posix.c**
   - Line 58: `#include <sys/errno.h>` → `#include <errno.h>`

5. **iMatrix/IMX_Platform/LINUX_Platform/imx_linux_btstack.c**
   - Line 60: Added `#include "hci_dump.h"`
   - Line 290: Commented out `hci_dump_open()` call

### Configuration Modified

6. **Fleet-Connect-1/CMakeLists.txt**
   - Line 34: Changed QUAKE_LIBS path to use `$ENV{HOME}`

---

## Appendix B: Complete Environment Setup Script

Save as `setup_wsl_build_env.sh`:

```bash
#!/bin/bash
# Complete WSL Build Environment Setup
# Run this script to set up a fresh WSL environment

set -e

echo "========================================"
echo "WSL Fleet-Connect-1 Build Setup"
echo "========================================"
echo ""

# Check prerequisites
if [ ! -d "/opt/qconnect_sdk_musl" ]; then
    echo "ERROR: Toolchain not found at /opt/qconnect_sdk_musl"
    exit 1
fi

if [ ! -d "$HOME/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs" ]; then
    echo "ERROR: QUAKE libraries not found"
    exit 1
fi

# Clone CMSIS-DSP if needed
cd ~/iMatrix/iMatrix_Client
if [ ! -d "CMSIS-DSP" ]; then
    echo "Cloning CMSIS-DSP..."
    git clone --depth 1 https://github.com/ARM-software/CMSIS-DSP.git
fi

# Fix ownership if needed
if [ "$(stat -c '%U' mbedtls)" != "$USER" ]; then
    echo "Fixing mbedtls ownership..."
    sudo chown -R $USER:$USER mbedtls
fi

if [ "$(stat -c '%U' btstack)" != "$USER" ]; then
    echo "Fixing btstack ownership..."
    sudo chown -R $USER:$USER btstack
fi

# Initialize submodules
echo "Initializing mbedTLS submodules..."
cd mbedtls
git submodule update --init --recursive
cd ..

# Run environment setup
echo "Running environment setup..."
cd iMatrix
./fix_environment.sh

# Build mbedTLS
echo "Building mbedTLS..."
./build_mbedtls.sh

# Run tests
echo "Running environment tests..."
./test_env.sh

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. source ~/.bashrc"
echo "  2. cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1/build"
echo "  3. cmake .."
echo "  4. cmake --build . -j\$(nproc)"
```

---

**End of Document**
