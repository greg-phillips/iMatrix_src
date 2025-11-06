# PPPD Routing Conflict Analysis

**Issue:** wlan0 ping tests fail when ppp0 becomes active, even though physical link is good
**Root Cause:** handle_pppd_route_conflict() modifies routing table DURING active ping tests
**Log File:** logs/routing5.txt, lines 662-729

---

## Problem Timeline (from routing5.txt)

### Step 1: wlan0 Ping Test Starts (Line 662-665)
```
[00:00:39.270] [NET: wlan0] execute_ping: Starting ping to IP: 34.94.71.128
[00:00:39.270] [NET: wlan0] execute_ping: Executing command: ping -n -I wlan0 -c 3 -W 1 -s 56 34.94.71.128 2>&1
[00:00:39.277] [NET: wlan0] execute_ping: Ping command started (PID ~1075), reading output...
[00:00:39.302] [NET: wlan0] execute_ping: Raw output: PING 34.94.71.128 (34.94.71.128): 56 data bytes
```
**Ping is running** - waiting for replies

### Step 2: Route Manipulation Happens DURING Ping (Lines 667-714)
```
[00:00:39.851] [NET] Verified default route exists for wlan0: default via 10.2.0.1 dev wlan0 linkdown ← PROBLEM!
[00:00:39.886] [NET] Route is marked as linkdown for wlan0: default via 10.2.0.1 linkdown
[00:00:39.892] [NET] WARNING: Default route for wlan0 is marked as linkdown - unusable

...multiple attempts to fix the route...

[00:00:41.910] [NETMGR-PPP0] State: NET_ONLINE_CHECK_RESULTS | PPPD route conflict detected: PPP0 has default route but wlan0 is active
[00:00:42.030] [NETMGR-PPP0] State: NET_ONLINE_CHECK_RESULTS | Adjusted PPP0 route metric to 200 (backup) to resolve conflict
[00:00:42.271] [NETMGR-PPP0] State: NET_ONLINE_CHECK_RESULTS | Re-established default route for wlan0 with primary metric after PPPD conflict
```
**Routes being deleted/re-added while ping is in flight!**

### Step 3: Ping Fails Due to Route Corruption (Line 716-729)
```
[00:00:42.312] [NET: wlan0] execute_ping: Raw output: --- 34.94.71.128 ping statistics ---
[00:00:42.312] [NET: wlan0] execute_ping: Raw output: 3 packets transmitted, 0 packets received, 100% packet loss
[00:00:42.312] [NET: wlan0] execute_ping: 100% packet loss detected
[00:00:42.314] [NET] wlan0: marked as failed - score=0 latency=0 link_up=false
```
**100% packet loss** - ping failed because routes were modified mid-test

---

## Root Cause Analysis

### The Problem

**handle_pppd_route_conflict()** (line 1076-1241 in process_network.c) is called from:
1. Line 4866: In NET_ONLINE state
2. Line 5147: In NET_ONLINE_CHECK_RESULTS state

**Critical Issue:** It's called in NET_ONLINE_CHECK_RESULTS **while a ping test is running on wlan0!**

The function:
1. Detects ppp0 has default route (line 1117)
2. Deletes ppp0's default route (line 1127)
3. Re-adds ppp0 route with metric 200 (line 1128)
4. Calls `set_default_via_iface(wlan0)` (line 1134) to re-establish wlan0 route

**But:** The wlan0 ping test is already running! Modifying routes mid-ping causes:
- Route marked as "linkdown" by kernel
- Ping packets can't route
- 100% packet loss
- wlan0 incorrectly marked as failed

### Shell Syntax Error

Lines 1125-1129 show problematic shell command:
```c
snprintf(cmd, sizeof(cmd),
         "ip route | grep '^default.*dev ppp0' | head -1 | "
         "if read line; then "
         "ip route del $line 2>/dev/null; "
         "ip route add $line metric 200 2>/dev/null; "
         "fi");
```

This causes: `sh: syntax error: unexpected end of file (expecting "fi")`

**Problem:** Piping to `if read line; then` doesn't work in `/bin/sh -c`. The subshell syntax is wrong.

---

