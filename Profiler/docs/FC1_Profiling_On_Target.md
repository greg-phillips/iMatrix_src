# FC-1 Profiling On Target - Implementation Guide

**Date:** 2025-12-23
**Version:** 1.4
**Author:** Claude Code
**Branch:** feature/performance-tools-setup
**Status:** Fully Implemented and Tested

---

## 1. Overview

This document provides the complete implementation guide for the FC-1 profiling toolkit, which builds and deploys profiling tools for the FC-1 (Fleet-Connect-1) gateway application on embedded BusyBox Linux targets.

### 1.1 Objective

A complete, repeatable profiling toolkit that:
1. Uses configuration file for SSH connection settings
2. Cross-compiles tools for ARM using musl toolchain
3. Deploys binaries to embedded BusyBox system
4. Enables CPU, memory, IO, and network profiling of FC-1
5. Provides real-time monitoring dashboard

### 1.2 Target Platform

| Item | Value |
|------|-------|
| Hardware | NXP i.MX6 (ARM Cortex-A9) |
| RAM | 512MB |
| Flash | 512MB (MTD) |
| OS | BusyBox Linux (musl libc) |
| Kernel | 6.1.55-QConnect_v4.0.0 |
| Application | `/usr/qk/bin/FC-1` |
| SSH Port | 22222 |

### 1.3 Host Environment

| Item | Value |
|------|-------|
| Platform | WSL Ubuntu |
| Cross-Compiler | `/opt/qconnect_sdk_musl/bin/arm-linux-*` (musl-based) |
| Working Directory | `~/iMatrix/iMatrix_Client/Profiler` |

---

## 2. Configuration

### 2.1 Connection Settings

All scripts use a centralized configuration file:

**File:** `config/target_connection.conf`

```sh
TARGET_USER="root"
TARGET_HOST="192.168.7.1"
TARGET_PORT="22222"
TARGET_PASS="PasswordQConnect"
```

This file is git-ignored to protect credentials.

### 2.2 Testing Connection

```sh
./scripts/test_connection.sh
```

### 2.3 Command Line Override

All scripts accept an optional target argument that overrides the config:

```sh
./scripts/deploy_tools.sh root@192.168.1.100
```

---

## 3. Directory Structure

```
Profiler/
├── config/
│   ├── target_connection.conf       # SSH credentials (git-ignored)
│   └── target_connection.conf.template
├── scripts/
│   ├── common_ssh.sh                # Shared SSH functions
│   ├── test_connection.sh           # Connection testing
│   ├── monitor_fc1.sh               # Real-time monitoring
│   ├── target_discover.sh           # Capability discovery
│   ├── verify_fc1.sh                # Binary verification
│   ├── build_tools_host.sh          # Cross-compilation
│   ├── deploy_tools.sh              # Tool deployment
│   ├── profile_fc1.sh               # Profiling session
│   ├── grab_profiles.sh             # Bundle retrieval
│   ├── cleanup_samplers.sh          # Kill orphaned samplers
│   ├── setup_fc1_service.sh         # Service configuration
│   └── install_tools_target.sh      # Package manager install
├── docs/
│   └── FC1_Profiling_On_Target.md   # This document
├── artifacts/
│   ├── target_reports/              # Discovery reports
│   ├── profiles/                    # Downloaded bundles
│   └── logs/                        # Execution logs
├── build/
│   └── target_tools/
│       └── armhf/
│           └── bin/                 # Compiled ARM binaries
├── tools/
│   └── manifests/                   # Build manifests with SHA256
└── README.md                        # Quick start guide
```

---

## 4. Built Tools

### 4.1 Pre-Built Binaries

Located in `build/target_tools/armhf/bin/`:

| Tool | Size | Linking | Purpose |
|------|------|---------|---------|
| strace | 1014K | static | System call tracing |
| iperf3 | 124K | dynamic (musl) | Network performance |

### 4.2 Rebuilding

```sh
# Skip if already built (default)
./scripts/build_tools_host.sh

# Force rebuild
./scripts/build_tools_host.sh --force
```

The build script:
- Detects ARM binaries and skips if already built
- Uses `/opt/qconnect_sdk_musl/bin/arm-linux-*` toolchain
- Generates SHA256 manifest

---

## 5. Scripts Reference

### 5.1 Core Scripts

| Script | Purpose |
|--------|---------|
| `common_ssh.sh` | Shared SSH/SCP functions with sshpass support |
| `test_connection.sh` | Test SSH connectivity |
| `monitor_fc1.sh` | Real-time process monitoring dashboard |

### 5.2 Discovery Scripts

