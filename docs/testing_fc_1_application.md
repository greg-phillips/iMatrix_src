# Testing the FC-1 Application on QConnect Gateway

**Document Version**: 1.4
**Date**: 2025-12-30
**Last Updated**: 2025-12-31
**Author**: Development Team

## Overview

This document provides detailed instructions for developers to connect to and test the FC-1 (Fleet Connect) application running on the QConnect gateway device. FC-1 is a gateway application that manages vehicle connectivity, cellular modems, OBD2/CAN bus processing, and iMatrix cloud connectivity.

## Prerequisites

### Host Machine Requirements
- Linux workstation (Ubuntu/WSL2 recommended)
- `sshpass` package installed: `sudo apt-get install sshpass`
- Network connectivity to the gateway (USB or Ethernet)

### Gateway Connection Methods
1. **USB Connection**: Gateway appears as USB network device at `192.168.7.1`
2. **WiFi AP Mode**: Connect to gateway's WiFi AP (if configured)
3. **Ethernet**: Direct ethernet connection (if available)

## Gateway Connection Details

| Parameter | Value |
|-----------|-------|
| IP Address | `192.168.7.1` |
| SSH Port | `22222` (non-standard) |
| Username | `root` |
| Password | `PasswordQConnect` |
| FC-1 Console | `/usr/qk/etc/sv/FC-1/console` (symlink to PTY) |
| FC-1 Details | `/usr/qk/etc/sv/FC-1/FC-1_details.txt` |

**Important**: The SSH port is `22222`, not the standard port 22.

**Note**: The console symlink always points to the current PTY device (e.g., `/dev/pts/3`), providing a consistent access path regardless of the dynamically assigned PTY number.

## Connection Methods

### Method 1: Using the fc1 Helper Script (Recommended)

The repository includes a helper script at `scripts/fc1` that simplifies common operations:

```bash
cd /home/greg/iMatrix/iMatrix_Client/scripts

# Check FC-1 service status
./fc1 status

# View PPP connection status
./fc1 ppp

# View recent logs
./fc1 log

# Open SSH session to gateway
./fc1 ssh

# Start/stop/restart FC-1 service
./fc1 start
./fc1 stop
./fc1 restart

# Deploy new FC-1 binary
./fc1 push         # Deploy but don't start
./fc1 push -run    # Deploy and start service
```

### Method 2: Direct SSH Connection

```bash
# Using sshpass for non-interactive login
sshpass -p 'PasswordQConnect' ssh -p 22222 -o StrictHostKeyChecking=no root@192.168.7.1

# Or interactively (will prompt for password)
ssh -p 22222 root@192.168.7.1
```

### Method 3: SCP File Transfer

```bash
# Copy file TO gateway
sshpass -p 'PasswordQConnect' scp -P 22222 -o StrictHostKeyChecking=no localfile root@192.168.7.1:/path/on/gateway

# Copy file FROM gateway
sshpass -p 'PasswordQConnect' scp -P 22222 -o StrictHostKeyChecking=no root@192.168.7.1:/path/on/gateway localfile
```

## Connecting to the FC-1 CLI

The FC-1 application provides an interactive command-line interface (CLI) accessible via a pseudo-terminal (PTY). A well-known symlink at `/usr/qk/etc/sv/FC-1/console` always points to the current PTY, providing consistent access.

### Step-by-Step CLI Connection

#### Step 1: SSH to the Gateway
```bash
ssh -p 22222 root@192.168.7.1
# Enter password: PasswordQConnect
```

You will see a security warning banner:
```
*** WARNING ***
This is a private system. Unauthorized access is prohibited.
All activities may be monitored and recorded.
Use of this system constitutes consent to monitoring.
```

#### Step 2: Verify FC-1 is Running
```bash
sv status FC-1
```

Expected output:
```
run: FC-1: (pid XXXXX) XXXXs, normally down
```

If FC-1 is not running:
```bash
sv start FC-1
```

