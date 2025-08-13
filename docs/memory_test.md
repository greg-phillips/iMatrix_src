# iMatrix Tiered Storage Memory Test Documentation

## Table of Contents
1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Test Programs](#test-programs)
4. [Building the Tests](#building-the-tests)
5. [Running the Tests](#running-the-tests)
6. [Test Scenarios](#test-scenarios)
7. [Understanding Test Output](#understanding-test-output)
8. [Performance Analysis](#performance-analysis)
9. [Troubleshooting](#troubleshooting)
10. [API Usage Examples](#api-usage-examples)

## Overview

The iMatrix Tiered Storage Memory Test Suite provides comprehensive validation of the tiered storage system's functionality, performance, and reliability. The test suite validates:

- **Data Integrity**: All 100,000+ records are preserved correctly
- **Automatic Migration**: RAM-to-disk migration triggers at 80% threshold
- **Shutdown Handling**: Complete data preservation during system shutdown
- **Power Failure Recovery**: Full recovery from unexpected power loss
- **Performance**: Throughput, latency, and resource usage metrics
- **Cross-Storage Operations**: Seamless sector chain traversal across RAM and disk

### Key Features
- Writes sequential test data with verifiable patterns
- Exercises both TSD (Time Series Data) and EVT (Event) record types
- Simulates real-world usage patterns
- Provides detailed performance metrics
- Supports stress testing and failure simulation

## Test Architecture

### Component Overview
```
┌─────────────────────────────────────┐
│        Test Application             │
├─────────────────────────────────────┤
│         iMatrix APIs                │
│  write_tsd_evt() / read_tsd_evt()  │
├─────────────────────────────────────┤
│    Memory Manager + Tiered Storage  │
│  - State Machine (process_memory)   │
│  - Sector Allocation               │
│  - RAM/Disk Migration              │
├─────────────────────────────────────┤
│         Storage Layer               │
│  RAM: sectors 0-64K                 │
│  Disk: /usr/qk/etc/sv/FC-1/history │
└─────────────────────────────────────┘
```

### Test Data Pattern
```c
// Simple incrementing pattern (basic test)
record[0] = 0    // First TSD record
record[1] = 1    // First EVT record  
record[2] = 2    // Second TSD record
record[3] = 3    // Second EVT record
...
record[99999] = 99999  // Last record

// Stress test pattern (advanced test)
value = (record_num * 31337 + sensor_id * 12345) ^ random_seed
```

### Sensor Configuration
- **TSD Sensors**: Even-numbered IDs (10, 12, 14...)
  - 6 entries per sector
  - Larger record size
- **EVT Sensors**: Odd-numbered IDs (11, 13, 15...)
  - 3 entries per sector
  - Smaller record size

## Test Programs

### 1. Basic Test Program (`test_tiered_storage.c`)

**Purpose**: Validates core functionality with a fixed test scenario

**Features**:
- Writes exactly 100,000 records
- Uses 2 sensors (1 TSD, 1 EVT)
- Performs complete shutdown sequence
- Verifies all data after restart
- Simple pass/fail result

**Key Functions**:
```c
// Initialize test sensors
static void init_test_sensors(void);

// Write test records with progress monitoring
static bool write_test_records(void);

// Perform shutdown with disk flush
static bool perform_shutdown(void);

// Verify all records after restart
static bool verify_test_records(void);
```

### 2. Advanced Test Program (`test_tiered_storage_advanced.c`)

**Purpose**: Configurable testing with performance analysis

**Features**:
- Command-line configuration
- Multi-sensor support (up to 10)
- Performance measurements
- Stress testing modes
- Power failure simulation
- Detailed metrics and statistics

**Command-line Options**:
```
-r, --records NUM      Number of records to write (default: 100000)
-b, --batch NUM        Batch size for processing (default: 1000)
-s, --sensors NUM      Number of sensors to test (default: 2, max: 10)
-v, --verify           Verify records during write
-p, --power-fail       Simulate power failure during test
-S, --stress           Run stress test mode
-V, --verbose          Enable verbose output
-P, --performance      Enable performance measurement mode
-R, --seed NUM         Random seed for stress testing
-h, --help             Show help message
```

## Building the Tests

### Prerequisites
- Linux platform with GCC compiler
- iMatrix source code
- POSIX file system support
- pthread library

### Using the Makefile
```bash
# Build basic test program
make -f Makefile.test

# Build and run immediately
make -f Makefile.test run

# Clean build artifacts
make -f Makefile.test clean

# Setup storage directories (requires sudo)
make -f Makefile.test setup-storage
```

### Manual Build Commands
```bash
# Basic test
gcc -o test_tiered_storage test_tiered_storage.c \
    iMatrix/cs_ctrl/memory_manager.c \
    iMatrix/cs_ctrl/cs_memory_mgt.c \
    iMatrix/cs_ctrl/sensors.c \
    iMatrix/storage.c \
    -I. -IiMatrix -DLINUX_PLATFORM -pthread -Wall -O2

# Advanced test (same source files)
gcc -o test_tiered_storage_advanced test_tiered_storage_advanced.c \
    [same object files] \
    -I. -IiMatrix -DLINUX_PLATFORM -pthread -Wall -O2
```

## Running the Tests

### Storage Setup (One-time)
```bash
# Create required directories
sudo mkdir -p /usr/qk/etc/sv/FC-1/history/corrupted
sudo chown $USER:$USER /usr/qk/etc/sv/FC-1/history/
sudo chmod 755 /usr/qk/etc/sv/FC-1/history/
```

### Basic Test Execution
```bash
# Run basic test
./test_tiered_storage

# Expected output:
# iMatrix Tiered Storage Test Program
# ===================================
# Test parameters:
#   Record count: 100000
#   TSD sensor ID: 10
#   EVT sensor ID: 11
#   Batch size: 1000
# 
# --- Phase 1: Write Test Records ---
# Progress: 10000 records written, RAM usage: 15.2%
# Progress: 20000 records written, RAM usage: 30.5%
# ...
# Write complete:
#   TSD records: 50000
#   EVT records: 50000
#   Total records: 100000
#   Errors: 0
# 
# --- Phase 2: System Shutdown ---
# Sectors pending disk write: 1250
# Flushing: 1250 sectors remaining...
# Shutdown flush completed in 2341 ms
# 
# --- Phase 5: Verify Test Records ---
# Verification complete:
#   TSD records verified: 50000
#   EVT records verified: 50000
#   Total records verified: 100000
#   Errors: 0
# 
# OVERALL RESULT: PASSED ✓
```

### Advanced Test Examples

#### Quick Functional Test
```bash
./test_tiered_storage_advanced -r 10000 -b 100
# Tests basic functionality with smaller dataset
```

#### Performance Benchmark
```bash
./test_tiered_storage_advanced -r 200000 -P -b 5000
# Measures throughput with larger batches
```

#### Multi-Sensor Stress Test
```bash
./test_tiered_storage_advanced -r 100000 -s 5 -S -v
# Tests 5 sensors with stress patterns and verification
```

#### Power Failure Simulation
```bash
./test_tiered_storage_advanced -r 50000 -p
# Simulates power loss at 50% completion
# Run again without -p to test recovery
```

### Automated Test Suite
```bash
# Run complete test suite
./run_tiered_storage_tests.sh

# Tests performed:
# 1. Basic functionality (100k records)
# 2. Small dataset (10k records)
# 3. Large dataset (200k records)
# 4. Multi-sensor (5 sensors, 50k records)
# 5. Stress test with verification
# 6. Power failure simulation
# 7. Recovery verification
# 8. Performance benchmark
```

### Real-time Monitoring
```bash
# In a separate terminal
./monitor_tiered_storage.sh

# Shows:
# - Disk usage with color coding
# - File counts and recent files
# - Storage statistics
# - Sensor distribution
```

## Test Scenarios

### 1. Basic Functionality Test
**Objective**: Validate core operations work correctly

**Process**:
1. Initialize 2 sensors (TSD and EVT)
2. Write 100,000 records with incrementing values
3. Monitor RAM usage and migration triggers
4. Perform controlled shutdown
5. Restart and verify all data

**Success Criteria**:
- All records written successfully
- Automatic migration occurs at 80% RAM usage
- All data preserved through shutdown
- All records read back with correct values

### 2. Performance Test
**Objective**: Measure system throughput and resource usage

**Metrics Collected**:
- Write throughput (records/second)
- Shutdown flush rate (sectors/second)
- Peak RAM usage percentage
- Total files created
- Total bytes written to disk

**Example Results**:
```
Performance Metrics:
  Write Performance:
    Time: 45.32 seconds
    Rate: 2207 records/second
  Shutdown Performance:
    Time: 3.45 seconds
    Rate: 362 sectors/second
  Peak RAM Usage: 82.3%
  Files Created: 42
  Data Written: 15.6 MB
```

### 3. Stress Test
**Objective**: Validate system under heavy load

**Configuration**:
- Multiple sensors (5-10)
- Complex data patterns
- Continuous verification
- Extended run time

**Stress Factors**:
- High write rate
- Random access patterns
- Concurrent operations
- Memory pressure

### 4. Power Failure Test
**Objective**: Validate recovery from unexpected shutdown

**Process**:
1. Start normal write operations
2. Simulate power failure at 50% completion
3. Restart system
4. Run recovery process
5. Verify recovered data
6. Complete remaining writes
7. Verify all data

**Recovery Validation**:
- Journal integrity check
- File validation
- Metadata reconstruction
- Sector chain verification

### 5. Multi-Sensor Test
**Objective**: Validate handling of multiple data streams

**Configuration**:
- 5+ sensors active
- Mixed TSD/EVT types
- Concurrent writes
- Different data rates

**Validation**:
- Per-sensor data integrity
- Correct sector allocation
- Proper file organization
- No cross-sensor corruption

## Understanding Test Output

### Progress Messages
```
Progress: 20000 records written, RAM usage: 30.5%
```
- Shows records written so far
- Current RAM usage percentage
- Appears every 10,000 records

### Write Statistics
```
Write complete:
  TSD records: 50000
  EVT records: 50000
  Total records: 100000
  Errors: 0

Final RAM usage: 15.2% (1250/8192 sectors)
Peak RAM usage: 82.5% (6758 sectors)
```
- Record counts by type
- Error count (should be 0)
- Current and peak RAM usage

### Tiered Storage Statistics
```
Tiered storage stats:
  Files created: 42
  Files deleted: 0
  Bytes written: 15728640
```
- Number of disk files created
- Cleanup operations performed
- Total data written to disk

### Shutdown Progress
```
Sectors pending disk write: 1250
Flushing: 625/1250 sectors (500 sectors/sec)
Shutdown flush completed in 2500 ms
```
- Initial pending sectors
- Progress with rate calculation
- Total shutdown time

### Verification Results
```
Verification complete:
  TSD records verified: 50000
  EVT records verified: 50000
  Total records verified: 100000
  Errors: 0
```
- Records successfully verified
- Any data corruption errors
- Should match write counts

### Error Messages
```
ERROR: TSD entry 1234 mismatch - expected 2468, got 0
ERROR: Disk space insufficient for migration
WARNING: No progress for 10 seconds
```
- Data corruption detection
- Resource exhaustion
- Performance issues

## Performance Analysis

### Key Performance Indicators

#### Write Performance
- **Target**: >1000 records/second
- **Factors**: CPU speed, disk I/O, batch size
- **Optimization**: Increase batch size, reduce logging

#### Migration Performance
- **Trigger**: 80% RAM usage
- **Rate**: Depends on disk speed
- **Impact**: <5% on write throughput

#### Shutdown Performance
- **Target**: <10 seconds for 100k records
- **Rate**: >100 sectors/second
- **Critical**: Must complete before power loss

### Performance Tuning

#### Batch Size Optimization
```bash
# Small batches (more responsive, lower throughput)
./test_tiered_storage_advanced -r 100000 -b 100

# Large batches (less responsive, higher throughput)
./test_tiered_storage_advanced -r 100000 -b 10000
```

#### Memory Pressure Testing
```bash
# Force early migration by using more sensors
./test_tiered_storage_advanced -r 100000 -s 10
```

#### Disk I/O Analysis
```bash
# Monitor disk activity during test
iostat -x 1

# Check file system performance
dd if=/dev/zero of=/usr/qk/etc/sv/FC-1/history/test.dat bs=1M count=100
```

### Bottleneck Identification

#### CPU Bound
- High CPU usage during processing
- Solution: Optimize algorithms, increase batch size

#### I/O Bound
- Low CPU, high disk wait time
- Solution: Use faster storage, optimize file operations

#### Memory Bound
- Frequent migration cycles
- Solution: Increase RAM allocation, optimize sector usage

## Troubleshooting

### Common Issues and Solutions

#### 1. Permission Denied
```
ERROR: Failed to create directory /usr/qk/etc/sv/FC-1/history/
```
**Solution**:
```bash
sudo mkdir -p /usr/qk/etc/sv/FC-1/history/
sudo chown $USER:$USER /usr/qk/etc/sv/FC-1/history/
```

#### 2. Test Fails with "No space left on device"
```
ERROR: Failed to create temp file: No space left on device
```
**Solution**:
```bash
# Check disk space
df -h /usr/qk/etc/sv/FC-1/history/

# Clean old test data
rm -f /usr/qk/etc/sv/FC-1/history/*.dat
```

#### 3. Verification Errors
```
ERROR: TSD entry 1234 mismatch - expected 2468, got 0
```
**Possible Causes**:
- Data corruption during write
- Power failure during test
- File system errors

**Debugging Steps**:
1. Check corrupted files directory
2. Examine recovery journal
3. Run with verbose mode
4. Check system logs

#### 4. Slow Performance
```
Write Performance: 100 records/second (too slow)
```
**Optimization Steps**:
1. Increase batch size (`-b 5000`)
2. Check disk performance (`iostat`)
3. Reduce verification frequency
4. Use performance mode (`-P`)

#### 5. Recovery Failures
```
ERROR: Recovery journal checksum mismatch
```
**Recovery Steps**:
```bash
# Backup corrupted journal
mv /usr/qk/etc/sv/FC-1/history/recovery.journal \
   /usr/qk/etc/sv/FC-1/history/recovery.journal.bad

# System will create new journal
# Existing data files will be scanned
```

### Debug Options

#### Verbose Output
```bash
./test_tiered_storage_advanced -V -r 1000
# Shows detailed processing information
```

#### GDB Debugging
```bash
make -f Makefile.test debug
# Or
gdb ./test_tiered_storage
(gdb) run
(gdb) bt  # backtrace on crash
```

#### Memory Leak Detection
```bash
make -f Makefile.test memcheck
# Or
valgrind --leak-check=full ./test_tiered_storage
```

#### System Call Tracing
```bash
strace -e trace=file ./test_tiered_storage
# Shows all file operations
```

## API Usage Examples

### Basic Write/Read Pattern
```c
// Initialize sensors
imx_control_sensor_block_t csb;
control_sensor_data_t csd;

// Configure sensor
csb.sensor.id = 10;  // Even = TSD
csb.sensor.type = SENSOR_TYPE_TSD;
csb.sensor.enabled = true;

// Write data
for (int i = 0; i < 1000; i++) {
    write_tsd_evt(&csb, &csd, i, i * 100, false);
    
    // Process background storage periodically
    if (i % 100 == 0) {
        imx_time_t current_time;
        imx_time_get_time(&current_time);
        process_memory(current_time);
    }
}

// Read data back
for (int i = 0; i < 1000; i++) {
    uint32_t value;
    read_tsd_evt(&csb, &csd, i, &value);
    assert(value == i * 100);
}
```

### Shutdown Sequence
```c
// Request flush
flush_all_to_disk();

// Wait for completion with progress
while (get_pending_disk_write_count() > 0) {
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    process_memory(current_time);
    
    printf("Pending: %u sectors\n", 
           get_pending_disk_write_count());
    
    usleep(100000);  // 100ms
}
```

### Recovery After Restart
```c
// On system startup
void system_init(void) {
    // Initialize memory system
    imx_sat_init();
    
    // Perform recovery
    perform_power_failure_recovery();
    
    // Check recovery status
    if (tiered_state_machine.power_failure_recoveries > 0) {
        printf("Recovered from power failure\n");
    }
    
    // System ready for normal operation
}
```

### Performance Monitoring
```c
// Get memory statistics
imx_memory_statistics_t *stats = imx_get_memory_statistics();

printf("Memory Usage: %.1f%% (%u/%u sectors)\n",
       stats->usage_percentage,
       stats->used_sectors,
       stats->total_sectors);

printf("Peak Usage: %.1f%% (%u sectors)\n",
       stats->peak_usage_percentage,
       stats->peak_usage);

// Get tiered storage statistics  
printf("Files Created: %u\n", 
       tiered_state_machine.total_files_created);
printf("Bytes Written: %llu\n",
       tiered_state_machine.total_bytes_written);
```

### Error Handling
```c
// Use secure functions for better error handling
imx_memory_error_t result;
uint32_t buffer[128];

result = read_rs_safe(sector, offset, buffer, 
                     sizeof(buffer), sizeof(buffer));

switch (result) {
    case IMX_MEMORY_SUCCESS:
        // Process data
        break;
    case IMX_MEMORY_ERROR_INVALID_SECTOR:
        printf("Invalid sector number\n");
        break;
    case IMX_MEMORY_ERROR_BUFFER_TOO_SMALL:
        printf("Buffer too small\n");
        break;
    default:
        printf("Read error: %d\n", result);
        break;
}
```

## Conclusion

The iMatrix Tiered Storage Memory Test Suite provides comprehensive validation of the tiered storage system's functionality and performance. By following this documentation, you can:

1. **Validate** correct operation of the tiered storage system
2. **Measure** performance characteristics for your hardware
3. **Stress test** the system under various conditions
4. **Debug** issues with detailed diagnostic information
5. **Optimize** configuration for your specific use case

The test suite ensures that the tiered storage system meets all requirements for:
- Data integrity and preservation
- Automatic storage management
- Power failure recovery
- Performance targets
- Resource efficiency

For additional support or custom test scenarios, refer to the source code comments and the main tiered storage documentation.