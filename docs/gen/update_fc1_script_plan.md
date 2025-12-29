# FC-1 Script Update Plan: Add Enable/Disable Service Commands

**Date:** 2025-12-29
**Author:** Claude Code
**Status:** Completed
**Branch:** feature/update_fc1_script (merged to main)
**Commit:** 7dc18e7

---

## Overview

Add the ability to enable and disable the FC-1 application in the runsv service. This allows the service to be prevented from auto-starting on boot while preserving the run script for easy re-enabling.

## Current State

**Repository Branches:**
- iMatrix_Client: `main`
- iMatrix submodule: `debug/investigate_memory_leak`
- Fleet-Connect-1 submodule: `Aptera_1_Clean`

**Files Modified:**
- `scripts/fc1` - Host-side remote control script
- `scripts/fc1_service.sh` - Target-side service control script

## Design

### Runit Service Enable/Disable Mechanism

Runit uses a `down` file to control automatic service startup:
- **Enabled:** No `down` file exists in service directory
- **Disabled:** A `down` file exists at `/usr/qk/etc/sv/FC-1/down`

When a `down` file is present:
- `runsv` will NOT automatically start the service
- Manual `sv start FC-1` will still work
- The run script is preserved

### New Commands

| Command | Host Script | Target Script | Behavior |
|---------|-------------|---------------|----------|
| `enable` | `fc1 enable` | `fc1_service.sh enable` | Remove `down` file + start service |
| `disable` | `fc1 disable` | `fc1_service.sh disable` | Stop service + create `down` file |

### Behavior Specifications

**`disable` command:**
1. Display warning: "Service will not auto-start on reboot"
2. Prompt for confirmation (unless `-y` flag provided)
3. Stop the running service
4. Create `/usr/qk/etc/sv/FC-1/down` file
5. Confirm disabled state

**`enable` command:**
1. Remove `/usr/qk/etc/sv/FC-1/down` file (if exists)
2. Start the service
3. Confirm enabled state

**`status` command update:**
- Add enabled/disabled indicator to status output
- Check for presence of `down` file

### Safety Features

1. Confirmation prompt on `disable` (skip with `-y` flag)
2. Warning message about boot behavior
3. Status clearly shows enabled/disabled state

---

## Implementation Todo List

### Phase 1: Branch Setup
- [x] Create feature branch `feature/update_fc1_script` from main

### Phase 2: Target-Side Script (fc1_service.sh)
- [x] Add `is_enabled()` helper function to check for down file
- [x] Add `enable_service()` function - removes down file, starts service
- [x] Add `disable_service()` function - stops service, creates down file, with confirmation
- [x] Update `print_status()` to show enabled/disabled state
- [x] Add `enable` and `disable` cases to main switch
- [x] Update `show_help()` with new commands

### Phase 3: Host-Side Script (fc1)
- [x] Add `enable` and `disable` to the case statement
- [x] Pass through `-y` flag for disable confirmation skip
- [x] Update `show_help()` with new commands and examples

### Phase 4: Verification
- [x] Run linter/shellcheck on both scripts
- [x] Verify scripts have no syntax errors
- [x] Test help output displays correctly

### Phase 5: Documentation
- [x] Update this plan with implementation summary
- [x] Record metrics (tokens, time, etc.)

### Phase 6: Finalization
- [x] Commit changes with descriptive message
- [x] Merge branch back to main

---

## File Changes Detail

### scripts/fc1_service.sh

**New functions:**
```sh
is_enabled()        # Returns 0 if enabled (no down file), 1 if disabled
enable_service()    # Remove down file + start service
disable_service()   # Confirm + stop service + create down file
```

**Modified functions:**
- `print_status()` - Add "[OK] Auto-start: Enabled" or "[--] Auto-start: Disabled" line
- `show_help()` - Add enable/disable documentation
- Main case statement - Add enable/disable cases

### scripts/fc1

**Modified sections:**
- Case statement - Add enable/disable routing
- `show_help()` - Add enable/disable documentation

---

## Implementation Summary

### Work Completed

Successfully implemented enable/disable functionality for the FC-1 runsv service:

1. **Target-side script (fc1_service.sh):**
   - Added `FC1_DOWN_FILE` variable for down file path
   - Added `is_enabled()` helper function
   - Added `enable_service()` function that removes down file and starts service
   - Added `disable_service()` function with warning banner and confirmation prompt
   - Updated `print_status()` to show auto-start enabled/disabled state
   - Added enable/disable cases to main switch
   - Updated help text with new commands and examples

2. **Host-side script (fc1):**
   - Added `enable` to simple commands case
   - Added `disable` case with argument passthrough for `-y` flag
   - Updated help text with new commands and examples

### Metrics

- **Recompilations required for syntax errors:** 0
- **Elapsed time:** ~5 minutes
- **User wait time:** Minimal (initial questions, approval)

---

**Implementation Completed:** 2025-12-29
**Implemented By:** Claude Code
