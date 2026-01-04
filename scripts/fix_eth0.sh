#!/bin/sh
#
# fix_eth0.sh - Reset eth0 interface on QConnect device
#
# Use this script when eth0 fails to get its IP address after boot.
# Can be run directly on the device or pushed via SCP.
#
# Usage: ./fix_eth0.sh
#

ETH0_IP="192.168.7.1"
ETH0_MASK="24"

echo "=== eth0 Fix Script ==="
echo ""

# Show current state
echo "Current eth0 state:"
ip addr show eth0 2>/dev/null | grep -E "(state|inet )"
echo ""

# Check if eth0 exists
if ! ip link show eth0 >/dev/null 2>&1; then
    echo "ERROR: eth0 interface not found"
    exit 1
fi

# Check if IP is already correctly assigned
CURRENT_IP=$(ip addr show eth0 2>/dev/null | grep "inet " | awk '{print $2}')
if [ "$CURRENT_IP" = "${ETH0_IP}/${ETH0_MASK}" ]; then
    echo "eth0 already has correct IP: $CURRENT_IP"
    echo "No fix needed."
    exit 0
fi

echo "Fixing eth0 interface..."

# Flush existing addresses
echo "  Flushing old addresses..."
ip addr flush dev eth0

# Add the correct IP
echo "  Adding ${ETH0_IP}/${ETH0_MASK}..."
if ip addr add ${ETH0_IP}/${ETH0_MASK} dev eth0; then
    echo "  Success!"
else
    echo "  ERROR: Failed to add IP address"
    exit 1
fi

# Ensure interface is up
ip link set eth0 up

# Verify
echo ""
echo "New eth0 state:"
ip addr show eth0 | grep -E "(state|inet )"

echo ""
echo "=== Fix complete ==="
