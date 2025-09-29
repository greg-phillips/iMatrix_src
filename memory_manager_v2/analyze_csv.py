#!/usr/bin/env python3
"""
CSV Analysis Script for Million Record Test
Provides basic analysis of the disk overflow test CSV data
"""

import csv
import sys

def analyze_csv(filename):
    print("=== Million Record Test CSV Analysis ===")
    print(f"Analyzing: {filename}")
    print()

    try:
        with open(filename, 'r') as file:
            reader = csv.DictReader(file)

            # Statistics
            total_rows = 0
            max_ram_records = 0
            max_disk_records = 0
            max_disk_files = 0
            max_disk_space = 0.0
            final_operations = 0

            # Event counts
            disk_overflow_events = 0
            disk_cleanup_events = 0
            progress_logs = 0

            # Sample data for visualization
            progress_data = []

            for row in reader:
                total_rows += 1

                # Extract data
                operation_count = int(row['operation_count'])
                ram_records = int(row['ram_records'])
                disk_records = int(row['disk_records'])
                disk_files = int(row['disk_files'])
                disk_space = float(row['total_disk_space_mb'])
                operation_type = row['operation_type']

                # Update statistics
                max_ram_records = max(max_ram_records, ram_records)
                max_disk_records = max(max_disk_records, disk_records)
                max_disk_files = max(max_disk_files, disk_files)
                max_disk_space = max(max_disk_space, disk_space)
                final_operations = max(final_operations, operation_count)

                # Count events
                if operation_type == 'disk_overflow':
                    disk_overflow_events += 1
                elif operation_type == 'disk_cleanup':
                    disk_cleanup_events += 1
                elif operation_type == 'progress_log':
                    progress_logs += 1
                    progress_data.append((operation_count, ram_records, disk_records))

            # Print analysis
            print("📊 Test Summary:")
            print(f"  Total CSV entries: {total_rows:,}")
            print(f"  Final operations: {final_operations:,}")
            print()

            print("💾 Memory Usage Analysis:")
            print(f"  Max RAM records: {max_ram_records}")
            print(f"  Max RAM utilization: {max_ram_records}/384 ({max_ram_records/384*100:.1f}%)")
            print(f"  Max disk records: {max_disk_records}")
            print(f"  Max disk files: {max_disk_files}")
            print(f"  Max disk space: {max_disk_space:.3f} MB")
            print()

            print("🔄 Operation Analysis:")
            print(f"  Disk overflow events: {disk_overflow_events:,}")
            print(f"  Disk cleanup events: {disk_cleanup_events:,}")
            print(f"  Progress log entries: {progress_logs}")
            print()

            print("📈 Key Progress Points (RAM vs Disk):")
            for i, (ops, ram, disk) in enumerate(progress_data[:10]):
                print(f"  {ops:,} ops: {ram} RAM records, {disk} disk records")

            if len(progress_data) > 10:
                print(f"  ... (showing first 10 of {len(progress_data)} progress points)")

            print()
            print("✅ CSV Analysis Complete")
            print()
            print("📊 For graphing:")
            print("  - X-axis: operation_count")
            print("  - Y-axis: ram_records (blue) + disk_records (red)")
            print("  - Secondary: disk_files growth over time")
            print("  - Events: disk_overflow (markers), disk_cleanup (markers)")

    except FileNotFoundError:
        print(f"❌ CSV file not found: {filename}")
        return False
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        return False

    return True

if __name__ == "__main__":
    filename = "FC_filesystem/million_record_test.csv"
    if len(sys.argv) > 1:
        filename = sys.argv[1]

    analyze_csv(filename)