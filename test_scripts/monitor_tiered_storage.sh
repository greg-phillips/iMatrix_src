#!/bin/bash
#
# monitor_tiered_storage.sh
#
# Real-time monitoring script for iMatrix Tiered Storage System
# Shows storage directory status, file counts, and disk usage
# Supports both production and test environments
#

# Default configuration
PROD_STORAGE_DIR="/usr/qk/etc/sv/FC-1/history"
TEST_STORAGE_DIR="/tmp/imatrix_test_storage/history"
REFRESH_INTERVAL=2
MODE="production"

# Parse command line arguments
show_help() {
    echo "iMatrix Tiered Storage Monitor"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --test     Monitor test directory ($TEST_STORAGE_DIR)"
    echo "  -p, --prod     Monitor production directory ($PROD_STORAGE_DIR) [default]"
    echo "  -i, --interval Set refresh interval in seconds [default: $REFRESH_INTERVAL]"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Monitor production (default)"
    echo "  $0 --test             # Monitor test environment"
    echo "  $0 --test -i 1        # Monitor test with 1-second refresh"
    echo ""
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--test)
            MODE="test"
            shift
            ;;
        -p|--prod)
            MODE="production"
            shift
            ;;
        -i|--interval)
            REFRESH_INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Set storage directory based on mode
if [ "$MODE" = "test" ]; then
    STORAGE_DIR="$TEST_STORAGE_DIR"
    FILE_PATTERN="*.imx"
    FILE_EXT="imx"
else
    STORAGE_DIR="$PROD_STORAGE_DIR"
    FILE_PATTERN="*.dat"
    FILE_EXT="dat"
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to get color based on percentage
get_color() {
    local percent=$1
    if [ $percent -lt 70 ]; then
        echo $GREEN
    elif [ $percent -lt 85 ]; then
        echo $YELLOW
    else
        echo $RED
    fi
}

# Main monitoring loop
while true; do
    clear
    echo "iMatrix Tiered Storage Monitor"
    echo "=============================="
    if [ "$MODE" = "test" ]; then
        echo -e "${YELLOW}TEST MODE${NC} - Monitoring: $STORAGE_DIR"
        echo "File type: .$FILE_EXT files"
    else
        echo -e "${GREEN}PRODUCTION MODE${NC} - Monitoring: $STORAGE_DIR"
        echo "File type: .$FILE_EXT files"
    fi
    date
    echo ""
    
    # Check if directory exists
    if [ ! -d "$STORAGE_DIR" ]; then
        echo -e "${YELLOW}Waiting: Storage directory not found: $STORAGE_DIR${NC}"
        echo "Checking again in $REFRESH_INTERVAL seconds..."
        sleep $REFRESH_INTERVAL
        continue
    fi
    
    # Disk usage
    echo "Disk Usage:"
    df -h "$STORAGE_DIR" | tail -1 | while read fs size used avail percent mount; do
        percent_num=${percent%\%}
        color=$(get_color $percent_num)
        echo -e "  Filesystem: $fs"
        echo -e "  Total Size: $size"
        echo -e "  Used: $used (${color}$percent${NC})"
        echo -e "  Available: $avail"
    done
    echo ""
    
    # File counts (hierarchical structure aware)
    echo "Storage Files:"
    data_count=$(find "$STORAGE_DIR" -name "$FILE_PATTERN" 2>/dev/null | wc -l)
    journal_count=$(find "$STORAGE_DIR" -name "recovery.journal*" 2>/dev/null | wc -l)
    corrupted_count=$(find "$STORAGE_DIR/corrupted" -name "*" -type f 2>/dev/null | wc -l)
    
    # Count bucket directories
    bucket_count=0
    if [ -d "$STORAGE_DIR" ]; then
        bucket_count=$(ls -d "$STORAGE_DIR"/[0-9]* 2>/dev/null | wc -l)
    fi
    
    echo "  Data files (.$FILE_EXT): $data_count"
    echo "  Journal files: $journal_count"
    if [ $corrupted_count -gt 0 ]; then
        echo -e "  ${RED}Corrupted files: $corrupted_count${NC}"
    else
        echo -e "  ${GREEN}Corrupted files: 0${NC}"
    fi
    
    # Display bucket information
    if [ $bucket_count -gt 0 ]; then
        echo "  Bucket directories: $bucket_count"
        echo ""
        echo "Bucket Distribution:"
        for bucket_dir in $(ls -d "$STORAGE_DIR"/[0-9]* 2>/dev/null | sort -V); do
            bucket_num=$(basename "$bucket_dir")
            bucket_files=$(find "$bucket_dir" -name "$FILE_PATTERN" 2>/dev/null | wc -l)
            if [ $bucket_files -gt 0 ]; then
                echo "  Bucket $bucket_num: $bucket_files files"
            fi
        done
    else
        echo "  No bucket directories found"
    fi
    echo ""
    
    # Recent files (hierarchical structure aware)
    echo "Recent Files (last 5):"
    # Find recent files across all buckets
    recent_files=$(find "$STORAGE_DIR" -name "$FILE_PATTERN" -type f 2>/dev/null | xargs ls -lt 2>/dev/null | head -5)
    
    if [ -n "$recent_files" ]; then
        echo "$recent_files" | while read perms links owner group size month day time file; do
            basename=$(basename "$file")
            bucket=$(basename "$(dirname "$file")")
            if [[ "$bucket" =~ ^[0-9]+$ ]]; then
                echo "  $basename (bucket $bucket) - $size bytes - $month $day $time"
            else
                echo "  $basename - $size bytes - $month $day $time"
            fi
        done
    else
        echo "  (No data files found)"
    fi
    echo ""
    
    # Storage statistics
    if [ $data_count -gt 0 ]; then
        echo "Storage Statistics:"
        total_size=$(du -sh "$STORAGE_DIR" 2>/dev/null | cut -f1)
        data_size=$(find "$STORAGE_DIR" -name "$FILE_PATTERN" -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)
        avg_file_size=$(find "$STORAGE_DIR" -name "$FILE_PATTERN" -exec stat -c%s {} + 2>/dev/null | awk '{sum+=$1; count++} END {if(count>0) printf "%.1f", sum/count/1024; else print "0"}')
        
        echo "  Total storage used: $total_size"
        echo "  Data files size: $data_size"
        echo "  Average file size: ${avg_file_size}KB"
        
        # Sensor distribution (hierarchical structure aware)
        echo ""
        if [ "$MODE" = "test" ]; then
            echo "Test Files by Sensor:"
            # Use sampling for performance with large numbers of files
            if [ $data_count -gt 10000 ]; then
                echo "  (Sampling due to large dataset: $data_count files across $bucket_count buckets)"
                # Sample from multiple buckets for better representation
                sample_files=""
                for bucket_dir in $(ls -d "$STORAGE_DIR"/[0-9]* 2>/dev/null | head -10); do
                    bucket_sample=$(find "$bucket_dir" -name "sector_*_sensor_*.$FILE_EXT" 2>/dev/null | head -100)
                    if [ -n "$bucket_sample" ]; then
                        sample_files="$sample_files
