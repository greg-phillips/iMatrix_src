# Network Stability Issues - Developer Handoff Document

**Date:** November 16, 2025
**Branch:** `bugfix/network-stability`
**Status:** Main loop lockup FIXED, Network issues remain
**For:** New developer continuing network stability work

---

## Current State

### What's Working ✓

1. **Main Loop Stability**: System runs 24+ minutes without lockups (GPS race condition fixed)
2. **Diagnostic Tools**: Complete mutex tracking and breadcrumb diagnostics in place
3. **GPS Processing**: Fixed race conditions in NMEA processing
4. **Thread Safety**: 7 mutexes tracked, showing healthy lock statistics

### What Needs Work ✗

1. **Network State Machine**: State transition deadlocks preventing recovery
2. **Cellular/PPP0**: Connection failures (connect script continuously failing)
3. **WiFi Stability**: Unnecessary disconnections and forced reassociations
4. **Interface Selection**: Logic not finding available interfaces

---

## Background - How We Got Here

### Original Problem Statement

The system had TWO major issues:
1. Main loop lockups (FIXED)
2. Network connection failures (PENDING)

We discovered the main loop issue was caused by GPS race conditions, NOT network problems. However, the network logs revealed significant stability issues that need addressing.

### Log Analysis Summary

Analyzed logs: net1.txt (814KB), net2.txt (810KB), net3.txt (287KB), net4.txt (140KB), net5.txt (776KB)

**Common patterns found:**
- State machine gets stuck in NET_SELECT_INTERFACE trying to return to NET_INIT
- PPP0 connect script fails repeatedly (~128 failures in net3.txt)
- WiFi disconnects unnecessarily when link might recover naturally
- Circular buffer errors appear when main loop can't keep up with GPS data

---

## Network Issues Detailed Analysis

### Issue #1: State Machine Transition Deadlock

**Symptom:**
```
[NETMGR] State: NET_SELECT_INTERFACE | No interface found, returning to NET_INIT
[NETMGR] State: NET_SELECT_INTERFACE | Invalid transition from SELECT_INTERFACE to NET_INIT
[NETMGR] State: NET_SELECT_INTERFACE | State transition blocked: NET_SELECT_INTERFACE -> NET_INIT
```

**Occurrence:** 20+ times in net3.txt when no interfaces available

**Root Cause:**
State machine validation prevents NET_SELECT_INTERFACE → NET_INIT transition even when it's necessary (no interfaces available, need to reset and start over).

**Impact:**
System stuck in NET_SELECT_INTERFACE state, continuously checking interfaces but unable to reset.

**Recommended Fix:**

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

Add special case in state transition validation:

```c
static bool is_valid_transition(netmgr_state_t from, netmgr_state_t to, netmgr_ctx_t* ctx)
{
    // Allow return to INIT when stuck with no interfaces
    if (to == NET_INIT) {
        if (from == NET_SELECT_INTERFACE && !any_interface_available(ctx)) {
            return true;  // Allow reset when stuck
        }
        if (from == NET_ONLINE && current_interface_invalid(ctx)) {
            return true;  // Allow reset when connection lost
        }
    }

    // Existing validation logic...
}

// Add helper function
static bool any_interface_available(netmgr_ctx_t* ctx)
{
    for (uint32_t i = 0; i < IFACE_COUNT; i++) {
        if (!ctx->states[i].disabled &&
            (ctx->states[i].link_up || has_valid_ip_address(if_names[i]))) {
            return true;
        }
    }
    return false;
}
```

**Testing:** Reproduce net3.txt scenario (no interfaces), verify state machine can reset to NET_INIT.

---

### Issue #2: PPP0 Connection Failures

**Symptom:**
```
[NETMGR-PPP0] PPP0 not ready (device=missing, pppd=running), waiting (4211 ms elapsed)
[NETMGR-PPP0] PPP0 connect script likely failing - no device after 34004 ms
pppd[2423]: Connect script failed  (repeated 128+ times)
```

**Occurrence:** Continuous failures every ~22 seconds

**Root Cause:**
PPP connect script fails to establish ppp0 network device despite:
- Cellular modem ready (cellular_ready=YES)
- PPPD daemon running (cellular_started=YES)
- But ppp0 device never appears (has_ip=NO)

**Impact:**
Cellular fallback completely non-functional, system cannot use cellular when WiFi fails.

