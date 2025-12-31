# FC-1 Filesystem Logging System

**Document Version**: 1.0
**Date**: 2025-12-30
**Author**: Claude Code
**Status**: Approved

## Overview

The FC-1 gateway uses a filesystem-based logging system that captures all diagnostic output to persistent storage. This enables post-mortem debugging, remote log retrieval, and long-term operational monitoring without requiring a console connection.

## Log File Location

| Item | Value |
|------|-------|
| **Primary Log** | `/var/log/fc-1.log` |
| **Rotated Logs** | `/var/log/fc-1.YYYY-MM-DD.log` |
| **Max File Size** | 10 MB |
| **Retention** | 5 days OR 100 MB total |

## Operating Modes

### Quiet Mode (Default)

In production, FC-1 runs in quiet mode where all log output goes **only** to the filesystem:

```bash
/usr/qk/bin/FC-1
```

- No console output (stdout is silent)
- All logs written to `/var/log/fc-1.log`
- Ideal for production deployments

### Interactive Mode (-i)

For development and debugging, use the `-i` flag to enable console output:

```bash
/usr/qk/bin/FC-1 -i
```

- Logs written to **both** console and filesystem
- Useful for real-time debugging
- Shows startup banner confirming mode

## Accessing Logs on the Device

### SSH Connection

Connect to the device via SSH:

```bash
ssh -p 22222 root@<device-ip>
# Password: PasswordQConnect
```

### Viewing Live Logs

```bash
# Follow log in real-time
tail -f /var/log/fc-1.log

# View last 100 lines
tail -100 /var/log/fc-1.log

# Search for specific patterns
grep "ERROR" /var/log/fc-1.log
grep "CAN" /var/log/fc-1.log
grep "Cellular" /var/log/fc-1.log
```

### Viewing Rotated Logs

```bash
# List all log files
ls -la /var/log/fc-1*.log

# View a specific date's log
cat /var/log/fc-1.2025-12-30.log
```

### Downloading Logs via SCP

```bash
# Download current log
scp -P 22222 root@<device-ip>:/var/log/fc-1.log ./

# Download all logs
scp -P 22222 root@<device-ip>:/var/log/fc-1*.log ./
```

## Log Format

Each log entry follows this format:

```
[HH:MM:SS.mmm] [MODULE] Message text
```

Example:
```
[00:01:39.386] [DEBUG] AT response state initialized
[00:01:39.490] [Cellular Connection - Cellular state changed from 14 (ONLINE) to 3 (GET_RESPONSE)]
[00:01:39.529] [NETMGR-PPP0] State: NET_ONLINE_CHECK_RESULTS | PPP0 using peer address as gateway: 10.64.64.64
```

### Log Session Header

Each time FC-1 starts, a session header is written:

```
=== FC-1 Log Started: 2025-12-30 23:44:06 ===
```

## Log Rotation

Rotation occurs automatically under these conditions:

| Trigger | Description |
|---------|-------------|
| **Startup** | New session starts, previous log rotated |
| **Daily** | At midnight, current log is rotated |
| **Size Limit** | When log exceeds 10 MB |

Rotated files are renamed with the date: `fc-1.YYYY-MM-DD.log`

### Retention Policy

The system automatically deletes old logs based on:

- **Age**: Logs older than 5 days are deleted
- **Total Size**: If total log size exceeds 100 MB, oldest logs are deleted first

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Application Code                      │
│                                                         │
│   imx_cli_log_printf() ──► fs_logger_write()           │
│                                │                        │
│                                ▼                        │
│                    ┌───────────────────┐               │
│                    │  Write Buffer     │               │
│                    │  (Thread-safe)    │               │
│                    └─────────┬─────────┘               │
│                              │                          │
│                              ▼                          │
│                    ┌───────────────────┐               │
│                    │  /var/log/fc-1.log│               │
│                    └───────────────────┘               │
│                                                         │
│   ┌─────────────────────────────────────┐              │
│   │  Background Rotation Thread          │              │
│   │  (Async, non-blocking)              │              │
│   └─────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### Key Source Files

