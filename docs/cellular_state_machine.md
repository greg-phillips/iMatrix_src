# Cellular Manager State Machine Documentation

**Date**: 2025-12-09
**Last Updated**: 2025-12-09
**File**: `cellular_man.c`
**Author**: Claude Code Analysis

---

## Overview

The cellular manager (`cellular_man.c`) implements a comprehensive state machine that controls:
1. Modem initialization and AT command processing
2. Network registration and connection
3. Carrier scanning and selection
4. PPP daemon management
5. Hardware reset procedures
6. SMS handling
7. Power management

---

## State Categories

The states are organized into functional groups:

| Category | States | Purpose |
|----------|--------|---------|
| **Initialization** | CELL_INIT, CELL_PURGE_PORT, CELL_PROCIESS_INITIALIZATION, CELL_INIT_AFTER_PPP_STOP | Modem startup |
| **AT Command** | CELL_GET_RESPONSE, CELL_PROCESS_RESPONSE | Command/response handling |
| **Network Setup** | CELL_TEST_NETWORK_SETUP, CELL_SETUP_OPERATOR, CELL_PROCESS_OPERATOR_SETUP | Operator configuration |
| **Connection** | CELL_CONNECTED, CELL_CONNECT_TO_SELECTED, CELL_TEST_CONNECTION | Connection establishment |
| **Registration** | CELL_INIT_REGISTER, CELL_REGISTER | Network registration |
| **Online** | CELL_ONLINE, CELL_ONLINE_OPERATOR_CHECK, CELL_ONLINE_CHECK_CSQ | Active connection monitoring |
| **Offline** | CELL_DISCONNECTED, CELL_DELAY, CELL_PROCESS_RETRY | Disconnection handling |
| **Scan** | CELL_SCAN_* (18 states including CELL_WAIT_PPP_STARTUP) | Carrier scanning |
| **PPP Monitor** | CELL_WAIT_PPP_INTERFACE, CELL_BLACKLIST_AND_RETRY | PPP establishment monitoring |
| **PPP Stop** | CELL_STOP_PPP_* (5 states) | Non-blocking PPP termination |
| **PPP Continuation** | CELL_INIT_AFTER_PPP_STOP, CELL_HARDWARE_RESET_AFTER_PPP | Resume after PPP stop |
| **Hardware Reset** | CELL_HARDWARE_RESET_* (5 states) | GPIO power cycle |
| **Quick Status** | CELL_QUICK_STATUS_* (3 states) | Fast-path when PPP already up |
| **SMS** | CELL_SET_TEXT_MODE, CELL_FORWARD_SMS_TO_TE, CELL_USE_UCS2_CHARSET | SMS setup |
| **Power** | CELL_SET_LOW_POWER_MODE, CELL_LOW_POWER_MODE, CELL_START_SHUTDOWN | Power management |

---

## Complete State List

### 1. Initialization States

| State | ID | Description |
|-------|----|----|
| `CELL_INIT` | 0 | Entry point - stops PPP, prepares modem |
| `CELL_PURGE_PORT` | 1 | Flush serial port buffers |
| `CELL_PROCIESS_INITIALIZATION` | 2 | Send AT initialization commands |
| `CELL_INIT_AFTER_PPP_STOP` | 49 | Continue init after non-blocking PPP stop |

### 2. AT Command States

| State | ID | Description |
|-------|----|----|
| `CELL_GET_RESPONSE` | 3 | Wait for AT command response |
| `CELL_PROCESS_RESPONSE` | 4 | Parse and handle response |

### 3. Network Setup States

| State | ID | Description |
|-------|----|----|
| `CELL_TEST_NETWORK_SETUP` | 5 | Query network parameters |
| `CELL_SETUP_OPERATOR` | 6 | Configure operator settings |
| `CELL_PROCESS_OPERATOR_SETUP` | 7 | Handle operator setup response |

### 4. Connection States

| State | ID | Description |
|-------|----|----|
| `CELL_CONNECTED` | 8 | Initial connection established |
| `CELL_PROCESS_CSQ` | 9 | Process signal quality response |
| `CELL_CONNECT_TO_SELECTED` | 10 | Connect to selected operator |
| `CELL_TEST_CONNECTION` | 11 | Verify connection quality |

### 5. Registration States

| State | ID | Description |
|-------|----|----|
| `CELL_INIT_REGISTER` | 12 | Initialize registration process |
| `CELL_REGISTER` | 13 | Wait for network registration |

### 6. Online States

