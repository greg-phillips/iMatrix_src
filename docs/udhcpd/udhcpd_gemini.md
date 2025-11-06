A single instance of the BusyBox `udhcpd` DHCP server can only be bound to **one network interface** at a time, as indicated by the `interface` option in its configuration file.

To serve DHCP requests on **multiple interfaces** (like `eth0` and `wlan0`) with independent settings on a BusyBox system, you must run **two independent instances** of the `udhcpd` daemon, each with its own configuration file, lease file, and PID file.

Here is a detailed tutorial and example for setting up two independent `udhcpd` instances.

-----

## 🛠️ Step 1: Configure Static IPs for Interfaces

Before starting a DHCP server, the interfaces it will serve **must** have a static IP address configured in the network subnet it will manage. This is often done in `/etc/network/interfaces`.

| Interface | IP Address | Netmask | Subnet/Range |
| :--- | :--- | :--- | :--- |
| **eth0** | `192.168.10.1` | `255.255.255.0` | `192.168.10.0/24` |
| **wlan0** | `192.168.20.1` | `255.255.255.0` | `192.168.20.0/24` |

### Example `/etc/network/interfaces`

```bash
# Configuration for eth0 (Ethernet)
auto eth0
iface eth0 inet static
    address 192.168.10.1
    netmask 255.255.255.0

# Configuration for wlan0 (Wireless)
auto wlan0
iface wlan0 inet static
    address 192.168.20.1
    netmask 255.255.255.0
```

-----

## ⚙️ Step 2: Create Two Separate `udhcpd` Configuration Files

Each instance requires its own configuration file to specify the interface, IP range, options, and file locations.

### Configuration File for eth0: `/etc/udhcpd.eth0.conf`

```bash
# Interface for this instance
interface eth0

# Lease IP range
start 192.168.10.100
end 192.168.10.199

# Lease files (must be unique for each instance)
pidfile /var/run/udhcpd.eth0.pid
lease_file /var/lib/misc/udhcpd.eth0.leases

# DNS server (example: a custom server and Google DNS)
option dns 192.168.10.1 8.8.8.8

# Default router (should be the static IP of eth0)
option router 192.168.10.1

# Subnet Mask
option subnet 255.255.255.0

# Lease time in seconds (e.g., 2 hours)
option lease 7200
```

-----

### Configuration File for wlan0: `/etc/udhcpd.wlan0.conf`

```bash
# Interface for this instance
interface wlan0

# Lease IP range (must be in the wlan0 subnet)
start 192.168.20.10
end 192.168.20.50

# Lease files (must be unique for each instance)
pidfile /var/run/udhcpd.wlan0.pid
lease_file /var/lib/misc/udhcpd.wlan0.leases

# DNS server (example: different settings for a WiFi client)
option dns 1.1.1.1 1.0.0.1

# Default router (should be the static IP of wlan0)
option router 192.168.20.1

# Subnet Mask
option subnet 255.255.255.0

# Lease time in seconds (e.g., 1 day)
option lease 86400
```

-----

## 🚀 Step 3: Startup Script and Daemon Commands

Since BusyBox doesn't typically use systemd or complex init systems, you will use a simple shell script (often in `/etc/init.d` or `/etc/local.d`) to manage the two daemons.

### Example Init Script (`/etc/init.d/S80udhcpd_multi`)

This script can be modified for your specific BusyBox init system (like runit or openrc).

```bash
#!/bin/sh

# Define the config files
CONF_ETH0="/etc/udhcpd.eth0.conf"
CONF_WLAN0="/etc/udhcpd.wlan0.conf"

# Define the PID files
PID_ETH0="/var/run/udhcpd.eth0.pid"
PID_WLAN0="/var/run/udhcpd.wlan0.pid"

# Create misc directory if it doesn't exist for lease files
mkdir -p /var/lib/misc

start() {
    echo "Starting udhcpd for eth0..."
    # Start udhcpd for eth0. -f for foreground, -p for pidfile, -C for config file.
    # We remove -f and run it in the background (&) for an init script
    /usr/sbin/udhcpd -p $PID_ETH0 $CONF_ETH0 &

    echo "Starting udhcpd for wlan0..."
    /usr/sbin/udhcpd -p $PID_WLAN0 $CONF_WLAN0 &
}

stop() {
    echo "Stopping udhcpd for eth0..."
    if [ -f $PID_ETH0 ]; then
        kill $(cat $PID_ETH0)
        rm -f $PID_ETH0
    fi

    echo "Stopping udhcpd for wlan0..."
    if [ -f $PID_WLAN0 ]; then
        kill $(cat $PID_WLAN0)
        rm -f $PID_WLAN0
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac

exit 0
```

**Actions:**

1.  Save the script: `vi /etc/init.d/S80udhcpd_multi`
2.  Make it executable: `chmod +x /etc/init.d/S80udhcpd_multi`
3.  **Ensure paths are correct:** Replace `/usr/sbin/udhcpd` with the actual path to your `udhcpd` binary if it's different.
4.  Run the static IP configuration: `ifup eth0` and `ifup wlan0`
5.  Start the daemons: `/etc/init.d/S80udhcpd_multi start`

### Verification

Check that both daemons are running and have created their respective PID and lease files:

```bash
# Check for two processes
ps | grep udhcpd

# Check PID files
ls /var/run/udhcpd.*.pid

# Check lease files
ls /var/lib/misc/udhcpd.*.leases
```

The `ps` output should show two separate `udhcpd` processes running. Your clients connecting to `eth0` will receive an IP in the `192.168.10.x` range with the eth0-specific options, and clients on `wlan0` will get an IP in the `192.168.20.x` range with the wlan0-specific options.

-----

Would you like to explore how to set up **iptables NAT/masquerading** to allow clients on both subnets to share an internet connection through your BusyBox device?