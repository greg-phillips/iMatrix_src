# Cellular Scan - Non-Blocking State Machine Plan

**Date**: 2025-11-21
**Principle**: ALL operations must be NON-BLOCKING using state machine
**Architecture**: Sequential scan with state-based verification

---

## Core Principle

**CRITICAL**: cellular_man.c and process_network.c are state machines
- ✅ **Non-blocking**: Each state does minimal work and returns
- ✅ **Event-driven**: Progress happens on next iteration
- ❌ **No blocking waits**: No while loops, no sleep in states
- ❌ **No polling loops**: Use states with timeouts

---

## State Machine Flow

### New States Required

Add to cellular_man.c:
```c
typedef enum {
    // ... existing states ...

    // New scan states
    CELL_SCAN_STOP_PPP = 25,         // Stop PPP daemon
    CELL_SCAN_VERIFY_STOPPED = 26,   // Verify PPP stopped (with timeout)
    CELL_SCAN_GET_OPERATORS = 27,    // Send AT+COPS=?
    CELL_SCAN_WAIT_RESULTS = 28,     // Wait for operator list
    CELL_SCAN_TEST_CARRIER = 29,     // Test current carrier
    CELL_SCAN_WAIT_CSQ = 30,         // Wait for CSQ response
    CELL_SCAN_NEXT_CARRIER = 31,     // Move to next carrier
    CELL_SCAN_SELECT_BEST = 32,      // Select best operator
    CELL_SCAN_CONNECT_BEST = 33,     // Connect to best
    CELL_SCAN_START_PPP = 34,        // Start PPP
    CELL_SCAN_COMPLETE = 35,         // Scan complete
    CELL_SCAN_FAILED = 36,           // Scan failed, retry

} cellular_state_t;
```

---

## Detailed State Implementations

### State 1: CELL_SCAN_STOP_PPP

**Purpose**: Initiate PPP shutdown
**Duration**: Instant (non-blocking)
**Next State**: CELL_SCAN_VERIFY_STOPPED

```c
case CELL_SCAN_STOP_PPP:
    PRINTF("[Cellular Scan - State 1: Stopping PPP]\r\n");

    // Issue stop command (non-blocking)
    stop_pppd(true);

    // Set timeout for verification (5 seconds)
    scan_timeout = current_time + 5000;
    scan_retry_count = 0;

    // Transition to verify state
    cellular_state = CELL_SCAN_VERIFY_STOPPED;
    break;
```

**Key**: No waiting! Just issue command and move to next state.

---

### State 2: CELL_SCAN_VERIFY_STOPPED

**Purpose**: Check if PPP stopped (non-blocking check with timeout)
**Duration**: Instant check, returns immediately
**Next State**: CELL_SCAN_GET_OPERATORS or retry

```c
case CELL_SCAN_VERIFY_STOPPED:
    // Quick check if pppd is running (non-blocking)
    int pppd_running = system("pidof pppd >/dev/null 2>&1");

    if (pppd_running != 0)
    {
        // PPP stopped successfully
        PRINTF("[Cellular Scan - State 2: PPP stopped successfully]\r\n");
        cellular_state = CELL_SCAN_GET_OPERATORS;
    }
    else if (imx_is_later(current_time, scan_timeout))
    {
        // Timeout - force kill
        PRINTF("[Cellular Scan - State 2: Timeout, forcing PPP kill]\r\n");
        system("killall -9 pppd 2>/dev/null");

        // Give it one more iteration to die
        scan_retry_count++;
        if (scan_retry_count > 3)
        {
            PRINTF("[Cellular Scan - ERROR: Cannot stop PPP, aborting scan]\r\n");
            cellular_state = CELL_SCAN_FAILED;
        }
        else
        {
            scan_timeout = current_time + 1000;  // 1 more second
        }
    }
    // else: Still waiting, check again next iteration (non-blocking return)
    break;
```

**Key**:
- Check once per iteration (no loop)
- Track timeout using current_time
- Return immediately
- Will be called again next iteration

---

### State 3: CELL_SCAN_GET_OPERATORS

**Purpose**: Send AT+COPS=? to get operator list
**Duration**: Instant (command send)
**Next State**: CELL_SCAN_WAIT_RESULTS

