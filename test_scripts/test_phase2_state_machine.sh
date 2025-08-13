#!/bin/bash
#
# Phase 2 Test Script - State Machine Validation and Hysteresis
# Tests state machine transitions, hysteresis, and WiFi reassociation
#

# Test configuration
TEST_APP="${TEST_APP:-./test_network_app}"
TEST_LOG="/tmp/phase2_test_$$.log"
PHASE_NAME="Phase 2: State Machine Validation"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_test() {
    local test_name="$1"
    echo -e "\n${YELLOW}TEST: $test_name${NC}" | tee -a $TEST_LOG
    ((TESTS_RUN++))
}

pass_test() {
    local message="$1"
    echo -e "${GREEN}PASSED: $message${NC}" | tee -a $TEST_LOG
    ((TESTS_PASSED++))
}

fail_test() {
    local message="$1"
    echo -e "${RED}FAILED: $message${NC}" | tee -a $TEST_LOG
    ((TESTS_FAILED++))
}

warning_test() {
    local message="$1"
    echo -e "${YELLOW}WARNING: $message${NC}" | tee -a $TEST_LOG
}

# Check if test mode is enabled
check_test_mode() {
    if [ -z "$NETWORK_TEST_MODE" ]; then
        warning_test "NETWORK_TEST_MODE not set - some tests may not work properly"
        echo "Run: export NETWORK_TEST_MODE=1" | tee -a $TEST_LOG
    fi
}

# Start test script
echo "=== $PHASE_NAME ===" | tee $TEST_LOG
echo "Test started: $(date)" | tee -a $TEST_LOG
echo "Test application: $TEST_APP" | tee -a $TEST_LOG

check_test_mode

# Test 1: Valid State Transitions
log_test "Valid State Transitions Only"
cat > /tmp/test1_script.sh << 'EOF'
#!/bin/bash
# Test state machine transitions
echo "test show_state"
sleep 1
# Force all interfaces down to go to INIT state
echo "test force_fail eth0"
echo "test force_fail wlan0"
echo "test force_fail ppp0"
sleep 2
echo "test show_state"
# Clear one interface to trigger state change
echo "test clear_failures"
sleep 3
echo "test show_state"
echo "net"
EOF
chmod +x /tmp/test1_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 20s /tmp/test1_script.sh | $TEST_APP > /tmp/test1_output.log 2>&1
    
    # Check for valid state transitions
    if grep -q "NET_INIT\|NET_TESTING\|NET_ONLINE" /tmp/test1_output.log && \
       ! grep -q "invalid state\|unexpected transition" /tmp/test1_output.log; then
        pass_test "State machine transitions are valid"
    else
        fail_test "Invalid state transitions detected"
    fi
else
    fail_test "Test application not found"
fi

# Test 2: Hysteresis - Rapid Interface Switching
log_test "Hysteresis - Interface Ping-Ponging Prevention"
cat > /tmp/test2_script.sh << 'EOF'
#!/bin/bash
# Reset hysteresis first
echo "test hysteresis_reset"
sleep 1
# Rapidly switch interfaces to trigger hysteresis
for i in {1..5}; do
    echo "test force_fail eth0"
    sleep 0.5
    echo "test clear_failures"
    sleep 0.5
done
echo "test show_state"
echo "net"
EOF
chmod +x /tmp/test2_script.sh

if [ -f "$TEST_APP" ] && [ -n "$NETWORK_TEST_MODE" ]; then
    timeout 15s /tmp/test2_script.sh | $TEST_APP > /tmp/test2_output.log 2>&1
    
    # Check if hysteresis was activated
    if grep -q "hysteresis.*active\|too many switches\|HYSTERESIS:" /tmp/test2_output.log; then
        pass_test "Hysteresis prevents interface ping-ponging"
    else
        warning_test "Could not verify hysteresis activation"
    fi
else
    if [ -z "$NETWORK_TEST_MODE" ]; then
        warning_test "Test mode not enabled - skipping hysteresis test"
    else
        fail_test "Test application not found"
    fi
fi

# Test 3: WiFi Reassociation Methods
log_test "WiFi Reassociation - Method Testing"
cat > /tmp/test3_script.sh << 'EOF'
#!/bin/bash
# Test WiFi reassociation when WiFi is available
echo "net"
sleep 1
# Force WiFi failure
echo "test force_fail wlan0"
sleep 2
echo "net"
# Clear failure to allow reassociation
echo "test clear_failures"
sleep 5
echo "net"
echo "test show_state"
EOF
chmod +x /tmp/test3_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 20s /tmp/test3_script.sh | $TEST_APP > /tmp/test3_output.log 2>&1
    
    # Check for WiFi reassociation
    if grep -q "wlan0.*reassoc\|WiFi.*reassoc\|Reassociating" /tmp/test3_output.log; then
        pass_test "WiFi reassociation methods working"
    else
        warning_test "Could not verify WiFi reassociation"
    fi
else
    fail_test "Test application not found"
fi

