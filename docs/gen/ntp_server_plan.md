# Fleet-Connect-1 NTP Server DHCP Option Implementation Plan

**Date:** 2026-01-09
**Author:** Claude Code
**Status:** Plan - Awaiting Approval
**Branch:** feature/ntp-dhcp-option

---

## Executive Summary

Implement a configurable NTP server advertisement via DHCP for Fleet-Connect-1 devices. The NTP server option (DHCP option 42) will be advertised to DHCP clients when:
1. The interface is in **server mode** (eth0 always, wlan0 in AP mode)
2. The **advertise_ntp_server** configuration bit is enabled

A new CLI command `ntp server` will allow enabling/disabling this feature per-interface.

---

## 1. Current Branch Information

| Repository | Current Branch |
|------------|----------------|
| iMatrix | Aptera_1_Clean |
| Fleet-Connect-1 | Aptera_1_Clean |

---

## 2. Requirements Summary

| Requirement | Details |
|-------------|---------|
| NTP on eth0 | Only when eth0 is in server mode AND `advertise_ntp_server` bit is set |
| NTP on wlan0 | Only when wlan0 is in AP/server mode AND `advertise_ntp_server` bit is set |
| Configuration | New bit flag in `network_interfaces_t` structure |
| CLI Command | New `ntp server` command to set/clear the bit |
| Persistence | Configuration saved via `imatrix_save_config()` |
| Default | Disabled (bit = 0) for backward compatibility |

---

## 3. Architecture Overview

```
+------------------+     +-------------------+     +--------------------+
|   CLI Command    |     |  Device Config    |     |  DHCP Config Gen   |
|   ntp server     | --> | network_interfaces| --> | dhcp_server_config |
|   on/off/status  |     | .advertise_ntp    |     | write_dhcp_config  |
+------------------+     +-------------------+     +--------------------+
                                                            |
                                                            v
                                                   +--------------------+
                                                   | udhcpd.eth0.conf   |
                                                   | option ntpsrv x.x  |
                                                   +--------------------+
```

---

## 4. Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/common.h` | Add `advertise_ntp_server` bit to `network_interfaces_t` |
| `iMatrix/cli/cli_ntp.c` | Extend to handle `ntp server` subcommand |
| `iMatrix/cli/cli_ntp.h` | No changes needed (function signature unchanged) |
| `iMatrix/cli/cli.c` | Update help text for `ntp` command |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c` | Add NTP option to DHCP config generation |
| `tools/test_ntp_server.py` | **NEW** - Python script to test NTP server from client |

---

## 5. Detailed Implementation Plan

### Phase 1: Configuration Structure Changes

#### 5.1.1 Modify `network_interfaces_t` in `common.h`

**File:** `iMatrix/common.h` (lines 419-432)

**Current:**
```c
typedef struct network_interfaces_ {
    char name[ IMX_MAX_INTERFACE_NAME_LENGTH + 1 ];
    interface_mode_t mode;
    char ip_address[ 16 ];
    char netmask[ 16 ];
    char gateway[ 16 ];
    char dhcp_start[ 16 ];
    char dhcp_end[ 16 ];
    uint32_t dhcp_lease_time;
    unsigned int enabled                : 1;    // 0
    unsigned int use_connection_sharing : 1;    // 1
    unsigned int use_dhcp_server        : 1;    // 2
    unsigned int reserved : 29;                 // 3 - 31
} network_interfaces_t;
```

**Change to:**
```c
typedef struct network_interfaces_ {
    char name[ IMX_MAX_INTERFACE_NAME_LENGTH + 1 ];
    interface_mode_t mode;
    char ip_address[ 16 ];
    char netmask[ 16 ];
    char gateway[ 16 ];
    char dhcp_start[ 16 ];
    char dhcp_end[ 16 ];
    uint32_t dhcp_lease_time;
    unsigned int enabled                : 1;    // 0 - is this interface being used
    unsigned int use_connection_sharing : 1;    // 1 - Use connection sharing for this interface
    unsigned int use_dhcp_server        : 1;    // 2 - Enable DHCP server on this interface
    unsigned int advertise_ntp_server   : 1;    // 3 - Advertise this device as NTP server via DHCP
    unsigned int reserved : 28;                 // 4 - 31
} network_interfaces_t;
```

**Notes:**
- Uses bit 3 from reserved pool
- Default value will be 0 (disabled) for backward compatibility
- No structure size change (still fits in 32-bit bitfield)

---

### Phase 2: CLI Command Implementation

#### 5.2.1 Extend `cli_ntp()` in `cli_ntp.c`

**File:** `iMatrix/cli/cli_ntp.c`

**Current function:** Simple NTP sync trigger (~20 lines)

**New implementation:** Extended to handle subcommands

```c
/**
 * @brief NTP CLI command handler
 *
 * Supports:
 *   ntp              - Force NTP sync now
 *   ntp status       - Show NTP sync status
 *   ntp server       - Show NTP server advertisement status
 *   ntp server on    - Enable NTP server advertisement on all server-mode interfaces
 *   ntp server off   - Disable NTP server advertisement
 *   ntp server eth0 on/off   - Enable/disable for specific interface
 *   ntp server wlan0 on/off  - Enable/disable for specific interface
 *
 * @param arg Unused parameter
 */
