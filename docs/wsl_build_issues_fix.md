# WSL Build Issues Resolution Plan

**Date**: 2026-01-02
**Author**: Claude Code Analysis
**Status**: READY FOR IMPLEMENTATION
**Target Environment**: WSL Ubuntu with GCC 6.4.0 ARM Toolchain

---

## Executive Summary

The build failures are caused by using the **wrong BTstack repository**. The working system uses Sierra Telecom's forked BTstack which includes required functions. The remote system likely cloned from the standard bluekitchen repository.

**Root Cause**: Wrong BTstack version (missing `hci_dump_open()` function)

**Solution**: Clone the correct BTstack fork from Sierra Telecom

---

## Quick Fix (5 minutes)

### Step 1: Replace BTstack with Correct Fork

```bash
cd ~/iMatrix/udhcp_issue

# Backup current btstack (optional)
mv btstack btstack.bluekitchen.backup

# Clone the correct Sierra Telecom fork
git clone https://github.com/sierratelecom/btstack.git btstack

# Checkout the exact working commit
cd btstack
git checkout 7b96a5268

# Verify hci_dump_open exists
grep "hci_dump_open" src/hci_dump.h
# Should output: void hci_dump_open(const char *filename, hci_dump_format_t format);
```

### Step 2: Clean and Rebuild

```bash
cd ~/iMatrix/udhcp_issue/Fleet-Connect-1/build

# Remove CMake cache
rm -f CMakeCache.txt

# Reconfigure
cmake --preset=arm-cross-debug ..

# Build
make -j4
```

### Step 3: Verify

```bash
# Check binary was created
file FC-1
# Should show: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
#              dynamically linked, interpreter /lib/ld-musl-armhf.so.1
```

---

## Detailed Explanation

### Why The Build Fails

The `.gitmodules` file incorrectly points to:
```
[submodule "btstack"]
    url = https://github.com/bluekitchen/btstack.git
```

But the working system uses:
```
origin = https://github.com/sierratelecom/btstack.git
```

Sierra Telecom's fork includes:
- `hci_dump_open()` function in `src/hci_dump.c` and `src/hci_dump.h`
- Other customizations for the iMatrix platform

### Working Environment Components

| Component | Repository | Commit/Version |
|-----------|------------|----------------|
| BTstack | `sierratelecom/btstack.git` | `7b96a5268` (v1.3.2-6) |
| mbedTLS | `Mbed-TLS/mbedtls.git` | `107ea89daaefb` |
| Toolchain | `/opt/qconnect_sdk_musl/` | GCC 6.4.0 (Buildroot 2018.02.6) |
| iMatrix | `sierratelecom/iMatrix-WICED-6.6-Client.git` | Current branch |
| Fleet-Connect-1 | `sierratelecom/Fleet-Connect-1.git` | Current branch |

### Toolchain Notes

The toolchain uses a **Buildroot toolchain-wrapper** binary at `/opt/qconnect_sdk_musl/bin/arm-linux-gcc`. This is an ELF executable (not a shell script) that wraps the real compiler.

**Toolchain wrapper checksum (for verification):**
```
6b5696b67492bab312caed15a9f86027  /opt/qconnect_sdk_musl/bin/toolchain-wrapper
```

---

## Alternative: Use Tar Archive

If you cannot access the Sierra Telecom GitHub repository, use the pre-created tar archive.

**Archive Location (on Greg's machine):**
```
/home/greg/qconnect_sw/ARM_Tools/btstack_sierratelecom_7b96a5268.tar.gz
Size: 139 MB
Contents: Complete BTstack fork at commit 7b96a5268
```

**Transfer to remote system** (choose one method):
```bash
# Option 1: SCP
scp greg@working-machine:/home/greg/qconnect_sw/ARM_Tools/btstack_sierratelecom_7b96a5268.tar.gz ~/

# Option 2: USB drive / shared folder
# Copy btstack_sierratelecom_7b96a5268.tar.gz to remote system
```

**On remote system - Extract and use:**
```bash
cd ~/iMatrix/udhcp_issue

# Backup current btstack
mv btstack btstack.bluekitchen.backup

# Extract the correct version
tar -xzvf ~/btstack_sierratelecom_7b96a5268.tar.gz

# Verify
grep "hci_dump_open" btstack/src/hci_dump.h
# Should output: void hci_dump_open(const char *filename, hci_dump_format_t format);
```

---

## Verification Checklist

After fixing, verify these points:

### 1. BTstack Version
```bash
cd ~/iMatrix/udhcp_issue/btstack
git log --oneline -1
# Should show: 7b96a5268 Delete worker_threads in open() if they ware already created.
```

### 2. hci_dump_open Function Exists
```bash
grep "void hci_dump_open" btstack/src/hci_dump.h
# Should output: void hci_dump_open(const char *filename, hci_dump_format_t format);
```

### 3. Toolchain Works
```bash
/opt/qconnect_sdk_musl/bin/arm-linux-gcc --version
# Should show: arm-linux-gcc.br_real (Buildroot 2018.02.6-g926ee31) 6.4.0
```

### 4. Build Succeeds
```bash
cd ~/iMatrix/udhcp_issue/Fleet-Connect-1/build
make -j4
file FC-1
# Should show ARM EABI5 executable
```

### 5. Binary Architecture
```bash
arm-linux-readelf -h FC-1 | grep Machine
# Should show: Machine: ARM
```

---

## Troubleshooting

### Error: Repository not found (sierratelecom/btstack)

If you don't have access to Sierra Telecom's GitHub:
1. Request access from Greg/team lead
2. Or request a tar archive of the btstack directory

### Error: Still getting hci_dump_open error after fix

Verify the correct BTstack is being used:
```bash
cd ~/iMatrix/udhcp_issue/btstack
git remote -v
# Must show: origin https://github.com/sierratelecom/btstack.git
```

### Error: -Wno-format-truncation not recognized

This error should NOT occur if using the correct toolchain. The Buildroot toolchain-wrapper handles this. Verify:
```bash
file /opt/qconnect_sdk_musl/bin/arm-linux-gcc
# Should show: symbolic link to toolchain-wrapper
```

### Error: sys/errno.h warning

This should NOT occur with the correct BTstack fork. If it does, the toolchain or BTstack version is wrong.

---

## Summary

| Issue | Root Cause | Solution |
|-------|------------|----------|
| `hci_dump_open` undefined | Wrong BTstack repo | Use `sierratelecom/btstack.git` @ `7b96a5268` |
| `-Wno-format-truncation` | Should not occur | Verify toolchain-wrapper is present |
| `sys/errno.h` warning | Should not occur | Verify correct BTstack fork |

**The fix is simple: Use the correct BTstack fork from Sierra Telecom.**

---

## Contact

If issues persist after following this guide:
1. Verify all component versions match the table above
2. Request a complete environment archive from the working system
3. Contact Greg for repository access

---

**Document Version**: 2.0
**Created**: 2026-01-02
**Based on**: Analysis of working build system vs remote system issues
