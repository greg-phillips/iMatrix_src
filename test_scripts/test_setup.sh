#!/bin/bash

# test_setup.sh
# Initialize file system and build environment for iMatrix memory tests
# 
# This script:
# 1. Creates required storage directories
# 2. Sets proper permissions
# 3. Builds test programs
# 4. Validates the test environment
#
# Usage: ./test_setup.sh [options]
# Options:
#   -f, --force       Force rebuild even if programs exist
#   -c, --clean       Clean all build artifacts first
#   -v, --verbose     Enable verbose output
#   -h, --help        Show this help message

set -e  # Exit on any error

# Default options
FORCE_REBUILD=false
CLEAN_FIRST=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Storage paths (matching the iMatrix configuration)
STORAGE_BASE="/usr/qk/etc/sv/test_scripts"
CORRUPTED_PATH="${STORAGE_BASE}/corrupted"
JOURNAL_FILE="${STORAGE_BASE}/recovery.journal"
JOURNAL_BACKUP="${STORAGE_BASE}/recovery.journal.bak"

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

print_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Function to show help
show_help() {
    cat << EOF
iMatrix Memory Test Setup Script
================================

This script initializes the file system and builds test programs for iMatrix memory testing.

Usage: $0 [options]

Options:
    -f, --force       Force rebuild even if programs exist
    -c, --clean       Clean all build artifacts first
    -v, --verbose     Enable verbose output
    -h, --help        Show this help message

Storage Directories Created:
    ${STORAGE_BASE}/          - Main storage directory
    ${STORAGE_BASE}/corrupted/    - Corrupted data storage
    
Test Programs Built:
    simple_memory_test           - Basic memory manager test
    tiered_storage_test          - Full tiered storage test
    performance_test             - Performance testing program
    diagnostic_test              - Comprehensive diagnostic testing suite
    spillover_test               - Memory spillover testing
    module_link_test            - Module linkage testing
    minimal_test                - Minimal functionality test
    ultra_minimal_test          - Ultra minimal test for debugging
    size_check_test             - Structure size validation test
    bare_minimal_test           - Bare minimal test (init only)

Examples:
    $0                           # Basic setup
    $0 --verbose                 # Setup with verbose output
    $0 --clean --force          # Clean rebuild
    $0 --force                  # Force rebuild without clean

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_REBUILD=true
                shift
                ;;
            -c|--clean)
                CLEAN_FIRST=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Function to check if running as root/sudo for directory creation
check_sudo_needed() {
    if [[ ! -d "$STORAGE_BASE" ]]; then
        if [[ $EUID -ne 0 ]]; then
            print_warning "Storage directories don't exist and script is not running as root."
            print_info "Will attempt to create directories. You may be prompted for sudo password."
            return 1
        fi
    fi
    return 0
}

# Function to create storage directories
create_storage_directories() {
    print_info "Creating storage directories..."
    
    # Try to create directories without sudo first
    local created_successfully=true
    
    # Create main storage directory
    if [[ ! -d "$STORAGE_BASE" ]]; then
        print_verbose "Creating main storage directory: $STORAGE_BASE"
        if mkdir -p "$STORAGE_BASE" 2>/dev/null; then
            print_verbose "Created directory successfully"
        else
            print_warning "Failed to create directory without sudo. Trying with sudo..."
            if command -v sudo >/dev/null 2>&1; then
                sudo mkdir -p "$STORAGE_BASE" || created_successfully=false
            else
                print_error "sudo not available and cannot create directory"
                created_successfully=false
            fi
        fi
    else
        print_verbose "Main storage directory already exists: $STORAGE_BASE"
    fi
    
    # Create corrupted data directory
    if [[ ! -d "$CORRUPTED_PATH" ]] && [[ "$created_successfully" == "true" ]]; then
        print_verbose "Creating corrupted data directory: $CORRUPTED_PATH"
        mkdir -p "$CORRUPTED_PATH" 2>/dev/null || {
            if command -v sudo >/dev/null 2>&1; then
                sudo mkdir -p "$CORRUPTED_PATH" || created_successfully=false
            else
                created_successfully=false
            fi
        }
    elif [[ -d "$CORRUPTED_PATH" ]]; then
        print_verbose "Corrupted data directory already exists: $CORRUPTED_PATH"
    fi
    
    # Set ownership and permissions if directories were created
    if [[ "$created_successfully" == "true" ]] && [[ -d "$STORAGE_BASE" ]]; then
        print_verbose "Setting ownership and permissions..."
        
        # Try without sudo first
        if chown -R $USER:$USER "$STORAGE_BASE" 2>/dev/null && chmod -R 755 "$STORAGE_BASE" 2>/dev/null; then
            print_verbose "Permissions set successfully"
        else
            # Try with sudo if available
            if command -v sudo >/dev/null 2>&1; then
                sudo chown -R $USER:$USER "$STORAGE_BASE" 2>/dev/null || true
                sudo chmod -R 755 "$STORAGE_BASE" 2>/dev/null || true
            fi
        fi
        
        print_success "Storage directories created and configured"
    else
        print_warning "Could not create storage directories. Tests may run in fallback mode."
        print_info "You can manually create: $STORAGE_BASE"
    fi
}

