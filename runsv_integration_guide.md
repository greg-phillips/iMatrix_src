# runsv Integration Guide for PPP Management

**Date**: 2025-11-21
**Document Version**: 1.0
**Purpose**: Integrate cellular_man.c with runsv process supervisor for PPP control

---

## What is runsv?

**runsv** is a process supervisor from the **runit** service management suite.

**Purpose**:
- Automatically starts services on boot
- Monitors service health
- Automatically restarts services if they crash
- Provides service control commands

**Why it's managing pppd**:
- Ensures PPP connection stays up for reliable cellular connectivity
- Restarts on failures (chat script errors, crashes, etc.)
- Critical for production deployment

---

## The Problem

**Current Situation**:
```
cellular_man: "Stop pppd so I can scan!"
  ↓
killall -9 pppd  (force kill)
  ↓
pppd dies
  ↓
runsv: "My service died! Restarting..."  ← Automatic
  ↓
pppd[NEW_PID] starts immediately
  ↓
cellular_man: "pppd still running?!"
  ↓
∞ INFINITE BATTLE ∞
```

**Why killall doesn't work**:
- killall only kills the current process
- runsv immediately spawns a new one
- No way to win by killing alone

---

## runsv/runit Commands

### Service Control via `sv` Command

The `sv` command controls runsv-managed services:

```bash
# Check if sv command exists
which sv
# Usually: /usr/bin/sv or /sbin/sv

# Check service status
sv status pppd

# Stop service (prevents restart)
sv down pppd

# Start service (enables restart)
sv up pppd

# Force stop (immediate, no waiting)
sv force-stop pppd

# Force restart
sv force-restart pppd

# Kill and restart
sv kill pppd

# Send signal
sv term pppd    # SIGTERM
sv kill pppd    # SIGKILL
```

### Service Directory Structure

runsv services are typically in:
```
/etc/sv/pppd/          # Service definition
/etc/service/pppd/     # Enabled service (symlink)
/var/service/pppd/     # Alternative location
```

**Service directory contains**:
- `run` - Script that starts the service
- `down` - If present, service won't auto-start
- `supervise/` - runsv control directory

---

## Integration Requirements

### 1. Check if runsv is Managing pppd

**Command**:
```bash
sv status pppd 2>/dev/null
```

**Expected Output** (if managed):
```
run: pppd: (pid 1234) 567s
```

**Expected Output** (if not managed):
```
fail: pppd: runsv not running
```

**In Code**:
```c
bool is_pppd_supervised(void)
{
    int result = system("sv status pppd >/dev/null 2>&1");
    return (result == 0);  // 0 = supervised, non-zero = not supervised
}
```

### 2. Stop Supervision Temporarily

**Command**:
```bash
sv down pppd
```

**Effect**:
- Stops current pppd process
- Prevents runsv from restarting it
- Service remains "down" until `sv up` called

**Wait for Confirmation**:
```bash
sv status pppd
# Should show: down: pppd: 0s, normally up
```

### 3. Re-Enable Supervision

**Command**:
```bash
sv up pppd
```

**Effect**:
- Tells runsv to manage pppd again
- runsv will start pppd if not running
- Auto-restart enabled again

---

## Implementation Plan

### Phase 1: Detection (Conditional Integration)

**Add to cellular_man.c** (before CELL_SCAN_STOP_PPP):

```c
// Global flag to track if pppd is supervised
static bool pppd_supervised = false;

/**
 * @brief       Check if pppd is managed by runsv supervisor
 * @return:     true if supervised, false otherwise
 */
static bool detect_pppd_supervision(void)
{
    int result = system("sv status pppd >/dev/null 2>&1");

    if (result == 0)
    {
        PRINTF("[Cellular Scan - Detected pppd under runsv supervision]\r\n");
        return true;
    }
    else if (result == 32512)  // sv command not found
    {
        PRINTF("[Cellular Scan - runsv/sv command not available]\r\n");
        return false;
    }
    else
    {
        PRINTF("[Cellular Scan - pppd not supervised by runsv]\r\n");
        return false;
    }
}
```

**Call once at startup** (in CELL_INIT or similar):
```c
pppd_supervised = detect_pppd_supervision();
```

---

