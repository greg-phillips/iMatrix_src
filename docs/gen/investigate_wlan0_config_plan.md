# WLAN0 DHCP Investigation Plan

**Date Created:** 2025-12-27
**Last Updated:** 2025-12-27
**Document Version:** 1.1
**Status:** Investigation Complete - Ready for Implementation
**Author:** Claude Code Analysis

---

## 1. Executive Summary

### Problem Statement
After the FC-1 Application starts and loads a new configuration, the WLAN0 interface connects to the WiFi access point (SSID) but fails to obtain an IPv4 address via DHCP. The interface shows UP/LOWER_UP status but has no IPv4 address.

### Root Cause Summary
Two interconnected issues prevent wlan0 from obtaining/maintaining an IP address:

1. **ifplugd debounce behavior**: The system uses ifplugd to start DHCP on link-up events, but ifplugd doesn't re-execute the action script when WiFi link flaps quickly (up/down within seconds).

2. **FC-1 network manager not running**: When FC-1 is not running, the network manager's self-healing mechanisms (which include DHCP recovery) are inactive.

3. **No persistent DHCP client**: The udhcpc client is started once but not maintained. When it exits or fails, nothing restarts it.

### Selected Solution
**Option B: FC-1 Self-Provisioning DHCP Monitor Service**

The FC-1 application will create and install a dedicated DHCP monitor service during network initialization. This ensures:
- Self-healing at system level independent of FC-1 runtime
- Works on fresh installations (no pre-existing scripts required)
- FC-1 owns and maintains the network healing infrastructure

---

## 2. Investigation Findings

### 2.1 System State Observed

| Component | Status | Notes |
|-----------|--------|-------|
| wlan0 interface | UP, LOWER_UP | Connected to AP but no IPv4 |
| wpa_supplicant | Running | Connected to "SierraTelecom" SSID |
| udhcpc (wlan0) | NOT Running | No DHCP client active |
| ifplugd | Running | Monitoring wlan0 but not restarting DHCP |
| FC-1 | DOWN | Network manager not processing |
| DHCP manual test | SUCCESS | `udhcpc -i wlan0` obtains IP immediately |

### 2.2 ifplugd Analysis

**ifplugd command:**
```bash
/usr/sbin/ifplugd -n -s -i wlan0 -a -M -r /etc/ifplugd/ifplugd.action -p -q
```

**Key flags:**
- `-a`: Don't up interface at each link probe
- `-p`: Don't run "up" script on startup
- `-q`: Don't run "down" script on exit
- `-M`: Monitor creation/destruction of interface

**ifplugd.action script behavior:**
- Only starts udhcpc on `up` events when conditions are met
- Uses blocking `udhcpc` without `-b` flag (waits for completion)
- No mechanism to restart if DHCP fails or client exits

**Log analysis (from /var/log/ifplugd/current):**
```
22:28:16 - link is up + executing action + Starting udhcpc (SUCCESS)
22:29:53 - link is down
22:29:54 - link is up (NO action script execution!)
22:31:23 - link is down
22:31:24 - link is up (NO action script execution!)
... (pattern continues)
```

**Problem:** When WiFi link flaps quickly (within 1 second), ifplugd does not re-execute the action script. This appears to be debounce behavior.

### 2.3 Network Manager Analysis

The FC-1 network manager (`process_network.c`) has several self-healing mechanisms:

1. **WiFi linkdown recovery** (lines 7478-7649):
   - Detects when WiFi is active=YES but link_up=NO for 30 seconds
   - Triggers recovery sequence: kill DHCP → wpa_cli disconnect → reconnect → start DHCP
   - **Requires FC-1 to be running**

2. **DHCP renewal mechanism** (lines 3000-3109):
   - State machine for non-blocking DHCP renewal
   - Can start udhcpc for wlan0
   - **Requires FC-1 to be running**

3. **No standalone monitoring**: No system-level daemon ensures DHCP stays running independent of FC-1.

