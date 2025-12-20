# WLAN0 Failure Fix - Device Test Plan

**Date:** 2025-12-17
**Document Version:** 1.0
**Target Device:** iMatrix FC-1 Gateway
**Test Duration:** Minimum 4 hours, recommended 24+ hours

---

## Prerequisites

### Hardware Required
- iMatrix FC-1 device with WiFi capability
- WiFi access point (preferably one you can control/restart)
- Ethernet connection for backup access (recommended)
- Serial console access (recommended for debugging)

### Software Required
- Updated FC-1 binary with fixes
- SSH/serial access to device
- Log monitoring capability

### Before Starting
1. Note the current firmware version on the device
2. Backup current working binary if needed
3. Ensure device has stable power supply
4. Have rollback binary ready

---

## Phase 1: Deploy Fix to Device

### Step 1.1: Build the Binary
```bash
# On build machine
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
make clean
make -j4
```

### Step 1.2: Transfer Binary to Device
```bash
# From build machine
scp FC-1 root@<device-ip>:/tmp/FC-1_new

# Or via other transfer method (SD card, USB, etc.)
```

### Step 1.3: Install on Device
```bash
# SSH to device
ssh root@<device-ip>

# Stop running service
systemctl stop fc1
# Or: killall FC-1

# Backup current binary
cp /usr/bin/FC-1 /usr/bin/FC-1.backup

# Install new binary
cp /tmp/FC-1_new /usr/bin/FC-1
chmod +x /usr/bin/FC-1

# Verify binary is updated (check date)
ls -la /usr/bin/FC-1
```

### Step 1.4: Start Service
```bash
# Start the service
systemctl start fc1
# Or: /usr/bin/FC-1 &

# Verify it's running
ps | grep FC-1
```

---

## Phase 2: Basic Sanity Tests (10 minutes)

### Test 2.1: Verify Device Boots and Runs
```bash
# Check process is running
ps | grep FC-1

# Check for crashes in log
dmesg | grep -i segfault
```
**Expected:** FC-1 process running, no segfaults

### Test 2.2: Verify WiFi Connects
```bash
# Check wpa_supplicant state
wpa_cli -i wlan0 status | grep wpa_state

# Check for IP address
ip addr show wlan0 | grep "inet "
```
**Expected:** `wpa_state=COMPLETED` and valid IP address

### Test 2.3: Verify Single DHCP Client
```bash
# Count udhcpc processes for wlan0
ps | grep 'udhcpc.*wlan0' | grep -v grep | wc -l

# List them
ps | grep 'udhcpc.*wlan0' | grep -v grep
```
**Expected:** Exactly 1 udhcpc process for wlan0

### Test 2.4: Verify Network Connectivity
```bash
# Ping external host
ping -c 3 8.8.8.8

# Ping cloud server
ping -c 3 api.imatrixsys.com
```
**Expected:** All pings successful

---

## Phase 3: Test Fix A - No Unnecessary Reconfigure (1-2 hours)

This tests that the hourly WiFi list check doesn't cause disconnection when no changes exist.

### Test 3.1: Monitor for WiFi List Check
```bash
# Start continuous log monitoring
tail -f /var/log/messages | grep -E "(WiFi list|wifi_list|reconfigure|WIFI)"
```

### Test 3.2: Wait for Hourly Check
- Wait up to 60 minutes for the hourly WiFi list check
- Or trigger it manually if possible

### Test 3.3: Verify No Disconnection

**Look for these log messages (GOOD - fix working):**
```
WiFi configuration unchanged, skipping reconfigure
```
Or:
```
[WiFi list - Changing state from: X to IDLE]
```
Without seeing:
```
wpa_cli reconfigure
```

**Look for these log messages (BAD - fix not working):**
```
Writing wifi network XXX to config
wpa_cli reconfigure
wlan0: deauthenticating
```

### Test 3.4: Verify WiFi Stayed Connected
```bash
# After the hourly check, verify still connected
wpa_cli -i wlan0 status | grep wpa_state
ip addr show wlan0 | grep "inet "
ping -c 3 8.8.8.8
```
**Expected:** Still connected with same IP, pings succeed

---

## Phase 4: Test Fix B - DHCP Race Condition (30 minutes)

This tests that WiFi recovery doesn't spawn duplicate DHCP clients.

