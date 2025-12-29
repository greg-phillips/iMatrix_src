# Cellular Carrier Processing - Operating Algorithm

**Date**: 2025-11-22
**Time**: 11:50
**Document Version**: 1.0
**Status**: Specification
**Author**: Claude Code Analysis
**Purpose**: Define the complete operating algorithm for cellular carrier selection, blacklisting, and PPP management

---

## Table of Contents

1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Data Structures](#data-structures)
4. [State Machine Flow](#state-machine-flow)
5. [Blacklist Management Algorithm](#blacklist-management-algorithm)
6. [PPP Monitoring Algorithm](#ppp-monitoring-algorithm)
7. [Carrier Selection Algorithm](#carrier-selection-algorithm)
8. [Integration Points](#integration-points)
9. [Error Recovery](#error-recovery)
10. [Testing Scenarios](#testing-scenarios)

---

## Overview

The cellular carrier processing system manages the selection and connection to cellular carriers with automatic failover, blacklisting, and recovery mechanisms. The system ensures continuous connectivity by intelligently rotating through available carriers when failures occur.

### Key Components
- **Carrier Scanner**: Discovers available carriers via AT+COPS
- **Blacklist Manager**: Tracks failed carriers temporarily
- **PPP Monitor**: Validates PPP link establishment
- **Network Coordinator**: Interfaces with network manager
- **State Machine**: Controls the overall process flow

---

## Core Principles

1. **Fresh Start on Scan**: Every AT+COPS scan clears the blacklist
2. **Temporary Blacklisting**: Failed carriers blacklisted for 5 minutes
3. **Progressive Retry**: Try each carrier before clearing blacklist
4. **PPP Validation**: Verify PPP link before declaring success
5. **Coordinated Recovery**: Network and cellular managers work together

---

## Data Structures

```c
// Carrier information from scan
typedef struct {
    char name[64];          // Human-readable name (e.g., "Verizon")
    char mccmnc[16];        // MCC+MNC identifier (e.g., "311480")
    int signal;             // Signal strength in dBm or CSQ
    int status;             // 0=unknown, 1=available, 2=current, 3=forbidden
    int technology;         // RAT: 0=GSM, 2=UMTS, 7=LTE, etc.
} ScanOperator;

// Blacklist entry
typedef struct {
    char mccmnc[16];        // Carrier identifier
    uint32_t blacklist_time; // When blacklisted (ms since boot)
    int failure_count;      // Number of consecutive failures
    bool permanent;         // Session-permanent after N failures
    char failure_reason[64]; // Last failure reason
} BlacklistEntry;

// PPP monitoring state
typedef struct {
    uint32_t start_time;    // When PPP started (ms)
    uint32_t last_check;    // Last status check (ms)
    int retry_count;        // Retries for current carrier
    bool interface_up;      // ppp0 interface exists
    bool has_ip;            // Interface has IP address
    bool ping_success;      // Can reach internet
} PPPMonitorState;

// Global state
typedef struct {
    ScanOperator carriers[MAX_OPERATORS];  // All discovered carriers
    int carrier_count;                     // Number of carriers found
    int selected_carrier_idx;              // Currently selected carrier
    BlacklistEntry blacklist[MAX_BLACKLIST]; // Blacklisted carriers
    int blacklist_count;                   // Number in blacklist
    PPPMonitorState ppp_state;            // PPP monitoring
    bool scan_requested;                   // Rescan requested
    bool blacklist_cleared;                // Cleared this scan cycle
} CellularState;
```

---

## State Machine Flow

### Main State Progression

```
CELL_INIT
    ↓
CELL_CHECK_SIM_READY
    ↓
CELL_ONLINE (existing connection)
    ├─[PPP Failed]→ CELL_SCAN_STOP_PPP
    └─[PPP Success]→ (stay in CELL_ONLINE)
        ↓
CELL_SCAN_STOP_PPP
    ↓
CELL_SCAN_STOP_RUNSV
    ↓
CELL_SCAN_SEND_COPS (CLEARS BLACKLIST)
    ↓
CELL_SCAN_WAIT_COPS
    ↓
CELL_SCAN_PROCESS_COPS
    ↓
CELL_SCAN_TEST_CARRIER (loop for each)
    ↓
CELL_SCAN_SELECT_BEST
    ↓
CELL_SCAN_CONNECT_BEST
    ↓
CELL_SCAN_START_PPP
    ↓
CELL_WAIT_PPP_INTERFACE (NEW)
    ├─[Success]→ CELL_ONLINE
    └─[Timeout]→ Blacklist → CELL_SCAN_SELECT_BEST
```

### Detailed State Behaviors

#### CELL_ONLINE State
```
1. IF existing_connection THEN
     Monitor PPP status every 2 seconds
2. IF ppp_failed THEN
     Blacklist current carrier
     Transition to CELL_SCAN_STOP_PPP
3. IF network_manager_requests_rescan THEN
     Blacklist current carrier
     Transition to CELL_SCAN_STOP_PPP
4. ELSE
     Maintain connection
```

#### CELL_SCAN_SEND_COPS State
```
1. CLEAR all blacklist entries  // CRITICAL
2. Send "AT+COPS=?" command
3. Set 180-second timeout
4. Transition to CELL_SCAN_WAIT_COPS
5. Mark blacklist_cleared = true
```

#### CELL_SCAN_PROCESS_COPS State
```
1. Parse AT+COPS response
2. Remove duplicate carriers
3. Filter out empty/invalid entries
4. Store all valid carriers
5. Reset blacklist_cleared flag
6. IF carriers_found > 0 THEN
     Transition to CELL_SCAN_TEST_CARRIER
   ELSE
     Transition to CELL_SCAN_FAILED
```

---

## Blacklist Management Algorithm

### Adding to Blacklist
```algorithm
FUNCTION blacklist_carrier(mccmnc, reason):
    IF blacklist_count >= MAX_BLACKLIST THEN
        Remove oldest entry
    END IF

    entry = new BlacklistEntry
    entry.mccmnc = mccmnc
    entry.blacklist_time = current_time_ms()
    entry.failure_count = get_previous_failures(mccmnc) + 1
    entry.failure_reason = reason

    IF entry.failure_count >= 3 THEN
        entry.permanent = true  // This session only
    ELSE
        entry.permanent = false
    END IF

    blacklist[blacklist_count++] = entry
    LOG("Blacklisted %s: %s (count=%d)", mccmnc, reason, entry.failure_count)
END FUNCTION
```

### Checking Blacklist Status
```algorithm
FUNCTION is_blacklisted(mccmnc):
    current_time = current_time_ms()

    FOR each entry in blacklist:
        IF entry.mccmnc == mccmnc THEN
            IF entry.permanent THEN
                RETURN true  // Always skip
            END IF

            elapsed = current_time - entry.blacklist_time
            IF elapsed < BLACKLIST_TIMEOUT_MS THEN
                RETURN true  // Still blacklisted
            ELSE
                Remove entry from blacklist
                RETURN false  // Timeout expired
            END IF
        END IF
    END FOR

    RETURN false  // Not in blacklist
END FUNCTION
```

### Clearing Blacklist
```algorithm
FUNCTION clear_blacklist():
    LOG("Clearing all %d blacklisted carriers", blacklist_count)

    FOR each entry in blacklist:
        LOG("  - %s (failures=%d, reason=%s)",
            entry.mccmnc, entry.failure_count, entry.failure_reason)
    END FOR

    blacklist_count = 0
    memset(blacklist, 0, sizeof(blacklist))
    blacklist_cleared = true
END FUNCTION
```

---

## PPP Monitoring Algorithm

### PPP Establishment Check
```algorithm
FUNCTION monitor_ppp_establishment():
    IF ppp_state.start_time == 0 THEN
        ppp_state.start_time = current_time_ms()
        ppp_state.retry_count = 0
    END IF

    elapsed = current_time_ms() - ppp_state.start_time

    // Check every 2 seconds
    IF (current_time_ms() - ppp_state.last_check) >= 2000 THEN
        ppp_state.last_check = current_time_ms()

        // Stage 1: Interface exists (5-10 sec)
        IF NOT ppp_state.interface_up THEN
            IF check_interface_exists("ppp0") THEN
                ppp_state.interface_up = true
                LOG("PPP interface up after %d ms", elapsed)
            ELSE IF elapsed > 15000 THEN
                RETURN PPP_FAILED_NO_INTERFACE
            END IF
        END IF

        // Stage 2: Has IP address (10-20 sec)
        IF ppp_state.interface_up AND NOT ppp_state.has_ip THEN
            IF check_interface_has_ip("ppp0") THEN
                ppp_state.has_ip = true
                LOG("PPP has IP after %d ms", elapsed)
            ELSE IF elapsed > 25000 THEN
                RETURN PPP_FAILED_NO_IP
            END IF
        END IF

        // Stage 3: Internet connectivity (15-30 sec)
        IF ppp_state.has_ip AND NOT ppp_state.ping_success THEN
            IF test_internet_connectivity("ppp0") THEN
                ppp_state.ping_success = true
                LOG("PPP connected after %d ms", elapsed)
                RETURN PPP_SUCCESS
            ELSE IF elapsed > 35000 THEN
                RETURN PPP_FAILED_NO_INTERNET
            END IF
        END IF
    END IF

    RETURN PPP_IN_PROGRESS
END FUNCTION
```

### PPP Failure Handling
```algorithm
FUNCTION handle_ppp_failure(reason):
    current_carrier = get_current_carrier_mccmnc()

    ppp_state.retry_count++

    IF ppp_state.retry_count >= 2 THEN
        // Blacklist after 2 failures
        blacklist_carrier(current_carrier, reason)
        request_carrier_rescan()
    ELSE
        // Retry once with same carrier
        LOG("Retrying PPP for %s (attempt %d)",
            current_carrier, ppp_state.retry_count + 1)
        stop_ppp()
        sleep(2000)
        start_ppp()
        ppp_state.start_time = current_time_ms()
    END IF
END FUNCTION
```

---

## Carrier Selection Algorithm

### Complete Selection Process
```algorithm
FUNCTION select_best_carrier():
    best_idx = -1
    best_signal = -999
    blacklisted_count = 0
    total_carriers = carrier_count

    LOG("Selecting from %d carriers", total_carriers)

    // Phase 1: Try non-blacklisted carriers
    FOR i = 0 to carrier_count:
        carrier = carriers[i]

        IF is_blacklisted(carrier.mccmnc) THEN
            blacklisted_count++
            LOG("  %s: BLACKLISTED", carrier.name)
            CONTINUE
        END IF

        IF carrier.status == FORBIDDEN THEN
            LOG("  %s: FORBIDDEN", carrier.name)
            CONTINUE
        END IF

        IF carrier.signal > best_signal THEN
            best_signal = carrier.signal
            best_idx = i
            LOG("  %s: signal=%d (NEW BEST)", carrier.name, carrier.signal)
        ELSE
            LOG("  %s: signal=%d", carrier.name, carrier.signal)
        END IF
    END FOR

    // Phase 2: All blacklisted? Clear and retry
    IF best_idx == -1 AND blacklisted_count > 0 THEN
        LOG("All %d carriers blacklisted, clearing blacklist",
            blacklisted_count)
        clear_blacklist()

        // Re-evaluate with cleared blacklist
        FOR i = 0 to carrier_count:
            carrier = carriers[i]

            IF carrier.status == FORBIDDEN THEN
                CONTINUE
            END IF

            IF carrier.signal > best_signal THEN
                best_signal = carrier.signal
                best_idx = i
            END IF
        END FOR
    END IF

    // Phase 3: Select or fail
    IF best_idx >= 0 THEN
        selected_carrier_idx = best_idx
        LOG("SELECTED: %s (signal=%d)",
            carriers[best_idx].name, best_signal)
        RETURN SUCCESS
    ELSE
        LOG("FAILED: No viable carriers found")
        RETURN FAILURE
    END IF
END FUNCTION
```

---

## Integration Points

### 1. Network Manager → Cellular Manager

```c
// In process_network.c
IF ppp_failures >= THRESHOLD THEN
    cellular_request_rescan = true
    LOG("[NETMGR] Requesting cellular carrier change")
END IF

// In cellular_man.c
IF cellular_request_rescan THEN
    blacklist_carrier(current_carrier, "Network manager request")
    state = CELL_SCAN_STOP_PPP
    cellular_request_rescan = false
END IF
```

### 2. Cellular Manager → Network Manager

```c
// In cellular_man.c
IF ppp_established THEN
    cellular_ppp_ready = true
    LOG("[Cellular] PPP ready for network manager")
END IF

// In process_network.c
IF cellular_ppp_ready THEN
    test_interface("ppp0")
    cellular_ppp_ready = false
END IF
```

### 3. CLI Integration

```c
// Commands
"cell scan"        → Trigger manual scan (clears blacklist)
"cell operators"   → Display carriers and blacklist status
"cell blacklist"   → Show current blacklist
"cell clear"       → Manual blacklist clear
```

---

## Error Recovery

### Scenario 1: All Carriers Fail
```
1. Try each carrier sequentially
2. Blacklist each failure
3. When all blacklisted:
   - Clear blacklist
   - Wait 30 seconds
   - Restart scan
4. Repeat up to 3 cycles
5. If still failing, enter maintenance mode
```

### Scenario 2: PPP Stuck
```
1. Detect PPP process hung (no state change for 60s)
2. Force kill pppd and runsv
3. Clean up resources
4. Blacklist carrier
5. Move to next carrier
```

### Scenario 3: Modem Unresponsive
```
1. Detect AT command timeout
2. Reset modem (AT+CFUN=1,1)
3. Wait for modem ready
4. Restart from CELL_INIT
5. If fails 3 times, hardware reset
```

---

## Testing Scenarios

### Test 1: Normal Operation
```bash
# Start with no connection
1. System performs AT+COPS scan
2. Finds carriers: Verizon(29), AT&T(18), T-Mobile(15)
3. Selects Verizon (best signal)
4. PPP establishes successfully
5. System enters CELL_ONLINE state
✅ PASS: Connected to best carrier
```

### Test 2: Primary Carrier Fails
```bash
# Verizon connected but PPP fails
1. System detects PPP timeout (30s)
2. Blacklists Verizon
3. Triggers new scan (clears blacklist after COPS)
4. Finds same carriers
5. Skips Verizon (blacklisted)
6. Tries AT&T
7. PPP succeeds with AT&T
✅ PASS: Failed over to alternate carrier
```

### Test 3: All Carriers Fail Initially
```bash
# All carriers have poor signal/issues
1. Try Verizon → PPP fails → blacklist
2. Try AT&T → PPP fails → blacklist
3. Try T-Mobile → PPP fails → blacklist
4. All blacklisted → clear list
5. Retry Verizon → PPP succeeds
✅ PASS: Recovered after clearing blacklist
```

### Test 4: Location Change
```bash
# Device moves to new location
1. Connected to Verizon (weak signal)
2. PPP starts failing intermittently
3. Network manager requests rescan
4. AT+COPS finds better AT&T signal
5. Switches to AT&T automatically
✅ PASS: Adapted to location change
```

### Test 5: Persistent Failure
```bash
# Carrier has persistent issues
1. Verizon fails 3 times
2. Marked as permanent blacklist
3. Won't retry Verizon this session
4. Uses alternate carriers only
5. Blacklist clears on reboot
✅ PASS: Avoids problematic carrier
```

---

## Performance Considerations

### Timing Guidelines
- AT+COPS scan: 60-180 seconds
- Per-carrier test: 15-30 seconds
- PPP establishment: 10-35 seconds
- Blacklist timeout: 300 seconds
- State timeout: 20 seconds per state

### Resource Usage
- Memory: ~10KB for carrier data
- CPU: <5% during scan, <1% monitoring
- Serial: Exclusive during AT commands
- Network: Minimal until PPP established

---

## Conclusion

This operating algorithm provides a robust, self-healing cellular connection system that:

1. **Automatically recovers** from carrier failures
2. **Intelligently rotates** through available options
3. **Learns from failures** via blacklisting
4. **Adapts to changes** in network availability
5. **Coordinates seamlessly** with network management

The key innovation is **clearing the blacklist after each AT+COPS scan**, ensuring the system can always try fresh combinations while avoiding recent failures.

---

**Document Version**: 1.0
**Date**: 2025-11-22
**Time**: 11:50
**Implementation Status**: Specification Complete
**Next Step**: Code Implementation