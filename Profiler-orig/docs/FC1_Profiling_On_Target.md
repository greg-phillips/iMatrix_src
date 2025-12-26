# FC-1 Profiling On Target - Complete Guide

**Date:** 2025-12-21
**Version:** 1.0
**Author:** Claude Code

## Overview

This document provides comprehensive instructions for profiling the FC-1 (Fleet Connect 1) gateway application on embedded Linux targets. The profiling toolkit supports CPU analysis, memory monitoring, I/O tracking, and network capture.

## Target Platform

- **Hardware:** NXP i.MX6 (ARM Cortex-A9)
- **OS:** BusyBox Linux
- **RAM:** 512MB
- **Flash:** 512MB
- **Application:** `/home/FC-1`

## Prerequisites

### Host Machine Requirements

1. **SSH Access:** Key-based SSH authentication to target
2. **Build Tools:** (only if building tools on host)
   - Cross-compiler for ARM (e.g., `arm-linux-gnueabihf-gcc`)
   - Make, wget/curl
3. **Disk Space:** ~100MB for tool builds and profiles

### Target Requirements

1. FC-1 binary at `/home/FC-1` (must not be moved)
2. SSH server running
3. Sufficient storage for profile data (~10-50MB per session)

## Directory Structure

```
Profiler/
├── scripts/                    # All profiling scripts
│   ├── target_discover.sh      # Discover target capabilities
│   ├── verify_fc1.sh           # Verify FC-1 binary
│   ├── install_tools_target.sh # Install tools via package manager
│   ├── build_tools_host.sh     # Cross-compile tools on host
│   ├── deploy_tools.sh         # Deploy built tools to target
│   ├── setup_fc1_service.sh    # Configure FC-1 as service
│   ├── profile_fc1.sh          # Run profiling session
│   └── grab_profiles.sh        # Retrieve profiles from target
├── docs/                       # Documentation
├── artifacts/                  # Output files
│   ├── target_reports/         # Target discovery reports
│   ├── profiles/               # Downloaded profile bundles
│   └── logs/                   # Script execution logs
├── build/                      # Build outputs
│   ├── src/                    # Downloaded source code
│   └── target_tools/           # Built binaries by architecture
└── tools/
    ├── bin/                    # Optional host helper binaries
    └── manifests/              # Build manifests
```

## Quick Start

```sh
cd ~/iMatrix/iMatrix_Client/Profiler
TARGET=root@192.168.1.100

# 1. Discover target capabilities
./scripts/target_discover.sh "$TARGET"

# 2. Verify FC-1 exists
./scripts/verify_fc1.sh "$TARGET"

# 3. Install tools (try package manager first)
./scripts/install_tools_target.sh "$TARGET" || true

# 4. If step 3 exited with code 2, build on host
./scripts/build_tools_host.sh "$TARGET"
./scripts/deploy_tools.sh "$TARGET"

# 5. Setup FC-1 as a service
./scripts/setup_fc1_service.sh "$TARGET"

# 6. Run profiling session
./scripts/profile_fc1.sh "$TARGET" --duration 60

# 7. Retrieve profile bundle
./scripts/grab_profiles.sh "$TARGET"
```

## Detailed Script Reference

### 1. target_discover.sh

Connects to target and collects comprehensive system information.

**Usage:**
```sh
./scripts/target_discover.sh user@target
```

**Collects:**
- System info (uname, os-release, BusyBox version)
- Architecture and libc type (glibc vs musl)
- Kernel capabilities (perf_event, ftrace support)
- Available profiling tools
- Package manager detection
- Init system detection
- CPU, memory, storage, and network info

**Output:**
```
artifacts/target_reports/target_report_<host>_<timestamp>.txt
```

### 2. verify_fc1.sh

Verifies the FC-1 binary exists and is properly configured.

**Usage:**
```sh
./scripts/verify_fc1.sh user@target
```

**Checks:**
- File existence at `/home/FC-1`
- Executable permissions
- ELF format and architecture
- Debug symbols presence
- Running process status

**Output:**
```
artifacts/target_reports/fc1_verify_<host>_<timestamp>.txt
```

**Exit Codes:**
- 0: FC-1 verified successfully
- 1: FC-1 not found or not executable

