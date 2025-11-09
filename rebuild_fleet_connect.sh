#!/bin/bash
# Rebuild Fleet-Connect-1 from Scratch

BASE_DIR="$(dirname "$0")"

echo "========================================="
echo "Rebuilding Fleet-Connect-1 from Scratch"
echo "========================================="

cd "$BASE_DIR/Fleet-Connect-1"

# Clean
echo "Cleaning old build..."
rm -rf build CMakeCache.txt CMakeFiles cmake_install.cmake Makefile *.o
echo "✓ Cleaned"
echo ""

# Configure
echo "Configuring with CMake..."
cmake . -DENABLE_TESTING=OFF
echo "✓ Configured"
echo ""

# Build
echo "Building FC-1..."
make FC-1 -j4

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✓ REBUILD COMPLETE"
    echo "========================================="
    echo "Binary: Fleet-Connect-1/build/FC-1"
else
    echo ""
    echo "✗ BUILD FAILED"
    exit 1
fi