## Why wlan0 Gets Marked "linkdown"

When you delete and re-add a route while the interface is in use:
1. Kernel temporarily has no route
2. Pending packets (from ping) are queued
3. Interface state becomes uncertain
4. Kernel marks route as "linkdown"
5. Even when route is re-added, linkdown flag persists

**The user is correct:** The physical link IS good, but route manipulation broke the routing table.

---

## Solution Design

### Immediate Fix: Don't Call handle_pppd_route_conflict() During Active Ping Tests

**Problem:** Function is called in NET_ONLINE_CHECK_RESULTS while ping is running

**Solution:** Only call it in NET_ONLINE state (not during tests), or add check for active tests

### Better Fix: Fix the Shell Command Syntax

Replace lines 1124-1129 with correct shell syntax:
```c
// WRONG (current):
snprintf(cmd, sizeof(cmd),
         "ip route | grep '^default.*dev ppp0' | head -1 | "
         "if read line; then "
         "ip route del $line 2>/dev/null; "
         "ip route add $line metric 200 2>/dev/null; "
         "fi");

// CORRECT:
snprintf(cmd, sizeof(cmd),
         "line=$(ip route | grep '^default.*dev ppp0' | head -1); "
         "if [ -n \"$line\" ]; then "
         "ip route del $line 2>/dev/null; "
         "ip route add $line metric 200 2>/dev/null; "
         "fi");
```

### Best Fix: Use More Targeted Route Commands

Instead of complex shell parsing:
```c
// Just adjust the metric directly
snprintf(cmd, sizeof(cmd),
         "ip route change default dev ppp0 metric 200 2>/dev/null || "
         "ip route replace default dev ppp0 metric 200 2>/dev/null");
system(cmd);
```

---

## Recommended Implementation

### Option 1: Delay Conflict Resolution Until Test Complete

**Where:** Lines 4866, 5147 (calls to handle_pppd_route_conflict)

**Change:**
```c
// In NET_ONLINE state
handle_pppd_route_conflict(ctx, current_time);  // OK - no tests running

// In NET_ONLINE_CHECK_RESULTS state
// DON'T call it - tests are running!
// Comment out line 5147
```

### Option 2: Check for Running Tests Before Manipulating Routes

**Where:** Line 1076 in handle_pppd_route_conflict()

**Add at function start:**
```c
static bool handle_pppd_route_conflict(netmgr_ctx_t *ctx, imx_time_t current_time)
{
    /* Don't manipulate routes during active ping tests */
    for (uint32_t i = 0; i < IFACE_COUNT; i++)
    {
        if (ctx->states[i].running)
        {
            NETMGR_LOG_PPP0(ctx, "Deferring PPPD conflict resolution - ping test running on %s", if_names[i]);
            return false;
        }
    }

    // Rest of function...
}
```

### Option 3: Fix Shell Command AND Add Test Check (RECOMMENDED)

Combine both fixes for maximum safety.

---

## Why This Wasn't Caught Earlier

This is a **race condition** that only happens when:
1. wlan0 is active and being tested
2. ppp0 comes up at the same time
3. handle_pppd_route_conflict() runs DURING the ping test
4. Route manipulation happens while packets are in flight

**Timing window:** Very narrow (during ~3 second ping test)

---

## Evidence from Log

**Lines 662-719 show the exact sequence:**
1. 39.270: wlan0 ping starts
2. 39.851: wlan0 route shows "linkdown" (route was manipulated)
3. 40.656-42.271: Multiple route fix attempts, conflict resolutions
4. 42.312: Ping completes with 100% packet loss
5. 42.314: wlan0 marked as failed

**Time between ping start and route corruption:** 581ms
**Time ping was running with bad routes:** ~3 seconds
**Result:** Total ping failure despite good physical link

---

## Questions for Implementation

1. **Should we defer PPPD conflict resolution until tests complete?**
2. **Should we fix the shell command syntax error?**
3. **Should we use ip route change/replace instead of del/add?**
4. **Should we add a flag to prevent route changes during tests?**

---

**Status:** ✅ ROOT CAUSE IDENTIFIED - AWAITING USER INPUT ON FIX APPROACH
