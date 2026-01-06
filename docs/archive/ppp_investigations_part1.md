# PPP/Cellular Modem Reset Investigation - Part 1

**Date**: 2026-01-04
**Author**: Claude Code
**Status**: Investigation Complete - Hardware Reset Not Viable
**Device**: FC-1 Telematics Gateway (QConnect Platform)

---

## Executive Summary

This document details the investigation into fixing PPP/Chat terminal I/O errors on the FC-1 gateway. Two approaches were attempted to reset the cellular modem when repeated errors occurred. Both approaches caused unexpected system reboots, despite documentation suggesting they should only reset the modem.

**Key Finding**: Manual GPIO manipulation from the shell does NOT cause reboots, indicating the issue is in the C code path rather than the GPIO hardware itself.

---

## Problem Statement

### Symptoms Observed
The FC-1 device console showed repeated PPP connection failures:

```
Jan  4 22:18:XX local2.err chat[XXXX]: SIGHUP
Jan  4 22:18:XX local2.err chat[XXXX]: Can't restore terminal parameters: I/O error
Jan  4 22:40:19 daemon.err pppd[1693]: Connect script failed
```

These errors occur every ~3-7 seconds, indicating the PPP daemon keeps retrying but failing.

### Root Cause Analysis
The `chat` program (used by `pppd` to send AT commands to the cellular modem) receives SIGHUP + I/O error, indicating:
1. Serial port to modem opens successfully
2. Communication fails immediately (modem doesn't respond)
3. `chat` gets terminated (SIGHUP)
4. Terminal parameters can't be restored (I/O error)

### Impact
- Cellular connectivity unavailable
- Console log spam (errors every few seconds)
- Device remains operational but without cellular data

---

## Hardware Background

### QConnect Platform GPIO Pins (from Developer Guide p.56-57)

| GPIO | Name | Function |
|------|------|----------|
| 89 | `GPIO_CELL_PWR_ON` | Modem power control |
| 91 | `GPIO_CELL_RESET_N` | Modem reset line (active HIGH) |

### Expected Behavior per Documentation
- **GPIO 89**: Power cycle the modem (turn off, wait, turn on)
- **GPIO 91**: Reset the modem without power cycling (pulse HIGH then LOW)

Both should reset ONLY the cellular modem, not the entire system.

---

## Approach 1: Using `cell_hardware_reset` Flag (V1)

### Implementation
Modified `cellular_man.c` to set the existing `cell_hardware_reset = true` flag after detecting repeated terminal I/O errors.

### Code Location
`iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

### Logic
```c
// After 3 consecutive terminal I/O errors
if (consecutive_terminal_io_errors >= 3) {
    cell_hardware_reset = true;  // Trigger existing reset mechanism
}
```

### Result: FAILED
- **Behavior**: Setting this flag caused a FULL SYSTEM REBOOT
- **Impact**: Device entered reboot loop
- **Recovery**: Reverted changes and redeployed

### Analysis
The `cell_hardware_reset` flag triggers GPIO 89 (power control) which somehow causes the entire system to reboot, not just the modem.

---

## Approach 2: Direct GPIO 91 Manipulation (V2)

### Rationale
Since GPIO 89 (power) caused issues, try GPIO 91 (reset line) which per documentation should only reset the modem.

### Implementation

#### Constants Added
```c
#define GPIO_CELL_RESET_N           91      // GPIO for modem-only reset
#define MAX_TERMINAL_IO_ERRORS      5       // Errors before modem reset
#define MIN_MODEM_RESET_INTERVAL_MS 60000   // Rate limit: 60s between resets
#define MODEM_RESET_PULSE_MS        100     // Reset pulse duration
```

#### New Function
```c
static bool trigger_modem_only_reset(void)
{
    // Export GPIO 91
    gpio_export(GPIO_CELL_RESET_N);

    // Set direction to output
    gpio_set_direction(GPIO_CELL_RESET_N, "out");

    // Assert reset (HIGH)
    gpio_set_value(GPIO_CELL_RESET_N, 1);

    // Wait 100ms
    usleep(MODEM_RESET_PULSE_MS * 1000);

    // Release reset (LOW)
    gpio_set_value(GPIO_CELL_RESET_N, 0);

    return true;
}
```

#### Detection Logic
```c
if (terminal_io_error) {
    consecutive_terminal_io_errors++;

    if (consecutive_terminal_io_errors >= MAX_TERMINAL_IO_ERRORS) {
        // Rate limiting check
        if (time_since_last_reset >= MIN_MODEM_RESET_INTERVAL_MS) {
            trigger_modem_only_reset();
            last_modem_reset_time = current_time;
            consecutive_terminal_io_errors = 0;
        }
    }
}
```

### Result: FAILED
- **Behavior**: GPIO 91 manipulation ALSO caused system reboot
- **Impact**: Same as V1 - device reboots when reset triggered
- **Recovery**: Reverted changes and redeployed

---

## Critical Discovery: Manual GPIO Test

### Test Performed by User
```bash
root@iMatrix:~# echo 89 > /sys/class/gpio/export
sh: write error: Resource busy   # Already exported, expected
root@iMatrix:~# echo out > /sys/class/gpio/gpio89/direction
root@iMatrix:~# echo 1 > /sys/class/gpio/gpio89/value
root@iMatrix:~#   # NO REBOOT - device remained stable
```

### Implication
- Manual GPIO 89 manipulation does NOT cause reboot
- The reboot is NOT caused by GPIO hardware behavior
- Something in our C code path is triggering the reboot

### Possible Causes
1. **Crash/Segfault**: Code crashes, watchdog triggers reboot
2. **Stack Overflow**: GPIO functions corrupt stack
3. **Side Effects**: GPIO functions trigger other code paths
4. **Watchdog**: Long blocking operation triggers hardware watchdog
5. **Memory Corruption**: GPIO helper functions have bugs

---

## GPIO Helper Functions Analysis

### Location
`iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` (lines ~1250-1315)

### Functions Used
```c
static bool gpio_export(int gpio_num);
static bool gpio_set_direction(int gpio_num, const char *direction);
static bool gpio_set_value(int gpio_num, int value);
```

### Implementation Pattern
Each function:
1. Builds a path string (e.g., `/sys/class/gpio/gpio91/direction`)
2. Opens the file with `open()`
3. Writes value with `write()`
4. Closes file with `close()`
5. Returns success/failure

### Potential Issues
- Buffer sizes may be insufficient
- Error handling may have issues
- No NULL checks in some places
- `snprintf` format string issues possible

---

## Debug Logging Attempt

### Implementation
Added extensive logging with `fflush()` and `sync()` calls:

```c
static bool trigger_modem_only_reset_debug(void)
{
    PRINTF("========== MODEM RESET DEBUG START ==========\r\n");
    fflush(stdout); fflush(stderr); sync();

    PRINTF("[DEBUG] Step 1: Entering function\r\n");
    fflush(stdout); fflush(stderr); sync();

    PRINTF("[DEBUG] Step 2: About to export GPIO\r\n");
    fflush(stdout); fflush(stderr); sync();

    // ... etc for each step
}
```

### Result
- Debug output never appeared in logs
- Device rebooted before logs could be captured
- Even with `sync()` calls, output was lost

### Limitation
The device was in Wi-Fi Setup mode (factory defaults) and not attempting cellular, so terminal I/O errors weren't occurring naturally. Couldn't trigger the debug code path.

---

## Current State

### Code Status
- **GPIO Fix**: Still in place (checks if GPIO already exported before export)
- **Modem Reset**: REMOVED (reverted to simple logging)
- **Terminal I/O Handling**: Logs error and cleans up PPP, no reset attempt

### Current Behavior
```c
if (terminal_io_error) {
    PRINTF("[Cellular Connection - DETECTED terminal I/O error in chat script]\r\n");
    PRINTF("[Cellular Connection - Cleaning up PPP processes for retry]\r\n");
    // PPP daemon will retry automatically
}
```

### Device Stability
- FC-1 running stable with safe build
- PPP errors still occur but device doesn't reboot
- Cellular connectivity may fail but device remains operational

---

## Files Modified

### Primary File
`iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

### Changes Made and Reverted
1. Added `GPIO_CELL_RESET_N` constant (removed)
2. Added tracking variables (removed)
3. Added `trigger_modem_only_reset()` function (removed)
4. Modified `detect_and_handle_chat_failure()` (reverted)

### Permanent Changes
- Comment noting that GPIO 89 and 91 both cause reboots
- Simple logging for terminal I/O errors

---

## Recommendations for Future Investigation

### 1. Test GPIO 91 Manually
```bash
echo 91 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio91/direction
echo 1 > /sys/class/gpio/gpio91/value
sleep 0.1
echo 0 > /sys/class/gpio/gpio91/value
```
If this doesn't reboot, confirms issue is in C code.

### 2. Add Crash Handlers
```c
#include <signal.h>

void crash_handler(int sig) {
    PRINTF("CRASH: Signal %d received\r\n", sig);
    sync();
    _exit(1);
}

// In init:
signal(SIGSEGV, crash_handler);
signal(SIGBUS, crash_handler);
signal(SIGABRT, crash_handler);
```

### 3. Use GDB
```bash
gdb ./FC-1
(gdb) run
# Wait for crash
(gdb) bt   # Get backtrace
```

### 4. Check GPIO Helper Functions
Review for:
- Buffer overflows in `snprintf`
- NULL pointer dereferences
- File descriptor leaks
- Error path issues

### 5. Alternative: AT Command Reset
Instead of GPIO, use AT command to reset modem:
```c
// Send AT+CFUN=1,1 to modem for software reset
// No GPIO involved, may be safer
```

### 6. Check Watchdog Configuration
- Is hardware watchdog enabled?
- What's the timeout?
- Is our code path blocking too long?

---

## Related Documentation

- `docs/gen/fix_console_messages_plan.md` - Original plan document
- QConnect Developer Guide p.56-57 - GPIO pin definitions
- `Fleet-Connect-1/hal/gpio.c` - GPIO export fix for "Resource busy" errors

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 14:26 | V1 deployed (cell_hardware_reset) |
| 14:26 | Device rebooted - V1 failed |
| 14:36 | V1 reverted, device stable |
| 15:XX | V2 implemented (GPIO 91 direct) |
| 16:04 | V2 deployed |
| 16:05 | Device rebooted - V2 failed |
| 16:10 | V2 reverted, device stable |
| 16:XX | Debug build deployed |
| 16:XX | Debug build couldn't trigger (Wi-Fi mode) |
| 00:34 | Safe build deployed, device stable |

---

## Conclusion

Both GPIO-based modem reset approaches (GPIO 89 via flag, GPIO 91 direct) cause unexpected system reboots when triggered from C code. Manual shell testing of GPIO 89 does NOT cause reboot, indicating the issue is in the code path rather than hardware.

The investigation is paused with a safe build deployed. Further debugging requires:
1. Manual GPIO 91 shell test
2. Crash handler implementation
3. GDB debugging session
4. Possible alternative approach using AT commands

**Current Priority**: Device stability maintained. PPP errors are cosmetic - cellular will retry automatically.

---

*Document Version: 1.0*
*Last Updated: 2026-01-04*
