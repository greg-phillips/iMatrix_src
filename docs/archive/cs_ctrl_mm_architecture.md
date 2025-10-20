# iMatrix Memory Management Architecture

**Document Version:** 1.0
**Last Updated:** 2025-10-10
**Authors:** Architectural Analysis via Claude Code

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Memory Management Helper Functions](#memory-management-helper-functions)
3. [data_store_info_t Structure Deep Dive](#data_store_info_t-structure-deep-dive)
4. [Comprehensive Usage Analysis](#comprehensive-usage-analysis)
5. [Critical Architectural Insights](#critical-architectural-insights)
6. [Platform-Specific Considerations](#platform-specific-considerations)

---

## Executive Summary

The iMatrix sensor collection system uses a sophisticated tiered memory management architecture centered around the `data_store_info_t` structure. This structure is embedded in every `control_sensor_data_t` instance and manages sector chains that can span both RAM and disk storage (on Linux platforms).

**Key Characteristics:**
- **Sector-based allocation**: All data stored in linked sector chains
- **Platform-adaptive**: 16-bit addressing for embedded, 32-bit extended addressing for Linux
- **Tiered storage**: Transparent RAM-to-disk migration on Linux platforms
- **Transaction safety**: Atomic operations with journaling for crash recovery
- **Multi-tier APIs**: Legacy (unsafe), safe (bounds-checked), and extended (tiered storage)

---

## Memory Management Helper Functions

### 1. Core SAT Management Functions

#### `imx_sat_init()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
void imx_sat_init(void)
```
**Purpose**: Initialize the Sector Allocation Table (SAT) for RAM sector tracking. Sets up the allocation bitmap and initializes sector metadata structures.

**Call Tracing Summary**:
- Called during system initialization
- Invoked by device startup routines
- Required before any sector allocation operations

---

#### `init_sat()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
sram_init_status_t init_sat(void)
```
**Purpose**: Platform-specific SAT initialization with state machine. Handles different memory configurations and validates sector structures.

**Call Tracing Summary**:
- Called by `imx_sat_init()`
- Returns status indicating initialization success/failure
- Sets up platform-specific memory addressing

---

#### `imx_get_free_sector()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
#ifdef LINUX_PLATFORM
    int32_t imx_get_free_sector(void)    // Can return -1 or extended sector numbers
#else
    int16_t imx_get_free_sector(void)    // Original 16-bit return
#endif
```
**Purpose**: Allocate a free sector from SAT. On Linux, falls back to disk allocation when RAM exhausted. Returns -1 on failure.

**Call Tracing Summary**:
- Called by `write_tsd_evt_time()` when allocating new sectors for data
- Called throughout codebase for sector allocation
- On Linux: Automatically calls `allocate_disk_sector()` when RAM full
- Critical path for all data storage operations

---

#### `imx_get_free_sector_safe()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
#ifdef LINUX_PLATFORM
    int32_t imx_get_free_sector_safe(void)
#else
    int16_t imx_get_free_sector_safe(void)
#endif
```
**Purpose**: Safe version with comprehensive bounds checking and overflow protection.

**Call Tracing Summary**:
- Called by memory-critical operations requiring validation
- Preferred in new code for safety
- Includes extensive error checking and logging

---

#### `free_sector()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
void free_sector(platform_sector_t sector)
```
**Purpose**: Free a previously allocated sector. Handles both RAM and disk sectors transparently. Updates SAT bitmap and sector metadata.

**Call Tracing Summary**:
- Called by `erase_tsd_evt()` when removing old data
- Called by `reset_csd_entry()` during sensor cleanup
- Called by `imx_free_app_sectors()` in gateway applications
- Delegates to `free_sector_extended()` for disk sectors on Linux

---

#### `free_sector_safe()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
imx_memory_error_t free_sector_safe(platform_sector_t sector)
```
**Purpose**: Safe sector freeing with validation and error reporting.

**Call Tracing Summary**:
- Called by error recovery paths
- Used in validated operations requiring error codes
- Returns specific error types for debugging

---

#### `get_next_sector()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
platform_sector_t get_next_sector(platform_sector_t current_sector)
```
**Purpose**: Traverse sector chains by getting next sector pointer from sector metadata.

**Call Tracing Summary**:
- Called by `read_tsd_evt()` to traverse data chains
- Called by `print_sat()` for diagnostic output
- Used extensively in sector chain validation
- Delegates to `get_next_sector_extended()` for disk sectors

---

#### `get_next_sector_safe()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
sector_result_t get_next_sector_safe(platform_sector_t current_sector)
```
**Purpose**: Safe sector chain traversal with error checking. Returns both next sector and error status.

**Call Tracing Summary**:
- Called by `read_tsd_evt()` for safe chain traversal
- Used in `count_sectors_in_chain()` validation routines
- Preferred in new code for robustness

---

### 2. Raw Sector Read/Write Operations

#### `read_rs()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
void read_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)
```
**Purpose**: Read data from RAM sector. **CRITICAL**: Length parameter is number of uint32_t values, NOT bytes!

**Call Tracing Summary**:
- Called by internal read operations
- Legacy unsafe code (being replaced by `read_rs_safe()`)
- Used in performance-critical paths where validation already done

**⚠️ WARNING**: Length is in uint32_t units, not bytes!

---

#### `write_rs()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
void write_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)
```
**Purpose**: Write data to RAM sector. **CRITICAL**: Length parameter is number of uint32_t values, NOT bytes!

**Call Tracing Summary**:
- Called by internal write operations
- Legacy unsafe code (being replaced by `write_rs_safe()`)

**⚠️ WARNING**: Length is in uint32_t units, not bytes!

---

#### `read_rs_safe()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
imx_memory_error_t read_rs_safe(platform_sector_t sector, uint16_t offset,
                                 uint32_t *data, uint16_t length,
                                 uint16_t data_buffer_size)
```
**Purpose**: Bounds-checked sector read with buffer validation. Validates sector number, offset, and buffer size before operation.

**Call Tracing Summary**:
- Called by `read_tsd_evt()` for safe data reads
- Called by `write_tsd_evt_time()` when reading existing data
- Used throughout new safe code
- Prevents buffer overflows and invalid sector access

---

#### `write_rs_safe()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
imx_memory_error_t write_rs_safe(platform_sector_t sector, uint16_t offset,
                                  const uint32_t *data, uint16_t length,
                                  uint16_t data_buffer_size)
```
**Purpose**: Bounds-checked sector write with buffer validation.

**Call Tracing Summary**:
- Called by `write_tsd_evt_time()` for safe data writes
- Used throughout new safe code
- Ensures data integrity

---

### 3. Sector Metadata Access Functions

#### `write_sector_id()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
imx_memory_error_t write_sector_id(platform_sector_t sector, uint32_t id)
```
**Purpose**: Write control/sensor ID to sector metadata area. Each sector stores which sensor/control owns it.

**Call Tracing Summary**:
- Called by `write_tsd_evt_time()` during sector allocation
- Called during sector initialization
- Used for sector validation and ownership tracking

---

#### `write_sector_next()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
imx_memory_error_t write_sector_next(platform_sector_t sector, platform_sector_t next_sector)
```
**Purpose**: Link sectors in chain by setting next pointer in sector metadata.

**Call Tracing Summary**:
- Called by `write_tsd_evt_time()` when chaining new sectors
- Critical for building sector chains
- Used in all sector chain operations

---

#### `read_sector_id()`
**File**: `iMatrix/cs_ctrl/memory_manager_core.c`
**Signature**:
```c
imx_memory_error_t read_sector_id(platform_sector_t sector, uint32_t *id)
```
**Purpose**: Read control/sensor ID from sector metadata for validation.

**Call Tracing Summary**:
- Called by validation routines
- Used in sector verification and debugging
- Called by `print_sat()` diagnostic functions

---

### 4. TSD/EVT Data Operations

#### `write_tsd_evt()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void write_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry, uint32_t value, bool add_gps_location)
```
**Purpose**: Write Time Series Data or Event data with current timestamp and optional GPS coordinates.

**Call Tracing Summary**:
- Called by sensor/control sampling code throughout system
- Called by data collection routines
- Wrapper around `write_tsd_evt_time()` that adds current timestamp

---

#### `write_tsd_evt_time()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void write_tsd_evt_time(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                        uint16_t entry, uint32_t value, uint32_t utc_time)
```
**Purpose**: Core data write function with specific timestamp. Handles sector allocation, chain management, and data storage.

**Key Operations**:
- Allocates first sector if `csd[entry].ds.start_sector == 0`
- Allocates new sector when current sector full
- Reclaims space when out of sectors (erases oldest data)
- Updates `csd[entry].ds.count`, `no_samples`, `no_pending`

**Call Tracing Summary**:
- Called by `write_tsd_evt()`
- Called directly when explicit timestamp needed
- Core of all sensor data storage
- **Most important function for data_store_info_t manipulation**

---

#### `read_tsd_evt()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value)
```
**Purpose**: Read TSD/EVT data from current pending position, advances pending counter.

**Key Operations**:
- Traverses pending entries to find read position
- Reads data using `read_rs_safe()`
- Increments `csd[entry].no_pending`

**Call Tracing Summary**:
- Called by data upload/transmission code in `imatrix_upload/`
- Called by iMatrix cloud upload routines
- Called during data retrieval for processing

---

#### `erase_tsd_evt()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry)
```
**Purpose**: Erase pending data by advancing start_index. Releases sectors when empty.

**Key Operations**:
- Advances `csd[entry].ds.start_index` by `pending * record_size`
- Decrements `csd[entry].no_samples` and `ds.count`
- Frees sectors when chain traversed to end

**Call Tracing Summary**:
- Called after successful data transmission
- Called by `erase_tsd_evt_pending_data()`
- Critical for memory reclamation

---

#### `revert_tsd_evt_pending_data()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void revert_tsd_evt_pending_data(imx_control_sensor_block_t *csb,
                                  control_sensor_data_t *csd, uint16_t no_items)