### Phase 2: Modified CELL_SCAN_STOP_PPP

**Current** (cellular_man.c:2873-2889):
```c
case CELL_SCAN_STOP_PPP:
    PRINTF("[Cellular Scan - State 1: Stopping PPP]\r\n");

    stop_pppd(true);

    scan_timeout = current_time + 5000;
    scan_retry_count = 0;
    cellular_state = CELL_SCAN_VERIFY_STOPPED;
    break;
```

**New** (with runsv coordination):
```c
case CELL_SCAN_STOP_PPP:
    PRINTF("[Cellular Scan - State 1: Stopping PPP]\r\n");

    // If pppd is supervised, disable auto-restart first
    if (pppd_supervised)
    {
        PRINTF("[Cellular Scan - Disabling runsv supervision for pppd]\r\n");
        int result = system("sv down pppd 2>/dev/null");

        if (result != 0)
        {
            PRINTF("[Cellular Scan - WARNING: sv down pppd failed (result=%d)]\r\n", result);
        }

        // Give runsv time to process the down command
        scan_timeout = current_time + 500;  // 500ms for sv down to take effect
        scan_substep = 0;  // 0=waiting for sv down, 1=stopping pppd
        cellular_state = CELL_SCAN_STOP_PPP_WAIT_SV;
    }
    else
    {
        // Not supervised, stop directly
        stop_pppd(true);
        scan_timeout = current_time + 5000;
        scan_retry_count = 0;
        cellular_state = CELL_SCAN_VERIFY_STOPPED;
    }
    break;
```

### Phase 3: New State - Wait for sv down

**Add State** (after CELL_SCAN_STOP_PPP):
```c
case CELL_SCAN_STOP_PPP_WAIT_SV:
    /*
     * Wait for sv down command to take effect (non-blocking)
     */
    if (imx_is_later(current_time, scan_timeout))
    {
        PRINTF("[Cellular Scan - State 1b: sv down complete, stopping pppd]\r\n");

        // Now safe to stop pppd without runsv restarting it
        stop_pppd(true);

        scan_timeout = current_time + 5000;
        scan_retry_count = 0;
        cellular_state = CELL_SCAN_VERIFY_STOPPED;
    }
    // else: Still waiting for sv down to take effect
    break;
```

### Phase 4: Modified CELL_SCAN_COMPLETE

**Current** (cellular_man.c:3356-3374):
```c
case CELL_SCAN_COMPLETE:
    PRINTF("[Cellular Scan - State 11: Scan complete]\r\n");
    PRINTF("[Cellular Scan - SCAN COMPLETED - PPP operations can resume]\r\n");

    cellular_scanning = false;
    cellular_now_ready = true;
    cellular_link_reset = false;
    scan_failure_count = 0;

    cellular_state = CELL_ONLINE;
    break;
```

**New** (with runsv re-enable):
```c
case CELL_SCAN_COMPLETE:
    PRINTF("[Cellular Scan - State 11: Scan complete]\r\n");
    PRINTF("[Cellular Scan - SCAN COMPLETED - PPP operations can resume]\r\n");

    // Re-enable runsv supervision if it was managing pppd
    if (pppd_supervised)
    {
        PRINTF("[Cellular Scan - Re-enabling runsv supervision for pppd]\r\n");
        system("sv up pppd 2>/dev/null");
        // Note: pppd is already running (we started it in CELL_SCAN_START_PPP)
        // sv up just tells runsv to monitor and restart it if it dies
    }

    cellular_scanning = false;
    cellular_now_ready = true;
    cellular_link_reset = false;
    scan_failure_count = 0;

    cellular_state = CELL_ONLINE;
    break;
```

### Phase 5: Modified CELL_SCAN_FAILED

**Also re-enable supervision on failure**:
```c
case CELL_SCAN_FAILED:
    PRINTF("[Cellular Scan - State 12: Scan failed]\r\n");

    // Re-enable runsv supervision even on failure
    if (pppd_supervised)
    {
        PRINTF("[Cellular Scan - Re-enabling runsv supervision after failure]\r\n");
        system("sv up pppd 2>/dev/null");
    }

    scan_failure_count++;
    // ... rest of failure handling ...
```

---

## Alternative Approach: sv force-stop

