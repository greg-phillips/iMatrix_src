# Cellular Scan Complete Fix Plan - Version 2

**Date**: 2025-11-22
**Time**: 11:47
**Document Version**: 2.0
**Status**: Updated with Blacklist Clearing Mechanism
**Author**: Claude Code Analysis
**Build Analyzed**: Nov 21 2025 @ 15:01
**Reviewer**: Greg

---

## Executive Summary

Analysis of net10.txt and **net11.txt** reveals critical issues:
1. The cellular scan **is completing successfully** but fails to establish PPP connectivity afterward
2. **NEW FINDING**: When an existing carrier (Verizon) is already connected but PPP fails, the system doesn't blacklist it and rescan
3. **CRITICAL**: After AT+COPS=? response, all returned carriers should be processed with a clean slate (clear blacklist)

The scan correctly identifies carriers but lacks proper failure recovery and carrier rotation mechanisms when PPP establishment fails.

---

## Critical New Finding from net11.txt

### The Problem
```
[00:00:21.234] [Cellular COPS Operator: Verizon (311480) - Status: 0, Technology: 7]
[00:00:21.540] [Cellular Connection to Operator Verizon - CSQ: 18, BER: 99]
[00:00:21.644] [Cellular Connection - Ready state changed from NOT_READY to READY]
[00:00:21.829] [Cellular Connection - Starting PPPD: /etc/start_pppd.sh]
```

Then repeated failures:
```
[00:01:20.848] [NETMGR-PPP0] PPP0 connection timeout after 59084 ms
[00:01:20.848] [NETMGR-PPP0] Final status: ERROR (Connect script failed)
[00:01:28.812] [NETMGR-PPP0] PPP0 connection timeout after 65897 ms
```

### What Should Happen
1. Verizon connection exists from previous session
2. System attempts to establish PPP link
3. **When PPP fails**: Blacklist Verizon
4. Trigger AT+COPS=? scan to find all carriers
5. **Clear blacklist after receiving carrier list** (fresh start)
6. Test each carrier systematically
7. Select best non-blacklisted carrier
8. If all fail, clear blacklist and retry

---

## Updated Root Causes

### 1. No Carrier Rotation on PPP Failure
**Problem**: When existing carrier's PPP fails, no mechanism to try others
**Evidence**: Verizon stays selected despite repeated PPP failures
**Impact**: System stuck with non-functional carrier indefinitely

### 2. Missing Blacklist Clear on New Scan
**Problem**: Blacklist persists across scans, preventing retry
**Evidence**: No blacklist clearing logic in scan states
**Impact**: Once blacklisted, carriers never get retried

### 3. PPP Interface Timing Issue
**Problem**: PPP daemon starts but interface takes 5-15 seconds to appear
**Evidence**: `Connect script failed` repeatedly in logs
**Impact**: Network manager fails connectivity test before PPP is ready

### 4. No Integration Between PPP Failure and Cellular Scan
**Problem**: process_network.c doesn't signal cellular_man.c to rescan
**Evidence**: NET_SELECT_INTERFACE stuck in loop, cellular doesn't react
**Impact**: No recovery mechanism when PPP fails

---

## Comprehensive Fix Plan - Version 2

### Phase 1: Blacklist Management with Clear Logic (PRIORITY 1)

#### Enhanced Blacklist System

**Location**: cellular_man.c

```c
// Global blacklist management
#define MAX_BLACKLIST 10
#define BLACKLIST_DURATION_MS 300000  // 5 minutes per carrier

typedef struct {
    char mccmnc[16];
    uint32_t blacklist_time;
    int failure_count;
    bool permanent;  // For this session only
} BlacklistEntry;

static BlacklistEntry blacklist[MAX_BLACKLIST];
static int blacklist_count = 0;
static bool blacklist_cleared_this_scan = false;

// Clear blacklist when starting new scan
void clear_blacklist_for_scan() {
    PRINTF("[Cellular] Clearing blacklist for new scan cycle\n");
    blacklist_count = 0;
    memset(blacklist, 0, sizeof(blacklist));
    blacklist_cleared_this_scan = true;
}

// Temporary blacklist for retry logic
void blacklist_carrier_temporary(const char* mccmnc) {
    if (blacklist_count < MAX_BLACKLIST) {
        strncpy(blacklist[blacklist_count].mccmnc, mccmnc, 15);
        blacklist[blacklist_count].blacklist_time = imx_get_ms_ticks();
        blacklist[blacklist_count].failure_count = 1;
        blacklist[blacklist_count].permanent = false;
        blacklist_count++;
        PRINTF("[Cellular] Temporarily blacklisted: %s\n", mccmnc);
    }
}

// Check if carrier should be skipped
bool is_carrier_blacklisted(const char* mccmnc) {
    uint32_t now = imx_get_ms_ticks();

    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklist[i].mccmnc, mccmnc) == 0) {
            // Check if temporary blacklist expired
            if (!blacklist[i].permanent &&
                (now - blacklist[i].blacklist_time) > BLACKLIST_DURATION_MS) {
                // Remove from blacklist
                PRINTF("[Cellular] Blacklist expired for %s\n", mccmnc);
                memmove(&blacklist[i], &blacklist[i+1],
                        (blacklist_count - i - 1) * sizeof(BlacklistEntry));
                blacklist_count--;
                return false;
            }
            return true;
        }
    }
    return false;
}
```

