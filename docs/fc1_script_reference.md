# FC-1 Remote Control Script Reference

**Date**: 2026-01-02
**Document Version**: 1.0
**Author**: Development Team
**Status**: Production

---

## Overview

The `fc1` script (`scripts/fc1`) is a comprehensive remote control utility for managing the FC-1 (Fleet Connect) application on QConnect gateway devices. It provides a unified interface for:

- Service management (start, stop, restart, enable, disable)
- Binary deployment
- Log viewing
- Remote CLI command execution
- SSH access
- PPP link status monitoring

The script runs on the development host machine and communicates with the gateway over SSH.

---

## Prerequisites

### Host Machine Requirements

| Requirement | Details |
|-------------|---------|
| Operating System | Linux (Ubuntu/WSL2 recommended) |
| sshpass | Required for non-interactive SSH |
| Network | Connectivity to gateway (USB, WiFi, or Ethernet) |

### Install sshpass

```bash
# Ubuntu/Debian
sudo apt-get install sshpass

# macOS (via Homebrew)
brew install hudochenkov/sshpass/sshpass

# Verify installation
command -v sshpass && echo "sshpass installed"
```

### Gateway Connection

| Parameter | Default Value |
|-----------|---------------|
| Host | `192.168.7.1` |
| Port | `22222` |
| User | `root` |
| Password | `PasswordQConnect` |

---

## Usage Syntax

```bash
./scripts/fc1 [-d <destination>] <command> [options]
```

### Global Options

| Option | Description |
|--------|-------------|
| `-d <host>` | Override target host (default: 192.168.7.1) |

---

## Command Reference

### Service Control Commands

| Command | Description |
|---------|-------------|
| `start` | Start FC-1 runit service |
| `stop` | Stop FC-1 runit service |
| `restart` | Restart FC-1 service |
| `status` | Show service status (default if no command given) |
| `enable` | Enable auto-start and start service |
| `disable` | Disable auto-start (prompts for confirmation) |
| `disable -y` | Disable auto-start without confirmation |

**Examples:**
```bash
./fc1 start              # Start FC-1
./fc1 stop               # Stop FC-1
./fc1 restart            # Restart FC-1
./fc1 status             # Check service status
./fc1 enable             # Enable and start
./fc1 disable            # Disable (with prompt)
./fc1 disable -y         # Disable (no prompt)
```

### Deployment Commands

| Command | Description |
|---------|-------------|
| `push` | Deploy FC-1 binary to gateway (service stays stopped) |
| `push -run` | Deploy binary and start service |
| `config <file>` | Deploy config file to gateway (removes old .bin files first) |
| `deploy` | Deploy the service helper script to gateway |

**Examples:**
```bash
# Build and deploy workflow
cd Fleet-Connect-1/build && make -j4
cd ../../scripts
./fc1 push               # Deploy only
./fc1 push -run          # Deploy and start

# Deploy configuration file
./fc1 config /path/to/device_config.bin
./fc1 config configs/my_config.json
```

**Binary Paths:**
| Location | Path |
|----------|------|
| Local (host) | `Fleet-Connect-1/build/FC-1` |
| Remote (gateway) | `/usr/qk/bin/FC-1` |

**Config Deployment:**
- Removes all existing `.bin` files from `/usr/qk/etc/sv/FC-1/` before copying
- Copies the specified config file to `/usr/qk/etc/sv/FC-1/`
- Preserves the original filename

### CLI Command Execution

| Command | Description |
|---------|-------------|
| `cmd "<command>"` | Execute CLI command via expect/microcom |

The `cmd` command uses cross-compiled expect tools to automate microcom interaction with the FC-1 console. This allows remote execution of any FC-1 CLI command.

**Examples:**
```bash
./fc1 cmd "help"              # Show CLI help
./fc1 cmd "?"                 # Full command list
./fc1 cmd "v"                 # Version info
./fc1 cmd "cell status"       # Cellular status
./fc1 cmd "cell scan"         # Trigger carrier scan
./fc1 cmd "cell operators"    # List operators
./fc1 cmd "ppp"               # PPP status
./fc1 cmd "net"               # Network status
./fc1 cmd "imx stats"         # iMatrix statistics
./fc1 cmd "ms"                # Memory statistics
./fc1 cmd "debug ?"           # Debug flags
./fc1 cmd "log"               # Logging status
./fc1 cmd "config"            # Show configuration
```

