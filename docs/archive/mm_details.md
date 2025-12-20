# iMatrix Memory Manager (MM2) - Technical Reference

**Document Version:** 1.0
**Date:** 2025-11-19
**Memory Manager Version:** v2.8
**Purpose:** Comprehensive reference for debugging memory corruption issues

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Data Structures](#key-data-structures)
3. [Memory Pool Management](#memory-pool-management)
4. [Sector Chain Management](#sector-chain-management)
5. [Data Types: TSD vs EVT](#data-types-tsd-vs-evt)
6. [Operation Flows](#operation-flows)
7. [Platform Differences](#platform-differences)
8. [Error Handling & Recovery](#error-handling--recovery)
9. [Critical Debug Points](#critical-debug-points)

---

## Architecture Overview

### Design Philosophy

MM2 achieves **75% space efficiency** by removing embedded `next_sector` pointers from RAM sectors and using a separate chain management table. This is a critical optimization for embedded systems with limited RAM.

**Key Innovation:**
- **Old Design:** Sectors contained data + next_sector pointer (overhead)
- **New Design:** Sectors contain ONLY data, chains managed separately

### Core Components

```
iMatrix/cs_ctrl/
├── mm2_api.c/h           # Public API interface
├── mm2_core.h            # Core data structures and constants
├── mm2_internal.h        # Internal function declarations
├── mm2_pool.c            # Memory pool allocation/deallocation
├── mm2_read.c            # Read operations (TSD/EVT)
├── mm2_write.c           # Write operations (TSD/EVT)
├── mm2_disk_*.c          # Disk spooling subsystem (Linux only)
├── mm2_power*.c          # Power management and abort handling
├── mm2_startup_recovery.c # Startup recovery from disk
├── mm2_stm32.c           # STM32-specific implementation
├── mm2_compatibility.c   # Legacy API compatibility
└── memory_manager_stats.c # Statistics and monitoring
```

### Tiered Storage System (Linux)

```
┌─────────────────────────────────────────────┐
│          Application Layer                  │
│  (Sensors writing data via imx_write_*)    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│           MM2 API Layer                     │
│  - imx_write_tsd()                          │
│  - imx_write_evt()                          │
│  - imx_read_bulk_samples()                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│      RAM Pool (64KB on Linux)               │
│  - Fast allocation from free list           │
│  - Separate chain table for links          │
│  - 75% data efficiency (TSD)                │
└─────────────────────────────────────────────┘
                    ↓ (when RAM fills)
┌─────────────────────────────────────────────┐
│    Disk Spooling (/tmp/mm2/)                │
│  - Organized by upload_source/sensor_id     │
│  - Oldest data spooled first                │
│  - Read back on demand                      │
└─────────────────────────────────────────────┘
```

---

## Key Data Structures

### 1. Memory Sector (32 bytes)

```c
typedef struct {
    uint8_t data[SECTOR_SIZE];  // SECTOR_SIZE = 32 bytes
} memory_sector_t;
```

**Critical:** Contains ONLY raw data - no metadata!

### 2. Sector Chain Entry

```c
typedef struct {
    SECTOR_ID_TYPE sector_id;        // This sector ID
    SECTOR_ID_TYPE next_sector_id;   // Next in chain (NULL_SECTOR_ID = end)
    uint32_t sensor_id;              // Owner sensor
    uint8_t sector_type;             // TSD or EVT
    uint8_t reserved1;
    uint16_t reserved2;
    uint64_t creation_time_ms;       // Allocation time

    // Status flags (bitfields)
    unsigned int in_use              : 1;
    unsigned int spooled_to_disk     : 1;
    unsigned int pending_ack         : 1;
    unsigned int reserved_flags      : 29;
} sector_chain_entry_t;
```

**This is the key to 75% efficiency** - chain metadata stored separately!

### 3. Global Memory Pool

```c
typedef struct {
    memory_sector_t* sectors;         // Raw sector storage
    sector_chain_entry_t* chain_table; // Separate chain management
    uint32_t total_sectors;
    uint32_t free_sectors;

    SECTOR_ID_TYPE* free_list;        // Free sector IDs
    uint32_t free_list_head;

    #ifdef LINUX_PLATFORM
    pthread_mutex_t pool_lock;        // Thread safety
    #endif

    // Statistics
    uint64_t total_allocations;
    uint64_t total_deallocations;
    uint64_t allocation_failures;
} global_memory_pool_t;
```

### 4. Memory Control Block (per sensor)

Embedded in `control_sensor_data_t` as `mmcb` field:

```c
typedef struct {
    SECTOR_ID_TYPE ram_start_sector;
    SECTOR_ID_TYPE ram_end_sector;
    uint16_t ram_read_offset;
    uint16_t ram_write_offset;

    // Per-upload-source pending tracking
    struct {
        SECTOR_ID_TYPE pending_start_sector;
        uint16_t pending_start_offset;
        uint32_t pending_count;
    } pending_by_source[UPLOAD_SOURCE_MAX];

    uint64_t total_records_written;
    uint64_t last_sample_time_ms;

    unsigned int active : 1;
    unsigned int configured : 1;
    // ... more flags
} imx_mmcb_t;  // Defined in common.h
```

---

## Memory Pool Management

### Initialization (Linux Platform)

```c
imx_result_t init_memory_pool(uint32_t pool_size)
```

1. Allocates `pool_size` bytes for sectors (default: 64KB = 2048 sectors)
2. Allocates parallel chain_table (2048 × sector_chain_entry_t)
3. Initializes free_list with all sector IDs (0...2047)
4. Sets `free_list_head = 0`, `free_sectors = 2048`
5. Initializes mutex for thread safety

### Sector Allocation

```c
SECTOR_ID_TYPE allocate_sector_for_sensor(uint32_t sensor_id, uint8_t sector_type)
```

**Algorithm:**
1. Lock `pool_lock`
2. Check `free_sectors > 0`
3. Pop sector ID from `free_list[free_list_head++]`
4. Initialize `chain_table[sector_id]`:
   - `in_use = 1`
   - `sensor_id = sensor_id`
   - `sector_type = sector_type`
   - `next_sector_id = NULL_SECTOR_ID`
   - `creation_time_ms = current_time`
5. Decrement `free_sectors`
6. Clear sector data to zero
7. Unlock and return sector ID

**On Failure (free_sectors == 0):**
- **Linux:** Trigger disk spooling to free RAM
- **STM32:** Discard oldest non-pending data

### Sector Deallocation

```c
imx_result_t free_sector(SECTOR_ID_TYPE sector_id)
```

**Algorithm:**
1. Lock `pool_lock`
2. Validate sector_id < total_sectors
3. Clear `chain_table[sector_id]` (set `in_use = 0`)
4. Push sector_id back onto `free_list[--free_list_head]`
5. Increment `free_sectors`
6. Unlock

---

## Sector Chain Management

### Chain Operations

**Get Next Sector:**
```c
SECTOR_ID_TYPE get_next_sector_in_chain(SECTOR_ID_TYPE sector_id) {
    return chain_table[sector_id].next_sector_id;
}
```

**Set Next Sector:**
```c
void set_next_sector_in_chain(SECTOR_ID_TYPE sector_id, SECTOR_ID_TYPE next) {
    chain_table[sector_id].next_sector_id = next;
}
```

**Link New Sector to End:**
```c
imx_result_t link_sector_to_chain(SECTOR_ID_TYPE current_end, SECTOR_ID_TYPE new_sector)
```

### Chain Walking

```c
// Typical chain traversal
SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector;
while (current != NULL_SECTOR_ID) {
    sector_chain_entry_t* entry = &chain_table[current];
    // Process sector data...
    current = entry->next_sector_id;
}
```

**CRITICAL:** Always use `get_next_sector_in_chain()` - NEVER assume sequential allocation!

---

## Data Types: TSD vs EVT

### Time Series Data (TSD)

**Used for:** Regular sampled data (temperature, voltage, speed, etc.)

**Sector Format (32 bytes):**
```
┌────────────────┬────────┬────────┬────────┬────────┬────────┬────────┐
│  first_UTC:8   │ val0:4 │ val1:4 │ val2:4 │ val3:4 │ val4:4 │ val5:4 │
└────────────────┴────────┴────────┴────────┴────────┴────────┴────────┘
     8 bytes      + 6 × 4 = 24 bytes = 32 bytes total
```

**Space Efficiency:** 24/32 = **75%**

**Timestamp Calculation:**
```c
timestamp[i] = first_UTC + (i × sample_rate_ms)
```

**Detection:** `IS_TSD_SENSOR(csb)` returns true if `csb->sample_rate > 0`

### Event Data (EVT)

**Used for:** Irregular events with individual timestamps

**Sector Format (32 bytes):**
```
┌────────┬──────────────┬────────┬──────────────┬─────────┐
│ val0:4 │ UTC_0:8      │ val1:4 │ UTC_1:8      │ pad:8   │
└────────┴──────────────┴────────┴──────────────┴─────────┘
  12 bytes (pair 0)  + 12 bytes (pair 1)  + 8 padding = 32 bytes
```

**Capacity:** 2 events per sector

**Detection:** `IS_TSD_SENSOR(csb)` returns false if `csb->sample_rate == 0`

---

## Operation Flows

### Write Path (TSD)

```c
imx_result_t imx_write_tsd(upload_source, csb, csd, value)
```

1. **Get current write sector:**
   - If `ram_end_sector == NULL_SECTOR_ID`: Allocate first sector
   - Otherwise: Use existing `ram_end_sector`

2. **Check space in current sector:**
   - TSD can hold 6 values per sector
   - If `ram_write_offset < 6`: Space available
   - Otherwise: Allocate new sector and link to chain

3. **Write value:**
   - If first value in sector: Set `first_UTC` timestamp
   - Write value to `sector_data[8 + (offset × 4)]`
   - Increment `ram_write_offset`

4. **Update mmcb:**
   - Increment `total_records_written`
   - Update `last_sample_time_ms`

5. **Check memory pressure (Linux):**
   - If `free_sectors < threshold`: Trigger spooling

### Write Path (EVT)

```c
imx_result_t imx_write_evt(upload_source, csb, csd, value, utc_time_ms)
```

Similar to TSD but:
- Each event has individual timestamp
- 2 events per sector (12 bytes each)
- Format: `[value:4][UTC:8]` × 2 + 8 bytes padding

### Read Path (Bulk)

```c
imx_result_t imx_read_bulk_samples(upload_source, csb, csd, array, ...)
```

1. **Check data available:**
   - Calculate: `new_count = total_records - pending_count`
   - If 0: Return `IMX_NO_DATA`

2. **Start from read position:**
   - Sector: `mmcb.ram_start_sector`
   - Offset: `mmcb.ram_read_offset`

3. **Read loop:**
   - Extract values from sectors
   - Calculate timestamps (TSD) or copy timestamps (EVT)
   - Fill output array
   - Walk chain using `get_next_sector_in_chain()`

4. **Mark as pending:**
   - Set `pending_start_sector` and `pending_start_offset`
   - Set `pending_count = records_read`

5. **Advance read position:**
   - Update `ram_read_offset`
   - If sector exhausted: Move to next sector in chain

### ACK Handling (Erase Pending)

```c
imx_result_t imx_erase_all_pending(upload_source, csb, csd)
```

1. **Get pending info:**
   - Start: `pending_by_source[upload_source].pending_start_sector`
   - Count: `pending_by_source[upload_source].pending_count`

2. **Erase data:**
   - Walk chain from start
   - Free completely empty sectors
   - Update `ram_start_sector` to first non-empty

3. **Clear pending:**
   - Set `pending_count = 0`
   - Reset `pending_start_sector`

---

## Platform Differences

### Linux Platform

- **Pool Size:** 64KB (2048 sectors)
- **Sector ID Type:** `uint32_t`
- **NULL_SECTOR_ID:** `0xFFFFFFFF`
- **Thread Safety:** pthread mutexes
- **Disk Spooling:** Enabled (tiered storage)
- **UTC:** Available immediately, converted later if needed

**Directory Structure:**
```
/tmp/mm2/
├── gateway/
│   ├── sensor_12345/
│   │   ├── 00000001.dat
│   │   └── 00000002.dat
│   └── sensor_67890/
├── ble/
├── can/
└── corrupted/  # Corrupted files moved here
```

### STM32 Platform

- **Pool Size:** 4KB (128 sectors)
- **Sector ID Type:** `uint16_t`
- **NULL_SECTOR_ID:** `0xFFFF`
- **Thread Safety:** Interrupt disabling
- **Disk Spooling:** Not available
- **UTC Blocking:** Waits until UTC time established
- **RAM Exhaustion:** Discards oldest non-pending data

---

## Error Handling & Recovery

### Startup Recovery

```c
imx_result_t imx_recover_sensor_disk_data(upload_source, csb, csd)
```

**Process:**
1. Scan `/tmp/mm2/{upload_source}/sensor_{id}/` directory
2. Find all `*.dat` files
3. Read file headers to validate
4. Load data back into RAM sectors
5. Rebuild sector chains
6. Update mmcb with recovered state

**File Format:**
```
[Header: 32 bytes]
  - Magic: 0x4D4D3256 ("MM2V")
  - Version: 0x0208
  - Sensor ID: uint32_t
  - Upload Source: uint8_t
  - Sector Type: uint8_t
  - Record Count: uint32_t
  - First UTC: uint64_t
  - Checksum: uint32_t
[Data: variable length]
```

### Corruption Detection

**Chain Validation:**
```c
imx_result_t validate_chain_integrity(SECTOR_ID_TYPE start_sector)
```

Checks for:
- Circular chains (loop detection)
- Invalid sector IDs (>= total_sectors)
- Orphaned sectors
- Inconsistent ownership (sensor_id mismatches)

### Power-Down Handling

**Graceful Shutdown:**
```c
imx_result_t imx_memory_manager_shutdown(upload_source, csb, csd, timeout_ms)
```

**Emergency Power Loss:**
```c
void imx_power_event_detected(void)
```

**Power Abort Recovery:**
```c
imx_result_t handle_power_abort_recovery(void)
```

Handles cases where power-down was initiated but aborted (power restored).

---

## Critical Debug Points

### 1. Sector Allocation Failures

**Symptom:** `allocation_failures` counter increasing

**Causes:**
- RAM pool exhausted
- Disk spooling not keeping up (Linux)
- Too many active sensors
- Data not being acknowledged/erased

**Debug:**
```bash
# Enable MM2 debugging
debug DEBUGS_FOR_MEMORY_MANAGER

# Check pool status
ms stats
```

### 2. Chain Corruption

**Symptoms:**
- Circular chains (infinite loops)
- Invalid sector IDs in chain
- Sector count mismatches

**Common Causes:**
- Race conditions (missing mutex locks)
- Double-free of sectors
- Incorrect chain linking

**Debug Points:**
- `mm2_pool.c`: `allocate_sector_for_sensor()` - check free_list corruption
- `mm2_pool.c`: `free_sector()` - validate sector_id before freeing
- `mm2_read.c`: Chain walking loops - add loop counters

### 3. Read/Write Offset Issues

**Symptoms:**
- Data skipped or duplicated
- Read returns wrong number of records
- Pending count mismatches

**Debug Points:**
- `mm2_write.c`: Offset increment logic
- `mm2_read.c`: Offset advancement after reads
- ACK handling: Offset reset after erase

### 4. Disk Spooling Issues (Linux)

**Symptoms:**
- Files not created
- Corrupted file headers
- Recovery fails on restart

**Debug Points:**
- `mm2_disk_spooling.c`: File creation permissions
- `mm2_disk_reading.c`: Header validation
- `mm2_file_management.c`: Directory structure

### 5. Pending Data Tracking

**Symptoms:**
- Data uploaded multiple times
- Data lost after ACK
- Pending count incorrect

**Debug Points:**
- `mm2_read.c`: `mark_data_as_pending()` - verify counts
- `mm2_write.c`: `clear_pending_data()` - verify erasure
- Multi-source: Check correct `upload_source` index

### 6. Thread Safety Issues (Linux)

**Race Condition Hotspots:**
- Pool allocation/deallocation without locks
- Chain table modifications
- mmcb field updates
- Disk file operations

**Validation:**
```c
// Add assertions
assert(pthread_mutex_lock(&pool_lock) == 0);
// ... critical section ...
assert(pthread_mutex_unlock(&pool_lock) == 0);
```

### 7. Sensor ID Collisions

**Multi-Source Context:**
- Sensor ID 5 in IMX_UPLOAD_GATEWAY ≠ Sensor ID 5 in IMX_UPLOAD_BLE_DEVICE
- Always use `(upload_source, sensor_id)` pair
- Never assume global uniqueness

---

## Debug Macros and Logging

### Enable MM2 Debugging

```c
#define PRINT_DEBUGS_FOR_MEMORY_MANAGER 1
```

**CLI Commands:**
```bash
debug DEBUGS_FOR_MEMORY_MANAGER
```

### Logging Levels

```
[MM2]          - Normal operations
[MM2-INFO]     - Informational messages
[MM2-WARNING]  - Warning conditions
[MM2-ERROR]    - Error conditions
[MM2-RECOVERY] - Recovery operations
```

### Key Statistics

```c
mm2_stats_t stats;
imx_get_memory_stats(&stats);

printf("Total sectors: %u\n", stats.total_sectors);
printf("Free sectors: %u\n", stats.free_sectors);
printf("Usage: %u%%\n", ((stats.total_sectors - stats.free_sectors) * 100) / stats.total_sectors);
printf("Allocations: %llu\n", stats.total_allocations);
printf("Failures: %llu\n", stats.allocation_failures);
printf("Efficiency: %u%%\n", stats.space_efficiency_percent);
```

---

## Common Pitfalls

1. **Assuming Sequential Allocation:**
   - ❌ `sector_count = end_sector - start_sector + 1`
   - ✅ `sector_count = count_sectors_in_chain(start_sector)`

2. **Ignoring Platform Differences:**
   - Check `#ifdef LINUX_PLATFORM` vs STM32
   - Sector ID type differs (32-bit vs 16-bit)

3. **Missing Upload Source Context:**
   - Always pass `upload_source` to MM2 APIs
   - Pending data is per-source, not global

4. **Modifying Chain Without Locks:**
   - Always acquire `pool_lock` (Linux)
   - Always disable interrupts (STM32)

5. **Forgetting to Check Return Values:**
   - `allocate_sector_for_sensor()` can return `NULL_SECTOR_ID`
   - Always validate before using

---

## Glossary

- **TSD:** Time Series Data - regular sampled data with calculated timestamps
- **EVT:** Event Data - irregular data with individual timestamps
- **Sector:** 32-byte memory unit containing only data (no metadata)
- **Chain:** Linked sequence of sectors managed via separate chain table
- **Upload Source:** Context for data routing (GATEWAY, BLE, CAN, etc.)
- **Spooling:** Writing RAM sectors to disk when memory fills
- **Pending:** Data marked for upload, awaiting ACK
- **mmcb:** Memory Manager Control Block (per-sensor state)

---

## References

- **Source Files:** `/home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl/`
- **API Documentation:** `mm2_api.h` and `docs/MM2_API_GUIDE.md`
- **Configuration:** `mm2_core.h` - adjust pool size and constants
- **Testing:** `memory_test_framework.c` and `memory_test_suites.c`

---

**End of Document**
