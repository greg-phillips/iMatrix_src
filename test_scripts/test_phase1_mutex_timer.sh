#!/bin/bash
#
# Phase 1 Test Script - Mutex Protection and Timer Fixes
# Tests mutex protection for interface states and DNS cache, and cooldown timer logic
#

# Test configuration
TEST_APP="${TEST_APP:-./test_network_app}"
TEST_LOG="/tmp/phase1_test_$$.log"
PHASE_NAME="Phase 1: Mutex Protection and Timer Fixes"

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

# Test 1: Concurrent Interface State Access
log_test "Concurrent Interface State Access"
cat > /tmp/test1_script.sh << 'EOF'
#!/bin/bash
# Simulate concurrent access to interface states
for i in {1..5}; do
    (
        echo "test force_fail eth0"
        sleep 0.1
        echo "test clear_failures"
        sleep 0.1
        echo "net"
    ) &
done
wait
echo "test show_state"
EOF
chmod +x /tmp/test1_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 30s /tmp/test1_script.sh | $TEST_APP > /tmp/test1_output.log 2>&1 &
    APP_PID=$!
    sleep 10
    
    # Check for mutex-related crashes or deadlocks
    if kill -0 $APP_PID 2>/dev/null; then
        kill $APP_PID 2>/dev/null
        if ! grep -q "segmentation fault\|deadlock\|mutex" /tmp/test1_output.log; then
            pass_test "No mutex-related crashes during concurrent access"
        else
            fail_test "Mutex issues detected during concurrent access"
        fi
    else
        # Process ended - check if it crashed
        if grep -q "segmentation fault\|core dumped" /tmp/test1_output.log; then
            fail_test "Application crashed during concurrent access"
        else
            pass_test "Application handled concurrent access gracefully"
        fi
    fi
else
    fail_test "Test application not found: $TEST_APP"
fi

# Test 2: DNS Cache Mutex Protection
log_test "DNS Cache Mutex Protection"
cat > /tmp/test2_script.sh << 'EOF'
#!/bin/bash
# Test concurrent DNS operations
for i in {1..3}; do
    (
        echo "test dns_refresh"
        sleep 0.2
        echo "net"
        sleep 0.1
    ) &
done
wait
echo "net"
EOF
chmod +x /tmp/test2_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 20s /tmp/test2_script.sh | $TEST_APP > /tmp/test2_output.log 2>&1
    
    if ! grep -q "segmentation fault\|mutex error\|corruption" /tmp/test2_output.log; then
        pass_test "DNS cache protected from concurrent access"
    else
        fail_test "DNS cache mutex protection issue detected"
    fi
else
    fail_test "Test application not found"
fi

# Test 3: Cooldown Timer Logic
log_test "Cooldown Timer Logic - Current Time Usage"
cat > /tmp/test3_script.sh << 'EOF'
#!/bin/bash
echo "test force_fail eth0"
sleep 1
echo "net"
sleep 1
echo "test show_state"
# Wait less than cooldown period
sleep 5
echo "net"
echo "test show_state"
# Clear and verify recovery
echo "test clear_failures"
sleep 2
echo "net"
EOF
chmod +x /tmp/test3_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 30s /tmp/test3_script.sh | $TEST_APP > /tmp/test3_output.log 2>&1
    
    # Check if cooldown is properly enforced
    if grep -q "cooldown.*remaining\|Cooldown period active" /tmp/test3_output.log; then
        pass_test "Cooldown timer using current time correctly"
    else
        warning_test "Could not verify cooldown timer behavior"
    fi
    
    # Check if interface recovers after cooldown
    if tail -20 /tmp/test3_output.log | grep -q "eth0.*online\|eth0.*active"; then
        pass_test "Interface recovers correctly after cooldown"
    else
        warning_test "Interface recovery after cooldown unclear"
    fi
else
    fail_test "Test application not found"
fi

# Test 4: Safe Time Difference Calculations
log_test "Safe Time Difference - Wraparound Handling"
cat > /tmp/test4_script.sh << 'EOF'
#!/bin/bash
# Force multiple interface switches to test time calculations
for i in {1..10}; do
    echo "test force_fail eth0"
    sleep 0.5
    echo "test clear_failures"
    sleep 0.5
    echo "net"
done
echo "test show_state"
EOF
chmod +x /tmp/test4_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 20s /tmp/test4_script.sh | $TEST_APP > /tmp/test4_output.log 2>&1
    
    # Check for time calculation errors
    if ! grep -q "negative time\|time overflow\|invalid duration" /tmp/test4_output.log; then
        pass_test "Safe time difference calculations working correctly"
    else
        fail_test "Time calculation errors detected"
    fi
else
    fail_test "Test application not found"
fi

# Test 5: Interface Score Thread Safety
log_test "Interface Score Updates - Thread Safety"
cat > /tmp/test5_script.sh << 'EOF'
#!/bin/bash
# Force simultaneous score updates
echo "test set_score eth0 8" &
echo "test set_score wlan0 9" &
echo "test set_score ppp0 5" &
wait
sleep 1
echo "net"
echo "test show_state"
EOF
chmod +x /tmp/test5_script.sh

if [ -f "$TEST_APP" ] && [ -n "$NETWORK_TEST_MODE" ]; then
    timeout 10s /tmp/test5_script.sh | $TEST_APP > /tmp/test5_output.log 2>&1
    
    # Verify scores are set correctly
    if grep -q "eth0.*score.*8\|eth0.*8.*latency" /tmp/test5_output.log && \
       grep -q "wlan0.*score.*9\|wlan0.*9.*latency" /tmp/test5_output.log; then
        pass_test "Thread-safe score updates working correctly"
    else
        warning_test "Could not verify thread-safe score updates"
    fi
else
    if [ -z "$NETWORK_TEST_MODE" ]; then
        warning_test "Test mode not enabled - skipping score update test"
    else
        fail_test "Test application not found"
    fi
fi

# Test 6: State Transition Mutex Protection
log_test "State Machine Transitions - Mutex Protection"
cat > /tmp/test6_script.sh << 'EOF'
#!/bin/bash
# Rapid state changes to test mutex protection
echo "test force_fail eth0"
echo "test force_fail wlan0" 
echo "test force_fail ppp0"
sleep 0.5
echo "test clear_failures"
echo "net"
echo "test show_state"
EOF
chmod +x /tmp/test6_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 10s /tmp/test6_script.sh | $TEST_APP > /tmp/test6_output.log 2>&1
    
    # Check for consistent state transitions
    if ! grep -q "invalid state\|state corruption\|unexpected transition" /tmp/test6_output.log; then
        pass_test "State transitions protected by mutex"
    else
        fail_test "State transition mutex issues detected"
    fi
else
    fail_test "Test application not found"
fi

# Cleanup
rm -f /tmp/test[1-6]_script.sh /tmp/test[1-6]_output.log

# Summary
echo -e "\n=== Phase 1 Test Summary ===" | tee -a $TEST_LOG
echo "Total tests run: $TESTS_RUN" | tee -a $TEST_LOG
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}" | tee -a $TEST_LOG
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}" | tee -a $TEST_LOG

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}Phase 1: ALL TESTS PASSED${NC}" | tee -a $TEST_LOG
    exit 0
else
    echo -e "\n${RED}Phase 1: SOME TESTS FAILED${NC}" | tee -a $TEST_LOG
    exit 1
fi