void cli_ntp(uint16_t arg);
```

**Pseudocode for new implementation:**

```c
void cli_ntp(uint16_t arg)
{
    UNUSED_PARAMETER(arg);
    char *token = strtok(NULL, " ");

    if (token == NULL) {
        // No arguments - perform NTP sync (existing behavior)
        perform_ntp_sync();
        return;
    }

    if (strcmp(token, "status") == 0) {
        // Show NTP sync status
        show_ntp_status();
        return;
    }

    if (strcmp(token, "server") == 0) {
        // Handle NTP server advertisement configuration
        char *subtoken = strtok(NULL, " ");

        if (subtoken == NULL) {
            // Show current NTP server advertisement status
            show_ntp_server_status();
            return;
        }

        if (strcmp(subtoken, "on") == 0) {
            // Enable NTP server on all server-mode interfaces
            set_ntp_server_all(true);
            return;
        }

        if (strcmp(subtoken, "off") == 0) {
            // Disable NTP server on all interfaces
            set_ntp_server_all(false);
            return;
        }

        // Check if it's an interface name (eth0 or wlan0)
        if (strcmp(subtoken, "eth0") == 0 || strcmp(subtoken, "wlan0") == 0) {
            char *interface = subtoken;
            char *state = strtok(NULL, " ");

            if (state == NULL) {
                // Show status for specific interface
                show_ntp_server_interface_status(interface);
                return;
            }

            if (strcmp(state, "on") == 0) {
                set_ntp_server_interface(interface, true);
            } else if (strcmp(state, "off") == 0) {
                set_ntp_server_interface(interface, false);
            } else {
                imx_cli_print("Error: Invalid state '%s'. Use 'on' or 'off'\r\n", state);
            }
            return;
        }

        // Unknown subcommand
        show_ntp_usage();
        return;
    }

    // Unknown command
    show_ntp_usage();
}
```

#### 5.2.2 Helper Functions for `cli_ntp.c`

```c
/**
 * @brief Find interface configuration by name
 * @param interface Interface name (eth0, wlan0)
 * @return Pointer to interface config, or NULL if not found
 */
static network_interfaces_t* find_interface_by_name(const char *interface);

/**
 * @brief Check if interface is in server mode
 * @param interface Interface name
 * @return true if in server mode, false otherwise
 */
static bool is_interface_server_mode(const char *interface);

/**
 * @brief Show NTP server advertisement status for all interfaces
 */
static void show_ntp_server_status(void);

/**
 * @brief Show NTP server status for specific interface
 * @param interface Interface name
 */
static void show_ntp_server_interface_status(const char *interface);

/**
 * @brief Set NTP server advertisement for all server-mode interfaces
 * @param enable true to enable, false to disable
 */
static void set_ntp_server_all(bool enable);

/**
 * @brief Set NTP server advertisement for specific interface
 * @param interface Interface name
 * @param enable true to enable, false to disable
 */
static void set_ntp_server_interface(const char *interface, bool enable);

/**
 * @brief Display NTP command usage
 */
