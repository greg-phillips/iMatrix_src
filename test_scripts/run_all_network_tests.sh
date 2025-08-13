#!/bin/bash
#
# Master test runner for all network manager improvement tests
# This script runs all phase tests and generates a comprehensive report

TEST_RESULTS_DIR="/tmp/network_tests_$(date +%Y%m%d_%H%M%S)"
SUMMARY_FILE="$TEST_RESULTS_DIR/test_summary.txt"
APP_PATH="./test_network_app"  # Update with actual app path

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

echo "=== Network Manager Test Suite ===" | tee $SUMMARY_FILE
echo "Test run started: $(date)" | tee -a $SUMMARY_FILE
echo "Results directory: $TEST_RESULTS_DIR" | tee -a $SUMMARY_FILE
echo "" | tee -a $SUMMARY_FILE

# Function to run a test phase
run_test_phase() {
    local phase_num=$1
    local phase_name=$2
    local test_script=$3
    local log_file="$TEST_RESULTS_DIR/phase${phase_num}_${phase_name}.log"
    
    echo -e "\n${YELLOW}Running Phase $phase_num: $phase_name${NC}" | tee -a $SUMMARY_FILE
    echo "----------------------------------------" | tee -a $SUMMARY_FILE
    
    if [ -f "$test_script" ]; then
        # Run the test and capture output
        ./$test_script > "$log_file" 2>&1
        local exit_code=$?
        
        # Extract results
        local passed=$(grep -c "PASSED:" "$log_file" 2>/dev/null || echo "0")
        local failed=$(grep -c "FAILED:" "$log_file" 2>/dev/null || echo "0")
        local warnings=$(grep -c "WARNING:" "$log_file" 2>/dev/null || echo "0")
        
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}Phase $phase_num: PASSED${NC} (P:$passed F:$failed W:$warnings)" | tee -a $SUMMARY_FILE
        else
            echo -e "${RED}Phase $phase_num: FAILED${NC} (P:$passed F:$failed W:$warnings)" | tee -a $SUMMARY_FILE
        fi
        
        # Show any critical errors
        grep -E "FAILED:|ERROR:|CRITICAL:" "$log_file" | head -5 >> $SUMMARY_FILE 2>/dev/null
        
        return $exit_code
    else
        echo -e "${RED}Phase $phase_num: SKIPPED${NC} - Test script not found: $test_script" | tee -a $SUMMARY_FILE
        return 1
    fi
}

# Function to run PTY-based tests
run_pty_tests() {
    echo -e "\n${YELLOW}Running PTY-Based Integration Tests${NC}" | tee -a $SUMMARY_FILE
    echo "----------------------------------------" | tee -a $SUMMARY_FILE
    
    local pty_log="$TEST_RESULTS_DIR/pty_tests.log"
    local pty_json="$TEST_RESULTS_DIR/pty_results.json"
    
    if [ -f "pty_test_controller.py" ] && [ -f "$APP_PATH" ]; then
        python3 pty_test_controller.py "$APP_PATH" \
            --log "$pty_log" \
            --json "$pty_json" \
            --tests all
        
        local exit_code=$?
        
        # Parse JSON results if available
        if [ -f "$pty_json" ]; then
            local total=$(jq -r '.total' "$pty_json" 2>/dev/null || echo "0")
            local passed=$(jq -r '.passed' "$pty_json" 2>/dev/null || echo "0")
            local failed=$(jq -r '.failed' "$pty_json" 2>/dev/null || echo "0")
            
            if [ $exit_code -eq 0 ]; then
                echo -e "${GREEN}PTY Tests: PASSED${NC} ($passed/$total tests)" | tee -a $SUMMARY_FILE
            else
                echo -e "${RED}PTY Tests: FAILED${NC} ($passed/$total tests, $failed failed)" | tee -a $SUMMARY_FILE
            fi
        fi
        
        return $exit_code
    else
        echo -e "${RED}PTY Tests: SKIPPED${NC} - Controller or app not found" | tee -a $SUMMARY_FILE
        return 1
    fi
}

# Check if we're running in test mode
if [ -z "$NETWORK_TEST_MODE" ]; then
    echo -e "${YELLOW}Warning: NETWORK_TEST_MODE not set${NC}" | tee -a $SUMMARY_FILE
    echo "The application should be compiled with TEST_MODE enabled" | tee -a $SUMMARY_FILE
    echo "Set environment: export NETWORK_TEST_MODE=1" | tee -a $SUMMARY_FILE
    echo "" | tee -a $SUMMARY_FILE
