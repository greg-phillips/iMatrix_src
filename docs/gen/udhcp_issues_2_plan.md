# Plan: Fix Persistent udhcpc Multiple Process Issue

**Date:** 2026-01-06
**Branch:** feature/udhcp_issues_2
**Status:** Draft - Awaiting Approval
**Author:** Claude Code

---

## Executive Summary

The udhcp issue persists because there are **5 independent, uncoordinated code paths** spawning udhcpc processes for wlan0. Previous fixes only addressed race conditions in one code path (WiFi recovery) but missed the external services and scripts that also spawn udhcpc.

---

## Current State Analysis

### Observed on Device (192.168.7.1)

**6 udhcpc processes running for wlan0:**

| PID | Command | Source |
|-----|---------|--------|
| 3997 | `udhcpc -b -R -p /var/run/udhcpc.wlan0.pid -i wlan0` | wlan0-dhcp-monitor.sh |
| 22770 | `udhcpc -R -n -x hostname:iMatrix:FC-1:0174664659 -p ... -i wlan0` | DHCP renewal |
| 25152 | `udhcpc -R -n -x hostname:iMatrix:FC-1:0174664659 -p ... -i wlan0` | DHCP renewal |
| 26412 | `udhcpc -b -R -p /var/run/udhcpc.wlan0.pid -i wlan0` | wlan0-dhcp-monitor.sh |
| 28849 | `udhcpc -b -R -p /var/run/udhcpc.wlan0.pid -i wlan0` | wlan0-dhcp-monitor.sh |
| 31480 | `udhcpc -b -R -p /var/run/udhcpc.wlan0.pid -i wlan0` | wlan0-dhcp-monitor.sh |

**PID File Status:**
- `/var/run/udhcpc.wlan0.pid` contains only PID 3997
- 5 processes are "orphaned" - untrackable and unkillable via PID file

**Device Uptime:** 1 day, 23:07 (processes accumulated over time)

### Root Cause: 5 Independent Spawn Points

| # | Source | Location | Pattern | Trigger |
|---|--------|----------|---------|---------|
| 1 | **wlan0-dhcp-monitor.sh** | `/usr/local/bin/` (runit service) | `udhcpc -b -R -p ...` | Every 10s if no IP |
| 2 | **WiFi recovery** | `process_network.c:7718` | `udhcpc -i wlan0 -b -q -p ...` | Link down timeout |
| 3 | **DHCP renewal** | `process_network.c:3145` | `udhcpc -R -n -x hostname:...` | Lease expiry |
| 4 | **ifplugd.action** | `/etc/ifplugd/ifplugd.action` | `udhcpc -R -n -x hostname:$(hostname)` | Link up event |
| 5 | **network_provisioning.c** | Line 180 | `udhcpc -b -R -p ...` | Provisioning mode |

**Critical Problem:** All 5 sources:
- Check "is udhcpc running" before spawning
- Have TOCTOU (Time-Of-Check-to-Time-Of-Use) race conditions
- Write to the same PID file (last wins, others orphaned)
- Have NO coordination with each other

---

## Proposed Solution: Single Authority Architecture

### Strategy

Establish **FC-1 application as the single authority** for DHCP client management. External services should be disabled or modified to defer to FC-1.

### Phase 1: Disable External DHCP Spawners (Immediate Fix)

**1.1 Disable wlan0-dhcp-monitor.sh service**

The FC-1 application already handles DHCP management. The wlan0-dhcp-monitor.sh is redundant and causes process duplication.

```bash
# On device:
sv stop wlan0-dhcp
rm /var/service/wlan0-dhcp
# Or mark as down:
touch /var/service/wlan0-dhcp/down
```

**1.2 Modify ifplugd.action to not spawn udhcpc**

Edit `/etc/ifplugd/ifplugd.action` to remove the udhcpc spawn:

```bash
# Current (problematic):
printf "Starting udhcpc for wlan0\n"
udhcpc -R -n -x hostname:"$(hostname)" -p /var/run/udhcpc.wlan0.pid -i wlan0

# Changed to (deferred to FC-1):
printf "wlan0 link up - FC-1 will handle DHCP\n"
# udhcpc is managed by FC-1 application
```

### Phase 2: Harden FC-1 DHCP Management (Code Changes)

**2.1 Add aggressive cleanup before spawning**

In all FC-1 code paths that spawn udhcpc, add:

