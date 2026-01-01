# Network Manager Analysis - Handler Investigation

**Date:** 2026-01-01
**Time:** 19:00 UTC
**Analysis By:** Claude Code

## Executive Summary

The FC-1 system has **NO INTERNET CONNECTIVITY** due to a network manager configuration issue. The system is stuck in "Wi-Fi Setup mode" with no viable Internet interface.

## Root Cause Analysis

### 1. Network Interface Status

| Interface | Status | IP Address | Role | Internet |
|-----------|--------|------------|------|----------|
| **eth0** | UP, CARRIER | 192.168.7.1/24 | DHCP Server | ❌ Excluded |
| **wlan0** | DOWN, NO-CARRIER | None | Client (failed) | ❌ No connection |
| **ppp0** | Not present | None | Not started | ❌ Not available |

### 2. Why No Internet Connection

Based on the Network Manager Architecture (Section 3.3):

> **DHCP Server Interface Exclusion:** Interfaces operating as DHCP servers are **automatically excluded** from Internet gateway selection.

The system has:
1. **eth0 in DHCP server mode** (192.168.7.1) - serving local clients via USB
2. **eth0 is EXCLUDED** from Internet routing per network manager design
3. **wlan0 has NO-CARRIER** - not associated with any WiFi network
4. **No PPP/cellular fallback** - ppp0 interface doesn't exist

### 3. The Zombie DHCP Process Problem

**Found:** 19-22 `udhcpc` processes for wlan0
```
PID: 575, 940, 5309, 6027, 11171, 11927, 12252, 12633, 13414, 13578, 14093, 
     27123, 27925, 29406, 30288, 32369, 32536, 32691, etc.
```

**Cause:** Network manager repeatedly attempting to get DHCP lease on wlan0:
- wlan0 has NO-CARRIER (not connected to WiFi)
- Each retry spawns new udhcpc process
- Processes accumulate because they can't get IP (no WiFi connection)
- Classic symptom of network manager stuck in retry loop

### 4. Process Restart Sequence

**Timeline:**
1. System running normally (PID 19054)
2. Network connectivity lost (wlan0 down, eth0 in server mode)
3. IMX_UPLOAD attempts fail → timeouts
4. Handler potentially blocked in `imatrix_upload()` waiting for network
5. Watchdog or manual intervention kills process
6. New process starts (PID 6538)
7. Still no connectivity → cycle continues

### 5. Why System is in "Wi-Fi Setup Mode"

From startup log:
```
system_init.c:1089 - force AP setup
Initialization Complete, Thing will run in Wi-FI Setup mode
```

The system detected no viable Internet connection and entered WiFi Setup mode where:
- eth0 becomes DHCP server (Access Point mode)
- User expected to connect to configure WiFi
- But this leaves NO Internet connectivity

## Network Manager State Machine Analysis

Based on the architecture document, the network manager likely stuck in this cycle:

```
NET_SELECT_INTERFACE
    ↓
[Test eth0] → DHCP server mode → EXCLUDED
    ↓
[Test wlan0] → NO-CARRIER → FAIL → Spawn udhcpc → Cooldown
    ↓
[Test ppp0] → Not available
    ↓
NET_SELECT_INTERFACE (repeat)
```

### Cooldown and Retry Logic

Per Section 6.2-6.3 of Network Manager Architecture:
- **wlan0 cooldown:** 30 seconds default
- **Max retries:** 3 attempts before blacklisting
- **But:** Can't blacklist when there's no BSSID (not connected)
- **Result:** Infinite retry loop with cooldowns

## Impact on Handler

### The IMX_UPLOAD Timeout Issue

The "IMX_UPLOAD: Ignoring response since timeout waiting for response" messages indicate:

1. **Upload attempts to coap-dev.imatrixsys.com:3000**
2. **No route to host** (errno 113) - no Internet connection
3. **Handler waiting for response** that will never come
4. **Potential blocking** in upload thread/function

### Handler Stuck Hypothesis

While no explicit "Handler stuck" warning was logged, the evidence suggests:
- Handler may be blocked in network I/O
- IMX_UPLOAD timeouts consuming handler time
- Eventually triggers watchdog or manual restart
- New process starts but same network issue persists

## Recommendations

### Immediate Actions

1. **Restore WiFi Connectivity:**
   ```bash
   # Check WiFi status
   wpa_cli -i wlan0 status
   
   # Scan for networks
   wpa_cli -i wlan0 scan
   wpa_cli -i wlan0 scan_results
   
   # Connect to network
   wpa_cli -i wlan0 add_network
   wpa_cli -i wlan0 set_network 0 ssid '"YourSSID"'
   wpa_cli -i wlan0 set_network 0 psk '"YourPassword"'
   wpa_cli -i wlan0 enable_network 0
   ```

2. **Or Switch eth0 to Client Mode:**
   ```bash
   # Kill DHCP server on eth0
   killall udhcpd
   
   # Request DHCP client on eth0
   udhcpc -i eth0
   ```

3. **Or Enable Cellular Backup:**
   ```bash
   # Start PPP daemon
   sv up pppd
   ```

### Long-term Fixes

1. **Network Manager Configuration:**
   - Ensure at least one interface configured for Internet access
   - Prevent system from entering setup mode when configured
   - Add timeout/retry limits for DHCP client spawning

2. **Handler Resilience:**
   - Add timeouts to IMX_UPLOAD operations
   - Ensure handler doesn't block on network I/O
   - Implement async upload with proper timeout handling

3. **Process Monitoring:**
   - Add network connectivity check before upload attempts
   - Implement backoff when connectivity lost
   - Prevent process restart loops

## Conclusion

The handler investigation revealed a **network configuration issue** rather than a handler code bug:
- System has NO Internet connectivity
- eth0 in DHCP server mode (excluded from routing)
- wlan0 not connected to any WiFi network
- Network manager spawning zombie DHCP processes
- IMX_UPLOAD failures are symptom, not cause

**The handler is likely not stuck** - it's just unable to upload data due to lack of Internet connectivity. The process restart was likely triggered by accumulated network failures or manual intervention.

---

*Investigation complete - network connectivity must be restored for normal operation*