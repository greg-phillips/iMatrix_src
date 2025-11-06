Here’s a practical, copy-pasteable, end-to-end guide to running **multiple `udhcpd` (BusyBox DHCP server) instances** on the same BusyBox Linux host—one serving **`eth0`** and one serving **`wlan0`**—with **independent** configuration, lease files, and PID files.

I’ll assume a small router-style box where BusyBox provides `udhcpd`, `udhcpc`, `ip`, and `iptables`. If your distro uses a different init system, I’ve included alternatives you can pick from.

---

# Plan & topology

We’ll give the server box two LAN subnets:

* `eth0`: `192.168.10.0/24` (server IP `192.168.10.1`)
* `wlan0`: `192.168.20.0/24` (server IP `192.168.20.1`)

Each interface will run its **own** `udhcpd` instance with its **own** config and lease state.

> Key points
>
> * `udhcpd` serves **only one interface per process**, so we run **two processes**.
> * Use **distinct** config files, **distinct** lease files, **distinct** PID files.
> * Bring the interfaces **up with static IPs** before starting `udhcpd`.

---

# 0) Packages & files you’ll use

* BusyBox with `udhcpd` (server) and `udhcpc` (client).
* Optional: `start-stop-daemon` (often included in BusyBox), `syslogd` (for logs).

Useful paths (feel free to adapt):

```
/etc/udhcpd-eth0.conf
/etc/udhcpd-wlan0.conf
/var/lib/misc/udhcpd-eth0.leases
/var/lib/misc/udhcpd-wlan0.leases
/var/run/udhcpd-eth0.pid
/var/run/udhcpd-wlan0.pid
/usr/local/sbin/udhcpd-eth0.sh
/usr/local/sbin/udhcpd-wlan0.sh
```

Create directories if missing:

```sh
mkdir -p /var/lib/misc /var/run /usr/local/sbin
```

---

# 1) Assign static IPs to the server interfaces

Make sure your box owns the gateway IP on each subnet.

```sh
# eth0: 192.168.10.1/24
ip link set dev eth0 up
ip addr flush dev eth0
ip addr add 192.168.10.1/24 dev eth0

# wlan0: 192.168.20.1/24
ip link set dev wlan0 up
ip addr flush dev wlan0
ip addr add 192.168.20.1/24 dev wlan0
```

> If you use `ifconfig` instead:
>
> ```
> ifconfig eth0 192.168.10.1 netmask 255.255.255.0 up
> ifconfig wlan0 192.168.20.1 netmask 255.255.255.0 up
> ```

Make these persistent via your interface scripts (varies by distro). For a lean BusyBox system, add these lines to `/etc/rc.local` (see §6).

---

# 2) Create independent `udhcpd` configuration files

The BusyBox `udhcpd` config format is simple: one interface, one pool, options per config. You can repeat `option` lines as needed.

## `/etc/udhcpd-eth0.conf`

```conf
# === udhcpd instance for eth0 (192.168.10.0/24) ===

# The DHCP pool this instance will hand out:
start           192.168.10.100
end             192.168.10.200
interface       eth0

# Lease file for this instance (unique!)
lease_file      /var/lib/misc/udhcpd-eth0.leases

# PID file for this instance (unique!)
pidfile         /var/run/udhcpd-eth0.pid

# Optional: limit & timers
max_leases      101
remaining       yes
offer_time      60
min_lease       120
lease           86400          # default lease, seconds (1 day)

# Network options advertised to clients
option  subnet      255.255.255.0
option  router      192.168.10.1
option  dns         1.1.1.1 8.8.8.8
option  domain      lan-eth0.local
option  mtu         1500

# Classless static routes (DHCP option 121), if you need them:
# option  classless_static_routes  10.10.0.0/16 192.168.10.1

# PXE/TFTP example (uncomment if you run TFTP):
# option  tftp        192.168.10.1
# option  boot_file   pxelinux.0

# Hand out a few static reservations by MAC (optional)
# static_lease  aa:bb:cc:dd:ee:f0  192.168.10.50
# static_lease  aa:bb:cc:dd:ee:f1  192.168.10.51
```

## `/etc/udhcpd-wlan0.conf`

