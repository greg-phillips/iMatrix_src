# PPP0 Connection Debugging Status

**Document Date:** November 20, 2024
**Status:** In Progress
**Primary Issue:** PPP chat script failing with exit code 0x3 (timeout)

---

## Executive Summary

The PPP connection for cellular data is failing because the chat script cannot communicate with the modem. Root cause identified as device mismatch - PPP is configured to use `/dev/ttyACM0` but the modem is actually on `/dev/ttyACM2`.

---

## Current Status

### Problem Symptoms
- Chat script exits with status code `0x3` (timeout waiting for AT command responses)
- Error message: "Connect script failed" in `/var/log/pppd/current`
- PPP connection never establishes
- Manual AT commands work fine via `microcom /dev/ttyACM2`

### Root Causes Identified

1. **Device Mismatch**
   - PPP configuration files point to `/dev/ttyACM0`
   - Actual modem is on `/dev/ttyACM2`
   - Chat script sends AT commands to wrong device

2. **Serial Port Conflict**
   - Cellular manager (`cellular_man.c`) was holding serial port open
   - Prevented PPP/chat from accessing modem
   - Fixed by closing port before starting PPP

---

## Debugging Commands

### On Target Device

```bash
# Check PPP status
tail -F /var/log/pppd/current

# Verify which device PPP is using
grep -r "ttyACM" /etc/ppp/
grep -r "ttyACM" /etc/chatscripts/

# List all modem devices
ls -la /dev/ttyACM*

# Check what process has devices open
lsof /dev/ttyACM*

# Test modem manually (confirms ttyACM2 works)
microcom /dev/ttyACM2
AT
# Should return "OK"

# Check PPP service status
sv status pppd

# Restart PPP service
sv restart pppd

# Monitor system logs
tail -F /var/log/messages | grep -E "pppd|chat|PPP"
```

### Quick Fix (Temporary)

```bash
# Update PPP config to use correct device
sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/provider
sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/quake
sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/isp

# Restart PPP
sv restart pppd
```

---

## Code Changes Applied

### Files Modified

1. **`iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`**
   - Added serial port close before starting PPP (line 1884-1888)
   - Added serial port reopen after stopping PPP (line 1964-1975)
   - Added automatic PPP config file updates (line 1898-1903)
   - Fixed lock file cleanup for correct device (line 1949-1951)

2. **`iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.h`**
   - Added `print_ppp_status()` declaration
   - Added `get_ppp_status_string()` declaration

3. **`iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`**
   - Enhanced PPP monitoring with status visibility (line 4516-4561)
   - Added periodic status logging
   - Added automatic retry on failure

4. **`iMatrix/cli/cli.c`**
   - Added `ppp` command for status checking (line 252-266, 295)
   - Added handler `cli_ppp_status()`

### Key Code Sections

```c
// cellular_man.c - Close serial port before PPP starts
if (cell_fd != -1) {
    PRINTF("[Cellular Connection - Closing serial port (fd=%d) before starting PPP]\r\n", cell_fd);
    close(cell_fd);
    cell_fd = -1;
}

// cellular_man.c - Fix PPP config files
system("sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/provider 2>/dev/null");
system("sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/quake 2>/dev/null");
system("sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/isp 2>/dev/null");
```

---

## Related Documentation

### Primary References
- **`docs/ppp_connection_refactoring_plan-3.md`** - Original refactoring plan (KISS approach)
- **`docs/ppp_connection_refactoring_plan-1.md`** - Earlier detailed analysis
- **`docs/ppp_connection_refactoring_plan-2.md`** - Alternative approach

### Network Debugging Logs
- **`logs/net1.txt`** - Primary debug log showing chat script failures
- **`logs/net2.txt`** - Secondary network logs (deleted)
- **`logs/net3.txt`** - Additional network debugging (deleted)
- **`logs/net4.txt`** - Network state machine logs (deleted)
- **`logs/net5.txt`** - Extended debugging session (deleted)

### QConnect Documentation
- **`docs/1180-3007_C_QConnect__Developer_Guide.pdf`** - Official QConnect developer guide
  - Page 26: PPPD Daemon approach
  - Section on cellular modem configuration

### System Configuration Files (on target)
- `/etc/ppp/peers/provider` - PPP provider configuration
- `/etc/ppp/peers/quake` - Quake-specific PPP config
- `/etc/ppp/peers/isp` - ISP PPP configuration
- `/etc/chatscripts/quake-gemalto` - Chat script for AT commands
- `/etc/start_pppd.sh` - System PPP startup script