static void show_ntp_usage(void);
```

#### 5.2.3 Update CLI Help Text in `cli.c`

**File:** `iMatrix/cli/cli.c` (line ~357)

**Current:**
```c
{"ntp", &cli_ntp, 0, "NTP time sync - 'ntp' (force sync now), 'ntp status' (show sync status), 'ntp server <ip>' (set server)"},
```

**Change to:**
```c
{"ntp", &cli_ntp, 0, "NTP - 'ntp' (sync), 'ntp status', 'ntp server [on|off]', 'ntp server <eth0|wlan0> [on|off]'"},
```

---

### Phase 3: DHCP Configuration Generation

#### 5.3.1 Modify `write_dhcp_config_file()` in `dhcp_server_config.c`

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

**Location:** Lines 371-377 in `write_dhcp_config_file()` function

**Current:**
```c
// Options
fprintf(fp, "option subnet %s\n", params->subnet);
fprintf(fp, "option router %s\n", params->router);
fprintf(fp, "option dns %s\n", dns_servers);
fprintf(fp, "option lease 86400\n");  // 24 hours
```

**Change to:**
```c
// Options
fprintf(fp, "option subnet %s\n", params->subnet);
fprintf(fp, "option router %s\n", params->router);
fprintf(fp, "option dns %s\n", dns_servers);

// NTP server option (DHCP option 42) - only if enabled for this interface
if (params->advertise_ntp) {
    fprintf(fp, "option ntpsrv %s\n", params->router);
    imx_cli_print("  NTP Server:       %s (advertised via DHCP)\n", params->router);
}

fprintf(fp, "option lease 86400\n");  // 24 hours
```

#### 5.3.2 Update `dhcp_config_params_t` Structure

**File:** `dhcp_server_config.c` (lines 82-89)

**Current:**
```c
typedef struct {
    const char *interface;
    const char *ip_start;
    const char *ip_end;
    const char *subnet;
    const char *router;
    const char *dns_servers;
} dhcp_config_params_t;
```

**Change to:**
```c
typedef struct {
    const char *interface;
    const char *ip_start;
    const char *ip_end;
    const char *subnet;
    const char *router;
    const char *dns_servers;
    bool advertise_ntp;     // Advertise NTP server via DHCP option 42
} dhcp_config_params_t;
```

#### 5.3.3 Update `generate_dhcp_server_config()` to Pass NTP Flag

**File:** `dhcp_server_config.c` (in `generate_dhcp_server_config()` function, around line 457-470)

**Add after setting other params:**
```c
// Set NTP advertisement flag from interface configuration
params.advertise_ntp = iface->advertise_ntp_server;

DHCP_CONFIG_DEBUG(("DHCP params: start=%s, end=%s, router=%s, ntp=%s\n",
                   params.ip_start, params.ip_end, params.router,
                   params.advertise_ntp ? "on" : "off"));