| State | ID | Description |
|-------|----|----|
| `CELL_ONLINE` | 14 | Normal operating state |
| `CELL_ONLINE_OPERATOR_CHECK` | 15 | Periodic operator verification |
| `CELL_ONLINE_CHECK_CSQ` | 16 | Periodic signal quality check |

### 7. Offline/Recovery States

| State | ID | Description |
|-------|----|----|
| `CELL_DISCONNECTED` | 17 | Connection lost |
| `CELL_DELAY` | 18 | Timed delay between operations |
| `CELL_PROCESS_RETRY` | 19 | Retry failed operation |

### 8. SMS States

| State | ID | Description |
|-------|----|----|
| `CELL_SET_TEXT_MODE` | 21 | Set SMS to text mode (AT+CMGF=1) |
| `CELL_FORWARD_SMS_TO_TE` | 22 | Enable SMS forwarding (AT+CNMI) |
| `CELL_USE_UCS2_CHARSET` | 23 | Set UCS2 character set |

### 9. Power Management States

| State | ID | Description |
|-------|----|----|
| `CELL_START_SHUTDOWN` | 20 | Begin shutdown sequence |
| `CELL_SET_LOW_POWER_MODE` | 24 | Configure low power settings |
| `CELL_LOW_POWER_MODE` | 25 | Modem in low power state |

### 10. Carrier Scan States (18 states)

| State | ID | Description |
|-------|----|----|
| `CELL_SCAN_STOP_PPP` | 26 | Issue `sv down pppd` |
| `CELL_SCAN_STOP_PPP_WAIT_SV` | 27 | Wait for sv command |
| `CELL_SCAN_VERIFY_STOPPED` | 28 | Verify PPP process ended |
| `CELL_SCAN_DEREGISTER` | 29 | Send AT+COPS=2 to deregister from network |
| `CELL_SCAN_WAIT_DEREGISTER` | 30 | Wait for deregister response |
| `CELL_SCAN_GET_OPERATORS` | 31 | Send AT+COPS=? |
| `CELL_SCAN_WAIT_RESULTS` | 32 | Wait for operator list (up to 180s) |
| `CELL_SCAN_TEST_CARRIER` | 33 | Test individual carrier (AT+COPS=1,2,"MCC-MNC") |
| `CELL_SCAN_WAIT_CSQ` | 34 | Get signal quality (AT+CSQ) |
| `CELL_SCAN_NEXT_CARRIER` | 35 | Move to next carrier in list |
| `CELL_SCAN_SELECT_BEST` | 36 | Choose best carrier by signal |
| `CELL_SCAN_CONNECT_BEST` | 37 | Connect to selected carrier |
| `CELL_SCAN_START_PPP` | 38 | Wait for COPS=1,2 OK response |
| `CELL_SCAN_VERIFY_CARRIER` | 39 | Verify carrier switch (AT+COPS?) |
| `CELL_SCAN_VERIFY_WAIT` | 40 | Wait between verify queries |
| `CELL_SCAN_COMPLETE` | 41 | Scan finished successfully |
| `CELL_WAIT_PPP_STARTUP` | 42 | Wait for PPP to establish after scan (10s grace period) |
| `CELL_SCAN_FAILED` | 43 | Scan failed, schedule retry |

### 11. PPP Monitoring States

| State | ID | Description |
|-------|----|----|
| `CELL_WAIT_PPP_INTERFACE` | 42 | Monitor PPP establishment |
| `CELL_BLACKLIST_AND_RETRY` | 43 | Handle carrier failure |

### 12. Non-Blocking PPP Stop States (5 states)

| State | ID | Description |
|-------|----|----|
| `CELL_STOP_PPP_INIT` | 44 | Send SIGTERM to pppd, start 2s timer |
| `CELL_STOP_PPP_WAIT` | 45 | Poll for graceful exit |
| `CELL_STOP_PPP_FORCE` | 46 | Send SIGKILL if still running |
| `CELL_STOP_PPP_CLEANUP` | 47 | Remove lock files, return to caller |
| `CELL_STOP_PPP_EXTENDED` | 48 | Extended cleanup (runsv, logging) |

### 13. Continuation States After PPP Stop (2 states)

| State | ID | Description |
|-------|----|----|
| `CELL_INIT_AFTER_PPP_STOP` | 49 | Continue CELL_INIT after PPP stopped |
| `CELL_HARDWARE_RESET_AFTER_PPP` | 50 | Continue hardware reset after PPP stopped |

### 14. Hardware Reset States (5 states)