# Function to clean existing test data
clean_test_data() {
    print_info "Cleaning existing test data..."
    
    if [[ -d "$STORAGE_BASE" ]]; then
        print_verbose "Removing .dat files..."
        rm -f "${STORAGE_BASE}"/*.dat
        
        print_verbose "Removing journal files..."
        rm -f "$JOURNAL_FILE" "${JOURNAL_BACKUP}"
        
        print_verbose "Removing corrupted data..."
        rm -f "${CORRUPTED_PATH}"/*
        
        print_success "Test data cleaned"
    else
        print_verbose "No existing test data to clean"
    fi
}

# Function to check build prerequisites
check_build_prerequisites() {
    print_info "Checking build prerequisites..."
    
    # Check for required tools
    local missing_tools=()
    
    if ! command -v gcc &> /dev/null; then
        missing_tools+=("gcc")
    fi
    
    if ! command -v make &> /dev/null; then
        missing_tools+=("make")
    fi
    
    if ! command -v cmake &> /dev/null; then
        missing_tools+=("cmake")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_info "Install missing tools with: sudo apt-get install ${missing_tools[*]}"
        return 1
    fi
    
    # Check for required directories
    if [[ ! -d "../iMatrix" ]]; then
        print_error "iMatrix source directory not found at ../iMatrix"
        print_info "Ensure you're running this script from the memory_test directory"
        return 1
    fi
    
    # Check for CMakeLists.txt
    if [[ ! -f "CMakeLists.txt" ]]; then
        print_error "CMakeLists.txt not found in current directory"
        return 1
    fi
    
    print_success "Build prerequisites satisfied"
    return 0
}

# Function to build test programs
build_test_programs() {
    print_info "Building test programs..."
    
    # Clean if requested
    if [[ "$CLEAN_FIRST" == "true" ]]; then
        print_verbose "Cleaning build artifacts..."
        if [[ -d "build" ]]; then
            rm -rf build
        fi
        # Also clean any executables in main directory from previous builds
        rm -f simple_memory_test tiered_storage_test performance_test diagnostic_test
        rm -f spillover_test module_link_test minimal_test ultra_minimal_test
        rm -f size_check_test bare_minimal_test comprehensive_memory_test
        rm -f real_world_test test_disk_batching
    fi
    
    # Build all test programs using CMake in build directory
    print_verbose "Building all test programs..."
    
    # Create build directory if it doesn't exist
    mkdir -p build
    cd build
    
    # Run CMake configuration
    print_verbose "Configuring CMake..."
    if cmake ..; then
        print_verbose "CMake configuration successful"
    else
        print_error "CMake configuration failed"
        cd ..
        return 1
    fi
    
    # Build all targets
    print_verbose "Building all targets..."
    if make -j$(nproc); then
        print_success "All test programs built successfully"
        cd ..
    else
        print_error "Failed to build test programs"
        cd ..
        return 1
    fi
    
    return 0
}

# Function to validate test environment
validate_test_environment() {
    print_info "Validating test environment..."
    
    # Check storage directories (warn but don't fail if missing)
    if [[ ! -d "$STORAGE_BASE" ]]; then
        print_warning "Main storage directory not found: $STORAGE_BASE"
        print_info "Tests will run without persistent storage"
    else
        print_verbose "Main storage directory found: $STORAGE_BASE"
        
        if [[ ! -d "$CORRUPTED_PATH" ]]; then
            print_warning "Corrupted data directory not found: $CORRUPTED_PATH"
        else
            print_verbose "Corrupted data directory found: $CORRUPTED_PATH"
        fi
        
        # Check permissions
        if [[ ! -w "$STORAGE_BASE" ]]; then
            print_warning "Storage directory not writable: $STORAGE_BASE"
            print_info "Some tests may not work correctly"
        else
            print_verbose "Storage directory is writable"
        fi
    fi
    
    # Check for test programs
    local available_programs=()
    local missing_programs=()
    
    # List of all test programs
    local test_programs=(
        "simple_memory_test"
        "tiered_storage_test"
        "performance_test"
        "diagnostic_test"
        "spillover_test"
        "module_link_test"
        "minimal_test"
        "ultra_minimal_test"
        "size_check_test"
        "bare_minimal_test"
        "comprehensive_memory_test"
        "real_world_test"
        "test_disk_batching"
    )
    
    # Check each program
    for prog in "${test_programs[@]}"; do
        if [[ -x "./build/$prog" ]]; then
            available_programs+=("$prog")
        else
            missing_programs+=("$prog")
        fi
    done
    
    # Report status
    if [[ ${#available_programs[@]} -gt 0 ]]; then
        print_success "Available test programs: ${available_programs[*]}"
    fi
    
    if [[ ${#missing_programs[@]} -gt 0 ]]; then
        if [[ "${missing_programs[*]}" == *"simple_memory_test"* ]]; then
            print_error "Critical: simple_memory_test program not available"
            return 1
        else
            print_warning "Optional test programs not available: ${missing_programs[*]}"
            print_verbose "These require additional iMatrix dependencies"
        fi
    fi
    
    print_success "Test environment validation complete"
    return 0
}

# Function to run basic smoke test
run_smoke_test() {
    print_info "Running basic smoke test..."
    
    # Try bare_minimal_test first as it's the most basic
    if [[ -x "./build/bare_minimal_test" ]]; then
        print_verbose "Running bare_minimal_test to verify basic initialization..."
        if ./build/bare_minimal_test > /tmp/smoke_test.log 2>&1; then
            local test_result=$(tail -5 /tmp/smoke_test.log)
            if [[ "$test_result" == *"Test completed"* ]]; then
                print_success "Basic initialization test passed"
                
                # Try size_check_test next
                if [[ -x "./build/size_check_test" ]]; then
                    print_verbose "Running size_check_test to verify structure sizes..."
                    if ./build/size_check_test > /tmp/smoke_test2.log 2>&1; then
                        print_success "Structure size validation passed"
                        return 0
                    else
                        print_warning "Structure size validation failed but basic init works"
                        if [[ "$VERBOSE" == "true" ]]; then
                            echo "Size check output:"
                            cat /tmp/smoke_test2.log
                        fi
                        return 0  # Still consider it a success since basic init works
                    fi
                fi
                return 0
            else
                print_warning "Basic initialization test completed with unexpected output"
                if [[ "$VERBOSE" == "true" ]]; then
                    echo "Last few lines of test output:"
                    tail -5 /tmp/smoke_test.log
                fi
                return 1
            fi
        else
            print_error "Smoke test failed - bare_minimal_test execution error"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "Error output:"
                cat /tmp/smoke_test.log
            fi
            return 1
        fi
    else
        print_warning "Skipping smoke test - bare_minimal_test not available"
        return 0
    fi
}

# Function to display environment summary
display_summary() {
    echo
    echo "=================================="
    echo "iMatrix Test Environment Summary"
    echo "=================================="
    echo
    echo "Storage Configuration:"
    echo "  Main directory:    $STORAGE_BASE"
    echo "  Corrupted data:    $CORRUPTED_PATH"
    echo "  Journal file:      $JOURNAL_FILE"
    echo
    echo "Available Test Programs:"
    
    # Define test programs with descriptions
    declare -A test_descriptions=(
        ["simple_memory_test"]="Basic memory manager functionality"
        ["tiered_storage_test"]="Full tiered storage test"
        ["performance_test"]="Performance testing program"
        ["diagnostic_test"]="Comprehensive diagnostic testing suite"
        ["spillover_test"]="Memory spillover testing"
        ["module_link_test"]="Module linkage testing"
        ["minimal_test"]="Minimal functionality test"
        ["ultra_minimal_test"]="Ultra minimal test for debugging"
        ["size_check_test"]="Structure size validation test"
        ["bare_minimal_test"]="Bare minimal test (init only)"
        ["comprehensive_memory_test"]="Comprehensive test of all memory manager functions"
        ["real_world_test"]="Real-world usage patterns test"
        ["test_disk_batching"]="Disk batching operations test"
    )
    
    # Check and display each program
    for prog in simple_memory_test tiered_storage_test performance_test diagnostic_test spillover_test module_link_test minimal_test ultra_minimal_test size_check_test bare_minimal_test comprehensive_memory_test real_world_test test_disk_batching; do
        if [[ -x "./build/$prog" ]]; then
            printf "  ✓ %-25s - %s\n" "$prog" "${test_descriptions[$prog]}"
        else
            printf "  ✗ %-25s - Not available\n" "$prog"
        fi
    done
    
    echo
    echo "Quick Start Commands:"
    echo "  Basic Tests:"
    echo "    ./build/bare_minimal_test      # Test basic initialization only"
    echo "    ./build/size_check_test        # Verify structure sizes"
    echo "    ./build/minimal_test           # Run minimal functionality test"
    echo "    ./build/simple_memory_test     # Run basic memory manager test"
    echo
    echo "  Advanced Tests:"
    if [[ -x "./build/module_link_test" ]]; then
        echo "    ./build/module_link_test       # Test module linkage"
    fi
    if [[ -x "./build/spillover_test" ]]; then
        echo "    ./build/spillover_test         # Test memory spillover"
    fi
    if [[ -x "./build/performance_test" ]]; then
        echo "    ./build/performance_test       # Run performance benchmarks"
    fi
    if [[ -x "./build/diagnostic_test" ]]; then
        echo "    ./build/diagnostic_test        # Run comprehensive diagnostics"
    fi
    if [[ -x "./build/tiered_storage_test" ]]; then
        echo "    ./build/tiered_storage_test    # Run full tiered storage test"
    fi
    echo
    echo "  Comprehensive Testing:"
    if [[ -x "./build/comprehensive_memory_test" ]]; then
        echo "    ./build/comprehensive_memory_test       # Run all memory manager tests"
        echo "    ./build/comprehensive_memory_test -h    # Show test options"
        echo ""
        echo "  Disk Simulation Examples:"
        echo "    IMX_TEST_DISK_USAGE=79 ./build/comprehensive_memory_test"
        echo "    IMX_TEST_DISK_USAGE=95 ./build/comprehensive_memory_test --section 5"
    fi
    if [[ -x "./build/real_world_test" ]]; then
        echo "    ./build/real_world_test        # Test real-world usage patterns"
    fi
    if [[ -x "./build/test_disk_batching" ]]; then
        echo "    ./build/test_disk_batching     # Test disk batching operations"
    fi
    echo
    echo "  Utility Scripts:"
    echo "    ./run_tiered_storage_tests.sh  # Run automated test suite"
    echo "    ./monitor_tiered_storage.sh    # Monitor storage in real-time"
    echo "    ./clear_old_data.sh --dry-run  # Preview cleanup of old data"
    echo "    ./clear_old_data.sh --help     # Show cleanup options"
    echo
    echo "Environment Status: Ready for Testing"
    echo
    
    # Add note about storage directory if it doesn't exist
    if [[ ! -d "$STORAGE_BASE" ]]; then
        echo "Note: For persistent storage support, create the directory manually:"
        echo "  sudo mkdir -p $STORAGE_BASE"
        echo "  sudo chown $USER:$USER $STORAGE_BASE"
        echo
    fi
}

# Main execution function
main() {
    echo "iMatrix Memory Test Setup"
    echo "========================="
    echo "Timestamp: $(date '+%Y%m%d_%H%M%S')"
    echo
    
    # Parse arguments
    parse_args "$@"
    
    # Execute setup steps
    if ! check_build_prerequisites; then
        exit 1
    fi
    
    if ! create_storage_directories; then
        exit 1
    fi
    
    clean_test_data
    
    if ! build_test_programs; then
        exit 1
    fi
    
    if ! validate_test_environment; then
        exit 1
    fi
    
    if ! run_smoke_test; then
        print_warning "Setup completed but smoke test failed"
        print_info "Environment may still be usable for testing"
    fi
    
    display_summary
    
    print_success "Test environment setup complete!"
}

# Run main function with all arguments
main "$@"