```
**Purpose**: Rollback transaction by resetting pending count to 0.

**Call Tracing Summary**:
- Called on transaction failure/abort paths
- Called when data transmission fails
- Allows re-reading same data

---

#### `erase_tsd_evt_pending_data()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void erase_tsd_evt_pending_data(imx_control_sensor_block_t *csb,
                                 control_sensor_data_t *csd, uint16_t no_items)
```
**Purpose**: Commit pending data by calling `erase_tsd_evt()` for each entry.

**Call Tracing Summary**:
- Called after successful data transmission
- Finalizes data removal from storage
- Frees memory for new data

---

#### `imx_init_data_store_entry()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void imx_init_data_store_entry(data_store_info_t *ds)
```
**Purpose**: Initialize `data_store_info_t` structure to clean/unallocated state.

**Call Tracing Summary**:
- Called by `reset_csd_entry()`
- Called during initialization routines
- Sets all fields to 0 (no sectors allocated)

---

#### `reset_csd_entry()`
**File**: `iMatrix/cs_ctrl/memory_manager_tsd_evt.c`
**Signature**:
```c
void reset_csd_entry(control_sensor_data_t *csd, uint16_t entry)
```
**Purpose**: Free all sectors and reset complete CSD entry to clean state.

**Call Tracing Summary**:
- Called during sensor/control reset operations
- Called by cleanup routines
- Frees entire sector chain starting from `csd[entry].ds.start_sector`
- Calls `imx_init_data_store_entry(&csd[entry].ds)` to zero structure

---

### 5. Memory Statistics Functions

#### `imx_init_memory_statistics()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
void imx_init_memory_statistics(void)
```
**Purpose**: Initialize memory statistics tracking structure.

**Call Tracing Summary**:
- Called during system initialization
- Sets up statistics collection

---

#### `imx_update_memory_statistics()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
void imx_update_memory_statistics(void)
```
**Purpose**: Update current memory usage statistics from SAT.

**Call Tracing Summary**:
- Called after allocation/deallocation operations
- Called periodically for monitoring
- Updates usage percentages, fragmentation metrics

---

#### `imx_get_memory_statistics()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
imx_memory_statistics_t* imx_get_memory_statistics(void)
```
**Purpose**: Get pointer to current memory statistics structure.

**Call Tracing Summary**:
- Called by CLI commands
- Used by monitoring code
- Provides real-time memory metrics

---

#### `imx_calculate_fragmentation_level()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
uint32_t imx_calculate_fragmentation_level(void)
```
**Purpose**: Calculate memory fragmentation percentage (0-100).

**Call Tracing Summary**:
- Called by `imx_update_memory_statistics()`
- Analyzes SAT for fragmentation patterns
- Returns 0 (no fragmentation) to 100 (highly fragmented)

---

#### `record_allocation()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
void record_allocation(platform_sector_t sector)
```
**Purpose**: Record sector allocation event for statistics tracking.

**Call Tracing Summary**:
- Called by `imx_get_free_sector()`
- Called by `allocate_disk_sector()` on Linux
- Updates allocation counters and peak usage

---

#### `record_deallocation()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
void record_deallocation(platform_sector_t sector)
```
**Purpose**: Record sector deallocation event for statistics.

**Call Tracing Summary**:
- Called by `free_sector()`
- Called by `free_sector_extended()` on Linux
- Updates deallocation counters

---

#### `record_allocation_failure()`
**File**: `iMatrix/cs_ctrl/memory_manager_stats.c`
**Signature**:
```c
void record_allocation_failure(void)
```
**Purpose**: Record failed allocation attempt for monitoring.

**Call Tracing Summary**:
- Called by `imx_get_free_sector()` when out of memory
- Critical for diagnosing memory exhaustion

---

### 6. Tiered Storage Functions (Linux Only)

#### `process_memory()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
void process_memory(imx_time_t current_time)
```
**Purpose**: Main state machine for tiered storage. Called from main event loop every second.

**Call Tracing Summary**:
- Called by main event loop in Fleet-Connect-1
- Manages RAM-to-disk migration
- Handles shutdown flush operations
- Processes state: IDLE → CHECK_USAGE → MOVE_TO_DISK → CLEANUP_DISK → FLUSH_ALL

---

#### `flush_all_to_disk()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
void flush_all_to_disk(void)
```
**Purpose**: Request shutdown flush of all RAM data to disk.

**Call Tracing Summary**:
- Called by system shutdown handling code
- Called when ignition off detected
- Initiates migration of all RAM sectors to persistent disk storage

---

#### `get_flush_progress()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
uint8_t get_flush_progress(void)
```
**Purpose**: Get percentage of flush completion (0-100, returns 101 when complete).

**Call Tracing Summary**:
- Called by shutdown progress monitoring
- Provides feedback during graceful shutdown
- Returns 101 to indicate "safe to power off"

---

#### `is_all_ram_empty()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
bool is_all_ram_empty(void)
```
**Purpose**: Check if all RAM sectors have been freed/flushed to disk.

**Call Tracing Summary**:
- Called by shutdown completion detection
- Iterates all controls, sensors, gateway data
- Checks `ds.start_sector` for all entries
- Returns true only when all RAM sectors released

---

#### `cancel_memory_flush()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
void cancel_memory_flush(void)
```
**Purpose**: Cancel in-progress memory flush (e.g., ignition back on during shutdown).

**Call Tracing Summary**:
- Called by shutdown abort paths
- Called when ignition turns back on during flush
- Safely cancels ongoing file operations

---

#### `allocate_disk_sector()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
extended_sector_t allocate_disk_sector(uint16_t sensor_id)
```
**Purpose**: Allocate new disk sector with hierarchical file storage.

**Call Tracing Summary**:
- Called by `imx_get_free_sector()` when RAM exhausted
- Creates disk files in bucket hierarchy
- Returns extended sector number (>= SAT_NO_SECTORS)
- Uses sector recycling when possible

---

#### `move_sectors_to_disk()`
**File**: `iMatrix/cs_ctrl/memory_manager_tiered.c`
**Signature**:
```c
imx_memory_error_t move_sectors_to_disk(uint16_t sensor_id, uint16_t max_sectors, bool force_all)
```
**Purpose**: Migrate RAM sectors to disk for specific sensor.

**Call Tracing Summary**:
- Called by `handle_move_to_disk_state()` in state machine
- Called during tiered storage migration
- Reads RAM sectors, writes to disk files, updates `csd->ds` pointers
- Frees RAM sectors after successful migration

---

#### `read_sector_extended()`
**File**: `iMatrix/cs_ctrl/memory_manager.c`
**Signature**:
```c
imx_memory_error_t read_sector_extended(extended_sector_t sector, uint16_t offset,
                                         uint32_t *data, uint16_t length,
                                         uint16_t data_buffer_size)
