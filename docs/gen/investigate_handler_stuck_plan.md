# Fleet-Connect-1 Handler Stuck Investigation Plan

**Date Created:** 2026-01-01
**Time:** 14:35
**Document Version:** 1.0
**Status:** Draft
**Author:** Claude Code Analysis
**Reviewer:** Greg

---

## Executive Summary

This document outlines a comprehensive plan to conduct a 24-hour stability test of the Fleet-Connect-1 (FC-1) system to verify that the handler does not become stuck in a loop. The test is a validation exercise, not a development task.

## Test Objective

Monitor the FC-1/iMatrix system continuously for 24 hours to confirm:
- No handler stuck conditions occur
- System maintains normal operational state
- No unexpected reboots or failures

## Connection Setup

### 1. SSH Connection
```bash
# Primary connection method
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1

# Alternative with SSH config (if configured)
ssh fc1
```

### 2. CLI Access via minicom
Once connected via SSH:
```bash
# Connect to console symlink
minicom

# Or directly to the console device if known
minicom -D /dev/ttyUSB0  # Adjust device as needed
```

## Monitoring Schedule

### 24-Hour Timeline with 4-Hour Checkpoints

| Check # | Time Offset | UTC Time (Example) | Status |
|---------|-------------|-------------------|---------|
| 1 | T+0h | Start Time | Initial baseline |
| 2 | T+4h | Start + 4 hours | First checkpoint |
| 3 | T+8h | Start + 8 hours | Second checkpoint |
| 4 | T+12h | Start + 12 hours | Third checkpoint |
| 5 | T+16h | Start + 16 hours | Fourth checkpoint |
| 6 | T+20h | Start + 20 hours | Fifth checkpoint |
| 7 | T+24h | Start + 24 hours | Final verification |

## Verification Commands

### Main CLI Commands (prompt: ">")

1. **Check system state:**
   ```
   s
   ```
   Expected: `MAIN_IMATRIX_NORMAL` state

2. **Check thread status:**
   ```
   threads
   threads -v
   ```
   Look for: Any "WARNING: Handler stuck" messages

3. **Check boot count:**
   ```
   bootcount
   ```
   Record initial value; should not change during test

4. **Check timer status:**
   ```
   timerstatus
   ```
   Look for: Persistent OVERRUN conditions

### App CLI Commands (prompt: "app>")

1. **Enter app mode:**
   ```
   app
   ```
   Or press `TAB` key

2. **Check CAN registration:**
   ```
   s
   ```
   Expected: CAN controller registered

3. **Check loop status:**
   ```
   loopstatus
   ```
   Critical: Detect any loop conditions

4. **Return to main CLI:**
   ```
   exit
   ```
   Or press `TAB` key

## Data Collection Template

### For Each 4-Hour Checkpoint:

```markdown
## Checkpoint #X - T+Xh
**Time:** [UTC timestamp]
**Uptime:** [from system]

### Main CLI Status
- System State: [MAIN_IMATRIX_NORMAL or other]
- Thread Warnings: [None/Details if any]
- Boot Count: [number]
- Timer Status: [Normal/OVERRUN details]

### App CLI Status
- CAN Registration: [Yes/No]
- Loop Status: [Clear/Details if stuck]

### System Health
- Free Memory: [from 'free' command]
- CPU Load: [from 'uptime']
- Process Status: [FC-1 PID and status]

### Issues Found
- [ ] None
- [ ] Handler stuck warning (detail: _______)
- [ ] Blocking message (detail: _______)
- [ ] GPS failure (detail: _______)
- [ ] Other: _______

### Notes:
[Any observations or anomalies]
```

## Success/Failure Criteria

### PASS Conditions (ALL must be true):
- ✅ No "WARNING: Handler stuck" messages during 24 hours
- ✅ No "BLOCKING IN:" messages detected
- ✅ Boot count remains unchanged (no unexpected reboots)
- ✅ System state remains MAIN_IMATRIX_NORMAL
- ✅ No persistent timer OVERRUN conditions

### FAIL Conditions (ANY triggers failure):
- ❌ "WARNING: Handler stuck at 'Before imx_process()' for XXXXX ms!"
- ❌ "BLOCKING IN: imatrix_upload() (position 50)" or similar
- ❌ Frequent "GPS Nema serial data processing failure" messages
- ❌ Unexpected reboot (boot count changes)
- ❌ System enters error state

## Failure Response Protocol

If a stuck condition is detected:

