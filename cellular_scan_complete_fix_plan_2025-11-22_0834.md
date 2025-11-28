# Cellular Scan Complete Fix Plan

**Date**: 2025-11-22
**Time**: 08:34
**Document Version**: 1.0
**Status**: Draft
**Author**: Claude Code Analysis
**Build Analyzed**: Nov 21 2025 @ 15:01

---

## Executive Summary

Analysis of net10.txt reveals the cellular scan **is completing successfully** but fails to establish PPP connectivity afterward. The scan correctly identifies and selects Verizon (signal=29) but the PPP link never comes up, resulting in ping failures and no network connectivity. Additionally, the system lacks proper carrier blacklisting and retry mechanisms when PPP fails.

---

## Current Behavior (From net10.txt)

### What's Working ✅

1. **Scan States Execute Properly** (States 1-11)
   - runsv coordination working (sv down/up)
   - PPP stops successfully
   - AT+COPS=? returns operator list
   - All carriers tested for signal strength
   - Best carrier selected (Verizon, signal=29)
   - PPP start attempted after scan

2. **Network Manager Coordination**
   - Correctly detects `cellular_scanning = true`
   - Waits passively during scan
   - Resumes operations after scan complete

### What's Failing ❌

1. **PPP Never Comes Up**
   ```
   [00:02:47.419] Starting PPPD: /etc/start_pppd.sh
   [00:02:47.916] ping: bad address 'ppp0'
   ```
   - PPP daemon starts but interface never appears
   - Ping fails immediately with "bad address"

2. **No Carrier Blacklisting on Failure**
   - Verizon selected but PPP fails
   - No mechanism to blacklist and retry with AT&T (signal=18)
   - System stuck with non-functional carrier

3. **Duplicate/Invalid Carriers in Scan**
   ```
   Carrier 1: T-Mobile (310260) - signal 15
   Carrier 2: 313 100 (313100) - signal 18
   Carrier 3: Verizon (311480) - signal 29
   Carrier 4: T-Mobile (310260) - signal 14  ← DUPLICATE
   Carrier 5: AT&T (310410) - signal 18
   Carrier 6: (empty) - signal 18  ← INVALID
   Carrier 7: (empty) - signal 18  ← INVALID
   ```

4. **No PPP Wait Mechanism**
   - Network manager tests ppp0 immediately
   - Doesn't wait for interface to come up
   - No timeout/retry for PPP establishment

5. **Missing Operator Storage**
   - "cell operators" command not populated
   - Scan results not persisted for display
   - No way to view tested carriers/signals

---

## Root Causes

### 1. PPP Interface Timing Issue
**Problem**: PPP daemon starts but interface takes 5-15 seconds to appear
**Evidence**: `ping: bad address 'ppp0'` immediately after starting PPP
**Impact**: Network manager fails connectivity test before PPP is ready

### 2. No Failure Recovery
**Problem**: When PPP fails, no mechanism to blacklist carrier and retry
**Evidence**: Scan completes, PPP fails, system stuck
**Impact**: Cannot recover from bad carrier selection

### 3. Parsing Issues in AT+COPS Response
**Problem**: Parser creating duplicate and empty entries
**Evidence**: 7 carriers parsed but only 5 valid, 2 duplicates, 2 empty
**Impact**: Wasted time testing invalid carriers

### 4. Missing Integration Layer
**Problem**: No coordination between scan completion and PPP establishment
**Evidence**: Scan sets `cellular_ready=true` but no wait for PPP interface
**Impact**: Network manager tests fail prematurely

---

## Comprehensive Fix Plan

### Phase 1: Fix PPP Interface Wait (PRIORITY 1)

#### Add New State: CELL_WAIT_PPP_INTERFACE

**Location**: cellular_man.c

```c
// Add after CELL_ONLINE state
CELL_WAIT_PPP_INTERFACE,  // Wait for ppp0 interface to appear

// In process_cellular():
case CELL_ONLINE:
    if (!cellular_ppp_verified) {
        // After scan, wait for PPP to come up
        cellular_state = CELL_WAIT_PPP_INTERFACE;
        ppp_wait_timeout = current_time + 30000;  // 30 sec timeout
        ppp_check_interval = current_time + 2000;  // Check every 2 sec
    }
    break;

case CELL_WAIT_PPP_INTERFACE:
    if (imx_is_later(current_time, ppp_check_interval)) {
        // Check if ppp0 exists
        if (system("ip link show ppp0 >/dev/null 2>&1") == 0) {
            PRINTF("[Cellular] PPP interface UP, verifying connectivity\n");
            cellular_ppp_verified = true;
            cellular_state = CELL_ONLINE;
            // Signal network manager PPP is ready
            cellular_ppp_ready = true;
        }
        else if (imx_is_later(current_time, ppp_wait_timeout)) {
            PRINTF("[Cellular] PPP interface timeout, blacklisting carrier\n");
            blacklist_current_carrier();
            cellular_state = CELL_SCAN_STOP_PPP;  // Retry scan
        }
        ppp_check_interval = current_time + 2000;  // Next check
    }
    break;
```

