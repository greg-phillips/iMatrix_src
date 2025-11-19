<!--
AUTO-GENERATED PROMPT
Generated from: specs/examples/simple/quick_bug_fix.yaml
Generated on: 2025-11-17 09:22:37
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Fix memory leak in CAN processing

**Date:** 2025-11-17
**Branch:** bugfix/can-memory-leak

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

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Additional Notes

- Issue reported in production vehicles
- Affects vehicles with high CAN traffic (>1000 msgs/sec)
- Memory consumption grows ~10MB/hour under load

## Task

Fix the memory leak occurring in can_process.c when processing high-frequency
CAN messages. The leak was identified at line 245 where allocated buffers are
not being freed after processing.

Steps:
1. Review can_process.c line 245 and surrounding code
2. Identify where buffer allocation occurs
3. Add proper cleanup/free calls
4. Verify with valgrind that leak is resolved


**Files to modify:**
- iMatrix/canbus/can_process.c
- iMatrix/canbus/can_process.h

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/fix_memory_leak_in_can_processing.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** specs/examples/simple/quick_bug_fix.yaml
**Generated:** 2025-11-17 09:22:37