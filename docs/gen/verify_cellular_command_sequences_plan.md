# Cellular Command Sequences Analysis Report

**Date:** 2025-12-29
**Author:** Claude Code Analysis
**Status:** Analysis Complete - Awaiting Review
**Document Version:** 1.0

---

## Executive Summary

This document provides a comprehensive analysis of the cellular command sequences in the Fleet Connect 1 system's cellular manager (`cellular_man.c`). The analysis covers the state machine structure, AT command sequences, PPP management, and failure recovery mechanisms for the Telit Cinterion PLS62/63 modem.

---

## 1. System Overview

### 1.1 Hardware Configuration
- **Modem:** Telit Cinterion PLS62-W (LTE Cat 1 with 2G/3G fallback)
- **Serial Port:** `/dev/ttyACM2` (AT commands)
- **PPP Data Port:** `/dev/ttyACM0` (PPP data connection)
- **APN:** `Globaldata.iot`
- **GPIO for Power:** GPIO 89 (hardware modem reset)

### 1.2 Key Files
| File | Purpose |
|------|---------|
| `cellular_man.c` | Main cellular state machine (~5700 lines) |
| `cellular_man.h` | Public API declarations |
| `cellular_blacklist.c` | Carrier blacklisting logic |
| `/etc/start_pppd.sh` | PPP daemon startup script |

---

## 2. State Machine Architecture

### 2.1 State Categories

The cellular manager uses a comprehensive state machine with **48 states** organized into these categories:

#### Initialization States
```
CELL_INIT                    -> Entry point, check for existing PPP
CELL_PURGE_PORT              -> Flush serial port buffer
CELL_PROCIESS_INITIALIZATION -> Send AT command sequence
CELL_GET_RESPONSE            -> Wait for AT response
CELL_PROCESS_RESPONSE        -> Parse AT response
CELL_INIT_AFTER_PPP_STOP     -> Continue init after PPP stopped
```

#### Network Registration States
```
CELL_TEST_NETWORK_SETUP      -> Verify network configuration
CELL_SETUP_OPERATOR          -> Configure operator selection
CELL_PROCESS_OPERATOR_SETUP  -> Process operator response
CELL_INIT_REGISTER           -> Begin registration
CELL_REGISTER                -> Registration in progress
```

#### Online/Connected States
```
CELL_CONNECTED               -> Connected to network
CELL_ONLINE                  -> PPP established, periodic checks
CELL_ONLINE_OPERATOR_CHECK   -> Query current operator (AT+COPS?)
CELL_ONLINE_CHECK_CSQ        -> Query signal strength (AT+CSQ)
```

#### Quick Status States (Phase 6 - Fast Path)
```
CELL_QUICK_STATUS_INIT       -> Open port without killing PPP
CELL_QUICK_STATUS_COPS       -> Query carrier info
CELL_QUICK_STATUS_CSQ        -> Query signal strength
```

#### Operator Scan States (Non-Blocking)
```
CELL_SCAN_STOP_PPP           -> Stop PPP daemon
CELL_SCAN_STOP_PPP_WAIT_SV   -> Wait for sv down
CELL_SCAN_VERIFY_STOPPED     -> Verify PPP stopped
CELL_SCAN_DEREGISTER         -> AT+COPS=2 deregister
CELL_SCAN_WAIT_DEREGISTER    -> Wait for deregister
CELL_SCAN_GET_OPERATORS      -> AT+COPS=? scan
CELL_SCAN_WAIT_RESULTS       -> Wait for operator list
CELL_SCAN_TEST_CARRIER       -> Test specific carrier
CELL_SCAN_WAIT_CSQ           -> Wait for CSQ response
CELL_SCAN_NEXT_CARRIER       -> Move to next carrier
CELL_SCAN_SELECT_BEST        -> Select best operator
CELL_SCAN_CONNECT_BEST       -> Connect to best
CELL_SCAN_START_PPP          -> Wait for COPS response
CELL_SCAN_VERIFY_CARRIER     -> Verify carrier switch
CELL_SCAN_VERIFY_WAIT        -> Wait between verifications
CELL_SCAN_COMPLETE           -> Scan success
CELL_WAIT_PPP_STARTUP        -> Wait for ppp0 interface
CELL_SCAN_FAILED             -> Scan failure handler
```

#### PPP Stop States (Non-Blocking)
```
CELL_STOP_PPP_INIT           -> Send SIGTERM
CELL_STOP_PPP_WAIT           -> Wait 2s for graceful exit
CELL_STOP_PPP_FORCE          -> Send SIGKILL
CELL_STOP_PPP_CLEANUP        -> Remove lock files
CELL_STOP_PPP_EXTENDED       -> Extended cleanup
```

#### Hardware Reset States
```
CELL_HARDWARE_RESET_INIT     -> Close port, export GPIO
CELL_HARDWARE_RESET_GPIO_LOW -> Set GPIO 89 LOW (1s)
CELL_HARDWARE_RESET_GPIO_HIGH-> Set GPIO 89 HIGH (1s)
CELL_HARDWARE_RESET_GPIO_DONE-> Set GPIO 89 LOW
CELL_HARDWARE_RESET_WAIT_BOOT-> Wait for enumeration (30s)
```

---

## 3. AT Command Sequences

### 3.1 Initialization Command Sequence

The modem initialization sends these commands in order:

