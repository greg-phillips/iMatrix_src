# Cellular Network Testing Guide
**Project**: Fleet-Connect-1 Cellular Network Fixes
**Branch**: `debug_cellular_network_fix`
**Date**: 2025-01-10

---

## Quick Test Setup

### 1. Enable Debug Logging

Before starting tests, enable comprehensive debug output:

```bash
# From Fleet-Connect CLI:
debug DEBUGS_FOR_NETWORKING
debug DEBUGS_FOR_PPP0_NETWORKING
debug DEBUGS_FOR_WIFI0_NETWORKING
debug DEBUGS_FOR_CELLULAR
```

Or set in configuration file before starting.

---

## Test Scenario 1: Verify Fixes with Current Setup

**Objective**: Run system and check logs for the two errors we fixed

**Procedure**:
```bash
# 1. Start Fleet-Connect-1
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
./FC-1

# 2. Let it run for 2-3 minutes

# 3. Check logs for issues we fixed:
grep "expecting fi" <logfile>           # Should be EMPTY
grep "State transition blocked" <logfile>  # Should be EMPTY
```

**Expected Results**:
- ✅ NO "sh: syntax error: unexpected end of file (expecting fi)"
- ✅ NO "State transition blocked" messages
- ✅ Clean state transitions throughout

---

## Test Scenario 2: WiFi → Cellular Failover

**Objective**: Verify smooth failover when WiFi fails

**Prerequisites**:
- Working WiFi connection (wlan0)
- Cellular modem connected with SIM card
- Cellular signal available

**Procedure**:

```bash
# 1. Verify starting state
ip addr show wlan0        # Should have IP address
ip addr show ppp0         # May not exist yet

# 2. Start Fleet-Connect with logging
./FC-1 2>&1 | tee /tmp/test_failover.log

# In another terminal:
# 3. Wait for system to be online with WiFi (check logs)
# Look for: "NET_ONLINE" with wlan0

# 4. Trigger WiFi failure
sudo ifconfig wlan0 down

# 5. Monitor logs for cellular activation sequence:
# - "Cellular transitioned from NOT_READY to READY"
# - "Activating cellular"
# - "Started pppd"
# - "ppp0 device detected"
# - "Interface switch: wlan0 -> ppp0" or "NONE -> ppp0"

# 6. Verify ppp0 is active
ip addr show ppp0         # Should have IP address
ip route show             # Should have default via ppp0

# 7. Test connectivity
ping -I ppp0 -c 4 8.8.8.8
```

**Expected Timeline**:
- WiFi down detected: Immediate
- Cellular ready: 5-15 seconds
- pppd started: Within 2 seconds of ready
- ppp0 device appears: 5-10 seconds
- Interface online: Total 15-35 seconds

**Expected Log Messages**:
```
[NETMGR] No IP address found, returning to interface selection
[Cellular Connection - Ready state changed from NOT_READY to READY]
[NETMGR-PPP0] Cellular transitioned from NOT_READY to READY
[NETMGR-PPP0] Activating cellular: cellular_ready=YES, state=NET_SELECT_INTERFACE
[NETMGR-PPP0] Started pppd, will monitor for PPP0 device creation
[NETMGR-PPP0] ppp0 device detected, marking as active
[NETMGR] COMPUTE_BEST selected: ppp0
[NETMGR] State transition: NET_REVIEW_SCORE -> NET_ONLINE
```

**Success Criteria**:
- ✅ No "State transition blocked" errors
- ✅ No "expecting fi" shell errors
- ✅ ppp0 becomes active within 35 seconds
- ✅ Internet connectivity via ppp0
- ✅ Clean state machine transitions

---

## Test Scenario 3: Cold Start (No WiFi)

**Objective**: Verify automatic cellular activation from boot

**Prerequisites**:
- Cellular modem connected with SIM card
- WiFi disabled or out of range
- Ethernet disabled or disconnected

**Procedure**:

```bash
# 1. Ensure WiFi is disabled/unavailable
sudo ifconfig wlan0 down  # Or move out of AP range

# 2. Ensure eth0 is not in client mode
# (Should be DHCP server mode per configuration)

# 3. Start Fleet-Connect
./FC-1 2>&1 | tee /tmp/test_coldstart.log

# 4. Monitor logs for cellular activation
# Should see immediate attempt to activate cellular

# 5. Verify ppp0 becomes active
# Should happen within 20-40 seconds from start

# 6. Check final state
ip addr show ppp0
ip route show
ping -I ppp0 -c 4 8.8.8.8
```