**Recommended Fix:**

**Option A: Enhanced Logging**
Add detailed logging to PPP connect script to identify failure point:

```bash
#!/bin/bash
# /etc/ppp/peers/cellular-connect
echo "Connect script starting at $(date)" >> /var/log/ppp-connect.log

# Check modem device
if ! [ -c /dev/ttyACM2 ]; then
    echo "ERROR: Modem device /dev/ttyACM2 not available" >> /var/log/ppp-connect.log
    exit 1
fi

# Test AT communication
timeout 5 echo -e "AT\r" > /dev/ttyACM2 || {
    echo "ERROR: AT command timeout" >> /var/log/ppp-connect.log
    exit 1
}

# Continue with detailed logging...
```

**Option B: Monitor Connect Script Status**
**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

Add monitoring of connect script log file to identify failures:

```c
static void check_ppp_connect_status(imx_time_t current_time)
{
    static imx_time_t last_check = 0;

    if (imx_time_difference(current_time, last_check) > 5000) {
        FILE* log = fopen("/var/log/ppp-connect.log", "r");
        if (log) {
            // Check last line for "ERROR:"
            // Log to diagnostics if found
            fclose(log);
        }
        last_check = current_time;
    }
}
```

**Testing:** Enable cellular, monitor connect script log, identify exact failure point.

---

### Issue #3: WiFi Unnecessary Disconnections

**Symptom:**
```
[WIFI_REASSOC] Starting wpa_cli reassociation on wlan0
[WIFI_REASSOC] Executing: wpa_cli -i wlan0 disconnect
Kernel: wlan0: deauthenticating from 16:18:d6:22:21:2b by local choice (Reason: 3=DEAUTH_LEAVING)
[NETMGR] Started cooldown of: wlan0 for 10 seconds
```

**Occurrence:** 3-8 times per test when WiFi link drops briefly

**Root Cause:**
When WiFi link goes down temporarily, system immediately forces disconnect/reassociation instead of waiting for natural recovery. The forced disconnect compounds the problem by putting WiFi into cooldown.

**Impact:**
Service interruptions from unnecessary WiFi cycling, delays recovery.

**Recommended Fix:**

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

Add grace period before forcing WiFi disconnect (user approved 15 seconds):

```c
#define WIFI_LINK_DOWN_GRACE_PERIOD_MS  (15000)  // 15 seconds

static void monitor_wifi_link_state(netmgr_ctx_t *ctx, imx_time_t current_time)
{
    iface_state_t* wifi_state = &ctx->states[IFACE_WIFI];

    if (!wifi_state->link_up) {
        uint32_t down_duration = imx_time_difference(current_time, wifi_state->last_ping_time);

        // Give WiFi time to recover before forcing reassociation
        if (down_duration < WIFI_LINK_DOWN_GRACE_PERIOD_MS) {
            if (has_valid_ip_address("wlan0")) {
                PRINTF_WIFI0("WiFi link down but has IP, waiting for recovery (%u ms)",
                             down_duration);
                return;  // Don't force reassociation yet
            }
        }

        // Only force reassociation after grace period
        if (down_duration >= WIFI_LINK_DOWN_GRACE_PERIOD_MS) {
            PRINTF_WIFI0("WiFi link down for %u ms, forcing reassociation", down_duration);
            // ... existing reassociation code ...
        }
    }
}
```

**Testing:** Temporarily disconnect WiFi AP, verify system waits 15s before forcing reassociation.

---

### Issue #4: Interface Selection Logic Flaws

**Symptom:**
```
[COMPUTE_BEST] Current interface states:
  wlan0: active=YES, link_up=NO, score=0, latency=0
[COMPUTE_BEST] Final result: NO_INTERFACE_FOUND - all interfaces down or inactive
```

But wlan0 has valid IP address (10.2.0.169)!

**Root Cause:**
COMPUTE_BEST algorithm rejects interfaces where `link_up=NO` even if they have valid IP addresses. The link_up flag can be stale after a failed ping test, but the interface is actually working.

**Impact:**
System fails to use working interfaces, unnecessarily switches or goes offline.

**Recommended Fix:**

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

Modify compute_best_interface() to consider interfaces with valid IPs:

