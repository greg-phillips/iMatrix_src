# FC-1 Profiling Toolkit

**Date:** 2025-12-21
**Version:** 1.0

Comprehensive profiling toolkit for the FC-1 gateway application on embedded Linux targets.

## Quick Start

```sh
cd ~/iMatrix/iMatrix_Client/Profiler
TARGET=user@192.168.x.x
./scripts/target_discover.sh "$TARGET"
./scripts/verify_fc1.sh "$TARGET"
./scripts/install_tools_target.sh "$TARGET" || true
# If install_tools_target.sh exits 2, do:
./scripts/build_tools_host.sh "$TARGET"
./scripts/deploy_tools.sh "$TARGET"
./scripts/setup_fc1_service.sh "$TARGET"
./scripts/profile_fc1.sh "$TARGET" --duration 60
./scripts/grab_profiles.sh "$TARGET"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `target_discover.sh` | Discover target system capabilities |
| `verify_fc1.sh` | Verify FC-1 binary exists and is executable |
| `install_tools_target.sh` | Install tools via package manager |
| `build_tools_host.sh` | Cross-compile tools on host |
| `deploy_tools.sh` | Deploy built tools to target |
| `setup_fc1_service.sh` | Configure FC-1 as a service |
| `profile_fc1.sh` | Run profiling session |
| `grab_profiles.sh` | Retrieve profile bundles |

## Requirements

### Target
- FC-1 binary at `/home/FC-1`
- SSH server with key-based auth
- 10-50MB free storage

### Host
- SSH client
- Cross-compiler (for host builds)
- wget or curl

## Collected Data

- **System:** CPU, memory, storage info
- **Process:** Memory maps, file descriptors, I/O stats
- **Tracing:** strace syscall analysis
- **Performance:** perf counters (if available) or ftrace
- **Network:** Connection stats, packet capture

## Directory Structure

```
Profiler/
├── scripts/           # Profiling scripts
├── docs/              # Documentation
├── artifacts/
│   ├── target_reports/  # Discovery reports
│   ├── profiles/        # Downloaded bundles
│   └── logs/            # Execution logs
├── build/
│   └── target_tools/    # Built binaries
└── tools/
    └── manifests/       # Build manifests
```

## Documentation

See [docs/FC1_Profiling_On_Target.md](docs/FC1_Profiling_On_Target.md) for complete documentation.

## License

Part of the iMatrix IoT Platform.
