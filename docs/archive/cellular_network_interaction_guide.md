# Cellular Network Interaction Guide
**Project**: Fleet-Connect-1 Cellular Connectivity System
**Version**: 1.0
**Date**: 2025-01-10

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Cellular Driver (cell_man.c)](#cellular-driver)
4. [Network Manager (process_network.c)](#network-manager)
5. [Integration & Data Flow](#integration--data-flow)
6. [PPP0 Activation Sequence](#ppp0-activation-sequence)
7. [Carrier Blacklisting](#carrier-blacklisting)
8. [WiFi Scanning](#wifi-scanning)
9. [State Machine Details](#state-machine-details)
10. [Debugging & Troubleshooting](#debugging--troubleshooting)

---

## Overview

The Fleet-Connect-1 cellular connectivity system provides automatic failover to cellular networks (ppp0) when primary network interfaces (eth0, wlan0) become unavailable. The system consists of two primary components that work together:

1. **Cellular Driver Manager** (`cell_man.c`) - Manages modem initialization, carrier selection, and network registration
2. **Network Manager** (`process_network.c`) - Handles interface selection, failover logic, and connectivity testing

### Key Features

- Automatic carrier scanning and selection
- Multi-interface failover (eth0 → wlan0 → ppp0)
- Ping-based connectivity verification
- Carrier blacklisting with exponential backoff
- Opportunistic interface discovery
- WiFi rescanning on connection failure
- Interface cooldown periods for stability

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│              (Fleet-Connect-1 Gateway)                        │
└──────────────────┬───────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │                              │
    ▼                              ▼
┌────────────────────┐    ┌────────────────────┐
│   cell_man.c       │    │  process_network.c │
│ (Cellular Driver)  │◄───┤  (Network Manager) │
│                    │    │                    │
│  - AT commands     │    │  - State machine   │
│  - Carrier scan    │    │  - Interface tests │
│  - Registration    │    │  - Failover logic  │
│  - Ready flag      │    │  - Route mgmt      │
└────────┬───────────┘    └────────┬───────────┘
         │                         │
         │                         │
    ┌────┼─────────────────────────┼────┐
    │    │   Integration Layer     │    │
    │    │  imx_is_cellular_now_ready()│
    │    │  start_pppd()           │    │
    │    │  stop_pppd()            │    │
    │    └─────────────────────────┘    │
    │                                    │
    └────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌────────┐   ┌─────────┐   ┌────────┐
│  eth0  │   │  wlan0  │   │  ppp0  │
│(DHCP   │   │(WiFi    │   │(Cellular)
│ Server)│   │ Client) │   │         │
└────────┘   └─────────┘   └────────┘
```

---

## Cellular Driver

### File Location
`iMatrix/IMX_Platform/networking/cell_man.c`

### Responsibilities

1. **Modem Initialization**
   - Serial port communication (typically /dev/ttyUSB2)
   - AT command sequences
   - SIM card validation
   - IMEI/IMSI retrieval

2. **Carrier Management**
   - Scan for available carriers
   - Select best carrier based on signal strength
   - Register with selected network
   - Handle registration failures

3. **Ready State Management**
   - Set `cellular_now_ready` flag when connected
   - Clear flag on disconnection or failure
   - Signal network manager via `imx_is_cellular_now_ready()`

### State Machine

```c
typedef enum CellularState_ {
    CELL_INIT,                     // Initialize modem
    CELL_PURGE_PORT,               // Clear serial port buffers
    CELL_PROCIESS_INITIALIZATION,  // Process init commands
    CELL_GET_RESPONSE,             // Waiting for AT response
    CELL_PROCESS_RESPONSE,         // Parse AT response
    CELL_TEST_NETWORK_SETUP,       // Test network configuration
    CELL_SETUP_OPERATOR,           // Select operator
    CELL_PROCESS_OPERATOR_SETUP,   // Process operator selection
    CELL_CONNECTED,                // Connected to carrier
    CELL_PROCESS_CSQ,              // Check signal quality
    CELL_CONNECT_TO_SELECTED,      // Connect to specific carrier
    CELL_TEST_CONNECTION,          // Test connection
    CELL_INIT_REGISTER,            // Initialize registration
    CELL_REGISTER,                 // Register with network
    CELL_ONLINE,                   // Fully online (ready)
    CELL_ONLINE_OPERATOR_CHECK,    // Online operator verification
    CELL_ONLINE_CHECK_CSQ,         // Online signal check
    // ... additional states
} CellularState_t;
```

### Key State Transitions

**Startup Flow**:
```
CELL_INIT
  → CELL_PURGE_PORT
  → CELL_PROCIESS_INITIALIZATION
  → CELL_GET_RESPONSE (AT commands)
  → CELL_PROCESS_RESPONSE
  → CELL_SETUP_OPERATOR (scan carriers)
  → CELL_CONNECTED (carrier selected)
  → CELL_ONLINE (ready!)
```

**Online Monitoring Flow**:
```
CELL_ONLINE
  → CELL_ONLINE_OPERATOR_CHECK (verify still connected)
  → CELL_ONLINE_CHECK_CSQ (check signal strength)
  → CELL_ONLINE (loop)
```

### AT Command Sequence

1. **Dummy AT** - Test modem responsiveness
2. **ATZ** - Reset modem to defaults
3. **AT+CPIN?** - Check SIM card status (should return "READY")
4. **ATI** - Get modem manufacturer/model
5. **AT+CGDCONT?** - Query APN configuration
6. **AT+CGSN** - Get IMEI
7. **AT+CIMI** - Get IMSI
8. **AT+CCID** - Get SIM card ID
9. **AT+COPS=?** - Scan for available carriers
10. **AT+COPS=1,2,"<carrier_id>"** - Register with specific carrier
11. **AT+CSQ** - Check signal quality

### Setting cellular_now_ready Flag

The `cellular_now_ready` flag is set at three key points:

**Location 1** (line 2032):
```c
case DONE_INIT_REGISTER:
    cellular_now_ready = true;
    cellular_link_reset = false;
```

**Location 2** (line 2141):
```c
case CELL_CONNECTED:
    cellular_now_ready = true;
```

**Location 3** (line 2273):
```c
// After successful test connection
cellular_now_ready = true;
```

---

## Network Manager

### File Location
`iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

### Responsibilities

1. **Interface Discovery**
   - Detect available interfaces (eth0, wlan0, ppp0)
   - Check link status (physical layer)
   - Verify IP address assignment

2. **Connectivity Testing**
   - Launch ping tests to cloud endpoints
   - Measure latency and packet loss
   - Score interfaces based on results

3. **Interface Selection**
   - Select best interface based on scores
   - Apply cooldown periods to prevent flapping
   - Handle interface switching

4. **Route Management**
   - Set default routes
   - Manage routing table
   - Handle route conflicts

5. **Failover Logic**
   - Detect interface failures
   - Trigger automatic failover
   - Retry failed interfaces after cooldown

### State Machine

```c
typedef enum {
    NET_INIT,                    // Initialization
    NET_SELECT_INTERFACE,        // Select interface to test
    NET_WAIT_RESULTS,            // Wait for ping results
    NET_REVIEW_SCORE,            // Review test scores
    NET_ONLINE,                  // Online with active interface
    NET_ONLINE_CHECK_RESULTS,    // Online - periodic verification
    NET_ONLINE_VERIFY_RESULTS,   // Online - opportunistic discovery
    NET_NO_STATES
} netmgr_state_t;
```

### State Flow Diagram

```
┌─────────────┐
│  NET_INIT   │ (Startup)
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ NET_SELECT_INTERFACE │◄─────┐
│                      │      │
│ - Check eth0         │      │
│ - Check wlan0        │      │
│ - Check ppp0         │      │(No interface
│ - Launch ping tests  │      │ available)
└──────┬───────────────┘      │
       │                      │
       ▼                      │
┌─────────────────┐           │
│ NET_WAIT_RESULTS│           │
│                 │           │
│ - Monitor pings │           │
│ - Track threads │           │
└──────┬──────────┘           │
       │                      │
       ▼                      │
┌──────────────────┐          │
│ NET_REVIEW_SCORE │          │
│                  │          │
│ - Compare scores │          │
│ - Select best    │──────────┘
└──────┬───────────┘  (score < threshold)
       │
       │ (good interface found)
       ▼
┌────────────┐
│ NET_ONLINE │◄──────┐
│            │       │
│ - Active   │       │(Verify OK)
│ - Routing  │       │
└──────┬─────┘       │
       │             │
       │(Periodic    │
       │ check)      │
       ▼             │
┌──────────────────────────┐
│ NET_ONLINE_CHECK_RESULTS │
│                          │
│ - Test current interface │
│ - Opportunistic discovery│
└──────┬───────────────────┘
       │
       │(Verify failed)
       ▼
┌───────────────────────────┐
│ NET_ONLINE_VERIFY_RESULTS │
│                           │
│ - Test backup interfaces  │
└──────┬────────────────────┘
       │
       │(Better interface found)
       ▼
   (Back to NET_SELECT_INTERFACE)
```

### Valid State Transitions

The network manager enforces strict state transition rules:

```c
NET_INIT → NET_SELECT_INTERFACE (only)

NET_SELECT_INTERFACE → {
    NET_WAIT_RESULTS,
    NET_SELECT_INTERFACE (retry)
}

NET_WAIT_RESULTS → {
    NET_REVIEW_SCORE,
    NET_SELECT_INTERFACE (timeout)
}

NET_REVIEW_SCORE → {
    NET_ONLINE (good interface),
    NET_SELECT_INTERFACE (retry)
}

NET_ONLINE → {
    NET_ONLINE_CHECK_RESULTS,
    NET_ONLINE_VERIFY_RESULTS,
    NET_SELECT_INTERFACE (failure)
}

NET_ONLINE_CHECK_RESULTS → {
    NET_ONLINE (pass),
    NET_ONLINE_VERIFY_RESULTS (verify),
    NET_SELECT_INTERFACE (fail)
}

NET_ONLINE_VERIFY_RESULTS → {
    NET_ONLINE (pass),
    NET_SELECT_INTERFACE (fail)
}
```

**Important**: `NET_ONLINE → NET_INIT` is **NOT** a valid transition. This causes the "blocked transition" error when system tries to restart from degraded state.

---

## Integration & Data Flow

### Cellular Ready Detection

**Function**: `imx_is_cellular_now_ready()`

**Detection Flow** (in `process_network.c`, lines 4131-4141):

```c
bool current_cellular_ready = imx_is_cellular_now_ready();

if (!g_prev_cellular_ready && current_cellular_ready)
{
    // Cellular just transitioned from NOT_READY to READY
    NETMGR_LOG_PPP0(ctx, "Cellular transitioned from NOT_READY to READY, allowing PPP retry");

    // Reset cellular flags to allow new connection attempt
    ctx->cellular_started = false;
    ctx->cellular_stopped = false;
}

g_prev_cellular_ready = current_cellular_ready;
```

### Starting pppd

**Function**: `start_pppd()`

**Trigger Conditions** (in `process_network.c`, lines 4233-4277):

```c
// In NET_SELECT_INTERFACE state
for (int i = 0; i < NUM_INTERFACES; i++)
{
    if (i == IFACE_PPP)
    {
        // Check if cellular is ready
        if (!imx_is_cellular_now_ready())
        {
            NETMGR_LOG_PPP0(ctx, "Skipping ppp0 - cellular not ready");
            continue;
        }

        // Check if we've already started pppd
        if (ctx->cellular_started)
        {
            NETMGR_LOG_PPP0(ctx, "pppd already started, skipping");
            continue;
        }

        // Start pppd
        start_pppd();
        ctx->cellular_started = true;
        ctx->ppp_start_time = current_time;

        NETMGR_LOG_PPP0(ctx, "Started pppd, will monitor for PPP0 device creation");
    }
}
```

### PPP0 Device Detection

**Location**: `process_network.c`, lines 4436-4481

**Monitoring Logic**:

```c
if (ctx->cellular_started && !ctx->states[IFACE_PPP].active)
{
    // Check if ppp0 device exists
    int ret = system("ip link show ppp0 >/dev/null 2>&1");

    if (ret == 0)
    {
        // ppp0 device created!
        NETMGR_LOG_PPP0(ctx, "ppp0 device detected, marking as active");
        ctx->states[IFACE_PPP].active = true;
        ctx->states[IFACE_PPP].link_up = true;

        // Will be tested in next iteration
    }
    else
    {
        // Still waiting for device
        uint32_t elapsed = current_time - ctx->ppp_start_time;

        if (elapsed > 30000)  // 30 second timeout
        {
            NETMGR_LOG_PPP0(ctx, "Timeout waiting for ppp0 device");
            ctx->cellular_started = false;
            ctx->cellular_stopped = true;
            stop_pppd();
        }
        else
        {
            NETMGR_LOG_PPP0(ctx, "Waiting for ppp0 device (%dms elapsed)", elapsed);
        }
    }
}
```

---

## PPP0 Activation Sequence

### Complete Flow

```
┌─────────────────────────────────┐
│ 1. Cellular Driver Initialization│
│    - Send AT commands            │
│    - Scan carriers               │
│    - Register with network       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 2. Set cellular_now_ready = true│
│    (cell_man.c)                  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 3. Network Manager Detects      │
│    Transition (false → true)    │
│    (process_network.c:4131-4141)│
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 4. Reset Cellular Flags         │
│    cellular_started = false     │
│    cellular_stopped = false     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 5. Enter NET_SELECT_INTERFACE   │
│    State                         │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 6. Check PPP Interface          │
│    - cellular_ready? YES         │
│    - cellular_started? NO        │
│    → Call start_pppd()           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 7. pppd Process Starts          │
│    - Negotiates with carrier    │
│    - Creates ppp0 device        │
│    - Obtains IP via PPP         │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 8. Monitor for ppp0 Device      │
│    Loop: ip link show ppp0      │
│    (30 second timeout)           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 9. ppp0 Device Detected         │
│    states[IFACE_PPP].active = T │
│    states[IFACE_PPP].link_up = T│
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 10. Transition to               │
│     NET_WAIT_RESULTS             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 11. Launch Ping Tests           │
│     - Ping cloud endpoints      │
│     - Measure latency           │
│     - Calculate score           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 12. Transition to               │
│     NET_REVIEW_SCORE             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 13. Select Best Interface       │
│     if (ppp0_score >= threshold)│
│         select ppp0              │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 14. Transition to NET_ONLINE    │
│     current_interface = ppp0    │
│     Set default route           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 15. System Fully Online         │
│     with Cellular Connection    │
└─────────────────────────────────┘
```

### Timing Expectations

- **Carrier Registration**: 5-15 seconds
- **pppd Negotiation**: 5-10 seconds
- **Device Creation**: 1-3 seconds
- **Ping Tests**: 2-5 seconds
- **Total Failover Time**: 15-35 seconds (typical)

---

## Carrier Blacklisting

### Purpose

Prevent repeated connection attempts to carriers that fail, allowing the system to try alternative carriers.

### Implementation Files

- `iMatrix/IMX_Platform/networking/cellular_blacklist.c`
- `iMatrix/IMX_Platform/networking/cellular_blacklist.h`

### Features

1. **Automatic Blacklisting**
   - Carriers are blacklisted when connection fails
   - Default blacklist duration: 5 minutes

2. **Exponential Backoff**
   - First failure: 5 minutes
   - Second failure: 10 minutes
   - Third failure: 20 minutes
   - etc.

3. **Automatic Expiration**
   - Blacklist entries expire after duration
   - Carrier becomes available for retry

4. **Manual Management**
   - CLI commands to view blacklist
   - CLI commands to clear specific entries
   - CLI commands to clear all entries

### Integration

Called from `cell_man.c` (line 2180):
```c
if (connection_failed)
{
    cellular_blacklist_add(carrier_id, operator_name);
}
```

### CLI Commands

```bash
# View blacklist
cellular blacklist

# Clear specific carrier
cellular blacklist clear 310410

# Clear all entries
cellular blacklist clear all
```

---

## WiFi Scanning

### Purpose

Discover available WiFi access points and reconnect when primary interface fails.

### Trigger Conditions

WiFi scanning is triggered on interface failure (not continuously):

1. **wlan0 Interface Down**
   - Physical link lost (linkdown flag)
   - IP address lost
   - Ping tests fail

2. **In NET_SELECT_INTERFACE State**
   - Part of interface discovery process
   - Lines 4486-4523 in `process_network.c`

### Implementation

**Function**: `trigger_wifi_scan_if_down()`

**Process**:
```c
if (ctx->states[IFACE_WLAN0].link_up == false)
{
    NETMGR_LOG(ctx, "wlan0 down, triggering WiFi scan");

    // Use wpa_cli to trigger scan
    system("wpa_cli -i wlan0 scan");

    // Wait for scan results
    sleep(2);

    // Attempt reassociation
    system("wpa_cli -i wlan0 reassociate");
}
```

### From Logs

WiFi scanning observed at:
- 00:00:43.525
- 00:01:13.632
- 00:01:48.209

Approximately every 30 seconds when interface is down.

---

## State Machine Details

### Interface Scoring

Interfaces are scored based on ping test results:

**Score 10** (Excellent):
- All pings successful
- Latency < 100ms
- Packet loss: 0%

**Score 7** (Good):
- Most pings successful
- Latency 100-200ms
- Packet loss: < 20%

**Score 3** (Minimum Acceptable):
- At least 1 ping successful
- Latency 200-500ms
- Packet loss: < 80%

**Score 0** (Failed):
- All pings failed OR
- No pings attempted

**Threshold**: Interface must score ≥ 3 to be selected.

### Interface Priority

When multiple interfaces have same score:

1. **eth0** (Highest priority - wired, reliable, low latency)
2. **wlan0** (Medium priority - wireless, good latency when available)
3. **ppp0** (Lowest priority - cellular, higher latency, metered)

### Cooldown Periods

After an interface fails, it enters a cooldown period:

- **Default Cooldown**: 30 seconds
- **After Repeated Failures**: Increases exponentially

During cooldown:
- Interface is not tested
- Prevents flapping
- Allows physical issues to resolve

### Opportunistic Discovery

Even when online with one interface, system periodically tests other interfaces to find better options:

**Trigger**: Every 60 seconds in `NET_ONLINE` state

**Process**:
1. Transition to `NET_ONLINE_VERIFY_RESULTS`
2. Test currently inactive interfaces
3. Compare scores
4. Switch if better interface found (score difference ≥ 3)

---

## Debugging & Troubleshooting

### Debug Flags

Enable comprehensive logging:

```bash
# Network manager general
debug DEBUGS_FOR_NETWORKING

# Ethernet specific
debug DEBUGS_FOR_ETH0_NETWORKING

# WiFi specific
debug DEBUGS_FOR_WIFI0_NETWORKING

# Cellular specific
debug DEBUGS_FOR_PPP0_NETWORKING

# Cellular driver
debug DEBUGS_FOR_CELLULAR
```

### Key Log Messages

**Cellular Ready Transition**:
```
[Cellular Connection - Ready state changed from NOT_READY to READY]
[NETMGR-PPP0] Cellular transitioned from NOT_READY to READY, allowing PPP retry
```

**pppd Started**:
```
[Cellular Connection - PPPD started (count=1)]
[NETMGR-PPP0] Started pppd, will monitor for PPP0 device creation
```

**ppp0 Device Detected**:
```
[NETMGR-PPP0] ppp0 device detected, marking as active
```

**Interface Selection**:
```
[NETMGR] COMPUTE_BEST selected: ppp0 (score=10, latency=154ms)
[NETMGR] Interface switch: NONE -> ppp0
```

**State Transitions**:
```
[NETMGR] State transition: NET_SELECT_INTERFACE -> NET_WAIT_RESULTS
[NETMGR] State transition: NET_WAIT_RESULTS -> NET_REVIEW_SCORE
[NETMGR] State transition: NET_REVIEW_SCORE -> NET_ONLINE
```

### Common Issues

**Issue 1: "State transition blocked"**
- **Symptom**: `Invalid transition from ONLINE to NET_INIT`
- **Cause**: Code attempts invalid state transition
- **Impact**: System may get stuck temporarily
- **Fix**: Ensure transitions follow valid state machine rules

**Issue 2: "sh: syntax error: unexpected end of file (expecting "fi")"**
- **Symptom**: Shell syntax error in logs
- **Cause**: Buffer overflow in `set_default_via_iface()` truncates shell command
- **Impact**: Route management fails, connectivity issues
- **Fix**: Split commands or increase buffer size

**Issue 3: "ppp0 not activating"**
- **Symptom**: Cellular ready, but ppp0 never becomes active
- **Cause**: State machine stuck, can't reach `NET_SELECT_INTERFACE`
- **Impact**: No cellular connectivity despite modem connection
- **Fix**: Ensure proper state transitions during interface failover

**Issue 4: "Cellular keeps retrying same carrier"**
- **Symptom**: Repeated attempts to failed carrier
- **Cause**: Blacklisting not working
- **Impact**: Slow failover, wasted time
- **Fix**: Verify `cellular_blacklist_add()` called on failure

### Diagnostic Commands

```bash
# Check network manager state
netmgr status

# Check cellular driver state
cellular status

# View blacklisted carriers
cellular blacklist

# Check interface status
ip link show
ip addr show

# Check routing table
ip route show

# Check pppd process
ps aux | grep pppd

# Check cellular modem
# (AT commands via /dev/ttyUSB2)
```

### Testing Scenarios

**Test Cellular Failover**:
```bash
# 1. Start with working WiFi
# 2. Disable WiFi
sudo ifconfig wlan0 down

# 3. Monitor logs
tail -f /var/log/Fleet-Connect.log | grep -E "PPP0|Cellular"

# 4. Verify ppp0 activates
ip addr show ppp0

# 5. Test connectivity
ping -I ppp0 8.8.8.8
```

**Test Interface Priority**:
```bash
# 1. Start with cellular only
# 2. Enable WiFi
sudo ifconfig wlan0 up

# 3. System should automatically switch to WiFi (better latency)
# 4. Monitor logs for interface switch
```

---

## Summary

The Fleet-Connect-1 cellular connectivity system provides robust, automatic failover to cellular networks through the coordinated operation of two main components:

1. **Cellular Driver** manages modem initialization, carrier selection, and network registration
2. **Network Manager** handles interface discovery, connectivity testing, and failover logic

The integration between these components via the `cellular_now_ready` flag and pppd management ensures seamless transitions between network interfaces, with cellular serving as a reliable backup when primary interfaces fail.

---

**End of Cellular Network Interaction Guide**
