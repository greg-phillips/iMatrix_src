#!/bin/bash

# clear_old_data.sh
# 
# Comprehensive data cleanup script for iMatrix Tiered Storage System
# Safely removes old test data, build artifacts, and log files
# Supports both test and production environments with selective cleanup options
#
# Usage: ./clear_old_data.sh [options]
# Options:
#   -t, --test-only       Clean only test environment data
#   -p, --prod-only       Clean only production environment data
#   -a, --age DAYS        Clean files older than N days
#   -f, --file-types      Specify file types to clean (imx,dat,log,journal)
#   -d, --dry-run         Show what would be deleted without deleting
#   -i, --interactive     Interactive mode with confirmations
#   -v, --verbose         Verbose output
#   -b, --backup          Create backup before deletion
#   -h, --help            Show this help message
#
# Examples:
#   ./clear_old_data.sh --dry-run          # Preview cleanup
#   ./clear_old_data.sh --test-only -i     # Clean test data interactively
#   ./clear_old_data.sh --age 7 -v         # Clean files older than 7 days
#   ./clear_old_data.sh --file-types imx,log  # Clean only .imx and .log files

set -e  # Exit on any error

# Default configuration
TEST_STORAGE_DIR="/tmp/imatrix_test_storage"
PROD_STORAGE_DIR="/usr/qk/etc/sv/FC-1/history"
BUILD_DIR="./build"
LOG_DIR="./test_logs"
BACKUP_DIR="./backup_$(date +%Y%m%d_%H%M%S)"

# Default options
CLEAN_TEST=true
CLEAN_PROD=true
AGE_DAYS=0
FILE_TYPES="all"
DRY_RUN=false
INTERACTIVE=false
VERBOSE=false
CREATE_BACKUP=false
FORCE_CLEANUP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Statistics
TOTAL_FILES_FOUND=0
TOTAL_SIZE_FOUND=0
TOTAL_FILES_DELETED=0
TOTAL_SIZE_DELETED=0

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

print_dry_run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would delete: $1"
    fi
}

# Function to show help
show_help() {
    cat << EOF
iMatrix Data Cleanup Script
==========================

This script safely removes old test data, build artifacts, and log files from both
test and production environments.

Usage: $0 [options]

Options:
    -t, --test-only       Clean only test environment data
    -p, --prod-only       Clean only production environment data
    -a, --age DAYS        Clean files older than N days (0 = all files)
    -f, --file-types      Specify file types to clean (imx,dat,log,journal,all)
    -d, --dry-run         Show what would be deleted without deleting
    -i, --interactive     Interactive mode with confirmations
    -v, --verbose         Verbose output
    -b, --backup          Create backup before deletion
    --force              Skip safety confirmations (use with caution)
    -h, --help            Show this help message

Storage Locations:
    Test environment:     $TEST_STORAGE_DIR
    Production environment: $PROD_STORAGE_DIR
    Build artifacts:      $BUILD_DIR
    Log files:           $LOG_DIR

File Types:
    imx      - Test data files (sector_*.imx)
    dat      - Production data files (*.dat)
    log      - Log files (*.log)
    journal  - Recovery journal files (recovery.journal*)
    all      - All supported file types

Examples:
    $0 --dry-run                    # Preview what would be cleaned
    $0 --test-only --interactive    # Clean test data with confirmations
    $0 --age 7 --verbose           # Clean files older than 7 days
    $0 --file-types imx,log        # Clean only .imx and .log files
    $0 --backup --force            # Backup then force cleanup all data

Safety Features:
    - Confirmation prompts for destructive operations
    - Automatic detection of running tests
    - Backup options for critical data
    - Dry-run mode to preview operations
    - Age-based filtering to preserve recent data

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--test-only)
                CLEAN_TEST=true
                CLEAN_PROD=false
                shift
                ;;
            -p|--prod-only)
                CLEAN_TEST=false
                CLEAN_PROD=true
                shift
                ;;
            -a|--age)
                AGE_DAYS="$2"
                shift 2
                ;;
            -f|--file-types)
                FILE_TYPES="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -i|--interactive)
                INTERACTIVE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -b|--backup)
                CREATE_BACKUP=true
                shift
                ;;
            --force)
                FORCE_CLEANUP=true
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