```
**Purpose**: Read from either RAM or disk sector transparently.

**Call Tracing Summary**:
- Called by `read_rs()` when sector is disk-based (>= SAT_NO_SECTORS)
- Looks up sector location in sector lookup table
- Reads from disk file if needed
- Provides transparent access to tiered storage

---

#### `write_sector_extended()`
**File**: `iMatrix/cs_ctrl/memory_manager.c`
**Signature**:
```c
imx_memory_error_t write_sector_extended(extended_sector_t sector, uint16_t offset,
                                          const uint32_t *data, uint16_t length,
                                          uint16_t data_buffer_size)
```
**Purpose**: Write to either RAM or disk sector transparently.

**Call Tracing Summary**:
- Called by `write_rs()` when sector is disk-based
- Updates disk files in-place
- Maintains sector metadata consistency

---

#### `free_sector_extended()`
**File**: `iMatrix/cs_ctrl/memory_manager.c`
**Signature**:
```c
imx_memory_error_t free_sector_extended(extended_sector_t sector)
```
**Purpose**: Free either RAM or disk sector, adds disk sectors to recycling list.

**Call Tracing Summary**:
- Called by `free_sector()` when sector is disk-based
- Adds freed sector to free list for recycling
- Checks if entire disk file can be deleted
- Calls `check_and_cleanup_disk_file()` for cleanup

---

#### `get_next_sector_extended()`
**File**: `iMatrix/cs_ctrl/memory_manager.c`
**Signature**:
```c
extended_sector_result_t get_next_sector_extended(extended_sector_t current_sector)
```
**Purpose**: Get next sector in chain for RAM or disk sectors.

**Call Tracing Summary**:
- Called by `get_next_sector()` when traversing disk chains
- Reads next pointer from disk sector metadata
- Returns extended sector result with error checking

---

### 7. Disk Management Functions

#### `create_disk_file_atomic()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
imx_memory_error_t create_disk_file_atomic(uint16_t sensor_id,
                                            extended_evt_tsd_sector_t *sectors,
                                            uint32_t sector_count,
                                            char *filename, size_t filename_size)
