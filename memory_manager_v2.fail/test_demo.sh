#!/bin/bash

echo "=== Memory Manager v2 Test Harness Demo ==="
echo ""

echo "1. Testing command line options:"
echo ""

echo "   a) Help display:"
./test_harness --help
echo ""

echo "   b) Quiet mode (automation-friendly):"
./test_harness --test=all --quiet
echo ""

echo "   c) Specific test with verbose output:"
./test_harness --test=3 --verbose
echo ""

echo "   d) Detailed diagnostics:"
./test_harness --test=5 --detailed
echo ""

echo "2. Platform switching demo:"
echo ""

echo "   a) LINUX platform (current):"
./test_harness --test=1 --quiet
echo ""

echo "   b) WICED platform:"
cmake -DTARGET_PLATFORM=WICED . > /dev/null 2>&1
make > /dev/null 2>&1
./test_harness --test=1 --quiet
echo ""

echo "   c) Back to LINUX platform:"
cmake -DTARGET_PLATFORM=LINUX . > /dev/null 2>&1
make > /dev/null 2>&1
./test_harness --test=1 --quiet
echo ""

echo "=== Demo Complete ==="
echo ""
echo "Interactive mode:"
echo "Run './test_harness' with no arguments for interactive menu"