| File | Purpose |
|------|---------|
| `iMatrix/cli/filesystem_logger.h` | API declarations and configuration constants |
| `iMatrix/cli/filesystem_logger.c` | Core implementation (rotation, retention, thread safety) |
| `iMatrix/cli/interface.c` | Integration point in `imx_cli_log_printf()` |
| `iMatrix/imatrix_interface.c` | Initialization and `-i` option parsing |

### Thread Safety

The logging system is fully thread-safe:

- Mutex-protected file operations
- Async rotation runs in background thread
- Condition variable signaling for rotation requests
- Non-blocking writes to avoid impacting CAN processing

## Configuration

Configuration constants are defined in `filesystem_logger.h`:

```c
#define FS_LOG_DIRECTORY        "/var/log"
#define FS_LOG_FILENAME         "fc-1.log"
#define FS_LOG_MAX_SIZE         (10 * 1024 * 1024)  // 10 MB
#define FS_LOG_MAX_AGE_DAYS     5
#define FS_LOG_MAX_TOTAL_SIZE   (100 * 1024 * 1024) // 100 MB
```

## API Reference

### Initialization

```c
#include "cli/filesystem_logger.h"

// Initialize the logging system (called automatically at startup)
imx_result fs_logger_init(void);
```

### Writing Logs

Application code typically uses the standard logging macro:

```c
imx_cli_log_printf(true, "My message: %s\n", value);
```

For direct filesystem logging:

```c
fs_logger_write("Direct log message\n");
```

### Shutdown

```c
// Clean shutdown (flushes buffers, stops rotation thread)
void fs_logger_shutdown(void);
```

### Status Checks

```c
// Check if logger is active
bool fs_logger_is_active(void);

// Global variable for interactive mode
extern bool fs_logger_interactive_mode;
```

## Troubleshooting

### Logs Not Being Written

1. Check if FC-1 is running:
   ```bash
   sv status /usr/qk/etc/sv/FC-1
   ```

2. Check disk space:
   ```bash
   df -h /var/log
   ```

3. Check file permissions:
   ```bash
   ls -la /var/log/fc-1.log
   ```

### Log File Too Large

The system should auto-rotate at 10 MB. If not:

1. Check for rotation thread issues in system logs
2. Manually rotate:
   ```bash
   mv /var/log/fc-1.log /var/log/fc-1.manual-backup.log
   sv restart /usr/qk/etc/sv/FC-1
   ```

### No Console Output in Interactive Mode

Verify the `-i` flag is being passed:

```bash
# Check the run script
cat /usr/qk/etc/sv/FC-1/run

# For interactive debugging, run manually:
sv stop /usr/qk/etc/sv/FC-1
/usr/qk/bin/FC-1 -i
```

### Finding Specific Events

```bash
# CAN bus events
grep -i "can" /var/log/fc-1.log

# Network events
grep -i "netmgr\|network" /var/log/fc-1.log

# Cellular events
grep -i "cellular\|AT\|ppp" /var/log/fc-1.log

# Errors only
grep -i "error\|fail\|warn" /var/log/fc-1.log

# Events in time range (e.g., between 01:30 and 01:45)
grep "^\[01:3[0-9]\|^\[01:4[0-5]" /var/log/fc-1.log
```

## Service Management

### Start/Stop/Restart

```bash
# Using runit service manager
sv start /usr/qk/etc/sv/FC-1
sv stop /usr/qk/etc/sv/FC-1
sv restart /usr/qk/etc/sv/FC-1
sv status /usr/qk/etc/sv/FC-1
```

### Check Process

```bash
ps aux | grep FC-1
```

## Best Practices

1. **Production**: Always run in quiet mode (no `-i` flag)
2. **Debugging**: Use `-i` flag for real-time console output
3. **Log Retrieval**: Use `scp` to download logs for offline analysis
4. **Monitoring**: Use `tail -f` for live monitoring during testing
5. **Storage**: Monitor `/var/log` disk usage on constrained devices

---

*Last Updated: 2025-12-30*
