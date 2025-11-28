<!--
AUTO-GENERATED PROMPT
Generated from: specs/dev/debug_mm_prompt.md
Generated on: 2025-11-19 15:51:00 UTC
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Fix issues with the memory management system after reviewing logs

**Date:** 2025-11-19
**Branch:** bugfix/memory_manager_1

---

## Code Structure:

**iMatrix (Core Library):** Contains all core telematics functionality including memory management, data logging, communications, and peripherals. The memory management subsystem (cs_ctrl) provides tiered storage with RAM and disk spillover, custom memory pools for efficient allocation, recovery mechanisms for corruption, and statistics/monitoring capabilities.

**Fleet-Connect-1 (Main Application):** Gateway application for vehicle connectivity, integrating OBD2 protocols, CAN bus processing, and iMatrix cloud platform. Utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The WiFi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following:

- /home/greg/iMatrix/iMatrix_Client/CLAUDE.md - Repository overview and development guidelines
- /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/CLAUDE.md - Project-specific instructions
- /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl/* - Memory management subsystem source code

Use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using Doxygen style

**Use the KISS principle - do not over-engineer. Keep it simple and maintainable.**

## Task

The memory manager is a sophisticated embedded memory manager for STM32 and LINUX_PLATFORM versions of the Fleet Connect product. We are working on the LINUX_PLATFORM version.

1. Review all source code in the directory ~/iMatrix/iMatrix_Client/iMatrix/cs_ctrl and create a documentation file ~/iMatrix/iMatrix_Client/docs/mm_details.md to use as a reference as we debug and fix these issues.

2. As you review logs, find the first sign of corruption and stop further examination at that point. Must fix the first issue before proceeding.

3. Run more user tests and review logs in cycles until there are no more issues.

4. The logs are long - use an agent to read them in small sections for efficient processing.

5. Read initial log file ~/iMatrix/iMatrix_Client/logs/mm1.txt to identify the first corruption issue.

## Files to Modify

- iMatrix/cs_ctrl - Memory management subsystem directory

## Notes

- Happens when processing normal sampling data
- Focus on LINUX_PLATFORM implementation
- Debug incrementally - fix one issue at a time
- Use structured approach with documentation

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
   - Create branch: **bugfix/memory_manager_1**

2. Detailed plan document, ***docs/gen/memory_manager_debug_plan.md***, of all aspects and detailed todo list for me to review before commencing the implementation.

3. Once plan is approved, implement and check off the items on the todo list as they are completed.

4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found, fix them immediately.

5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues

6. Once I have determined the work is completed successfully, add a concise description to the plan document of the work undertaken.

7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.

8. Merge the branch back into the original branch.

9. Update all documents with relevant details.

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** specs/dev/debug_mm_prompt.md
**Generated:** 2025-11-19 15:51:00 UTC