# PPP0 Connection Refactoring Plan

**Date:** November 16, 2025
**Branch:** bugfix/network-stability
**Objective:** Refactor PPP connection management to use PPPD Daemon approach for better logging and control

---

## Executive Summary

Refactor PPP0 connection management from simple `pon`/`poff` commands to a robust daemon-based approach using `/etc/start_pppd.sh` with comprehensive logging via `/var/log/pppd/current`. This provides detailed diagnostics, connection state tracking, and better error reporting for cellular connectivity.

---

## Current Implementation Analysis

### Workflow

1. **cellular_man.c** state machine initializes modem and registers with carrier (AT&T)
2. At `DONE_INIT_REGISTER` state: Sets `cellular_now_ready = true` (line 2064)
3. **process_network.c** detects ready flag via `imx_is_cellular_now_ready()`
4. Calls `start_pppd()` from cellular_man.c (line 4531)
5. `start_pppd()` executes `pon` command (line 1797)
6. Waits up to 30 seconds for ppp0 device with IP address

### Problems

- **Missing Configuration:** `pon` requires `/etc/ppp/peers/provider` which doesn't exist
- **No Logging:** Cannot see chat script execution, LCP/IPCP negotiation
- **No State Visibility:** Just waiting for IP, no intermediate status
- **Limited Diagnostics:** "Connect script failed" with no details
- **No Error Recovery:** Cannot distinguish between different failure modes

### Working System Evidence

Working log from `/var/log/pppd/current` shows system HAS PPPD daemon infrastructure:
- `/etc/start_pppd.sh` script exists and works
- Chat script: `/usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto`
- Modem device: `/dev/ttyACM0`
- Log output: `/var/log/pppd/current` with detailed connection info
- Connection time: ~3 seconds from start to IP assignment

**Conclusion:** Switch from `pon`/`poff` to `/etc/start_pppd.sh` daemon approach.

---

## Proposed Architecture

### New Module: ppp_connection.c

**Purpose:** Encapsulate all PPP daemon management, log parsing, and status monitoring

**Location:** `iMatrix/IMX_Platform/LINUX_Platform/networking/ppp_connection.c`

**Responsibilities:**
- Start/stop PPPD daemon via `/etc/start_pppd.sh`
- Parse `/var/log/pppd/current` for connection state
- Extract IP addresses, DNS servers, error messages
- Provide structured status to callers
- Comprehensive logging with PPP-specific debug flags

---

## Detailed Design

### Data Structures

#### Connection State Enumeration

```c
/**
 * @brief PPP connection states derived from log parsing
 */
typedef enum {
    PPP_STATE_STOPPED,           /**< pppd daemon not running */
    PPP_STATE_STARTING,          /**< start_pppd.sh executing */
    PPP_STATE_CHAT_RUNNING,      /**< Chat script negotiating with modem */
    PPP_STATE_LCP_NEGOTIATION,   /**< LCP ConfReq/ConfAck exchange */
    PPP_STATE_IPCP_NEGOTIATION,  /**< IPCP negotiating IP address */
    PPP_STATE_CONNECTED,         /**< ppp0 has IP, ip-up script finished */
    PPP_STATE_ERROR              /**< Connection failed, see last_error */
} ppp_state_t;
```

#### Connection Status Structure

```c
/**
 * @brief PPP connection status information
 */
typedef struct {
    ppp_state_t state;              /**< Current connection state */
    bool pppd_running;              /**< PPPD daemon process running */
    bool ppp0_device_exists;        /**< ppp0 network device exists */
    bool ppp0_has_ip;               /**< ppp0 has valid IP address */
    char local_ip[16];              /**< Local IP (e.g., "10.183.192.75") */
    char remote_ip[16];             /**< Remote IP (e.g., "10.64.64.64") */
    char dns_primary[16];           /**< Primary DNS (e.g., "8.8.8.8") */
    char dns_secondary[16];         /**< Secondary DNS (e.g., "8.8.4.4") */
    uint32_t connection_time_ms;    /**< Time since start attempt */
    imx_time_t connection_start;    /**< Timestamp when connection started */
    char last_error[256];           /**< Parsed error message from logs */
    uint32_t chat_script_failures;  /**< Count of "Connect script failed" */
    uint32_t modem_hangups;         /**< Count of "Modem hangup" */
} ppp_connection_status_t;
```

#### Health Check Structure

```c
/**
 * @brief PPP connection health indicators from log analysis
 */
typedef struct {
    bool chat_script_ok;         /**< No "Connect script failed" errors */
    bool lcp_negotiated;         /**< Saw "LCP ConfAck" */
    bool ipcp_negotiated;        /**< Saw "IPCP ConfAck" */
    bool ip_assigned;            /**< Saw "local  IP address" */
    bool ip_up_script_ok;        /**< ip-up script finished successfully */
    char failure_reason[128];    /**< Parsed failure reason if unhealthy */
    uint32_t log_lines_analyzed; /**< Number of log lines checked */
} ppp_health_check_t;
```

