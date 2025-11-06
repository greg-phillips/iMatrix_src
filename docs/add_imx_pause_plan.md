# Implementation Plan: Add imx pause/resume Commands

**Document Version:** 1.0
**Created:** 2025-11-05
**Task:** Add pause/resume functionality to iMatrix upload system
**Target Branches:** To be created from current branches

---

## Executive Summary

This plan outlines the implementation of two new subcommands for the `imx` CLI command: `pause` and `resume`. These commands will allow users to temporarily halt and restart the iMatrix upload process without disabling the entire system. This is useful for debugging, testing, or temporarily conserving bandwidth.

---

## Current Branch Status

### iMatrix_Client Repository
- **Current Branch:** `feature/wrp-config-v12-migration`
- **New Branch:** `feature/imx-pause-resume`

### iMatrix Submodule
- **Current Branch:** `Aptera_1`
- **New Branch:** `feature/imx-pause-resume`

### Fleet-Connect-1 Submodule
- **Current Branch:** `Aptera_1`
- **New Branch:** No changes needed (CLI is in iMatrix core)

---

## Background Analysis

### Key Files Identified

1. **iMatrix/imatrix_upload/imatrix_upload.h** (lines 67-85)
   - Contains `imatrix_data_t` structure with bit flags
   - Current flag: `cli_disabled` at line 84
   - **Action:** Add new `imatrix_upload_paused` flag

2. **iMatrix/imatrix_upload/imatrix_upload.c** (line 223)
   - Defines global instance: `imatrix_data_t imatrix CCMSRAM;`
   - Line 498-550: Upload prevention logic with conditions
   - Lines 1813-1852: Status display showing why upload is not running
   - **Actions:**
     - Add pause check to line 498 condition
     - Add pause status to line 1813+ status display
     - Implement pause/resume subcommand handlers

3. **iMatrix/cli/cli.c** (line 289)
   - Existing `imx` command: `{"imx", &imatrix_status, 0, "iMatrix client - 'imx' (status), 'imx flush' (clear statistics), 'imx stats' (detailed statistics)"}`
   - **Action:** Update help text to include pause/resume

4. **Template Files** (for reference)
   - iMatrix/templates/blank.c
   - iMatrix/templates/blank.h

### Current Upload Prevention Logic (Line 498)

```c
if ((icb.AP_setup_mode == true) ||
    (imx_network_up() == false) ||
    (icb.wifi.restart == true) ||
    (icb.ws.wifi_scan_active == true) ||
    (strlen(device_config.device_serial_number) == 0) ||
    device_config.connected_to_imatrix == false ||
    device_config.imatrix_upload_enabled == false ||
    (imatrix.cli_disabled == true))
```

**New condition to add:** `|| (imatrix.imatrix_upload_paused == true)`

### Current Status Display Logic (Lines 1813-1852)

The `imatrix_status()` function displays reasons why upload is not running:
- Disabled by CLI
- Disabled in configuration
- AP Mode
- Network down
- WiFi restart pending
- Scan active
- No serial number
- Not connected to iMatrix

**New status to add:** "Paused by user command"

---

## Implementation Design

### 1. Structure Modification

**File:** `iMatrix/imatrix_upload/imatrix_upload.h`

**Location:** Line 84 (after `cli_disabled`)

**Change:**
```c
typedef struct imatrix_data {
    imatrix_upload_source_t upload_source;
    uint16_t active_ble_device;
    uint8_t *data_ptr;
    uint16_t state, sensor_no;
    uint16_t notify_cs, notify_entry;
    uint32_t no_imx_uploads;
    imx_utc_time_ms_t upload_utc_ms_time;
    imx_time_t last_upload_time;
    imx_time_t last_dns_time;
    message_t *msg;
    unsigned int imatix_dns_failed      : 1;
    unsigned int imx_error              : 1;
    unsigned int imx_warning            : 1;
    unsigned int imx_send_available     : 1;
    unsigned int printed_error          : 1;
    unsigned int imatrix_active         : 1;
    unsigned int cli_disabled           : 1;
    unsigned int imatrix_upload_paused  : 1;  // NEW: User-requested pause
} imatrix_data_t;
```

