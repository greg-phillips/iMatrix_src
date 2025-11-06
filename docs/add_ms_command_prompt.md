
## Aim Add new sub command to ms command

Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md
docs/comprehensive_code_review_report.md
docs/CLI_and_Debug_System_Complete_Guide.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

The system is built on a VM. Perform Linting on all generated code and then leave it to me to build and test.

## Task
Add a new sub command "use" to the ms command
THe use sub command will review all memory used in the memory management system for each of the csd data structures that show a summary of the number of sectors used and how many sectors are in pending mode, total use and related statistics

## Deliveralbles
1. Detailed plan document, docs/mm_use_command.md, of all aspectsa and detailed todo list for me to review before commencing the implementation.

## ASK ANY QUESIONS needed to verify work requirements.

