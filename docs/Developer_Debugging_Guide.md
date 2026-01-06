# Fleet-Connect-1 Developer Debugging Guide

**Document Version:** 1.0
**Date:** 2026-01-06
**Author:** Claude Code
**Status:** Production

---

## Table of Contents

1. [Introduction](#introduction)
2. [Device Connection Methods](#device-connection-methods)
3. [SSH Access and Log Files](#ssh-access-and-log-files)
4. [Using the fc1 Script](#using-the-fc1-script)
5. [CLI Command Execution](#cli-command-execution)
6. [Debug Flags System](#debug-flags-system)
7. [Log Analysis and Debugging](#log-analysis-and-debugging)
8. [Practical Debugging Workflows](#practical-debugging-workflows)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Quick Reference](#quick-reference)

---

## Introduction

This guide provides comprehensive instructions for developers debugging the Fleet-Connect-1 application running on QConnect gateway devices. It covers:

- How to connect to the device under test
- How to use SSH for remote access
- How to download and analyze log files
- How to use the `fc1` script to execute CLI commands
- How to configure debug flags for targeted logging
- Practical debugging workflows and troubleshooting

### Prerequisites

| Requirement | Details |
|-------------|---------|
| Development Host | Linux (Ubuntu/WSL2 recommended) |
| sshpass | Required for non-interactive SSH (`sudo apt-get install sshpass`) |
| Network Access | USB, WiFi, or Ethernet connection to gateway |
| Build Tools | CMake, ARM cross-compiler for code changes |

---

## Device Connection Methods

### Connection Options Overview

The Fleet-Connect-1 device supports multiple connection methods:

| Method | IP Address | Port | Use Case |
|--------|------------|------|----------|
| USB (Default) | `192.168.7.1` | 22222 | Development and debugging |
| WiFi | `192.168.111.2` | 22222 | Over-the-air updates |
| Ethernet | Device-specific | 22222 | Factory/production |
| Cellular PPP | Via SSH tunnel | 22222 | Remote field debugging |

### USB Connection (Recommended for Development)

The USB connection provides a direct network link between your development machine and the gateway.

**Setup:**
1. Connect USB cable between development PC and gateway
2. Gateway appears as a USB Ethernet adapter
3. Default IP: `192.168.7.1` (gateway) / `192.168.7.2` (host)

**Verify Connection:**
```bash
# Check if device is reachable
ping -c 3 192.168.7.1

# Check if SSH port is open
nc -zv 192.168.7.1 22222
```

### WiFi Connection

**Default WiFi Configuration:**
- SSID: `QConnect-FC1-XXXX` (where XXXX is device-specific)
- Password: Device-specific
- Gateway IP: `192.168.111.2`

```bash
# Connect using WiFi
./fc1 -d 192.168.111.2 ssh
```

### Connection Credentials

| Parameter | Default Value |
|-----------|---------------|
| Host | `192.168.7.1` |
| Port | `22222` |
| User | `root` |
| Password | `PasswordQConnect` |

---

## SSH Access and Log Files

### Direct SSH Connection

**Using the fc1 script (recommended):**
```bash
# Interactive SSH session
./scripts/fc1 ssh

# SSH to a specific host
./scripts/fc1 -d 192.168.111.2 ssh
```

**Using SSH directly:**
```bash
# With sshpass for automation
sshpass -p 'PasswordQConnect' ssh -o StrictHostKeyChecking=no -p 22222 root@192.168.7.1

# Interactive (will prompt for password)
ssh -p 22222 root@192.168.7.1
```

### Log File Locations on Device

| Log Type | Path | Description |
|----------|------|-------------|
| Application Log | `/var/log/fc-1.log` | Main FC-1 application log |
| Service Log | `/var/log/FC-1/current` | Runit service log |
| PPP Log | `/var/log/pppd/current` | PPP/Cellular connection log |
| Kernel Log | `/var/log/messages` | System kernel messages |
| System Log | `/var/log/syslog` | General system log |

### Viewing Logs on Device

```bash
# Connect to device
./fc1 ssh

# View application log (tail -f for live monitoring)
tail -f /var/log/fc-1.log

# View last 100 lines of application log
tail -100 /var/log/fc-1.log

# Search for specific content
grep -i "error" /var/log/fc-1.log
grep "CAN" /var/log/fc-1.log

# View service log
cat /var/log/FC-1/current

# View PPP log for cellular debugging
tail -100 /var/log/pppd/current
```

### Downloading Log Files

**Download specific log:**
```bash
# From your development machine
sshpass -p 'PasswordQConnect' scp -P 22222 root@192.168.7.1:/var/log/fc-1.log ./logs/

# Download with timestamp
sshpass -p 'PasswordQConnect' scp -P 22222 root@192.168.7.1:/var/log/fc-1.log ./logs/fc-1_$(date +%Y%m%d_%H%M%S).log
```

**Download all relevant logs:**
```bash
#!/bin/bash
# download_logs.sh - Download all logs from device

DEVICE="192.168.7.1"
PORT="22222"
PASS="PasswordQConnect"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="./logs/${TIMESTAMP}"

mkdir -p "$LOG_DIR"

# Download logs
sshpass -p "$PASS" scp -P $PORT root@$DEVICE:/var/log/fc-1.log "$LOG_DIR/"
sshpass -p "$PASS" scp -P $PORT root@$DEVICE:/var/log/FC-1/current "$LOG_DIR/service.log"
sshpass -p "$PASS" scp -P $PORT root@$DEVICE:/var/log/pppd/current "$LOG_DIR/ppp.log"

echo "Logs downloaded to: $LOG_DIR"
```

### Live Log Streaming

```bash
# Stream application log in real-time
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 'tail -f /var/log/fc-1.log'

# Stream with grep filter for specific messages
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 'tail -f /var/log/fc-1.log | grep --line-buffered "CAN\|Error"'
```

---

## Using the fc1 Script

The `fc1` script (`scripts/fc1`) is the primary tool for managing and debugging Fleet-Connect-1 on remote devices.

### Basic Usage

```bash
./scripts/fc1 [-d <destination>] <command> [options]
```

### Service Control Commands

| Command | Description |
|---------|-------------|
| `start` | Start FC-1 runit service |
| `stop` | Stop FC-1 runit service |
| `restart` | Restart FC-1 service |
| `status` | Show service status (default) |
| `enable` | Enable auto-start and start service |
| `disable` | Disable auto-start |

**Examples:**
```bash
./fc1 start              # Start FC-1
./fc1 stop               # Stop FC-1
./fc1 restart            # Restart FC-1
./fc1 status             # Check service status
./fc1 enable             # Enable and start
./fc1 disable -y         # Disable without prompt
```

### Deployment Commands

| Command | Description |
|---------|-------------|
| `push` | Deploy FC-1 binary (service stays stopped) |
| `push -run` | Deploy binary and start service |
| `config <file>` | Deploy config file |

**Development Workflow:**
```bash
# Build
cd Fleet-Connect-1/build && make -j4

# Deploy and run
cd ../../scripts
./fc1 push -run

# Verify deployment
./fc1 cmd "v"            # Check version
./fc1 status             # Check service status
```

### Log and Status Commands

```bash
./fc1 log                # View recent application logs
./fc1 ppp                # View PPP link status
```

---

## CLI Command Execution

### Two Methods for Remote CLI Access

**Method 1: Using `fc1 cmd` (Recommended)**
```bash
./fc1 cmd "<command>"
```

**Method 2: Interactive SSH + microcom**
```bash
./fc1 ssh
microcom /usr/qk/etc/sv/FC-1/console
# Press Enter to see prompt
# Type commands directly
# Press Ctrl+X to exit microcom
```

### CLI Modes

The CLI has two modes:

1. **CLI Mode (Default)**: iMatrix system commands (memory, network, debug, etc.)
   - Prompt: `>`

2. **App Mode**: Fleet-Connect-1 application commands (CAN, OBD2, vehicle, etc.)
   - Prompt: `app>`

**Mode Switching:**
- Press `TAB` to toggle between modes
- Type `app` in CLI mode to switch to App mode
- Type `exit` in App mode to return to CLI mode

### Direct App Command Access (New Feature)

Execute app CLI commands directly from CLI mode without switching modes using the `app:` prefix:

```bash
# Using fc1 cmd
./fc1 cmd "app: loopstatus"     # With space after colon
./fc1 cmd "app:loopstatus"      # Without space (also works)
./fc1 cmd "app: s"              # App status
./fc1 cmd "app: c"              # App configuration
./fc1 cmd "app: debug ?"        # App debug flags

# Interactive (at CLI prompt >)
>app: loopstatus
>app:s
```

The CLI stays in CLI mode after the command executes - no mode switching occurs.

### Common CLI Commands

**System Commands (CLI Mode):**
```bash
./fc1 cmd "?"                   # Full command list
./fc1 cmd "v"                   # Version information
./fc1 cmd "s"                   # System status
./fc1 cmd "mem"                 # Memory status
./fc1 cmd "ms"                  # Memory statistics
./fc1 cmd "net"                 # Network status
./fc1 cmd "ppp"                 # PPP status
./fc1 cmd "cell status"         # Cellular status
./fc1 cmd "imx stats"           # iMatrix statistics
./fc1 cmd "debug ?"             # Debug flags help
./fc1 cmd "log"                 # Logging status
./fc1 cmd "config"              # Device configuration
```

**Application Commands (App Mode or via `app:` prefix):**
```bash
./fc1 cmd "app: ?"              # App command list
./fc1 cmd "app: loopstatus"     # CAN processing loop status
./fc1 cmd "app: s"              # App status
./fc1 cmd "app: c"              # App configuration
./fc1 cmd "app: can"            # CAN bus status
./fc1 cmd "app: obd2"           # OBD2 status
./fc1 cmd "app: trip"           # Trip information
./fc1 cmd "app: debug ?"        # App debug flags help
```

### Special Characters in Commands

Always quote commands containing special characters:
```bash
./fc1 cmd "debug ?"             # Correct - ? is quoted
./fc1 cmd debug ?               # Wrong - ? may be expanded by shell
```

---

## Debug Flags System

The system uses two separate sets of debug flags:

1. **iMatrix Debug Flags**: System-level debugging (networking, memory, CoAP, etc.)
2. **Application Debug Flags**: Fleet-Connect-1 specific debugging (CAN, OBD2, vehicle, etc.)

### iMatrix Debug Commands (CLI Mode)

**Basic Debug Control:**
```bash
./fc1 cmd "debug on"            # Enable debug output (master switch)
./fc1 cmd "debug off"           # Disable debug output
./fc1 cmd "debug ?"             # List all available flags with hex values
```

**Setting Debug Flags:**
```bash
# Set specific flag (replaces all flags)
./fc1 cmd "debug 0x1"           # Enable DEBUGS_GENERAL only

# Add flags to current setting
./fc1 cmd "debug +0x100"        # Add BLE debugging

# Remove flags from current setting
./fc1 cmd "debug -0x100"        # Remove BLE debugging

# Set multiple flags
./fc1 cmd "debug 0x180001"      # Enable multiple flags at once
```

**Common iMatrix Debug Flags:**

| Flag | Hex Value | Description |
|------|-----------|-------------|
| DEBUGS_GENERAL | 0x0000000000000001 | General debugging |
| DEBUGS_FOR_XMIT | 0x0000000000000002 | CoAP transmit |
| DEBUGS_FOR_RECV | 0x0000000000000004 | CoAP receive |
| DEBUGS_FOR_IMX_UPLOAD | 0x0000000000000010 | iMatrix upload |
| DEBUGS_FOR_MEMORY_MANAGER | 0x0000000000004000 | Memory manager |
| DEBUGS_FOR_ETH0_NETWORKING | 0x0000000000020000 | Ethernet networking |
| DEBUGS_FOR_WIFI0_NETWORKING | 0x0000000000040000 | WiFi networking |
| DEBUGS_FOR_PPP0_NETWORKING | 0x0000000000080000 | PPP/Cellular networking |
| DEBUGS_FOR_NETWORKING_SWITCH | 0x0000000000100000 | Network switching |
| DEBUGS_FOR_CANBUS | 0x0000020000000000 | CAN bus |
| DEBUGS_FOR_CANBUS_DATA | 0x0000040000000000 | CAN bus data |
| DEBUGS_FOR_GPS | 0x0000001000000000 | GPS |
| DEBUGS_FOR_GPS_DATA | 0x0000002000000000 | GPS data |
| DEBUGS_FOR_CELLUAR | 0x0000000800000000 | Cellular modem |

### Application Debug Commands (App Mode)

**Basic Debug Control:**
```bash
./fc1 cmd "app: debug on"       # Enable app debug output
./fc1 cmd "app: debug off"      # Disable app debug output
./fc1 cmd "app: debug ?"        # List all app debug flags
```

**Setting App Debug Flags:**
```bash
# Set specific flag
./fc1 cmd "app: debug general"  # Enable general app debugging

# Using hex values
./fc1 cmd "app: debug 0x1"      # DEBUGS_APP_GENERAL
./fc1 cmd "app: debug +0x20"    # Add CAN controller debug
./fc1 cmd "app: debug -0x20"    # Remove CAN controller debug
```

**Common Application Debug Flags:**

| Flag | Bit | Hex Value | Description |
|------|-----|-----------|-------------|
| DEBUGS_APP_GENERAL | 0 | 0x00000001 | General app debugging |
| DEBUGS_APP_HAL | 1 | 0x00000002 | HAL functions |
| DEBUGS_APP_GPIO | 2 | 0x00000004 | GPIO operations |
| DEBUGS_APP_POWER | 3 | 0x00000008 | Power management |
| DEBUGS_APP_ENERGY_MANAGER | 4 | 0x00000010 | Energy manager |
| DEBUGS_APP_CAN_CTRL | 5 | 0x00000020 | CAN controller |
| DEBUGS_APP_CAN | 6 | 0x00000040 | CAN bus |
| DEBUGS_APP_CAN_READ | 7 | 0x00000080 | CAN read operations |
| DEBUGS_APP_CAN_DATA | 8 | 0x00000100 | CAN data |
| DEBUGS_APP_CAN_UPLOAD | 9 | 0x00000200 | CAN upload |
| DEBUGS_APP_MAPPINGS | 10 | 0x00000400 | Signal mappings |
| DEBUGS_APP_OBD2 | 11 | 0x00000800 | OBD2 protocol |
| DEBUGS_APP_OBD2_READ | 12 | 0x00001000 | OBD2 reads |
| DEBUGS_APP_PID_READ | 13 | 0x00002000 | PID reads |
| DEBUGS_APP_SAMPLE | 14 | 0x00004000 | Sampling |
| DEBUGS_APP_HOST_UPLOAD | 15 | 0x00008000 | Upload to host |
| DEBUGS_APP_REGISTRATION | 16 | 0x00010000 | Vehicle registration |
| DEBUGS_APP_APTERA | 25 | 0x02000000 | Aptera vehicle |

### Debug Flag Storage

Debug flags are stored persistently in device configuration:
- **iMatrix flags**: `device_config.log_messages` (64-bit)
- **App flags**: `mgc.log_messages` (32-bit)

Settings persist across reboots. Use `debug 0` to clear all flags.

### Redirecting Debug Output to File

```bash
# Start logging to file
./fc1 cmd "debug save /tmp/debug.log"

# Reproduce the issue...

# Stop file logging
./fc1 cmd "debug stop"

# Download the log file
sshpass -p 'PasswordQConnect' scp -P 22222 root@192.168.7.1:/tmp/debug.log ./
```

---

## Log Analysis and Debugging

### Log Message Format

**Standard Format:**
```
[HH:MM:SS.mmm] Log message here
[14:32:15.234] Network state changed to CONNECTED
```

**With RTC Timestamp (when DEBUGS_LOG_RTC enabled):**
```
[HH:MM:SS.mmm] [UTC_HH:MM:SS.mmm] Log message
[14:32:15.234] [22:32:15.234] Network state changed
```

### Filtering Logs

**By Component:**
```bash
# CAN bus messages
grep -i "CAN" /var/log/fc-1.log

# Network messages
grep -i "network\|eth0\|wifi\|ppp" /var/log/fc-1.log

# GPS messages
grep -i "GPS\|location" /var/log/fc-1.log

# Upload messages
grep -i "upload\|coap" /var/log/fc-1.log
```

**By Severity:**
```bash
# Errors only
grep -i "error\|fail" /var/log/fc-1.log

# Warnings
grep -i "warn" /var/log/fc-1.log

# State changes
grep -i "state\|transition" /var/log/fc-1.log
```

**By Time Range:**
```bash
# Messages from specific hour
grep "^\[14:" /var/log/fc-1.log

# Messages from time range
awk '/^\[14:30:/ , /^\[14:45:/' /var/log/fc-1.log
```

### Common Log Patterns

**Startup Sequence:**
```
[00:00:01.123] FC-1 Application Starting
[00:00:01.234] Build: Jan 06 2026 @ 14:30:00
[00:00:01.345] Serial: XXXXXXXXXXXX
[00:00:02.456] Network Manager initialized
```

**CAN Bus Activity:**
```
[00:00:05.123] CAN bus initialized on can0
[00:00:05.234] CAN registration started
[00:00:10.345] Vehicle VIN: XXXXXXXXXXXXXXXXX
```

**Network State Changes:**
```
[00:01:00.123] Network state: DISCOVERING -> CONNECTING
[00:01:05.234] Interface eth0 acquired IP: 192.168.1.100
[00:01:05.345] Network state: CONNECTING -> CONNECTED
```

---

## Practical Debugging Workflows

### Workflow 1: CAN Bus Issues

**Symptoms:** CAN data not being received or processed

**Debug Steps:**
```bash
# 1. Check CAN interface status
./fc1 cmd "app: can"

# 2. Enable CAN debugging
./fc1 cmd "app: debug +0x1E0"   # CAN_CTRL + CAN + CAN_READ + CAN_DATA

# 3. Watch live logs
./fc1 ssh
tail -f /var/log/fc-1.log | grep --line-buffered "CAN"

# 4. Reproduce the issue and collect logs
# Ctrl+C to stop, then download logs

# 5. Disable debug flags when done
./fc1 cmd "app: debug -0x1E0"
```

### Workflow 2: Network Connectivity Issues

**Symptoms:** Unable to upload data, connection drops

**Debug Steps:**
```bash
# 1. Check network status
./fc1 cmd "net"
./fc1 cmd "ppp"

# 2. Enable network debugging
./fc1 cmd "debug +0x1E0000"    # ETH0 + WIFI0 + PPP0 + NETWORKING_SWITCH

# 3. Monitor network events
./fc1 ssh
tail -f /var/log/fc-1.log | grep --line-buffered "network\|eth\|wifi\|ppp"

# 4. Check cellular specifically
./fc1 cmd "cell status"
./fc1 ppp                       # PPP link status via fc1

# 5. Download and analyze logs
```

### Workflow 3: Upload/CoAP Issues

**Symptoms:** Data not appearing on server

**Debug Steps:**
```bash
# 1. Check iMatrix stats
./fc1 cmd "imx stats"

# 2. Enable upload debugging
./fc1 cmd "debug +0x16"        # XMIT + RECV + IMX_UPLOAD

# 3. Watch for upload attempts
./fc1 ssh
tail -f /var/log/fc-1.log | grep --line-buffered "upload\|coap\|XMIT\|RECV"

# 4. Force an upload cycle if available
./fc1 cmd "app: upload"        # If supported

# 5. Analyze results
```

### Workflow 4: Memory Issues

**Symptoms:** System slowdown, crashes

**Debug Steps:**
```bash
# 1. Check memory status
./fc1 cmd "mem"
./fc1 cmd "ms"

# 2. Enable memory debugging
./fc1 cmd "debug +0x4000"      # MEMORY_MANAGER

# 3. Monitor memory usage over time
./fc1 ssh
watch -n 5 'cat /proc/meminfo | head -5'

# 4. Check for memory leaks in logs
grep -i "alloc\|free\|memory" /var/log/fc-1.log
```

### Workflow 5: GPS/Location Issues

**Symptoms:** No location data, incorrect coordinates

**Debug Steps:**
```bash
# 1. Check GPS status (if command available)
./fc1 cmd "gps"

# 2. Enable GPS debugging
./fc1 cmd "debug +0x3000000000"  # GPS + GPS_DATA

# 3. Monitor GPS messages
./fc1 ssh
tail -f /var/log/fc-1.log | grep --line-buffered -i "gps\|lat\|lon\|location"
```

### Workflow 6: Complete System Debug

**For complex issues requiring full visibility:**

```bash
# 1. Stop service and run in foreground with all debug
./fc1 stop
./fc1 run

# 2. Or enable comprehensive debugging
./fc1 cmd "debug on"
./fc1 cmd "debug 0xFFFFFFFF"   # All iMatrix flags (lower 32)
./fc1 cmd "app: debug on"
./fc1 cmd "app: debug 0xFFFFFFFF"  # All app flags

# 3. Warning: This produces LOTS of output
# Redirect to file for analysis
./fc1 cmd "debug save /tmp/full_debug.log"

# 4. Reproduce issue

# 5. Stop and download
./fc1 cmd "debug stop"
sshpass -p 'PasswordQConnect' scp -P 22222 root@192.168.7.1:/tmp/full_debug.log ./

# 6. Disable all debugging when done
./fc1 cmd "debug 0"
./fc1 cmd "app: debug 0"
```

---

## Troubleshooting Guide

### Connection Issues

**Cannot reach device:**
```bash
# Check network
ping 192.168.7.1

# Check SSH port
nc -zv 192.168.7.1 22222

# Clear stale SSH key
./fc1 clear-key
```

**"Host key verification failed":**
```bash
./fc1 clear-key
# Or manually:
ssh-keygen -R "[192.168.7.1]:22222"
```

**"sshpass not found":**
```bash
sudo apt-get install sshpass
```

### Service Issues

**FC-1 not running:**
```bash
./fc1 status                    # Check status
./fc1 start                     # Start service
./fc1 log                       # Check for errors
```

**Service won't start:**
```bash
./fc1 ssh
ls -la /usr/qk/bin/FC-1         # Check binary exists
chmod +x /usr/qk/bin/FC-1       # Ensure executable
/usr/qk/bin/FC-1 -h             # Test binary directly
```

### CLI Command Issues

**"Expect not found on target":**
```bash
# Manually deploy expect tools
scp -P 22222 external_tools/build/expect-arm.tar.gz root@192.168.7.1:/tmp/
./fc1 ssh
mkdir -p /usr/qk/etc/sv/FC-1/expect
cd /usr/qk/etc/sv/FC-1/expect
tar xzf /tmp/expect-arm.tar.gz
```

**"microcom: can't create lock file":**
```bash
./fc1 ssh
rm /var/lock/LCK..console       # Remove stale lock
```

**Commands not responding:**
```bash
# Check if console is available
./fc1 ssh
ls -la /usr/qk/etc/sv/FC-1/console
# Should be a symlink to a PTY device
```

### Debug Output Issues

**No debug output appearing:**
```bash
# Check master debug switch
./fc1 cmd "debug on"

# Verify flags are set
./fc1 cmd "debug ?"             # Should show enabled flags

# Check if logging to file
./fc1 cmd "debug status"
```

**Too much debug output:**
```bash
# Disable all flags
./fc1 cmd "debug 0"
./fc1 cmd "app: debug 0"

# Enable only needed flags
./fc1 cmd "debug +0x1"          # Just general
```

---

## Quick Reference

### Essential fc1 Commands

```bash
# Service control
./fc1 status                    # Check status (default)
./fc1 start / stop / restart    # Service control
./fc1 push -run                 # Deploy and start

# CLI commands
./fc1 cmd "v"                   # Version
./fc1 cmd "s"                   # System status
./fc1 cmd "?"                   # Full help
./fc1 cmd "app: loopstatus"     # App loop status (direct)
./fc1 cmd "app: ?"              # App help (direct)

# Debug control
./fc1 cmd "debug on/off"        # Master switch
./fc1 cmd "debug ?"             # List flags
./fc1 cmd "debug +0xXXX"        # Add flags
./fc1 cmd "debug -0xXXX"        # Remove flags

# Logs
./fc1 log                       # View logs
./fc1 ssh                       # Interactive session
```

### SSH Quick Commands

```bash
# Log viewing
tail -f /var/log/fc-1.log                              # Live log
tail -100 /var/log/fc-1.log                            # Last 100 lines
grep -i "error" /var/log/fc-1.log                      # Search errors

# Download logs
sshpass -p 'PasswordQConnect' scp -P 22222 root@192.168.7.1:/var/log/fc-1.log ./
```

### Debug Flag Quick Reference

**iMatrix (use with `debug` command):**
```
0x1       - General
0x2       - CoAP TX
0x4       - CoAP RX
0x10      - Upload
0x4000    - Memory
0x20000   - Ethernet
0x40000   - WiFi
0x80000   - PPP
0x100000  - Network switching
```

**Application (use with `app: debug` command):**
```
0x1       - General
0x20      - CAN controller
0x40      - CAN bus
0x80      - CAN read
0x100     - CAN data
0x800     - OBD2
0x4000    - Sampling
0x8000    - Upload
0x10000   - Registration
```

### Log File Locations

| Log | Path |
|-----|------|
| Application | `/var/log/fc-1.log` |
| Service | `/var/log/FC-1/current` |
| PPP | `/var/log/pppd/current` |
| System | `/var/log/messages` |

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [fc1_script_reference.md](fc1_script_reference.md) | Complete fc1 script reference |
| [CLI_and_Debug_System_Complete_Guide.md](CLI_and_Debug_System_Complete_Guide.md) | Full CLI/debug technical details |
| [connecting_to_Fleet-Connect-1.md](connecting_to_Fleet-Connect-1.md) | Connection methods |
| [ssh_access_to_Fleet_Connect.md](ssh_access_to_Fleet_Connect.md) | SSH access details |

---

**Document Created:** 2026-01-06
**Author:** Claude Code