```
**Purpose**: Create disk file atomically using journaling for crash safety.

**Call Tracing Summary**:
- Called by `move_sectors_to_disk()`
- Uses temp file → fsync → rename pattern
- Writes journal entry before operation
- Ensures no data loss on power failure

---

#### `get_available_disk_space()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
uint64_t get_available_disk_space(void)
```
**Purpose**: Get available disk space in bytes using statvfs().

**Call Tracing Summary**:
- Called by `allocate_disk_sector()` before allocation
- Used for disk space checks
- Triggers cleanup if space low

---

#### `get_total_disk_space()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
uint64_t get_total_disk_space(void)
```
**Purpose**: Get total disk space in bytes.

**Call Tracing Summary**:
- Used for calculating disk usage percentage
- Called during statistics updates

---

#### `init_disk_sector_recycling()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
void init_disk_sector_recycling(void)
```
**Purpose**: Initialize disk sector recycling free list.

**Call Tracing Summary**:
- Called by `init_disk_storage_system()`
- Sets up free sector linked list
- Initializes recycling metadata

---

#### `add_sector_to_free_list()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
void add_sector_to_free_list(extended_sector_t sector)
```
**Purpose**: Add freed disk sector to recycling list.

**Call Tracing Summary**:
- Called by `free_sector_extended()`
- Called by cleanup operations
- Maintains free list for sector reuse

---

#### `get_recycled_sector()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
extended_sector_t get_recycled_sector(void)
```
**Purpose**: Get a recycled sector from free list.

**Call Tracing Summary**:
- Called by `allocate_disk_sector()` before creating new sectors
- Reuses freed sectors to minimize disk file creation
- Returns 0 if no recycled sectors available

---

#### `check_and_cleanup_disk_file()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
void check_and_cleanup_disk_file(const char *filename)
```
**Purpose**: Check if all sectors in file have been freed and delete file if empty.

**Call Tracing Summary**:
- Called by `free_sector_extended()` after freeing disk sector
- Scans file to check if all sectors freed
- Deletes file and updates metadata if empty
- Reclaims disk space

---

#### `free_oldest_disk_data()`
**File**: `iMatrix/cs_ctrl/memory_manager_disk.c`
**Signature**:
```c
bool free_oldest_disk_data(uint64_t bytes_needed)
```
**Purpose**: Free oldest disk files to make space when disk usage high.

**Call Tracing Summary**:
- Called by `allocate_disk_sector()` when disk usage > 80%
- Deletes oldest files first
- Returns true if enough space freed

---

### 8. Utility Functions

#### `update_sector_location()`
**File**: `iMatrix/cs_ctrl/memory_manager_utils.c`
**Signature**:
```c
void update_sector_location(extended_sector_t sector, sector_location_t location,
                             const char *filename, uint32_t offset)
