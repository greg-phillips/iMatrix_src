# iMatrix Network Manager Architecture

## Document Overview

This document provides comprehensive technical details on how the iMatrix Network Manager (`process_network.c`) handles dynamic interface failover, priority-based interface selection, blacklisting, cooldown periods, and cellular connectivity management.

**Primary Source Files:**
- `IMX_Platform/LINUX_Platform/networking/process_network.c` (7663 lines)
- `IMX_Platform/LINUX_Platform/networking/cellular_man.c` (5952 lines)
- `IMX_Platform/LINUX_Platform/networking/cellular_blacklist.c`
- `IMX_Platform/LINUX_Platform/networking/wpa_blacklist.c`
- `IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`
- `IMX_Platform/LINUX_Platform/networking/network_timing_config.c`
- `IMX_Platform/LINUX_Platform/networking/network_timing_config.h`

---

## 1. System Overview

### 1.1 Core Purpose

The Network Manager implements **dynamic interface failover** with automatic selection among three primary network interfaces:

1. **eth0** - Ethernet (highest priority)
2. **wlan0** - WiFi (medium priority)
3. **ppp0** - Cellular via PPP daemon (lowest priority)

### 1.2 Key Design Principles

- **Priority-Based Selection**: Strict priority order with quality thresholds
- **Active Testing**: Periodic ping-based connectivity verification to `coap.imatrixsys.com`
- **Automatic Failover**: Seamless switching when current interface degrades
- **Interface Recovery**: Cooldown periods and opportunistic testing
- **DHCP Server Exclusion**: Interfaces in DHCP server mode are excluded from Internet routing
- **Blacklisting**: Problematic WiFi access points and cellular carriers are temporarily blacklisted

---

## 2. State Machine Architecture

### 2.1 Network Manager States

The network manager operates through a well-defined state machine:

```c
typedef enum {
    NET_INIT,                    // Initial state - initialize context
    NET_SELECT_INTERFACE,        // Select best interface based on tests
    NET_WAIT_RESULTS,            // Waiting for ping test results
    NET_REVIEW_SCORE,            // Review scores and make selection
    NET_ONLINE,                  // Currently online with selected interface
    NET_ONLINE_CHECK_RESULTS,    // Checking online interface health
    NET_ONLINE_VERIFY_RESULTS,   // Verifying online interface connectivity
    NET_NO_STATES                // Sentinel value
} netmgr_state_t;
```

### 2.2 State Transitions

**Initialization Flow:**
```
NET_INIT → NET_SELECT_INTERFACE → NET_WAIT_RESULTS → NET_REVIEW_SCORE → NET_ONLINE
```

**Online Monitoring Flow:**
```
NET_ONLINE → NET_ONLINE_CHECK_RESULTS → NET_ONLINE_VERIFY_RESULTS
                                               ↓ (on failure)
                                    NET_SELECT_INTERFACE
```

**State Timeout Protection:**
- Maximum state duration: **20 seconds** (configurable via `MAX_STATE_DURATION`)
- Prevents getting stuck in any state
- Forces transition to `NET_INIT` or `NET_SELECT_INTERFACE` on timeout

### 2.3 Interface Indices

```c
enum {
    IFACE_ETH = 0,    // eth0 - Ethernet
    IFACE_WIFI,       // wlan0 - WiFi
    IFACE_PPP,        // ppp0 - Cellular
    IFACE_COUNT       // Total count = 3
};
```

---

## 3. Priority System: eth0 → wlan0 → ppp0

### 3.1 Priority Order

The network manager implements **strict priority-based selection** with quality thresholds:

**Phase 1: GOOD Threshold (Score ≥ 7/10)**
```
Priority Order: eth0 → wlan0 → ppp0
```
- First interface with score ≥ 7 is immediately selected
- No further evaluation needed if GOOD interface found

**Phase 1b: MINIMUM Threshold (Score ≥ 3/10)**
```
Priority Order: eth0 → wlan0 → ppp0
```
- If no GOOD interface found, look for minimum acceptable
- Select first interface with score ≥ 3
- Tie-breaking: Higher score wins, or lower latency if scores equal

**Phase 2: Absolute Best (Any Score > 0)**
```
Priority Order: eth0 → wlan0 → ppp0
```
- If no acceptable interface found, select best available
- Compares all interfaces and picks highest score/lowest latency

### 3.2 Scoring Mechanism

**Ping Test Configuration:**
- Ping count: **4 packets** (configurable, default in `network_timing_config.c`)
- Ping timeout: **1 second** per packet (configurable)
- Packet size: **56 bytes** (fixed)
- Target: `coap.imatrixsys.com` (DNS cached for 5 minutes)

**Score Calculation:**
```c
score = (100 - packet_loss_percentage) / 10;  // Range: 0-10
```

**Examples:**
- 0% packet loss → Score = 10/10 (perfect)
- 30% packet loss → Score = 7/10 (good threshold)
- 70% packet loss → Score = 3/10 (minimum threshold)
- 100% packet loss → Score = 0/10 (failed)

### 3.3 DHCP Server Interface Exclusion

**Critical Design Decision:** Interfaces operating as DHCP servers are **automatically excluded** from Internet gateway selection.

**Rationale:**
- DHCP server interfaces serve local clients (e.g., WiFi hotspot, Ethernet sharing)
- These interfaces don't provide Internet connectivity themselves
- Including them in selection would break Internet routing

**Implementation:**
```c
bool is_interface_in_server_mode(const char *ifname) {
    return is_dhcp_server_enabled(ifname);
}
```

**Exclusion Points:**
1. **Ping test initiation** - DHCP server interfaces are not tested
2. **Interface selection** - Excluded from `compute_best_interface()`
3. **Cooldown application** - No cooldown applied (wasn't tested, didn't fail)
4. **Route management** - Never set as default gateway