### Phase 2: Implement Carrier Blacklisting (PRIORITY 1)

#### Add Blacklist Management

**Location**: cellular_man.c

```c
// Global arrays
static char blacklisted_carriers[MAX_BLACKLIST][16];
static int blacklist_count = 0;
static int blacklist_retry_count[MAX_BLACKLIST];  // Track retries per carrier

// Functions to add
void blacklist_carrier(const char* mccmnc) {
    if (blacklist_count < MAX_BLACKLIST) {
        strncpy(blacklisted_carriers[blacklist_count], mccmnc, 15);
        blacklist_retry_count[blacklist_count] = 1;
        blacklist_count++;
        PRINTF("[Cellular] Blacklisted carrier: %s\n", mccmnc);
    }
}

bool is_carrier_blacklisted(const char* mccmnc) {
    for (int i = 0; i < blacklist_count; i++) {
        if (strcmp(blacklisted_carriers[i], mccmnc) == 0) {
            return true;
        }
    }
    return false;
}

void clear_blacklist() {
    blacklist_count = 0;
    memset(blacklisted_carriers, 0, sizeof(blacklisted_carriers));
}

// Modify CELL_SCAN_SELECT_BEST state:
case CELL_SCAN_SELECT_BEST:
    int best_idx = -1;
    int best_signal = -1;

    for (int i = 0; i < scan_operator_count; i++) {
        // Skip blacklisted carriers
        if (is_carrier_blacklisted(scan_operators[i].mccmnc)) {
            PRINTF("[Cellular Scan] Skipping blacklisted: %s\n",
                   scan_operators[i].name);
            continue;
        }

        if (scan_operators[i].signal > best_signal) {
            best_signal = scan_operators[i].signal;
            best_idx = i;
        }
    }

    if (best_idx == -1) {
        PRINTF("[Cellular Scan] All carriers blacklisted, clearing list\n");
        clear_blacklist();
        cellular_state = CELL_SCAN_FAILED;
    }
    else {
        selected_operator_idx = best_idx;
        cellular_state = CELL_SCAN_CONNECT_BEST;
    }
    break;
```

### Phase 3: Fix Operator Parsing (PRIORITY 2)

#### Improve parse_cops_scan_results()

**Location**: cellular_man.c

```c
int parse_cops_scan_results(char* response, ScanOperator* operators, int max) {
    int count = 0;
    char* ptr = strstr(response, "+COPS:");
    if (!ptr) return 0;

    ptr += 6;  // Skip "+COPS:"

    // Track seen operators to avoid duplicates
    char seen_mccmnc[MAX_OPERATORS][16];
    int seen_count = 0;

    while (*ptr && count < max) {
        // Skip whitespace and commas
        while (*ptr && (*ptr == ' ' || *ptr == ',')) ptr++;

        // Check for end of response
        if (*ptr == '\r' || *ptr == '\n' || strncmp(ptr, "OK", 2) == 0) {
            break;
        }

        // Parse (status,"long name","short name","mccmnc",rat)
        if (*ptr == '(') {
            ptr++;  // Skip '('

            // Parse status
            int status = *ptr - '0';
            ptr += 2;  // Skip status and comma

            // Parse long name
            if (*ptr == '"') {
                ptr++;  // Skip opening quote
                char* end = strchr(ptr, '"');
                if (!end || (end - ptr) == 0) {
                    // Empty name, skip this entry
                    ptr = strchr(ptr, ')');
                    if (ptr) ptr++;
                    continue;
                }

                int len = end - ptr;
                if (len > 0 && len < 64) {
                    strncpy(operators[count].name, ptr, len);
                    operators[count].name[len] = '\0';
                }
                ptr = end + 1;  // Move past closing quote
            }

            // Skip short name
            ptr = strchr(ptr, '"');
            if (ptr) {
                ptr++;  // Skip opening quote
                ptr = strchr(ptr, '"');
                if (ptr) ptr++;  // Skip closing quote
            }

            // Parse MCCMNC
            ptr = strchr(ptr, '"');
            if (ptr) {
                ptr++;  // Skip opening quote
                char* end = strchr(ptr, '"');
                if (!end || (end - ptr) == 0) {
                    // Empty MCCMNC, skip this entry
                    ptr = strchr(ptr, ')');
                    if (ptr) ptr++;
                    continue;
                }

                int len = end - ptr;
                if (len > 0 && len < 16) {
                    // Check for duplicate
                    bool is_duplicate = false;
                    for (int i = 0; i < seen_count; i++) {
                        if (strcmp(seen_mccmnc[i], ptr) == 0) {
                            is_duplicate = true;
                            break;
                        }
                    }

                    if (!is_duplicate) {
                        strncpy(operators[count].mccmnc, ptr, len);
                        operators[count].mccmnc[len] = '\0';
                        strncpy(seen_mccmnc[seen_count], operators[count].mccmnc, 15);
                        seen_count++;

                        operators[count].status = status;
                        operators[count].signal = -1;  // Will be filled during test
                        count++;
                    }
                }
                ptr = end + 1;
            }

            // Skip to end of entry
            ptr = strchr(ptr, ')');
            if (ptr) ptr++;
        }
        else {
            // Unexpected format, move forward
            ptr++;
        }
    }

    return count;
}
```

