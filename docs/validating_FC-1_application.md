# Validating FC-1 Application

**Last Updated**: 2026-01-02

Read: `/home/greg/iMatrix/iMatrix_Client/docs/testing_fc_1_application.md` to learn how to connect to the gateway.

## Quick Start

Use the script: `scripts/fc1` to control the FC-1 application on the gateway.

### Common Workflow

1. **Build and push the binary:**
   ```bash
   cd Fleet-Connect-1/build && make -j4
   cd ../../scripts
   ./fc1 push -run    # Deploy and start
   ```

2. **Check status and run commands:**
   ```bash
   ./fc1 status                  # Service status
   ./fc1 cmd "cell status"       # Cellular status
   ./fc1 cmd "imx stats"         # iMatrix statistics
   ./fc1 cmd "?"                 # Full CLI help
   ```

3. **View logs:**
   ```bash
   ./fc1 log                     # Recent logs
   ```

4. **Stop service when done:**
   ```bash
   ./fc1 stop
   ```

## Full Script Options

```
FC-1 Remote Control

Usage: scripts/fc1 [-d destination] <command> [options]

Options:
  -d <addr>   Specify target host (default: 192.168.7.1)

Commands:
  start       Start FC-1 service on target
  stop        Stop FC-1 service on target
  restart     Restart FC-1 service
  status      Show service status
  enable      Enable FC-1 auto-start and start service
  disable     Disable FC-1 auto-start (with confirmation)
  disable -y  Disable without confirmation prompt
  run [opts]  Run FC-1 in foreground on target
  log         Show recent logs
  ppp         Show PPP link status (interface, service, log)
  cmd <cmd>   Execute CLI command via microcom (returns output)
  deploy      Deploy service script to target
  push        Push built FC-1 binary to target (leaves service stopped)
  push -run   Push binary and start FC-1 service
  ssh         Open SSH session to target
  clear-key   Clear SSH host key (for device changes)
  help        Show this help

Target: root@192.168.7.1:22222
```

## Examples

```bash
# Service control
scripts/fc1 start                    # Start FC-1
scripts/fc1 stop                     # Stop FC-1
scripts/fc1 restart                  # Restart FC-1
scripts/fc1 status                   # Check status

# Remote CLI commands (supports special characters like ?)
scripts/fc1 cmd "help"               # Show CLI help
scripts/fc1 cmd "?"                  # Full command list
scripts/fc1 cmd "v"                  # Version info
scripts/fc1 cmd "debug ?"            # Debug flags
scripts/fc1 cmd "cell status"        # Cellular status
scripts/fc1 cmd "imx stats"          # iMatrix statistics
scripts/fc1 cmd "ms"                 # Memory statistics

# Deployment
scripts/fc1 push                     # Deploy binary (stays stopped)
scripts/fc1 push -run                # Deploy and start

# Logs
scripts/fc1 log                      # View recent logs
scripts/fc1 ppp                      # PPP link status

# SSH access
scripts/fc1 ssh                      # Interactive SSH session
scripts/fc1 -d 10.0.0.50 ssh         # SSH to specific host
```

## Notes

- The `cmd` command uses expect/microcom to execute CLI commands remotely
- Expect tools are automatically deployed on first use if not present
- Expect tools are stored persistently at `/usr/qk/etc/sv/FC-1/expect/`
- Special characters like `?` are properly handled in commands