### Phase 2: AT+COPS Scan with Blacklist Clear (PRIORITY 1)

#### Modified Scan State Machine

**Location**: cellular_man.c

```c
case CELL_SCAN_SEND_COPS:
    // CRITICAL: Clear blacklist when starting new scan
    if (!blacklist_cleared_this_scan) {
        clear_blacklist_for_scan();
    }

    PRINTF("[Cellular Scan] Sending AT+COPS=? to discover all carriers\n");
    send_at_command("AT+COPS=?", 180000);  // 3 minute timeout
    cellular_state = CELL_SCAN_WAIT_COPS;
    break;

case CELL_SCAN_PROCESS_COPS:
    // Parse AT+COPS response
    scan_operator_count = parse_cops_scan_results(response_buffer,
                                                  scan_operators,
                                                  MAX_OPERATORS);

    PRINTF("[Cellular Scan] Found %d carriers, blacklist cleared\n",
           scan_operator_count);

    // Reset flag for next scan
    blacklist_cleared_this_scan = false;

    if (scan_operator_count > 0) {
        current_test_idx = 0;
        cellular_state = CELL_SCAN_TEST_CARRIER;
    } else {
        cellular_state = CELL_SCAN_FAILED;
    }
    break;

case CELL_SCAN_SELECT_BEST:
    int best_idx = -1;
    int best_signal = -1;
    int blacklisted_count = 0;

    // First pass: Find best non-blacklisted carrier
    for (int i = 0; i < scan_operator_count; i++) {
        if (is_carrier_blacklisted(scan_operators[i].mccmnc)) {
            blacklisted_count++;
            PRINTF("[Cellular Scan] Skipping blacklisted: %s (%s)\n",
                   scan_operators[i].name, scan_operators[i].mccmnc);
            continue;
        }

        if (scan_operators[i].signal > best_signal) {
            best_signal = scan_operators[i].signal;
            best_idx = i;
        }
    }

    // If all carriers blacklisted, clear and retry
    if (best_idx == -1 && blacklisted_count > 0) {
        PRINTF("[Cellular Scan] All %d carriers blacklisted, clearing list\n",
               blacklisted_count);
        clear_blacklist_for_scan();

        // Find best carrier with cleared blacklist
        for (int i = 0; i < scan_operator_count; i++) {
            if (scan_operators[i].signal > best_signal) {
                best_signal = scan_operators[i].signal;
                best_idx = i;
            }
        }
    }

    if (best_idx >= 0) {
        selected_operator_idx = best_idx;
        PRINTF("[Cellular Scan] Selected: %s (signal=%d)\n",
               scan_operators[best_idx].name, best_signal);
        cellular_state = CELL_SCAN_CONNECT_BEST;
    } else {
        cellular_state = CELL_SCAN_FAILED;
    }
    break;
```

### Phase 3: PPP Failure Detection & Carrier Switch (PRIORITY 1)

#### Add PPP Monitoring State

**Location**: cellular_man.c

```c
// Global PPP monitoring
static uint32_t ppp_start_time = 0;
static int ppp_retry_count = 0;
static char current_carrier_mccmnc[16];

case CELL_ONLINE:
    // Monitor PPP establishment
    if (!cellular_ppp_verified) {
        if (ppp_start_time == 0) {
            ppp_start_time = current_time;
            ppp_retry_count = 0;
        }

        // Check PPP status every 2 seconds
        if (imx_is_later(current_time, ppp_check_interval)) {
            ppp_check_interval = current_time + 2000;

            // Check if ppp0 interface exists and has IP
            if (check_ppp_interface_ready()) {
                PRINTF("[Cellular] PPP interface verified after %d ms\n",
                       current_time - ppp_start_time);
                cellular_ppp_verified = true;
                ppp_start_time = 0;
                ppp_retry_count = 0;
            }
            else if ((current_time - ppp_start_time) > 30000) {  // 30 sec timeout
                ppp_retry_count++;
                PRINTF("[Cellular] PPP timeout #%d for carrier %s\n",
                       ppp_retry_count, current_carrier_mccmnc);

                if (ppp_retry_count >= 2) {
                    // Blacklist current carrier after 2 failures
                    PRINTF("[Cellular] Blacklisting carrier %s after %d PPP failures\n",
                           current_carrier_mccmnc, ppp_retry_count);
                    blacklist_carrier_temporary(current_carrier_mccmnc);

                    // Trigger new scan
                    cellular_state = CELL_SCAN_STOP_PPP;
                    ppp_start_time = 0;
                } else {
                    // Retry same carrier once
                    PRINTF("[Cellular] Retrying PPP for carrier %s\n",
                           current_carrier_mccmnc);
                    stop_ppp();
                    start_ppp();
                    ppp_start_time = current_time;
                }
            }
        }
    }
    break;

// Helper function to check PPP readiness
bool check_ppp_interface_ready() {
    // Check if interface exists
    if (system("ip link show ppp0 >/dev/null 2>&1") != 0) {
        return false;
    }

    // Check if interface has IP
    char cmd[128];
    snprintf(cmd, sizeof(cmd),
             "ip addr show ppp0 | grep -q 'inet ' && echo 1 || echo 0");

    FILE* fp = popen(cmd, "r");
    if (fp) {
        char result[8];
        if (fgets(result, sizeof(result), fp)) {
            pclose(fp);
            return (result[0] == '1');
        }
        pclose(fp);
    }

    return false;
}
```

