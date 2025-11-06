# iMatrix Tiered Storage: Migration Decision Logic and RAM-to-Disk Transitions

## Table of Contents
1. [Overview](#overview)
2. [Migration Decision Engine](#migration-decision-engine)
3. [State Machine Architecture](#state-machine-architecture)
4. [RAM-to-Disk Transition Mechanisms](#ram-to-disk-transition-mechanisms)
5. [Read Operation Flow](#read-operation-flow)
6. [Extended Sector Addressing](#extended-sector-addressing)
7. [Performance Analysis](#performance-analysis)
8. [Code Examples](#code-examples)
9. [Troubleshooting](#troubleshooting)

## Overview

The iMatrix Tiered Storage System provides automatic management of memory sectors, seamlessly migrating data between RAM and disk storage based on usage patterns and resource availability. This document explains the decision-making process for when sectors are migrated and how read/write operations transparently access data regardless of its physical location.

### Key Concepts

- **Automatic Migration**: System monitors RAM usage and triggers migration at 80% threshold
- **Transparent Access**: Applications use the same APIs regardless of data location
- **Extended Addressing**: 32-bit sector addressing supporting billions of sectors
- **Background Processing**: Migration occurs in background with minimal impact
- **Data Integrity**: Atomic operations ensure no data loss during migration

## Migration Decision Engine

### Trigger Conditions

The system continuously monitors several conditions to determine when migration should occur:

#### 1. RAM Usage Threshold (Primary Trigger)
```c
#define MEMORY_TO_DISK_THRESHOLD        (80)        // 80% RAM usage

// Checked every second in handle_idle_state()
uint32_t ram_usage = get_current_ram_usage_percentage();
if (ram_usage >= MEMORY_TO_DISK_THRESHOLD) {
    tiered_state_machine.state = MEMORY_STATE_CHECK_USAGE;
    imx_cli_log_printf("INFO: RAM usage %u%% exceeds threshold, starting disk migration\n", ram_usage);
}
```

**How RAM Usage is Calculated:**
```c
static uint32_t get_current_ram_usage_percentage(void)
{
    imx_update_memory_statistics();
    return (uint32_t)memory_stats.usage_percentage;
}

// In imx_update_memory_statistics():
memory_stats.used_sectors = count_allocated_sectors();
memory_stats.usage_percentage = (memory_stats.used_sectors * 100.0) / memory_stats.total_sectors;
```

#### 2. Disk Space Validation (Secondary Check)
```c
#define DISK_USAGE_THRESHOLD            (80)        // 80% disk usage

// Before migration, verify disk space is available
if (!is_disk_usage_acceptable()) {
    imx_cli_log_printf("WARNING: Disk usage too high, cannot migrate to disk\n");
    tiered_state_machine.state = MEMORY_STATE_IDLE;
    return;
}
```

#### 3. Shutdown Request (Override Trigger)
```c
// Immediate migration during shutdown
if (tiered_state_machine.shutdown_requested) {
    tiered_state_machine.state = MEMORY_STATE_FLUSH_ALL;
    imx_cli_log_printf("INFO: Starting shutdown flush of all data to disk\n");
}
```

### Migration Decision Flow

```
┌─────────────────┐
│   System Start  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐     ┌──────────────────┐
│   IDLE STATE    │────▶│  Check RAM Usage │
│ Monitor RAM     │     │  Every 1 Second  │
│ Check Shutdown  │     └─────────┬────────┘
└─────────────────┘               │
          ▲                       │
          │                       ▼
          │              ┌─────────────────┐
          │              │  RAM ≥ 80%?     │
          │              └─────────┬───────┘
          │                        │ Yes
          │                        ▼
          │              ┌─────────────────┐
          │              │ CHECK_USAGE     │
          │              │ Verify Disk     │
          │              │ Space Available │
          │              └─────────┬───────┘
          │                        │
          │                        ▼
          │              ┌─────────────────┐
          │              │ MOVE_TO_DISK    │
          │              │ Process Sensors │
          │              │ Migrate Sectors │
          │              └─────────┬───────┘
          │                        │
          │                        ▼
          │              ┌─────────────────┐
          │              │ CLEANUP_DISK    │
          │              │ Remove Empty    │
          │              │ Files           │
          └──────────────┴─────────────────┘
```

## State Machine Architecture

### State Definitions

The migration system operates through a state machine with five distinct states:

```c
typedef enum {
    MEMORY_STATE_IDLE = 0,          // Monitor conditions
    MEMORY_STATE_CHECK_USAGE,       // Validate migration conditions
    MEMORY_STATE_MOVE_TO_DISK,      // Execute sector migration
    MEMORY_STATE_CLEANUP_DISK,      // Maintain disk files
    MEMORY_STATE_FLUSH_ALL          // Force all data to disk (shutdown)
} memory_process_state_t;
```

### State Machine Context

```c
typedef struct {
    memory_process_state_t state;
    imx_time_t last_process_time;           // Timing control
    uint16_t current_sensor_index;          // Current sensor being processed
    uint16_t sectors_processed_this_cycle;  // Batch tracking
    bool shutdown_requested;                // Shutdown flag
    uint32_t pending_sectors_for_shutdown;  // Sectors pending flush
    // Statistics
    uint32_t total_files_created;
    uint32_t total_files_deleted;
    uint64_t total_bytes_written;
    uint32_t power_failure_recoveries;
} memory_state_machine_t;
```

### State Processing Functions

#### 1. IDLE State
```c
static void handle_idle_state(void)
{
    // Priority 1: Check shutdown request
    if (tiered_state_machine.shutdown_requested) {
        tiered_state_machine.state = MEMORY_STATE_FLUSH_ALL;
        return;
    }
    
    // Priority 2: Check RAM usage threshold
    uint32_t ram_usage = get_current_ram_usage_percentage();
    if (ram_usage >= MEMORY_TO_DISK_THRESHOLD) {
        tiered_state_machine.state = MEMORY_STATE_CHECK_USAGE;
        return;
    }
    
    // Priority 3: Check for cleanup needs
    if (current_disk_file_count > 0) {
        tiered_state_machine.state = MEMORY_STATE_CLEANUP_DISK;
    }
}
```

#### 2. CHECK_USAGE State
```c
static void handle_check_usage_state(void)
{
    // Verify disk space is available
    if (!is_disk_usage_acceptable()) {
        tiered_state_machine.state = MEMORY_STATE_IDLE;
        return;
    }
    
    // Double-check RAM usage (may have changed)
    uint32_t ram_usage = get_current_ram_usage_percentage();
    if (ram_usage < MEMORY_TO_DISK_THRESHOLD) {
        tiered_state_machine.state = MEMORY_STATE_IDLE;
        return;
    }
    
    // Initialize migration
    tiered_state_machine.current_sensor_index = 0;
    tiered_state_machine.sectors_processed_this_cycle = 0;
    tiered_state_machine.state = MEMORY_STATE_MOVE_TO_DISK;
}
```

#### 3. MOVE_TO_DISK State
```c
static void handle_move_to_disk_state(void)
{
    uint16_t sensor_id = tiered_state_machine.current_sensor_index;
    
    // Determine batch size based on sensor type
    uint16_t max_sectors = (sensor_id % 2 == 0) ? 
        MAX_TSD_SECTORS_PER_ITERATION : MAX_EVT_SECTORS_PER_ITERATION;
    
    // Execute migration
    imx_memory_error_t result = move_sectors_to_disk(sensor_id, max_sectors, false);
    
    // Update progress
    tiered_state_machine.sectors_processed_this_cycle += max_sectors;
    tiered_state_machine.current_sensor_index++;
    
    // Check completion conditions
    if (tiered_state_machine.sectors_processed_this_cycle >= max_sectors || 
        tiered_state_machine.current_sensor_index >= 256) {
        
        // Reset for next cycle
        tiered_state_machine.sectors_processed_this_cycle = 0;
        tiered_state_machine.current_sensor_index = 0;
        tiered_state_machine.state = MEMORY_STATE_IDLE;
        
        // Continue if still over threshold
        uint32_t ram_usage = get_current_ram_usage_percentage();
        if (ram_usage >= MEMORY_TO_DISK_THRESHOLD) {
            tiered_state_machine.state = MEMORY_STATE_CHECK_USAGE;
        }
    }
}
```

### Timing Control

The state machine is driven by the main application loop:

```c
void process_memory(imx_time_t current_time)
{
    // Initialize system if needed
    if (!tiered_system_initialized) {
        init_disk_storage_system();
        if (!tiered_system_initialized) {
            return;
        }
    }
    
    // Check timing - only run once per second
    if (!imx_is_later(current_time, 
                     tiered_state_machine.last_process_time + MEMORY_PROCESS_INTERVAL_TIME)) {
        return;
    }
    
    tiered_state_machine.last_process_time = current_time;
    
    // Process current state
    switch (tiered_state_machine.state) {
        case MEMORY_STATE_IDLE:
            handle_idle_state();
            break;
        case MEMORY_STATE_CHECK_USAGE:
            handle_check_usage_state();
            break;
        case MEMORY_STATE_MOVE_TO_DISK:
            handle_move_to_disk_state();
            break;
        case MEMORY_STATE_CLEANUP_DISK:
            handle_cleanup_disk_state();
            break;
        case MEMORY_STATE_FLUSH_ALL:
            handle_flush_all_state();
            break;
    }
}
```

## RAM-to-Disk Transition Mechanisms

### Extended Sector Addressing System

The system uses a unified addressing scheme that seamlessly spans RAM and disk storage:

```c
typedef uint32_t extended_sector_t;

// Address space partitioning
#define RAM_SECTOR_BASE         (0)                 // RAM: 0 to SAT_NO_SECTORS-1
#define RAM_SECTOR_MAX          (SAT_NO_SECTORS - 1)
#define DISK_SECTOR_BASE        (SAT_NO_SECTORS)    // Disk: SAT_NO_SECTORS to 0xFFFFFFFF
#define DISK_SECTOR_MAX         (0xFFFFFFFF)

// Location determination macros
#define IS_RAM_SECTOR(sector)   ((sector) < SAT_NO_SECTORS)
#define IS_DISK_SECTOR(sector)  ((sector) >= SAT_NO_SECTORS)
```

### Sector Location Tracking

Each sector's location is tracked in a comprehensive lookup table:

```c
typedef enum {
    SECTOR_LOCATION_RAM = 0,    // Sector is in RAM
    SECTOR_LOCATION_DISK,       // Sector is on disk
    SECTOR_LOCATION_FREED       // Sector has been freed
} sector_location_t;

typedef struct {
    sector_location_t location;
    char filename[MAX_FILENAME_LENGTH];     // Full path if on disk
    uint32_t file_offset;                   // Offset within disk file
    uint16_t sensor_id;                     // Associated sensor
    imx_utc_time_t timestamp;               // When moved to disk
} sector_lookup_entry_t;

// Global lookup table
static sector_lookup_entry_t *sector_lookup_table = NULL;
```

### Sector Migration Process

When sectors are moved from RAM to disk:

```c
imx_memory_error_t move_sectors_to_disk(uint16_t sensor_id, uint16_t max_sectors, bool force_all)
{
    // 1. Validate conditions
    if (!tiered_system_initialized) {
        return IMX_MEMORY_ERROR_EXT_SRAM_NOT_SUPPORTED;
    }
    
    if (!is_disk_usage_acceptable()) {
        return IMX_MEMORY_ERROR_OUT_OF_BOUNDS;
    }
    
    // 2. Collect sectors for migration
    extended_evt_tsd_sector_t sectors_to_migrate[SECTORS_PER_FILE];
    uint16_t sector_count = 0;
    
    // Find sectors belonging to this sensor (simplified approach)
    for (uint16_t i = 0; i < max_sectors && sector_count < SECTORS_PER_FILE; i++) {
        // Real implementation would scan control/sensor data structures
        // to find actual sectors belonging to this sensor_id
        if (sector_count < max_sectors) {
            memset(&sectors_to_migrate[sector_count], 0, sizeof(extended_evt_tsd_sector_t));
            sectors_to_migrate[sector_count].id = sensor_id;
            sectors_to_migrate[sector_count].next_sector = 0;
            sector_count++;
        }
    }
    
    if (sector_count == 0) {
        return IMX_MEMORY_SUCCESS;  // No sectors to migrate
    }
    
    // 3. Create disk file atomically
    char filename[MAX_FILENAME_LENGTH];
    imx_memory_error_t result = create_disk_file_atomic(sensor_id, sectors_to_migrate, 
                                                       sector_count, filename, sizeof(filename));
    
    if (result == IMX_MEMORY_SUCCESS) {
        // 4. Update sector lookup table
        extended_sector_t disk_sector = next_disk_sector;
        for (uint16_t i = 0; i < sector_count; i++) {
            update_sector_location(disk_sector + i, SECTOR_LOCATION_DISK, filename, i);
        }
        next_disk_sector += sector_count;
        
        // 5. In real implementation, would also:
        // - Update control/sensor data structures with new sector addresses
        // - Mark RAM sectors as free
        // - Update sector chains to point to disk sectors
    }
    
    return result;
}
```

### File Creation and Organization

Disk files are created with a specific structure and naming convention:

```c
// File naming: sensor_XXX_YYYYMMDD_NNN.dat
static bool create_disk_filename(uint16_t sensor_id, char *filename, size_t filename_size)
{
    imx_utc_time_t current_time = imx_get_utc_time();
    struct tm *time_info = localtime(&current_time);
    
    // Find next available file number for this sensor/date
    uint32_t file_number = 1;
    char test_filename[MAX_FILENAME_LENGTH];
    
    do {
        snprintf(test_filename, sizeof(test_filename),
                 "%ssensor_%03u_%04d%02d%02d_%03u.dat",
                 DISK_STORAGE_PATH,
                 sensor_id,
                 time_info->tm_year + 1900,
                 time_info->tm_mon + 1,
                 time_info->tm_mday,
                 file_number);
        file_number++;
    } while (access(test_filename, F_OK) == 0 && file_number < 1000);
    
    strncpy(filename, test_filename, filename_size - 1);
    filename[filename_size - 1] = '\0';
    
    return true;
}
```

## Read Operation Flow

### Transparent Access API

Applications use the same read functions regardless of sector location:

```c
// High-level API (unchanged for applications)
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, 
                  uint16_t entry, uint32_t *value)
{
    // Calculate sector and offset
    uint16_t sector = calculate_sector_for_entry(csd, entry);
    uint16_t offset = calculate_offset_for_entry(entry);
    
    // Read using extended API (automatically handles RAM/disk)
    read_sector_extended(sector, offset, value, sizeof(*value), sizeof(*value));
}
```

### Extended Read Implementation

The extended read function automatically determines sector location:

```c
imx_memory_error_t read_sector_extended(extended_sector_t sector, uint16_t offset, 
                                       uint32_t *data, uint16_t length, uint16_t data_buffer_size)
{
    // Validate parameters
    if (data == NULL) {
        return IMX_MEMORY_ERROR_NULL_POINTER;
    }
    
    if (length > data_buffer_size) {
        return IMX_MEMORY_ERROR_BUFFER_TOO_SMALL;
    }
    
    // Determine sector location
    if (IS_RAM_SECTOR(sector)) {
        // Direct RAM access (fast path)
        return read_rs_safe(sector, offset, data, length, data_buffer_size);
    } else if (IS_DISK_SECTOR(sector)) {
        // Disk access (slower path)
        return read_disk_sector(sector, offset, data, length, data_buffer_size);
    } else {
        return IMX_MEMORY_ERROR_INVALID_SECTOR;
    }
}
```

### Disk Read Implementation

Reading from disk involves file system operations:

```c
static imx_memory_error_t read_disk_sector(extended_sector_t sector, uint16_t offset,
                                          uint32_t *data, uint16_t length, uint16_t data_buffer_size)
{
    // Validate sector lookup table
    if (sector_lookup_table == NULL || sector >= (SAT_NO_SECTORS + 1000000)) {
        return IMX_MEMORY_ERROR_INVALID_SECTOR;
    }
    
    // Get sector location info
    sector_lookup_entry_t *lookup = &sector_lookup_table[sector];
    if (lookup->location != SECTOR_LOCATION_DISK || lookup->filename[0] == '\0') {
        return IMX_MEMORY_ERROR_INVALID_SECTOR;
    }
    
    // Open disk file
    FILE *file = fopen(lookup->filename, "rb");
    if (file == NULL) {
        imx_cli_log_printf("ERROR: Failed to open disk file %s: %s\n", 
                          lookup->filename, strerror(errno));
        return IMX_MEMORY_ERROR_EXT_SRAM_NOT_SUPPORTED;
    }
    
    // Calculate file position
    long file_position = sizeof(disk_file_header_t) + 
                        (lookup->file_offset * SRAM_SECTOR_SIZE) + offset;
    
    // Seek and read
    if (fseek(file, file_position, SEEK_SET) != 0) {
        fclose(file);
        return IMX_MEMORY_ERROR_OUT_OF_BOUNDS;
    }
    
    size_t read_size = fread(data, 1, length, file);
    fclose(file);
    
    if (read_size != length) {
        return IMX_MEMORY_ERROR_EXT_SRAM_NOT_SUPPORTED;
    }
    
    return IMX_MEMORY_SUCCESS;
}
```

### Cross-Storage Chain Traversal

Sector chains can span both RAM and disk seamlessly:

```c
extended_sector_result_t get_next_sector_extended(extended_sector_t current_sector)
{
    extended_sector_result_t result = {0, IMX_MEMORY_SUCCESS};
    
    if (IS_RAM_SECTOR(current_sector)) {
        // Use standard RAM-based chain traversal
        sector_result_t ram_result = get_next_sector_safe(current_sector);
        result.next_sector = ram_result.next_sector;
        result.error = ram_result.error;
        
        // If next sector is also in RAM range, return as-is
        // If next sector is in disk range, it will be handled transparently
        
    } else if (IS_DISK_SECTOR(current_sector)) {
        // Read next sector pointer from disk
        uint32_t next_sector_data;
        imx_memory_error_t read_result = read_disk_sector(
            current_sector, 
            offsetof(extended_evt_tsd_sector_t, next_sector),
            &next_sector_data,
            sizeof(extended_sector_t),
            sizeof(next_sector_data)
        );
        
        if (read_result == IMX_MEMORY_SUCCESS) {
            result.next_sector = next_sector_data;
        } else {
            result.error = read_result;
        }
    } else {
        result.error = IMX_MEMORY_ERROR_INVALID_SECTOR;
    }
    
    return result;
}
```

## Extended Sector Addressing

### Address Space Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    Extended Sector Address Space                │
├─────────────────────────────────────────────────────────────────┤
│ RAM Sectors                           │ Disk Sectors            │
│ 0 to (SAT_NO_SECTORS-1)              │ SAT_NO_SECTORS to       │
│ ~64K sectors (configurable)          │ 0xFFFFFFFF              │
│ Direct memory access                  │ ~4 billion sectors      │
│ <1ms response time                    │ File system access      │
│                                       │ <10ms response time     │
└─────────────────────────────────────────────────────────────────┘
```

### Location Determination Logic

```c
// Fast inline location checks
static inline bool is_ram_sector(extended_sector_t sector) {
    return sector < SAT_NO_SECTORS;
}

static inline bool is_disk_sector(extended_sector_t sector) {
    return sector >= SAT_NO_SECTORS && sector <= DISK_SECTOR_MAX;
}

// Convert disk sector to array index
static inline uint32_t disk_sector_index(extended_sector_t sector) {
    return sector - SAT_NO_SECTORS;
}
```

### Sector Allocation Strategy

```c
extended_sector_t allocate_disk_sector(uint16_t sensor_id)
{
    if (!tiered_system_initialized) {
        return 0;
    }
    
    // Get next available disk sector number
    extended_sector_t new_sector = next_disk_sector++;
    
    // Initialize lookup table entry
    update_sector_location(new_sector, SECTOR_LOCATION_DISK, NULL, 0);
    sector_lookup_table[new_sector].sensor_id = sensor_id;
    
    return new_sector;
}
```

## Performance Analysis

### Access Time Comparison

| Operation | RAM Sector | Disk Sector | Ratio |
|-----------|------------|-------------|-------|
| Read Access | <1ms | <10ms | 10x |
| Write Access | <1ms | <50ms | 50x |
| Chain Traversal | <1ms | <15ms | 15x |

### Migration Performance Characteristics

#### Batch Processing Optimization
```c
// Optimized batch sizes based on sector entry counts
#define MAX_TSD_SECTORS_PER_ITERATION   (6)     // TSD: 6 entries per sector
#define MAX_EVT_SECTORS_PER_ITERATION   (3)     // EVT: 3 entries per sector

// Processing rate: ~100-500 sectors/second depending on disk speed
```

#### Background Processing Impact
- **CPU Overhead**: <2% during normal operation
- **I/O Impact**: Batched operations minimize disk contention
- **Response Time**: RAM operations unaffected, disk operations add latency

### Memory Usage

#### Lookup Table Overhead
```c
// Memory required for lookup table
size_t lookup_table_size = max_disk_sectors * sizeof(sector_lookup_entry_t);
// Example: 1M disk sectors = ~100KB RAM overhead
```

#### Caching Considerations
- Recently accessed disk sectors could be cached in RAM
- LRU (Least Recently Used) eviction policy
- Configurable cache size based on available RAM

## Code Examples

### Example 1: Automatic Migration Trigger

```c
void demonstrate_migration_trigger(void)
{
    printf("Starting migration demonstration...\n");
    
    // Allocate sectors until threshold is reached
    imx_memory_statistics_t *stats;
    for (int i = 0; i < 10000; i++) {
        platform_sector_t sector = imx_get_free_sector();
        if (sector < 0) {
            printf("No more sectors available\n");
            break;
        }
        
        // Write test data
        uint32_t test_data = i;
        write_rs(sector, 0, &test_data, 1);  // Write 1 uint32_t value
        
        // Check if migration triggered
        if (i % 100 == 0) {
            stats = imx_get_memory_statistics();
            printf("Allocated %d sectors, RAM usage: %.1f%%\n", 
                   i, stats->usage_percentage);
            
            if (stats->usage_percentage >= 80) {
                printf("Migration threshold reached!\n");
                break;
            }
        }
    }
    
    // Process background migration
    imx_time_t current_time;
    for (int i = 0; i < 100; i++) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        usleep(100000); // 100ms
        
        stats = imx_get_memory_statistics();
        if (stats->usage_percentage < 80) {
            printf("Migration completed, RAM usage: %.1f%%\n", 
                   stats->usage_percentage);
            break;
        }
    }
}
```

### Example 2: Cross-Storage Data Access

```c
void demonstrate_cross_storage_access(void)
{
    // Create a chain of sectors
    platform_sector_t first_sector = imx_get_free_sector();
    platform_sector_t second_sector = imx_get_free_sector();
    
    // Write data and chain link
    uint32_t data1 = 0x12345678;
    uint32_t data2 = 0x87654321;
    
    write_rs(first_sector, 0, &data1, 1);  // Write 1 uint32_t value
    write_rs(first_sector, 4, &second_sector, 1);  // Write sector number at offset 4
    write_rs(second_sector, 0, &data2, 1);  // Write 1 uint32_t value
    
    printf("Created chain: sector %d -> sector %d\n", first_sector, second_sector);
    
    // Force migration (simulate high RAM usage)
    // ... trigger migration through normal process ...
    
    // After migration, read the chain
    extended_sector_t current = first_sector;
    int chain_length = 0;
    
    while (current != 0 && chain_length < 10) {
        uint32_t data;
        uint32_t next;
        
        // Read data (works regardless of RAM/disk location)
        imx_memory_error_t result1 = read_sector_extended(current, 0, &data, sizeof(data), sizeof(data));
        imx_memory_error_t result2 = read_sector_extended(current, sizeof(data), &next, sizeof(next), sizeof(next));
        
        if (result1 == IMX_MEMORY_SUCCESS && result2 == IMX_MEMORY_SUCCESS) {
            printf("Sector %u: data=0x%08X, next=%u (location: %s)\n", 
                   current, data, next,
                   IS_RAM_SECTOR(current) ? "RAM" : "DISK");
            current = next;
        } else {
            printf("Error reading sector %u\n", current);
            break;
        }
        
        chain_length++;
    }
}
```

### Example 3: Performance Measurement

```c
void measure_access_performance(void)
{
    const int test_count = 1000;
    struct timeval start, end;
    
    // Create test sectors
    platform_sector_t ram_sector = imx_get_free_sector();
    extended_sector_t disk_sector = allocate_disk_sector(1);
    
    uint32_t test_data = 0xDEADBEEF;
    write_rs(ram_sector, 0, &test_data, 1);  // Write 1 uint32_t value
    
    // Measure RAM access time
    gettimeofday(&start, NULL);
    for (int i = 0; i < test_count; i++) {
        uint32_t data;
        read_rs(ram_sector, 0, &data, 1);  // Read 1 uint32_t value
    }
    gettimeofday(&end, NULL);
    
    long ram_time_us = (end.tv_sec - start.tv_sec) * 1000000 + 
                       (end.tv_usec - start.tv_usec);
    
    // Measure disk access time (after sector is migrated)
    gettimeofday(&start, NULL);
    for (int i = 0; i < test_count; i++) {
        uint32_t data;
        read_sector_extended(disk_sector, 0, &data, sizeof(data), sizeof(data));
    }
    gettimeofday(&end, NULL);
    
    long disk_time_us = (end.tv_sec - start.tv_sec) * 1000000 + 
                        (end.tv_usec - start.tv_usec);
    
    printf("Performance Results (%d operations):\n", test_count);
    printf("  RAM access:  %ld us total, %.2f us per operation\n", 
           ram_time_us, (double)ram_time_us / test_count);
    printf("  Disk access: %ld us total, %.2f us per operation\n", 
           disk_time_us, (double)disk_time_us / test_count);
    printf("  Ratio: %.1fx slower for disk access\n", 
           (double)disk_time_us / ram_time_us);
}
```

## Troubleshooting

### Common Issues and Diagnostics

#### 1. Migration Not Triggering
**Symptoms**: RAM usage stays high, no disk files created

**Diagnosis**:
```c
void diagnose_migration_issues(void)
{
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    
    printf("Migration Diagnostics:\n");
    printf("  RAM Usage: %.1f%% (%u/%u sectors)\n", 
           stats->usage_percentage, stats->used_sectors, stats->total_sectors);
    printf("  Threshold: %d%%\n", MEMORY_TO_DISK_THRESHOLD);
    printf("  State Machine State: %d\n", tiered_state_machine.state);
    printf("  System Initialized: %s\n", tiered_system_initialized ? "Yes" : "No");
    
    // Check disk space
    if (!is_disk_usage_acceptable()) {
        printf("  ERROR: Disk usage too high for migration\n");
    }
    
    // Check timing
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    printf("  Last Process Time: %u\n", tiered_state_machine.last_process_time);
    printf("  Current Time: %u\n", current_time);
}
```

#### 2. Slow Disk Access
**Symptoms**: High latency for disk sector reads

**Optimization**:
```c
void optimize_disk_access(void)
{
    // Check file system performance
    printf("Testing disk performance...\n");
    
    struct timeval start, end;
    char test_file[] = "/usr/qk/etc/sv/FC-1/history/perf_test.dat";
    
    gettimeofday(&start, NULL);
    FILE *file = fopen(test_file, "wb");
    if (file) {
        char buffer[SRAM_SECTOR_SIZE];
        memset(buffer, 0xAA, sizeof(buffer));
        
        for (int i = 0; i < 100; i++) {
            fwrite(buffer, sizeof(buffer), 1, file);
        }
        fflush(file);
        fsync(fileno(file));
        fclose(file);
    }
    gettimeofday(&end, NULL);
    
    long write_time = (end.tv_sec - start.tv_sec) * 1000000 + 
                      (end.tv_usec - start.tv_usec);
    
    printf("Disk write performance: %ld us for 100 sectors (%.1f sectors/sec)\n",
           write_time, 100000000.0 / write_time);
    
    unlink(test_file);
}
```

#### 3. Sector Chain Corruption
**Symptoms**: Read errors, invalid next sector pointers

**Validation**:
```c
bool validate_sector_chain(extended_sector_t start_sector)
{
    extended_sector_t current = start_sector;
    uint32_t chain_length = 0;
    const uint32_t max_chain_length = 10000;
    
    printf("Validating chain starting at sector %u...\n", start_sector);
    
    while (current != 0 && chain_length < max_chain_length) {
        // Check for valid sector number
        if (current >= DISK_SECTOR_MAX) {
            printf("ERROR: Invalid sector number %u at position %u\n", 
                   current, chain_length);
            return false;
        }
        
        // Read next sector pointer
        extended_sector_result_t result = get_next_sector_extended(current);
        if (result.error != IMX_MEMORY_SUCCESS) {
            printf("ERROR: Failed to read sector %u: %d\n", current, result.error);
            return false;
        }
        
        printf("  Sector %u -> %u (%s)\n", 
               current, result.next_sector,
               IS_RAM_SECTOR(current) ? "RAM" : "DISK");
        
        current = result.next_sector;
        chain_length++;
    }
    
    if (chain_length >= max_chain_length) {
        printf("ERROR: Chain too long (possible loop)\n");
        return false;
    }
    
    printf("Chain validation successful (%u sectors)\n", chain_length);
    return true;
}
```

### Performance Monitoring

```c
void monitor_migration_performance(void)
{
    static uint32_t last_files_created = 0;
    static uint64_t last_bytes_written = 0;
    static imx_time_t last_check_time = 0;
    
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    
    if (last_check_time == 0) {
        last_check_time = current_time;
        last_files_created = tiered_state_machine.total_files_created;
        last_bytes_written = tiered_state_machine.total_bytes_written;
        return;
    }
    
    uint32_t time_elapsed = current_time - last_check_time;
    if (time_elapsed >= 10000) { // Every 10 seconds
        uint32_t files_created = tiered_state_machine.total_files_created - last_files_created;
        uint64_t bytes_written = tiered_state_machine.total_bytes_written - last_bytes_written;
        
        printf("Migration Performance (last %u ms):\n", time_elapsed);
        printf("  Files created: %u (%.1f files/sec)\n", 
               files_created, (files_created * 1000.0) / time_elapsed);
        printf("  Bytes written: %llu (%.1f KB/sec)\n", 
               bytes_written, (bytes_written / 1024.0 * 1000.0) / time_elapsed);
        
        // Update for next interval
        last_check_time = current_time;
        last_files_created = tiered_state_machine.total_files_created;
        last_bytes_written = tiered_state_machine.total_bytes_written;
    }
}
```

---

## Sector Freeing and Disk Space Recovery

### Overview

The iMatrix Tiered Storage System implements a comprehensive sector lifecycle management system that handles not only the migration from RAM to disk, but also the freeing of sectors and recovery of disk space. This section covers the complete lifecycle from sector allocation through migration to final cleanup and space recovery.

### RAM Sector Freeing

#### Basic Sector Deallocation

When data is no longer needed, RAM sectors are freed to make them available for reuse:

```c
/**
 * @brief  Free sector - Clear bit in SAT and make available for reuse
 * @param  sector - Sector number to free
 */
void free_sector(uint16_t sector)
{
    uint16_t sat_entry;
    uint32_t bit_mask;

    if (icb.ext_sram_failed == true)
        return;

    if (sector >= SAT_NO_SECTORS) {
        imx_printf("Attempting to release invalid sector: %u\r\n", sector);
        return;
    }
    
    PRINTF("Freeing Sector: %u\r\n", sector);
    sat_entry = (sector & 0xFFE0) >> 5;
    bit_mask = 1 << (sector & 0x1F);
    icb.sat.block[sat_entry] &= ~bit_mask;  // Clear allocation bit
}
```

#### Secure Sector Freeing

The enhanced secure version provides comprehensive validation:

```c
/**
 * @brief  Secure version of free_sector with comprehensive validation
 * @param  sector - sector number to free
 * @retval IMX_MEMORY_SUCCESS on success, error code on failure
 */
imx_memory_error_t free_sector_safe(uint16_t sector)
{
    if (icb.ext_sram_failed == true) {
        imx_printf("ERROR: free_sector_safe - external SRAM failed\r\n");
        return IMX_MEMORY_ERROR_EXT_SRAM_NOT_SUPPORTED;
    }

    if (sector >= SAT_NO_SECTORS) {
        imx_printf("ERROR: free_sector_safe - invalid sector %u >= %u\r\n", 
                   sector, SAT_NO_SECTORS);
        return IMX_MEMORY_ERROR_INVALID_SECTOR;
    }
    
    // Calculate SAT entry with proper bounds checking
    uint16_t sat_entry = (sector & 0xFFE0) >> 5;
    if (sat_entry >= SAT_NO_ENTRIES) {
        imx_printf("ERROR: free_sector_safe - invalid SAT entry %u >= %u\r\n", 
                   sat_entry, SAT_NO_ENTRIES);
        return IMX_MEMORY_ERROR_OUT_OF_BOUNDS;
    }
    
    uint32_t bit_mask = 1 << (sector & 0x1F);
    
    // Verify sector is actually allocated before freeing
    if ((icb.sat.block[sat_entry] & bit_mask) == 0) {
        imx_printf("WARNING: free_sector_safe - sector %u was already free\r\n", sector);
        return IMX_MEMORY_SUCCESS; // Not an error, just already free
    }
    
    // Clear the allocation bit
    icb.sat.block[sat_entry] &= ~bit_mask;
    
    PRINTF("Freed sector %u successfully\r\n", sector);
    return IMX_MEMORY_SUCCESS;
}
```

#### Multi-Sector Chain Freeing

When sensor data spans multiple sectors, the system frees entire chains:

```c
// Example from erase_tsd_evt() showing chain freeing
if (csd[entry].ds.start_sector != csd[entry].ds.end_sector) {
    // Multi-sector storage - may need to free sectors
    if (csb[entry].sample_rate == 0) {
        if ((csd[entry].ds.start_index / EVT_RECORD_SIZE) >= NO_EVT_ENTRIES_PER_SECTOR)
            release_sector = true;
    } else {
        if ((csd[entry].ds.start_index / TSD_RECORD_SIZE) >= NO_TSD_ENTRIES_PER_SECTOR)
            release_sector = true;
    }
    
    if (release_sector == true) {
        // Free the start sector and move to next sector in chain
        new_start_sector = ((evt_tsd_sector_t *)&rs[csd[entry].ds.start_sector * SRAM_SECTOR_SIZE])->next_sector;
        free_sector(csd[entry].ds.start_sector);
        csd[entry].ds.start_sector = new_start_sector;
        csd[entry].ds.start_index = 0;
    }
}
```

### Disk Sector and File Management

#### Disk File Tracking Structure

Each disk file is tracked with metadata including free sector counts:

```c
typedef struct {
    char filename[MAX_FILENAME_LENGTH];
    uint16_t sensor_id;
    uint16_t sector_count;          // Total sectors in file
    uint16_t free_count;            // Number of freed sectors
    imx_utc_time_t created;
    bool marked_for_deletion;       // Flag for cleanup
} disk_file_info_t;
```

#### Marking Files for Deletion

When all sectors in a disk file are freed, the file is marked for deletion:

```c
/**
 * @brief Mark disk file for deletion when all sectors are freed
 * @param filename Full path to disk file
 */
static void mark_file_for_deletion(const char *filename)
{
    for (uint32_t i = 0; i < current_disk_file_count; i++) {
        if (strcmp(disk_files[i].filename, filename) == 0) {
            // Check if all sectors in this file are freed
            if (disk_files[i].free_count >= disk_files[i].sector_count) {
                disk_files[i].marked_for_deletion = true;
                imx_cli_log_printf("INFO: Marked file %s for deletion (all sectors freed)\n", filename);
                return;
            }
        }
    }
}
```

#### Extended Sector Freeing

For disk-based sectors, freeing involves updating lookup tables and file tracking:

```c
/**
 * @brief Free extended sector (RAM or disk)
 * @param sector Extended sector number
 * @retval IMX_MEMORY_SUCCESS on success, error code on failure
 */
imx_memory_error_t free_sector_extended(extended_sector_t sector)
{
    if (IS_RAM_SECTOR(sector)) {
        // Use standard RAM freeing
        return free_sector_safe((uint16_t)sector);
    } else if (IS_DISK_SECTOR(sector)) {
        // Update sector lookup table
        if (sector_lookup_table == NULL || sector >= (SAT_NO_SECTORS + 1000000)) {
            return IMX_MEMORY_ERROR_INVALID_SECTOR;
        }
        
        sector_lookup_entry_t *lookup = &sector_lookup_table[sector];
        if (lookup->location != SECTOR_LOCATION_DISK) {
            return IMX_MEMORY_ERROR_INVALID_SECTOR;
        }
        
        // Mark sector as freed
        lookup->location = SECTOR_LOCATION_FREED;
        
        // Update file tracking
        for (uint32_t i = 0; i < current_disk_file_count; i++) {
            if (strcmp(disk_files[i].filename, lookup->filename) == 0) {
                disk_files[i].free_count++;
                
                // Mark file for deletion if all sectors are freed
                if (disk_files[i].free_count >= disk_files[i].sector_count) {
                    disk_files[i].marked_for_deletion = true;
                    imx_cli_log_printf("INFO: All sectors freed, marking file %s for deletion\n", 
                                     disk_files[i].filename);
                }
                break;
            }
        }
        
        return IMX_MEMORY_SUCCESS;
    } else {
        return IMX_MEMORY_ERROR_INVALID_SECTOR;
    }
}
```

### Disk Cleanup State Machine

#### MEMORY_STATE_CLEANUP_DISK Operation

The cleanup state systematically removes files marked for deletion:

```c
/**
 * @brief Handle cleanup disk state - remove empty files and update tracking
 */
static void handle_cleanup_disk_state(void)
{
    bool cleanup_done = true;
    
    // Check for files marked for deletion
    for (uint32_t i = 0; i < current_disk_file_count; i++) {
        if (disk_files[i].marked_for_deletion) {
            if (delete_disk_file(disk_files[i].filename)) {
                // Remove from tracking array by shifting remaining entries
                memmove(&disk_files[i], &disk_files[i + 1], 
                       (current_disk_file_count - i - 1) * sizeof(disk_file_info_t));
                current_disk_file_count--;
                tiered_state_machine.total_files_deleted++;
                i--; // Adjust index after removal
                cleanup_done = false; // More work might be needed
            }
        }
    }
    
    if (cleanup_done) {
        tiered_state_machine.state = MEMORY_STATE_IDLE;
    }
}
```

#### File Deletion Implementation

```c
/**
 * @brief Delete disk file and recover disk space
 * @param filename Full path to file to delete
 * @retval true if file was deleted successfully
 */
static bool delete_disk_file(const char *filename)
{
    if (unlink(filename) == 0) {
        imx_cli_log_printf("INFO: Deleted disk file %s\n", filename);
        return true;
    } else if (errno == ENOENT) {
        // File doesn't exist, that's okay
        return true;
    } else {
        imx_cli_log_printf("ERROR: Failed to delete file %s: %s\n", filename, strerror(errno));
        return false;
    }
}
```

### Cleanup Triggers and Timing

#### Automatic Cleanup Triggers

The cleanup state is triggered automatically when files are available for deletion:

```c
static void handle_idle_state(void)
{
    // Check if shutdown was requested
    if (tiered_state_machine.shutdown_requested) {
        tiered_state_machine.state = MEMORY_STATE_FLUSH_ALL;
        return;
    }
    
    // Check RAM usage
    uint32_t ram_usage = get_current_ram_usage_percentage();
    if (ram_usage >= MEMORY_TO_DISK_THRESHOLD) {
        tiered_state_machine.state = MEMORY_STATE_CHECK_USAGE;
        return;
    }
    
    // Check if cleanup is needed
    if (current_disk_file_count > 0) {
        // Check if any files are marked for deletion
        for (uint32_t i = 0; i < current_disk_file_count; i++) {
            if (disk_files[i].marked_for_deletion) {
                tiered_state_machine.state = MEMORY_STATE_CLEANUP_DISK;
                return;
            }
        }
    }
}
```

#### Cleanup Flow Chart

```
┌─────────────────┐
│   IDLE STATE    │
│ Monitor RAM     │
│ Check Cleanup   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Files marked    │
│ for deletion?   │
└─────────┬───────┘
          │ Yes
          ▼
┌─────────────────┐
│ CLEANUP_DISK    │
│ State           │
│                 │
│ For each marked │
│ file:           │
│ • delete_disk_  │
│   file()        │
│ • Remove from   │
│   tracking      │
│ • Update stats  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ All files       │
│ cleaned up?     │
└─────────┬───────┘
          │ Yes
          ▼
┌─────────────────┐
│ Return to       │
│ IDLE STATE      │
└─────────────────┘
```

### Error Handling and Recovery

#### Corrupted File Handling

When files cannot be properly processed, they are moved to a corrupted directory:

```c
/**
 * @brief Move file to corrupted data directory
 * @param filename Original filename
 */
static void move_corrupted_file(const char *filename)
{
    char corrupted_filename[MAX_FILENAME_LENGTH];
    char *basename_start;
    
    // Extract basename from full path
    basename_start = strrchr(filename, '/');
    if (basename_start == NULL) {
        basename_start = (char*)filename;
    } else {
        basename_start++; // Skip the '/'
    }
    
    // Create corrupted file path
    snprintf(corrupted_filename, sizeof(corrupted_filename), 
             "%s%s", CORRUPTED_DATA_PATH, basename_start);
    
    if (rename(filename, corrupted_filename) == 0) {
        imx_cli_log_printf("INFO: Moved corrupted file %s to %s\n", filename, corrupted_filename);
    } else {
        imx_cli_log_printf("ERROR: Failed to move corrupted file %s: %s\n", 
                          filename, strerror(errno));
        // If move fails, try to delete the corrupted file
        delete_disk_file(filename);
    }
}
```

#### Failed Deletion Handling

When file deletion fails, the system logs the error but continues operation:

- Files remain marked for deletion
- Cleanup state will retry on next cycle  
- System continues to function with reduced disk space
- Manual intervention may be required for persistent failures

### Disk Space Recovery Metrics

#### Tracking Cleanup Statistics

The state machine tracks cleanup operations for monitoring:

```c
typedef struct {
    memory_process_state_t state;
    // ... other fields ...
    
    // Statistics
    uint32_t total_files_created;
    uint32_t total_files_deleted;    // Tracks successful deletions
    uint64_t total_bytes_written;
    uint32_t power_failure_recoveries;
} memory_state_machine_t;
```

#### Monitoring Disk Space Recovery

```c
/**
 * @brief Check disk space recovery effectiveness
 */
void monitor_disk_cleanup_effectiveness(void)
{
    printf("Disk Cleanup Statistics:\n");
    printf("  Files created: %u\n", tiered_state_machine.total_files_created);
    printf("  Files deleted: %u\n", tiered_state_machine.total_files_deleted);
    printf("  Current files: %u\n", current_disk_file_count);
    
    // Check for files marked but not deleted
    uint32_t pending_deletions = 0;
    for (uint32_t i = 0; i < current_disk_file_count; i++) {
        if (disk_files[i].marked_for_deletion) {
            pending_deletions++;
        }
    }
    
    if (pending_deletions > 0) {
        printf("  WARNING: %u files pending deletion\n", pending_deletions);
    }
    
    float cleanup_efficiency = 0.0f;
    if (tiered_state_machine.total_files_created > 0) {
        cleanup_efficiency = ((float)tiered_state_machine.total_files_deleted / 
                             (float)tiered_state_machine.total_files_created) * 100.0f;
    }
    printf("  Cleanup efficiency: %.1f%%\n", cleanup_efficiency);
}
```

### Performance Considerations

#### Cleanup Performance Impact

- **CPU Overhead**: File deletion operations are I/O bound
- **Timing**: Cleanup runs in background during idle state
- **Batch Processing**: Multiple files can be deleted per cleanup cycle
- **Priority**: Cleanup has lower priority than migration operations

#### Optimization Strategies

1. **Delayed Cleanup**: Don't immediately delete files when sectors are freed
2. **Batch Deletion**: Process multiple marked files in single cleanup cycle
3. **Background Operation**: Only perform cleanup when system is idle
4. **Error Recovery**: Continue operation even if some deletions fail

### Integration with Memory Statistics

The sector freeing and cleanup operations integrate with the memory statistics system:

```c
void imx_update_memory_statistics(void)
{
    // ... existing RAM statistics ...
    
    // Update deallocation count when sectors are freed
    if (current_operation == OPERATION_FREE_SECTOR) {
        memory_stats.deallocation_count++;
        
        // Recalculate fragmentation after freeing
        memory_stats.fragmentation_level = imx_calculate_fragmentation_level();
    }
}
```

### Summary

The sector freeing and disk space recovery system provides:

1. **Complete Lifecycle Management**: From allocation through migration to final cleanup
2. **Automatic Space Recovery**: Files automatically deleted when all sectors freed
3. **Background Processing**: Cleanup occurs during idle periods without impacting performance
4. **Error Resilience**: System continues to operate even with failed cleanup operations
5. **Monitoring and Statistics**: Comprehensive tracking of cleanup effectiveness
6. **Data Protection**: Corrupted files moved to safe location rather than lost

This comprehensive approach ensures that the tiered storage system not only efficiently migrates data from RAM to disk but also recovers disk space when data is no longer needed, maintaining optimal resource utilization throughout the system's operation.

## Conclusion

The iMatrix Tiered Storage System provides a sophisticated yet transparent mechanism for managing the complete lifecycle of data storage, from initial allocation through migration to final cleanup and space recovery. Key takeaways:

1. **Automatic Decision Making**: The 80% RAM threshold trigger ensures optimal resource utilization
2. **Transparent Access**: Applications use the same APIs regardless of data location
3. **Performance Optimization**: Batched processing and background operation minimize impact
4. **Data Integrity**: Atomic operations and recovery mechanisms ensure no data loss
5. **Scalability**: Extended addressing supports billions of sectors across storage tiers
6. **Complete Lifecycle Management**: From allocation through migration to cleanup and space recovery
7. **Automatic Cleanup**: Files automatically deleted when all sectors freed, recovering disk space
8. **Error Resilience**: System continues operation even with failed cleanup operations

The system seamlessly handles the complexity of cross-storage operations while maintaining high performance for RAM-based access and acceptable performance for disk-based access. The state machine approach ensures predictable behavior and enables fine-tuning for specific deployment requirements. The comprehensive sector lifecycle management ensures optimal resource utilization throughout the entire data storage lifecycle.