**Expected Timeline**:
- System start: 0 seconds
- Detect no WiFi/eth0: Immediate
- Cellular initialization: 5-15 seconds
- Carrier registration: 5-15 seconds
- pppd negotiation: 5-10 seconds
- Total to online: 15-40 seconds

**Expected Log Messages**:
```
[NETMGR] State transition: NET_INIT -> NET_SELECT_INTERFACE
[NETMGR-PPP0] No other interfaces available, attempting to activate ppp0
[NETMGR-PPP0] Activating cellular: cellular_ready=YES, state=NET_SELECT_INTERFACE
[NETMGR-PPP0] Started pppd, will monitor for PPP0 device creation
[Cellular Connection - PPPD started (count=1)]
[NETMGR-PPP0] ppp0 device detected, marking as active
[NETMGR] COMPUTE_BEST selected: ppp0
[NETMGR] State transition: NET_REVIEW_SCORE -> NET_ONLINE
```

**Success Criteria**:
- ✅ Cellular activates automatically
- ✅ No manual intervention required
- ✅ System online within 40 seconds
- ✅ No error messages in logs
- ✅ Clean state transitions throughout

---

## Test Scenario 4: Cellular → WiFi Recovery (Optional)

**Objective**: Verify system switches back to WiFi when available

**Prerequisites**:
- System currently on ppp0 (cellular)
- WiFi AP in range

**Procedure**:

```bash
# 1. Starting state: System on ppp0
ip route show  # Should show default via ppp0

# 2. Enable WiFi
sudo ifconfig wlan0 up

# 3. Monitor logs for WiFi scanning
# Should see: "wpa_cli scan" commands
# Should see: WiFi reconnection attempts

# 4. Wait for automatic switch to WiFi
# System should prefer WiFi (better latency, lower cost)

# 5. Verify final state
ip addr show wlan0  # Should have IP
ip route show       # Should show default via wlan0
                    # ppp0 route should have metric 200 (backup)
```

**Expected Timeline**:
- WiFi enabled: 0 seconds
- First scan: Within 5 seconds
- WiFi connection: 10-20 seconds
- Interface switch: Within 60 seconds (opportunistic discovery)

**Success Criteria**:
- ✅ WiFi rescanning triggers
- ✅ System reconnects to WiFi AP
- ✅ Automatic switch from ppp0 to wlan0
- ✅ ppp0 kept as backup with higher metric

---

## Log Analysis Checklist

After each test, check logs for these items:

### ✅ Items That Should NOT Appear:
- ❌ "sh: syntax error: unexpected end of file (expecting "fi")"
- ❌ "State transition blocked"
- ❌ "Invalid transition from ONLINE to NET_INIT"
- ❌ "Invalid transition from ONLINE_CHECK_RESULTS to NET_INIT"

### ✅ Items That SHOULD Appear:
- ✅ "Cellular transitioned from NOT_READY to READY"
- ✅ "Activating cellular: cellular_ready=YES"
- ✅ "Started pppd, will monitor for PPP0 device creation"
- ✅ "ppp0 device detected, marking as active"
- ✅ "COMPUTE_BEST selected: ppp0"
- ✅ "State transition: NET_REVIEW_SCORE -> NET_ONLINE"
- ✅ "No IP address found, returning to interface selection" (if interface fails)

### State Transition Patterns (All Valid):
```
NET_INIT -> NET_SELECT_INTERFACE ✅
NET_SELECT_INTERFACE -> NET_WAIT_RESULTS ✅
NET_WAIT_RESULTS -> NET_REVIEW_SCORE ✅
NET_REVIEW_SCORE -> NET_ONLINE ✅
NET_ONLINE -> NET_ONLINE_CHECK_RESULTS ✅
NET_ONLINE_CHECK_RESULTS -> NET_ONLINE ✅
NET_ONLINE_CHECK_RESULTS -> NET_SELECT_INTERFACE ✅ (our fix!)
NET_ONLINE -> NET_SELECT_INTERFACE ✅ (our fix!)
```

