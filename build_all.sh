#!/bin/bash
# Build Complete iMatrix System

set -e  # Exit on first error

BASE_DIR="$(dirname "$0")"

echo "========================================="
echo "Building Complete iMatrix System"
echo "========================================="
echo ""

# Build iMatrix library
echo "Step 1/2: Building iMatrix library..."
echo "---------------------------------------"
cd "$BASE_DIR/iMatrix"
if [ ! -f "Makefile" ]; then
    cmake .
fi
make -j4
echo "✓ iMatrix library complete"
echo ""

# Build Fleet-Connect-1
echo "Step 2/2: Building Fleet-Connect-1..."
echo "---------------------------------------"
cd "$BASE_DIR/Fleet-Connect-1"
if [ ! -f "Makefile" ]; then
    cmake . -DENABLE_TESTING=OFF
fi
make FC-1 -j4
echo "✓ Fleet-Connect-1 complete"
echo ""

echo "========================================="
echo "✓ BUILD COMPLETE"
echo "========================================="
echo "Binary: Fleet-Connect-1/build/FC-1"
echo ""
echo "To run:"
echo "  cd Fleet-Connect-1/build"
echo "  ./FC-1"
