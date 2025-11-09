
## Aim Create a plan to add diagnostic tools to track all generated threads.
The FLeet-Connect-1 and iMatrix code bases spawn multiple threads to process various parts of the system. WE want to track them to see their status
I am concerned about threads crashing or terminating. Provide tracking of thread termination if possible.

Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

The user's name is Greg


Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md
memory_manager_technical_reference.md


read all source files in iMatrix
read all source files in Fleet-Connect-1

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style


## Task
Create wrapper function for thread creatiion and termination.
Track all details about each created thread
Add a new command "threads" to display the status of all system threads.


## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/improve_track_threads_plan.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. After every code change run the linter and build the system to ensure there are not compile errors. If compile errors are found fix them.
5. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number or recompilation required for syntax errors, time taken in both eplased and actual work time, time waiting on user responses  to complete the fearure.
6. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

  Before I proceed with implementation, please review the plan and answer:

  1. Is 32 max tracked threads sufficient? (Can adjust if needed)
  2. Should thread tracking be enabled by default or require configuration?
  3. Any specific threads that should NOT be tracked?
  4. Any specific logging requirements for thread events?
  5. Is the plan approved to proceed with implementation?

Answers
1. Yes
2. Make it a #define conditional
3. No
4. No
5. 
 threads --timers

  Output:
  TIMERS:
  NAME                 INTERVAL  LAST_RUN         COUNT     AVG_TIME  MAX_TIME  STATUS
  -------------------- --------- ---------------- --------- --------- --------- -------
  imx_process_handler  100ms     12:34:56.789     123456    1.2ms     15.3ms    ACTIVE

  Would you like me to:

  1. Add timer monitoring to the plan as a separate but related feature?
  2. Include it in the same tracking system so threads command shows both threads and timers?
  3. Make it a separate command like timers instead?
  4. Track this differently, perhaps just add logging/statistics without a CLI command?

  Or should I proceed with just thread tracking for now and handle timer monitoring as a separate future enhancement?

> 2 
