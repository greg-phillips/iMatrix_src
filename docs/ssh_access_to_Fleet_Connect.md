# SSH Access to Fleet-Connect-1 Gateway

**Date Created:** 2025-12-23
**Last Updated:** 2025-12-31
**Version:** 1.1
**Author:** Claude Code

---

## 1. Overview

This document explains how to connect to a Fleet-Connect-1 (FC-1) gateway device via SSH for system examination, debugging, and configuration review.

### 1.1 Target Platform

| Item | Value |
|------|-------|
| Hardware | NXP i.MX6 (ARM Cortex-A9) |
| OS | BusyBox Linux (musl libc) |
| Kernel | 6.1.55-QConnect_v4.0.0 |
| SSH Port | **22222** (non-standard) |
| Default User | root |

---

## 2. Connection Credentials

### 2.1 Default Settings

| Parameter | Value |
|-----------|-------|
| Username | `root` |
| Host IP | `192.168.7.1` (USB network) |
| SSH Port | `22222` |
| Password | `PasswordQConnect` |

### 2.2 Network Interfaces

The gateway may be accessible via multiple interfaces:

| Interface | Typical IP | Notes |
|-----------|------------|-------|
| USB (usb0) | 192.168.7.1 | Direct USB connection to host |
| Ethernet (eth0) | DHCP assigned | Check router for IP |
| WiFi (wlan0) | DHCP assigned | If WiFi configured |

---

## 3. Connecting via SSH

### 3.1 Basic SSH Connection

```bash
# Standard SSH command (will prompt for password)
ssh -p 22222 root@192.168.7.1
```

When prompted, enter: `PasswordQConnect`

### 3.2 Using sshpass (Non-Interactive)

For scripted or repeated access, install `sshpass`:

```bash
# Install sshpass on Ubuntu/Debian
sudo apt-get install sshpass

# Connect without password prompt
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1
```

### 3.3 SSH Options for Convenience

Suppress host key warnings (useful for development):

```bash
ssh -p 22222 \
    -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 \
    root@192.168.7.1
```

### 3.4 Creating an SSH Alias

Add to `~/.ssh/config` for quick access:

```
Host fc1
    HostName 192.168.7.1
    Port 22222
    User root
    StrictHostKeyChecking accept-new
    UserKnownHostsFile /dev/null
```

Then simply:
```bash
ssh fc1
# Or with sshpass:
sshpass -p 'PasswordQConnect' ssh fc1
```

---

## 4. Examining the Linux System

### 4.1 System Information

```bash
# Kernel and OS info
uname -a
cat /etc/os-release

# CPU information
cat /proc/cpuinfo

# Memory usage
free -m
cat /proc/meminfo

# Disk usage
df -h

# Uptime and load
uptime
cat /proc/loadavg
```

### 4.2 Network Configuration

```bash
# IP addresses
ip addr
ifconfig

# Routing table
ip route
route -n

# Active connections
netstat -tlnp
ss -tlnp

# Network interfaces stats
ip -s link

# DNS configuration
cat /etc/resolv.conf
```

### 4.3 Process Information

```bash
# Running processes
ps aux
ps -ef

# Find FC-1 process
pidof FC-1
ps | grep FC-1

# Process details (replace PID)
cat /proc/<PID>/status
cat /proc/<PID>/cmdline
ls -la /proc/<PID>/fd/
```

### 4.4 System Logs

```bash
# Kernel messages
dmesg | tail -50

# System log (if available)
cat /var/log/messages

# FC-1 specific logs (filesystem logger)
ls -la /var/log/fc-1*.log
cat /var/log/fc-1.log
```

---

## 5. Key Directories and Files

### 5.1 FC-1 Application

| Path | Description |
|------|-------------|
| `/usr/qk/bin/FC-1` | Main application binary |
| `/usr/qk/etc/sv/FC-1/` | Service directory (run script, console, details) |
| `/usr/qk/etc/` | Application configuration |
| `/var/log/fc-1.log` | Application log file (filesystem logger) |
| `/var/log/FC-1/` | runit service logs (svlogd) |

### 5.2 System Configuration

| Path | Description |
|------|-------------|
| `/etc/` | System configuration files |
| `/etc/network/` | Network configuration |
| `/etc/init.d/` | Init scripts |
| `/etc/sv/` | runit service definitions |

### 5.3 Runtime Data

