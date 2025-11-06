# Update command line options

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read CAN_DM/src/core/CAN_DM.c
Read iMatrix/imatrix_interface.c

## Overview
Add a new -S (print summary configuration) option to the command line options
Review the current behaviour of the -P  and -S command line options for the program CAN_DM.c

Mimich these functions for the Fleet-Connect-1 application.
Update the -P to match the CAN_DM.c program
Add new -S to match  the CAN_DM.c program
### 1. Deliveralbles
1. Create a plan document to implement this enhancements
2. Allow me to review before proceeding.


Incorrect assumption about program start. The main entry point is in iMatrix/imatrix_interface.c this processes command line options.

Answers.
1. ✅ Is the approach (matching CAN_DM.c implementation) correct?
Yes.
2. ✅ Should both -P and -S auto-locate the configuration file in IMATRIX_STORAGE_PATH?
Refer to existing -P implementation.
3. ✅ Should we add -I option as well (for configuration index display)?
Yes.
4. ✅ Any specific formatting requirements for the output?
Best practices.
5. ✅ Any additional command-line options needed while we're implementing this?
Not at this stage

Update plan and wait for my approval before continuing