```c
case CELL_SCAN_GET_OPERATORS:
    PRINTF("[Cellular Scan - State 3: Requesting operator list]\r\n");

    // Send scan command (non-blocking)
    send_AT_command(cell_fd, "+COPS=?");

    // Initialize response buffer
    memset(response_buffer, 0, sizeof(response_buffer));
    initATResponseState(&state, current_time);

    // Set timeout for response (180 seconds - scans can be slow)
    scan_timeout = current_time + 180000;

    // Transition to wait state
    cellular_state = CELL_SCAN_WAIT_RESULTS;
    break;
```

---

### State 4: CELL_SCAN_WAIT_RESULTS

**Purpose**: Wait for AT+COPS=? response
**Duration**: Returns immediately, called repeatedly
**Next State**: CELL_SCAN_TEST_CARRIER

```c
case CELL_SCAN_WAIT_RESULTS:
    // Check for response (non-blocking)
    ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 180);

    if (status == AT_COMPLETE)
    {
        PRINTF("[Cellular Scan - State 4: Operator list received]\r\n");

        // Parse operators from response_buffer
        scan_operator_count = parse_cops_operators(response_buffer, scan_operators, MAX_OPERATORS);

        PRINTF("[Cellular Scan - Found %d operators]\r\n", scan_operator_count);

        // Start testing first carrier
        scan_current_index = 0;
        cellular_state = CELL_SCAN_TEST_CARRIER;
    }
    else if (status == AT_ERROR || imx_is_later(current_time, scan_timeout))
    {
        PRINTF("[Cellular Scan - State 4: Failed to get operator list]\r\n");
        cellular_state = CELL_SCAN_FAILED;
    }
    // else: Still waiting (AT_PENDING), return and check next iteration
    break;
```

**Key**: Uses existing storeATResponse() which is already non-blocking!

---

### State 5: CELL_SCAN_TEST_CARRIER

**Purpose**: Connect to operator and request signal strength
**Duration**: Instant (command send)
**Next State**: CELL_SCAN_WAIT_CSQ

```c
case CELL_SCAN_TEST_CARRIER:
    // Check if we've tested all operators
    if (scan_current_index >= scan_operator_count)
    {
        PRINTF("[Cellular Scan - State 5: All operators tested]\r\n");
        cellular_state = CELL_SCAN_SELECT_BEST;
        break;
    }

    operator_info_t *op = &scan_operators[scan_current_index];

    // Skip if blacklisted
    if (op->blacklisted)
    {
        PRINTF("[Cellular Scan - State 5: Skipping blacklisted: %s]\r\n", op->operator_name);
        scan_current_index++;
        // Stay in this state, will process next operator on next iteration
        break;
    }

    PRINTF("[Cellular Scan - State 5: Testing operator %s (%s)]\r\n",
           op->operator_name, op->operator_id);

    // Connect to this operator (non-blocking send)
    char cmd[64];
    snprintf(cmd, sizeof(cmd), "+COPS=1,2,\"%s\"", op->operator_id);
    send_AT_command(cell_fd, cmd);

    // Wait for connection, then query signal
    scan_timeout = current_time + 10000;  // 10 sec to connect
    scan_substep = 0;  // Track sub-states: 0=connect, 1=CSQ
    cellular_state = CELL_SCAN_WAIT_CSQ;
    break;
```

---

### State 6: CELL_SCAN_WAIT_CSQ

**Purpose**: Wait for connection, then get CSQ
**Duration**: Returns immediately
**Next State**: CELL_SCAN_NEXT_CARRIER

