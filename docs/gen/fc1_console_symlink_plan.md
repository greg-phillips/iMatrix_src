# Plan: FC-1 Console Symlink at /usr/qk/etc/sv/FC-1/console

**Date:** 2025-12-30
**Branch:** feature/fc1-console-symlink
**Author:** Claude Code
**Status:** Draft - Awaiting Review

---

## Problem Analysis

### Current Behavior
The FC-1 application creates a PTY (pseudo-terminal) for CLI access using `posix_openpt()` in `/home/greg/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/imx_linux_tty.c`. The PTY number (e.g., `/dev/pts/3`, `/dev/pts/7`) is dynamically assigned by the Linux kernel, requiring users to check the PTY number each time FC-1 starts.

### User Requirement
Provide a consistent, well-known path for FC-1 console access that doesn't change between restarts.

### Technical Challenge
Linux's devpts filesystem allocates PTY numbers sequentially. Applications cannot request a specific PTY number through standard APIs. The device nodes in `/dev/pts/` are created/destroyed automatically by the kernel when PTY masters are opened/closed.

---

## Proposed Solution

### Approach: Well-Known Symlink + Guaranteed Cleanup

Instead of trying to force a specific PTY number (which is not possible with standard Linux APIs), we will:

1. **Create a well-known symlink** at `/usr/qk/etc/sv/FC-1/console` that always points to FC-1's current PTY
2. **On startup**, remove any stale symlink and create a fresh one pointing to the actual PTY device
3. **Move `FC-1_details.txt`** from `/root/` to `/usr/qk/etc/sv/FC-1/FC-1_details.txt`
4. **Update the details file** with the actual PTY path and the symlink path
5. **Print clear connection instructions** on startup

### Directory Structure
```
/usr/qk/etc/sv/FC-1/
├── console          # Symlink to actual PTY (e.g., -> /dev/pts/3)
└── FC-1_details.txt # Startup details including PTY info and debug flags
```

### Connection Method
Users will connect using:
```bash
microcom /usr/qk/etc/sv/FC-1/console
```

---

## Implementation Details

### Files to Modify

1. **`iMatrix/IMX_Platform/LINUX_Platform/imx_linux_tty.c`**
   - Add function `imx_tty_create_symlink()` to create symlink at known location
   - Modify `imx_tty_init()` to call the symlink function after PTY creation
   - Modify `imx_tty_deinit()` to remove symlink on clean shutdown

2. **`iMatrix/IMX_Platform/LINUX_Platform/imx_linux_tty.h`**
   - Add constants for paths:
     - `#define IMX_FC1_DIR "/usr/qk/etc/sv/FC-1"`
     - `#define IMX_TTY_SYMLINK_PATH "/usr/qk/etc/sv/FC-1/console"`
   - Add declaration for new function

3. **`Fleet-Connect-1/init/init.c`**
   - Change `write_fc1_details_file()` to write to `/usr/qk/etc/sv/FC-1/FC-1_details.txt`
   - Ensure directory exists before writing
   - Include symlink path in output

### Implementation Steps

#### Step 1: Add Symlink Creation Function

```c
/**
 * @brief Create well-known symlink to PTY device
 *
 * Creates a symlink at /usr/qk/etc/sv/FC-1/console pointing to the actual PTY device.
 * This provides a consistent access path regardless of dynamically assigned PTY number.
 * Ensures the directory exists before creating the symlink.
 *
 * @return IMX_SUCCESS on success, error code otherwise
 */
imx_result_t imx_tty_create_symlink(void);
```

#### Step 2: Modify imx_tty_init()

After successful PTY creation (around line 334):
```c
printf("[TTY] Created pseudo-terminal - connect using: %s\r\n", slave_name);

// Create well-known symlink
if (imx_tty_create_symlink() == IMX_SUCCESS) {
    printf("[TTY] Symlink created: %s -> %s\r\n", IMX_TTY_SYMLINK_PATH, slave_name);
    printf("[TTY] Connect using: microcom %s\r\n", IMX_TTY_SYMLINK_PATH);
}
```