```conf
# === udhcpd instance for wlan0 (192.168.20.0/24) ===

start           192.168.20.50
end             192.168.20.150
interface       wlan0

lease_file      /var/lib/misc/udhcpd-wlan0.leases
pidfile         /var/run/udhcpd-wlan0.pid

max_leases      101
remaining       yes
offer_time      60
min_lease       120
lease           43200          # 12h; maybe you prefer shorter leases on Wi-Fi

option  subnet      255.255.255.0
option  router      192.168.20.1
option  dns         1.1.1.1 8.8.8.8
option  domain      lan-wlan0.local
option  mtu         1500

# Example captive-portal hint (WPAD), if you host PAC:
# option  252         "http://192.168.20.1/wpad.dat"

# Static leases for known Wi-Fi devices (optional)
# static_lease  00:11:22:33:44:55  192.168.20.60
```

> Notes
>
> * `interface` must be different per file—this is what binds each daemon to one NIC.
> * Use **unique** `lease_file` and `pidfile` paths (otherwise the instances conflict).
> * `option` and `lease` syntax are BusyBox-style (accepts `option xyz ...`).

---

# 3) Minimal wrapper scripts (one per interface)

You can start `udhcpd` directly with a config file, but wrapper scripts make it easy to add checks and logging.

## `/usr/local/sbin/udhcpd-eth0.sh`

```sh
#!/bin/sh
CONF=/etc/udhcpd-eth0.conf
PID=/var/run/udhcpd-eth0.pid

# Ensure interface is up with the right IP
ip link show eth0 >/dev/null 2>&1 || exit 1
ip addr show dev eth0 | grep -q "192\.168\.10\.1/24" || {
  ip addr add 192.168.10.1/24 dev eth0
  ip link set dev eth0 up
}

# Clean stale pid
[ -f "$PID" ] && ! kill -0 "$(cat "$PID")" 2>/dev/null && rm -f "$PID"

# Start in background, syslog logging (-S). Remove -S if you prefer stderr.
exec /sbin/udhcpd -S "$CONF"
```

## `/usr/local/sbin/udhcpd-wlan0.sh`

```sh
#!/bin/sh
CONF=/etc/udhcpd-wlan0.conf
PID=/var/run/udhcpd-wlan0.pid

ip link show wlan0 >/dev/null 2>&1 || exit 1
ip addr show dev wlan0 | grep -q "192\.168\.20\.1/24" || {
  ip addr add 192.168.20.1/24 dev wlan0
  ip link set dev wlan0 up
}

[ -f "$PID" ] && ! kill -0 "$(cat "$PID")" 2>/dev/null && rm -f "$PID"

exec /sbin/udhcpd -S "$CONF"
```

Make them executable:

```sh
chmod +x /usr/local/sbin/udhcpd-eth0.sh /usr/local/sbin/udhcpd-wlan0.sh
```

> Flags you might care about
>
> * `-S` logs to syslog (useful on embedded boxes).
> * `-f` runs in foreground (handy while debugging under a console).

---

# 4) Start & verify both servers

Start both:

```sh
/usr/local/sbin/udhcpd-eth0.sh
/usr/local/sbin/udhcpd-wlan0.sh
```

Verify processes:

```sh
ps | grep udhcpd | grep -v grep
# or
pidof udhcpd
```

Check they bound to different config/PID/lease files:

```sh
ls -l /var/run/udhcpd-*.pid /var/lib/misc/udhcpd-*.leases
```

Tail logs (depends on your syslog):

```sh
logread -f            # BusyBox syslogd/klogd
# or
tail -f /var/log/messages
```

---

# 5) (Optional) Enable routing/NAT to the internet

If this box also routes traffic from these LANs to a WAN (e.g., `ppp0`, `wwan0`, or `eth1`), enable forwarding + NAT:

```sh
# 5.1 Enable IPv4 forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
# Persist across boots:
#   echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf && sysctl -p

# 5.2 Masquerade outbound via your WAN interface (example: ppp0)
WAN=ppp0
iptables -t nat -A POSTROUTING -o "$WAN" -j MASQUERADE
iptables -A FORWARD -i "$WAN" -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o "$WAN" -j ACCEPT
iptables -A FORWARD -i "$WAN" -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i wlan0 -o "$WAN" -j ACCEPT
```