| Script | Purpose |
|--------|---------|
| `target_discover.sh` | Comprehensive target capability scan |
| `verify_fc1.sh` | Verify FC-1 binary and debug symbols |

### 5.3 Build/Deploy Scripts

| Script | Purpose |
|--------|---------|
| `build_tools_host.sh` | Cross-compile strace/iperf3 |
| `deploy_tools.sh` | Deploy binaries to target |
| `install_tools_target.sh` | Use package manager (if available) |

### 5.4 Profiling Scripts

| Script | Purpose |
|--------|---------|
| `profile_fc1.sh` | Run comprehensive profiling session |
| `grab_profiles.sh` | Download profile bundles |
| `cleanup_samplers.sh` | Kill orphaned background samplers |
| `setup_fc1_service.sh` | Configure FC-1 as runit service |

---

## 6. Workflow

### 6.1 Quick Start

```sh
cd ~/iMatrix/iMatrix_Client/Profiler

# 1. Configure (one-time)
nano config/target_connection.conf

# 2. Test connection
./scripts/test_connection.sh

# 3. Deploy tools
./scripts/deploy_tools.sh

# 4. Profile
./scripts/profile_fc1.sh --duration 60

# 5. Retrieve results
./scripts/grab_profiles.sh
```

### 6.2 Real-Time Monitoring

```sh
# Live dashboard (2-second refresh)
./scripts/monitor_fc1.sh

# Custom interval
./scripts/monitor_fc1.sh -i 5

# No screen clearing
./scripts/monitor_fc1.sh -n
```

**Dashboard output:**
```
================================================================
  FC-1 Monitor                              2025-12-22 23:00:04
================================================================

-- SERVICE --
  Status:  RUNNING
  PID:     10210
  runit:   run: FC-1: (pid 10210) 839s

-- PROCESS --
  Memory:  7 MB (RSS)
  Threads: 5
  FDs:     14 (sockets: 5)

-- SYSTEM --
  RAM:     43 / 496 MB (428 MB available)
  Load:    0.94 0.94 0.79
  Disk:    89.5M used, 396.6M free
================================================================
```

---

## 7. Profiling Session

### 7.1 Running a Profile

```sh
# Full 60-second profile
./scripts/profile_fc1.sh --duration 60

# Quick 10-second profile, no network capture
./scripts/profile_fc1.sh --duration 10 --no-tcpdump
```

### 7.2 Data Collected

| Category | Files |
|----------|-------|
| System baseline | cpuinfo, meminfo, df, mounts, ip_addr |
| Process state | proc_maps, proc_fd, proc_status |
| Tracing | strace_summary.txt, strace_trace.txt |
| Sampling | samples.txt (periodic snapshots) |
| I/O stats | diskstats_start/end, proc_io |
| Network | ip_link_stats, netstat/ss output |

### 7.3 Output Bundle

Profile data is packaged as:
```
/var/log/fc-1/profiles/profile_bundle_<timestamp>.tar.gz
```

### 7.4 Retrieving Results

```sh
./scripts/grab_profiles.sh
# Results saved to: artifacts/profiles/
```

---

## 8. Tool Deployment Locations

The deploy script tries these locations in order:

| Priority | Path | Notes |
|----------|------|-------|
| 1 | `/usr/qk/bin/` | Persistent, used by FC-1 |
| 2 | `/opt/fc-1-tools/bin/` | Standard optional tools location |
| 3 | `~/fc-1-tools/bin/` | Non-root fallback |

The profile script searches these paths when looking for strace/iperf3.

---

## 9. Technical Details

### 9.1 SSH Configuration

All scripts use `common_ssh.sh` which provides:
- Password authentication via sshpass
- Configurable port (default: 22222)
- Connection timeout handling
- Remote command execution

### 9.2 Cross-Compilation

```sh
CC=/opt/qconnect_sdk_musl/bin/arm-linux-gcc
LDFLAGS="-static"  # For strace
```

The musl toolchain produces binaries compatible with BusyBox.

### 9.3 POSIX and BusyBox Compliance

All scripts:
- Use `#!/bin/sh` (not bash)
- Use `set -eu` for safety
- Avoid bashisms
- Use `printf "%s\n" "text"` for strings starting with `-`
- Avoid `timeout` command (not in BusyBox) - use `cmd & sleep N; kill $!` pattern instead
- **Do NOT use `pkill -f`** on BusyBox - it doesn't work properly
- Use `ps | grep | awk | kill` pattern for process cleanup (see section 10.3)

---

## 10. Troubleshooting

### 10.1 Connection Issues

```sh
# Test with verbose output
./scripts/test_connection.sh

# Check sshpass installed
which sshpass || sudo apt-get install sshpass

# Manual test
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 "echo OK"
```