#### Step 3: Connect Using the Console Symlink (Recommended)
```bash
microcom /usr/qk/etc/sv/FC-1/console
```

The symlink automatically points to the current PTY device. You can verify the symlink target with:
```bash
ls -la /usr/qk/etc/sv/FC-1/console
```

#### Step 4 (Alternative): Connect Using Direct PTY
If the symlink is unavailable, find and use the direct PTY device:
```bash
ls -la /dev/pts/
microcom /dev/pts/X  # Replace X with actual PTY number
```

**Important microcom notes:**
- Press **Enter** after connecting to see the CLI prompt
- Debug output streams continuously in the background
- To exit microcom: Press **Ctrl+X**

#### Step 5: Interact with the CLI
Once connected, press Enter to see the prompt. You can now type commands:
```
> cell status
> ppp
> help
```

### Alternative: Using screen (if microcom unavailable)
```bash
screen /usr/qk/etc/sv/FC-1/console
```
Exit screen with: `Ctrl+A` then `K`, then `Y` to confirm

### Method 4: Telnet CLI Access (Port 23)

FC-1 runs a telnet server on port 23 that provides direct CLI access without needing to use microcom or screen on the gateway.

#### From Host Machine
```bash
# Using telnet
telnet 192.168.7.1 23

# Using netcat (nc)
nc 192.168.7.1 23
```

#### Interactive Session Example
```bash
$ nc 192.168.7.1 23
IoT Device Command Line Processor
> help
...command list...
> cell status
...cellular status output...
> log
...logging status...
```

**Note**: Press Enter after connecting to see the CLI prompt. Type `quit` or press Ctrl+C to disconnect.

#### Scripted Command Execution
```bash
# Send a single command
echo "cell status" | nc 192.168.7.1 23

# Send multiple commands
echo -e "cell status\nppp\nlog" | nc 192.168.7.1 23

# Capture output to file
echo "imx stats" | nc 192.168.7.1 23 > output.txt
```

### Alternative: Sending Commands Non-Interactively
For scripting or automation, you can send commands directly:
```bash
# From host machine (using console symlink)
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 "echo 'cell status' > /usr/qk/etc/sv/FC-1/console"
```

**Note**: Non-interactive command sending may not work reliably for all commands as the CLI expects an interactive terminal.

## FC-1 CLI Commands Reference

### Cellular Commands
| Command | Description |
|---------|-------------|
| `cell` | Print cellular status summary |
| `cell status` | Same as `cell` |
| `cell scan` | Trigger manual carrier scan (bypasses protection) |
| `cell reset` | Soft reset cellular state machine |
| `cell reset hard` | Hardware GPIO modem reset (power cycle) |
| `cell reinit` | Reinitialize cellular modem |
| `cell operators` | List discovered operators from last scan |
| `cell blacklist` | Show blacklisted carriers |

### PPP Commands
| Command | Description |
|---------|-------------|
| `ppp` | PPP connection status |
| `ppp log` | Recent PPP log output |

### Network Commands
| Command | Description |
|---------|-------------|
| `net` | Network manager status |
| `net stats` | Network statistics |

### System Commands
| Command | Description |
|---------|-------------|
| `help` | List available commands |
| `v` | Display software version |
| `debug on` | Enable debug output |
| `debug off` | Disable debug output |
| `debug <flag>` | Toggle specific debug flag |
| `reboot` | Reboot the gateway |

### Log Commands
| Command | Description |
|---------|-------------|
| `log` | Show current logging status |
| `log on` | Enable iMatrix cloud logging |
| `log off` | Disable iMatrix cloud logging |
| `log test` | Run log rotation test (generates test messages) |

**Note**: FC-1 also writes logs to the filesystem at `/var/log/fc-1.log` with automatic rotation.

### iMatrix Commands
| Command | Description |
|---------|-------------|
| `imx` | iMatrix client status |
| `imx flush` | Clear statistics |
| `imx stats` | Detailed statistics |
| `imx pause` | Pause cloud upload |
| `imx resume` | Resume cloud upload |