---

## Core Functions

### 1. ppp_connection_start()

**Prototype:**
```c
/**
 * @brief Start PPPD daemon using /etc/start_pppd.sh
 * @return IMX_SUCCESS if daemon started, IMX_ERROR on failure
 */
imx_result_t ppp_connection_start(void);
```

**Implementation Logic:**
1. Check prerequisites:
   - Verify `/etc/start_pppd.sh` exists and is executable
   - Verify modem device `/dev/ttyACM0` exists
   - Check `/var/log/pppd/` directory writable
2. Check if already running (avoid duplicate start)
3. Execute `/etc/start_pppd.sh` via `system()` call
4. Wait 500ms for daemon initialization
5. Verify pppd process started with `pidof pppd`
6. Log success/failure with detailed diagnostics
7. Return result code

**Logging:**
- `[PPP_CONN] Checking prerequisites for PPPD startup`
- `[PPP_CONN] Executing /etc/start_pppd.sh`
- `[PPP_CONN] PPPD daemon started successfully`
- `[PPP_CONN] ERROR: start_pppd.sh failed with exit code N`

**Error Handling:**
- Missing script: Return `IMX_ERROR`, log specific file missing
- Execution failure: Log exit code, suggest checking system logs
- Daemon didn't start: Log failure, suggest manual troubleshooting

---

### 2. ppp_connection_stop()

**Prototype:**
```c
/**
 * @brief Stop PPPD daemon and clean up resources
 * @param cellular_reset true if stopping due to cellular reset
 * @return IMX_SUCCESS if stopped, IMX_ERROR on failure
 */
imx_result_t ppp_connection_stop(bool cellular_reset);
```

**Implementation Logic:**
1. Check if pppd is running
2. Log reason for stop (reset vs. normal shutdown)
3. Send SIGTERM to pppd (allows clean shutdown with ip-down script)
4. Wait up to 2 seconds for graceful exit
5. If still running, send SIGKILL
6. Clean up lock files: `rm -f /var/lock/LCK..ttyACM0`
7. Verify process terminated
8. Log completion

**Logging:**
- `[PPP_CONN] Stopping PPPD (reason: cellular_reset/normal_shutdown)`
- `[PPP_CONN] PPPD stopped successfully`
- `[PPP_CONN] WARNING: PPPD required SIGKILL for termination`

---

### 3. ppp_connection_get_status()

**Prototype:**
```c
/**
 * @brief Get current PPP connection status with detailed state information
 * @param status Pointer to status structure to populate
 * @return IMX_SUCCESS if status retrieved, IMX_ERROR on failure
 */
imx_result_t ppp_connection_get_status(ppp_connection_status_t *status);
```

**Implementation Logic:**
1. Initialize status structure to zeros
2. Check if pppd process running: `pidof pppd`
3. If not running: Set state to `PPP_STATE_STOPPED`, return
4. Check for ppp0 device: `ifconfig ppp0`
5. Check for IP address: `has_valid_ip_address("ppp0")`
6. If has IP: Parse log for IP/DNS details, set state to `PPP_STATE_CONNECTED`
7. If no IP yet: Parse log to determine intermediate state
8. Extract timing information
9. Return structured status

**Log Parsing Strategy:**
- Cache log file read for 1 second (performance optimization)
- Read last 100 lines from `/var/log/pppd/current`
- Search in reverse chronological order for state indicators
- Most recent state match determines current state

---

### 4. ppp_connection_parse_log()

**Prototype:**
```c
/**
 * @brief Parse recent PPPD log entries and copy to buffer
 * @param buffer Output buffer for log content
 * @param max_len Maximum buffer size
 * @param lines_to_read Number of recent lines to extract (0 = all)
 * @return IMX_SUCCESS if parsed, IMX_ERROR if log unavailable
 */
imx_result_t ppp_connection_parse_log(char *buffer, size_t max_len, uint32_t lines_to_read);
```

**Implementation Logic:**
1. Open `/var/log/pppd/current` for reading
2. If `lines_to_read == 0`: Copy entire file
3. If `lines_to_read > 0`: Extract last N lines
4. Filter for relevant entries (skip empty lines)
5. Format with timestamps preserved
6. Copy to output buffer with bounds checking
7. Return status

**Use Cases:**
- Diagnostic dumps when connection fails
- CLI command to view PPP status
- Error logging in `process_network.c`

