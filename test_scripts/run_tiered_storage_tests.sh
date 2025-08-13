#!/bin/bash
#
# run_tiered_storage_tests.sh
# 
# Comprehensive test suite for iMatrix Tiered Storage System
# Runs multiple test scenarios and generates a report
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="/tmp/imatrix_test_storage/history"
LOG_DIR="./test_logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${LOG_DIR}/test_report_${TIMESTAMP}.txt"

# Create directories
mkdir -p ${LOG_DIR}

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}[PASS]${NC} $message"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}[FAIL]${NC} $message"
    else
        echo -e "${YELLOW}[INFO]${NC} $message"
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "INFO" "Checking prerequisites..."
    
    # Check if ANY test program exists
    local has_test_program=false
    
    # Check in build directory first (preferred location)
    if [ -f "./build/simple_memory_test" ]; then
        print_status "INFO" "simple_memory_test found in build/ (basic functionality)"
        has_test_program=true
    elif [ -f "./simple_memory_test" ]; then
        print_status "INFO" "simple_memory_test found in main directory"
        has_test_program=true
    fi
    
    if [ -f "./build/tiered_storage_test" ]; then
        print_status "INFO" "tiered_storage_test found in build/ (full test)"
        has_test_program=true
    elif [ -f "./tiered_storage_test" ]; then
        print_status "INFO" "tiered_storage_test found in main directory"
        has_test_program=true
    fi
    
    if [ -f "./build/performance_test" ]; then
        print_status "INFO" "performance_test found in build/ (performance test)"
        has_test_program=true
    elif [ -f "./performance_test" ]; then
        print_status "INFO" "performance_test found in main directory"
        has_test_program=true
    fi
    
    if [ -f "./build/diagnostic_test" ]; then
        print_status "INFO" "diagnostic_test found in build/ (diagnostic test)"
        has_test_program=true
    elif [ -f "./diagnostic_test" ]; then
        print_status "INFO" "diagnostic_test found in main directory"
        has_test_program=true
    fi
    
    if [ -f "./build/spillover_test" ]; then
        print_status "INFO" "spillover_test found in build/ (spillover test)"
        has_test_program=true
    elif [ -f "./spillover_test" ]; then
        print_status "INFO" "spillover_test found in main directory"
        has_test_program=true
    fi
    
    if [ "$has_test_program" = false ]; then
        print_status "FAIL" "No test programs found. Run 'make' to build first."
        print_status "INFO" "Available targets: simple_memory_test, tiered_storage_test, performance_test, diagnostic_test, spillover_test"
        exit 1
    fi
    
    # Ensure test storage directory exists
    mkdir -p ${TEST_DIR}/corrupted
    if [ ! -w "$TEST_DIR" ]; then
        print_status "FAIL" "Cannot write to test directory: $TEST_DIR"
        exit 1
    fi
    
    print_status "PASS" "Prerequisites checked"
}