```c
case CELL_SCAN_WAIT_CSQ:
    operator_info_t *op = &scan_operators[scan_current_index];

    if (scan_substep == 0)
    {
        // Waiting for AT+COPS connection response
        ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 10);

        if (status == AT_COMPLETE)
        {
            PRINTF("[Cellular Scan - State 6: Connected to %s]\r\n", op->operator_name);

            // Now request signal strength
            send_AT_command(cell_fd, "+CSQ");
            memset(response_buffer, 0, sizeof(response_buffer));
            initATResponseState(&state, current_time);

            scan_timeout = current_time + 5000;  // 5 sec for CSQ
            scan_substep = 1;
        }
        else if (status == AT_ERROR || imx_is_later(current_time, scan_timeout))
        {
            PRINTF("[Cellular Scan - State 6: Failed to connect to %s]\r\n", op->operator_name);
            op->signal_strength = -1;  // Mark as failed
            op->tested = true;
            cellular_state = CELL_SCAN_NEXT_CARRIER;
        }
    }
    else if (scan_substep == 1)
    {
        // Waiting for AT+CSQ response
        ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 5);

        if (status == AT_COMPLETE)
        {
            // Parse CSQ from response
            op->signal_strength = parse_csq_response(response_buffer);
            op->tested = true;

            PRINTF("[Cellular Scan - State 6: %s signal strength: %d]\r\n",
                   op->operator_name, op->signal_strength);

            cellular_state = CELL_SCAN_NEXT_CARRIER;
        }
        else if (status == AT_ERROR || imx_is_later(current_time, scan_timeout))
        {
            PRINTF("[Cellular Scan - State 6: Failed to get CSQ for %s]\r\n", op->operator_name);
            op->signal_strength = -1;
            op->tested = true;
            cellular_state = CELL_SCAN_NEXT_CARRIER;
        }
    }
    break;
```

**Key**: Uses substeps for multi-phase operation, still non-blocking!

---

### State 7: CELL_SCAN_NEXT_CARRIER

**Purpose**: Move to next carrier in list
**Duration**: Instant
**Next State**: CELL_SCAN_TEST_CARRIER or CELL_SCAN_SELECT_BEST

```c
case CELL_SCAN_NEXT_CARRIER:
    scan_current_index++;

    if (scan_current_index >= scan_operator_count)
    {
        PRINTF("[Cellular Scan - State 7: All carriers tested]\r\n");
        cellular_state = CELL_SCAN_SELECT_BEST;
    }
    else
    {
        PRINTF("[Cellular Scan - State 7: Moving to next carrier (%d/%d)]\r\n",
               scan_current_index + 1, scan_operator_count);
        cellular_state = CELL_SCAN_TEST_CARRIER;
    }
    break;
```

---

### State 8: CELL_SCAN_SELECT_BEST

**Purpose**: Select operator with best signal
**Duration**: Instant (computation)
**Next State**: CELL_SCAN_CONNECT_BEST

```c
case CELL_SCAN_SELECT_BEST:
    PRINTF("[Cellular Scan - State 8: Selecting best operator]\r\n");

    int best_idx = -1;
    int best_signal = -1;

    // Find operator with best signal (not blacklisted, tested successfully)
    for (int i = 0; i < scan_operator_count; i++)
    {
        operator_info_t *op = &scan_operators[i];

        if (!op->blacklisted && op->tested && op->signal_strength > best_signal)
        {
            best_signal = op->signal_strength;
            best_idx = i;
        }
    }

    if (best_idx < 0)
    {
        PRINTF("[Cellular Scan - State 8: No suitable operator found]\r\n");
        cellular_state = CELL_SCAN_FAILED;
    }
    else
    {
        scan_best_operator_idx = best_idx;
        PRINTF("[Cellular Scan - State 8: Best operator: %s (signal=%d)]\r\n",
               scan_operators[best_idx].operator_name,
               scan_operators[best_idx].signal_strength);
        cellular_state = CELL_SCAN_CONNECT_BEST;
    }
    break;
```

---

### State 9: CELL_SCAN_CONNECT_BEST

**Purpose**: Connect to best operator
**Duration**: Instant (command send)
**Next State**: CELL_SCAN_START_PPP

```c
case CELL_SCAN_CONNECT_BEST:
    operator_info_t *best = &scan_operators[scan_best_operator_idx];

    PRINTF("[Cellular Scan - State 9: Connecting to %s]\r\n", best->operator_name);

    // Connect to best operator
    char cmd[64];
    snprintf(cmd, sizeof(cmd), "+COPS=1,2,\"%s\"", best->operator_id);
    send_AT_command(cell_fd, cmd);

    // Wait for connection
    memset(response_buffer, 0, sizeof(response_buffer));
    initATResponseState(&state, current_time);
    scan_timeout = current_time + 10000;  // 10 sec timeout

    cellular_state = CELL_SCAN_START_PPP;
    break;
```