**Example Failure log**
2025-11-16_23:22:33.77886 Start Pppd runit service...
2025-11-16_23:22:35.47446 AATQ0
2025-11-16_23:22:35.47618 OK
2025-11-16_23:22:35.51697 ATZ
2025-11-16_23:22:35.51911 OK
2025-11-16_23:22:35.62099 AT+CMEE=2
2025-11-16_23:22:35.62328 OK
2025-11-16_23:22:35.66452 ATI
2025-11-16_23:22:35.66850 Cinterion
2025-11-16_23:22:35.66899 PLS63-W
2025-11-16_23:22:35.67001 REVISION 01.202
2025-11-16_23:22:35.67005 
2025-11-16_23:22:35.67009 OK
2025-11-16_23:22:35.76158 AT+COPS?
2025-11-16_23:22:35.76512 +COPS: 1
2025-11-16_23:22:35.76643 
2025-11-16_23:22:35.76662 OK
2025-11-16_23:22:35.90221 ATDT*99***1#
2025-11-16_23:22:36.66619 +CME ERRORScript /usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto finished (pid 1288), status = 0xb
2025-11-16_23:22:36.66958 Connect script failed

**Example Success log**
2025-11-16_23:13:16.27011 Start Pppd runit service...
2025-11-16_23:13:17.90931 
2025-11-16_23:13:17.90989 ^SYSSTART
2025-11-16_23:13:17.91175 ATQ0
2025-11-16_23:13:17.91251 OK
2025-11-16_23:13:17.95510 ATZ
2025-11-16_23:13:17.95763 OK
2025-11-16_23:13:18.05981 AT+CMEE=2
2025-11-16_23:13:18.06170 OK
2025-11-16_23:13:18.10296 ATI
2025-11-16_23:13:18.10972 Cinterion
2025-11-16_23:13:18.11119 PLS63-W
2025-11-16_23:13:18.11237 REVISION 01.202
2025-11-16_23:13:18.11339 
2025-11-16_23:13:18.11343 OK
2025-11-16_23:13:18.20508 AT+COPS?
2025-11-16_23:13:18.21371 +COPS: 1,0,"AT&T",7
2025-11-16_23:13:18.21544 
2025-11-16_23:13:18.21548 OK
2025-11-16_23:13:18.35310 ATDT*99***1#
2025-11-16_23:13:18.37091 CONNECTchat:  Nov 16 23:13:18 CONNECT
2025-11-16_23:13:18.38299 Script /usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto finished (pid 2541), status = 0x0
2025-11-16_23:13:18.38367 Serial connection established.
2025-11-16_23:13:18.38587 using channel 1
2025-11-16_23:13:18.38988 Using interface ppp0
2025-11-16_23:13:18.39298 Connect: ppp0 <--> /dev/ttyACM0
2025-11-16_23:13:19.39756 sent [LCP ConfReq id=0x1 <asyncmap 0x0> <magic 0x54b9a8ae> <pcomp> <accomp>]
2025-11-16_23:13:19.40380 rcvd [LCP ConfReq id=0x0 <asyncmap 0x0> <auth chap MD5> <magic 0xceff926b> <pcomp> <accomp>]
2025-11-16_23:13:19.40388 No auth is possible
2025-11-16_23:13:19.40392 sent [LCP ConfRej id=0x0 <auth chap MD5>]
2025-11-16_23:13:19.40396 rcvd [LCP ConfAck id=0x1 <asyncmap 0x0> <magic 0x54b9a8ae> <pcomp> <accomp>]
2025-11-16_23:13:19.40582 rcvd [LCP ConfReq id=0x1 <asyncmap 0x0> <magic 0xceff926b> <pcomp> <accomp>]
2025-11-16_23:13:19.40592 sent [LCP ConfAck id=0x1 <asyncmap 0x0> <magic 0xceff926b> <pcomp> <accomp>]
2025-11-16_23:13:19.41657 sent [IPCP ConfReq id=0x1 <addr 0.0.0.0> <ms-dns1 0.0.0.0> <ms-dns2 0.0.0.0>]
2025-11-16_23:13:19.41666 rcvd [LCP DiscReq id=0x2 magic=0xceff926b]
2025-11-16_23:13:19.43067 rcvd [IPCP ConfReq id=0x0]
2025-11-16_23:13:19.43074 sent [IPCP ConfNak id=0x0 <addr 0.0.0.0>]
2025-11-16_23:13:19.43078 rcvd [IPCP ConfNak id=0x1 <addr 10.183.192.75> <ms-dns1 8.8.8.8> <ms-dns2 8.8.4.4>]
2025-11-16_23:13:19.43083 sent [IPCP ConfReq id=0x2 <addr 10.183.192.75> <ms-dns1 8.8.8.8> <ms-dns2 8.8.4.4>]
2025-11-16_23:13:19.43227 rcvd [IPCP ConfReq id=0x1]
2025-11-16_23:13:19.43236 sent [IPCP ConfAck id=0x1]
2025-11-16_23:13:19.43240 rcvd [IPCP ConfAck id=0x2 <addr 10.183.192.75> <ms-dns1 8.8.8.8> <ms-dns2 8.8.4.4>]
2025-11-16_23:13:19.43244 Could not determine remote IP address: defaulting to 10.64.64.64
2025-11-16_23:13:19.45545 not replacing default route to wlan0 [10.2.0.1]
2025-11-16_23:13:19.45612 local  IP address 10.183.192.75
2025-11-16_23:13:19.45667 remote IP address 10.64.64.64
2025-11-16_23:13:19.45729 primary   DNS address 8.8.8.8
2025-11-16_23:13:19.45782 secondary DNS address 8.8.4.4
2025-11-16_23:13:19.46191 Script /etc/ppp/ip-up started (pid 2546)
2025-11-16_23:13:19.81636 Script /etc/ppp/ip-up finished (pid 2546), status = 0x0
---

