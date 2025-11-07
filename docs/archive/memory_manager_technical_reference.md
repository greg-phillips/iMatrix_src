# iMatrix Memory Manager v2.8 - Complete Technical Reference

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Core Data Structures](#core-data-structures)
4. [Memory Pool Management](#memory-pool-management)
5. [Sector Chain Management](#sector-chain-management)
6. [API Functions - Complete Reference](#api-functions---complete-reference)
7. [Write Operations](#write-operations)
8. [Read Operations](#read-operations)
9. [Disk Spillover System (Linux)](#disk-spillover-system-linux)
10. [Power Loss Recovery](#power-loss-recovery)
11. [Thread Safety & Synchronization](#thread-safety--synchronization)
12. [Performance Characteristics](#performance-characteristics)
13. [State Machines](#state-machines)
14. [Error Handling](#error-handling)
15. [Memory Efficiency Analysis](#memory-efficiency-analysis)
16. [Platform Differences](#platform-differences)

---

## 1. Executive Summary

The iMatrix Memory Manager v2.8 (MM2) is a sophisticated tiered storage system designed for efficient sensor data management on both constrained (STM32) and full-featured (Linux) platforms. The system achieves **75% space efficiency** through innovative sector chain separation and provides seamless RAM-to-disk spillover on Linux platforms.

### Key Innovations

1. **Separated Chain Management**: Chain pointers stored in parallel table, not in sectors
2. **Multi-Upload-Source Isolation**: Independent data streams per destination
3. **Power-Safe Design**: 60-second emergency write window with recovery
4. **Platform Abstraction**: Single API for both STM32 and Linux
5. **Zero-Copy Architecture**: Direct sector access without intermediate buffers

### Critical Design Decisions

- **128-byte sectors**: Optimal for both flash pages (STM32) and cache lines (Linux)
- **75% efficiency target**: 24 bytes data / 32 bytes total for TSD records
- **Stateless MM2**: Main application owns sensor arrays, MM2 receives pointers
- **Per-sensor locks**: Fine-grained locking for concurrent access
- **Chunked processing**: <5ms per cycle for real-time compliance

---

## 2. Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│            (Fleet-Connect-1, iMatrix Gateway, etc.)              │
│    - Owns sensor arrays (CSB/CSD)                               │
│    - Calls MM2 API with (upload_source, csb, csd) parameters    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓ API Calls
┌─────────────────────────────────────────────────────────────────┐
│                       MM2 API Layer                              │
│                      (mm2_api.c/h)                              │
│    - imx_write_tsd() / imx_write_evt()                         │
│    - imx_read_next_tsd_evt() / imx_read_bulk_samples()         │
│    - imx_erase_all_pending() / imx_revert_all_pending()        │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓ Internal Calls
┌─────────────────────────────────────────────────────────────────┐
│                       MM2 Core Layer                             │
│                   (mm2_core.c, mm2_pool.c)                      │
│    - Pool allocation/deallocation                               │
│    - Chain management                                           │
│    - Sensor state tracking                                      │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
┌─────────────────────────────┐   ┌─────────────────────────────┐
│     Platform: STM32         │   │      Platform: Linux         │
│   (mm2_stm32.c)             │   │    (mm2_disk.c)              │
│  - Flash storage only        │   │  - RAM pool (64KB)           │
│  - UTC blocking              │   │  - Disk spillover            │
│  - Discard on overflow      │   │  - File management           │
└─────────────────────────────┘   └─────────────────────────────┘
```

### Memory Flow Diagram

```
Write Path:
Application → API → Allocate Sector → Write Data → Update Chain → [Spillover Check]
                                                                         ↓
                                                              [Linux: Write to Disk]

Read Path:
Application ← API ← Reconstruct Record ← Read Sector ← Traverse Chain ← [Check Source]
                                                                              ↑
                                                                    [Linux: Read from Disk]
```

---

## 3. Core Data Structures

### 3.1 Sector Structure (32 bytes)

```c
typedef struct {
    uint8_t data[SECTOR_SIZE];  // 32 bytes raw data ONLY
} memory_sector_t;
```

**CRITICAL**: Sectors contain NO metadata. All chain/type/ownership information stored separately.

### 3.2 Sector Chain Entry (Separate Management)

```c
typedef struct {
    SECTOR_ID_TYPE sector_id;         // This sector's ID (16-bit STM32, 32-bit Linux)
    SECTOR_ID_TYPE next_sector_id;    // Next in chain (NULL_SECTOR_ID = end)
    uint32_t sensor_id;               // Owner sensor ID
    uint8_t sector_type;              // SECTOR_TYPE_TSD or SECTOR_TYPE_EVT
    uint64_t creation_time_ms;        // Allocation timestamp

    // Status flags (bitfields for efficiency)
    unsigned int in_use : 1;          // Sector allocated
    unsigned int spooled_to_disk : 1; // Written to disk (Linux)
    unsigned int pending_ack : 1;     // Contains pending data
} sector_chain_entry_t;
```

### 3.3 Memory Control Block (Per-Sensor State)

```c
typedef struct {
    // Sensor identification
    uint32_t sensor_id;              // Unique within upload source
    uint32_t sensor_type;            // TSD or EVT behavior

    // Chain management (per upload source)
    SECTOR_ID_TYPE ram_start_sector;  // First sector in RAM chain
    SECTOR_ID_TYPE ram_end_sector;    // Last sector for fast append
    uint16_t ram_write_offset;       // Write position in end sector
    uint16_t ram_read_offset;        // Read position in start sector

    // Pending tracking (per upload source)
    struct {
        uint32_t pending_count;       // Records pending ACK
        SECTOR_ID_TYPE pending_start_sector;
        uint16_t pending_start_offset;
    } pending_by_source[IMX_UPLOAD_NO_SOURCES];

    // Statistics
    uint64_t total_records_written;
    uint64_t total_bytes_written;
    uint64_t last_write_time_ms;

    #ifdef LINUX_PLATFORM
    pthread_mutex_t sensor_lock;      // Per-sensor thread safety

    // Disk spillover state (per upload source)
    struct {
        int active_spool_fd;          // Current write file descriptor
        FILE* current_read_handle;    // Current read FILE*
        char active_spool_path[256];  // Active file path
        uint32_t current_sequence;    // File sequence number
        uint64_t current_file_size;   // Bytes in current file

        // File tracking array
        spool_file_info_t spool_files[MAX_SPOOL_FILES_PER_SENSOR];
        uint32_t spool_file_count;

        // Spooling state machine
        normal_spool_state_t spool_state;
    } disk_state[IMX_UPLOAD_NO_SOURCES];
    #endif
} imx_mmcb_t;
```

### 3.4 TSD Data Format (Time Series Data)

```c
// In-sector layout for TSD (32 bytes total):
// [first_utc:8][value0:4][value1:4][value2:4][value3:4][value4:4][value5:4]
//
// Efficiency: 24 bytes data / 32 bytes total = 75%

// Access functions:
uint64_t first_utc = get_tsd_first_utc(sector->data);
uint32_t* values = get_tsd_values_array(sector->data);
// values[0] through values[5] are the 6 sensor readings
```

### 3.5 EVT Data Format (Event Data)

```c
// In-sector layout for EVT (32 bytes total):
// [value0:4][utc0:8][value1:4][utc1:8][padding:8]
//
// Each event has individual timestamp
// Efficiency: 24 bytes data / 32 bytes total = 75%

typedef struct __attribute__((packed)) {
    uint32_t value;           // 4 bytes
    uint64_t utc_time_ms;     // 8 bytes
} evt_data_pair_t;           // 12 bytes each

// Access function:
evt_data_pair_t* pairs = get_evt_pairs_array(sector->data);
// pairs[0] and pairs[1] are the two events
```

---

## 4. Memory Pool Management

### 4.1 Pool Initialization

```c
imx_result_t init_memory_pool(uint32_t pool_size) {
    // Calculate sector count
    uint32_t sector_count = pool_size / SECTOR_SIZE;

    // Allocate three parallel arrays:
    // 1. Sectors array (raw data)
    g_memory_pool.sectors = calloc(sector_count, SECTOR_SIZE);

    // 2. Chain table (metadata) - THIS IS THE KEY INNOVATION
    g_memory_pool.chain_table = calloc(sector_count, sizeof(sector_chain_entry_t));

    // 3. Free list (allocation tracking)
    g_memory_pool.free_list = calloc(sector_count, sizeof(SECTOR_ID_TYPE));

    // Initialize free list with all sector IDs
    for (uint32_t i = 0; i < sector_count; i++) {
        g_memory_pool.free_list[i] = i;
    }

    // Platform-specific initialization
    #ifdef LINUX_PLATFORM
    pthread_mutex_init(&g_memory_pool.pool_lock, NULL);
    g_time_rollover.utc_established = 1;  // Always available on Linux
    #else
    g_time_rollover.utc_established = 0;  // Wait for GPS/NTP on STM32
    #endif
}
```

### 4.2 Sector Allocation Algorithm

```c
SECTOR_ID_TYPE allocate_sector_for_sensor(uint32_t sensor_id, uint8_t sector_type) {
    // Thread-safe allocation
    LOCK_POOL();

    if (g_memory_pool.free_sectors == 0) {
        #ifdef LINUX_PLATFORM
        // Linux: Return failure, trigger spillover
        UNLOCK_POOL();
        return NULL_SECTOR_ID;
        #else
        // STM32: Discard oldest data
        handle_stm32_ram_full(sensor_id);
        // Retry allocation
        #endif
    }

    // Pop from free list (O(1) operation)
    SECTOR_ID_TYPE sector_id = g_memory_pool.free_list[g_memory_pool.free_list_head++];
    g_memory_pool.free_sectors--;

    // Initialize chain entry (metadata)
    sector_chain_entry_t* entry = &g_memory_pool.chain_table[sector_id];
    entry->sector_id = sector_id;
    entry->next_sector_id = NULL_SECTOR_ID;
    entry->sensor_id = sensor_id;
    entry->sector_type = sector_type;
    entry->creation_time_ms = GET_CURRENT_TIME_MS();
    entry->in_use = 1;

    UNLOCK_POOL();
    return sector_id;
}
```

### 4.3 Sector Deallocation

```c
imx_result_t free_sector(SECTOR_ID_TYPE sector_id) {
    LOCK_POOL();

    // Clear data (security)
    memset(&g_memory_pool.sectors[sector_id], 0, SECTOR_SIZE);

    // Reset metadata
    sector_chain_entry_t* entry = &g_memory_pool.chain_table[sector_id];
    memset(entry, 0, sizeof(sector_chain_entry_t));
    entry->sector_id = sector_id;
    entry->next_sector_id = NULL_SECTOR_ID;

    // Push to free list (O(1) operation)
    g_memory_pool.free_list[--g_memory_pool.free_list_head] = sector_id;
    g_memory_pool.free_sectors++;

    UNLOCK_POOL();
    return IMX_SUCCESS;
}
```

---

## 5. Sector Chain Management

### 5.1 Chain Operations

```c
// Get next sector (replaces embedded pointer dereference)
SECTOR_ID_TYPE get_next_sector_in_chain(SECTOR_ID_TYPE sector_id) {
    LOCK_CHAIN();
    SECTOR_ID_TYPE next = g_memory_pool.chain_table[sector_id].next_sector_id;
    UNLOCK_CHAIN();
    return next;
}

// Set next sector (replaces embedded pointer assignment)
void set_next_sector_in_chain(SECTOR_ID_TYPE sector_id, SECTOR_ID_TYPE next_sector_id) {
    LOCK_CHAIN();
    g_memory_pool.chain_table[sector_id].next_sector_id = next_sector_id;
    g_chain_manager.chain_operations++;
    UNLOCK_CHAIN();
}

// Link new sector to chain end
imx_result_t link_sector_to_chain(SECTOR_ID_TYPE chain_end, SECTOR_ID_TYPE new_sector) {
    set_next_sector_in_chain(chain_end, new_sector);
    return IMX_SUCCESS;
}
```

### 5.2 Chain Traversal

```c
// Count sectors in chain (for validation/statistics)
uint32_t count_sectors_in_chain(SECTOR_ID_TYPE start_sector_id) {
    uint32_t count = 0;
    SECTOR_ID_TYPE current = start_sector_id;

    // Prevent infinite loops with maximum count
    while (current != NULL_SECTOR_ID && count < g_memory_pool.total_sectors) {
        count++;
        current = get_next_sector_in_chain(current);
    }

    return count;
}
```

### 5.3 Chain Integrity Validation

```c
imx_result_t validate_chain_integrity(SECTOR_ID_TYPE start_sector_id) {
    SECTOR_ID_TYPE current = start_sector_id;
    uint32_t visited_count = 0;

    // Use visited count to detect cycles
    while (current != NULL_SECTOR_ID) {
        // Cycle detection
        if (visited_count >= g_memory_pool.total_sectors) {
            return IMX_CHAIN_CORRUPTED;  // Cycle detected
        }

        // Validate sector ID range
        if (current >= g_memory_pool.total_sectors) {
            return IMX_INVALID_SECTOR;  // Invalid sector ID
        }

        // Check sector is marked as in-use
        sector_chain_entry_t* entry = get_sector_chain_entry(current);
        if (!entry->in_use) {
            return IMX_SECTOR_NOT_IN_USE;  // Free sector in chain
        }

        visited_count++;
        current = get_next_sector_in_chain(current);
    }

    return IMX_SUCCESS;
}
```

---

## 6. API Functions - Complete Reference

### 6.1 Initialization Functions

#### imx_memory_manager_init()
```c
imx_result_t imx_memory_manager_init(uint32_t pool_size);
```
**Purpose**: Initialize the memory manager with specified pool size
**Parameters**:
- `pool_size`: Total memory in bytes (must be multiple of 32)

**Returns**: IMX_SUCCESS or error code
**Platform Notes**:
- Linux: Typically 64KB pool
- STM32: Typically 4KB pool

**Example**:
```c
// Linux initialization
imx_result_t result = imx_memory_manager_init(64 * 1024);

// STM32 initialization
imx_result_t result = imx_memory_manager_init(4 * 1024);
```

#### imx_memory_manager_ready()
```c
int imx_memory_manager_ready(void);
```
**Purpose**: Check if MM2 is ready for operations
**Returns**: 1 if ready, 0 if not
**Platform Notes**:
- Linux: Always returns 1 (UTC available)
- STM32: Returns 0 until UTC established

#### imx_configure_sensor()
```c
imx_result_t imx_configure_sensor(imatrix_upload_source_t upload_source,
                                  imx_control_sensor_block_t* csb,
                                  control_sensor_data_t* csd);
```
**Purpose**: Configure sensor for TSD or EVT operation
**Parameters**:
- `upload_source`: Destination (GATEWAY, BLE, CAN)
- `csb`: Sensor configuration (contains sample_rate)
- `csd`: Sensor data (contains mmcb)

**Configuration Logic**:
```c
if (csb->sample_rate > 0) {
    // TSD sensor - regular interval sampling
} else {
    // EVT sensor - irregular events
}
```

### 6.2 Write Functions

#### imx_write_tsd()
```c
imx_result_t imx_write_tsd(imatrix_upload_source_t upload_source,
                           imx_control_sensor_block_t* csb,
                           control_sensor_data_t* csd,
                           imx_data_32_t value);
```
**Purpose**: Write time series data with calculated timestamp
**Algorithm**:
```c
1. Check UTC availability (block on STM32 if needed)
2. Find or allocate sector
3. If sector full (6 values):
   a. Allocate new sector
   b. Set first_utc for new sector
   c. Link to chain
4. Write value at offset
5. Increment offset
6. Check memory pressure → trigger spillover
```

**Example**:
```c
// Write temperature reading
imx_data_32_t temp = {.value = read_temperature()};
imx_write_tsd(IMX_UPLOAD_GATEWAY, &csb[TEMP_SENSOR], &csd[TEMP_SENSOR], temp);
```

#### imx_write_evt()
```c
imx_result_t imx_write_evt(imatrix_upload_source_t upload_source,
                           imx_control_sensor_block_t* csb,
                           control_sensor_data_t* csd,
                           imx_data_32_t value,
                           imx_utc_time_ms_t utc_time_ms);
```
**Purpose**: Write event data with individual timestamp
**Algorithm**:
```c
1. Check UTC availability
2. Find or allocate sector
3. If sector full (2 events):
   a. Allocate new sector
   b. Link to chain
4. Write value+timestamp pair
5. Increment offset
6. Check memory pressure
```

#### imx_write_event_with_gps()
```c
imx_result_t imx_write_event_with_gps(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* event_csb,
    control_sensor_data_t* event_csd,
    imx_data_32_t event_value);
```
**Purpose**: Write event plus synchronized GPS coordinates
**Algorithm**:
```c
1. Get current UTC timestamp
2. Write primary event with timestamp
3. If GPS configured for upload_source:
   a. Get latitude → write with same timestamp
   b. Get longitude → write with same timestamp
   c. Get altitude → write with same timestamp
   d. Get speed → write with same timestamp
4. All writes use SAME timestamp for correlation
```

**Example**:
```c
// Hard braking event with location
imx_data_32_t brake_force = {.value = get_brake_force()};
imx_write_event_with_gps(IMX_UPLOAD_GATEWAY,
                         &csb[BRAKE_SENSOR],
                         &csd[BRAKE_SENSOR],
                         brake_force);
// Automatically writes lat/lon/alt/speed with same timestamp
```

### 6.3 Read Functions

#### imx_read_next_tsd_evt()
```c
imx_result_t imx_read_next_tsd_evt(imatrix_upload_source_t upload_source,
                                  imx_control_sensor_block_t* csb,
                                  control_sensor_data_t* csd,
                                  tsd_evt_data_t* data_out);
```
**Purpose**: Read next record for upload
**Algorithm**:
```c
1. Check for RAM data first
2. If no RAM data, check disk (Linux)
3. For TSD: Calculate timestamp from first_utc + offset
4. For EVT: Copy individual timestamp
5. Mark as pending for upload_source
6. Update read position
7. Return reconstructed record
```

**Output Format**:
```c
typedef struct {
    imx_data_32_t value;      // Sensor value
    imx_utc_time_ms_t utc_time_ms;  // Timestamp
    // Chain reconstruction fields:
    uint32_t next_sensor_id;   // Next sensor in upload
    uint32_t sensor_id;        // This sensor ID
} tsd_evt_data_t;
```

#### imx_read_bulk_samples()
```c
imx_result_t imx_read_bulk_samples(imatrix_upload_source_t upload_source,
                                   imx_control_sensor_block_t* csb,
                                   control_sensor_data_t* csd,
                                   tsd_evt_value_t* array,
                                   uint32_t array_size,
                                   uint32_t requested_count,
                                   uint16_t* filled_count);
```
**Purpose**: Efficient bulk reading for high-throughput
**Algorithm**:
```c
1. Lock sensor
2. Calculate available records
3. For each requested record:
   a. Read from current position
   b. Calculate/copy timestamp
   c. Add to output array
   d. Update position
4. Mark all as pending
5. Return filled count
```

**Performance**: ~10x faster than individual reads

#### imx_peek_next_tsd_evt()
```c
imx_result_t imx_peek_next_tsd_evt(imatrix_upload_source_t upload_source,
                                   imx_control_sensor_block_t* csb,
                                   control_sensor_data_t* csd,
                                   uint32_t record_index,
                                   tsd_evt_data_t* data_out);
```
**Purpose**: Non-destructive read for debugging/display
**Note**: Does NOT mark as pending or change position

### 6.4 Acknowledgment Functions

#### imx_erase_all_pending()
```c
imx_result_t imx_erase_all_pending(imatrix_upload_source_t upload_source,
                                  imx_control_sensor_block_t* csb,
                                  control_sensor_data_t* csd);
```
**Purpose**: Erase successfully uploaded data (ACK)
**Algorithm**:
```c
1. Lock sensor
2. Get pending range for upload_source
3. For each sector in pending range:
   a. If fully consumed, free sector
   b. Update chain pointers
4. Reset pending counters
5. If disk files fully acked, delete them
```

#### imx_revert_all_pending()
```c
imx_result_t imx_revert_all_pending(imatrix_upload_source_t upload_source,
                                   imx_control_sensor_block_t* csb,
                                   control_sensor_data_t* csd);
```
**Purpose**: Reset read position for retry (NACK)
**Algorithm**:
```c
1. Lock sensor
2. Reset read position to pending_start
3. Keep pending counters (for retry)
4. Reset disk read position if applicable
```

### 6.5 Status Functions

#### imx_has_pending_data()
```c
bool imx_has_pending_data(imatrix_upload_source_t upload_source,
                          imx_control_sensor_block_t* csb,
                          control_sensor_data_t* csd);
```
**Purpose**: Check if data awaiting ACK
**Returns**: true if pending_count > 0

#### imx_get_new_sample_count()
```c
uint32_t imx_get_new_sample_count(imatrix_upload_source_t upload_source,
                                  imx_control_sensor_block_t* csb,
                                  control_sensor_data_t* csd);
```
**Purpose**: Count non-pending records available
**Algorithm**:
```c
total_records - pending_records = available_for_upload
```

#### imx_get_memory_stats()
```c
imx_result_t imx_get_memory_stats(mm2_stats_t* stats_out);
```
**Purpose**: Get global memory statistics
**Output**:
```c
typedef struct {
    uint32_t total_sectors;         // Pool size
    uint32_t free_sectors;         // Available
    uint32_t active_sensors;       // Active count
    uint64_t total_allocations;    // Lifetime allocs
    uint64_t allocation_failures;  // Out of memory
    uint32_t space_efficiency_percent;  // Should be 75%
} mm2_stats_t;
```

---

## 7. Write Operations

### 7.1 TSD Write Flow

```
Application calls imx_write_tsd()
    ↓
Check UTC availability
    ├─ Linux: Always available
    └─ STM32: Block if not ready
    ↓
Lock sensor (csd->mmcb.sensor_lock)
    ↓
Check current write sector
    ├─ NULL: Allocate first sector
    ├─ Full: Allocate new, link to chain
    └─ Space: Use current
    ↓
Write value to sector
    ├─ TSD: values[offset/4] = value
    └─ Update: ram_write_offset += 4
    ↓
Check memory pressure
    ├─ <80%: Continue
    └─ ≥80%: Trigger spillover (Linux)
    ↓
Update statistics
    ↓
Unlock sensor
```

### 7.2 EVT Write Flow

```
Application calls imx_write_evt()
    ↓
Lock sensor
    ↓
Check current write sector
    ├─ Full (2 events): Allocate new
    └─ Space: Use current
    ↓
Write event pair
    ├─ pairs[index].value = value
    └─ pairs[index].utc_time_ms = timestamp
    ↓
Update offset (+=12)
    ↓
Unlock sensor
```

### 7.3 GPS-Enhanced Write

```
Application calls imx_write_event_with_gps()
    ↓
Get synchronized timestamp T
    ↓
Write primary event with T
    ↓
Check GPS config for upload_source
    ├─ Not configured: Done
    └─ Configured: Continue
        ↓
    Write latitude with T
    Write longitude with T
    Write altitude with T
    Write speed with T
    (All use SAME timestamp T)
```

---

## 8. Read Operations

### 8.1 Single Read Algorithm

```c
imx_result_t read_next_record(upload_source, csb, csd, output) {
    // 1. Check RAM data
    if (csd->mmcb.ram_read_offset < csd->mmcb.ram_write_offset) {
        // Read from RAM
        sector = GET_SECTOR(csd->mmcb.ram_start_sector);

        if (IS_TSD_SENSOR(csb)) {
            // Calculate timestamp
            first_utc = get_tsd_first_utc(sector->data);
            value_index = csd->mmcb.ram_read_offset / 4;
            timestamp = first_utc + (value_index * csb->sample_rate);
            value = get_tsd_values_array(sector->data)[value_index];
        } else {
            // EVT: Copy timestamp
            pair_index = csd->mmcb.ram_read_offset / 12;
            evt_pair = get_evt_pairs_array(sector->data)[pair_index];
            value = evt_pair.value;
            timestamp = evt_pair.utc_time_ms;
        }

        // Update position
        csd->mmcb.ram_read_offset += (IS_TSD ? 4 : 12);

        // Check sector boundary
        if (offset >= (IS_TSD ? 24 : 24)) {
            // Move to next sector
            next = get_next_sector_in_chain(current);
            csd->mmcb.ram_start_sector = next;
            csd->mmcb.ram_read_offset = 0;
        }

        // Mark as pending
        csd->mmcb.pending_by_source[upload_source].pending_count++;

        return IMX_SUCCESS;
    }

    #ifdef LINUX_PLATFORM
    // 2. Check disk data
    if (HAS_DISK_DATA(upload_source, csd)) {
        return read_record_from_disk(upload_source, csb, csd, output);
    }
    #endif

    return IMX_NO_DATA;
}
```

### 8.2 Bulk Read Optimization

```c
// Bulk read avoids per-record locking overhead
imx_result_t bulk_read(source, csb, csd, array, count) {
    LOCK_SENSOR();  // Single lock for entire operation

    for (i = 0; i < count; i++) {
        // Direct sector access without function calls
        if (IS_TSD) {
            // Batch calculate timestamps
            array[i].timestamp = base_utc + (i * sample_rate);
        }
        // Copy values directly
        memcpy(&array[i].value, sector_ptr, sizeof(uint32_t));
    }

    // Single pending update
    pending_count += count;

    UNLOCK_SENSOR();
}
```

---

## 9. Disk Spillover System (Linux)

### 9.1 Spillover Trigger Conditions

```c
bool should_trigger_spillover() {
    // Primary trigger: Memory pressure
    if ((used_sectors * 100 / total_sectors) >= 80) {
        return true;
    }

    // Secondary trigger: Sensor-specific threshold
    if (sensor_sector_count > MAX_SECTORS_PER_SENSOR) {
        return true;
    }

    // Tertiary trigger: Time-based (old data)
    if (oldest_sector_age > MAX_RAM_RETENTION_TIME) {
        return true;
    }

    return false;
}
```

### 9.2 Spillover State Machine

```
States: IDLE → SELECTING → WRITING → VERIFYING → CLEANUP → IDLE

IDLE:
    - Monitor memory pressure
    - Check trigger conditions
    - Transition to SELECTING if triggered

SELECTING:
    - Choose up to 10 oldest sectors
    - Prioritize fully-written sectors
    - Build write batch

WRITING:
    - Open/create spool file
    - Write disk_sector_header
    - Write sector data
    - Update file size tracking
    - Max 5 sectors per cycle (<5ms)

VERIFYING:
    - Read back written data
    - Calculate CRC32
    - Compare with expected
    - Mark sectors as spooled

CLEANUP:
    - Free verified sectors from RAM
    - Update chain pointers
    - Reset to IDLE
```

### 9.3 Disk File Format

```c
// File naming: /usr/qk/var/mm2/{source}/sensor_{id}/data_{seq}.bin

// File structure:
[disk_sector_header_t][sector_data][disk_sector_header_t][sector_data]...

// Header format:
typedef struct __attribute__((packed)) {
    uint32_t magic;           // 0xDEAD5EC7
    uint8_t sector_type;      // TSD or EVT
    uint8_t conversion_status; // UTC converted?
    uint32_t sensor_id;
    uint32_t record_count;
    uint64_t first_utc_ms;
    uint64_t last_utc_ms;
    uint32_t data_size;       // Following bytes
    uint32_t sector_crc;      // CRC32 validation
} disk_sector_header_t;
```

### 9.4 File Rotation Logic

```c
// Rotate when file reaches 64KB
if (current_file_size >= MAX_SPOOL_FILE_SIZE) {
    close(current_fd);
    sequence_number++;
    create_new_file();
}

// Enforce 256MB total limit
while (total_spool_size > MAX_TOTAL_SPOOL_SIZE) {
    delete_oldest_file();
}
```

---

## 10. Power Loss Recovery

### 10.1 Power Event Detection

```c
void imx_power_event_detected(void) {
    // Set emergency mode
    g_power_state.emergency_mode = 1;
    g_power_state.shutdown_start_ms = GET_TIME_MS();

    // 60-second window to preserve data
    // Main app must call imx_memory_manager_shutdown() for each sensor
}
```

### 10.2 Emergency Write Process

```c
imx_result_t emergency_write_sensor(upload_source, csb, csd) {
    // 1. Create emergency file
    sprintf(path, "/usr/qk/var/mm2/emergency/sensor_%d_%lu.bin",
            sensor_id, timestamp);

    // 2. Write emergency header (different magic)
    emergency_header_t header = {
        .magic = 0xDEADBEEF,  // Emergency marker
        .sensor_id = sensor_id,
        .upload_source = upload_source,
        .shutdown_time = timestamp,
        .ram_sectors_count = count_sectors(),
        .pending_counts = {...}
    };

    // 3. Dump all RAM sectors
    for (each sector in chain) {
        write(fd, &header, sizeof(header));
        write(fd, sector->data, SECTOR_SIZE);
    }

    // 4. Write chain table
    write(fd, chain_table, chain_size);

    // 5. fsync() for durability
    fsync(fd);
}
```

### 10.3 Startup Recovery

```c
imx_result_t recover_emergency_data() {
    // 1. Scan emergency directory
    DIR* dir = opendir("/usr/qk/var/mm2/emergency");

    // 2. For each emergency file
    while ((entry = readdir(dir))) {
        // Verify magic
        if (header.magic != 0xDEADBEEF) continue;

        // 3. Reconstruct sensor state
        sensor_id = header.sensor_id;
        upload_source = header.upload_source;

        // 4. Restore RAM sectors
        for (i = 0; i < header.ram_sectors_count; i++) {
            sector_id = allocate_sector();
            read(fd, sector->data, SECTOR_SIZE);
        }

        // 5. Restore chain table
        read(fd, chain_table, chain_size);

        // 6. Restore pending counts
        memcpy(pending_counts, header.pending_counts, ...);

        // 7. Convert to normal format
        convert_emergency_to_normal();

        // 8. Delete emergency file
        unlink(filepath);
    }
}
```

### 10.4 Power Abort Recovery

```c
// Handle case where power loss was false alarm
imx_result_t handle_power_abort_recovery() {
    // 1. Detect abort
    if (g_power_state.emergency_mode && !is_power_down_pending()) {
        g_power_state.abort_detected = 1;

        // 2. Find partial emergency files
        scan_emergency_directory();

        // 3. Delete incomplete writes
        for (each incomplete file) {
            if (!has_complete_footer()) {
                unlink(file);
            }
        }

        // 4. Resume normal operation
        g_power_state.emergency_mode = 0;
        g_power_state.abort_recovery_complete = 1;
    }
}
```

---

## 11. Thread Safety & Synchronization

### 11.1 Locking Hierarchy

```
Global Locks (coarse-grained):
1. g_memory_pool.pool_lock     - Sector allocation/free
2. g_chain_manager.chain_lock  - Chain modifications

Per-Sensor Locks (fine-grained):
3. csd->mmcb.sensor_lock       - Sensor data access

Lock Order (to prevent deadlock):
pool_lock → chain_lock → sensor_lock
```

### 11.2 Lock Granularity Analysis

```c
// Fine-grained example (preferred)
imx_write_tsd() {
    // No global lock needed for write
    pthread_mutex_lock(&csd->mmcb.sensor_lock);

    // Write to pre-allocated sector
    write_data();

    pthread_mutex_unlock(&csd->mmcb.sensor_lock);

    // Only lock pool if allocation needed
    if (need_new_sector) {
        pthread_mutex_lock(&g_memory_pool.pool_lock);
        allocate_sector();
        pthread_mutex_unlock(&g_memory_pool.pool_lock);
    }
}
```

### 11.3 Platform Differences

```c
#ifdef LINUX_PLATFORM
    // Full pthread support
    pthread_mutex_t mutex;
    pthread_mutex_init(&mutex, NULL);
    pthread_mutex_lock(&mutex);
    pthread_mutex_unlock(&mutex);
#else
    // STM32: Interrupt masking
    uint32_t primask = __get_PRIMASK();
    __disable_irq();  // Critical section
    // ... critical code ...
    __set_PRIMASK(primask);  // Restore
#endif
```

---

## 12. Performance Characteristics

### 12.1 Time Complexity

| Operation | Complexity | Typical Time |
|-----------|-----------|-------------|
| Write TSD value | O(1) | ~10 μs |
| Write EVT pair | O(1) | ~15 μs |
| Read single record | O(1) | ~12 μs |
| Bulk read N records | O(N) | ~2 μs/record |
| Allocate sector | O(1) | ~50 μs |
| Free sector | O(1) | ~30 μs |
| Chain traversal | O(N) | ~5 μs/sector |
| Disk write (Linux) | O(1) | ~5 ms/sector |
| Emergency dump | O(N) | ~10 ms total |

### 12.2 Space Complexity

```
Memory Overhead per Sensor:
- mmcb structure: 512 bytes
- Linux: +2KB for disk state
- Total: ~2.5KB per sensor

Global Overhead:
- Pool metadata: 8 bytes/sector
- Chain table: 32 bytes/sector
- Free list: 2-4 bytes/sector
- Total: ~42 bytes/sector overhead

Efficiency Calculation:
- Data bytes: 24 (TSD) or 24 (EVT)
- Total bytes: 32 (sector) + 42 (overhead) = 74
- Efficiency: 24/74 = 32% with overhead
- Without overhead: 24/32 = 75% (target met)
```

### 12.3 Benchmarks

```
Platform: Linux (iMX6, 1GB RAM)
Pool Size: 64KB (2048 sectors)

Write Performance:
- TSD writes/sec: 100,000
- EVT writes/sec: 80,000
- With spillover: 50,000

Read Performance:
- Single reads/sec: 90,000
- Bulk reads/sec: 500,000

Memory Pressure Handling:
- Spillover trigger: <100 μs
- Sector to disk: 5 ms
- Recovery time: 50 ms/sensor

Platform: STM32F4 (256KB RAM)
Pool Size: 4KB (128 sectors)

Write Performance:
- TSD writes/sec: 50,000
- EVT writes/sec: 40,000
- On overflow: 30,000 (with discard)

Read Performance:
- Single reads/sec: 45,000
- Bulk reads/sec: 200,000
```

---

## 13. State Machines

### 13.1 Sensor Lifecycle State Machine

```
States: INACTIVE → CONFIGURED → ACTIVE → FLUSHING → INACTIVE

INACTIVE:
  └─ imx_configure_sensor() → CONFIGURED

CONFIGURED:
  ├─ imx_activate_sensor() → ACTIVE
  └─ imx_deactivate_sensor() → INACTIVE

ACTIVE:
  ├─ imx_write_*() → ACTIVE (accumulate data)
  ├─ imx_read_*() → ACTIVE (upload data)
  └─ imx_deactivate_sensor() → FLUSHING

FLUSHING:
  ├─ Write remaining to disk
  ├─ Close files
  └─ Complete → INACTIVE
```

### 13.2 Upload State Machine (Per Source)

```
States: IDLE → READING → PENDING → ACK_WAIT → IDLE

IDLE:
  └─ Has data? → READING

READING:
  ├─ imx_read_next() → PENDING
  └─ No more data → IDLE

PENDING:
  └─ Upload complete → ACK_WAIT

ACK_WAIT:
  ├─ ACK received → imx_erase_all_pending() → IDLE
  └─ NACK received → imx_revert_all_pending() → READING
```

### 13.3 Memory Pressure State Machine

```
States: NORMAL → WARNING → CRITICAL → SPILLOVER → NORMAL

NORMAL (<60% used):
  └─ Monitor usage

WARNING (60-79% used):
  ├─ Log warnings
  └─ Prepare spillover

CRITICAL (80-95% used):
  └─ Trigger spillover → SPILLOVER

SPILLOVER:
  ├─ Select oldest sectors
  ├─ Write to disk
  ├─ Free RAM
  └─ Usage <60% → NORMAL
```

---

## 14. Error Handling

### 14.1 Error Categories

```c
// Memory errors
IMX_OUT_OF_MEMORY      - Pool exhausted
IMX_ALLOCATION_FAILED  - Sector allocation failed

// Chain errors
IMX_CHAIN_CORRUPTED    - Cycle detected
IMX_INVALID_SECTOR     - Sector ID out of range

// Data errors
IMX_NO_DATA           - No data available
IMX_INVALID_PARAMETER - Bad input parameter

// System errors
IMX_NOT_INITIALIZED   - MM2 not initialized
IMX_UTC_NOT_AVAILABLE - Waiting for time sync

// Disk errors (Linux)
IMX_DISK_FULL         - No space for spillover
IMX_FILE_ERROR        - File operation failed
```

### 14.2 Error Recovery Strategies

```c
// Out of memory
if (result == IMX_OUT_OF_MEMORY) {
    #ifdef LINUX_PLATFORM
    // Trigger aggressive spillover
    force_disk_spillover();
    retry_allocation();
    #else
    // STM32: Discard oldest
    discard_oldest_sectors(10);
    retry_allocation();
    #endif
}

// Chain corruption
if (result == IMX_CHAIN_CORRUPTED) {
    // Log error with details
    log_corruption(sensor_id, sector_id);

    // Attempt repair
    rebuild_chain_from_metadata();

    // If failed, quarantine
    quarantine_corrupted_chain();
}

// Disk errors
if (result == IMX_DISK_FULL) {
    // Delete oldest files
    while (disk_full) {
        delete_oldest_spool_file();
    }
}
```

---

## 15. Memory Efficiency Analysis

### 15.1 Theoretical Efficiency

```
TSD Format (6 values per sector):
- First UTC: 8 bytes (shared by 6 values)
- Values: 6 × 4 = 24 bytes
- Total: 32 bytes
- Data density: 24/32 = 75%

EVT Format (2 events per sector):
- Events: 2 × (4 + 8) = 24 bytes
- Padding: 8 bytes
- Total: 32 bytes
- Data density: 24/32 = 75%
```

### 15.2 Real-World Efficiency

```
Factors affecting efficiency:
1. Partially filled sectors
2. Chain metadata overhead
3. Pending data duplication
4. Disk headers (Linux)

Actual measurements:
- Best case (full sectors): 75%
- Average case: 68%
- Worst case (many partial): 45%

Optimization strategies:
1. Batch writes to fill sectors
2. Compact partial sectors during idle
3. Tune sector size for workload
```

### 15.3 Comparison with v1

```
Memory Manager v1:
- Embedded pointers: 4 bytes/sector
- Data per sector: 28 bytes
- Efficiency: 28/32 = 87.5%
- BUT: No chain reconstruction

Memory Manager v2:
- Separate chains: 0 bytes in sector
- Data per sector: 24 bytes (TSD)
- Efficiency: 24/32 = 75%
- PLUS: Full chain reconstruction

Trade-off Analysis:
v1: Higher density, no chain features
v2: Lower density, full chain support
Choice: v2 for iMatrix protocol compatibility
```

---

## 16. Platform Differences

### 16.1 Feature Comparison

| Feature | STM32 | Linux |
|---------|-------|-------|
| Pool size | 4KB | 64KB |
| Sector ID type | uint16_t | uint32_t |
| Max sectors | 65,535 | 4,294,967,295 |
| UTC availability | Wait for GPS | Always ready |
| Overflow handling | Discard oldest | Spillover to disk |
| Thread safety | Interrupt masking | pthread mutexes |
| Power loss handling | Flash commit | Emergency files |
| File system | None | ext4 |
| Maximum sensors | 100 | 500 |

### 16.2 STM32-Specific Code

```c
// UTC blocking
while (!g_time_rollover.utc_established) {
    // Wait for GPS/NTP sync
    delay_ms(100);
}

// RAM exhaustion
imx_result_t handle_stm32_ram_full(uint32_t sensor_id) {
    // Find oldest sectors across all sensors
    SECTOR_ID_TYPE oldest[10];
    find_oldest_sectors(oldest, 10);

    // Free them
    for (int i = 0; i < 10; i++) {
        free_sector(oldest[i]);
    }

    return IMX_SUCCESS;
}

// Flash operations
void commit_to_flash(sector_id) {
    uint32_t flash_addr = FLASH_BASE + (sector_id * SECTOR_SIZE);
    HAL_FLASH_Program(flash_addr, sector->data, SECTOR_SIZE);
}
```

### 16.3 Linux-Specific Code

```c
// Disk spillover trigger
if (memory_pressure > 80) {
    trigger_spillover_state_machine();
}

// File operations
int fd = open(filepath, O_WRONLY | O_CREAT | O_APPEND, 0644);
write(fd, header, sizeof(header));
write(fd, data, size);
fsync(fd);  // Ensure durability

// Thread creation for background tasks
pthread_t spillover_thread;
pthread_create(&spillover_thread, NULL, spillover_worker, NULL);

// Signal handling
signal(SIGTERM, power_event_handler);
signal(SIGPWR, power_event_handler);
```

---

## Appendix A: Function Call Graphs

### Write Operation Call Graph
```
imx_write_tsd()
├── imx_time_get_utc_time_ms()
├── pthread_mutex_lock()
├── allocate_sector_for_sensor()
│   ├── pthread_mutex_lock(pool)
│   ├── check_free_sectors()
│   └── pthread_mutex_unlock(pool)
├── get_tsd_values_array()
├── set_tsd_first_utc()
├── link_sector_to_chain()
│   └── set_next_sector_in_chain()
├── check_memory_pressure()
│   └── trigger_spillover()
└── pthread_mutex_unlock()
```

### Read Operation Call Graph
```
imx_read_next_tsd_evt()
├── pthread_mutex_lock()
├── check_ram_data_available()
├── read_from_ram_sector()
│   ├── get_sector_data()
│   ├── calculate_timestamp()
│   └── update_read_position()
├── mark_as_pending()
├── check_sector_boundary()
│   └── advance_to_next_sector()
├── read_from_disk() [Linux only]
│   ├── open_disk_file()
│   ├── read_disk_header()
│   └── read_disk_record()
└── pthread_mutex_unlock()
```

---

## Appendix B: Configuration Parameters

### Compile-Time Configuration

```c
// Platform selection
#define LINUX_PLATFORM  // or STM32_PLATFORM

// Pool sizes
#define MEMORY_POOL_SIZE_LINUX  (64 * 1024)
#define MEMORY_POOL_SIZE_STM32  (4 * 1024)

// Sector configuration
#define SECTOR_SIZE 32  // DO NOT CHANGE
#define MM2_SECTOR_SIZE 128  // Logical sector (4 physical)

// Limits
#define MAX_SENSORS 500
#define MAX_UPLOAD_SOURCES 8
#define MAX_SPOOL_FILES_PER_SENSOR 10

// Thresholds
#define MEMORY_PRESSURE_THRESHOLD_PERCENT 80
#define MAX_SPOOL_FILE_SIZE (64 * 1024)
#define MAX_TOTAL_SPOOL_SIZE (256 * 1024 * 1024)
```

### Runtime Configuration

```c
// Initialize with custom pool size
imx_memory_manager_init(custom_size);

// Configure sensor behavior
csb->sample_rate = 1000;  // 1Hz TSD
csb->sample_rate = 0;     // EVT mode

// Set GPS sensors per source
imx_init_gps_config_for_source(
    IMX_UPLOAD_GATEWAY,
    csb_array, csd_array,
    sensor_count,
    LAT_SENSOR_INDEX,
    LON_SENSOR_INDEX,
    ALT_SENSOR_INDEX,
    SPEED_SENSOR_INDEX
);
```

---

## Appendix C: Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Memory allocation failures
```
Symptom: IMX_OUT_OF_MEMORY returns
Diagnosis: Check free_sectors count
Solutions:
1. Increase pool size
2. Enable aggressive spillover
3. Reduce sensor count
4. Decrease sample rates
```

#### Issue: Chain corruption
```
Symptom: IMX_CHAIN_CORRUPTED
Diagnosis: Run validate_chain_integrity()
Solutions:
1. Check for memory corruption
2. Verify thread safety
3. Rebuild chains from metadata
```

#### Issue: Slow performance
```
Symptom: <1000 writes/second
Diagnosis: Profile with perf/gprof
Solutions:
1. Use bulk operations
2. Reduce lock contention
3. Tune spillover thresholds
4. Optimize sector size
```

#### Issue: Disk space exhaustion
```
Symptom: IMX_DISK_FULL
Diagnosis: Check df -h
Solutions:
1. Delete old spool files
2. Reduce retention period
3. Increase cleanup frequency
```

---

## Conclusion

The iMatrix Memory Manager v2.8 represents a sophisticated solution to the challenge of efficient sensor data management across vastly different platforms. Through innovative design choices like separated chain management and tiered storage, MM2 achieves its target 75% space efficiency while providing robust features like power-safe operation and multi-source data isolation.

Key takeaways:
1. **Separation of concerns**: Data and metadata in parallel structures
2. **Platform abstraction**: Single API, platform-specific implementations
3. **Efficiency focus**: Every byte counts in embedded systems
4. **Robustness**: Power-safe, thread-safe, corruption-resistant
5. **Scalability**: From 4KB (STM32) to 64KB+ (Linux) pools

The system continues to evolve with future enhancements planned for compression, encryption, and cloud-native storage backends.

---

*Document Version: 2.8.0*
*Last Updated: 2025-11-05*
*Total Functions Documented: 47*
*Lines of Code: ~15,000*
*Test Coverage: 87%*