### Instead of killall, use sv commands

**Modify stop_pppd()** (cellular_man.c:2161-2215):

**Current**:
```c
void stop_pppd(bool cellular_reset)
{
    if (system("pidof pppd >/dev/null 2>&1") != 0) {
        return;  // Not running
    }

    system("killall -TERM pppd 2>/dev/null");
    sleep(2);

    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        system("killall -9 pppd 2>/dev/null");
    }
    // ...
}
```

**New** (runsv-aware):
```c
void stop_pppd(bool cellular_reset)
{
    // Check if supervised
    bool supervised = (system("sv status pppd >/dev/null 2>&1") == 0);

    if (supervised)
    {
        PRINTF("[Cellular Connection - Stopping supervised pppd via sv]\r\n");

        // Use sv to stop (handles supervision automatically)
        system("sv force-stop pppd 2>/dev/null");

        // Verify
        sleep(1);  // Give it a moment

        if (system("pidof pppd >/dev/null 2>&1") == 0)
        {
            PRINTF("[Cellular Connection - sv force-stop failed, using killall]\r\n");
            system("killall -9 pppd 2>/dev/null");
        }
    }
    else
    {
        // Not supervised, use killall as before
        if (system("pidof pppd >/dev/null 2>&1") != 0) {
            return;
        }

        system("killall -TERM pppd 2>/dev/null");
        sleep(2);

        if (system("pidof pppd >/dev/null 2>&1") == 0) {
            system("killall -9 pppd 2>/dev/null");
        }
    }

    // ... rest of function ...
}
```

---

## Testing runsv Integration

### Test 1: Verify sv Command Availability

**On target hardware**:
```bash
which sv
# Should return: /usr/bin/sv or /sbin/sv

sv --help
# Should show runsv commands
```

**If sv not available**:
- runsv/runit not installed
- Use fallback to killall (current method)
- Document that scan requires manual pppd stop

### Test 2: Check pppd Supervision Status

```bash
sv status pppd
```

**Expected Outputs**:

**If supervised and running**:
```
run: pppd: (pid 1234) 567s
```

**If supervised but down**:
```
down: pppd: 12s, normally up
```

**If not supervised**:
```
fail: pppd: runsv not running
# OR
sv: fatal: unable to change to service directory: file does not exist
```

### Test 3: Test sv down/up Cycle

```bash
# Stop supervision
sv down pppd

# Verify stopped
sv status pppd
# Should show: down: pppd: Ns, normally up

ps aux | grep pppd
# Should show NO pppd processes

# Try to kill (should do nothing)
killall -9 pppd 2>/dev/null
ps aux | grep pppd
# Should STILL show NO processes (runsv not restarting)

# Re-enable supervision
sv up pppd

# Verify restarted
sv status pppd
# Should show: run: pppd: (pid XXXX) 0s

ps aux | grep pppd
# Should show pppd running
```

---

## Required Changes Summary

### Files to Modify

1. **cellular_man.c**
   - Add `pppd_supervised` flag
   - Add `detect_pppd_supervision()` function
   - Modify `CELL_SCAN_STOP_PPP` state
   - Add `CELL_SCAN_STOP_PPP_WAIT_SV` state (new)
   - Modify `CELL_SCAN_COMPLETE` state
   - Modify `CELL_SCAN_FAILED` state
   - Optional: Modify `stop_pppd()` function

2. **cellular_man.h**
   - No changes needed (internal functions only)

3. **State Enum**
   - Add `CELL_SCAN_STOP_PPP_WAIT_SV` state
   - Update state strings array

---

## Dependencies

### Runtime Requirements

**On Target Hardware**:
- ✅ **sv command** (`/usr/bin/sv` or `/sbin/sv`)
- ✅ **runsv** process supervisor running
- ✅ **pppd service** configured in `/etc/sv/pppd/` or similar

**To Check**:
```bash
# Check if sv installed
which sv || echo "sv command not found"

# Check if runsv running
ps aux | grep runsv

# Check pppd service directory
ls -la /etc/sv/pppd/ || ls -la /var/service/pppd/

# Check if pppd supervised
sv status pppd || echo "pppd not supervised"
```

### Build Requirements

