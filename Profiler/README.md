# FC-1 Profiling Toolkit

**Date:** 2025-12-23
**Version:** 1.4

Comprehensive profiling toolkit for the FC-1 gateway application on embedded BusyBox Linux targets.

**BusyBox Compatible:** All scripts avoid bash-specific features and commands not available in BusyBox (like `timeout`).

## Quick Start

```sh
cd ~/iMatrix/iMatrix_Client/Profiler

# 1. Configure target connection (edit TARGET_HOST, TARGET_PASS)
nano config/target_connection.conf

# 2. Test connection
./scripts/test_connection.sh

# 3. Deploy profiling tools (strace, iperf3)
./scripts/deploy_tools.sh

# 4. Run profiling session (60 seconds)
./scripts/profile_fc1.sh --duration 60

# 5. Retrieve profile bundle
./scripts/grab_profiles.sh
```

All scripts read connection settings from `config/target_connection.conf`.

## Real-Time Monitoring

Monitor FC-1 process status with a live dashboard:

```sh
# Start monitoring (updates every 2 seconds)
./scripts/monitor_fc1.sh

# Custom update interval (5 seconds)
./scripts/monitor_fc1.sh -i 5

# No screen clearing (append mode)
./scripts/monitor_fc1.sh -n

# Press Ctrl+C to stop
```

**Dashboard shows:**
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

## Pre-Built ARM Binaries

Cross-compiled tools are available in `build/target_tools/armhf/bin/`:

| Tool | Size | Linking | Purpose |
|------|------|---------|---------|
| strace | 1014K | static | System call tracing |
| iperf3 | 124K | dynamic (musl) | Network performance testing |

### Rebuilding Tools

```sh
# Skip rebuild if binaries exist
./scripts/build_tools_host.sh

# Force rebuild
./scripts/build_tools_host.sh --force
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `test_connection.sh` | Test SSH connectivity to target |
| `monitor_fc1.sh` | Real-time FC-1 process monitoring dashboard |
| `target_discover.sh` | Discover target system capabilities |
| `verify_fc1.sh` | Verify FC-1 binary exists and is executable |
| `build_tools_host.sh` | Cross-compile tools on WSL host |
| `deploy_tools.sh` | Deploy built tools to target via SCP |
| `profile_fc1.sh` | Run comprehensive profiling session |
| `grab_profiles.sh` | Retrieve profile bundles from target |
| `cleanup_samplers.sh` | Kill orphaned sampling scripts on target |
| `setup_fc1_service.sh` | Configure FC-1 as a managed service |
| `install_tools_target.sh` | Install tools via target's package manager |

## Requirements

### Target (Embedded)
- FC-1 binary at `/usr/qk/bin/FC-1`
- SSH server running (port 22222)
- 10-50MB free storage for profiles
- **ptrace enabled** for strace: `echo 0 > /proc/sys/kernel/yama/ptrace_scope`

### Host (WSL Ubuntu)
- Cross-compiler: `/opt/qconnect_sdk_musl/bin/arm-linux-*`
- SSH client
- wget/curl for downloading sources
- **sshpass**: `sudo apt-get install sshpass`

## Connection Setup

### Configuration File (Recommended)

Edit `config/target_connection.conf`:

```sh
TARGET_USER="root"
TARGET_HOST="192.168.7.1"
TARGET_PORT="22222"
TARGET_PASS="PasswordQConnect"
```

Test the connection:
```sh
./scripts/test_connection.sh
```

### Command Line Override

All scripts accept an optional target argument:
```sh
./scripts/deploy_tools.sh root@192.168.1.100
./scripts/profile_fc1.sh root@192.168.1.100 --duration 30
```

## Profiling Session

### Running a Profile

```sh
# Full 60-second profile
./scripts/profile_fc1.sh --duration 60

# Quick 10-second profile, no network capture
./scripts/profile_fc1.sh --duration 10 --no-tcpdump
```

### Data Collected

- **System:** CPU, memory, storage, network info
- **Process:** Memory maps, file descriptors, I/O stats
- **Tracing:** strace syscall summary and detailed trace
- **Sampling:** Periodic snapshots during profiling
- **Network:** Connection stats, optional packet capture

### Retrieving Results

```sh
./scripts/grab_profiles.sh
# Results saved to: artifacts/profiles/
```

## Directory Structure

```
Profiler/
├── config/
│   └── target_connection.conf   # SSH credentials (git-ignored)
├── scripts/                     # All profiling scripts
├── docs/                        # Documentation
├── artifacts/
│   ├── target_reports/          # Discovery reports
│   ├── profiles/                # Downloaded bundles
│   └── logs/                    # Execution logs
├── build/
│   └── target_tools/
│       └── armhf/
│           └── bin/             # Compiled ARM binaries
└── tools/
    └── manifests/               # Build manifests with SHA256
```

## Workflow Diagram

```
Host (WSL)                          Target (Embedded)
==========                          =================

test_connection.sh  ──SSH──>        Verify connectivity

build_tools_host.sh
  └── Cross-compile strace/iperf3   (skips if already built)

deploy_tools.sh     ──SCP──>        /usr/qk/bin/ or /opt/fc-1-tools/

monitor_fc1.sh      ──SSH──>        Real-time status display

profile_fc1.sh      ──SSH──>        Run profiling session
                                    └── Creates bundle.tar.gz

grab_profiles.sh    <──SCP──        Download bundle
  └── artifacts/profiles/
```

## Troubleshooting

### SSH Connection Failed
```sh
# Test with verbose output
./scripts/test_connection.sh

# Check sshpass is installed
which sshpass || sudo apt-get install sshpass
```

### strace Permission Denied
The kernel's ptrace_scope setting restricts process tracing. Set to 0 for strace to work:
```sh
# On target, as root:
echo 0 > /proc/sys/kernel/yama/ptrace_scope

# To make permanent, add to startup script
```
**Note:** This resets on reboot. Add to `/etc/init.d/` or runit service for persistence.

### Orphaned Sampling Scripts
If profile sessions are interrupted, background samplers may keep running:
```sh
# Check for orphaned samplers (recommended)
./scripts/cleanup_samplers.sh

# Or manually on target (BusyBox-compatible method):
ps | grep 'sample.sh' | grep -v grep | awk '{print $1}' | while read pid; do kill -9 $pid; done
```

**Note:** Do NOT use `pkill -f sample.sh` on BusyBox - it doesn't work properly.

The profile script now automatically cleans up orphaned samplers at startup.

### Tools Already Deployed
Tools are deployed to `/usr/qk/bin/` (persistent) or `/opt/fc-1-tools/` (fallback).
The deploy script detects and uses existing locations.

### Disk Space Issues
```sh
# On target, remove old profiles:
ssh -p 22222 root@192.168.7.1 'rm -rf /var/log/fc-1/profiles/2024*'
```

## Cross-Compiler

The toolkit uses the musl-based ARM cross-compiler:
```
/opt/qconnect_sdk_musl/bin/arm-linux-gcc
```

This produces smaller binaries with better BusyBox compatibility than glibc.

## Documentation

See [docs/FC1_Profiling_On_Target.md](docs/FC1_Profiling_On_Target.md) for complete documentation.

## License

Part of the iMatrix IoT Platform.
