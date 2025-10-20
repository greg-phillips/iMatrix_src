# Data Structure Refactoring: per_source_disk_state_s Migration

## Executive Summary

**Problem**: The `per_source_disk_state_s` structure is incorrectly nested within `imx_mmcb_t`, which is itself nested within `control_sensor_data_t`. This creates a per-sensor duplication of disk spooling state, resulting in massive memory waste (up to 25 sensors × N sources × large state structures).

**Solution**: Move `per_source_disk_state_s` array directly into `iMatrix_Control_Block_t` (icb_data_), making it a global device-level structure rather than per-sensor.

**Impact**: 191 code references across 10 files in the cs_ctrl directory require updates.

---

## 1. Current vs. Target Structure

### Current Structure (INCORRECT)

```
iMatrix_Control_Block_t (Global Device Control Block)
  └─ control_sensor_data_t i_sd[IMX_MAX_NO_SENSORS] (Per-sensor data)
       └─ imx_mmcb_t mmcb (MM2 memory control block)
            └─ per_source_disk_state_s per_source[IMX_UPLOAD_NO_SOURCES]  ← INCORRECTLY NESTED
                 ├─ char active_spool_filename[256]
                 ├─ int active_spool_fd
                 ├─ uint64_t current_spool_file_size
                 ├─ uint32_t next_sequence_number
                 ├─ spool_files[10] tracking array
                 ├─ spool_state (state machine)
                 ├─ FILE* current_read_handle
                 ├─ disk reading state
                 └─ statistics
```

**Memory Impact**: With 25 sensors and 4 upload sources, this creates:
- 25 × 4 = 100 instances of per_source_disk_state_s
- Each instance: ~3KB (256B filename + 10×256B files + buffers + state)
- Total waste: ~300KB of duplicated disk spooling state

### Target Structure (CORRECT)

```
iMatrix_Control_Block_t (Global Device Control Block)
  ├─ control_sensor_data_t i_sd[IMX_MAX_NO_SENSORS] (Per-sensor data)
  │    └─ imx_mmcb_t mmcb (MM2 memory control block - WITHOUT per_source)
  │         ├─ RAM sector tracking
  │         ├─ per-source pending tracking
  │         └─ statistics
  └─ per_source_disk_state_s per_source_disk[IMX_UPLOAD_NO_SOURCES]  ← CORRECTLY AT DEVICE LEVEL
       ├─ char active_spool_filename[256]
       ├─ int active_spool_fd
       ├─ uint64_t current_spool_file_size
       ├─ uint32_t next_sequence_number
       ├─ spool_files[10] tracking array
       ├─ spool_state (state machine)
       ├─ FILE* current_read_handle
       ├─ disk reading state
       └─ statistics
```

**Memory Savings**: Only IMX_UPLOAD_NO_SOURCES (typically 4) instances instead of 100.

---

## 2. Access Path Mapping Summary

| Current Path | New Path | Notes |
|:-------------|:---------|:------|
| `csd->mmcb.per_source[source].{field}` | `icb.per_source_disk[source].{field}` | Most common pattern (191 occurrences) |
| `csd->mmcb.per_source[source].spool_state.{field}` | `icb.per_source_disk[source].spool_state.{field}` | State machine access |
| `csd->mmcb.per_source[source].spool_files[i].{field}` | `icb.per_source_disk[source].spool_files[i].{field}` | File tracking array |
| `SPOOL_STATE(csd, src)` macro | `SPOOL_STATE_GLOBAL(src)` macro | Simplified macro (no csd needed) |

**Critical Insight**: All functions that access `per_source` must now include:
```c
extern iMatrix_Control_Block_t icb;
```

---

## 3. File-by-File Change List

### 3.1 Structure Definition Changes

#### File: `iMatrix/common.h` (lines 1212-1304)

**CHANGE 1: Remove per_source from imx_mmcb_t**

