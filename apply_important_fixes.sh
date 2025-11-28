#!/bin/bash
#
# apply_important_fixes.sh
# Apply all important cellular fixes
# Date: 2025-11-22
#

set -e  # Exit on error

echo "=================================="
echo " Applying Important Cellular Fixes"
echo "=================================="
echo ""

# Check we're in the right directory
if [ ! -d "iMatrix/IMX_Platform/LINUX_Platform/networking" ]; then
    echo "Error: Not in iMatrix_Client directory"
    echo "Please run from /home/greg/iMatrix/iMatrix_Client"
    exit 1
fi

# Create backups
echo "Creating backups..."
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
cp iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c \
   iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c.backup_${BACKUP_DATE}
cp iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c \
   iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c.backup_${BACKUP_DATE}

echo "Backups created with suffix: backup_${BACKUP_DATE}"
echo ""

# Apply patches
echo "Applying patches..."
echo ""

echo "1. Applying cellular_man.c fixes (critical blacklist clearing, PPP monitoring, etc.)..."
cd iMatrix/IMX_Platform/LINUX_Platform/networking
if patch -p0 < ../../../../IMPORTANT_FIXES_COMPLETE.patch; then
    echo "   ✅ cellular_man.c patch applied successfully"
else
    echo "   ⚠️  cellular_man.c patch failed - manual intervention needed"
    echo "   Check for .rej files"
fi
cd ../../../..

echo ""
echo "2. Applying process_network.c coordination fixes..."
cd iMatrix/IMX_Platform/LINUX_Platform/networking
if patch -p0 < ../../../../process_network_coordination.patch; then
    echo "   ✅ process_network.c patch applied successfully"
else
    echo "   ⚠️  process_network.c patch failed - manual intervention needed"
    echo "   Check for .rej files"
fi
cd ../../../..

echo ""
echo "3. Adding header definitions..."
if [ ! -f "iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man_additions.h" ]; then
    cp cellular_man_additions.h iMatrix/IMX_Platform/LINUX_Platform/networking/
    echo "   ✅ Header file added"
else
    echo "   ℹ️  Header file already exists"
fi

echo ""
echo "4. Adding blacklist display functions..."
if ! grep -q "get_blacklist_timeout_remaining" iMatrix/networking/cellular_blacklist.c 2>/dev/null; then
    cat cellular_blacklist_additions.c >> iMatrix/networking/cellular_blacklist.c
    echo "   ✅ Blacklist functions added"
else
    echo "   ℹ️  Blacklist functions already present"
fi

echo ""
echo "=================================="
echo " Verification"
echo "=================================="
echo ""

# Verify critical fix is present
echo "Checking for critical fixes..."
echo ""

if grep -q "clear_blacklist_for_scan()" iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c; then
    echo "✅ CRITICAL FIX: Blacklist clearing is present"
    grep -n "clear_blacklist_for_scan" iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c | head -1
else
    echo "❌ CRITICAL FIX MISSING: Blacklist clearing not found!"
    echo "   Manual intervention required!"
fi

if grep -q "CELL_WAIT_PPP_INTERFACE" iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c; then
    echo "✅ PPP monitoring state is present"
else
    echo "❌ PPP monitoring state missing!"
fi

if grep -q "cellular_request_rescan" iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c; then
    echo "✅ Network coordination flags present"
else
    echo "❌ Network coordination missing!"
fi

if grep -q "log_carrier_details" iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c; then
    echo "✅ Enhanced logging integrated"
else
    echo "⚠️  Enhanced logging not fully integrated"
fi

echo ""
echo "=================================="
echo " Build Instructions"
echo "=================================="
echo ""
echo "To build with the fixes:"
echo ""
echo "  cd iMatrix"
echo "  make clean"
echo "  make"
echo ""
echo "To test:"
echo ""
echo "  ./FC-1"
echo "  cell operators    # Check display shows tested/blacklist status"
echo "  cell scan        # Trigger scan and verify blacklist clears"
echo "  cell blacklist   # Show detailed blacklist"
echo ""

echo "=================================="
echo " Summary"
echo "=================================="
echo ""
echo "Important fixes applied:"
echo "  1. Blacklist clearing on AT+COPS scan"
echo "  2. PPP establishment monitoring"
echo "  3. Network/cellular coordination"
echo "  4. Enhanced logging integration"
echo "  5. Carrier failure handling"
echo ""
echo "These fixes address:"
echo "  - Carriers getting permanently stuck"
echo "  - PPP failures not detected"
echo "  - No recovery from failures"
echo "  - Poor debugging visibility"
echo ""

# Check for any .rej files
if find iMatrix -name "*.rej" 2>/dev/null | grep -q rej; then
    echo "⚠️  WARNING: Patch rejects found!"
    echo "   Manual resolution required for:"
    find iMatrix -name "*.rej" 2>/dev/null
else
    echo "✅ No patch conflicts detected"
fi

echo ""
echo "Script complete!"
echo ""