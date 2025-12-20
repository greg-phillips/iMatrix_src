#!/bin/sh
# Diagnostic script to identify timing issues in net command interface status
# Date: 2025-12-18

echo "=== Net Interface Link Status Timing Diagnostic ==="
echo ""

# Function to print timestamp and run command
run_timed() {
    cmd="$1"
    desc="$2"
    echo "--- $desc ---"
    echo "CMD: $cmd"
    echo "START: $(date '+%H:%M:%S.%3N' 2>/dev/null || date '+%H:%M:%S')"
    eval "$cmd"
    ret=$?
    echo "END:   $(date '+%H:%M:%S.%3N' 2>/dev/null || date '+%H:%M:%S') (exit=$ret)"
    echo ""
}

echo "=== ETH0 Tests ==="
run_timed "cat /sys/class/net/eth0/carrier 2>/dev/null" "eth0 carrier check"
run_timed "cat /sys/class/net/eth0/operstate 2>/dev/null" "eth0 operstate"
run_timed "ethtool eth0 2>/dev/null | grep -E 'Speed:|Link detected:'" "ethtool eth0 (full)"
run_timed "ethtool eth0 2>/dev/null | grep 'Speed:' | awk '{print \$2}'" "ethtool eth0 speed only"

echo "=== WLAN0 Tests ==="
run_timed "cat /sys/class/net/wlan0/carrier 2>/dev/null" "wlan0 carrier check"
run_timed "cat /sys/class/net/wlan0/operstate 2>/dev/null" "wlan0 operstate"
run_timed "wpa_cli -i wlan0 status 2>/dev/null | grep '^wpa_state='" "wpa_cli wpa_state"
run_timed "wpa_cli -i wlan0 status 2>/dev/null | grep '^ssid=' | cut -d= -f2" "wpa_cli ssid"
run_timed "iw dev wlan0 link 2>/dev/null | grep 'SSID:'" "iw wlan0 SSID"
run_timed "iw dev wlan0 link 2>/dev/null" "iw wlan0 link (full)"

echo "=== PPP0 Tests ==="
run_timed "cat /sys/class/net/ppp0/carrier 2>/dev/null" "ppp0 carrier check"
run_timed "pgrep -x pppd" "pppd running check"
run_timed "ip link show ppp0 2>/dev/null" "ppp0 link show"

echo "=== IP Address Checks ==="
run_timed "ip addr show eth0 2>/dev/null | grep 'inet '" "eth0 IP address"
run_timed "ip addr show wlan0 2>/dev/null | grep 'inet '" "wlan0 IP address"
run_timed "ip addr show ppp0 2>/dev/null | grep 'inet '" "ppp0 IP address"

echo "=== Complete ==="
echo "Total script finished at: $(date '+%H:%M:%S.%3N' 2>/dev/null || date '+%H:%M:%S')"