### 5. ppp_connection_check_health()

**Prototype:**
```c
/**
 * @brief Analyze PPPD logs for connection health indicators
 * @param health Pointer to health check structure to populate
 * @return IMX_SUCCESS if health checked, IMX_ERROR if log unavailable
 */
imx_result_t ppp_connection_check_health(ppp_health_check_t *health);
```

**Implementation Logic:**
1. Read recent log entries (last 200 lines)
2. Search for success indicators:
   - `"CONNECT"` → chat_script_ok = true
   - `"LCP ConfAck"` → lcp_negotiated = true
   - `"IPCP ConfAck"` → ipcp_negotiated = true
   - `"local  IP address"` → ip_assigned = true
   - `"ip-up finished (pid X), status = 0x0"` → ip_up_script_ok = true
3. Search for failure indicators:
   - `"Connect script failed"` → Extract reason
   - `"Modem hangup"` → Connection dropped
   - `"LCP terminated"` → Negotiation failed
   - `"No carrier"` → Modem issue
4. Populate health structure
5. Return result

---

### 6. Helper Functions

**`ppp_connection_init()`**
- Called once during network manager initialization
- Verify `/etc/start_pppd.sh` exists and is executable
- Check `/var/log/pppd/` directory accessible
- Initialize internal state tracking
- Log configuration status

**`ppp_state_name(ppp_state_t state)`**
- Return human-readable state name
- Used for logging

**`parse_ip_from_log(const char *log_line, char *ip_buffer)`**
- Extract IP address from log lines like "local  IP address 10.183.192.75"
- Helper for log parsing

**`is_pppd_daemon_running()`**
- Quick check: `pidof pppd`
- Used internally for status checks

---

## Implementation Phases

### Phase 1: Create New Module (ppp_connection.c/h)

**Files to Create:**
1. `iMatrix/IMX_Platform/LINUX_Platform/networking/ppp_connection.c`
2. `iMatrix/IMX_Platform/LINUX_Platform/networking/ppp_connection.h`

**Implementation Order:**
1. Define data structures in header
2. Implement `ppp_connection_init()` - prerequisite checking
3. Implement `ppp_connection_start()` - daemon startup
4. Implement `ppp_connection_stop()` - daemon shutdown
5. Implement log parsing: `ppp_connection_parse_log()`
6. Implement status: `ppp_connection_get_status()`
7. Implement health check: `ppp_connection_check_health()`
8. Add helper functions
9. Add comprehensive Doxygen comments

**CMakeLists.txt Update:**
```cmake
# Add new source file
set(NETWORKING_SOURCES
    # ... existing sources ...
    IMX_Platform/LINUX_Platform/networking/ppp_connection.c
)
```

---

### Phase 2: Deprecate Old Functions in cellular_man.c

**Line 1763-1816:** `start_pppd()`
- Rename to `start_pppd_deprecated()`
- Add `@deprecated` Doxygen tag
- Add comment block explaining why deprecated

**Line 1823-1850:** `stop_pppd()`
- Rename to `stop_pppd_deprecated()`
- Add `@deprecated` Doxygen tag
- Keep for reference

**Add New Wrapper Functions:**
```c
/**
 * @brief Start PPPD using daemon-based approach
 * @note Wrapper function - implementation in ppp_connection.c
 * @return IMX_SUCCESS on success, IMX_ERROR on failure
 */
void start_pppd(void)
{
    ppp_connection_start();
}

/**
 * @brief Stop PPPD using daemon-based approach
 * @param cellular_reset true if stopping due to cellular reset
 * @note Wrapper function - implementation in ppp_connection.c
 */
void stop_pppd(bool cellular_reset)
{
    ppp_connection_stop(cellular_reset);
}
```

**Update Header:**
- Update `cellular_man.h` function declarations
- Add `#include "ppp_connection.h"`

**Maintain Compatibility:**
- No changes to cellular_man.c state machine logic
- `cellular_now_ready` flag still set at line 2064
- All existing call sites continue to work

---

### Phase 3: Enhance process_network.c Monitoring

**Location:** Lines 4646-4676

