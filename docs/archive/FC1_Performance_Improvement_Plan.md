# FC-1 Performance Improvement Plan

**Date:** 2025-12-22
**Version:** 1.0
**Author:** Claude Code
**Status:** Planning Phase
**Based On:** strace profiling analysis from profile_bundle_20251222_161721

---

## Executive Summary

Profiling analysis identified three major performance hotspots in FC-1:

| Issue | Current Impact | Estimated Reduction |
|-------|----------------|---------------------|
| Heavy `ip route` spawning | ~113 spawns/30s, 49.8% wait time | 90-95% reduction |
| Excessive `clock_gettime` calls | ~31,000 calls/30s (1,031/sec) | 70-80% reduction |
| Repeated file I/O for carrier state | Multiple fopen/fread/fclose per check | 50-70% reduction |

**Total Expected Improvement:** 40-60% reduction in CPU overhead

---

## Issue 1: Heavy `ip route` Process Spawning

### Current Behavior
The network manager spawns external `ip route` commands approximately 4 times per second via `popen()` and `system()` calls.

**Files involved:**
- `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
  - Line 3333: `system("ip route show | head -5");` (debug logging)
  - Line 3483: `system("ip route show | head -10");` (debug logging)

**strace evidence:**
```
clone() → pipe2 → wait4 = 113 times in 30 seconds
wait4: 2.12 seconds (49.8% of total syscall time)
```

### Root Cause
- Route checking uses external commands instead of native APIs
- Debug logging executes route commands even when not actively debugging
- Each spawn involves: `clone + pipe2 + exec + wait4` overhead

### Recommended Fixes

#### Fix 1.1: Use Netlink API for Route Queries (HIGH PRIORITY)
Replace `popen("ip route")` with direct netlink socket communication.

**Implementation approach:**
```c
// Instead of:
FILE *fp = popen("ip route show default", "r");

// Use netlink:
#include <linux/rtnetlink.h>

static int get_default_route_via_netlink(const char *ifname, char *gateway, size_t len)
{
    int sock = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    struct {
        struct nlmsghdr nlh;
        struct rtmsg rtm;
    } req;

    memset(&req, 0, sizeof(req));
    req.nlh.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
    req.nlh.nlmsg_type = RTM_GETROUTE;
    req.nlh.nlmsg_flags = NLM_F_REQUEST | NLM_F_DUMP;
    req.rtm.rtm_family = AF_INET;
    req.rtm.rtm_table = RT_TABLE_MAIN;

    send(sock, &req, req.nlh.nlmsg_len, 0);
    // Parse response to extract gateway for interface
    close(sock);
    return 0;
}
```

**Benefit:** Eliminates all process spawning for route queries
**Effort:** Medium (2-3 hours)
**Risk:** Low - netlink is stable Linux API

#### Fix 1.2: Cache Route Information (MEDIUM PRIORITY)
Instead of checking routes on every network poll, cache and refresh periodically.

**Implementation:**
```c
// In process_network.c - add to netmgr_ctx_t
typedef struct {
    char default_gateway[16];
    char default_interface[16];
    imx_time_t last_update;
    bool valid;
} route_cache_t;

static route_cache_t g_route_cache = {0};
#define ROUTE_CACHE_TTL_MS 5000  // Refresh every 5 seconds