### 2. Upload Logic Modification

**File:** `iMatrix/imatrix_upload/imatrix_upload.c`

**Location:** Line 498-501

**Current Code:**
```c
if ((icb.AP_setup_mode == true) || (imx_network_up() == false) || (icb.wifi.restart == true) || (icb.ws.wifi_scan_active == true) ||
    (strlen(device_config.device_serial_number) == 0) || device_config.connected_to_imatrix == false || device_config.imatrix_upload_enabled == false || (imatrix.cli_disabled == true))
{
```

**Modified Code:**
```c
if ((icb.AP_setup_mode == true) || (imx_network_up() == false) || (icb.wifi.restart == true) || (icb.ws.wifi_scan_active == true) ||
    (strlen(device_config.device_serial_number) == 0) || device_config.connected_to_imatrix == false || device_config.imatrix_upload_enabled == false || (imatrix.cli_disabled == true) || (imatrix.imatrix_upload_paused == true))
{
```

### 3. Status Display Modification

**File:** `iMatrix/imatrix_upload/imatrix_upload.c`

**Location:** After line 1816 (in the status display section)

**New Code to Add:**
```c
if (imatrix.imatrix_upload_paused == true)
{
    imx_cli_print("Paused by user command\r\n");
}
```

**Also add to debug output section (after line 512):**
```c
if (imatrix.imatrix_upload_paused == true)
{
    imx_cli_log_printf(true,"Paused by user command ");
}
```

### 4. Command Handler Implementation

**File:** `iMatrix/imatrix_upload/imatrix_upload.c`

**Location:** In the `imatrix_status()` function (search for "imx stats" handling)

**Implementation:**

The `imatrix_status()` function already handles subcommands like "flush" and "stats". We'll add handling for "pause" and "resume" in the same pattern.

**Pseudocode:**
```c
void imatrix_status(uint16_t arg)
{
    char *token;

    token = strtok(NULL, " ");

    if (token == NULL) {
        // Display status (existing code)
    }
    else if (strcmp(token, "flush") == 0) {
        // Existing flush code
    }
    else if (strcmp(token, "stats") == 0) {
        // Existing stats code
    }
    else if (strcmp(token, "pause") == 0) {
        // NEW: Pause upload
        imatrix.imatrix_upload_paused = 1;
        imx_cli_print("iMatrix upload paused\r\n");
    }
    else if (strcmp(token, "resume") == 0) {
        // NEW: Resume upload
        imatrix.imatrix_upload_paused = 0;
        imx_cli_print("iMatrix upload resumed\r\n");
    }
    else {
        imx_cli_print("Unknown imx subcommand: %s\r\n", token);
        imx_cli_print("Valid subcommands: status, flush, stats, pause, resume\r\n");
    }
}
```

### 5. Help Text Update

**File:** `iMatrix/cli/cli.c`

**Location:** Line 289

**Current:**
```c
{"imx", &imatrix_status, 0, "iMatrix client - 'imx' (status), 'imx flush' (clear statistics), 'imx stats' (detailed statistics)"},
```

**Modified:**
```c
{"imx", &imatrix_status, 0, "iMatrix client - 'imx' (status), 'imx flush' (clear statistics), 'imx stats' (detailed statistics), 'imx pause' (pause upload), 'imx resume' (resume upload)"},
```

### 6. Initialization

**File:** `iMatrix/imatrix_upload/imatrix_upload.c`

**Location:** In `init_imatrix()` or `start_imatrix()` function

**Action:** Ensure the new flag is initialized to 0 (not paused) at startup

```c
imatrix.imatrix_upload_paused = 0;
```

---

## Detailed Implementation Todo List