**Current Code:**
```c
if (!has_valid_ip_address("ppp0")) {
    if (time_since_start < 30000) {
        NETMGR_LOG_PPP0(ctx, "PPP0 not ready (device=missing, pppd=running)");
    } else {
        NETMGR_LOG_PPP0(ctx, "PPP0 connect script likely failing");
    }
}
```

**Enhanced Implementation:**
```c
/* Monitor PPP0 connection status with detailed state tracking */
if (ctx->cellular_started && !ctx->states[IFACE_PPP].active)
{
    ppp_connection_status_t ppp_status;

    if (ppp_connection_get_status(&ppp_status) == IMX_SUCCESS)
    {
        imx_time_t time_since_start = imx_time_difference(current_time, ctx->ppp_start_time);

        switch (ppp_status.state)
        {
        case PPP_STATE_CONNECTED:
            /* PPP0 fully connected with IP address */
            NETMGR_LOG_PPP0(ctx, "PPP0 CONNECTED: local=%s, remote=%s, DNS=%s/%s (in %lu ms)",
                       ppp_status.local_ip, ppp_status.remote_ip,
                       ppp_status.dns_primary, ppp_status.dns_secondary,
                       time_since_start);

            MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
            ctx->states[IFACE_PPP].active = true;
            MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);
            break;

        case PPP_STATE_STARTING:
            if (time_since_start % 5000 < 1000) { /* Log every 5 seconds */
                NETMGR_LOG_PPP0(ctx, "PPP0 starting daemon (%lu ms elapsed)", time_since_start);
            }
            break;

        case PPP_STATE_CHAT_RUNNING:
            if (time_since_start % 5000 < 1000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 chat script running (modem negotiation, %lu ms elapsed)",
                           time_since_start);
            }
            break;

        case PPP_STATE_LCP_NEGOTIATION:
            if (time_since_start % 5000 < 1000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 LCP negotiation in progress (%lu ms elapsed)",
                           time_since_start);
            }
            break;

        case PPP_STATE_IPCP_NEGOTIATION:
            if (time_since_start % 5000 < 1000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 IPCP negotiation (requesting IP, %lu ms elapsed)",
                           time_since_start);
            }
            break;

        case PPP_STATE_ERROR:
            NETMGR_LOG_PPP0(ctx, "PPP0 connection FAILED: %s", ppp_status.last_error);

            /* Get recent logs for diagnostics */
            char log_buffer[1024];
            if (ppp_connection_parse_log(log_buffer, sizeof(log_buffer), 20) == IMX_SUCCESS) {
                NETMGR_LOG_PPP0(ctx, "Recent PPPD log (last 20 lines):");
                NETMGR_LOG_PPP0(ctx, "%s", log_buffer);
            }

            /* Enhanced diagnostics */
            NETMGR_LOG_PPP0(ctx, "Check: /var/log/pppd/current for full details");
            NETMGR_LOG_PPP0(ctx, "Verify: ls -l /dev/ttyACM* for modem device");

            /* Mark as failed, will retry based on process_network logic */
            ctx->cellular_started = false;
            break;

        case PPP_STATE_STOPPED:
            if (time_since_start > 5000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 daemon not running (stopped or failed to start)");

                /* Check health to see why it stopped */
                ppp_health_check_t health;
                if (ppp_connection_check_health(&health) == IMX_SUCCESS) {
                    if (!health.chat_script_ok) {
                        NETMGR_LOG_PPP0(ctx, "Chat script failed: %s", health.failure_reason);
                    }
                }
            }
            break;
        }

        /* Timeout check - connection should complete in ~3-5 seconds normally */
        if (time_since_start > 30000 && ppp_status.state != PPP_STATE_CONNECTED) {
            NETMGR_LOG_PPP0(ctx, "PPP0 connection timeout after %lu ms (state=%s)",
                       time_since_start, ppp_state_name(ppp_status.state));

            /* Perform health check to identify issue */
            ppp_health_check_t health;
            ppp_connection_check_health(&health);
            NETMGR_LOG_PPP0(ctx, "Health: chat=%s, lcp=%s, ipcp=%s, ip=%s",
                       health.chat_script_ok ? "OK" : "FAIL",
                       health.lcp_negotiated ? "OK" : "FAIL",
                       health.ipcp_negotiated ? "OK" : "FAIL",
                       health.ip_assigned ? "OK" : "FAIL");

            /* Could restart PPP here if needed */
        }
    }
    else
    {
        /* Error getting status */
        NETMGR_LOG_PPP0(ctx, "Failed to get PPP connection status");
    }
}
```

---

### Phase 4: Add Network Manager Initialization

**File:** `process_network.c`, function `network_manager_init()` (line 4211)

