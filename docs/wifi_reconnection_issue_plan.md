# WiFi Reconnection Failure Issue Analysis and Fix Plan

**Date**: 2025-12-09
**Issue Type**: Network Manager Bug
**Priority**: High
**Status**: Analysis Complete - Ready for Implementation

---

## Executive Summary

When WiFi disconnects (DEAUTH_LEAVING), the network manager fails to properly reconnect to WiFi even though:
1. The WiFi interface is marked as `active=YES`
2. WiFi scans find available APs (26-43 networks found)
3. The configured SSID is available

The root cause is that when `link_up=NO` but `active=YES`, the COMPUTE_BEST function skips the interface entirely, and the network manager doesn't trigger a proper reconnection sequence.

---

## Problem Analysis

### Evidence from Logs (net2.txt)

#### 1. Initial WiFi Working (lines 302-307)
```
[COMPUTE_BEST] wlan0: active=YES, link_up=YES, score=10, latency=41
[COMPUTE_BEST] Found GOOD link by priority: wlan0 (score=10, latency=41)
```

#### 2. WiFi Disconnects with DEAUTH_LEAVING (line 615)
```
[ 2264.279834] wlan0: deauthenticating from e2:63:da:91:33:80 by local choice (Reason: 3=DEAUTH_LEAVING)
```

#### 3. Interface Shows NO-CARRIER (line 620)
```
7: wlan0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DORMANT
```

#### 4. COMPUTE_BEST Skips wlan0 (lines 870-885)
```
[COMPUTE_BEST] wlan0: active=YES, link_up=NO, score=0, latency=0
[COMPUTE_BEST] Skipping wlan0: active=YES, link_up=NO, disabled=NO
[COMPUTE_BEST] Final result: NO_INTERFACE_FOUND - all interfaces down or inactive
```

#### 5. WiFi Scans Find Networks But Don't Reconnect (lines 3267+)
```
[NETMGR-WIFI0] WiFi scan found 26 APs, triggering reconnection
[NETMGR-WIFI0] WiFi scan found 36 APs, triggering reconnection
... (repeats many times)
```

### Root Cause

The network manager has a state inconsistency:
- `active=YES` means "we want to use this interface"
- `link_up=NO` means "interface has no physical connection"

When WiFi disconnects:
1. The interface remains marked as `active=YES`
2. But `link_up` becomes `NO`
3. COMPUTE_BEST skips interfaces with `link_up=NO`
4. WiFi scans run but reconnection never succeeds
5. No mechanism to reset the WiFi association properly

### Why WiFi Reconnection Fails

Looking at the logs, the system:
1. Detects WiFi is down (`link_up=NO`)
2. Runs WiFi scans (finding APs)
3. Logs "triggering reconnection"
4. But the reconnection never actually works

The WiFi likely needs a full reset sequence:
1. Kill existing wpa_supplicant associations
2. Re-run wpa_supplicant or `wpa_cli reconfigure`
3. Request DHCP lease
4. Verify link comes up

---

## Proposed Solution

### Fix 1: Enhanced WiFi Link Recovery in process_network.c

When WiFi is `active=YES` but `link_up=NO` for extended period, trigger a full recovery:

1. **Detect Stuck State**: If wlan0 is `active=YES`, `link_up=NO` for > 30 seconds
2. **Kill DHCP Client**: `killall udhcpc` for wlan0
3. **Reset WiFi Association**: `wpa_cli -i wlan0 disconnect && wpa_cli -i wlan0 reconnect`
4. **Restart DHCP**: Start udhcpc for wlan0
5. **Monitor**: Give 15 seconds for link to come up
6. **Fallback**: If still down after 3 attempts, mark interface as failed temporarily

### Implementation Location

File: `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

Add to `process_network()` function, in the NET_ONLINE state when checking interfaces.

### Pseudocode

```c
// In process_network.c, add WiFi recovery logic
static imx_time_t wifi_linkdown_start = 0;
static int wifi_recovery_attempts = 0;
#define WIFI_LINKDOWN_TIMEOUT 30000  // 30 seconds
#define WIFI_MAX_RECOVERY_ATTEMPTS 3

