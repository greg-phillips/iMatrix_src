#!/bin/bash

# Script to generate Doxygen documentation with call graphs

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Doxygen Documentation Generator${NC}"

# Check if Doxygen is installed
if ! command -v doxygen &> /dev/null; then
    echo -e "${RED}Error: Doxygen is not installed!${NC}"
    echo "Please install Doxygen first:"
    echo "  Ubuntu/Debian: sudo apt-get install doxygen graphviz"
    echo "  macOS: brew install doxygen graphviz"
    echo "  RHEL/CentOS: sudo yum install doxygen graphviz"
    exit 1
fi

# Check if Graphviz is installed (needed for call graphs)
if ! command -v dot &> /dev/null; then
    echo -e "${YELLOW}Warning: Graphviz is not installed!${NC}"
    echo "Call graphs will not be generated without Graphviz."
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install graphviz"
    echo "  macOS: brew install graphviz"
    echo "  RHEL/CentOS: sudo yum install graphviz"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMATRIX_ROOT="$(dirname "$SCRIPT_DIR")/iMatrix"
FLEET_CONNECT_ROOT="$(dirname "$SCRIPT_DIR")/Fleet-Connect-1"

# Function to generate docs for a project
generate_docs() {
    local project_root=$1
    local project_name=$2
    
    echo -e "${GREEN}Generating documentation for $project_name...${NC}"
    
    cd "$project_root"
    
    if [ ! -f "Doxyfile" ]; then
        echo -e "${RED}Error: Doxyfile not found in $project_root${NC}"
        return 1
    fi
    
    # Clean previous documentation
    if [ -d "docs/doxygen" ]; then
        echo "  Cleaning previous documentation..."
        rm -rf "docs/doxygen"
    fi
    
    # Run Doxygen
    echo "  Running Doxygen..."
    doxygen Doxyfile 2>&1 | grep -E "(error|warning|Generating)" || true
    
    if [ -d "docs/doxygen/html" ]; then
        echo -e "  ${GREEN}Documentation generated successfully!${NC}"
        
        # Count generated files
        local html_count=$(find docs/doxygen/html -name "*.html" | wc -l)
        local svg_count=$(find docs/doxygen/html -name "*.svg" 2>/dev/null | wc -l || echo "0")
        
        echo "  Generated: $html_count HTML files, $svg_count call graphs"
        
        # Check for call graph examples
        if [ $svg_count -gt 0 ]; then
            echo -e "  ${GREEN}Call graphs generated successfully!${NC}"
            echo "  Sample call graphs:"
            find docs/doxygen/html -name "*_cgraph.svg" -o -name "*_icgraph.svg" | head -5 | while read graph; do
                echo "    - $(basename $graph)"
            done
        else
            echo -e "  ${YELLOW}No call graphs generated. Make sure Graphviz is installed.${NC}"
        fi
    else
        echo -e "  ${RED}Documentation generation failed!${NC}"
        return 1
    fi
}

# Generate documentation for iMatrix
if [ -d "$IMATRIX_ROOT" ]; then
    generate_docs "$IMATRIX_ROOT" "iMatrix"
else
    echo -e "${YELLOW}Warning: iMatrix directory not found at $IMATRIX_ROOT${NC}"
fi

echo ""

# Generate documentation for Fleet-Connect-1
if [ -d "$FLEET_CONNECT_ROOT" ]; then
    generate_docs "$FLEET_CONNECT_ROOT" "Fleet-Connect-1"
else
    echo -e "${YELLOW}Warning: Fleet-Connect-1 directory not found at $FLEET_CONNECT_ROOT${NC}"
fi

echo ""
echo -e "${BLUE}Documentation generation complete!${NC}"
echo ""
echo "To view the documentation:"
echo "  iMatrix: Open $IMATRIX_ROOT/docs/doxygen/html/index.html"
echo "  Fleet-Connect-1: Open $FLEET_CONNECT_ROOT/docs/doxygen/html/index.html"
echo ""
echo "Call graphs (if generated) can be found in:"
echo "  - *_cgraph.svg: Call graphs (functions called by this function)"
echo "  - *_icgraph.svg: Caller graphs (functions that call this function)"