**Add PPP connection module initialization:**
```c
bool network_manager_init(void)
{
    init_netmgr_context(&g_netmgr_ctx);

    /* Initialize ping statistics */
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    g_ping_stats.stats_start_time = current_time;
    g_ping_stats.total_processes_created = 0;

    /* ... existing code ... */

    /* List configured WiFi networks for diagnostics */
    list_configured_wifi_networks();

    /* Initialize PPP connection module */
    if (ppp_connection_init() != IMX_SUCCESS) {
        NETMGR_LOG(&g_netmgr_ctx, "WARNING: PPP connection module initialization failed");
        NETMGR_LOG(&g_netmgr_ctx, "PPP0 cellular connectivity may not be available");
    }

    NETMGR_LOG(&g_netmgr_ctx, "Network manager initialized");
    return true;
}
```

---

## Log Parsing Implementation

### State Detection Pattern Matching

**Log Patterns from Working Example:**

| Pattern | State | Example |
|---------|-------|---------|
| `"Start Pppd runit service"` | STARTING | First line in log |
| `"ATDT*99***1#"` | CHAT_RUNNING | Chat script dialing |
| `"CONNECT"` | Chat succeeded | Modem connected |
| `"LCP ConfReq"` | LCP_NEGOTIATION | LCP handshake |
| `"LCP ConfAck"` | LCP negotiated | LCP complete |
| `"IPCP ConfReq"` | IPCP_NEGOTIATION | IP negotiation |
| `"local  IP address"` | CONNECTED | Full connection |
| `"Script /etc/ppp/ip-up finished"` | CONNECTED | Setup complete |
| `"Connect script failed"` | ERROR | Chat failed |
| `"Modem hangup"` | ERROR | Disconnected |
| `"LCP terminated"` | ERROR | Protocol failure |

### IP/DNS Extraction Patterns

```c
// Parse "local  IP address 10.183.192.75"
if (strstr(line, "local  IP address")) {
    sscanf(line, "local  IP address %15s", status->local_ip);
}

// Parse "remote IP address 10.64.64.64"
if (strstr(line, "remote IP address")) {
    sscanf(line, "remote IP address %15s", status->remote_ip);
}

// Parse "primary   DNS address 8.8.8.8"
if (strstr(line, "primary   DNS address")) {
    sscanf(line, "primary   DNS address %15s", status->dns_primary);
}

// Parse "secondary DNS address 8.8.4.4"
if (strstr(line, "secondary DNS address")) {
    sscanf(line, "secondary DNS address %15s", status->dns_secondary);
}
```

### Error Message Extraction

```c
// "Connect script failed" - generic error
// "No carrier" - modem not responding
// "Modem hangup" - connection dropped
// "LCP: timeout sending Config-Requests" - negotiation timeout

if (strstr(line, "Connect script failed")) {
    snprintf(health->failure_reason, sizeof(health->failure_reason),
             "Chat script failed - check modem AT command response");
} else if (strstr(line, "No carrier")) {
    snprintf(health->failure_reason, sizeof(health->failure_reason),
             "No carrier detected - verify SIM card and cellular signal");
} else if (strstr(line, "Modem hangup")) {
    snprintf(health->failure_reason, sizeof(health->failure_reason),
             "Modem disconnected - check signal strength and carrier");
}
```

---

## Configuration Requirements

### System Files Required

**Must exist on target system:**

1. **`/etc/start_pppd.sh`** - PPPD startup script
   - Must be executable (`chmod +x`)
   - Should handle modem initialization
   - Should start pppd with proper options

2. **`/var/log/pppd/`** - Log directory
   - Must be writable
   - `/var/log/pppd/current` created by logger

3. **`/etc/chatscripts/quake-gemalto`** - Chat script
   - Contains AT commands for modem dial-up
   - Referenced by pppd configuration

4. **`/etc/ppp/ip-up`** - IP up script
   - Executed when connection established
   - Can set routes, update DNS, etc.

5. **`/etc/ppp/ip-down`** - IP down script
   - Executed when connection terminated
   - Cleanup routes, etc.

**Note:** These are deployment files, not in source repository.

---

## Testing Strategy

### Unit Testing

**Test Cases:**

1. **Prerequisites Check**
   - Missing `/etc/start_pppd.sh` → Should fail gracefully with clear error
   - Script not executable → Should fail with permission error
   - Missing log directory → Should warn but attempt to continue

2. **Start/Stop Cycle**
   - Start when not running → Success
   - Start when already running → Should detect and skip
   - Stop when running → Should terminate cleanly
   - Stop when not running → Should skip gracefully

3. **Status Queries**
   - Query during each connection state
   - Verify state correctly identified from logs
   - Check IP/DNS extraction accuracy

4. **Log Parsing**
   - Parse working log → Should identify CONNECTED state
   - Parse error log → Should extract failure reason
   - Parse partial log → Should identify intermediate state

### Integration Testing

**Test Scenarios:**