```

---

## 6. Implementation Todo Checklist

### Phase 1: Configuration Structure
- [ ] **1.1** Create feature branch `feature/ntp-dhcp-option` from `Aptera_1_Clean`
- [ ] **1.2** Modify `iMatrix/common.h`:
  - [ ] Add `advertise_ntp_server : 1` bit field to `network_interfaces_t`
  - [ ] Reduce `reserved` from 29 to 28 bits
  - [ ] Add Doxygen comment for new field
- [ ] **1.3** Build and verify no compilation errors

### Phase 2: CLI Command
- [ ] **2.1** Backup existing `iMatrix/cli/cli_ntp.c`
- [ ] **2.2** Rewrite `cli_ntp.c` with extended functionality:
  - [ ] Add required includes (`storage.h`, `device/config.h`)
  - [ ] Add `find_interface_by_name()` helper function
  - [ ] Add `is_interface_server_mode()` helper function
  - [ ] Add `show_ntp_server_status()` function
  - [ ] Add `show_ntp_server_interface_status()` function
  - [ ] Add `set_ntp_server_all()` function
  - [ ] Add `set_ntp_server_interface()` function
  - [ ] Add `show_ntp_usage()` function
  - [ ] Modify main `cli_ntp()` to dispatch to subcommands
- [ ] **2.3** Update help text in `iMatrix/cli/cli.c`
- [ ] **2.4** Build and verify no compilation errors
- [ ] **2.5** Test CLI commands locally (syntax check)

### Phase 3: DHCP Config Generation
- [ ] **3.1** Modify `dhcp_server_config.c`:
  - [ ] Add `advertise_ntp` field to `dhcp_config_params_t` structure
  - [ ] Update `write_dhcp_config_file()` to write NTP option conditionally
  - [ ] Update `generate_dhcp_server_config()` to pass `advertise_ntp` flag
  - [ ] Add debug logging for NTP option
- [ ] **3.2** Build and verify no compilation errors

### Phase 4: Testing
- [ ] **4.1** Deploy to FC-1 test unit
- [ ] **4.2** Test CLI commands:
  - [ ] `ntp` (verify existing sync still works)
  - [ ] `ntp status` (verify status display)
  - [ ] `ntp server` (verify shows current state)
  - [ ] `ntp server on` (verify enables for all server-mode interfaces)
  - [ ] `ntp server off` (verify disables)
  - [ ] `ntp server eth0 on` (verify per-interface enable)
  - [ ] `ntp server eth0 off` (verify per-interface disable)
  - [ ] `ntp server wlan0 on` (verify for wlan0 in AP mode)
- [ ] **4.3** Verify configuration persistence:
  - [ ] Enable NTP server
  - [ ] Reboot device
  - [ ] Verify setting retained
- [ ] **4.4** Test DHCP configuration generation:
  - [ ] Set eth0 to server mode with NTP enabled
  - [ ] Verify `/etc/network/udhcpd.eth0.conf` contains `option ntpsrv`
  - [ ] Set NTP to disabled
  - [ ] Verify config does NOT contain `option ntpsrv`
- [ ] **4.5** Test client NTP discovery:
  - [ ] Connect client device to eth0 network
  - [ ] Verify client receives NTP server via DHCP
  - [ ] Verify client can sync time from FC-1
- [ ] **4.6** Test WiFi AP mode:
  - [ ] Set wlan0 to server (AP) mode with NTP enabled
  - [ ] Connect WiFi client
  - [ ] Verify client receives NTP server via DHCP

### Phase 5: Documentation and Completion
- [ ] **5.1** Update this plan document with implementation notes
- [ ] **5.2** Add summary of work completed
- [ ] **5.3** Record metrics (tokens, time, recompilations)
- [ ] **5.4** Final clean build verification
- [ ] **5.5** Merge branch back to `Aptera_1_Clean`

---

## 7. CLI Command Reference (After Implementation)

### Command: `ntp`

| Subcommand | Description |
|------------|-------------|
| `ntp` | Force NTP time synchronization now |
| `ntp status` | Display current NTP sync status |
| `ntp server` | Show NTP server advertisement status for all interfaces |
| `ntp server on` | Enable NTP advertisement on all server-mode interfaces |
| `ntp server off` | Disable NTP advertisement on all interfaces |
| `ntp server eth0` | Show NTP status for eth0 |
| `ntp server eth0 on` | Enable NTP advertisement for eth0 (if in server mode) |
| `ntp server eth0 off` | Disable NTP advertisement for eth0 |
| `ntp server wlan0` | Show NTP status for wlan0 |
| `ntp server wlan0 on` | Enable NTP advertisement for wlan0 (if in AP/server mode) |
| `ntp server wlan0 off` | Disable NTP advertisement for wlan0 |

### Example Output

```
> ntp server
NTP Server Advertisement Status
===============================
Interface  Mode      NTP Advertise  Status
---------  --------  -------------  ------
eth0       server    enabled        Active - advertising 192.168.7.1
wlan0      client    n/a            Not applicable (client mode)

> ntp server eth0 on
NTP server advertisement enabled for eth0
Configuration saved. Changes take effect on next DHCP config regeneration.

