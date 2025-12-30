# Cell Scan PPP Reconnection Failure Analysis

**Date:** 2025-12-29
**Log File:** logs/scan1.txt
**Author:** Claude Code Analysis
**Status:** CRITICAL BUG IDENTIFIED

---

## 1. Executive Summary

After a cell scan operation completes, the PPP connection fails to re-establish. The failure is caused by a **complex timing/synchronization bug** between three subsystems:
1. Cellular Manager (scan completion)
2. Network Manager (ppp0 activation)
3. runsv/pppd (PPP daemon)

The core issue: **Network Manager terminates PPPD before it can complete connection** due to missing coordination flags and route conflicts.

---

## 2. Timeline of Events

### 2.1 Pre-Scan State (00:09:28 - 00:09:31)
| Time | Event | State |
|------|-------|-------|
| 00:09:28.833 | System online, wlan0 active | cellular_ready=YES |
| 00:09:31.121 | **MANUAL scan requested via CLI** | - |
| 00:09:31.225 | `sv down pppd` executed | Stopping PPP |
| 00:09:31.358 | **cellular_ready → NOT_READY** | Link reset |
| 00:09:31.769 | sv down complete | PPP stopped |

### 2.2 During Scan (00:09:32 - 00:11:15)
- State: `SCAN_*` states
- Operators found: T-Mobile, Verizon, AT&T, 313 100
- Signal strengths: T-Mobile=16, Verizon=22, **AT&T=25** (BEST), 313 100=FAIL
- **cellular_ready=NO, cellular_started=NO** throughout scan

### 2.3 Scan Completion (00:11:15)
| Time | Event |
|------|-------|
| 00:11:07.898 | Scan complete, selecting best operator |
| 00:11:08.001 | SELECTED: AT&T (310410) with signal=25 |
| 00:11:15.306 | VERIFIED: Registered to AT&T (310410) |
| 00:11:15.408 | **`sv up pppd`** - Re-enabling runsv supervision |
| 00:11:15.408 | State → WAIT_PPP_STARTUP (10s grace period) |

### 2.4 PPP Reconnection Attempt #1 (FAILS)
| Time | Event | Problem |
|------|-------|---------|
| 00:11:16.449 | NETMGR: Skipping ppp0 | **cellular_ready=NO, cellular_started=NO** |
| 00:11:16.459 | Skipping ppp0 test | **has_ip=YES but cellular_ready=NO** |
| 00:11:17.557 | NETMGR: Skipping ppp0 | Still NO flags |
| 00:11:18.448 | PPP interface detected | Finally enabling cellular_now_ready |
| 00:11:18.553 | **Ready → READY** | Cellular state transition |
| 00:11:18.643 | PPPD already running | Setting cellular_started=true |
| 20:14:05 | **pppd[7459]: not replacing default route to wlan0** | ROUTE CONFLICT |
| 00:11:19.581 | ppp0 obtained IP | Starting grace period |
| 00:11:19.682 | **PPP0 timeout** | Other interfaces available, stopping |
| 00:11:19.773 | **Stopping PPPD** | cellular_reset=false |
| 00:11:21.958 | PPPD did not exit gracefully | Forcing kill |
| 00:11:22.091 | PPPD stopped (count=3) | - |

### 2.5 PPP Reconnection Attempt #2 (FAILS)
| Time | Event |
|------|-------|
| 00:11:22.645 | PPPD already running (runsv restarted it) |
| 20:14:09 | **pppd[7545]: Connect script failed** |

### 2.6 PPP Reconnection Attempt #3 (FAILS)
| Time | Event |
|------|-------|
| 20:14:23 | pppd[7545]: not replacing default route |
| 00:11:37.892 | Stopping PPPD |
| 00:11:40.071 | PPPD did not exit gracefully |
| 20:14:30 | **pppd[7774]: Connect script failed** |

---

## 3. Root Cause Analysis

### 3.1 Issue #1: Flag Synchronization Failure (CRITICAL)

**Problem:** After scan completion, `cellular_ready` remains `NO` for ~3 seconds while PPPD is already running.

```
00:11:15.408  sv up pppd                    <- PPPD starts
00:11:16.459  cellular_ready=NO, has_ip=YES <- PPP has IP but flags wrong
00:11:18.448  PPP interface detected        <- 3 seconds later!
00:11:18.553  cellular_ready → READY        <- Too late
```