| State | ID | Description |
|-------|----|----|
| `CELL_HARDWARE_RESET_INIT` | 51 | Close port, stop PPP, export GPIO |
| `CELL_HARDWARE_RESET_GPIO_LOW` | 52 | Set GPIO 89 LOW, wait 1s |
| `CELL_HARDWARE_RESET_GPIO_HIGH` | 53 | Set GPIO 89 HIGH (power pulse), wait 1s |
| `CELL_HARDWARE_RESET_GPIO_DONE` | 54 | Set GPIO 89 LOW, start boot wait |
| `CELL_HARDWARE_RESET_WAIT_BOOT` | 55 | Wait for modem enumeration (30s max) |

### 15. Quick Status States (Phase 6 - 3 states)

These states provide a fast-path when PPP is already running with a valid IP address.
Instead of killing PPP and reinitializing, they query carrier/signal info and go online.

| State | ID | Description |
|-------|----|----|
| `CELL_QUICK_STATUS_INIT` | 56 | Open serial port (PPP already up) |
| `CELL_QUICK_STATUS_COPS` | 57 | Query AT+COPS? for carrier info |
| `CELL_QUICK_STATUS_CSQ` | 58 | Query AT+CSQ for signal strength |

**Note**: `NO_CELL_STATES` = 59 (sentinel value marking end of enum)

**Flow**: CELL_INIT (detects ppp0 with IP) -> QUICK_STATUS_INIT -> QUICK_STATUS_COPS -> QUICK_STATUS_CSQ -> CELL_ONLINE

**Purpose**: Preserve existing PPP connection on program restart, avoiding unnecessary modem resets.

---

## State Transition Diagrams

### Main Initialization Flow

```
                    ┌─────────────┐
                    │  CELL_INIT  │
                    └──────┬──────┘
                           │ Stop PPP (non-blocking)
                           ▼
              ┌────────────────────────┐
              │ CELL_STOP_PPP_INIT     │───────┐
              └────────────────────────┘       │
                           │                   │ (PPP stop state machine)
                           ▼                   │
              ┌────────────────────────┐       │
              │ CELL_INIT_AFTER_PPP_STOP│◄─────┘
              └────────────────────────┘
                           │ Open serial port
                           ▼
              ┌────────────────────────┐
              │    CELL_PURGE_PORT     │
              └────────────────────────┘
                           │ Flush buffers
                           ▼
         ┌─────────────────────────────────┐
         │  CELL_PROCIESS_INITIALIZATION   │◄──────┐
         └─────────────────────────────────┘       │
                           │                       │
                           ▼                       │ Retry
              ┌────────────────────────┐           │
              │   CELL_GET_RESPONSE    │───────────┘
              └────────────────────────┘
                           │ Response received
                           ▼
              ┌────────────────────────┐
              │  CELL_PROCESS_RESPONSE │
              └────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      (More AT commands)        (Init complete)
              │                         │
              ▼                         ▼
      CELL_PROCIESS_INIT...    CELL_TEST_NETWORK_SETUP
```

### Carrier Scan Flow

```
    Scan Triggered (manual or auto)
              │
              ▼
    ┌─────────────────────┐
    │  CELL_SCAN_STOP_PPP │ ──► sv down pppd
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │ CELL_SCAN_STOP_PPP_WAIT_SV │ ──► Wait 500ms
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │  CELL_SCAN_VERIFY_STOPPED │ ──► Check pppd PID
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │   CELL_SCAN_DEREGISTER   │ ──► AT+COPS=2 (deregister)
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │ CELL_SCAN_WAIT_DEREGISTER│ ──► Wait for OK (10s timeout)
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │  CELL_SCAN_GET_OPERATORS │ ──► AT+COPS=?
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │  CELL_SCAN_WAIT_RESULTS  │ ──► Parse operator list (180s timeout)
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐◄─────────────────────┐
    │  CELL_SCAN_TEST_CARRIER  │ ──► AT+COPS=1,2,MCC │
    └─────────────────────────┘                      │
              │                                      │
              ▼                                      │
    ┌─────────────────────────┐                      │
    │    CELL_SCAN_WAIT_CSQ    │ ──► AT+CSQ          │
    └─────────────────────────┘                      │
              │                                      │
              ▼                                      │
    ┌─────────────────────────┐                      │
    │  CELL_SCAN_NEXT_CARRIER  │ ─── More carriers? ─┘
    └─────────────────────────┘
              │ No more carriers
              ▼
    ┌─────────────────────────┐
    │  CELL_SCAN_SELECT_BEST   │ ──► Pick highest signal
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │  CELL_SCAN_CONNECT_BEST  │ ──► AT+COPS=1,2,"best"
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │   CELL_SCAN_START_PPP    │ ──► Wait for OK
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐◄─────┐
    │ CELL_SCAN_VERIFY_CARRIER │      │ Retry every 2s
    └─────────────────────────┘      │
              │                      │
              ├── Carrier mismatch ──┘
              │
              ▼ Carrier verified
    ┌─────────────────────────┐
    │   CELL_SCAN_COMPLETE     │ ──► sv up pppd
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │  CELL_WAIT_PPP_STARTUP   │ ──► 10s grace period for PPP
    └─────────────────────────┘
              │ ppp0 interface up
              ▼
    ┌─────────────────────────┐
    │       CELL_ONLINE        │
    └─────────────────────────┘
```