```c
static uint32_t compute_best_interface(netmgr_ctx_t* ctx, imx_time_t now)
{
    for (uint32_t i = 0; i < IFACE_COUNT; i++) {
        iface_state_t* state = &ctx->states[i];

        if (state->disabled || in_cooldown(state, now)) {
            continue;
        }

        // Consider interface if link is up OR has valid IP
        bool has_ip = has_valid_ip_address(if_names[i]);

        if (state->link_up || has_ip) {
            // Give benefit of doubt to untested interfaces with IPs
            uint32_t effective_score = state->score;
            if (!state->test_attempted && has_ip) {
                effective_score = MIN_ACCEPTABLE_SCORE;
            }

            // Update best selection logic...
        }
    }
    // ...
}
```

**Testing:** Set up scenario where interface has IP but link_up=NO, verify interface is selected.

---

## Architecture Overview

### Network Manager (`process_network.c`)

**State Machine:**
```
NET_INIT
  ↓
NET_SELECT_INTERFACE (select best: eth0 → wlan0 → ppp0)
  ↓
NET_WAIT_RESULTS (wait for ping tests)
  ↓
NET_REVIEW_SCORE (evaluate ping results)
  ↓
NET_ONLINE (active connection)
  ↓
NET_ONLINE_CHECK_RESULTS (periodic health checks)
  ↓
NET_ONLINE_VERIFY_RESULTS (verify connection quality)
```

**Key Functions:**
- `process_network()` - Main state machine (line ~2200)
- `compute_best_interface()` - Interface selection algorithm
- `launch_ping_thread()` - Spawn detached ping tests
- `execute_ping()` - Run ping and parse results

**State Files:**
- `process_network.c` - Main state machine (~5500 lines)
- `cellular_man.c` - Cellular modem control via AT commands
- `network_utils.c` - Helper functions
- `wifi_reassociate.c` - WiFi reconnection logic

### Cellular System (`cellular_man.c`)

**Responsibilities:**
- Initialize cellular modem via AT commands
- Scan for carriers, select best non-blacklisted
- Establish data connection
- Set flags that process_network monitors
- Black list carriers on connection failure

**Integration with Network Manager:**
- process_network checks cellular_ready, cellular_started, has_ip flags
- If PPP0 connection fails, process_network blacklists the carrier
- cellular_man responsible for selecting next non-blacklisted carrier

---

## Diagnostic Tools Available

### 1. Mutex Tracking

**Command:** `mutex` or `mutex verbose`

**Shows:**
- All 7 tracked mutexes
- Lock counts, durations, contentions
- Currently locked mutexes with holding function
- Statistics for debugging contention

**Use When:**
- Suspecting mutex deadlock
- Analyzing lock contention
- Debugging threading issues

### 2. Main Loop Breadcrumbs

**Command:** `app` then `loopstatus`

**Shows:**
- Handler position (0-3): Where in imx_process_handler()
- imx_process position: Where in imx_process() state machine
- do_everything position: Where in main processing loop
- Time at each position
- Loop execution count

**Use When:**
- Main loop appears frozen
- Diagnosing blocking operations
- Identifying slow code paths

**Breadcrumb Position Codes:**

**Handler (0-3):**
- 0 = Before imx_process()
- 1 = After imx_process(), before do_everything()
- 2 = Before do_everything()
- 3 = After do_everything()

**imx_process (0-99):**
- 0 = Entry
- 10-11 = process_network() in PROVISION_SETUP
- 20-21 = process_network() in ESTABLISH_WIFI
- 30-31 = process_network() in NORMAL
- 50-51 = imatrix_upload()
- 60-61 = Diagnostics
- 67 = Before process_location()
- 670 = Entered process_location()
- 6710-6715 = Inside process_nmea()
- 67120-67150 = Inside process_nmea_sentence()
- 70-71 = print_background_messages()
- 99 = Exiting

**do_everything (0-19):**
- 0 = Entry
- 1 = Reboot check
- 2 = CS config check
- 3 = GPS event check
- 4 = GPS write
- 5 = GPIO read
- 6 = Accelerometer
- 7 = Power management
- 8 = CAN product check
- 9 = OBD2 process
- 10 = EV abstraction
- 11 = Gateway sample
- 12-13 = Trip/energy
- 14 = CAN debug display
- 15-17 = CLI monitors
- 18 = Async log flush
- 19 = Exit

### 3. Thread and Timer Tracking

