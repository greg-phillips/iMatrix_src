<!--
AUTO-GENERATED PROMPT - ADVANCED COMPLEXITY
Generated from: specs/examples/advanced/ppp_refactoring.yaml
Generated on: 2025-11-17 09:22:38
Schema version: 1.0
Complexity level: advanced

To modify this prompt, edit the source YAML file and regenerate.
-->

# PPP0 Connection Refactoring Plan

**Date:** 2025-11-16
**Branch:** bugfix/network-stability
**Objective:** Refactor PPP connection management to use PPPD Daemon approach for better logging and control
**Estimated Effort:** 4-6 hours development + 2 hours testing
**Priority:** high

---

## Executive Summary

Refactor PPP connection management to use PPPD Daemon approach for better logging and control

This refactoring focuses specifically on the cellular PPP0 connection
management subsystem within the network manager. The goal is to replace
the simple pon/poff approach with a robust daemon-based system that
provides detailed logging and state visibility.


---

## Current Implementation Analysis

### Workflow

1. **cellular_man.c state machine initializes modem and registers with carrier (AT&T)**
   - Location: `cellular_man.c:2064`
2. **At DONE_INIT_REGISTER state: Sets cellular_now_ready = true**
   - Location: `cellular_man.c:2064`
3. **process_network.c detects ready flag via imx_is_cellular_now_ready()**
   - Location: `process_network.c:4531`
4. **Calls start_pppd() from cellular_man.c**
   - Location: `cellular_man.c:1797`
5. **start_pppd() executes 'pon' command**
   - Location: `cellular_man.c:1797`
6. **Waits up to 30 seconds for ppp0 device with IP address**
   - Location: `cellular_man.c:1800-1816`

### Problems

- **Missing Configuration** (Severity: high)
  - pon requires /etc/ppp/peers/provider which doesn't exist
- **No Logging** (Severity: high)
  - Cannot see chat script execution, LCP/IPCP negotiation
- **No State Visibility** (Severity: medium)
  - Just waiting for IP, no intermediate status
- **Limited Diagnostics** (Severity: high)
  - Connect script failed with no details
- **No Error Recovery** (Severity: medium)
  - Cannot distinguish between different failure modes

---

## Proposed Architecture

### New Module: ppp_connection.c

**Purpose:** To be defined

**Location:** `~/iMatrix/iMatrix_Client/iMatrix/IMX_Platform/LINUX_Platform/networking/ppp_connection.c`

**Responsibilities:**
- Start/stop PPPD daemon via /etc/start_pppd.sh
- Parse /var/log/pppd/current for connection state
- Extract IP addresses, DNS servers, error messages
- Provide structured status to callers
- Comprehensive logging with PPP-specific debug flags

### Data Structures

#### ppp_state_t (enum)

PPP connection states derived from log parsing

```c
typedef enum {
    PPP_STATE_STOPPED,
    PPP_STATE_STARTING,
    PPP_STATE_CHAT_RUNNING,
    PPP_STATE_LCP_NEGOTIATION,
    PPP_STATE_IPCP_NEGOTIATION,
    PPP_STATE_CONNECTED,
    PPP_STATE_ERROR,
} ppp_state_t;
```

#### ppp_connection_status_t (struct)

PPP connection status information

```c
typedef struct {
    ppp_state_t state;
    bool pppd_running;
    bool ppp0_device_exists;
    bool ppp0_has_ip;
    char[16] local_ip;
    char[16] remote_ip;
    char[16] dns_primary;
    char[16] dns_secondary;
    uint32_t connection_time_ms;
    char[256] last_error;
} ppp_connection_status_t;
```

#### ppp_health_check_t (struct)

PPP connection health indicators from log analysis

```c
typedef struct {
    bool chat_script_ok;
    bool lcp_negotiated;
    bool ipcp_negotiated;
    bool ip_assigned;
    bool ip_up_script_ok;
    char[128] failure_reason;
} ppp_health_check_t;
```

---

## Implementation Phases

### Phase 1: Create New Module (ppp_connection.c/h)

**Tasks:**
- [ ] Define data structures in header
- [ ] Implement ppp_connection_init() - prerequisite checking
- [ ] Implement ppp_connection_start() - daemon startup
- [ ] Implement ppp_connection_stop() - daemon shutdown
- [ ] Implement log parsing: ppp_connection_parse_log()
- [ ] Implement status: ppp_connection_get_status()
- [ ] Implement health check: ppp_connection_check_health()
- [ ] Add helper functions
- [ ] Add comprehensive Doxygen comments
- [ ] Update CMakeLists.txt to include new source file

**Deliverable:** Working ppp_connection module with comprehensive logging

### Phase 2: Deprecate Old Functions in cellular_man.c

**Tasks:**
- [ ] Rename start_pppd() to start_pppd_deprecated()
- [ ] Rename stop_pppd() to stop_pppd_deprecated()
- [ ] Add @deprecated Doxygen tags
- [ ] Create new wrapper functions calling ppp_connection module
- [ ] Update cellular_man.h function declarations
- [ ] Add #include ppp_connection.h

**Deliverable:** Backward compatible API with deprecated old functions

### Phase 3: Enhance process_network.c Monitoring