# Function to check if tests are currently running
check_running_tests() {
    print_info "Checking for running tests..."
    
    # Check for running test processes
    if pgrep -f "simple_memory_test|tiered_storage_test|performance_test|diagnostic_test" > /dev/null; then
        print_warning "Active test processes detected!"
        if [[ "$INTERACTIVE" == "true" ]] && [[ "$FORCE_CLEANUP" == "false" ]]; then
            echo -n "Continue cleanup anyway? (y/N): "
            read -r response
            if [[ "$response" != "y" ]] && [[ "$response" != "Y" ]]; then
                print_info "Cleanup cancelled by user"
                exit 0
            fi
        elif [[ "$FORCE_CLEANUP" == "false" ]]; then
            print_error "Cannot cleanup while tests are running. Use --force to override."
            exit 1
        fi
    fi
    
    print_verbose "No running tests detected"
}

# Function to get file size in bytes
get_file_size() {
    local file="$1"
    if [[ -f "$file" ]]; then
        stat -c%s "$file" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

# Function to format bytes to human readable
format_bytes() {
    local bytes=$1
    if [[ $bytes -lt 1024 ]]; then
        echo "${bytes}B"
    elif [[ $bytes -lt 1048576 ]]; then
        echo "$((bytes/1024))KB"
    elif [[ $bytes -lt 1073741824 ]]; then
        echo "$((bytes/1048576))MB"
    else
        echo "$((bytes/1073741824))GB"
    fi
}

# Function to check if file should be cleaned based on age
should_clean_by_age() {
    local file="$1"
    
    if [[ $AGE_DAYS -eq 0 ]]; then
        return 0  # Clean all files
    fi
    
    if [[ ! -f "$file" ]]; then
        return 1  # File doesn't exist
    fi
    
    local file_age_seconds=$(( $(date +%s) - $(stat -c %Y "$file" 2>/dev/null || echo 0) ))
    local age_threshold_seconds=$(( AGE_DAYS * 24 * 60 * 60 ))
    
    if [[ $file_age_seconds -gt $age_threshold_seconds ]]; then
        return 0  # File is old enough
    else
        return 1  # File is too new
    fi
}

# Function to check if file type should be cleaned
should_clean_by_type() {
    local file="$1"
    local ext="${file##*.}"
    
    if [[ "$FILE_TYPES" == "all" ]]; then
        return 0
    fi
    
    case "$FILE_TYPES" in
        *"$ext"*)
            return 0
            ;;
        *imx* | *IMX*)
            if [[ "$ext" == "imx" ]]; then
                return 0
            fi
            ;;
        *dat* | *DAT*)
            if [[ "$ext" == "dat" ]]; then
                return 0
            fi
            ;;
        *log* | *LOG*)
            if [[ "$ext" == "log" ]]; then
                return 0
            fi
            ;;
        *journal* | *JOURNAL*)
            if [[ "$file" == *"journal"* ]]; then
                return 0
            fi
            ;;
    esac
    
    return 1
}

# Function to create backup
create_backup() {
    local source_dir="$1"
    local backup_name="$2"
    
    if [[ ! -d "$source_dir" ]]; then
        print_verbose "Backup source directory doesn't exist: $source_dir"
        return 0
    fi
    
    print_info "Creating backup: $backup_name"
    mkdir -p "$BACKUP_DIR"
    
    if cp -r "$source_dir" "$BACKUP_DIR/$backup_name" 2>/dev/null; then
        print_success "Backup created: $BACKUP_DIR/$backup_name"
        return 0
    else
        print_warning "Failed to create backup: $backup_name"
        return 1
    fi
}

