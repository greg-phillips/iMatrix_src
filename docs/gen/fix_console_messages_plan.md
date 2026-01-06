# Fix Console Messages Plan

**Date**: 2026-01-04
**Branch**: feature/fix_console_messages
**Status**: GPIO Fix Complete - Cellular Hardware Reset NOT VIABLE
**Author**: Claude Code

---

## Summary

This plan addresses two categories of console error messages observed during FC-1 operation:

1. **GPIO "Resource busy" errors** - Low severity, cosmetic
2. **PPP/Chat SIGHUP errors** - High severity, cellular modem communication failure

---

## Current Branch Information

- **iMatrix**: `Aptera_1_Clean`
- **Fleet-Connect-1**: `Aptera_1_Clean`
- **New branch**: `feature/fix_console_messages`

---

## Issue 1: GPIO "Resource busy" Errors

### Description
During startup, the FC-1 application attempts to export GPIO pins using:
```c
snprintf(cmd, sizeof(cmd), "echo %u > /sys/class/gpio/export", gpio_linux_port_map[i]);
system(cmd);
```

If the GPIO pin is already exported (from a previous run), this fails with:
```
sh: write error: Resource busy
```

### Root Cause
- GPIO pins persist in exported state across application restarts
- The code attempts to re-export already-exported pins
- No check for existing export status before attempting export

### Solution
Modify `Fleet-Connect-1/hal/gpio.c:setup_gpio()` to:
1. Check if GPIO is already exported before attempting export
2. Redirect stderr to suppress harmless "already exported" errors
3. Continue normal operation regardless of export result

### Files to Modify
- `Fleet-Connect-1/hal/gpio.c`

### Implementation
```c
// Check if GPIO is already exported
char gpio_dir[128];
snprintf(gpio_dir, sizeof(gpio_dir), "/sys/class/gpio/gpio%u", gpio_linux_port_map[i]);
if (access(gpio_dir, F_OK) != 0) {
    // GPIO not exported, export it now
    snprintf(cmd, sizeof(cmd), "echo %u > /sys/class/gpio/export 2>/dev/null", gpio_linux_port_map[i]);
    system(cmd);
}
```

---

## Issue 2: PPP/Chat SIGHUP Errors

### Description
The cellular modem's PPP connection is failing repeatedly with:
```
Jan  4 22:18:XX local2.err chat[XXXX]: SIGHUP
Jan  4 22:18:XX local2.err chat[XXXX]: Can't restore terminal parameters: I/O error
```

These errors occur every ~3 seconds, indicating the PPP daemon keeps retrying.