**Detection Method:**
- Checks for existence of `/etc/network/udhcpd-<interface>.conf`
- Verified by checking if `udhcpd` process is running for interface

---

## 4. Cellular Connectivity Management

### 4.1 Cellular Manager (`cellular_man.c`)

The cellular manager operates independently with its own state machine, managing:

1. **Modem Initialization** - AT command sequence for modem setup
2. **Network Registration** - Operator selection and network attachment
3. **PPP Connection** - Starting/stopping `pppd` daemon
4. **Signal Quality Monitoring** - RSSI and BER tracking
5. **Carrier Selection** - Automatic or manual operator selection

### 4.2 Cellular State Machine

**Key States:**
```c
typedef enum {
    CELL_INIT,                  // Initialize cellular modem
    CELL_PURGE_PORT,           // Clear serial port buffers
    CELL_PROCESS_INITIALIZATION, // Send initialization AT commands
    CELL_SETUP_OPERATOR,       // Configure network operator
    CELL_CONNECTED,            // Modem connected to network
    CELL_ONLINE,               // PPP connection established
    CELL_ONLINE_OPERATOR_CHECK, // Monitor connection health
    CELL_ONLINE_CHECK_CSQ,     // Check signal quality (CSQ)
    // ... additional states
} CellularState_t;
```

### 4.3 PPP Daemon Management

**Starting PPP:**
```c
void start_pppd(void);
```
- Called when cellular is ready and needed
- Network manager tracks start time in `ctx->ppp_start_time`
- Connection timeout: **60 seconds** (configurable via `PPP_WAIT_FOR_CONNECTION`)

**Stopping PPP:**
```c
void stop_pppd(bool cellular_reset);
```
- `cellular_reset=true`: Clean shutdown for modem reset
- `cellular_reset=false`: Shutdown due to failure (triggers blacklisting)

**Connection Detection:**
- Network manager checks for `ppp0` interface with valid IP address
- Uses `has_valid_ip_address("ppp0")` to verify connectivity
- Automatically marks `ctx->cellular_started = true` when detected

### 4.4 PPP Timeout and Blacklisting

**Timeout Handling:**
```c
#define PPP_WAIT_FOR_CONNECTION  60000  // 60 seconds (default)
```

**Integration with Network Manager:**
- If PPP doesn't obtain IP within timeout → cellular carrier may be blacklisted
- Timeout duration accessible via `imx_get_ppp_timeout()`
- Start time accessible via `imx_get_ppp_start_time()`

**Blacklisting Trigger:**
- PPP connection attempt exceeds timeout
- Cellular manager calls `blacklist_current_carrier(current_time)`
- Network manager receives notification via `imx_notify_pppd_stopped(false)`

---

## 5. Blacklisting Mechanisms

### 5.1 WiFi Access Point Blacklisting

**Implementation:** `wpa_blacklist.c`

**Purpose:** Temporarily blacklist WiFi access points (BSSIDs) that repeatedly fail connectivity tests.

**Mechanism:**
```c
int imx_blacklist_current_bssid(void);
```

**How it Works:**
1. Uses `wpa_cli` to communicate with `wpa_supplicant`
2. Retrieves current BSSID (MAC address of access point)
3. Issues `BLACKLIST <bssid>` command to `wpa_supplicant`
4. Access point is temporarily excluded from association attempts

**Blacklist Duration:**
- Managed by `wpa_supplicant` internal timeout
- Typically clears automatically after several minutes
- Can be manually cleared with `wpa_cli -i wlan0 blacklist clear`

**Trigger Conditions:**
1. WiFi score < MIN_ACCEPTABLE_SCORE (3/10)
2. Retry count reaches `MAX_WLAN_RETRIES` (3 attempts)
3. WiFi selected but performs poorly

**Network Manager Integration:**
```c
static void handle_wlan_retry(netmgr_ctx_t *ctx, bool wlan_test_success) {
    if (!wlan_test_success) {
        ctx->wlan_retries++;
        if (ctx->wlan_retries >= ctx->config.MAX_WLAN_RETRIES) {
            blacklist_current_ssid(ctx);  // Calls imx_blacklist_current_bssid()
            ctx->wlan_retries = 0;
        }
    }
}
```

### 5.2 Cellular Carrier Blacklisting

**Implementation:** `cellular_blacklist.c`

**Purpose:** Prevent repeated connection attempts to cellular carriers that fail to provide Internet connectivity.

**Data Structure:**
```c
typedef struct {
    uint32_t carrier_id;              // Numeric operator code (e.g., 310410 for AT&T)
    uint32_t current_blacklist_time;  // Current blacklist duration (ms)
    imx_time_t blacklist_start_time;  // When blacklisting started
    unsigned int blacklisted : 1;     // Currently blacklisted flag
} cellular_blacklist_t;
```

**Configuration:**
```c
#define NO_BLACKLISTED_CARRIERS  10      // Maximum carriers tracked
#define DEFAULT_BLACKLIST_TIME   300000  // 5 minutes (300 seconds)
```

**Blacklisting Process:**
```c
void blacklist_current_carrier(imx_time_t current_time);
```

**Mechanism:**
1. Retrieve current operator ID via `imx_get_4G_operator_id()`
2. Check if already blacklisted:
   - **First blacklist**: Set duration to 5 minutes
   - **Subsequent blacklists**: Double duration (exponential backoff)
3. Store in blacklist array with timestamp
4. Maximum of 10 carriers tracked; oldest entry replaced if full

**Blacklist Expiration:**
```c
void process_blacklist(imx_time_t current_time);
```
- Called periodically (every 60 seconds)
- Checks each blacklisted carrier's expiration time
- Automatically removes expired entries

**Carrier Checking:**
```c
bool is_carrier_blacklisted(uint32_t carrier_id);
```
- Called before attempting cellular connection
- Returns `true` if carrier is currently blacklisted
- Cellular manager skips blacklisted carriers during scan