| Index | Command | Timeout | Purpose |
|-------|---------|---------|---------|
| 0 | `AT` | 5s | Basic modem presence check |
| 1 | `AT+CFUN=1,0` | 10s | Set full functionality (no reset) |
| 2 | `AT&F` | 5s | Reset to factory defaults |
| 3 | `AT+CGDCONT=1,"IP","Globaldata.iot"` | 5s | Set APN context |
| 4 | `AT` | 5s | Verify modem responsive |
| 5 | `ATZ` | 5s | Soft reset |
| 6 | `AT+CMEE=2` | 5s | Enable verbose errors |
| 7 | `AT+CPIN?` | 10s | Check SIM status |
| 8 | `ATI` | 5s | Get modem info |
| 9 | `AT+CFUN=1,0` | 10s | Ensure full functionality |
| 10 | `AT+CGDCONT?` | 10s | Verify APN context |
| 11 | `AT+CGSN` | 20s | Get IMEI |
| 12 | `AT+CNUM` | 20s | Get phone number |
| 13 | `AT+CIMI` | 20s | Get IMSI |
| 14 | `AT+CCID` | 10s | Get SIM ICCID |
| 15 | `AT+COPS=3,2` | 10s | Set numeric operator format |
| 16 | `AT+COPS?` | 10s | Query current operator |
| 17 | `AT+CSQ` | 10s | Query signal strength |
| 18 | `AT+COPS=?` | 180s | Scan available operators |
| 19 | `AT+COPS=1,2,"<operator>"` | 180s | Select specific operator |
| 20 | `AT+CSQ` | 10s | Final signal check |

### 3.2 Periodic Online Check Sequence

Every 60 seconds while online:
```
AT+COPS?  -> Query current operator (timeout: 10s)
AT+CSQ    -> Query signal strength (timeout: 10s)
```

### 3.3 Operator Scan Sequence

```
1. sv down pppd                    # Disable service supervision
2. killall -TERM pppd              # Graceful PPP stop
3. AT+COPS=2                       # Deregister from network (10s)
4. AT+COPS=?                       # Scan operators (180s timeout)
5. For each operator:
   - AT+COPS=1,2,"<operator_id>"   # Connect to operator (10s)
   - AT+CSQ                        # Get signal strength (10s)
6. AT+COPS=1,2,"<best_operator>"   # Select best operator
7. AT+COPS?                        # Verify selection (30s retries)
8. sv up pppd                      # Re-enable service supervision
```

### 3.4 Signal Strength (CSQ) Interpretation

Response format: `+CSQ: <rssi>,<ber>`

| RSSI Value | dBm | Signal Quality |
|------------|-----|----------------|
| 0 | -113 dBm | Marginal |
| 1 | -111 dBm | Marginal |
| 2-30 | -109 to -53 dBm | Varies (formula: -113 + 2*rssi) |
| 31 | -51 dBm or better | Excellent |
| 99 | Unknown | Not detectable |

| BER Value | Bit Error Rate |
|-----------|----------------|
| 0 | < 0.2% |
| 1 | 0.2% to 0.4% |
| 2 | 0.4% to 0.8% |
| 3 | 0.8% to 1.6% |
| 4 | 1.6% to 3.2% |
| 5 | 3.2% to 6.4% |
| 6 | 6.4% to 12.8% |
| 7 | > 12.8% |
| 99 | Unknown |

---

## 4. PPP Service Management

### 4.1 PPP Start Sequence (`start_pppd()`)

```
1. Check for previous chat script failures (detect_and_handle_chat_failure)
2. Check if pppd already running (pidof pppd)
3. Remove stale lock file: /var/lock/LCK..ttyACM0
4. If first start:
   - Execute /etc/start_pppd.sh
5. Else:
   - Execute: sv restart pppd
   - Fallback to script if sv fails
6. Increment pppd_start_count
```

### 4.2 PPP Stop Sequence (`stop_pppd()` / Non-Blocking States)

```
CELL_STOP_PPP_INIT:
  1. Check if pppd running (pidof pppd)
  2. Send SIGTERM: killall -TERM pppd
  3. Start 2-second timer

CELL_STOP_PPP_WAIT:
  4. Poll pidof pppd until exit or timeout
  5. After 2 seconds, transition to FORCE

CELL_STOP_PPP_FORCE:
  6. Send SIGKILL: killall -9 pppd

CELL_STOP_PPP_CLEANUP:
  7. Remove lock files:
     - /var/lock/LCK..ttyACM2
     - /var/lock/LCK..ttyACM0
  8. Update counters
  9. Notify network manager: imx_notify_pppd_stopped()
```

### 4.3 Service Supervisor Commands