> If you only need DHCP on isolated subnets (no routing), you can skip this.

---

# 6) Start at boot (BusyBox rc.local or classic init script)

## Easiest: `/etc/rc.local`

Add lines **before** the final `exit 0`:

```sh
# Bring up interfaces with static IPs (if your system doesn’t already)
/sbin/ip link set dev eth0 up
/sbin/ip addr add 192.168.10.1/24 dev eth0 || true
/sbin/ip link set dev wlan0 up
/sbin/ip addr add 192.168.20.1/24 dev wlan0 || true

# Start both dhcpd instances
/usr/local/sbin/udhcpd-eth0.sh
/usr/local/sbin/udhcpd-wlan0.sh

# Optional: enable IP forwarding and basic NAT
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -C POSTROUTING -o ppp0 -j MASQUERADE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -o ppp0 -j MASQUERADE
```

Ensure rc.local is executed at boot (on many BusyBox systems it is).

## Alternative: classic `/etc/init.d` scripts (OpenRC/bare-bones)

If you have `start-stop-daemon`:

`/etc/init.d/udhcpd-eth0`

```sh
#!/bin/sh
# simple init script for udhcpd on eth0
case "$1" in
  start)
    start-stop-daemon -S -b -m -p /var/run/udhcpd-eth0.pid \
      --exec /sbin/udhcpd -- -S /etc/udhcpd-eth0.conf
    ;;
  stop)
    start-stop-daemon -K -p /var/run/udhcpd-eth0.pid
    ;;
  restart)
    $0 stop; sleep 1; $0 start
    ;;
  status)
    [ -f /var/run/udhcpd-eth0.pid ] && kill -0 "$(cat /var/run/udhcpd-eth0.pid)" && echo "running" || echo "stopped"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"; exit 1;;
esac
```

Duplicate for `wlan0` with the right paths.

Make executable and add to the appropriate runlevel:

```sh
chmod +x /etc/init.d/udhcpd-eth0 /etc/init.d/udhcpd-wlan0
# OpenRC:
rc-update add udhcpd-eth0 default
rc-update add udhcpd-wlan0 default
```

## If you happen to run systemd (some BusyBox hybrids do)

Create two services:

`/etc/systemd/system/udhcpd@.service`

