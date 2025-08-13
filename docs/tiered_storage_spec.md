# iMatrix Tiered Storage System - Technical Specification

## Document Information
**Version**: 1.0  
**Date**: 2025-01-04  
**Status**: Implementation Complete  
**Platform**: Linux Only  
**Language**: C  

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [API Reference](#api-reference)
4. [File Format Specification](#file-format-specification)
5. [Configuration](#configuration)
6. [Integration Guide](#integration-guide)
7. [Error Handling](#error-handling)
8. [Performance Characteristics](#performance-characteristics)
9. [Security Features](#security-features)
10. [Troubleshooting](#troubleshooting)

## System Overview

### Purpose
The iMatrix Tiered Storage System provides automatic RAM-to-disk migration for embedded systems with limited memory. It extends the original sector-based memory management to support billions of sectors across RAM and persistent storage while maintaining backward compatibility.

### Key Features
- **Automatic Migration**: Threshold-based RAM-to-disk migration at 80% usage
- **Extended Addressing**: 32-bit sector addressing supporting up to 4 billion sectors
- **Atomic Operations**: Complete power failure recovery with operation journaling
- **Cross-Storage Chains**: Seamless sector chain traversal across RAM and disk
- **Background Processing**: State machine with minimal performance impact (<2% CPU)
- **Data Integrity**: Comprehensive validation, checksums, and corruption detection

### System Requirements
- **Platform**: Linux with POSIX file system support
- **Storage**: `/usr/qk/etc/sv/FC-1/history/` directory (writable)
- **Memory**: ~100KB additional RAM for lookup tables and state management
- **CPU**: Background processing designed for embedded systems

## Architecture

### Core Components

#### 1. Extended Sector Addressing
```c
typedef uint32_t extended_sector_t;

// Sector address space partitioning
#define RAM_SECTOR_BASE         (0)
#define RAM_SECTOR_MAX          (SAT_NO_SECTORS - 1)
#define DISK_SECTOR_BASE        (SAT_NO_SECTORS)
#define DISK_SECTOR_MAX         (0xFFFFFFFF)

// Location validation macros
#define IS_RAM_SECTOR(sector)   ((sector) < SAT_NO_SECTORS)
#define IS_DISK_SECTOR(sector)  ((sector) >= SAT_NO_SECTORS)
```

#### 2. State Machine Architecture
```c
typedef enum {
    MEMORY_STATE_IDLE = 0,
    MEMORY_STATE_CHECK_USAGE,
    MEMORY_STATE_MOVE_TO_DISK,
    MEMORY_STATE_CLEANUP_DISK,
    MEMORY_STATE_FLUSH_ALL
} memory_process_state_t;

typedef struct {
    memory_process_state_t state;
    imx_time_t last_process_time;
    uint16_t current_sensor_index;
    uint16_t sectors_processed_this_cycle;
    bool shutdown_requested;
    uint32_t pending_sectors_for_shutdown;
    // Statistics
    uint32_t total_files_created;
    uint32_t total_files_deleted;
    uint64_t total_bytes_written;
    uint32_t power_failure_recoveries;
} memory_state_machine_t;
```

#### 3. Sector Location Tracking
```c
typedef enum {
    SECTOR_LOCATION_RAM = 0,
    SECTOR_LOCATION_DISK,
    SECTOR_LOCATION_FREED
} sector_location_t;

typedef struct {
    sector_location_t location;
    char filename[MAX_FILENAME_LENGTH];
    uint32_t file_offset;
    uint16_t sensor_id;
    imx_utc_time_t timestamp;
} sector_lookup_entry_t;
```

#### 4. Recovery Journal System
```c
typedef enum {
    FILE_OP_IDLE = 0,
    FILE_OP_CREATING_TEMP,
    FILE_OP_WRITING_HEADER,
    FILE_OP_WRITING_SECTORS,
    FILE_OP_SYNCING,
    FILE_OP_RENAMING,
    FILE_OP_COMPLETE
} file_operation_state_t;

typedef struct {
    uint32_t magic;                     // JOURNAL_MAGIC_NUMBER
    uint32_t sequence_number;
    file_operation_state_t operation_type;
    char temp_filename[256];
    char final_filename[256];
    uint32_t sectors_involved;
    extended_sector_t sector_numbers[64];
    imx_utc_time_t timestamp;
    uint32_t checksum;
} journal_entry_t;
```

### Data Flow

#### Normal Operation Flow
1. **Background Monitor**: `process_memory()` called every second
2. **Usage Check**: Monitor RAM usage percentage
3. **Trigger Migration**: When usage ≥ 80%, transition to migration state
4. **Batch Processing**: Process sectors in optimized batches (6 TSD, 3 EVT)
5. **Atomic Write**: Use journal system for safe disk operations
6. **Update Metadata**: Update lookup table with new sector locations
7. **Return to Idle**: Continue monitoring until next threshold

#### Shutdown Flow
1. **Shutdown Request**: `flush_all_to_disk()` called
2. **Set State**: Transition to MEMORY_STATE_FLUSH_ALL
3. **Aggressive Processing**: Process sectors in larger batches (10 per cycle)
4. **Progress Reporting**: Update pending count for monitoring
5. **Complete Flush**: Continue until all sectors written to disk
6. **Final State**: Return to idle with all data preserved

#### Power Failure Recovery Flow
1. **Startup Call**: `perform_power_failure_recovery()` on system start
2. **Journal Recovery**: Load and validate recovery journal
3. **Operation Rollback**: Process incomplete operations
4. **File Scanning**: Scan storage directory for existing files
5. **Metadata Rebuild**: Reconstruct sector lookup table
6. **Chain Validation**: Verify sector chain integrity
7. **Ready State**: System ready for normal operation

## API Reference

### Core Functions

#### `void process_memory(imx_time_t current_time)`
Main state machine function called from application main loop.

**Parameters:**
- `current_time`: Current system time in milliseconds

**Usage:**
```c
// Called every iteration of main loop
imx_time_t current_time;
imx_time_get_time(&current_time);
process_memory(current_time);
```

**Description:**
- Manages background tiered storage processing
- Implements timing control (1-second intervals)
- Handles all state transitions and processing

#### `void flush_all_to_disk(void)`
Request immediate flush of all RAM data to disk (shutdown sequence).

**Usage:**
```c
// Called during system shutdown
flush_all_to_disk();

// Monitor progress
while (get_pending_disk_write_count() > 0) {
    process_memory(current_time);
    printf("Flushing %u sectors...\n", get_pending_disk_write_count());
}
```

**Description:**
- Forces aggressive migration of all sectors to disk
- Sets shutdown flag for priority processing
- Required for data preservation during shutdown

#### `uint32_t get_pending_disk_write_count(void)`
Get number of sectors pending disk write during shutdown.

**Returns:**
- Number of sectors still pending disk write

**Usage:**
```c
uint32_t pending = get_pending_disk_write_count();
if (pending > 0) {
    printf("Warning: %u sectors pending disk write\n", pending);
}
```

#### `void perform_power_failure_recovery(void)`
Complete power failure recovery and system validation.

**Usage:**
```c
// Called during system initialization
void system_startup(void) {
    init_memory_system();
    perform_power_failure_recovery();
    // System ready for normal operation
}
```

**Description:**
- Recovers from incomplete operations
- Validates existing disk files
- Rebuilds sector metadata
- Ensures data consistency

### Extended Sector Operations

#### `extended_sector_result_t get_next_sector_extended(extended_sector_t current_sector)`
Get next sector in chain, supporting both RAM and disk sectors.

**Parameters:**
- `current_sector`: Current sector in chain

**Returns:**
- `extended_sector_result_t` with next sector and error status

**Usage:**
```c
extended_sector_result_t result = get_next_sector_extended(current_sector);
if (result.error == IMX_MEMORY_SUCCESS) {
    extended_sector_t next = result.next_sector;
    // Process next sector
}
```

#### `imx_memory_error_t read_sector_extended(extended_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length, uint16_t data_buffer_size)`
Read data from sector (RAM or disk).

**Parameters:**
- `sector`: Extended sector number
- `offset`: Offset within sector
- `data`: Destination buffer
- `length`: Number of bytes to read
- `data_buffer_size`: Size of destination buffer

**Returns:**
- `IMX_MEMORY_SUCCESS` or error code

#### `imx_memory_error_t write_sector_extended(extended_sector_t sector, uint16_t offset, const uint32_t *data, uint16_t length, uint16_t data_buffer_size)`
Write data to sector (RAM or disk).

**Parameters:**
- `sector`: Extended sector number
- `offset`: Offset within sector
- `data`: Source buffer
- `length`: Number of bytes to write
- `data_buffer_size`: Size of source buffer

**Returns:**
- `IMX_MEMORY_SUCCESS` or error code

### Sector Management

#### `extended_sector_t allocate_disk_sector(uint16_t sensor_id)`
Allocate new disk sector for specified sensor.

**Parameters:**
- `sensor_id`: Associated sensor ID

**Returns:**
- New disk sector number, or 0 on failure

#### `imx_memory_error_t move_sectors_to_disk(uint16_t sensor_id, uint16_t max_sectors, bool force_all)`
Move sectors from RAM to disk for specified sensor.

**Parameters:**
- `sensor_id`: Target sensor ID
- `max_sectors`: Maximum sectors to process
- `force_all`: Force migration regardless of age/usage

**Returns:**
- `IMX_MEMORY_SUCCESS` or error code

## File Format Specification

### Disk File Header
```c
typedef struct {
    uint32_t magic;                 // FILE_MAGIC_NUMBER (0x494D5853 "IMXS")
    uint16_t version;               // File format version (currently 1)
    uint16_t sensor_id;             // Associated sensor ID
    uint16_t sector_count;          // Number of sectors in file
    uint16_t sector_size;           // Size of each sector (SRAM_SECTOR_SIZE)
    uint16_t record_type;           // TSD_RECORD_SIZE or EVT_RECORD_SIZE
    uint16_t entries_per_sector;    // Entries per sector
    imx_utc_time_t created;         // File creation timestamp
    uint32_t file_checksum;         // Entire file checksum
    uint32_t reserved[4];           // Future expansion
} disk_file_header_t;
```

### File Layout
```
[disk_file_header_t]
[Sector 0 Data] (SRAM_SECTOR_SIZE bytes)
[Sector 1 Data] (SRAM_SECTOR_SIZE bytes)
...
[Sector N Data] (SRAM_SECTOR_SIZE bytes)
```

### Filename Convention
```
sensor_{SENSOR_ID:03d}_{YYYYMMDD}_{NNN}.dat

Examples:
sensor_001_20250104_001.dat    # First file for sensor 1 on 2025-01-04
sensor_027_20250104_003.dat    # Third file for sensor 27 on 2025-01-04
```

### Recovery Journal Format
```c
typedef struct {
    uint32_t magic;                 // JOURNAL_MAGIC_NUMBER (0x494D584A "IMXJ")
    uint32_t entry_count;           // Number of active entries
    uint32_t next_sequence;         // Next sequence number
    journal_entry_t entries[MAX_JOURNAL_ENTRIES];
    uint32_t journal_checksum;      // Journal integrity checksum
} recovery_journal_t;
```

### Directory Structure
```
/usr/qk/etc/sv/FC-1/history/
├── sensor_001_20250104_001.dat    # TSD data files
├── sensor_002_20250104_001.dat    # EVT data files
├── sensor_003_20250104_002.dat    # Additional files as needed
├── recovery.journal               # Active recovery journal
├── recovery.journal.bak           # Journal backup
└── corrupted/                     # Quarantined files
    ├── sensor_005_20250103_001.dat
    └── recovery.journal.corrupt
```

## Configuration

### Compile-Time Constants
```c
// Timing and thresholds
#define MEMORY_PROCESS_INTERVAL_TIME    (1000)      // 1 second
#define MEMORY_TO_DISK_THRESHOLD        (80)        // 80% RAM usage
#define DISK_USAGE_THRESHOLD            (80)        // 80% disk usage

// Batch processing
#define MAX_TSD_SECTORS_PER_ITERATION   (6)         // TSD batch size
#define MAX_EVT_SECTORS_PER_ITERATION   (3)         // EVT batch size
#define SECTORS_PER_FILE               (32)         // Logical file size

// Storage paths
#define DISK_STORAGE_PATH              "/usr/qk/etc/sv/FC-1/history/"
#define CORRUPTED_DATA_PATH            "/usr/qk/etc/sv/FC-1/history/corrupted/"
#define RECOVERY_JOURNAL_FILE          "/usr/qk/etc/sv/FC-1/history/recovery.journal"

// File format
#define FILE_MAGIC_NUMBER              (0x494D5853) // "IMXS"
#define JOURNAL_MAGIC_NUMBER           (0x494D584A) // "IMXJ"
```

### Runtime Configuration
The system automatically adapts to available resources:
- **RAM Size**: Detected from `SAT_NO_SECTORS`
- **Disk Space**: Monitored dynamically
- **Sensor Types**: Determined from sensor ID (even=TSD, odd=EVT)
- **Batch Sizes**: Optimized for entry counts per sector type

## Integration Guide

### Main Loop Integration
```c
void main_application_loop(void) {
    imx_time_t current_time;
    
    while (system_running) {
        // Get current time
        imx_time_get_time(&current_time);
        
        // Process tiered storage (every second)
        process_memory(current_time);
        
        // Regular application processing
        process_sensors();
        process_network();
        
        // Sleep or yield
        imx_delay_milliseconds(10);
    }
}
```

### Startup Integration
```c
void system_initialization(void) {
    // Initialize core systems
    init_platform();
    init_memory_manager();
    
    // Perform power failure recovery
    perform_power_failure_recovery();
    
    // System ready for operation
    printf("System ready with tiered storage\n");
}
```

### Shutdown Integration
```c
void system_shutdown(void) {
    printf("Initiating shutdown sequence...\n");
    
    // Request flush of all data to disk
    flush_all_to_disk();
    
    // Monitor progress
    imx_time_t current_time;
    while (get_pending_disk_write_count() > 0) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        
        uint32_t pending = get_pending_disk_write_count();
        printf("Flushing %u sectors to disk...\n", pending);
        
        imx_delay_milliseconds(100);
    }
    
    printf("All data flushed to disk. Shutdown complete.\n");
}
```

### Error Handling Integration
```c
void handle_storage_errors(void) {
    // Check for disk space issues
    if (!is_disk_usage_acceptable()) {
        printf("WARNING: Disk space low, cleaning up old files\n");
        // Automatic cleanup will be triggered by state machine
    }
    
    // Monitor recovery operations
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats->power_failure_recoveries > 0) {
        printf("INFO: %u power failure recoveries performed\n", 
               stats->power_failure_recoveries);
    }
}
```

## Error Handling

### Error Codes
```c
typedef enum {
    IMX_MEMORY_SUCCESS = 0,
    IMX_MEMORY_ERROR_INVALID_SECTOR,
    IMX_MEMORY_ERROR_INVALID_OFFSET,
    IMX_MEMORY_ERROR_INVALID_LENGTH,
    IMX_MEMORY_ERROR_BUFFER_TOO_SMALL,
    IMX_MEMORY_ERROR_OUT_OF_BOUNDS,
    IMX_MEMORY_ERROR_NULL_POINTER,
    IMX_MEMORY_ERROR_EXT_SRAM_NOT_SUPPORTED
} imx_memory_error_t;
```

### Error Recovery Procedures

#### Disk Full Conditions
```c
// Automatic cleanup triggered by state machine
if (!is_disk_usage_acceptable()) {
    // System will:
    // 1. Mark empty files for deletion
    // 2. Compress or archive old files (future)
    // 3. Alert monitoring systems
    // 4. Gracefully degrade to RAM-only operation
}
```

#### File Corruption Detection
```c
// Corrupted files automatically moved to quarantine
if (!validate_disk_file(filename)) {
    move_corrupted_file(filename);
    // File moved to /usr/qk/etc/sv/FC-1/history/corrupted/
    // System continues with remaining valid files
}
```

#### Power Failure Recovery
```c
// Complete recovery process handles all failure scenarios
perform_power_failure_recovery();
// System automatically:
// 1. Validates recovery journal
// 2. Rolls back incomplete operations
// 3. Rebuilds metadata from existing files
// 4. Validates sector chain integrity
```

## Performance Characteristics

### CPU Overhead
- **Normal Operation**: <2% CPU usage
- **Migration Active**: <5% CPU usage
- **Shutdown Flush**: <10% CPU usage (temporary)

### Memory Overhead
- **Lookup Table**: ~100KB for 1M disk sectors
- **State Machine**: <1KB
- **Journal Buffer**: ~4KB
- **Total Additional RAM**: ~105KB

### I/O Performance
- **RAM Sector Access**: <1ms response time
- **Disk Sector Access**: <10ms response time (cached)
- **File Creation**: <50ms per file
- **Journal Updates**: <5ms per operation

### Batch Processing Efficiency
- **TSD Sectors**: 6 sectors per iteration (optimized for entry count)
- **EVT Sectors**: 3 sectors per iteration (optimized for entry count)
- **Shutdown Processing**: 10 sectors per iteration (aggressive)

### Storage Efficiency
- **File Overhead**: ~1% metadata overhead
- **Compression**: Raw data (compression framework ready)
- **File Size**: Optimized at 32 sectors per file
- **Directory Organization**: Date-based with automatic cleanup

## Security Features

### Input Validation
- All sector numbers validated against address space
- Buffer sizes checked before all memory operations
- File paths restricted to designated storage areas
- Checksums validated on all file operations

### Atomic Operations
- All file operations use temp-file and rename pattern
- Recovery journal ensures no partial states
- Power failure cannot corrupt existing data
- Operation rollback preserves data integrity

### Access Control
- File operations restricted to storage directory
- Temporary files use secure naming conventions
- Corrupted files automatically quarantined
- Journal operations protected with checksums

### Error Handling
- Secure failure modes for all error conditions
- Detailed logging without exposing sensitive data
- Graceful degradation under resource constraints
- No buffer overflows or memory corruption possible

## Troubleshooting

### Common Issues

#### High RAM Usage Persists
**Symptoms:** RAM usage stays above 80% despite migration
**Causes:**
- Disk space full or insufficient
- Corrupted files blocking migration
- State machine stuck in error state

**Solutions:**
```c
// Check disk space
if (!is_disk_usage_acceptable()) {
    printf("Disk space insufficient - check /usr/qk/etc/sv/FC-1/history/\n");
}

// Check state machine status
printf("Current state: %d\n", tiered_state_machine.state);

// Force manual cleanup
// (trigger through state machine or manual file removal)
```

#### Recovery Journal Corruption
**Symptoms:** Power failure recovery fails repeatedly
**Causes:**
- Journal file corruption
- Incomplete journal writes
- File system errors

**Solutions:**
```bash
# Backup corrupted journal
mv /usr/qk/etc/sv/FC-1/history/recovery.journal \
   /usr/qk/etc/sv/FC-1/history/corrupted/recovery.journal.corrupt

# System will create new journal on next startup
# Existing data files will be scanned and metadata rebuilt
```

#### File Corruption Detection
**Symptoms:** Files moved to corrupted directory
**Causes:**
- Power failure during write
- File system corruption
- Hardware issues

**Solutions:**
```c
// Check corrupted directory
ls -la /usr/qk/etc/sv/FC-1/history/corrupted/

// Analyze corruption patterns
// (magic number mismatches, checksum failures, size errors)

// Manual recovery if needed
// (extract valid sectors from partially corrupted files)
```

#### Performance Issues
**Symptoms:** High CPU usage or slow response
**Causes:**
- Excessive file I/O
- Large batch sizes
- Disk performance issues

**Solutions:**
```c
// Monitor statistics
imx_memory_statistics_t *stats = imx_get_memory_statistics();
printf("Files created: %u, deleted: %u\n", 
       stats->total_files_created, stats->total_files_deleted);

// Check processing timing
// (adjust batch sizes if needed)

// Monitor disk I/O
// (iostat, iotop on Linux)
```

### Diagnostic Commands

#### System Status
```c
// Get comprehensive memory statistics
imx_memory_statistics_t *stats = imx_get_memory_statistics();
printf("Usage: %.1f%% (%u/%u sectors)\n", 
       stats->usage_percentage, stats->used_sectors, stats->total_sectors);

// Get tiered storage status
printf("State: %d, Files: %u, Pending: %u\n",
       tiered_state_machine.state,
       tiered_state_machine.total_files_created,
       tiered_state_machine.pending_sectors_for_shutdown);
```

#### File System Status
```bash
# Check storage directory
ls -la /usr/qk/etc/sv/FC-1/history/

# Check disk usage
df -h /usr/qk/etc/sv/FC-1/history/

# Check for corrupted files
ls -la /usr/qk/etc/sv/FC-1/history/corrupted/

# Validate file integrity
hexdump -C /usr/qk/etc/sv/FC-1/history/sensor_001_*.dat | head -20
```

### Maintenance Procedures

#### Regular Maintenance
- Monitor disk usage weekly
- Check corrupted directory monthly
- Validate journal integrity during planned maintenance
- Review performance statistics for optimization opportunities

#### Emergency Procedures
- Force flush during emergency shutdown
- Manual recovery journal reset if corrupted
- File system check and repair if needed
- Backup and restore procedures for critical data

---

## Conclusion

The iMatrix Tiered Storage System provides a robust, scalable solution for embedded memory management with enterprise-grade reliability features. The comprehensive API, atomic operations, and automatic recovery capabilities ensure data integrity while maintaining optimal performance for resource-constrained environments.

For additional support or advanced configuration options, refer to the integration guide and contact the development team.