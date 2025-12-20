<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/merge_branch.yaml
Generated on: 2025-12-12
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Merging update to Aptera_1_Clean branch

**Date:** 2025-12-12
**Branch:** Aptera_1_Clean

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

- CLAUDE.md - Repository and development guidelines
- Fleet-Connect-1/CLAUDE.md - Application-specific documentation
- iMatrix/CLAUDE.md - Core library documentation

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Notes

- Aptera_1_Clean branch is the latest version of the Aptera_1 branch
- Merge Aptera_1_Clean_fix to Aptera_1_Clean branch
- This merge needs to be reviewed in great detail the CMakeLists.txt file has been modified to allow building on jenkins in the cloud.
- This build needs to build in the Cloud Jenkins server and locallay on the development machines.
- Review all changes with user for approval.
- Create a tempory branch for testing of the merge.
- Test the merge in the temporary branch.
- When validated merge the temporary branch into the Aptera_1_Clean branch.
- Delete the temporary branch.

## Task

Merge the branch Aptera_1_Clean_fix to the Aptera_1_Clean branch.

**Repositories affected:**
- iMatrix
- Fleet-Connect-1

**Source Branch:** Aptera_1_Clean_fix
**Target Branch:** Aptera_1_Clean

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/merge_branch_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/merge_branch.yaml
**Generated:** 2025-12-12
