#!/bin/bash
# Clean All Build Artifacts

BASE_DIR="$(dirname "$0")"

echo "========================================="
echo "Cleaning All Build Artifacts"
echo "========================================="

# Clean iMatrix
echo "Cleaning iMatrix..."
cd "$BASE_DIR/iMatrix"
if [ -f "Makefile" ]; then
    make clean
fi
echo "✓ iMatrix cleaned"

# Clean Fleet-Connect-1
echo "Cleaning Fleet-Connect-1..."
cd "$BASE_DIR/Fleet-Connect-1"
rm -rf build CMakeCache.txt CMakeFiles cmake_install.cmake Makefile *.o
echo "✓ Fleet-Connect-1 cleaned"

echo ""
echo "✓ All build artifacts removed"
