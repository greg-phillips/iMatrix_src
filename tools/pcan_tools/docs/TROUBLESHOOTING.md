# PCAN TRC Logger - Troubleshooting Guide

This guide helps resolve common issues with the PCAN TRC Logger.

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Connection Problems](#connection-problems)
3. [Runtime Errors](#runtime-errors)
4. [Performance Issues](#performance-issues)
5. [Data Quality Problems](#data-quality-problems)
6. [Platform-Specific Issues](#platform-specific-issues)
7. [Diagnostic Commands](#diagnostic-commands)

## Installation Issues

### Python-can Installation Fails

**Problem:** `pip install python-can` fails with error

**Solutions:**
1. Update pip first:
   ```bash
   python3 -m pip install --upgrade pip
   ```

2. Install with user flag:
   ```bash
   pip install --user python-can
   ```

3. Use virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install python-can
   ```

### PCAN Drivers Not Found

**Problem:** "Failed to open PCAN bus" even with hardware connected

**Linux Solutions:**
1. Check if drivers are loaded:
   ```bash
   lsmod | grep peak
   ```

2. Load drivers manually:
   ```bash
   sudo modprobe peak_usb
   ```

3. Reinstall PCAN drivers:
   ```bash
   cd /path/to/peak-linux-driver
   sudo make clean
   make
   sudo make install
   sudo modprobe peak_usb
   ```

**Windows Solutions:**
1. Install PCAN-Basic from PEAK-System website
2. Check Device Manager for PCAN device
3. Update USB drivers if yellow warning icon present

## Connection Problems

### "Failed to open PCAN bus" Error

**Common Causes and Solutions:**

#### 1. Permission Denied (Linux)
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Logout and login again, then verify
groups | grep dialout

# Alternative: Run with sudo (not recommended)
sudo ./pcan_trc_logger.py --bitrate 500000
```

#### 2. Device Not Connected
```bash
# Linux: Check USB devices
lsusb | grep -i peak

# Linux: Check device files
ls -la /dev/pcan*

# Windows: Check Device Manager
# Look under "Universal Serial Bus controllers"
```

#### 3. Wrong Channel Name
```bash
# List available channels (Linux)
ls /dev/pcan*

# Common channel names:
# PCAN_USBBUS1, PCAN_USBBUS2, etc.
# PCAN_PCIBUS1, PCAN_PCIBUS2
# PCAN_LANBUS1, PCAN_LANBUS2
```

#### 4. Device Already in Use
```bash
# Check if another process is using the device
lsof | grep pcan

# Kill the conflicting process
kill -9 <PID>
```

### "Invalid bitrate" Warning

**Problem:** Non-standard bitrate warning appears

**Solution:** Use standard CAN bitrates:
- 10000 (10 kbit/s)
- 20000 (20 kbit/s)
- 50000 (50 kbit/s)
- 100000 (100 kbit/s)
- 125000 (125 kbit/s)
- 250000 (250 kbit/s)
- 500000 (500 kbit/s) - Most common
- 800000 (800 kbit/s)
- 1000000 (1 Mbit/s)

### No CAN Messages Received

**Diagnostic Steps:**

1. **Check Bus Termination:**
   - Ensure 120Ω termination resistors at both ends
   - Measure resistance between CAN-H and CAN-L (should be ~60Ω)

2. **Verify Bitrate:**
   ```bash
   # Try different bitrates
   for rate in 125000 250000 500000; do
       echo "Testing $rate bit/s..."
       timeout 5 ./pcan_trc_logger.py --bitrate $rate -v
   done
   ```

3. **Check Wiring:**
   - CAN-H to CAN-H
   - CAN-L to CAN-L
   - GND to GND
   - No crossed wires

4. **Test Loopback:**
   ```bash
   # Enable self-reception to test transmission
   ./pcan_trc_logger.py --bitrate 500000 --receive-own
   # Send test message from another terminal
   ```

## Runtime Errors

### Segmentation Fault

**Possible Causes:**
1. Incompatible python-can version
2. Corrupted PCAN driver installation
3. Python version mismatch

**Solutions:**
```bash
# Reinstall python-can
pip uninstall python-can
pip install python-can==4.2.2

# Check Python version
python3 --version  # Should be 3.7+

# Reinstall PCAN drivers
sudo apt-get remove --purge peak-*
# Then reinstall from source
```

### "Keyboard interrupt received" Without Pressing Ctrl+C

**Cause:** System sending SIGINT signal

**Solution:**
```bash
# Run with nohup to ignore signals
nohup ./pcan_trc_logger.py --bitrate 500000 &

# Or use screen/tmux
screen -S canlog
./pcan_trc_logger.py --bitrate 500000
# Detach with Ctrl+A, D
```

### File Write Errors

**Problem:** "Permission denied" or "No space left on device"

**Solutions:**
1. Check disk space:
   ```bash
   df -h
   ```

2. Check write permissions:
   ```bash
   touch test.trc
   ls -la test.trc
   rm test.trc
   ```

3. Use different output directory:
   ```bash
   ./pcan_trc_logger.py --bitrate 500000 --outfile /tmp/test.trc
   ```

## Performance Issues

### High CPU Usage

**Solutions:**
1. Disable statistics:
   ```bash
   ./pcan_trc_logger.py --bitrate 500000 --stats-interval 0
   ```

2. Reduce verbosity:
   ```bash
   # Don't use -v or -vv flags
   ./pcan_trc_logger.py --bitrate 500000
   ```

3. Increase sleep time (edit script):
   ```python
   can.util.sleep(0.1)  # Instead of 0.05
   ```

### Dropped Messages

**Indicators:**
- Gaps in timestamps
- Missing expected messages
- Buffer overflow warnings

**Solutions:**
1. Use faster storage (SSD instead of HDD)
2. Reduce system load
3. Increase process priority:
   ```bash
   nice -n -10 ./pcan_trc_logger.py --bitrate 500000
   ```

### Large File Sizes

**Management Strategies:**
1. Compress old logs:
   ```bash
   gzip *.trc
   ```

2. Rotate logs periodically:
   ```bash
   # Use timeout to limit duration
   timeout 3600 ./pcan_trc_logger.py --bitrate 500000
   ```

3. Filter unnecessary messages (post-processing):
   ```bash
   grep -v "0x7FF" input.trc > filtered.trc
   ```

## Data Quality Problems

### Corrupted TRC Files

**Symptoms:**
- PCAN-View cannot open file
- Garbled data in file

**Prevention:**
1. Always use Ctrl+C to stop (not kill -9)
2. Ensure clean shutdown
3. Check filesystem integrity

**Recovery:**
```bash
# Try to extract valid portions
head -n 1000 corrupted.trc > recovered.trc
# Add proper TRC header if missing
```

### Wrong Timestamps

**Causes:**
- System clock incorrect
- NTP not synchronized

**Solutions:**
```bash
# Check system time
date

# Sync with NTP (Linux)
sudo ntpdate -s time.nist.gov

# Set timezone
sudo timedatectl set-timezone America/New_York
```

## Platform-Specific Issues

### Linux

#### USB Device Not Recognized
```bash
# Reset USB subsystem
sudo modprobe -r peak_usb
sudo modprobe peak_usb

# Check kernel messages
dmesg | tail -20
```

#### SELinux/AppArmor Blocking
```bash
# Temporarily disable SELinux
sudo setenforce 0

# Check AppArmor status
sudo aa-status
```

### Windows

#### Windows Defender Blocking
1. Add exception for pcan_trc_logger.py
2. Or temporarily disable real-time protection

#### USB Power Management
1. Device Manager → USB Root Hub → Properties
2. Power Management → Uncheck "Allow computer to turn off this device"

### macOS

#### System Integrity Protection (SIP)
```bash
# Check SIP status
csrutil status

# May need to disable for driver installation (not recommended)
# Reboot to Recovery Mode, then:
# csrutil disable
```

#### Homebrew Issues
```bash
# Reinstall PCAN formula
brew uninstall pcan-basic
brew install pcan-basic
```

## Diagnostic Commands

### Quick Diagnostics Script
```bash
#!/bin/bash
echo "=== PCAN Diagnostics ==="

echo "1. Python version:"
python3 --version

echo "2. python-can installed:"
python3 -c "import can; print(can.__version__)" 2>/dev/null || echo "NOT INSTALLED"

echo "3. PCAN drivers loaded (Linux):"
lsmod | grep peak || echo "No PEAK modules loaded"

echo "4. PCAN devices:"
ls -la /dev/pcan* 2>/dev/null || echo "No PCAN devices found"

echo "5. USB devices:"
lsusb | grep -i peak || echo "No PEAK USB devices found"

echo "6. User groups:"
groups | grep dialout || echo "Not in dialout group"

echo "7. Available disk space:"
df -h .

echo "=== End Diagnostics ==="
```

### Test Connection Script
```python
#!/usr/bin/env python3
import can
import sys

bitrates = [125000, 250000, 500000, 1000000]
channels = ["PCAN_USBBUS1", "PCAN_USBBUS2"]

for channel in channels:
    for bitrate in bitrates:
        try:
            print(f"Testing {channel} @ {bitrate} bit/s...", end="")
            bus = can.Bus(interface="pcan", channel=channel, bitrate=bitrate)
            bus.shutdown()
            print(" SUCCESS")
            sys.exit(0)
        except Exception as e:
            print(f" Failed: {e}")

print("No working configuration found!")
sys.exit(1)
```

## Getting Help

If problems persist after trying these solutions:

1. **Enable Debug Logging:**
   ```bash
   ./pcan_trc_logger.py --bitrate 500000 -vv 2>debug.log
   ```

2. **Collect System Information:**
   ```bash
   uname -a > system_info.txt
   python3 --version >> system_info.txt
   pip list | grep can >> system_info.txt
   lsusb >> system_info.txt
   dmesg | tail -50 >> system_info.txt
   ```

3. **Contact Support:**
   - Include debug.log and system_info.txt
   - Describe steps to reproduce issue
   - Specify hardware model (PCAN-USB, PCAN-USB Pro, etc.)

## Common Error Messages Reference

| Error Message | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| "Failed to open PCAN bus" | No device/wrong channel | Check connection and channel name |
| "Permission denied" | Insufficient privileges | Add user to dialout group |
| "Invalid bitrate" | Non-standard rate | Use standard bitrate |
| "No module named 'can'" | python-can not installed | pip install python-can |
| "Device or resource busy" | Device in use | Kill other PCAN processes |
| "No such file or directory" | Drivers not installed | Install PCAN drivers |
| "Keyboard interrupt" | Ctrl+C pressed | Normal shutdown |
| "Segmentation fault" | Driver/library issue | Reinstall drivers |