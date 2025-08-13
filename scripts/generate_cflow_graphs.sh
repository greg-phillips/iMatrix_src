#!/bin/bash

# Script to generate call graphs using cflow and other tools

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Alternative Call Graph Generator${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMATRIX_ROOT="$(dirname "$SCRIPT_DIR")/iMatrix"
FLEET_CONNECT_ROOT="$(dirname "$SCRIPT_DIR")/Fleet-Connect-1"

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to generate cflow graphs
generate_cflow_graphs() {
    local project_root=$1
    local project_name=$2
    local output_dir="$project_root/docs/call_graphs/cflow"
    
    echo -e "${GREEN}Generating cflow graphs for $project_name...${NC}"
    
    # Create output directory
    mkdir -p "$output_dir"
    
    # Find all C source files
    cd "$project_root"
    
    # Generate text-based call graph
    echo "  Generating main call graph..."
    find . -name "*.c" -not -path "./external/*" -not -path "./build/*" | \
        xargs cflow --tree --depth=3 > "$output_dir/call_tree.txt" 2>/dev/null || \
        echo -e "  ${YELLOW}Warning: cflow encountered errors${NC}"
    
    # Generate reverse call graph (who calls what)
    echo "  Generating reverse call graph..."
    find . -name "*.c" -not -path "./external/*" -not -path "./build/*" | \
        xargs cflow --tree --reverse --depth=3 > "$output_dir/caller_tree.txt" 2>/dev/null || \
        echo -e "  ${YELLOW}Warning: cflow encountered errors${NC}"
    
    # Generate graph for specific key functions
    local key_functions=""
    if [ "$project_name" == "iMatrix" ]; then
        key_functions="main process_coap_msg coap_xmit ble_mgr_process"
    else
        key_functions="main process_obd2 can_msg_process i15765_tx_app"
    fi
    
    for func in $key_functions; do
        echo "  Generating graph for $func()..."
        find . -name "*.c" -not -path "./external/*" -not -path "./build/*" | \
            xargs cflow --tree --main=$func --depth=3 > "$output_dir/${func}_tree.txt" 2>/dev/null || \
            echo -e "    ${YELLOW}Function $func not found or error occurred${NC}"
    done
    
    echo -e "  ${GREEN}Text-based call graphs saved to $output_dir${NC}"
}

# Function to generate graphviz-compatible output using cflow2dot
generate_cflow2dot_graphs() {
    local project_root=$1
    local project_name=$2
    local output_dir="$project_root/docs/call_graphs/graphviz"
    
    echo -e "${GREEN}Generating Graphviz graphs for $project_name...${NC}"
    
    mkdir -p "$output_dir"
    cd "$project_root"
    
    # Create a Python script to convert cflow output to dot format
    cat > "$output_dir/cflow2dot.py" << 'EOF'
#!/usr/bin/env python3
import sys
import re

def cflow_to_dot(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    with open(output_file, 'w') as f:
        f.write('digraph CallGraph {\n')
        f.write('    rankdir=LR;\n')
        f.write('    node [shape=box];\n\n')
        
        stack = []
        for line in lines:
            # Count indentation level
            indent = len(line) - len(line.lstrip())
            level = indent // 4
            
            # Extract function name
            match = re.search(r'(\w+)\s*\(', line)
            if match:
                func_name = match.group(1)
                
                # Adjust stack to current level
                stack = stack[:level]
                
                # Add edge if not top level
                if stack:
                    parent = stack[-1]
                    f.write(f'    "{parent}" -> "{func_name}";\n')
                
                # Add to stack
                stack.append(func_name)
        
        f.write('}\n')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: cflow2dot.py input.txt output.dot")
        sys.exit(1)
    
    cflow_to_dot(sys.argv[1], sys.argv[2])
EOF

    chmod +x "$output_dir/cflow2dot.py"
    
    # Convert cflow output to dot format
    if [ -f "$project_root/docs/call_graphs/cflow/call_tree.txt" ]; then
        echo "  Converting call tree to Graphviz format..."
        python3 "$output_dir/cflow2dot.py" \
            "$project_root/docs/call_graphs/cflow/call_tree.txt" \
            "$output_dir/call_graph.dot"
        
        # Generate SVG if dot is available
        if command_exists dot; then
            echo "  Generating SVG from dot file..."
            dot -Tsvg "$output_dir/call_graph.dot" -o "$output_dir/call_graph.svg"
            echo -e "  ${GREEN}SVG call graph saved to $output_dir/call_graph.svg${NC}"
        fi
    fi
}

# Function to generate module dependency graph
generate_module_deps() {
    local project_root=$1
    local project_name=$2
    local output_dir="$project_root/docs/call_graphs/modules"
    
    echo -e "${GREEN}Generating module dependency graph for $project_name...${NC}"
    
    mkdir -p "$output_dir"
    
    # Create a script to analyze #include dependencies
    cat > "$output_dir/analyze_deps.py" << 'EOF'
#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict

def analyze_includes(root_dir):
    includes = defaultdict(set)
    
    for root, dirs, files in os.walk(root_dir):
        # Skip external and build directories
        if 'external' in root or 'build' in root:
            continue
            
        for file in files:
            if file.endswith(('.h', '.c')):
                filepath = os.path.join(root, file)
                module = os.path.basename(os.path.dirname(filepath))
                
                with open(filepath, 'r', errors='ignore') as f:
                    content = f.read()
                    
                # Find local includes
                local_includes = re.findall(r'#include\s*"([^"]+)"', content)
                for inc in local_includes:
                    inc_module = os.path.basename(os.path.dirname(inc))
                    if inc_module and inc_module != module:
                        includes[module].add(inc_module)
    
    return includes

def write_dot(includes, output_file):
    with open(output_file, 'w') as f:
        f.write('digraph ModuleDependencies {\n')
        f.write('    rankdir=TB;\n')
        f.write('    node [shape=box, style=filled, fillcolor=lightblue];\n\n')
        
        for module, deps in includes.items():
            for dep in deps:
                f.write(f'    "{module}" -> "{dep}";\n')
        
        f.write('}\n')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: analyze_deps.py root_dir output.dot")
        sys.exit(1)
    
    includes = analyze_includes(sys.argv[1])
    write_dot(includes, sys.argv[2])
EOF

    chmod +x "$output_dir/analyze_deps.py"
    
    # Generate module dependency graph
    echo "  Analyzing module dependencies..."
    python3 "$output_dir/analyze_deps.py" "$project_root" "$output_dir/module_deps.dot"
    
    if command_exists dot; then
        dot -Tsvg "$output_dir/module_deps.dot" -o "$output_dir/module_deps.svg"
        echo -e "  ${GREEN}Module dependency graph saved to $output_dir/module_deps.svg${NC}"
    fi
}

# Main execution
echo ""
echo "Checking for required tools..."

if ! command_exists cflow; then
    echo -e "${YELLOW}Warning: cflow is not installed${NC}"
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install cflow"
    echo "  macOS: brew install cflow"
    echo ""
    echo "Skipping cflow graph generation..."
else
    # Generate cflow graphs for iMatrix
    if [ -d "$IMATRIX_ROOT" ]; then
        generate_cflow_graphs "$IMATRIX_ROOT" "iMatrix"
        generate_cflow2dot_graphs "$IMATRIX_ROOT" "iMatrix"
    fi
    
    # Generate cflow graphs for Fleet-Connect-1
    if [ -d "$FLEET_CONNECT_ROOT" ]; then
        generate_cflow_graphs "$FLEET_CONNECT_ROOT" "Fleet-Connect-1"
        generate_cflow2dot_graphs "$FLEET_CONNECT_ROOT" "Fleet-Connect-1"
    fi
fi

# Generate module dependency graphs (doesn't require cflow)
if [ -d "$IMATRIX_ROOT" ]; then
    generate_module_deps "$IMATRIX_ROOT" "iMatrix"
fi

if [ -d "$FLEET_CONNECT_ROOT" ]; then
    generate_module_deps "$FLEET_CONNECT_ROOT" "Fleet-Connect-1"
fi

echo ""
echo -e "${BLUE}Call graph generation complete!${NC}"
echo ""
echo "Generated files:"
echo "  Text-based call trees: docs/call_graphs/cflow/*.txt"
echo "  Graphviz dot files: docs/call_graphs/graphviz/*.dot"
echo "  SVG visualizations: docs/call_graphs/*/*.svg"
echo ""
echo "To view text-based graphs:"
echo "  less $IMATRIX_ROOT/docs/call_graphs/cflow/call_tree.txt"
echo ""
echo "To view graphical graphs (if generated):"
echo "  Open the .svg files in a web browser"