### 2.4 Configuration File Analysis

**/etc/network/interfaces:**
```
auto wlan0
iface wlan0 inet dhcp
    wpa-driver nl80211
    wpa-conf /etc/network/wpa_supplicant.conf
```
- Configuration is correct
- Specifies DHCP for wlan0

**/etc/network/wpa_supplicant.conf:**
```
ctrl_interface=/var/run/wpa_supplicant
update_config=1
country=US

network={
    ssid="SierraTelecom"
    psk="happydog"
    key_mgmt=WPA-PSK
    proto=WPA2
}
```
- WiFi credentials are correct
- wpa_supplicant successfully connects to AP

---

## 3. Root Cause Analysis

### Primary Issue: No Persistent DHCP Client Management

The system relies on two mechanisms to start/maintain DHCP on wlan0:

1. **ifplugd**: Only starts DHCP on initial link-up, doesn't handle:
   - Quick link flaps (debounce skips action)
   - DHCP client exit/failure
   - Post-config-load state

2. **FC-1 Network Manager**: Handles recovery but only when FC-1 is running

**Gap:** When FC-1 is not running (or between FC-1 restart and network manager initialization), nothing ensures DHCP is running on wlan0.

### Contributing Factors

1. **ifplugd debounce**: WiFi connections often have brief disconnects; ifplugd doesn't re-run action for quick reconnects

2. **udhcpc exits after lease**: The ifplugd.action uses blocking udhcpc that exits after obtaining lease (no `-b` for background)

3. **No health check**: No periodic check to verify udhcpc is running and wlan0 has an IP

---

## 4. Solution: FC-1 Self-Provisioning DHCP Monitor

### 4.1 Architecture Overview

FC-1 will implement a **self-provisioning network infrastructure** that:

1. **Creates monitor scripts** on the target system if missing
2. **Installs runit service** for DHCP monitoring
3. **Enables the service** to run independently
4. **Maintains the scripts** (updates if version changes)

This ensures the system works on:
- Fresh installations with no pre-existing scripts
- Existing installations (scripts updated if needed)
- Systems where FC-1 was upgraded

### 4.2 Components to Create

| Component | Location on Target | Purpose |
|-----------|-------------------|---------|
| DHCP Monitor Script | `/usr/local/bin/wlan0-dhcp-monitor.sh` | Checks wlan0 and restarts DHCP |
| Runit Run Script | `/etc/sv/wlan0-dhcp/run` | Service entry point |
| Runit Log Script | `/etc/sv/wlan0-dhcp/log/run` | Service logging |
| Service Symlink | `/var/service/wlan0-dhcp` | Enable service |

### 4.3 FC-1 Initialization Flow

```
FC-1 Startup
    │
    ├─► network_manager_init()
    │       │
    │       ├─► install_wlan0_dhcp_monitor()
    │       │       │
    │       │       ├─► Check if scripts exist and are current version
    │       │       ├─► Create /usr/local/bin/wlan0-dhcp-monitor.sh
    │       │       ├─► Create /etc/sv/wlan0-dhcp/run
    │       │       ├─► Create /etc/sv/wlan0-dhcp/log/run
    │       │       ├─► Create symlink to enable service
    │       │       └─► Verify service is running
    │       │
    │       └─► Continue normal network init...
    │
    └─► Normal FC-1 operation
```

### 4.4 Monitor Script Logic

```
Every 10 seconds:
    │
    ├─► Is wlan0 interface present?
    │       NO → Sleep and retry
    │
    ├─► Is wlan0 configured for DHCP (not server mode)?
    │       NO → Sleep and retry
    │
    ├─► Is wlan0 associated with AP (carrier=1)?
    │       NO → Sleep and retry
    │
    ├─► Does wlan0 have an IPv4 address?
    │       YES → All good, sleep and retry
    │       │
    │       NO → Is udhcpc running for wlan0?
    │               YES → Wait for it (max 30s)
    │               NO → Start udhcpc -b -p /var/run/udhcpc.wlan0.pid -i wlan0
    │
    └─► Sleep and retry
```

