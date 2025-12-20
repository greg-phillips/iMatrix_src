# PRINTF_FRAME Debug Implementation Plan

**Date:** 2025-12-19
**Document Version:** 1.1
**Status:** Implementation Complete
**Author:** Claude Code
**Reviewer:** Greg
**Implementer:** Claude Code

---

## Summary

Add a new `DEBUGS_FOR_CAN_ETH_FRAME` debug flag to enable frame-level debugging of CAN frames received from the Ethernet interface. This will allow detailed inspection of:
1. Individual characters as they are received from the TCP stream
2. Complete parsed CAN frames

## Current Branch Status

| Submodule | Current Branch | New Feature Branch |
|-----------|----------------|-------------------|
| iMatrix | Aptera_1_Clean | feature/add_printf_frame_debug |
| Fleet-Connect-1 | Aptera_1_Clean | (no changes needed) |

## Files to Modify

### 1. iMatrix/cli/messages.h
- Add new enum value `DEBUGS_FOR_CAN_ETH_FRAME` after `DEBUGS_FOR_CAN_SERVER`
- Location: Line ~146 in the `DEBUGS_LOGS_COMPONENT_T` enum

### 2. iMatrix/cli/cli_debug.c
- Add description for the new flag in the `debug_flags_description` array
- Description: "Debugs for CAN Ethernet Frame parsing"

### 3. iMatrix/canbus/can_server.c
- Add new `PRINTF_FRAME` macro using the new debug flag
- Add character-level debug output showing hex bytes as received
- Add frame-level debug output showing complete parsed CAN frame

---

## Detailed Implementation Plan

### Step 1: Create Git Branch
```bash
cd iMatrix
git checkout -b feature/add_printf_frame_debug
```

### Step 2: Add Debug Flag to Enum (messages.h)

**Location:** After line 145 (DEBUGS_FOR_CAN_SERVER)

```c
    DEBUGS_FOR_CAN_SERVER,          // LOGS_ENABLED( DEBUGS_FOR_CAN_SERVER )
    DEBUGS_FOR_CAN_ETH_FRAME,       // LOGS_ENABLED( DEBUGS_FOR_CAN_ETH_FRAME )
```

### Step 3: Add Flag Description (cli_debug.c)

**Location:** In the `debug_flags_description` array

```c
    [DEBUGS_FOR_CAN_ETH_FRAME]      = "Debugs for CAN Ethernet Frame parsing",
```

### Step 4: Add PRINTF_FRAME Macro (can_server.c)

**Location:** After the existing PRINTF macro definition (~line 88)

```c
#define PRINTF_FRAME(...)                           \
    if (LOGS_ENABLED(DEBUGS_FOR_CAN_ETH_FRAME)) {   \
        imx_cli_log_printf(true, __VA_ARGS__);      \
    }
```

### Step 5: Add Character-Level Debug Output (can_server.c)

**Location:** In `tcp_server_thread()` after `recv()` returns data (~line 630)

Add debug output to show received bytes in hex format:

```c
/* Debug: show received bytes */
PRINTF_FRAME("[CAN ETH RX] %zd bytes: ", r);
for (ssize_t i = 0; i < r; i++) {
    PRINTF_FRAME("%02X ", (unsigned char)rx_buf[buf_pos - r + i]);
}
PRINTF_FRAME("\r\n");
```

### Step 6: Add Frame-Level Debug Output (can_server.c)

**Location:** After successful frame parsing (~line 661), before calling `canFrameHandlerWithTimestamp()`

```c
/* Debug: show parsed CAN frame */
PRINTF_FRAME("[CAN ETH Frame] Bus:%u ID:0x%X DLC:%d Data:", canbus, can_id, dlc);
for (int i = 0; i < dlc; i++) {
    PRINTF_FRAME(" %02X", data[i]);
}
PRINTF_FRAME(" TS:%" PRIu64 "\r\n", (uint64_t)utc_time_ms);
```

---

## Todo List