**OLD CODE** (lines 1227-1279):
```c
typedef struct imx_mmcb {
    /* RAM sector chain (using separate chain table) */
    platform_sector_t ram_start_sector_id;
    platform_sector_t ram_end_sector_id;
    uint16_t ram_read_sector_offset;
    uint16_t ram_write_sector_offset;

    /* Per-source pending tracking */
    struct {
        uint32_t pending_count;
        platform_sector_t pending_start_sector;
        uint16_t pending_start_offset;
    } pending_by_source[IMX_UPLOAD_NO_SOURCES];

    #ifdef LINUX_PLATFORM
    pthread_mutex_t sensor_lock;

    /* Per-source disk spooling state - REMOVE THIS ENTIRE SECTION */
    struct per_source_disk_state_s {
        /* ... entire 50-line structure definition ... */
    } per_source[IMX_UPLOAD_NO_SOURCES];    ← DELETE THIS ARRAY

    /* Total space usage across ALL sources */
    uint64_t total_disk_space_used;

    /* UTC conversion state */
    unsigned int utc_conversion_complete : 1;
    unsigned int utc_conversion_in_progress : 1;
    unsigned int reserved_utc_flags : 30;

    /* Emergency spooling file tracking */
    char emergency_spool_filename[256];
    int emergency_spool_fd;
    uint64_t emergency_file_size;
    #endif

    /* Power-down state */
    unsigned int power_flush_complete : 1;
    unsigned int reserved_power_flags : 31;
    uint32_t power_records_flushed;

    /* Statistics */
    uint64_t total_records;
    uint64_t total_disk_records;
    uint64_t last_sample_time;
} imx_mmcb_t;
```

**NEW CODE**:
```c
typedef struct imx_mmcb {
    /* RAM sector chain (using separate chain table) */
    platform_sector_t ram_start_sector_id;
    platform_sector_t ram_end_sector_id;
    uint16_t ram_read_sector_offset;
    uint16_t ram_write_sector_offset;

    /* Per-source pending tracking */
    struct {
        uint32_t pending_count;
        platform_sector_t pending_start_sector;
        uint16_t pending_start_offset;
    } pending_by_source[IMX_UPLOAD_NO_SOURCES];

    #ifdef LINUX_PLATFORM
    pthread_mutex_t sensor_lock;

    /* NOTE: per_source[] disk state moved to iMatrix_Control_Block_t */

    /* Total space usage across ALL sources (for 256MB limit enforcement) */
    uint64_t total_disk_space_used;

    /* UTC conversion state (applies to all sources for this sensor) */
    unsigned int utc_conversion_complete : 1;
    unsigned int utc_conversion_in_progress : 1;
    unsigned int reserved_utc_flags : 30;

    /* Emergency spooling file tracking (separate from normal source-specific files) */
    char emergency_spool_filename[256];
    int emergency_spool_fd;
    uint64_t emergency_file_size;
    #endif

    /* Power-down state */
    unsigned int power_flush_complete : 1;
    unsigned int reserved_power_flags : 31;
    uint32_t power_records_flushed;

    /* Statistics */
    uint64_t total_records;
    uint64_t total_disk_records;
    uint64_t last_sample_time;
} imx_mmcb_t;
```

**CHANGE 2: Define standalone per_source_disk_state_s structure**

Add BEFORE the imx_mmcb_t definition (around line 1205):

```c
#ifdef LINUX_PLATFORM
/**
 * @brief Disk spooling state per upload source (device-level, not per-sensor)
 *
 * This structure manages disk file operations, tracking, and state machines
 * for one upload source (gateway, BLE, CAN, etc.) globally across all sensors.
 *
 * NOTE: This structure was moved from imx_mmcb_t to iMatrix_Control_Block_t
 * to eliminate per-sensor duplication of disk spooling state.
 */
typedef struct per_source_disk_state_s {
    /* Active file state for this source */
    char active_spool_filename[256];
    int active_spool_fd;
    uint64_t current_spool_file_size;
    uint32_t next_sequence_number;

    /* Normal disk spooling state machine */
    struct {
        int current_state;
        uint32_t sectors_to_spool[10];
        uint32_t sectors_selected_count;
        uint32_t sectors_written_count;
        uint32_t sectors_verified_count;
        uint32_t sectors_freed_count;
        uint32_t consecutive_errors;
        uint32_t cycles_in_state;
    } spool_state;

    /* File tracking array (up to 10 files per source) */
    struct {
        char filename[256];
        uint32_t sequence_number;
        uint64_t file_size;
        uint64_t created_time;
        unsigned int active : 1;
        unsigned int readable : 1;
        unsigned int validated : 1;
        unsigned int reserved : 29;
    } spool_files[10];
    uint32_t spool_file_count;

    /* Disk reading state for upload */
    FILE* current_read_handle;
    uint32_t disk_reading_file_index;
    uint64_t disk_file_offset;
    uint32_t disk_record_index;
    uint32_t disk_records_in_sector;
    uint8_t disk_sector_buffer[512];
    uint8_t disk_current_sector_type;
    unsigned int disk_reading_active : 1;
    unsigned int disk_exhausted : 1;
    unsigned int reserved_disk_read_flags : 30;

    /* Statistics for this source */
    uint64_t total_disk_records;
    uint64_t bytes_written_to_disk;
} per_source_disk_state_t;
#endif
```