**Notes:**
- Always quote the command argument
- Special characters like `?` are properly handled
- Expect tools are automatically deployed on first use
- Expect tools persist at `/usr/qk/etc/sv/FC-1/expect/`

### Log and Status Commands

| Command | Description |
|---------|-------------|
| `log` | Show recent FC-1 logs |
| `ppp` | Show PPP link status (interface, service, log) |

**Examples:**
```bash
./fc1 log                # View recent logs
./fc1 ppp                # PPP connection status
```

### SSH and Utility Commands

| Command | Description |
|---------|-------------|
| `ssh` | Open interactive SSH session to gateway |
| `clear-key` | Clear SSH host key (for device changes) |
| `run [opts]` | Run FC-1 in foreground on gateway |
| `help` | Show help message |

**Examples:**
```bash
./fc1 ssh                     # Interactive SSH session
./fc1 -d 10.0.0.50 ssh        # SSH to specific host
./fc1 clear-key               # Clear cached host key
./fc1 run -S                  # Run FC-1 with config summary
./fc1 help                    # Show all commands
```

---

## Architecture

### Script Components

```
scripts/
├── fc1                  # Main control script
├── fc1_service.sh       # Service helper (deployed to gateway)
└── fc1_cmd.exp          # Expect script for CLI automation
```

### Communication Flow

```
Host Machine                              Gateway (192.168.7.1:22222)
┌────────────────┐                       ┌─────────────────────────────┐
│  ./fc1 <cmd>   │                       │                             │
│       │        │                       │  /tmp/fc1_service.sh        │
│       ▼        │                       │  (service control)          │
│  SSH/SCP       │ ──────────────────>   │                             │
│                │                       │  /usr/qk/bin/FC-1           │
│                │                       │  (application binary)       │
│                │                       │                             │
│                │                       │  /usr/qk/etc/sv/FC-1/       │
│                │                       │  ├── console (PTY symlink)  │
│                │                       │  └── expect/ (CLI tools)    │
└────────────────┘                       └─────────────────────────────┘
```

### Internal Functions

| Function | Purpose |
|----------|---------|
| `check_sshpass()` | Verify sshpass is installed |
| `check_target()` | Verify gateway is reachable |
| `clear_host_key()` | Remove stale SSH host key |
| `deploy_script()` | Deploy fc1_service.sh to gateway |
| `push_binary()` | Copy FC-1 binary to gateway |
| `run_remote()` | Execute command via SSH (uses eval) |
| `run_ssh()` | Execute command via SSH (preserves special chars) |
| `run_service_cmd()` | Execute service helper command |
| `deploy_expect()` | Deploy expect tools to gateway |
| `check_expect_installed()` | Check if expect is on gateway |
| `run_cli_cmd()` | Execute CLI command via expect |

---

## Configuration

### Default Settings

```bash
TARGET_HOST="192.168.7.1"
TARGET_PORT="22222"
TARGET_USER="root"
TARGET_PASS="PasswordQConnect"
```

### Path Configurations

| Variable | Default Value |
|----------|---------------|
| `LOCAL_BINARY` | `Fleet-Connect-1/build/FC-1` |
| `REMOTE_BINARY` | `/usr/qk/bin/FC-1` |
| `REMOTE_EXPECT_DIR` | `/usr/qk/etc/sv/FC-1/expect` |
| `REMOTE_SCRIPT` | `/tmp/fc1_service.sh` |

### Using Different Targets

```bash
# Single command to different host
./fc1 -d 10.0.0.50 status

# Multiple commands to different host
./fc1 -d 192.168.1.100 push -run
./fc1 -d 192.168.1.100 cmd "v"
```

---

## Workflows

### Development Workflow

```bash
# 1. Make code changes in Fleet-Connect-1/

# 2. Build
cd Fleet-Connect-1/build
make -j4

# 3. Deploy and test
cd ../../scripts
./fc1 push -run

# 4. Monitor and verify
./fc1 status
./fc1 cmd "v"           # Check version
./fc1 log               # View logs
```

### Debugging Workflow

```bash
# Check service status
./fc1 status

# Run in foreground with debug output
./fc1 stop
./fc1 run

# Or enable debug via CLI
./fc1 cmd "debug on"

# Check specific subsystems
./fc1 cmd "cell status"
./fc1 cmd "ppp"
./fc1 cmd "net"
./fc1 cmd "imx stats"

# View logs
./fc1 log
```

### Remote CLI Session