---

### State 10: CELL_SCAN_START_PPP

**Purpose**: Wait for connection, then start PPP
**Duration**: Returns immediately
**Next State**: CELL_SCAN_COMPLETE

```c
case CELL_SCAN_START_PPP:
    // Wait for connection response (non-blocking)
    ATResponseStatus status = storeATResponse(&state, cell_fd, current_time, 10);

    if (status == AT_COMPLETE)
    {
        PRINTF("[Cellular Scan - State 10: Connected, starting PPP]\r\n");

        // Start PPP (non-blocking)
        start_pppd();

        // Mark scan complete
        cellular_state = CELL_SCAN_COMPLETE;
    }
    else if (status == AT_ERROR || imx_is_later(current_time, scan_timeout))
    {
        PRINTF("[Cellular Scan - State 10: Failed to connect to best operator]\r\n");
        cellular_state = CELL_SCAN_FAILED;
    }
    // else: Still waiting, return and check next iteration
    break;
```

---

### State 11: CELL_SCAN_COMPLETE

**Purpose**: Finalize scan and return to normal operation
**Duration**: Instant
**Next State**: CELL_ONLINE

```c
case CELL_SCAN_COMPLETE:
    PRINTF("[Cellular Scan - State 11: Scan complete]\r\n");
    PRINTF("[Cellular Scan - SCAN COMPLETED - PPP operations can resume]\r\n");

    // Clear scanning flag - process_network can now use PPP
    cellular_scanning = false;
    cellular_now_ready = true;
    cellular_link_reset = false;

    // Return to normal operation
    cellular_state = CELL_ONLINE;
    break;
```

---

### State 12: CELL_SCAN_FAILED

**Purpose**: Handle scan failure, prepare for retry
**Duration**: Instant
**Next State**: CELL_INIT or CELL_DELAY

```c
case CELL_SCAN_FAILED:
    PRINTF("[Cellular Scan - State 12: Scan failed]\r\n");

    scan_failure_count++;

    if (scan_failure_count >= MAX_SCAN_RETRIES)
    {
        PRINTF("[Cellular Scan - ERROR: Max scan retries exceeded, reinitializing]\r\n");
        cellular_state = CELL_INIT;
    }
    else
    {
        PRINTF("[Cellular Scan - Will retry scan in 30 seconds (attempt %d/%d)]\r\n",
               scan_failure_count, MAX_SCAN_RETRIES);

        delay_time = current_time + 30000;  // 30 sec delay
        return_cellular_state = CELL_SCAN_STOP_PPP;  // Retry from start
        cellular_state = CELL_DELAY;
    }

    // Clear scanning flag so process_network doesn't wait forever
    cellular_scanning = false;
    break;
```

---

## Entry Point: Triggering Scan

### From User Command or Automatic Retry

```c
else if (cellular_flags.cell_scan)
{
    PRINTF("[Cellular Connection - SCAN REQUESTED]\r\n");
    PRINTF("[Cellular Connection - SCAN STARTED - All PPP operations will be suspended]\r\n");

    // Set scanning flag - tells process_network to wait
    cellular_scanning = true;
    cellular_now_ready = false;

    // Initialize scan state
    scan_operator_count = 0;
    scan_current_index = 0;
    scan_best_operator_idx = -1;
    scan_failure_count = 0;

    // Clear flag
    cellular_flags.cell_scan = false;

    // Start scan state machine
    cellular_state = CELL_SCAN_STOP_PPP;
}
```

---

## Data Structures

### Add to cellular_man.c

```c
// Operator information structure
typedef struct {
    char operator_id[16];        // Numeric ID (e.g., "310260")
    char operator_name[64];      // Name (e.g., "T-Mobile US")
    int signal_strength;         // CSQ value (0-31, or -1 if failed)
    bool blacklisted;            // Is this operator blacklisted?
    bool tested;                 // Have we tested this operator?
} operator_info_t;

// Scan state variables (static in cellular_man.c)
static operator_info_t scan_operators[MAX_OPERATORS];  // Max 20 operators
static int scan_operator_count = 0;
static int scan_current_index = 0;
static int scan_best_operator_idx = -1;
static imx_time_t scan_timeout = 0;
static int scan_retry_count = 0;
static int scan_failure_count = 0;
static int scan_substep = 0;  // For multi-phase states

#define MAX_OPERATORS 20
#define MAX_SCAN_RETRIES 3
```

