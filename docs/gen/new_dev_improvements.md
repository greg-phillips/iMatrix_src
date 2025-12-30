# /new_dev Slash Command - Improvement Recommendations

**Date**: 2025-12-30
**Author**: Claude Code Analysis
**Status**: Draft
**Related Command**: `/new_dev`

---

## Executive Summary

During execution of `/new_dev move_logging_to_filesystem`, several issues were encountered that required user intervention and added delays. This document captures these findings and proposes improvements to streamline the environment creation process.

---

## Issues Encountered

### 1. Missing mbedTLS ARM Build

**Problem**: The command checks for mbedTLS at `~/iMatrix/iMatrix_Client/mbedtls/build_arm/` but the actual build script creates the output in `~/iMatrix/iMatrix_Client/mbedtls/build/`.

**Impact**: False negative - the check fails even when mbedTLS may already be built.

**Current Behavior**:
```bash
# Check looks for:
ls -d ~/iMatrix/iMatrix_Client/mbedtls/build_arm

# But build_mbedtls.sh creates:
~/iMatrix/iMatrix_Client/mbedtls/build/
```

**Recommendation**: Update the check to look for `mbedtls/build/library/libmbedtls.a` which is the actual build artifact location.

---

### 2. Incorrect build_mbedtls.sh Path

**Problem**: The slash command documentation specifies running `build_mbedtls.sh` from `Fleet-Connect-1/` but the script is actually located in `iMatrix/`.

**Current Documentation**:
```bash
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1
./build_mbedtls.sh
```

**Correct Path**:
```bash
cd ~/iMatrix/iMatrix_Client/iMatrix
./build_mbedtls.sh
```

**Recommendation**: Update Step 3.5 in the slash command to use the correct path.

---

### 3. Missing CMSIS-DSP Repository

**Problem**: CMSIS-DSP is required for ARM math functions but is not included as a submodule in the iMatrix repository.

**Impact**: First-time users must manually clone CMSIS-DSP, adding ~30 seconds to setup.

**Recommendation**:
- Option A: Add CMSIS-DSP as a git submodule to iMatrix
- Option B: Auto-clone CMSIS-DSP without prompting (with `--auto-deps` flag)

---

### 4. No Dependency Caching/Sharing

**Problem**: Each new development environment requires its own mbedTLS build, wasting time and disk space.

**Impact**:
- Build time: ~3-5 seconds per environment
- Disk space: ~1.1MB per environment for mbedTLS libraries

**Recommendation**: Use symlinks to shared dependencies:
```bash
# Instead of copying/rebuilding mbedTLS for each worktree:
ln -s ~/iMatrix/iMatrix_Client/mbedtls/build ~/iMatrix/${env_name}/mbedtls/build
```

---

## Proposed Improvements

### Improvement 1: Pre-flight Dependency Resolution

Add a `--auto-deps` flag that automatically installs missing dependencies without prompting:

```bash
/new_dev my_feature --auto-deps
```

**Behavior**:
1. Check all dependencies upfront
2. Install any missing dependencies automatically
3. Continue with environment creation

---

### Improvement 2: Dependency Symlinking

For read-only dependencies that don't change between environments, use symlinks:

```yaml
# Dependencies that can be symlinked (read-only, shared):
shared_deps:
  - mbedtls/build/          # Pre-built libraries
  - iMatrix/CMSIS-DSP/      # ARM DSP library (large, read-only)

# Dependencies that must be copied (may be modified):
copied_deps:
  - .claude/
  - CLAUDE.md
```

**Benefits**:
- Faster environment creation (no rebuild)
- Less disk space usage
- Consistent library versions across environments

---

### Improvement 3: Correct Path References

Update the slash command with corrected paths:

| Current Path | Correct Path |
|--------------|--------------|
| `Fleet-Connect-1/build_mbedtls.sh` | `iMatrix/build_mbedtls.sh` |
| `mbedtls/build_arm/` | `mbedtls/build/library/` |

---

### Improvement 4: One-Time Bootstrap Script

Create a bootstrap script that prepares all dependencies once:

```bash
#!/bin/bash
# scripts/bootstrap_dev_deps.sh

echo "Bootstrapping development dependencies..."

# 1. Clone CMSIS-DSP if missing
if [ ! -d "$HOME/iMatrix/iMatrix_Client/iMatrix/CMSIS-DSP" ]; then
    echo "Cloning CMSIS-DSP..."
    git -C ~/iMatrix/iMatrix_Client/iMatrix clone https://github.com/ARM-software/CMSIS-DSP.git
fi

# 2. Build mbedTLS if missing
if [ ! -f "$HOME/iMatrix/iMatrix_Client/mbedtls/build/library/libmbedtls.a" ]; then
    echo "Building mbedTLS for ARM..."
    cd ~/iMatrix/iMatrix_Client/iMatrix && ./build_mbedtls.sh
fi

# 3. Verify QUAKE libs
if [ ! -d "$HOME/qfc/arm_musl/libs" ]; then
    echo "WARNING: QUAKE libs not found at ~/qfc/arm_musl/libs/"
    echo "Build may fail at link time."
fi

echo "Bootstrap complete!"
```