#### Step 3: Modify imx_tty_deinit()

Before closing the PTY, remove the symlink:
```c
// Remove symlink if we created one
if (tty_state.created_pty) {
    unlink(IMX_TTY_SYMLINK_PATH);
}
```

#### Step 4: Update Details File Location and Content

In `write_fc1_details_file()`:
```c
// Ensure directory exists
mkdir("/usr/qk/etc/sv/FC-1", 0755);

FILE *fp = fopen("/usr/qk/etc/sv/FC-1/FC-1_details.txt", "w");
// ...
fprintf(fp, "PTY Device: %s\n", tty_status.device_name);
fprintf(fp, "Console Symlink: /usr/qk/etc/sv/FC-1/console\n");
fprintf(fp, "Connect using: microcom /usr/qk/etc/sv/FC-1/console\n");
```

---

## Todo List

- [ ] Add `IMX_FC1_DIR` and `IMX_TTY_SYMLINK_PATH` constants to `imx_linux_tty.h`
- [ ] Add `imx_tty_create_symlink()` function declaration to header
- [ ] Implement `imx_tty_create_symlink()` in `imx_linux_tty.c`
- [ ] Modify `imx_tty_init()` to create symlink after PTY creation
- [ ] Modify `imx_tty_deinit()` to remove symlink on cleanup
- [ ] Update `write_fc1_details_file()` to write to `/usr/qk/etc/sv/FC-1/FC-1_details.txt`
- [ ] Update `write_fc1_details_file()` to show symlink path
- [ ] Build and verify no compile errors
- [ ] Test on target device

---

## Testing Plan

1. **SSH into FC-1 device** (per ssh_access_to_Fleet_Connect.md)
2. **Start FC-1 application** and observe:
   - PTY device creation message
   - Symlink creation message showing `/usr/qk/etc/sv/FC-1/console`
3. **Verify directory exists:** `ls -la /usr/qk/etc/sv/FC-1/`
4. **Verify symlink exists:** `ls -la /usr/qk/etc/sv/FC-1/console`
5. **Connect using symlink:** `microcom /usr/qk/etc/sv/FC-1/console`
6. **Verify CLI access** - should see FC-1 CLI interface
7. **Restart FC-1** and verify symlink is updated to new PTY
8. **Verify details file:** `cat /usr/qk/etc/sv/FC-1/FC-1_details.txt`

---

## User Experience Impact

### Before (Current)
```
[TTY] Created pseudo-terminal - connect using: /dev/pts/3
[TTY] Example: microcom /dev/pts/3
```
- User must note the PTY number each time FC-1 starts
- Details file at `/root/FC-1_details.txt`

### After (Proposed)
```
[TTY] Created pseudo-terminal: /dev/pts/3
[TTY] Symlink created: /usr/qk/etc/sv/FC-1/console -> /dev/pts/3
[TTY] Connect using: microcom /usr/qk/etc/sv/FC-1/console
```
- User always uses `microcom /usr/qk/etc/sv/FC-1/console` regardless of actual PTY number
- Details file at `/usr/qk/etc/sv/FC-1/FC-1_details.txt`
- All FC-1 related files in one consolidated location

---

## Summary of Changes

| Item | Before | After |
|------|--------|-------|
| Console Access | `microcom /dev/pts/X` (variable) | `microcom /usr/qk/etc/sv/FC-1/console` (fixed) |
| Details File | `/root/FC-1_details.txt` | `/usr/qk/etc/sv/FC-1/FC-1_details.txt` |
| Symlink Location | N/A | `/usr/qk/etc/sv/FC-1/console` |

---

**Plan Created By:** Claude Code
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/use_pts_7_for_FC-1.yaml
**Generated:** 2025-12-30
**Last Updated:** 2025-12-30
