# Connecting to Fleet-Connect-1 Device

**Date**: 2025-12-23
**Document Version**: 1.0
**Status**: Active

## Overview

The Fleet-Connect-1 is a BusyBox-based Linux embedded device. This document describes how to establish SSH connections for development, debugging, and profiling.

## Connection Details

| Parameter | Default Value |
|-----------|---------------|
| Host | 192.168.7.1 |
| Port | 22222 |
| User | root |
| Password | PasswordQConnect |

## Prerequisites

### Install sshpass (Recommended)

For non-interactive SSH connections (scripts, automation), install `sshpass`:

```bash
# Ubuntu/Debian
sudo apt-get install sshpass

# macOS (via Homebrew)
brew install hudochenkov/sshpass/sshpass

# Verify installation
command -v sshpass && echo "sshpass installed"
```

Without `sshpass`, you'll be prompted for the password on each connection.

## Method 1: Using the Connection Helper

The profiling system provides a configuration file with helper functions.

### Setup

1. Source the configuration file:

```bash
source Profiler/config/target_connection.conf
```

2. Verify the connection:

```bash
check_connection && echo "Connected!" || echo "Connection failed"
```

### Running Commands

Use `run_ssh` to execute commands on the target:

```bash
# Check device uptime
run_ssh "uptime"

# View running processes
run_ssh "ps"

# Check available memory
run_ssh "free"

# View system information
run_ssh "uname -a"

# Check disk usage
run_ssh "df -h"
```

### Transferring Files

Use `run_scp` for file transfers:

```bash
# Copy file TO the target
run_scp "./local_file.txt" "$(get_target):/tmp/"

# Copy file FROM the target
run_scp "$(get_target):/var/log/messages" "./target_logs.txt"

# Copy directory TO target (add -r flag manually if needed)
run_scp "./config_dir" "$(get_target):/etc/"
```

## Method 2: Direct SSH Connection

### Interactive Shell

```bash
# With sshpass (no password prompt)
sshpass -p "PasswordQConnect" ssh -p 22222 \
    -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile=/dev/null \
    root@192.168.7.1

# Without sshpass (will prompt for password)
ssh -p 22222 root@192.168.7.1
```

### Single Command Execution

```bash
sshpass -p "PasswordQConnect" ssh -p 22222 root@192.168.7.1 "ls -la /usr/qk"
```

### File Transfer with SCP

```bash
# Upload to target (note: -P uppercase for scp)
sshpass -p "PasswordQConnect" scp -P 22222 ./FC-1 root@192.168.7.1:/usr/qk/bin/

# Download from target
sshpass -p "PasswordQConnect" scp -P 22222 root@192.168.7.1:/var/log/messages ./
```

## Method 3: SSH Config File (Optional)

Add to `~/.ssh/config` for simplified access:

```
Host fc1
    HostName 192.168.7.1
    Port 22222
    User root
    StrictHostKeyChecking accept-new
    UserKnownHostsFile /dev/null
```

Then connect with:

```bash
# Still requires password (or use sshpass)
ssh fc1

# With sshpass
sshpass -p "PasswordQConnect" ssh fc1
```

## Common Tasks

### Deploy a New Binary

```bash
source Profiler/config/target_connection.conf

# Stop the running application
run_ssh "killall FC-1 2>/dev/null || true"

# Upload new binary
run_scp "./Fleet-Connect-1/build/FC-1" "$(get_target):/usr/qk/bin/"

# Set permissions
run_ssh "chmod +x /usr/qk/bin/FC-1"

# Restart (or let supervisor restart it)
run_ssh "/usr/qk/bin/FC-1 &"
```

### View Live Logs

```bash
# Tail system log
run_ssh "tail -f /var/log/messages"

# Or with direct SSH for better interactivity
sshpass -p "PasswordQConnect" ssh -p 22222 root@192.168.7.1 "tail -f /var/log/messages"
```

### Check Application Status

```bash
source Profiler/config/target_connection.conf

# Is FC-1 running?
run_ssh "pidof FC-1 && echo 'Running' || echo 'Not running'"

# Memory usage
run_ssh "cat /proc/\$(pidof FC-1)/status | grep -E 'VmRSS|VmSize'"
```

## BusyBox Considerations

The Fleet-Connect-1 runs BusyBox, a lightweight Unix utilities collection. Some differences from full Linux:

| Full Linux | BusyBox Equivalent |
|------------|-------------------|
| `ps aux` | `ps` (limited options) |
| `top -b -n 1` | `top -b -n 1` (may differ) |
| `netstat -tuln` | `netstat -tln` |
| `free -h` | `free` (no -h flag) |

When writing scripts, test commands on the target first to verify BusyBox compatibility.

## Troubleshooting

### Connection Refused

```bash
# Verify the device is reachable
ping 192.168.7.1

# Check if SSH port is open
nc -zv 192.168.7.1 22222
```

### Connection Timeout

- Verify you're on the correct network
- Check that TARGET_HOST is set correctly in the config
- Ensure no firewall is blocking port 22222

### Host Key Verification Failed

The helper scripts use `StrictHostKeyChecking=accept-new` to auto-accept new keys. If you get verification errors with direct SSH:

```bash
# Remove old key
ssh-keygen -R "[192.168.7.1]:22222"

# Reconnect
ssh -p 22222 root@192.168.7.1
```

### Permission Denied

- Verify password is correct
- Ensure you're connecting as `root`
- Check that sshpass is passing the password correctly

### sshpass Not Found

Install it (see Prerequisites) or use manual password entry:

```bash
ssh -p 22222 root@192.168.7.1
# Enter password when prompted: PasswordQConnect
```

## Security Notes

- The connection config contains credentials in plaintext
- Do not commit real passwords to version control
- The config file should be in `.gitignore`
- For production environments, consider SSH key-based authentication

## Related Documentation

- [FC1 Profiling On Target](../Profiler/docs/FC1_Profiling_On_Target.md)
- [SSH Access to Fleet Connect](ssh_access_to_Fleet_Connect.md)

---

*For issues with the connection helpers, see `Profiler/config/target_connection.conf`*