**Tasks:**
- [ ] Replace simple device check with detailed status monitoring
- [ ] Add state-aware logging for each PPP state
- [ ] Add health check on timeout/failure
- [ ] Include recent log output in error diagnostics
- [ ] Add ppp_connection_init() call in network_manager_init()

**Deliverable:** Enhanced monitoring with detailed state-aware logs

### Phase 4: Testing and Validation

**Tasks:**
- [ ] Test normal connection flow (STARTING → CONNECTED)
- [ ] Test connection failures (chat script, LCP, IPCP)
- [ ] Test connection drop and recovery
- [ ] Verify log parsing accuracy
- [ ] Long-run test: 30+ minutes with multiple cycles

**Deliverable:** Fully tested and validated refactored system

---

## Design Decisions & Rationale

### Wrapper Functions (Chosen Approach)

Keep start_pppd() / stop_pppd() names in cellular_man.c as thin wrappers.
- Zero changes required in process_network.c call sites
- Maintains API compatibility
- Easy to switch back if issues found
- Clear separation: cellular_man.c owns interface, ppp_connection.c owns implementation

### Log Read Caching (1 Second)

Cache log file reads for 1 second to reduce I/O.
- process_network() calls every 1 second
- Log file doesn't change faster than that
- Reduces filesystem I/O
- Still responsive (1s max staleness)

### Retry Logic in process_network.c

Keep retry management in process_network.c, not ppp_connection.c.
- Retry policy tied to network manager state machine
- Needs coordination with interface selection
- Cellular blacklisting logic already in process_network
- Separation of concerns: ppp_connection manages daemon, network manager manages policy

### 30-Second Timeout (Keep Current)

Maintain 30-second timeout despite 3-second normal connection time.
- Working log shows 3 seconds in ideal conditions
- Weak signal areas may take longer
- Chat script retries AT commands
- LCP/IPCP can timeout and retry
- Conservative timeout prevents premature failures

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Log parsing errors crash system | Robust error handling, bounds checking, fopen error checks |
| Log file too large causes memory issues | Read only last N lines (default 100), limit buffer sizes |
| Cache causes stale state data | 1-second cache timeout, invalidate on explicit calls |
| Breaking existing PPP functionality | Keep deprecated functions, use wrappers for compatibility |
| /etc/start_pppd.sh doesn't exist | Check in init, fail gracefully with clear error message |

---

## Success Criteria

### Functional Requirements

- PPP0 connects successfully using /etc/start_pppd.sh
- Logs show clear state progression: CHAT → LCP → IPCP → CONNECTED
- IP address, DNS servers logged on successful connection
- Connection failures show detailed error messages with actionable diagnostics
- No 'Connect script failed' without explanation
- State timeouts identify exact stuck state

### Quality Requirements

- Backward compatible - no changes required in cellular_man state machine
- Build clean with zero warnings
- Works in headless/production environment
- Memory-safe log parsing (no leaks, no crashes)

### Performance Requirements

- Normal connection time: 3-5 seconds
- Log parsing overhead: < 10ms per check
- Memory footprint: < 50KB additional

---

## Deliverables

1. **Plan Document:** docs/${prompt_name}.md
2. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
3. Detailed plan document with all aspects and detailed todo list for review before commencing implementation.
4. Once plan is approved implement and check off the items on the todo list as they are completed.
5. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings.
6. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
7. Once work is completed successfully add a concise description to the plan document of the work undertaken.
8. Update all documents with relevant details

**Additional Deliverables:**
- ppp_connection.c module with comprehensive Doxygen comments
- Integration test results showing state transitions
- Performance comparison: old vs new approach
- Updated CLAUDE.md with PPP connection module info

**Metrics to Track:**
- Connection time: old vs new (expect <3s with new approach)
- Log verbosity: lines per connection attempt
- Error diagnosis time: time to identify failure root cause
- Number of recompilations required for syntax errors
- Time taken in both elapsed and actual work time

---

## Special Instructions

### Pre-Implementation Steps

- Review /var/log/pppd/current log files from working system
- Understand chat script flow and AT command sequence
- Familiarize with LCP/IPCP negotiation process

### System Files Required

The following files must exist on the target system:

- **`/etc/start_pppd.sh`** - PPPD startup script (must be executable)
- **`/var/log/pppd/`** - Log directory (must be writable)
- **`/etc/chatscripts/quake-gemalto`** - Chat script with AT commands
- **`/etc/ppp/ip-up`** - Script executed when connection established
- **`/etc/ppp/ip-down`** - Script executed when connection terminated

---

## Questions

The following questions should be addressed before or during implementation:

**Q:** Cache timeout for log reads?
- Suggested: 1 second (matches process_network call frequency)
- **Answer:** 1 second

**Q:** Timeout before declaring connection failed?
- Suggested: 30 seconds (current value, conservative)
- **Answer:** 30 seconds

**Q:** Should we add CLI command to view PPP status?
- Suggested: Yes, useful for diagnostics
- **Answer:** _To be determined_

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** specs/examples/advanced/ppp_refactoring.yaml
**Generated:** 2025-11-17 09:22:38
**Estimated Effort:** 4-6 hours development + 2 hours testing

---