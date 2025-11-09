#!/bin/bash
# Build iMatrix Library

cd "$(dirname "$0")/iMatrix" || exit 1

echo "========================================="
echo "Building iMatrix Library"
echo "========================================="

# Configure if needed
if [ ! -f "Makefile" ]; then
    echo "Running cmake configuration..."
    cmake .
fi

# Build
echo "Building..."
make -j4

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ iMatrix library build complete"
else
    echo ""
    echo "✗ iMatrix library build FAILED"
    exit 1
fi
