#!/bin/bash
# DHCP Server Display Diagnostic Script
# Collects information to diagnose why DHCP SERVER STATUS isn't showing in 'net' command

echo "========================================"
echo "DHCP Server Display Diagnostics"
echo "========================================"
echo ""

echo "=== 1. Network Interfaces Configuration ==="
if [ -f /etc/network/interfaces ]; then
    cat /etc/network/interfaces
else
    echo "File not found: /etc/network/interfaces"
fi
echo ""

echo "=== 2. DHCP Server Config for eth0 ==="
if [ -f /etc/network/udhcpd.eth0.conf ]; then
    cat /etc/network/udhcpd.eth0.conf
else
    echo "File not found: /etc/network/udhcpd.eth0.conf"
fi
echo ""

echo "=== 3. DHCP Lease File Status ==="
if [ -f /var/lib/misc/udhcpd.eth0.leases ]; then
    echo "Lease file exists:"
    ls -la /var/lib/misc/udhcpd.eth0.leases
    echo ""
    echo "Current leases:"
    dumpleases -f /var/lib/misc/udhcpd.eth0.leases 2>/dev/null || echo "dumpleases command failed or no leases"
else
    echo "File not found: /var/lib/misc/udhcpd.eth0.leases"
fi
echo ""

echo "=== 4. udhcpd Service Run Script ==="
if [ -f /usr/qk/etc/sv/udhcpd/run ]; then
    cat /usr/qk/etc/sv/udhcpd/run
else
    echo "File not found: /usr/qk/etc/sv/udhcpd/run"
fi
echo ""

echo "=== 5. udhcpd Service Finish Script ==="
if [ -f /usr/qk/etc/sv/udhcpd/finish ]; then
    cat /usr/qk/etc/sv/udhcpd/finish
else
    echo "File not found: /usr/qk/etc/sv/udhcpd/finish"
fi
echo ""

echo "=== 6. udhcpd Service Link Status ==="
if [ -L /etc/service/udhcpd ] || [ -d /etc/service/udhcpd ]; then
    ls -la /etc/service/udhcpd
elif [ -L /service/udhcpd ] || [ -d /service/udhcpd ]; then
    ls -la /service/udhcpd
else
    echo "udhcpd service not linked in /etc/service or /service"
fi
echo ""

echo "=== 7. udhcpd Process Status ==="
ps aux | grep udhcpd | grep -v grep
if [ $? -ne 0 ]; then
    echo "No udhcpd process running"
fi
echo ""

echo "=== 8. eth0 Current IP Configuration ==="
ifconfig eth0 2>/dev/null || ip addr show eth0 2>/dev/null || echo "eth0 interface not found"
echo ""

echo "=== 9. Migration and Config Logs ==="
echo "Checking for migration messages in logs..."
grep -i "migration\|use_dhcp_server" /var/log/messages 2>/dev/null | tail -20 || echo "No /var/log/messages"
grep -i "migration\|use_dhcp_server" /var/log/syslog 2>/dev/null | tail -20 || echo "No /var/log/syslog"
echo ""

echo "=== 10. Network Config State File ==="
if [ -f /usr/qk/etc/sv/network_config.state ]; then
    echo "State file exists:"
    cat /usr/qk/etc/sv/network_config.state
else
    echo "File not found: /usr/qk/etc/sv/network_config.state"
fi
echo ""

echo "=== 11. Device Config Binary Location ==="
ls -la /usr/qk/etc/sv/memory_test/*.cfg.bin 2>/dev/null || echo "No .cfg.bin files found"
echo ""

echo "=== 12. Service Directory Structure ==="
echo "Checking /usr/qk/etc/sv/udhcpd directory:"
ls -laR /usr/qk/etc/sv/udhcpd 2>/dev/null || echo "Directory not found"
echo ""

echo "=== 13. PID Files ==="
ls -la /var/run/udhcpd*.pid 2>/dev/null || echo "No udhcpd PID files found"
echo ""

echo "========================================"
echo "Diagnostic collection complete"
echo "========================================"