| Path | Description |
|------|-------------|
| `/tmp/` | Temporary files |
| `/var/run/` | PID files and runtime data |
| `/sys/class/net/` | Network interface sysfs |
| `/proc/` | Process and kernel info |

---

## 6. Service Management

The gateway uses **runit** for service management:

```bash
# Check FC-1 service status
sv status FC-1

# Stop FC-1
sv stop FC-1

# Start FC-1
sv start FC-1

# Restart FC-1
sv restart FC-1

# View service logs
cat /var/log/FC-1/current
```

---

## 7. File Transfer (SCP)

### 7.1 Copy Files TO Target

```bash
# Copy single file
scp -P 22222 localfile.txt root@192.168.7.1:/tmp/

# Copy directory
scp -P 22222 -r localdir/ root@192.168.7.1:/tmp/

# With sshpass
sshpass -p 'PasswordQConnect' scp -P 22222 localfile.txt root@192.168.7.1:/tmp/
```

### 7.2 Copy Files FROM Target

```bash
# Copy single file (application log)
scp -P 22222 root@192.168.7.1:/var/log/fc-1.log ./

# Copy all log files
scp -P 22222 root@192.168.7.1:/var/log/fc-1*.log ./logs/

# With sshpass
sshpass -p 'PasswordQConnect' scp -P 22222 root@192.168.7.1:/tmp/file.txt ./
```

---

## 8. Using the Profiler Configuration

The Profiler toolkit includes pre-configured SSH settings:

### 8.1 Configuration File

Location: `Profiler/config/target_connection.conf`

```bash
TARGET_USER="root"
TARGET_HOST="192.168.7.1"
TARGET_PORT="22222"
TARGET_PASS="PasswordQConnect"
```

### 8.2 Test Connection Script

```bash
cd ~/iMatrix/iMatrix_Client/Profiler
./scripts/test_connection.sh
```

### 8.3 Using Profiler's SSH Functions

Source the configuration for scripted access:

```bash
cd ~/iMatrix/iMatrix_Client/Profiler
source config/target_connection.conf

# Use the helper function
run_ssh "uname -a"
run_ssh "df -h"
run_ssh "ps | grep FC-1"
```

---

## 9. Common Examination Tasks

### 9.1 Check FC-1 Status

```bash
ssh -p 22222 root@192.168.7.1 "sv status FC-1; pidof FC-1"
```

### 9.2 View Memory Usage

```bash
ssh -p 22222 root@192.168.7.1 "free -m; ps aux | head -10"
```

### 9.3 Check Network Connectivity

```bash
ssh -p 22222 root@192.168.7.1 "ip addr; ip route; ping -c 3 8.8.8.8"
```

### 9.4 View CAN Bus Status

```bash
ssh -p 22222 root@192.168.7.1 "ip link show can0; cat /proc/net/can/stats"
```

### 9.5 Check Disk Space

```bash
ssh -p 22222 root@192.168.7.1 "df -h; du -sh /var/log/*"
```

### 9.6 View FC-1 File Descriptors

```bash
ssh -p 22222 root@192.168.7.1 "ls -la /proc/\$(pidof FC-1)/fd/"
```

---

## 10. Troubleshooting

### 10.1 Connection Refused

```bash
# Check if target is reachable
ping 192.168.7.1

# Check if SSH port is open
nc -zv 192.168.7.1 22222
```

### 10.2 Connection Timeout

- Verify USB cable is connected (for USB network)
- Check IP address is correct
- Verify network interface is up on host

```bash
# Check USB network interface on host
ip addr show usb0
```

### 10.3 Permission Denied

- Verify password is correct: `PasswordQConnect`
- Check username is `root`
- Ensure port is `22222` (not default 22)

### 10.4 Host Key Changed

If target was reflashed, clear old host key:

```bash
ssh-keygen -R "[192.168.7.1]:22222"
```

Or use options to ignore:
```bash
ssh -p 22222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.7.1
```

---

## 11. Security Notes

1. **Default credentials** should be changed in production environments
2. **Port 22222** is non-standard to avoid automated scanning
3. **Root access** is enabled for development; consider restricting in production
4. **sshpass** stores passwords in process list; use SSH keys for production
5. The configuration file `target_connection.conf` is **git-ignored** to protect credentials

---

## 12. Quick Reference

```bash
# One-liner connection
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1

# Quick system check
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 "uname -a; uptime; free -m; df -h"

# Interactive shell with alias (after configuring ~/.ssh/config)
ssh fc1
```

---

*Document Version: 1.1*
*Last Updated: 2025-12-31*
