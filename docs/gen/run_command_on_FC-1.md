<!--
AUTO-GENERATED PROMPT
Generated from: /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/run_command_on_FC-1.yaml
Generated on: 2025-12-31
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Add a command to run a command on the FC-1 device and get the output.

**Date:** 2025-12-30
**Branch:** feature/run_command_on_FC-1

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

- `/home/greg/iMatrix/iMatrix_Client/docs/CLI_and_Debug_System_Complete_Guide.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/testing_fc_1_application.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/ssh_access_to_Fleet_Connect.md`
- `/home/greg/iMatrix/iMatrix_Client/docs/connecting_to_Fleet-Connect-1.md`

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Key Connection Details (from ssh_access_to_Fleet_Connect.md)

| Parameter | Value |
|-----------|-------|
| Host IP | `192.168.7.1` (USB network) |
| SSH Port | `22222` |
| Username | `root` |
| Password | `PasswordQConnect` |

### FC-1 Console Access (from testing_fc_1_application.md)

| Item | Path |
|------|------|
| FC-1 Console | `/usr/qk/etc/sv/FC-1/console` (symlink to PTY) |

To connect to the CLI:
```bash
# SSH to gateway first
ssh -p 22222 root@192.168.7.1

# Then use microcom to connect to the console
microcom /usr/qk/etc/sv/FC-1/console
```

**microcom notes:**
- Press **Enter** after connecting to see the CLI prompt
- To exit microcom: Press **Ctrl+X**

### Alternative CLI Access Methods

1. **Telnet CLI Access (Port 23)** - Direct CLI access without microcom:
   ```bash
   telnet 192.168.7.1 23
   # or
   nc 192.168.7.1 23
   ```

2. **Scripted Command Execution via Telnet**:
   ```bash
   echo "cell status" | nc 192.168.7.1 23
   ```

---

## Task

Using the FC script add a new command to run a command on the FC-1 device and get the output.
Connect to the FC-1 device using the ssh_access_to_Fleet_Connect.md document.
Connect to the cli using micocom connection to the console symlink.
Run the command on the FC-1 device and get the output.
Exit the cli using Ctrl+X.

Return the output to the user.


Ask any questions you need to before starting the work.

---

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/run_command_on_FC-1_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/run_command_on_FC-1.yaml
**Generated:** 2025-12-31
