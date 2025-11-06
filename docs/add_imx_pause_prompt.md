
## Aim Add Feature
Add two new sub commands to the imx command "pause" "resume"

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

read iMatrix/imatrix_upload/imatrix_upload.c routine of interest is _imatrix_upload

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

The system is built on a VM. Perform Linting on all generated code and then leave it to me to build and test.

The imatrix upload system reads data from the memory management system and sends the data to the iMatrix cloud. The upload routine waits for acknowledgemets from the cloud before it frees the pending data.

## Task
Add a new flag to the icb global variable "unsigned int imatrix_upload_paused : 1" 
when the command "imx pause" is run set the flag imatrix_upload_paused to 1.
when the command "imx resume" is run set the flag imatrix_upload_paused to 0.
in the routine imatrix_upload on line 498 add to the if statement a check if the flag imatrix_upload_paused is set to false, if set to true the routine should nto continue. 
Add to the imx command output, around line 1813, that lists why the upload is not running to include the status of this flag 

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/add_imx_pause_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken and the number of tokens used, time taken in both eplased and actual work time  to complete the fearure.
5. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