```
**Purpose**: Update sector lookup table with location info (RAM/disk/freed).

**Call Tracing Summary**:
- Called during disk migration
- Called by sector tracking operations
- Maintains global sector lookup table

---

#### `get_sector_location()`
**File**: `iMatrix/cs_ctrl/memory_manager_utils.c`
**Signature**:
```c
sector_location_t get_sector_location(extended_sector_t sector)
```
**Purpose**: Query sector location (RAM/disk/freed).

**Call Tracing Summary**:
- Called by `read_sector_extended()`
- Called by `write_sector_extended()`
- Called by `free_sector_extended()`
- Critical for transparent tiered storage

---

#### `calculate_checksum()`
**File**: `iMatrix/cs_ctrl/memory_manager_utils.c`
**Signature**:
```c
uint32_t calculate_checksum(const void *data, size_t size)
```
**Purpose**: Calculate simple checksum for data integrity validation.

**Call Tracing Summary**:
- Called during disk file operations
- Called for journal operations
- Validates data integrity after read

---

#### `ensure_directory_exists()`
**File**: `iMatrix/cs_ctrl/memory_manager_utils.c`
**Signature**:
```c
bool ensure_directory_exists(const char *path)
```
**Purpose**: Create directory recursively if doesn't exist.

**Call Tracing Summary**:
- Called before disk file creation
- Called during storage initialization
- Creates bucket hierarchy

---

## data_store_info_t Structure Deep Dive

### Structure Definition

**File**: `iMatrix/common.h:1177-1187`

```c
typedef struct _data_store_info {
    platform_sector_t start_sector;   // Platform-dependent: 16-bit (embedded) or 32-bit (LINUX)
    platform_sector_t end_sector;     // Platform-dependent: 16-bit (embedded) or 32-bit (LINUX)
    /*
     * The count refers to the current sector NOT total count.
     * For Variable length records this represents the actual byte count used in the sector
     * For Total Count is # sectors * number of readings in a sector + count
     * and is also stored in the no_samples variable in the control_sensor_data_t structure
     */
    uint16_t start_index;
    uint16_t count;
} data_store_info_t;
```

### Member Field Descriptions

| Field | Type | Purpose | Range | Notes |
|-------|------|---------|-------|-------|
| `start_sector` | `platform_sector_t` | First sector in data chain | 0 to PLATFORM_MAX_SECTORS | Points to oldest data; 0 means no data allocated |
| `end_sector` | `platform_sector_t` | Last sector in data chain | 0 to PLATFORM_MAX_SECTORS | Points to newest data; where new writes occur |
| `start_index` | `uint16_t` | Byte offset in start_sector | 0 to SRAM_SECTOR_SIZE-1 | Offset to oldest unread data |
| `count` | `uint16_t` | Records in end_sector | 0 to entries_per_sector | **NOT total count** - only in current end_sector |

### Platform-Specific Sector Types

```c
#ifdef LINUX_PLATFORM
    typedef uint32_t platform_sector_t;  // Extended addressing
    #define PLATFORM_MAX_SECTORS    (0xFFFFFFFF)
    #define PLATFORM_INVALID_SECTOR (0xFFFFFFFF)
    // Sectors 0 to SAT_NO_SECTORS-1: RAM
    // Sectors SAT_NO_SECTORS to 0xFFFFFFFF: Disk
#else
    typedef uint16_t platform_sector_t;  // Embedded systems
    #define PLATFORM_MAX_SECTORS    (0xFFFF)
    #define PLATFORM_INVALID_SECTOR (0xFFFF)
    // All sectors in RAM only
#endif
```

### Embedded Context: control_sensor_data_t

**File**: `iMatrix/common.h:1189-1211`

```c
typedef struct control_sensor_data {
    imx_utc_time_ms_t last_sample_time;
    uint16_t no_samples;              // ⚡ Total samples across ALL sectors
    uint16_t no_pending;              // Samples ready for upload/transmission
    uint32_t errors;
    imx_time_t last_poll_time;
    imx_time_t condition_started_time;
    imx_data_32_t last_raw_value;
    imx_data_32_t last_value;
    data_store_info_t ds;             // ⚡ DATA STORE INFO EMBEDDED HERE
    // ... bit fields for flags ...
} control_sensor_data_t;
```

**Key Relationship**:
- `csd.ds` - The data store structure embedded in every sensor/control
- `csd.no_samples` - **Total** count across all sectors in chain
- `csd.ds.count` - Count in **current end_sector only**

### Critical Invariants

These relationships MUST be maintained at all times:

```c
// Total samples calculation
total_samples = (sectors_in_chain - 1) * entries_per_sector + ds.count

// Must match
csd.no_samples == total_samples

// Pending constraint
csd.no_pending <= csd.no_samples

// Sector chain validity
if (ds.start_sector == 0) then ds.end_sector == 0  // No data allocated
if (ds.start_sector != 0) then ds.end_sector != 0  // Data exists

