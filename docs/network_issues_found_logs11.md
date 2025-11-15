# Critical Network Issues Found in logs11.txt

**Date:** 2025-11-13
**Analysis:** Detailed review of logs11.txt reveals multiple critical bugs
**Status:** ⚠️ **SYSTEM UNSTABLE - MULTIPLE BUGS FOUND**

---

## Executive Summary

While the WiFi retry counter fix IS working correctly (increments on score=0), **logs11.txt reveals much more serious issues:**

### Critical Bugs Found:

1. ❌ **System force reboots on SSL errors** during network switching
2. ❌ **WiFi reassociation causes unnecessary AP hopping**
3. ❌ **No mechanism to prefer last working AP**
4. ❌ **Blacklisting only affects ONE BSSID, not entire SSID**
5. ❌ **System never stayed on working secondary AP** (SierraTelecom)

---

## Issue #1: System Force Reboot on SSL Error 🔴 **CRITICAL**

### Evidence

**Line 5891 (00:07:44.495):**
```
Resetting UDP connection for: SSL Bad Input Data - forcing a reboot -0x7100
```

### Timeline

| Time | Event | Details |
|------|-------|---------|
| 00:07:42 | ppp0 ping successful | 3/3 replies, 0% loss, score=10 |
| 00:07:43 | Switch to ppp0 | Network manager switches interface |
| 00:07:43 | UDP Coordinator | "Init UDP ppp0" |
| 00:07:44 | SSL error | "SSL Bad Input Data -0x7100" |
| 00:07:44 | **FORCED REBOOT** | System reboots instead of recovering |

### Root Cause

The SSL/TLS/DTLS stack (likely mbedtls) encountered an error when:
1. Interface changed from wlan0 → ppp0
2. UDP connection reset initiated
3. DTLS handshake attempted on new interface
4. **SSL context got corrupted or invalid**
5. **System chose to reboot instead of recovering**

### Impact

**CRITICAL:** Network instability should NEVER cause system reboot. This defeats the purpose of failover:
- Loses all in-memory data
- Interrupts ongoing operations
- Takes ~30+ seconds to recover
- User experiences service outage

### Location

Likely in:
- `iMatrix/networking/` - UDP coordinator
- `iMatrix/coap/` - CoAP client
- `mbedtls/` - SSL/TLS library
- Error code `-0x7100` is mbedtls error `MBEDTLS_ERR_SSL_BAD_INPUT_DATA`

### Fix Required

**Priority:** HIGHEST

**Solution:**
1. Catch SSL errors gracefully
2. Destroy and recreate SSL context on interface change
3. Retry connection with exponential backoff
4. Only reboot as LAST resort after multiple retry failures
5. Add error recovery state machine

---

## Issue #2: WiFi Thrashing Between APs 🔴 **CRITICAL**

### Evidence

**WiFi Connection Sequence:**

| Time | Event | BSSID | SSID | Status |
|------|-------|-------|------|--------|
| 00:00:38 | ✓ Connected | 16:18:d6:22:21:2b | **SierraTelecom** | Working |
| 00:04:46 | ✗ Disconnected | 16:18:d6:22:21:2b | SierraTelecom | |
| 00:04:49 | ✓ Reconnected | 16:18:d6:22:21:2b | **SierraTelecom** | Working again |
| 00:05:41 | ✗ Disconnected | 16:18:d6:22:21:2b | SierraTelecom | |
| 00:05:43 | ✓ Connected | 24:5a:4c:89:36:6b | **2ROOS-Tahoe** | Different AP! |
| 00:06:49 | ✗ Disconnected | 24:5a:4c:89:36:6b | 2ROOS-Tahoe | |
| 00:06:52 | ✓ Connected | e0:63:da:81:33:80 | **2ROOS-Tahoe** | Yet another BSSID! |

### Problem

**SierraTelecom was working!** System connected twice and it worked both times. But WiFi reassociation logic caused it to:
1. Disconnect from working SierraTelecom
2. Scan for new APs
3. Randomly connect to different AP (2ROOS-Tahoe)
4. 2ROOS-Tahoe fails repeatedly
5. System never returns to known-working SierraTelecom

