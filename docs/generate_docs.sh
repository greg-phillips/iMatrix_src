#!/bin/bash
# Documentation generation script for iMatrix and Fleet-Connect-1 projects
# This script generates comprehensive documentation including API docs and call graphs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$ROOT_DIR/docs"

echo "=========================================="
echo "Documentation Generation Script"
echo "=========================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
echo "Checking for required tools..."
if ! command_exists doxygen; then
    echo "Error: doxygen is not installed. Please install it first."
    exit 1
fi

if ! command_exists dot; then
    echo "Warning: graphviz (dot) is not installed. Call graphs will not be generated."
    echo "Install graphviz for full functionality."
fi

# Generate iMatrix documentation
echo ""
echo "Generating iMatrix documentation..."
cd "$ROOT_DIR/iMatrix"
if [ -f "Doxyfile" ]; then
    doxygen Doxyfile
    echo "iMatrix documentation generated successfully."
else
    echo "Error: Doxyfile not found in iMatrix directory."
fi

# Generate Fleet-Connect-1 documentation
echo ""
echo "Generating Fleet-Connect-1 documentation..."
cd "$ROOT_DIR/Fleet-Connect-1"
if [ -f "Doxyfile" ]; then
    doxygen Doxyfile
    echo "Fleet-Connect-1 documentation generated successfully."
else
    echo "Error: Doxyfile not found in Fleet-Connect-1 directory."
fi

# Check if cflow is available for text-based call graphs
if command_exists cflow; then
    echo ""
    echo "Generating cflow call graphs..."
    "$SCRIPT_DIR/generate_cflow_graphs.sh"
fi

# Generate index page
echo ""
echo "Generating documentation index..."
cat > "$DOCS_DIR/index.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>iMatrix and Fleet-Connect-1 Documentation</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2 {
            color: #333;
        }
        .project {
            border: 1px solid #ddd;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>iMatrix and Fleet-Connect-1 Documentation</h1>
    
    <div class="project">
        <h2>iMatrix IoT Platform</h2>
        <p>Comprehensive IoT platform with BLE, WiFi, CoAP, and cellular connectivity</p>
        <ul>
            <li><a href="api/iMatrix/html/index.html">API Documentation</a></li>
            <li><a href="architecture/call_graphs/imatrix/">Call Graphs</a></li>
            <li><a href="summaries/imatrix/">Module Summaries</a></li>
        </ul>
    </div>
    
    <div class="project">
        <h2>Fleet-Connect-1 CAN/OBD2 Gateway</h2>
        <p>Vehicle CAN bus and OBD2 gateway for fleet management</p>
        <ul>
            <li><a href="api/Fleet-Connect-1/html/index.html">API Documentation</a></li>
            <li><a href="architecture/call_graphs/fleet-connect/">Call Graphs</a></li>
            <li><a href="summaries/fleet-connect/">Module Summaries</a></li>
        </ul>
    </div>
    
    <div class="project">
        <h2>Architecture Documentation</h2>
        <ul>
            <li><a href="architecture/function_analysis/">Function Pointer Analysis</a></li>
            <li><a href="architecture/module_dependencies/">Module Dependencies</a></li>
            <li><a href="documentation_plan.md">Documentation Plan</a></li>
        </ul>
    </div>
    
    <p><em>Generated on $(date)</em></p>
</body>
</html>
EOF

echo ""
echo "=========================================="
echo "Documentation generation complete!"
echo "Open $DOCS_DIR/index.html to view the documentation."
echo "=========================================="