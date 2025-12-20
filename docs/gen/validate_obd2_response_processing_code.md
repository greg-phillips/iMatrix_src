<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/validate_OBD2.yaml
Generated on: 2025-12-13
Schema version: 1.0
Complexity level: moderate
Auto-populated sections: project, hardware, user, guidelines, references

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Validate OBD2 Response Processing Code

**Date:** 2025-12-13
**Branch:** review/validate_obd2
**Objective:** Compare Fleet-Connect-1 OBD2 response processing against the well-tested python-OBD library to identify discrepancies, missing features, and bugs.

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

- Fleet-Connect-1/CLAUDE.md
- iMatrix/CLAUDE.md

Python OBD2 Library Reference:
- /home/greg/iMatrix/iMatrix_Client/python-OBD

Fleet-Connect-1 OBD2/CAN Processing:
- Fleet-Connect-1/OBD2/
- Fleet-Connect-1/can_process/

use the template files as a base for any new files created
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

code runs on embedded system from: /usr/qk

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

The python OBD2 Library has been tested heavily and we want to use this as a reference for the OBD2 response processing code.

### Requirements:

1. **Read and understand the python-OBD Library**
   - Read the entire python OBD2 Library documentation
   - The repository has been cloned to: `/home/greg/iMatrix/iMatrix_Client/python-OBD`
   - Read all files in the python-OBD directory and understand the code

2. **Review Fleet-Connect-1 OBD2 code**
   - Review the code in `Fleet-Connect-1/can_process` directory
   - Review the code in `Fleet-Connect-1/OBD2` directory

3. **Compare implementations**
   - Compare to ensure our code is consistent with the python OBD2 Library
   - Focus on response parsing and decoding logic
   - Compare PID handling and value extraction

4. **Document findings**
   - Define any missing features in the iMatrix code
   - Identify any bugs in the iMatrix code
   - Note any discrepancies in behavior

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/validate_obd2_response_processing_code_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Comprehensive comparison report** documenting:
   - Feature parity analysis
   - Bug findings with severity ratings
   - Missing functionality
   - Recommendations for fixes
5. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
6. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
7. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
8. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.
9. Merge the branch back into the original branch.
10. Update all documents with relevant details

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/validate_OBD2.yaml
**Generated:** 2025-12-13
**Auto-populated:** 5 sections
