# PPP0 Connection Refactoring Plan (Enhanced)

**Document:** PPP Connection Refactoring Plan v2
**Date:** November 16, 2025
**Branch:** bugfix/network-stability
**Objective:** Comprehensive refactoring of PPP connection management using PPPD Daemon approach with advanced diagnostics and CLI integration
**Status:** Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Implementation Analysis](#current-implementation-analysis)
3. [Problem Statement](#problem-statement)
4. [Proposed Architecture](#proposed-architecture)
5. [Detailed Design](#detailed-design)
6. [Implementation Phases](#implementation-phases)
7. [CLI Commands Integration](#cli-commands-integration)
8. [Log Parsing Strategy](#log-parsing-strategy)
9. [Testing Strategy](#testing-strategy)
10. [Future Enhancements](#future-enhancements)
11. [References](#references)

---

## Executive Summary

Refactor PPP0 connection management from basic `pon`/`poff` Linux utility commands to a comprehensive daemon-based approach using `/etc/start_pppd.sh` with real-time log parsing via `/var/log/pppd/current`. This transformation provides:

- **Detailed Connection State Visibility:** Track CHAT → LCP → IPCP → CONNECTED progression
- **Comprehensive Diagnostics:** Parse logs for IP addresses, DNS servers, error messages
- **Better Error Reporting:** Actionable error messages instead of generic failures
- **CLI Integration:** New commands for status, logs, and troubleshooting
- **Improved Reliability:** Health checks, prerequisite validation, robust error handling

**Impact:** Reduces PPP connection debugging time from hours to minutes by providing clear visibility into connection state and failure modes.

---

## Current Implementation Analysis

### System Workflow

**Step 1: Cellular Modem Initialization (cellular_man.c)**

```
cellular_man.c state machine:
├── CELL_INIT
├── CELL_CHECK_SIM
├── CELL_GET_IMEI
├── CELL_CHECK_REGISTRATION
├── CELL_SCAN_FOR_CARRIERS
├── CELL_SELECT_CARRIER
├── CELL_REGISTER_ON_NETWORK
└── DONE_INIT_REGISTER ────> Sets cellular_now_ready = TRUE (line 2064)
```

**Step 2: Network Manager Detects Cellular Ready (process_network.c)**

```c
// Line ~4304-4310
if (!g_prev_cellular_ready && current_cellular_ready)
{
    NETMGR_LOG_PPP0(ctx, "Cellular transitioned from NOT_READY to READY, allowing PPP retry");
    ctx->cellular_started = false;  // Allow retry
}
```

**Step 3: Network Manager Starts PPPD (process_network.c)**

```c
// Line 4531
start_pppd();
ctx->cellular_started = true;
ctx->ppp_start_time = current_time;
NETMGR_LOG_PPP0(ctx, "Started pppd, will monitor for PPP0 device creation");
```

**Step 4: Wait for PPP0 Device (process_network.c)**

```c
// Line 4646-4676 - Simple polling loop
if (!has_valid_ip_address("ppp0")) {
    if (time_since_start < 30000) {
        NETMGR_LOG_PPP0(ctx, "PPP0 not ready (device=missing, pppd=running), waiting (%lu ms elapsed)",
                   time_since_start);
    } else {
        NETMGR_LOG_PPP0(ctx, "PPP0 connect script likely failing - no device after %lu ms",
                   time_since_start);
    }
}
```

### Current Implementation of start_pppd()

**Location:** `cellular_man.c:1763-1816`

```c
void start_pppd(void)
{
    char cmd[CMD_LENGTH + 1];

    // Check if pppd is already running
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        PRINTF("[Cellular Connection - PPPD already running, skipping start]\r\n");
        return;
    }

    // Start PPPD using 'pon' command (Linux utility approach)
    snprintf(cmd, sizeof(cmd), "pon");
    system(cmd);
    pppd_start_count++;

    PRINTF("[Cellular Connection - PPPD started (count=%d)]\r\n", pppd_start_count);
}
```

**Problem:** Uses `pon` command which requires `/etc/ppp/peers/provider` configuration file (missing on system).

---

## Problem Statement

### Issues with Current Implementation

#### 1. Missing PPP Configuration

**Symptom:**
```
Nov 15 23:55:21 iMatrix daemon.err pppd[1394]: Connect script failed
```

**Root Cause:**
- Code calls `pon` command (Linux utility approach from QConnect Developer Guide page 27)
- `pon` requires `/etc/ppp/peers/provider` or `/etc/ppp/peers/gprs` configuration
- System has `/etc/start_pppd.sh` (PPPD Daemon approach from page 26) but code doesn't use it

**Evidence from Logs (net3.txt):**
- 128+ "Connect script failed" errors
- PPPD starts but ppp0 device never appears
- Cellular modem ready (cellular_ready=YES, connected to AT&T)
- PPPD daemon running (pidof pppd succeeds)
- But: No ppp0 network interface created

#### 2. Zero Visibility into Connection State

**Current logging:**
```
[NETMGR-PPP0] PPP0 not ready (device=missing, pppd=running), waiting (4211 ms elapsed)
[NETMGR-PPP0] PPP0 connect script likely failing - no device after 34004 ms
```

**What's missing:**
- Is chat script running? (No visibility)
- Is modem responding to AT commands? (Unknown)
- Did LCP negotiation start? (No indication)
- Is IPCP requesting IP? (Cannot tell)
- Why exactly did it fail? (Generic error only)

**Contrast with Working Log:**
```
2025-11-16_23:13:18.35310 ATDT*99***1#
2025-11-16_23:13:18.37091 CONNECT
2025-11-16_23:13:18.38299 Script /usr/sbin/chat finished, status = 0x0
2025-11-16_23:13:18.38367 Serial connection established.
2025-11-16_23:13:19.39756 sent [LCP ConfReq ...]
2025-11-16_23:13:19.40396 rcvd [LCP ConfAck ...]
2025-11-16_23:13:19.41657 sent [IPCP ConfReq ...]
2025-11-16_23:13:19.43240 rcvd [IPCP ConfAck ...]
2025-11-16_23:13:19.45612 local  IP address 10.183.192.75
```

**Result:** Working system provides detailed state progression - current code cannot access this data.

#### 3. No Diagnostic Capability

**Missing Features:**
- Cannot view PPPD logs from CLI
- Cannot see IP address without `ifconfig`
- No health check to identify specific failure point
- Cannot determine if chat/LCP/IPCP stage failed
- No way to check connection history

#### 4. Limited Error Recovery

**Current Approach:**
- Wait 30 seconds
- If no IP, assume failure
- Reset cellular_started flag
- Retry from beginning

**Problems:**
- Cannot distinguish between:
  - Modem not responding (need cellular reset)
  - Chat script error (need script fix)
  - LCP timeout (network/signal issue)
  - APN incorrect (configuration issue)
- All failures treated identically
- Retry may repeat same failure mode

---

## Proposed Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CELLULAR CONNECTION STACK                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────┐         ┌──────────────────────────────┐   │
│  │  cellular_man.c    │         │   process_network.c          │   │
│  │  (State Machine)   │────────>│   (Network Manager)          │   │
│  │                    │ ready   │                               │   │
│  │ - Modem init       │         │ - Detects cellular_ready     │   │
│  │ - AT commands      │         │ - Calls start_pppd()         │   │
│  │ - Carrier scan     │         │ - Monitors connection        │   │
│  │ - Registration     │         │ - Handles failover           │   │
│  └────────────────────┘         └──────────────────────────────┘   │
│           │                                   │                     │
│           │ wrapper calls                     │ status queries      │
│           ▼                                   ▼                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              ppp_connection.c (NEW MODULE)                  │   │
│  │                                                             │   │
│  │ ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │ │ Daemon Control  │  │ Log Parser   │  │ Status Query  │  │   │
│  │ │                 │  │              │  │               │  │   │
│  │ │ - start/stop    │  │ - State      │  │ - Current     │  │   │
│  │ │ - Prerequisites │  │ - IP/DNS     │  │   state       │  │   │
│  │ │ - Validation    │  │ - Errors     │  │ - Health      │  │   │
│  │ └─────────────────┘  └──────────────┘  └───────────────┘  │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                        │                       │        │
│           ▼                        ▼                       ▼        │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐   │
│  │ /etc/start_      │   │ /var/log/pppd/   │   │ CLI Commands │   │
│  │  pppd.sh         │   │  current         │   │ (NEW)        │   │
│  │                  │   │                  │   │              │   │
│  │ - Start daemon   │   │ - Detailed logs  │   │ - ppp status │   │
│  │ - Modem init     │   │ - State info     │   │ - ppp logs   │   │
│  │ - Chat script    │   │ - IP/DNS         │   │ - ppp health │   │
│  └──────────────────┘   └──────────────────┘   └──────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

**cellular_man.c** (No changes to core logic)
- Initialize cellular modem hardware (GPIO 89)
- Execute AT command sequence
- Scan and select carrier
- Set `cellular_now_ready` flag
- Provide thin wrapper functions for backward compatibility

**ppp_connection.c** (NEW)
- Start/stop PPPD daemon via `/etc/start_pppd.sh`
- Parse `/var/log/pppd/current` for connection state
- Extract IP addresses, DNS servers, error messages
- Provide structured status API
- Implement health checking
- Cache log reads for performance

**process_network.c** (Enhanced monitoring)
- Detect `cellular_ready` flag transition
- Call `start_pppd()` wrapper
- Query `ppp_connection_get_status()` for detailed state
- Log state progression with timing
- Handle errors with diagnostic output
- Manage retry policy and carrier blacklisting

---

## Detailed Design

### Data Structures

#### ppp_connection.h - Public API

```c
/**
 * @file ppp_connection.h
 * @brief PPP connection management using PPPD daemon approach
 * @author iMatrix Systems
 * @date November 2025
 *
 * Provides comprehensive PPP connection management with log parsing,
 * state tracking, and diagnostic capabilities.
 */

#ifndef PPP_CONNECTION_H
#define PPP_CONNECTION_H

#include <stdint.h>
#include <stdbool.h>
#include "../../time/ck_time.h"
#include "../../imatrix.h"

/******************************************************
 *                Connection States
 ******************************************************/

/**
 * @brief PPP connection states derived from log analysis
 *
 * States are determined by parsing /var/log/pppd/current for
 * specific protocol messages and events.
 */
typedef enum {
    PPP_STATE_STOPPED,           /**< PPPD daemon not running */
    PPP_STATE_STARTING,          /**< start_pppd.sh executing, daemon initializing */
    PPP_STATE_CHAT_RUNNING,      /**< Chat script sending AT commands to modem */
    PPP_STATE_CHAT_CONNECTED,    /**< Modem responded CONNECT, serial link established */
    PPP_STATE_LCP_NEGOTIATION,   /**< LCP ConfReq/ConfAck exchange in progress */
    PPP_STATE_LCP_ESTABLISHED,   /**< LCP negotiation complete, link layer ready */
    PPP_STATE_IPCP_NEGOTIATION,  /**< IPCP negotiating IP address assignment */
    PPP_STATE_CONNECTED,         /**< ppp0 has IP, ip-up script finished, fully connected */
    PPP_STATE_DISCONNECTING,     /**< Connection terminating, ip-down script running */
    PPP_STATE_ERROR              /**< Connection failed, see last_error field */
} ppp_state_t;

/**
 * @brief PPP connection error categories
 */
typedef enum {
    PPP_ERROR_NONE,
    PPP_ERROR_PREREQUISITES,     /**< Missing /etc/start_pppd.sh or modem device */
    PPP_ERROR_CHAT_SCRIPT,       /**< Chat script failed (modem not responding) */
    PPP_ERROR_NO_CARRIER,        /**< No carrier signal from modem */
    PPP_ERROR_LCP_TIMEOUT,       /**< LCP negotiation timeout */
    PPP_ERROR_IPCP_TIMEOUT,      /**< IPCP negotiation timeout */
    PPP_ERROR_AUTH_FAILED,       /**< Authentication rejected by network */
    PPP_ERROR_MODEM_HANGUP,      /**< Modem disconnected during session */
    PPP_ERROR_DAEMON_DIED,       /**< PPPD process terminated unexpectedly */
    PPP_ERROR_UNKNOWN            /**< Unclassified error */
} ppp_error_t;

/**
 * @brief Comprehensive PPP connection status
 *
 * Populated by ppp_connection_get_status(), provides complete
 * view of connection state, IP configuration, and error information.
 */
typedef struct {
    /* Connection State */
    ppp_state_t state;              /**< Current connection state */
    ppp_error_t error_type;         /**< Error category if state is ERROR */

    /* Process Status */
    bool pppd_running;              /**< PPPD daemon process running (pidof check) */
    bool ppp0_device_exists;        /**< ppp0 network device exists (ifconfig check) */
    bool ppp0_has_ip;               /**< ppp0 has valid IP address */

    /* IP Configuration (from log parsing) */
    char local_ip[16];              /**< Local IP (e.g., "10.183.192.75") */
    char remote_ip[16];             /**< Remote IP (e.g., "10.64.64.64") */
    char dns_primary[16];           /**< Primary DNS (e.g., "8.8.8.8") */
    char dns_secondary[16];         /**< Secondary DNS (e.g., "8.8.4.4") */

    /* Timing Information */
    uint32_t connection_time_ms;    /**< Time since start_pppd() call */
    imx_time_t connection_start;    /**< Timestamp when connection started */
    imx_time_t last_state_change;   /**< Timestamp of last state transition */
    uint32_t time_in_current_state; /**< Milliseconds in current state */

    /* Error Information */
    char last_error[256];           /**< Parsed error message from logs */
    uint32_t chat_script_failures;  /**< Count of "Connect script failed" */
    uint32_t modem_hangups;         /**< Count of "Modem hangup" */
    uint32_t lcp_failures;          /**< Count of "LCP terminated" */

    /* Log Statistics */
    uint32_t log_lines_parsed;      /**< Number of log lines analyzed */
    imx_time_t log_last_read;       /**< When log was last parsed */
} ppp_connection_status_t;

/**
 * @brief PPP connection health check results
 *
 * Analyzes logs for successful progression through connection stages.
 * Used for diagnostics and troubleshooting.
 */
typedef struct {
    /* Success Indicators */
    bool chat_script_ok;         /**< No "Connect script failed" in recent logs */
    bool modem_responded;        /**< Saw "CONNECT" response from modem */
    bool serial_established;     /**< Saw "Serial connection established" */
    bool lcp_negotiated;         /**< Saw "LCP ConfAck" exchange */
    bool ipcp_negotiated;        /**< Saw "IPCP ConfAck" exchange */
    bool ip_assigned;            /**< Saw "local  IP address" */
    bool ip_up_script_ok;        /**< ip-up script finished successfully (status = 0x0) */

    /* Failure Indicators */
    bool has_errors;             /**< Any error messages found */
    char failure_reason[256];    /**< Detailed failure reason if unhealthy */
    ppp_error_t error_category;  /**< Categorized error type */

    /* Analysis Metadata */
    uint32_t log_lines_analyzed; /**< Number of log lines checked */
    imx_time_t analysis_time;    /**< When health check was performed */
} ppp_health_check_t;

/******************************************************
 *                Function Prototypes
 ******************************************************/

/**
 * @brief Initialize PPP connection module
 *
 * Checks for required files and configurations:
 * - /etc/start_pppd.sh exists and is executable
 * - /var/log/pppd/ directory exists and is writable
 * - /dev/ttyACM0 modem device exists
 *
 * Should be called once during network manager initialization.
 *
 * @return IMX_SUCCESS if initialization successful, IMX_ERROR otherwise
 */
imx_result_t ppp_connection_init(void);

/**
 * @brief Start PPPD daemon using /etc/start_pppd.sh
 *
 * Executes the PPPD startup script which handles:
 * - Modem device verification
 * - Chat script execution
 * - PPPD daemon launch with proper options
 *
 * Returns immediately after starting daemon. Use ppp_connection_get_status()
 * to monitor connection progress.
 *
 * @return IMX_SUCCESS if daemon started, IMX_ERROR on failure
 */
imx_result_t ppp_connection_start(void);

/**
 * @brief Stop PPPD daemon and clean up resources
 *
 * Terminates PPPD daemon which triggers:
 * - ip-down script execution
 * - ppp0 device removal
 * - Route cleanup
 *
 * @param cellular_reset true if stopping due to cellular reset, false for normal shutdown
 * @return IMX_SUCCESS if stopped cleanly, IMX_ERROR on failure
 */
imx_result_t ppp_connection_stop(bool cellular_reset);

/**
 * @brief Get current PPP connection status with detailed state
 *
 * Queries PPPD daemon status and parses logs to determine:
 * - Current connection state
 * - IP configuration details
 * - Error information if failed
 * - Timing statistics
 *
 * Results are cached for 1 second to minimize filesystem I/O.
 *
 * @param status Pointer to status structure to populate
 * @return IMX_SUCCESS if status retrieved, IMX_ERROR if unavailable
 */
imx_result_t ppp_connection_get_status(ppp_connection_status_t *status);

/**
 * @brief Parse recent PPPD log entries
 *
 * Extracts last N lines from /var/log/pppd/current for display
 * or diagnostic purposes.
 *
 * @param buffer Output buffer for log content
 * @param max_len Maximum buffer size
 * @param lines_to_read Number of recent lines to extract (0 = last 100 lines)
 * @return IMX_SUCCESS if parsed, IMX_ERROR if log unavailable
 */
imx_result_t ppp_connection_parse_log(char *buffer, size_t max_len, uint32_t lines_to_read);

/**
 * @brief Perform health check on PPP connection
 *
 * Analyzes recent logs to verify successful progression through
 * connection stages. Identifies specific failure point if unhealthy.
 *
 * @param health Pointer to health check structure to populate
 * @return IMX_SUCCESS if check completed, IMX_ERROR if log unavailable
 */
imx_result_t ppp_connection_check_health(ppp_health_check_t *health);

/**
 * @brief Get human-readable state name
 *
 * @param state PPP state enum value
 * @return String representation of state
 */
const char* ppp_state_name(ppp_state_t state);

/**
 * @brief Get human-readable error type name
 *
 * @param error PPP error enum value
 * @return String representation of error type
 */
const char* ppp_error_name(ppp_error_t error);

/**
 * @brief Restart PPPD daemon
 *
 * Convenience function that stops and restarts daemon.
 * Useful for error recovery scenarios.
 *
 * @return IMX_SUCCESS if restarted, IMX_ERROR on failure
 */
imx_result_t ppp_connection_restart(void);

/**
 * @brief Clear cached log data to force fresh read
 *
 * Call when you need immediate/uncached status information.
 */
void ppp_connection_clear_cache(void);

#endif /* PPP_CONNECTION_H */
```

---

### Internal Implementation Details

#### ppp_connection.c - Private Data

```c
/**
 * @file ppp_connection.c
 * @brief PPP connection management implementation
 */

/******************************************************
 *                Internal State
 ******************************************************/

/* Log parsing cache */
static struct {
    char cached_log[8192];          /* Last 100 lines from log file */
    uint32_t cached_lines;          /* Number of lines in cache */
    imx_time_t last_read_time;      /* When cache was populated */
    bool valid;                     /* Cache validity flag */
    ppp_state_t last_parsed_state;  /* Last state from parse */
} g_log_cache = {0};

/* Connection tracking */
static struct {
    bool initialized;               /* Module initialized */
    bool prerequisites_checked;     /* Prerequisites verified */
    bool start_script_exists;       /* /etc/start_pppd.sh available */
    bool log_dir_writable;          /* /var/log/pppd/ writable */
    imx_time_t init_time;           /* Module initialization time */
} g_ppp_module = {0};

/* Statistics */
static struct {
    uint32_t successful_connections;
    uint32_t failed_connections;
    uint32_t total_disconnects;
    imx_time_t longest_connection_time;
    imx_time_t shortest_connection_time;
} g_ppp_stats = {0};

/******************************************************
 *                Helper Functions
 ******************************************************/

/**
 * @brief Check if PPPD daemon process is running
 * @return true if running, false otherwise
 */
static bool is_pppd_running(void)
{
    return (system("pidof pppd >/dev/null 2>&1") == 0);
}

/**
 * @brief Check if ppp0 network device exists
 * @return true if exists, false otherwise
 */
static bool does_ppp0_exist(void)
{
    return (system("ifconfig ppp0 >/dev/null 2>&1") == 0);
}

/**
 * @brief Read last N lines from log file into cache
 * @param lines Number of lines to read (0 = all available, max 100)
 * @return IMX_SUCCESS if read, IMX_ERROR on failure
 */
static imx_result_t read_pppd_log_to_cache(uint32_t lines);

/**
 * @brief Parse cached log for current connection state
 * @return Detected state from log patterns
 */
static ppp_state_t parse_state_from_cached_log(void);

/**
 * @brief Extract IP address from log line
 * @param line Log line containing "local  IP address X.X.X.X"
 * @param ip_buffer Buffer to store extracted IP (min 16 bytes)
 * @return true if extracted, false if pattern not found
 */
static bool extract_ip_from_log_line(const char *line, char *ip_buffer);

/**
 * @brief Categorize error from log patterns
 * @param log Cached log buffer
 * @return Error category enum
 */
static ppp_error_t categorize_error_from_log(const char *log);
```

---

## Implementation Phases

### Phase 1: Create Core Module (ppp_connection.c/h)

#### Step 1.1: Create Header File

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/ppp_connection.h`

Include:
- All public data structures (shown above)
- All function prototypes
- Doxygen documentation for each
- Include guards
- Required system headers

**Estimated Time:** 30 minutes

#### Step 1.2: Implement Initialization

**Function:** `ppp_connection_init()`

**Implementation:**
```c
imx_result_t ppp_connection_init(void)
{
    if (g_ppp_module.initialized) {
        return IMX_SUCCESS;  /* Already initialized */
    }

    imx_time_get_time(&g_ppp_module.init_time);

    /* Check for /etc/start_pppd.sh */
    if (access("/etc/start_pppd.sh", X_OK) == 0) {
        g_ppp_module.start_script_exists = true;
        PRINTF("[PPP_CONN] Prerequisites: /etc/start_pppd.sh exists (executable: YES)\r\n");
    } else {
        g_ppp_module.start_script_exists = false;
        PRINTF("[PPP_CONN] ERROR: /etc/start_pppd.sh not found or not executable\r\n");
        PRINTF("[PPP_CONN] PPP connection unavailable - system configuration required\r\n");
        PRINTF("[PPP_CONN] See: QConnect Developer Guide page 26 (PPPD Daemon approach)\r\n");
        /* Don't fail init - allow system to run without PPP */
    }

    /* Check log directory */
    if (access("/var/log/pppd", W_OK) == 0) {
        g_ppp_module.log_dir_writable = true;
        PRINTF("[PPP_CONN] Log directory: /var/log/pppd/ (writable: YES)\r\n");
    } else {
        g_ppp_module.log_dir_writable = false;
        PRINTF("[PPP_CONN] WARNING: /var/log/pppd/ not writable - logging may fail\r\n");
    }

    /* Check modem device */
    if (access("/dev/ttyACM0", F_OK) == 0) {
        PRINTF("[PPP_CONN] Modem device: /dev/ttyACM0 (exists: YES)\r\n");
    } else {
        PRINTF("[PPP_CONN] WARNING: /dev/ttyACM0 not found - modem may not be ready\r\n");
        PRINTF("[PPP_CONN] This is normal on startup, modem will appear after GPIO 89 enabled\r\n");
    }

    /* Initialize cache */
    memset(&g_log_cache, 0, sizeof(g_log_cache));

    /* Initialize statistics */
    memset(&g_ppp_stats, 0, sizeof(g_ppp_stats));

    g_ppp_module.initialized = true;
    g_ppp_module.prerequisites_checked = true;

    PRINTF("[PPP_CONN] PPP connection module initialized\r\n");
    return IMX_SUCCESS;
}
```

**Estimated Time:** 45 minutes

#### Step 1.3: Implement Daemon Control

**Function:** `ppp_connection_start()`

**Implementation:**
```c
imx_result_t ppp_connection_start(void)
{
    /* Verify initialization */
    if (!g_ppp_module.initialized) {
        PRINTF("[PPP_CONN] ERROR: Module not initialized, call ppp_connection_init() first\r\n");
        return IMX_ERROR;
    }

    /* Check prerequisites */
    if (!g_ppp_module.start_script_exists) {
        PRINTF("[PPP_CONN] ERROR: Cannot start - /etc/start_pppd.sh missing\r\n");
        return IMX_ERROR;
    }

    /* Check if already running */
    if (is_pppd_running()) {
        PRINTF("[PPP_CONN] PPPD already running, skipping start\r\n");
        return IMX_SUCCESS;
    }

    /* Verify modem device exists NOW (after cellular_man enabled it) */
    if (access("/dev/ttyACM0", F_OK) != 0) {
        PRINTF("[PPP_CONN] ERROR: Modem device /dev/ttyACM0 not available\r\n");
        PRINTF("[PPP_CONN] Verify cellular modem is powered (GPIO 89 = 1)\r\n");
        return IMX_ERROR;
    }

    /* Execute start script */
    PRINTF("[PPP_CONN] Starting PPPD daemon: /etc/start_pppd.sh\r\n");

    int result = system("/etc/start_pppd.sh");

    if (result != 0) {
        PRINTF("[PPP_CONN] ERROR: start_pppd.sh failed with exit code %d\r\n", result);
        PRINTF("[PPP_CONN] Check system logs for script errors\r\n");
        g_ppp_stats.failed_connections++;
        return IMX_ERROR;
    }

    /* Wait briefly for daemon to initialize */
    usleep(500000);  /* 500ms */

    /* Verify daemon started */
    if (!is_pppd_running()) {
        PRINTF("[PPP_CONN] ERROR: PPPD daemon failed to start\r\n");
        PRINTF("[PPP_CONN] Check /var/log/pppd/current for error details\r\n");
        g_ppp_stats.failed_connections++;
        return IMX_ERROR;
    }

    PRINTF("[PPP_CONN] PPPD daemon started successfully\r\n");
    PRINTF("[PPP_CONN] Monitor connection via ppp_connection_get_status()\r\n");

    /* Clear cache to force fresh read */
    ppp_connection_clear_cache();

    return IMX_SUCCESS;
}
```

**Function:** `ppp_connection_stop()`

**Implementation:**
```c
imx_result_t ppp_connection_stop(bool cellular_reset)
{
    /* Check if running */
    if (!is_pppd_running()) {
        PRINTF("[PPP_CONN] PPPD not running, skipping stop\r\n");
        return IMX_SUCCESS;
    }

    PRINTF("[PPP_CONN] Stopping PPPD daemon (reason: %s)\r\n",
           cellular_reset ? "cellular_reset" : "normal_shutdown");

    /* Send SIGTERM for graceful shutdown (allows ip-down script to run) */
    int result = system("killall -TERM pppd 2>/dev/null");

    if (result != 0) {
        PRINTF("[PPP_CONN] WARNING: killall -TERM failed, attempting kill -9\r\n");
        system("killall -9 pppd 2>/dev/null");
    }

    /* Wait up to 2 seconds for graceful exit */
    int wait_count = 0;
    while (is_pppd_running() && wait_count < 20) {
        usleep(100000);  /* 100ms */
        wait_count++;
    }

    /* Force kill if still running */
    if (is_pppd_running()) {
        PRINTF("[PPP_CONN] WARNING: PPPD did not exit gracefully, sending SIGKILL\r\n");
        system("killall -9 pppd 2>/dev/null");
        usleep(500000);  /* 500ms */
    }

    /* Clean up lock files */
    system("rm -f /var/lock/LCK..ttyACM0 2>/dev/null");

    /* Verify stopped */
    if (is_pppd_running()) {
        PRINTF("[PPP_CONN] ERROR: Failed to stop PPPD daemon\r\n");
        return IMX_ERROR;
    }

    PRINTF("[PPP_CONN] PPPD daemon stopped successfully\r\n");

    /* Update statistics */
    g_ppp_stats.total_disconnects++;

    /* Clear cache */
    ppp_connection_clear_cache();

    return IMX_SUCCESS;
}
```

**Estimated Time:** 1 hour

#### Step 1.4: Implement Log Parsing

**Function:** `read_pppd_log_to_cache()`

**Implementation Strategy:**
- Use `tail -n 100 /var/log/pppd/current` to get last 100 lines
- Store in `g_log_cache.cached_log`
- Set `g_log_cache.valid = true`
- Update `g_log_cache.last_read_time`

**Function:** `parse_state_from_cached_log()`

**State Detection Logic:**
```c
static ppp_state_t parse_state_from_cached_log(void)
{
    const char *log = g_log_cache.cached_log;

    /* Search in reverse chronological order (most recent first) */

    /* Check for final connected state */
    if (strstr(log, "local  IP address") && strstr(log, "ip-up finished")) {
        return PPP_STATE_CONNECTED;
    }

    /* Check for IPCP negotiation */
    if (strstr(log, "IPCP ConfReq") || strstr(log, "IPCP ConfAck")) {
        if (!strstr(log, "local  IP address")) {
            return PPP_STATE_IPCP_NEGOTIATION;
        }
    }

    /* Check for LCP established */
    if (strstr(log, "LCP ConfAck")) {
        if (!strstr(log, "IPCP ConfReq")) {
            return PPP_STATE_LCP_ESTABLISHED;
        }
    }

    /* Check for LCP negotiation */
    if (strstr(log, "LCP ConfReq")) {
        if (!strstr(log, "LCP ConfAck")) {
            return PPP_STATE_LCP_NEGOTIATION;
        }
    }

    /* Check for chat script success */
    if (strstr(log, "CONNECT") && strstr(log, "Serial connection established")) {
        if (!strstr(log, "LCP ConfReq")) {
            return PPP_STATE_CHAT_CONNECTED;
        }
    }

    /* Check for chat script running */
    if (strstr(log, "ATDT*99***1#") || strstr(log, "chat -V -f")) {
        if (!strstr(log, "CONNECT")) {
            return PPP_STATE_CHAT_RUNNING;
        }
    }

    /* Check for daemon starting */
    if (strstr(log, "Start Pppd") || strstr(log, "starting pppd")) {
        if (!strstr(log, "ATDT")) {
            return PPP_STATE_STARTING;
        }
    }

    /* Check for errors */
    if (strstr(log, "Connect script failed") ||
        strstr(log, "Modem hangup") ||
        strstr(log, "LCP terminated")) {
        return PPP_STATE_ERROR;
    }

    /* Check if disconnecting */
    if (strstr(log, "Terminating") || strstr(log, "ip-down started")) {
        return PPP_STATE_DISCONNECTING;
    }

    /* Default: If pppd running but no state indicators, assume STARTING */
    if (is_pppd_running()) {
        return PPP_STATE_STARTING;
    }

    return PPP_STATE_STOPPED;
}
```

**Estimated Time:** 2 hours

#### Step 1.5: Implement Status Query

**Function:** `ppp_connection_get_status()`

**Implementation:**
```c
imx_result_t ppp_connection_get_status(ppp_connection_status_t *status)
{
    if (!g_ppp_module.initialized) {
        return IMX_ERROR;
    }

    /* Initialize status structure */
    memset(status, 0, sizeof(*status));

    imx_time_t current_time;
    imx_time_get_time(&current_time);

    /* Check process status */
    status->pppd_running = is_pppd_running();
    status->ppp0_device_exists = does_ppp0_exist();
    status->ppp0_has_ip = has_valid_ip_address("ppp0");

    /* If not running, return early */
    if (!status->pppd_running) {
        status->state = PPP_STATE_STOPPED;
        status->error_type = PPP_ERROR_NONE;
        return IMX_SUCCESS;
    }

    /* Check if cache is valid (< 1 second old) */
    bool need_refresh = !g_log_cache.valid ||
                        imx_time_difference(current_time, g_log_cache.last_read_time) >= 1000;

    if (need_refresh) {
        if (read_pppd_log_to_cache(100) != IMX_SUCCESS) {
            PRINTF("[PPP_CONN] WARNING: Failed to read PPPD log\r\n");
            /* Continue with basic status */
            status->state = status->ppp0_has_ip ? PPP_STATE_CONNECTED : PPP_STATE_STARTING;
            return IMX_SUCCESS;
        }
    }

    /* Parse state from logs */
    status->state = parse_state_from_cached_log();
    status->log_lines_parsed = g_log_cache.cached_lines;
    status->log_last_read = g_log_cache.last_read_time;

    /* Extract IP configuration if connected */
    if (status->state == PPP_STATE_CONNECTED || status->ppp0_has_ip) {
        parse_ip_configuration_from_log(g_log_cache.cached_log, status);
    }

    /* Check for errors */
    if (status->state == PPP_STATE_ERROR) {
        status->error_type = categorize_error_from_log(g_log_cache.cached_log);
        extract_error_message_from_log(g_log_cache.cached_log, status->last_error,
                                       sizeof(status->last_error));
    }

    /* Count error occurrences in log */
    status->chat_script_failures = count_occurrences(g_log_cache.cached_log, "Connect script failed");
    status->modem_hangups = count_occurrences(g_log_cache.cached_log, "Modem hangup");
    status->lcp_failures = count_occurrences(g_log_cache.cached_log, "LCP terminated");

    return IMX_SUCCESS;
}
```

**Estimated Time:** 1.5 hours

#### Step 1.6: Implement Health Check

**Function:** `ppp_connection_check_health()`

**Implementation:**
```c
imx_result_t ppp_connection_check_health(ppp_health_check_t *health)
{
    memset(health, 0, sizeof(*health));

    imx_time_get_time(&health->analysis_time);

    /* Ensure we have fresh log data */
    if (read_pppd_log_to_cache(200) != IMX_SUCCESS) {
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "Unable to read /var/log/pppd/current");
        health->has_errors = true;
        health->error_category = PPP_ERROR_PREREQUISITES;
        return IMX_ERROR;
    }

    const char *log = g_log_cache.cached_log;
    health->log_lines_analyzed = g_log_cache.cached_lines;

    /* Check success progression */
    health->chat_script_ok = (strstr(log, "Connect script failed") == NULL);
    health->modem_responded = (strstr(log, "CONNECT") != NULL);
    health->serial_established = (strstr(log, "Serial connection established") != NULL);
    health->lcp_negotiated = (strstr(log, "LCP ConfAck") != NULL);
    health->ipcp_negotiated = (strstr(log, "IPCP ConfAck") != NULL);
    health->ip_assigned = (strstr(log, "local  IP address") != NULL);
    health->ip_up_script_ok = (strstr(log, "ip-up finished") != NULL &&
                               strstr(log, "status = 0x0") != NULL);

    /* Categorize errors if any stage failed */
    if (!health->chat_script_ok) {
        health->has_errors = true;
        health->error_category = PPP_ERROR_CHAT_SCRIPT;
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "Chat script failed - modem not responding to AT commands");
    } else if (health->modem_responded && !health->serial_established) {
        health->has_errors = true;
        health->error_category = PPP_ERROR_NO_CARRIER;
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "Modem CONNECT received but serial link failed to establish");
    } else if (health->serial_established && !health->lcp_negotiated) {
        health->has_errors = true;
        health->error_category = PPP_ERROR_LCP_TIMEOUT;
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "LCP negotiation failed or timed out");
    } else if (health->lcp_negotiated && !health->ipcp_negotiated) {
        health->has_errors = true;
        health->error_category = PPP_ERROR_IPCP_TIMEOUT;
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "IPCP negotiation failed or timed out");
    } else if (health->ipcp_negotiated && !health->ip_assigned) {
        health->has_errors = true;
        health->error_category = PPP_ERROR_IPCP_TIMEOUT;
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "IPCP negotiated but no IP address assigned");
    }

    /* Check for modem hangup */
    if (strstr(log, "Modem hangup")) {
        health->has_errors = true;
        health->error_category = PPP_ERROR_MODEM_HANGUP;
        snprintf(health->failure_reason, sizeof(health->failure_reason),
                 "Modem hung up - check signal strength and carrier");
    }

    return IMX_SUCCESS;
}
```

**Estimated Time:** 1 hour

**Total Phase 1 Time:** 5-6 hours

---

### Phase 2: Update cellular_man.c

#### Step 2.1: Rename Existing Functions

**Line 1763-1816:**

```c
/**
 * @brief DEPRECATED: Start PPPD using legacy 'pon' command
 *
 * @deprecated This function is deprecated. Use ppp_connection_start() from
 *             ppp_connection.c instead, which uses the PPPD Daemon approach
 *             with /etc/start_pppd.sh for better logging and control.
 *
 * @note Original implementation uses 'pon' Linux utility (QConnect Guide p.27)
 *       which requires /etc/ppp/peers/provider configuration file.
 *
 * @note Kept for reference only. All new development should use the
 *       PPPD Daemon approach (QConnect Guide p.26).
 *
 * @warning This function will be removed in a future release.
 *
 * @see ppp_connection_start() for new implementation
 * @see QConnect Developer Guide document #1180-3007, page 26-27
 */
void start_pppd_deprecated(void)
{
    /* ... existing pon-based implementation ... */
}

/**
 * @brief DEPRECATED: Stop PPPD using legacy 'poff' command
 *
 * @deprecated Use ppp_connection_stop() from ppp_connection.c instead
 *
 * @param cellular_reset true if stopping due to cellular reset
 *
 * @see ppp_connection_stop() for new implementation
 */
void stop_pppd_deprecated(bool cellular_reset)
{
    /* ... existing poff-based implementation ... */
}
```

#### Step 2.2: Add New Wrapper Functions

**After deprecated functions, add:**

```c
/**
 * @brief Start PPPD using daemon-based approach
 *
 * Wrapper function that calls the new implementation in ppp_connection.c.
 * Uses /etc/start_pppd.sh script for better logging and control.
 *
 * @return None (logs errors internally)
 *
 * @note This maintains API compatibility with existing call sites
 * @see ppp_connection_start() for implementation details
 */
void start_pppd(void)
{
    if (ppp_connection_start() != IMX_SUCCESS) {
        PRINTF("[Cellular Connection - PPPD start failed, see logs above]\r\n");
    }
}

/**
 * @brief Stop PPPD using daemon-based approach
 *
 * Wrapper function that calls the new implementation in ppp_connection.c.
 *
 * @param cellular_reset true if stopping due to cellular reset, false otherwise
 *
 * @note This maintains API compatibility with existing call sites
 * @see ppp_connection_stop() for implementation details
 */
void stop_pppd(bool cellular_reset)
{
    if (ppp_connection_stop(cellular_reset) != IMX_SUCCESS) {
        PRINTF("[Cellular Connection - PPPD stop failed, may still be running]\r\n");
    }
}
```

#### Step 2.3: Update Header

**File:** `cellular_man.h`

Add include:
```c
#include "ppp_connection.h"
```

**Estimated Time:** 30 minutes

---

### Phase 3: Enhance process_network.c

#### Step 3.1: Add Include

**Line ~84:**
```c
#include "ppp_connection.h"
```

#### Step 3.2: Add Initialization Call

**Function:** `network_manager_init()` at line 4230

```c
/* Initialize PPP connection module */
if (ppp_connection_init() != IMX_SUCCESS) {
    NETMGR_LOG(&g_netmgr_ctx, "WARNING: PPP connection module initialization failed");
    NETMGR_LOG(&g_netmgr_ctx, "PPP0 cellular connectivity may not be available");
    NETMGR_LOG(&g_netmgr_ctx, "Check /etc/start_pppd.sh exists and is executable");
} else {
    NETMGR_LOG(&g_netmgr_ctx, "PPP connection module initialized successfully");
}
```

#### Step 3.3: Replace PPP Monitoring Logic

**Location:** Lines 4646-4676

**Current simple check:**
```c
if (!has_valid_ip_address("ppp0")) {
    // Generic waiting message
}
```

**New detailed status monitoring:**

```c
/*
 * Enhanced PPP0 connection monitoring with state visibility
 * Uses ppp_connection module for detailed status and diagnostics
 */
if (ctx->cellular_started && !ctx->states[IFACE_PPP].active)
{
    ppp_connection_status_t ppp_status;

    if (ppp_connection_get_status(&ppp_status) == IMX_SUCCESS)
    {
        imx_time_t time_since_start = imx_time_difference(current_time, ctx->ppp_start_time);

        /* Update connection time tracking */
        ppp_status.connection_time_ms = time_since_start;

        switch (ppp_status.state)
        {
        case PPP_STATE_STOPPED:
            /* Daemon not running - unexpected state */
            if (time_since_start > 5000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 daemon not running (expected after start_pppd call)");
                NETMGR_LOG_PPP0(ctx, "Possible causes: start_pppd.sh failed, daemon crashed");

                /* Check health to understand why */
                ppp_health_check_t health;
                if (ppp_connection_check_health(&health) == IMX_SUCCESS && health.has_errors) {
                    NETMGR_LOG_PPP0(ctx, "Health check: %s", health.failure_reason);
                }

                /* Reset to allow retry */
                ctx->cellular_started = false;
            }
            break;

        case PPP_STATE_STARTING:
            /* Daemon starting, no chat activity yet */
            if (time_since_start % 5000 < 1000) {  /* Log every 5 seconds */
                NETMGR_LOG_PPP0(ctx, "PPP0 daemon starting (%lu ms elapsed)", time_since_start);
            }

            /* Timeout check */
            if (time_since_start > 10000) {
                NETMGR_LOG_PPP0(ctx, "WARNING: PPP0 stuck in STARTING state for %lu ms",
                           time_since_start);
                NETMGR_LOG_PPP0(ctx, "Expected: Chat script should begin within 2-3 seconds");
            }
            break;

        case PPP_STATE_CHAT_RUNNING:
            /* Chat script communicating with modem */
            if (time_since_start % 5000 < 1000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 chat script running (AT command sequence, %lu ms elapsed)",
                           time_since_start);
            }

            if (time_since_start > 15000) {
                NETMGR_LOG_PPP0(ctx, "WARNING: Chat script taking longer than expected (%lu ms)",
                           time_since_start);
                NETMGR_LOG_PPP0(ctx, "Possible modem communication issue or weak signal");
            }
            break;

        case PPP_STATE_CHAT_CONNECTED:
            /* Modem responded CONNECT, serial link established */
            NETMGR_LOG_PPP0(ctx, "PPP0 modem CONNECT received, serial link established (%lu ms)",
                       time_since_start);
            break;

        case PPP_STATE_LCP_NEGOTIATION:
            /* LCP handshake in progress */
            if (time_since_start % 5000 < 1000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 LCP negotiation (link control protocol, %lu ms elapsed)",
                           time_since_start);
            }

            if (time_since_start > 20000) {
                NETMGR_LOG_PPP0(ctx, "WARNING: LCP negotiation timeout (%lu ms)", time_since_start);
            }
            break;

        case PPP_STATE_LCP_ESTABLISHED:
            /* LCP complete, ready for IP negotiation */
            NETMGR_LOG_PPP0(ctx, "PPP0 LCP established (%lu ms)", time_since_start);
            break;

        case PPP_STATE_IPCP_NEGOTIATION:
            /* IPCP requesting IP address */
            if (time_since_start % 5000 < 1000) {
                NETMGR_LOG_PPP0(ctx, "PPP0 IPCP negotiation (requesting IP address, %lu ms elapsed)",
                           time_since_start);
            }

            if (time_since_start > 25000) {
                NETMGR_LOG_PPP0(ctx, "WARNING: IPCP taking longer than expected (%lu ms)",
                           time_since_start);
                NETMGR_LOG_PPP0(ctx, "Network may be slow or APN configuration issue");
            }
            break;

        case PPP_STATE_CONNECTED:
            /* Fully connected with IP address */
            NETMGR_LOG_PPP0(ctx, "PPP0 CONNECTION ESTABLISHED:");
            NETMGR_LOG_PPP0(ctx, "  Local IP:  %s", ppp_status.local_ip);
            NETMGR_LOG_PPP0(ctx, "  Remote IP: %s", ppp_status.remote_ip);
            NETMGR_LOG_PPP0(ctx, "  DNS 1:     %s", ppp_status.dns_primary);
            NETMGR_LOG_PPP0(ctx, "  DNS 2:     %s", ppp_status.dns_secondary);
            NETMGR_LOG_PPP0(ctx, "  Time:      %lu ms", time_since_start);

            /* Mark interface as active */
            MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
            ctx->states[IFACE_PPP].active = true;
            MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);

            /* Update statistics */
            if (time_since_start < 10000) {
                NETMGR_LOG_PPP0(ctx, "Connection established in %lu ms (excellent)", time_since_start);
            } else if (time_since_start < 20000) {
                NETMGR_LOG_PPP0(ctx, "Connection established in %lu ms (normal)", time_since_start);
            } else {
                NETMGR_LOG_PPP0(ctx, "Connection established in %lu ms (slow - check signal)",
                           time_since_start);
            }
            break;

        case PPP_STATE_DISCONNECTING:
            /* Connection terminating */
            NETMGR_LOG_PPP0(ctx, "PPP0 disconnecting (ip-down script running)");
            break;

        case PPP_STATE_ERROR:
            /* Connection failed - provide detailed diagnostics */
            NETMGR_LOG_PPP0(ctx, "========================================");
            NETMGR_LOG_PPP0(ctx, "PPP0 CONNECTION FAILED");
            NETMGR_LOG_PPP0(ctx, "========================================");
            NETMGR_LOG_PPP0(ctx, "Error Type: %s", ppp_error_name(ppp_status.error_type));
            NETMGR_LOG_PPP0(ctx, "Error Message: %s", ppp_status.last_error);
            NETMGR_LOG_PPP0(ctx, "Time Elapsed: %lu ms", time_since_start);

            /* Perform detailed health check */
            ppp_health_check_t health;
            if (ppp_connection_check_health(&health) == IMX_SUCCESS) {
                NETMGR_LOG_PPP0(ctx, "Health Check Results:");
                NETMGR_LOG_PPP0(ctx, "  Chat Script:       %s", health.chat_script_ok ? "OK" : "FAILED");
                NETMGR_LOG_PPP0(ctx, "  Modem Response:    %s", health.modem_responded ? "OK" : "FAILED");
                NETMGR_LOG_PPP0(ctx, "  Serial Link:       %s", health.serial_established ? "OK" : "FAILED");
                NETMGR_LOG_PPP0(ctx, "  LCP Negotiation:   %s", health.lcp_negotiated ? "OK" : "FAILED");
                NETMGR_LOG_PPP0(ctx, "  IPCP Negotiation:  %s", health.ipcp_negotiated ? "OK" : "FAILED");
                NETMGR_LOG_PPP0(ctx, "  IP Assignment:     %s", health.ip_assigned ? "OK" : "FAILED");

                if (health.has_errors) {
                    NETMGR_LOG_PPP0(ctx, "Failure Analysis: %s", health.failure_reason);
                }
            }

            /* Show recent logs for debugging */
            char log_buffer[1024];
            if (ppp_connection_parse_log(log_buffer, sizeof(log_buffer), 20) == IMX_SUCCESS) {
                NETMGR_LOG_PPP0(ctx, "Recent PPPD Log (last 20 lines):");
                NETMGR_LOG_PPP0(ctx, "----------------------------------------");
                NETMGR_LOG_PPP0(ctx, "%s", log_buffer);
                NETMGR_LOG_PPP0(ctx, "----------------------------------------");
            }

            /* Actionable diagnostics based on error type */
            switch (ppp_status.error_type) {
            case PPP_ERROR_CHAT_SCRIPT:
                NETMGR_LOG_PPP0(ctx, "Troubleshooting Steps:");
                NETMGR_LOG_PPP0(ctx, "  1. Check modem: ls -l /dev/ttyACM*");
                NETMGR_LOG_PPP0(ctx, "  2. Test AT commands: echo -e 'at\\r' | microcom -t 2000 /dev/ttyACM2");
                NETMGR_LOG_PPP0(ctx, "  3. Verify SIM: echo -e 'at+cpin?\\r' | microcom -t 2000 /dev/ttyACM2");
                break;

            case PPP_ERROR_NO_CARRIER:
                NETMGR_LOG_PPP0(ctx, "Troubleshooting Steps:");
                NETMGR_LOG_PPP0(ctx, "  1. Check signal: echo -e 'at+csq\\r' | microcom -t 2000 /dev/ttyACM2");
                NETMGR_LOG_PPP0(ctx, "  2. Check registration: echo -e 'at+creg?\\r' | microcom -t 2000 /dev/ttyACM2");
                NETMGR_LOG_PPP0(ctx, "  3. Verify carrier: echo -e 'at+cops?\\r' | microcom -t 2000 /dev/ttyACM2");
                break;

            case PPP_ERROR_LCP_TIMEOUT:
            case PPP_ERROR_IPCP_TIMEOUT:
                NETMGR_LOG_PPP0(ctx, "Troubleshooting Steps:");
                NETMGR_LOG_PPP0(ctx, "  1. Check APN: echo -e 'at+cgdcont?\\r' | microcom -t 2000 /dev/ttyACM2");
                NETMGR_LOG_PPP0(ctx, "  2. Verify network registration complete");
                NETMGR_LOG_PPP0(ctx, "  3. Check signal strength (weak signal can cause timeouts)");
                break;

            default:
                NETMGR_LOG_PPP0(ctx, "Check: /var/log/pppd/current for detailed error information");
                break;
            }

            NETMGR_LOG_PPP0(ctx, "========================================");

            /* Reset to allow retry */
            ctx->cellular_started = false;
            break;
        }

        /* Overall timeout check (30 seconds) */
        if (time_since_start > 30000 && ppp_status.state != PPP_STATE_CONNECTED) {
            NETMGR_LOG_PPP0(ctx, "PPP0 connection TIMEOUT after %lu ms", time_since_start);
            NETMGR_LOG_PPP0(ctx, "Final state: %s", ppp_state_name(ppp_status.state));
            NETMGR_LOG_PPP0(ctx, "Expected connection time: 3-5 seconds (normal conditions)");

            /* Perform final health check */
            ppp_health_check_t health;
            ppp_connection_check_health(&health);
            NETMGR_LOG_PPP0(ctx, "Failure Point: %s", health.failure_reason);

            /* Reset for retry */
            ctx->cellular_started = false;

            /* Could blacklist carrier here if IPCP consistently fails */
        }
    }
    else
    {
        /* Error getting status - should not happen */
        NETMGR_LOG_PPP0(ctx, "ERROR: Failed to get PPP connection status");
    }
}
```

**Estimated Time:** 1.5 hours

---

### Phase 4: Build System Integration

#### Update CMakeLists.txt

**File:** `iMatrix/CMakeLists.txt` or appropriate build file

**Add new source file:**
```cmake
set(NETWORKING_SOURCES
    IMX_Platform/LINUX_Platform/networking/process_network.c
    IMX_Platform/LINUX_Platform/networking/cellular_man.c
    IMX_Platform/LINUX_Platform/networking/ppp_connection.c  # NEW
    IMX_Platform/LINUX_Platform/networking/network_utils.c
    # ... other sources ...
)
```

**Estimated Time:** 15 minutes

**Total Phase 2-4 Time:** 2.5-3 hours

---

## CLI Commands Integration

### Overview

Add comprehensive CLI commands for PPP diagnostics, status monitoring, and troubleshooting. Follows established CLI patterns from `cli_net_cell.c` and `cli.c`.

### New CLI Commands

#### 1. `ppp` - Main PPP Status Command

**Usage:** `ppp` or `ppp status`

**Output Format:**
```
+=====================================================================================================+
|                                       PPP0 CONNECTION STATUS                                        |
+=====================================================================================================+
| State: CONNECTED         | Device: ppp0 (UP)      | Daemon: RUNNING       | Uptime: 5m 23s        |
+-----------------------------------------------------------------------------------------------------+
| Local IP:    10.183.192.75                        | Remote IP:   10.64.64.64                       |
| Primary DNS: 8.8.8.8                              | Secondary:   8.8.4.4                           |
+-----------------------------------------------------------------------------------------------------+
| Connection Time: 3.2 seconds                      | State Transitions: 8                           |
| Chat Script:     OK                               | LCP Negotiation:   OK                          |
| IPCP Negotiation: OK                              | IP Assignment:     OK                          |
+=====================================================================================================+
```

**Implementation:**

**File:** `iMatrix/cli/cli_ppp.c` (NEW)

```c
/**
 * @file cli_ppp.c
 * @brief CLI commands for PPP connection diagnostics
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>

#include "../imx_platform.h"
#include "interface.h"
#include "cli_ppp.h"
#include "../IMX_Platform/LINUX_Platform/networking/ppp_connection.h"

/**
 * @brief Format uptime duration to human-readable string
 */
static void format_uptime(uint32_t ms, char *buffer, size_t size)
{
    if (ms < 1000) {
        snprintf(buffer, size, "%lu ms", (unsigned long)ms);
    } else if (ms < 60000) {
        snprintf(buffer, size, "%lu s", (unsigned long)(ms / 1000));
    } else if (ms < 3600000) {
        uint32_t minutes = ms / 60000;
        uint32_t seconds = (ms % 60000) / 1000;
        snprintf(buffer, size, "%um %us", minutes, seconds);
    } else {
        uint32_t hours = ms / 3600000;
        uint32_t minutes = (ms % 3600000) / 60000;
        snprintf(buffer, size, "%uh %um", hours, minutes);
    }
}

/**
 * @brief Display PPP connection status
 */
void cli_ppp_status(void)
{
    ppp_connection_status_t status;

    if (ppp_connection_get_status(&status) != IMX_SUCCESS) {
        imx_cli_print("ERROR: Failed to get PPP connection status\r\n");
        return;
    }

    /* Header */
    imx_cli_print("+=====================================================================================================+\r\n");
    imx_cli_print("|                                       PPP0 CONNECTION STATUS                                        |\r\n");
    imx_cli_print("+=====================================================================================================+\r\n");

    /* Main status line */
    char uptime_str[20];
    format_uptime(status.connection_time_ms, uptime_str, sizeof(uptime_str));

    const char *state_str = ppp_state_name(status.state);
    const char *device_str = status.ppp0_device_exists ? "ppp0 (UP)" : "ppp0 (DOWN)";
    const char *daemon_str = status.pppd_running ? "RUNNING" : "STOPPED";

    imx_cli_print("| State: %-20s | Device: %-18s | Daemon: %-13s | Uptime: %-18s |\r\n",
                  state_str, device_str, daemon_str, uptime_str);

    /* IP Configuration */
    if (status.state == PPP_STATE_CONNECTED || status.ppp0_has_ip) {
        imx_cli_print("+-----------------------------------------------------------------------------------------------------+\r\n");
        imx_cli_print("| Local IP:    %-32s | Remote IP:   %-38s |\r\n",
                      status.local_ip, status.remote_ip);
        imx_cli_print("| Primary DNS: %-32s | Secondary:   %-38s |\r\n",
                      status.dns_primary, status.dns_secondary);
    }

    /* Connection Health */
    ppp_health_check_t health;
    if (ppp_connection_check_health(&health) == IMX_SUCCESS) {
        imx_cli_print("+-----------------------------------------------------------------------------------------------------+\r\n");

        char conn_time_str[20];
        format_uptime(status.connection_time_ms, conn_time_str, sizeof(conn_time_str));

        imx_cli_print("| Connection Time: %-28s | State Transitions: %-32u |\r\n",
                      conn_time_str, status.log_lines_parsed);
        imx_cli_print("| Chat Script:     %-28s | LCP Negotiation:   %-32s |\r\n",
                      health.chat_script_ok ? "OK" : "FAILED",
                      health.lcp_negotiated ? "OK" : "FAILED");
        imx_cli_print("| IPCP Negotiation: %-28s | IP Assignment:     %-32s |\r\n",
                      health.ipcp_negotiated ? "OK" : "FAILED",
                      health.ip_assigned ? "OK" : "FAILED");
    }

    /* Error Information */
    if (status.state == PPP_STATE_ERROR) {
        imx_cli_print("+-----------------------------------------------------------------------------------------------------+\r\n");
        imx_cli_print("|                                          ERROR DETAILS                                              |\r\n");
        imx_cli_print("+-----------------------------------------------------------------------------------------------------+\r\n");
        imx_cli_print("| Error Type: %-84s |\r\n", ppp_error_name(status.error_type));
        imx_cli_print("| Message:    %-84s |\r\n", status.last_error);
        imx_cli_print("| Chat Failures: %-5u | Modem Hangups: %-5u | LCP Failures: %-40u |\r\n",
                      status.chat_script_failures, status.modem_hangups, status.lcp_failures);
    }

    imx_cli_print("+=====================================================================================================+\r\n");
}
```

#### 2. `ppp logs` - Display Recent PPPD Logs

**Usage:** `ppp logs [lines]`

**Examples:**
- `ppp logs` - Last 50 lines
- `ppp logs 100` - Last 100 lines

**Output:**
```
PPP0 Connection Log (last 50 lines from /var/log/pppd/current):
========================================
2025-11-16_23:13:18.35310 ATDT*99***1#
2025-11-16_23:13:18.37091 CONNECT
2025-11-16_23:13:18.38299 Script /usr/sbin/chat finished, status = 0x0
2025-11-16_23:13:18.38367 Serial connection established.
2025-11-16_23:13:19.39756 sent [LCP ConfReq id=0x1 <asyncmap 0x0>]
...
========================================
```

**Implementation:**
```c
void cli_ppp_logs(uint16_t arg)
{
    /* Parse argument for number of lines */
    uint32_t lines = 50;  /* Default */
    char *token = strtok(NULL, " ");
    if (token) {
        lines = (uint32_t)atoi(token);
        if (lines == 0 || lines > 500) {
            imx_cli_print("Invalid line count. Use 1-500. Defaulting to 50.\r\n");
            lines = 50;
        }
    }

    char log_buffer[8192];
    imx_result_t result = ppp_connection_parse_log(log_buffer, sizeof(log_buffer), lines);

    if (result != IMX_SUCCESS) {
        imx_cli_print("ERROR: Failed to read /var/log/pppd/current\r\n");
        imx_cli_print("Check that PPPD daemon has been started at least once.\r\n");
        return;
    }

    imx_cli_print("PPP0 Connection Log (last %u lines from /var/log/pppd/current):\r\n", lines);
    imx_cli_print("========================================\r\n");
    imx_cli_print("%s", log_buffer);
    imx_cli_print("========================================\r\n");
}
```

#### 3. `ppp health` - Connection Health Check

**Usage:** `ppp health`

**Output:**
```
PPP0 Connection Health Check
========================================
Overall Health:     HEALTHY
Connection State:   CONNECTED
Time in State:      5m 23s

Connection Progression:
  [✓] Chat Script:       OK (modem responded)
  [✓] Serial Link:       OK (connection established)
  [✓] LCP Negotiation:   OK (link layer ready)
  [✓] IPCP Negotiation:  OK (IP protocol ready)
  [✓] IP Assignment:     OK (10.183.192.75 assigned)
  [✓] IP-up Script:      OK (routing configured)

Error History:
  Chat Script Failures:  0
  Modem Hangups:         0
  LCP Failures:          0

Log Analysis:
  Lines Analyzed:        200
  Last Updated:          1.2 seconds ago
========================================
```

**For Failures:**
```
PPP0 Connection Health Check
========================================
Overall Health:     UNHEALTHY
Connection State:   ERROR
Time in State:      45s

Connection Progression:
  [✓] Chat Script:       OK (modem responded)
  [✓] Serial Link:       OK (connection established)
  [✓] LCP Negotiation:   OK (link layer ready)
  [✗] IPCP Negotiation:  FAILED (timeout)
  [✗] IP Assignment:     FAILED (no IP received)
  [✗] IP-up Script:      NOT RUN

Failure Analysis:
  Error Category: IPCP_TIMEOUT
  Root Cause:     IPCP negotiation failed or timed out

Recommended Actions:
  1. Check APN configuration (may be incorrect)
  2. Verify carrier allows data connection on this account
  3. Check for weak signal (IPCP requires stable connection)
  4. Review /var/log/pppd/current for detailed IPCP messages

Error History:
  Chat Script Failures:  0
  Modem Hangups:         0
  LCP Failures:          0

Log Analysis:
  Lines Analyzed:        200
  Last Updated:          0.8 seconds ago
========================================
```

**Implementation:**
```c
void cli_ppp_health(void)
{
    ppp_connection_status_t status;
    ppp_health_check_t health;

    if (ppp_connection_get_status(&status) != IMX_SUCCESS) {
        imx_cli_print("ERROR: Failed to get PPP connection status\r\n");
        return;
    }

    if (ppp_connection_check_health(&health) != IMX_SUCCESS) {
        imx_cli_print("ERROR: Failed to perform health check\r\n");
        return;
    }

    imx_cli_print("PPP0 Connection Health Check\r\n");
    imx_cli_print("========================================\r\n");

    /* Overall health */
    bool healthy = !health.has_errors &&
                   (status.state == PPP_STATE_CONNECTED || status.pppd_running);
    imx_cli_print("Overall Health:     %s\r\n", healthy ? "HEALTHY" : "UNHEALTHY");
    imx_cli_print("Connection State:   %s\r\n", ppp_state_name(status.state));

    char uptime_str[20];
    format_uptime(status.time_in_current_state, uptime_str, sizeof(uptime_str));
    imx_cli_print("Time in State:      %s\r\n\r\n", uptime_str);

    /* Connection progression */
    imx_cli_print("Connection Progression:\r\n");
    imx_cli_print("  [%s] Chat Script:       %s\r\n",
                  health.chat_script_ok ? "✓" : "✗",
                  health.chat_script_ok ? "OK (modem responded)" : "FAILED");
    imx_cli_print("  [%s] Serial Link:       %s\r\n",
                  health.serial_established ? "✓" : "✗",
                  health.serial_established ? "OK (connection established)" : "FAILED");
    imx_cli_print("  [%s] LCP Negotiation:   %s\r\n",
                  health.lcp_negotiated ? "✓" : "✗",
                  health.lcp_negotiated ? "OK (link layer ready)" : "FAILED");
    imx_cli_print("  [%s] IPCP Negotiation:  %s\r\n",
                  health.ipcp_negotiated ? "✓" : "✗",
                  health.ipcp_negotiated ? "OK (IP protocol ready)" : "FAILED");
    imx_cli_print("  [%s] IP Assignment:     %s\r\n",
                  health.ip_assigned ? "✓" : "✗",
                  health.ip_assigned ? (status.local_ip[0] ? status.local_ip : "OK") : "FAILED");
    imx_cli_print("  [%s] IP-up Script:      %s\r\n\r\n",
                  health.ip_up_script_ok ? "✓" : "✗",
                  health.ip_up_script_ok ? "OK (routing configured)" : "NOT RUN");

    /* Failure analysis if unhealthy */
    if (health.has_errors) {
        imx_cli_print("Failure Analysis:\r\n");
        imx_cli_print("  Error Category: %s\r\n", ppp_error_name(health.error_category));
        imx_cli_print("  Root Cause:     %s\r\n\r\n", health.failure_reason);

        /* Recommended actions based on error type */
        imx_cli_print("Recommended Actions:\r\n");
        display_troubleshooting_steps(health.error_category);
        imx_cli_print("\r\n");
    }

    /* Error history */
    imx_cli_print("Error History:\r\n");
    imx_cli_print("  Chat Script Failures:  %u\r\n", status.chat_script_failures);
    imx_cli_print("  Modem Hangups:         %u\r\n", status.modem_hangups);
    imx_cli_print("  LCP Failures:          %u\r\n\r\n", status.lcp_failures);

    /* Analysis metadata */
    char analysis_age[20];
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    uint32_t age_ms = imx_time_difference(current_time, health.analysis_time);
    format_uptime(age_ms, analysis_age, sizeof(analysis_age));

    imx_cli_print("Log Analysis:\r\n");
    imx_cli_print("  Lines Analyzed:        %u\r\n", health.log_lines_analyzed);
    imx_cli_print("  Last Updated:          %s ago\r\n", analysis_age);
    imx_cli_print("========================================\r\n");
}
```

#### 4. `ppp restart` - Restart PPP Connection

**Usage:** `ppp restart`

**Output:**
```
Restarting PPP0 connection...
Stopping PPPD daemon... OK
Starting PPPD daemon... OK
Monitor connection with: ppp status
```

**Implementation:**
```c
void cli_ppp_restart(void)
{
    imx_cli_print("Restarting PPP0 connection...\r\n");

    /* Stop */
    imx_cli_print("Stopping PPPD daemon... ");
    if (ppp_connection_stop(false) == IMX_SUCCESS) {
        imx_cli_print("OK\r\n");
    } else {
        imx_cli_print("FAILED\r\n");
        imx_cli_print("Attempting force kill...\r\n");
        system("killall -9 pppd 2>/dev/null");
        usleep(1000000);
    }

    /* Wait between stop and start */
    imx_cli_print("Waiting 2 seconds...\r\n");
    sleep(2);

    /* Start */
    imx_cli_print("Starting PPPD daemon... ");
    if (ppp_connection_start() == IMX_SUCCESS) {
        imx_cli_print("OK\r\n");
        imx_cli_print("Monitor connection with: ppp status\r\n");
        imx_cli_print("Expected connection time: 3-5 seconds\r\n");
    } else {
        imx_cli_print("FAILED\r\n");
        imx_cli_print("Check /var/log/pppd/current for errors\r\n");
    }
}
```

#### 5. `ppp start` / `ppp stop` - Manual Control

**Usage:**
- `ppp start` - Manually start PPP connection
- `ppp stop` - Manually stop PPP connection

**Implementation:**
```c
void cli_ppp_start(void)
{
    imx_cli_print("Starting PPP0 connection manually...\r\n");

    if (ppp_connection_start() == IMX_SUCCESS) {
        imx_cli_print("PPPD daemon started\r\n");
        imx_cli_print("Use 'ppp status' to monitor connection progress\r\n");
    } else {
        imx_cli_print("Failed to start PPPD daemon\r\n");
        imx_cli_print("Check prerequisite errors above\r\n");
    }
}

void cli_ppp_stop(void)
{
    imx_cli_print("Stopping PPP0 connection...\r\n");

    if (ppp_connection_stop(false) == IMX_SUCCESS) {
        imx_cli_print("PPPD daemon stopped\r\n");
    } else {
        imx_cli_print("Failed to stop PPPD daemon\r\n");
    }
}
```

#### 6. Main Command Dispatcher

**Function:** `cli_ppp()`

**File:** `iMatrix/cli/cli_ppp.c`

```c
/**
 * @brief Main PPP CLI command dispatcher
 * @param arg Unused
 */
void cli_ppp(uint16_t arg)
{
    UNUSED_PARAMETER(arg);

    char *subcommand = strtok(NULL, " ");

    if (subcommand == NULL || strcmp(subcommand, "status") == 0) {
        cli_ppp_status();
    }
    else if (strcmp(subcommand, "logs") == 0) {
        cli_ppp_logs(0);
    }
    else if (strcmp(subcommand, "health") == 0) {
        cli_ppp_health();
    }
    else if (strcmp(subcommand, "start") == 0) {
        cli_ppp_start();
    }
    else if (strcmp(subcommand, "stop") == 0) {
        cli_ppp_stop();
    }
    else if (strcmp(subcommand, "restart") == 0) {
        cli_ppp_restart();
    }
    else {
        imx_cli_print("Unknown subcommand: %s\r\n", subcommand);
        imx_cli_print("Usage: ppp [status|logs|health|start|stop|restart]\r\n");
    }
}
```

#### 7. Register Commands in cli.c

**File:** `iMatrix/cli/cli.c`

**Add to command table (alphabetically):**
```c
#ifdef CELLULAR_PLATFORM
    {"ppp", &cli_ppp, 0, "PPP connection - 'ppp [status|logs|health|start|stop|restart]' - Cellular PPP0 diagnostics and control"},
#endif // CELLULAR_PLATFORM
```

**Estimated Time for All CLI Commands:** 3-4 hours

---

## Log Parsing Strategy

### Log Pattern Reference (from Working Example)

#### Successful Connection Sequence

```
Pattern                              | State              | Time Offset | Notes
------------------------------------|--------------------+-------------+------------------------
"Start Pppd runit service"          | STARTING           | 0ms         | Script begins
"ATQ0" / "ATZ"                      | CHAT_RUNNING       | +10ms       | Chat script init
"ATDT*99***1#"                      | CHAT_RUNNING       | +350ms      | Dialing command
"CONNECT"                           | CHAT_CONNECTED     | +370ms      | Modem responded
"Serial connection established"     | CHAT_CONNECTED     | +380ms      | Serial link up
"sent [LCP ConfReq"                 | LCP_NEGOTIATION    | +1400ms     | LCP handshake
"rcvd [LCP ConfAck"                 | LCP_ESTABLISHED    | +1430ms     | LCP complete
"sent [IPCP ConfReq"                | IPCP_NEGOTIATION   | +1450ms     | IP negotiation
"rcvd [IPCP ConfAck"                | IPCP_NEGOTIATION   | +3240ms     | IP agreed
"local  IP address 10.183.192.75"   | CONNECTED          | +3460ms     | IP assigned
"ip-up finished (pid X), status=0x0"| CONNECTED          | +3820ms     | Setup complete
```

**Total Connection Time:** ~3.8 seconds

#### Error Patterns

```
Error Message                | Error Type          | Cause
----------------------------|---------------------|--------------------------------
"Connect script failed"     | CHAT_SCRIPT         | Modem not responding to AT commands
"No carrier"                | NO_CARRIER          | No cellular signal
"Modem hangup"              | MODEM_HANGUP        | Connection dropped mid-session
"LCP terminated"            | LCP_TIMEOUT         | Link negotiation failed
"LCP: timeout sending"      | LCP_TIMEOUT         | No response from network
"IPCP: timeout sending"     | IPCP_TIMEOUT        | IP negotiation timeout
"peer refused to auth"      | AUTH_FAILED         | Network rejected authentication
"Serial link disconnected"  | MODEM_HANGUP        | Hardware disconnection
```

### Parsing Implementation

#### State Detection Algorithm

```c
/**
 * @brief Parse connection state from log patterns
 *
 * Searches log in reverse chronological order (most recent events first)
 * to determine current connection state.
 *
 * @param log Log buffer to search
 * @return Detected connection state
 */
static ppp_state_t parse_state_from_log(const char *log)
{
    /* Search for state indicators in order of completion */

    /* 1. Check if fully connected (final state) */
    bool has_ip = (strstr(log, "local  IP address") != NULL);
    bool ip_up_done = (strstr(log, "ip-up finished") != NULL);

    if (has_ip && ip_up_done) {
        return PPP_STATE_CONNECTED;
    }

    /* 2. Check if IPCP negotiation in progress */
    bool ipcp_started = (strstr(log, "IPCP ConfReq") != NULL);
    bool ipcp_complete = (strstr(log, "IPCP ConfAck") != NULL);

    if (ipcp_started) {
        if (has_ip) {
            return PPP_STATE_CONNECTED;  /* Has IP but ip-up still running */
        } else if (ipcp_complete) {
            return PPP_STATE_IPCP_NEGOTIATION;  /* Negotiating IP value */
        } else {
            return PPP_STATE_IPCP_NEGOTIATION;  /* Starting IPCP */
        }
    }

    /* 3. Check if LCP negotiation in progress or complete */
    bool lcp_started = (strstr(log, "LCP ConfReq") != NULL);
    bool lcp_complete = (strstr(log, "LCP ConfAck") != NULL);

    if (lcp_started) {
        if (lcp_complete && !ipcp_started) {
            return PPP_STATE_LCP_ESTABLISHED;  /* LCP done, waiting for IPCP */
        } else if (lcp_started) {
            return PPP_STATE_LCP_NEGOTIATION;  /* LCP handshake */
        }
    }

    /* 4. Check if chat script connected */
    bool modem_connect = (strstr(log, "CONNECT") != NULL);
    bool serial_established = (strstr(log, "Serial connection established") != NULL);

    if (modem_connect || serial_established) {
        if (!lcp_started) {
            return PPP_STATE_CHAT_CONNECTED;  /* Connected but no LCP yet */
        }
    }

    /* 5. Check if chat script running */
    bool chat_running = (strstr(log, "ATDT") != NULL) ||
                        (strstr(log, "chat -V -f") != NULL);

    if (chat_running && !modem_connect) {
        return PPP_STATE_CHAT_RUNNING;  /* Sending AT commands */
    }

    /* 6. Check if daemon just starting */
    bool daemon_start = (strstr(log, "Start Pppd") != NULL) ||
                        (strstr(log, "starting") != NULL);

    if (daemon_start && !chat_running) {
        return PPP_STATE_STARTING;  /* Initializing */
    }

    /* 7. Check for error conditions */
    if (strstr(log, "Connect script failed") ||
        strstr(log, "Modem hangup") ||
        strstr(log, "LCP terminated") ||
        strstr(log, "No carrier")) {
        return PPP_STATE_ERROR;
    }

    /* 8. Check if disconnecting */
    if (strstr(log, "Terminating") || strstr(log, "ip-down started")) {
        return PPP_STATE_DISCONNECTING;
    }

    /* Default: Daemon running but state unclear */
    return PPP_STATE_STARTING;
}
```

#### IP/DNS Extraction

```c
/**
 * @brief Parse IP configuration from log
 */
static void parse_ip_configuration_from_log(const char *log, ppp_connection_status_t *status)
{
    char line[512];
    const char *ptr = log;

    /* Search for IP configuration lines */
    while ((ptr = strchr(ptr, '\n')) != NULL) {
        ptr++;  /* Skip newline */

        const char *next_line = strchr(ptr, '\n');
        if (!next_line) break;

        size_t line_len = next_line - ptr;
        if (line_len >= sizeof(line)) line_len = sizeof(line) - 1;

        strncpy(line, ptr, line_len);
        line[line_len] = '\0';

        /* Parse "local  IP address X.X.X.X" */
        if (strstr(line, "local  IP address")) {
            sscanf(line, "%*[^0-9]%15[0-9.]", status->local_ip);
        }

        /* Parse "remote IP address X.X.X.X" */
        else if (strstr(line, "remote IP address")) {
            sscanf(line, "%*[^0-9]%15[0-9.]", status->remote_ip);
        }

        /* Parse "primary   DNS address X.X.X.X" */
        else if (strstr(line, "primary   DNS address")) {
            sscanf(line, "%*[^0-9]%15[0-9.]", status->dns_primary);
        }

        /* Parse "secondary DNS address X.X.X.X" */
        else if (strstr(line, "secondary DNS address")) {
            sscanf(line, "%*[^0-9]%15[0-9.]", status->dns_secondary);
        }
    }
}
```

---

## Testing Strategy

### Unit Tests

#### Test 1: Prerequisite Checking

**Setup:**
- System with `/etc/start_pppd.sh` missing
- System with script present but not executable
- System with script present and executable

**Expected Results:**
- Missing script: `ppp_connection_init()` warns but returns SUCCESS
- Not executable: Warns, returns SUCCESS
- Present and executable: Logs success, returns SUCCESS

**Command:** Build and run on test system, check initialization logs

#### Test 2: Log State Parsing

**Setup:** Create test log buffers with patterns from working log

**Test Cases:**
```c
/* Test CONNECTED state detection */
char test_log_connected[] =
    "CONNECT\n"
    "Serial connection established\n"
    "LCP ConfAck\n"
    "IPCP ConfAck\n"
    "local  IP address 10.183.192.75\n"
    "ip-up finished (pid 1234), status = 0x0\n";

assert(parse_state_from_log(test_log_connected) == PPP_STATE_CONNECTED);

/* Test CHAT_RUNNING state */
char test_log_chat[] =
    "Start Pppd\n"
    "ATDT*99***1#\n";

assert(parse_state_from_log(test_log_chat) == PPP_STATE_CHAT_RUNNING);

/* Test ERROR state */
char test_log_error[] =
    "ATDT*99***1#\n"
    "Connect script failed\n";

assert(parse_state_from_log(test_log_error) == PPP_STATE_ERROR);
```

#### Test 3: IP Extraction

**Setup:** Test log with IP configuration

**Expected:**
- Local IP: `10.183.192.75`
- Remote IP: `10.64.64.64`
- DNS Primary: `8.8.8.8`
- DNS Secondary: `8.8.4.4`

### Integration Tests

#### Test 4: Full Connection Flow

**Procedure:**
1. Ensure cellular modem ready (`cell` command shows connected)
2. Start PPP: Call `start_pppd()` or `ppp start`
3. Monitor state transitions every 500ms
4. Verify progression: STARTING → CHAT → LCP → IPCP → CONNECTED
5. Check timing: Should complete in 3-10 seconds
6. Verify `ppp status` shows correct IP configuration
7. Verify `ppp health` shows all checkpoints passed
8. Test `ppp logs` shows complete connection sequence

**Success Criteria:**
- Connection completes within 10 seconds
- All states detected correctly
- IP/DNS extracted accurately
- Logs show detailed progression

#### Test 5: Connection Failure Scenarios

**Test 5a: Modem Not Responding**

**Setup:**
- Disable modem or disconnect /dev/ttyACM0
- Attempt connection

**Expected:**
- State: `PPP_STATE_ERROR`
- Error Type: `PPP_ERROR_CHAT_SCRIPT`
- Health check: chat_script_ok = false
- Log shows: "Connect script failed"
- Recommended actions displayed

**Test 5b: Weak Signal / Timeout**

**Setup:**
- Move to area with weak cellular signal
- Attempt connection

**Expected:**
- States progress slowly: CHAT (5-10s), LCP (10-15s)
- May timeout in IPCP if signal too weak
- Health check identifies which stage timed out
- Logs show multiple retry attempts

**Test 5c: Incorrect APN**

**Setup:**
- Configure wrong APN via AT command
- Attempt connection

**Expected:**
- Chat, LCP succeed
- IPCP negotiation fails
- Error Type: `PPP_ERROR_IPCP_TIMEOUT`
- Recommended action: Check APN configuration

#### Test 6: CLI Commands

**Test Each Command:**
- `ppp` → Shows status table
- `ppp status` → Same as above
- `ppp logs` → Shows last 50 lines
- `ppp logs 100` → Shows last 100 lines
- `ppp health` → Shows health check with checkmarks
- `ppp start` → Starts daemon, shows progress
- `ppp stop` → Stops daemon cleanly
- `ppp restart` → Stops then starts with delay

**Success Criteria:**
- All commands execute without crashes
- Output formatted correctly (103-char wide tables)
- Information accurate and up-to-date
- Help text clear and actionable

### Long-Run Tests

#### Test 7: 24-Hour Stability

**Setup:**
- System with cellular connection
- Enable full PPP debugging: `debug 0x00080000`
- Let run for 24 hours

**Monitor:**
- Connection drops and recovery
- Log cache performance (no memory leaks)
- State detection accuracy over time
- Multiple connection/disconnection cycles

**Success Criteria:**
- No memory leaks
- Accurate state detection throughout
- Clean error recovery
- Log cache invalidates properly

---

## Future Enhancements

### Phase 1: Advanced CLI Commands (Priority 1)

#### 1. `ppp trace` - Real-time Connection Tracing

**Description:** Live monitoring of PPP connection with auto-updating status

**Usage:** `ppp trace`

**Output:**
```
PPP0 Connection Trace (updating every 1 second, Ctrl+C to exit)
========================================
[00:00] State: STARTING           | Daemon: RUNNING  | Device: DOWN
[00:01] State: CHAT_RUNNING       | Daemon: RUNNING  | Device: DOWN
        AT> ATDT*99***1#
[00:02] State: CHAT_CONNECTED     | Daemon: RUNNING  | Device: DOWN
        Modem: CONNECT received
[00:03] State: LCP_NEGOTIATION    | Daemon: RUNNING  | Device: UP
        Protocol: LCP handshake in progress
[00:04] State: IPCP_NEGOTIATION   | Daemon: RUNNING  | Device: UP
        Protocol: Requesting IP address
[00:05] State: CONNECTED          | Daemon: RUNNING  | Device: UP (10.183.192.75)
        SUCCESS: Connection established in 5.2 seconds
========================================
```

**Implementation:**
- Loop with 1-second sleep
- Call `ppp_connection_get_status()` each iteration
- Detect state changes and log
- Parse recent log lines for relevant events
- Allow Ctrl+C to exit

**Use Case:** Interactive debugging of connection issues

#### 2. `ppp stats` - Connection Statistics

**Description:** Historical statistics about PPP connections

**Output:**
```
PPP0 Connection Statistics
========================================
Lifetime Statistics:
  Successful Connections: 42
  Failed Connections:     3
  Total Disconnects:      45
  Success Rate:           93.3%

Connection Times:
  Average:    4.2 seconds
  Fastest:    2.8 seconds
  Slowest:    8.7 seconds
  Last:       3.6 seconds

Error Breakdown:
  Chat Script Failures:   1 (33%)
  LCP Timeouts:           1 (33%)
  IPCP Timeouts:          1 (33%)
  Modem Hangups:          0 (0%)

Current Session:
  Uptime:         2h 15m 43s
  Disconnects:    2
  Last Connect:   2h 10m ago
========================================
```

**Implementation:**
- Add statistics structure to ppp_connection.c (global)
- Update on each connect/disconnect event
- Persist to storage for power-cycle retention
- CLI command reads and formats

#### 3. `ppp diag` - Automated Diagnostics

**Description:** Run comprehensive diagnostic sequence

**Output:**
```
PPP0 Automated Diagnostics
========================================
Checking Prerequisites...
  [✓] /etc/start_pppd.sh      EXISTS (executable)
  [✓] /var/log/pppd/          WRITABLE
  [✓] /dev/ttyACM0            EXISTS
  [✓] /etc/chatscripts/       CONFIGURED

Checking Modem Status...
  [✓] Modem Power:            ON (GPIO 89 = 1)
  [✓] ttyACM Devices:         5 ports detected
  [✓] SIM Card:               READY
  [✓] Carrier:                AT&T (310410)
  [✓] Signal Strength:        -67 dBm (Good)
  [✓] Registration:           Registered, home network

Checking PPPD Daemon...
  [✓] Process Status:         RUNNING (PID 2541)
  [✓] Connection State:       CONNECTED
  [✓] Device Status:          ppp0 UP
  [✓] IP Address:             10.183.192.75
  [✓] Uptime:                 10m 32s

Checking Connection Health...
  [✓] Chat Script:            OK
  [✓] LCP Negotiation:        OK
  [✓] IPCP Negotiation:       OK
  [✓] IP Assignment:          OK
  [✓] Routing:                OK

Overall Status: HEALTHY ✓
========================================
```

**Implementation:**
- Sequence of checks covering entire stack
- From hardware (GPIO, modem) to application (IP routing)
- Each check returns pass/fail with details
- Actionable recommendations for failures

#### 4. `ppp reset` - Full Reset Sequence

**Description:** Complete reset of cellular and PPP

**Usage:** `ppp reset`

**Procedure:**
1. Stop PPPD daemon
2. Power cycle cellular modem (GPIO 89)
3. Wait for modem re-initialization
4. Restart cellular_man state machine
5. Restart PPPD when modem ready

**Output:**
```
PPP0 Full Reset Sequence
========================================
Step 1: Stopping PPPD daemon...         OK
Step 2: Powering down modem (GPIO 89)... OK
Step 3: Waiting 5 seconds...            OK
Step 4: Powering up modem...            OK
Step 5: Waiting for modem ready...      OK (8 seconds)
Step 6: Modem initialized               OK (AT commands responding)
Step 7: Starting PPPD daemon...         OK
Step 8: Monitoring connection...        IN PROGRESS

Use 'ppp trace' to monitor connection progress
========================================
```

### Phase 2: Statistics and Analytics (Priority 2)

#### 5. Connection Quality Metrics

**Features:**
- Track connection establishment times
- Identify patterns in failures (time of day, carrier, signal strength)
- Detect degradation over time
- Alert on repeated failures

**Implementation:**
- Persistent statistics in flash storage
- Export via CLI or upload to iMatrix cloud
- Graphs/trends if UI available

#### 6. Predictive Diagnostics

**Features:**
- Detect early warning signs (slow LCP/IPCP)
- Proactive modem reset before failure
- Learn carrier/location patterns
- Optimize APN selection

#### 7. Remote Diagnostics API

**Features:**
- Export status via MQTT/CoAP
- Allow cloud-based troubleshooting
- Remote command execution
- Log upload to iMatrix platform

### Phase 3: Advanced Error Recovery (Priority 3)

#### 8. Intelligent Retry Logic

**Features:**
- Different retry strategies per error type
- Exponential backoff for persistent failures
- Modem reset after N chat failures
- APN rotation if IPCP consistently fails

#### 9. Multi-APN Support

**Features:**
- Configure multiple APNs in priority order
- Auto-fallback if primary APN fails
- Per-carrier APN preferences
- Dynamic APN discovery from carrier

#### 10. Connection Optimization

**Features:**
- Measure connection latency, throughput
- Select fastest carrier when multiple available
- Cache successful APN/carrier combinations
- Optimize based on time-of-day patterns

---

## References

### Primary Documentation

1. **QConnect Developer Guide (Document #1180-3007, Revision C)**
   - Location: `docs/1180-3007_C_QConnect__Developer_Guide.pdf`
   - Page 26: "Establishing a Cell Connection - PPPD Daemon" (recommended approach)
   - Page 27: "Linux Utility" (`pon`/`poff` approach - currently used, problematic)
   - Page 28: "Verify the Cell Connection" and troubleshooting steps
   - Page 24-25: Cellular module AT commands and port usage

2. **Network Stability Handoff Document**
   - Location: `docs/network_stability_handoff.md`
   - Section: "Issue #2: PPP0 Connection Failures" (lines 108-176)
   - Analysis of 128+ connect script failures in net3.txt
   - Root cause analysis and diagnostic recommendations

3. **Network Manager Architecture**
   - Location: `docs/Network_Manager_Architecture.md`
   - Multi-interface failover design
   - PPP0 integration with eth0/wlan0
   - State machine documentation

4. **CLI and Debug System Complete Guide**
   - Location: `docs/CLI_and_Debug_System_Complete_Guide.md`
   - CLI command structure and patterns
   - Debug flag usage (`DEBUGS_FOR_PPP0_NETWORKING = 0x00080000`)
   - Logging macros and conventions

5. **Debug Network Issue Plan**
   - Location: `docs/debug_network_issue_plan_2.md`
   - Historical network debugging approach
   - Lessons learned from network troubleshooting
   - Diagnostic methodology

### Source Code References

6. **cellular_man.c**
   - Location: `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`
   - Lines 1763-1850: Current `start_pppd()` / `stop_pppd()` implementation
   - Lines 1863-2750: Cellular state machine and modem control
   - Line 2064: `cellular_now_ready` flag set when modem registered

7. **process_network.c**
   - Location: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
   - Lines 4304-4310: Cellular ready detection
   - Lines 4514-4544: PPP activation logic
   - Lines 4646-4676: PPP device monitoring (to be enhanced)

8. **cli_net_cell.c**
   - Location: `iMatrix/cli/cli_net_cell.c`
   - Example CLI implementation for cellular status
   - Table formatting patterns (103-char width)
   - Command structure reference

### Log Files

9. **Working PPP Connection Log**
   - Example provided by user showing successful connection
   - From: `/var/log/pppd/current`
   - Shows: Complete CHAT → LCP → IPCP → CONNECTED sequence in 3.8 seconds
   - Reference for state detection patterns

10. **Failed Connection Logs**
    - Location: `logs/net3.txt` (287KB)
    - 128+ "Connect script failed" errors
    - Evidence of PPP configuration mismatch
    - Used for error pattern detection

### External References

11. **PPPD Manual**
    - Command: `man pppd` on target system
    - Documents pppd options, connect scripts, ip-up/ip-down
    - Log format specifications

12. **Chat Script Manual**
    - Command: `man chat` on target system
    - AT command sequences
    - Error handling and timeout behavior

### Related Fixes

13. **Network Stability Fixes**
    - This document: Section on enhanced PPP logging (Issue #2)
    - State machine deadlock fix (Issue #1)
    - Interface selection improvements (Issue #4)
    - WiFi grace period (Issue #3)

---

## Implementation Timeline

### Week 1: Core Development

**Day 1-2:** Phase 1 - Create ppp_connection.c/h module
- Data structures
- Daemon control functions
- Basic log parsing

**Day 3:** Phase 2 - Update cellular_man.c
- Deprecate old functions
- Add wrappers
- Test compatibility

**Day 4:** Phase 3 - Enhance process_network.c
- Add detailed monitoring
- Update CMakeLists.txt
- Build verification

**Day 5:** Initial testing and fixes

### Week 2: CLI and Testing

**Day 6-7:** CLI Commands
- Create cli_ppp.c
- Implement all commands
- Register in cli.c
- Format and test output

**Day 8-9:** Integration testing
- Full connection flow
- Failure scenarios
- Long-run stability

**Day 10:** Documentation and code review

---

## Migration Path

### For Existing Systems

**Option 1: Automatic Detection (Recommended)**

Code detects which approach to use:
```c
imx_result_t ppp_connection_start(void)
{
    /* Try new approach first */
    if (access("/etc/start_pppd.sh", X_OK) == 0) {
        return start_via_daemon();  /* PPPD Daemon approach */
    }

    /* Fallback to old approach */
    if (access("/etc/ppp/peers/provider", R_OK) == 0 ||
        access("/etc/ppp/peers/gprs", R_OK) == 0) {
        return start_via_pon();  /* Linux utility approach */
    }

    /* Neither available */
    log_error("No PPP configuration found (need start_pppd.sh OR /etc/ppp/peers/)");
    return IMX_ERROR;
}
```

**Option 2: Configuration Flag**

Add to device configuration:
```c
typedef enum {
    PPP_METHOD_AUTO,        /* Auto-detect (try daemon first, fall back to pon) */
    PPP_METHOD_DAEMON,      /* Force /etc/start_pppd.sh */
    PPP_METHOD_LINUX_UTIL   /* Force pon/poff */
} ppp_start_method_t;
```

---

## Appendix A: Code Snippets

### Complete ppp_connection.h (Full Header)

*(See Detailed Design section - included above)*

### Example Health Check Output Formatting

```c
void display_troubleshooting_steps(ppp_error_t error)
{
    switch (error) {
    case PPP_ERROR_CHAT_SCRIPT:
        imx_cli_print("  1. Check modem device: ls -l /dev/ttyACM*\r\n");
        imx_cli_print("  2. Test AT commands: echo -e 'at\\r' | microcom -t 2000 /dev/ttyACM2\r\n");
        imx_cli_print("  3. Verify SIM ready: echo -e 'at+cpin?\\r' | microcom -t 2000 /dev/ttyACM2\r\n");
        imx_cli_print("  4. Check signal strength: echo -e 'at+csq\\r' | microcom -t 2000 /dev/ttyACM2\r\n");
        break;

    case PPP_ERROR_NO_CARRIER:
        imx_cli_print("  1. Check signal strength: echo -e 'at+csq\\r' | microcom -t 2000 /dev/ttyACM2\r\n");
        imx_cli_print("     (Values: 0-31, >10 = usable, >20 = good)\r\n");
        imx_cli_print("  2. Verify registration: echo -e 'at+creg?\\r' | microcom -t 2000 /dev/ttyACM2\r\n");
        imx_cli_print("     (Status: 1=home, 5=roaming, 0/2=searching)\r\n");
        imx_cli_print("  3. Check antenna connection (FAKRA connector)\r\n");
        break;

    case PPP_ERROR_LCP_TIMEOUT:
        imx_cli_print("  1. Verify network registration complete\r\n");
        imx_cli_print("  2. Check carrier allows data connection\r\n");
        imx_cli_print("  3. Try different carrier if multiple available\r\n");
        imx_cli_print("  4. Verify SIM card is activated for data\r\n");
        break;

    case PPP_ERROR_IPCP_TIMEOUT:
        imx_cli_print("  1. Verify APN: echo -e 'at+cgdcont?\\r' | microcom -t 2000 /dev/ttyACM2\r\n");
        imx_cli_print("  2. Check APN configuration for your carrier\r\n");
        imx_cli_print("  3. Some carriers require specific APN settings\r\n");
        imx_cli_print("  4. Verify SIM account has data enabled\r\n");
        break;

    case PPP_ERROR_MODEM_HANGUP:
        imx_cli_print("  1. Check signal stability (may be moving in/out of coverage)\r\n");
        imx_cli_print("  2. Verify antenna connection secure\r\n");
        imx_cli_print("  3. Check for carrier network issues\r\n");
        break;

    case PPP_ERROR_AUTH_FAILED:
        imx_cli_print("  1. Verify APN username/password if required\r\n");
        imx_cli_print("  2. Some carriers don't require auth (leave blank)\r\n");
        imx_cli_print("  3. Check carrier-specific authentication requirements\r\n");
        break;

    default:
        imx_cli_print("  1. Review /var/log/pppd/current for detailed error messages\r\n");
        imx_cli_print("  2. Check system logs: tail -f /var/log/messages | grep ppp\r\n");
        break;
    }
}
```

---

## Appendix B: Testing Checklist

### Pre-Integration Testing

- [ ] ppp_connection.c compiles without warnings
- [ ] All functions have Doxygen comments
- [ ] Unit tests for log parsing pass
- [ ] Unit tests for IP extraction pass
- [ ] State detection algorithm validated

### Integration Testing

- [ ] Cellular modem initializes correctly
- [ ] cellular_now_ready flag triggers PPP start
- [ ] PPPD daemon starts via /etc/start_pppd.sh
- [ ] State transitions logged correctly
- [ ] Connection completes in 3-10 seconds
- [ ] IP address extracted and displayed
- [ ] ppp0 marked active in network manager
- [ ] Failover to ppp0 works from eth0/wlan0
- [ ] Failback from ppp0 to wlan0 works

### Error Scenario Testing

- [ ] Missing /etc/start_pppd.sh handled gracefully
- [ ] Modem not responding detected and logged
- [ ] Chat script failure diagnosed correctly
- [ ] LCP timeout identified with diagnostics
- [ ] IPCP timeout shows APN troubleshooting
- [ ] Modem hangup detected and connection retried
- [ ] 30-second timeout triggers with health check

### CLI Command Testing

- [ ] `ppp` displays status table correctly
- [ ] `ppp logs` shows recent log lines
- [ ] `ppp logs 100` respects line count argument
- [ ] `ppp health` displays health check accurately
- [ ] `ppp start` manually starts connection
- [ ] `ppp stop` cleanly stops daemon
- [ ] `ppp restart` performs stop-wait-start sequence
- [ ] All commands handle errors gracefully
- [ ] Table formatting correct (103-char width)

### Long-Run Testing

- [ ] 24-hour run with no crashes
- [ ] Log cache doesn't leak memory
- [ ] Multiple connect/disconnect cycles work
- [ ] State detection accurate over time
- [ ] Statistics tracked correctly
- [ ] No mutex deadlocks with PPP operations

### Diagnostic Tools Verification

- [ ] `debug 0x00080000` enables PPP logging
- [ ] `mutex verbose` shows no PPP-related deadlocks
- [ ] `loopstatus` shows main loop not blocked by PPP
- [ ] `threads -v` shows no hung PPP-related threads
- [ ] `net` command shows PPP status correctly
- [ ] `cell` command shows modem status

---

## Appendix C: Deployment Notes

### System Requirements

**Required Files on Target System:**

1. `/etc/start_pppd.sh` - PPPD startup script (executable)
2. `/etc/chatscripts/quake-gemalto` - Chat script with AT commands
3. `/var/log/pppd/` - Log directory (writable)
4. `/dev/ttyACM0` - Cellular modem device (appears after GPIO 89 enabled)
5. `/etc/ppp/ip-up` - IP up script (sets routes, DNS)
6. `/etc/ppp/ip-down` - IP down script (cleanup)

**Optional Files:**

- `/etc/ppp/options` - PPPD global options
- `/etc/ppp/pap-secrets` - PAP authentication (if required by carrier)
- `/etc/ppp/chap-secrets` - CHAP authentication (if required by carrier)

### Deployment Checklist

- [ ] All required files present
- [ ] Scripts have execute permissions
- [ ] Log directory writable
- [ ] Modem device accessible
- [ ] Cellular modem powered and initialized
- [ ] SIM card inserted and activated
- [ ] APN configured correctly for carrier
- [ ] Test connection manually before code integration

---

## Conclusion

This comprehensive refactoring transforms PPP connection management from a black-box "wait and hope" approach to a fully visible, diagnosable, and controllable system. The key improvements are:

1. **Visibility:** Real-time state progression (CHAT → LCP → IPCP → CONNECTED)
2. **Diagnostics:** Detailed health checks identifying exact failure points
3. **Error Reporting:** Actionable error messages with troubleshooting steps
4. **CLI Integration:** User-accessible commands for status, logs, and control
5. **Maintainability:** Modular design with clear separation of concerns
6. **Reliability:** Robust error handling and recovery mechanisms

**Success Metric:** Reduce PPP connection debugging time from hours to minutes through comprehensive logging and diagnostics.

**Next Steps:** Proceed with Phase 1 implementation (create ppp_connection module) or request clarification on any aspect of the plan.

---

**Document Version:** 2.0
**Author:** Claude Code
**Review Status:** Ready for Implementation
**Estimated Total Effort:** 12-15 hours (development) + 4-6 hours (testing)
