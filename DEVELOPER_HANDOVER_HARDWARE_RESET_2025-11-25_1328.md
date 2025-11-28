# Developer Handover: Cellular Modem Hardware Reset Implementation

**Date**: 2025-11-25 13:28 PST
**Session**: Cellular Serial Port Recovery & Hardware Reset
**Status**: Plan Created - Implementation Pending
**Author**: Claude Code Analysis
**Handover To**: Next Developer

---

## Executive Summary

This document captures the analysis and implementation plan for adding hardware modem reset capability to the iMatrix cellular subsystem. The feature is needed to recover from serial port failures that occur when running `cell scan` while PPP is connected.

**Key Constraint**: The cellular_man state machine must be **non-blocking**. All delays must be implemented using state machine transitions with timer checks, not sleep() calls.

---

## Problem Analysis

### Issue Discovered in net19.txt

When `cell scan` is run while PPP is connected:

| Time | Event | Result |
|------|-------|--------|
| 00:00:21 | Verizon connected at power on | SUCCESS |
| 00:02:44 | `cell scan` command issued | TRIGGER |
| 00:05:55 | PPP restart after scan | FAILED |
| 00:06:08 | Serial port error | `write() AT failed: I/O error (errno=5)` |
| 00:06:12 | Device disappears | `Failed to open /dev/ttyACM0: No such file or directory` |
| 00:07:35+ | System stuck | No recovery mechanism |

### Root Cause

1. Scan stops PPP correctly
2. AT+COPS=? scan completes
3. PPP restarts but fails ("Connect script failed")
4. Serial port becomes corrupted (errno=5 - I/O error)
5. USB modem interface destabilizes, /dev/ttyACM0 disappears
6. **No recovery mechanism exists** - system stays stuck

### Solution Required

Add hardware modem reset via **GPIO 89** to power cycle the Cinterion PLS63 modem when serial port errors are detected.

---

## Hardware Information

### Modem Power Control

From Quake documentation:
```bash
# Cellular Bring-up Sequence using GPIO 89
echo 89 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio89/direction
echo 1 > /sys/class/gpio/gpio89/value   # Power on pulse
# Wait, then set back to 0
```

### Serial Ports After Reset

| Port | Usage |
|------|-------|
| ttyACM0 | PPPD |
| ttyACM1 | qsvc_terr (Quake Service) |
| ttyACM2 | Available for AT commands |
| ttyACM3 | Available (PLS-63 only) |

---

## Source Code Reference

### Primary Files

| File | Path | Purpose |
|------|------|---------|
| **cellular_man.c** | `iMatrix/IMX_Platform/LINUX_Platform/networking/` | Main cellular state machine - **MODIFY** |
| **cellular_blacklist.c** | `iMatrix/IMX_Platform/LINUX_Platform/networking/` | Blacklist management (timer bug fixed) |
| **cli_net_cell.c** | `iMatrix/cli/` | CLI commands - add `cell reset hard` |

### Key Code Locations in cellular_man.c

| Item | Line(s) | Description |
|------|---------|-------------|
| `cellular_states_t` enum | ~165-210 | State definitions - add new reset states |
| State name array | ~212-260 | String names for debug output |
| `cell_fd` variable | 551 | Serial port file descriptor |
| `open_serial_port()` | ~650 | Opens /dev/ttyACM0 |
| `send_at_command()` | ~719-745 | AT command with error detection |
| `CELL_DELAY` state | ~2475 | Non-blocking delay pattern |
| `CELL_INIT` state | ~2516-2545 | Initialization sequence |
| Scan states | ~3098-3284 | Multi-step non-blocking sequence example |

### Existing Non-Blocking Delay Pattern

```c
// Current pattern for delays (CELL_DELAY state):
case CELL_DELAY:
    if (imx_is_later(current_time, delay_start_time + delay_time)) {
        cellular_state = return_cellular_state;  // Continue to next state
    }
    // Otherwise, return and let main loop continue
    break;
```

### GPIO Reference Code

**File**: `iMatrix/external/Quake Source/lowlevel_sample/TERR/src/module.c`

```c
// Power on sequence (lines 55-84):
GPIO_valueSet(GPIO_CELL_RESET_N, GPIO_VAL_LO);  // Reset must be off
GPIO_valueSet(GPIO_CELL_PWR_ON, GPIO_VAL_LO);   // Prepare
sleep(GPIO_TOGGLE_WAIT_SECONDS);                 // 1 second
GPIO_valueSet(GPIO_CELL_PWR_ON, GPIO_VAL_HI);   // Power pulse
sleep(GPIO_TOGGLE_WAIT_SECONDS);                 // 1 second
GPIO_valueSet(GPIO_CELL_PWR_ON, GPIO_VAL_LO);   // Complete
sleep(TERR_BOOT_SECONDS);                        // Wait for boot (~10s)
```

---

## Implementation Plan

### New States Required (Non-Blocking)

