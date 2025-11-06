#!/bin/bash

echo "=== Interactive Menu Demo ==="
echo ""
echo "Demonstrating interactive test menu functionality:"
echo ""

echo "1. Testing menu with test selection 3:"
echo "3" | ./test_harness
echo ""

echo "2. The menu would normally loop back for another selection"
echo "   (Demo shows single execution)"
echo ""

echo "3. Testing quit functionality:"
echo "q" | ./test_harness
echo ""

echo "=== Interactive Demo Complete ==="
echo ""
echo "To use interactively:"
echo "  ./test_harness"
echo "  (then select test 1-5, 0 for all, or q to quit)"