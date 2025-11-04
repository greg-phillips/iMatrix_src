# Update processing of hash tables for CAN BUS processing
Stop and ask questions if any failures to find Background material

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read all source files, *.c, *.h in Fleet-Connect-1/can_process
Read Fleeti-Connect-1/init/imx_client_init.c

## Overview
The CAN BUS processing uses has hash tables to find the correct node to decode the received data.
The orginal code had a fixed number of CAN BUS entries (NO_CAN_BUS)
New functionality was added to allow this 

### 1. Deliveralbles
1. The new -R command line option with force the system to rewite the network configuration regardless if the hash codes match
2. Allow me to review before proceeding.


program start. The main entry point is in iMatrix/imatrix_interface.c this processes command line options.
