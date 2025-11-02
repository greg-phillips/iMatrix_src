# DHCP Server Shutdown Integration Plan
**Version**: 1.0
**Date**: 2025-11-02
**Author**: System Integration Team
**Status**: Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Power Management Analysis](#current-power-management-analysis)
3. [Integration Strategy](#integration-strategy)
4. [Implementation Plan](#implementation-plan)
5. [Code Changes Required](#code-changes-required)
6. [Testing Strategy](#testing-strategy)
7. [Rollback Procedures](#rollback-procedures)

---

## Executive Summary

### Problem Statement
The graceful power-down sequence in Fleet-Connect-1 currently handles:
- ✅ Sensor data flushing (RAM to cloud)
- ✅ Emergency disk writes
- ✅ Cellular modem shutdown
- ✅ System reboot/powerdown

But it does **NOT** handle:
- ❌ DHCP server (udhcpd) shutdown
- ❌ Network service cleanup
- ❌ PID file cleanup for udhcpd processes

### Solution Overview
Integrate DHCP server shutdown into the power management state machine at the optimal point in the sequence to ensure:
1. **Data Preservation**: All sensor data uploaded before network services stop
2. **Clean Shutdown**: udhcpd processes terminated gracefully via runit
3. **Resource Cleanup**: PID files and service state cleaned up
4. **Fast Recovery**: System can resume quickly if ignition returns

### Expected Outcomes
- ✅ DHCP server stopped gracefully during power-down
- ✅ Both eth0 and wlan0 udhcpd instances terminated properly
- ✅ Network services available until after all data is saved
- ✅ Clean state for system reboot or power-down
- ✅ No orphaned processes or stale PID files

---

## Current Power Management Analysis

### Shutdown Sequence (From process_power.c)

The graceful shutdown follows this state machine:

| State | Duration | Purpose | Can Abort? |
|-------|----------|---------|------------|
| **POWER_STATE_READ_DATA** | Continuous | Normal operation, monitoring | N/A |
| **POWER_STATE_PREPARE_SHUTDOWN** | Instant | Start shutdown, call flush_all_devices() | ❌ |
| **POWER_STATE_FLUSH_RAM** | 2 minutes | Wait for sensors to upload to cloud | ✅ Yes |
| **POWER_STATE_FLUSH_DISK** | 2 minutes | Wait for emergency files + pending uploads | ✅ Yes |
| **POWER_STATE_CELLULAR_SHUTDOWN** | Instant | Shutdown cellular modem | ✅ Yes |
| **POWER_STATE_SHUTDOWN** | 5 minutes | Wait for cellular down, save config | ✅ Yes |
| **POWER_STATE_REBOOT** | N/A | System rebooting (idle state) | ❌ |
| **POWER_DOWN_STATE** | N/A | System powered down | ✅ Yes |

### Key Code Locations (process_power.c)

**Shutdown Initiation:**
```c
// Line 376: Shutdown starts when ignition off or reboot requested
if (ignition == false || icb.reboot == true)
{
    start_shutdown();  // Sets power_state = POWER_STATE_PREPARE_SHUTDOWN
}
```

**Data Preservation Sequence:**
```c
// Line 394-437: POWER_STATE_FLUSH_RAM
// - Waits for all sensors to upload to cloud
// - Timeout: 2 minutes (IMATRIX_RAM_FLUSH_TIME)
// - On completion: flush_all_sensors_to_disk()
// - Transitions to: POWER_STATE_FLUSH_DISK

// Line 439-476: POWER_STATE_FLUSH_DISK
// - Waits for pending uploads to ACK
// - Emergency files already written (synchronous)
// - Timeout: 2 minutes (IMATRIX_DISK_FLUSH_TIME)
// - Transitions to: POWER_STATE_CELLULAR_SHUTDOWN
```

**Network/System Shutdown:**
```c
// Line 477-492: POWER_STATE_CELLULAR_SHUTDOWN
// - Calls set_sms_wakeup()
// - Immediately transitions to: POWER_STATE_SHUTDOWN

// Line 493-551: POWER_STATE_SHUTDOWN
// - Waits for cellular modem power down
// - Saves configuration: imx_save_config()
// - Timeout: 5 minutes (CELLULAR_POWER_DOWN_TIMEOUT)
// - Final action: system("reboot") or quake_power_down()
```

### Critical Timing Constraints

**Why These Timings Matter:**
1. **FLUSH_RAM (2 min)**: Allows cloud uploads while network is UP
2. **FLUSH_DISK (2 min)**: Ensures all emergency files written
3. **CELLULAR_SHUTDOWN**: Network still needed for final operations
4. **SHUTDOWN (5 min)**: Final cleanup before hardware shutdown

**Network Dependency Analysis:**
- **Cloud Uploads**: Require cellular/WiFi/Ethernet connectivity
- **Emergency Files**: Local disk writes (no network needed)
- **Configuration Save**: Local flash writes (no network needed)
- **DHCP Server**: Only needed while devices may connect

**Conclusion**: DHCP server can be stopped **AFTER** FLUSH_DISK completes, since all critical network-dependent operations are finished.

---

## Integration Strategy

### Optimal Integration Point

**Selected State**: **POWER_STATE_CELLULAR_SHUTDOWN**

**Rationale:**
1. ✅ **All data preserved**: FLUSH_RAM and FLUSH_DISK already completed
2. ✅ **Cloud uploads done**: All sensors uploaded or emergency files written
3. ✅ **Configuration saved**: Critical config already persisted
4. ✅ **Before system halt**: Ensures clean shutdown before reboot/powerdown
5. ✅ **Network still active**: Cellular shutdown happens here, so network services should stop too

### Shutdown Sequence with DHCP Integration

```
POWER_STATE_FLUSH_DISK complete
         ↓
POWER_STATE_CELLULAR_SHUTDOWN entered
         ↓
    [NEW] Stop DHCP Server (udhcpd service)
         ↓
    Set SMS wakeup (existing)
         ↓
    Transition to POWER_STATE_SHUTDOWN
         ↓
    Wait for cellular down (existing)
         ↓
    Save configuration (existing)
         ↓
    Reboot or Power Down (existing)
```

### Service Shutdown Method

**Approach**: Use runit's `sv` command for graceful shutdown

**Advantages:**
1. ✅ Runit handles process management
2. ✅ Finish script is automatically executed
3. ✅ PID files cleaned up properly
4. ✅ Both eth0 and wlan0 instances terminated
5. ✅ Consistent with runit service architecture

**Command**: `sv stop udhcpd`

This will:
- Send TERM signal to wlan0 foreground process (runit supervised)
- Execute `/etc/sv/udhcpd/finish` script
- Finish script kills eth0 background process using PID file
- Finish script removes all PID files
- Clean state restored

---

## Implementation Plan

### Phase 1: Add DHCP Shutdown Function

**File**: `Fleet-Connect-1/power/process_power.c`

**Task 1.1**: Add function to stop DHCP server
- [ ] Create `stop_dhcp_server()` function
- [ ] Check if udhcpd service exists
- [ ] Call `sv stop udhcpd` via system()
- [ ] Add comprehensive logging
- [ ] Handle errors gracefully

**Task 1.2**: Add verification function
- [ ] Create `verify_dhcp_stopped()` function
- [ ] Check for running udhcpd processes
- [ ] Verify PID files removed
- [ ] Return status for diagnostics

### Phase 2: Integrate with Power State Machine

**File**: `Fleet-Connect-1/power/process_power.c`

**Task 2.1**: Modify POWER_STATE_CELLULAR_SHUTDOWN
- [ ] Add DHCP shutdown before cellular shutdown
- [ ] Add state logging
- [ ] Add debug prints
- [ ] Maintain existing cellular shutdown logic

**Task 2.2**: Update CLI status display
- [ ] Add DHCP shutdown status to `cli_power_state()`
- [ ] Show service status in CELLULAR_SHUTDOWN state
- [ ] Display cleanup progress

### Phase 3: Testing and Validation

**Task 3.1**: Unit Testing
- [ ] Test DHCP shutdown function in isolation
- [ ] Verify sv command works correctly
- [ ] Test with single interface (eth0 only)
- [ ] Test with single interface (wlan0 only)
- [ ] Test with dual interfaces (eth0 + wlan0)

**Task 3.2**: Integration Testing
- [ ] Test complete shutdown sequence
- [ ] Verify data preservation not affected
- [ ] Test ignition abort at each state
- [ ] Verify clean reboot
- [ ] Verify clean powerdown

**Task 3.3**: Regression Testing
- [ ] Confirm existing power-down works
- [ ] Verify cloud uploads still succeed
- [ ] Check cellular shutdown timing unchanged
- [ ] Validate configuration save still works

---

## Code Changes Required

### File: Fleet-Connect-1/power/process_power.c

#### Addition 1: DHCP Shutdown Function (Add after line 322)

```c
/**
 * @brief Stop DHCP server gracefully using runit
 *
 * Stops the udhcpd service which will:
 * - Terminate wlan0 foreground process (runit supervised)
 * - Execute finish script to kill eth0 background process
 * - Clean up all PID files
 * - Restore clean service state
 *
 * @return 0 on success, -1 on error
 */
static int stop_dhcp_server(void)
{
    int ret;
    struct stat st;

    PRINTF("[Power - Stopping DHCP server (udhcpd service)\r\n");

    // Check if udhcpd service directory exists
    if (stat("/etc/sv/udhcpd", &st) != 0) {
        PRINTF("[Power - udhcpd service not installed, skipping\r\n");
        return 0;  // Not an error - service may not be configured
    }

    // Check if udhcpd service is actually running
    ret = system("sv check udhcpd >/dev/null 2>&1");
    if (ret != 0) {
        PRINTF("[Power - udhcpd service not running, already stopped\r\n");
        return 0;  // Not an error - already stopped
    }

    // Stop the service using runit
    PRINTF("[Power - Executing: sv stop udhcpd\r\n");
    ret = system("sv stop udhcpd");
    if (ret != 0) {
        PRINTF("[Power - WARNING: Failed to stop udhcpd service (exit code: %d)\r\n", ret);
        // Continue anyway - don't block shutdown
    } else {
        PRINTF("[Power - udhcpd service stopped successfully\r\n");
    }

    // Give the service a moment to clean up
    usleep(500000);  // 500ms

    return 0;  // Always return success to not block shutdown
}

/**
 * @brief Verify DHCP server processes are stopped
 *
 * Checks for any remaining udhcpd processes and PID files
 * to ensure clean shutdown.
 *
 * @return true if fully stopped, false if processes remain
 */
static bool verify_dhcp_stopped(void)
{
    int ret;
    struct stat st;
    bool fully_stopped = true;

    // Check for running udhcpd processes
    ret = system("pgrep udhcpd >/dev/null 2>&1");
    if (ret == 0) {
        PRINTF("[Power - WARNING: udhcpd processes still running\r\n");
        fully_stopped = false;
    }

    // Check for PID files
    if (stat("/var/run/udhcpd.eth0.pid", &st) == 0 ||
        stat("/var/run/udhcpd.wlan0.pid", &st) == 0 ||
        stat("/var/run/udhcpd.eth0.launcher.pid", &st) == 0) {
        PRINTF("[Power - WARNING: udhcpd PID files still present\r\n");
        fully_stopped = false;
    }

    if (fully_stopped) {
        PRINTF("[Power - DHCP server fully stopped and cleaned up\r\n");
    }

    return fully_stopped;
}
```

#### Addition 2: Integrate into POWER_STATE_CELLULAR_SHUTDOWN (Modify lines 477-492)

**Current Code:**
```c
case POWER_STATE_CELLULAR_SHUTDOWN:
    /*
     * Check if the ignition is back on, if then back to normal operation.
     * MM2 Note: Abort recovery is automatic - emergency files will be cleaned up
     */
    if (ignition == true)
    {
        power_state = POWER_STATE_READ_DATA;
        PRINTF("[Power - Ignition ON: Abort recovery will be automatic via MM2\r\n");
        break;
    }
    PRINTF("[Power - Shutting down cellular modem\n");
    set_sms_wakeup();
    last_power_time = current_time;
    power_state = POWER_STATE_SHUTDOWN;
    break;
```

**New Code:**
```c
case POWER_STATE_CELLULAR_SHUTDOWN:
    /*
     * Check if the ignition is back on, if then back to normal operation.
     * MM2 Note: Abort recovery is automatic - emergency files will be cleaned up
     */
    if (ignition == true)
    {
        power_state = POWER_STATE_READ_DATA;
        PRINTF("[Power - Ignition ON: Abort recovery will be automatic via MM2\r\n");
        break;
    }

    // Stop DHCP server before cellular and system shutdown
    PRINTF("[Power - Phase 1: Stopping network services\r\n");
    stop_dhcp_server();
    verify_dhcp_stopped();  // Log status but don't block on failures

    // Continue with cellular shutdown
    PRINTF("[Power - Phase 2: Shutting down cellular modem\r\n");
    set_sms_wakeup();

    last_power_time = current_time;
    power_state = POWER_STATE_SHUTDOWN;
    break;
```

#### Addition 3: Update cli_power_state() Display (Modify lines 684-705)

**Add after line 689 in POWER_STATE_CELLULAR_SHUTDOWN display:**

```c
case POWER_STATE_CELLULAR_SHUTDOWN:
    {
        bool cellular_down = get_cellular_power_down();
        uint32_t elapsed = imx_time_difference(current_time, last_power_time);
        uint32_t remaining = (elapsed < CELLULAR_POWER_DOWN_TIMEOUT) ?
                           (CELLULAR_POWER_DOWN_TIMEOUT - elapsed) : 0;

        imx_cli_print("Status: Shutting down network services and cellular modem\r\n");

        // NEW: Add DHCP server status
        int dhcp_ret = system("sv check udhcpd >/dev/null 2>&1");
        imx_cli_print("DHCP Server: %s\r\n", (dhcp_ret == 0) ? "Running" : "Stopped");

        imx_cli_print("Cellular Power: %s\r\n", cellular_down ? "DOWN" : "UP");
        imx_cli_print("Elapsed: %u.%u seconds\r\n", elapsed / 1000, (elapsed % 1000) / 100);
        imx_cli_print("Timeout: %u.%u seconds remaining\r\n", remaining / 1000, (remaining % 1000) / 100);

        if (cellular_down) {
            imx_cli_print("Condition: Network services and cellular powered down\r\n");
        } else if (remaining == 0) {
            imx_cli_print("Condition: Timeout reached - forcing shutdown\r\n");
        } else {
            imx_cli_print("Waiting: For network cleanup and cellular modem power down\r\n");
        }
        imx_cli_print("Next: Will %s system\r\n", icb.reboot ? "REBOOT" : "POWER DOWN");
    }
    break;
```

### File: Fleet-Connect-1/power/process_power.h

#### Addition: Add include for stat() function

**Add after line 32:**
```c
#include <sys/stat.h>
#include <unistd.h>  // For usleep()
```

---

## Testing Strategy

### Test Scenario 1: Normal Shutdown (Ignition Off)

**Setup:**
- Both eth0 and wlan0 configured as DHCP servers
- System running normally with ignition ON
- DHCP clients connected to both interfaces

**Test Steps:**
1. Turn ignition OFF
2. Monitor power state transitions
3. Observe DHCP server shutdown timing
4. Verify processes terminated
5. Verify clean system shutdown

**Expected Results:**
- DHCP server stops during CELLULAR_SHUTDOWN state
- All udhcpd processes terminated
- All PID files removed
- System shuts down cleanly
- No orphaned processes

**Verification Commands:**
```bash
# Monitor power state
while true; do
    ./Fleet-Connect-1 -c "power"
    sleep 2
done

# Monitor DHCP processes
watch -n 1 'ps | grep udhcpd'

# Check PID files
watch -n 1 'ls -la /var/run/udhcpd*.pid'

# Monitor service status
watch -n 1 'sv status udhcpd'
```

### Test Scenario 2: Ignition Abort During Shutdown

**Setup:**
- Ignition OFF, shutdown in progress
- DHCP server stopped
- Cellular modem shutting down

**Test Steps:**
1. Start shutdown sequence
2. Wait for CELLULAR_SHUTDOWN state
3. Turn ignition ON (abort shutdown)
4. Verify system recovery
5. Check DHCP server status

**Expected Results:**
- Power state returns to READ_DATA
- DHCP server should be restarted (manual or automatic?)
- System resumes normal operation

**Important Question**: Should DHCP server be automatically restarted when shutdown is aborted?

**Current Behavior**:
- Cellular modem is automatically restarted via `cellular_re_init()`
- DHCP server is NOT automatically restarted

**Recommendation**: Add DHCP server restart in abort path:
```c
if (ignition == true)
{
    power_state = POWER_STATE_READ_DATA;

    // Restart network services
    cellular_re_init();  // Existing

    // NEW: Restart DHCP server if it was running
    system("sv start udhcpd");  // Will start if configured, no-op if not

    PRINTF("[Power - Ignition ON: System recovery complete\r\n");
    break;
}
```

### Test Scenario 3: Reboot Request

**Setup:**
- System running normally
- Reboot requested via CLI or API

**Test Steps:**
1. Issue reboot command: `icb.reboot = true`
2. Monitor shutdown sequence
3. Verify DHCP server stops
4. Verify clean reboot
5. Check DHCP server state after reboot

**Expected Results:**
- DHCP server stops during shutdown
- System reboots cleanly
- DHCP server auto-starts on boot (if configured)

### Test Scenario 4: Single Interface Configurations

**Test 4A: eth0 Only**
- Only eth0 configured as DHCP server
- Verify shutdown works correctly

**Test 4B: wlan0 Only**
- Only wlan0 configured as DHCP server
- Verify shutdown works correctly

**Test 4C: No DHCP Server**
- No interfaces configured as DHCP server
- Verify shutdown doesn't fail
- Verify no errors logged

### Test Scenario 5: Service Not Installed

**Setup:**
- `/etc/sv/udhcpd` directory does not exist
- DHCP server not configured

**Test Steps:**
1. Initiate shutdown
2. Verify graceful handling
3. Check for error messages

**Expected Results:**
- Shutdown continues without error
- Log shows "service not installed, skipping"
- No blocking or failures

### Test Scenario 6: Timing Validation

**Objective**: Ensure DHCP shutdown doesn't delay critical operations

**Measurements:**
1. Time from FLUSH_DISK completion to CELLULAR_SHUTDOWN entry
2. Time for `sv stop udhcpd` to complete
3. Total time from shutdown start to system halt

**Expected Timing:**
- DHCP shutdown: < 1 second
- No impact on data preservation timing
- No significant increase in total shutdown time

---

## Rollback Procedures

### If Implementation Causes Issues

**Immediate Rollback** (No Code Changes):
1. Disable DHCP server shutdown:
   ```bash
   # Comment out stop_dhcp_server() call in code
   # Or remove udhcpd service directory
   rm -rf /etc/sv/udhcpd
   ```

2. Restore previous behavior:
   - DHCP server continues running during shutdown
   - Runit will terminate udhcpd on system halt
   - Not ideal but functional

**Code Rollback** (Revert Changes):
1. Remove `stop_dhcp_server()` function
2. Remove `verify_dhcp_stopped()` function
3. Restore original CELLULAR_SHUTDOWN case
4. Restore original cli_power_state() display
5. Rebuild and deploy

### Potential Issues and Mitigations

**Issue 1**: DHCP shutdown delays critical operations
- **Mitigation**: Add timeout (already included - 500ms)
- **Fallback**: Skip verification, continue shutdown

**Issue 2**: Ignition abort doesn't restart DHCP
- **Mitigation**: Add restart in abort paths
- **Fallback**: Manual restart required

**Issue 3**: Service command fails
- **Mitigation**: Error handling, continue shutdown
- **Fallback**: Runit cleans up on system halt

---

## Additional Considerations

### 1. DHCP Server Restart on Abort

**Current Analysis**:
- Shutdown can be aborted if ignition returns ON
- Cellular modem is restarted automatically
- DHCP server is NOT automatically restarted

**Recommendation**: Add DHCP restart to all abort paths

**Locations to Update**:
- POWER_STATE_FLUSH_RAM (line 407-412)
- POWER_STATE_FLUSH_DISK (line 444-449)
- POWER_STATE_CELLULAR_SHUTDOWN (line 482-487)
- POWER_STATE_SHUTDOWN (line 494-501)
- POWER_DOWN_STATE (line 564-571)

**Code Pattern**:
```c
if (ignition == true)
{
    power_state = POWER_STATE_READ_DATA;

    // Restart communication services
    cellular_re_init();
    system("sv start udhcpd");  // NEW: Restart DHCP server

    PRINTF("[Power - Ignition ON: System recovery complete\r\n");
    break;
}
```

### 2. Logging and Diagnostics

**Enhanced Logging Needed**:
1. Log when DHCP shutdown starts
2. Log when DHCP shutdown completes
3. Log if DHCP server not installed
4. Log if verification fails
5. Add to power state CLI display

**Debug Flag**:
- Use existing DEBUGS_APP_POWER flag
- All DHCP shutdown messages use PRINTF() macro

### 3. Error Handling Philosophy

**Principle**: DHCP shutdown must NEVER block system shutdown

**Implementation**:
- All functions return success (0) even on errors
- Errors logged but not fatal
- Verification logs warnings but continues
- Timeouts used to prevent blocking

### 4. Service Dependencies

**Current Service Architecture**:
```
hostapd (for wlan0 AP mode)
    ↓
udhcpd (DHCP server)
    ↓
System Shutdown
```

**Shutdown Order**:
1. udhcpd (this implementation)
2. hostapd (existing - handled by runit)
3. Cellular modem (existing)
4. System halt/reboot (existing)

**Note**: Runit will handle service dependencies automatically

### 5. Performance Impact

**Expected Impact**: Minimal
- `sv stop` completes in < 1 second
- Finish script runs quickly (kill + rm)
- Total delay: < 1 second
- No impact on data preservation timing

**Validation**: Measure actual timing during testing

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review current power management code
- [ ] Verify udhcpd service architecture
- [ ] Understand runit service management
- [ ] Document current shutdown timing
- [ ] Prepare test environment

### Implementation
- [ ] Add stop_dhcp_server() function
- [ ] Add verify_dhcp_stopped() function
- [ ] Modify POWER_STATE_CELLULAR_SHUTDOWN
- [ ] Update cli_power_state() display
- [ ] Add DHCP restart to abort paths
- [ ] Add includes to header file
- [ ] Review all code changes
- [ ] Build and compile

### Testing
- [ ] Test normal shutdown (ignition off)
- [ ] Test ignition abort scenarios
- [ ] Test reboot request
- [ ] Test single interface configurations
- [ ] Test service not installed scenario
- [ ] Validate timing measurements
- [ ] Test regression scenarios

### Documentation
- [ ] Update power management documentation
- [ ] Document DHCP shutdown behavior
- [ ] Add troubleshooting guide
- [ ] Create operator guide section
- [ ] Update CLI command documentation

### Deployment
- [ ] Create deployment package
- [ ] Prepare rollback procedure
- [ ] Test on target hardware
- [ ] Validate in production-like environment
- [ ] Get approval for deployment
- [ ] Deploy to production
- [ ] Monitor for issues

---

## Summary

This implementation plan provides a complete, production-ready approach to integrating DHCP server shutdown into the Fleet-Connect-1 graceful power-down sequence.

**Key Strengths**:
1. ✅ **Minimal Code Changes**: Only 2 new functions + small modifications
2. ✅ **No Blocking**: Errors don't prevent shutdown
3. ✅ **Comprehensive Testing**: All scenarios covered
4. ✅ **Easy Rollback**: Simple to revert if needed
5. ✅ **Well Documented**: Clear implementation guide
6. ✅ **Timing Optimized**: Shutdown after data preserved, before system halt

**Integration Point Summary**:
- **State**: POWER_STATE_CELLULAR_SHUTDOWN
- **Timing**: After all data flushed, before system halt
- **Method**: `sv stop udhcpd` via runit
- **Duration**: < 1 second
- **Recovery**: Automatic restart on abort

**Next Steps**:
1. Review this plan with development team
2. Get approval for implementation
3. Begin Phase 1: Add DHCP shutdown functions
4. Proceed through phases 2-3 with testing
5. Deploy to test environment
6. Validate and deploy to production

---

**End of Implementation Plan**