```c
// Kill ALL existing udhcpc for interface, not just via PID file
snprintf(cmd, sizeof(cmd), "pkill -9 -f 'udhcpc.*-i %s'", ifname);
system(cmd);
usleep(100000);  // Wait 100ms for cleanup

// Verify all killed
snprintf(cmd, sizeof(cmd), "pgrep -f 'udhcpc.*-i %s'", ifname);
if (system(cmd) == 0) {
    PRINTF("[NET-DHCP] WARNING: udhcpc processes still exist for %s after pkill\r\n", ifname);
}

// Now spawn new process
```

**2.2 Add process count enforcement**

Before any spawn, check and enforce maximum:

```c
#define MAX_UDHCPC_PER_INTERFACE 1

int count = count_udhcpc_processes(ifname);
if (count >= MAX_UDHCPC_PER_INTERFACE) {
    PRINTF("[NET-DHCP] Already have %d udhcpc for %s, killing before spawn\r\n", count, ifname);
    kill_all_udhcpc_for_interface(ifname);
}
```

**2.3 Add file locking for spawn coordination**

Create a lock file to prevent simultaneous spawns from different FC-1 code paths:

```c
#define UDHCPC_LOCK_FILE "/var/run/udhcpc_spawn.lock"

bool spawn_udhcpc_with_lock(const char *ifname, const char *cmd) {
    int lock_fd = open(UDHCPC_LOCK_FILE, O_CREAT | O_RDWR, 0644);
    if (lock_fd < 0) {
        return false;
    }

    if (flock(lock_fd, LOCK_EX | LOCK_NB) != 0) {
        // Another process is spawning
        close(lock_fd);
        return false;
    }

    // Kill existing, spawn new
    kill_all_udhcpc_for_interface(ifname);
    system(cmd);

    flock(lock_fd, LOCK_UN);
    close(lock_fd);
    return true;
}
```

### Phase 3: Testing and Verification

**3.1 Immediate test after Phase 1:**
```bash
# Kill all existing udhcpc
pkill -9 -f 'udhcpc.*wlan0'

# Verify services stopped
sv status wlan0-dhcp  # Should show "down"

# Monitor for 1 hour
watch -n 5 'ps | grep udhcpc | grep -v grep'
```

**3.2 Expected result:**
- Only 1 udhcpc process for wlan0 at any time
- No process accumulation over time
- Network remains stable

---

## Implementation Todo List

### Phase 1: Disable External Services (Device-side)

- [ ] 1.1 SSH to device and stop wlan0-dhcp service
- [ ] 1.2 Disable wlan0-dhcp from starting at boot
- [ ] 1.3 Backup and modify /etc/ifplugd/ifplugd.action
- [ ] 1.4 Kill all existing udhcpc processes
- [ ] 1.5 Verify only FC-1 spawns udhcpc
- [ ] 1.6 Monitor for 30 minutes

### Phase 2: Code Changes (If Phase 1 insufficient)

- [ ] 2.1 Add `kill_all_udhcpc_for_interface()` helper function
- [ ] 2.2 Modify WiFi recovery to use aggressive cleanup
- [ ] 2.3 Modify DHCP renewal to use aggressive cleanup
- [ ] 2.4 Add process count enforcement
- [ ] 2.5 Add file locking for spawn coordination
- [ ] 2.6 Build and deploy
- [ ] 2.7 Test stability

### Phase 3: Permanent Fix

- [ ] 3.1 Update fleet provisioning to not install wlan0-dhcp-monitor
- [ ] 3.2 Update ifplugd.action in base image
- [ ] 3.3 Document single authority architecture

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Disabling wlan0-dhcp breaks DHCP | High | FC-1 already handles DHCP; test thoroughly |
| ifplugd change affects other interfaces | Medium | Only modify wlan0 section |
| Network instability during testing | Medium | Test on dev device first |

---

## Questions for Greg

1. **Phase 1 approach:** Can I proceed with disabling the wlan0-dhcp runit service and modifying ifplugd.action? This is the quickest fix and requires no code changes.

2. **Service ownership:** Should wlan0-dhcp-monitor.sh be removed entirely from the fleet, or just disabled on this device?

3. **Testing duration:** How long should we monitor after the fix before considering it successful?

---

## Files to Modify

### Device-side (immediate):
- `/var/service/wlan0-dhcp/` - disable or remove
- `/etc/ifplugd/ifplugd.action` - remove udhcpc spawn for wlan0

### Source code (if needed):
- `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
  - Lines 7670-7720 (WiFi recovery)
  - Lines 3060-3170 (DHCP renewal state machine)

---

**Document Created:** 2026-01-06
**Status:** Awaiting approval to proceed with Phase 1
