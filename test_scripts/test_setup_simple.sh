#!/bin/bash

# test_setup_simple.sh
# Simple test setup that uses temporary directories (no sudo required)
# 
# This script:
# 1. Creates temporary storage directories
# 2. Builds test programs
# 3. Validates the test environment
#
# Usage: ./test_setup_simple.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Storage paths (using temporary directory)
STORAGE_BASE="/tmp/imatrix_test_storage"
CORRUPTED_PATH="${STORAGE_BASE}/corrupted"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create storage directories
create_storage_directories() {
    print_info "Creating temporary storage directories..."
    
    # Create directories
    mkdir -p "$STORAGE_BASE"
    mkdir -p "$CORRUPTED_PATH"
    
    # Set permissions
    chmod 755 "$STORAGE_BASE"
    chmod 755 "$CORRUPTED_PATH"
    
    print_success "Storage directories created at: $STORAGE_BASE"
}

# Function to build test programs
build_test_programs() {
    print_info "Building test programs..."
    
    # Build simple test (minimal dependencies)
    if make simple_test; then
        print_success "simple_test built successfully"
    else
        print_error "Failed to build simple_test"
        return 1
    fi
    
    return 0
}

# Function to run basic test
run_basic_test() {
    print_info "Running basic functionality test..."
    
    if ./simple_test; then
        print_success "Basic test passed"
        return 0
    else
        print_error "Basic test failed"
        return 1
    fi
}

# Function to display summary
display_summary() {
    echo
    echo "=================================="
    echo "Simple iMatrix Test Setup Complete"
    echo "=================================="
    echo
    echo "Storage Configuration:"
    echo "  Temporary directory: $STORAGE_BASE"
    echo "  Corrupted data:      $CORRUPTED_PATH"
    echo
    echo "Available Test Programs:"
    echo "  ✓ simple_test - Basic memory manager functionality"
    echo
    echo "Quick Start Commands:"
    echo "  ./simple_test                          # Run basic test"
    echo "  STORAGE_DIR=$STORAGE_BASE ./run_simple_tests.sh  # Run with temp storage"
    echo
    echo "Note: This setup uses temporary storage (/tmp)"
    echo "For full tiered storage testing, use ./test_setup.sh with sudo"
    echo
}

# Main execution
main() {
    echo "Simple iMatrix Memory Test Setup"
    echo "==============================="
    echo "Timestamp: $(date '+%Y%m%d_%H%M%S')"
    echo
    
    create_storage_directories
    
    if ! build_test_programs; then
        exit 1
    fi
    
    if ! run_basic_test; then
        print_warning "Setup completed but basic test failed"
    fi
    
    display_summary
    
    print_success "Simple test environment setup complete!"
}

# Run main function
main "$@"