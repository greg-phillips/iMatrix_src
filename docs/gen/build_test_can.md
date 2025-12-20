<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/build_test_can.yaml
Generated on: 2025-12-15
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Build a new program to test the CAN bus

**Date:** 2025-12-15
**Branch:** feature/build_test_can

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

- Fleet-Connect-1/CMakeLists.txt - The main build configuration for Fleet-Connect-1
- iMatrix/CMakeLists.txt - The iMatrix library build configuration
- test_system/can_test.c - The source file to be built

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

The test_system/can_test.c file demonstrates CAN Driver and J1939 module usage for:
- Receiving raw and J1939 CAN messages
- Sending CAN messages on the bus
- Filtering the receive buffer to only receive specified CAN IDs

## Task

Using the main program in the source file test_system/can_test.c as a base, create a CMakeLists.txt file to build the program.

The program needs to use the same build system that the Fleet-Connect-1 program uses.

This program is cross compiled and used on an embedded target system.

The libqfc and other libraries should be used from the Fleet-Connect-1 program.

### Files to Reference

- **test_system/can_test.c** - Main source file for CAN test program
- **Fleet-Connect-1/CMakeLists.txt** - Reference build system to follow
- **iMatrix/CMakeLists.txt** - iMatrix library build configuration

### Key Build Requirements

1. Cross-compilation support for iMX6 embedded target
2. Link against libqfc library from Fleet-Connect-1
3. Include iMatrix library for CAN driver support (CanEvents)
4. Use same compiler flags and settings as Fleet-Connect-1

Ask any questions needed to clarify requirements before proceeding.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/build_test_can_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/build_test_can.yaml
**Generated:** 2025-12-15
