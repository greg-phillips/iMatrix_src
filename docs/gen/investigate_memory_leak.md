<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/investigate_memory_leak.yaml
Generated on: 2025-12-28
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Investigate Memory Manager Memory Leak

**Date:** 2025-12-28
**Branch:** debug/investigate_memory_leak

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

- iMatrix/cs_ctrl/memory_manager.c - Memory management subsystem
- iMatrix/cs_ctrl/ directory - Contains memory management related code
- /home/greg/iMatrix/iMatrix_Client/docs/Network_Manager_Architecture.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

The Memory Manager is responsible for managing the memory used by the system for storing sensor data. It is not freeing the memory when it is no longer needed.

## Task

Read: /home/greg/iMatrix/iMatrix_Client/docs/Network_Manager_Architecture.md
Read /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl/memory_manager.c and understand the code.
This is a very long log file use and agent to read it in small sections.
Read the log file /home/greg/iMatrix/iMatrix_Client/logs/mm5.txt and understand the problem.
There are two issues.
1. The memory manager is not freeing the memory when it is instructred to erase the memory.
2. The memory manager is triggering write to disk @ 80% usage.
Generate a detailed plan to investigate the problem and fix it.

Ask any questions you need to before starting.

## Files to Analyze

- `/home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl/memory_manager.c` - Main memory manager source
- `/home/greg/iMatrix/iMatrix_Client/logs/mm5.txt` - Log file showing the issues

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/investigate_memory_leak_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/investigate_memory_leak.yaml
**Generated:** 2025-12-28