### Phase 1: Branch Creation and Setup
- [ ] Create new branch `feature/imx-pause-resume` in iMatrix_Client repository
- [ ] Enter iMatrix submodule and create new branch `feature/imx-pause-resume`
- [ ] Verify all branches are correctly set up
- [ ] Document branch information

### Phase 2: Structure Modification
- [ ] Open `iMatrix/imatrix_upload/imatrix_upload.h`
- [ ] Add `imatrix_upload_paused` flag to `imatrix_data_t` structure (after line 84)
- [ ] Add Doxygen comment explaining the new flag
- [ ] Verify structure alignment and syntax

### Phase 3: Upload Logic Modification
- [ ] Open `iMatrix/imatrix_upload/imatrix_upload.c`
- [ ] Locate the condition at line 498
- [ ] Add pause check: `|| (imatrix.imatrix_upload_paused == true)`
- [ ] Verify condition syntax and parentheses balance
- [ ] Add debug output for pause status (after line 512)

### Phase 4: Status Display Modification
- [ ] In `imatrix_status()` function, locate status display section (around line 1813)
- [ ] Add check for `imatrix.imatrix_upload_paused` flag
- [ ] Add corresponding print statement: "Paused by user command\r\n"
- [ ] Verify output formatting matches existing style

### Phase 5: Command Handler Implementation
- [ ] Locate existing subcommand handling in `imatrix_status()` function
- [ ] Add "pause" subcommand handler
  - [ ] Set `imatrix.imatrix_upload_paused = 1`
  - [ ] Print confirmation message
- [ ] Add "resume" subcommand handler
  - [ ] Set `imatrix.imatrix_upload_paused = 0`
  - [ ] Print confirmation message
- [ ] Add error handling for unknown subcommands
- [ ] Test command parsing logic

### Phase 6: Help Text Update
- [ ] Open `iMatrix/cli/cli.c`
- [ ] Locate `imx` command entry (line 289)
- [ ] Update help string to include pause and resume subcommands
- [ ] Verify string fits within reasonable line length

### Phase 7: Initialization
- [ ] Locate `init_imatrix()` or `start_imatrix()` function
- [ ] Add initialization: `imatrix.imatrix_upload_paused = 0;`
- [ ] Verify initialization happens before first upload attempt

### Phase 8: Code Review and Documentation
- [ ] Review all changes for consistency with coding style
- [ ] Verify all Doxygen comments are complete and accurate
- [ ] Check for proper indentation and formatting
- [ ] Verify no trailing whitespace or unnecessary changes

### Phase 9: Linting and Static Analysis
- [ ] Run linting tools on modified files
- [ ] Address any warnings or errors
- [ ] Verify code compiles without warnings
- [ ] Check for memory leaks or uninitialized variables

### Phase 10: Testing Preparation
- [ ] Document test cases for user to execute
- [ ] Create test scenarios:
  - [ ] Normal operation (no pause)
  - [ ] Pause during upload
  - [ ] Resume after pause
  - [ ] Status display shows pause state
  - [ ] Reboot behavior (should unpause)
- [ ] Prepare verification commands

### Phase 11: Documentation
- [ ] Update this plan document with actual implementation details
- [ ] Document any deviations from original plan
- [ ] Record token usage and time taken
- [ ] Add implementation summary section

---

## Files to Modify

| File | Lines | Modifications |
|------|-------|---------------|
| `iMatrix/imatrix_upload/imatrix_upload.h` | 84 | Add `imatrix_upload_paused` flag to structure |
| `iMatrix/imatrix_upload/imatrix_upload.c` | 498 | Add pause check to upload condition |
| `iMatrix/imatrix_upload/imatrix_upload.c` | 512 | Add pause status to debug output |
| `iMatrix/imatrix_upload/imatrix_upload.c` | 1813+ | Add pause status to status display |
| `iMatrix/imatrix_upload/imatrix_upload.c` | TBD | Add pause/resume command handlers |
| `iMatrix/imatrix_upload/imatrix_upload.c` | TBD | Initialize flag in init function |
| `iMatrix/cli/cli.c` | 289 | Update help text |