**Command:** `threads` or `threads -v`

**Shows:**
- All active threads with status
- Thread creation times and creators
- Stack sizes
- Timer execution statistics
- Health metrics (late/missed counts)

**Use When:**
- Checking if threads are blocked
- Verifying timer execution
- Diagnosing scheduling issues

---

## Code Locations for Network Fixes

### State Machine Transition Logic

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

**Key Functions:**
- `is_valid_transition()` - State transition validation (needs fix for NET_INIT)
- `netmgr_state_name()` - Human-readable state names
- Line ~2200: Main process_network() state machine

**Debug Flags:**
- `DEBUGS_FOR_ETH0_NETWORKING` (0x00020000)
- `DEBUGS_FOR_WIFI0_NETWORKING` (0x00040000)
- `DEBUGS_FOR_PPP0_NETWORKING` (0x00080000)
- `DEBUGS_FOR_NETWORKING_SWITCH` (0x00100000)

Enable with: `debug 0x001F0000` for all network debugging

### Interface Selection

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

**Function:** `compute_best_interface()` (search for "COMPUTE_BEST" in logs)

**Current Logic:**
1. Skip interfaces in cooldown
2. Skip interfaces with link_up=NO
3. Prefer interfaces with score ≥ 7
4. Fall back to any interface with score ≥ 3

**Needs:** Consider interfaces with valid IP even if link_up=NO