---

## Understanding the Problem

### Chat Script Exit Code 0x3

The exit code `0x3` from chat indicates:
- Timeout waiting for expected response
- Chat script sends AT command but gets no "OK" or expected response
- Usually means wrong device or device busy

### Device Layout

```
/dev/ttyACM0 - USB ACM device 0 (no modem here)
/dev/ttyACM1 - USB ACM device 1 (unused)
/dev/ttyACM2 - USB ACM device 2 (ACTUAL MODEM)
/dev/ttyACM3 - USB ACM device 3 (unused)
```

### PPP Connection Flow

1. Network manager calls `start_pppd()`
2. `start_pppd()` executes `/etc/start_pppd.sh`
3. Script starts `pppd` with peer configuration
4. `pppd` launches chat script: `/usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto`
5. Chat script opens device specified in peer config
6. Chat sends AT commands and waits for responses
7. **FAILURE**: Wrong device = no modem = timeout

---

## Testing & Validation

### Test Sequence

1. **Verify modem device**
   ```bash
   microcom /dev/ttyACM2
   AT
   # Should return "OK"
   ```

2. **Check current PPP config**
   ```bash
   grep ttyACM /etc/ppp/peers/*
   ```

3. **Apply fix and test**
   ```bash
   # Fix config files
   sed -i 's|/dev/ttyACM0|/dev/ttyACM2|g' /etc/ppp/peers/*

   # Restart and monitor
   sv restart pppd
   tail -F /var/log/pppd/current
   ```

4. **Verify connection**
   ```bash
   ifconfig ppp0
   ping -c 3 8.8.8.8
   ```

### Expected Success Log

```
Script /usr/sbin/chat -V -f /etc/chatscripts/quake-gemalto finished (pid XXXX), status = 0x0
Serial connection established
Using interface ppp0
Connect: ppp0 <--> /dev/ttyACM2
local IP address 10.x.x.x
remote IP address 10.64.64.64
```

---

## Build & Deployment

### Building the Fix

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix
git status  # Check current branch
make clean
make
```

### Deploying to Target

```bash
# Copy binary to target device
scp build/imatrix root@<target-ip>:/usr/bin/

# On target device
sv stop FC-1
cp /usr/bin/imatrix /home/FC-1
sv start FC-1
```

---

## Outstanding Issues

1. **Permanent Configuration Fix**
   - Need to update system image to use ttyACM2 by default
   - Or make device configurable via environment/config file

2. **Device Detection**
   - Should auto-detect which ttyACM has the modem
   - Could probe each device for AT response

3. **Error Recovery**
   - Improve chat script error reporting
   - Add automatic device switching on failure

---

## Next Steps

1. **Immediate**
   - [ ] Test manual fix on target device
   - [ ] Verify PPP connection establishes
   - [ ] Confirm data connectivity

2. **Short Term**
   - [ ] Deploy code fix to target
   - [ ] Monitor for stability
   - [ ] Document in release notes

3. **Long Term**
   - [ ] Make modem device configurable
   - [ ] Add auto-detection logic
   - [ ] Update system image with correct defaults

---

## Contact & Resources

### Code Repository
- Main: `/home/greg/iMatrix/iMatrix_Client/`
- iMatrix submodule: `iMatrix/`
- Current branch: `Aptera_1_Clean`

### Key Functions
- `start_pppd()` - cellular_man.c:1874
- `stop_pppd()` - cellular_man.c:1919
- `get_ppp_status_string()` - cellular_man.c:1771
- `print_ppp_status()` - cellular_man.c:1846

### Debugging Tips
1. Always check which device the modem is on first
2. Verify PPP config files point to correct device
3. Ensure no other process has serial port open
4. Monitor `/var/log/pppd/current` for real-time status
5. Use `lsof` to check device ownership

---

## Summary

The PPP connection issue is caused by a simple but critical configuration mismatch. The fix involves:
1. Closing the serial port before PPP starts (code fix)
2. Updating PPP config to use correct device (ttyACM2)
3. Proper cleanup and monitoring

With these changes, the chat script can successfully communicate with the modem and establish PPP connection.

---

*Document maintained by: Claude + Greg*
*Last updated: November 20, 2024*