// Index constraints
ds.start_index < SRAM_SECTOR_SIZE
ds.count <= entries_per_sector
```

---

## Comprehensive Usage Analysis

### Usage Table: data_store_info_t Field Access

| Source File | Function Name | Variable/Context | Type of Access | Code Context |
| :--- | :--- | :--- | :--- | :--- |
| `memory_manager_tsd_evt.c` | `write_tsd_evt_time` | `csd[entry].ds.start_sector` | **Write (allocation)** | Allocates first sector if 0: `csd[entry].ds.start_sector = first_sector` |
| `memory_manager_tsd_evt.c` | `write_tsd_evt_time` | `csd[entry].ds.end_sector` | **Write (allocation)** | Allocates new sector: `csd[entry].ds.end_sector = new_sector` |
| `memory_manager_tsd_evt.c` | `write_tsd_evt_time` | `csd[entry].ds.count` | **Write (increment)** | Increments after write: `csd[entry].ds.count += 1` |
| `memory_manager_tsd_evt.c` | `write_tsd_evt_time` | `csd[entry].ds.count` | **Write (reset)** | Resets on sector overflow: `csd[entry].ds.count = 0` |
| `memory_manager_tsd_evt.c` | `write_tsd_evt_time` | `csd[entry].ds.end_sector` | **Read** | Checks if sector full before allocation |
| `memory_manager_tsd_evt.c` | `read_tsd_evt` | `csd[entry].ds.start_sector` | **Read** | Starts traversal: `sector = csd[entry].ds.start_sector` |
| `memory_manager_tsd_evt.c` | `read_tsd_evt` | `csd[entry].ds.end_sector` | **Read** | Checks end of chain for validation |
| `memory_manager_tsd_evt.c` | `read_tsd_evt` | `csd[entry].ds.start_index` | **Read** | Uses as offset: `index = csd[entry].ds.start_index` |
| `memory_manager_tsd_evt.c` | `read_tsd_evt` | `csd[entry].ds.count` | **Read** | Validates against count for bounds checking |
| `memory_manager_tsd_evt.c` | `erase_tsd_evt` | `csd[entry].ds.start_sector` | **Read/Write** | Reads to traverse, writes when freeing sectors |
| `memory_manager_tsd_evt.c` | `erase_tsd_evt` | `csd[entry].ds.end_sector` | **Read** | Checks if reached end of chain |
| `memory_manager_tsd_evt.c` | `erase_tsd_evt` | `csd[entry].ds.start_index` | **Write (advance)** | Advances: `csd[entry].ds.start_index += total_advancement` |
| `memory_manager_tsd_evt.c` | `erase_tsd_evt` | `csd[entry].ds.start_index` | **Write (reset)** | Resets on wraparound: `csd[entry].ds.start_index = 0` |
| `memory_manager_tsd_evt.c` | `erase_tsd_evt` | `csd[entry].ds.count` | **Write (decrement)** | Decrements: `csd[entry].ds.count -= records_to_erase` |
| `memory_manager_tsd_evt.c` | `erase_tsd_evt` | `csd[entry].ds.count` | **Write (reset)** | Resets: `csd[entry].ds.count = 0` on sector free |
| `memory_manager_tsd_evt.c` | `imx_init_data_store_entry` | `ds->start_sector` | **Write (init)** | Zeros: `ds->start_sector = 0` |
| `memory_manager_tsd_evt.c` | `imx_init_data_store_entry` | `ds->end_sector` | **Write (init)** | Zeros: `ds->end_sector = 0` |
| `memory_manager_tsd_evt.c` | `imx_init_data_store_entry` | `ds->start_index` | **Write (init)** | Zeros: `ds->start_index = 0` |
| `memory_manager_tsd_evt.c` | `imx_init_data_store_entry` | `ds->count` | **Write (init)** | Zeros: `ds->count = 0` |
| `memory_manager_tsd_evt.c` | `reset_csd_entry` | `csd[entry].ds` | **Write (via init)** | Calls `imx_init_data_store_entry(&csd[entry].ds)` |
| `memory_manager_tsd_evt.c` | `reset_csd_entry` | `csd[entry].ds.start_sector` | **Read** | Reads to free sector chain before zeroing |
| `memory_manager_tsd_evt.c` | `print_sat` | All fields | **Read (diagnostic)** | Prints all ds fields for debugging |
| `memory_manager_tiered.c` | `flush_all_to_disk` | `cd[i].ds.start_sector` | **Read** | Checks: `if (cd[i].ds.start_sector != 0 && < SAT_NO_SECTORS)` |
| `memory_manager_tiered.c` | `flush_all_to_disk` | `sd[i].ds.start_sector` | **Read** | Checks: `if (sd[i].ds.start_sector != 0 && < SAT_NO_SECTORS)` |
| `memory_manager_tiered.c` | `is_all_ram_empty` | `cd[i].ds.start_sector` | **Read** | Validates: `cd[i].ds.start_sector == 0 \|\| >= SAT_NO_SECTORS` |
| `memory_manager_tiered.c` | `is_all_ram_empty` | `sd[i].ds.start_sector` | **Read** | Validates: `sd[i].ds.start_sector == 0 \|\| >= SAT_NO_SECTORS` |
| `memory_manager_tiered.c` | `is_all_ram_empty` | `mgs.csd[i].ds.start_sector` | **Read** | Checks gateway control data |
| `memory_manager_tiered.c` | `is_all_ram_empty` | `mgs.can_csd[i].ds.start_sector` | **Read** | Checks CAN gateway data |
| `memory_manager_tiered.c` | `is_all_ram_empty` | `cb.can_controller->csd[i].ds.start_sector` | **Read** | Checks CAN controller data |
| `memory_manager_tiered.c` | `move_sectors_to_disk` | `csd->ds.start_sector` | **Read** | Starts migration: `current = csd->ds.start_sector` |
| `memory_manager_tiered.c` | `move_sectors_to_disk` | `csd->ds.end_sector` | **Read** | Checks end: `while (current != csd->ds.end_sector)` |
| `memory_manager_tiered.c` | `move_sectors_to_disk` | `csd->ds.start_sector` | **Write** | Updates after migration: `csd->ds.start_sector = disk_sector` |
| `memory_manager_tiered.c` | `move_sectors_to_disk` | `csd->ds.end_sector` | **Write** | Updates: `csd->ds.end_sector = disk_sector + count - 1` |
| `imatrix_upload.c` | (multiple functions) | `csd[i].ds.start_sector` | **Read** | Gets chain start for data upload |
| `imatrix_upload.c` | (multiple functions) | `csd[i].ds.start_index` | **Read** | Uses for read offset during upload |
| `imatrix_upload.c` | (multiple functions) | `csd[i].ds.end_sector` | **Read** | Determines end of data chain |
| `cs_memory_mgt.c` | (legacy functions) | `csd[entry].ds.*` | **Read/Write** | Legacy compatibility wrappers |

---

## Critical Architectural Insights

### 1. The Central Role of data_store_info_t

**Every sensor and control** in the iMatrix system has a `control_sensor_data_t` structure which embeds a `data_store_info_t ds` field. This single structure manages:

- All storage locations for that sensor's data
- The chain of sectors holding historical data
- Read and write positions within the chain
- Total data count and pending transmission count

**Without `data_store_info_t`, the entire sensor data storage system would collapse.**

---

### 2. Sector Chain Architecture

```
control_sensor_data_t.ds:
  start_sector -> [Sector 0] -> [Sector 1] -> [Sector 2] -> ... -> end_sector
                   ^                                                  ^
                   |                                                  |
                   oldest data                                        newest data
                   start_index offset
