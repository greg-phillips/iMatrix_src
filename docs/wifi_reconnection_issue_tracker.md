# WiFi Reconnection Failure Issue Tracker

**Issue ID**: WIFI-001
**Created**: 2025-12-09
**Last Updated**: 2025-12-09
**Priority**: High
**Status**: IMPLEMENTED - Awaiting Testing

---

## Issue Summary

When WiFi disconnects (DEAUTH_LEAVING), the network manager fails to properly reconnect even though WiFi scans find available APs. The root cause is that when `link_up=NO` but `active=YES`, the COMPUTE_BEST function skips the interface entirely, and no recovery mechanism exists to re-establish the connection.

---

## Current Status

| Phase | Status | Date |
|-------|--------|------|
| Analysis | Complete | 2025-12-09 |
| Plan Created | Complete | 2025-12-09 |
| Implementation | Complete | 2025-12-09 |
| Code Review | Pending | - |
| Testing | Pending | - |
| Deployed | Pending | - |

---

## Root Cause

From log analysis (`logs/net2.txt`):

1. WiFi was working: `wlan0: active=YES, link_up=YES, score=10, latency=41`
2. WiFi disconnected: `wlan0: deauthenticating from e2:63:da:91:33:80 (Reason: 3=DEAUTH_LEAVING)`
3. Interface shows NO-CARRIER: `wlan0: <NO-CARRIER,BROADCAST,MULTICAST,UP>`
4. COMPUTE_BEST skips interface: `Skipping wlan0: active=YES, link_up=NO, disabled=NO`
5. WiFi scans find APs but reconnection never succeeds

---

## Implementation Details

### Files Modified

| File | Changes |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Added `detect_and_recover_wifi_linkdown()` function |

### Code Changes

1. **Forward declaration added** (line 462):
   ```c
   static void detect_and_recover_wifi_linkdown(netmgr_ctx_t *ctx, imx_time_t current_time);
   ```

2. **New function implementation** (lines 7275-7394):
   - Monitors for stuck state: `active=YES` but `link_up=NO`
   - 30-second timeout before triggering recovery
   - Recovery sequence:
     1. `pkill -f 'udhcpc.*wlan0'` - Kill DHCP client
     2. `wpa_cli -i wlan0 disconnect` - Disconnect from stale association
     3. `wpa_cli -i wlan0 reconnect` - Request reconnection
     4. `udhcpc -i wlan0 -b -q` - Restart DHCP client
   - Max 3 recovery attempts before 5-minute cooldown
   - Resets counters when link recovers

3. **Function call in main loop** (line 4439):
   ```c
   detect_and_recover_wifi_linkdown(ctx, current_time);
   ```

### Build Status

- **Build Date**: 2025-12-09
- **Result**: Success (no errors or warnings)

### CRITICAL FIX: Removed Blocking Code (2025-12-09)

The original implementation had **blocking `usleep()` calls** that caused system slowdown:
- `usleep(100000)` - 100ms blocking
- `usleep(500000)` - 500ms blocking

**Fixed** by converting to a non-blocking state machine with 8 states that uses timestamp comparisons instead of blocking delays. Each main loop iteration advances one state - no blocking.

---

## Expected Behavior After Fix

When WiFi link drops and stays down:

```
[NETMGR-WIFI0] WiFi link down detected (active=YES, link_up=NO), starting recovery timer
... 30 seconds later ...
[NETMGR-WIFI0] WiFi linkdown timeout (30000 ms), attempting recovery 1/3
[NETMGR-WIFI0] Recovery step 1: Killing udhcpc for wlan0
[NETMGR-WIFI0] Recovery step 2: wpa_cli disconnect
[NETMGR-WIFI0] Recovery step 3: wpa_cli reconnect
[NETMGR-WIFI0] Recovery step 4: Starting udhcpc for wlan0
```

On successful recovery:
```
[NETMGR-WIFI0] WiFi link recovered (attempts used: 1)
```

On max failures:
```
[NETMGR-WIFI0] WiFi recovery failed after 3 attempts, entering 300000 ms cooldown
```

---

## Testing Checklist

- [ ] Test WiFi disconnect recovery (manually disconnect AP)
- [ ] Test recovery during cellular scan
- [ ] Test max retry behavior (3 attempts)
- [ ] Test cooldown period (5 minutes)
- [ ] Verify normal WiFi operation unaffected
- [ ] Verify no rapid restart loops
- [ ] Check log messages are informative

---

## Progress History

| Date | Action | Details |
|------|--------|---------|
| 2025-12-09 | Issue identified | Analyzed net2.txt logs, found DEAUTH_LEAVING causing stuck state |
| 2025-12-09 | Plan created | Created wifi_reconnection_issue_plan.md |
| 2025-12-09 | Implementation complete | Added detect_and_recover_wifi_linkdown() to process_network.c |
| 2025-12-09 | Build verified | Code compiles without errors |

---

## Related Documents

- [WiFi Reconnection Issue Plan](wifi_reconnection_issue_plan.md)
- [Network Manager Architecture](Network_Manager_Architecture.md)

---

## Notes

- The fix uses the existing `wpa_cli` commands which are already used elsewhere in the codebase
- The 30-second timeout prevents rapid recovery attempts during brief disconnects
- The 5-minute cooldown after 3 failures prevents infinite loops if WiFi is truly unavailable