### Test 4.1: Simulate WiFi Disconnect

**Option A: Disable AP temporarily**
- Turn off WiFi access point for 60 seconds
- Turn it back on

**Option B: Force wpa_supplicant disconnect**
```bash
# On device
wpa_cli -i wlan0 disconnect
sleep 5
wpa_cli -i wlan0 reconnect
```

**Option C: Trigger reconfigure manually**
```bash
wpa_cli -i wlan0 reconfigure
```

### Test 4.2: Monitor Recovery
```bash
# Watch for recovery messages
tail -f /var/log/messages | grep -E "(Recovery|udhcpc|DHCP)"
```

**Look for these log messages (GOOD - fix working):**
```
Recovery step 4: udhcpc already running for wlan0, skipping start
```
Or:
```
Recovery step 4: Starting udhcpc for wlan0
```
(Only if no udhcpc was running)

### Test 4.3: Verify Single DHCP Client After Recovery
```bash
# Wait 60 seconds for recovery to complete
sleep 60

# Check udhcpc count
ps | grep 'udhcpc.*wlan0' | grep -v grep | wc -l
ps | grep 'udhcpc.*wlan0' | grep -v grep
```
**Expected:** Exactly 1 udhcpc process

### Test 4.4: Verify IP Address Obtained
```bash
# Check IP
ip addr show wlan0 | grep "inet "

# Verify connectivity
ping -c 3 8.8.8.8
```
**Expected:** Valid IP address, pings succeed

---

## Phase 5: Stress Test - Multiple Reconnections (1 hour)

### Test 5.1: Repeated Disconnect/Reconnect
```bash
# Run this loop 10 times with 5 minute intervals
for i in $(seq 1 10); do
    echo "=== Test iteration $i ==="
    wpa_cli -i wlan0 disconnect
    sleep 10
    wpa_cli -i wlan0 reconnect
    sleep 60

    # Check state
    echo "udhcpc count: $(ps | grep 'udhcpc.*wlan0' | grep -v grep | wc -l)"
    echo "IP: $(ip addr show wlan0 | grep 'inet ' | awk '{print $2}')"
    echo "Ping: $(ping -c 1 8.8.8.8 > /dev/null 2>&1 && echo OK || echo FAIL)"

    sleep 240  # Wait 4 minutes before next iteration
done
```

### Test 5.2: Verify After Stress Test
```bash
# Final state check
ps | grep 'udhcpc.*wlan0' | grep -v grep
wpa_cli -i wlan0 status
ip addr show wlan0
ping -c 3 8.8.8.8
```
**Expected:** Single udhcpc, connected state, valid IP, pings succeed

---

## Phase 6: Long-Running Stability Test (24+ hours)

### Test 6.1: Start Monitoring Script
Create and run this monitoring script:

```bash
#!/bin/bash
# Save as /tmp/wifi_monitor.sh

LOG_FILE="/tmp/wifi_stability_test.log"

echo "=== WiFi Stability Test Started $(date) ===" >> $LOG_FILE

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    UDHCPC_COUNT=$(ps | grep 'udhcpc.*wlan0' | grep -v grep | wc -l)
    WPA_STATE=$(wpa_cli -i wlan0 status 2>/dev/null | grep wpa_state | cut -d= -f2)
    IP_ADDR=$(ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}')
    PING_RESULT=$(ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1 && echo "OK" || echo "FAIL")

    # Log status
    echo "$TIMESTAMP | udhcpc=$UDHCPC_COUNT | wpa=$WPA_STATE | ip=$IP_ADDR | ping=$PING_RESULT" >> $LOG_FILE

    # Alert on problems
    if [ "$UDHCPC_COUNT" != "1" ]; then
        echo "$TIMESTAMP | WARNING: udhcpc count is $UDHCPC_COUNT (expected 1)" >> $LOG_FILE
    fi

    if [ "$PING_RESULT" == "FAIL" ]; then
        echo "$TIMESTAMP | WARNING: Ping failed" >> $LOG_FILE
        # Capture diagnostic info
        echo "--- Diagnostic dump ---" >> $LOG_FILE
        ps | grep udhcpc >> $LOG_FILE
        wpa_cli -i wlan0 status >> $LOG_FILE
        ip addr show wlan0 >> $LOG_FILE
        echo "--- End diagnostic ---" >> $LOG_FILE
    fi

    sleep 300  # Check every 5 minutes
done
```

