# Fleet-Connect-1 Build System Duplication Plan

**Date:** 2026-01-01
**Author:** Claude Code Analysis
**Status:** COMPLETED
**Branch:** feature/build_system_toollchain
**Completion Time:** 2026-01-01 16:00 UTC

---

## Executive Summary

This document outlines the complete plan to duplicate the Fleet-Connect-1 build system toolchain for deployment on another WSL instance. The goal is to copy all required ARM build tools to `/home/greg/qconnect_sw/ARM_Tools` and create setup scripts for easy deployment.

**Implementation Status:** All phases completed successfully.

---

## Implementation Summary

### Work Completed

| Phase | Description | Status | Duration |
|-------|-------------|--------|----------|
| 1 | Copy ARM Toolchain (586 MB) | COMPLETE | ~2 min |
| 2 | Create Setup Scripts (3 scripts) | COMPLETE | ~5 min |
| 3 | Documentation (README_SETUP.md) | COMPLETE | ~3 min |
| 4 | Build Verification | COMPLETE | ~1 min |

### Deliverables Created

```
/home/greg/qconnect_sw/ARM_Tools/
├── qconnect_sdk_musl/           (586 MB - Complete ARM toolchain)
│   ├── bin/                     (Cross-compiler binaries)
│   ├── lib/                     (Host libraries)
│   ├── arm-buildroot-linux-musleabihf/
│   │   └── sysroot/             (Target system root)
│   └── ...
├── setup_toolchain.sh           (Install toolchain to /opt/)
├── setup_environment.sh         (Configure ~/.bashrc)
├── verify_installation.sh       (Validate installation - 11 tests)
└── README_SETUP.md              (Complete setup documentation)
```

### Verification Results

```
===========================================
ARM Build Environment Verification
===========================================
Test 1:  Cross-compiler installation...  PASS
Test 2:  Cross-compiler in PATH...       PASS
Test 3:  Environment variables...        PASS
Test 4:  Toolchain sysroot...           PASS
Test 5:  CMSIS-DSP (ARM_MATH)...        PASS
Test 6:  QUAKE libraries...             PASS
Test 7:  CMake availability...          PASS
Test 8:  iMatrix repository...          PASS
Test 9:  mbedTLS source...              PASS
Test 10: mbedTLS ARM build...           PASS
Test 11: Compile test...                PASS
===========================================
PASSED: 11, WARNINGS: 0, FAILED: 0
```

### Binary Verification

```
FC-1: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
      dynamically linked, interpreter /lib/ld-musl-armhf.so.1,
      with debug_info, not stripped
```

---

## Current State Analysis

### Current Branches
- **iMatrix:** `feature/csr_process_fix`
- **Fleet-Connect-1:** `Aptera_1_Clean`

### Existing Toolchain Location
```
/opt/qconnect_sdk_musl/                    (586 MB total)
├── arm-buildroot-linux-musleabihf/        (Target sysroot and libraries)
├── bin/                                    (Cross-compiler binaries)
├── etc/                                    (Configuration files)
├── include/                                (Host headers)
├── lib/                                    (Host libraries)
├── libexec/                                (GCC internal tools)
├── share/                                  (Documentation and data)
└── var/                                    (Variable data)
```

### Toolchain Details
- **Compiler:** arm-linux-gcc.br_real (Buildroot 2018.02.6-g926ee31) 6.4.0
- **Target Triple:** arm-buildroot-linux-musleabihf
- **Architecture:** ARM Cortex-A7, ARMv7-A
- **C Library:** musl libc
- **ABI:** Hard float (armhf)

### Required Dependencies
1. **ARM Toolchain** - `/opt/qconnect_sdk_musl/` (586 MB)
2. **QUAKE Libraries** - `/home/greg/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs/` (~7 MB)
3. **CMSIS-DSP** - `/home/greg/iMatrix/iMatrix_Client/CMSIS-DSP/` (clone from GitHub)
4. **mbedTLS** - Built from source in `/home/greg/iMatrix/iMatrix_Client/mbedtls/`
5. **BTstack** - `/home/greg/iMatrix/iMatrix_Client/btstack/` (submodule)

---

## Implementation Plan

### Phase 1: Copy ARM Toolchain (COMPLETED)

**Objective:** Copy the complete ARM toolchain to a portable location.

**Tasks:**
- [x] 1.1 Create target directory `/home/greg/qconnect_sw/ARM_Tools`
- [x] 1.2 Copy toolchain: `cp -a /opt/qconnect_sdk_musl /home/greg/qconnect_sw/ARM_Tools/`
- [x] 1.3 Verify copy integrity (586 MB matches)
- [x] 1.4 Test copied compiler (GCC 6.4.0 confirmed)