### 3. install_tools_target.sh

Attempts to install profiling tools using the target's package manager.

**Usage:**
```sh
./scripts/install_tools_target.sh user@target
```

**Supported Package Managers:**
- opkg (OpenWrt)
- apk (Alpine)
- apt (Debian/Ubuntu)
- yum/dnf (RHEL/Fedora)

**Tools Installed:**
| Priority | Tools |
|----------|-------|
| Critical | strace |
| Recommended | tcpdump, ethtool, iperf3, lsof |
| Optional | procps, sysstat, perf, htop, iotop, gdb |

**Exit Codes:**
- 0: Critical tools installed
- 1: SSH connection failed
- 2: No package manager or critical tools missing (use host build)

### 4. build_tools_host.sh

Cross-compiles profiling tools on the host machine.

**Usage:**
```sh
./scripts/build_tools_host.sh user@target
```

**Built Tools:**
- strace (critical) - System call tracer
- iperf3 (optional) - Network performance testing

**Requirements:**
- Cross-compiler for target architecture
- wget or curl for downloading sources
- ~50MB disk space

**Cross-Compiler Setup (Ubuntu/Debian):**
```sh
# For ARM hard-float
sudo apt-get install gcc-arm-linux-gnueabihf

# For ARM soft-float
sudo apt-get install gcc-arm-linux-gnueabi

# For ARM64
sudo apt-get install gcc-aarch64-linux-gnu
```

**Output:**
```
build/target_tools/<arch>/bin/strace
build/target_tools/<arch>/bin/iperf3
tools/manifests/target_tools_<arch>_<timestamp>.txt
```

### 5. deploy_tools.sh

Deploys built tools to the target system.

**Usage:**
```sh
./scripts/deploy_tools.sh user@target
```

**Deployment Locations:**
1. Preferred: `/opt/fc-1-tools/bin` (if root writable)
2. Fallback: `/home/<user>/fc-1-tools/bin`

**PATH Setup:**
After deployment, add tools to PATH:
```sh
export PATH=/opt/fc-1-tools/bin:$PATH
# or
. /opt/fc-1-tools/setup_path.sh
```

**Output:**
```
artifacts/logs/deploy_tools_<host>_<timestamp>.txt
```

### 6. setup_fc1_service.sh

Configures FC-1 to run as a managed service.

**Usage:**
```sh
./scripts/setup_fc1_service.sh user@target
```

**Supported Init Systems:**
| System | Service Location | Commands |
|--------|-----------------|----------|
| runit | `/etc/sv/FC-1/` | `sv start/stop/status FC-1` |
| systemd | `/etc/systemd/system/fc-1.service` | `systemctl start/stop/status fc-1` |
| sysvinit | `/etc/init.d/fc-1` | `/etc/init.d/fc-1 start/stop/status` |
| none (userland) | `~/fc1_run.sh` | `~/fc1_run.sh`, `~/fc1_stop.sh` |

**Created Directories:**
- Logs: `/var/log/fc-1/` or `~/fc-1-logs/`
- Profiles: `/var/log/fc-1/profiles/` or `~/fc-1-profiles/`
- Runtime: `/var/run/fc-1/` or `~/fc-1-run/`

### 7. profile_fc1.sh

Runs a comprehensive profiling session.

**Usage:**
```sh
./scripts/profile_fc1.sh user@target [--duration 60] [--no-tcpdump]
```

**Options:**
- `--duration N`: Profile duration in seconds (default: 60)
- `--no-tcpdump`: Skip network packet capture

**Data Collected:**

| Category | Files |
|----------|-------|
| System Info | uname.txt, cpuinfo.txt, mounts.txt |
| Memory | meminfo_start.txt, meminfo_end.txt |
| Process | proc_status_*.txt, proc_stat_*.txt, proc_io_*.txt |
| I/O | diskstats_start.txt, diskstats_end.txt |
| Network | ip_addr.txt, ip_route.txt, capture.pcap |
| Sampling | samples.txt (periodic snapshots) |
| Tracing | strace_summary.txt, strace_trace.txt |
| Performance | perf_stat.txt, perf_report.txt (if available) |
| Fallback | ftrace.txt (if perf unavailable) |

