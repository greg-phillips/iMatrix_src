<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/memory_manger_issue_2.yaml
Generated on: 2026-01-07
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Corruption detected in the memory manager sector chain.

**Date:** 2025-12-30
**Branch:** feature/memory_manger_issue_2

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

- `/home/greg/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/Developer_Debugging_Guide.md`
- `/home/greg/iMatrix/upload_errors/iMatrix/cs_ctrl/docs/MM2_Sector_Chain_Corruption_Fix.md` (2026-01-07, 9KB)
- `/home/greg/iMatrix/upload_errors/iMatrix/cs_ctrl/MM2_Developer_Guide.md` (2025-12-06, 38KB)

use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Important Reference: Previous Sector Chain Corruption Fix

A previous sector chain corruption issue was fixed (documented in MM2_Sector_Chain_Corruption_Fix.md). Key findings from that fix:

**Root Cause Pattern:**
- Race condition in `cleanup_spooled_sectors()` where `free_sector()` was called without updating chain pointers first
- Missing lock protection allowing concurrent modifications
- Result: sector=X (owner=A) → next=Y (owner=B) CORRUPTION (SENSOR_ID MISMATCH)

**Fix Applied:**
- Update chain pointers BEFORE freeing sectors
- Hold `sensor_lock` during entire cleanup operation
- Properly handle head/tail pointer edge cases

**This New Issue:**
The current corruption shows a different pattern:
```
[00:05:02.501] [MM2-VALIDATE] CORRUPTION: free_sector: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.502] [MM2-VALIDATE] CORRUPTION: imx_erase_all_pending: sector=381 points to FREED sector=756 (in_use=0)
```

This appears to be a sector pointing to an already-freed sector (not a sensor ownership mismatch). The pattern repeats rapidly, suggesting a systematic issue rather than a race condition.

## Task

Determine why corruption is detected in the memory manager sector chain.

Note: Log file contains all memory manager debug messages.

Review full log file on device before restarting to understand the issue.

Plan additional debugging output if needed to track issue.

From the log file on the device:
```
[00:05:02.501] [MM2-VALIDATE] CORRUPTION: free_sector: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.502] [MM2-VALIDATE] CORRUPTION: imx_erase_all_pending: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.503] [MM2-VALIDATE] CORRUPTION: free_sector: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.503] [MM2-VALIDATE] CORRUPTION: imx_erase_all_pending: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.505] [MM2-VALIDATE] CORRUPTION: free_sector: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.505] [MM2-VALIDATE] CORRUPTION: imx_erase_all_pending: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.506] [MM2-VALIDATE] CORRUPTION: free_sector: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.507] [MM2-VALIDATE] CORRUPTION: imx_erase_all_pending: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.508] [MM2-VALIDATE] CORRUPTION: free_sector: sector=381 points to FREED sector=756 (in_use=0)
[00:05:02.509] [MM2-VALIDATE] CORRUPTION: imx_erase_all_pending: sector=381 points to FREED sector=756 (in_use=0)
```

### Key Observations from Log:
1. Same sectors (381 → 756) repeatedly reported
2. Both `free_sector` and `imx_erase_all_pending` detect the corruption
3. Errors occur in rapid succession (~1ms apart)
4. sector=756 has `in_use=0` (already freed)

### Investigation Areas:
1. Review how `free_sector()` handles chain cleanup
2. Check `imx_erase_all_pending()` logic for double-free scenarios
3. Verify chain validation logic in both functions
4. Look for timing/ordering issues in sector deallocation

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/memory_manger_issue_2_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/memory_manger_issue_2.yaml
**Generated:** 2026-01-07