> ntp server off
NTP server advertisement disabled for all interfaces
Configuration saved.
```

---

## 8. Validation Criteria

### Functional Requirements

| # | Requirement | Validation Method |
|---|-------------|-------------------|
| F1 | NTP option only advertised when `advertise_ntp_server` bit is set | Check generated udhcpd config file |
| F2 | NTP option only on server-mode interfaces | Attempt to enable on client-mode interface - should warn |
| F3 | CLI can enable/disable per-interface | Test all CLI subcommands |
| F4 | Configuration persists across reboots | Enable, reboot, verify state |
| F5 | DHCP clients receive NTP server | Connect client, check DHCP lease |
| F6 | Clients can sync time from FC-1 | Run `ntpdate -q <fc1-ip>` from client |

### Non-Functional Requirements

| # | Requirement | Validation Method |
|---|-------------|-------------------|
| N1 | Backward compatible (default disabled) | Fresh install should have NTP disabled |
| N2 | No structure size change | Verify `sizeof(network_interfaces_t)` unchanged |
| N3 | Clean build with no warnings | Build with `-Wall -Werror` |

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Structure size change breaks config loading | Low | High | Verify sizeof() unchanged; use reserved bits |
| Existing NTP CLI users confused | Medium | Low | Maintain backward compatibility for `ntp` command |
| DHCP clients don't honor NTP option | Low | Medium | Test with multiple client types |

---

## 10. Questions Resolved

| Question | Answer |
|----------|--------|
| Should NTP always be advertised? | No - configurable via bit flag |
| Should WiFi AP mode include NTP? | Yes - when wlan0 is in server/AP mode |
| Default state? | Disabled (0) for backward compatibility |
| Per-interface or global setting? | Per-interface (stored in each `network_interfaces_t`) |

---

## 11. Python NTP Client Test Script

### 11.1 Overview

A Python test script will be created to validate NTP server functionality from a Linux client connected to the FC-1's ethernet interface.

**File:** `tools/test_ntp_server.py`

### 11.2 Script Features

| Feature | Description |
|---------|-------------|
| DHCP NTP Discovery | Check if NTP server was received via DHCP option 42 |
| NTP Query | Query the FC-1 NTP server for current time |
| Time Offset Check | Calculate and display time offset from server |
| Sync Test | Optionally sync local time to FC-1 NTP server |
| Connectivity Test | Verify UDP port 123 is reachable |
| Verbose Mode | Detailed output for debugging |

### 11.3 Script Design

```python
#!/usr/bin/env python3
"""
NTP Server Test Script for Fleet-Connect-1

Tests NTP server functionality from a client connected to FC-1's ethernet interface.

Usage:
    ./test_ntp_server.py                    # Auto-detect NTP server from DHCP
    ./test_ntp_server.py -s 192.168.7.1     # Specify NTP server IP
    ./test_ntp_server.py -s 192.168.7.1 -v  # Verbose output
    ./test_ntp_server.py --sync             # Actually sync time (requires root)

Requirements:
    - Python 3.6+
    - ntplib (pip install ntplib)
    - Root privileges for --sync option
"""

import argparse
import socket
import subprocess
import sys
from datetime import datetime

# Test functions to implement:
# - check_dhcp_ntp_option()    - Parse /var/lib/dhcp/dhclient.leases for NTP server
# - test_ntp_port_reachable()  - UDP connectivity test to port 123
# - query_ntp_server()         - Get time from NTP server using ntplib
# - calculate_offset()         - Compare local vs server time
# - sync_time()                - Optionally set system time (requires root)
# - print_results()            - Display test results summary
```

### 11.4 Command Line Interface

```
usage: test_ntp_server.py [-h] [-s SERVER] [-v] [--sync] [--timeout TIMEOUT]

NTP Server Test Script for Fleet-Connect-1

optional arguments:
  -h, --help            show this help message and exit
  -s SERVER, --server SERVER
                        NTP server IP address (default: auto-detect from DHCP)
  -v, --verbose         Enable verbose output
  --sync                Sync local time to NTP server (requires root)
  --timeout TIMEOUT     NTP query timeout in seconds (default: 5)
```

### 11.5 Expected Output

```
$ ./test_ntp_server.py -s 192.168.7.1 -v

Fleet-Connect-1 NTP Server Test
================================
Date: 2026-01-09 14:32:15
Target: 192.168.7.1

[1/4] Checking DHCP NTP option...
      DHCP lease file: /var/lib/dhcp/dhclient.eth0.leases
      NTP Server from DHCP: 192.168.7.1 ✓

[2/4] Testing NTP port connectivity...
      UDP port 123: OPEN ✓

[3/4] Querying NTP server...
      Server: 192.168.7.1
      Stratum: 1 (local clock)
      Reference: LOCAL
      Server time: 2026-01-09 14:32:15.123456
      Local time:  2026-01-09 14:32:15.234567
      Offset: +0.111111 seconds ✓

[4/4] Summary
      ✓ NTP server is functioning correctly
      ✓ Time offset is within acceptable range (<1 second)

Test Results: PASSED (4/4 checks passed)
```

### 11.6 Test Script Todo Items

Add to Phase 4 testing:

- [ ] **4.7** Create `tools/test_ntp_server.py`:
  - [ ] Implement argument parsing with argparse
  - [ ] Implement `check_dhcp_ntp_option()` - parse DHCP lease file
  - [ ] Implement `test_ntp_port_reachable()` - UDP socket test
  - [ ] Implement `query_ntp_server()` - NTP query using ntplib
  - [ ] Implement `calculate_offset()` - time comparison
  - [ ] Implement `sync_time()` - optional time sync (root required)
  - [ ] Implement `print_results()` - formatted output
  - [ ] Add proper error handling and timeouts
  - [ ] Add Doxygen-style docstrings
- [ ] **4.8** Test the script:
  - [ ] Run with auto-detection (no arguments)
  - [ ] Run with explicit server IP
  - [ ] Run with verbose mode
  - [ ] Test error handling (no NTP server, timeout, etc.)
  - [ ] Test on Ubuntu/Debian client connected to FC-1 eth0

### 11.7 Dependencies

The test script requires:

```bash
# Install on test client
pip3 install ntplib

