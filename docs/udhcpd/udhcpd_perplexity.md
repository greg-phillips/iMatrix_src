<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# provide an extremely detailed tutorial about the scripts to be used and examples for using udhcpd with multiple interfaces on a busybox linux system. The example should show two interfaces eth0 and wlan0 both with independent udhcpd settings

Based on the information gathered, udhcpd on a busybox Linux system can handle only one interface per process. To run udhcpd on multiple interfaces like eth0 and wlan0 with independent settings, you need to run multiple instances of udhcpd — one instance per interface with its own configuration file. This approach requires writing scripts to start and manage these udhcpd instances separately.

Here is a detailed tutorial covering the scripts and configuration examples for running udhcpd on eth0 and wlan0 with independent configurations on a busybox Linux system.

***

## Overview of udhcpd and Multiple Interfaces

- The udhcpd daemon supports serving DHCP on one interface per running process.
- To serve DHCP on multiple interfaces, you must run one udhcpd instance per interface.
- Each instance uses its own configuration file specifying the DHCP range and options for that interface.
- You can create startup scripts or an ifup/ifdown network hook to start/stop udhcpd instances on interface state changes.

***

## Step 1: Prepare udhcpd Configuration Files

Create two separate configuration files for eth0 and wlan0 in `/etc`.

Example: `/etc/udhcpd.eth0.conf`

```
start 192.168.10.100
end 192.168.10.150
interface eth0
option subnet 255.255.255.0
option router 192.168.10.1
option lease 86400
option dns 8.8.8.8
```

Example: `/etc/udhcpd.wlan0.conf`

```
start 192.168.20.100
end 192.168.20.150
interface wlan0
option subnet 255.255.255.0
option router 192.168.20.1
option lease 86400
option dns 8.8.4.4
```

Each config defines a separate subnet for the interface.

***

## Step 2: Create Separate Lease Files

Create lease files for each interface, e.g.,

```
/var/lib/misc/udhcpd.eth0.leases
/var/lib/misc/udhcpd.wlan0.leases
```

Make sure udhcpd has write permission to these files/directories.

***

## Step 3: Write Script to Start Multiple udhcpd Instances

Create a script `/usr/local/bin/start-udhcpd.sh` with the following content:

```sh
#!/bin/sh

# Start udhcpd for eth0
udhcpd -f /etc/udhcpd.eth0.conf -p /var/run/udhcpd.eth0.pid -l /var/lib/misc/udhcpd.eth0.leases &

# Start udhcpd for wlan0
udhcpd -f /etc/udhcpd.wlan0.conf -p /var/run/udhcpd.wlan0.pid -l /var/lib/misc/udhcpd.wlan0.leases &
```

Make the script executable:

```sh
chmod +x /usr/local/bin/start-udhcpd.sh
```

This script launches independent udhcpd processes in the background for eth0 and wlan0.

***

## Step 4: Create Stop Script for udhcpd

To stop the udhcpd daemons cleanly, create `/usr/local/bin/stop-udhcpd.sh`:

```sh
#!/bin/sh

kill $(cat /var/run/udhcpd.eth0.pid) 2>/dev/null
kill $(cat /var/run/udhcpd.wlan0.pid) 2>/dev/null
```

Make executable:

```sh
chmod +x /usr/local/bin/stop-udhcpd.sh
```


***

## Step 5: Integrate with Network Up/Down Scripts

You can hook into BusyBox interface up/down events with `/etc/network/if-up.d/udhcpd` and `/etc/network/if-down.d/udhcpd` scripts:

Example `/etc/network/if-up.d/udhcpd`:

```sh
#!/bin/sh

if [ "$IFACE" = "eth0" ]; then
    udhcpd -f /etc/udhcpd.eth0.conf -p /var/run/udhcpd.eth0.pid -l /var/lib/misc/udhcpd.eth0.leases &
elif [ "$IFACE" = "wlan0" ]; then
    udhcpd -f /etc/udhcpd.wlan0.conf -p /var/run/udhcpd.wlan0.pid -l /var/lib/misc/udhcpd.wlan0.leases &
fi
```

Make it executable:

```sh
chmod +x /etc/network/if-up.d/udhcpd
```

Example `/etc/network/if-down.d/udhcpd`:

```sh
#!/bin/sh

if [ "$IFACE" = "eth0" ]; then
    kill $(cat /var/run/udhcpd.eth0.pid) 2>/dev/null
elif [ "$IFACE" = "wlan0" ]; then
    kill $(cat /var/run/udhcpd.wlan0.pid) 2>/dev/null
fi
```

Make it executable:

```sh
chmod +x /etc/network/if-down.d/udhcpd
```

These scripts start and stop udhcpd automatically when interfaces come up or down.

***

## Additional Notes

- Each udhcpd process must have its own configuration, lease file, and pidfile to avoid conflicts.
- Assign distinct IP ranges and subnets for each interface.
- Test each udhcpd instance manually before automating with scripts.
- Adjust DHCP options as needed per interface (e.g., different routers or DNS servers).

***

This setup provides independent DHCP service on eth0 and wlan0 interfaces using udhcpd on BusyBox Linux.

If you want sample startup and configuration files or troubleshooting info, please ask.

***

References:

- Multiple udhcpd instances recommended for multi-interface use[^1][^2]
- Sample udhcpd.conf format and options[^3]
- Shell script examples for starting/stopping udhcpd per interface[^2][^4]
<span style="display:none">[^10][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://e2e.ti.com/support/processors-group/processors/f/processors-forum/554612/configuring-udhcpd-for-more-than-one-network-interfaces

[^2]: https://lists.debian.org/debian-boot/2015/03/msg00119.html

[^3]: https://dunedlin.wordpress.com/2013/09/21/network-connections-with-udhcpc-and-udhcpd/

[^4]: https://iotbytes.wordpress.com/configure-dhcp-server-on-microcore-tiny-linux/

[^5]: https://stackoverflow.com/questions/35595633/how-can-i-use-udhcpd-to-start-a-dhcp-server-on-more-than-one-nic

[^6]: https://busybox.net/BusyBox.html

[^7]: https://mangoh.discourse.group/t/how-to-use-busybox-to-generate-udhcpd/9430

[^8]: https://www.juniper.net/documentation/us/en/software/junos/subscriber-mgmt-sessions/topics/topic-map/dhcp-common-config-interface-group.html

[^9]: https://stackoverflow.com/questions/18369848/multiple-ethernet-interfaces-how-to-create-a-separate-network-and-access-from

[^10]: https://udhcp.busybox.net

