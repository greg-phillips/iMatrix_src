
## Aim Create a plan to analyze the performance of can bus, especially etherenet bnse packet processing
Logs indicate dropping a lot of data
=== CAN Ethernet Server Status ===

Server Configuration:
  Enabled:                 Yes
  Status:                  Running
  Listen Address:          192.168.7.1:5555
  Ethernet CAN Bus:        Open

Format Settings:
  Parser Type:             PCAN

Traffic Statistics:
  Cumulative Totals:
    RX Frames:             1041286
    TX Frames:             0
    RX Bytes:              7932657
    TX Bytes:              0
    Dropped (Buffer Full): 942605  ⚠️
    RX Errors:             0
    TX Errors:             0
    Malformed Frames:      31

  Current Rates:
    RX Frame Rate:         829 fps
    TX Frame Rate:         0 fps
    RX Byte Rate:          6315 Bps
    TX Byte Rate:          0 Bps
    Drop Rate:             566 drops/sec  ⚠️

  Peak Rates:
    Peak RX:               2117 fps
    Peak TX:               0 fps
    Peak Drops:            1851 drops/sec

  Ring Buffer:
    Total Size:            500 messages
    Free Messages:         36
    In Use:                464 (92%)  ⚠️
    Peak Usage:            481 messages (96%)

  ⚠️  Performance Warnings:
    - Packets being dropped (566 drops/sec)
    - Ring buffer >80% full (92%)
    Consider: Increase buffer size or reduce CAN traffic

  Note: Use 'canstats' for multi-bus comparison

Server Health:
  Status:                  Healthy

========================================

Stop and ask questions if any failure to find Background material

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Backgroud

Read and understand the following

docs/comprehensive_code_review_report.md
docs/developer_onboarding_guide.md
memory_manager_technical_reference.md


read all source files in iMatrix/canbus
read all source files in Fleet-Connect-1/can_process

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

The system is built on a VM. Perform Linting on all generated code and then leave it to me to build and test.

Packets are being upload and response are being received however the system is not clearing pending data correctly.

## Task
Review code in detail

## Deliveralbles
1. Make a note of the current banches for iMatrix and Fleet-Connect-1 and create new git branchs for any work created.
2. Detailed plan document, *** docs/improve_can_performance_plan_2.md ***, of all aspectsa and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check of the items on the todo list as they are completed.
4. Once I have determined the work is completed sucessfuly add a consise description to the plan document of the work undertaken and the number of tokens used, time taken in both eplased and actual work time  to complete the fearure.
5. merge the branch back in to the original branch.

## ASK ANY QUESIONS needed to verify work requirements.