```c
// Add to cellular_states_t enum:
CELL_HARDWARE_RESET_INIT = 39,      // Close port, stop PPP, export GPIO
CELL_HARDWARE_RESET_GPIO_LOW = 40,  // Set GPIO 89 LOW, start 1s timer
CELL_HARDWARE_RESET_GPIO_HIGH = 41, // Set GPIO 89 HIGH, start 1s timer
CELL_HARDWARE_RESET_GPIO_DONE = 42, // Set GPIO 89 LOW, start boot timer
CELL_HARDWARE_RESET_WAIT_BOOT = 43, // Wait for modem enumeration (10s max)
```

### State Machine Flow

```
Serial Error Detected (3x)
         |
         v
CELL_HARDWARE_RESET_INIT
  - Close cell_fd
  - Kill PPP
  - Export GPIO 89
  - Set timer: 100ms
         |
         v
CELL_HARDWARE_RESET_GPIO_LOW
  - Set GPIO 89 = 0
  - Set timer: 1000ms
         |
         v
CELL_HARDWARE_RESET_GPIO_HIGH
  - Set GPIO 89 = 1
  - Set timer: 1000ms
         |
         v
CELL_HARDWARE_RESET_GPIO_DONE
  - Set GPIO 89 = 0
  - Set timer: 10000ms (boot wait)
         |
         v
CELL_HARDWARE_RESET_WAIT_BOOT
  - Check if /dev/ttyACM0 exists
  - If yes → CELL_INIT
  - If timeout → retry or fail
         |
         v
CELL_INIT (normal startup)
```

### Error Detection Variables

```c
// Add to cellular_man.c:
#define MAX_SERIAL_ERRORS 3
#define GPIO_CELL_PWR_ON 89
#define MODEM_BOOT_WAIT_MS 10000

static int serial_error_count = 0;
static bool modem_needs_hard_reset = false;
static imx_time_t hardware_reset_timer = 0;
```

### GPIO Helper Functions

```c
static bool gpio_export(int gpio_num);
static bool gpio_set_direction(int gpio_num, const char *dir);
static bool gpio_set_value(int gpio_num, int value);
static bool is_modem_enumerated(void);  // Check /dev/ttyACM0 exists
```

---

## Documentation Reference

### Existing Documentation

| Document | Path | Content |
|----------|------|---------|
| **CELLULAR_MODEM_RESET_PLAN_2025-11-25_0830.md** | Root | Initial plan (has blocking sleeps - needs update) |
| **CELLULAR_BLACKLIST_DEBUG_HANDOVER_2025-11-25_0756.md** | Root | Blacklist timer bug fix (completed) |
| **DEVELOPER_HANDOVER_DOCUMENT.md** | Root | Previous cellular fixes overview |
| **net19.txt** | logs/ | Test log showing the serial port failure |
| **net18.txt** | logs/ | Test log showing blacklist issues |

### Test Logs Analysis

| Log | Finding |
|-----|---------|
| net19.txt:2071 | `Failed to open /dev/ttyACM0: No such file or directory` |
| net19.txt:2282 | `[ERROR] write() AT failed: I/O error (errno=5)` |
| net19.txt:1936 | `Connect script failed` after scan |

---

## Verification Checklist

After implementation:

1. [ ] `cell reset hard` CLI command works
2. [ ] Automatic reset triggers after 3 serial errors
3. [ ] GPIO 89 toggles correctly (can verify with scope or log)
4. [ ] /dev/ttyACM0-4 reappear after reset
5. [ ] Cellular reconnects automatically
6. [ ] No blocking delays in state machine
7. [ ] State transitions logged for debugging

### Expected Log Output

```
[Cellular Reset] Serial error count: 3/3
[Cellular Reset] Initiating hardware reset sequence
[Cellular Reset] State: INIT - Closing port, stopping PPP
[Cellular Reset] State: GPIO_LOW - Setting GPIO 89 LOW
[Cellular Reset] State: GPIO_HIGH - Setting GPIO 89 HIGH (power pulse)
[Cellular Reset] State: GPIO_DONE - Waiting for modem boot
[Cellular Reset] State: WAIT_BOOT - Checking for /dev/ttyACM0
[Cellular Reset] Modem enumerated, proceeding to CELL_INIT
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| GPIO access fails | Log error, retry, fall back to soft reset |
| Modem doesn't re-enumerate | Retry hardware reset up to 3 times |
| State machine blocks | Use timer-based transitions only |
| False positive errors | Require 3 consecutive errors |

---

## Next Steps for Developer

1. **Read** the existing state machine pattern in cellular_man.c (CELL_DELAY, scan states)
2. **Add** new states to the enum and state name array
3. **Implement** GPIO helper functions (non-blocking file I/O)
4. **Add** state handlers with timer-based transitions
5. **Add** error counting in send_at_command()
6. **Add** CLI command `cell reset hard`
7. **Test** with `cell scan` while PPP connected

---

## Previously Completed Work

### Blacklist Timer Bug (FIXED)

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_blacklist.c`

**Change**: Removed timer reset on re-blacklist (line ~184)
- Before: Timer reset on every re-blacklist attempt
- After: Timer preserved, only duration extended

This fix was applied and compilation verified.

---

## Contact

- Project docs: CLAUDE.md
- Issues: https://github.com/anthropics/claude-code/issues

---

**End of Handover Document**