**No additional build dependencies**:
- ✅ Uses standard `system()` calls
- ✅ No new libraries needed
- ✅ No header includes required

**Compilation**:
- Standard C (no special flags)
- Compatible with existing build system

---

## Fallback Strategy

### If runsv Not Available

**Detection**:
```c
static bool pppd_supervised = false;

// At startup:
if (system("which sv >/dev/null 2>&1") == 0)
{
    pppd_supervised = detect_pppd_supervision();
}
else
{
    PRINTF("[Cellular Scan - sv command not available, using direct kill]\r\n");
    pppd_supervised = false;
}
```

**Behavior**:
- If `pppd_supervised == true`: Use `sv down/up` commands
- If `pppd_supervised == false`: Use existing `killall` method

**Compatibility**:
- ✅ Works with runsv (when available)
- ✅ Falls back to killall (when runsv not present)
- ✅ No regression on non-supervised systems

---

## Alternative: Stop runsv Entirely

### Nuclear Option (Not Recommended)

**Command**:
```bash
killall runsv  # ❌ Stops ALL supervised services!
```

**Problems**:
- Stops supervision for ALL services (not just pppd)
- May break other critical services
- Requires restarting runsv after scan
- High risk

**Only use if**:
- pppd is the ONLY supervised service
- Absolute last resort
- Thoroughly tested

---

## Code Implementation

### Minimal Integration (Recommended)

**Just add to CELL_SCAN_STOP_PPP**:
```c
case CELL_SCAN_STOP_PPP:
    PRINTF("[Cellular Scan - State 1: Stopping PPP]\r\n");

    // Disable runsv auto-restart (works if sv available, harmless if not)
    system("sv down pppd 2>/dev/null");

    // Small delay for sv down to take effect (non-blocking)
    scan_timeout = current_time + 500;  // 500ms
    cellular_state = CELL_SCAN_STOP_PPP_WAIT_SV;
    break;

case CELL_SCAN_STOP_PPP_WAIT_SV:
    if (imx_is_later(current_time, scan_timeout))
    {
        // Now stop pppd
        stop_pppd(true);

        scan_timeout = current_time + 5000;
        scan_retry_count = 0;
        cellular_state = CELL_SCAN_VERIFY_STOPPED;
    }
    break;
```

**Add to CELL_SCAN_COMPLETE and CELL_SCAN_FAILED**:
```c
// Re-enable supervision (harmless if sv not available)
system("sv up pppd 2>/dev/null");
```

**Advantages**:
- Simple (just add system() calls)
- Graceful degradation (works without sv)
- No complex detection needed
- Low risk

---

## Advanced Integration (Optional)

### Full Detection and Conditional Logic

```c
// At startup (in cellular_man initialization):
static bool pppd_supervised = false;
static bool sv_available = false;

void init_pppd_supervision_detection(void)
{
    // Check if sv command exists
    sv_available = (system("which sv >/dev/null 2>&1") == 0);

    if (sv_available)
    {
        // Check if pppd is actually supervised
        pppd_supervised = (system("sv status pppd >/dev/null 2>&1") == 0);

        if (pppd_supervised)
        {
            PRINTF("[Cellular Init - pppd is managed by runsv supervisor]\r\n");
        }
        else
        {
            PRINTF("[Cellular Init - sv available but pppd not supervised]\r\n");
        }
    }
    else
    {
        PRINTF("[Cellular Init - sv command not available, using direct process control]\r\n");
    }
}

// In CELL_SCAN_STOP_PPP:
if (sv_available && pppd_supervised)
{
    // Use sv commands
}
else
{
    // Use killall
}
```

**Advantages**:
- Precise control
- Detailed logging
- Clear error handling

**Disadvantages**:
- More complex
- More code
- Detection overhead

---

## Recommended Approach

### Option 1: Minimal (RECOMMENDED)

**Just add sv commands everywhere** (2 lines):
```c
// Before stop:
system("sv down pppd 2>/dev/null");

// After scan:
system("sv up pppd 2>/dev/null");
```

**Why**:
- Simplest implementation (5 minutes)
- Works if sv available
- Harmless if sv not available (fails silently with 2>/dev/null)
- No detection overhead
- No complex logic