# Or on Debian/Ubuntu
sudo apt-get install python3-ntplib
```

---

## 12. Estimated Effort

| Phase | Estimated Lines Changed | Complexity |
|-------|-------------------------|------------|
| Phase 1: Structure | ~5 lines | Low |
| Phase 2: CLI | ~200 lines | Medium |
| Phase 3: DHCP Config | ~15 lines | Low |
| Phase 4: Testing | N/A | Medium |
| Phase 4.7-4.8: Python Test Script | ~250 lines | Medium |
| **Total** | **~470 lines** | **Medium** |

---

**Plan Created By:** Claude Code
**Source Specification:** /home/greg/iMatrix/iMatrix_Client/docs/prompt_work/ntp_server.yaml
**Plan Created:** 2026-01-09
**Last Updated:** 2026-01-09
**Status:** Implementation Complete

---

## 13. Implementation Summary

### 13.1 Work Completed

**Date:** 2026-01-09

All planned implementation phases have been completed successfully:

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Structure | Complete | Added `advertise_ntp_server : 1` bit to `network_interfaces_t` |
| Phase 2: CLI | Complete | Extended `cli_ntp.c` with `ntp server` subcommands (~390 lines) |
| Phase 3: DHCP Config | Complete | Added NTP option (DHCP option 42) to `dhcp_server_config.c` |
| Phase 4: Python Script | Complete | Created `tools/test_ntp_server.py` (~420 lines) |

### 13.2 Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `iMatrix/common.h` | +2 | Added `advertise_ntp_server` bit field |
| `iMatrix/cli/cli_ntp.c` | ~390 (rewrite) | Extended with NTP server subcommands |
| `iMatrix/cli/cli.c` | 1 | Updated help text |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c` | +12 | Added NTP option support |
| `Fleet-Connect-1/tools/test_ntp_server.py` | +420 (new) | Python test script |

### 13.3 Build Verification

- **Build Status:** SUCCESS
- **Compilation Errors:** 0
- **Compilation Warnings:** 0
- **Recompilations Required:** 2 (fixed #ifdef guards for Linux-only code)

### 13.4 Implementation Notes

1. **Platform Guards:** The NTP server configuration CLI is wrapped in `#ifdef LINUX_PLATFORM` since `network_interfaces` array is only available on Linux builds.

2. **Interface Handling:** The `find_interface_index()` function handles wlan0 specially - it checks both STA and AP interfaces to find which one is in server mode.

3. **Default State:** The `advertise_ntp_server` bit defaults to 0 (disabled) for backward compatibility with existing configurations.

4. **Python Script Features:**
   - Auto-detects NTP server from DHCP lease files
   - Tests UDP port 123 connectivity
   - Queries NTP server using ntplib
   - Optional time sync (requires root)
   - Colorized output for terminal

### 13.5 Metrics

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~825 |
| Build Iterations | 2 |
| Syntax Errors Fixed | 1 (unused function, missing #ifdef) |

---

## 14. Testing Checklist (For User Verification)

### Device Testing (FC-1)

- [ ] Deploy updated firmware to FC-1
- [ ] Run `ntp server` CLI command - verify status display
- [ ] Run `ntp server eth0 on` - verify enables NTP advertising
- [ ] Check `/etc/network/udhcpd.eth0.conf` contains `option ntpsrv`
- [ ] Reboot device and verify setting persists
- [ ] Run `ntp server off` - verify disables NTP advertising

### Client Testing

- [ ] Copy `tools/test_ntp_server.py` to client machine
- [ ] Install ntplib: `pip3 install ntplib`
- [ ] Connect client to FC-1 ethernet interface
- [ ] Run: `./test_ntp_server.py -s 192.168.7.1 -v`
- [ ] Verify all tests pass

---

**Implementation Completed:** 2026-01-09
**Implemented By:** Claude Code