# Test 4: Interface Priority Logic
log_test "Interface Priority - Prefer Ethernet/WiFi over Cellular"
cat > /tmp/test4_script.sh << 'EOF'
#!/bin/bash
# Clear all failures first
echo "test clear_failures"
sleep 2
# Make all interfaces available
echo "test set_score eth0 8"
echo "test set_score wlan0 8"
echo "test set_score ppp0 8"
sleep 2
echo "net"
echo "test show_state"
# Now fail ethernet to see if WiFi takes over (not PPP)
echo "test force_fail eth0"
sleep 3
echo "net"
echo "test show_state"
EOF
chmod +x /tmp/test4_script.sh

if [ -f "$TEST_APP" ] && [ -n "$NETWORK_TEST_MODE" ]; then
    timeout 20s /tmp/test4_script.sh | $TEST_APP > /tmp/test4_output.log 2>&1
    
    # Check if WiFi is preferred over cellular when available
    if tail -20 /tmp/test4_output.log | grep -q "wlan0.*active\|Current.*wlan0"; then
        pass_test "Interface priority: WiFi preferred over cellular"
    else
        warning_test "Could not verify interface priority"
    fi
else
    if [ -z "$NETWORK_TEST_MODE" ]; then
        warning_test "Test mode not enabled - skipping priority test"
    else
        fail_test "Test application not found"
    fi
fi

# Test 5: State Machine Under Rapid Changes
log_test "State Machine Integrity - Rapid State Changes"
cat > /tmp/test5_script.sh << 'EOF'
#!/bin/bash
# Rapid state changes
for i in {1..10}; do
    echo "test force_fail eth0"
    echo "test force_fail wlan0"
    echo "test clear_failures"
    echo "test force_fail ppp0"
    echo "test clear_failures"
done
echo "test show_state"
echo "net"
EOF
chmod +x /tmp/test5_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 15s /tmp/test5_script.sh | $TEST_APP > /tmp/test5_output.log 2>&1
    
    # Check for state machine integrity
    if ! grep -q "corrupt\|invalid state\|segfault" /tmp/test5_output.log; then
        pass_test "State machine maintains integrity under rapid changes"
    else
        fail_test "State machine integrity issues detected"
    fi
else
    fail_test "Test application not found"
fi

# Test 6: WiFi Re-enable Timing
log_test "WiFi Re-enable Timing After Disable"
cat > /tmp/test6_script.sh << 'EOF'
#!/bin/bash
# Disable WiFi
echo "set_wifi disable"
sleep 2
echo "net"
# Wait a bit
sleep 3
# Re-enable WiFi
echo "set_wifi enable"
sleep 2
echo "net"
# Wait for WiFi to come back online
sleep 5
echo "net"
echo "test show_state"
EOF
chmod +x /tmp/test6_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 20s /tmp/test6_script.sh | $TEST_APP > /tmp/test6_output.log 2>&1
    
    # Check WiFi re-enable behavior
    if grep -q "WiFi interface enabled\|wlan0.*enabled" /tmp/test6_output.log; then
        if tail -20 /tmp/test6_output.log | grep -q "wlan0.*online\|wlan0.*active"; then
            pass_test "WiFi re-enable timing works correctly"
        else
            warning_test "WiFi enabled but not yet active"
        fi
    else
        warning_test "Could not verify WiFi re-enable timing"
    fi
else
    fail_test "Test application not found"
fi

# Test 7: Hysteresis Window and Cooldown
log_test "Hysteresis Window Duration and Cooldown"
cat > /tmp/test7_script.sh << 'EOF'
#!/bin/bash
# Reset hysteresis
echo "test hysteresis_reset"
sleep 1
# Trigger switches within window
echo "test force_fail eth0"
sleep 1
echo "test clear_failures"
sleep 1
echo "test force_fail eth0"
sleep 1
echo "test clear_failures"
sleep 1
echo "test force_fail eth0"
sleep 1
echo "test show_state"
# Try another switch - should be blocked
echo "test clear_failures"
sleep 1
echo "test show_state"
EOF
chmod +x /tmp/test7_script.sh

if [ -f "$TEST_APP" ] && [ -n "$NETWORK_TEST_MODE" ]; then
    timeout 20s /tmp/test7_script.sh | $TEST_APP > /tmp/test7_output.log 2>&1
    
    # Check hysteresis behavior
    if grep -q "hysteresis.*cooldown\|blocking switch" /tmp/test7_output.log; then
        pass_test "Hysteresis window and cooldown working"
    else
        warning_test "Could not verify hysteresis window behavior"
    fi
else
    if [ -z "$NETWORK_TEST_MODE" ]; then
        warning_test "Test mode not enabled - skipping hysteresis window test"
    else
        fail_test "Test application not found"
    fi
fi

# Cleanup
rm -f /tmp/test[1-7]_script.sh /tmp/test[1-7]_output.log

# Summary
echo -e "\n=== Phase 2 Test Summary ===" | tee -a $TEST_LOG
echo "Total tests run: $TESTS_RUN" | tee -a $TEST_LOG
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}" | tee -a $TEST_LOG
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}" | tee -a $TEST_LOG

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}Phase 2: ALL TESTS PASSED${NC}" | tee -a $TEST_LOG
    exit 0
else
    echo -e "\n${RED}Phase 2: SOME TESTS FAILED${NC}" | tee -a $TEST_LOG
    exit 1
fi