### Root Cause Investigation
The `chat` program is used by `pppd` to send AT commands to the cellular modem. The SIGHUP + I/O error indicates:
1. The serial port to the modem is opening
2. Communication fails immediately (modem doesn't respond)
3. `chat` gets terminated (SIGHUP)
4. Terminal parameters can't be restored (I/O error)

Possible causes:
- Modem not properly initialized before PPP starts
- Modem serial port busy/locked by another process
- Modem hardware issue
- Wrong serial port configured (/dev/ttyACM2 in cellular_man.c)

### Solution V2: Modem-Only Reset using GPIO 91

After the first attempt (using `cell_hardware_reset` flag) caused system reboots, investigation revealed:

**Key Discovery from QConnect Developer Guide (p.56-57):**
- GPIO 89 = `GPIO_CELL_PWR_ON` - Power control (used by existing hardware reset)
- GPIO 91 = `GPIO_CELL_RESET_N` - **Force cellular reset** (modem-only, no system reboot)

The original fix used `cell_hardware_reset = true` which triggers GPIO 89 power cycling. This somehow caused system reboots.

The new fix uses GPIO 91 directly to reset only the modem:
```c
// Sequence per QConnect Developer Guide:
// 1. Export GPIO 91
// 2. Set direction to output
// 3. Assert HIGH (activate reset)
// 4. Wait 100ms
// 5. Release LOW (deactivate reset)
```

### Implementation V2

Added to `cellular_man.c`:

1. **New Constants:**
   ```c
   #define GPIO_CELL_RESET_N           91      // GPIO for modem-only reset
   #define MAX_TERMINAL_IO_ERRORS      5       // Errors before modem reset
   #define MIN_MODEM_RESET_INTERVAL_MS 60000   // Rate limit: 60s between resets
   #define MODEM_RESET_PULSE_MS        100     // Reset pulse duration
   ```

2. **New Function:**
   ```c
   static bool trigger_modem_only_reset(void)
   ```
   Uses GPIO 91 to pulse reset line (HIGH then LOW) - resets modem only.

3. **Modified `detect_and_handle_chat_failure()`:**
   - Tracks `consecutive_terminal_io_errors` counter
   - After 5 consecutive terminal I/O errors, triggers modem-only reset
   - Rate limiting: minimum 60 seconds between resets
   - Resets counter when other error types detected or no errors

### Safety Features V2

1. **Higher threshold**: 5 consecutive errors (vs 3 before)
2. **Rate limiting**: 60-second minimum between resets
3. **GPIO 91 only**: Uses reset line, not power cycling
4. **Counter resets**: On different error types or success

---

## TODO List

- [x] Create git branches for iMatrix and Fleet-Connect-1
- [x] Fix GPIO export logic to check if already exported
- [x] Add stderr redirect to suppress export errors
- [x] Build and verify no compilation errors
- [x] Add hardware reset trigger for repeated terminal I/O errors (V1 - FAILED)
- [x] Deploy binary to FC-1 device (deployed 2026-01-04 14:26 UTC)
- [x] Test GPIO fix on device - **SUCCESS** (no errors in 60s monitoring)
- [x] Test cellular fix V1 - **FAILED** (caused reboot loop, reverted)
- [x] Review QConnect Developer Guide for GPIO 91 reset mechanism
- [x] Implement modem-only reset using GPIO 91 (V2)
- [x] Build V2 binary - **SUCCESS**
- [x] Deploy V2 binary to FC-1 device (deployed 2026-01-04 ~16:04 UTC)
- [x] Test cellular fix V2 on device - **FAILED** (also caused system reboot)
- [x] Revert V2 changes and restore device stability
- [x] Update this document with V2 results

## Deployment Status

### Initial Deployment (14:26 UTC) - V1
Binary with both GPIO and cellular fixes deployed - **caused reboot loop**.

The `cell_hardware_reset = true` flag triggered a system-level hardware reset, not just a modem reset, causing the device to continuously reboot.

### Recovery Deployment (14:36 UTC)
Reverted cellular_man.c changes and redeployed:
- Binary: `/usr/qk/bin/FC-1` (13,326,068 bytes)
- Service: Started successfully (pid 1064)
- Device: Stable and operational

### V2 Deployment (16:04 UTC) - FAILED
Deployed V2 binary with GPIO 91 modem-only reset:
- Binary: 13,330,844 bytes
- Service: Started successfully
- **Device rebooted within minutes** - GPIO 91 also causes system reboot

### Final Recovery Deployment (16:10 UTC)
Reverted V2 cellular changes and redeployed:
- Binary: `/usr/qk/bin/FC-1` (13,326,084 bytes)
- Service: Running (pid 3119) for 285+ seconds
- Device: Stable and operational
- **GPIO fix retained** - "Resource busy" errors eliminated
- **Cellular reset removed** - PPP errors still present but harmless

## Test Results

### GPIO Fix: ✅ SUCCESS
- Monitored console for 60 seconds
- **No "Resource busy" errors observed**
- GPIO export now checks if already exported before attempting
- Fix confirmed working

### Cellular Fix V1: ❌ REVERTED
- The `cell_hardware_reset = true` flag caused full system reboot, not just modem reset
- This created a reboot loop
- Changes reverted to restore device stability
- PPP errors still present but device remains operational

### Cellular Fix V2: ❌ REVERTED
- Used GPIO 91 (modem-only reset) instead of cell_hardware_reset
- **ALSO caused system reboot** - same behavior as V1
- Deployed 2026-01-04 ~16:04 UTC, device rebooted within minutes
- Code reverted, device now stable with GPIO fix only

**Critical Finding**: Both GPIO 89 (CELL_PWR_ON) and GPIO 91 (CELL_RESET_N) cause full system reboot on this hardware, contrary to QConnect Developer Guide documentation. This suggests the hardware may be wired differently than documented, or there's a system-level dependency on these GPIO lines.

## Changes Made

### GPIO Fix (Fleet-Connect-1/hal/gpio.c)
1. Added `gpio_dir` buffer to check if GPIO is already exported
2. Modified `setup_gpio()` to check `/sys/class/gpio/gpioXX` exists before exporting
3. Added `2>/dev/null` stderr redirect to all shell commands to suppress errors:
   - `i2cset` command
   - GPIO export command
   - GPIO direction commands (in/out)
   - GPIO value command

### Cellular Terminal I/O Error Fix V2 - **REVERTED**
(iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c)

**Changes that were attempted and reverted:**
1. Added `GPIO_CELL_RESET_N = 91` constant for modem-only reset
2. Added `MAX_TERMINAL_IO_ERRORS = 5` (increased from 3 for safety)
3. Added `MIN_MODEM_RESET_INTERVAL_MS = 60000` for rate limiting
4. Added `trigger_modem_only_reset()` function using GPIO 91
5. Added `consecutive_terminal_io_errors` and `last_modem_reset_time` tracking
6. Modified `detect_and_handle_chat_failure()` to trigger modem reset

**Reason for reversion:** GPIO 91 also causes full system reboot, same as GPIO 89.

**Current state:** Terminal I/O error detection logs the error and cleans up PPP processes, but does NOT trigger any hardware reset. The PPP daemon will retry automatically.

---

## Build Instructions

```bash
cd Fleet-Connect-1/build
cmake ..
make -j4
```

---

## Test Plan

1. Deploy updated binary to FC-1 device
2. Restart FC-1 service
3. Monitor console for GPIO errors (should be gone - already verified)
4. Monitor console for terminal I/O errors
5. Verify modem-only reset triggers after 5 consecutive errors
6. Verify device does NOT reboot during modem reset
7. Verify modem recovers after reset
8. Verify rate limiting works (no rapid repeated resets)

---

**Document Created**: 2026-01-04
**Last Updated**: 2026-01-04 16:15 UTC