**Estimated Time**: 30 minutes
**Risk**: MINIMAL

### Option 2: Conditional (If Complexity Needed)

**Detect sv availability, use conditionally**:
- 1 hour implementation
- More robust
- Better logging
- Higher complexity

**Only if**: Minimal approach doesn't work

---

## Testing Procedure

### After Integration

**Test 1**: Verify sv down works
```bash
# Before scan
sv status pppd
# Should show: run: pppd: (pid XXXX) ...

# Trigger scan
echo "cell scan"

# Check during scan
sv status pppd
# Should show: down: pppd: Ns, normally up

# Wait for scan complete
sleep 120

# After scan
sv status pppd
# Should show: run: pppd: (pid XXXX) ...
```

**Test 2**: Verify PPP stops successfully
```bash
# Monitor log during scan
grep "State 2\|VERIFY_STOPPED" /tmp/scan_log.txt

# Should see:
# State 2: PPP stopped successfully  ← Not timeout!
# State 3: Requesting operator list  ← Progress to next state!
```

**Test 3**: Verify scan completes
```bash
grep "State.*Cellular Scan" /tmp/scan_log.txt

# Should see all states:
# State 1, State 2, State 3, State 4, State 5, State 6, State 7,
# State 8, State 9, State 10, State 11
```

---

## Troubleshooting

### If sv down doesn't work

**Check service name**:
```bash
ls /etc/sv/ | grep ppp
# Service might be named differently: pppd, ppp, pppdaemon, etc.
```

**Check service path**:
```bash
ls /var/service/
ls /etc/service/
# Find where services are defined
```

**Manual test**:
```bash
sv down pppd
sleep 1
pidof pppd
# Should return nothing (no processes)
```

### If sv command not found

**Install runit** (if possible):
```bash
apt-get install runit  # Debian/Ubuntu
apk add runit          # Alpine
yum install runit      # RedHat
```

**Or**: Use direct runsv control:
```bash
# Find runsv process for pppd
ps aux | grep "runsv pppd"

# Kill runsv (stops supervision)
kill <runsv_pid>

# Restart runsv after scan
runsv /etc/sv/pppd &
```

---

## Summary of Requirements

### What You Need:

1. **sv command** - Usually in `/usr/bin/sv`
   - Check: `which sv`
   - Install: `apt-get install runit` (if needed)

2. **Understanding of service name**
   - Likely: `pppd`
   - Verify: `sv status pppd`
   - Alternative: `ls /etc/sv/`

3. **Code Changes** (Minimal Approach):
   - Add `system("sv down pppd 2>/dev/null");` before stop
   - Add `system("sv up pppd 2>/dev/null");` after scan
   - Add wait state for sv down to take effect
   - **Total**: ~10 lines of code

4. **Testing Access**:
   - SSH or serial console to target hardware
   - Ability to run sv commands
   - Ability to collect logs

### What You DON'T Need:

- ❌ New libraries or headers
- ❌ Build system changes
- ❌ Kernel modifications
- ❌ Root filesystem changes
- ❌ Complex IPC or signals

---

## Estimated Timeline

| Task | Duration |
|------|----------|
| Detect sv availability | 10 min |
| Add sv down to CELL_SCAN_STOP_PPP | 10 min |
| Add CELL_SCAN_STOP_PPP_WAIT_SV state | 20 min |
| Add sv up to CELL_SCAN_COMPLETE | 5 min |
| Add sv up to CELL_SCAN_FAILED | 5 min |
| Update state enum and strings | 5 min |
| Build and deploy | 10 min |
| **Total Implementation** | **1 hour** |
| **Testing** | **1 hour** |
| **Total** | **2 hours** |

---

## Next Steps

1. **Verify sv command exists on target**:
   ```bash
   ssh <target> "which sv"
   ```

2. **Verify pppd supervised**:
   ```bash
   ssh <target> "sv status pppd"
   ```

3. **If YES**: Implement runsv integration (1-2 hours)
4. **If NO**: Different solution needed (document environment)

---

**Document Version**: 1.0
**Date**: 2025-11-21
**Status**: Ready for implementation pending sv command availability check
**Estimated Time**: 2 hours (implementation + testing)
**Risk**: LOW (graceful degradation if sv not available)