**Usage**:
```bash
# Run once after initial clone:
./scripts/bootstrap_dev_deps.sh

# Then create environments without prompts:
/new_dev my_feature
```

---

### Improvement 5: Environment Creation Time Tracking

Add timing information to help identify bottlenecks:

```
══════════════════════════════════════════════════════════════════
TIMING BREAKDOWN:
  Pre-flight checks:     0.5s
  Worktree creation:     2.1s
  Submodule init:        1.8s
  Configuration copy:    0.1s
  Build:                45.2s
  ─────────────────────────────
  Total:                49.7s
══════════════════════════════════════════════════════════════════
```

---

## Updated Slash Command Specification

### Corrected Step 3.5: ARM Cross-Compiler Requirements Validation

```bash
# 1. Core Toolchain (REQUIRED)
[ -f /opt/qconnect_sdk_musl/bin/arm-linux-gcc ]
[ -f /opt/qconnect_sdk_musl/bin/arm-linux-g++ ]
[ -d /opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot ]

# 2. QUAKE Libraries (REQUIRED for linking)
[ -d ~/qfc/arm_musl/libs ] || [ -d /home/greg/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs ]

# 3. mbedTLS Built Libraries (REQUIRED) - CORRECTED PATH
[ -f ~/iMatrix/iMatrix_Client/mbedtls/build/library/libmbedtls.a ]

# 4. CMSIS-DSP (REQUIRED for ARM math functions)
[ -d ~/iMatrix/iMatrix_Client/iMatrix/CMSIS-DSP ]
```

### Corrected mbedTLS Build Instructions

```bash
# CORRECTED: build_mbedtls.sh is in iMatrix/, not Fleet-Connect-1/
cd ~/iMatrix/iMatrix_Client/iMatrix
./build_mbedtls.sh
```

---

## Quick Reference: Dependency Checklist

Before running `/new_dev`, ensure these dependencies exist:

| Dependency | Path | How to Install |
|------------|------|----------------|
| ARM GCC | `/opt/qconnect_sdk_musl/bin/arm-linux-gcc` | Contact Sierra Telecom |
| ARM G++ | `/opt/qconnect_sdk_musl/bin/arm-linux-g++` | Contact Sierra Telecom |
| Sysroot | `/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot` | Contact Sierra Telecom |
| QUAKE Libs | `~/qfc/arm_musl/libs/` | Contact Sierra Telecom |
| mbedTLS | `~/iMatrix/iMatrix_Client/mbedtls/build/library/` | `cd iMatrix && ./build_mbedtls.sh` |
| CMSIS-DSP | `~/iMatrix/iMatrix_Client/iMatrix/CMSIS-DSP/` | `cd iMatrix && git clone https://github.com/ARM-software/CMSIS-DSP.git` |

---

## Recommended Workflow

### First-Time Setup (One-Time)

```bash
# 1. Ensure ARM toolchain is installed (contact Sierra Telecom)

# 2. Clone CMSIS-DSP
cd ~/iMatrix/iMatrix_Client/iMatrix
git clone https://github.com/ARM-software/CMSIS-DSP.git

# 3. Build mbedTLS
cd ~/iMatrix/iMatrix_Client/iMatrix
./build_mbedtls.sh

# 4. Verify all dependencies
ls /opt/qconnect_sdk_musl/bin/arm-linux-gcc
ls ~/qfc/arm_musl/libs/
ls ~/iMatrix/iMatrix_Client/mbedtls/build/library/libmbedtls.a
ls ~/iMatrix/iMatrix_Client/iMatrix/CMSIS-DSP/
```

### Creating New Environments (Fast Path)

```bash
# After first-time setup, environments create quickly:
/new_dev feature_name

# Expected time: ~50 seconds (mostly build time)
# With --no-build: ~5 seconds
```

---

## Action Items

| Priority | Item | Owner | Status |
|----------|------|-------|--------|
| High | Fix mbedTLS path check (`build_arm` → `build`) | Dev | Pending |
| High | Fix build_mbedtls.sh path in docs | Dev | Pending |
| Medium | Add CMSIS-DSP as iMatrix submodule | Dev | Pending |
| Medium | Create bootstrap_dev_deps.sh script | Dev | Pending |
| Low | Implement `--auto-deps` flag | Dev | Pending |
| Low | Add symlink support for shared deps | Dev | Pending |

---

## Appendix: Session Log Summary

**Environment Created**: `move_logging_to_filesystem`
**Total Time**: ~2 minutes (including dependency installation)

**Dependencies Installed During Session**:
1. CMSIS-DSP - Cloned from GitHub (6,580 files)
2. mbedTLS - Built for ARM (~3 seconds)

**Build Result**:
- Binary: FC-1 (13MB, ARM EABI5)
- Errors: 0
- Warnings: 4 (implicit function declarations - pre-existing)