### WiFi Reassociation

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/wifi_reassociate.c`

**Functions:**
- `wifi_reassociate_wpa_cli()` - Uses wpa_cli disconnect/reassociate
- `wifi_reassociate_ifupdown()` - Uses ifdown/ifup
- `wifi_reassociate_network_manager()` - Uses nmcli

**Called From:** `process_network.c` when WiFi link detection shows failure

**Needs:** Add 15-second grace period before forcing reassociation

### Cellular/PPP0

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

**State Machine:** CellularState_t with 26 states

**Key States:**
- CELL_INIT → CELL_CONNECTED → CELL_ONLINE
- Handles AT command communication with modem
- Sets flags: cellular_ready, cellular_started

**Integration:**
- process_network() monitors these flags
- Expects ppp0 device to appear after cellular_started=YES
- Blacklists carrier if connection fails

**Needs:**
- Enhanced logging in connect script
- Timeout handling for failed connections
- Better error reporting from AT command layer

---

## Testing Procedures

### Basic Network Testing

**1. Ethernet Only:**
```bash
# Disable WiFi and cellular
ifdown wlan0
killall pppd
# Verify eth0 connects and stays connected
```

**2. WiFi Only:**
```bash
# Disable ethernet
ifdown eth0
# Verify WiFi connects and handles link drops gracefully
```

**3. Cellular Only:**
```bash
# Disable eth0 and wlan0
ifdown eth0 wlan0
# Verify cellular connects and ppp0 device appears
```

**4. Failover Testing:**
```bash
# Start with eth0, then disconnect, verify failover to wlan0
# Disconnect wlan0, verify failover to ppp0
# Reconnect wlan0, verify failback from ppp0
```

### Log Collection

**Enable full network debugging:**
```
> debug 0x001F0000
```

**Monitor in real-time:**
```bash
tail -f /var/log/imatrix.log
```

**Collect logs:**
- System startup to first connection
- Interface failover scenarios
- Connection failure and recovery
- At least 30 minutes continuous operation

### Success Criteria

1. ✓ No state machine deadlocks (can always return to NET_INIT)
2. ✓ No main loop lockups (verified with loopstatus)
3. ✓ WiFi reconnects without unnecessary disconnects (15s grace period)
4. ✓ PPP0 connects successfully OR logs detailed failure reason
5. ✓ Interface selection finds available interfaces correctly
6. ✓ Clean logs with understandable state transitions

---

## Development Workflow

### Making Changes

1. **Always test with diagnostics enabled:**
   - Leave mutex tracking ON (ENABLE_MUTEX_TRACKING=ON)
   - Keep breadcrumb positions in code
   - Use loopstatus to verify changes don't block

2. **Before implementing fixes:**
   - Read relevant sections of network manager code
   - Understand current state machine flow
   - Test proposed fix logic with log analysis

3. **After changes:**
   - Build with zero errors/warnings
   - Test on embedded target
   - Collect logs with full debug flags
   - Verify with loopstatus and mutex commands
   - Run for 30+ minutes to ensure stability

### Debug Commands During Testing

```
> debug 0x001F0000              # Enable all network debugging
> net                            # Network status
> mutex verbose                  # Check mutex health
> threads -v                     # Check thread status
> app
app> loopstatus                  # Check main loop position
```

---

## Known Good State

**Build:** FC-1 dated Nov 16 11:55
**Branch:** bugfix/network-stability
**Status:** Main loop stable, GPS fixed, diagnostic tools working

**Mutex Statistics (from stable run):**
- 7 mutexes tracked
- 19,350+ operations
- 0.02% contention rate
- No deadlocks

**System Health:**
- Main loop executing every 100ms
- All threads RUNNING
- Timer health normal
- No circular buffer errors

---

## References

### Documentation
- **CLAUDE.md** - Repository overview and development guidelines
- **debug_network_issue_plan_2.md** - Complete debugging history and fixes
- **debug_network_issue_prompt_2.md** - Original task requirements
- **comprehensive_code_review_report.md** - Code quality analysis
- **CLI_and_Debug_System_Complete_Guide.md** - Debug system usage

### Log Files
- **logs/net1.txt** (814KB) - Extended test with circular buffer errors
- **logs/net2.txt** (810KB) - Similar to net1
- **logs/net3.txt** (287KB) - State machine deadlock, PPP failures
- **logs/net4.txt** (140KB) - First test with mutex tracking
- **logs/net5.txt** (776KB) - GPS buffer error analysis

### Key Source Files
- **process_network.c** (5500 lines) - Network state machine
- **cellular_man.c** (2000+ lines) - Cellular modem control
- **imatrix_interface.c** (2438 lines) - Main iMatrix state machine
- **get_location.c** (820 lines) - GPS data management
- **process_nmea.c** (1600+ lines) - NMEA sentence processing

---

## Questions for Next Developer

Before starting network fixes, answer:

1. **Which network issue to tackle first?**
   - State machine deadlock (highest impact)?
   - PPP0 connection (enable cellular fallback)?
   - WiFi stability (reduce service interruptions)?

2. **Testing environment:**
   - Do you have access to cellular modem for PPP testing?
   - Can you reproduce the state machine deadlock?
   - WiFi AP available for reconnection testing?

3. **Approach preference:**
   - Fix all issues together?
   - One issue at a time with testing between?
   - Start with diagnostics/logging improvements?

---

## Success Story: Main Loop Lockup Fix

**How we diagnosed it:**

1. Started with symptom: "Main loop frozen, GPS buffer errors"
2. Ruled out mutex deadlock: `mutex` showed 0 locked
3. Added breadcrumbs: Found blocking at position 67 (process_location)
4. Narrowed down: Position 6712 (process_nmea_sentence)
5. Agent analysis: Identified GPS circular buffer race condition
6. Fixed: Added nmeaCB_mutex and gps_data_mutex protection
7. Verified: 24+ minutes stable operation

**Key insight:** Breadcrumb diagnostics were critical. Without knowing EXACTLY where the code was stuck (down to specific breadcrumb positions), we couldn't have identified the GPS race condition.

**Lesson:** When debugging complex issues, invest time in diagnostic infrastructure first. The breadcrumbs paid off immediately.

---

## Handoff Summary

**What's Done:**
- ✓ Main loop lockup fixed (GPS race conditions)
- ✓ Mutex tracking infrastructure (7 mutexes)
- ✓ Breadcrumb diagnostics (40+ positions)
- ✓ System stable for 24+ minutes

**What's Next:**
- Network state machine deadlock fix
- PPP0 connection debugging and fix
- WiFi grace period implementation
- Interface selection logic improvements
- Integration testing of all network fixes

**Tools You Have:**
- mutex/mutex verbose - Monitor mutex health
- loopstatus - Pinpoint blocking locations
- threads -v - Check thread status
- Full network debugging flags

**Recommendation:**
Start with the state machine transition fix (easiest, highest impact), then tackle PPP0 and WiFi issues. Test thoroughly between each fix using the diagnostic tools.

Good luck! The diagnostic infrastructure is solid and will help you debug any issues that arise.

---

**Document Prepared By:** Claude Code
**Date:** November 16, 2025
**Build Version:** FC-1 Nov 16 11:55