### Phase 4: Network Manager Integration (PRIORITY 1)

#### Modify process_network() PPP Handling

**Location**: process_network.c

```c
// Add new flag
static bool cellular_ppp_wait_logged = false;

// In NET_SELECT_INTERFACE state for ppp0:
case NET_SELECT_INTERFACE:
    if (strcmp(iface->name, "ppp0") == 0) {
        // Check if cellular scan just completed
        if (cellular_now_ready && !cellular_ppp_ready) {
            if (!cellular_ppp_wait_logged) {
                PRINTF("[NETMGR-PPP0] Waiting for PPP interface after scan\n");
                cellular_ppp_wait_logged = true;
            }
            // Don't test yet, wait for cellular_ppp_ready flag
            break;
        }

        // Check if interface exists before testing
        if (system("ip link show ppp0 >/dev/null 2>&1") != 0) {
            PRINTF("[NETMGR-PPP0] Interface not yet present, deferring test\n");
            break;
        }

        // Now safe to test PPP
        cellular_ppp_wait_logged = false;
        // ... existing ping test code ...
    }
    break;

// In NET_ONLINE state for PPP failure:
case NET_ONLINE:
    if (current_interface == PPP0_INTERFACE && !test_passed) {
        // PPP test failed, request cellular blacklist and rescan
        PRINTF("[NETMGR] PPP connectivity failed, requesting carrier change\n");
        cellular_request_carrier_change = true;
        cellular_ppp_ready = false;
    }
    break;
```

### Phase 5: Implement "cell operators" Command (PRIORITY 2)

#### Store and Display Scan Results

**Location**: cellular_man.c & cli.c

```c
// In cellular_man.c - Store results globally
static ScanOperator stored_operators[MAX_OPERATORS];
static int stored_operator_count = 0;
static char scan_timestamp[32];

// After scan completes successfully:
case CELL_SCAN_COMPLETE:
    // Store results for display
    memcpy(stored_operators, scan_operators, sizeof(scan_operators));
    stored_operator_count = scan_operator_count;

    // Store timestamp
    time_t now = time(NULL);
    strftime(scan_timestamp, sizeof(scan_timestamp),
             "%Y-%m-%d %H:%M:%S", localtime(&now));

    // ... rest of completion code ...
    break;

// Add function for CLI
void display_cellular_operators() {
    PRINTF("\n=== Cellular Operators ===\n");
    PRINTF("Last Scan: %s\n", scan_timestamp[0] ? scan_timestamp : "Never");
    PRINTF("Operators Found: %d\n\n", stored_operator_count);

    PRINTF("%-20s %-10s %-8s %-12s %-10s\n",
           "Name", "MCCMNC", "Signal", "Status", "Blacklist");
    PRINTF("%-20s %-10s %-8s %-12s %-10s\n",
           "----", "------", "------", "------", "---------");

    for (int i = 0; i < stored_operator_count; i++) {
        char status_str[16];
        switch (stored_operators[i].status) {
            case 0: strcpy(status_str, "Unknown"); break;
            case 1: strcpy(status_str, "Available"); break;
            case 2: strcpy(status_str, "Current"); break;
            case 3: strcpy(status_str, "Forbidden"); break;
            default: strcpy(status_str, "?"); break;
        }

        bool blacklisted = is_carrier_blacklisted(stored_operators[i].mccmnc);

        PRINTF("%-20s %-10s %-8d %-12s %-10s\n",
               stored_operators[i].name,
               stored_operators[i].mccmnc,
               stored_operators[i].signal,
               status_str,
               blacklisted ? "YES" : "");
    }

    if (selected_operator_idx >= 0 && selected_operator_idx < stored_operator_count) {
        PRINTF("\nCurrently Selected: %s (Signal: %d)\n",
               stored_operators[selected_operator_idx].name,
               stored_operators[selected_operator_idx].signal);
    }

    PRINTF("\n");
}

// In cli.c - Add command handler
else if (strcmp(command, "cell operators") == 0) {
    display_cellular_operators();
}
```