**Manual Override:**
```c
void remove_carrier_from_blacklist(uint32_t carrier_id);
```
- Available via CLI for debugging/testing
- Immediately clears blacklist for specific carrier

**Export Information:**
```c
int get_blacklist_info(blacklist_export_info_t *info, size_t max_entries);
```
- Retrieve list of all blacklisted carriers
- Includes carrier ID, time remaining, and blacklist count
- Used for CLI display and monitoring

---

## 6. Cooldown Periods

### 6.1 Purpose

Cooldown periods prevent excessive connection attempts to failed interfaces, reducing:
- Network thrashing
- Power consumption
- Log noise
- Modem/driver instability

### 6.2 Cooldown Configuration

**Default Timing:**
```c
#define DEFAULT_ETH0_COOLDOWN_MS  30000   // 30 seconds
#define DEFAULT_WIFI_COOLDOWN_MS  30000   // 30 seconds
#define DEFAULT_PPP_COOLDOWN_MS   60000   // 60 seconds (PPP_WAIT_CONNECTION)
```

**Runtime Configuration:**
Stored in `device_config.netmgr_timing`:
```c
typedef struct {
    uint32_t eth0_cooldown_s;        // Ethernet cooldown (seconds)
    uint32_t wifi_cooldown_s;        // WiFi cooldown (seconds)
    uint32_t ppp_cooldown_s;         // PPP cooldown (seconds)
    uint32_t ppp_wait_connection_s;  // PPP connection timeout (seconds)
    // ... additional timing parameters
} netmgr_timing_config_t;
```

**Environment Variable Override:**
```bash
export NETMGR_ETH0_COOLDOWN_MS=60000   # 60 seconds
export NETMGR_WIFI_COOLDOWN_MS=45000   # 45 seconds
export NETMGR_PPP_COOLDOWN_MS=120000   # 120 seconds
```

### 6.3 Cooldown Activation

**Trigger Conditions:**

