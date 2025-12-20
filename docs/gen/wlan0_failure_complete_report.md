# WLAN0 Failure Analysis - Complete Report

**Date:** 2025-12-17
**Document Version:** 1.1
**Status:** ✅ TESTED AND VERIFIED - Bug Resolved
**Author:** Claude Code Analysis
**Reviewer:** Greg
**Completed:** 2025-12-18

---

## Executive Summary

The WLAN0 failure issue manifested as WiFi connectivity loss approximately every hour. Investigation revealed two distinct but related problems:

1. **Unnecessary WiFi Reconfiguration** - The hourly WiFi list cloud check triggers `wpa_cli reconfigure` even when no changes exist, causing WiFi disconnection.

2. **DHCP Race Condition** (Critical) - When WiFi reconnects, two udhcpc processes can be spawned simultaneously, preventing either from completing DHCP and leaving the interface without an IP address.

Both issues have been fixed and verified to compile successfully.

---

## Problem Timeline

### Initial Observation
- WiFi (wlan0) disconnects approximately every hour
- Device fails to regain connectivity after disconnection
- Log analysis showed disconnections correlating with WiFi list cloud checks

### Investigation Phases
1. Log file analysis (`logs/net_fail1.txt`)
2. Code review of WiFi list state machine
3. Code review of network manager
4. Live device debugging (revealed DHCP race condition)

---

## Issue 1: Unnecessary WiFi Reconfiguration

### Evidence from Log (logs/net_fail1.txt)

**WiFi Working Before Failure (Lines 1-26):**
```
[NET] wlan0: replies=3 avg_lat=74ms link_up=true
[NETMGR] State: NET_ONLINE_CHECK_RESULTS | Interface test complete - score:10, latency: 74
```

**WiFi List Info Check Shows No Changes (Lines 250-252):**
```
WIFI_LIST Request: /api/v1/wifi/info?sn=0248195461
Received 25 bytes response.
wifi_info.count = 0 (was 0), checksum = '' (was '')
```
The count is 0 and unchanged, checksum is empty and unchanged - NO new WiFi networks to configure.

**Configuration Update Triggered Anyway (Lines 277-282):**
```
[WiFi list - Changing state from: 7 to 8]
Writing wifi network iMatrix-IoT to config
Selected interface 'wlan0'
OK
[WiFi list - Changing state from: 8 to 10]
WiFi configuration updated successfully.
```

**wpa_supplicant Disconnects (Lines 381-388):**
```
[18222.210069] wlan0: deauthenticating from 26:18:d6:22:21:2b by local choice (Reason: 3=DEAUTH_LEAVING)
```
The "by local choice" with Reason 3 (DEAUTH_LEAVING) indicates this was triggered internally by wpa_supplicant reconfiguration.

**Connection Duration:**
```
[NETMGR-WIFI0] State: NET_ONLINE_CHECK_RESULTS | Link was up for 3587501 ms
```
3587501 ms = 59.8 minutes, matching the hourly WiFi list check interval (`WIFI_LIST_REQUEST_PERIODIC_TIMEOUT_MS = 60 * 60 * 1000`).

### Root Cause Analysis

**Code Flow:**

1. **Hourly Trigger** (`process_wifi_list.c:1100`):
   ```c
   if (imx_is_later(current_time, wifi_list_request.time + WIFI_LIST_REQUEST_PERIODIC_TIMEOUT_MS))
       wifi_list_state = WIFI_LIST_STATE_REQUEST_INIT;
   ```

2. **Cloud Check** - Even when count/checksum unchanged, still proceeds to download state

3. **Unconditional Config Update** (`process_wifi_list.c:1083-1086`):
   ```c
   case WIFI_LIST_STATE_WIFI_LIST_DOWNLOAD_COMPLETED:
       wifi_list_cleanup();
       wifi_list_save_status();
       wifi_list_state = WIFI_LIST_STATE_UPDATE_WIFI_CONFIG;  // Always goes here!
       break;
   ```

4. **Always Reconfigures** (`wifi_connect.c:459`):
   ```c
   system("wpa_cli reconfigure");
   ```

### Fixes Implemented

#### Fix A: Track Changes in process_wifi_list.c

Added flag to track if actual changes occurred:

```c
static bool wifi_list_config_changed = false;  /**< Track if WiFi config needs updating */
```