---

## Quick Commands Reference

### Check Interface Status
```bash
ip addr show                    # All interfaces
ip addr show wlan0              # WiFi
ip addr show ppp0               # Cellular
ip link show                    # Link status
```

### Check Routing
```bash
ip route show                   # Routing table
ip route show | grep default    # Default routes
ip route show | grep linkdown   # Check for linkdown flags
```

### Check Cellular
```bash
ps aux | grep pppd              # Check if pppd running
pidof pppd                      # Get pppd PID
ls -la /var/run/ppp*.pid        # Check PID files
```

### Check WiFi
```bash
wpa_cli status                  # WiFi connection status
wpa_cli scan                    # Trigger scan
wpa_cli scan_results            # View scan results
iwconfig wlan0                  # WiFi details
```

### Test Connectivity
```bash
ping -c 4 8.8.8.8                    # Test general connectivity
ping -I ppp0 -c 4 8.8.8.8            # Test via cellular
ping -I wlan0 -c 4 8.8.8.8           # Test via WiFi
curl --interface ppp0 ifconfig.me    # Get external IP via cellular
```

---

## Troubleshooting

### If Cellular Doesn't Activate:

1. **Check modem connection**:
   ```bash
   ls -la /dev/ttyUSB*  # Should see ttyUSB0, ttyUSB1, ttyUSB2
   ```

2. **Check cellular driver status**:
   ```bash
   # From Fleet-Connect CLI:
   cellular status
   ```

3. **Check SIM card**:
   ```bash
   # Look in logs for:
   # "AT+CPIN?" -> "+CPIN: READY"
   ```

4. **Check carrier registration**:
   ```bash
   # Look in logs for:
   # "AT+COPS?" -> Network operator ID
   ```

5. **Manual cellular activation**:
   ```bash
   # From Fleet-Connect CLI (if available):
   cellular start
   ```

### If WiFi Doesn't Reconnect:

1. **Check wpa_supplicant**:
   ```bash
   ps aux | grep wpa_supplicant
   ```

2. **Check WiFi configuration**:
   ```bash
   cat /etc/wpa_supplicant/wpa_supplicant.conf
   ```

3. **Manual WiFi scan**:
   ```bash
   wpa_cli scan
   sleep 2
   wpa_cli scan_results
   wpa_cli reconnect
   ```

### If Routes Look Wrong:

1. **Check for linkdown flags**:
   ```bash
   ip route show | grep linkdown
   ```

2. **Manually fix routes**:
   ```bash
   # Remove bad route
   sudo ip route del default via <gateway> dev <interface>

   # Add correct route
   sudo ip route add default via <gateway> dev <interface>
   ```

3. **Check for multiple default routes**:
   ```bash
   ip route show | grep default
   # Should only see one active default (others should have higher metric)
   ```

---

## Expected Test Duration

- **Test Scenario 1**: 5 minutes
- **Test Scenario 2**: 10 minutes
- **Test Scenario 3**: 10 minutes
- **Test Scenario 4**: 10 minutes (optional)

**Total**: 25-35 minutes for core tests

---

## Reporting Results

When reporting results back, please provide:

1. **Test scenarios completed**: Which tests were run
2. **Success/Failure**: Did each test pass?
3. **Log excerpts**: Key log messages observed
4. **Issues found**: Any unexpected behavior
5. **Timing measurements**: How long did failover take?

Example format:
```
Test Scenario 2: WiFi → Cellular Failover
Status: ✅ PASS
Failover Time: 23 seconds
Issues: None
Log: No "State transition blocked" errors, clean transition observed
```

---

## Success Criteria Summary

All tests PASS if:

1. ✅ NO shell syntax errors in logs
2. ✅ NO "State transition blocked" errors
3. ✅ Cellular activates when primary interfaces fail
4. ✅ Failover completes within 35 seconds
5. ✅ Internet connectivity works on ppp0
6. ✅ WiFi rescanning triggers when interface down
7. ✅ Clean state machine transitions throughout

---

**Ready to test!** Start with Test Scenario 1 (quick log check), then proceed to Scenario 2 or 3 based on your current network setup.

---

**End of Testing Guide**