# Function to clean files in a directory
clean_directory() {
    local dir="$1"
    local pattern="$2"
    local description="$3"
    
    if [[ ! -d "$dir" ]]; then
        print_verbose "Directory doesn't exist: $dir"
        return 0
    fi
    
    print_info "Cleaning $description in: $dir"
    
    local files_found=0
    local size_found=0
    local files_deleted=0
    local size_deleted=0
    
    # Find files matching pattern
    while IFS= read -r -d '' file; do
        if should_clean_by_age "$file" && should_clean_by_type "$file"; then
            local file_size=$(get_file_size "$file")
            files_found=$((files_found + 1))
            size_found=$((size_found + file_size))
            
            if [[ "$DRY_RUN" == "true" ]]; then
                print_dry_run "$file ($(format_bytes $file_size))"
            else
                if [[ "$INTERACTIVE" == "true" ]]; then
                    echo -n "Delete $file ($(format_bytes $file_size))? (y/N): "
                    read -r response
                    if [[ "$response" != "y" ]] && [[ "$response" != "Y" ]]; then
                        print_verbose "Skipped: $file"
                        continue
                    fi
                fi
                
                if rm -f "$file"; then
                    print_verbose "Deleted: $file ($(format_bytes $file_size))"
                    files_deleted=$((files_deleted + 1))
                    size_deleted=$((size_deleted + file_size))
                else
                    print_warning "Failed to delete: $file"
                fi
            fi
        fi
    done < <(find "$dir" -name "$pattern" -type f -print0 2>/dev/null)
    
    # Update global statistics
    TOTAL_FILES_FOUND=$((TOTAL_FILES_FOUND + files_found))
    TOTAL_SIZE_FOUND=$((TOTAL_SIZE_FOUND + size_found))
    TOTAL_FILES_DELETED=$((TOTAL_FILES_DELETED + files_deleted))
    TOTAL_SIZE_DELETED=$((TOTAL_SIZE_DELETED + size_deleted))
    
    if [[ $files_found -gt 0 ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            print_info "Found $files_found files ($(format_bytes $size_found)) in $description"
        else
            print_success "Cleaned $files_deleted/$files_found files ($(format_bytes $size_deleted)) from $description"
        fi
    else
        print_verbose "No files found matching criteria in $description"
    fi
}

# Function to clean empty directories
clean_empty_directories() {
    local dir="$1"
    local description="$2"
    
    if [[ ! -d "$dir" ]]; then
        return 0
    fi
    
    print_verbose "Cleaning empty directories in: $dir"
    
    # Find and remove empty directories (excluding the root directory)
    while IFS= read -r -d '' empty_dir; do
        if [[ "$empty_dir" != "$dir" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                print_dry_run "empty directory: $empty_dir"
            else
                if rmdir "$empty_dir" 2>/dev/null; then
                    print_verbose "Removed empty directory: $empty_dir"
                fi
            fi
        fi
    done < <(find "$dir" -type d -empty -print0 2>/dev/null)
}

# Function to clean test environment
clean_test_environment() {
    if [[ "$CLEAN_TEST" == "false" ]]; then
        return 0
    fi
    
    print_info "=== Cleaning Test Environment ==="
    
    # Create backup if requested
    if [[ "$CREATE_BACKUP" == "true" ]]; then
        create_backup "$TEST_STORAGE_DIR" "test_storage_backup"
    fi
    
    # Clean test data files
    clean_directory "$TEST_STORAGE_DIR/history" "sector_*.imx" "test data files"
    clean_directory "$TEST_STORAGE_DIR/history" "*.imx" "additional test files"
    clean_directory "$TEST_STORAGE_DIR/history/corrupted" "*" "corrupted test files"
    clean_directory "$TEST_STORAGE_DIR" "*.log" "test log files"
    clean_directory "$TEST_STORAGE_DIR" "recovery.journal*" "test journal files"
    
    # Clean empty directories
    clean_empty_directories "$TEST_STORAGE_DIR" "test environment"
    
    print_success "Test environment cleanup completed"
}

# Function to clean production environment
clean_production_environment() {
    if [[ "$CLEAN_PROD" == "false" ]]; then
        return 0
    fi
    
    print_info "=== Cleaning Production Environment ==="
    
    # Extra safety check for production
    if [[ "$INTERACTIVE" == "false" ]] && [[ "$FORCE_CLEANUP" == "false" ]]; then
        print_warning "Production cleanup requires interactive mode or --force flag"
        return 0
    fi
    
    # Create backup if requested
    if [[ "$CREATE_BACKUP" == "true" ]]; then
        create_backup "$PROD_STORAGE_DIR" "prod_storage_backup"
    fi
    
    # Clean production data files
    clean_directory "$PROD_STORAGE_DIR" "*.dat" "production data files"
    clean_directory "$PROD_STORAGE_DIR" "sensor_*.dat" "sensor data files"
    clean_directory "$PROD_STORAGE_DIR/corrupted" "*" "corrupted production files"
    clean_directory "$PROD_STORAGE_DIR" "recovery.journal*" "production journal files"
    
    # Clean empty directories
    clean_empty_directories "$PROD_STORAGE_DIR" "production environment"
    
    print_success "Production environment cleanup completed"
}

# Function to clean build artifacts
clean_build_artifacts() {
    print_info "=== Cleaning Build Artifacts ==="
    
    # Clean build directory
    if [[ -d "$BUILD_DIR" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            local size=$(du -sb "$BUILD_DIR" 2>/dev/null | cut -f1)
            print_dry_run "build directory: $BUILD_DIR ($(format_bytes $size))"
        else
            if [[ "$INTERACTIVE" == "true" ]]; then
                echo -n "Delete entire build directory $BUILD_DIR? (y/N): "
                read -r response
                if [[ "$response" == "y" ]] || [[ "$response" == "Y" ]]; then
                    rm -rf "$BUILD_DIR"
                    print_success "Deleted build directory"
                else
                    print_verbose "Skipped build directory"
                fi
            else
                rm -rf "$BUILD_DIR"
                print_success "Deleted build directory"
            fi
        fi
    fi
    
    # Clean individual executables in main directory
    for exe in simple_memory_test tiered_storage_test performance_test diagnostic_test; do
        if [[ -f "./$exe" ]]; then
            local size=$(get_file_size "./$exe")
            if [[ "$DRY_RUN" == "true" ]]; then
                print_dry_run "./$exe ($(format_bytes $size))"
            else
                rm -f "./$exe"
                print_verbose "Deleted: ./$exe"
            fi
        fi
    done
    
    print_success "Build artifacts cleanup completed"
}

# Function to clean log files
clean_log_files() {
    print_info "=== Cleaning Log Files ==="
    
    # Clean log directory
    clean_directory "$LOG_DIR" "*.log" "test log files"
    
    # Clean temporary log files
    for temp_log in /tmp/smoke_test.log /tmp/diagnostic.log; do
        if [[ -f "$temp_log" ]]; then
            local size=$(get_file_size "$temp_log")
            if [[ "$DRY_RUN" == "true" ]]; then
                print_dry_run "$temp_log ($(format_bytes $size))"
            else
                rm -f "$temp_log"
                print_verbose "Deleted: $temp_log"
            fi
        fi
    done
    
    # Clean empty log directory
    clean_empty_directories "$LOG_DIR" "log files"
    
    print_success "Log files cleanup completed"
}

# Function to display cleanup summary
display_summary() {
    echo ""
    echo "=================================="
    echo "        CLEANUP SUMMARY"
    echo "=================================="
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "DRY RUN RESULTS:"
        echo "  Files that would be deleted: $TOTAL_FILES_FOUND"
        echo "  Space that would be freed: $(format_bytes $TOTAL_SIZE_FOUND)"
        echo ""
        echo "Run without --dry-run to perform actual cleanup"
    else
        echo "CLEANUP RESULTS:"
        echo "  Files found: $TOTAL_FILES_FOUND"
        echo "  Files deleted: $TOTAL_FILES_DELETED"
        echo "  Space freed: $(format_bytes $TOTAL_SIZE_DELETED)"
        echo ""
        
        if [[ "$CREATE_BACKUP" == "true" ]] && [[ -d "$BACKUP_DIR" ]]; then
            echo "BACKUP CREATED:"
            echo "  Backup location: $BACKUP_DIR"
            echo "  Backup size: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
        fi
    fi
    
    echo ""
    echo "CLEANUP CONFIGURATION:"
    echo "  Test environment: $([ "$CLEAN_TEST" == "true" ] && echo "YES" || echo "NO")"
    echo "  Production environment: $([ "$CLEAN_PROD" == "true" ] && echo "YES" || echo "NO")"
    echo "  File age filter: $([ "$AGE_DAYS" -eq 0 ] && echo "ALL FILES" || echo ">${AGE_DAYS} days")"
    echo "  File types: $FILE_TYPES"
    echo "  Interactive mode: $([ "$INTERACTIVE" == "true" ] && echo "YES" || echo "NO")"
    echo "  Backup created: $([ "$CREATE_BACKUP" == "true" ] && echo "YES" || echo "NO")"
    echo ""
    echo "=================================="
}

# Main execution function
main() {
    echo "iMatrix Data Cleanup Script"
    echo "=========================="
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Parse arguments
    parse_args "$@"
    
    # Display configuration
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN MODE - No files will be deleted"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        print_info "Verbose mode enabled"
    fi
    
    # Safety checks
    check_running_tests
    
    # Perform cleanup operations
    clean_test_environment
    clean_production_environment
    clean_build_artifacts
    clean_log_files
    
    # Display summary
    display_summary
    
    if [[ "$DRY_RUN" == "false" ]]; then
        print_success "Cleanup completed successfully!"
    else
        print_info "Dry run completed - no files were modified"
    fi
}

# Run main function with all arguments
main "$@"