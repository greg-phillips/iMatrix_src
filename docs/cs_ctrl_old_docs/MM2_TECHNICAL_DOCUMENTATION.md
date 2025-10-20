# iMatrix Memory Manager v2.8 (MM2) - Complete Technical Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Core Data Structures](#core-data-structures)
3. [Public API Functions](#public-api-functions)
4. [Internal Implementation Functions](#internal-implementation-functions)
5. [System Workflow and State Machines](#system-workflow-and-state-machines)
6. [Platform-Specific Implementations](#platform-specific-implementations)
7. [Disk Spooling Subsystem](#disk-spooling-subsystem)
8. [Power Management](#power-management)
9. [Compatibility Layer](#compatibility-layer)
10. [Structural Issues and Recommendations](#structural-issues-and-recommendations)

---

## 1. System Overview

### Architecture
MM2 is a tiered memory management system achieving 75% space efficiency through separation of data and metadata. The system manages up to 500 concurrent sensors with both Time Series Data (TSD) and Event (EVT) storage patterns.

### Key Design Principles
- **Space Efficiency**: 75% for TSD data through chain table separation
- **Platform Aware**: Different behaviors for Linux vs STM32
- **Upload Source Segregation**: Independent tracking per upload destination
- **Power Safety**: Atomic operations with immediate disk sync
- **5ms Timing Constraint**: Phase-based processing for real-time compliance

### File Organization
```
iMatrix/cs_ctrl/
├── Core Headers
│   ├── mm2_api.h          - Public API definitions
│   ├── mm2_core.h         - Core data structures
│   ├── mm2_internal.h     - Internal function declarations
│   └── mm2_disk.h         - Disk spooling definitions
├── Core Implementation
│   ├── mm2_api.c          - Public API implementation
│   ├── mm2_pool.c         - Memory pool management
│   ├── mm2_write.c        - Write operations
│   └── mm2_read.c         - Read operations
├── Disk Operations (Linux)
│   ├── mm2_disk_spooling.c    - Normal spooling state machine
│   ├── mm2_disk_helpers.c     - File management utilities
│   └── mm2_disk_reading.c     - Disk read operations
├── Special Operations
│   ├── mm2_power.c            - Power management
│   ├── mm2_power_abort.c      - Power abort recovery
│   ├── mm2_startup_recovery.c - Startup disk recovery
│   └── mm2_file_management.c  - File lifecycle management
├── Platform Specific
│   └── mm2_stm32.c           - STM32-specific operations
├── Compatibility
│   ├── mm2_compatibility.c   - Legacy API wrappers
│   └── memory_manager.h      - Legacy header definitions
└── Testing
    ├── memory_test_framework.c/h
    └── memory_test_suites.c/h
```

---

## 2. Core Data Structures

### 2.1 Sector Structure (mm2_core.h)

```c
/**
 * @brief Raw 32-byte sector (NO header, NO next pointer)
 * CRITICAL: Contains ONLY data - no metadata
 */
typedef struct {
    uint8_t data[SECTOR_SIZE];  // 32 bytes of raw data only
} memory_sector_t;
```

### 2.2 Chain Management Entry

```c
/**
 * @brief Separate chain table entry (enables 75% efficiency)
 * Size: 32 bytes on 64-bit, 24 bytes on 32-bit
 */
typedef struct {
    SECTOR_ID_TYPE sector_id;          // This sector ID
    SECTOR_ID_TYPE next_sector_id;     // Next in chain (NULL_SECTOR_ID = end)
    uint32_t sensor_id;                // Owner sensor (0-499)
    uint8_t sector_type;               // SECTOR_TYPE_TSD or SECTOR_TYPE_EVT
    uint8_t reserved1;
    uint16_t reserved2;
    uint64_t creation_time_ms;         // Allocation timestamp

    // Status flags (bitfields for portability)
    unsigned int in_use : 1;           // Sector allocated
    unsigned int spooled_to_disk : 1;  // Written to disk (Linux)
    unsigned int pending_ack : 1;      // Contains pending upload data
    unsigned int reserved_flags : 29;  // Padding to 32-bit
} sector_chain_entry_t;
```

### 2.3 Global Memory Pool

```c
/**
 * @brief Global memory pool with separate chain management
 */
typedef struct {
    memory_sector_t* sectors;           // Raw sector storage array
    sector_chain_entry_t* chain_table;  // Parallel chain management array
    uint32_t total_sectors;            // Total sectors allocated
    uint32_t free_sectors;             // Currently free sectors

    SECTOR_ID_TYPE* free_list;         // Stack of free sector IDs
    uint32_t free_list_head;           // Top of free list stack

    #ifdef LINUX_PLATFORM
    pthread_mutex_t pool_lock;         // Thread safety
    #endif

    // Statistics
    uint64_t total_allocations;
    uint64_t total_deallocations;
    uint64_t allocation_failures;
} global_memory_pool_t;
```

### 2.4 Memory Management Control Block (MMCB)

```c
/**
 * @brief Per-sensor memory management control block
 * Embedded directly in control_sensor_data_t
 */
typedef struct {
    // RAM chain management
    SECTOR_ID_TYPE ram_start_sector_id;    // First sector in chain
    SECTOR_ID_TYPE ram_end_sector_id;      // Last sector (for append)
    uint16_t ram_read_sector_offset;       // Read position in bytes
    uint16_t ram_write_sector_offset;      // Write position in bytes

    // Per-upload-source pending tracking
    struct {
        uint32_t pending_count;             // Records pending upload
        SECTOR_ID_TYPE pending_start_sector;// First pending sector
        uint16_t pending_start_offset;      // Offset in first sector
    } pending_by_source[UPLOAD_SOURCE_MAX];

    #ifdef LINUX_PLATFORM
    pthread_mutex_t sensor_lock;           // Per-sensor thread safety

    // Per-upload-source disk spooling
    struct {
        int active_spool_fd;                // Current write file descriptor
        uint64_t current_spool_file_size;    // Current file size
        char active_spool_filename[256];    // Current filename
        uint32_t next_sequence_number;      // Next file sequence

        // Spool file tracking
        spool_file_info_t spool_files[MAX_SPOOL_FILES_PER_SENSOR];
        uint32_t spool_file_count;

        // Disk reading state
        FILE* current_read_handle;
        uint32_t disk_reading_file_index;
        uint64_t disk_file_offset;
        uint32_t disk_record_index;
        uint32_t disk_records_in_sector;
        uint8_t disk_sector_buffer[SECTOR_SIZE];
        uint8_t disk_current_sector_type;
        unsigned int disk_reading_active : 1;
        unsigned int disk_exhausted : 1;

        // Spooling state machine
        normal_spool_state_t spool_state;

        // Statistics
        uint64_t total_disk_records;
        uint64_t bytes_written_to_disk;
    } per_source[IMX_UPLOAD_NO_SOURCES];

    // Emergency spooling
    char emergency_spool_filename[256];
    int emergency_spool_fd;
    uint64_t emergency_file_size;

    // UTC conversion state
    unsigned int utc_conversion_complete : 1;
    unsigned int utc_conversion_in_progress : 1;
    #endif

    // Power management
    unsigned int power_flush_complete : 1;
    uint32_t power_records_flushed;

    // Statistics
    uint64_t total_records;            // Total records in RAM
    uint64_t total_disk_records;       // Total records on disk
    uint64_t last_sample_time;         // Last write timestamp
    uint64_t total_disk_space_used;    // Total disk usage
} imx_mmcb_t;
```

### 2.5 Data Format Structures

```c
/**
 * @brief TSD data format (75% efficiency)
 * Total: 32 bytes, Data: 24 bytes
 */
// Sector layout:
// [first_utc:8][value_0:4][value_1:4][value_2:4][value_3:4][value_4:4][value_5:4]

/**
 * @brief EVT data pair (12 bytes)
 */
typedef struct __attribute__((packed)) {
    uint32_t value;         // Sensor value
    uint64_t utc_time_ms;   // Individual timestamp
} evt_data_pair_t;

// EVT Sector layout (2 pairs + padding):
// [pair_0:12][pair_1:12][padding:8]
```

### 2.6 Statistics Structures

```c
/**
 * @brief Memory manager statistics
 */
typedef struct {
    uint32_t total_sectors;
    uint32_t free_sectors;
    uint32_t active_sensors;
    uint64_t total_allocations;
    uint64_t allocation_failures;
    uint64_t chain_operations;
    uint32_t space_efficiency_percent;  // Should be 75% for TSD
} mm2_stats_t;

/**
 * @brief Detailed sensor state
 */
typedef struct {
    uint32_t sensor_id;
    unsigned int active : 1;
    SECTOR_ID_TYPE ram_start_sector;
    SECTOR_ID_TYPE ram_end_sector;
    uint16_t ram_read_offset;
    uint16_t ram_write_offset;
    uint64_t total_records;
    uint64_t last_sample_time;
    uint32_t pending_counts[UPLOAD_SOURCE_MAX];
} mm2_sensor_state_t;
```

### 2.7 Platform-Specific Types

```c
// Platform-aware sector ID types
#ifdef LINUX_PLATFORM
    typedef uint32_t SECTOR_ID_TYPE;       // 32-bit for Linux
    #define NULL_SECTOR_ID 0xFFFFFFFF
    #define SECTOR_SIZE 32
    #define MEMORY_POOL_SIZE (64 * 1024)   // 64KB
#else
    typedef uint16_t SECTOR_ID_TYPE;       // 16-bit for STM32
    #define NULL_SECTOR_ID 0xFFFF
    #define SECTOR_SIZE 32
    #define MEMORY_POOL_SIZE (4 * 1024)    // 4KB
#endif
```

---

## 3. Public API Functions

### 3.1 Initialization and Shutdown

```c
/**
 * @brief Initialize memory manager
 * @param pool_size Total memory pool size in bytes (0 for default)
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_memory_manager_init(uint32_t pool_size);

/**
 * @brief Shutdown memory manager with data preservation for single sensor
 * Main application must call this for each active sensor during shutdown
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block (contains sensor ID)
 * @param csd Sensor data block (contains mmcb)
 * @param timeout_ms Maximum time to spend preserving data (60000ms max)
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_memory_manager_shutdown(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    uint32_t timeout_ms);

/**
 * @brief Check if memory manager is ready for operations
 * STM32: Returns false until UTC time is established
 * Linux: Always returns true (UTC conversion happens later)
 * @return 1 if ready, 0 if not ready
 */
int imx_memory_manager_ready(void);
```

### 3.2 Sensor Management

```c
/**
 * @brief Configure sensor for TSD or EVT operation
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration (contains ID and sample_rate)
 * @param csd Sensor data block (contains mmcb)
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_configure_sensor(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

/**
 * @brief Activate sensor for data collection
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_activate_sensor(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

/**
 * @brief Deactivate sensor and flush remaining data
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_deactivate_sensor(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);
```

### 3.3 Write Operations

```c
/**
 * @brief Write TSD (Time Series Data) record
 * Achieves 75% space efficiency
 * STM32: Blocks until UTC available
 * Linux: Writes immediately, UTC converted later
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @param value 32-bit sensor value
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_write_tsd(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value);

/**
 * @brief Write EVT (Event) record with individual timestamp
 * Each EVT record has its own timestamp for irregular events
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @param value 32-bit sensor value
 * @param utc_time_ms Individual timestamp for this event
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_write_evt(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value,
    imx_utc_time_ms_t utc_time_ms);
```

### 3.4 Read Operations

```c
/**
 * @brief Get count of new (non-pending) samples available for upload
 * Counts all records not currently marked as pending for upload
 * Includes both RAM and disk spooled data (Linux)
 * @param upload_source Upload source to check
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @return Count of available non-pending records
 */
uint32_t imx_get_new_sample_count(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

/**
 * @brief Read multiple samples in bulk into preallocated array
 * Reads up to requested_count records into provided array
 * Automatically marks read data as pending for this upload source
 * TSD: Timestamps are CALCULATED (first_utc + index * sample_rate)
 * EVT: Timestamps are COPIED (individual timestamps)
 * @param upload_source Upload source for pending tracking
 * @param csb Sensor configuration (contains sample_rate)
 * @param csd Sensor data (contains mmcb)
 * @param array Preallocated array for output data
 * @param array_size Total size of preallocated array
 * @param requested_count Number of records requested
 * @param filled_count [OUT] Actual number of records filled
 * @return IMX_SUCCESS if data available, IMX_NO_DATA if none
 */
imx_result_t imx_read_bulk_samples(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    tsd_evt_value_t* array,
    uint32_t array_size,
    uint32_t requested_count,
    uint16_t* filled_count);

/**
 * @brief Read next TSD/EVT record for upload (legacy compatibility)
 * Maintains compatibility with existing iMatrix upload system
 * @param upload_source Upload source
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @param data_out Output buffer for record data
 * @return IMX_SUCCESS with data, IMX_NO_DATA if no more data
 */
imx_result_t imx_read_next_tsd_evt(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    tsd_evt_data_t* data_out);
```

### 3.5 Upload Management

```c
/**
 * @brief Revert pending data for upload retry (NACK handling)
 * Resets read position to allow re-reading same data
 * Operation is idempotent - safe to call multiple times
 * @param upload_source Upload source that failed
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_revert_all_pending(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

/**
 * @brief Mark uploaded data as acknowledged (ACK handling)
 * Erases pending data that has been successfully uploaded
 * @param upload_source Upload source
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @param record_count Number of records to mark as acknowledged
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t imx_erase_all_pending(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    uint32_t record_count);
```

### 3.6 Diagnostics and Maintenance

```c
/**
 * @brief Validate sector chain integrity for specific sensor
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @return IMX_SUCCESS if valid, error code if corruption detected
 */
imx_result_t imx_validate_sector_chains(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

/**
 * @brief Get memory manager statistics
 * @param stats_out Output buffer for statistics
 * @return IMX_SUCCESS on success
 */
imx_result_t imx_get_memory_stats(mm2_stats_t* stats_out);

/**
 * @brief Get detailed sensor state
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @param state_out Output buffer for sensor state
 * @return IMX_SUCCESS on success
 */
imx_result_t imx_get_sensor_state(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    mm2_sensor_state_t* state_out);

/**
 * @brief Force garbage collection for specific sensor (dev/test only)
 * Main application must call this for each sensor when needed
 * @param upload_source Upload source for directory separation
 * @param csb Sensor configuration block
 * @param csd Sensor data block
 * @return Number of sectors freed
 */
uint32_t imx_force_garbage_collection(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);
```

### 3.7 Time Management

```c
/**
 * @brief Set UTC time availability (STM32 only)
 * @param utc_available 1 if UTC is available, 0 if not
 * @return IMX_SUCCESS on success
 */
imx_result_t imx_set_utc_available(int utc_available);

/**
 * @brief Get current UTC time
 * @return Current UTC time in milliseconds, or 0 if not available
 */
imx_utc_time_ms_t mm2_get_utc_time_ms(void);

/**
 * @brief Get system time (platform-specific)
 * @return System time in platform-specific units
 */
imx_time_t imx_time_get_system_time(void);
```

### 3.8 Process Management

```c
/**
 * @brief Main memory manager processing function (called periodically)
 * CRITICAL: Must complete in <5ms chunks to avoid blocking
 * Handles time rollover, UTC conversion, disk spooling, and cleanup
 * @param current_time Current system time
 * @return IMX_SUCCESS on success, error code on failure
 */
imx_result_t process_memory_manager(imx_time_t current_time);

/**
 * @brief Power event detected - initiate emergency shutdown
 * Called when power loss is detected
 */
void imx_power_event_detected(void);

/**
 * @brief Handle power-down abort recovery
 * Called when power-down event is cancelled mid-process
 * @return IMX_SUCCESS on successful recovery, error code on failure
 */
imx_result_t handle_power_abort_recovery(void);

/**
 * @brief Get power abort recovery statistics
 * @param total_aborts Output for total abort events handled
 * @param files_deleted Output for total emergency files deleted
 */
void get_power_abort_statistics(uint32_t* total_aborts, uint32_t* files_deleted);
```

---

## 4. Internal Implementation Functions

### 4.1 Memory Pool Management (mm2_pool.c)

```c
// Initialization and cleanup
imx_result_t init_memory_pool(uint32_t pool_size);
void cleanup_memory_pool(void);

// Sector allocation and deallocation
SECTOR_ID_TYPE allocate_sector_for_sensor(uint32_t sensor_id, uint8_t sector_type);
imx_result_t free_sector(SECTOR_ID_TYPE sector_id);

// Chain management
SECTOR_ID_TYPE get_next_sector_in_chain(SECTOR_ID_TYPE sector_id);
void set_next_sector_in_chain(SECTOR_ID_TYPE sector_id, SECTOR_ID_TYPE next_sector_id);
imx_result_t link_sector_to_chain(SECTOR_ID_TYPE chain_end_sector_id, SECTOR_ID_TYPE new_sector_id);
uint32_t count_sectors_in_chain(SECTOR_ID_TYPE start_sector_id);
imx_result_t validate_chain_integrity(SECTOR_ID_TYPE start_sector_id);

// Sensor management
control_sensor_data_t* get_sensor_data(uint32_t sensor_id);
uint32_t get_active_sensor_count(void);
void increment_active_sensor_count(void);
void decrement_active_sensor_count(void);
uint32_t compute_active_sensor_count(void);
uint32_t get_sensor_id_from_csd(const control_sensor_data_t* csd);

// Statistics
uint32_t calculate_space_efficiency(void);
imx_result_t generate_memory_stats(mm2_stats_t* stats_out);
```

### 4.2 Write Operations (mm2_write.c)

```c
// Sensor control block management
imx_result_t init_sensor_control_block(control_sensor_data_t* csd);
imx_result_t cleanup_sensor_control_block(control_sensor_data_t* csd);

// Low-level sector write operations
imx_result_t write_tsd_value_to_sector(uint8_t* sector_data, uint32_t value_index, uint32_t value);
imx_result_t write_evt_pair_to_sector(uint8_t* sector_data, uint32_t pair_index,
                                     uint32_t value, uint64_t utc_time_ms);

// Pending data management
imx_result_t mark_data_as_pending(control_sensor_data_t* csd,
                                 imatrix_upload_source_t upload_source,
                                 SECTOR_ID_TYPE start_sector,
                                 uint16_t start_offset,
                                 uint32_t record_count);

imx_result_t clear_pending_data(control_sensor_data_t* csd,
                               imatrix_upload_source_t upload_source,
                               uint32_t record_count);
```

### 4.3 Read Operations (mm2_read.c)

```c
// Low-level sector read operations
imx_result_t read_tsd_value_from_sector(const uint8_t* sector_data, uint32_t value_index,
                                       uint32_t* value_out);
imx_result_t read_evt_pair_from_sector(const uint8_t* sector_data, uint32_t pair_index,
                                      uint32_t* value_out, uint64_t* utc_time_out);

// Static helper functions
static imx_result_t read_tsd_from_sector(const memory_sector_t* sector,
                                        const sector_chain_entry_t* entry,
                                        imx_control_sensor_block_t* csb,
                                        uint16_t offset,
                                        tsd_evt_data_t* data_out);

static imx_result_t read_evt_from_sector(const memory_sector_t* sector,
                                        const sector_chain_entry_t* entry,
                                        imx_control_sensor_block_t* csb,
                                        uint16_t offset,
                                        tsd_evt_data_t* data_out);

static int is_sector_completely_erased(SECTOR_ID_TYPE sector_id);
static imx_result_t free_sector_and_update_chain(control_sensor_data_t* csd,
                                                SECTOR_ID_TYPE sector_id);
```

### 4.4 Time Management Functions

```c
imx_result_t init_time_management(void);
imx_result_t handle_time_rollover(imx_time_t current_time);
imx_utc_time_ms_t convert_system_time_to_utc(imx_time_t system_time);

// Inline helper functions
static inline uint64_t get_tsd_first_utc(const uint8_t* sector_data);
static inline void set_tsd_first_utc(uint8_t* sector_data, uint64_t utc_ms);
static inline uint32_t* get_tsd_values_array(uint8_t* sector_data);
static inline evt_data_pair_t* get_evt_pairs_array(uint8_t* sector_data);
static inline sector_chain_entry_t* get_sector_chain_entry(SECTOR_ID_TYPE sector_id);
```

### 4.5 Platform-Specific Functions

#### STM32-Specific (mm2_stm32.c)
```c
imx_result_t handle_stm32_ram_full(uint32_t requesting_sensor_id);
imx_result_t find_oldest_non_pending_sector(SECTOR_ID_TYPE* oldest_sector_out,
                                           uint32_t* owner_sensor_out);
int is_sector_safe_to_discard(uint32_t sensor_id, SECTOR_ID_TYPE sector_id);
```

#### Linux-Specific (various files)
```c
// Emergency disk operations
imx_result_t emergency_write_sector_to_disk(control_sensor_data_t* csd,
                                           const memory_sector_t* sector,
                                           SECTOR_ID_TYPE sector_id);

// Normal disk spooling
uint32_t spool_sectors_to_disk(imx_control_sensor_block_t* csb,
                               control_sensor_data_t* csd,
                               imatrix_upload_source_t upload_source,
                               uint32_t sectors_to_spool);

uint32_t read_sectors_from_disk(imx_control_sensor_block_t* csb,
                                control_sensor_data_t* csd,
                                imatrix_upload_source_t upload_source,
                                uint32_t sectors_to_read);

imx_result_t perform_batch_utc_conversion(imx_control_sensor_block_t* csb,
                                         control_sensor_data_t* csd,
                                         imatrix_upload_source_t upload_source);
```

---

## 5. System Workflow and State Machines

### 5.1 Write Operation Flow

```
Application Request
    ↓
imx_write_tsd/evt()
    ↓
Thread Lock (Linux)
    ↓
Check Shutdown State → [Reject if shutting down]
    ↓
Check UTC (STM32) → [Block until available]
    ↓
Check Current Sector Space
    ↓
    ├─ Space Available → Write to current sector
    │                    Update offset
    │                    Update statistics
    │
    └─ Sector Full → Allocate new sector
                     Link to chain
                     Initialize sector
                     Write data
                     Update pointers
    ↓
Thread Unlock (Linux)
    ↓
Return Status
```

### 5.2 Read Operation Flow

```
Application Request
    ↓
imx_read_bulk_samples()
    ↓
Thread Lock (Linux)
    ↓
Save Pending Start Position
    ↓
Loop for requested_count:
    ↓
    ├─ Check Disk First (Linux)
    │   ├─ Data Available → Read from disk
    │   └─ Disk Exhausted → Fall through to RAM
    │
    └─ Read from RAM Chain
        ├─ Find valid sector
        ├─ Check sector type (TSD/EVT)
        ├─ Calculate timestamp
        │   ├─ TSD: first_utc + (index * sample_rate)
        │   └─ EVT: Use stored timestamp
        ├─ Copy to output array
        └─ Update read position
    ↓
Mark Data as Pending
    ↓
Thread Unlock (Linux)
    ↓
Return Data
```

### 5.3 Normal Disk Spooling State Machine (Linux)

```
States:
┌──────────────┐
│     IDLE     │ ← Memory pressure < 80%
└──────┬───────┘
       │ Memory pressure ≥ 80%
       ↓
┌──────────────┐
│  SELECTING   │ → Select up to 10 sectors
└──────┬───────┘   Skip pending/spooled
       ↓
┌──────────────┐
│   WRITING    │ → Write up to 5 sectors
└──────┬───────┘   Use writev() for atomic
       ↓
┌──────────────┐
│  VERIFYING   │ → Read back and check CRC
└──────┬───────┘
       ↓
┌──────────────┐
│   CLEANUP    │ → Free RAM sectors
└──────┬───────┘   Update chain table
       ↓
   Back to IDLE

Error Handling:
- Any state → ERROR (3 consecutive failures)
- ERROR → IDLE (after reset)
- Watchdog: 100 cycles max per state
```

### 5.4 Emergency Shutdown Flow

```
Power Event Detected
    ↓
imx_power_event_detected()
    ↓
Set Global Flags
    ↓
Main App Iterates Sensors:
    ↓
    For Each Active Sensor:
        ↓
        imx_memory_manager_shutdown(sensor)
            ↓
            Lock Sensor
            ↓
            Open Emergency File
            ↓
            While (sectors && time < deadline):
                ├─ Create Header (magic=0xDEADBEEF)
                ├─ Calculate Checksum
                ├─ writev(header + sector)
                ├─ fsync() immediately
                └─ Update statistics
            ↓
            Close File
            ↓
            Unlock Sensor
```

### 5.5 Power Abort Recovery Flow

```
process_memory_manager() called
    ↓
Check: emergency_mode && !imx_is_power_down_pending()
    ↓
Abort Detected!
    ↓
handle_power_abort_recovery()
    ↓
    For Each Sensor:
        ↓
        Check Emergency Files
        ↓
        ├─ .tmp files → Delete
        ├─ .partial files → Validate and recover
        └─ .complete files → Move to normal spool
    ↓
Reset Power State
    ↓
Resume Normal Operation
```

---

## 6. Platform-Specific Implementations

### 6.1 Linux Platform Features

```c
// Constants
#define SECTOR_ID_TYPE uint32_t
#define NULL_SECTOR_ID 0xFFFFFFFF
#define MEMORY_POOL_SIZE (64 * 1024)  // 64KB

// Features
- Disk spooling at 80% memory pressure
- Thread safety with pthread mutexes
- File rotation at 64KB
- 256MB total space limit
- Emergency and normal spooling modes
- Batch UTC conversion
- Power abort recovery

// Directory Structure
/tmp/mm2/                           // Test environment
├── telemetry/
│   └── sensor_XXX_seq_NNN.spool
├── diagnostics/
│   └── sensor_XXX_seq_NNN.spool
├── gateway/
├── hosted_device/
├── ble_device/
└── corrupted/                     // Quarantine directory

/usr/qk/etc/sv/{APP_NAME}/history/  // Production environment
└── [same structure]
```

### 6.2 STM32 Platform Features

```c
// Constants
#define SECTOR_ID_TYPE uint16_t
#define NULL_SECTOR_ID 0xFFFF
#define MEMORY_POOL_SIZE (4 * 1024)   // 4KB

// Features
- RAM-only operation (no disk)
- Blocks writes until UTC established
- Discards oldest non-pending data when full
- Single-threaded (no mutex needed)
- Power-optimized operations
- Smaller data types for memory efficiency
```

---

## 7. Disk Spooling Subsystem

### 7.1 Disk Sector Format

```c
/**
 * Normal disk sector header (40 bytes)
 */
typedef struct __attribute__((packed)) {
    uint32_t magic;                    // 0xDEAD5EC7
    uint8_t sector_type;               // TSD or EVT
    uint8_t conversion_status;         // UTC converted?
    uint8_t format_version;            // Version 1
    uint8_t reserved;

    uint32_t sensor_id;                // Owner sensor
    uint32_t record_count;             // Records in sector

    uint64_t first_utc_ms;             // First timestamp
    uint64_t last_utc_ms;              // Last timestamp

    uint32_t data_size;                // Bytes following
    SECTOR_ID_TYPE original_sector_id; // Debug info
    uint32_t sector_crc;               // CRC32 of data
} disk_sector_header_t;

/**
 * Emergency sector header (24 bytes)
 */
struct emergency_sector_header {
    uint32_t magic;                    // 0xDEADBEEF
    SECTOR_ID_TYPE sector_id;
    uint8_t sector_type;
    uint8_t reserved1;
    uint16_t reserved2;
    uint64_t timestamp_ms;
    uint32_t checksum;
};
```

### 7.2 File Management Functions

```c
// File lifecycle
imx_result_t add_spool_file_to_tracking(control_sensor_data_t* csd,
                                       imatrix_upload_source_t upload_source,
                                       const char* filename,
                                       uint32_t sequence,
                                       int is_active);

imx_result_t rotate_spool_file(control_sensor_data_t* csd,
                              imatrix_upload_source_t upload_source);

imx_result_t delete_spool_file(control_sensor_data_t* csd,
                              imatrix_upload_source_t upload_source,
                              int file_index);

imx_result_t cleanup_fully_acked_files(control_sensor_data_t* csd,
                                       imatrix_upload_source_t upload_source);

// Space management
uint64_t calculate_total_spool_size(control_sensor_data_t* csd,
                                   imatrix_upload_source_t upload_source);

imx_result_t enforce_space_limit(control_sensor_data_t* csd,
                                imatrix_upload_source_t upload_source);

// Reading operations
imx_result_t read_record_from_disk(imatrix_upload_source_t upload_source,
                                   imx_control_sensor_block_t* csb,
                                   control_sensor_data_t* csd,
                                   tsd_evt_value_t* value_out);
```

---

## 8. Power Management

### 8.1 Power States

```c
typedef struct {
    unsigned int shutdown_requested : 1;
    unsigned int emergency_mode : 1;
    unsigned int data_preservation_mode : 1;
    unsigned int abort_detected : 1;
    unsigned int abort_recovery_needed : 1;
    unsigned int abort_recovery_complete : 1;
    unsigned int reserved_flags : 26;

    uint64_t shutdown_start_ms;
    uint64_t abort_detected_ms;
    uint32_t sensors_flushed;
    uint64_t records_preserved;
    uint64_t bytes_written_during_shutdown;
    uint32_t abort_count;
} power_management_state_t;
```

### 8.2 Power Management Functions

```c
// Shutdown operations
imx_result_t request_graceful_shutdown(uint32_t timeout_ms);  // DEPRECATED

imx_result_t flush_sensor_data_for_shutdown(imx_control_sensor_block_t* csb,
                                           control_sensor_data_t* csd,
                                           imatrix_upload_source_t upload_source,
                                           uint64_t deadline_ms);

int is_shutdown_in_progress(void);

// Utility functions
uint32_t calculate_sector_checksum(const uint8_t* sector_data);
int validate_sector_data(const uint8_t* sector_data, uint32_t expected_checksum);
```

---

## 9. Compatibility Layer

### 9.1 Legacy API Wrappers

```c
// Legacy write functions
void write_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry, uint32_t value, bool add_gps_location);

void write_tsd_evt_time(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                        uint16_t entry, uint32_t value, uint32_t utc_time);

// Legacy read functions
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value);

void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry);

// Legacy transaction functions
void revert_tsd_evt_pending_data(imx_control_sensor_block_t *csb,
                                 control_sensor_data_t *csd, uint16_t no_items);

void erase_tsd_evt_pending_data(imx_control_sensor_block_t *csb,
                                control_sensor_data_t *csd, uint16_t no_items);

// Raw sector operations (deprecated)
void read_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length);
void write_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length);

imx_memory_error_t read_rs_safe(platform_sector_t sector, uint16_t offset,
                                uint32_t *data, uint16_t length, uint16_t data_buffer_size);

imx_memory_error_t write_rs_safe(platform_sector_t sector, uint16_t offset,
                                 const uint32_t *data, uint16_t length, uint16_t data_buffer_size);
```

### 9.2 Global Variables for Compatibility

```c
#ifdef LINUX_PLATFORM
// Global mutex for backward compatibility
imx_mutex_t data_store_mutex = {
    .m = PTHREAD_MUTEX_INITIALIZER,
    .name = "data_store_mutex",
    .thread_id = 0
};
#endif
```

---

## 10. Structural Issues and Recommendations

### 10.1 Critical Issues

#### Issue 1: Sensor ID Calculation from Pointer Arithmetic
**Location**: `mm2_core.h:201`, `mm2_pool.c:646`
```c
// Current problematic approach:
#define GET_SENSOR_ID(csd) ((uint32_t)((csd) - g_sensor_array.sensors))
uint32_t get_sensor_id_from_csd(const control_sensor_data_t* csd) {
    ptrdiff_t offset = csd - g_sensor_array.sensors;
    return (uint32_t)offset;
}
```
**Problem**: Relies on pointer arithmetic which is fragile and assumes contiguous array storage.
**Recommendation**: Store sensor_id directly in control_sensor_data_t structure.

#### Issue 2: API Signature Inconsistency
**Location**: Throughout API
```c
// Most functions use this order:
imx_function(upload_source, csb, csd, ...)
// But some legacy functions use:
function(csb, csd, entry, ...)
```
**Problem**: Inconsistent parameter ordering makes API harder to use.
**Recommendation**: Standardize on upload_source as first parameter.

#### Issue 3: Process Control Delegation Issues
**Location**: `mm2_api.c:544-640`
```c
// Main app must now iterate all sensors for:
// - Disk spooling
// - UTC conversion
// - Garbage collection
// - Shutdown
```
**Problem**: Pushes too much responsibility to application layer.
**Recommendation**: Provide optional convenience functions that iterate sensors internally.

### 10.2 Design Limitations

#### Limitation 1: Fixed Sector Size
**Impact**: 32-byte sectors may be inefficient for some data patterns.
**Suggestion**: Consider variable sector sizes in future versions.

#### Limitation 2: No Compression Support
**Impact**: Missing opportunity for better space efficiency.
**Suggestion**: Add optional compression for cold data.

#### Limitation 3: Single Upload Source per Write
**Impact**: Cannot write same data to multiple destinations atomically.
**Suggestion**: Support multiple upload sources in single write operation.

### 10.3 Performance Concerns

#### Concern 1: Linear Chain Traversal
```c
while (current != NULL_SECTOR_ID) {
    // O(n) traversal for each operation
    current = get_next_sector_in_chain(current);
}
```
**Impact**: Performance degrades with chain length.
**Suggestion**: Add skip-list or index for faster traversal.

#### Concern 2: Mutex Granularity
```c
pthread_mutex_lock(&csd->mmcb.sensor_lock);
// Entire operation locked
pthread_mutex_unlock(&csd->mmcb.sensor_lock);
```
**Impact**: Reduced concurrency for multi-threaded applications.
**Suggestion**: Use reader-writer locks or finer-grained locking.

### 10.4 Maintenance Issues

#### Issue 1: Magic Numbers
```c
#define DISK_SECTOR_MAGIC    0xDEAD5EC7
#define EMERGENCY_SECTOR_MAGIC 0xDEADBEEF
```
**Problem**: Cute but unprofessional magic numbers.
**Recommendation**: Use more professional constants.

#### Issue 2: Incomplete Error Handling
```c
if (result != IMX_SUCCESS) {
    // Many places just return without cleanup
    return result;
}
```
**Problem**: Resource leaks on error paths.
**Recommendation**: Add cleanup labels and goto-based error handling.

#### Issue 3: Missing Function Documentation
Several internal functions lack proper Doxygen comments.
**Recommendation**: Complete documentation for all functions.

### 10.5 Security Considerations

#### Concern 1: No Data Encryption
**Impact**: Sensitive sensor data stored in plaintext.
**Recommendation**: Add optional encryption layer.

#### Concern 2: No Integrity Protection Beyond CRC
**Impact**: CRC32 is weak against intentional modification.
**Recommendation**: Consider cryptographic hashes for critical data.

#### Concern 3: Predictable File Names
```c
snprintf(filename, sizeof(filename), "sensor_%03u_seq_%06u.spool",
         sensor_id, sequence);
```
**Impact**: Predictable patterns may be exploitable.
**Recommendation**: Add randomization to file naming.

### 10.6 Recommendations Summary

**High Priority**:
1. Fix sensor ID pointer arithmetic dependency
2. Add proper error cleanup paths
3. Standardize API parameter ordering
4. Complete function documentation

**Medium Priority**:
1. Implement convenience iteration functions
2. Add reader-writer locks for better concurrency
3. Improve chain traversal performance
4. Add data encryption option

**Low Priority**:
1. Support variable sector sizes
2. Add compression support
3. Change magic number constants
4. Randomize file naming patterns

---

## Conclusion

The MM2 memory management system is a sophisticated, production-ready solution for embedded IoT devices. It successfully achieves its primary goal of 75% space efficiency while maintaining data integrity and supporting complex features like multi-source uploads, disk spooling, and power-safe operations.

The architecture shows careful consideration for embedded constraints, platform differences, and real-time requirements. While there are areas for improvement (particularly around sensor ID management and API consistency), the overall design is solid and well-suited for its intended use case.

The separation of concerns between data storage and metadata management is elegant and enables the high space efficiency. The platform-aware design allows the same codebase to run efficiently on both resource-constrained STM32 devices and more capable Linux systems.

Key strengths:
- Excellent space efficiency (75%)
- Robust power-loss handling
- Good platform abstraction
- Comprehensive error handling
- Well-structured codebase

Areas for improvement:
- API consistency
- Sensor ID management
- Documentation completeness
- Performance optimizations
- Security enhancements