- [ ] Create git branch `feature/add_printf_frame_debug` for iMatrix
- [ ] Add `DEBUGS_FOR_CAN_ETH_FRAME` enum value in messages.h
- [ ] Add description in cli_debug.c debug_flags_description array
- [ ] Add `PRINTF_FRAME` macro in can_server.c
- [ ] Add character-level debug output (bytes received)
- [ ] Add frame-level debug output (parsed frame)
- [ ] Run linter (if available)
- [ ] Build and verify no compile errors
- [ ] Build and verify no compile warnings
- [ ] Test debug output with `debug ?` command
- [ ] Update plan document with completion summary

---

## Usage After Implementation

Once implemented, the debug output can be enabled with:

```bash
# Show all available debug flags (new flag should be listed)
debug ?

# Enable CAN Ethernet frame debugging
debug +0x[flag_value]

# Or set specifically
debug 0x[flag_value]
```

The debug output will show:
1. **Character level:** `[CAN ETH RX] 20 bytes: 36 44 33 23 30 30 36 45...`
2. **Frame level:** `[CAN ETH Frame] Bus:2 ID:0x6D3 DLC:8 Data: 00 6E 02 07 00 00 00 00 TS:1734567890123`

---

## Build Verification

```bash
# Build from Fleet-Connect-1 directory
cd Fleet-Connect-1
mkdir -p build && cd build
cmake ..
make

# Verify no errors or warnings
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| High debug output volume | Performance impact when enabled | Flag is off by default, only enabled manually |
| Buffer overflow in debug string | Security/stability | Use bounded format specifiers |
| Interrupt long-running debug | Timing issues | Use non-blocking imx_cli_log_printf |

---

## Acceptance Criteria

1. New debug flag `DEBUGS_FOR_CAN_ETH_FRAME` visible in `debug ?` output
2. Character-level debug shows hex bytes as they arrive
3. Frame-level debug shows parsed frame details
4. Zero compilation errors
5. Zero compilation warnings
6. No performance impact when flag is disabled

---

**Plan Created By:** Claude Code
**Source Task:** docs/gen/add_printf_frame_debug.md
**Created:** 2025-12-19

---

## Completion Summary

### Work Completed: 2025-12-19

**Implementation Details:**

1. **Git Branch Created:** `feature/add_printf_frame_debug` in iMatrix submodule (from Aptera_1_Clean)

2. **Files Modified:**
   - `iMatrix/cli/messages.h` - Added `DEBUGS_FOR_CAN_ETH_FRAME` enum at line 146
   - `iMatrix/cli/cli_debug.c` - Added description "Debugs for CAN Ethernet Frame parsing" at line 116
   - `iMatrix/canbus/can_server.c` - Added PRINTF_FRAME macro and two debug output points

3. **Debug Output Added:**
   - **Character-level:** Shows hex bytes received from TCP socket
     ```
     [CAN ETH RX] 20 bytes: 36 44 33 23 30 30 36 45...
     ```
   - **Frame-level:** Shows parsed CAN frame with all details
     ```
     [CAN ETH Frame] Bus:2 ID:0x6D3 DLC:8 Data: 00 6E 02 07 00 00 00 00 TS:1734567890123
     ```

4. **Build Verification:**
   - Clean build completed successfully
   - Zero compilation errors
   - Zero new compilation warnings related to changes
   - Build reached 100% completion

### Metrics

| Metric | Value |
|--------|-------|
| Recompilations for syntax errors | 0 |
| Files modified | 3 |
| Lines of code added | ~25 |
| Build time | ~2 minutes |

### Branch Merged

- Feature branch `feature/add_printf_frame_debug` merged to `Aptera_1_Clean`
- Commit: `9a69412d`
- Feature branch deleted after merge

### Pending User Actions

1. Test debug output on target device with `debug ?` command
2. Push changes to remote if desired

---

**Implementation Completed:** 2025-12-19
**Branch Merged:** 2025-12-19