```

**Write Flow**:
1. New data written at `end_sector` with offset `count * record_size`
2. `count` incremented
3. When `count` reaches `entries_per_sector`, allocate new sector
4. Link new sector: `write_sector_next(end_sector, new_sector)`
5. Update `end_sector = new_sector`, reset `count = 0`

**Read Flow**:
1. Start at `start_sector` with offset `start_index`
2. Read `no_pending` entries
3. Traverse chain using `get_next_sector()`
4. Increment `no_pending` to track what's been read

**Erase Flow**:
1. Advance `start_index` by `pending * record_size`
2. If `start_index` exceeds sector boundary:
   - Free `start_sector`
   - Advance to next sector in chain
   - Reset `start_index = 0`
3. Decrement `no_samples` and `count`

---

### 3. Platform-Dependent Sector Addressing

#### Embedded Platforms (WICED)
```c
typedef uint16_t platform_sector_t;
// All sectors 0 to 65535 are in RAM (SFLASH)
// Typical: SAT_NO_SECTORS = 256 (small embedded systems)
```

#### Linux Platforms (Fleet-Connect-1)
```c
typedef uint32_t platform_sector_t;
// Extended addressing with tiered storage:
//   Sectors 0 to SAT_NO_SECTORS-1: RAM (fast, limited)
//   Sectors SAT_NO_SECTORS to 0xFFFFFFFF: Disk (slow, unlimited)
// Typical: SAT_NO_SECTORS = 65536 (64K RAM sectors)
```

**Transparent Access**:
- `read_rs()` automatically delegates to `read_sector_extended()` for disk sectors
- `write_rs()` automatically delegates to `write_sector_extended()` for disk sectors
- `free_sector()` automatically delegates to `free_sector_extended()` for disk sectors
- **Application code doesn't know if data is in RAM or on disk!**

---

### 4. Critical Metadata Relationships

#### Invariants (MUST be maintained)

```c
// Total sample calculation
total_samples = (number_of_sectors_in_chain - 1) * entries_per_sector + ds.count
csd.no_samples == total_samples  // MUST be equal

// Pending constraint
csd.no_pending <= csd.no_samples  // Cannot have more pending than total

// Allocation state
if (ds.start_sector == 0) {
    ds.end_sector == 0     // No data allocated
    no_samples == 0
    no_pending == 0
}

if (ds.start_sector != 0) {
    ds.end_sector != 0     // Data exists
    no_samples > 0
}

// Index constraints
ds.start_index < SRAM_SECTOR_SIZE
ds.count <= entries_per_sector
```

#### Common Calculation Patterns

```c
// Calculate total samples
uint32_t total = 0;
platform_sector_t sector = csd.ds.start_sector;
while (sector != csd.ds.end_sector) {
    total += entries_per_sector;
    sector = get_next_sector(sector);
}
total += csd.ds.count;  // Add records in last sector

// Calculate bytes used
uint32_t bytes = (total * record_size);

// Calculate sectors used
uint32_t sectors = 1;  // At least one if data exists
sector = csd.ds.start_sector;
while (sector != csd.ds.end_sector) {
    sectors++;
    sector = get_next_sector(sector);
}
```

---

### 5. Tiered Storage Transparency (Linux Only)

On Linux platforms, the system provides **unlimited storage** through transparent tiering:

#### Storage Hierarchy
```
Level 1: RAM Sectors (0 to SAT_NO_SECTORS-1)
  - Fast access (microseconds)
  - Limited capacity (e.g., 64K sectors = ~128MB)
  - Managed by SAT (Sector Allocation Table)

Level 2: Disk Sectors (SAT_NO_SECTORS to 0xFFFFFFFF)
  - Slower access (milliseconds)
  - Unlimited capacity (limited by disk space)
  - Organized in hierarchical directories
  - File format: buckets/bucket_N/sensor_NNNN_SSSSSSS.dat
```

#### Automatic Migration

The `process_memory()` state machine runs every second:

```c
State: CHECK_USAGE
  if (ram_usage > 80%) {
      transition to MOVE_TO_DISK
  }

State: MOVE_TO_DISK
  - Select sensor with most RAM sectors
  - Move batch of sectors to disk
  - Update ds.start_sector and ds.end_sector to disk sector numbers
  - Free RAM sectors
  - Repeat until RAM usage < 80%