**Impact:** Network Manager skips ppp0 testing because `cellular_ready=NO`, even though PPP already has an IP address.

**Location:** `cellular_man.c` - `SCAN_COMPLETE` → `WAIT_PPP_STARTUP` state transition

### 3.2 Issue #2: Premature PPP Termination (CRITICAL)

**Problem:** Network Manager decides PPP "timed out" and stops it, even though PPP just connected.

```
00:11:19.581  ppp0 obtained IP address, starting grace period
00:11:19.682  PPP0 timeout but other interfaces available, stopping without blacklist
```

**Cause:** The "grace period" starts but immediately sees a "timeout" condition because:
1. PPP wasn't tested (skipped due to `cellular_ready=NO`)
2. No ping test was run on ppp0
3. System concludes PPP is "not working" and terminates it

**Location:** `process_network.c` - `NET_REVIEW_SCORE` state

### 3.3 Issue #3: Default Route Conflict

**Problem:** PPPD cannot establish its default route because wlan0 already has one.

```
pppd[7459]: not replacing default route to wlan0 [10.2.0.1]
```

**Impact:** Even if PPP gets an IP, traffic still goes through wlan0. The network manager's ping test (if it ran) would fail because ppp0 has no route.

**Routing table during failure:**
```
default via 10.2.0.1 dev wlan0           <- wlan0 is primary
10.2.0.0/24 dev wlan0 proto kernel
192.168.7.0/24 dev eth0 proto kernel
```
Note: **No ppp0 route exists** despite having IP.

### 3.4 Issue #4: Connect Script Failure on Retry

**Problem:** After first PPPD is killed, subsequent restarts fail with "Connect script failed".

```
20:14:09  pppd[7545]: Connect script failed
20:14:30  pppd[7774]: Connect script failed
```

**Possible Causes:**
1. Modem not stabilized after carrier change (AT&T selection)
2. Previous PPP session not properly closed
3. Serial port locked by previous instance
4. Modem in unexpected state after forced kill

---

## 4. State Machine Flow Diagram

```
                    SCAN_COMPLETE
                         │
                         ▼
              sv up pppd (runsv starts PPPD)
                         │
                         ▼
               WAIT_PPP_STARTUP ─────────────────┐
                         │                       │
                    (10s timeout)                │
                         │                       │
     ┌───────────────────┴───────────────────┐   │
     │                                       │   │
     ▼                                       ▼   │
PPP gets IP                            PPP fails │
cellular_ready=NO (WRONG!)                       │
     │                                           │
     ▼                                           │
Network Manager skips ppp0 ◄─────────────────────┘
     │
     ▼
"PPP0 timeout" detected
     │
     ▼
Network Manager KILLS PPPD ← ← ← THIS IS THE BUG
     │
     ▼
runsv restarts PPPD
     │
     ▼
Connect script fails (modem unstable)
```

---

## 5. Detailed Log Evidence

### 5.1 Flag Never Set Properly After Scan
```log
[00:11:16.449] [NETMGR-PPP0] Skipping ppp0: cellular_ready=NO, cellular_started=NO
[00:11:16.459] Skipping ppp0 test - not active (cellular_ready=NO, cellular_started=NO, has_ip=YES)
                                                                                        ^^^^^^^^
                                                                            PPP HAS IP BUT FLAGS WRONG!
```

### 5.2 Premature Termination Decision
```log
[00:11:19.581] ppp0 obtained IP address, starting grace period
[00:11:19.682] PPP0 timeout but other interfaces available, stopping without blacklist
[00:11:19.773] Stopping PPPD (cellular_reset=false)
```

### 5.3 Route Conflict
```log
Dec 29 20:14:05 pppd[7459]: not replacing default route to wlan0 [10.2.0.1]
```

### 5.4 Subsequent Failures
```log
Dec 29 20:14:09 pppd[7545]: Connect script failed
Dec 29 20:14:23 pppd[7545]: not replacing default route to wlan0 [10.2.0.1]
Dec 29 20:14:30 pppd[7774]: Connect script failed
```

---

## 6. Affected Code Locations