Modified `wifi_list_parse_info_json()` to skip to IDLE when no changes:
```c
if ((count == wifi_list_status.count) &&
    (strcmp(checksum, wifi_list_status.checksum) == 0))
{
    int storage_count = btstack_linked_list_count(&wifi_list);
    if (storage_count == count)
    {
        wifi_list_config_changed = false;
        wifi_list_state = WIFI_LIST_STATE_IDLE;
        return true;
    }
}
wifi_list_config_changed = true;
```

Modified download complete state to check flag:
```c
case WIFI_LIST_STATE_WIFI_LIST_DOWNLOAD_COMPLETED:
    wifi_list_cleanup();
    wifi_list_save_status();
    if (wifi_list_config_changed) {
        wifi_list_state = WIFI_LIST_STATE_UPDATE_WIFI_CONFIG;
    } else {
        wifi_list_state = WIFI_LIST_STATE_IDLE;
    }
    break;
```

#### Fix B: Configuration Comparison in wifi_connect.c

Added helper functions to compare configurations before writing:

```c
static bool generate_wifi_config_to_buffer(char **buffer, size_t *size);
static bool read_existing_wifi_config(char **buffer, size_t *size);
```

Modified `set_wifi_config()` to:
1. Generate new config to memory buffer
2. Read existing config
3. Compare - if identical, skip write and reconfigure
4. Only write and reconfigure if different

#### Fix C: Smart Reconfigure in wifi_connect.c

Added helper to check current connection:
```c
static bool is_connected_to_configured_network(void);
```

Skip reconfigure if already connected to a configured network, even when config changes.

---

## Issue 2: DHCP Race Condition (Critical)

### Discovery

During live device debugging, it was observed that even when wpa_supplicant successfully reconnected to the AP (`wpa_state=COMPLETED`), the interface had no IP address.

### Evidence from Live Device

```bash
# Two udhcpc processes running for wlan0
# ps | grep udhcpc
 1004 root       548 S    udhcpc -R -n -x hostname:iMatrix:FC-1:0248195461 -p /var/run/udhcpc.wlan0.pid -i wlan0
22633 root      1000 S    udhcpc -i wlan0 -b -q -p /var/run/udhcpc.wlan0.pid

# wpa_supplicant is connected but no IP
# wpa_cli status | grep wpa_state
wpa_state=COMPLETED

# PID file missing (both processes trying to write to same file)
# cat /var/run/udhcpc.wlan0.pid
(empty)

# dmesg shows martian source packets (broadcast rejected - no IP on interface)
IPv4: martian source 255.255.255.255 from 10.2.0.1, on dev wlan0
```

**Manual Recovery Confirmed Diagnosis:**
```bash
# Kill both processes
kill 1004 22633

# Start fresh udhcpc
udhcpc -R -n -x hostname:iMatrix:FC-1:0248195461 -p /var/run/udhcpc.wlan0.pid -i wlan0

# Result: Immediate success
udhcpc: lease of 10.2.0.192 obtained, lease time 86400
```

### Root Cause Analysis

Two independent systems can spawn udhcpc for wlan0:

1. **ifplugd (System Daemon)**
   - Monitors network interface carrier state
   - When carrier comes UP on wlan0, automatically starts udhcpc
   - This is standard Linux behavior configured on the device

2. **Network Manager WiFi Recovery** (`process_network.c:7479`)
   - Monitors for stuck WiFi state (active but link_up=NO)
   - After 30 second timeout, runs recovery sequence
   - Recovery step 4 starts udhcpc unconditionally

**Race Condition Sequence:**
1. wpa_cli reconfigure triggers WiFi disconnect
2. ifplugd sees carrier DOWN (may kill udhcpc per ifplugd_fix.sh)
3. wpa_supplicant reconnects to AP
4. ifplugd sees carrier UP → starts udhcpc
5. Network manager recovery timer may still fire → starts second udhcpc
6. Two DHCP clients race for UDP port 68
7. Neither completes DHCP handshake
8. Interface has no IP address

### Fix Implemented

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

In the `WIFI_RECOVERY_START_DHCP` state, added check using existing `is_wlan0_dhcp_client_running()` function:

```c
case WIFI_RECOVERY_START_DHCP:
    /*
     * Check if udhcpc is already running for wlan0 before starting another.
     * This prevents a race condition where both ifplugd (system daemon) and
     * network manager recovery can spawn udhcpc when WiFi reconnects.
     * Having two DHCP clients racing causes neither to complete properly.
     */
    if (is_wlan0_dhcp_client_running())
    {
        NETMGR_LOG_WIFI0(ctx, "Recovery step 4: udhcpc already running for wlan0, skipping start");
    }
    else
    {
        NETMGR_LOG_WIFI0(ctx, "Recovery step 4: Starting udhcpc for wlan0");
        system("udhcpc -i wlan0 -b -q -p /var/run/udhcpc.wlan0.pid >/dev/null 2>&1 &");
    }
    recovery_state = WIFI_RECOVERY_DONE;
    break;
```