// When processing wlan0 interface:
if (interfaces[WLAN0].active && !interfaces[WLAN0].link_up) {
    if (wifi_linkdown_start == 0) {
        wifi_linkdown_start = current_time;
        PRINTF("[NETMGR-WIFI0] WiFi link down detected, starting recovery timer\n");
    }
    else if (imx_is_later(current_time, wifi_linkdown_start + WIFI_LINKDOWN_TIMEOUT)) {
        if (wifi_recovery_attempts < WIFI_MAX_RECOVERY_ATTEMPTS) {
            PRINTF("[NETMGR-WIFI0] WiFi linkdown timeout, attempting recovery %d/%d\n",
                   wifi_recovery_attempts + 1, WIFI_MAX_RECOVERY_ATTEMPTS);

            // Kill DHCP client
            system("killall -9 udhcpc 2>/dev/null");
            usleep(100000);  // 100ms

            // Reset WiFi association
            system("wpa_cli -i wlan0 disconnect");
            usleep(500000);  // 500ms
            system("wpa_cli -i wlan0 reconnect");

            // Restart DHCP
            system("udhcpc -i wlan0 -b -q &");

            wifi_recovery_attempts++;
            wifi_linkdown_start = current_time;  // Reset timer
        }
        else {
            PRINTF("[NETMGR-WIFI0] WiFi recovery failed after %d attempts\n",
                   WIFI_MAX_RECOVERY_ATTEMPTS);
            // Mark WiFi as temporarily disabled
            interfaces[WLAN0].disabled_until = current_time + 300000; // 5 min cooldown
            wifi_recovery_attempts = 0;
            wifi_linkdown_start = 0;
        }
    }
}
else if (interfaces[WLAN0].active && interfaces[WLAN0].link_up) {
    // Link recovered, reset counters
    if (wifi_linkdown_start != 0) {
        PRINTF("[NETMGR-WIFI0] WiFi link recovered\n");
        wifi_linkdown_start = 0;
        wifi_recovery_attempts = 0;
    }
}
```

---

## Implementation Todo List

### Phase 1: Analysis (Completed)

- [x] Review net2.txt logs for WiFi behavior
- [x] Identify DEAUTH_LEAVING trigger
- [x] Track COMPUTE_BEST interface selection
- [x] Verify WiFi scans are finding APs
- [x] Document root cause

### Phase 2: Implementation

- [ ] **2.1** Add wifi_linkdown_start and wifi_recovery_attempts static variables
- [ ] **2.2** Add linkdown detection in NET_ONLINE state WiFi processing
- [ ] **2.3** Implement 30-second timeout check
- [ ] **2.4** Add recovery sequence (kill udhcpc, wpa_cli disconnect/reconnect, restart udhcpc)
- [ ] **2.5** Add recovery attempt counter with max 3 attempts
- [ ] **2.6** Add 5-minute cooldown after max failures
- [ ] **2.7** Add link recovery detection to reset counters
- [ ] **2.8** Add comprehensive logging

### Phase 3: Testing

- [ ] **3.1** Test WiFi disconnect recovery (manually disconnect)
- [ ] **3.2** Test recovery during cellular scan
- [ ] **3.3** Test max retry behavior
- [ ] **3.4** Test cooldown period
- [ ] **3.5** Verify normal WiFi operation unaffected

---

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Add WiFi recovery logic |

---

## Risk Assessment

### Low Risk
- Adding static variables for tracking
- Adding logging statements

### Medium Risk
- Calling system() for wpa_cli commands
- Killing udhcpc process

### Mitigations
1. Use non-blocking system calls where possible
2. Add timeouts to prevent stuck states
3. Include comprehensive logging for debugging
4. Implement cooldown to prevent infinite recovery loops

---

## Alternative Approaches Considered

### Option A: Reset via wpa_supplicant restart
- Pro: Clean slate approach
- Con: Would lose all WiFi configuration temporarily

### Option B: Implement in wifi_man.c
- Pro: WiFi-specific code location
- Con: Requires cross-module coordination with process_network.c

### Option C: Mark interface as inactive on linkdown (Selected approach - integrated)
- Pro: Simple, works with existing COMPUTE_BEST logic
- Con: May delay reconnection if we're too aggressive

**Selected**: Hybrid approach - use recovery sequence first, then fallback to cooldown

---

**Review Status**: IMPLEMENTED - 2025-12-09

## Implementation Details

### Changes Made to process_network.c

1. **Added forward declaration** (line 462):
   ```c
   static void detect_and_recover_wifi_linkdown(netmgr_ctx_t *ctx, imx_time_t current_time);
   ```

2. **Added function implementation** (lines 7275-7394):
   - `detect_and_recover_wifi_linkdown()` monitors WiFi state
   - Detects when `active=YES` but `link_up=NO` for 30 seconds
   - Triggers recovery sequence:
     1. Kill existing udhcpc for wlan0 (`pkill -f 'udhcpc.*wlan0'`)
     2. Disconnect WiFi (`wpa_cli -i wlan0 disconnect`)
     3. Reconnect WiFi (`wpa_cli -i wlan0 reconnect`)
     4. Restart DHCP client (`udhcpc -i wlan0 -b -q`)
   - Limits to 3 recovery attempts before 5-minute cooldown
   - Resets counters when link recovers

3. **Added function call in main loop** (line 4439):
   ```c
   detect_and_recover_wifi_linkdown(ctx, current_time);
   ```

### Build Status
- Compiled successfully on 2025-12-09
- No warnings or errors
