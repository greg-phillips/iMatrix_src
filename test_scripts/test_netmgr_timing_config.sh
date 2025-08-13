#!/bin/bash

# Test script for network manager timing configuration persistence
# This script verifies that:
# 1. Default values are initialized on first boot
# 2. CLI commands work to view and modify settings
# 3. Settings persist across reboots

echo "=== Network Manager Timing Configuration Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test application path
TEST_APP="./tiered_storage_test"

# Check if test app exists
if [ ! -f "$TEST_APP" ]; then
    echo -e "${RED}Error: Test application $TEST_APP not found${NC}"
    echo "Please build the test application first"
    exit 1
fi

# Function to send command via PTY
send_command() {
    local cmd="$1"
    echo -e "\n${YELLOW}Sending command: $cmd${NC}"
    echo "$cmd" > /tmp/test_pty_input
    sleep 1
}

# Function to check output for expected string
check_output() {
    local expected="$1"
    local timeout="${2:-5}"
    local found=0
    
    for i in $(seq 1 $timeout); do
        if grep -q "$expected" /tmp/test_pty_output 2>/dev/null; then
            found=1
            break
        fi
        sleep 1
    done
    
    if [ $found -eq 1 ]; then
        echo -e "${GREEN}✓ Found: $expected${NC}"
        return 0
    else
        echo -e "${RED}✗ Not found: $expected${NC}"
        return 1
    fi
}

# Clean up any previous test files
rm -f /tmp/test_pty_*

# Start the test application with PTY capture
echo "Starting test application..."
script -f -c "$TEST_APP" /tmp/test_pty_output &
TEST_PID=$!
sleep 3

# Create input pipe
mkfifo /tmp/test_pty_input
exec 3>/tmp/test_pty_input

# Test 1: Check initial timing configuration
echo -e "\n${YELLOW}Test 1: Checking initial timing configuration${NC}"
send_command "netmgr_timing"
sleep 2

# Check for default values or initialization message
if check_output "Network Manager Timing Configuration" || check_output "initializing defaults"; then
    echo -e "${GREEN}✓ Test 1 passed: Configuration command works${NC}"
else
    echo -e "${RED}✗ Test 1 failed: Configuration command not working${NC}"
fi

# Test 2: Modify a timing parameter
echo -e "\n${YELLOW}Test 2: Modifying eth0 cooldown time${NC}"
send_command "netmgr_set_timing eth0_cooldown 45"
sleep 2

if check_output "set to 45 and saved"; then
    echo -e "${GREEN}✓ Test 2 passed: Parameter modification works${NC}"
else
    echo -e "${RED}✗ Test 2 failed: Parameter modification failed${NC}"
fi

# Test 3: Verify the change
echo -e "\n${YELLOW}Test 3: Verifying the change${NC}"
send_command "netmgr_timing"
sleep 2

if check_output "Ethernet (eth0):     45 seconds"; then
    echo -e "${GREEN}✓ Test 3 passed: Parameter change verified${NC}"
else
    echo -e "${RED}✗ Test 3 failed: Parameter change not reflected${NC}"
fi

# Test 4: Modify multiple parameters
echo -e "\n${YELLOW}Test 4: Modifying multiple parameters${NC}"
send_command "netmgr_set_timing wifi_cooldown 20"
sleep 1
send_command "netmgr_set_timing ping_count 5"
sleep 1
send_command "netmgr_set_timing hysteresis_window 90"
sleep 1

# Verify all changes
send_command "netmgr_timing"
sleep 2

echo "Checking modified values..."
if check_output "WiFi (wlan0):        20 seconds" && \
   check_output "Ping count:          5" && \
   check_output "Window duration:     90 seconds"; then
    echo -e "${GREEN}✓ Test 4 passed: Multiple parameter changes work${NC}"
else
    echo -e "${RED}✗ Test 4 failed: Some parameter changes not reflected${NC}"
fi

# Test 5: Test invalid parameters
echo -e "\n${YELLOW}Test 5: Testing invalid parameters${NC}"
send_command "netmgr_set_timing eth0_cooldown 5000"  # Too large
sleep 1

if check_output "must be 1-3600 seconds"; then
    echo -e "${GREEN}✓ Test 5 passed: Invalid parameter rejected${NC}"
else
    echo -e "${RED}✗ Test 5 failed: Invalid parameter not properly validated${NC}"
fi

# Test 6: Simulate reboot to test persistence
echo -e "\n${YELLOW}Test 6: Testing configuration persistence (simulated)${NC}"
echo "Saving current configuration state..."
send_command "netmgr_timing"
sleep 2

# Extract current values from output
ETH0_VAL=$(grep -oP "Ethernet \(eth0\):\s+\K\d+" /tmp/test_pty_output | tail -1)
WIFI_VAL=$(grep -oP "WiFi \(wlan0\):\s+\K\d+" /tmp/test_pty_output | tail -1)
PING_VAL=$(grep -oP "Ping count:\s+\K\d+" /tmp/test_pty_output | tail -1)

echo "Current values: eth0=$ETH0_VAL, wifi=$WIFI_VAL, ping_count=$PING_VAL"

# Clean up
echo -e "\n${YELLOW}Cleaning up...${NC}"
send_command "exit"
sleep 1

# Kill the test application
kill $TEST_PID 2>/dev/null
wait $TEST_PID 2>/dev/null

# Close input pipe
exec 3>&-
rm -f /tmp/test_pty_*

echo -e "\n${YELLOW}=== Test Summary ===${NC}"
echo "Network timing configuration tests completed."
echo ""
echo "To test actual persistence across reboots:"
echo "1. Run the application and note the timing values"
echo "2. Reboot the system"
echo "3. Run the application again and verify the values are preserved"
echo ""
echo "Example commands to use:"
echo "  netmgr_timing              - View current configuration"
echo "  netmgr_set_timing <param> <value> - Modify a parameter"
echo ""
echo "Parameters: eth0_cooldown, wifi_cooldown, ppp_cooldown, ppp_wait,"
echo "           max_state, online_check, ping_interval, ping_timeout,"
echo "           ping_count, hysteresis_switches, hysteresis_window,"
echo "           hysteresis_cooldown, wifi_scan_wait, wifi_dhcp_wait"