---

## Files Modified

| File | Changes | Lines Modified |
|------|---------|----------------|
| `iMatrix/wifi/process_wifi_list.c` | Add `wifi_list_config_changed` flag, skip config update when no changes | ~20 lines |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/wifi_connect.c` | Add config comparison functions, smart reconfigure logic | ~100 lines |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Check if udhcpc running before starting in WiFi recovery | ~15 lines |

---

## Build Verification

All changes compile successfully with no errors or warnings:

```
[ 43%] Building C object CMakeFiles/iMatrix.dir/CMakeFiles/imatrix.dir/IMX_Platform/LINUX_Platform/networking/process_network.c.o
[ 50%] Linking C static library libimatrix.a
[ 85%] Built target imatrix
[ 85%] Linking C executable FC-1
[100%] Built target FC-1
```

---

## Testing Recommendations

### Phase 1: Basic Functionality
- [ ] Verify device boots and WiFi connects normally
- [ ] Verify device obtains IP address via DHCP
- [ ] Check that only one udhcpc process exists for wlan0

### Phase 2: Hourly Check Verification
- [ ] Wait for hourly WiFi list check
- [ ] Verify WiFi does NOT disconnect when no changes exist
- [ ] Check logs for "WiFi configuration unchanged, skipping reconfigure" message

### Phase 3: Configuration Change Test
- [ ] Add a new WiFi network via cloud
- [ ] Verify device downloads new config and reconfigures
- [ ] Verify device reconnects and obtains IP

### Phase 4: Recovery Test
- [ ] Manually trigger WiFi disconnect (e.g., disable AP temporarily)
- [ ] Verify recovery kicks in after 30 seconds
- [ ] Verify only one udhcpc process after recovery
- [ ] Verify IP is obtained

### Phase 5: Long-Running Stability
- [ ] Run device for 24+ hours
- [ ] Monitor for WiFi disconnections
- [ ] Verify no duplicate udhcpc processes accumulate
- [ ] Check memory usage remains stable

---

## Risk Assessment

### Low Risk
- Adding change tracking flag
- Adding logging statements
- Configuration comparison logic
- udhcpc running check

### Medium Risk
- Changing WiFi list state machine flow
- Memory stream operations in config comparison

### Mitigations Applied
1. Used existing `is_wlan0_dhcp_client_running()` function (proven code)
2. Added comprehensive logging for troubleshooting
3. Implemented fixes incrementally
4. All changes compile without warnings

---

## Future Considerations

1. **Grace Period After Reconfigure**: When a genuine configuration change occurs, consider adding a brief grace period in the network manager to allow wpa_supplicant time to reconnect.

2. **Configurable WiFi List Check Interval**: Currently fixed at 1 hour. Making this configurable could reduce unnecessary cloud requests.

3. **Network Manager Notification**: Consider a mechanism to notify the network manager that a wpa_supplicant reconfigure is about to happen, so it can temporarily suspend connectivity monitoring.

4. **ifplugd Coordination**: The current fix is defensive (check before spawning). A more robust solution might involve disabling ifplugd for wlan0 entirely and letting the network manager handle all DHCP client management.

---

## Summary

Two bugs were identified and fixed:

| Issue | Impact | Fix |
|-------|--------|-----|
| Unnecessary reconfigure | Hourly WiFi disconnect | Track changes, compare config before writing |
| DHCP race condition | No IP after reconnect | Check if udhcpc running before starting |

The fixes are complementary:
- Fix 1 prevents unnecessary disconnections
- Fix 2 ensures proper IP acquisition when disconnections do occur

---

## Verification Results

**Testing Completed:** 2025-12-18
**Result:** ✅ Bug Resolved

The fix was deployed to a live device and verified:
- WiFi maintains connection during hourly WiFi list checks
- No duplicate udhcpc processes after WiFi reconnection
- Device properly obtains IP address after any disconnection event

---

**Report Generated:** 2025-12-17
**Report Updated:** 2025-12-18
**Build Verified:** Yes
**Device Tested:** Yes
**Bug Status:** RESOLVED
