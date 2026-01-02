# Plan: Add Remote Command Execution to FC-1 Script

**Date**: 2025-12-31
**Author**: Claude Code
**Branch**: feature/run_command_on_FC-1
**Status**: COMPLETED
**Last Updated**: 2026-01-02

---

## Overview

Add a new command to the `scripts/fc1` script that executes CLI commands on the FC-1 device via the microcom console interface and returns the output.

## Current Branch Status

| Repository | Current Branch |
|------------|---------------|
| iMatrix | feature/logging_work |
| Fleet-Connect-1 | feature/logging_work |

New branches to create: `feature/run_command_on_FC-1`

---

## Technical Approach

### Challenge

The FC-1 CLI is accessed via microcom connected to a PTY device (`/usr/qk/etc/sv/FC-1/console`). Microcom is an interactive terminal emulator that requires automation to:
1. Connect to the PTY
2. Send a command
3. Capture the output
4. Exit cleanly (Ctrl+X)

### Solution: Cross-Compile Expect for ARM

**Expect** is a TCL-based tool designed to automate interactive applications. We will:
1. Cross-compile Tcl 8.6 for ARM (expect's dependency)
2. Cross-compile Expect for ARM
3. Deploy both to the target device
4. Create an expect script to automate microcom interaction
5. Add `cmd` command to the fc1 script

### Dependencies

| Component | Version | Source |
|-----------|---------|--------|
| Tcl | 8.6.x | https://sourceforge.net/projects/tcl/files/Tcl/ |
| Expect | Latest | https://github.com/aeruder/expect |

### Target Platform

| Attribute | Value |
|-----------|-------|
| Architecture | ARM Cortex-A7 (ARMv7-A) |
| C Library | musl libc |
| Toolchain | `/opt/qconnect_sdk_musl/bin/arm-linux-gcc` |
| Sysroot | `/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot` |

---

## Implementation Plan

### Phase 1: Setup

- [x] Create feature branches in iMatrix and Fleet-Connect-1
- [x] Create build directory structure for external tools

### Phase 2: Build Tcl for ARM

- [x] Download Tcl 8.6.13 source
- [x] Create cross-compile build script
- [x] Configure Tcl for ARM with:
  - `--host=arm-linux`
  - `--prefix=/usr/local`
  - Cross-compiler settings
- [x] Build and create minimal deployment package

### Phase 3: Build Expect for ARM

- [x] Clone expect from https://github.com/aeruder/expect
- [x] Create Python patch script (patch_expect_v5.py) for cross-compilation
- [x] Patch Expect's configure to allow cross-compilation (9 error blocks, 1 warning)
- [x] Configure Expect for ARM with:
  - `--host=arm-linux`
  - `--with-tcl=<tcl-build-dir>`
  - Cross-compiler settings
- [x] Build and create deployment package

### Phase 4: Create Deployment Package

- [x] Create minimal runtime package containing:
  - `expect` binary (5.5KB stripped)
  - `libexpect5.45.3.so` (156KB stripped)
  - `libtcl8.6.so` (1.5MB stripped)
  - Tcl init scripts (minimal set)
- [x] Create wrapper script (expect-wrapper) for library paths
- [x] Create tarball: expect-arm.tar.gz (776KB)

### Phase 5: Implement fc1 Command

- [x] Create expect script for microcom automation (`fc1_cmd.exp`)
- [x] Add `cmd` command to `scripts/fc1`
- [x] Implement command with:
  - 10 second timeout
  - Raw output mode
  - Single command execution
- [x] Add auto-deployment of expect tools to target

### Phase 6: Testing

- [x] Test expect installation on target
- [x] Test basic command execution (e.g., `help`, `?`, `v`)
- [x] Test commands with multi-line output (`imx stats`, `ms`)
- [x] Test timeout handling
- [x] Verify clean exit from microcom
- [x] Test special characters (e.g., `?`) in commands

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `scripts/build_expect.sh` | Build script for Tcl + Expect cross-compilation |
| `scripts/fc1_cmd.exp` | Expect script for microcom automation |
| `external_tools/patch_expect_v5.py` | Python script to patch Expect's configure for cross-compilation |
| `external_tools/tcl8.6.13/` | Tcl 8.6.13 source (downloaded) |
| `external_tools/expect/` | Expect source (cloned from GitHub) |
| `external_tools/build/expect-arm.tar.gz` | ARM deployment package (776KB) |

### Modified Files

| File | Changes |
|------|---------|
| `scripts/fc1` | Add `cmd` command for CLI execution, auto-deploy expect tools |

---

## Command Usage

```bash
# Execute a single command on FC-1 CLI
./fc1 cmd "cell status"

# Execute help command
./fc1 cmd "help"

# Execute iMatrix stats
./fc1 cmd "imx stats"
```

### Expected Output

```bash
$ ./fc1 cmd "cell status"
Connecting to FC-1 CLI...
[Raw CLI output from command]
```

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Tcl build complexity | Use minimal configuration, disable unused features |
| Shared library dependencies | Static link where possible, deploy required libs |
| Target disk space | Create minimal package (~2-3 MB) |
| Microcom timing issues | Use expect's robust pattern matching |

---

## Alternative Approaches Considered

### 1. Telnet Port 23
The FC-1 has a telnet CLI on port 23 which is simpler to script:
```bash
echo "cell status" | nc 192.168.7.1 23
```
**Rejected**: User specifically requested microcom approach.

### 2. Direct PTY Write
Write directly to the PTY device without microcom.
**Rejected**: Less reliable, timing issues, no proper terminal handling.

### 3. Screen Automation
Use screen with scripting capabilities.
**Rejected**: More complex than expect, similar cross-compile requirements.

---

## Approval Checklist

- [x] Approach approved by user
- [x] Build dependencies available
- [x] Target has sufficient disk space for expect (~776KB package)
- [x] Testing on actual hardware

---

## Implementation Summary

**Date Completed**: 2025-12-31

### Technical Challenges Overcome

1. **Expect Cross-Compilation**: Expect's configure script has 9 explicit checks that block cross-compilation with "Expect can't be cross compiled" errors. Created a Python patch script (`patch_expect_v5.py`) that:
   - Replaces error blocks with sensible defaults for Linux ARM
   - Assumes termios (POSIX) terminal handling
   - Sets TCGETS/TCGETA as available
   - Handles setpgrp System V style

2. **Tcl Cross-Compilation**: Required cache variable hints for runtime tests:
   - `tcl_cv_strtod_buggy=ok`
   - `tcl_cv_strtod_unbroken=ok`
   - `ac_cv_func_memcmp_working=yes`

3. **Make Install Issues**: Full `make install` failed because it tried to run ARM binaries. Implemented partial install with fallback to manual file copying.

### Package Size

| Component | Size (stripped) |
|-----------|----------------|
| expect binary | 5.5 KB |
| libexpect5.45.3.so | 156 KB |
| libtcl8.6.so | 1.5 MB |
| Tcl init scripts | ~66 KB |
| **Total tarball** | **776 KB** |

### Usage

```bash
# Execute CLI commands on FC-1
./scripts/fc1 cmd "help"
./scripts/fc1 cmd "cell status"
./scripts/fc1 cmd "imx stats"
```

First run will automatically deploy expect tools to target.

---

## Post-Implementation Fixes (2026-01-02)

### Issue 1: Expect Tools Lost After Reboot

**Problem**: Expect tools deployed to `/usr/local` were lost after device reboot because `/usr/local` is volatile on the embedded system.

**Solution**: Changed deployment location to `/usr/qk/etc/sv/FC-1/expect/` which is persistent storage.

**Files Modified**:
- `scripts/fc1` - Updated `REMOTE_EXPECT_DIR` from `/usr/local` to `/usr/qk/etc/sv/FC-1/expect`
- Added error handling in `deploy_expect()` function with SCP verification

### Issue 2: Special Characters Lost in Commands

**Problem**: Commands containing special characters like `?` were not passed correctly. For example, `fc1 cmd "debug ?"` only sent "debug" without the `?`.

**Root Cause**: Shell glob expansion of `?` during SSH command processing via `eval`.

**Solution**:
1. Added `run_ssh()` function that uses arrays instead of `eval`
2. Properly quoted the command argument with single quotes in the SSH call

**Files Modified**:
- `scripts/fc1`:
  - Added `SSH_OPTS` and `SCP_OPTS` arrays for safe SSH execution
  - Added `run_ssh()` function to avoid eval issues with special chars
  - Fixed command quoting in `run_cli_cmd()` function

### Deployment Locations

| Component | Path |
|-----------|------|
| expect binary | `/usr/qk/etc/sv/FC-1/expect/bin/expect` |
| expect-wrapper | `/usr/qk/etc/sv/FC-1/expect/bin/expect-wrapper` |
| libtcl8.6.so | `/usr/qk/etc/sv/FC-1/expect/lib/libtcl8.6.so` |
| Tcl init scripts | `/usr/qk/etc/sv/FC-1/expect/lib/tcl8.6/` |

### Verified Working Commands

```bash
scripts/fc1 cmd "?"         # Full CLI help
scripts/fc1 cmd "v"         # Version info
scripts/fc1 cmd "ms"        # Memory statistics
scripts/fc1 cmd "debug ?"   # Debug flags (special char works)
scripts/fc1 cmd "cell status"  # Cellular status
scripts/fc1 cmd "imx stats"    # iMatrix statistics
```

---

**COMPLETED**: All implementation and testing complete as of 2026-01-02.
