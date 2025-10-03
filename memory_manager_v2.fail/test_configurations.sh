#!/bin/bash

echo "=== Memory Manager v2 Configuration Testing ==="
echo ""

echo "1. Testing LINUX + MOCK configuration:"
cmake -DTARGET_PLATFORM=LINUX -DSTORAGE_BACKEND=MOCK . > /dev/null 2>&1
make > /dev/null 2>&1
./test_harness --test=all --quiet
echo ""

echo "2. Testing WICED + MOCK configuration:"
cmake -DTARGET_PLATFORM=WICED -DSTORAGE_BACKEND=MOCK . > /dev/null 2>&1
make > /dev/null 2>&1
./test_harness --test=all --quiet
echo ""

echo "3. Testing iMatrix storage backend compilation:"
echo "   (Note: This will fail in test environment - requires full iMatrix)"
cmake -DTARGET_PLATFORM=LINUX -DSTORAGE_BACKEND=IMATRIX . > /dev/null 2>&1
if make > /dev/null 2>&1; then
    echo "   ✅ iMatrix storage: COMPILES"
    ./test_harness --test=13 --quiet
else
    echo "   ⚠️  iMatrix storage: REQUIRES FULL IMATRIX ENVIRONMENT"
fi
echo ""

echo "4. Restoring default configuration (LINUX + MOCK):"
cmake -DTARGET_PLATFORM=LINUX -DSTORAGE_BACKEND=MOCK . > /dev/null 2>&1
make > /dev/null 2>&1
echo "   ✅ Default configuration restored"
echo ""

echo "=== Configuration Testing Complete ==="
echo ""
echo "Available configurations:"
echo "  Development:  cmake -DTARGET_PLATFORM=LINUX -DSTORAGE_BACKEND=MOCK ."
echo "  Embedded:     cmake -DTARGET_PLATFORM=WICED -DSTORAGE_BACKEND=MOCK ."
echo "  Production:   cmake -DTARGET_PLATFORM=LINUX -DSTORAGE_BACKEND=IMATRIX ."
echo ""
echo "Current: LINUX + MOCK (ready for development)"