---

### Phase 2: Create Setup Scripts (COMPLETED)

**Objective:** Create comprehensive setup scripts for new WSL instance deployment.

**Tasks:**
- [x] 2.1 Create `setup_toolchain.sh` - Main installation script
- [x] 2.2 Create `setup_environment.sh` - Environment variable configuration
- [x] 2.3 Create `verify_installation.sh` - Validation script (11 tests)
- [x] 2.4 Create `README_SETUP.md` - Setup documentation

---

### Phase 3: Documentation (COMPLETED)

**Objective:** Create comprehensive documentation for the portable build system.

**Tasks:**
- [x] 4.1 Update this plan document with completion status
- [x] 4.2 Create `ARM_Tools/README_SETUP.md` explaining the contents
- [x] 4.3 Document the complete new WSL setup procedure

---

### Phase 4: Verification (COMPLETED)

**Objective:** Verify the build system works correctly.

**Tasks:**
- [x] 5.1 Build mbedTLS using the toolchain (383K + 80K + 665K)
- [x] 5.2 Verify Fleet-Connect-1 binary (13.2 MB)
- [x] 5.3 Verify binary is correct architecture (ARM EABI5)
- [x] 5.4 Run all verification scripts (11/11 passed)

---

## Deliverables Checklist

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | ARM toolchain copied to ARM_Tools | COMPLETE |
| 2 | setup_toolchain.sh script | COMPLETE |
| 3 | setup_environment.sh script | COMPLETE |
| 4 | verify_installation.sh script | COMPLETE |
| 5 | README_SETUP.md documentation | COMPLETE |
| 6 | mbedTLS build verification | COMPLETE |
| 7 | FC-1 binary verification | COMPLETE |
| 8 | Final documentation updated | COMPLETE |

---

## New WSL Instance Setup Procedure

### Quick Start

1. **Copy ARM_Tools to new system:**
   ```bash
   # From backup location (USB drive, network share, etc.)
   cp -r /path/to/ARM_Tools ~/qconnect_sw/ARM_Tools
   ```

2. **Install Toolchain (requires sudo):**
   ```bash
   cd ~/qconnect_sw/ARM_Tools
   sudo ./setup_toolchain.sh
   ```

3. **Configure Environment:**
   ```bash
   ./setup_environment.sh
   source ~/.bashrc
   ```

4. **Clone Repository:**
   ```bash
   git clone --recurse-submodules <repo-url> ~/iMatrix/iMatrix_Client
   cd ~/iMatrix/iMatrix_Client
   git submodule update --init --recursive
   ```

5. **Clone CMSIS-DSP:**
   ```bash
   cd ~/iMatrix/iMatrix_Client
   git clone --depth 1 https://github.com/ARM-software/CMSIS-DSP.git
   ```

6. **Verify Installation:**
   ```bash
   cd ~/qconnect_sw/ARM_Tools
   ./verify_installation.sh
   ```

7. **Build mbedTLS:**
   ```bash
   cd ~/iMatrix/iMatrix_Client/iMatrix
   ./build_mbedtls.sh
   ```

8. **Build Fleet-Connect-1:**
   ```bash
   cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1
   cmake --preset arm-cross-debug
   cd build
   make -j4
   ```

9. **Verify Binary:**
   ```bash
   file build/FC-1
   # Should show: ARM, EABI5
   ```

---

## Files Created

| File | Location | Size | Purpose |
|------|----------|------|---------|
| qconnect_sdk_musl/ | ARM_Tools/ | 586 MB | Complete ARM toolchain |
| setup_toolchain.sh | ARM_Tools/ | 3.5 KB | Install to /opt/ |
| setup_environment.sh | ARM_Tools/ | 3.4 KB | Configure ~/.bashrc |
| verify_installation.sh | ARM_Tools/ | 8.6 KB | 11-test validation |
| README_SETUP.md | ARM_Tools/ | 4.5 KB | Setup documentation |

---

## Risk Assessment

| Risk | Mitigation | Status |
|------|------------|--------|
| Large file copy failure | Size comparison verified | Mitigated |
| Path dependencies in toolchain | Tested compiler works | Mitigated |
| Permission issues | Scripts check for sudo | Mitigated |
| Missing QUAKE libraries | Documented in README | Mitigated |

---

**Plan Created By:** Claude Code Analysis
**Source Specification:** docs/prompt_work/build_system_toollchain.yaml
**Document Version:** 2.0
**Implementation Completed:** 2026-01-01