#### File: `iMatrix/device/icb_def.h` (line ~792, inside icb_data_ structure)

**CHANGE 3: Add per_source_disk array to iMatrix_Control_Block_t**

Find the icb_data_ structure definition (starts around line 531) and add BEFORE the `end_of_indexes` field (line 794):

**OLD CODE** (line 793-795):
```c
    uint32_t ota_images_ready_mask[((NO_KNOWN_BLE_DEVICES - 1) / 32) + 1];
    uint32_t ota_images_error_mask[((NO_KNOWN_BLE_DEVICES - 1) / 32) + 1];
    char ota_target_custom_image_version[OTA_VERSION_SIZE];


    uint16_t end_of_indexes;
```

**NEW CODE**:
```c
    uint32_t ota_images_ready_mask[((NO_KNOWN_BLE_DEVICES - 1) / 32) + 1];
    uint32_t ota_images_error_mask[((NO_KNOWN_BLE_DEVICES - 1) / 32) + 1];
    char ota_target_custom_image_version[OTA_VERSION_SIZE];

#ifdef LINUX_PLATFORM
    /**
     * @brief Global disk spooling state per upload source
     *
     * Moved from per-sensor (imx_mmcb_t) to device-level to eliminate duplication.
     * Each upload source (gateway, BLE, CAN) has ONE state structure shared across
     * all sensors, managing disk files and state machines globally.
     */
    per_source_disk_state_t per_source_disk[IMX_UPLOAD_NO_SOURCES];
#endif

    uint16_t end_of_indexes;
```

---

### 3.2 Code Reference Updates

All files in `iMatrix/cs_ctrl/` that access `csd->mmcb.per_source[]` must be updated.

#### File: `iMatrix/cs_ctrl/mm2_pool.c` (13 occurrences, lines 182-272)

**Function**: `init_control_sensor_memory_manager()` (lines 180-198)

**OLD CODE** (lines 182-197):
```c
            csd->mmcb.per_source[source].active_spool_fd = -1;
            csd->mmcb.per_source[source].current_spool_file_size = 0;
            csd->mmcb.per_source[source].active_spool_filename[0] = '\0';
            csd->mmcb.per_source[source].next_sequence_number = 0;
            csd->mmcb.per_source[source].spool_file_count = 0;
            csd->mmcb.per_source[source].current_read_handle = NULL;
            csd->mmcb.per_source[source].disk_reading_file_index = 0;
            csd->mmcb.per_source[source].disk_file_offset = 0;
            csd->mmcb.per_source[source].disk_record_index = 0;
            csd->mmcb.per_source[source].disk_records_in_sector = 0;
            csd->mmcb.per_source[source].disk_reading_active = 0;
            csd->mmcb.per_source[source].disk_exhausted = 0;
            csd->mmcb.per_source[source].total_disk_records = 0;
            csd->mmcb.per_source[source].bytes_written_to_disk = 0;
            memset(&csd->mmcb.per_source[source].spool_state, 0,
                   sizeof(csd->mmcb.per_source[source].spool_state));
```

