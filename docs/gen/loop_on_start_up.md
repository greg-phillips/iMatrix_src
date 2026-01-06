<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/program_loop.yaml
Generated on: 2026-01-04
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Since last changes to the logging of start up messages the system just locks on start up.

**Date:** 2026-01-04
**Branch:** feature/loop_on_start_up

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

Read and understand the following:
- /home/greg/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md
- /home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Find issue and fix.

The system appears to hang during startup. Example of log file messages showing the issue:

```
=== FC-1 Log Started: 2026-01-04 18:39:33 ===
[FS_LOGGER] Initialized - logging to /var/log/fc-1.log
[EARLY_BUFFER] === Early startup messages (before logger init) ===
[00:00:00.000] Async log queue initialized (10000 message capacity)
[FS_LOGGER] Rotated existing log to /var/log/fc-1.2026-01-04.96.log
[EARLY_BUFFER] === End of early messages (2 buffered, 0 dropped) ===
[00:00:00.016] Filesystem logger initialized (/var/log/fc-1.log)
[00:00:00.016]   Quiet mode: logs to filesystem only
[00:00:00.016] Startup looking for lockfile: /usr/qk/etc/sv/FC-1/iMatrix.lock
[00:00:00.019] Lock acquired successfully. No other instance is running now.
[00:00:00.020] Fleet Connect built on Jan  4 2026 @ 09:47:27
[00:00:00.020] Display setup finished
[00:00:00.021] Setting CLI Handler to 0x0001cf90
[00:00:00.022] Commencing iMatrix Initialization Phase 0.0
[00:00:00.022] Initialization Phase 0.1
[00:00:02.023] Initialization Phase 0.2
[00:00:02.023] Initialization Phase 0.4
[00:00:06.024] Commencing iMatrix Initialization Sequence
[00:00:06.025] [MM2-INFO] ========================================
[00:00:06.025] [MM2-INFO] Creating upload source directory structure
[00:00:06.025] [MM2-INFO] ========================================
[00:00:06.025] [MM2-INFO] Base directory: /tmp/mm2
[00:00:06.026] [MM2-INFO] Corrupted directory: /tmp/mm2/corrupted
[00:00:06.026] [MM2-INFO] Created/verified source directory: /tmp/mm2/gateway
[00:00:06.026] [MM2-INFO] Created/verified source directory: /tmp/mm2/hosted
[00:00:06.026] [MM2-INFO] Created/verified source directory: /tmp/mm2/ble
[00:00:06.026] [MM2-INFO] Created/verified source directory: /tmp/mm2/can
[00:00:06.026] [MM2-INFO] Created/verified corrupted subdirectory: /tmp/mm2/corrupted/gateway
[00:00:06.026] [MM2-INFO] Created/verified corrupted subdirectory: /tmp/mm2/corrupted/hosted
[00:00:06.027] [MM2-INFO] Created/verified corrupted subdirectory: /tmp/mm2/corrupted/ble
[00:00:06.027] [MM2-INFO] Created/verified corrupted subdirectory: /tmp/mm2/corrupted/can
[00:00:06.027] [MM2-INFO] Directory structure created successfully
[00:00:06.027] [MM2-INFO] ========================================
[00:00:06.027] [MM2-RECOVERY] ========================================
[00:00:06.027] [MM2-RECOVERY] WARNING: recover_disk_spooled_data() is DEPRECATED
[00:00:06.027] [MM2-RECOVERY] Main app should call imx_recover_sensor_disk_data() per sensor
[00:00:06.027] [MM2-RECOVERY] ========================================
[00:00:06.027] iMatrix Configuration size: 560648
[00:00:06.099] Read both pages, valid flag = 3, seq=[21609, 21608], using page 0
[00:00:06.101] Restored configuration from SFLASH
[00:00:06.305] Configuration Loaded
[00:00:06.306] iMX6 Ultralite Serial Number: 0x0000000000000000
[00:00:06.678] iMatrix memory tracking initialized
[00:00:06.678] Using 8740 Bytes of storage for message queues
[00:00:06.678] Creating Lists
[00:00:06.679] 25 message_t structs added to the free list.
[00:00:06.681] RTC using System time
[00:00:06.681] System time used
[00:00:06.681] Core System Initialized
[00:00:06.681] Command Line Processor
[00:00:06.681] Setting up Fleet Connect, Product ID: 374664309, Serial Number:
[00:00:06.681] Initializing Variable length data pool, pool size: 5048 Bytes
[00:00:06.682] System has 8 Controls, 48 Sensors and 0 Variables
[00:00:06.682] Initializing Controls & Sensors
[00:00:06.832] Initializing Location System
[00:00:06.837] system_init.c - force AP setup
[00:00:06.837] Initialization Complete, Thing will run in Wi-FI Setup mode
tail: /var/log/fc-1.log has been replaced; following end of new file
[00:00:08.853] iMatrix Gateway Configuration successfully Initialized
[00:00:08.854] Loading Application Config: 274360 Bytes
[00:00:08.854] System contains Application Configuration
[00:00:08.854] Magic: 0x87654321
[00:00:08.854] Linux Gateway Configuration loaded from iMatrix
[00:00:08.855] iMatrix memory tracking initialized
[00:00:08.855] OS Version verified: 4.0.0
[00:00:08.860] Found matching file: /usr/qk/etc/sv/FC-1/Light_Vehicle_cfg.bin
[00:00:08.860] Opening /usr/qk/etc/sv/FC-1/Light_Vehicle_cfg.bin to read configuration
[00:00:08.912] read_config: Successfully read config file '/usr/qk/etc/sv/FC-1/Light_Vehicle_cfg.bin'
[00:00:08.913] Configuration file /usr/qk/etc/sv/FC-1/Light_Vehicle_cfg.bin read successfully
[00:00:08.913] Loading 2 network interface(s) from configuration file
[00:00:08.913]   Mapping eth0 from config[0] to device_config[2]
[00:00:08.913]     DHCP range: 192.168.7.100 - 192.168.7.199
[00:00:08.913]   Config[0] ? device_config[2]: eth0, mode=server, IP=192.168.7.1
[00:00:08.913]   Mapping wlan0 from config[1] to device_config[0]
[00:00:08.913]   Config[1] ? device_config[0]: wlan0, mode=client, IP=DHCP
[00:00:08.913] Network configuration loaded successfully
[00:00:08.914] Total interfaces configured: 2 (max 4)
[00:00:08.914] Product ID updated: 0x00000000 -> 0xB9C3E2A2
[00:00:08.914] Vehicle type changed: Product ID 0x00000000 -> 0xB9C3E2A2
[00:00:08.914] Internal sensor count changed: Saved 0 -> Current 52
[00:00:08.914] Configuration for CAN Product missing or changed. Replacing with file data
[00:00:08.914] Loading 52 predefined sensors from configuration
[00:00:08.914] Successfully loaded 52 valid predefined sensors
[00:00:08.914] Configuration updated: 52 predefined sensors loaded from config
[00:00:08.914] Sensor configuration breakdown:
[00:00:08.914]   - Predefined sensors: 52
[00:00:08.915]   - Product controls: 0
[00:00:08.915]   - Product sensors: 1
[00:00:08.915]   - Total control_sensors (array size): 53
[00:00:08.915]   Product sensor details:
[00:00:08.915]     [0] ID: 0x0D3EA3AF, Name: Fault Code
[00:00:08.915]   After sorting, sensor at index 52 (first non-predefined):
[00:00:08.915]     ID: 0x0D3EA3AF, Name: Fault Code
[00:00:08.915] Configuration for CAN Product contains 0 Controls and 53 Sensors
[00:00:08.915] Configuration for CAN BUS contains 4 Sensors
[00:00:08.929] No DBC files configured for Ethernet CAN bus (bus 2)
[00:00:08.929] Ethernet CAN format: none (CAN_FORMAT_NONE = 0)
[00:00:08.929] OBD2 frame processing: ENABLED (support_obd2 = 1)
[00:00:08.929] Configuration Summary:
[00:00:08.929]   Product ID: 3116622498
[00:00:08.929]   Organization ID: 250007060
[00:00:08.929]   Name: Light Vehicle 2
[00:00:08.930]   No. Predefined: 52
[00:00:08.930]   No. DBC Files: 0
[00:00:08.930]   No. Controls: 0
[00:00:08.930]   No. Sensors: 53
[00:00:08.930]   No. Control Sensors: 53
[00:00:08.930]   No. CAN Controls: 0
[00:00:08.930]   No. CAN Sensors: 596
[00:00:08.930]   No. CAN Control Sensors: 596
[00:00:08.930]   Check-in Period: 300 seconds
[00:00:08.930]   Ethernet CAN Format: none (0)
[00:00:08.930]   OBD2 Processing: ENABLED (1)
[00:00:08.942]   Mapped logical bus 'O-11' (2 nodes) to physical CAN bus 0
[00:00:08.942]   Mapped logical bus 'O-29' (2 nodes) to physical CAN bus 0
[00:00:08.942] Physical CAN bus 0: 4 total nodes (sorted)
[00:00:08.942] Physical CAN bus 1: No nodes configured
[00:00:08.943] No Ethernet CAN buses configured
```

**Key observations from log:**
- System starts normally through initialization phases
- Configuration loads successfully
- Network interfaces configured
- CAN bus sensors loaded
- Log shows activity up to 00:00:08.943 then stops
- The `tail: /var/log/fc-1.log has been replaced; following end of new file` message suggests log rotation occurred during startup

**Investigation focus:**
1. What happens immediately after the CAN bus configuration at ~8.943 seconds?
2. Check the main loop initialization code in `do_everything.c`
3. Look for recent changes to startup logging that may have introduced the issue
4. Check for infinite loops or blocking calls in the initialization sequence

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/loop_on_start_up_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** docs/prompt_work/program_loop.yaml
**Generated:** 2026-01-04
