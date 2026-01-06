# Plan: Add PPP Status Command to fc1 Script

**Date:** 2025-12-29
**Author:** Claude Code Analysis
**Status:** Draft - Awaiting Review

---

## 1. Overview

Add a new `ppp` command to the `fc1` remote control script that connects to the gateway device and displays comprehensive PPP link status including:
- ppp0 interface status (IP address, link state)
- pppd service status (`sv status pppd`)
- PPP log file tail for latest connection status

---

## 2. Current Script Structure

### 2.1 Host Script: `scripts/fc1`
- Runs on development machine
- Connects to target via SSH (sshpass)
- Delegates commands to `fc1_service.sh` on target
- Target: `192.168.7.1:22222` (root@gateway)

### 2.2 Target Script: `scripts/fc1_service.sh`
- Runs on gateway device
- Controls FC-1 service via runsv
- Located at `/usr/qk/etc/sv/FC-1/fc1_service.sh` when deployed (persistent across reboots)

---

## 3. Implementation Plan

### 3.1 Changes to `fc1_service.sh` (Target Script)

Add new function `show_ppp_status()`:

```sh
show_ppp_status() {
    echo "========================================"
    echo " PPP Link Status"
    echo "========================================"

    # 1. Check ppp0 interface
    echo ""
    echo "=== PPP0 Interface ==="
    if ip addr show ppp0 2>/dev/null; then
        echo "[OK]  ppp0 interface exists"
    else
        echo "[--]  ppp0 interface not found"
    fi

    # 2. Check pppd service status
    echo ""
    echo "=== PPPD Service Status ==="
    sv status pppd 2>/dev/null || echo "  pppd service not configured"

    # 3. Check if pppd process is running
    echo ""
    PPPD_PID=$(pidof pppd 2>/dev/null)
    if [ -n "$PPPD_PID" ]; then
        echo "[OK]  pppd process: Running (PID: $PPPD_PID)"
    else
        echo "[--]  pppd process: Not running"
    fi

    # 4. Show PPP log tail
    echo ""
    echo "=== PPP Log (last 30 lines) ==="
    if [ -f /var/log/pppd/current ]; then
        tail -30 /var/log/pppd/current
    else
        echo "  No log file at /var/log/pppd/current"
    fi

    # 5. Show connection status summary
    echo ""
    echo "=== Connection Summary ==="
    if [ -f /var/log/pppd/current ]; then
        # Check for recent connection success
        if tail -50 /var/log/pppd/current | grep -q "local IP address"; then
            LAST_IP=$(tail -50 /var/log/pppd/current | grep "local IP address" | tail -1)
            echo "[OK]  Last connection: $LAST_IP"
        fi
        # Check for recent failures
        if tail -20 /var/log/pppd/current | grep -qE "Connect script failed|CME ERROR|NO CARRIER"; then
            echo "[ERR] Recent failure detected in log"
            tail -20 /var/log/pppd/current | grep -E "Connect script failed|CME ERROR|NO CARRIER|Exit" | tail -5
        fi
    fi

    echo "========================================"
}
```

Add case handler in main switch:
```sh
    ppp)
        show_ppp_status
        ;;
```

Update help text to include new command.

### 3.2 Changes to `fc1` (Host Script)

Add `ppp` to the case statement:
```sh
case "$1" in
    start|stop|restart|status|enable|log|create-run|ppp)
        check_target
        run_service_cmd "$1"
        ;;
```

Update help text:
```sh
    echo "  ppp         Show PPP link status (interface, service, log)"
```

---

## 4. Detailed Status Checks

### 4.1 PPP0 Interface Check
```sh
ip addr show ppp0
# Or alternatively:
ifconfig ppp0 2>/dev/null
```

**Expected output when connected:**
```
ppp0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500
    inet 10.x.x.x peer 10.x.x.x/32 scope global ppp0
```

### 4.2 Service Status Check
```sh
sv status pppd
```

**Expected output:**
- Running: `run: pppd: (pid 1234) 3600s`
- Stopped: `down: pppd: 0s, normally up`

### 4.3 Log File Check
```sh
tail -30 /var/log/pppd/current
```

**Key patterns to look for:**
| Pattern | Meaning |
|---------|---------|
| `local IP address` | PPP connected successfully |
| `remote IP address` | Peer address assigned |
| `Connect script failed` | Chat script failure |
| `CME ERROR` | Carrier/modem error |
| `NO CARRIER` | No cellular signal |
| `LCP terminated` | Connection dropped |
| `Hangup (SIGHUP)` | Intentional disconnect |

---

## 5. Files to Modify

| File | Changes |
|------|---------|
| `scripts/fc1` | Add `ppp` case, update help |
| `scripts/fc1_service.sh` | Add `show_ppp_status()` function, add `ppp` case, update help |

---

## 6. Testing Plan

1. **Deploy updated scripts:**
   ```sh
   ./fc1 deploy
   ```

2. **Test PPP status command:**
   ```sh
   ./fc1 ppp
   ```

3. **Verify output includes:**
   - [ ] ppp0 interface status (or "not found")
   - [ ] pppd service status from sv
   - [ ] pppd process PID (or "not running")
   - [ ] Last 30 lines of pppd log
   - [ ] Connection summary (success/failure indicators)

4. **Test edge cases:**
   - [ ] PPP connected and working
   - [ ] PPP not running (pppd stopped)
   - [ ] PPP failed (chat script error)
   - [ ] No log file present

---

## 7. Example Expected Output

```
========================================
 PPP Link Status
========================================

=== PPP0 Interface ===
3: ppp0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 state UNKNOWN
    inet 10.64.64.64 peer 10.64.64.65/32 scope global ppp0
[OK]  ppp0 interface exists

=== PPPD Service Status ===
run: pppd: (pid 1847) 14523s

[OK]  pppd process: Running (PID: 1847)

=== PPP Log (last 30 lines) ===
@4000000065f2a3b2... pppd 2.4.7 started
@4000000065f2a3b3... Using interface ppp0
@4000000065f2a3b4... Connect: ppp0 <--> /dev/ttyACM0
@4000000065f2a3c1... local IP address 10.64.64.64
@4000000065f2a3c2... remote IP address 10.64.64.65
@4000000065f2a3c3... primary DNS address 8.8.8.8

=== Connection Summary ===
[OK]  Last connection: local IP address 10.64.64.64
========================================
```

---

## 8. Implementation Checklist

- [ ] Review and approve plan
- [ ] Modify `scripts/fc1_service.sh` - add `show_ppp_status()` function
- [ ] Modify `scripts/fc1_service.sh` - add `ppp` case to main switch
- [ ] Modify `scripts/fc1_service.sh` - update help text
- [ ] Modify `scripts/fc1` - add `ppp` to case statement
- [ ] Modify `scripts/fc1` - update help text
- [ ] Test on target device
- [ ] Verify all status checks work

---

**Document End**