$bucket_sample"
                    fi
                done
                
                for sensor in $(echo "$sample_files" | sed 's/.*sector_[0-9]*_sensor_\([0-9]*\)\.'"$FILE_EXT"'/\1/' | sort -u | head -10); do
                    count=$(find "$STORAGE_DIR" -name "sector_*_sensor_${sensor}.$FILE_EXT" 2>/dev/null | wc -l)
                    echo "  Sensor $sensor: $count files"
                done
            else
                for sensor in $(find "$STORAGE_DIR" -name "sector_*_sensor_*.$FILE_EXT" 2>/dev/null | sed 's/.*sector_[0-9]*_sensor_\([0-9]*\)\.'"$FILE_EXT"'/\1/' | sort -u); do
                    count=$(find "$STORAGE_DIR" -name "sector_*_sensor_${sensor}.$FILE_EXT" 2>/dev/null | wc -l)
                    echo "  Sensor $sensor: $count files"
                done
            fi
            
            # Show sector range for test files (hierarchical structure aware)
            echo ""
            echo "Sector Range:"
            if [ $data_count -gt 10000 ]; then
                echo "  (Estimated from bucket sampling)"
                # Get min from first bucket, max from last bucket
                first_bucket=$(ls -d "$STORAGE_DIR"/[0-9]* 2>/dev/null | sort -V | head -1)
                last_bucket=$(ls -d "$STORAGE_DIR"/[0-9]* 2>/dev/null | sort -V | tail -1)
                
                if [ -n "$first_bucket" ]; then
                    min_sector=$(find "$first_bucket" -name "sector_*_sensor_*.$FILE_EXT" 2>/dev/null | head -10 | sed 's/.*sector_\([0-9]*\)_sensor_.*/\1/' | sort -n | head -1)
                fi
                if [ -n "$last_bucket" ]; then
                    max_sector=$(find "$last_bucket" -name "sector_*_sensor_*.$FILE_EXT" 2>/dev/null | tail -10 | sed 's/.*sector_\([0-9]*\)_sensor_.*/\1/' | sort -n | tail -1)
                fi
                
                # Display bucket range info
                if [ $bucket_count -gt 0 ]; then
                    first_bucket_num=$(basename "$first_bucket" 2>/dev/null)
                    last_bucket_num=$(basename "$last_bucket" 2>/dev/null)
                    echo "  Bucket range: $first_bucket_num - $last_bucket_num ($bucket_count buckets)"
                    echo "  Estimated sectors per bucket: ~1000 (max)"
                fi
            else
                min_sector=$(find "$STORAGE_DIR" -name "sector_*_sensor_*.$FILE_EXT" 2>/dev/null | sed 's/.*sector_\([0-9]*\)_sensor_.*/\1/' | sort -n | head -1)
                max_sector=$(find "$STORAGE_DIR" -name "sector_*_sensor_*.$FILE_EXT" 2>/dev/null | sed 's/.*sector_\([0-9]*\)_sensor_.*/\1/' | sort -n | tail -1)
            fi
            
            if [ -n "$min_sector" ] && [ -n "$max_sector" ]; then
                echo "  Sectors: $min_sector - $max_sector"
                if [ $data_count -le 10000 ]; then
                    echo "  Range: $((max_sector - min_sector + 1)) sectors allocated"
                fi
            fi
        else
            echo "Files by Sensor:"
            for sensor in $(ls "$STORAGE_DIR"/sensor_*.$FILE_EXT 2>/dev/null | sed 's/.*sensor_\([0-9]*\)_.*/\1/' | sort -u); do
                count=$(ls "$STORAGE_DIR"/sensor_${sensor}_*.$FILE_EXT 2>/dev/null | wc -l)
                echo "  Sensor $sensor: $count files"
            done
        fi
    fi
    
    echo ""
    echo "Press Ctrl+C to exit"
    echo "Refreshing every $REFRESH_INTERVAL seconds..."
    
    sleep $REFRESH_INTERVAL
done