# Expect Tool for FC-1 Remote CLI Access

**Date**: 2026-01-02
**Author**: Claude Code
**Status**: Production
**Last Updated**: 2026-01-02

---

## Overview

The expect tool provides remote CLI command execution on FC-1 gateways via the `fc1 cmd` command. It automates interaction with the microcom console interface, allowing commands to be sent and output captured from the host development machine.

### Use Cases

- Execute CLI commands remotely without manual SSH/microcom sessions
- Script automated testing and diagnostics
- Capture command output for logging and analysis
- Debug device behavior without physical console access

---

## Architecture

```
Host Machine                          FC-1 Gateway
┌─────────────┐                      ┌─────────────────────────────┐
│ fc1 cmd "?" │ ──── SSH ────────>   │ expect-wrapper              │
│             │                      │   └── expect                │
│             │                      │       └── microcom          │
│             │                      │           └── PTY console   │
│             │ <─── output ──────   │               └── FC-1 CLI  │
└─────────────┘                      └─────────────────────────────┘
```

### Components

| Component | Location (Gateway) | Purpose |
|-----------|-------------------|---------|
| expect | `/usr/qk/etc/sv/FC-1/expect/bin/expect` | TCL-based automation tool |
| expect-wrapper | `/usr/qk/etc/sv/FC-1/expect/bin/expect-wrapper` | Sets up library paths |
| libtcl8.6.so | `/usr/qk/etc/sv/FC-1/expect/lib/libtcl8.6.so` | TCL runtime library |
| fc1_cmd.exp | `/tmp/fc1_cmd.exp` | Expect script for microcom automation |

---

## Building Expect for ARM

The FC-1 gateway uses an ARM Cortex-A7 processor with musl libc. Expect and its TCL dependency must be cross-compiled.

### Prerequisites

