# Plan: Cellular Modem Hardware Reset on Serial Port Error

**Date**: 2025-11-25
**Time**: 08:30 PST
**Status**: Draft
**Author**: Claude Code Analysis

---

## Problem Statement

When a `cell scan` command is issued while PPP is connected, the following failure sequence occurs:

1. Scan stops PPP correctly
2. AT+COPS=? scan completes successfully
3. PPP restarts but fails with "Connect script failed"
4. Serial port becomes unusable: `[ERROR] write() AT failed: I/O error (errno=5)`
5. `/dev/ttyACM0` disappears: `Failed to open /dev/ttyACM0: No such file or directory`
6. System stuck - no recovery mechanism

**Root Cause**: The modem USB interface becomes unstable and needs a hardware power cycle to recover.

---

## Proposed Solution

Add a hardware modem reset capability using **GPIO 89** (Cell Power On) to power cycle the modem when serial port errors are detected.

### Hardware Reset Sequence (from Quake documentation)

```bash
# Modem Power Cycle Sequence
echo 89 > /sys/class/gpio/export           # Export GPIO 89
echo out > /sys/class/gpio/gpio89/direction # Set as output
echo 0 > /sys/class/gpio/gpio89/value       # Set LOW (prepare)
sleep 1                                      # Wait
echo 1 > /sys/class/gpio/gpio89/value       # Set HIGH (power on pulse)
sleep 1                                      # Hold
echo 0 > /sys/class/gpio/gpio89/value       # Set LOW (complete)
sleep 10                                     # Wait for modem boot
# ttyACM0-4 should reappear
```

### Port Assignment Reference
| Port | Usage |
|------|-------|
| ttyACM0 | PPPD |
| ttyACM1 | qsvc_terr (Quake Service) |
| ttyACM2 | Available for AT commands |
| ttyACM3 | Available (PLS-63 only) |

---

## Implementation Plan

### Phase 1: Add GPIO Control Functions

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

#### 1.1 Add Constants and State
```c
// Add near top of file with other defines
#define GPIO_CELL_PWR_ON        89
#define GPIO_SYSFS_PATH         "/sys/class/gpio"
#define MODEM_BOOT_WAIT_SECONDS 10
#define MAX_SERIAL_ERRORS       3

// Add new state for hardware reset
// In cellular_states_t enum:
CELL_HARDWARE_RESET,
CELL_WAIT_MODEM_BOOT,

// Add tracking variable
static int serial_error_count = 0;
static bool modem_needs_hard_reset = false;
```

#### 1.2 Add GPIO Helper Functions
```c
/**
 * @brief Export and configure GPIO pin
 * @param gpio_num GPIO number to export
 * @param direction "in" or "out"
 * @return true on success, false on failure
 */
static bool gpio_export_and_configure(int gpio_num, const char *direction)
{
    char path[128];
    FILE *fp;

    // Check if already exported
    snprintf(path, sizeof(path), "%s/gpio%d/direction", GPIO_SYSFS_PATH, gpio_num);
    if (access(path, F_OK) != 0) {
        // Export GPIO
        snprintf(path, sizeof(path), "%s/export", GPIO_SYSFS_PATH);
        fp = fopen(path, "w");
        if (!fp) {
            PRINTF("[Cellular Reset] Failed to export GPIO %d\r\n", gpio_num);
            return false;
        }
        fprintf(fp, "%d", gpio_num);
        fclose(fp);
        usleep(100000); // Wait for sysfs to create files
    }

    // Set direction
    snprintf(path, sizeof(path), "%s/gpio%d/direction", GPIO_SYSFS_PATH, gpio_num);
    fp = fopen(path, "w");
    if (!fp) {
        PRINTF("[Cellular Reset] Failed to set GPIO %d direction\r\n", gpio_num);
        return false;
    }
    fprintf(fp, "%s", direction);
    fclose(fp);

    return true;
}

/**
 * @brief Set GPIO value
 * @param gpio_num GPIO number
 * @param value 0 or 1
 * @return true on success, false on failure
 */
static bool gpio_set_value(int gpio_num, int value)
{
    char path[128];
    FILE *fp;

    snprintf(path, sizeof(path), "%s/gpio%d/value", GPIO_SYSFS_PATH, gpio_num);
    fp = fopen(path, "w");
    if (!fp) {
        PRINTF("[Cellular Reset] Failed to write GPIO %d value\r\n", gpio_num);
        return false;
    }
    fprintf(fp, "%d", value);
    fclose(fp);

    return true;
}
```

