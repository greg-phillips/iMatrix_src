#!/bin/bash

# Script to generate directory-level function summaries for iMatrix and Fleet-Connect-1

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Generating Function Summaries for iMatrix and Fleet-Connect-1${NC}"

# Function to extract function declarations from header files
extract_functions() {
    local dir=$1
    local output_file=$2
    
    echo "# Function Summary: $(basename $dir)" > "$output_file"
    echo "" >> "$output_file"
    echo "Generated on: $(date)" >> "$output_file"
    echo "" >> "$output_file"
    
    # Find all header files
    local headers=$(find "$dir" -maxdepth 1 -name "*.h" -type f | sort)
    
    if [ -z "$headers" ]; then
        echo "No header files found in this directory." >> "$output_file"
        return
    fi
    
    for header in $headers; do
        echo "## $(basename $header)" >> "$output_file"
        echo "" >> "$output_file"
        
        # Extract function declarations (simplified - looks for patterns)
        # This captures most function declarations but may need refinement
        grep -E "^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]+\**[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*\(" "$header" | \
        grep -v "^[[:space:]]*typedef" | \
        grep -v "^[[:space:]]*#" | \
        sed 's/^[[:space:]]*//' | \
        sed 's/[[:space:]]*{.*$//' | \
        sed 's/;$//' | \
        while read -r func; do
            echo "- \`$func\`" >> "$output_file"
        done
        
        echo "" >> "$output_file"
    done
}

# Function to generate summaries for a project
generate_project_summaries() {
    local project_root=$1
    local project_name=$2
    
    echo -e "${GREEN}Processing $project_name...${NC}"
    
    # Create function_summaries directory
    mkdir -p "$project_root/docs/function_summaries"
    
    # Generate summaries for each major directory
    for dir in "$project_root"/*/ ; do
        if [ -d "$dir" ]; then
            dirname=$(basename "$dir")
            
            # Skip certain directories
            if [[ "$dirname" == "build" || "$dirname" == "docs" || "$dirname" == "external" || "$dirname" == "archive" || "$dirname" == "CMakeFiles" ]]; then
                continue
            fi
            
            echo -e "  ${YELLOW}Processing $dirname...${NC}"
            
            output_file="$project_root/docs/function_summaries/${dirname}_functions.md"
            extract_functions "$dir" "$output_file"
            
            # For directories with subdirectories, process them too
            for subdir in "$dir"*/ ; do
                if [ -d "$subdir" ]; then
                    subdirname=$(basename "$subdir")
                    echo -e "    Processing $subdirname..."
                    
                    output_file="$project_root/docs/function_summaries/${dirname}_${subdirname}_functions.md"
                    extract_functions "$subdir" "$output_file"
                fi
            done
        fi
    done
    
    # Generate index file
    index_file="$project_root/docs/function_summaries/README.md"
    echo "# Function Summaries for $project_name" > "$index_file"
    echo "" >> "$index_file"
    echo "This directory contains automatically generated function summaries for each module." >> "$index_file"
    echo "" >> "$index_file"
    echo "## Directory Summaries" >> "$index_file"
    echo "" >> "$index_file"
    
    for summary in "$project_root/docs/function_summaries"/*.md; do
        if [ -f "$summary" ] && [ "$summary" != "$index_file" ]; then
            filename=$(basename "$summary")
            module_name=${filename%_functions.md}
            echo "- [$module_name]($filename)" >> "$index_file"
        fi
    done
    
    echo "" >> "$index_file"
    echo "## Generation" >> "$index_file"
    echo "" >> "$index_file"
    echo "These summaries were generated using \`generate_function_summaries.sh\`." >> "$index_file"
    echo "To regenerate: \`./scripts/generate_function_summaries.sh\`" >> "$index_file"
}

# Main execution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMATRIX_ROOT="$(dirname "$SCRIPT_DIR")/iMatrix"
FLEET_CONNECT_ROOT="$(dirname "$SCRIPT_DIR")/Fleet-Connect-1"

# Generate summaries for iMatrix
if [ -d "$IMATRIX_ROOT" ]; then
    generate_project_summaries "$IMATRIX_ROOT" "iMatrix"
else
    echo -e "${YELLOW}Warning: iMatrix directory not found at $IMATRIX_ROOT${NC}"
fi

# Generate summaries for Fleet-Connect-1
if [ -d "$FLEET_CONNECT_ROOT" ]; then
    generate_project_summaries "$FLEET_CONNECT_ROOT" "Fleet-Connect-1"
else
    echo -e "${YELLOW}Warning: Fleet-Connect-1 directory not found at $FLEET_CONNECT_ROOT${NC}"
fi

echo -e "${BLUE}Function summary generation complete!${NC}"
echo ""
echo "Summaries generated in:"
echo "  - $IMATRIX_ROOT/docs/function_summaries/"
echo "  - $FLEET_CONNECT_ROOT/docs/function_summaries/"