### Root Cause

**File:** `process_network.c` - `force_wifi_reassociate()`

**Current WiFi Reassociation Method:**
```c
system("wpa_cli -i wlan0 disconnect");
sleep(200ms);
system("wpa_cli -i wlan0 scan");
sleep(2000ms);
system("wpa_cli -i wlan0 reconnect");
```

**Problem:**
- `disconnect` drops current connection (even if working!)
- `scan` refreshes AP list
- `reconnect` tells wpa_supplicant "pick any configured AP"
- wpa_supplicant uses signal strength + internal algorithm
- **No preference for "last working" AP**
- **No memory of which APs failed**

### Why This Is Bad

1. **Loses good connection:** Disconnects from working AP
2. **Random selection:** wpa_supplicant picks "best" by signal, not reliability
3. **No learning:** Same failed APs tried repeatedly
4. **Excessive scanning:** Unnecessary RF activity, power consumption

### What Should Happen

When WiFi fails:
1. **Keep track of last working BSSID**
2. **Blacklist current failed BSSID** (already doing this, but see Issue #3)
3. **Try reassociation to SAME BSSID first** (don't scan/disconnect)
4. **Only scan for alternatives if reassociation fails**
5. **Prefer last-known-working BSSID if available**

---

## Issue #3: Per-BSSID Blacklisting Insufficient 🟠 **HIGH**

### Problem

**2ROOS-Tahoe has multiple BSSIDs** (dual-band router):

| BSSID | Frequency | Observations |
|-------|-----------|--------------|
| e0:63:da:81:33:7f | 2.4 GHz likely | Seen in logs9.txt, failed |
| 24:5a:4c:89:36:6b | 5 GHz likely | Seen in logs11.txt, failed |
| e0:63:da:81:33:80 | 2.4 GHz likely | Seen in logs11.txt, failed |

**Current blacklisting:**
```c
imx_blacklist_current_bssid();  // Only blacklists ONE BSSID
```

**Result:**
- Blacklist e0:63:da:81:33:7f
- wpa_supplicant connects to 24:5a:4c:89:36:6b (different BSSID, same SSID)
- System fails again
- Blacklist 24:5a:4c:89:36:6b
- wpa_supplicant connects to e0:63:da:81:33:80
- **Infinite loop!**

### Solution Needed

**Option 1: Blacklist Entire SSID**
```c
bool blacklist_ssid_all_bssids(const char *ssid)
{
    // Tell wpa_supplicant to disable this network entirely
    system("wpa_cli -i wlan0 disable_network <network_id>");
}
```

**Option 2: Track Failed BSSIDs per SSID**
```c
typedef struct {
    char ssid[33];
    uint8_t failed_bssids[10][6];  // Track up to 10 failed BSSIDs
    uint32_t failure_count;
    imx_time_t last_failure;
} ssid_failure_tracker_t;

// After 3 failures of ANY BSSID for this SSID, blacklist entire SSID
```

**Option 3: Prefer Different SSID**
```c
// After SSID fails, temporarily boost priority of other SSIDs
// e.g., increase SierraTelecom priority, decrease 2ROOS-Tahoe priority
```

---

## Issue #4: WiFi Retry Counter Correct But Incomplete ✅/⚠️

### What's Working

✅ **The score=0 bug fix IS working:**
```
[00:04:45.943] Wi-Fi failed (score=0), retry 1/3
[00:07:43.205] Wi-Fi failed (score=0), retry 2/3
```

Retry counter correctly increments on total failures.

### What's Still Wrong

**Problem:** System never reached retry 3/3 because:
1. System rebooted before 3rd failure (Issue #1)
2. Even if it had reached 3/3:
   - Would blacklist e0:63:da:81:33:80 (current BSSID)
   - wpa_supplicant would just try different BSSID of same SSID
   - 2ROOS-Tahoe has 3+ BSSIDs, so blacklisting is ineffective

### Missing Piece

**Need to track failures per SSID, not just per BSSID:**

```c
// Current (per-interface, all SSIDs lumped together):
ctx->wlan_retries = 2;  // Any WiFi failure increments this

// Needed (per-SSID tracking):
typedef struct {
    char ssid[33];
    uint32_t consecutive_failures;
    imx_time_t last_failure_time;
} ssid_failure_t;

ssid_failure_t ssid_failures[MAX_SSIDS];
```

---

## Issue #5: No "Last Working AP" Preference 🟠 **HIGH**

### Evidence

**SierraTelecom was working:**
- 00:00:38: Connected, working
- 00:04:49: Reconnected, working again

**But system abandoned it:**
- 00:05:43: Connected to 2ROOS-Tahoe instead
- 2ROOS-Tahoe failed repeatedly
- Never returned to SierraTelecom

### Problem

**No mechanism to remember which AP was last working.**

When WiFi reassociation triggered:
1. Disconnected from SierraTelecom (working)
2. Scanned for APs
3. wpa_supplicant picked 2ROOS-Tahoe (stronger signal?)
4. System "forgot" that SierraTelecom was working
5. Got stuck trying 2ROOS-Tahoe variants

### Solution Needed

**Add "last working AP" tracking:**

```c
typedef struct {
    char ssid[33];
    uint8_t bssid[6];
    imx_time_t last_success_time;
    uint32_t success_count;
    int16_t signal_strength;
} last_working_ap_t;

last_working_ap_t last_working_ap;
```

**WiFi reassociation logic:**
```c
void force_wifi_reassociate()
{
    // Option 1: Try to reconnect to same BSSID first
    if (last_working_ap.last_success_time > 0) {
        // Try to roam to last working BSSID
        snprintf(cmd, sizeof(cmd), "wpa_cli -i wlan0 bssid %s",
                 format_bssid(last_working_ap.bssid));
        system(cmd);
        system("wpa_cli -i wlan0 reassociate");

        // Wait and test
        sleep(5);
        if (test_wifi_connection()) {
            return;  // Success!
        }
    }

    // Option 2: If that fails, THEN do full scan
    system("wpa_cli -i wlan0 disconnect");
    system("wpa_cli -i wlan0 scan");
    system("wpa_cli -i wlan0 reconnect");
}
```

---

## Timeline Analysis: What Actually Happened

| Time | Event | Analysis |
|------|-------|----------|
| 00:00:38 | ✓ Connected to SierraTelecom | System working well |
| 00:04:41 | First WiFi failure (score=0) | ✅ **Retry 1/3 logged** (fix working!) |
| 00:04:43 | WiFi reassociation initiated | Disconnect → Scan → Reconnect |
| 00:04:49 | ✓ Reconnected to SierraTelecom | Good! Same AP |
| 00:05:38 | Second reassociation attempt | Disconnect → Scan → Reconnect again |
| 00:05:43 | ✓ Connected to **2ROOS-Tahoe** | ❌ Wrong! Abandoned working AP |
| 00:06:46 | Third reassociation attempt | Disconnect → Scan → Reconnect |
| 00:06:52 | ✓ Connected to 2ROOS-Tahoe (different BSSID) | Still trying same failed SSID |
| 00:07:43 | Second counted failure (score=0) | ✅ **Retry 2/3 logged** (fix working!) |
| 00:07:43 | Switch to ppp0 | Correct failover decision |
| 00:07:44 | **SSL Error → REBOOT** | ❌ CRITICAL: System crashed |

---

## Comparison: Expected vs Actual Behavior

### Expected (With All Fixes)

```
1. SierraTelecom works → Remember as "last working"
2. SierraTelecom fails → Try reassociate to SAME BSSID
3. If fails again → Blacklist SierraTelecom BSSID
4. wpa_supplicant finds alternate: 2ROOS-Tahoe
5. 2ROOS-Tahoe fails → Count failure against "2ROOS-Tahoe" SSID
6. 2ROOS-Tahoe fails (different BSSID) → Count against same SSID
7. After 3 SSID failures → Blacklist entire "2ROOS-Tahoe" SSID
8. Try next available SSID
9. If all fail → Use cellular backup
10. SSL error on interface change → Recover gracefully, don't reboot!
```

### Actual (Current Behavior)

```
1. SierraTelecom works ✓
2. SierraTelecom fails → Reassociate with disconnect/scan/reconnect
3. Reconnects to SierraTelecom (by luck) ✓
4. Fails again → Reassociate with disconnect/scan/reconnect
5. Connects to 2ROOS-Tahoe (wrong choice) ✗
6. 2ROOS-Tahoe fails repeatedly ✗
7. Keeps trying different BSSIDs of 2ROOS-Tahoe ✗
8. Never returns to SierraTelecom ✗
9. Switch to ppp0 ✓
10. SSL error → SYSTEM REBOOT ✗✗✗
```

---

## Required Fixes

### Priority 1: CRITICAL (System Stability)

1. **Fix SSL crash on interface change**
   - Add error recovery instead of reboot
   - Properly destroy/recreate SSL context
   - Retry with backoff
   - **File:** CoAP/UDP coordinator code

2. **Add per-SSID failure tracking**
   - Track failures by SSID, not just per-interface
   - Blacklist entire SSID after N failures (all BSSIDs)
   - **File:** `process_network.c`, new: `wifi_ssid_tracker.c`

### Priority 2: HIGH (Connection Stability)

3. **Improve WiFi reassociation logic**
   - Remember last working AP
   - Try reassociate to same BSSID first
   - Only scan for alternatives if reassociation fails
   - **File:** `process_network.c`

4. **Prefer known-working SSIDs**
   - Boost priority of recently-successful SSIDs
   - Lower priority of recently-failed SSIDs
   - Persist across reboots
   - **File:** New: `wifi_ap_preference.c`

### Priority 3: MEDIUM (Long-term Improvement)

5. **Add comprehensive WiFi quality tracking**
   - Track per-BSSID success/failure rates
   - Calculate reliability score over time
   - Use for intelligent AP selection
   - **File:** Enhancement #4 from original plan

---

## Testing Requirements

### Test 1: SSL Recovery
- Force interface change during active SSL connection
- Verify system recovers without reboot
- Check error logs for proper recovery sequence

### Test 2: Per-SSID Blacklisting
- Configure wpa_supplicant with multi-BSSID SSID
- Force failures on all BSSIDs
- Verify entire SSID is blacklisted after threshold
- Verify wpa_supplicant tries different SSID

### Test 3: Last Working AP Preference
- Connect to working AP-A
- Force failure
- Verify system tries to reconnect to AP-A first
- Only tries AP-B if AP-A unavailable

### Test 4: Long-term Stability
- Run for 24-48 hours with periodic WiFi disruptions
- Verify no reboots
- Verify system converges to most reliable AP
- Check memory for leaks

---

## Summary

### What We Fixed (Score=0 Retry Counter)

✅ **Working correctly:**
- WiFi total failures (score=0) now increment retry counter
- Logging shows "retry N/3" as expected
- Code change validated in production

### What We Still Need to Fix

❌ **Critical Issues Found:**
1. System reboots on SSL errors (HIGHEST PRIORITY)
2. WiFi abandons working AP unnecessarily
3. Per-BSSID blacklisting insufficient for multi-BSSID SSIDs
4. No "last working AP" preference
5. No per-SSID failure tracking

### Recommendation

**DO NOT MERGE current fix alone.** While the retry counter fix is correct, logs11.txt reveals system is still unstable:

**Next Steps:**
1. Fix SSL crash (Priority 1 - CRITICAL)
2. Add per-SSID tracking (Priority 1 - CRITICAL)
3. Improve WiFi reassociation (Priority 2 - HIGH)
4. Then merge all fixes together

---

**Analysis Date:** 2025-11-13
**Status:** ⚠️ MULTIPLE CRITICAL BUGS IDENTIFIED
**Recommendation:** Additional fixes required before production deployment