#### 1.3 Add Hardware Reset Function
```c
/**
 * @brief Perform hardware power cycle of cellular modem
 * @return true if reset sequence completed, false on failure
 *
 * This function uses GPIO 89 to power cycle the Cinterion PLS63 modem.
 * After reset, ttyACM0-4 will reappear when modem boots.
 */
bool cellular_hardware_reset(void)
{
    PRINTF("[Cellular Reset] Initiating hardware power cycle via GPIO %d\r\n", GPIO_CELL_PWR_ON);

    // Close serial port before reset
    extern int cell_fd;
    if (cell_fd != -1) {
        close(cell_fd);
        cell_fd = -1;
        PRINTF("[Cellular Reset] Closed serial port fd\r\n");
    }

    // Stop any running PPP
    system("sv down pppd 2>/dev/null");
    system("killall -9 pppd 2>/dev/null");
    usleep(500000);

    // Export and configure GPIO
    if (!gpio_export_and_configure(GPIO_CELL_PWR_ON, "out")) {
        PRINTF("[Cellular Reset] Failed to configure GPIO\r\n");
        return false;
    }

    // Power cycle sequence
    PRINTF("[Cellular Reset] Setting GPIO LOW (prepare)\r\n");
    if (!gpio_set_value(GPIO_CELL_PWR_ON, 0)) return false;
    sleep(1);

    PRINTF("[Cellular Reset] Setting GPIO HIGH (power pulse)\r\n");
    if (!gpio_set_value(GPIO_CELL_PWR_ON, 1)) return false;
    sleep(1);

    PRINTF("[Cellular Reset] Setting GPIO LOW (complete)\r\n");
    if (!gpio_set_value(GPIO_CELL_PWR_ON, 0)) return false;

    PRINTF("[Cellular Reset] Waiting %d seconds for modem boot\r\n", MODEM_BOOT_WAIT_SECONDS);
    // Note: Actual wait happens in state machine to avoid blocking

    serial_error_count = 0;
    modem_needs_hard_reset = false;

    return true;
}

/**
 * @brief Check if ttyACM0 device exists (modem enumerated)
 * @return true if device exists
 */
bool is_modem_enumerated(void)
{
    return (access("/dev/ttyACM0", F_OK) == 0);
}
```

---

### Phase 2: Add Error Detection and State Machine Updates

#### 2.1 Modify `send_at_command()` to Track Errors

In the existing `send_at_command()` function, after detecting write failure:

```c
// After: PRINTF("[ERROR] write() AT failed: %s (errno=%d)\r\n", strerror(errno), errno);
serial_error_count++;
PRINTF("[Cellular Connection - Serial error count: %d/%d]\r\n",
       serial_error_count, MAX_SERIAL_ERRORS);
if (serial_error_count >= MAX_SERIAL_ERRORS) {
    modem_needs_hard_reset = true;
    PRINTF("[Cellular Connection - Too many serial errors, requesting hardware reset]\r\n");
}
```

#### 2.2 Add New States to State Machine

Add to `cellular_states_t` enum (around line 165):
```c
CELL_HARDWARE_RESET = 39,      // Perform GPIO power cycle
CELL_WAIT_MODEM_BOOT = 40,     // Wait for modem to re-enumerate
```

Add to state name array:
```c
"HARDWARE_RESET",
"WAIT_MODEM_BOOT",
```

#### 2.3 Add State Handlers in Main Loop

In `process_cellular()` switch statement:

```c
case CELL_HARDWARE_RESET:
    if (cellular_hardware_reset()) {
        hardware_reset_start_time = current_time;
        cellular_state = CELL_WAIT_MODEM_BOOT;
        PRINTF("[Cellular Connection - Hardware reset initiated, waiting for modem]\r\n");
    } else {
        PRINTF("[Cellular Connection - Hardware reset failed, retrying in 30s]\r\n");
        // Set delay and retry
        cellular_state = CELL_DELAY;
        delay_time = 30000;
        return_cellular_state = CELL_HARDWARE_RESET;
    }
    break;

case CELL_WAIT_MODEM_BOOT:
    if (is_modem_enumerated()) {
        PRINTF("[Cellular Connection - Modem re-enumerated, reinitializing]\r\n");
        cellular_state = CELL_INIT;
        serial_error_count = 0;
    } else if (imx_is_later(current_time, hardware_reset_start_time + (MODEM_BOOT_WAIT_SECONDS * 1000))) {
        PRINTF("[Cellular Connection - Modem boot timeout, retrying reset]\r\n");
        cellular_state = CELL_HARDWARE_RESET;
    }
    // Otherwise keep waiting
    break;
```

#### 2.4 Add Trigger Points for Hardware Reset

**Location 1**: In `CELL_INIT` state, check if hardware reset needed:
```c
case CELL_INIT:
    // Check if hardware reset was requested
    if (modem_needs_hard_reset) {
        cellular_state = CELL_HARDWARE_RESET;
        break;
    }
    // ... existing CELL_INIT code
```

**Location 2**: After serial port open failure:
```c
cell_fd = open_serial_port(CELLULAR_SERIAL_PORT);
if (cell_fd == -1) {
    serial_error_count++;
    if (serial_error_count >= MAX_SERIAL_ERRORS || !is_modem_enumerated()) {
        PRINTF("[Cellular Connection - Serial port unavailable, requesting hardware reset]\r\n");
        modem_needs_hard_reset = true;
    }
    // ... existing error handling
}
```