1. **Normal Connection Flow**
   - Modem ready → cellular_now_ready=YES
   - process_network calls start_pppd()
   - Verify state transitions: STARTING → CHAT_RUNNING → LCP → IPCP → CONNECTED
   - Verify timing: Should complete in 3-5 seconds
   - Verify IP assigned and ppp0 active

2. **Connection Failure Scenarios**
   - No modem device (/dev/ttyACM0 missing)
   - Chat script fails (modem not responding)
   - LCP negotiation timeout
   - IPCP failure (no IP assigned)
   - Verify errors logged with actionable diagnostics

3. **Recovery Testing**
   - Connection drops (modem hangup)
   - Verify clean shutdown
   - Verify retry logic works
   - Check cellular_started reset properly

4. **Log Analysis**
   - Run for 30+ minutes
   - Collect logs showing multiple connection/disconnection cycles
   - Verify no memory leaks from log parsing
   - Verify cached reads don't cause stale data

---

## Expected Log Output

### Successful Connection

```
[PPP_CONN] Initializing PPP connection module
[PPP_CONN] Prerequisites: /etc/start_pppd.sh exists (executable: YES)
[PPP_CONN] Log directory: /var/log/pppd/ (writable: YES)
[PPP_CONN] Checking prerequisites for PPPD startup
[PPP_CONN] Modem device: /dev/ttyACM0 (exists: YES)
[PPP_CONN] Executing /etc/start_pppd.sh
[PPP_CONN] PPPD daemon started successfully
[NETMGR-PPP0] PPP0 starting daemon (1200 ms elapsed)
[NETMGR-PPP0] PPP0 chat script running (modem negotiation, 1500 ms elapsed)
[NETMGR-PPP0] PPP0 LCP negotiation in progress (2000 ms elapsed)
[NETMGR-PPP0] PPP0 IPCP negotiation (requesting IP, 2500 ms elapsed)
[NETMGR-PPP0] PPP0 CONNECTED: local=10.183.192.75, remote=10.64.64.64, DNS=8.8.8.8/8.8.4.4 (in 3246 ms)
```

### Connection Failure (Chat Script)

```
[PPP_CONN] Executing /etc/start_pppd.sh
[PPP_CONN] PPPD daemon started successfully
[NETMGR-PPP0] PPP0 chat script running (modem negotiation, 5000 ms elapsed)
[NETMGR-PPP0] PPP0 connection FAILED: Chat script failed - check modem AT command response
[NETMGR-PPP0] Recent PPPD log (last 20 lines):
ATDT*99***1#
ERROR
Connect script failed
[NETMGR-PPP0] Check: /var/log/pppd/current for full details
[NETMGR-PPP0] Verify: ls -l /dev/ttyACM* for modem device
```

### Missing Configuration

```
[PPP_CONN] Checking prerequisites for PPPD startup
[PPP_CONN] ERROR: /etc/start_pppd.sh does not exist or not executable
[PPP_CONN] PPP connection unavailable - system configuration required
[PPP_CONN] Required: /etc/start_pppd.sh script for PPPD daemon startup
```

---

## Design Decisions & Rationale

### 1. Wrapper Functions (Chosen Approach)

**Decision:** Keep `start_pppd()` / `stop_pppd()` names in cellular_man.c as thin wrappers

**Rationale:**
- Zero changes required in process_network.c call sites
- Maintains API compatibility
- Easy to switch back if issues found
- Clear separation: cellular_man.c owns interface, ppp_connection.c owns implementation

### 2. Log Read Caching (1 Second)

**Decision:** Cache log file reads for 1 second to reduce I/O

**Implementation:**
```c
static imx_time_t last_log_read_time = 0;
static char cached_log[MAX_LOG_SIZE];
static bool cache_valid = false;

// In ppp_connection_get_status():
imx_time_t now;
imx_time_get_time(&now);

if (cache_valid && imx_time_difference(now, last_log_read_time) < 1000) {
    // Use cached_log
} else {
    // Read log file, update cache
    last_log_read_time = now;
    cache_valid = true;
}
```

**Rationale:**
- `process_network()` calls every 1 second
- Log file doesn't change faster than that
- Reduces filesystem I/O
- Still responsive (1s max staleness)

### 3. Retry Logic in process_network.c

**Decision:** Keep retry management in process_network.c, not ppp_connection.c

**Rationale:**
- Retry policy tied to network manager state machine
- Needs coordination with interface selection
- Cellular blacklisting logic already in process_network
- Separation of concerns: ppp_connection manages daemon, network manager manages policy

### 4. 30-Second Timeout (Keep Current)

**Decision:** Maintain 30-second timeout despite 3-second normal connection time

**Rationale:**
- Working log shows 3 seconds in ideal conditions
- Weak signal areas may take longer
- Chat script retries AT commands
- LCP/IPCP can timeout and retry
- Conservative timeout prevents premature failures
- Can add intermediate logging every 5 seconds for visibility