### 10.2 strace Permission Denied

The kernel's `ptrace_scope` setting restricts process tracing:

| Value | Meaning |
|-------|---------|
| 0 | Classic - any process can trace any other |
| 1 | Restricted - only child processes |
| 2 | Admin only - requires CAP_SYS_PTRACE |
| 3 | No ptrace allowed |

```sh
# Check current setting
cat /proc/sys/kernel/yama/ptrace_scope

# Set to 0 (required for strace to attach to FC-1)
echo 0 > /proc/sys/kernel/yama/ptrace_scope
```

**Note:** This resets on reboot. To persist, add to startup script or runit service.

### 10.3 Orphaned Sampling Scripts

If a profiling session is interrupted (Ctrl+C, disconnect), background samplers may keep running:

```sh
# Check for orphaned samplers on target
ps | grep 'sample.sh' | grep -v grep

# Clean up using the utility script (recommended)
./scripts/cleanup_samplers.sh

# Or manually on target (BusyBox-compatible method):
ps | grep 'sample.sh' | grep -v grep | awk '{print $1}' | while read pid; do kill -9 $pid; done
```

**IMPORTANT:** Do NOT use `pkill -f sample.sh` on BusyBox - it doesn't work properly.
BusyBox's `pkill -f` doesn't match full command lines, so processes won't be found.

The `profile_fc1.sh` script now:
- Cleans up orphaned samplers at startup
- Sets trap to cleanup on exit/interrupt
- Uses reliable PID-based killing (ps | grep | awk | kill pattern)

### 10.4 Build Failures

```sh
# Force clean rebuild
./scripts/build_tools_host.sh --force

# Check cross-compiler
/opt/qconnect_sdk_musl/bin/arm-linux-gcc --version
```

### 10.5 Disk Space

```sh
# Check target disk usage
ssh -p 22222 root@192.168.7.1 "df -h /usr/qk"

# Remove old profiles
ssh -p 22222 root@192.168.7.1 "rm -rf /var/log/fc-1/profiles/2024*"
```

---

## 11. Implementation History

### Version 1.4 (2025-12-23)
- **CRITICAL FIX**: Replaced `pkill -f` with reliable PID-based killing
- BusyBox's `pkill -f` doesn't work properly (doesn't match full command lines)
- Updated `cleanup_samplers.sh` to use `ps | grep | awk | kill` pattern
- Updated `profile_fc1.sh` cleanup functions with same fix
- Updated all documentation with correct BusyBox process killing instructions

### Version 1.3 (2025-12-22)
- Added `cleanup_samplers.sh` for orphaned sampler cleanup
- Fixed profiler to run for full requested duration
- Added automatic orphaned sampler cleanup at profile start
- Added exit trap for cleanup on interrupt (Ctrl+C)
- Replaced all `timeout` commands with BusyBox-compatible pattern
- Added progress display during long profiling sessions
- Expanded ptrace_scope documentation

### Version 1.2 (2025-12-22)
- Added `monitor_fc1.sh` real-time dashboard
- Fixed all scripts to use config file by default
- Added `--force` flag to build_tools_host.sh
- Fixed printf issues with leading dashes/equals
- Updated FC-1 path to `/usr/qk/bin/FC-1`
- Added `/usr/qk/bin/` to tool search paths
- Fixed local vs remote file write issues in profile_fc1.sh

### Version 1.1 (2025-12-21)
- Added `common_ssh.sh` with sshpass support
- Created `target_connection.conf` for centralized settings
- All scripts updated to use config file
- Cross-compiled strace 6.5 (static) and iperf3 3.15 (dynamic)

### Version 1.0 (2025-12-21)
- Initial implementation
- Directory structure created
- 8 core scripts migrated from Profiler-orig

---

## 12. Acceptance Criteria

| Criteria | Status |
|----------|--------|
| strace cross-compiled and runs on target | PASS |
| All scripts use config file | PASS |
| Real-time monitoring available | PASS |
| Profile bundle can be captured | PASS |
| Profile bundle can be retrieved | PASS |
| README.md provides working quickstart | PASS |

---

## Appendix A: Quick Reference

```sh
cd ~/iMatrix/iMatrix_Client/Profiler

# Connection
./scripts/test_connection.sh

# Monitoring
./scripts/monitor_fc1.sh

# Full profile workflow
./scripts/deploy_tools.sh
./scripts/profile_fc1.sh --duration 60
./scripts/grab_profiles.sh

# Force rebuild tools
./scripts/build_tools_host.sh --force
```

---

*Document Version: 1.4*
*Last Updated: 2025-12-23*