```bash
# Run the monitor
chmod +x /tmp/wifi_monitor.sh
nohup /tmp/wifi_monitor.sh &
```

### Test 6.2: Check Results After 24 Hours
```bash
# View log summary
cat /tmp/wifi_stability_test.log | grep WARNING | wc -l
cat /tmp/wifi_stability_test.log | tail -50

# Check for any ping failures
grep "ping=FAIL" /tmp/wifi_stability_test.log | wc -l

# Check for udhcpc count issues
grep "udhcpc count" /tmp/wifi_stability_test.log | grep -v "udhcpc=1"
```

**Expected Results:**
- Zero or minimal ping failures
- udhcpc count always 1
- No extended disconnection periods

---

## Verification Checklist

### Must Pass (Critical)
- [ ] Device boots and runs without crashes
- [ ] WiFi connects on startup
- [ ] Only one udhcpc process for wlan0
- [ ] Device obtains IP address
- [ ] Network connectivity works (ping succeeds)

### Should Pass (Important)
- [ ] Hourly WiFi check doesn't cause disconnection
- [ ] Log shows "configuration unchanged, skipping reconfigure"
- [ ] After manual disconnect/reconnect, still only one udhcpc
- [ ] After recovery, IP is obtained within 30 seconds

### Nice to Have (Stability)
- [ ] 24-hour test shows no connectivity issues
- [ ] No accumulated udhcpc processes over time
- [ ] Memory usage remains stable

---

## Troubleshooting

### Issue: Multiple udhcpc Processes Still Appearing
```bash
# Check if ifplugd is the culprit
ps | grep ifplugd

# Check ifplugd action script
cat /etc/ifplugd/ifplugd.action

# Temporary workaround: disable ifplugd for wlan0
# (consult system documentation)
```

### Issue: WiFi Still Disconnecting Hourly
```bash
# Check if fix is actually in binary
strings /usr/bin/FC-1 | grep "configuration unchanged"

# If not found, binary may not have the fix
```

### Issue: No IP After Reconnect
```bash
# Manual recovery
killall udhcpc
udhcpc -R -n -x hostname:iMatrix:FC-1:$(cat /etc/serial) -p /var/run/udhcpc.wlan0.pid -i wlan0

# Check for DHCP server issues
tcpdump -i wlan0 port 67 or port 68
```

### Issue: Device Crashes
```bash
# Check for core dumps
ls -la /var/crash/

# Check kernel log
dmesg | tail -100

# Rollback to previous binary
cp /usr/bin/FC-1.backup /usr/bin/FC-1
systemctl restart fc1
```

---

## Rollback Procedure

If testing reveals critical issues:

```bash
# Stop service
systemctl stop fc1

# Restore backup
cp /usr/bin/FC-1.backup /usr/bin/FC-1

# Restart
systemctl start fc1

# Verify
ps | grep FC-1
```

---

## Test Results Template

```
Test Date: ________________
Tester: ________________
Device Serial: ________________
Firmware Version: ________________

Phase 2 - Basic Sanity:
  [ ] PASS  [ ] FAIL  - Device boots and runs
  [ ] PASS  [ ] FAIL  - WiFi connects
  [ ] PASS  [ ] FAIL  - Single udhcpc process
  [ ] PASS  [ ] FAIL  - Network connectivity

Phase 3 - No Unnecessary Reconfigure:
  [ ] PASS  [ ] FAIL  - Hourly check doesn't disconnect
  [ ] PASS  [ ] FAIL  - Log shows skip message

Phase 4 - DHCP Race Condition:
  [ ] PASS  [ ] FAIL  - Single udhcpc after recovery
  [ ] PASS  [ ] FAIL  - IP obtained after reconnect

Phase 5 - Stress Test:
  [ ] PASS  [ ] FAIL  - 10 reconnect cycles successful

Phase 6 - Long-Running:
  [ ] PASS  [ ] FAIL  - 24-hour stability test
  Ping failures: ____
  udhcpc anomalies: ____

Overall Result: [ ] PASS  [ ] FAIL

Notes:
_________________________________
_________________________________
_________________________________
```

---

**Document Created:** 2025-12-17
**Estimated Total Test Time:** 4-26 hours (depending on thoroughness)
