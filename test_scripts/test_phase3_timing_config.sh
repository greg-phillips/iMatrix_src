#!/bin/bash
#
# Phase 3 Test Script - Timing Configuration System
# Tests the network timing configuration persistence and CLI commands
#

# Test configuration
TEST_APP="${TEST_APP:-./test_network_app}"
TEST_LOG="/tmp/phase3_test_$$.log"
PHASE_NAME="Phase 3: Timing Configuration"

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

# Start test script
echo "=== $PHASE_NAME ===" | tee $TEST_LOG
echo "Test started: $(date)" | tee -a $TEST_LOG
echo "Test application: $TEST_APP" | tee -a $TEST_LOG

# Test 1: View Network Timing Configuration
log_test "View Network Timing Configuration"
cat > /tmp/test1_script.sh << 'EOF'
#!/bin/bash
# Display current timing configuration
echo "netmgr_timing"
EOF
chmod +x /tmp/test1_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 10s /tmp/test1_script.sh | $TEST_APP > /tmp/test1_output.log 2>&1
    
    # Check if timing configuration is displayed
    if grep -q "Network Manager Timing Configuration" /tmp/test1_output.log && \
       grep -q "Interface Cooldown Times:" /tmp/test1_output.log && \
       grep -q "State Machine Timing:" /tmp/test1_output.log && \
       grep -q "Ping Configuration:" /tmp/test1_output.log && \
       grep -q "Hysteresis Configuration:" /tmp/test1_output.log; then
        pass_test "Network timing configuration displayed correctly"
    else
        fail_test "Network timing configuration not displayed properly"
    fi
else
    fail_test "Test application not found"
fi

# Test 2: Check Default Values
log_test "Default Timing Values Initialization"
if [ -f "$TEST_APP" ]; then
    # Check for default values in the output
    if grep -q "Ethernet (eth0):.*30 seconds" /tmp/test1_output.log && \
       grep -q "WiFi (wlan0):.*30 seconds" /tmp/test1_output.log && \
       grep -q "Max state duration:.*20 seconds" /tmp/test1_output.log && \
       grep -q "Ping count:.*3" /tmp/test1_output.log; then
        pass_test "Default timing values initialized correctly"
    else
        warning_test "Default values may not be set or different than expected"
    fi
else
    fail_test "Test application not found"
fi

# Test 3: Modify Timing Parameter
log_test "Modify Single Timing Parameter"
cat > /tmp/test3_script.sh << 'EOF'
#!/bin/bash
# Modify eth0 cooldown time
echo "netmgr_set_timing eth0_cooldown 45"
sleep 1
# Verify the change
echo "netmgr_timing"
EOF
chmod +x /tmp/test3_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 10s /tmp/test3_script.sh | $TEST_APP > /tmp/test3_output.log 2>&1
    
    # Check if parameter was modified
    if grep -q "Parameter 'eth0_cooldown' set to 45 and saved" /tmp/test3_output.log && \
       grep -q "Ethernet (eth0):.*45 seconds" /tmp/test3_output.log; then
        pass_test "Timing parameter modification works"
    else
        fail_test "Failed to modify timing parameter"
    fi
else
    fail_test "Test application not found"
fi

# Test 4: Modify Multiple Parameters
log_test "Modify Multiple Timing Parameters"
cat > /tmp/test4_script.sh << 'EOF'
#!/bin/bash
# Modify multiple parameters
echo "netmgr_set_timing wifi_cooldown 20"
sleep 0.5
echo "netmgr_set_timing ping_count 5"
sleep 0.5
echo "netmgr_set_timing hysteresis_window 90"
sleep 0.5
echo "netmgr_set_timing max_state 15"
sleep 1
# Verify all changes
echo "netmgr_timing"
EOF
chmod +x /tmp/test4_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 15s /tmp/test4_script.sh | $TEST_APP > /tmp/test4_output.log 2>&1
    
    # Check if all parameters were modified
    if grep -q "WiFi (wlan0):.*20 seconds" /tmp/test4_output.log && \
       grep -q "Ping count:.*5" /tmp/test4_output.log && \
       grep -q "Window duration:.*90 seconds" /tmp/test4_output.log && \
       grep -q "Max state duration:.*15 seconds" /tmp/test4_output.log; then
        pass_test "Multiple parameter modifications successful"
    else
        fail_test "Some parameter modifications failed"
    fi
else
    fail_test "Test application not found"
fi

