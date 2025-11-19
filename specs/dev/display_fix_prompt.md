# CAN Monitor display bug
# The display is being truncated

complexity_level: "simple"

title: "Fix CAN monitor display"

task: |
  Fix the trucation of the "can montor" command.
  Curreny display is truncataed - display full output of the command

  Steps:
  1. Review current output.
+--------------------------- CAN Bus Monitor ---------------------------+
| Last Updated: 20:27:21.534                                              |
+-----------------------------------------------------------------------+
+-----------------------------------------------------------------------+
| Physical Buses                                                        |
+-----------------------------------------------------------------------+
+-----------------------------------+-----------------------------------+
| CAN 0                             | CAN 1                             |
+-----------------------------------+-----------------------------------+
| Status:      Closed               | Status:      Closed               |
| RX:              0 fps (-)        | RX:              0 fps (-)        |
| TX:              0 fps (-)        | TX:              0 fps (-)        |
| RX Rate:            0 B/s         | RX Rate:            0 B/s         |
| TX Rate:            0 B/s         | TX Rate:            0 B/s         |
| RX Total:             0 B         | RX Total:             0 B         |
| TX Total:             0 B         | TX Total:             0 B         |
| Errors:               0           | Errors:               0           |
| Drops:                0           | Drops:                0           |
| Buffer:      [----------]   0%    | Buffer:      [----------]   0%    |
| Peak Buf:      0% (0/4000)        | Peak Buf:      0% (0/4000)        |
+-----------------------------------+-----------------------------------+
+-----------------------------------------------------------------------+
| Ethernet CAN Server (Bus 2)                                           |
+-----------------------------------------------------------------------+
+-----------------------------------+-----------------------------------+
| Status:      Running              | Format:      APTERA               |
| Connection:  Open                 | Virt Buses:  2                    |
| RX:            829 fps (^)        | TX:              0 fps (-)        |
| RX Rate:        6.17 KB/s         | TX Rate:            0 B/s         |
| RX Total:         7.37 MB         | TX Total:             0 B         |
| Errors:               0           | Malformed:            0           |
| Drops:           0 (0/s)          | Buffer:      [----------]   0%    |
| Peak Buf:      0% (2/4000)        |                                   |
+-----------------------------------+-----------------------------------+
+-----------------------------------------------------------------------+
| Logical Buses on Ethernet                                             |
+-----------------------------------------------------------------------+

Lines 1-37 of 68 | RUNNING | Press '?' for help, 'q' to quit

  2. Note oly 37 of potential 68
  3. Do not display blank lines - just generated outut

branch: "bugfix/can-monitor-truncation"

notes:
  - "Issue reported with Ethernet CAN BUS logical bus display"

files_to_modify:
  - "iMatrix/cli/cli_can_monitor.c"

# Optional: Override default branch if needed
# prompt_name will be auto-generated from title as: fix_memory_leak_in_can_processing