### Phase 6: PPP Link Priority (PRIORITY 3)

#### Only Use PPP When eth0/wlan0 Unavailable

**Location**: process_network.c

```c
// Modify interface scoring/selection
case NET_SELECT_INTERFACE:
    // Check if eth0 or wlan0 are available and working
    bool wired_wireless_available = false;

    for (int i = 0; i < interface_count; i++) {
        if ((interfaces[i].type == ETH0_INTERFACE ||
             interfaces[i].type == WLAN0_INTERFACE) &&
            interfaces[i].has_ip &&
            interfaces[i].link_up) {
            wired_wireless_available = true;
            break;
        }
    }

    // Skip PPP testing if better interfaces available
    if (iface->type == PPP0_INTERFACE && wired_wireless_available) {
        PRINTF("[NETMGR-PPP0] Skipping - eth0/wlan0 available\n");
        iface->score = 0;
        iface->priority = 0;  // Lowest priority
        break;
    }

    // ... continue with normal testing ...
    break;
```

---

## Implementation Sequence

### Step 1: Critical Fixes (Immediate)
1. **Add CELL_WAIT_PPP_INTERFACE state** - Ensure PPP comes up before use
2. **Implement carrier blacklisting** - Handle PPP failures gracefully
3. **Fix network manager PPP wait** - Coordinate with cellular manager

### Step 2: Quality Improvements (Next)
4. **Fix operator parsing** - Eliminate duplicates and empty entries
5. **Add "cell operators" command** - Enable operator visibility
6. **Store scan results** - Persist for debugging and display

### Step 3: Optimization (Later)
7. **Implement PPP priority logic** - Only use when necessary
8. **Add retry with backoff** - Smart retry on failures
9. **Enhance logging** - Better debugging information

---

## Testing Strategy

### Test Case 1: Basic Scan and Connect
```bash
# Start with clean state
echo "cell scan"
# Wait 2-3 minutes
echo "cell operators"  # Should show all carriers with signals
ip link show ppp0      # Should show interface
ping -I ppp0 8.8.8.8   # Should succeed
```

### Test Case 2: Blacklist and Retry
```bash
# Simulate PPP failure (kill pppd after scan)
echo "cell scan"
# After scan completes:
killall pppd
# System should:
# 1. Detect PPP timeout
# 2. Blacklist current carrier
# 3. Automatically rescan
# 4. Select next best carrier
echo "cell operators"  # Should show blacklist status
```

### Test Case 3: Priority Testing
```bash
# With eth0 connected:
ip link show eth0      # Has IP
echo "cell operators"  # PPP should not be primary
# Disconnect eth0
ifconfig eth0 down
# PPP should become active
```

---

## Success Metrics

1. **PPP Establishment**: PPP interface appears within 30 seconds of scan
2. **Connectivity**: Ping tests succeed after carrier selection
3. **Blacklist Recovery**: System recovers from bad carrier selection
4. **No Duplicates**: Scan shows each carrier only once
5. **Operator Display**: "cell operators" shows accurate information
6. **Priority Respect**: PPP only used when eth0/wlan0 unavailable

---

## Risk Mitigation

1. **Timeout Safeguards**: All waits have maximum timeouts
2. **Blacklist Limits**: Clear blacklist after N failures to prevent lockout
3. **State Recovery**: Can always return to CELL_INIT for full reset
4. **Logging**: Comprehensive logs for debugging
5. **Backward Compatible**: Changes don't break existing functionality

---

## Expected Outcome

After implementation:

```
[00:00:00] cell scan initiated
[00:01:30] Scan complete: 5 operators found
[00:01:30] Selected: Verizon (signal=29)
[00:01:32] Starting PPP daemon
[00:01:45] PPP interface detected
[00:01:48] PPP connectivity verified ✅
[00:01:48] Network state: ONLINE via ppp0

# If PPP fails:
[00:01:50] PPP connectivity test FAILED
[00:01:50] Blacklisting Verizon (311480)
[00:01:51] Rescanning for operators...
[00:03:00] Selected: AT&T (signal=18)
[00:03:15] PPP connectivity verified ✅
```

---

## Conclusion

The cellular scan is working but lacks critical integration with PPP establishment and failure recovery. This plan addresses all identified issues with a phased approach prioritizing connectivity and reliability. Implementation should begin with Phase 1 (PPP wait) and Phase 2 (blacklisting) as these are critical for basic functionality.

---

**Document Version**: 1.0
**Date**: 2025-11-22
**Time**: 08:34
**Next Review**: After Phase 1 implementation