**NEW CODE**:
```c
            icb.per_source_disk[source].active_spool_fd = -1;
            icb.per_source_disk[source].current_spool_file_size = 0;
            icb.per_source_disk[source].active_spool_filename[0] = '\0';
            icb.per_source_disk[source].next_sequence_number = 0;
            icb.per_source_disk[source].spool_file_count = 0;
            icb.per_source_disk[source].current_read_handle = NULL;
            icb.per_source_disk[source].disk_reading_file_index = 0;
            icb.per_source_disk[source].disk_file_offset = 0;
            icb.per_source_disk[source].disk_record_index = 0;
            icb.per_source_disk[source].disk_records_in_sector = 0;
            icb.per_source_disk[source].disk_reading_active = 0;
            icb.per_source_disk[source].disk_exhausted = 0;
            icb.per_source_disk[source].total_disk_records = 0;
            icb.per_source_disk[source].bytes_written_to_disk = 0;
            memset(&icb.per_source_disk[source].spool_state, 0,
                   sizeof(icb.per_source_disk[source].spool_state));
```

**Function**: `cleanup_control_sensor_memory_manager()` (lines 268-272)

**OLD CODE**:
```c
            if (csd->mmcb.per_source[source].active_spool_fd >= 0) {
                close(csd->mmcb.per_source[source].active_spool_fd);
            }
            if (csd->mmcb.per_source[source].current_read_handle) {
                fclose(csd->mmcb.per_source[source].current_read_handle);
            }
```

**NEW CODE**:
```c
            if (icb.per_source_disk[source].active_spool_fd >= 0) {
                close(icb.per_source_disk[source].active_spool_fd);
            }
            if (icb.per_source_disk[source].current_read_handle) {
                fclose(icb.per_source_disk[source].current_read_handle);
            }
```

---

#### File: `iMatrix/cs_ctrl/mm2_startup_recovery.c` (63 occurrences, lines 112-610)

**Function**: `discover_existing_spool_files()` (lines 149-209)

**Pattern**: All 37 references in this function follow the same replacement pattern.

**Example OLD CODE** (lines 149-199):
```c
    csd->mmcb.per_source[upload_source].spool_file_count = 0;
    // ... scan directory ...
    uint32_t file_idx = csd->mmcb.per_source[upload_source].spool_file_count;
    // ... parse filename ...
    strncpy(csd->mmcb.per_source[upload_source].spool_files[file_idx].filename,
            full_path, sizeof(csd->mmcb.per_source[upload_source].spool_files[file_idx].filename) - 1);
    csd->mmcb.per_source[upload_source].spool_files[file_idx].filename[
        sizeof(csd->mmcb.per_source[upload_source].spool_files[file_idx].filename) - 1] = '\0';
    csd->mmcb.per_source[upload_source].spool_files[file_idx].sequence_number = sequence;
    csd->mmcb.per_source[upload_source].spool_files[file_idx].file_size = st.st_size;
    csd->mmcb.per_source[upload_source].spool_files[file_idx].created_time = st.st_mtime * 1000;
    csd->mmcb.per_source[upload_source].spool_files[file_idx].readable = 0;
    csd->mmcb.per_source[upload_source].spool_files[file_idx].active = 0;
    csd->mmcb.per_source[upload_source].spool_files[file_idx].validated = 0;
    csd->mmcb.per_source[upload_source].spool_file_count++;
```

**Example NEW CODE**:
```c
    icb.per_source_disk[upload_source].spool_file_count = 0;
    // ... scan directory ...
    uint32_t file_idx = icb.per_source_disk[upload_source].spool_file_count;
    // ... parse filename ...
    strncpy(icb.per_source_disk[upload_source].spool_files[file_idx].filename,
            full_path, sizeof(icb.per_source_disk[upload_source].spool_files[file_idx].filename) - 1);
    icb.per_source_disk[upload_source].spool_files[file_idx].filename[
        sizeof(icb.per_source_disk[upload_source].spool_files[file_idx].filename) - 1] = '\0';
    icb.per_source_disk[upload_source].spool_files[file_idx].sequence_number = sequence;
    icb.per_source_disk[upload_source].spool_files[file_idx].file_size = st.st_size;
    icb.per_source_disk[upload_source].spool_files[file_idx].created_time = st.st_mtime * 1000;
    icb.per_source_disk[upload_source].spool_files[file_idx].readable = 0;
    icb.per_source_disk[upload_source].spool_files[file_idx].active = 0;
    icb.per_source_disk[upload_source].spool_files[file_idx].validated = 0;
    icb.per_source_disk[upload_source].spool_file_count++;
```

