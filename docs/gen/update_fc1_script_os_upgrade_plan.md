# FC1 Script OS Upgrade Feature - Implementation Plan

**Date Created:** 2026-01-04
**Author:** Claude Code
**Status:** Implemented
**Document Version:** 1.1
**Implementation Date:** 2026-01-04

---

## Overview

Add OS version checking and upgrade capability to the `fc1` script when running the `deploy` or `push` commands. The system will check if the target device is running the latest OS (4.0.0) and offer to upgrade if needed.

## Current State Analysis

### Branch Information
- **iMatrix submodule:** `Aptera_1_Clean`
- **Fleet-Connect-1 submodule:** `Aptera_1_Clean`
- **Feature branch to create:** `feature/fc1_os_upgrade`

### Files to Modify
- `scripts/fc1` - Main control script (406 lines)

### Existing Script Structure
The `fc1` script is a bash script that:
- Controls FC-1 service remotely via SSH/SCP
- Handles commands: start, stop, restart, status, deploy, push, ssh, cmd, config
- Uses `sshpass` for password-based SSH authentication
- Target default: `192.168.7.1:22222` (root user)

### Upgrade Files Verified
**512MB version** (`quake_sw/rev_4.0.0/OSv4.0.0_512MB/`):
- kernel_4.0.0.zip (5.4 MB)
- root-fs_4.0.0.zip (7.1 MB)
- squash-fs_4.0.0.zip (8.5 MB)
- u-boot-512_4.0.0.zip (152 KB)

**128MB version** (`quake_sw/rev_4.0.0/OSv4.0.0_128MB/`):
- kernel_4.0.0.zip (5.4 MB)
- root-fs_4.0.0.zip (7.1 MB)
- squash-fs_4.0.0.zip (8.5 MB)
- u-boot-128_4.0.0.zip (152 KB)

---

## Implementation Plan

### 1. Add Configuration Constants

Add the following constants near the top of the script (after existing configuration):

```bash
# OS Upgrade Configuration
LATEST_OS_VERSION="4.0.0"
UPGRADE_DIR="${SCRIPT_DIR}/../quake_sw/rev_4.0.0"
UPGRADE_DIR_512MB="${UPGRADE_DIR}/OSv4.0.0_512MB"
UPGRADE_DIR_128MB="${UPGRADE_DIR}/OSv4.0.0_128MB"
REMOTE_UPGRADE_DIR="/root"
MEMORY_THRESHOLD_KB=509740  # 512MB threshold
```

### 2. Add Version Checking Function

```bash
##
# @brief Check if OS upgrade is needed by comparing versions
# @return 0 if upgrade needed, 1 if current
##
check_os_version() {
    echo "Checking OS version on target..."

    local versions
    versions=$(run_remote "cat /var/ver/versions 2>/dev/null")

    if [ -z "$versions" ]; then
        echo "Warning: Could not read /var/ver/versions"
        return 1
    fi

    # Extract version components
    local uboot_ver kernel_ver squash_ver rootfs_ver
    uboot_ver=$(echo "$versions" | grep "^u-boot=" | cut -d= -f2)
    kernel_ver=$(echo "$versions" | grep "^kernel=" | cut -d= -f2)
    squash_ver=$(echo "$versions" | grep "^squash-fs=" | cut -d= -f2)
    rootfs_ver=$(echo "$versions" | grep "^root-fs=" | cut -d= -f2)

    echo "Current versions:"
    echo "  u-boot:    ${uboot_ver:-unknown}"
    echo "  kernel:    ${kernel_ver:-unknown}"
    echo "  squash-fs: ${squash_ver:-unknown}"
    echo "  root-fs:   ${rootfs_ver:-unknown}"
    echo "  Latest:    ${LATEST_OS_VERSION}"

    # Check if all components are at latest version
    if [ "$uboot_ver" = "$LATEST_OS_VERSION" ] && \
       [ "$kernel_ver" = "$LATEST_OS_VERSION" ] && \
       [ "$squash_ver" = "$LATEST_OS_VERSION" ] && \
       [ "$rootfs_ver" = "$LATEST_OS_VERSION" ]; then
        echo ""
        echo "OS is up to date (${LATEST_OS_VERSION})"
        return 1
    fi

    echo ""
    echo "OS upgrade available: current -> ${LATEST_OS_VERSION}"
    return 0
}
```

### 3. Add Memory Model Detection Function