### Non-Blocking PPP Stop Flow

```
    Stop PPP Requested
    (from any state via pppd_stop_return_state)
              │
              ▼
    ┌─────────────────────┐
    │  CELL_STOP_PPP_INIT │
    └─────────────────────┘
              │ Find pppd PID
              │ Send SIGTERM
              │ Start 2-second timer
              ▼
    ┌─────────────────────┐
    │  CELL_STOP_PPP_WAIT │◄────────────────┐
    └─────────────────────┘                 │
              │                             │
              ├── PID still exists ─────────┘ (poll every 100ms)
              │
              ├── PID gone ──────────────────┐
              │                              │
              ├── Timeout (2s) ──┐           │
              │                  ▼           │
              │    ┌─────────────────────┐   │
              │    │ CELL_STOP_PPP_FORCE │   │
              │    └─────────────────────┘   │
              │              │ SIGKILL       │
              │              ▼               │
              │    ┌─────────────────────┐   │
              │    │ CELL_STOP_PPP_CLEANUP│◄─┘
              │    └─────────────────────┘
              │              │
              │              ├── Extended cleanup? ──┐
              │              │                       ▼
              │              │       ┌───────────────────────┐
              │              │       │ CELL_STOP_PPP_EXTENDED│
              │              │       └───────────────────────┘
              │              │                       │
              │              ▼                       │
              └──────► Return to pppd_stop_return_state
```

### Hardware Reset Flow

```
    Hardware Reset Triggered
    (serial errors or explicit request)
              │
              ▼
    ┌─────────────────────────┐
    │ CELL_HARDWARE_RESET_INIT│
    └─────────────────────────┘
              │ Close serial port
              │ Stop PPP (non-blocking)
              │ Export GPIO 89
              ▼
    ┌─────────────────────────────┐
    │ CELL_HARDWARE_RESET_GPIO_LOW│
    └─────────────────────────────┘
              │ Set GPIO 89 = LOW
              │ Wait 1 second
              ▼
    ┌──────────────────────────────┐
    │ CELL_HARDWARE_RESET_GPIO_HIGH│
    └──────────────────────────────┘
              │ Set GPIO 89 = HIGH (power pulse)
              │ Wait 1 second
              ▼
    ┌──────────────────────────────┐
    │ CELL_HARDWARE_RESET_GPIO_DONE│
    └──────────────────────────────┘
              │ Set GPIO 89 = LOW
              │ Start 30-second boot timer
              ▼
    ┌──────────────────────────────┐
    │ CELL_HARDWARE_RESET_WAIT_BOOT│
    └──────────────────────────────┘
              │ Check for /dev/ttyACM0
              │
              ├── Found ────► CELL_INIT
              │
              └── Timeout ──► Retry (max 3 attempts)
                              then CELL_DISCONNECTED
```

---

## Scan Trigger Mechanisms

### 1. Manual Trigger (CLI) - Phase 4 Update

**IMPORTANT**: As of Dec 5, 2025, manual CLI scans ALWAYS bypass the connection protection gate.

```
User: "cell scan"
    │
    ▼
cli_cell() in cellular_man.c
    │
    ▼
imx_request_manual_cellular_scan()
    │
    ▼
cellular_flags.cell_scan = true
cellular_flags.cell_manual_scan = true   ◄── NEW: Manual flag set
    │
    ▼
cellular_man() checks flags at top of function
    │
    ▼
if (cellular_flags.cell_scan) {
    if (cellular_flags.cell_manual_scan) {
        // BYPASS - Manual scan always allowed
        // Fall through to start scan
    } else if (should_protect_connection_from_scan()) {
        // BLOCKED - healthy connection protected (automated rescans only)
    }
    │
    ▼
    scan_is_manual = true  ◄── Track for no-blacklist behavior
    cellular_scanning = true;
    cellular_state = CELL_SCAN_STOP_PPP;
}
```

