<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/memory_manger_issue_1.yaml
Generated on: 2026-01-01
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim The memory manager is not spooling to disk when 80% level is reached.

**Date:** 2025-12-30
**Branch:** feature/memory_manger_issue_1

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

Read and understand the following

- iMatrix/cs_ctrl/memory_manager.c - Main memory manager implementation
- iMatrix/cs_ctrl/memory_manager_tiered.c - Tiered storage implementation
- iMatrix/cs_ctrl/memory_manager_disk.c - Disk spillover functionality
- docs/memory_manager_technical_reference.md - Technical reference documentation

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Determine why the memory manager is not spooling data to disk when 80% threshold is reached
Read /home/greg/iMatrix/iMatrix_Client/docs/memory_manager_technical_reference.md
Read using a sub agent is small sections this vey long log file: logs/mm1.log
Determine why this is happening and fix it.
After completion provide a summary of the changes made.
Use the /home/greg/iMatrix/iMatrix_Client/docs/testing_fc_1_application.md to test the changes.

Note the output from the ms command:
```
>ms
Memory: 1945/2048 sectors (95.0%), Free: 103, Efficiency: 75%
Summary:
  Total active sensors: 1120
  Total sectors used: 600
  Total pending: 317
  Total records: 3356
>ms disk

=== Disk Storage Statistics (MM2) ===
Disk Spooling:
  Status: Automatic (managed by MM2)
  Storage path: /tmp/mm2_spool/

Note: MM2 handles disk spooling automatically
      when memory pressure is detected.
```

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/memory_manger_issue_1_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/memory_manger_issue_1.yaml
**Generated:** 2026-01-01