**REPLACEMENT RULE**: Perform global search-and-replace in this file:
- Find: `csd->mmcb\.per_source\[upload_source\]\.`
- Replace: `icb.per_source_disk[upload_source].`
- Count: 63 replacements

---

#### File: `iMatrix/cs_ctrl/mm2_disk_spooling.c` (85 occurrences, lines 81-707)

**CHANGE 1: Update SPOOL_STATE macro** (line 81)

**OLD CODE**:
```c
#define SPOOL_STATE(csd, src)  ((csd)->mmcb.per_source[src].spool_state)
```

**NEW CODE**:
```c
#define SPOOL_STATE(src)  (icb.per_source_disk[src].spool_state)
```

**CHANGE 2: Update all macro usages**

**OLD CODE** (examples from lines 244, 269, 277, etc.):
```c
csd->mmcb.per_source[upload_source].spool_state.current_state = SPOOL_STATE_SELECTING;
SPOOL_STATE(csd, upload_source).sectors_selected_count = 0;
memset(SPOOL_STATE(csd, upload_source).sectors_to_spool, 0xFF,
       sizeof(SPOOL_STATE(csd, upload_source).sectors_to_spool));
```

**NEW CODE**:
```c
icb.per_source_disk[upload_source].spool_state.current_state = SPOOL_STATE_SELECTING;
SPOOL_STATE(upload_source).sectors_selected_count = 0;
memset(SPOOL_STATE(upload_source).sectors_to_spool, 0xFF,
       sizeof(SPOOL_STATE(upload_source).sectors_to_spool));
```

**REPLACEMENT RULES** for this file:
1. Find: `csd->mmcb\.per_source\[(upload_source|source)\]\.` → Replace: `icb.per_source_disk[$1].`
2. Find: `SPOOL_STATE\(csd, (upload_source|source)\)` → Replace: `SPOOL_STATE($1)`
3. Total replacements: 85

**Critical Code Sections** (lines 330-371, 485-526):

**OLD CODE** (line 330-371, write_tsd_sector_to_disk):
```c
    if (csd->mmcb.per_source[upload_source].active_spool_fd < 0) {
        // ... path setup ...
        uint32_t sequence = csd->mmcb.per_source[upload_source].next_sequence_number;
        int written = snprintf(csd->mmcb.per_source[upload_source].active_spool_filename,
                              sizeof(csd->mmcb.per_source[upload_source].active_spool_filename),
                              "%s/sensor_%u_seq_%u.dat",
                              source_path, GET_SENSOR_ID(csd), sequence);
        if (written < 0 || (size_t)written >= sizeof(csd->mmcb.per_source[upload_source].active_spool_filename)) {
            LOG_SPOOL_ERROR("Filename too long for source %d sensor %u", upload_source, GET_SENSOR_ID(csd));
            return IMX_INVALID_PARAMETER;
        }
        csd->mmcb.per_source[upload_source].active_spool_fd =
            open(csd->mmcb.per_source[upload_source].active_spool_filename,
                 O_WRONLY | O_CREAT | O_APPEND, 0644);
        if (csd->mmcb.per_source[upload_source].active_spool_fd < 0) {
            LOG_SPOOL_ERROR("Failed to open spool file: %s (%s)",
                           csd->mmcb.per_source[upload_source].active_spool_filename,
                           strerror(errno));
            return IMX_ERROR;
        }
        add_spool_file_to_tracking(csd, upload_source, csd->mmcb.per_source[upload_source].active_spool_filename, sequence, 1);
        csd->mmcb.per_source[upload_source].next_sequence_number++;
        csd->mmcb.per_source[upload_source].current_spool_file_size = 0;
    }
```