### Configuration Commands
| Command | Description |
|---------|-------------|
| `config` | Show configuration |
| `config <item> <value>` | Set configuration item |

## FC-1 Service Management

The FC-1 application runs as a runit service on the gateway.

### Service Control Commands (via SSH)
```bash
# Check service status
sv status FC-1

# Start FC-1
sv start FC-1

# Stop FC-1
sv stop FC-1

# Restart FC-1
sv restart FC-1

# Enable auto-start on boot
touch /etc/service/FC-1/down  # Remove to enable
rm /etc/service/FC-1/down     # Enable auto-start
```

### Service Locations
| Item | Path |
|------|------|
| FC-1 Binary | `/usr/qk/etc/sv/FC-1/FC-1` |
| Service Directory | `/usr/qk/etc/sv/FC-1/` |
| Run Script | `/usr/qk/etc/sv/FC-1/run` |
| Console Symlink | `/usr/qk/etc/sv/FC-1/console` (-> `/dev/pts/X`) |
| Details File | `/usr/qk/etc/sv/FC-1/FC-1_details.txt` |
| runit Log Directory | `/var/log/FC-1/` |
| Application Log File | `/var/log/fc-1.log` |

### Viewing FC-1 Logs

**runit Service Logs** (stdout/stderr captured by svlogd):
```bash
# View current log
cat /var/log/FC-1/current

# Tail log in real-time
tail -f /var/log/FC-1/current

# View with timestamps (svlogd format)
cat /var/log/FC-1/current | tai64nlocal
```

**Filesystem Logger Logs** (application logs with rotation):
```bash
# View current application log
cat /var/log/fc-1.log

# Tail application log in real-time
tail -f /var/log/fc-1.log

# List all log files (including rotated)
ls -la /var/log/fc-1*.log

# View rotated logs (format: fc-1.YYYY-MM-DD.N.log)
cat /var/log/fc-1.2025-12-31.1.log
```

**Log File Rotation**:
- Maximum file size: 10 MB per file
- Maximum total storage: 100 MB
- Retention: 5 days
- Format: `/var/log/fc-1.YYYY-MM-DD.N.log` (N = sequence number)

## PPP Service Management

The PPP daemon (pppd) is also managed by runit.

### PPP Service Commands
```bash
# Check PPP status
sv status pppd

# Start PPP
sv start pppd
sv up pppd      # Alternative

# Stop PPP
sv stop pppd
sv down pppd    # Alternative (also disables auto-restart)

# Restart PPP
sv restart pppd
```

### PPP Log Location
```bash
# View PPP log
cat /var/log/pppd/current

# Tail PPP log
tail -f /var/log/pppd/current
```

## Modem Access

The gateway has two modems:

| Modem | Device | Usage |
|-------|--------|-------|
| Qualcomm 4108 | `/dev/ttyACM0` | Data connection (pppd) |
| Cinterion PLS63-W | `/dev/ttyACM2` | AT commands (FC-1 cellular_man) |

### Direct Modem AT Commands
To send AT commands directly to the Cinterion modem:
```bash
microcom /dev/ttyACM2
```

Common AT commands:
```
AT              # Test modem response
AT+CSQ          # Signal strength (0-31)
AT+COPS?        # Current operator
AT+COPS=?       # Scan for operators (takes 3-5 minutes!)
ATI             # Modem identification
AT+CPIN?        # SIM status
```

Exit with **Ctrl+X**

## Deploying New FC-1 Builds

### Using the fc1 Script (Recommended)
```bash
cd /home/greg/iMatrix/iMatrix_Client/scripts

# Build FC-1 first
cd ../Fleet-Connect-1/build
make -j4
cd ../../scripts

# Deploy without starting
./fc1 push

# Deploy and start
./fc1 push -run
```