1. **Immediate Documentation:**
   - Exact timestamp of detection
   - Handler position from warning message
   - Time stuck (milliseconds)
   - Blocking function name and position
   - System state at time of failure

2. **Diagnostic Collection:**
   ```bash
   # Save current logs
   scp -P 22222 root@192.168.7.1:/var/log/fc-1/*.log ./failure_logs/
   
   # Get process information
   ssh -p 22222 root@192.168.7.1 "ps aux | grep FC-1"
   
   # Check file descriptors
   ssh -p 22222 root@192.168.7.1 "ls -la /proc/$(pidof FC-1)/fd/"
   
   # Memory state
   ssh -p 22222 root@192.168.7.1 "cat /proc/meminfo"
   ```

3. **Mark Test as FAILED**
4. **Stop monitoring (test objective achieved)**

## Detailed Todo List

- [ ] Verify SSH connectivity to target device (192.168.7.1:22222)
- [ ] Test minicom connection to console
- [ ] Record initial system state (boot count, uptime, memory)
- [ ] Document test start time
- [ ] Perform Checkpoint #1 (T+0h) - Initial baseline
- [ ] Set reminder/alarm for T+4h
- [ ] Perform Checkpoint #2 (T+4h)
- [ ] Set reminder/alarm for T+8h
- [ ] Perform Checkpoint #3 (T+8h)
- [ ] Set reminder/alarm for T+12h
- [ ] Perform Checkpoint #4 (T+12h)
- [ ] Set reminder/alarm for T+16h
- [ ] Perform Checkpoint #5 (T+16h)
- [ ] Set reminder/alarm for T+20h
- [ ] Perform Checkpoint #6 (T+20h)
- [ ] Set reminder/alarm for T+24h
- [ ] Perform Checkpoint #7 (T+24h) - Final verification
- [ ] Compile all checkpoint data
- [ ] Determine PASS/FAIL status
- [ ] Create final report with all findings
- [ ] Archive logs and documentation

## Tools and Scripts

### Quick Status Check Script
Create `check_status.sh`:
```bash
#!/bin/bash
echo "=== FC-1 Status Check - $(date) ==="
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 << 'EOF'
echo "Uptime: $(uptime)"
echo "FC-1 PID: $(pidof FC-1)"
echo "Memory: $(free | grep Mem)"
echo "Boot count: $(cat /sys/class/misc/bootcount/count 2>/dev/null || echo 'N/A')"
EOF
```

### Automated Monitoring Option
If continuous monitoring is preferred, a script can be created to check status every hour and log results automatically.

## Risk Mitigation

1. **Connection Loss:** 
   - Keep SSH session alive with keepalive settings
   - Have backup connection method ready

2. **Missing Checkpoint:**
   - Set multiple alarms/reminders
   - Document reason if checkpoint is delayed

3. **Ambiguous Results:**
   - Capture screenshots/logs of any questionable output
   - When in doubt, continue monitoring

## Final Report Template

```markdown
# FC-1 Handler Stuck Investigation - Final Report

**Test Duration:** 24 hours
**Start Time:** [UTC]
**End Time:** [UTC]
**Result:** [PASS/FAIL]

## Summary
[Brief summary of test execution and results]

## Checkpoints Completed
- [ ] T+0h - Initial
- [ ] T+4h - Checkpoint 1
- [ ] T+8h - Checkpoint 2
- [ ] T+12h - Checkpoint 3
- [ ] T+16h - Checkpoint 4
- [ ] T+20h - Checkpoint 5
- [ ] T+24h - Final

## Issues Found
[List any issues or none]

## Conclusion
[PASS: System ran for 24 hours without handler stuck conditions]
[FAIL: Handler stuck detected at T+Xh with details...]

## Supporting Evidence
[Attach logs, screenshots, checkpoint data]
```

## Questions for User Before Starting

1. **Target Device:** Is the device currently at 192.168.7.1 and accessible?
2. **Current State:** Is the FC-1 application currently running?
3. **Start Time:** When should the 24-hour monitoring period begin?
4. **Automation:** Should I create automated monitoring scripts, or will checks be manual?
5. **Notification:** How should I alert you at each 4-hour checkpoint?

---

**Next Steps:**
1. Review and approve this plan
2. Confirm device connectivity
3. Begin 24-hour monitoring period
4. Document results at each checkpoint
5. Deliver final PASS/FAIL determination

---

*Plan prepared for review and approval*