### 5. Detailed Logging with State Visibility

**Decision:** Log state transitions every 5 seconds during connection

**Rationale:**
- User can see progress (CHAT → LCP → IPCP → CONNECTED)
- Identifies WHERE connection is stuck (not just "waiting")
- Helps diagnose modem issues vs. network issues
- Matches diagnostic philosophy from GPS fix (breadcrumbs)

### 6. Use NETMGR_LOG_PPP0 Macro

**Decision:** Use existing `NETMGR_LOG_PPP0()` macro for consistency

**Rationale:**
- Consistent with rest of network manager logging
- Respects debug flags (`DEBUGS_FOR_PPP0_NETWORKING`)
- Users already know how to enable PPP logging
- Maintains established logging patterns

---

## Implementation Checklist

### Code Changes

- [ ] Create `ppp_connection.h` with data structures and function prototypes
- [ ] Create `ppp_connection.c` with core implementation:
  - [ ] `ppp_connection_init()` - Prerequisites check
  - [ ] `ppp_connection_start()` - Daemon startup
  - [ ] `ppp_connection_stop()` - Daemon shutdown
  - [ ] `ppp_connection_get_status()` - Status query with log parsing
  - [ ] `ppp_connection_parse_log()` - Extract log lines
  - [ ] `ppp_connection_check_health()` - Health analysis
  - [ ] Helper functions (state_name, IP parsing, etc.)
- [ ] Update `cellular_man.c`:
  - [ ] Rename `start_pppd()` → `start_pppd_deprecated()`
  - [ ] Rename `stop_pppd()` → `stop_pppd_deprecated()`
  - [ ] Add new wrapper `start_pppd()` calling `ppp_connection_start()`
  - [ ] Add new wrapper `stop_pppd()` calling `ppp_connection_stop()`
  - [ ] Add `#include "ppp_connection.h"`
- [ ] Update `cellular_man.h`:
  - [ ] Update function declarations
- [ ] Update `process_network.c`:
  - [ ] Add `#include "ppp_connection.h"`
  - [ ] Replace simple device check (lines 4646-4676) with detailed status monitoring
  - [ ] Add `ppp_connection_init()` call in `network_manager_init()`
- [ ] Update `CMakeLists.txt`:
  - [ ] Add `ppp_connection.c` to build sources

### Testing

- [ ] Build verification (zero errors/warnings)
- [ ] Unit test log parsing with working log example
- [ ] Integration test: Normal connection flow
- [ ] Integration test: Connection failure scenarios
- [ ] Integration test: Connection drop and recovery
- [ ] Long-run test: 30+ minutes with multiple cycles
- [ ] Verify diagnostics tools still work (mutex, loopstatus, threads)

### Documentation

- [ ] Add Doxygen comments to all functions
- [ ] Update `CLAUDE.md` with PPP connection module info
- [ ] Create usage examples for log analysis
- [ ] Document state machine in comments

---

## Success Criteria

1. ✅ PPP0 connects successfully using `/etc/start_pppd.sh`
2. ✅ Logs show clear state progression: CHAT → LCP → IPCP → CONNECTED
3. ✅ IP address, DNS servers logged on successful connection
4. ✅ Connection failures show detailed error messages with actionable diagnostics
5. ✅ No "Connect script failed" without explanation
6. ✅ State timeouts identify exact stuck state (e.g., "stuck in IPCP_NEGOTIATION")
7. ✅ Backward compatible - no changes required in cellular_man state machine
8. ✅ Build clean with zero warnings
9. ✅ Works in headless/production environment

---

## Risk Mitigation

### Risks & Mitigation Strategies

| Risk | Mitigation |
|------|------------|
| Log parsing errors crash system | Robust error handling, bounds checking, fopen error checks |
| Log file too large causes memory issues | Read only last N lines (default 100), limit buffer sizes |
| Cache causes stale state data | 1-second cache timeout, invalidate on explicit calls |
| Breaking existing PPP functionality | Keep deprecated functions, use wrappers for compatibility |
| `/etc/start_pppd.sh` doesn't exist | Check in init, fail gracefully with clear error message |
| Log format changes in future | Use flexible pattern matching, multiple fallback patterns |

---

## Future Enhancements (Out of Scope)

- Add CLI command to view PPP status: `ppp status` or `ppp logs`
- Implement automatic chat script retry on specific errors
- Add support for multiple PPP interfaces (ppp0, ppp1)
- Integrate with cellular carrier selection (prefer carriers with fast connect times)
- Export PPP statistics (connection time, failures, uptime)

---

**Plan Created By:** Claude Code
**Date:** November 16, 2025
**Status:** Ready for Implementation
**Estimated Effort:** 4-6 hours development + 2 hours testing

---

This plan is comprehensive and ready for implementation. Shall I proceed with Phase 1 (creating the new ppp_connection module)?