### Manual Deployment
```bash
# Stop FC-1
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 "sv stop FC-1"

# Copy new binary
sshpass -p 'PasswordQConnect' scp -P 22222 \
    /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1 \
    root@192.168.7.1:/usr/qk/etc/sv/FC-1/FC-1

# Set permissions and start
sshpass -p 'PasswordQConnect' ssh -p 22222 root@192.168.7.1 "chmod +x /usr/qk/etc/sv/FC-1/FC-1 && sv start FC-1"
```

## Troubleshooting

### Cannot Connect via SSH
1. Verify gateway is powered on
2. Check USB connection (for USB-connected gateways)
3. Verify IP address: `ping 192.168.7.1`
4. Ensure using correct port: `-p 22222`

### FC-1 Not Responding to CLI
1. Verify FC-1 is running: `sv status FC-1`
2. Check console symlink exists: `ls -la /usr/qk/etc/sv/FC-1/console`
3. Verify symlink target is valid: The symlink should point to an existing `/dev/pts/X` device
4. Try restarting FC-1: `sv restart FC-1`

### Console Symlink Issues
1. **Symlink doesn't exist**: FC-1 may not have started correctly. Check `sv status FC-1`
2. **Symlink points to stale PTY**: Restart FC-1 to create fresh symlink: `sv restart FC-1`
3. **Permission denied**: Verify you're running as root
4. **Fall back to direct PTY**: If symlink issues persist, find the PTY manually:
   ```bash
   ls -la /dev/pts/
   cat /usr/qk/etc/sv/FC-1/FC-1_details.txt  # Shows actual PTY device
   ```

### microcom Connection Issues
1. Ensure no other process is using the PTY
2. Try using console symlink: `microcom /usr/qk/etc/sv/FC-1/console`
3. Use screen as alternative: `screen /usr/qk/etc/sv/FC-1/console`

### PPP Connection Failures
1. Check modem: `microcom /dev/ttyACM2` then `AT+CSQ`
2. View PPP log: `cat /var/log/pppd/current`
3. Check for carrier: `AT+COPS?`
4. Restart pppd: `sv restart pppd`

### Debug Output Too Verbose
In FC-1 CLI:
```
debug off
```

## Quick Reference Card

```bash
# Connect to gateway via SSH
ssh -p 22222 root@192.168.7.1  # Password: PasswordQConnect

# Connect to FC-1 CLI via telnet (from host machine - recommended)
nc 192.168.7.1 23              # Exit: Ctrl+C or type 'quit'
telnet 192.168.7.1 23          # Alternative

# Connect to FC-1 CLI via console (on gateway)
microcom /usr/qk/etc/sv/FC-1/console   # Exit: Ctrl+X

# Check symlink target
ls -la /usr/qk/etc/sv/FC-1/console     # Shows -> /dev/pts/X

# View FC-1 startup details
cat /usr/qk/etc/sv/FC-1/FC-1_details.txt

# Common FC-1 CLI commands
cell status                    # Cellular status
cell scan                      # Trigger carrier scan
ppp                           # PPP status
log                           # Logging status
log test                      # Test log rotation
help                          # List commands

# Service management
sv status FC-1                # Check FC-1
sv restart FC-1               # Restart FC-1
sv status pppd                # Check PPP
sv restart pppd               # Restart PPP

# Logs
tail -f /var/log/fc-1.log      # Application log (filesystem logger)
tail -f /var/log/FC-1/current  # runit service log
tail -f /var/log/pppd/current  # PPP log
```

---

## Related Documentation

- `docs/ppp_testing_plan_1.md` - Full PPP testing plan and fix history
- `docs/ppp_testing_status.md` - Current testing status and handoff document
- `docs/gen/fix3_deployment_test_plan.md` - Post-scan PPP fix deployment procedure
- `docs/gen/cell_scan_test_plan.md` - Cell scan test procedure
- `docs/gen/fc1_console_symlink_plan.md` - Console symlink implementation details
