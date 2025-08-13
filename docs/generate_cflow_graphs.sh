#!/bin/bash
# Generate cflow-based call graphs for iMatrix and Fleet-Connect-1

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CFLOW_DIR="$ROOT_DIR/docs/architecture/call_graphs"

echo "Generating cflow call graphs..."

# Create output directories
mkdir -p "$CFLOW_DIR/imatrix"
mkdir -p "$CFLOW_DIR/fleet-connect"

# Function to generate cflow graph for a module
generate_cflow() {
    local module_name=$1
    local source_dir=$2
    local output_dir=$3
    local include_dirs=$4
    
    echo "  Processing $module_name..."
    
    # Find all C source files
    local sources=$(find "$source_dir" -name "*.c" -type f 2>/dev/null | grep -v "/external/" | grep -v "/build/" || true)
    
    if [ -n "$sources" ]; then
        # Generate forward call graph
        cflow $include_dirs --omit-arguments --omit-symbol-names --level-indent='0=\t' \
            $sources > "$output_dir/${module_name}_forward.txt" 2>/dev/null || true
        
        # Generate reverse call graph (who calls what)
        cflow --reverse $include_dirs --omit-arguments --omit-symbol-names --level-indent='0=\t' \
            $sources > "$output_dir/${module_name}_reverse.txt" 2>/dev/null || true
        
        # Generate cross-reference
        cflow --xref $include_dirs \
            $sources > "$output_dir/${module_name}_xref.txt" 2>/dev/null || true
    fi
}

# iMatrix modules
echo "Processing iMatrix modules..."
IMATRIX_INCLUDES="-I$ROOT_DIR/iMatrix -I$ROOT_DIR/iMatrix/IMX_Platform/LINUX_Platform"

generate_cflow "platform" "$ROOT_DIR/iMatrix/IMX_Platform" "$CFLOW_DIR/imatrix" "$IMATRIX_INCLUDES"
generate_cflow "ble" "$ROOT_DIR/iMatrix/ble" "$CFLOW_DIR/imatrix" "$IMATRIX_INCLUDES"
generate_cflow "coap" "$ROOT_DIR/iMatrix/coap" "$CFLOW_DIR/imatrix" "$IMATRIX_INCLUDES"
generate_cflow "device" "$ROOT_DIR/iMatrix/device" "$CFLOW_DIR/imatrix" "$IMATRIX_INCLUDES"
generate_cflow "cli" "$ROOT_DIR/iMatrix/cli" "$CFLOW_DIR/imatrix" "$IMATRIX_INCLUDES"

# Fleet-Connect-1 modules
echo "Processing Fleet-Connect-1 modules..."
FC_INCLUDES="-I$ROOT_DIR/Fleet-Connect-1 -I$ROOT_DIR/iMatrix"

generate_cflow "obd2" "$ROOT_DIR/Fleet-Connect-1/OBD2" "$CFLOW_DIR/fleet-connect" "$FC_INCLUDES"
generate_cflow "can_process" "$ROOT_DIR/Fleet-Connect-1/can_process" "$CFLOW_DIR/fleet-connect" "$FC_INCLUDES"
generate_cflow "hal" "$ROOT_DIR/Fleet-Connect-1/hal" "$CFLOW_DIR/fleet-connect" "$FC_INCLUDES"
generate_cflow "main" "$ROOT_DIR/Fleet-Connect-1/linux_gateway.c $ROOT_DIR/Fleet-Connect-1/do_everything.c" "$CFLOW_DIR/fleet-connect" "$FC_INCLUDES"

# Generate index for cflow graphs
cat > "$CFLOW_DIR/index.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Call Graphs</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        h1, h2 { font-family: Arial, sans-serif; }
        .module { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Call Graph Analysis</h1>
    
    <h2>iMatrix Modules</h2>
    <div class="module">
        <h3>Platform</h3>
        <a href="imatrix/platform_forward.txt">Forward Call Graph</a> |
        <a href="imatrix/platform_reverse.txt">Reverse Call Graph</a> |
        <a href="imatrix/platform_xref.txt">Cross Reference</a>
    </div>
    
    <div class="module">
        <h3>BLE</h3>
        <a href="imatrix/ble_forward.txt">Forward Call Graph</a> |
        <a href="imatrix/ble_reverse.txt">Reverse Call Graph</a> |
        <a href="imatrix/ble_xref.txt">Cross Reference</a>
    </div>
    
    <div class="module">
        <h3>CoAP</h3>
        <a href="imatrix/coap_forward.txt">Forward Call Graph</a> |
        <a href="imatrix/coap_reverse.txt">Reverse Call Graph</a> |
        <a href="imatrix/coap_xref.txt">Cross Reference</a>
    </div>
    
    <h2>Fleet-Connect-1 Modules</h2>
    <div class="module">
        <h3>OBD2</h3>
        <a href="fleet-connect/obd2_forward.txt">Forward Call Graph</a> |
        <a href="fleet-connect/obd2_reverse.txt">Reverse Call Graph</a> |
        <a href="fleet-connect/obd2_xref.txt">Cross Reference</a>
    </div>
    
    <div class="module">
        <h3>CAN Processing</h3>
        <a href="fleet-connect/can_process_forward.txt">Forward Call Graph</a> |
        <a href="fleet-connect/can_process_reverse.txt">Reverse Call Graph</a> |
        <a href="fleet-connect/can_process_xref.txt">Cross Reference</a>
    </div>
    
    <div class="module">
        <h3>Main Application</h3>
        <a href="fleet-connect/main_forward.txt">Forward Call Graph</a> |
        <a href="fleet-connect/main_reverse.txt">Reverse Call Graph</a> |
        <a href="fleet-connect/main_xref.txt">Cross Reference</a>
    </div>
</body>
</html>
EOF

echo "cflow graphs generated in $CFLOW_DIR"