**NEW CODE**:
```c
    if (icb.per_source_disk[upload_source].active_spool_fd < 0) {
        // ... path setup ...
        uint32_t sequence = icb.per_source_disk[upload_source].next_sequence_number;
        int written = snprintf(icb.per_source_disk[upload_source].active_spool_filename,
                              sizeof(icb.per_source_disk[upload_source].active_spool_filename),
                              "%s/sensor_%u_seq_%u.dat",
                              source_path, GET_SENSOR_ID(csd), sequence);
        if (written < 0 || (size_t)written >= sizeof(icb.per_source_disk[upload_source].active_spool_filename)) {
            LOG_SPOOL_ERROR("Filename too long for source %d sensor %u", upload_source, GET_SENSOR_ID(csd));
            return IMX_INVALID_PARAMETER;
        }
        icb.per_source_disk[upload_source].active_spool_fd =
            open(icb.per_source_disk[upload_source].active_spool_filename,
                 O_WRONLY | O_CREAT | O_APPEND, 0644);
        if (icb.per_source_disk[upload_source].active_spool_fd < 0) {
            LOG_SPOOL_ERROR("Failed to open spool file: %s (%s)",
                           icb.per_source_disk[upload_source].active_spool_filename,
                           strerror(errno));
            return IMX_ERROR;
        }
        add_spool_file_to_tracking(csd, upload_source, icb.per_source_disk[upload_source].active_spool_filename, sequence, 1);
        icb.per_source_disk[upload_source].next_sequence_number++;
        icb.per_source_disk[upload_source].current_spool_file_size = 0;
    }
```

---

#### File: `iMatrix/cs_ctrl/mm2_read.c` (1 occurrence, line 187)

**Function**: `read_next_record_from_memory()` (line 187)

**OLD CODE**:
```c
        if (!csd->mmcb.per_source[upload_source].disk_exhausted) {
```

**NEW CODE**:
```c
        if (!icb.per_source_disk[upload_source].disk_exhausted) {
```

---

#### File: `iMatrix/cs_ctrl/mm2_write.c` (16 occurrences, lines 379-397)

**Function**: `close_all_spool_files_for_sensor()` (lines 379-397)

**OLD CODE** (lines 379-397):
```c
        if (csd->mmcb.per_source[source].active_spool_fd >= 0) {
            close(csd->mmcb.per_source[source].active_spool_fd);
            csd->mmcb.per_source[source].active_spool_fd = -1;
        }
        if (csd->mmcb.per_source[source].current_read_handle) {
            fclose(csd->mmcb.per_source[source].current_read_handle);
            csd->mmcb.per_source[source].current_read_handle = NULL;
        }

        /* Reset file tracking */
        csd->mmcb.per_source[source].current_spool_file_size = 0;
        csd->mmcb.per_source[source].active_spool_filename[0] = '\0';
        csd->mmcb.per_source[source].next_sequence_number = 0;
        csd->mmcb.per_source[source].spool_file_count = 0;
        csd->mmcb.per_source[source].disk_reading_file_index = 0;
        csd->mmcb.per_source[source].disk_file_offset = 0;
        csd->mmcb.per_source[source].disk_exhausted = 0;
        memset(&csd->mmcb.per_source[source].spool_state, 0,
               sizeof(csd->mmcb.per_source[source].spool_state));
```

**NEW CODE**:
```c
        if (icb.per_source_disk[source].active_spool_fd >= 0) {
            close(icb.per_source_disk[source].active_spool_fd);
            icb.per_source_disk[source].active_spool_fd = -1;
        }
        if (icb.per_source_disk[source].current_read_handle) {
            fclose(icb.per_source_disk[source].current_read_handle);
            icb.per_source_disk[source].current_read_handle = NULL;
        }

        /* Reset file tracking */
        icb.per_source_disk[source].current_spool_file_size = 0;
        icb.per_source_disk[source].active_spool_filename[0] = '\0';
        icb.per_source_disk[source].next_sequence_number = 0;
        icb.per_source_disk[source].spool_file_count = 0;
        icb.per_source_disk[source].disk_reading_file_index = 0;
        icb.per_source_disk[source].disk_file_offset = 0;
        icb.per_source_disk[source].disk_exhausted = 0;
        memset(&icb.per_source_disk[source].spool_state, 0,
               sizeof(icb.per_source_disk[source].spool_state));
```

---

#### Files: `mm2_disk_reading.c` and `mm2_file_management.c`

These files also contain `per_source[]` references but weren't captured in the initial grep. Use the same replacement pattern:
- Find: `csd->mmcb\.per_source\[([^]]+)\]\.`
- Replace: `icb.per_source_disk[$1].`