---

## 5. Implementation Plan

### Phase 1: Create FC-1 Network Provisioning Module

#### Task 1.1: Create New Source Files
- [ ] Create `iMatrix/IMX_Platform/LINUX_Platform/networking/network_provisioning.h`
- [ ] Create `iMatrix/IMX_Platform/LINUX_Platform/networking/network_provisioning.c`
- [ ] Add to CMakeLists.txt

#### Task 1.2: Implement Script Content Storage
- [ ] Define DHCP monitor script as embedded string
- [ ] Define runit run script as embedded string
- [ ] Define runit log script as embedded string
- [ ] Include version marker in scripts for upgrade detection

#### Task 1.3: Implement Installation Functions
- [ ] `install_wlan0_dhcp_monitor()` - Main installation function
- [ ] `write_script_if_changed()` - Write file only if content differs
- [ ] `ensure_directory_exists()` - Create directories as needed
- [ ] `enable_runit_service()` - Create symlink and start service
- [ ] `verify_service_running()` - Check service is operational

#### Task 1.4: Integrate with Network Manager
- [ ] Call `install_wlan0_dhcp_monitor()` from `network_manager_init()`
- [ ] Add error handling and logging
- [ ] Handle installation failures gracefully (don't block FC-1 startup)

### Phase 2: Create Script Content

#### Task 2.1: DHCP Monitor Script (`wlan0-dhcp-monitor.sh`)
- [ ] Check interface exists
- [ ] Check interface is in client mode (not DHCP server)
- [ ] Check carrier/association status
- [ ] Check for IPv4 address
- [ ] Start udhcpc if needed
- [ ] Add comprehensive logging
- [ ] Add version marker comment

#### Task 2.2: Runit Service Scripts
- [ ] Create run script that executes monitor in loop
- [ ] Create log script for svlogd
- [ ] Ensure proper permissions (755)

### Phase 3: Testing and Verification

#### Task 3.1: Build Verification
- [ ] Add new files to CMakeLists.txt
- [ ] Build with zero errors and warnings
- [ ] Verify binary includes new code

#### Task 3.2: Fresh Installation Test
- [ ] Remove any existing monitor scripts from device
- [ ] Start FC-1
- [ ] Verify scripts are created
- [ ] Verify service is running
- [ ] Verify DHCP recovery works

#### Task 3.3: Upgrade Test
- [ ] Modify script version in code
- [ ] Restart FC-1
- [ ] Verify scripts are updated to new version

#### Task 3.4: Self-Healing Test
- [ ] Stop FC-1
- [ ] Kill udhcpc for wlan0
- [ ] Verify monitor service restarts DHCP within 10-20 seconds
- [ ] Verify wlan0 gets IP address

---

## 6. Detailed File Specifications

### 6.1 network_provisioning.h

```c
/**
 * @file network_provisioning.h
 * @brief Network infrastructure provisioning for self-healing DHCP
 *
 * This module installs and maintains system-level scripts and services
 * that provide network self-healing independent of FC-1 runtime.
 */

#ifndef NETWORK_PROVISIONING_H
#define NETWORK_PROVISIONING_H

#include <stdbool.h>

/** Version of provisioned scripts - increment when scripts change */
#define NETWORK_PROVISIONING_VERSION  "1.0.0"

/**
 * @brief Install wlan0 DHCP monitor service
 *
 * Creates the following on the target system:
 * - /usr/local/bin/wlan0-dhcp-monitor.sh
 * - /etc/sv/wlan0-dhcp/run
 * - /etc/sv/wlan0-dhcp/log/run
 * - /var/service/wlan0-dhcp (symlink)
 *
 * @return true if installation successful, false on error
 */
bool install_wlan0_dhcp_monitor(void);

/**
 * @brief Check if DHCP monitor service is installed and current version
 *
 * @return true if installed and current, false if missing or outdated
 */
bool is_wlan0_dhcp_monitor_current(void);

/**
 * @brief Remove wlan0 DHCP monitor service
 *
 * @return true if removal successful, false on error
 */
bool remove_wlan0_dhcp_monitor(void);

#endif /* NETWORK_PROVISIONING_H */
```

### 6.2 wlan0-dhcp-monitor.sh (Embedded in C)

```bash
#!/bin/sh
# wlan0-dhcp-monitor.sh - WLAN0 DHCP Self-Healing Monitor
# Version: 1.0.0
# Installed by: FC-1 Application
# DO NOT EDIT - This file is managed by FC-1

INTERFACE="wlan0"
CHECK_INTERVAL=10
DHCP_WAIT_TIME=30
PID_FILE="/var/run/udhcpc.wlan0.pid"
LOG_TAG="wlan0-dhcp-monitor"

log_msg() {
    logger -t "$LOG_TAG" "$1"
}

is_interface_present() {
    [ -d "/sys/class/net/$INTERFACE" ]
}

is_dhcp_client_mode() {
    # Check if interface is configured for DHCP (not server mode)
    if [ -f "/etc/network/udhcpd-${INTERFACE}.conf" ]; then
        # Server mode config exists, check if server is running
        if pgrep -f "udhcpd.*${INTERFACE}" > /dev/null 2>&1; then
            return 1  # Server mode active
        fi
    fi
    # Check interfaces file for dhcp
    grep -q "iface ${INTERFACE} inet dhcp" /etc/network/interfaces 2>/dev/null
}

is_associated() {
    # Check if WiFi is associated (has carrier)
    [ "$(cat /sys/class/net/$INTERFACE/carrier 2>/dev/null)" = "1" ]
}

has_ipv4_address() {
    ip addr show "$INTERFACE" 2>/dev/null | grep -q "inet "
}

is_dhcp_client_running() {
    pgrep -f "udhcpc.*-i ${INTERFACE}" > /dev/null 2>&1
}

start_dhcp_client() {
    log_msg "Starting udhcpc for $INTERFACE"
    udhcpc -b -R -p "$PID_FILE" -i "$INTERFACE" > /dev/null 2>&1
}

wait_for_dhcp() {
    local count=0
    while [ $count -lt $DHCP_WAIT_TIME ]; do
        if has_ipv4_address; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

# Main monitoring loop
log_msg "Starting WLAN0 DHCP monitor (version 1.0.0)"

while true; do
    sleep $CHECK_INTERVAL

    # Skip if interface doesn't exist
    if ! is_interface_present; then
        continue
    fi

    # Skip if not in DHCP client mode
    if ! is_dhcp_client_mode; then
        continue
    fi

    # Skip if not associated with AP
    if ! is_associated; then
        continue
    fi

    # Check if we have an IP address
    if has_ipv4_address; then
        continue
    fi

    # No IP address - check if DHCP client is running
    if is_dhcp_client_running; then
        log_msg "DHCP client running but no IP, waiting..."
        if ! wait_for_dhcp; then
            log_msg "DHCP timeout, restarting client"
            pkill -f "udhcpc.*-i ${INTERFACE}"
            sleep 1
            start_dhcp_client
        fi
    else
        log_msg "No DHCP client running, starting..."
        start_dhcp_client
    fi
done
```

### 6.3 Runit Run Script (Embedded in C)

```bash
#!/bin/sh
# /etc/sv/wlan0-dhcp/run
# Runit service script for wlan0 DHCP monitor
# Version: 1.0.0
# Installed by: FC-1 Application

exec 2>&1
exec /usr/local/bin/wlan0-dhcp-monitor.sh
```

### 6.4 Runit Log Script (Embedded in C)

```bash
#!/bin/sh
# /etc/sv/wlan0-dhcp/log/run
# Runit log script for wlan0 DHCP monitor
# Version: 1.0.0
# Installed by: FC-1 Application

exec svlogd -tt /var/log/wlan0-dhcp
```

---

## 7. Files to Create/Modify

### New Source Files
| File | Purpose |
|------|---------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/network_provisioning.h` | Header for provisioning functions |
| `iMatrix/IMX_Platform/LINUX_Platform/networking/network_provisioning.c` | Implementation of provisioning |

### Modified Source Files
| File | Change |
|------|--------|
| `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` | Call `install_wlan0_dhcp_monitor()` from init |
| `iMatrix/CMakeLists.txt` | Add new source file |

### Created on Target System (by FC-1)
| File | Purpose |
|------|---------|
| `/usr/local/bin/wlan0-dhcp-monitor.sh` | Monitor script |
| `/etc/sv/wlan0-dhcp/run` | Runit service |
| `/etc/sv/wlan0-dhcp/log/run` | Runit logging |
| `/var/log/wlan0-dhcp/` | Log directory |
| `/var/service/wlan0-dhcp` | Service enable symlink |

---

## 8. Detailed Todo List

### Implementation Tasks
- [ ] Create `network_provisioning.h` header file
- [ ] Create `network_provisioning.c` implementation
- [ ] Embed monitor script content as C string
- [ ] Embed runit scripts as C strings
- [ ] Implement `install_wlan0_dhcp_monitor()`
- [ ] Implement `is_wlan0_dhcp_monitor_current()`
- [ ] Implement helper functions (write_script, mkdir, etc.)
- [ ] Add to CMakeLists.txt
- [ ] Integrate with `network_manager_init()`
- [ ] Add logging for installation process
- [ ] Build and verify zero errors/warnings

### Testing Tasks
- [ ] Deploy to device
- [ ] Test fresh installation (no existing scripts)
- [ ] Test script upgrade detection
- [ ] Test DHCP recovery with FC-1 stopped
- [ ] Test DHCP recovery with WiFi reconnect
- [ ] Verify logging works
- [ ] Test edge cases (interface missing, server mode, etc.)

### Documentation Tasks
- [ ] Update this plan with implementation notes
- [ ] Document any deviations from plan
- [ ] Record build/test results

---

## 9. Appendix: Debug Commands

### Check Current State
```bash
# SSH to device
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1

# Check wlan0 status
ip addr show wlan0
cat /sys/class/net/wlan0/carrier
cat /sys/class/net/wlan0/operstate

# Check DHCP client
ps | grep udhcpc
ls -la /var/run/udhcpc.*

# Check monitor service
sv status wlan0-dhcp
cat /var/log/wlan0-dhcp/current

# Check provisioned scripts
ls -la /usr/local/bin/wlan0-dhcp-monitor.sh
ls -la /etc/sv/wlan0-dhcp/
```

### Force DHCP Recovery Test
```bash
# Kill existing DHCP client
pkill -f 'udhcpc.*wlan0'

# Watch monitor logs
tail -f /var/log/wlan0-dhcp/current

# Should see "No DHCP client running, starting..." within 10-20 seconds
```

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Script write fails (disk full) | Low | Medium | Log error, continue FC-1 startup |
| Service fails to start | Low | Medium | Log error, rely on FC-1 network manager |
| Permission issues | Low | Low | Use proper chmod (755) |
| Conflicts with existing scripts | Low | Low | Version check before overwrite |

---

## 11. Acceptance Criteria

1. **Self-Provisioning**: FC-1 creates all required scripts on first run
2. **Version Management**: FC-1 updates scripts when version changes
3. **Self-Healing**: wlan0 gets IP within 30 seconds of association, even with FC-1 stopped
4. **No Side Effects**: Monitor doesn't interfere with DHCP server mode or manual config
5. **Logging**: All actions logged for troubleshooting
6. **Build Clean**: Zero errors, zero warnings

---

**Ready for Implementation**

---

*Document Version: 1.1*
*Investigation Completed: 2025-12-27*
*Plan Updated: 2025-12-27 - Added self-provisioning requirement*