fi

# Track overall results
TOTAL_PHASES=0
PASSED_PHASES=0
FAILED_PHASES=0

# Run all test phases
echo -e "\n${YELLOW}=== Running Test Phases ===${NC}" | tee -a $SUMMARY_FILE

# Phase 1: Mutex and Timer tests
if run_test_phase 1 "mutex_timer" "test_phase1_mutex_timer.sh"; then
    ((PASSED_PHASES++))
else
    ((FAILED_PHASES++))
fi
((TOTAL_PHASES++))

# Phase 2: State Machine tests
if run_test_phase 2 "state_machine" "test_phase2_state_machine.sh"; then
    ((PASSED_PHASES++))
else
    ((FAILED_PHASES++))
fi
((TOTAL_PHASES++))

# Phase 3: Timing Configuration tests
if run_test_phase 3 "timing_config" "test_phase3_timing_config.sh"; then
    ((PASSED_PHASES++))
else
    ((FAILED_PHASES++))
fi
((TOTAL_PHASES++))

# Run PTY integration tests
echo "" | tee -a $SUMMARY_FILE
if run_pty_tests; then
    ((PASSED_PHASES++))
else
    ((FAILED_PHASES++))
fi
((TOTAL_PHASES++))

# Generate final summary
echo -e "\n${YELLOW}=== Final Test Summary ===${NC}" | tee -a $SUMMARY_FILE
echo "=========================" | tee -a $SUMMARY_FILE
echo "Total test phases: $TOTAL_PHASES" | tee -a $SUMMARY_FILE
echo -e "Passed phases: ${GREEN}$PASSED_PHASES${NC}" | tee -a $SUMMARY_FILE
echo -e "Failed phases: ${RED}$FAILED_PHASES${NC}" | tee -a $SUMMARY_FILE

# Calculate success rate
if [ $TOTAL_PHASES -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; 100 * $PASSED_PHASES / $TOTAL_PHASES" | bc)
    echo "Success rate: $SUCCESS_RATE%" | tee -a $SUMMARY_FILE
fi

echo "" | tee -a $SUMMARY_FILE
echo "Test run completed: $(date)" | tee -a $SUMMARY_FILE
echo "Full results saved in: $TEST_RESULTS_DIR" | tee -a $SUMMARY_FILE

# Generate HTML report if possible
if command -v pandoc &> /dev/null; then
    echo "" | tee -a $SUMMARY_FILE
    echo "Generating HTML report..." | tee -a $SUMMARY_FILE
    
    # Create markdown summary
    MD_FILE="$TEST_RESULTS_DIR/report.md"
    cat > "$MD_FILE" << EOF
# Network Manager Test Report

**Date:** $(date)  
**Test Suite Version:** 1.0  

## Summary

- **Total Phases:** $TOTAL_PHASES
- **Passed:** $PASSED_PHASES
- **Failed:** $FAILED_PHASES
- **Success Rate:** $SUCCESS_RATE%

## Test Results by Phase

### Phase 1: Mutex Protection and Timer Fixes
Tests mutex protection for interface states and DNS cache, and verifies cooldown timer logic.

### Phase 2: State Machine Validation
Tests state machine transitions and hysteresis to prevent interface ping-ponging.

### Phase 3: Timing Configuration
Tests the network timing configuration system with environment variables.

### PTY Integration Tests
Comprehensive integration tests using pseudo-terminal interface.

## Detailed Logs

All detailed test logs are available in the results directory.
EOF

    pandoc "$MD_FILE" -o "$TEST_RESULTS_DIR/report.html" --standalone --metadata title="Network Test Report"
    echo "HTML report generated: $TEST_RESULTS_DIR/report.html" | tee -a $SUMMARY_FILE
fi

# Exit with appropriate code
if [ $FAILED_PHASES -gt 0 ]; then
    echo -e "\n${RED}TEST SUITE FAILED${NC}" | tee -a $SUMMARY_FILE
    exit 1
else
    echo -e "\n${GREEN}TEST SUITE PASSED${NC}" | tee -a $SUMMARY_FILE
    exit 0
fi