---

## process_network.c Integration

### Passive Waiting During Scan

```c
// In main state machine, check at top of loop
if (imx_is_cellular_scanning())
{
    // Cellular is scanning - be completely passive about PPP
    NETMGR_LOG_PPP0(ctx, "Cellular scan in progress - waiting passively");

    // Don't launch ping tests
    // Don't try to establish routes
    // Don't mark PPP as failed
    // Just wait

    return;  // Early exit, do nothing this iteration
}
```

### Request Scan on Failure

```c
// In ping failure handling
if (ppp_failure_count >= MAX_PPP_FAILURES)
{
    NETMGR_LOG_PPP0(ctx, "PPP failed %d times, requesting operator scan",
                    MAX_PPP_FAILURES);

    // Request rescan
    imx_request_cellular_scan();

    ppp_failure_count = 0;
}
```

### Add Request Function

```c
// In cellular_man.c, add:
void imx_request_cellular_scan(void)
{
    PRINTF("[Cellular Connection - Scan requested by network manager]\r\n");
    cellular_flags.cell_scan = true;
}
```

---

## State Transition Diagram

```
User/Auto Request
       ↓
[CELL_SCAN_STOP_PPP] ──→ Issue stop_pppd()
       ↓
[CELL_SCAN_VERIFY_STOPPED] ──→ Check pidof (non-blocking)
       ↓ (if stopped)           ↑ (if timeout, retry)
[CELL_SCAN_GET_OPERATORS] ──→ Send AT+COPS=?
       ↓
[CELL_SCAN_WAIT_RESULTS] ──→ Wait for response
       ↓ (when received)        ↑ (still pending)
[CELL_SCAN_TEST_CARRIER] ──→ Send AT+COPS=1,2,"id"
       ↓
[CELL_SCAN_WAIT_CSQ] ──────→ Wait for connection
       ↓                        ↓ (substep 1)
       └─────→ Send AT+CSQ ────→ Wait for CSQ
       ↓ (when received)
[CELL_SCAN_NEXT_CARRIER] ──→ Increment index
       ↓
       ├──→ [CELL_SCAN_TEST_CARRIER] (if more)
       └──→ [CELL_SCAN_SELECT_BEST] (if done)
              ↓
       [CELL_SCAN_CONNECT_BEST] ──→ Connect to best
              ↓
       [CELL_SCAN_START_PPP] ──→ Wait, then start_pppd()
              ↓
       [CELL_SCAN_COMPLETE] ──→ Clear flags, go to CELL_ONLINE


(Any state) ──[timeout/error]──→ [CELL_SCAN_FAILED] ──→ Retry or CELL_INIT
```

---

## Key Non-Blocking Principles

### ✅ Correct (Non-Blocking)

```c
case CELL_SCAN_VERIFY_STOPPED:
    if (pppd_stopped())
        cellular_state = NEXT_STATE;
    else if (timeout)
        handle_timeout();
    // else: return, check again next iteration
    break;
```

### ❌ Wrong (Blocking)

```c
case CELL_SCAN_VERIFY_STOPPED:
    while (!pppd_stopped() && !timeout) {  // ❌ BLOCKS!
        check_status();
        sleep(100);
    }
    break;
```

---

## Testing Strategy

### Test 1: State Progression

**Monitor state transitions**:
```bash
grep "Cellular Scan - State" log.txt
```

**Expected**:
```
[Cellular Scan - State 1: Stopping PPP]
[Cellular Scan - State 2: PPP stopped successfully]
[Cellular Scan - State 3: Requesting operator list]
[Cellular Scan - State 4: Operator list received]
[Cellular Scan - State 5: Testing operator T-Mobile]
[Cellular Scan - State 6: Connected to T-Mobile]
[Cellular Scan - State 6: T-Mobile signal strength: 25]
[Cellular Scan - State 7: Moving to next carrier]
... (repeat for each carrier)
[Cellular Scan - State 8: Best operator: T-Mobile (signal=25)]
[Cellular Scan - State 9: Connecting to T-Mobile]
[Cellular Scan - State 10: Connected, starting PPP]
[Cellular Scan - State 11: Scan complete]
```