---

## Dependencies

### Internal Dependencies
- None - This is a self-contained feature
- Uses existing CLI command structure
- Uses existing imatrix global variable

### External Dependencies
- None

### Build Dependencies
- Standard iMatrix build system (CMake)
- No new libraries required

---

## Risk Analysis

### Low Risk
- ✅ Changes are localized to upload system
- ✅ No changes to memory management or network code
- ✅ Flag is properly sized (1 bit) for efficiency
- ✅ No persistence required (simple state management)

### Potential Issues
- ⚠️ User might forget upload is paused
  - **Mitigation:** Status display clearly shows pause state
- ⚠️ Pause during active transmission
  - **Mitigation:** Current code structure checks flag at start of upload loop

### Testing Considerations
- Test pause/resume transitions
- Verify status display accuracy
- Test behavior across different upload sources
- Verify reboot clears pause state

---

## Coding Standards Compliance

### Style Guidelines
- ✅ Use existing code style (4 spaces, K&R braces)
- ✅ Follow existing comment patterns
- ✅ Match variable naming conventions
- ✅ Use Doxygen-style comments

### Platform Considerations
- ✅ No platform-specific code needed
- ✅ Works on both Linux and STM32
- ✅ Minimal memory footprint (1 bit flag)
- ✅ No dynamic allocation

### Documentation Requirements
- ✅ Doxygen comments for structure field
- ✅ Inline comments for command handlers
- ✅ Update CLI help text
- ✅ Document in this plan

---

## Test Plan (For User Execution)

### Test Case 1: Basic Pause/Resume
```bash
# Start system and verify upload is running
imx

# Pause upload
imx pause
# Expected: "iMatrix upload paused"

# Check status
imx
# Expected: Status shows "Paused by user command"

# Resume upload
imx resume
# Expected: "iMatrix upload resumed"

# Check status
imx
# Expected: Status no longer shows pause message
```

### Test Case 2: Pause Persistence
```bash
# Pause upload
imx pause

# Reboot system
reboot

# After reboot, check status
imx
# Expected: Upload should NOT be paused (flag clears on boot)
```

### Test Case 3: Invalid Subcommands
```bash
# Try invalid subcommand
imx invalid
# Expected: Error message with valid subcommands listed
```

### Test Case 4: Pause During Active Upload
```bash
# Trigger data upload (generate sensor data)
# While upload is in progress:
imx pause

# Verify upload stops at next iteration
# Check logs for pause indication
```

---

## Questions for User Review

### Clarifications Needed:
1. ✅ **Flag Location**: Confirmed adding to `imatrix_data_t` structure (not icb)
2. ❓ **Persistence**: Should pause state persist across reboots? (Current plan: NO)
3. ❓ **Scope**: Should pause affect all upload sources or just current? (Current plan: ALL)
4. ✅ **Command Structure**: Confirmed as subcommands of `imx` command

### Design Decisions to Confirm:
1. Should there be a visual indicator in the prompt when paused?
2. Should pause/resume be logged to syslog?
3. Should there be a timeout for auto-resume?
4. Should pause state be included in device configuration?

---

## Success Criteria

### Functional Requirements
- [ ] `imx pause` command sets pause flag and stops uploads
- [ ] `imx resume` command clears pause flag and restarts uploads
- [ ] `imx` status command shows pause state when paused
- [ ] Upload loop respects pause flag
- [ ] System initializes with flag cleared (not paused)

### Code Quality Requirements
- [ ] All code follows existing style guidelines
- [ ] Doxygen comments are complete and accurate
- [ ] No compiler warnings
- [ ] No linting errors
- [ ] Proper error handling

### Documentation Requirements
- [ ] Help text updated
- [ ] Plan document complete
- [ ] Test cases documented
- [ ] Implementation summary added

---

## Implementation Notes