static bool get_cached_default_route(char *gateway, char *iface)
{
    imx_time_t now;
    imx_time_get_time(&now);

    if (g_route_cache.valid &&
        imx_time_difference(now, g_route_cache.last_update) < ROUTE_CACHE_TTL_MS) {
        strcpy(gateway, g_route_cache.default_gateway);
        strcpy(iface, g_route_cache.default_interface);
        return true;
    }

    // Cache miss - refresh via netlink
    update_route_cache_via_netlink();
    return g_route_cache.valid;
}
```

**Benefit:** 80-95% reduction in route lookups
**Effort:** Low (1 hour)
**Risk:** Low

#### Fix 1.3: Guard Debug Route Logging (LOW PRIORITY)
The `system("ip route show")` calls are inside debug blocks but still execute.

**Current code (line 3333):**
```c
if (LOGS_ENABLED(DEBUGS_FOR_ETH0_NETWORKING) ||
    LOGS_ENABLED(DEBUGS_FOR_WIFI0_NETWORKING) ||
    LOGS_ENABLED(DEBUGS_FOR_PPP0_NETWORKING)) {
    system("ip route show | head -5");  // Still spawns process!
}
```

**Fix:** These are already guarded by debug flags. Ensure debug flags are OFF in production builds, or use cached route info for display.

---

## Issue 2: Excessive clock_gettime Calls

### Current Behavior
The application calls `imx_time_get_time()` approximately 1,031 times per second, resulting in 31,000 `clock_gettime64` syscalls in 30 seconds.

**Files with heavy usage:**
| File | Calls | Purpose |
|------|-------|---------|
| `process_network.c` | 16 | Network state machine timing |
| `can_file_send.c` | 8 | CAN data file transfers |
| `can_server.c` | 4 | CAN server operations |
| `can_utils.c` | 4 | CAN utilities |
| `can_processing_thread.c` | 1 | CAN thread timing |

**strace evidence:**
```
clock_gettime64: 30,929 calls, 0.68 seconds (15.9% of total)
Average: ~1,031 calls/second
```

### Root Cause
- Time is fetched fresh for every operation, even within same loop iteration
- No time caching within processing cycles
- Multiple subsystems independently fetch time

### Recommended Fixes

#### Fix 2.1: Implement Per-Cycle Time Caching (HIGH PRIORITY)
Cache the current time at the start of each main loop iteration.

**Implementation in `imatrix_interface.c` or `do_everything.c`:**
```c
// Global cached time (thread-local if multi-threaded)
static __thread imx_time_t g_cached_time = 0;
static __thread bool g_time_valid = false;

/**
 * @brief Get cached time for current processing cycle
 *
 * Returns the time cached at the start of the current loop iteration.
 * Much faster than clock_gettime for repeated calls.
 */
imx_time_t imx_get_cycle_time(void)
{
    return g_cached_time;
}

/**
 * @brief Refresh cached time - call once per main loop iteration
 */
void imx_refresh_cycle_time(void)
{
    imx_time_get_time(&g_cached_time);
    g_time_valid = true;
}

// In main loop (do_everything.c):
while (running) {
    imx_refresh_cycle_time();  // Single syscall per iteration

    // All subsystems use imx_get_cycle_time() instead of imx_time_get_time()
    process_network(imx_get_cycle_time());
    process_can();
    // ...
}
```

**Benefit:** Reduces clock_gettime from ~1000/sec to ~50/sec (main loop rate)
**Effort:** Medium (3-4 hours to update all call sites)
**Risk:** Low - time accuracy of ~20ms is acceptable for most operations

#### Fix 2.2: Create Time-Aware API Variants (MEDIUM PRIORITY)
For functions that need current time, pass it as a parameter instead of fetching.

**Current pattern:**
```c
void process_can_message(can_msg_t *msg)
{
    imx_time_t current_time;
    imx_time_get_time(&current_time);  // Syscall!

    if (imx_time_difference(current_time, msg->timestamp) > TIMEOUT) {
        // ...
    }
}
```

**Improved pattern:**
```c
void process_can_message(can_msg_t *msg, imx_time_t current_time)
{
    // No syscall - time passed from caller
    if (imx_time_difference(current_time, msg->timestamp) > TIMEOUT) {
        // ...
    }
}
```

**Files to update:**
- `can_server.c`: Pass time to `can_server_process()`
- `can_utils.c`: Pass time to utility functions
- `process_network.c`: Already receives time in some functions

**Benefit:** Eliminates redundant time fetches
**Effort:** Medium (2-3 hours)
**Risk:** Low

#### Fix 2.3: Use Relative Timeouts Where Possible (LOW PRIORITY)
For operations that just need "has X milliseconds passed", use relative counters.

```c
// Instead of:
imx_time_get_time(&current_time);
if (imx_time_difference(current_time, start_time) > 1000) { ... }

// Use:
static uint32_t loop_counter = 0;
#define MS_PER_LOOP 20  // Main loop runs at 50Hz