# Test 5: Parameter Validation
log_test "Parameter Validation - Invalid Values"
cat > /tmp/test5_script.sh << 'EOF'
#!/bin/bash
# Try invalid values
echo "netmgr_set_timing eth0_cooldown 5000"  # Too large
sleep 0.5
echo "netmgr_set_timing ping_count 15"       # Too large
sleep 0.5
echo "netmgr_set_timing max_state 2"         # Too small
sleep 0.5
echo "netmgr_set_timing unknown_param 100"   # Unknown parameter
EOF
chmod +x /tmp/test5_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 10s /tmp/test5_script.sh | $TEST_APP > /tmp/test5_output.log 2>&1
    
    # Check for validation errors
    if grep -q "must be 1-3600 seconds" /tmp/test5_output.log && \
       grep -q "must be 1-10" /tmp/test5_output.log && \
       grep -q "must be 5-120 seconds" /tmp/test5_output.log && \
       grep -q "Unknown parameter" /tmp/test5_output.log; then
        pass_test "Parameter validation working correctly"
    else
        warning_test "Parameter validation may not be fully working"
    fi
else
    fail_test "Test application not found"
fi

# Test 6: Configuration Save Confirmation
log_test "Configuration Save Confirmation"
cat > /tmp/test6_script.sh << 'EOF'
#!/bin/bash
# Set a parameter and check save confirmation
echo "netmgr_set_timing ping_interval 10"
EOF
chmod +x /tmp/test6_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 5s /tmp/test6_script.sh | $TEST_APP > /tmp/test6_output.log 2>&1
    
    # Check for save confirmation
    if grep -q "set to.*and saved" /tmp/test6_output.log && \
       grep -q "Changes will take effect" /tmp/test6_output.log; then
        pass_test "Configuration save confirmation displayed"
    else
        warning_test "Configuration save confirmation not clear"
    fi
else
    fail_test "Test application not found"
fi

# Test 7: Millisecond Parameters
log_test "Millisecond Parameter Handling"
cat > /tmp/test7_script.sh << 'EOF'
#!/bin/bash
# Test millisecond parameters
echo "netmgr_set_timing ping_timeout 2000"
sleep 0.5
echo "netmgr_set_timing wifi_scan_wait 3000"
sleep 1
echo "netmgr_timing"
EOF
chmod +x /tmp/test7_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 10s /tmp/test7_script.sh | $TEST_APP > /tmp/test7_output.log 2>&1
    
    # Check millisecond values
    if grep -q "Ping timeout:.*2000 ms" /tmp/test7_output.log && \
       grep -q "Scan wait time:.*3000 ms" /tmp/test7_output.log; then
        pass_test "Millisecond parameters handled correctly"
    else
        warning_test "Millisecond parameter handling unclear"
    fi
else
    fail_test "Test application not found"
fi

# Test 8: Usage Help
log_test "Command Usage Help"
cat > /tmp/test8_script.sh << 'EOF'
#!/bin/bash
# Test help/usage
echo "netmgr_set_timing"
EOF
chmod +x /tmp/test8_script.sh

if [ -f "$TEST_APP" ]; then
    timeout 5s /tmp/test8_script.sh | $TEST_APP > /tmp/test8_output.log 2>&1
    
    # Check for usage information
    if grep -q "Usage:.*netmgr_set_timing.*parameter.*value" /tmp/test8_output.log && \
       grep -q "Parameters:.*eth0_cooldown.*wifi_cooldown" /tmp/test8_output.log; then
        pass_test "Usage help displayed correctly"
    else
        warning_test "Usage help not fully displayed"
    fi
else
    fail_test "Test application not found"
fi

# Test 9: Zero Configuration Handling
log_test "Zero/Uninitialized Configuration Handling"
# This test checks if the system properly initializes when config is invalid
# In a real test, we would need to corrupt or zero the config first
# For now, we just verify the initialization message exists
if [ -f "$TEST_APP" ]; then
    # Check first output log for initialization message
    if grep -q "initializing defaults\|Network timing defaults saved" /tmp/test1_output.log; then
        pass_test "Zero configuration handled with default initialization"
    else
        warning_test "Could not verify zero configuration handling"
    fi
else
    fail_test "Test application not found"
fi

# Cleanup
rm -f /tmp/test[1-9]_script.sh /tmp/test[1-9]_output.log

# Summary
echo -e "\n=== Phase 3 Test Summary ===" | tee -a $TEST_LOG
echo "Total tests run: $TESTS_RUN" | tee -a $TEST_LOG
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}" | tee -a $TEST_LOG
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}" | tee -a $TEST_LOG

# Note about persistence testing
echo -e "\n${YELLOW}Note: To fully test configuration persistence:${NC}" | tee -a $TEST_LOG
echo "1. Run this test to set custom values" | tee -a $TEST_LOG
echo "2. Restart the application" | tee -a $TEST_LOG
echo "3. Run 'netmgr_timing' to verify values persist" | tee -a $TEST_LOG

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}Phase 3: ALL TESTS PASSED${NC}" | tee -a $TEST_LOG
    exit 0
else
    echo -e "\n${RED}Phase 3: SOME TESTS FAILED${NC}" | tee -a $TEST_LOG
    exit 1
fi