State: CLEANUP_DISK
  - Check disk usage
  - If disk > 80%, delete oldest files
  - Maintain available space
```

#### Crash Recovery

Every disk operation uses journaling:

```c
1. Write journal entry (temp file, final file, sectors involved)
2. Sync journal to disk
3. Create temp file with data
4. Sync temp file to disk
5. Rename temp to final (atomic operation)
6. Clear journal entry
7. Sync journal again
```

On startup after power failure:
- Read recovery journal
- Check for incomplete operations
- Complete or rollback based on state
- Validate all files
- Rebuild metadata

---

### 6. Memory Safety Evolution

The codebase shows clear evolution toward memory safety:

#### Legacy (Unsafe) APIs
```c
void read_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)
void write_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)
void free_sector(platform_sector_t sector)
```
- No bounds checking
- No error returns
- Potential for buffer overflows
- **Still used in performance-critical paths**

#### Modern (Safe) APIs
```c
imx_memory_error_t read_rs_safe(..., uint16_t data_buffer_size)
imx_memory_error_t write_rs_safe(..., uint16_t data_buffer_size)
imx_memory_error_t free_sector_safe(platform_sector_t sector)
sector_result_t get_next_sector_safe(platform_sector_t current_sector)
```
- Comprehensive validation
- Error code returns
- Buffer size parameters
- Overflow detection
- **Used in all new code**

---

### 7. Fragmentation Management

The system tracks and manages memory fragmentation:

```c
uint32_t imx_calculate_fragmentation_level(void)
{
    // Scans SAT for free sector distribution
    // Returns 0 (no fragmentation) to 100 (highly fragmented)

    // Low fragmentation: Free sectors are contiguous blocks
    // High fragmentation: Free sectors scattered throughout SAT
}
```

**Impact of Fragmentation**:
- **Low impact on performance**: Sector allocation is O(n) scan anyway
- **High impact on wear leveling**: Scattered allocations spread wear
- **Disk storage is immune**: Files are contiguous, no fragmentation

---

### 8. Performance Characteristics

#### Operation Time Complexity

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| `imx_get_free_sector()` | O(n) worst case | Linear scan of SAT bitmap |
| `free_sector()` | O(1) | Direct bitmap update |
| `get_next_sector()` | O(1) | Read metadata from sector |
| `write_tsd_evt_time()` | O(1) amortized | Occasional sector allocation |
| `read_tsd_evt()` | O(n) worst case | May traverse multiple sectors |
| `erase_tsd_evt()` | O(n) worst case | May free multiple sectors |
| `move_sectors_to_disk()` | O(n) | Read all sectors, write file |

#### Memory Footprint

**Per Sensor/Control**:
- `control_sensor_data_t`: ~64 bytes
- `data_store_info_t`: 8-12 bytes (embedded in above)
- Sector overhead: 8 bytes per sector (next pointer + ID)

**System Global**:
- SAT bitmap: `SAT_NO_SECTORS / 8` bytes (e.g., 8KB for 64K sectors)
- Sector lookup table (Linux): ~32 bytes per disk sector
- Free sector list (Linux): ~16 bytes per freed disk sector

---

## Platform-Specific Considerations

### Embedded Platforms (WICED)

**Characteristics**:
- Limited RAM: Typically 256-512 sectors
- All storage in RAM/SFLASH
- No tiered storage
- 16-bit sector addressing

**Optimization Strategies**:
- Aggressive data compression
- Circular buffer overwrites when full
- Shorter retention periods
- Immediate upload to cloud

**Memory Constraints**:
```c
#define SAT_NO_SECTORS 256
typedef uint16_t platform_sector_t;
// Total capacity: 256 sectors * ~500 bytes/sector = ~128KB
```

---

### Linux Platforms (Fleet-Connect-1)

**Characteristics**:
- Abundant RAM: 64K+ sectors typical
- Tiered storage to disk
- 32-bit extended addressing
- Unlimited capacity (disk-limited)

**Optimization Strategies**:
- RAM caching of hot data
- Background migration to disk
- Graceful shutdown flush
- Long retention periods

**Memory Configuration**:
```c
#define SAT_NO_SECTORS 65536
typedef uint32_t platform_sector_t;
// RAM capacity: 65536 sectors * ~500 bytes = ~32MB
// Disk capacity: Limited by filesystem (typically gigabytes)
```

---

### Cross-Platform Abstraction

The system uses conditional compilation for platform differences:

```c
#ifdef LINUX_PLATFORM
    // 32-bit extended addressing
    typedef uint32_t platform_sector_t;
    int32_t imx_get_free_sector(void);
    // Tiered storage functions available
    void process_memory(imx_time_t current_time);
#else
    // 16-bit addressing for embedded
    typedef uint16_t platform_sector_t;
    int16_t imx_get_free_sector(void);
    // No tiered storage
#endif
```

**Application code remains platform-agnostic** - same API works on both platforms!

---

## Conclusion

The iMatrix memory management architecture is a sophisticated, battle-tested system that provides:

✅ **Scalability**: From 256 sectors (embedded) to billions (Linux disk)
✅ **Reliability**: Journaling, atomic operations, crash recovery
✅ **Transparency**: Applications don't know if data is in RAM or on disk
✅ **Safety**: Modern APIs prevent buffer overflows and corruption
✅ **Performance**: O(1) for common operations, efficient sector chaining
✅ **Flexibility**: Platform-specific optimizations with unified API

The `data_store_info_t` structure is the linchpin of this entire architecture, embedded in every sensor/control and accessed by virtually every memory operation in the system.

---

**End of Document**