if ((loop_counter - start_counter) * MS_PER_LOOP > 1000) { ... }
```

**Benefit:** Eliminates time syscalls for simple timeout checks
**Effort:** Low (1-2 hours)
**Risk:** Medium - requires accurate loop timing knowledge

---

## Issue 3: Repeated Sysfs File I/O for Carrier State

### Current Behavior
The `has_carrier()` function opens, reads, and closes `/sys/class/net/*/carrier` on every check, with up to 3 retries.

**Code location:** `process_network.c:2836-2883`

**Current implementation:**
```c
static bool has_carrier(const char *ifname)
{
    int retries = 3;
    while (retries > 0) {
        fp = fopen(path, "r");      // Open file
        fscanf(fp, "%d", &carrier); // Read value
        fclose(fp);                 // Close file
        retries--;
    }
}
```

**strace evidence:**
```
open("/sys/class/net/wlan0/carrier"): Multiple times per second
```

### Root Cause
- File is reopened on every carrier check
- Retries add additional file operations
- No caching of carrier state

### Recommended Fixes

#### Fix 3.1: Keep Carrier File Descriptor Open (HIGH PRIORITY)
Open the sysfs file once and keep it open for repeated reads.

**Implementation:**
```c
// Persistent file descriptors for each interface
static struct {
    int fd;
    bool initialized;
} carrier_fds[3] = {{-1, false}, {-1, false}, {-1, false}};

static bool has_carrier_optimized(iface_t iface)
{
    static const char *carrier_paths[] = {
        "/sys/class/net/eth0/carrier",
        "/sys/class/net/wlan0/carrier",
        NULL  // PPP has no carrier file
    };

    if (iface == IFACE_PPP) return true;  // PPP has no carrier

    // Open file descriptor if not already open
    if (!carrier_fds[iface].initialized) {
        carrier_fds[iface].fd = open(carrier_paths[iface], O_RDONLY);
        carrier_fds[iface].initialized = true;
    }

    if (carrier_fds[iface].fd < 0) return false;

    // Seek to beginning and read
    lseek(carrier_fds[iface].fd, 0, SEEK_SET);
    char buf[4] = {0};
    read(carrier_fds[iface].fd, buf, 1);

    return buf[0] == '1';
}
```

**Benefit:** Eliminates open/close overhead (50-70% reduction)
**Effort:** Low (1 hour)
**Risk:** Low - sysfs files are stable

#### Fix 3.2: Use Netlink for Carrier State Notifications (MEDIUM PRIORITY)
Subscribe to netlink events instead of polling.

**Implementation:**
```c
#include <linux/rtnetlink.h>
#include <linux/if.h>

// Subscribe to link state changes
int setup_carrier_notifications(void)
{
    int sock = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    struct sockaddr_nl addr = {
        .nl_family = AF_NETLINK,
        .nl_groups = RTMGRP_LINK  // Subscribe to link changes
    };
    bind(sock, (struct sockaddr *)&addr, sizeof(addr));
    return sock;
}

// Process link change events (non-blocking)
void process_carrier_events(int sock)
{
    struct nlmsghdr *nlh;
    struct ifinfomsg *ifi;
    char buf[4096];

    int len = recv(sock, buf, sizeof(buf), MSG_DONTWAIT);
    if (len <= 0) return;

    nlh = (struct nlmsghdr *)buf;
    ifi = NLMSG_DATA(nlh);

    if (nlh->nlmsg_type == RTM_NEWLINK) {
        bool carrier_up = (ifi->ifi_flags & IFF_RUNNING) != 0;
        // Update cached carrier state
    }
}
```

**Benefit:** Event-driven instead of polling
**Effort:** High (4-6 hours)
**Risk:** Medium - requires careful integration

#### Fix 3.3: Cache Carrier State with TTL (MEDIUM PRIORITY)
Cache the carrier state and only refresh periodically.

**Implementation:**
```c
typedef struct {
    bool carrier_up;
    imx_time_t last_check;
    bool valid;
} carrier_cache_t;

static carrier_cache_t carrier_cache[3] = {0};
#define CARRIER_CACHE_TTL_MS 1000  // Check at most once per second

static bool has_carrier_cached(iface_t iface)
{
    imx_time_t now = imx_get_cycle_time();

    if (carrier_cache[iface].valid &&
        imx_time_difference(now, carrier_cache[iface].last_check) < CARRIER_CACHE_TTL_MS) {
        return carrier_cache[iface].carrier_up;
    }

    // Cache expired - refresh
    carrier_cache[iface].carrier_up = has_carrier_optimized(iface);
    carrier_cache[iface].last_check = now;
    carrier_cache[iface].valid = true;

    return carrier_cache[iface].carrier_up;
}
```

**Benefit:** Reduces carrier checks by 50-90%
**Effort:** Low (1 hour)
**Risk:** Low - 1-second latency acceptable for carrier detection

---

## Implementation Priority Matrix

### Phase 1: Quick Wins (Week 1)
| Task | Effort | Impact | Risk |
|------|--------|--------|------|
| 2.1 Per-cycle time caching | 3-4h | High | Low |
| 3.1 Keep carrier FD open | 1h | Medium | Low |
| 3.3 Cache carrier state | 1h | Medium | Low |

**Expected improvement:** 50-60% reduction in syscall overhead

### Phase 2: Medium Effort (Week 2)
| Task | Effort | Impact | Risk |
|------|--------|--------|------|
| 1.2 Cache route information | 1h | Medium | Low |
| 2.2 Time-aware API variants | 2-3h | Medium | Low |

**Expected improvement:** Additional 20-30% reduction

### Phase 3: Larger Changes (Week 3-4)
| Task | Effort | Impact | Risk |
|------|--------|--------|------|
| 1.1 Netlink for route queries | 2-3h | High | Low |
| 3.2 Netlink for carrier events | 4-6h | Medium | Medium |

**Expected improvement:** Additional 10-20% reduction

---

## Testing Strategy

### Performance Baseline
Before implementing fixes, establish baseline:
```bash
# Run strace profiling
./scripts/profile_fc1.sh --duration 60

# Record metrics:
# - clock_gettime64 call count
# - wait4 time (process spawning)
# - open/close count for sysfs files
```

### Validation After Each Fix
After each fix, re-run profiling and compare:
```bash
# Compare syscall counts
diff strace_summary_before.txt strace_summary_after.txt
```

### Regression Testing
Ensure functionality isn't broken:
1. Network failover works correctly
2. CAN bus processing continues normally
3. Interface detection responds within 2 seconds

---

## Appendix A: Current Call Sites

### imx_time_get_time() Call Sites (Top Files)

| File | Line | Context |
|------|------|---------|
| process_network.c | 796 | cooldown check |
| process_network.c | 1935 | state machine |
| process_network.c | 2572 | dhcp renewal |
| process_network.c | 3076 | interface check |
| process_network.c | 4106 | wifi reassoc |
| process_network.c | 4354 | main processing |
| can_server.c | 566 | client timeout |
| can_server.c | 611 | activity tracking |
| can_server.c | 643 | activity tracking |
| can_file_send.c | 1066-1446 | file transfer timing |

### Route Query Call Sites

| File | Line | Command |
|------|------|---------|
| process_network.c | 3333 | `system("ip route show \| head -5")` |
| process_network.c | 3483 | `system("ip route show \| head -10")` |

---

## Appendix B: Netlink API Reference

### Route Query via Netlink
```c
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <net/if.h>

// Message types:
// RTM_GETROUTE - Query routes
// RTM_NEWROUTE - Route added
// RTM_DELROUTE - Route deleted

// Multicast groups:
// RTMGRP_LINK - Link state changes
// RTMGRP_IPV4_ROUTE - IPv4 route changes
```

### Carrier State via Netlink
```c
// IFF_RUNNING flag indicates carrier presence
struct ifinfomsg {
    unsigned char  ifi_family;
    unsigned char  __ifi_pad;
    unsigned short ifi_type;
    int           ifi_index;
    unsigned      ifi_flags;   // Check IFF_RUNNING
    unsigned      ifi_change;
};
```

---

*Document Version: 1.0*
*Last Updated: 2025-12-22*
