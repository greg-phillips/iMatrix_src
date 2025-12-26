# FC-1 Startup Options and runsv Service Configuration

**Date:** 2025-12-24
**Author:** Claude Code
**Target:** FC-1 Gateway Board (192.168.7.1)
**Status:** Investigation Complete

---

## Executive Summary

The FC-1 application is **NOT RUNNING** because the runsv `run` script is missing from `/usr/qk/etc/sv/FC-1/run`. The binary exists at `/home/FC-1` but the service cannot start.

---

## 1. FC-1 Application

### Binary Location

| Item | Value |
|------|-------|
| Path | `/home/FC-1` |
| Size | 13,005,104 bytes (~13MB) |
| Permissions | -rwxr-xr-x |
| Last Modified | Dec 23 19:02 |

### Command Line Options

```
Usage: /home/FC-1 [OPTIONS]

Configuration Options:
  -P                  Print detailed configuration from file
  -S                  Print configuration summary
  -I                  Display configuration file index/analysis

System Options:
  -R                  Reset network configuration (force regeneration)
  --clear_history     Delete all disk-based sensor history
                      WARNING: Deletes all unsent data! Cannot be undone.

Information:
  --help, -?          Display this help message

Examples:
  /home/FC-1                  Normal startup (default)
  /home/FC-1 -S               Print config summary and start
  /home/FC-1 --clear_history  Clear all history and exit
  /home/FC-1 --help           Show this help
```

### Configuration Locations

| Item | Path |
|------|------|
| Config directory | `/usr/qk/etc/sv/FC-1` |
| Main config | `/usr/qk/etc/sv/FC-1/imatrix_config.bin` |
| Config backup | `/usr/qk/etc/sv/FC-1/imatrix_config.bak` |
| Product config | `/usr/qk/etc/sv/FC-1/Aptera_PI_1_cfg.bin` |
| Disk history | `/tmp/mm2/` (Linux) |

---

## 2. runsv Service Configuration

### Service Structure

```
/service/FC-1 -> /usr/qk/etc/sv/FC-1  (symlink)

/usr/qk/etc/sv/FC-1/
├── Aptera_PI_1_cfg.bin      (505,792 bytes - product config)
├── imatrix_config.bin       (560,648 bytes - main config)
├── imatrix_config.bak       (560,648 bytes - backup)
├── imatrix_private_key.bin  (228 bytes)
├── imatrix_public_cert.bin  (831 bytes)
├── iMatrix.lock             (6 bytes - lock file)
├── ota.state                (12 bytes)
├── wifi_*.bin               (Wi-Fi network configs)
├── energy_trips/            (Trip data storage)
├── shared/                  (Shared data)
├── supervise/               (runsv control)
│   ├── control              (named pipe)
│   ├── ok                   (named pipe)
│   ├── lock
│   ├── pid                  (empty - not running)
│   ├── stat                 (contains "down")
│   └── status
└── run                      ** MISSING! **
```

### Current Service Status

```bash
$ sv status FC-1
down: FC-1: 0s, normally up, want up
```

**Problem:** The `run` script is missing, causing runsv to fail repeatedly:
```
runsv FC-1: fatal: unable to start ./run: file does not exist
```

---

## 3. All Configured Services

The system uses **runit** (runsvdir) for service management:

| Service | Location | Status |
|---------|----------|--------|
| FC-1 | /usr/qk/etc/sv/FC-1 | **DOWN** (missing run script) |
| udhcpd | /usr/qk/etc/sv/udhcpd | Running |
| wpa | /etc/sv/wpa | Running |
| dropbear | /etc/sv/dropbear | Running |
| dbus | /etc/sv/dbus | Running |
| chrony | /etc/sv/chrony | Running |
| gpsd | /etc/sv/gpsd | Running |
| bluetoothd | /etc/sv/bluetoothd | Running |
| mosquitto | /etc/sv/mosquitto | Running |
| syslogd | /etc/sv/syslogd | Running |
| klogd | /etc/sv/klogd | Running |
| haveged | /etc/sv/haveged | Running |
| dnsmasq | /etc/sv/dnsmasq | Running |
| earlyoom | /etc/sv/earlyoom | Running |
| monit | /etc/sv/monit | Running |
| wdog_* | /etc/sv/wdog_* | Running |

---

## 4. Example Run Scripts

### udhcpd (similar structure to what FC-1 needs)

```bash
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/opt:/opt/bin

echo "Start udhcpd for eth0..."

# Wait for eth0
while ! ifconfig eth0 >/dev/null 2>&1; do
    sleep 0.5
done

# Set IP
ifconfig eth0 192.168.7.1

# Create lease file if needed
mkdir -p /var/lib/misc
touch /var/lib/misc/udhcpd.eth0.leases

exec udhcpd -f /etc/network/udhcpd.eth0.conf
```

### dropbear (SSH server)

```bash
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/opt:/opt/bin

printf "Start Dropbear runit service...\n"

mkdir -p /var/run/dropbear
if [ ! -f /etc/dropbear_rsa/dropbear_rsa_host_key ]; then
    sleep 1
    dropbearkey -t ed25519 -f /etc/dropbear_rsa/dropbear_rsa_host_key
fi

exec dropbear -F -r /etc/dropbear_rsa/dropbear_rsa_host_key -p 22222 -T 3 -b /etc/issue.net
```

---

## 5. Proposed FC-1 Run Script

Based on the service patterns, the missing run script should be:

```bash
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/opt:/opt/bin

printf "Start FC-1 Gateway Service...\n"

# Change to config directory
cd /usr/qk/etc/sv/FC-1

# Wait for network to be ready (optional)
sleep 2

# Execute FC-1 in foreground
exec /home/FC-1
```

### To Create the Run Script

```bash
ssh -p 22222 root@192.168.7.1

cat > /usr/qk/etc/sv/FC-1/run << 'EOF'
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/opt:/opt/bin

printf "Start FC-1 Gateway Service...\n"

cd /usr/qk/etc/sv/FC-1

exec /home/FC-1
EOF

chmod +x /usr/qk/etc/sv/FC-1/run

# Restart the service
sv restart FC-1
```

---

## 6. Service Control Commands

```bash
# Check status
sv status FC-1

# Start service
sv start FC-1

# Stop service
sv stop FC-1

# Restart service
sv restart FC-1

# Force restart
sv force-restart FC-1

# View logs (if log service configured)
cat /var/log/FC-1/current
```

---

## 7. Questions for User

1. **Why is the run script missing?** Was it accidentally deleted, or was FC-1 installed without it?

2. **Should I create the run script?** I can create it based on the pattern used by other services.

3. **Are there any special startup requirements?** Such as waiting for specific services or interfaces?

4. **Should logging be configured?** The service doesn't have a log/ subdirectory - should one be created?

---

## Summary

| Item | Status |
|------|--------|
| FC-1 binary | Present at `/home/FC-1` |
| FC-1 options | `-P`, `-S`, `-I`, `-R`, `--clear_history`, `--help` |
| Service directory | `/usr/qk/etc/sv/FC-1` |
| Run script | **MISSING** |
| Service status | **DOWN** |
| Config files | Present |

**Next Step:** Create the missing run script to enable FC-1 to start.

---

*Report Generated: 2025-12-24*
