#!/bin/bash
# Build Fleet-Connect-1 Application

cd "$(dirname "$0")/Fleet-Connect-1" || exit 1

echo "========================================="
echo "Building Fleet-Connect-1"
echo "========================================="

# Configure if needed
if [ ! -f "Makefile" ]; then
    echo "Running cmake configuration..."
    cmake . -DENABLE_TESTING=OFF
fi

# Build
echo "Building FC-1..."
make FC-1 -j4

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Fleet-Connect-1 build complete"
    echo "Binary: Fleet-Connect-1/build/FC-1"
else
    echo ""
    echo "✗ Fleet-Connect-1 build FAILED"
    exit 1
fi