### Code Style Observations
- Use `imx_cli_print()` for CLI output
- Use `imx_cli_log_printf(true, ...)` for debug output
- Follow existing pattern for subcommand parsing with `strtok()`
- Maintain consistent indentation (4 spaces)
- Use `\r\n` for line endings in output

### Pattern Reference
Example of existing subcommand handling from `imatrix_status()`:
```c
token = strtok(NULL, " ");
if (token != NULL) {
    if (strcmp(token, "flush") == 0) {
        // Handle flush
    }
    else if (strcmp(token, "stats") == 0) {
        // Handle stats
    }
}
```

---

## Timeline Estimate

| Phase | Estimated Time | Description |
|-------|----------------|-------------|
| Branch Setup | 5 minutes | Create and verify branches |
| Structure Mod | 5 minutes | Add flag to header |
| Logic Changes | 15 minutes | Modify upload and status logic |
| Command Handler | 15 minutes | Implement pause/resume |
| Testing Prep | 10 minutes | Document test cases |
| Review & Lint | 10 minutes | Code review and cleanup |
| **Total** | **60 minutes** | Actual coding time |

---

## Next Steps

1. **User Review**: Please review this plan and answer the questions above
2. **Approval**: Confirm plan is acceptable before implementation begins
3. **Implementation**: Execute todo list items in order
4. **Testing**: User performs testing on target hardware
5. **Merge**: Merge branches back after successful testing

---

## Notes

- This is a VM-based build system - linting only, no compilation
- User will perform actual build and hardware testing
- Changes are minimal and focused for easy review
- No impact on existing functionality when not paused

---

## Implementation Summary

### Completion Status: ✅ COMPLETE

**Implementation Date:** 2025-11-05
**Branches Created:**
- iMatrix_Client: `feature/imx-pause-resume`
- iMatrix submodule: `feature/imx-pause-resume`

### Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `iMatrix/imatrix_upload/imatrix_upload.h` | +1 | Added `imatrix_upload_paused` flag to structure |
| `iMatrix/imatrix_upload/imatrix_upload.c` | +32 | Upload logic, status display, command handlers, initialization |
| `iMatrix/cli/cli.c` | +1 | Updated help text |
| **Total** | **34 lines added** | **3 files modified** |

### Implementation Details

#### 1. Structure Modification (imatrix_upload.h:85)
```c
unsigned int imatrix_upload_paused  : 1;    /**< User-requested upload pause flag */
```
Added new 1-bit flag to `imatrix_data_t` structure following the pattern of `cli_disabled`.

#### 2. Upload Logic Check (imatrix_upload.c:499)
```c
|| (imatrix.imatrix_upload_paused == true)
```
Added pause check to the upload prevention condition on line 499.

#### 3. Debug Output (imatrix_upload.c:515-517)
```c
if (imatrix.imatrix_upload_paused == true)
{
    imx_cli_log_printf(true,"Paused by user command ");
}
```
Added pause status to debug logging output.

#### 4. Status Display (imatrix_upload.c:1822-1825)
```c
if (imatrix.imatrix_upload_paused == true)
{
    imx_cli_print("Paused by user command\r\n");
}
```
Added pause status to user-facing status display in `imx` command output.

#### 5. Pause Command Handler (imatrix_upload.c:1768-1774)
```c
else if (strcmp(token, "pause") == 0x00)
{
    /*
     * Pause iMatrix upload
     */
    imatrix.imatrix_upload_paused = 1;
    imx_cli_print("iMatrix upload paused\r\n");
    return;
}
```
Implemented `imx pause` command to set the flag.

#### 6. Resume Command Handler (imatrix_upload.c:1776-1783)
```c
else if (strcmp(token, "resume") == 0x00)
{
    /*
     * Resume iMatrix upload
     */
    imatrix.imatrix_upload_paused = 0;
    imx_cli_print("iMatrix upload resumed\r\n");
    return;
}
```
Implemented `imx resume` command to clear the flag.