**Ethernet (eth0):**
1. Interface ping test fails (score = 0)
2. Interface had valid IP but lost connectivity
3. **Exception**: Grace period of 15 seconds after obtaining IP
4. **Exception**: DHCP server mode (no cooldown - wasn't tested)

**WiFi (wlan0):**
1. Ping test fails (score = 0)
2. Active interface loses connectivity
3. Repeated failures trigger WiFi reassociation or blacklisting
4. **Exception**: Grace period of 15 seconds after obtaining IP
5. **Exception**: Recently re-enabled (within 30 seconds)

**PPP (ppp0):**
1. Connection timeout (60 seconds without IP)
2. Ping test failures while connected
3. **Note**: PPP cooldown managed differently - relies on cellular manager state

### 6.4 Cooldown Implementation

**Setting Cooldown:**
```c
static void start_cooldown(netmgr_ctx_t *ctx, uint32_t iface, uint32_t duration_ms) {
    imx_time_t current_time;
    imx_time_get_time(&current_time);

    pthread_mutex_lock(&ctx->states[iface].mutex);
    ctx->states[iface].cooldown_until = current_time + duration_ms;
    ctx->states[iface].active = false;
    pthread_mutex_unlock(&ctx->states[iface].mutex);
}
```

**Checking Cooldown:**
```c
static bool is_in_cooldown(netmgr_ctx_t *ctx, uint32_t iface, imx_time_t current_time) {
    if (ctx->states[iface].cooldown_until == 0)
        return false;

    return !imx_is_later(current_time, ctx->states[iface].cooldown_until);
}
```

**Cooldown Bypass:**
- WiFi: Manual re-enable via `imx_set_wifi0_enabled(true)` clears cooldown
- Ethernet: Carrier detection (cable plug-in) can clear cooldown
- PPP: Cellular transition from NOT_READY → READY clears state

### 6.5 Grace Periods

**IP Obtained Grace Period:**
```c
const uint32_t GRACE_PERIOD_MS = 15000;  // 15 seconds
```

**Purpose:**
- Newly obtained IP addresses need time to stabilize
- Prevents premature interface failure detection
- Allows DHCP, routing, and ARP to settle

**Implementation:**
```c
imx_time_t time_since_ip = imx_time_difference(current_time,
                                                ctx->states[iface].ip_obtained_time);

if (ctx->states[iface].ip_obtained_time > 0 &&
    time_since_ip < GRACE_PERIOD_MS) {
    // Don't flush or apply cooldown yet
    return;
}
```

---

## 7. Data Structures and Key Variables

### 7.1 Network Manager Context

**Primary Context:**
```c
typedef struct {
    netmgr_config_t config;              // Configuration parameters
    netmgr_state_t state;                // Current state
    netmgr_state_t state_previous;       // Previous state (for logging)
    imx_time_t state_entry_time;         // When we entered current state

    uint32_t current_interface;          // Currently selected interface
    uint32_t last_interface;             // Previously selected interface
    uint32_t verify_interface;           // Interface being verified

    iface_state_t states[IFACE_COUNT];   // Per-interface state (3 interfaces)

    // Timing and retry tracking
    imx_time_t last_network_process_time;
    imx_time_t ppp_start_time;           // When PPP connection started
    imx_time_t link_up_time;
    uint32_t wlan_retries;               // WiFi retry counter
    uint32_t ppp_retries;                // PPP retry counter
    uint32_t ppp_ping_failures;          // Consecutive PPP ping failures

    // Flags
    unsigned int last_link_up : 1;
    unsigned int reset_udp : 1;          // UDP needs reset after switch
    unsigned int any_interface_online : 1;
    unsigned int first_test_run : 1;     // First test run flag
    unsigned int offline_mode : 1;       // Testing mode
    unsigned int cellular_started : 1;   // PPP daemon started
    unsigned int cellular_stopped : 1;   // PPP daemon stopped

    // WiFi re-enable tracking
    imx_time_t wifi_reenable_time;       // When WiFi was re-enabled
    uint32_t wifi_reconnect_attempts;    // Reconnection attempts
    unsigned int came_from_ppp : 1;      // Were we on PPP before WiFi re-enable?

    // Hysteresis tracking
    imx_time_t last_interface_switch_time;
    uint32_t interface_switch_count;
    imx_time_t hysteresis_window_start;
    bool hysteresis_active;

    // Ethernet reconnection
    bool eth0_had_carrier;
    imx_time_t eth0_dhcp_renewal_time;
    bool eth0_dhcp_restarted;

    // PPPD conflict management
    imx_time_t last_pppd_conflict_time;
    uint32_t pppd_conflict_count;
    uint32_t pppd_conflict_cooldown_ms;

    // WiFi background scanning
    imx_time_t last_wifi_scan_time;
    uint32_t wifi_scan_attempts;

    pthread_mutex_t state_mutex;         // State transition protection
} netmgr_ctx_t;
```

**Global Instance:**
```c
static netmgr_ctx_t g_netmgr_ctx = {0};
```

### 7.2 Per-Interface State

```c
typedef struct {
    pthread_t thread;                    // Ping thread handle
    imx_time_t last_spawn;
    imx_time_t start_time;               // When ping test started

    bool link_up;                        // Interface has connectivity
    uint16_t latency;                    // Average latency (ms)
    uint16_t score;                      // Connectivity score (0-10)
    imx_time_t cooldown_until;           // Cooldown expiration time

    pthread_mutex_t mutex;               // Thread-safe access

    // Bit flags
    unsigned int running : 1;            // Ping test running
    unsigned int test_attempted : 1;     // Test has been attempted
    unsigned int active : 1;             // Interface has valid IP
    unsigned int disabled : 1;           // Manually disabled
    unsigned int thread_valid : 1;       // Thread handle is valid
    unsigned int reassociating : 1;      // WiFi reassociation in progress

    imx_time_t reassoc_start_time;       // When reassociation started
    imx_time_t ip_obtained_time;         // When IP was obtained (grace period)

    // Statistics
    uint32_t total_pings_sent;
    uint32_t total_pings_success;
    uint32_t total_pings_failed;
    uint32_t consecutive_failures;
    imx_time_t last_ping_time;
    uint32_t avg_latency_ms;
} iface_state_t;
```

### 7.3 Configuration Structure

```c
typedef struct {
    uint32_t ETH0_COOLDOWN_TIME;         // Ethernet cooldown (ms)
    uint32_t WIFI_COOLDOWN_TIME;         // WiFi cooldown (ms)
    uint32_t MAX_STATE_DURATION;         // Max time in any state (ms)
    uint32_t MAX_WLAN_RETRIES;           // WiFi retry limit
    uint32_t ONLINE_CHECK_TIME;          // Online check interval (ms)
    uint32_t PPP_WAIT_FOR_CONNECTION;    // PPP connection timeout (ms)

    bool wifi_reassoc_enabled;           // Enable WiFi reassociation
    wifi_reassoc_method_t wifi_reassoc_method;
    uint32_t wifi_scan_wait_ms;
} netmgr_config_t;
```

### 7.4 Timing Configuration

**Extended Timing Parameters:**
```c
typedef struct {
    // Interface cooldowns
    uint32_t eth0_cooldown_ms;
    uint32_t wifi_cooldown_ms;
    uint32_t ppp_cooldown_ms;

    // State machine timing
    uint32_t max_state_duration_ms;
    uint32_t online_check_time_ms;
    uint32_t ppp_wait_connection_ms;

    // Ping configuration
    uint32_t ping_interval_ms;           // Time between ping tests
    uint32_t ping_timeout_ms;            // Per-ping timeout
    uint32_t ping_count;                 // Number of pings per test

    // DNS timing
    uint32_t dns_cache_timeout_ms;

    // WiFi timing
    uint32_t wifi_scan_wait_ms;
    uint32_t wifi_dhcp_wait_ms;
    uint32_t wifi_reconnect_delay_ms;

    // Hysteresis configuration
    uint32_t hysteresis_window_ms;
    uint32_t hysteresis_switch_limit;
    uint32_t hysteresis_cooldown_ms;
    uint32_t hysteresis_min_stable_ms;
    bool hysteresis_enabled;
} network_timing_config_t;
```

### 7.5 Cellular Operator Structure

```c
typedef struct {
    uint32_t status;                     // Operator status (available/current/forbidden)
    char longAlphanumeric[17];           // Long operator name
    char shortAlphanumeric[9];           // Short operator name
    uint32_t numeric;                    // MCC+MNC code (e.g., 310410)
    int32_t networkAccessTechnology;     // RAT (GSM/UTRAN/E-UTRAN)
    int16_t rssi;                        // Signal strength
    int16_t ber;                         // Bit error rate
    unsigned int bad_operator : 1;       // Blacklisted flag
} Operator_t;
```

### 7.6 Ping Thread Arguments

```c
typedef struct {
    uint32_t iface;          // Interface index (IFACE_ETH/IFACE_WIFI/IFACE_PPP)
    uint32_t target_ip;      // Target IP in host order
} ping_arg_t;
```

### 7.7 DNS Cache

```c
static imx_ip_address_t cached_site_ip;   // Cached IP of coap.imatrixsys.com
static bool dns_primed = false;           // DNS cache valid flag
static imx_time_t dns_cache_time = 0;     // When DNS was resolved
static pthread_mutex_t dns_cache_mutex = PTHREAD_MUTEX_INITIALIZER;

#define DNS_CACHE_TIMEOUT_MS  300000      // 5 minutes
```

---

## 8. Key Algorithms and Logic

### 8.1 Interface Selection Algorithm

**Function:** `compute_best_interface()`

**Priority Array:**
```c
const uint32_t priority[IFACE_COUNT] = {IFACE_ETH, IFACE_WIFI, IFACE_PPP};
```

**Selection Logic:**

```
1. PHASE 1: GOOD Threshold (score ≥ 7)
   FOR each interface in priority order:
       IF active AND link_up AND NOT disabled AND score ≥ 7:
           RETURN interface

2. PHASE 1b: MINIMUM Threshold (score ≥ 3)
   best = NONE
   FOR each interface in priority order:
       IF active AND link_up AND NOT disabled AND score ≥ 3:
           IF best == NONE OR better_than(current, best):
               best = current
   IF best != NONE:
       RETURN best

3. PHASE 2: Absolute Best (any score > 0)
   best = NONE
   FOR each interface in priority order:
       IF active AND link_up AND NOT disabled:
           IF best == NONE OR better_than(current, best):
               best = current
   RETURN best (may be NONE if all interfaces down)
```

**Comparison Function:**
```c
static bool better_iface(const iface_state_t *a, const iface_state_t *b) {
    if (a->score != b->score)
        return a->score > b->score;  // Higher score wins
    return a->latency < b->latency;  // Lower latency wins if score tied
}
```

### 8.2 Ping Test Execution

**Function:** `execute_ping()`

**Process:**
1. Validate interface is enabled (check disabled flag)
2. Build ping command: `ping -n -I <iface> -c <count> -W <timeout> -s 56 <target>`
3. Execute via `popen()` and parse output
4. Extract statistics:
   - Replies received
   - Average latency
   - Packet loss percentage
5. Calculate score: `(100 - packet_loss) / 10`
6. Update interface state with results

**Thread Management:**
- Each ping runs in detached pthread
- Thread marked with `thread_valid` flag
- Cleanup handler ensures state reset on cancellation
- Maximum ping duration: `timeout_per_ping * count + 15 seconds`

### 8.3 WiFi Reassociation

**Function:** `force_wifi_reassociate()`

**Methods:**
1. **WPA_CLI Method** (default):
   ```bash
   wpa_cli -i wlan0 disconnect
   sleep 0.2
   wpa_cli -i wlan0 reconnect
   ```

2. **Blacklist Method**:
   ```bash
   wpa_cli -i wlan0 blacklist <current_bssid>
   wpa_cli -i wlan0 reassociate
   ```

3. **Reset Method**:
   ```bash
   ip link set wlan0 down
   sleep 1
   ip link set wlan0 up
   ```

**Reassociation Tracking:**
```c
ctx->states[IFACE_WIFI].reassociating = 1;
ctx->states[IFACE_WIFI].reassoc_start_time = current_time;
start_cooldown(ctx, IFACE_WIFI, 10000);  // 10 second cooldown during reassociation
```

### 8.4 Route Management

**Setting Default Route:**
```c
bool set_default_via_iface(const char *ifname) {
    // 1. Delete all existing default routes
    system("ip route del default 2>/dev/null");

    // 2. Get gateway IP for interface
    char gateway[32];
    if (get_gateway_ip(ifname, gateway) == 0) {
        // 3. Set default route via gateway
        snprintf(cmd, sizeof(cmd), "ip route add default via %s dev %s",
                 gateway, ifname);
        system(cmd);
    } else {
        // 4. Set default route via device only
        snprintf(cmd, sizeof(cmd), "ip route add default dev %s", ifname);
        system(cmd);
    }

    return verify_default_route(ifname);
}
```

**Route Verification:**
```c
bool verify_default_route(const char *ifname) {
    char cmd[256];
    snprintf(cmd, sizeof(cmd),
             "ip route | grep -q '^default.*dev %s'", ifname);
    return (system(cmd) == 0);
}
```

### 8.5 DHCP Management

**Killing DHCP Client:**
```c
bool kill_dhcp_client(const char *ifname) {
    char pidfile[64];
    snprintf(pidfile, sizeof(pidfile), "/var/run/udhcpc.%s.pid", ifname);

    FILE *fp = fopen(pidfile, "r");
    if (!fp) return false;

    pid_t pid;
    fscanf(fp, "%d", &pid);
    fclose(fp);

    kill(pid, SIGTERM);
    unlink(pidfile);
    return true;
}
```

**Flushing Interface:**
```c
bool flush_interface_addresses(const char *ifname) {
    char cmd[128];

    // Kill DHCP client
    kill_dhcp_client(ifname);

    // Flush IP addresses
    snprintf(cmd, sizeof(cmd), "ip addr flush dev %s", ifname);
    system(cmd);

    return true;
}
```

---

## 9. Timing Details

### 9.1 Cooldown Periods

| Interface | Default Duration | Configurable Via |
|-----------|------------------|------------------|
| **eth0** | 30 seconds | `NETMGR_ETH0_COOLDOWN_MS` |
| **wlan0** | 30 seconds | `NETMGR_WIFI_COOLDOWN_MS` |
| **ppp0** | 60 seconds | `NETMGR_PPP_COOLDOWN_MS` |

### 9.2 State Timing

| Parameter | Default | Purpose |
|-----------|---------|---------|
| **MAX_STATE_DURATION** | 20 seconds | Maximum time in any state before timeout |
| **ONLINE_CHECK_TIME** | 10 seconds | Interval between online connectivity checks |
| **PPP_WAIT_CONNECTION** | 60 seconds | Maximum time to wait for PPP IP address |

### 9.3 Ping Timing

| Parameter | Default | Configurable Via |
|-----------|---------|------------------|
| **Ping Count** | 4 packets | `NETMGR_PING_COUNT` |
| **Ping Timeout** | 1 second | `NETMGR_PING_TIMEOUT_MS` |
| **Ping Interval** | 5 seconds | `NETMGR_PING_INTERVAL_MS` |
| **DNS Cache** | 5 minutes | `NETMGR_DNS_CACHE_TIMEOUT_MS` |

### 9.4 WiFi Timing

| Parameter | Default | Purpose |
|-----------|---------|---------|
| **Scan Wait** | 2 seconds | Wait for scan completion |
| **DHCP Wait** | 5 seconds | Wait for DHCP IP assignment |
| **Scan Interval** | 30 seconds | Background scan when WiFi down |
| **Max Scan Attempts** | 10 | Stop scanning after this many attempts |
| **Scan Reset Interval** | 5 minutes | Reset scan attempts after this period |

### 9.5 Hysteresis Timing

| Parameter | Default | Purpose |
|-----------|---------|---------|
| **Window** | 60 seconds | Time window for tracking switches |
| **Switch Limit** | 3 | Max switches in window before hysteresis |
| **Cooldown** | 30 seconds | Cooldown when hysteresis triggered |
| **Min Stable** | 10 seconds | Minimum time on interface before switch |

### 9.6 Grace Periods

| Scenario | Duration | Purpose |
|----------|----------|---------|
| **IP Obtained** | 15 seconds | Allow network to stabilize after DHCP |
| **WiFi Re-enabled** | 30 seconds | Allow reconnection after manual re-enable |
| **PPP Connection** | 60 seconds | Allow PPP to establish before timeout |

---

## 10. Debugging and Monitoring

### 10.1 Debug Flags

**Per-Interface Debug Logging:**
```c
#define DEBUGS_FOR_ETH0_NETWORKING   // Enable eth0 debug logs
#define DEBUGS_FOR_WIFI0_NETWORKING  // Enable wlan0 debug logs
#define DEBUGS_FOR_PPP0_NETWORKING   // Enable ppp0 debug logs
#define DEBUGS_FOR_NETWORKING_SWITCH // Enable interface switch logs
```

**Activation:**
```bash
debug DEBUGS_FOR_ETH0_NETWORKING    # Enable eth0 debugging
debug DEBUGS_FOR_WIFI0_NETWORKING   # Enable WiFi debugging
debug DEBUGS_FOR_PPP0_NETWORKING    # Enable PPP debugging
```

### 10.2 CLI Commands

**Network Status:**
```bash
net status        # Display network manager state and interface status
net              # Alias for 'net status'
```

**Cellular Status:**
```bash
cell             # Display cellular modem status and carrier info
```

**Blacklist Management:**
```bash
cell blacklist   # Display cellular carrier blacklist
```

**Configuration Display:**
```bash
net config       # Display network timing configuration
```

### 10.3 Status Display Format

**Network Manager Status includes:**
- Current state and state duration
- Active interface and last interface
- Per-interface status:
  - Link status (carrier/association/daemon)
  - IP address
  - Score and latency
  - Active/disabled flags
  - Cooldown status
  - Ping statistics
- Routing table
- DHCP client status

### 10.4 Log Messages

**State Transition Logging:**
```
[NETMGR] State: NET_INIT | Initializing network manager
[NETMGR] State: NET_SELECT_INTERFACE | Starting interface tests
[NETMGR-ETH0] State: NET_WAIT_RESULTS | Launching ping test for eth0
```

**Interface Selection:**
```
[COMPUTE_BEST] Priority order: eth0 -> wlan0 -> ppp0
[COMPUTE_BEST] Phase 1: Looking for GOOD links
[COMPUTE_BEST] Found GOOD link by priority: eth0 (score=8, latency=12)
```

**Cooldown Activation:**
```
[NETMGR-ETH0] ETH0 failed test, flushing addresses and starting cooldown
[NETMGR-ETH0] Starting cooldown for 30000 ms
```

**Blacklisting:**
```
[NETMGR-WIFI0] WLAN max retries reached, blacklisting current SSID
[Cellular Connection - Blacklisting current carrier: 310410]
```

---

## 11. Special Scenarios and Edge Cases

### 11.1 First Test Run Deferral

**Problem:** On initial startup, interfaces may have IP addresses but routing/connectivity not fully established.

**Solution:**
```c
if (ctx->first_test_run && (eth0_score > 0 || wifi_score > 0)) {
    // Defer side effects (flushing, cooldown) on first run
    // Allow interface selection but skip route changes
    ctx->first_test_run = false;
    return;
}
```

### 11.2 WiFi Re-enable After PPP

**Scenario:** User disables WiFi, system falls back to PPP, then user re-enables WiFi.

**Challenge:** WiFi needs priority over PPP but may need time to reconnect.

**Solution:**
1. Track when WiFi was re-enabled: `ctx->wifi_reenable_time`
2. Track if we came from PPP: `ctx->came_from_ppp`
3. Allow 30-second grace period for WiFi reconnection
4. Prevent cooldown during reconnection attempts
5. Force WiFi reassociation on re-enable

### 11.3 Ethernet Cable Reconnection

**Scenario:** Ethernet cable unplugged, then reconnected.

**Detection:**
```c
bool carrier_detected = /* check carrier status */;
if (!ctx->eth0_had_carrier && carrier_detected) {
    // Cable just plugged in
    renew_dhcp_lease("eth0");
}
ctx->eth0_had_carrier = carrier_detected;
```

### 11.4 PPP Already Running

**Scenario:** `pppd` started externally or from previous run.

**Detection:**
```c
if (system("pidof pppd >/dev/null 2>&1") == 0) {
    // PPPD already running
    ctx->cellular_started = true;
    ctx->cellular_stopped = false;
}
```

### 11.5 PPPD Route Conflicts

**Problem:** PPPD automatically adds default route, conflicting with network manager.

**Solution:**
1. Delete conflicting routes before setting new default
2. Use `ip route del default 2>/dev/null` to clear all defaults
3. Re-establish desired default route
4. Track conflicts with cooldown and backoff

**Conflict Tracking:**
```c
#define PPPD_CONFLICT_MIN_COOLDOWN_MS   5000    // 5 seconds
#define PPPD_CONFLICT_MAX_COOLDOWN_MS   60000   // 60 seconds
#define PPPD_CONFLICT_MAX_COUNT         5       // Max before interface switch
#define PPPD_CONFLICT_BACKOFF_MULTIPLIER 2      // Exponential backoff
```

### 11.6 WiFi Background Scanning

**Purpose:** Help `wpa_supplicant` discover networks when WiFi is down.

**Implementation:**
```c
#define WIFI_SCAN_INTERVAL_MS      30000   // 30 seconds
#define WIFI_SCAN_MAX_ATTEMPTS     10      // Stop after 10 attempts
#define WIFI_SCAN_RESET_INTERVAL_MS 300000 // Reset after 5 minutes
```

**Logic:**
```c
static bool trigger_wifi_scan_if_down(netmgr_ctx_t *ctx, imx_time_t current_time) {
    // Only scan if WiFi enabled but inactive
    if (!imx_use_wifi0() || ctx->states[IFACE_WIFI].active)
        return false;

    // Respect cooldown period
    if (is_in_cooldown(ctx, IFACE_WIFI, current_time))
        return false;

    // Limit scan frequency
    if (time_since_last_scan < WIFI_SCAN_INTERVAL_MS)
        return false;

    // Limit total attempts
    if (ctx->wifi_scan_attempts >= WIFI_SCAN_MAX_ATTEMPTS) {
        // Reset after long period
        if (time_since_last_scan > WIFI_SCAN_RESET_INTERVAL_MS)
            ctx->wifi_scan_attempts = 0;
        else
            return false;
    }

    // Trigger scan
    system("wpa_cli -i wlan0 scan >/dev/null 2>&1");
    ctx->last_wifi_scan_time = current_time;
    ctx->wifi_scan_attempts++;
    return true;
}
```

---

## 12. Integration Points

### 12.1 Cellular Manager Integration

**Network Manager → Cellular Manager:**
- `start_pppd()` - Request PPP connection
- `stop_pppd(bool cellular_reset)` - Request PPP shutdown
- `imx_is_cellular_now_ready()` - Check if cellular modem is ready
- `imx_set_operator_as_bad()` - Mark current operator as bad

**Cellular Manager → Network Manager:**
- Sets `ppp0` interface when connection established
- Provides signal quality via `imx_get_4G_rssi()`, `imx_get_4G_ber()`
- Provides operator info via `imx_get_4G_operator_id()`
- Notifies connection status via `imx_is_4G_connected()`

### 12.2 CoAP/UDP Integration

**Interface Changes:**
```c
if (link_type_set_function != NULL) {
    link_type_set_function(new_link_type);
}
```
- Notifies upper layers of interface change
- Triggers UDP socket reset: `imx_network_reset_udp()`
- Registered via `imx_set_notify_link_type_set(callback)`

### 12.3 Configuration System

**Loading Configuration:**
```c
extern IOT_Device_Config_t device_config;

// Access timing config
netmgr_timing_config_t *timing = &device_config.netmgr_timing;

// Access interface config
network_interfaces_t *eth0 = &device_config.network_interfaces[IMX_ETH0_INTERFACE];
```

**Saving State:**
- Interface enabled/disabled states saved to `device_config`
- Timing parameters persisted with magic number validation
- Configuration saved via `imatrix_save_config()`

---

## 13. Future Enhancements

### 13.1 Potential Improvements

1. **Dynamic Priority Adjustment**
   - Allow runtime priority configuration
   - Consider signal strength in priority calculation
   - User-defined priority overrides

2. **Advanced Blacklisting**
   - Track failure reasons (timeout vs poor quality)
   - Progressive blacklist durations per SSID
   - Whitelist for trusted networks

3. **Bandwidth Monitoring**
   - Track data usage per interface
   - Cost-aware interface selection
   - Rate limiting on cellular

4. **Predictive Switching**
   - Learn network availability patterns
   - Pre-emptive failover based on history
   - Time-of-day based preferences

5. **Enhanced Diagnostics**
   - Detailed connectivity metrics export
   - Historical performance tracking
   - Anomaly detection

### 13.2 Known Limitations

1. **Single Target Testing**
   - Only tests connectivity to `coap.imatrixsys.com`
   - Doesn't verify general Internet connectivity
   - DNS dependency

2. **Fixed Ping Parameters**
   - Packet size fixed at 56 bytes
   - Cannot adjust for different network conditions
   - No adaptive timeout

3. **Serial Interface Selection**
   - Tests interfaces one at a time
   - Could parallelize for faster failover
   - Current approach reduces network load

4. **Blacklist Persistence**
   - WiFi blacklist managed by `wpa_supplicant` (volatile)
   - Cellular blacklist not persisted across reboots
   - Manual intervention required for persistent blacklisting

---

## 14. Identified Design Flaws and Recommendations

This section documents design issues identified during code review on 2025-12-06.

### 14.1 Critical: Race Conditions in Shared State Variables

**Location:** `cellular_man.c` lines 629-661, accessed by `process_network.c`

**Issue:** Shared state variables between cellular and network managers lack mutex protection:
- `cellular_scanning` (bool) - read by network manager to block PPP operations
- `cellular_now_ready` (bool) - read by network manager to determine PPP availability
- `cellular_request_rescan` (bool) - written by network manager, read by cellular manager

**Risk:** Race conditions where network manager reads stale or partially-updated state, leading to:
- PPP activation during active scan (modem conflict)
- Scan initiated while PPP is being established
- Missed scan requests due to flag race

**Recommendation:** Add mutex protection around all shared state access, or use atomic operations.

### 14.2 Critical: Blacklist Oldest Entry Detection Bug

**Location:** `cellular_blacklist.c` lines 153-165

**Issue:** The `oldest_time` variable is initialized to 0:
```c
imx_time_t oldest_time = 0;
for (uint32_t j = 0; j < blacklist_count; j++) {
    if (blacklist[j].blacklist_start_time < oldest_time) {  // Always false!
```

Since valid timestamps are always > 0, the comparison `blacklist_start_time < oldest_time` is never true. The oldest entry is never found.

**Impact:** When blacklist is full, the "replace oldest non-blacklisted entry" logic fails silently.

**Recommendation:** Initialize `oldest_time = UINT32_MAX` or use a found flag pattern.

### 14.3 High: Time Wraparound Vulnerability

**Location:** Throughout `process_network.c`

**Issue:** Direct comparisons of `imx_time_t` (uint32_t) values will fail after ~49 days:
```c
// Line 5405 - Direct comparison vulnerable to wraparound
if (ctx->states[IFACE_ETH].cooldown_until < current_check_time)
```

While `imx_time_difference()` and `imx_is_later()` may handle wraparound correctly, direct `<` comparisons scattered throughout the code do not.

**Affected Lines:** 5405, 5408, and similar direct time comparisons.

**Recommendation:** Audit all time comparisons and replace with `imx_is_later()` calls.

### 14.4 High: Blocking System Calls in State Machine

**Location:** `process_network.c` lines 4378-4380

**Issue:** Blocking calls halt the main processing loop:
```c
system("wpa_cli -i wlan0 disconnect >/dev/null 2>&1");
usleep(200000);  // 200ms blocking delay!
system("wpa_cli -i wlan0 reconnect >/dev/null 2>&1");
```

Also in `cellular_man.c` line 1070:
```c
system("sv up pppd 2>/dev/null");
```

**Impact:**
- Main loop stalls during WiFi reassociation
- Other interfaces not monitored during blocking calls
- Potential watchdog timeout on embedded systems

**Recommendation:** Convert to non-blocking state machine pattern or use fork/exec with async monitoring.

### 14.5 Medium: Fragile Scan Protection Gate

**Location:** `cellular_man.c` lines 907-933

**Issue:** Health protection resets completely on single failure:
```c
if (check_passed && score >= SCAN_PROTECTION_MIN_HEALTH_SCORE) {
    ppp_consecutive_health_passes++;  // Accumulates up to 100
} else {
    ppp_consecutive_health_passes = 0;  // Complete reset on one failure!
}
```

A single transient failure (e.g., DNS hiccup) resets protection even after 100 consecutive successes.

**Impact:** Valid connections can be scanned and killed due to momentary issues.

**Recommendation:** Use sliding window or require N failures in M checks before resetting protection.

### 14.6 Medium: Duplicate State Tracking

**Location:** `cellular_man.c` and `process_network.c`

**Issue:** Both modules independently track PPP/cellular status:
- `cellular_now_ready` (cellular_man.c)
- `cellular_started`, `cellular_stopped`, `cellular_reset_stop` (process_network.c context)

**Risk:** State divergence when updates aren't synchronized, leading to contradictory decisions.

**Recommendation:** Single source of truth with accessor functions, or formal state synchronization protocol.

### 14.7 Medium: Inconsistent Blacklist Functions

**Location:** `cellular_blacklist.c`

**Issue:** Two functions handle blacklisting differently:
- `blacklist_current_carrier()` - uses exponential backoff
- `blacklist_carrier_by_id()` - uses fixed default timeout

**Impact:** Different carriers get different blacklist treatment depending on how they're blacklisted.

**Recommendation:** Unify blacklisting logic into single function with consistent behavior.

### 14.8 Low: Missing Return Value Checks

**Location:** Throughout both files

**Issue:** Several `system()` calls don't check return values:
```c
system("sv up pppd 2>/dev/null");  // No error check
```

**Impact:** Failed commands proceed silently, potentially leaving system in inconsistent state.

**Recommendation:** Check return values and handle failures appropriately.

### 14.9 Low: Potential Thread Safety in Ping Thread

**Location:** `process_network.c` ping thread infrastructure

**Issue:** The `iface_state_t` structure is accessed from both main thread and ping threads with `MUTEX_LOCK` but:
- Thread cancellation during mutex hold could deadlock
- Timeout-based thread joining may leave orphaned threads

**Recommendation:** Use pthread cleanup handlers and ensure proper thread lifecycle management.

### 14.10 Architectural: Tight Coupling Between Modules

**Issue:** `process_network.c` and `cellular_man.c` have bidirectional dependencies:
- Network manager calls `cellular_man()`, `imx_is_cellular_now_ready()`, etc.
- Cellular manager receives health updates via `cellular_update_ppp_health()`
- Both share global flags via extern declarations

**Impact:** Changes in one module can break the other; difficult to test in isolation.

**Recommendation:** Define clear interface boundary with formal API contract.

---

## 15. Conclusion

The iMatrix Network Manager provides robust, priority-based interface failover with comprehensive error handling, blacklisting, and cooldown mechanisms. The architecture ensures:

✅ **Reliability:** Automatic failover with health monitoring
✅ **Efficiency:** Cooldown periods prevent excessive retries
✅ **Intelligence:** Blacklisting prevents repeated failures
✅ **Flexibility:** Configurable timing and priorities
✅ **Integration:** Seamless cellular management via `cellular_man.c`
✅ **Correctness:** DHCP server interfaces properly excluded

⚠️ **Known Issues:** Section 14 documents design flaws that should be addressed in future revisions.

This document serves as the definitive reference for understanding and maintaining the network management subsystem.

---

**Document Version:** 1.2
**Last Updated:** 2025-12-06
**Author:** Claude Code Analysis
**Source Code Version:** process_network.c (7663 lines), cellular_man.c (5952 lines)
**Review Status:** Design flaws documented - requires remediation