### Phase 4: Network Manager Integration (PRIORITY 1)

#### Signal from Network Manager to Cellular

**Location**: process_network.c

```c
// Global flag for cellular coordination
extern bool cellular_request_rescan;
static int ppp_failure_count = 0;

case NET_SELECT_INTERFACE:
    if (strcmp(iface->name, "ppp0") == 0) {
        // Check for repeated PPP failures
        if (ppp_test_failed) {
            ppp_failure_count++;

            if (ppp_failure_count >= 3) {
                PRINTF("[NETMGR-PPP0] Multiple PPP failures, requesting carrier change\n");
                cellular_request_rescan = true;  // Signal to cellular_man.c
                ppp_failure_count = 0;
            }
        }
    }
    break;
```

**Location**: cellular_man.c

```c
// Check for rescan request from network manager
case CELL_ONLINE:
    if (cellular_request_rescan) {
        PRINTF("[Cellular] Network manager requested carrier change\n");
        cellular_request_rescan = false;

        // Blacklist current carrier
        if (strlen(current_carrier_mccmnc) > 0) {
            blacklist_carrier_temporary(current_carrier_mccmnc);
        }

        // Start new scan
        cellular_state = CELL_SCAN_STOP_PPP;
    }
    break;
```

### Phase 5: Operating Algorithm Documentation

See next document: `docs/cellular_carrier_processing.md`

---

## Implementation Sequence

### Immediate Actions (Do First)
1. ✅ Add blacklist management with clear mechanism
2. ✅ Modify AT+COPS scan to clear blacklist
3. ✅ Add PPP failure detection in CELL_ONLINE
4. ✅ Implement carrier rotation on PPP failure
5. ✅ Add network manager signaling

### Testing Requirements
1. Test with Verizon already connected but PPP failing
2. Verify blacklist clearing after AT+COPS scan
3. Confirm carrier rotation works
4. Test all carriers get tried before blacklist clear
5. Verify 5-minute blacklist timeout

---

## Success Metrics

1. **Carrier Rotation**: System tries different carriers when PPP fails
2. **Blacklist Management**: Failed carriers blacklisted temporarily
3. **Fresh Scan**: AT+COPS clears blacklist for fresh attempt
4. **PPP Recovery**: System recovers from PPP failures automatically
5. **No Infinite Loops**: System doesn't get stuck with bad carrier

---

## Expected Behavior After Fix

```
[00:00:00] System starts with Verizon connected
[00:00:10] PPP establishment attempted
[00:00:40] PPP timeout detected (30 sec)
[00:00:41] Verizon blacklisted temporarily
[00:00:42] AT+COPS=? initiated (clears blacklist after response)
[00:02:00] Carriers found: Verizon(29), AT&T(18), T-Mobile(15)
[00:02:01] Testing AT&T (Verizon blacklisted)
[00:02:30] AT&T selected, PPP established ✅

OR if AT&T also fails:
[00:03:00] AT&T PPP failed, blacklisted
[00:03:01] Testing T-Mobile
[00:03:30] T-Mobile PPP failed, blacklisted
[00:03:31] All carriers blacklisted - clearing list
[00:03:32] Retrying Verizon with fresh attempt
```

---

## Risk Mitigation

1. **Blacklist Timeout**: 5-minute timeout prevents permanent lockout
2. **Clear on All Failed**: When all carriers fail, clear and retry
3. **Session Only**: Blacklist doesn't persist across reboots
4. **Failure Counting**: Track failures to identify persistent issues
5. **Manual Override**: CLI command to clear blacklist manually

---

## Conclusion

The critical missing piece is the blacklist clearing mechanism when AT+COPS returns the carrier list. This ensures the gateway can adapt when it moves to a new location with better carrier options. The combination of temporary blacklisting, automatic clearing, and PPP failure detection creates a robust carrier selection system.

---

**Document Version**: 2.0
**Date**: 2025-11-22
**Time**: 11:47
**Next Review**: After Phase 1 implementation