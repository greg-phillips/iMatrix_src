# Plan: Update App CLI Command Order to Alphabetical

**Date:** 2025-12-26
**Branch:** feature/update-app-cli-order
**Status:** COMPLETED
**Author:** Claude Code
**Completed:** 2025-12-26

---

## Summary

Update the order of commands in the Fleet-Connect-1 App CLI to be alphabetically sorted. When users type `?` in App mode, commands will be displayed in alphabetical order for easier discovery.

---

## Current State Analysis

### File Location
- **File:** `Fleet-Connect-1/cli/fcgw_cli.c`
- **Enum:** Lines 110-137 (`enum cmds`)
- **Command Array:** Lines 238-266 (`command[NO_CMDS]`)

### Important Constraint
The comment at line 110 states: `// Must match commands variable order`

This means the `enum cmds` and the `command[]` array must be kept in sync.

### Current Command Order (25 commands)
| # | Command | Enum | Description |
|---|---------|------|-------------|
| 1 | `?` | CLI_HELP | Show help output |
| 2 | `c` | CLI_CONFIG | Show CS Config |
| 3 | `cd` | CLI_CAN_DEBUG | CAN sensor debug display |
| 4 | `cf` | CLI_CONFIG_FILE | Read config from file |
| 5 | `cm` | CLI_CONFIG_MONITOR | Config with Monitor status |
| 6 | `cs` | CLI_CS | Show CAN BUS Sensors |
| 7 | `csi` | CLI_CSB_INFO | CSB entry info by ID |
| 8 | `ct` | CLI_CT | Cumulative throughput |
| 9 | `debug` | CLI_DEBUG | Set debug flags |
| 10 | `e` | CLI_ENERGY | Energy Manager |
| 11 | `g` | CLI_GFORCE | G-Force Details |
| 12 | `imx` | CLI_IMX | iMatrix Upload data |
| 13 | `n` | CLI_NODES | CAN BUS Nodes |
| 14 | `oor` | CLI_OOR | Out-of-range events |
| 15 | `pids` | CLI_PIDS | OBD2 PIDs |
| 16 | `dtc` | CLI_DTC | Diagnostic Trouble Codes |
| 17 | `ff` | CLI_FF | Freeze Frame data |
| 18 | `cleardtc` | CLI_CLEAR_DTC | Clear DTCs from vehicle |
| 19 | `s` | CLI_STATUS | Status |
| 20 | `so` | CLI_SEND_OBD2 | Send OBD2 msg |
| 21 | `soh` | CLI_SOH | Battery State of Health |
| 22 | `loopstatus` | CLI_LOOPSTATUS | Main loop breadcrumb |
| 23 | `t` | CLI_TEST | Run test |
| 24 | `vin` | CLI_VIN | Enter a VIN |
| 25 | `vsm` | CLI_VSM_TEST | VSM hash lookups |

---

## Proposed Alphabetical Order

The `?` command stays first (standard help convention), then alphabetically:

| # | Command | Enum | Change |
|---|---------|------|--------|
| 1 | `?` | CLI_HELP | No change |
| 2 | `c` | CLI_CONFIG | No change |
| 3 | `cd` | CLI_CAN_DEBUG | No change |
| 4 | `cf` | CLI_CONFIG_FILE | No change |
| 5 | `cleardtc` | CLI_CLEAR_DTC | Moved from #18 |
| 6 | `cm` | CLI_CONFIG_MONITOR | Moved from #5 |
| 7 | `cs` | CLI_CS | Moved from #6 |
| 8 | `csi` | CLI_CSB_INFO | No change |
| 9 | `ct` | CLI_CT | No change |
| 10 | `debug` | CLI_DEBUG | No change |
| 11 | `dtc` | CLI_DTC | Moved from #16 |
| 12 | `e` | CLI_ENERGY | No change |
| 13 | `ff` | CLI_FF | Moved from #17 |
| 14 | `g` | CLI_GFORCE | No change |
| 15 | `imx` | CLI_IMX | No change |
| 16 | `loopstatus` | CLI_LOOPSTATUS | Moved from #22 |
| 17 | `n` | CLI_NODES | No change |
| 18 | `oor` | CLI_OOR | No change |
| 19 | `pids` | CLI_PIDS | No change |
| 20 | `s` | CLI_STATUS | Moved from #19 |
| 21 | `so` | CLI_SEND_OBD2 | No change |
| 22 | `soh` | CLI_SOH | No change |
| 23 | `t` | CLI_TEST | No change |
| 24 | `vin` | CLI_VIN | No change |
| 25 | `vsm` | CLI_VSM_TEST | No change |

---

## Implementation Todo List

- [x] Create new git branch `feature/update-app-cli-order` in Fleet-Connect-1
- [x] Reorder `enum cmds` in fcgw_cli.c (lines 110-137) to match new alphabetical order
- [x] Reorder `command[]` array in fcgw_cli.c (lines 238-266) to match enum
- [x] Build and verify no compilation errors or warnings
- [ ] Test `?` command output shows alphabetical order (requires deployment to device)
- [x] Document completion in this plan

---

## Risk Assessment

**Risk Level:** Low

- **No functional changes:** Only display order changes
- **No API changes:** External interfaces unchanged
- **Compile-time validation:** Mismatches between enum and array will cause compilation errors
- **Easy to verify:** Run `?` command and visually confirm alphabetical order

---

## Questions Before Starting

1. **Should `?` remain first?** (Standard convention - recommend keeping first)
2. **Any commands that should be grouped together?** (e.g., all CAN commands, all OBD2 commands)
3. **Should single-letter commands (`c`, `e`, `g`, `n`, `s`, `t`) be sorted by their full name instead?**

---

## Completion Summary

### Work Undertaken
Updated the App CLI command order in `Fleet-Connect-1/cli/fcgw_cli.c` to be alphabetically sorted. The `?` help command remains first, followed by all other commands in alphabetical order.

### Changes Made
1. **Reordered `enum cmds`** (lines 110-137): Updated enum members to match alphabetical command order
2. **Reordered `command[]` array** (lines 238-267): Reordered command table entries to match enum
3. **Added clarifying comments**: Added note that commands are alphabetically sorted

### Commands Moved
- `cleardtc`: #18 → #5
- `cm`: #5 → #6
- `cs`: #6 → #7
- `dtc`: #16 → #11
- `ff`: #17 → #13
- `loopstatus`: #22 → #16
- `s`: #19 → #20

### Build Verification
- **Build Status:** SUCCESS
- **Compilation Errors:** 0
- **Compilation Warnings:** 0
- **Recompilations Required:** 0 (first build succeeded)

### Metrics
- **Tokens Used:** ~15,000 (estimate)
- **Elapsed Time:** ~5 minutes
- **Files Modified:** 1 (`Fleet-Connect-1/cli/fcgw_cli.c`)
- **Lines Changed:** ~60 (enum + command array)

### Git Status
- **Original Branches:**
  - iMatrix: `Aptera_1_Clean`
  - Fleet-Connect-1: `Aptera_1_Clean`
- **Work Branch:** `feature/update-app-cli-order` (Fleet-Connect-1)

### Next Steps
1. Test on device by running `?` command in App mode
2. Merge branch back to `Aptera_1_Clean` when verified
3. Consider applying same alphabetical sorting to iMatrix Core CLI if desired