```bash
##
# @brief Detect memory model (512MB or 128MB)
# @return Sets MEMORY_MODEL variable ("512" or "128")
##
detect_memory_model() {
    echo "Detecting memory model..."

    local meminfo
    meminfo=$(run_remote "cat /proc/meminfo 2>/dev/null")

    if [ -z "$meminfo" ]; then
        echo "Error: Could not read /proc/meminfo"
        return 1
    fi

    local mem_total_kb
    mem_total_kb=$(echo "$meminfo" | grep "^MemTotal:" | awk '{print $2}')

    if [ -z "$mem_total_kb" ]; then
        echo "Error: Could not parse MemTotal"
        return 1
    fi

    echo "Detected memory: ${mem_total_kb} kB"

    if [ "$mem_total_kb" -ge "$MEMORY_THRESHOLD_KB" ]; then
        MEMORY_MODEL="512"
        echo "Memory model: 512MB"
    else
        MEMORY_MODEL="128"
        echo "Memory model: 128MB"
    fi

    return 0
}
```

### 4. Add OS Upgrade Function

```bash
##
# @brief Perform OS upgrade on target device
# @note Requires MEMORY_MODEL to be set (call detect_memory_model first)
##
perform_os_upgrade() {
    if [ -z "$MEMORY_MODEL" ]; then
        echo "Error: Memory model not detected"
        return 1
    fi

    local upgrade_src_dir uboot_file
    if [ "$MEMORY_MODEL" = "512" ]; then
        upgrade_src_dir="$UPGRADE_DIR_512MB"
        uboot_file="u-boot-512_4.0.0.zip"
    else
        upgrade_src_dir="$UPGRADE_DIR_128MB"
        uboot_file="u-boot-128_4.0.0.zip"
    fi

    # Verify upgrade files exist
    echo "Verifying upgrade files in ${upgrade_src_dir}..."
    for file in kernel_4.0.0.zip root-fs_4.0.0.zip squash-fs_4.0.0.zip "$uboot_file"; do
        if [ ! -f "${upgrade_src_dir}/${file}" ]; then
            echo "Error: Missing upgrade file: ${file}"
            return 1
        fi
    done
    echo "All upgrade files found."

    # Copy upgrade files to target
    echo ""
    echo "Copying upgrade files to target ${REMOTE_UPGRADE_DIR}..."
    for file in kernel_4.0.0.zip root-fs_4.0.0.zip squash-fs_4.0.0.zip "$uboot_file"; do
        echo "  Copying ${file}..."
        if ! eval $SCP_CMD "${upgrade_src_dir}/${file}" "${TARGET_USER}@${TARGET_HOST}:${REMOTE_UPGRADE_DIR}/"; then
            echo "Error: Failed to copy ${file}"
            return 1
        fi
    done
    echo "All files copied successfully."

    # Execute upgrade commands in order
    echo ""
    echo "Executing OS upgrade sequence..."

    echo "1. Upgrading squash-fs..."
    if ! run_remote "/etc/update_universal.sh --yes --type squash-fs --save --arch squash-fs_4.0.0.zip --dir ${REMOTE_UPGRADE_DIR}"; then
        echo "Error: squash-fs upgrade failed"
        return 1
    fi

    echo "2. Upgrading kernel..."
    if ! run_remote "/etc/update_universal.sh --yes --type kernel --save --arch kernel_4.0.0.zip --dir ${REMOTE_UPGRADE_DIR}"; then
        echo "Error: kernel upgrade failed"
        return 1
    fi

    echo "3. Upgrading u-boot (${MEMORY_MODEL}MB)..."
    if ! run_remote "/etc/update_universal.sh --yes --type u-boot --save --arch ${uboot_file} --dir ${REMOTE_UPGRADE_DIR}"; then
        echo "Error: u-boot upgrade failed"
        return 1
    fi

    echo "4. Upgrading root-fs (this will trigger reboot)..."
    if ! run_remote "/etc/update_universal.sh --yes --type root-fs --save --arch root-fs_4.0.0.zip --dir ${REMOTE_UPGRADE_DIR}"; then
        echo "Error: root-fs upgrade failed"
        return 1
    fi

    echo ""
    echo "OS upgrade complete. The device will reboot."
    echo "Please wait for the device to come back online, then verify with:"
    echo "  ./fc1 ssh"
    echo "  cat /var/ver/versions"

    return 0
}
```

### 5. Add Upgrade Check Integration Function