- ARM toolchain: `/opt/qconnect_sdk_musl/`
- Python 3 (for patching expect's configure script)
- TCL 8.6.13 source
- Expect source

### Source Locations

```
external_tools/
├── tcl8.6.13/           # TCL source (download from sourceforge)
├── expect/              # Expect source (clone from github)
├── patch_expect_v5.py   # Cross-compilation patch script
└── build/
    └── expect-arm.tar.gz  # Built deployment package (776KB)
```

### Build Process

```bash
# From iMatrix_Client directory
./scripts/build_expect.sh
```

The build script performs:

1. **Configure TCL for ARM** with cross-compile hints:
   ```bash
   ./configure --host=arm-linux --build=x86_64-linux-gnu \
       --prefix=/usr/local --enable-shared --disable-threads \
       tcl_cv_strtod_buggy=ok tcl_cv_strtod_unbroken=ok \
       ac_cv_func_memcmp_working=yes
   ```

2. **Patch Expect's configure** - Expect has 9 explicit checks that block cross-compilation. The `patch_expect_v5.py` script replaces these with sensible defaults for Linux ARM (termios, POSIX signals, etc.)

3. **Configure and build Expect** linked against the cross-compiled TCL

4. **Create deployment package** with stripped binaries and minimal TCL runtime

### Package Contents

| File | Size (stripped) |
|------|-----------------|
| expect binary | 5.5 KB |
| libexpect5.45.3.so | 156 KB |
| libtcl8.6.so | 1.5 MB |
| TCL init scripts | ~66 KB |
| **Total tarball** | **776 KB** |

---

## Deployment

### Automatic Deployment

Expect tools are deployed automatically on first use of `fc1 cmd`:

```bash
scripts/fc1 cmd "help"
# If not installed, outputs:
# Expect not found on target. Deploying...
# Deploying expect tools to target (persistent location)...
```

### Manual Deployment

```bash
# Copy package to gateway
scp -P 22222 external_tools/build/expect-arm.tar.gz root@192.168.7.1:/tmp/

# SSH to gateway and extract
ssh -p 22222 root@192.168.7.1
mkdir -p /usr/qk/etc/sv/FC-1/expect
cd /usr/qk/etc/sv/FC-1/expect
tar xzf /tmp/expect-arm.tar.gz
rm /tmp/expect-arm.tar.gz
```

### Deployment Location

The tools are deployed to `/usr/qk/etc/sv/FC-1/expect/` which is **persistent storage** that survives reboots. Earlier versions used `/usr/local` which is volatile (tmpfs) on the embedded system.

---

## Usage

### Basic Command Execution

```bash
# Execute a CLI command and capture output
scripts/fc1 cmd "<command>"

# Examples:
scripts/fc1 cmd "v"              # Version info
scripts/fc1 cmd "?"              # Full CLI help
scripts/fc1 cmd "ms"             # Memory statistics
scripts/fc1 cmd "cell status"    # Cellular status
scripts/fc1 cmd "imx stats"      # iMatrix statistics
scripts/fc1 cmd "debug ?"        # Debug flags (special chars work)
scripts/fc1 cmd "net"            # Network status
```

### Specifying Target Host

```bash
# Default target: 192.168.7.1
scripts/fc1 cmd "v"

# Specify different target
scripts/fc1 -d 10.0.0.50 cmd "v"
```

### Output Format

```
Executing: v
---
spawn microcom /usr/qk/etc/sv/FC-1/console

>v
Device Name: FC-1, Product Name: Fleet Connect, Product ID: 0x1654ec75
Serial Number: 000000000000000000000000 - iMatrix assigned: 0131557250
Running iMatrix version:1.032.001, Running Product version:1.006.052

>
```

---

## Troubleshooting

### Issue: "Expect not found on target. Deploying..." followed by tar error

**Symptom:**
```
tar (child): /tmp/expect-arm.tar.gz: Cannot open: No such file or directory
```

**Cause:** SCP failed silently (file not transferred despite exit code 0).

**Solution:** Manually deploy:
```bash
scp -P 22222 external_tools/build/expect-arm.tar.gz root@192.168.7.1:/tmp/
ssh -p 22222 root@192.168.7.1 "mkdir -p /usr/qk/etc/sv/FC-1/expect && \
    cd /usr/qk/etc/sv/FC-1/expect && tar xzf /tmp/expect-arm.tar.gz"
```

### Issue: "microcom: can't create '/var/lock/LCK..console': File exists"

**Cause:** A previous microcom session didn't exit cleanly, leaving a stale lock file.

**Solution:**
```bash
# Check for stale microcom process
ssh -p 22222 root@192.168.7.1 "cat /var/lock/LCK..console; ps aux | grep microcom"

# Kill stale process (replace PID with actual)
ssh -p 22222 root@192.168.7.1 "kill <PID>"

# Or remove lock file if no process exists
ssh -p 22222 root@192.168.7.1 "rm /var/lock/LCK..console"
```

### Issue: Expect tools lost after reboot

**Cause:** Tools were deployed to volatile storage (`/usr/local` or `/tmp`).

**Solution:** Redeploy - the current script uses persistent storage at `/usr/qk/etc/sv/FC-1/expect/`.

### Issue: Special characters (?, *, etc.) not working in commands

**Cause:** Shell glob expansion consuming special characters.

**Solution:** Always quote the command argument:
```bash
scripts/fc1 cmd "debug ?"    # Correct - quoted
scripts/fc1 cmd debug ?      # Wrong - ? will be expanded
```

### Issue: Command timeout

**Cause:** Command takes longer than 10-second default timeout.

**Solution:** Modify `fc1_cmd.exp` to increase timeout value, or ensure the command produces output promptly.

---

## Files Reference

### Host Machine (iMatrix_Client/)

| File | Purpose |
|------|---------|
| `scripts/fc1` | Main control script with `cmd` command |
| `scripts/fc1_cmd.exp` | Expect script for microcom automation |
| `scripts/build_expect.sh` | Cross-compilation build script |
| `external_tools/patch_expect_v5.py` | Patches expect configure for cross-compile |
| `external_tools/tcl8.6.13/` | TCL source |
| `external_tools/expect/` | Expect source |
| `external_tools/build/expect-arm.tar.gz` | Deployment package |

### Gateway (/usr/qk/etc/sv/FC-1/expect/)

| File | Purpose |
|------|---------|
| `bin/expect` | Expect binary |
| `bin/expect-wrapper` | Library path setup wrapper |
| `bin/tclsh8.6` | TCL shell (optional) |
| `lib/libtcl8.6.so` | TCL shared library |
| `lib/tcl8.6/` | TCL initialization scripts |

---

## Related Documentation

- [Run Command on FC-1 Plan](gen/run_command_on_FC-1_plan.md) - Original implementation plan
- [Fix Expect Persistent Deployment](gen/fix_expect_persistent_deployment_plan.md) - Persistence and special char fixes
- [Testing FC-1 Application](testing_fc_1_application.md) - General testing procedures

---

## Version History

| Date | Change |
|------|--------|
| 2025-12-31 | Initial implementation - cross-compiled expect for ARM |
| 2026-01-02 | Fixed persistent storage location (moved from /usr/local to /usr/qk/) |
| 2026-01-02 | Fixed special character handling in commands |
