#!/bin/sh
# Generate manifest for built tools
set -eu

PROFILER_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="$PROFILER_DIR/build/target_tools/armhf"
MANIFEST_DIR="$PROFILER_DIR/tools/manifests"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MANIFEST_FILE="$MANIFEST_DIR/target_tools_armhf_${TIMESTAMP}.txt"

{
    echo "Target Tools Manifest"
    echo "====================="
    echo "Generated: $(date)"
    echo "Architecture: armhf"
    echo "Cross-compiler: /opt/qconnect_sdk_musl/bin/arm-linux"
    echo ""
    echo "Built tools:"
    echo "------------"

    for tool in "$OUTPUT_DIR/bin/"*; do
        if [ -f "$tool" ]; then
            name=$(basename "$tool")
            size=$(ls -lh "$tool" | awk '{print $5}')
            sha256=$(sha256sum "$tool" | awk '{print $1}')
            if file "$tool" | grep -q "statically linked"; then
                linktype="static"
            else
                linktype="dynamic (musl)"
            fi
            echo "  $name"
            echo "    Size:    $size"
            echo "    SHA256:  $sha256"
            echo "    Linking: $linktype"
        fi
    done
} > "$MANIFEST_FILE"

echo "Manifest saved to: $MANIFEST_FILE"
cat "$MANIFEST_FILE"