| File | Function/Area | Issue |
|------|---------------|-------|
| `cellular_man.c` | `SCAN_COMPLETE` state | Doesn't set `cellular_ready=YES` before `sv up pppd` |
| `cellular_man.c` | `WAIT_PPP_STARTUP` state | Only sets ready after detecting PPP interface (too late) |
| `process_network.c` | `NET_REVIEW_SCORE` | Terminates PPP too aggressively when grace period starts |
| `process_network.c` | PPP test logic | Skips ppp0 when `cellular_ready=NO` even if has_ip=YES |
| `start_pppd.sh` or ppp config | Route handling | Doesn't handle existing default route gracefully |

---

## 7. Recommended Fixes

### 7.1 Fix #1: Set cellular_ready BEFORE sv up pppd

In `SCAN_COMPLETE` state, before calling `sv up pppd`:
```c
// Set ready flag BEFORE starting PPPD
set_cellular_ready(true);
set_cellular_started(true);  // Mark as started
system("sv up pppd");
```

### 7.2 Fix #2: Wait for PPP Verification Before Allowing Termination

In `WAIT_PPP_STARTUP` state:
- Set a protection window (e.g., 30 seconds) during which Network Manager cannot terminate PPP
- Only transition to ONLINE after PPP ping test succeeds
- Add explicit coordination signal to Network Manager

### 7.3 Fix #3: Handle Route Conflict

Before starting PPPD after scan:
```c
// Remove conflicting default route temporarily
system("ip route del default dev wlan0");
// Or: Configure PPPD to use metric-based routing
// Or: Use replacedefaultroute option in ppp options
```

### 7.4 Fix #4: Add Modem Stabilization Delay

After carrier selection (AT+COPS=1,2,...), wait for modem to fully register:
```c
// In SCAN_CONNECT_BEST or before sv up pppd
imx_delay(3000);  // Wait 3 seconds for modem stabilization
// Verify registration with AT+CREG? before starting PPP
```

### 7.5 Fix #5: Coordinate with Network Manager

Add explicit scan completion notification:
```c
// New function to notify network manager
void notify_netmgr_scan_complete(bool success) {
    // Set flags atomically
    cellular_scan_complete = true;
    cellular_ppp_protected = true;  // Prevent termination
    cellular_ready = true;
}
```

---

## 8. Testing Plan

1. **Reproduce the bug:**
   ```
   ./fc1 ppp          # Verify PPP working
   cell scan          # Trigger scan via CLI
   ./fc1 ppp          # Verify PPP reconnected (currently fails)
   ```

2. **Test each fix individually**

3. **Verify success criteria:**
   - PPP reconnects within 15 seconds of scan completion
   - No "Connect script failed" errors
   - ppp0 has valid route and passes ping test
   - cellular_ready=YES before PPPD starts

---

## 9. Severity Assessment

| Issue | Severity | Impact |
|-------|----------|--------|
| Flag sync failure | CRITICAL | PPP never properly activated |
| Premature termination | CRITICAL | Working connection killed |
| Route conflict | HIGH | PPP unusable even with IP |
| Connect script failure | MEDIUM | Symptom of above issues |

**Overall:** CRITICAL - Cell scan renders cellular unusable until manual restart.

---

## 10. Appendix: Full Event Sequence

```
00:09:31.121  MANUAL scan requested via CLI
00:09:31.225  sv down pppd
00:09:31.358  cellular_ready → NOT_READY
00:09:31.769  sv down complete
00:09:32.485  AT+COPS=2 (deregister)
00:09:34.031  AT+COPS=? (scan)
00:10:33.548  Scan results received (5 operators)
00:10:33.653  Testing T-Mobile (310260) → signal=16
00:10:43.119  Testing Verizon (311480) → signal=22
00:10:56.076  Testing AT&T (310410) → signal=25
00:10:57.933  Testing 313 100 (313100) → FAILED
00:11:06.664  Testing T-Mobile (310260) → signal=16
00:11:07.898  SELECTED: AT&T (310410) signal=25
00:11:08.001  AT+COPS=1,2,"310410" (connect to AT&T)
00:11:15.306  VERIFIED: Registered to AT&T
00:11:15.408  sv up pppd
00:11:15.408  SCAN_COMPLETE → WAIT_PPP_STARTUP
00:11:18.448  PPP interface detected (3 seconds late!)
00:11:18.553  cellular_ready → READY (too late)
00:11:19.682  PPP0 timeout → STOPPING PPPD (BUG!)
00:11:21.958  PPPD force killed
20:14:09      Connect script failed (attempt #2)
20:14:30      Connect script failed (attempt #3)
```

---

**Document End**
