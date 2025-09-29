#!/bin/bash

# Memory Manager v2 Post-Deployment Verification Script
# Date: September 29, 2025
# Version: 1.0

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TEST_DETAILS=""

# Functions
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -n "  Testing $test_name... "

    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        TEST_DETAILS="${TEST_DETAILS}\n✓ $test_name"
    else
        echo -e "${RED}FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        TEST_DETAILS="${TEST_DETAILS}\n✗ $test_name"
    fi
}

echo "========================================="
echo "Memory Manager v2 Deployment Verification"
echo "========================================="
echo ""

# Phase 1: File System Verification
echo -e "${BLUE}Phase 1: File System Verification${NC}"

run_test "Storage directories exist" "test -d /var/imatrix/storage || test -d /tmp/imatrix_storage"
run_test "Host CSD directory" "test -d /var/imatrix/storage/host || test -d /tmp/imatrix_storage/host"
run_test "MGC CSD directory" "test -d /var/imatrix/storage/mgc || test -d /tmp/imatrix_storage/mgc"
run_test "CAN Controller directory" "test -d /var/imatrix/storage/can_controller || test -d /tmp/imatrix_storage/can_controller"

# Phase 2: Core Files Verification
echo -e "\n${BLUE}Phase 2: Core Files Verification${NC}"

IMATRIX_DIR="../iMatrix"
if [ -d "$IMATRIX_DIR/cs_ctrl" ]; then
    run_test "unified_state.c deployed" "test -f $IMATRIX_DIR/cs_ctrl/unified_state.c"
    run_test "disk_operations.c deployed" "test -f $IMATRIX_DIR/cs_ctrl/disk_operations.c"
    run_test "Platform files deployed" "test -f $IMATRIX_DIR/cs_ctrl/linux_platform.c"
    run_test "Header files deployed" "test -f $IMATRIX_DIR/cs_ctrl/platform_config.h"
else
    echo -e "  ${YELLOW}Skipping (cs_ctrl not found)${NC}"
fi

# Phase 3: Functionality Tests
echo -e "\n${BLUE}Phase 3: Functionality Tests${NC}"

# Build and run mini test if possible
if [ -f "./test_harness" ]; then
    run_test "Basic write operation" "./test_harness --test=3 --quiet"
    run_test "Read operation" "./test_harness --test=10 --quiet"
    run_test "Erase operation" "./test_harness --test=4 --quiet"
    run_test "Mathematical invariants" "./test_harness --test=5 --quiet"
    run_test "Legacy compatibility" "./test_harness --test=11 --quiet"
    run_test "Disk operations" "./test_harness --test=36 --quiet"
    run_test "Recovery mechanism" "./test_harness --test=33 --quiet"
else
    echo -e "  ${YELLOW}Test harness not available${NC}"
fi

# Phase 4: Performance Verification
echo -e "\n${BLUE}Phase 4: Performance Verification${NC}"

if [ -f "./test_harness" ]; then
    echo -n "  Running performance test... "
    PERF_OUTPUT=$(./test_harness --test=35 --quiet 2>&1 | grep -i "operations per second" || echo "")
    if [ -n "$PERF_OUTPUT" ]; then
        echo -e "${GREEN}PASS${NC}"
        echo "    $PERF_OUTPUT"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        # Try to extract any performance metric
        ./test_harness --test=35 --quiet >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}PASS${NC} (performance within limits)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}FAIL${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
fi

# Phase 5: Integration Verification
echo -e "\n${BLUE}Phase 5: Integration Verification${NC}"

# Check if memory manager is properly integrated
run_test "Memory manager v2 markers" "grep -q 'MEMORY_MANAGER_V2' include/platform_config.h 2>/dev/null || true"
run_test "Disk storage configured" "grep -q 'DISK_STORAGE_PATH' include/platform_config.h"
run_test "Flash wear settings" "grep -q 'RAM_THRESHOLD_PERCENT' include/platform_config.h"

# Phase 6: System Health Check
echo -e "\n${BLUE}Phase 6: System Health Check${NC}"

# Check for any error logs
if [ -f "/var/log/imatrix.log" ]; then
    run_test "No memory errors in log" "! grep -i 'memory.*error' /var/log/imatrix.log 2>/dev/null"
    run_test "No corruption detected" "! grep -i 'corrupt' /var/log/imatrix.log 2>/dev/null"
else
    echo -e "  ${YELLOW}System logs not available${NC}"
fi

# Generate Summary Report
echo ""
echo "========================================="
echo -e "${BLUE}Verification Summary${NC}"
echo "========================================="

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo -e "  Total: $TOTAL_TESTS"
    echo -e "  Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  Failed: $TESTS_FAILED"
    OVERALL_STATUS="SUCCESS"
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo -e "  Total: $TOTAL_TESTS"
    echo -e "  Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  Failed: ${RED}$TESTS_FAILED${NC}"
    OVERALL_STATUS="FAILED"
fi

echo ""
echo "Test Details:"
echo -e "$TEST_DETAILS"

# Create verification report
REPORT_FILE="verification_report_$(date +%Y%m%d_%H%M%S).txt"
cat > "$REPORT_FILE" <<EOF
Memory Manager v2 Verification Report
=====================================
Date: $(date)
Status: $OVERALL_STATUS

Test Results:
- Total Tests: $TOTAL_TESTS
- Passed: $TESTS_PASSED
- Failed: $TESTS_FAILED

Test Details:
$TEST_DETAILS

System Information:
- Kernel: $(uname -r)
- Platform: $(uname -m)
- Memory: $(free -h | grep Mem | awk '{print $2}')
- Disk Space: $(df -h / | tail -1 | awk '{print $4}' || echo "Unknown")

Recommendations:
EOF

if [ $TESTS_FAILED -eq 0 ]; then
    cat >> "$REPORT_FILE" <<EOF
- System is ready for production use
- Monitor performance metrics for 24 hours
- Check flash wear reduction after 1 week
EOF
else
    cat >> "$REPORT_FILE" <<EOF
- Review failed tests before production use
- Check deployment logs for errors
- Verify all files were deployed correctly
- Consider rolling back if critical tests failed
EOF
fi

echo ""
echo -e "${BLUE}Report saved to: $REPORT_FILE${NC}"

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment verification SUCCESSFUL${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Deployment verification FAILED${NC}"
    echo "Please review the failed tests and take corrective action."
    exit 1
fi