**Output:**
```
# On target
/var/log/fc-1/profiles/<timestamp>/profile_bundle_<timestamp>.tar.gz

# Local log
artifacts/logs/profile_<host>_<timestamp>.txt
```

### 8. grab_profiles.sh

Downloads profile bundles from target.

**Usage:**
```sh
./scripts/grab_profiles.sh user@target [--all]
```

**Options:**
- `--all`: Download all bundles (default: newest only)

**Output:**
```
artifacts/profiles/<host>/<filename>.tar.gz
```

## Profiling Techniques

### System Call Analysis (strace)

The toolkit uses strace for system call tracing:

```
strace_summary.txt  - Aggregate statistics (call counts, times)
strace_trace.txt    - Detailed trace with timestamps
```

**Interpreting strace_summary.txt:**
```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 45.23    0.123456          12     10234           read
 32.11    0.087654          45      1947           write
 12.56    0.034567           8      4321       123 select
```

- High `% time` in a syscall indicates potential bottleneck
- High `usecs/call` suggests slow operations
- `errors` column shows failed calls

### Performance Counters (perf)

When perf is available:

```
perf_stat.txt   - Hardware counter statistics
perf_report.txt - CPU sampling profile
```

**perf_stat output example:**
```
 Performance counter stats for process '1234':
       1,234,567      cpu-cycles
         567,890      instructions              #    0.46  insn per cycle
          12,345      cache-misses              #    1.23% of all cache refs
```

### Function Tracing (ftrace)

When perf is unavailable, ftrace provides function-level tracing:

```
ftrace.txt - Kernel function call graph
```

### Periodic Sampling

The `samples.txt` file contains snapshots taken every 5 seconds:
- Process memory (VmSize, VmRSS)
- I/O statistics
- Disk activity
- CPU usage

## Troubleshooting

### SSH Connection Issues

```sh
# Test connection
ssh -o BatchMode=yes user@target echo "OK"

# Setup key-based auth
ssh-copy-id user@target
```

### strace Attach Permission Denied

If strace cannot attach to FC-1:
1. Run as root
2. Check `/proc/sys/kernel/yama/ptrace_scope`:
   ```sh
   echo 0 > /proc/sys/kernel/yama/ptrace_scope
   ```

### perf Not Working

perf requires kernel support:
```sh
# Check kernel config
zcat /proc/config.gz | grep PERF_EVENT
```

If `CONFIG_PERF_EVENTS=y` is missing, perf won't work. Use ftrace instead.

### Out of Disk Space

Profile sessions generate 10-50MB of data. Clear old profiles:
```sh
ssh user@target 'rm -rf /var/log/fc-1/profiles/2024*'
```

### FC-1 Not Running

Start FC-1 before profiling:
```sh
# If using runit
sv start FC-1

# If using sysvinit
/etc/init.d/fc-1 start

# If using userland wrapper
~/fc1_run.sh
```

## Best Practices

1. **Baseline First:** Run target_discover.sh to understand target capabilities
2. **Short Sessions:** Start with 30-60 second profiles
3. **Disk Space:** Monitor available space before profiling
4. **Network:** Use --no-tcpdump if not analyzing network issues
5. **Multiple Runs:** Take several profiles under different conditions
6. **Archive Results:** Keep profiles organized by date and condition

## Profile Analysis

After downloading a profile bundle:

```sh
cd artifacts/profiles/<host>
tar xzf profile_bundle_<timestamp>.tar.gz
cd <timestamp>

# View strace summary
cat strace_summary.txt

# Check memory growth
diff meminfo_start.txt meminfo_end.txt

# Analyze periodic samples
grep "VmRSS" samples.txt

# View network capture (requires Wireshark)
wireshark capture.pcap
```

## Security Considerations

1. SSH keys should be properly secured
2. Profile data may contain sensitive information
3. Deployed tools should be removed after analysis
4. Limit profiling duration to minimize storage impact

## Related Documentation

- [Fleet-Connect-1 Architecture](../../docs/Fleet-Connect-1_architecture.md)
- [iMatrix Memory Management](../../iMatrix/cs_ctrl/README.md)
- [Network Manager Documentation](../../iMatrix/networking/README.md)
