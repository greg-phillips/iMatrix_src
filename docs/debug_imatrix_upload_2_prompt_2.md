Think ultrahard as you read and implement the following.


## Aim Debug imatrix upload and memory management processing
Logs indicate bug processing uploading of data 

Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md
memory_manager_technical_reference.md


read all source files in ~/iMatrix/iMatrix_Client/iMatrix/imatrix_upload special focus on upload processing
read all source files in ~/iMatrix/iMatrix_Client/iMatrix/cs_ctrl special focus on read and write of event data

use the template files as a base for any new files created
~/iMatrix/iMatrix_Client/iMatrix/templates/blank.c
~/iMatrix/iMatrix_Client/iMatrix/templates/blank.h

Always create extensive comments using doxygen style

## Task
Review code in detail
The log files maybe  large. Use and agent to process the log files in sections.
Initail log to review is the following  ~/iMatrix/iMatrix_Client/logs/mm1.txt
Then read using an agent ~/iMatrix/iMatrix_Client/logs/mm1.txt for any ERRORS. this is a 140MB file
after reivew I will provide log files with errors as we investigate and make any changes need.
Understand the process of upload and erasing pending data after acknowledegement.
Understand the other debug options available and ask to add them if needed to the tests.

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/debug_imatrix_upload_plan_2.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken and the number of tokens used, time taken in both eplased and actual work time  to complete the fearure.
5. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