#### 7. Initialization (imatrix_upload.c:334)
```c
imatrix.imatrix_upload_paused = 0;  /* Ensure upload is not paused on init */
```
Explicitly initialize flag to 0 (not paused) on system init.

#### 8. Help Text Update (cli.c:289)
```c
{"imx", &imatrix_status, 0, "iMatrix client - 'imx' (status), 'imx flush' (clear statistics), 'imx stats' (detailed statistics), 'imx pause' (pause upload), 'imx resume' (resume upload)"},
```
Updated CLI help text to document new pause/resume subcommands.

### Testing Checklist

Please perform the following tests:

- [ ] **Test 1: Basic Pause/Resume**
  ```bash
  imx              # Should show normal status
  imx pause        # Should display "iMatrix upload paused"
  imx              # Should show "Paused by user command"
  imx resume       # Should display "iMatrix upload resumed"
  imx              # Should no longer show pause message
  ```

- [ ] **Test 2: Pause Behavior**
  ```bash
  imx pause
  # Generate some sensor data or wait for regular upload cycle
  # Verify upload does not occur while paused
  # Check logs for "Paused by user command" message
  ```

- [ ] **Test 3: Resume Behavior**
  ```bash
  imx pause
  # Wait briefly
  imx resume
  # Verify uploads resume normally
  # Check that pending data gets uploaded
  ```

- [ ] **Test 4: Help Text**
  ```bash
  ?                # List all commands
  # Verify "imx" help text includes pause and resume
  ```

- [ ] **Test 5: Reboot Behavior**
  ```bash
  imx pause
  reboot
  # After reboot:
  imx              # Should NOT show "Paused by user command"
  # Upload should be running normally
  ```

- [ ] **Test 6: Multiple Upload Sources (if applicable)**
  ```bash
  imx pause
  # If system has BLE or CAN devices
  # Verify all upload sources are paused
  ```

### Design Decisions Made

1. **Non-Persistent State**: Pause state resets to "not paused" on reboot (via memset in init)
2. **Global Scope**: Affects all upload sources (Gateway, BLE, CAN)
3. **Command Structure**: Implemented as subcommands of `imx` (following existing pattern)
4. **Explicit Init**: Added explicit initialization for clarity, though memset would suffice
5. **Status Visibility**: Added to both debug output and user status display

### Metrics

- **Token Usage:** ~79,500 tokens
- **Implementation Time:** ~45 minutes (actual coding)
- **Lines of Code:** 34 lines added across 3 files
- **Complexity:** Low - simple flag-based feature
- **Risk Level:** Minimal - localized changes, follows existing patterns

### Code Quality

✅ **Follows existing code style**
- K&R brace style
- 4-space indentation
- Consistent comment format

✅ **Follows existing patterns**
- Flag structure matches `cli_disabled`
- Command handling matches `flush` pattern
- Status display matches existing checks

✅ **Documentation**
- Doxygen comment on structure field
- Inline comments for command handlers
- Updated CLI help text

✅ **Minimal footprint**
- 1-bit flag (no memory overhead)
- No dynamic allocation
- No platform-specific code

### Known Limitations

1. **No Persistence**: Pause state is lost on reboot
   - *Rationale:* Prevents system from staying paused unintentionally after maintenance

2. **No Timeout**: No auto-resume after period
   - *Rationale:* User may want indefinite pause for debugging

3. **No Visual Indicator**: Prompt doesn't show pause state
   - *Rationale:* Status display via `imx` command is sufficient

### Recommendations for Future Enhancement

1. **Optional Persistence**: Add configuration flag to make pause state persistent if needed
2. **Timeout Feature**: Add `imx pause <seconds>` to auto-resume after timeout
3. **Prompt Indicator**: Add "[PAUSED]" to CLI prompt when upload is paused
4. **Syslog Integration**: Log pause/resume events to syslog for audit trail
5. **Statistics**: Track total time paused in system statistics

---

**Plan Status:** ✅ IMPLEMENTED
**Ready for:** User testing on target hardware
