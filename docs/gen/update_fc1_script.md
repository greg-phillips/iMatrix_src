<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/fc1_update_fw.yaml
Generated on: 2026-01-04
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Update fc1 script to check for software upgrade of base OS file system.

**Date:** 2025-12-30
**Branch:** feature/update_fc1_script

---

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The wifi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following:

- iMatrix/CLAUDE.md
- Fleet-Connect-1/CLAUDE.md
- scripts/fc1 (the main script to be modified)
- scripts/fc1_service.sh (related service script)

use the template files as a base for any new files created
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

When running the fc1 script with option `deploy` or `push`, check the current OS version and determine if it is the latest version. The latest version is **4.0.0**.

### Checking OS Version

To check the version of the base OS file system, run the command: `cat /var/ver/versions` and check the values for u-boot, kernel, squash-fs, root-fs, and app.

Example output:
```
# cat /var/ver/versions
u-boot=3.0.0
kernel=3.0.0
squash-fs=3.0.0
root-fs=3.0.0
app=0
```

### Determining Memory Model

There are two memory models for the Fleet-Connect-1 Gateway:
- **512MB RAM** - use 512MB upgrade files
- **128MB RAM** - use 128MB upgrade files

Use the command: `cat /proc/meminfo` to determine the memory size.

If the value of "MemTotal" is **509740 kB or greater**, use the 512MB version for upgrade. Otherwise use the 128MB version.

Example:
```
# cat /proc/meminfo
MemTotal:         509740 kB
MemFree:          447992 kB
MemAvailable:     415272 kB
...
```

### Upgrade Files Location

**512MB version files** (located in `~/iMatrix/iMatrix_Client/quake_sw/rev_4.0.0/OSv4.0.0_512MB`):
- kernel_4.0.0.zip
- root-fs_4.0.0.zip
- squash-fs_4.0.0.zip
- u-boot-512_4.0.0.zip

**128MB version files** (located in `~/iMatrix/iMatrix_Client/quake_sw/rev_4.0.0/OSv4.0.0_128MB`):
- kernel_4.0.0.zip
- root-fs_4.0.0.zip
- squash-fs_4.0.0.zip
- u-boot-128_4.0.0.zip

### Upgrade Procedure

If an upgrade is needed:

1. Copy each of the upgrade files to the `/root/` directory on the gateway.

2. Execute the following commands in order:
   ```bash
   /etc/update_universal.sh --yes --type squash-fs --save --arch squash-fs_4.0.0.zip --dir /root
   /etc/update_universal.sh --yes --type kernel --save --arch kernel_4.0.0.zip --dir /root
   ```

3. For u-boot (depends on memory model):
   - **512MB model:**
     ```bash
     /etc/update_universal.sh --yes --type u-boot --save --arch u-boot-512_4.0.0.zip --dir /root
     ```
   - **128MB model:**
     ```bash
     /etc/update_universal.sh --yes --type u-boot --save --arch u-boot-128_4.0.0.zip --dir /root
     ```

4. Finally:
   ```bash
   /etc/update_universal.sh --yes --type root-fs --save --arch root-fs_4.0.0.zip --dir /root
   ```

5. After completion, reboot the gateway.

6. Reconnect and verify the upgrade:
   ```bash
   cat /var/ver/versions
   ```
   Expected output:
   ```
   u-boot=4.0.0
   kernel=4.0.0
   squash-fs=4.0.0
   root-fs=4.0.0
   app=0
   ```

### Files to Modify

- `scripts/fc1` - Main script requiring modification

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/update_fc1_script_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.
8. Merge the branch back into the original branch.
9. Update all documents with relevant details

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/fc1_update_fw.yaml
**Generated:** 2026-01-04