---

### 3.3 Function Signature Updates

**IMPORTANT**: No function signatures need to change. The `csd` parameter is still needed for:
- Sensor ID retrieval: `GET_SENSOR_ID(csd)`
- RAM sector chain access: `csd->mmcb.ram_start_sector_id`, etc.
- Mutex locking: `csd->mmcb.sensor_lock`
- Statistics: `csd->mmcb.total_records`

Only the disk spooling state (`per_source[]`) is being moved to global scope.

---

## 4. Initialization Changes

### File: `iMatrix/storage.c` (around line 74)

Add initialization after the `icb` declaration:

**NEW CODE** (add after global icb declaration):
```c
#ifdef LINUX_PLATFORM
/**
 * @brief Initialize global disk spooling state
 *
 * Called once at system startup to initialize per-source disk state.
 * Must be called before any memory manager operations.
 */
void init_global_disk_state(void) {
    for (int source = 0; source < IMX_UPLOAD_NO_SOURCES; source++) {
        icb.per_source_disk[source].active_spool_fd = -1;
        icb.per_source_disk[source].current_spool_file_size = 0;
        icb.per_source_disk[source].active_spool_filename[0] = '\0';
        icb.per_source_disk[source].next_sequence_number = 0;
        icb.per_source_disk[source].spool_file_count = 0;
        icb.per_source_disk[source].current_read_handle = NULL;
        icb.per_source_disk[source].disk_reading_file_index = 0;
        icb.per_source_disk[source].disk_file_offset = 0;
        icb.per_source_disk[source].disk_record_index = 0;
        icb.per_source_disk[source].disk_records_in_sector = 0;
        icb.per_source_disk[source].disk_reading_active = 0;
        icb.per_source_disk[source].disk_exhausted = 0;
        icb.per_source_disk[source].total_disk_records = 0;
        icb.per_source_disk[source].bytes_written_to_disk = 0;
        memset(&icb.per_source_disk[source].spool_state, 0,
               sizeof(icb.per_source_disk[source].spool_state));
        memset(icb.per_source_disk[source].spool_files, 0,
               sizeof(icb.per_source_disk[source].spool_files));
    }
}
#endif
```

Call this function early in system initialization (e.g., in `init_storage()` or `system_init()`).

---

## 5. Automated Search-and-Replace Commands

For safe, systematic replacement, use these grep/sed commands:

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl

# Backup files first
for file in mm2_*.c; do cp "$file" "$file.bak"; done

# Replace in mm2_pool.c
sed -i 's/csd->mmcb\.per_source\[source\]\./icb.per_source_disk[source]./g' mm2_pool.c

# Replace in mm2_startup_recovery.c
sed -i 's/csd->mmcb\.per_source\[upload_source\]\./icb.per_source_disk[upload_source]./g' mm2_startup_recovery.c

# Replace in mm2_disk_spooling.c
sed -i 's/csd->mmcb\.per_source\[\(upload_source\|source\)\]\./icb.per_source_disk[\1]./g' mm2_disk_spooling.c
sed -i 's/SPOOL_STATE(csd, \(upload_source\|source\))/SPOOL_STATE(\1)/g' mm2_disk_spooling.c

# Replace in mm2_write.c
sed -i 's/csd->mmcb\.per_source\[source\]\./icb.per_source_disk[source]./g' mm2_write.c

# Replace in mm2_read.c
sed -i 's/csd->mmcb\.per_source\[upload_source\]\./icb.per_source_disk[upload_source]./g' mm2_read.c

# Replace in mm2_disk_reading.c (if exists)
sed -i 's/csd->mmcb\.per_source\[\([^]]\+\)\]\./icb.per_source_disk[\1]./g' mm2_disk_reading.c

# Replace in mm2_file_management.c (if exists)
sed -i 's/csd->mmcb\.per_source\[\([^]]\+\)\]\./icb.per_source_disk[\1]./g' mm2_file_management.c
```

**Verification**:
```bash
# Check remaining references (should be 0)
grep -rn "csd->mmcb\.per_source\[" mm2_*.c