**Manual Scan Features:**
- **Bypasses protection gate**: Scans proceed even with healthy PPP connection
- **No carrier blacklisting**: Carriers that fail during manual scan are NOT blacklisted
- **Proper PPP shutdown**: PPP is cleanly stopped via CELL_SCAN_STOP_PPP state machine
- **Testing mode**: Used to verify scan functionality without affecting carrier selection

**Functions:**
- `imx_request_manual_cellular_scan()` - Sets both `cell_scan` and `cell_manual_scan` flags
- `imx_request_cellular_scan()` - Sets only `cell_scan` (subject to protection gate)

**Variables:**
- `cellular_flags.cell_manual_scan` - Request flag (cleared after scan starts)
- `scan_is_manual` - Runtime flag (used throughout scan to skip blacklisting)

### 2. Dynamic Trigger (PPP Failures)

```
process_network.c: NET_ONLINE_CHECK_RESULTS state
    │
    ▼
PPP ping test fails (score < MIN_ACCEPTABLE_SCORE)
    │
    ▼
ctx->ppp_ping_failures++
    │
    ▼
cellular_update_ppp_health(false, score, time)
    │
    ▼
if (ppp_ping_failures >= MAX_PPP_PING_FAILURES) {  // Default: 3
    │
    ▼
    cellular_reset_scan_protection()  // Allow scan
    │
    ▼
    ctx->ppp_rescan_attempts++
    │
    ▼
    if (ppp_rescan_attempts >= MAX_PPP_RESCAN_ATTEMPTS) {  // Default: 3
        blacklist_current_carrier()
        ctx->ppp_rescan_attempts = 0
    }
    │
    ▼
    request_carrier_rescan_rate_limited(time, "PPP ping failures")
        │
        ▼
        Rate limiting checks:
        - Not in extended backoff?
        - Not already scanning?
        - Not already requested?
        - Minimum interval passed?
        - Under max attempts?
        - Connection not protected?
            │
            ▼
        cellular_request_rescan = true
}
```

### 3. Carrier Connection Failure Trigger

```
process_network.c: NET_ACTIVATE_PPP state
    │
    ▼
PPP activation times out (default 30s)
    │
    ▼
if (!have_other_interface && !cellular_reset_stop) {
    │
    ▼
    blacklist_current_carrier(time)
    │
    ▼
    imx_request_cellular_scan()  // Direct call (no rate limiting)
}
```

### 4. CME ERROR Trigger

```
cellular_man.c: detect_and_handle_chat_failure()
    │
    ▼
Chat log contains CME ERROR patterns:
- "+CME ERROR:"
- "TERMINAL I/O ERROR"
- "CARRIER CME ERROR"
    │
    ▼
request_carrier_rescan_rate_limited(time, "CME ERROR rejection")
    │
    ▼
(Same rate limiting as PPP failures)
```

---

## Interaction Between cellular_man and process_network

### Shared Variables

```c
// In cellular_man.c - exposed via functions
static bool cellular_scanning = false;      // imx_is_cellular_scanning()
static bool cellular_now_ready = false;     // imx_is_cellular_now_ready()
static bool cellular_link_reset = false;    // imx_is_cellular_link_reset()

// In cellular_man.c - global
bool cellular_request_rescan = false;       // Set by process_network

// Functions called by process_network
void cellular_update_ppp_health(bool check_passed, int score, imx_time_t time);
void cellular_reset_scan_protection(void);
bool request_carrier_rescan_rate_limited(imx_time_t time, const char *reason);
void cellular_reset_scan_rate_limiter(void);
```

### process_network Passive Mode During Scan

```c
// In process_network.c - near top of function
if (imx_is_cellular_scanning()) {
    NETMGR_LOG_PPP0(ctx, "Cellular scan in progress - waiting passively");
    return IMX_SUCCESS;  // Early exit - do nothing
}
```

This ensures:
- No PPP start/stop operations during scan
- No interface switching during scan
- Scan has exclusive access to modem AT port

### Health Reporting Flow