**Location 3**: In scan failure state `CELL_SCAN_FAILED`:
```c
case CELL_SCAN_FAILED:
    if (modem_needs_hard_reset) {
        PRINTF("[Cellular Scan - Hardware reset required due to serial errors]\r\n");
        cellular_state = CELL_HARDWARE_RESET;
        break;
    }
    // ... existing scan failed handling
```

---

### Phase 3: Add CLI Command for Manual Reset

**File**: `iMatrix/cli/cli_net_cell.c`

Add new subcommand:

```c
// In cell command handler, add case for "reset":
else if (strcmp(argv[1], "reset") == 0) {
    if (argc > 2 && strcmp(argv[2], "hard") == 0) {
        imx_cli_print("Initiating hardware modem reset...\r\n");
        extern bool modem_needs_hard_reset;
        modem_needs_hard_reset = true;
        // Force state machine to process
        extern CellularState_t cellular_state;
        cellular_state = CELL_HARDWARE_RESET;
    } else {
        // Existing soft reset (AT+CFUN=1,1)
        imx_cli_print("Initiating soft modem reset (AT+CFUN=1,1)...\r\n");
        // ... existing code
    }
}
```

Update help text:
```c
"  reset      - Soft reset cellular modem (AT+CFUN=1,1)\r\n"
"  reset hard - Hardware power cycle modem (GPIO)\r\n"
```

---

### Phase 4: Add Logging and Diagnostics

#### 4.1 Track Reset Statistics
```c
// Add statistics structure
typedef struct {
    uint32_t soft_reset_count;
    uint32_t hard_reset_count;
    uint32_t serial_error_total;
    imx_time_t last_hard_reset_time;
} cellular_reset_stats_t;

static cellular_reset_stats_t reset_stats = {0};
```

#### 4.2 Add to `cell status` Output
```c
imx_cli_print("  Soft Resets: %u, Hard Resets: %u, Serial Errors: %u\r\n",
              reset_stats.soft_reset_count,
              reset_stats.hard_reset_count,
              reset_stats.serial_error_total);
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c` | Add GPIO functions, new states, error tracking |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.h` | Add extern declarations if needed |
| `iMatrix/cli/cli_net_cell.c` | Add `cell reset hard` command |

---

## Testing Plan

### Test 1: Manual Hardware Reset
```bash
# At CLI:
cell reset hard
# Verify: Modem power cycles, ttyACM ports reappear, cellular reinitializes
```

### Test 2: Automatic Reset on Serial Errors
```bash
# Run scan while PPP connected
cell scan
# If serial errors occur, verify automatic hardware reset
# Look for: "[Cellular Reset] Initiating hardware power cycle"
```

### Test 3: Verify Recovery
```bash
# After hardware reset:
cell status
# Should show: Connected to carrier, PPP established
```

### Test 4: Log Verification
Look for log messages:
- `[Cellular Reset] Initiating hardware power cycle via GPIO 89`
- `[Cellular Reset] Setting GPIO HIGH (power pulse)`
- `[Cellular Reset] Waiting 10 seconds for modem boot`
- `[Cellular Connection - Modem re-enumerated, reinitializing]`

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| GPIO access fails | Log error and fall back to soft reset |
| Modem doesn't re-enumerate | Retry hardware reset up to 3 times |
| Blocking during reset | Use state machine for non-blocking waits |
| False positive errors | Require 3 consecutive errors before hard reset |

---

## Alternative Approaches Considered

### Option A: Soft Reset Only (AT+CFUN=1,1)
- **Pro**: No hardware control needed
- **Con**: Won't fix USB enumeration issues (the actual problem)

### Option B: System Reboot
- **Pro**: Guaranteed to reset everything
- **Con**: Too disruptive, loses all state

### Option C: USB Reset via sysfs
- **Pro**: Resets USB without full power cycle
- **Con**: May not fully reset modem firmware state

**Selected**: GPIO hardware reset - directly addresses root cause with minimal disruption.

---

## Implementation Order

1. Add GPIO helper functions
2. Add `cellular_hardware_reset()` function
3. Add error counting in `send_at_command()`
4. Add new states to enum and state machine
5. Add trigger points in CELL_INIT and CELL_SCAN_FAILED
6. Add CLI command `cell reset hard`
7. Test manual reset
8. Test automatic reset on errors
9. Verify full recovery cycle

---

## Success Criteria

1. Serial port errors trigger automatic hardware reset after 3 failures
2. Hardware reset successfully power cycles modem
3. ttyACM ports reappear within 15 seconds
4. Cellular connection re-establishes automatically
5. No manual intervention required for recovery
6. `cell reset hard` CLI command works for manual override

---

**End of Plan**