### Test 2: Non-Blocking Verification

**Check system remains responsive**:
```bash
# During scan, system should respond to other commands
echo "help" | ./FC-1  # Should work even during scan
```

### Test 3: Timeout Handling

**Simulate stuck PPP**:
```bash
# Manually block pppd from stopping
# System should timeout and force kill
```

---

## Advantages of State Machine Approach

### vs Blocking Loops

| Aspect | State Machine | Blocking Loop |
|--------|---------------|---------------|
| **Responsive** | ✅ Always responsive | ❌ Frozen during wait |
| **Other Tasks** | ✅ Continue running | ❌ Blocked |
| **Timeout** | ✅ Natural with time checks | ⚠️ Must implement |
| **Debugging** | ✅ Clear state transitions | ❌ Hard to see where stuck |
| **Testability** | ✅ Easy to inject delays | ❌ Hard to test |

---

## Implementation Checklist

### cellular_man.c
- [ ] Add 12 new state enums
- [ ] Add operator_info_t structure
- [ ] Add scan state variables
- [ ] Implement CELL_SCAN_STOP_PPP
- [ ] Implement CELL_SCAN_VERIFY_STOPPED (with timeout)
- [ ] Implement CELL_SCAN_GET_OPERATORS
- [ ] Implement CELL_SCAN_WAIT_RESULTS
- [ ] Implement CELL_SCAN_TEST_CARRIER
- [ ] Implement CELL_SCAN_WAIT_CSQ (with substeps)
- [ ] Implement CELL_SCAN_NEXT_CARRIER
- [ ] Implement CELL_SCAN_SELECT_BEST
- [ ] Implement CELL_SCAN_CONNECT_BEST
- [ ] Implement CELL_SCAN_START_PPP
- [ ] Implement CELL_SCAN_COMPLETE
- [ ] Implement CELL_SCAN_FAILED
- [ ] Add parse_cops_operators() helper
- [ ] Add parse_csq_response() helper
- [ ] Add imx_request_cellular_scan() export

### process_network.c
- [ ] Add early exit if cellular_scanning
- [ ] Add imx_request_cellular_scan() call on PPP failure
- [ ] Remove complex flag checking (replaced by early exit)

### Testing
- [ ] Manual scan command
- [ ] Verify non-blocking (system responsive)
- [ ] Verify timeout handling (PPP won't stop)
- [ ] Verify carrier testing (multiple operators)
- [ ] Verify best selection (picks highest CSQ)
- [ ] Verify retry on failure
- [ ] Verify integration with process_network

---

## Estimated Timeline

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Add state enums and structures | 0.5h |
| 2 | Implement PPP stop/verify states | 1h |
| 3 | Implement operator scan states | 1.5h |
| 4 | Implement carrier testing loop | 2h |
| 5 | Implement selection/connect states | 1h |
| 6 | Add helper functions | 1h |
| 7 | Integrate with process_network | 1h |
| 8 | Testing and debugging | 3h |
| 9 | Documentation | 1h |
| **Total** | | **12 hours** |

---

## Success Criteria

✅ **All operations non-blocking**
- No while loops in states
- Each state returns immediately
- Progress on next iteration

✅ **Proper timeout handling**
- 5 sec for PPP stop
- 180 sec for operator scan
- 10 sec for carrier connection
- 5 sec for CSQ query

✅ **Complete carrier testing**
- Tests each non-blacklisted operator
- Gets real CSQ for each
- Selects best based on signal

✅ **Robust error handling**
- Handles PPP won't stop
- Handles scan timeout
- Handles connection failures
- Retries up to 3 times

✅ **Clean integration**
- process_network waits passively
- No interference during scan
- Clean transition when complete

---

**Document Version**: 2.0 (Non-Blocking)
**Date**: 2025-11-21
**Status**: Ready for Implementation
**Architecture**: State Machine (Non-Blocking)