```bash
##
# @brief Check for OS upgrade and prompt user
# @return 0 to continue, 1 to abort
##
check_and_prompt_upgrade() {
    if check_os_version; then
        echo ""
        printf "Would you like to upgrade the OS before continuing? [y/N]: "
        read -r response
        case "$response" in
            [yY]|[yY][eE][sS])
                if ! detect_memory_model; then
                    echo "Cannot determine memory model. Skipping upgrade."
                    return 0
                fi
                if perform_os_upgrade; then
                    echo ""
                    echo "Upgrade initiated. Please reconnect after reboot."
                    exit 0
                else
                    echo ""
                    printf "Upgrade failed. Continue with deploy/push anyway? [y/N]: "
                    read -r cont
                    case "$cont" in
                        [yY]|[yY][eE][sS])
                            return 0
                            ;;
                        *)
                            exit 1
                            ;;
                    esac
                fi
                ;;
            *)
                echo "Skipping OS upgrade."
                ;;
        esac
    fi
    return 0
}
```

### 6. Modify Deploy and Push Commands

Update the `deploy` case:
```bash
deploy)
    check_target
    check_and_prompt_upgrade
    deploy_script
    ;;
```

Update the `push` case:
```bash
push)
    check_target
    check_and_prompt_upgrade
    shift
    push_binary "$@"
    ;;
```

### 7. Add New Command for Manual Upgrade

Add a new command option:
```bash
upgrade)
    check_target
    if check_os_version; then
        if ! detect_memory_model; then
            echo "Error: Cannot determine memory model"
            exit 1
        fi
        perform_os_upgrade
    else
        echo "No upgrade needed."
    fi
    ;;
```

Update help text to document new command.

---

## Detailed Todo List

- [x] Create feature branch `feature/fc1_os_upgrade`
- [x] Add OS upgrade configuration constants
- [x] Implement `check_os_version()` function
- [x] Implement `detect_memory_model()` function
- [x] Implement `perform_os_upgrade()` function
- [x] Implement `check_and_prompt_upgrade()` function
- [x] Modify `deploy` case to call upgrade check
- [x] Modify `push` case to call upgrade check
- [x] Add `upgrade` command for manual upgrade
- [x] Update `show_help()` with new command documentation
- [x] Test script syntax (bash -n)
- [x] Update plan document with completion status

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Upgrade files missing | Verify files exist before attempting upgrade |
| SSH connection lost during upgrade | root-fs upgrade is last; device reboots cleanly |
| Wrong memory model detected | Use conservative threshold (509740 kB) |
| Partial upgrade failure | User prompted to continue or abort |
| User confusion | Clear prompts and status messages |

---

## Questions for Greg

1. **Abort vs Continue:** If upgrade fails partway through, should the script abort completely or give option to continue with deploy/push?
   - **Current plan:** Prompt user to continue or abort

2. **Force upgrade flag:** Would you like a `--force-upgrade` flag to skip the prompt and always upgrade if needed?
   - **Current plan:** Not included, but easy to add

3. **Skip upgrade flag:** Would you like a `--skip-upgrade` flag to bypass the check entirely?
   - **Current plan:** Not included, but easy to add

---

## Approval

Please review this plan and let me know if you would like any changes before I begin implementation.

---

## Implementation Summary

### Work Completed

Successfully implemented OS upgrade checking and execution capability for the FC-1 deployment script:

1. **Configuration Constants Added:**
   - `LATEST_OS_VERSION="4.0.0"`
   - `UPGRADE_DIR`, `UPGRADE_DIR_512MB`, `UPGRADE_DIR_128MB` paths
   - `REMOTE_UPGRADE_DIR="/root"`
   - `MEMORY_THRESHOLD_KB=509740` (512MB detection threshold)

2. **New Functions Implemented:**
   - `check_os_version()` - Reads `/var/ver/versions` and compares all components
   - `detect_memory_model()` - Reads `/proc/meminfo` to determine 512MB vs 128MB
   - `perform_os_upgrade()` - Copies files and executes upgrade sequence
   - `check_and_prompt_upgrade()` - Interactive prompt integrated into deploy/push

3. **Command Integration:**
   - `deploy` command now checks OS version before deploying
   - `push` command now checks OS version before pushing binary
   - New `upgrade` command for manual OS upgrade

4. **Help Text Updated:**
   - Documents new `upgrade` command
   - Notes OS version check on deploy/push commands
   - Includes example usage

### Files Modified

- `scripts/fc1` - Added ~200 lines of new functionality

### Metrics

- **Recompilations required for syntax errors:** 0
- **Elapsed time:** ~5 minutes
- **User wait time:** Minimal (approval only)

### Testing

- Script syntax validated with `bash -n`
- Help output verified to show new commands

---

**Plan Created By:** Claude Code
**Source Document:** docs/gen/update_fc1_script.md
**Implementation Completed:** 2026-01-04