| Command | Purpose |
|---------|---------|
| `sv down pppd` | Disable supervision (won't auto-restart) |
| `sv up pppd` | Enable supervision (auto-restart on crash) |
| `sv restart pppd` | Restart the pppd service |

---

## 5. Scenario Analysis

### 5.1 Scenario: First Power-Up (No Existing Connection)

```
State Flow:
CELL_INIT
  -> Check ppp0_has_valid_ip() = false
  -> CELL_STOP_PPP_INIT (ensure clean start)
  -> CELL_INIT_AFTER_PPP_STOP
     -> Close/reopen serial port
     -> prepare_cellular_modem()
     -> open_serial_port("/dev/ttyACM2")
     -> configure_serial_port()
  -> CELL_PURGE_PORT (flush for 2 min)
  -> CELL_PROCIESS_INITIALIZATION
     -> Send AT command sequence (20 commands)
  -> CELL_REGISTER
  -> CELL_ONLINE
     -> set_cellular_now_ready(true)
     -> start_pppd()

Commands Issued:
1. AT, AT+CFUN=1,0, AT&F, AT+CGDCONT, ATZ, AT+CMEE=2
2. AT+CPIN?, ATI, AT+CFUN=1,0, AT+CGDCONT?
3. AT+CGSN, AT+CNUM, AT+CIMI, AT+CCID
4. AT+COPS=3,2, AT+COPS?, AT+CSQ
5. AT+COPS=? (scan), AT+COPS=1,2,"<best>"
6. AT+CSQ (final check)
7. /etc/start_pppd.sh (via start_pppd())
```

### 5.2 Scenario: Power-Up with Existing PPP Connection (Phase 6 Fast-Path)

```
State Flow:
CELL_INIT
  -> Check ppp0_has_valid_ip() = true
  -> CELL_QUICK_STATUS_INIT (fast path!)
     -> open_serial_port("/dev/ttyACM2")
     -> configure_serial_port()
  -> CELL_PURGE_PORT (1 second only)
  -> CELL_QUICK_STATUS_COPS
     -> AT+COPS?
  -> CELL_QUICK_STATUS_CSQ
     -> AT+CSQ
     -> set_cellular_now_ready(true)
  -> CELL_ONLINE

Commands Issued:
1. AT+COPS? (query current operator)
2. AT+CSQ (query signal strength)

Note: PPP is NOT stopped - existing connection preserved!
```

### 5.3 Scenario: PPP Failure - Chat Script Error

```
Detection (detect_and_handle_chat_failure):
  - Read /var/log/pppd/current (last 30 lines)
  - Look for:
    - "Can't get terminal parameters" / "I/O error" -> terminal_io_error
    - "+CME ERROR" -> carrier rejection
    - "status = 0x3" -> script bug/timeout
    - "status = 0xb" -> carrier failure

Handling by Error Type:

TERMINAL I/O ERROR:
  -> Cleanup PPP processes
  -> Return to current state (allow retry)
  -> No blacklisting

CME ERROR (Carrier Rejection):
  -> Blacklist current carrier
  -> request_carrier_rescan_rate_limited()
  -> Non-blocking PPP cleanup
  -> Eventually triggers CELL_SCAN_STOP_PPP

SCRIPT TIMEOUT (0x3):
  -> Track consecutive timeouts per carrier
  -> After 3 consecutive: blacklist carrier + rescan
  -> Otherwise: cleanup and retry

CARRIER FAILURE (0xb with CME):
  -> Same as CME ERROR handling
```

### 5.4 Scenario: PPP Failure - Network Loss During Operation

```
State Flow:
CELL_ONLINE
  -> Every 60 seconds: AT+COPS?, AT+CSQ
  -> If network manager detects ppp0 failure:
     -> cellular_update_ppp_health(false, low_score)
     -> After threshold failures in sliding window:
        -> scan_protection_active = false
        -> Scan allowed

Scan Trigger:
  -> cellular_request_rescan = true
  -> should_protect_connection_from_scan() = false (due to failures)
  -> CELL_SCAN_STOP_PPP
     -> Full operator scan sequence
     -> Connect to best available carrier
  -> CELL_SCAN_COMPLETE
  -> CELL_WAIT_PPP_STARTUP
     -> Wait 10s for ppp0 interface
  -> CELL_ONLINE
```

### 5.5 Scenario: Scan with Connection Protection

```
Protection Criteria (should_protect_connection_from_scan):
  1. ppp0_has_valid_ip() = true
  2. Online duration >= 30 seconds
  3. ppp_consecutive_health_passes >= 2
  4. ppp_last_health_score >= 7

If Protected:
  -> SCAN BLOCKED message
  -> Scan request cleared
  -> Remain in current state

Phase 3.1 Enhancement (Sliding Window):
  - Track last 5 health checks
  - Need 3/5 failures to reset protection
  - Tolerates transient network hiccups
```

---

## 6. Timing Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `SCAN_PROTECTION_MIN_ONLINE_TIME` | 30,000 ms | Minimum time online before protection |
| `SCAN_PROTECTION_MIN_HEALTH_CHECKS` | 2 | Min passing health checks |
| `SCAN_PROTECTION_MIN_HEALTH_SCORE` | 7 | Min health score (0-10) |
| `SCAN_PROTECTION_COOLDOWN` | 300,000 ms | 5 min protection cooldown |
| `HEALTH_WINDOW_SIZE` | 5 | Sliding window for health tracking |
| `HEALTH_FAIL_THRESHOLD` | 3 | Failures to reset protection |
| `GPIO_PULSE_WAIT_MS` | 1,000 ms | GPIO pulse timing |
| `MODEM_BOOT_WAIT_MS` | 30,000 ms | Wait for modem after reset |
| `CELLULAR_LINK_CHECK_TIME` | 60 s | Periodic online check interval |
| `MAX_RETRY_BEFORE_RESET` | 10 | Retries before full reinit |
| `MAX_SCAN_RETRIES` | 3 | Scan retry attempts |
| `MAX_SERIAL_ERRORS` | 3 | Errors before hardware reset |
| PPP stop graceful timeout | 2,000 ms | Time for SIGTERM exit |
| PPP startup grace period | 10,000 ms | Wait for ppp0 after scan |

---

## 7. Identified Issues and Gaps

### 7.1 Potential Issues Found

#### Issue 1: Quick Status Path Missing PPP Service Verification (CRITICAL)
**Location:** `CELL_QUICK_STATUS_INIT` and `CELL_INIT` (lines 3807, 5643)
**Severity:** HIGH
**Description:** The Quick Status fast-path only checks `ppp0_has_valid_ip()` (interface IP) but does NOT verify:
1. Whether pppd daemon is actually running (`sv status pppd`)
2. Whether PPP link is connected (check `/var/log/pppd/current` for connectivity)
3. Start pppd service if modem connected but pppd not running

**Current Behavior:**
```
CELL_INIT:
  if (ppp0_has_valid_ip()) {  // Only checks interface IP!
      -> CELL_QUICK_STATUS_INIT
  }
```

**Problem:** The modem automatically powers up and reconnects to the last carrier. The ppp0 interface may have a stale IP from before reboot, or the modem may have connected but pppd isn't running.

**Required Verification Steps:**
```
1. Check if pppd running:    sv status pppd
2. If not running:           start_pppd() or sv up pppd
3. Verify connectivity:      tail -F /var/log/pppd/current (look for "local IP address")
4. Only then proceed with AT+COPS?/AT+CSQ queries
```

**Proposed Fix:**
Add new states or logic in `CELL_QUICK_STATUS_INIT`:
```c
// Step 1: Check if pppd is running
int pppd_status = system("sv status pppd 2>/dev/null | grep -q 'run:'");
if (pppd_status != 0) {
    // pppd not running - need to start it
    PRINTF("[Quick Status - pppd not running, starting service]\r\n");
    start_pppd();  // or sv up pppd
    // Wait for connection verification...
}

// Step 2: Verify PPP link connectivity via log
// Read /var/log/pppd/current for "local IP address" or connection success
```

**Impact:** Without this fix, the system may falsely believe PPP is connected when:
- pppd is not running (stale interface IP)
- pppd is running but connection failed
- Modem connected but PPP hasn't established yet

---

#### Issue 2: Blocking `sleep(2)` in `stop_pppd()`
**Location:** `cellular_man.c:3280`
**Severity:** Medium
**Description:** The `stop_pppd()` function still contains a blocking `sleep(2)` call, even though non-blocking PPP stop states exist.
**Impact:** Blocks main loop for 2 seconds during PPP stop.
**Recommendation:** The non-blocking state machine (CELL_STOP_PPP_*) should be used instead of calling `stop_pppd()` directly.

#### Issue 2: Scan Protection Not Applied to `stop_pppd()` Calls
**Location:** Various places call `stop_pppd()` directly
**Severity:** Low
**Description:** Direct `stop_pppd()` calls bypass the scan protection logic.
**Impact:** PPP could be killed outside the protected scan flow.
**Recommendation:** Audit all `stop_pppd()` call sites.

#### Issue 3: Race Condition in Quick Status Query
**Location:** `CELL_QUICK_STATUS_INIT`
**Severity:** Low
**Description:** If PPP drops between the check in `CELL_INIT` and serial port opening, the quick status path may fail.
**Impact:** May require fallback to full init path.
**Mitigation:** Already implemented - falls back to full init on serial port failure.

### 7.2 Design Observations

#### Observation 1: Comprehensive Protection Mechanisms
The code implements multiple layers of protection:
- Connection protection gate (Phase 1)
- Scan rate limiting (Phase 2)
- Sliding window health tracking (Phase 3.1)
- Quick status fast-path (Phase 6)

#### Observation 2: Non-Blocking Design
The state machine is designed to be non-blocking with:
- State-based PPP stop (no sleep)
- State-based hardware reset
- Timeout-based state transitions

#### Observation 3: Carrier Blacklisting
Carriers are blacklisted for 5 minutes after:
- CME ERROR responses
- 3 consecutive script timeouts
- Connection verification failures during scan

---

## 8. State Machine Diagram (Text-Based)

```
                    +---------------+
                    |   CELL_INIT   |
                    +-------+-------+
                            |
            +---------------+---------------+
            |                               |
      ppp0 has IP?                    No existing PPP
            |                               |
            v                               v
+----------------------+         +-----------------------+
| CELL_QUICK_STATUS_   |         | CELL_STOP_PPP_INIT    |
|        INIT          |         +-----------+-----------+
+----------+-----------+                     |
           |                                 v
           v                    +------------------------+
+----------------------+        | CELL_INIT_AFTER_PPP_   |
| CELL_QUICK_STATUS_   |        |         STOP           |
|        COPS          |        +------------+-----------+
+----------+-----------+                     |
           |                                 v
           v                    +------------------------+
+----------------------+        | CELL_PURGE_PORT        |
| CELL_QUICK_STATUS_   |        +------------+-----------+
|        CSQ           |                     |
+----------+-----------+                     v
           |                    +------------------------+
           |                    | CELL_PROCIESS_         |
           |                    |    INITIALIZATION      |
           |                    +------------+-----------+
           |                                 |
           |                    +------------v-----------+
           |                    |  (AT Command Sequence) |
           |                    +------------+-----------+
           |                                 |
           +-------------+-------------------+
                         |
                         v
                +--------+--------+
                |   CELL_ONLINE   |<---------+
                +--------+--------+          |
                         |                   |
        +----------------+----------------+  |
        |                |                |  |
   Periodic Check   Rescan Request    Failure
        |                |                |
        v                v                v
+---------------+  +-------------+  +-------------+
| AT+COPS?      |  | CELL_SCAN_  |  | Handle Chat |
| AT+CSQ        |  | STOP_PPP    |  | Failure     |
+---------------+  +------+------+  +------+------+
                          |                |
                          v                |
                   +------+------+         |
                   |  Scan Flow  |         |
                   |  (see 5.4)  +---------+
                   +------+------+
                          |
                          v
                   +------+------+
                   | CELL_SCAN_  |
                   |  COMPLETE   |
                   +------+------+
                          |
                          v
                   +------+------+
                   | CELL_WAIT_  |
                   | PPP_STARTUP |
                   +-------------+
```

---

## 9. Recommendations

### 9.1 Code Improvements

1. **Remove blocking sleep in `stop_pppd()`**
   - Replace with non-blocking state machine calls
   - Estimated complexity: Low

2. **Add signal strength threshold for carrier selection**
   - Current: Selects first available carrier with signal
   - Proposed: Require minimum CSQ >= 10 (about -93 dBm)
   - Location: `CELL_SCAN_SELECT_BEST`

3. **Add retry logic for quick status path**
   - If AT+COPS? fails, retry before falling back to full init
   - Current: Immediate fallback on any failure

### 9.2 Monitoring Improvements

1. **Add signal strength trending**
   - Track CSQ over time
   - Trigger rescan if signal degrading below threshold

2. **Add carrier session statistics**
   - Track time on each carrier
   - Track data transferred per carrier
   - Use for carrier selection optimization

### 9.3 Documentation Needs

1. **Network manager integration documentation**
   - Document `cellular_update_ppp_health()` callback
   - Document `imx_notify_pppd_stopped()` callback

2. **Chat script documentation**
   - Document expected chat script behavior
   - Document error codes and recovery

---

## 10. Todo Checklist for Implementation

- [ ] Review this analysis document
- [ ] Confirm accuracy of state machine understanding
- [ ] Decide which issues to address (if any)
- [ ] If implementing changes, create feature branch
- [ ] Build verification after each change
- [ ] Final clean build verification

---

## Appendix A: Key AT Commands Reference (PLS62/63)

| Command | Response | Description |
|---------|----------|-------------|
| `AT` | `OK` | Basic check |
| `AT+CPIN?` | `+CPIN: READY` | SIM status |
| `AT+CSQ` | `+CSQ: rssi,ber` | Signal quality |
| `AT+COPS?` | `+COPS: mode,format,"oper",AcT` | Current operator |
| `AT+COPS=?` | List of operators | Scan operators |
| `AT+COPS=0` | `OK` | Auto operator selection |
| `AT+COPS=1,2,"xxxxx"` | `OK` | Manual operator selection |
| `AT+COPS=2` | `OK` | Deregister from network |
| `AT+CFUN=1,0` | `OK` | Full functionality (no reset) |
| `AT+CGDCONT=1,"IP","apn"` | `OK` | Set PDP context |
| `AT+CGSN` | IMEI | Get IMEI |
| `AT+CIMI` | IMSI | Get IMSI |
| `AT+CCID` | ICCID | Get SIM ICCID |
| `AT+CMEE=2` | `OK` | Enable verbose errors |

---

## 11. Detailed AT Command Traces by Scenario

This section provides complete AT command traces for each operational scenario, showing the exact sequence of commands sent to the modem.

### 11.1 Scenario: Full Startup (No Existing PPP)

**State Flow:** `CELL_INIT` → `CELL_STOP_PPP_INIT` → `CELL_INIT_AFTER_PPP_STOP` → `CELL_PURGE_PORT` → `CELL_PROCIESS_INITIALIZATION` → `CELL_ONLINE`

**PPP Hooks Called:**
1. `sv down pppd` (if pppd running) - Disable supervision
2. `killall -TERM pppd` - Graceful stop
3. `killall -9 pppd` (if needed) - Force kill

**AT Command Sequence:**
```
Step  Command                                    Timeout  Purpose
──────────────────────────────────────────────────────────────────────────
 1    AT                                         5s       Modem presence check
 2    AT+CFUN=1,0                               10s       Set full functionality
 3    AT&F                                       5s       Reset to factory defaults
 4    AT+CGDCONT=1,"IP","Globaldata.iot"         5s       Set APN/PDP context
 5    AT                                         5s       Verify modem responsive
 6    ATZ                                        5s       Soft reset
 7    AT+CMEE=2                                  5s       Enable verbose errors
 8    AT+CPIN?                                  10s       Check SIM status
        Expected: +CPIN: READY
 9    ATI                                        5s       Get modem info
10    AT+CFUN=1,0                               10s       Ensure full functionality
11    AT+CGDCONT?                               10s       Verify APN configured
        Expected: +CGDCONT: 1,"IP","Globaldata.iot"
12    AT+CGSN                                   20s       Get IMEI
13    AT+CNUM                                   20s       Get phone number
14    AT+CIMI                                   20s       Get IMSI
15    AT+CCID                                   10s       Get SIM ICCID
16    AT+COPS=3,2                               10s       Set numeric operator format
17    AT+COPS?                                  10s       Query current operator
        Expected: +COPS: 0,2,"<operator_id>",<AcT>
18    AT+CSQ                                    10s       Query signal strength
        Expected: +CSQ: <rssi>,<ber>
19    AT+COPS=?                                180s       Scan available operators
        Expected: +COPS: (list),(list),...
20    AT+COPS=1,2,"<best_operator>"            180s       Select best operator
        Expected: OK
21    AT+CSQ                                    10s       Final signal check
```

**PPP Hooks Called After Init Complete:**
- `/etc/start_pppd.sh` (first start) - Initialize PPP via script

---

### 11.2 Scenario: Fast Reconnect (Existing PPP/Quick Status)

**State Flow (Current - INCOMPLETE):** `CELL_INIT` → `CELL_QUICK_STATUS_INIT` → `CELL_PURGE_PORT` (1s) → `CELL_QUICK_STATUS_COPS` → `CELL_QUICK_STATUS_CSQ` → `CELL_ONLINE`

**State Flow (Required - With Verification):**
```
CELL_INIT
  → CELL_QUICK_STATUS_INIT
  → CELL_QUICK_STATUS_VERIFY_PPPD  [NEW - verify pppd running]
  → CELL_QUICK_STATUS_VERIFY_LINK  [NEW - verify connectivity via log]
  → CELL_QUICK_STATUS_START_PPPD   [NEW - start if not running]
  → CELL_PURGE_PORT (1s)
  → CELL_QUICK_STATUS_COPS
  → CELL_QUICK_STATUS_CSQ
  → CELL_ONLINE
```

**PPP Hooks Required (Current implementation missing these):**
```
Step  Hook Command                               Purpose
──────────────────────────────────────────────────────────────────────────
 1    sv status pppd                            Check if pppd service running
 2    (If not running): sv up pppd              Start pppd service
      OR: /etc/start_pppd.sh                    First-time initialization
 3    tail -F /var/log/pppd/current             Verify PPP link connected
      (Look for: "local IP address" message)
```

**Complete Verification Sequence (Required):**
```
Step  Command/Check                              Timeout  Purpose
──────────────────────────────────────────────────────────────────────────
 1    ppp0_has_valid_ip()                        --       Check interface has IP
 2    sv status pppd | grep 'run:'               1s       Verify pppd daemon running
        Expected: "run: pppd: (pid XXXX) XXXs"
        If not running: goto step 2a
 2a   sv up pppd OR /etc/start_pppd.sh           5s       Start pppd if not running
 3    Read /var/log/pppd/current                 5s       Verify connectivity
        Look for: "local IP address" (success)
        Look for: "Connect script failed" (failure)
 4    (Open serial port /dev/ttyACM2)            --       Establish AT port
 5    (Purge buffer - 1 second only)             1s       Clear stale data
 6    AT+COPS?                                  10s       Query current operator
        Expected: +COPS: 0,2,"<operator_id>",<AcT>
 7    AT+CSQ                                    10s       Query signal strength
        Expected: +CSQ: <rssi>,<ber>
```

**CURRENT IMPLEMENTATION GAP:** Steps 2, 2a, and 3 are NOT implemented. The modem auto-connects to the last carrier on power-up, but pppd must be verified running and connected.

**Note:** This is the Phase 6 fast-path. After proper verification, only 2 AT commands issued. PPP service must be verified/started.

---

### 11.3 Scenario: Periodic Online Check

**State Flow:** `CELL_ONLINE` → `CELL_ONLINE_OPERATOR_CHECK` → `CELL_ONLINE_CHECK_CSQ` → `CELL_ONLINE`

**PPP Hooks Called:** NONE (periodic check only)

**AT Command Sequence (every 60 seconds):**
```
Step  Command                                    Timeout  Purpose
──────────────────────────────────────────────────────────────────────────
 1    AT+COPS?                                  10s       Verify still registered
        Expected: +COPS: 0,2,"<operator_id>",<AcT>
 2    AT+CSQ                                    10s       Check signal quality
        Expected: +CSQ: <rssi>,<ber>
```

**Note:** If AT+COPS? returns deregistered state or CSQ is 99,99, triggers rescan.

---

### 11.4 Scenario: Carrier Scan Request (Manual or Auto-Triggered)

**State Flow:** `CELL_SCAN_STOP_PPP` → `CELL_SCAN_STOP_PPP_WAIT_SV` → `CELL_SCAN_VERIFY_STOPPED` → `CELL_SCAN_DEREGISTER` → `CELL_SCAN_WAIT_DEREGISTER` → `CELL_SCAN_GET_OPERATORS` → `CELL_SCAN_WAIT_RESULTS` → (loop through carriers) → `CELL_SCAN_SELECT_BEST` → `CELL_SCAN_CONNECT_BEST` → `CELL_SCAN_START_PPP` → `CELL_SCAN_VERIFY_CARRIER` → `CELL_SCAN_COMPLETE` → `CELL_WAIT_PPP_STARTUP`

**PPP Hooks Called (in order):**
```
Phase       Hook Command                          Purpose
──────────────────────────────────────────────────────────────────────────
Pre-Scan    sv down pppd                         Disable auto-restart
Pre-Scan    killall -TERM pppd                   Graceful PPP stop
Pre-Scan    killall -9 pppd (if needed)          Force kill if stuck
Post-Scan   sv up pppd                           Re-enable supervision (starts PPP)
```

**AT Command Sequence:**
```
Step  Command                                    Timeout  Purpose
──────────────────────────────────────────────────────────────────────────
 1    (PPP stopped - see hooks above)            --       Clean up PPP first
 2    AT+COPS=2                                 10s       Deregister from network
        Expected: OK
 3    AT+COPS=?                                180s       Scan all operators
        Expected: +COPS: (1,"Oper A","A","31001",7),(2,"Oper B","B","31002",7),...

 -- For each operator found (loop): --
 4a   AT+COPS=1,2,"<operator_id>"              10s       Connect to operator N
        Expected: OK
 4b   AT+CSQ                                   10s       Get signal for operator N
        Expected: +CSQ: <rssi>,<ber>
 4c   (Store result: operator_id, rssi, ber)
 -- End loop --

 5    (Select best operator by signal strength)
 6    AT+COPS=1,2,"<best_operator_id>"        180s       Connect to best carrier
        Expected: OK

 -- Verification loop (up to 30s): --
 7a   AT+COPS?                                 10s       Verify registration
        Expected: +COPS: 1,2,"<best_operator_id>",<AcT>
 7b   (If modem deregistered): AT+COPS=0       10s       Trigger auto-registration
 -- End verification loop --

 8    (sv up pppd to start PPP - see hooks)
 9    (Wait 10s for ppp0 interface)
```

---

### 11.5 Scenario: PPP Failure - Chat Script Error

**Detection:** Reads `/var/log/pppd/current` for error patterns

**Error Types and AT Commands:**

#### Type A: Terminal I/O Error
**Pattern:** `"Can't get terminal parameters"` or `"I/O error"` in log
**State Flow:** `CELL_STOP_PPP_INIT` → `CELL_STOP_PPP_WAIT` → `CELL_STOP_PPP_CLEANUP` → `CELL_STOP_PPP_EXTENDED` → (return to previous state)

**PPP Hooks Called:**
```
Hook Command                                     Purpose
──────────────────────────────────────────────────────────────────────────
killall -TERM pppd                               Graceful stop
killall -9 pppd (if needed after 2s)            Force kill
kill -9 <runsv_pppd_pid>                         Kill supervisor process
killall -9 tail (pppd logs)                     Clean log monitors
echo "--- Terminal I/O error ---" >> log        Log cleanup marker
```

**AT Commands:** NONE (terminal issue, not modem issue). Returns to previous state.

---

#### Type B: Carrier CME Error
**Pattern:** `"+CME ERROR"` in log
**State Flow:** (cleanup) → `CELL_SCAN_STOP_PPP` (triggers full carrier rescan)

**PPP Hooks Called:**
```
Hook Command                                     Purpose
──────────────────────────────────────────────────────────────────────────
killall -TERM pppd                               Graceful stop
killall -9 pppd (if needed after 2s)            Force kill
kill -9 <runsv_pppd_pid>                         Kill supervisor process
echo "--- Carrier failure (CME) ---" >> log     Log cleanup marker
sv down pppd                                     Disable supervision for scan
-- (Full scan sequence - see 11.4) --
sv up pppd                                       Re-enable after scan
```

**AT Commands:** Full scan sequence (see 11.4), plus carrier is blacklisted for 5 minutes.

---

#### Type C: Script Bug/Timeout (0x3)
**Pattern:** `"status = 0x3"` in log
**State Flow:** (cleanup) → Track consecutive timeouts → After 3: blacklist + rescan

**PPP Hooks Called:**
```
Hook Command                                     Purpose
──────────────────────────────────────────────────────────────────────────
killall -TERM pppd                               Graceful stop
killall -9 pppd (if needed after 2s)            Force kill
kill -9 <runsv_pppd_pid>                         Kill supervisor process
echo "--- Script bug (0x3) ---" >> log          Log cleanup marker
```

**AT Commands:** None for single occurrence. After 3 consecutive: full scan sequence (see 11.4).

---

### 11.6 Scenario: Hardware Reset

**State Flow:** `CELL_HARDWARE_RESET_INIT` → `CELL_HARDWARE_RESET_AFTER_PPP` → `CELL_HARDWARE_RESET_GPIO_LOW` → `CELL_HARDWARE_RESET_GPIO_HIGH` → `CELL_HARDWARE_RESET_GPIO_DONE` → `CELL_HARDWARE_RESET_WAIT_BOOT` → `CELL_INIT`

**PPP Hooks Called:**
```
Hook Command                                     Purpose
──────────────────────────────────────────────────────────────────────────
sv down pppd                                     Disable supervision
killall -TERM pppd                               Graceful stop
killall -9 pppd (if needed after 2s)            Force kill
-- (GPIO 89 pulse: LOW 1s, HIGH 1s, LOW) --
-- (Wait 30s for modem enumeration) --
sv up pppd                                       Re-enable supervision
```

**AT Commands:** NONE during reset. After reset completes and modem re-enumerates, full init sequence (see 11.1) runs.

---

## 12. PPP Script Hook Usage Matrix

This section provides a complete reference of all PPP management hooks and when they are called.

### 12.1 Hook Definitions

| Hook | Command | Purpose |
|------|---------|---------|
| **sv down pppd** | `system("sv down pppd 2>/dev/null")` | Disable runsv supervision - prevents auto-restart |
| **sv up pppd** | `system("sv up pppd 2>/dev/null")` | Enable runsv supervision - enables auto-restart |
| **sv restart pppd** | `system("sv restart pppd")` | Restart pppd via supervisor (subsequent starts) |
| **start_pppd.sh** | `system("/etc/start_pppd.sh")` | First-time PPP initialization script |
| **SIGTERM** | `system("killall -TERM pppd 2>/dev/null")` | Request graceful pppd shutdown |
| **SIGKILL** | `system("killall -9 pppd 2>/dev/null")` | Force kill pppd if SIGTERM fails |
| **runsv kill** | `system("kill -9 <runsv_pid>")` | Kill supervisor process (extended cleanup) |

### 12.2 Hook Usage by State/Scenario

| Scenario | sv status | sv down | SIGTERM | SIGKILL | sv up | sv restart | start_pppd.sh |
|----------|-----------|---------|---------|---------|-------|------------|---------------|
| **Full Init (first start)** | - | - | ✓¹ | ✓² | - | - | ✓ |
| **Subsequent PPP Start** | - | - | - | - | - | ✓ | ✓³ |
| **Quick Status (fast-path)** | ✓⁵ | - | - | - | ✓⁵ | - | ✓⁵ |
| **Periodic Online Check** | - | - | - | - | - | - | - |
| **Carrier Scan** | - | ✓ | ✓ | ✓² | ✓ | - | - |
| **Chat Failure Cleanup** | - | - | ✓ | ✓² | - | - | - |
| **Hardware Reset** | - | ✓ | ✓ | ✓² | ✓ | - | - |
| **System Shutdown** | - | ✓ | ✓ | ✓² | - | - | - |
| **Re-init (link reset)** | - | - | ✓ | ✓² | ✓⁴ | - | - |

**Notes:**
- ¹ Only if pppd already running
- ² Only if SIGTERM doesn't succeed within 2 seconds
- ³ Fallback if sv restart fails
- ⁴ Re-enables supervision after cleanup
- ⁵ **REQUIRED BUT NOT IMPLEMENTED** - Quick Status must verify pppd running and start if needed

### 12.3 Hook Call Locations in Code

| Hook | Function/State | Line (approx) |
|------|----------------|---------------|
| `sv down pppd` | `CELL_SCAN_STOP_PPP` | 4454 |
| `sv down pppd` | `CELL_HARDWARE_RESET_INIT` | 5488 |
| `sv up pppd` | `cellular_re_init()` | 1176 |
| `sv up pppd` | `cellular_re_init()` (early return) | 3772 |
| `sv up pppd` | `CELL_SCAN_COMPLETE` | 5229 |
| `sv up pppd` | `CELL_SCAN_FAILED` | 5291 |
| `sv up pppd` | `CELL_HARDWARE_RESET_WAIT_BOOT` | 5601, 5623 |
| `sv restart pppd` | `start_pppd()` | 3243 |
| `/etc/start_pppd.sh` | `start_pppd()` (first start) | 3233 |
| `/etc/start_pppd.sh` | `start_pppd()` (sv restart fallback) | 3248 |
| `killall -TERM pppd` | `stop_pppd()` | 3277 |
| `killall -TERM pppd` | `CELL_STOP_PPP_INIT` | 5336 |
| `killall -9 pppd` | `stop_pppd()` | 3285 |
| `killall -9 pppd` | `CELL_STOP_PPP_FORCE` | 5374 |
| `killall -9 pppd` | `CELL_SCAN_VERIFY_STOPPED` (timeout) | 4514 |

### 12.4 PPP Start Decision Logic

```
start_pppd() called
        |
        v
   pppd already running?
        |
   yes──┴──no
   |        |
   |        v
   |   pppd_first_start == true?
   |        |
   |   yes──┴──no
   |    |        |
   |    v        v
   |   /etc/   sv restart pppd
   |   start_    |
   |   pppd.sh   failed?
   |    |        |
   |    v    yes─┴─no
   |   done      |   |
   |             v   v
   |            /etc/ done
   |            start_
   |            pppd.sh
   |             |
   v             v
  SKIP         done
```

### 12.5 PPP Stop State Machine

```
CELL_STOP_PPP_INIT
        |
        v
   pppd running? (pidof)
        |
   no───┴───yes
   |         |
   v         v
   |    killall -TERM pppd
   |    Start 2s timer
   |         |
   |         v
   |    CELL_STOP_PPP_WAIT
   |         |
   |    ┌────┴────┐
   |    |         |
   |   pppd     timeout
   |   exited?   (2s)?
   |    |         |
   |   yes       yes
   |    |         |
   |    v         v
   |    |    CELL_STOP_PPP_FORCE
   |    |         |
   |    |    killall -9 pppd
   |    |         |
   └────┴─────────┘
              |
              v
     CELL_STOP_PPP_CLEANUP
              |
        Remove lock files:
        - /var/lock/LCK..ttyACM2
        - /var/lock/LCK..ttyACM0
              |
        extended_cleanup?
              |
         no───┴───yes
         |         |
         v         v
         |    CELL_STOP_PPP_EXTENDED
         |         |
         |    Kill runsv pppd process
         |    Kill tail log monitors
         |    Log failure type
         |         |
         └─────────┘
              |
              v
        Return to pppd_stop_return_state
```

---

## 13. Summary Tables

### 13.1 AT Commands by Frequency

| Command | Frequency | Scenarios |
|---------|-----------|-----------|
| `AT+CSQ` | Very High | Init, Online Check, Scan (per carrier), Quick Status |
| `AT+COPS?` | High | Init, Online Check, Scan Verify, Quick Status |
| `AT` | Medium | Init (twice), general checks |
| `AT+CFUN=1,0` | Medium | Init (twice) |
| `AT+COPS=1,2,"x"` | Low | Scan (per carrier), Scan Select Best |
| `AT+COPS=?` | Low | Init, Scan |
| `AT+COPS=2` | Rare | Pre-scan deregister |
| `AT+COPS=0` | Rare | Recovery from deregistered state |

### 13.2 PPP Hook Frequency

| Hook | Frequency | Notes |
|------|-----------|-------|
| `sv up pppd` | Medium | After every scan, reset, re-init |
| `killall -TERM pppd` | Medium | Every PPP stop |
| `sv down pppd` | Low | Before scan, hardware reset |
| `sv restart pppd` | Low | Subsequent PPP starts only |
| `/etc/start_pppd.sh` | Rare | First start only (or sv fallback) |
| `killall -9 pppd` | Rare | Only if graceful stop fails |

---

**Document End**

*Generated by Claude Code Analysis*
*Source: cellular_man.c (~5700 lines analyzed)*
*Last Updated: 2025-12-29 (expanded with AT traces and PPP hooks)*