```bash
# Execute individual commands
./fc1 cmd "help"
./fc1 cmd "cell status"
./fc1 cmd "cell scan"

# Or open SSH and use microcom directly
./fc1 ssh
# Then on gateway:
microcom /usr/qk/etc/sv/FC-1/console
```

---

## Troubleshooting

### Connection Issues

**Cannot reach target:**
```bash
# Verify network connectivity
ping 192.168.7.1

# Check if SSH port is open
nc -zv 192.168.7.1 22222
```

**Host key verification failed:**
```bash
# Clear stale host key
./fc1 clear-key
```

**sshpass not found:**
```bash
sudo apt-get install sshpass
```

### Service Issues

**FC-1 not running:**
```bash
./fc1 status        # Check status
./fc1 start         # Start service
./fc1 log           # Check logs for errors
```

**Service won't start:**
```bash
# Check if binary exists
./fc1 ssh
ls -la /usr/qk/bin/FC-1

# Check permissions
chmod +x /usr/qk/bin/FC-1
```

### CLI Command Issues

**"Expect not found on target" followed by tar error:**
```bash
# SCP may have failed silently - manually deploy expect
scp -P 22222 external_tools/build/expect-arm.tar.gz root@192.168.7.1:/tmp/
./fc1 ssh
mkdir -p /usr/qk/etc/sv/FC-1/expect
cd /usr/qk/etc/sv/FC-1/expect
tar xzf /tmp/expect-arm.tar.gz
```

**"microcom: can't create '/var/lock/LCK..console': File exists":**
```bash
# Stale lock file from previous session
./fc1 ssh
cat /var/lock/LCK..console     # Shows PID
ps aux | grep microcom          # Check if process exists
kill <PID>                      # Kill if running
rm /var/lock/LCK..console       # Remove stale lock
```

**Special characters not working in commands:**
```bash
# Always quote the command
./fc1 cmd "debug ?"    # Correct
./fc1 cmd debug ?      # Wrong - ? gets expanded
```

### Deployment Issues

**Binary not found:**
```bash
# Build first
cd Fleet-Connect-1/build
make -j4
cd ../../scripts
./fc1 push -run
```

**Permission denied on push:**
```bash
# Check SSH connection
./fc1 ssh
# Verify you're connecting as root
whoami
```

---

## Gateway Paths Reference

| Item | Path |
|------|------|
| FC-1 Binary | `/usr/qk/bin/FC-1` |
| Service Directory | `/usr/qk/etc/sv/FC-1/` |
| Console Symlink | `/usr/qk/etc/sv/FC-1/console` |
| Expect Tools | `/usr/qk/etc/sv/FC-1/expect/` |
| Details File | `/usr/qk/etc/sv/FC-1/FC-1_details.txt` |
| Application Log | `/var/log/fc-1.log` |
| Service Log | `/var/log/FC-1/current` |
| PPP Log | `/var/log/pppd/current` |

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [connecting_to_Fleet-Connect-1.md](connecting_to_Fleet-Connect-1.md) | SSH connection methods and helpers |
| [testing_fc_1_application.md](testing_fc_1_application.md) | Comprehensive testing guide |
| [validating_FC-1_application.md](validating_FC-1_application.md) | Quick validation reference |
| [expect_tool_use.md](expect_tool_use.md) | Expect tools build and usage |
| [gen/run_command_on_FC-1_plan.md](gen/run_command_on_FC-1_plan.md) | CLI command implementation details |

---

## Quick Reference Card

```bash
# Service control
./fc1 start              # Start FC-1
./fc1 stop               # Stop FC-1
./fc1 restart            # Restart FC-1
./fc1 status             # Check status (default)
./fc1 enable             # Enable auto-start
./fc1 disable -y         # Disable auto-start

# Deployment
./fc1 push               # Deploy binary (stopped)
./fc1 push -run          # Deploy and start
./fc1 config <file>      # Deploy config (removes .bin files)

# CLI commands
./fc1 cmd "?"            # Full help
./fc1 cmd "v"            # Version
./fc1 cmd "cell status"  # Cellular
./fc1 cmd "ppp"          # PPP status
./fc1 cmd "net"          # Network
./fc1 cmd "imx stats"    # iMatrix stats
./fc1 cmd "ms"           # Memory stats
./fc1 cmd "debug ?"      # Debug flags

# Logs and status
./fc1 log                # View logs
./fc1 ppp                # PPP link status

# SSH access
./fc1 ssh                # Interactive session
./fc1 -d <host> ssh      # SSH to specific host
./fc1 clear-key          # Clear host key

# Help
./fc1 help               # Show all commands
```