```
process_network.c                          cellular_man.c
      │                                          │
      │ PPP ping test passes                     │
      │────────────────────────────────────────►│
      │ cellular_update_ppp_health(true, 8, t)  │
      │                                          │ ppp_consecutive_health_passes++
      │                                          │ ppp_last_health_score = 8
      │                                          │ if (ppp_online_start_time == 0)
      │                                          │     ppp_online_start_time = t
      │                                          │
      │ PPP ping test fails                      │
      │────────────────────────────────────────►│
      │ cellular_update_ppp_health(false, 2, t) │
      │                                          │ ppp_consecutive_health_passes = 0
      │                                          │ ppp_last_health_score = 2
      │                                          │
      │ 3 consecutive failures                   │
      │────────────────────────────────────────►│
      │ cellular_reset_scan_protection()        │
      │                                          │ ppp_online_start_time = 0
      │                                          │ scan_protection_active = false
      │                                          │
      │────────────────────────────────────────►│
      │ request_carrier_rescan_rate_limited()   │
      │                                          │ (rate limit checks)
      │                                          │ cellular_request_rescan = true
```

---

## Connection Protection Logic

### Protection Gate Algorithm

```
should_protect_connection_from_scan(current_time):

    1. Check if PPP has valid IP
       └── if (!ppp0_has_valid_ip()) return false  // Nothing to protect

    2. Check if online time recorded
       └── if (ppp_online_start_time == 0) {
               ppp_online_start_time = current_time  // Record start
               return false  // Just came online, allow scan
           }

    3. Calculate online duration
       └── online_duration = current_time - ppp_online_start_time

    4. Check minimum online time (30 seconds)
       └── if (online_duration < 30000) return false

    5. Check health check passes (minimum 2)
       └── if (ppp_consecutive_health_passes < 2) return false

    6. Check within protection cooldown (5 minutes)
       └── if (online_duration < 300000) {
               LOG("BLOCKED: Active healthy connection")
               return true  // PROTECT - block scan
           }

    7. Cooldown expired
       └── return false  // Allow scan after 5 minutes
```

### Rate Limiting Algorithm

```
request_carrier_rescan_rate_limited(current_time, reason):

    1. Check extended backoff
       └── if (scan_blocked_until != 0 && current_time < scan_blocked_until)
               return false  // In 10-minute backoff

    2. Clear expired backoff
       └── if (scan_blocked_until != 0 && current_time >= scan_blocked_until)
               scan_blocked_until = 0

    3. Check if scan already in progress
       └── if (cellular_scanning) return false

    4. Check if request already pending
       └── if (cellular_request_rescan) return false

    5. Check minimum interval (60 seconds)
       └── if (last_scan_request_time != 0 &&
               current_time < last_scan_request_time + 60000)
               return false

    6. Check attempt count (max 3)
       └── if (scan_request_attempt_count >= 3) {
               scan_blocked_until = current_time + 600000  // 10 min backoff
               scan_request_attempt_count = 0
               return false
           }

    7. Check connection protection
       └── if (should_protect_connection_from_scan(current_time))
               return false

    8. Accept request
       └── last_scan_request_time = current_time
           scan_request_attempt_count++
           cellular_request_rescan = true
           return true
```

---

## Key Timeouts and Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `SCAN_PROTECTION_MIN_ONLINE_TIME` | 30,000 ms | Min time online before protection |
| `SCAN_PROTECTION_COOLDOWN` | 300,000 ms | 5-minute protection window |
| `SCAN_PROTECTION_MIN_HEALTH_CHECKS` | 2 | Required passing health checks |
| `SCAN_PROTECTION_MIN_HEALTH_SCORE` | 7 | Minimum score for "healthy" |
| `SCAN_REQUEST_MIN_INTERVAL` | 60,000 ms | Minimum between scan requests |
| `SCAN_REQUEST_MAX_ATTEMPTS` | 3 | Attempts before extended backoff |
| `SCAN_REQUEST_EXTENDED_BACKOFF` | 600,000 ms | 10-minute backoff period |
| `MAX_PPP_PING_FAILURES` | 3 | Failures before requesting rescan |
| `MAX_PPP_RESCAN_ATTEMPTS` | 3 | Rescans before blacklisting carrier |
| PPP stop graceful timeout | 2,000 ms | Time to wait for SIGTERM |
| AT+COPS=? timeout | 180,000 ms | Operator list query timeout |
| Hardware reset boot timeout | 30,000 ms | Wait for modem enumeration |

---

## Document History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-05 | 1.0 | Claude Code Analysis | Initial document |
| 2025-12-06 | 1.1 | Claude Code Analysis | Corrected all state IDs to match enum order; added CELL_WAIT_PPP_STARTUP state; reorganized sections; updated state counts |