```ini
[Unit]
Description=BusyBox udhcpd on %I
After=network.target

[Service]
Type=simple
ExecStart=/sbin/udhcpd -S /etc/udhcpd-%i.conf
PIDFile=/var/run/udhcpd-%i.pid
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:

```sh
systemctl daemon-reload
systemctl enable --now udhcpd@eth0.service
systemctl enable --now udhcpd@wlan0.service
```

---

# 7) Testing from a client

On a separate client in each subnet, just request DHCP normally. If you only have this box, you can plug another host into `eth0` and associate a Wi-Fi station to `wlan0`.

For quick sanity tests (from another Linux host on the same L2):

```sh
# As root, force a DHCP request on its NIC (replace NIC):
udhcpc -i <client_nic> -n -q
ip addr show <client_nic>
ip route
cat /etc/resolv.conf
```

On the **server**, watch leases grow:

```sh
hexdump -C /var/lib/misc/udhcpd-eth0.leases
hexdump -C /var/lib/misc/udhcpd-wlan0.leases
```

(These are binary; BusyBox doesn’t ship a pretty printer by default.)

Or sniff for DHCP:

```sh
tcpdump -ni eth0 port 67 or port 68
tcpdump -ni wlan0 port 67 or port 68
```

---

# 8) Advanced: static leases & options you might want

Add more `option` lines as needed:

* **Multiple DNS**:

  ```
  option dns 192.168.10.1 1.1.1.1 8.8.8.8
  ```
* **NTP servers** (option 42):

  ```
  option ntpsrv 192.168.10.1
  ```
* **Classless static routes** (option 121):

  ```
  option classless_static_routes 10.50.0.0/16 192.168.10.1 172.20.5.0/24 192.168.10.254
  ```
* **WPAD / PAC** (option 252):

  ```
  option 252 "http://192.168.10.1/wpad.dat"
  ```
* **TFTP/PXE** (options 66/67):

  ```
  option tftp 192.168.10.1
  option boot_file pxelinux.0
  ```
* **Static reservations**:

  ```
  static_lease aa:bb:cc:dd:ee:f0 192.168.10.50
  static_lease 00:11:22:33:44:55 192.168.20.60
  ```

---

# 9) Debugging checklist

* **Two PIDs?**
  `cat /var/run/udhcpd-eth0.pid /var/run/udhcpd-wlan0.pid`
* **Conflicting files?**
  Ensure `lease_file` and `pidfile` paths are **different** per instance.
* **Interface up with the right IP?**
  `ip addr show dev eth0` should list `192.168.10.1/24`; `wlan0` should list `192.168.20.1/24`.
* **Firewall blocking DHCP?**
  Allow UDP 67/68 on each LAN interface if you have strict rules:

  ```sh
  iptables -A INPUT -i eth0 -p udp --dport 67:68 -j ACCEPT
  iptables -A INPUT -i wlan0 -p udp --dport 67:68 -j ACCEPT
  ```
* **Logs**
  `logread -f` (BusyBox) or `journalctl -u udhcpd@eth0 -f` (systemd) to see DISCOVER/OFFER/REQUEST/ACK flow.
* **Lease pool boundaries**
  Don’t overlap with the interface’s own IP or other statics. Avoid handing out gateway IP.
* **Bridging vs. routing**
  If you later bridge `eth0`+`wlan0`, you’d typically run a **single** DHCP scope on the bridge (e.g., `br0`) instead of two daemons.

---

# 10) Example: full minimal config you can paste & run

1. Create files:

```sh
cat > /etc/udhcpd-eth0.conf <<'EOF'
start           192.168.10.100
end             192.168.10.200
interface       eth0
lease_file      /var/lib/misc/udhcpd-eth0.leases
pidfile         /var/run/udhcpd-eth0.pid
max_leases      101
remaining       yes
offer_time      60
min_lease       120
lease           86400
option  subnet  255.255.255.0
option  router  192.168.10.1
option  dns     1.1.1.1 8.8.8.8
option  domain  lan-eth0.local
EOF

cat > /etc/udhcpd-wlan0.conf <<'EOF'
start           192.168.20.50
end             192.168.20.150
interface       wlan0
lease_file      /var/lib/misc/udhcpd-wlan0.leases
pidfile         /var/run/udhcpd-wlan0.pid
max_leases      101
remaining       yes
offer_time      60
min_lease       120
lease           43200
option  subnet  255.255.255.0
option  router  192.168.20.1
option  dns     1.1.1.1 8.8.8.8
option  domain  lan-wlan0.local
EOF
```

2. Bring up interfaces & start servers:

```sh
ip link set dev eth0 up
ip addr add 192.168.10.1/24 dev eth0

ip link set dev wlan0 up
ip addr add 192.168.20.1/24 dev wlan0

/sbin/udhcpd -S /etc/udhcpd-eth0.conf
/sbin/udhcpd -S /etc/udhcpd-wlan0.conf
```

3. Verify:

```sh
ps | grep udhcpd | grep -v grep
logread | tail
ls -l /var/lib/misc/udhcpd-*.leases /var/run/udhcpd-*.pid
```

---

# 11) Why not one config with two interfaces?

BusyBox `udhcpd` is intentionally small: **one process = one interface**. Trying to list two `interface` lines won’t do what you want. The robust pattern is **two configs + two daemons** (as above). If you ever move to a single L2 domain (bridge `eth0`+`wlan0` into `br0`), then you’d run **one** `udhcpd` instance on `br0` with a **single** scope.

---

# 12) Quick performance & reliability tips

* Keep lease ranges narrow and appropriate for expected clients.
* Use `remaining yes` so clients get T1/T2 hints and renew smoothly.
* Prefer a local DNS forwarder (e.g., `dnsmasq` or `unbound`) and point `option dns` to your router IP for lower latency.
* If Wi-Fi clients churn, shorter leases on `wlan0` help reclaim addresses quickly.
* Consider reserving addresses with `static_lease` for fixed gear (APs, cameras, printers).

---

If you want, tell me your existing network (WAN interface, whether you bridge `wlan0`, any firewall you’re running), and I’ll tailor the exact config and boot scripts to your box.