# Function to clean test data
clean_test_data() {
    print_status "INFO" "Cleaning test data..."
    rm -rf /tmp/imatrix_test_storage
    mkdir -p ${TEST_DIR}/corrupted
    rm -f ${TEST_DIR}/*.dat
    rm -f ${TEST_DIR}/*.imx
    rm -f ${TEST_DIR}/recovery.journal*
    rm -f ${TEST_DIR}/corrupted/*
    print_status "PASS" "Test data cleaned"
}

# Function to run a test scenario
run_test() {
    local test_name=$1
    local test_cmd=$2
    local log_file="${LOG_DIR}/${test_name}_${TIMESTAMP}.log"
    
    echo ""
    print_status "INFO" "Running test: $test_name"
    echo "Command: $test_cmd"
    
    # Run test and capture output
    $test_cmd > "$log_file" 2>&1
    local result=$?
    
    # Check result
    if [ $result -eq 0 ]; then
        print_status "PASS" "$test_name completed successfully"
        echo "[PASS] $test_name" >> "$REPORT_FILE"
    else
        print_status "FAIL" "$test_name failed (exit code: $result)"
        echo "[FAIL] $test_name (exit code: $result)" >> "$REPORT_FILE"
        
        # Show last few lines of error
        echo "Error output:"
        tail -20 "$log_file"
    fi
    
    # Extract key metrics
    if grep -q "OVERALL RESULT: PASSED\|ALL TESTS PASSED" "$log_file"; then
        # Try to extract tiered storage metrics
        local write_rate=$(grep "records/sec" "$log_file" | head -1 | grep -oE '[0-9]+ records/sec')
        local peak_ram=$(grep "Peak RAM usage:" "$log_file" | grep -oE '[0-9.]+%')
        local files=$(grep "Files created:" "$log_file" | tail -1 | grep -oE '[0-9]+')
        
        # Try to extract simple test metrics
        local test_count=$(grep "Tests passed:" "$log_file" | grep -oE '[0-9]+/[0-9]+')
        
        if [ -n "$write_rate" ] || [ -n "$peak_ram" ] || [ -n "$files" ]; then
            echo "  Metrics: Write: $write_rate, Peak RAM: $peak_ram, Files: $files" | tee -a "$REPORT_FILE"
        elif [ -n "$test_count" ]; then
            echo "  Metrics: Tests: $test_count" | tee -a "$REPORT_FILE"
        fi
    fi
    
    return $result
}

# Function to generate final report
generate_report() {
    echo ""
    echo "======================================"
    echo "        TEST SUITE SUMMARY"
    echo "======================================"
    cat "$REPORT_FILE"
    echo ""
    echo "Detailed logs available in: $LOG_DIR"
    echo ""
    echo "Cleanup Commands:"
    echo "  ./clear_old_data.sh --dry-run       # Preview cleanup"
    echo "  ./clear_old_data.sh --test-only     # Clean test data only"
    echo "  ./clear_old_data.sh --help          # Show cleanup options"
    echo "======================================"
}

# Main test execution
main() {
    echo "iMatrix Tiered Storage Test Suite"
    echo "================================="
    echo "Timestamp: $TIMESTAMP"
    echo ""
    
    # Initialize report
    echo "iMatrix Tiered Storage Test Report - $TIMESTAMP" > "$REPORT_FILE"
    echo "================================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check prerequisites
    check_prerequisites
    
    # Test 1: Basic memory manager functionality (always available)
    if [ -f "./build/simple_memory_test" ]; then
clean_test_data
        run_test "memory_manager_basic" "./build/simple_memory_test"
    elif [ -f "./simple_memory_test" ]; then
        clean_test_data
        run_test "memory_manager_basic" "./simple_memory_test"
    fi
    
    # Test 2: Complete tiered storage functionality
    if [ -f "./build/tiered_storage_test" ]; then
        clean_test_data
        run_test "tiered_storage_complete" "./build/tiered_storage_test"
    elif [ -f "./tiered_storage_test" ]; then
        clean_test_data
        run_test "tiered_storage_complete" "./tiered_storage_test"
    else
        print_status "INFO" "tiered_storage_test not available, skipping complete tiered storage test"
    fi
    
    # Test 3: Recovery system verification
    if [ -f "./build/tiered_storage_test" ]; then
        # Run test once to create test data
        clean_test_data
        print_status "INFO" "Running test to generate data for recovery test..."
        ./build/tiered_storage_test >/dev/null 2>&1
        
        # Now test recovery without cleaning data
        run_test "recovery_verification" "./build/tiered_storage_test"
    elif [ -f "./tiered_storage_test" ]; then
        # Run test once to create test data
        clean_test_data
        print_status "INFO" "Running test to generate data for recovery test..."
        ./tiered_storage_test >/dev/null 2>&1
        
        # Now test recovery without cleaning data
        run_test "recovery_verification" "./tiered_storage_test"
    fi
    
    # Test 4: Performance testing
    if [ -f "./build/performance_test" ]; then
        clean_test_data
        run_test "performance_benchmark" "./build/performance_test"
    elif [ -f "./performance_test" ]; then
        clean_test_data
        run_test "performance_benchmark" "./performance_test"
    else
        print_status "INFO" "performance_test not available, skipping performance test"
    fi
    
    # Test 5: Diagnostic testing for Test 5 data corruption issue
    if [ -f "./build/diagnostic_test" ]; then
        clean_test_data
        run_test "diagnostic_analysis" "./build/diagnostic_test"
    elif [ -f "./diagnostic_test" ]; then
        clean_test_data
        run_test "diagnostic_analysis" "./diagnostic_test"
    else
        print_status "INFO" "diagnostic_test not available, skipping diagnostic test"
    fi
    
    # Test 6: 80% Memory spillover testing with RAM validation
    if [ -f "./build/spillover_test" ]; then
        clean_test_data
        run_test "spillover_validation" "./build/spillover_test 500"
    elif [ -f "./spillover_test" ]; then
        clean_test_data
        run_test "spillover_validation" "./spillover_test 500"
    else
        print_status "INFO" "spillover_test not available, skipping spillover test"
    fi
    
    # Test 7: Real-world usage test
    if [ -f "./build/real_world_test" ]; then
        clean_test_data
        run_test "real_world_usage" "./build/real_world_test"
    elif [ -f "./real_world_test" ]; then
        clean_test_data
        run_test "real_world_usage" "./real_world_test"
    else
        print_status "INFO" "real_world_test not available, skipping real-world test"
    fi
    
    # Test 8: Comprehensive memory test
    if [ -f "./build/comprehensive_memory_test" ]; then
        clean_test_data
        run_test "comprehensive_memory" "./build/comprehensive_memory_test"
    elif [ -f "./comprehensive_memory_test" ]; then
        clean_test_data
        run_test "comprehensive_memory" "./comprehensive_memory_test"
    else
        print_status "INFO" "comprehensive_memory_test not available, skipping comprehensive test"
    fi
    
    # Test 9: Comprehensive test with simulated disk conditions
    if [ -f "./build/comprehensive_memory_test" ]; then
        clean_test_data
        IMX_TEST_DISK_USAGE=79 run_test "comprehensive_79pct_disk" "./build/comprehensive_memory_test --section 5"
        
        clean_test_data
        IMX_TEST_DISK_USAGE=95 run_test "comprehensive_95pct_disk" "./build/comprehensive_memory_test --section 5"
    elif [ -f "./comprehensive_memory_test" ]; then
        clean_test_data
        IMX_TEST_DISK_USAGE=79 run_test "comprehensive_79pct_disk" "./comprehensive_memory_test --section 5"
        
        clean_test_data
        IMX_TEST_DISK_USAGE=95 run_test "comprehensive_95pct_disk" "./comprehensive_memory_test --section 5"
    fi
    
    # Generate final report
    generate_report
    
    # Check overall status
    if grep -q "\[FAIL\]" "$REPORT_FILE"; then
        print_status "FAIL" "Some tests failed. Check logs for details."
        exit 1
    else
        print_status "PASS" "All tests passed!"
        exit 0
    fi
}

# Run main function
main "$@"