# Check new references (should be 191)
grep -rn "icb\.per_source_disk\[" mm2_*.c | wc -l
```

---

## 6. Compilation and Testing Checklist

### 6.1 Pre-Compilation Checks

- [ ] All structure definitions updated in `common.h`
- [ ] New structure added to `icb_def.h`
- [ ] All 191 code references updated
- [ ] SPOOL_STATE macro updated
- [ ] Initialization function added
- [ ] Backup files created

### 6.2 Compilation

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix
mkdir -p build
cd build
cmake ..
make 2>&1 | tee compile.log
```

**Expected Warnings**: None related to `per_source`

**Expected Errors**: If any errors occur, they likely indicate missed references. Search for:
```bash
grep -E "(per_source.*undeclared|per_source.*member)" compile.log
```

### 6.3 Runtime Testing

1. **Memory Initialization**:
   ```bash
   # Check icb.per_source_disk[] initialization
   gdb ./build/linux_gateway
   (gdb) break init_global_disk_state
   (gdb) run
   (gdb) print icb.per_source_disk[0].active_spool_fd
   # Should be: -1
   ```

2. **Disk Spooling**:
   - Trigger memory pressure (>80% RAM usage)
   - Verify files created in correct directories
   - Check state machine transitions with logging

3. **Multi-Sensor Operation**:
   - Enable multiple sensors
   - Verify each sensor writes to separate files
   - Confirm shared state machine doesn't interfere

---

## 7. Rollback Plan

If compilation fails or runtime issues occur:

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl

# Restore backups
for file in mm2_*.c.bak; do mv "$file" "${file%.bak}"; done

# Restore header files (manual backup required)
git checkout common.h device/icb_def.h
```

---

## 8. Post-Migration Validation

### 8.1 Memory Savings Verification

Before migration:
```c
sizeof(imx_mmcb_t) * IMX_MAX_NO_SENSORS
= ~3500 bytes * 25 sensors = 87.5KB
```

After migration:
```c
sizeof(per_source_disk_state_t) * IMX_UPLOAD_NO_SOURCES
= ~3000 bytes * 4 sources = 12KB
```

**Savings**: ~75KB (86% reduction in disk state memory)

### 8.2 Functional Validation

- [ ] Memory manager initializes correctly
- [ ] Disk spooling triggers at 80% RAM usage
- [ ] Files created with correct sensor IDs in filenames
- [ ] State machine operates across all sensors
- [ ] Upload process reads from disk files correctly
- [ ] File rotation works at 64KB boundaries
- [ ] Recovery on reboot discovers existing files

---

## 9. Known Risks and Mitigation

| Risk | Impact | Mitigation |
|:-----|:-------|:-----------|
| Missed code reference | Compilation failure | Use automated grep verification |
| Global state race condition | Data corruption | Verify mutex protection in shared access paths |
| Sensor-specific filename collision | File overwrite | Filenames already include sensor ID - no change needed |
| State machine interference | Lost data | Test with multiple active sensors |
| Initialization order dependency | Crash on startup | Call `init_global_disk_state()` early in boot sequence |

---

## 10. Success Criteria

- ✅ Clean compilation with zero warnings
- ✅ Memory footprint reduced by ~75KB
- ✅ All 191 references correctly updated
- ✅ Disk spooling operates correctly for multiple sensors
- ✅ File creation and tracking verified
- ✅ Upload process reads data correctly
- ✅ Recovery on reboot discovers files
- ✅ No regression in existing functionality

---

## 11. Summary

**Total Code Changes**:
- **Files modified**: 10 source files + 2 headers = 12 files
- **Lines changed**: 191 direct references + ~100 structure definition lines = ~291 lines
- **New code**: ~50 lines (initialization function + structure definition)
- **Net change**: ~341 lines modified/added

**Review Requirements**:
- Senior embedded systems engineer approval
- Memory management architect approval
- Cross-compiler test on target hardware
- Regression testing on existing memory manager operations

**Timeline Estimate**:
- Structure changes: 1 hour
- Automated replacements: 1 hour
- Manual verification: 2 hours
- Compilation and testing: 2 hours
- **Total**: ~6 hours for complete migration

---

*Document Version: 1.0*
*Created: 2025-10-13*
*Author: Claude Code (AI Assistant)*
*Reviewed By: [Pending]*
