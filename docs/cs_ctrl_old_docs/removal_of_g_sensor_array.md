# Removal of g_sensor_array - Architectural Refactoring Plan

## Executive Summary

**Problem**: MM2 maintains internal `g_sensor_array.sensors[500]` array that shadows the main application's **per-upload-source sensor arrays**, violating the API contract where `upload_source`, `csb` and `csd` are passed as parameters.

**Critical Architecture**: Main app has **separate csb/csd arrays for EACH upload source**:
- Gateway sensors: separate arrays (e.g., `icb.i_scb[]`, `icb.i_sd[]`)
- BLE device sensors: separate arrays
- CAN device sensors: separate arrays

**Root Cause**: `GET_SENSOR_ID(csd)` macro uses pointer arithmetic `(csd - g_sensor_array.sensors)` which only works if `csd` originates from MM2's internal array - breaks when main app passes upload source-specific arrays.

**Solution**: Eliminate `g_sensor_array` completely, use `csb->id` as truth source for sensor ID, track **(upload_source, sensor_id, csb, csd)** tuples for active sensors.

**Impact**: ~150 lines changed across 11 files

**Priority**: **CRITICAL** - Current code will fail when main app calls API with upload source-specific csd pointers

---

## Current Architecture (Broken)

```
Main Application (Fleet-Connect-1):
  PER UPLOAD SOURCE - Separate arrays:

  Gateway (IMX_UPLOAD_GATEWAY):
    icb.i_scb[25] (sensor configs with id field)
    icb.i_sd[25]  (sensor data with mmcb)

  BLE Devices (IMX_UPLOAD_BLE_DEVICE):
    ble_scb[128] (BLE sensor configs)
    ble_sd[128]  (BLE sensor data)

  CAN Devices (IMX_UPLOAD_CAN_DEVICE):
    can_scb[N] (CAN sensor configs)
    can_sd[N]  (CAN sensor data)
  ↓
  Calls: imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], value)
     or: imx_write_tsd(IMX_UPLOAD_BLE_DEVICE, &ble_scb[10], &ble_sd[10], value)
  ↓
MM2 Internal (WRONG):
  g_sensor_array.sensors[500]  ← Shadow duplicate, WRONG for ALL upload sources!
  GET_SENSOR_ID(csd) = (csd - g_sensor_array.sensors)  ← FAILS! csd not from this array
```

**Failure Mode**: Main app passes `&ble_sd[10]` for BLE upload source, GET_SENSOR_ID calculates garbage pointer offset because it expects csd from g_sensor_array.

**Critical Insight**: Sensor ID (csb->id) is unique within an upload source's sensor array, but may not be globally unique across all sources.

---

## Target Architecture (Correct)

```
Main Application:
  PER UPLOAD SOURCE - Separate arrays (main app manages):

  Gateway: icb.i_scb[25], icb.i_sd[25] (csb->id is truth source)
  BLE:     ble_scb[128], ble_sd[128]
  CAN:     can_scb[N], can_sd[N]
  ↓
  Calls: imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], value)
     or: imx_write_tsd(IMX_UPLOAD_BLE_DEVICE, &ble_scb[10], &ble_sd[10], value)
  ↓
MM2 Internal:
  NO internal sensor arrays
  Active sensor tracker: {upload_source, sensor_id, csb*, csd*} tuples
  GET_SENSOR_ID(csb) = csb->id  ← Direct access, always correct
  Uses (upload_source, csb, csd) tuple passed by caller

  Disk state: icb.per_source_disk[upload_source] ← Already per-source! ✓
```

**Success**: MM2 is truly stateless except for:
- Global memory pool (sectors + chains)
- Global per_source_disk state (already per-source)
- Minimal active sensor tracker (upload_source, sensor_id, csb*, csd*) tuples

**Key Insight**: `upload_source` parameter already exists in all MM2 API functions - we just need to ensure it's threaded through ALL helper functions too!

---

## Key Multi-Source Architecture Requirements

### 1. Upload Source is Primary Partitioning Key

**CRITICAL**: All disk operations, file paths, and state are partitioned by `upload_source`:
- Directory structure: `/usr/qk/var/mm2/{gateway|ble|can}/sensor_{id}_seq_{N}.dat`
- Disk state: `icb.per_source_disk[upload_source]` (already implemented ✓)
- Active sensors: must track `(upload_source, sensor_id)` tuple

### 2. Standard Parameter Order for ALL Functions

**Mandatory order**:
```c
function_name(imatrix_upload_source_t upload_source,
              imx_control_sensor_block_t* csb,
              control_sensor_data_t* csd,
              ...other parameters...)
```

**Rationale**:
- upload_source determines which directory/state to use
- csb provides sensor ID and configuration
- csd provides runtime state and mmcb

**Examples**:
```c
✓ imx_write_tsd(upload_source, csb, csd, value)
✓ imx_recover_sensor_disk_data(upload_source, csb, csd)
✓ rotate_spool_file(upload_source, csb, csd)
✗ some_function(csd, upload_source, ...)  // WRONG ORDER!
```

### 3. Sensor ID Scope

**csb->id is unique WITHIN an upload source, NOT globally!**

Example:
- Gateway sensor csb->id = 5 → files in `/usr/qk/var/mm2/gateway/sensor_5_seq_*.dat`
- BLE sensor csb->id = 5 → files in `/usr/qk/var/mm2/ble/sensor_5_seq_*.dat`
- Different sensors, different directories, same ID within their upload source

### 4. Active Sensor Identification

**Unique key**: `(upload_source, csb->id)` pair

```c
// Finding a specific sensor in tracker:
for (i = 0; i < count; i++) {
    if (tracker[i].upload_source == IMX_UPLOAD_BLE_DEVICE &&
        tracker[i].sensor_id == 5) {
        // Found BLE sensor ID 5
    }
}
```

---

## Phase 1: Fix GET_SENSOR_ID Macro

### Problem Analysis

Current macro (mm2_core.h:202):
```c
#define GET_SENSOR_ID(csd) ((uint32_t)((csd) - g_sensor_array.sensors))
```

**Issues**:
1. Assumes csd is from g_sensor_array (wrong!)
2. Pointer arithmetic only valid within same array
3. Yields undefined behavior when csd from icb.i_sd[]

**Uses**: 34 occurrences across 7 files (all for logging/diagnostics)

### Solution

**Change macro**:
```c
// mm2_core.h line 202
// OLD:
#define GET_SENSOR_ID(csd) ((uint32_t)((csd) - g_sensor_array.sensors))

// NEW:
#define GET_SENSOR_ID(csb) ((csb)->id)
```

### CRITICAL Multi-Source Implications

Since sensor arrays are per-upload-source:
1. **Sensor ID (csb->id) is only unique within an upload source**
   - Gateway sensor ID 5 ≠ BLE sensor ID 5 (different sensors!)
   - Must always use (upload_source, sensor_id) tuple to identify sensors

2. **Upload source must be passed to ALL functions**
   - File operations need it for directory paths
   - Logging needs it for context
   - Active sensor tracker needs it for uniqueness

3. **GET_SENSOR_ID(csb) is safe**
   - Returns csb->id which is unique within upload_source context
   - Always correct regardless of which array csb came from

### Step-by-Step Todo

#### Step 1.1: Update Macro Definition
- [ ] **File**: `mm2_core.h` line 202
- [ ] **Change**: Parameter from `csd` to `csb`, body from pointer arithmetic to `->id` access
- [ ] **Verify**: Macro now expects csb, not csd
- [ ] **Update comment**: Note that sensor ID is unique within upload_source context

#### Step 1.2: Update All Macro Call Sites (34 occurrences)

**Pattern**: Change `GET_SENSOR_ID(csd)` → `GET_SENSOR_ID(csb)`

**File: mm2_disk_spooling.c** (14 occurrences)
- [ ] Line 244: `GET_SENSOR_ID(csd)` → `GET_SENSOR_ID(csb)` in LOG_SPOOL_INFO
- [ ] Line 299: In select_sectors_for_spooling() - add csb parameter
- [ ] Line 348: In filename generation - use csb->id directly
- [ ] Line 352, 404, 503, 507, 555: All LOG messages
- [ ] Lines 676, 714, 740, 769, 831, 862, 867, 883, 887, 920, 957: Update all

**File: mm2_file_management.c** (11 occurrences)
- [ ] Lines 103, 125, 172, 246, 258, 263, 305, 330, 355, 411, 425: Update all

**File: mm2_power.c** (2 occurrences)
- [ ] Lines 175, 455: Update in LOG messages

**File: mm2_disk_reading.c** (1 occurrence)
- [ ] Line 271: Update in printf

**File: mm2_power_abort.c** (1 occurrence)
- [ ] Line 173: Update in LOG message

**Verification**:
```bash
grep -rn "GET_SENSOR_ID(csd)" mm2_*.c  # Should return 0
grep -rn "GET_SENSOR_ID(csb)" mm2_*.c  # Should return 34
```

#### Step 1.3: Add csb Parameter to Helper Functions

Functions that currently only have `csd` but use GET_SENSOR_ID:

**mm2_file_management.c**:
- [ ] `add_spool_file_to_tracking(csd, ...)` → add `csb` parameter (line ~88)
- [ ] `find_oldest_deletable_file_index(csd, ...)` → add `csb` parameter
- [ ] `calculate_total_spool_size(csd, ...)` → add `csb` parameter
- [ ] `delete_spool_file(csd, ...)` → add `csb` parameter
- [ ] `enforce_space_limit(csd, ...)` → add `csb` parameter
- [ ] `rotate_spool_file(csd, ...)` → add `csb` parameter
- [ ] `delete_all_sensor_files(csd, ...)` → add `csb` parameter
- [ ] `update_active_file_size(csd, ...)` → add `csb` parameter

**mm2_disk_spooling.c**:
- [ ] `write_tsd_sector_to_disk(csd, ...)` → add `csb` parameter (line ~312)
- [ ] `write_evt_sector_to_disk(csd, ...)` → add `csb` parameter
- [ ] `select_sectors_for_spooling(csd, ...)` → add `csb` parameter
- [ ] All state processing functions → add `csb` parameter

**mm2_disk_reading.c**:
- [ ] `get_oldest_readable_file_index(csd, ...)` → add `csb` parameter
- [ ] `open_disk_file_for_reading(csd, ...)` → add `csb` parameter
- [ ] `read_record_from_disk(...)` → already has csb ✓

**Update Call Sites**: ~25 function call sites need csb argument added

---

## Phase 2: Redesign Recovery Functions

### Problem Analysis

Current design (mm2_startup_recovery.c:538):
```c
imx_result_t recover_disk_spooled_data(void) {  // NO PARAMETERS!
    for (uint32_t sensor_id = 0; sensor_id < MAX_SENSORS; sensor_id++) {
        control_sensor_data_t* csd = &g_sensor_array.sensors[sensor_id];  // WRONG!
        // ... scan files ...
    }
}
```

**Issues**:
1. No parameters - assumes internal array
2. Loops over 500 sensors even if only 5 active
3. Uses sensor_id as array index, not csb->id
4. Main app can't control which sensors to recover

### Solution: Per-Sensor Recovery API

#### Step 2.1: Create New API Function

**Add to mm2_api.h** (~line 350):
```c
/**
 * @brief Recover disk-spooled data for specific sensor
 *
 * Main application must call this once for each active sensor during startup.
 * Scans all upload source directories for this sensor's spool files,
 * validates integrity, and prepares for continued upload operations.
 *
 * @param csb Sensor configuration block (contains sensor ID)
 * @param csd Sensor data block (contains mmcb)
 * @return IMX_SUCCESS on success, error code on failure (non-fatal)
 */
imx_result_t imx_recover_sensor_disk_data(imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd);
```

#### Step 2.2: Implement New Function (UPDATED for Multi-Source)

**File**: mm2_startup_recovery.c

**Add function** (~line 540):
```c
/**
 * @brief Recover disk-spooled data for specific sensor in specific upload source
 *
 * CRITICAL: upload_source parameter determines which directory to scan.
 * Sensor ID (csb->id) is unique within that upload source's sensor array.
 *
 * Main app calls this once per sensor per upload source.
 */
imx_result_t imx_recover_sensor_disk_data(imatrix_upload_source_t upload_source,
                                          imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd) {
    if (upload_source >= IMX_UPLOAD_NO_SOURCES || !csb || !csd) {
        return IMX_INVALID_PARAMETER;
    }

    uint32_t sensor_id = csb->id;

    PRINTF("[MM2-RECOVERY] Starting recovery for source %d, sensor %u (%s)\n",
           upload_source, sensor_id, csb->name);

    /* Initialize disk space tracking for this sensor */
    csd->mmcb.total_disk_space_used = 0;

    /* CRITICAL: Only scan THIS upload source's directory, not all sources!
     * The upload_source parameter tells us which directory to look in:
     * - IMX_UPLOAD_GATEWAY → /usr/qk/var/mm2/gateway/
     * - IMX_UPLOAD_BLE_DEVICE → /usr/qk/var/mm2/ble/
     * - IMX_UPLOAD_CAN_DEVICE → /usr/qk/var/mm2/can/
     */

    /* Initialize per-source state (global, not per-sensor) */
    icb.per_source_disk[upload_source].spool_file_count = 0;
    icb.per_source_disk[upload_source].total_disk_records = 0;
    icb.per_source_disk[upload_source].bytes_written_to_disk = 0;
    icb.per_source_disk[upload_source].active_spool_fd = -1;

    /* Scan for THIS sensor's files in THIS upload source's directory */
    imx_result_t scan_result = scan_sensor_spool_files_by_source(sensor_id, upload_source);
    if (scan_result != IMX_SUCCESS) {
        PRINTF("[MM2-RECOVERY] Scan failed for source %d sensor %u\n", upload_source, sensor_id);
        return scan_result;
    }

    /* Validate discovered files */
    imx_result_t validate_result = validate_and_integrate_files(sensor_id, upload_source);
    if (validate_result != IMX_SUCCESS) {
        PRINTF("[MM2-RECOVERY] Validation failed for source %d sensor %u\n", upload_source, sensor_id);
        return validate_result;
    }

    /* Rebuild sensor state from validated files */
    imx_result_t rebuild_result = rebuild_sensor_state(sensor_id, upload_source);
    if (rebuild_result != IMX_SUCCESS) {
        PRINTF("[MM2-RECOVERY] Rebuild failed for source %d sensor %u\n", upload_source, sensor_id);
        return rebuild_result;
    }

    uint64_t records_recovered = icb.per_source_disk[upload_source].total_disk_records;

    PRINTF("[MM2-RECOVERY] Source %d sensor %u recovery complete: %lu records\n",
           upload_source, sensor_id, (unsigned long)records_recovered);

    return IMX_SUCCESS;
}
```

#### Step 2.3: Update Existing Recovery Function

**Option A** (Deprecate but keep for compatibility):
```c
// Mark as deprecated, redirect to new API
imx_result_t recover_disk_spooled_data(void) {
    PRINTF("[MM2-RECOVERY-DEPRECATED] Use imx_recover_sensor_disk_data() instead\n");
    return IMX_SUCCESS;  // Main app must call new API
}
```

**Option B** (Remove completely):
- Delete entire function
- Remove from mm2_disk.h
- Remove call from mm2_api.c

**Recommended**: Option A (safer migration path)

#### Step 2.4: Update mm2_api.c Initialization

**File**: mm2_api.c line ~99

**Change**:
```c
// OLD:
result = recover_disk_spooled_data();

// NEW:
// NOTE: Main application must call imx_recover_sensor_disk_data()
// for each active sensor after init
PRINTF("[MM2-INIT] Recovery deferred to main application\n");
```

#### Step 2.5: Remove Obsolete Helper Uses

**mm2_startup_recovery.c** lines 124, 355, 466, 550:
```c
// OLD:
control_sensor_data_t* csd = &g_sensor_array.sensors[sensor_id];

// DELETE THIS LINE (csd already passed as parameter)
// Or if needed for internal helpers, use parameter validation
```

### Todo Checklist for Phase 2

- [ ] Add `imx_recover_sensor_disk_data()` to mm2_api.h
- [ ] Implement new function in mm2_startup_recovery.c
- [ ] Deprecate old `recover_disk_spooled_data()` function
- [ ] Remove call from mm2_api.c initialization
- [ ] Update helper functions to remove g_sensor_array lookups
- [ ] Add csb parameter to helper functions

---

## Phase 3: Fix STM32 RAM Exhaustion (CORRECTED DESIGN)

### Problem Analysis

**Current flawed design** (mm2_stm32.c):
```c
imx_result_t handle_stm32_ram_full(uint32_t requesting_sensor_id) {
    // Searches ALL sensors to find oldest data
    for (uint32_t i = 0; i < MAX_SENSORS; i++) {
        control_sensor_data_t* csd = &g_sensor_array.sensors[i];  // WRONG!
        // ... find oldest across all sensors ...
    }
}
```

**Issue**: Searches across all sensors using internal array that doesn't exist in main app.

### CORRECT Solution: Per-Sensor Circular Buffer

**Key Insight**: When RAM allocation fails, the **CALLER already has (upload_source, csb, csd)**!

**Example call chain**:
```
imx_write_tsd(upload_source, csb, csd, value)  ← Has all 3 parameters!
  ↓
  allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD)
  ↓
  Returns NULL_SECTOR_ID (RAM full)
  ↓
  imx_write_tsd handles it: discard oldest from CSD's own chain
  ↓
  Retry allocation
```

**New Design**: Each sensor implements circular buffer - when it needs space, it sacrifices its own oldest data.

```c
// In imx_write_tsd (already has upload_source, csb, csd):
SECTOR_ID_TYPE new_sector = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
if (new_sector == NULL_SECTOR_ID) {
    #ifndef LINUX_PLATFORM
    // STM32: RAM full - discard oldest from THIS sensor's chain
    imx_result_t discard_result = discard_oldest_non_pending_sector(csd);
    if (discard_result == IMX_SUCCESS) {
        // Retry allocation
        new_sector = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
    }
    #endif

    if (new_sector == NULL_SECTOR_ID) {
        return IMX_OUT_OF_MEMORY;  // Still failed
    }
}
```

**Benefits**:
- ✅ No cross-sensor search needed
- ✅ No active sensor tracker needed for STM32
- ✅ upload_source, csb, csd already in caller's scope
- ✅ Simpler implementation
- ✅ Per-sensor fairness (each sensor manages its own quota)
- ✅ No global state needed

### REVISED: Active Sensor Tracker

**Conclusion**: Active sensor tracker is **NOT needed** for STM32 RAM exhaustion with this correct design!

**Only needed for**:
- Linux power-down (if we need to iterate all sensors)
- Power abort recovery (if we need to iterate all sensors)

**For now**: DEFER active sensor tracker to Phase 4 (power functions) if actually needed. Most power functions can likely be per-sensor APIs too.

### Step-by-Step Todo

#### Step 3.1: Create discard_oldest_non_pending_sector Function

**File**: mm2_stm32.c (or mm2_pool.c for shared code)

**Add new function**:
```c
/**
 * @brief Discard oldest non-pending sector from sensor's chain
 *
 * CRITICAL: Called when requesting sensor runs out of RAM.
 * Implements circular buffer - sensor sacrifices its own oldest data.
 *
 * @param csd Sensor data (contains mmcb with sector chain)
 * @return IMX_SUCCESS if sector freed, IMX_ERROR if all data pending
 */
imx_result_t discard_oldest_non_pending_sector(control_sensor_data_t* csd) {
    if (!csd) {
        return IMX_INVALID_PARAMETER;
    }

    /* Find oldest non-pending sector in THIS sensor's chain */
    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;
    SECTOR_ID_TYPE oldest_non_pending = NULL_SECTOR_ID;

    while (current != NULL_SECTOR_ID) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current);
        if (entry && entry->in_use && !entry->pending_ack) {
            oldest_non_pending = current;  // Start of chain is oldest
            break;
        }
        current = get_next_sector_in_chain(current);
    }

    if (oldest_non_pending == NULL_SECTOR_ID) {
        return IMX_ERROR;  // All data is pending - cannot discard
    }

    /* Remove oldest sector from chain */
    SECTOR_ID_TYPE next_sector = get_next_sector_in_chain(oldest_non_pending);

    if (csd->mmcb.ram_start_sector_id == oldest_non_pending) {
        csd->mmcb.ram_start_sector_id = next_sector;
        csd->mmcb.ram_read_sector_offset = 0;
    }

    if (csd->mmcb.ram_end_sector_id == oldest_non_pending) {
        csd->mmcb.ram_end_sector_id = NULL_SECTOR_ID;
        csd->mmcb.ram_write_sector_offset = 0;
    }

    /* Free the sector */
    free_sector(oldest_non_pending);

    /* Decrement total_records */
    if (csd->mmcb.total_records > 0) {
        csd->mmcb.total_records--;
    }

    return IMX_SUCCESS;
}
```

#### Step 3.2: Update imx_write_tsd to Handle RAM Full

**File**: mm2_write.c

**Change** (around line 122):
```c
// OLD:
SECTOR_ID_TYPE new_sector_id = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
if (new_sector_id == NULL_SECTOR_ID) {
    return IMX_OUT_OF_MEMORY;
}

// NEW (STM32 circular buffer):
SECTOR_ID_TYPE new_sector_id = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
if (new_sector_id == NULL_SECTOR_ID) {
    #ifndef LINUX_PLATFORM
    /* STM32: RAM full - discard oldest from this sensor's chain */
    imx_result_t discard_result = discard_oldest_non_pending_sector(csd);
    if (discard_result == IMX_SUCCESS) {
        /* Retry allocation */
        new_sector_id = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
    }
    #endif

    if (new_sector_id == NULL_SECTOR_ID) {
        return IMX_OUT_OF_MEMORY;  // Still failed after discard attempt
    }
}
```

**Same pattern for imx_write_evt()**

#### Step 3.3: Simplify allocate_sector_for_sensor

**File**: mm2_pool.c

**Remove** embedded call to handle_stm32_ram_full:
```c
// DELETE this block from allocate_sector_for_sensor:
#ifndef LINUX_PLATFORM
/* STM32: Handle RAM exhaustion by discarding oldest data */
if (handle_stm32_ram_full(sensor_id) != IMX_SUCCESS) {
    return NULL_SECTOR_ID;
}
// Retry...
#endif
```

**Rationale**: Caller handles RAM full with full context (upload_source, csb, csd).

#### Step 3.4: OPTIONAL - Keep Active Tracker for Linux Power-Down Only

Active sensor tracker is NOW OPTIONAL - only needed if Linux power-down must iterate all sensors.

**Alternative**: Make power-down per-sensor API too (recommended):
```c
// Main app calls for each sensor during shutdown:
imx_memory_manager_shutdown(upload_source, csb, csd, timeout_ms);
```

**Decision**: DEFER tracker until we analyze power-down requirements in Phase 4.

### Revised Todo Checklist for Phase 3 (Simplified!)

- [ ] Create `discard_oldest_non_pending_sector(csd)` function in mm2_pool.c or mm2_stm32.c
- [ ] Update `imx_write_tsd()` to handle NULL sector: discard oldest, retry
- [ ] Update `imx_write_evt()` to handle NULL sector: discard oldest, retry
- [ ] Remove embedded `handle_stm32_ram_full()` call from `allocate_sector_for_sensor()`
- [ ] DELETE old cross-sensor search functions: `handle_stm32_ram_full()`, `find_oldest_non_pending_sector()`, etc.
- [ ] Test STM32 circular buffer behavior per sensor
- [ ] **No active sensor tracker needed for STM32!**

**File**: mm2_core.h (after line 189)
```c
/**
 * @brief Minimal active sensor tracking for STM32 RAM exhaustion
 *
 * CRITICAL: Tracks (upload_source, sensor_id, csb*, csd*) tuples.
 * Main app has SEPARATE sensor arrays per upload source, so we must
 * track the upload source along with sensor ID to uniquely identify sensors.
 *
 * Only stores pointers to main app's csb/csd, not duplicate data.
 * Memory: 24 bytes per entry × 100 max = 2.4KB (vs 250KB for g_sensor_array)
 */
typedef struct {
    imatrix_upload_source_t upload_source;  // Which upload source owns this sensor
    uint32_t sensor_id;                     // csb->id (unique within upload_source)
    imx_control_sensor_block_t* csb;        // Pointer to main app's csb
    control_sensor_data_t* csd;             // Pointer to main app's csd
} active_sensor_entry_t;

#define MAX_ACTIVE_SENSORS  100  // Realistic limit (25 gateway + 50 BLE + 25 CAN)

typedef struct {
    active_sensor_entry_t entries[MAX_ACTIVE_SENSORS];
    uint32_t count;
    #ifdef LINUX_PLATFORM
    pthread_mutex_t lock;
    #endif
} active_sensor_tracker_t;

extern active_sensor_tracker_t g_active_sensor_tracker;
```

**Memory**: 24 bytes × 100 sensors = 2.4KB (vs 250KB for g_sensor_array = **99% reduction**)

**File**: mm2_pool.c (add after line 63)
```c
/* Active sensor tracker (minimal - just pointers) */
active_sensor_tracker_t g_active_sensor_tracker = {0};
```

#### Step 3.2: Update Activation/Deactivation (UPDATED for Multi-Source)

**File**: mm2_api.c - `imx_activate_sensor()` function

**Add**:
```c
// Register in active tracker with upload_source
#ifdef LINUX_PLATFORM
pthread_mutex_lock(&g_active_sensor_tracker.lock);
#endif

if (g_active_sensor_tracker.count < MAX_ACTIVE_SENSORS) {
    uint32_t idx = g_active_sensor_tracker.count;
    g_active_sensor_tracker.entries[idx].upload_source = upload_source;  // CRITICAL!
    g_active_sensor_tracker.entries[idx].sensor_id = csb->id;
    g_active_sensor_tracker.entries[idx].csb = csb;
    g_active_sensor_tracker.entries[idx].csd = csd;
    g_active_sensor_tracker.count++;
}

#ifdef LINUX_PLATFORM
pthread_mutex_unlock(&g_active_sensor_tracker.lock);
#endif
```

**File**: mm2_api.c - `imx_deactivate_sensor()` function

**Add**:
```c
// Remove from active tracker - MUST match BOTH upload_source AND sensor_id
#ifdef LINUX_PLATFORM
pthread_mutex_lock(&g_active_sensor_tracker.lock);
#endif

for (uint32_t i = 0; i < g_active_sensor_tracker.count; i++) {
    if (g_active_sensor_tracker.entries[i].upload_source == upload_source &&
        g_active_sensor_tracker.entries[i].sensor_id == csb->id) {
        // Shift remaining entries down
        memmove(&g_active_sensor_tracker.entries[i],
                &g_active_sensor_tracker.entries[i+1],
                (g_active_sensor_tracker.count - i - 1) * sizeof(active_sensor_entry_t));
        g_active_sensor_tracker.count--;
        break;
    }
}

#ifdef LINUX_PLATFORM
pthread_mutex_unlock(&g_active_sensor_tracker.lock);
#endif
```

#### Step 3.3: Update STM32 Functions (UPDATED for Multi-Source)

**File**: mm2_stm32.c

**Function**: `find_oldest_non_pending_sector()` (line ~123)

**Change**:
```c
// OLD:
for (uint32_t i = 0; i < MAX_SENSORS; i++) {
    control_sensor_data_t* csd = &g_sensor_array.sensors[i];
    if (!csd->active) continue;
    // ...
}

// NEW (with upload_source tracking):
#ifdef LINUX_PLATFORM
pthread_mutex_lock(&g_active_sensor_tracker.lock);
#endif

for (uint32_t i = 0; i < g_active_sensor_tracker.count; i++) {
    imatrix_upload_source_t source = g_active_sensor_tracker.entries[i].upload_source;
    uint32_t sensor_id = g_active_sensor_tracker.entries[i].sensor_id;
    imx_control_sensor_block_t* csb = g_active_sensor_tracker.entries[i].csb;
    control_sensor_data_t* csd = g_active_sensor_tracker.entries[i].csd;

    // Now have full context: (source, sensor_id, csb, csd)
    // ...search for oldest sector...
}

#ifdef LINUX_PLATFORM
pthread_mutex_unlock(&g_active_sensor_tracker.lock);
#endif
```

**Same pattern for**:
- `handle_stm32_ram_full()` line 75
- `is_sector_safe_to_discard()` line 177 (needs upload_source param added)
- `handle_critical_ram_exhaustion()` line 218

### Revised Todo Checklist for Phase 3 (SIMPLIFIED!)

- [ ] Create `discard_oldest_non_pending_sector(csd)` function
- [ ] Update `imx_write_tsd()` to call discard on NULL sector, then retry
- [ ] Update `imx_write_evt()` to call discard on NULL sector, then retry
- [ ] Remove embedded `handle_stm32_ram_full()` call from `allocate_sector_for_sensor()`
- [ ] DELETE old functions: `handle_stm32_ram_full()`, `find_oldest_non_pending_sector()`, `is_sector_safe_to_discard()`, `handle_critical_ram_exhaustion()`
- [ ] Add function declaration to mm2_internal.h or mm2_api.h
- [ ] Test STM32 per-sensor circular buffer behavior
- [ ] **No active sensor tracker needed!** (deferred to Phase 4 if power functions need it)

---

## Phase 4: Fix Power Abort Recovery (REVISED)

### Problem Analysis

**File**: mm2_power_abort.c (lines 199, 361)

Current code loops over g_sensor_array:
```c
for (uint32_t i = 0; i < MAX_SENSORS; i++) {
    control_sensor_data_t* csd = &g_sensor_array.sensors[i];
    // ... cleanup emergency files ...
}
```

**Issue**: Needs to iterate all active sensors but uses internal array.

### Solution Decision Point

**Option A**: Use active sensor tracker (if we add it for this purpose)
```c
for (uint32_t i = 0; i < g_active_sensor_tracker.count; i++) {
    imatrix_upload_source_t source = g_active_sensor_tracker.entries[i].upload_source;
    imx_control_sensor_block_t* csb = g_active_sensor_tracker.entries[i].csb;
    control_sensor_data_t* csd = g_active_sensor_tracker.entries[i].csd;
    // ... cleanup emergency files for this sensor ...
}
```

**Option B**: Change to per-sensor API (RECOMMENDED - consistent with recovery design)
```c
/**
 * @brief Recover from power abort for specific sensor
 *
 * Main app calls this for each sensor during startup if power abort detected.
 */
imx_result_t imx_recover_power_abort_for_sensor(imatrix_upload_source_t upload_source,
                                                imx_control_sensor_block_t* csb,
                                                control_sensor_data_t* csd);
```

**Recommended**: **Option B** - Consistent with per-sensor recovery design, no tracker needed.

### Revised Design (Option B)

**Main app integration**:
```c
// Check if power abort occurred
if (imx_power_abort_detected()) {
    // Recover each upload source's sensors
    for (i = 0; i < device_config.no_sensors; i++) {
        imx_recover_power_abort_for_sensor(IMX_UPLOAD_GATEWAY,
                                          &icb.i_scb[i], &icb.i_sd[i]);
    }
    // Same for BLE, CAN sources...
}
```

### Conclusion on Active Sensor Tracker

**Decision**: **NOT NEEDED** with correct per-sensor API design!

- STM32 RAM exhaustion: ✅ Solved with per-sensor circular buffer (Phase 3)
- Recovery: ✅ Solved with per-sensor API (Phase 2)
- Power abort: ✅ Solved with per-sensor API (Phase 4)

**Result**: Can eliminate g_sensor_array with NO replacement tracker needed!

### Revised Todo Checklist for Phase 4

- [ ] Create `imx_recover_power_abort_for_sensor(upload_source, csb, csd)` API
- [ ] Implement function to cleanup emergency files for ONE sensor
- [ ] Add to mm2_api.h public interface
- [ ] UPDATE mm2_power_abort.c to remove loops over g_sensor_array
- [ ] Main app calls new API per sensor during startup
- [ ] Update any GET_SENSOR_ID calls to use csb
- [ ] Test power abort recovery per sensor
- [ ] **Active sensor tracker NOT needed!**

---

## Phase 5: Remove g_sensor_array Completely

### Step 5.1: Remove Typedef and Extern

**File**: mm2_core.h

**Delete** (lines 183-189):
```c
/**
 * @brief Global sensor array
 */
typedef struct {
    control_sensor_data_t sensors[MAX_SENSORS];
    uint32_t active_count;
} sensor_array_t;
```

**Delete** (line 114):
```c
extern sensor_array_t g_sensor_array;
```

### Step 5.2: Remove Definition and Initialization

**File**: mm2_pool.c

**Delete** (line 60):
```c
sensor_array_t g_sensor_array = {0};
```

**Delete** from `init_memory_pool()` (lines 151-229):
```c
/* Initialize sensor array */
for (uint32_t i = 0; i < MAX_SENSORS; i++) {
    control_sensor_data_t* csd = &g_sensor_array.sensors[i];
    // ... entire initialization block ...
}
g_sensor_array.active_count = 0;
```

**Delete** from `cleanup_memory_pool()` (lines 263-275):
```c
/* Destroy all sensor locks */
for (uint32_t i = 0; i < MAX_SENSORS; i++) {
    control_sensor_data_t* csd = &g_sensor_array.sensors[i];
    // ... cleanup ...
}
```

**Delete** (line 311):
```c
memset(&g_sensor_array, 0, sizeof(g_sensor_array));
```

### Step 5.3: Remove Obsolete Helper Functions

**File**: mm2_pool.c

**Delete** `get_sensor_data()` (lines 584-594):
```c
control_sensor_data_t* get_sensor_data(uint32_t sensor_id) {
    if (sensor_id >= MAX_SENSORS) {
        return NULL;
    }
    return &g_sensor_array.sensors[sensor_id];
}
```

**Delete** `compute_active_sensor_count()` (lines 627-635):
```c
uint32_t compute_active_sensor_count(void) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < MAX_SENSORS; i++) {
        if (g_sensor_array.sensors[i].active) {
            count++;
        }
    }
    return count;
}
```

**Delete** from mm2_pool.c (lines 655-658):
```c
uint32_t get_sensor_id_from_csd(const control_sensor_data_t* csd) {
    // ... pointer arithmetic using g_sensor_array ...
}
```

### Step 5.4: Update get_sensor_id_from_csd()

**File**: mm2_pool.c

**Change** (if function is still needed):
```c
// OLD (pointer arithmetic):
uint32_t get_sensor_id_from_csd(const control_sensor_data_t* csd) {
    ptrdiff_t offset = csd - g_sensor_array.sensors;
    return (uint32_t)offset;
}

// NEW (search tracker):
uint32_t get_sensor_id_from_csd(const control_sensor_data_t* csd) {
    for (uint32_t i = 0; i < g_active_sensor_tracker.count; i++) {
        if (g_active_sensor_tracker.entries[i].csd == csd) {
            return g_active_sensor_tracker.entries[i].sensor_id;
        }
    }
    return UINT32_MAX;  // Not found
}
```

**Or BETTER**: Deprecate completely since csb should always be available with csd

### Todo Checklist for Phase 5

- [ ] Remove sensor_array_t typedef from mm2_core.h
- [ ] Remove extern g_sensor_array from mm2_core.h
- [ ] Remove g_sensor_array definition from mm2_pool.c
- [ ] Remove sensor initialization loop from init_memory_pool()
- [ ] Remove sensor cleanup loop from cleanup_memory_pool()
- [ ] Remove memset g_sensor_array from cleanup_memory_pool()
- [ ] Delete get_sensor_data() function
- [ ] Delete compute_active_sensor_count() function
- [ ] Update or delete get_sensor_id_from_csd() function
- [ ] Remove any remaining references in comments/docs

---

## Phase 6: Update Function Signatures Systematically

### CRITICAL: Verify upload_source Threading

**Before adding csb**, verify EVERY helper function already has `upload_source` parameter!

**Why**: With separate arrays per upload source, we need (upload_source, csb->id) to uniquely identify sensors.

**Audit checklist**:
```bash
# Check all helper functions have upload_source
grep -n "imx_result_t.*(" mm2_file_management.c | grep -v "upload_source"
# If any found, add upload_source as first parameter!
```

### Functions Requiring csb Parameter

All functions that use `GET_SENSOR_ID(csd)` need csb parameter added.

**CRITICAL**: Ensure upload_source is FIRST parameter, csb is SECOND, csd is THIRD for consistency!

#### mm2_file_management.c (VERIFY upload_source FIRST!)

**Function: add_spool_file_to_tracking** (line ~88)

**CRITICAL**: Verify current signature has upload_source parameter! Then add csb.

```c
// CURRENT (verify upload_source exists):
imx_result_t add_spool_file_to_tracking(control_sensor_data_t* csd,
                                       imatrix_upload_source_t upload_source,  ✓ Already has it!
                                       const char* filename,
                                       uint32_t sequence,
                                       int is_active)

// NEW (add csb between upload_source and csd for consistency):
imx_result_t add_spool_file_to_tracking(imatrix_upload_source_t upload_source,
                                       imx_control_sensor_block_t* csb,
                                       control_sensor_data_t* csd,
                                       const char* filename,
                                       uint32_t sequence,
                                       int is_active)
```

**Standard Parameter Order**: `(upload_source, csb, csd, ...other params...)`

**Call sites to update**: mm2_disk_spooling.c lines 364, 519

**Same pattern for** (VERIFY each has upload_source first):
- `delete_spool_file(upload_source, csb, csd, ...)` - verify, then add csb
- `enforce_space_limit(upload_source, csb, csd, ...)` - verify, then add csb
- `rotate_spool_file(upload_source, csb, csd, ...)` - verify, then add csb
- `delete_all_sensor_files(upload_source, csb, csd, ...)` - verify, then add csb
- `update_active_file_size(upload_source, csb, csd, ...)` - verify, then add csb
- `find_oldest_deletable_file_index(upload_source, csb, csd, ...)` - internal
- `calculate_total_spool_size(upload_source, csb, csd, ...)` - internal

#### mm2_disk_spooling.c

**Functions needing csb**:
- `write_tsd_sector_to_disk(csb, csd, ...)` - line 312
- `write_evt_sector_to_disk(csb, csd, ...)` - line 468
- `process_idle_state(csb, csd, ...)` - line 227
- `select_sectors_for_spooling(csb, csd, ...)` - line 267
- `write_sector_batch(csb, csd, ...)` - line 636
- `process_selecting_state(csb, csd, ...)` - line 603
- `process_writing_state(csb, csd, ...)` - line 687
- `process_verifying_state(csb, csd, ...)` - line 749
- `cleanup_spooled_sectors(csb, csd, ...)` - line 780
- `process_cleanup_state(csb, csd, ...)` - line 840
- `process_error_state(csb, csd, ...)` - line 878
- `process_normal_disk_spooling(csb, csd, ...)` - line 908

#### mm2_disk_reading.c

**Functions needing csb**:
- `get_oldest_readable_file_index(csb, csd, ...)` - line 77
- `open_disk_file_for_reading(csb, csd, ...)` - line 98
- `read_next_disk_sector(csb, csd, ...)` - line 137
- `cleanup_fully_acked_files(csb, csd, ...)` - line 367

#### mm2_power.c

**Functions** (if they use GET_SENSOR_ID):
- Check all functions and add csb where needed

### Todo Checklist for Phase 6

- [ ] **FIRST**: Audit ALL helper functions - verify upload_source parameter exists
- [ ] If upload_source missing from any function, add it as FIRST parameter
- [ ] List all functions using GET_SENSOR_ID
- [ ] Add csb parameter to each function signature (after upload_source)
- [ ] Update function documentation to clarify (upload_source, csb->id) tuple
- [ ] Find all call sites for each function
- [ ] Update each call site to pass (upload_source, csb, csd, ...)
- [ ] Verify csb AND upload_source available at all call sites
- [ ] If either unavailable, redesign call chain
- [ ] Ensure parameter order: (upload_source, csb, csd, ...other)

---

## Phase 7: Update mm2_disk.h Function Declarations

All public functions in mm2_disk.h need signature updates to match implementation.

### Step 7.1: Update Recovery Function Declarations (UPDATED for Multi-Source)

**File**: mm2_disk.h / mm2_api.h

**Change**:
```c
// Add new API - MUST include upload_source parameter:
/**
 * @brief Recover disk-spooled data for specific sensor in specific upload source
 *
 * Main application must call this for each active sensor in each upload source.
 * Scans the upload source's directory for this sensor's spool files.
 *
 * @param upload_source Upload source (determines which directory to scan)
 * @param csb Sensor configuration (csb->id identifies sensor within this source)
 * @param csd Sensor data (contains mmcb state)
 * @return IMX_SUCCESS on success, error code (non-fatal) on failure
 */
imx_result_t imx_recover_sensor_disk_data(imatrix_upload_source_t upload_source,
                                          imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd);

// Deprecate old:
imx_result_t recover_disk_spooled_data(void) __attribute__((deprecated));
```

**Main app usage**:
```c
// Gateway sensors
for (i = 0; i < device_config.no_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i]);
}

// BLE sensors (if applicable)
for (i = 0; i < no_ble_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_BLE_DEVICE, &ble_scb[i], &ble_sd[i]);
}

// CAN sensors (if applicable)
for (i = 0; i < no_can_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_CAN_DEVICE, &can_scb[i], &can_sd[i]);
}
```

### Step 7.2: Update Helper Function Declarations

All helper functions in mm2_disk.h need csb parameter added to match new signatures.

### Todo Checklist for Phase 7

- [ ] Update all function declarations in mm2_disk.h
- [ ] Ensure signatures match implementation
- [ ] Add deprecation warnings where appropriate

---

## Verification and Testing

### Static Verification Commands

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl

# 1. Verify no g_sensor_array references (except docs)
grep -rn "g_sensor_array" mm2_*.c mm2_*.h
# Expected: 0 in code, only in comments

# 2. Verify GET_SENSOR_ID uses csb
grep -rn "GET_SENSOR_ID(csd)" mm2_*.c
# Expected: 0

grep -rn "GET_SENSOR_ID(csb)" mm2_*.c
# Expected: 34

# 3. Verify active tracker used
grep -rn "g_active_sensor_tracker" mm2_*.c
# Expected: ~20 (register/unregister/search)

# 4. Check for unused variable warnings
make -j4 2>&1 | grep "unused variable.*csd"
# Expected: 0
```

### Compilation Verification

```bash
# Clean build
make clean
make -j4 2>&1 | tee refactor_build.log

# Check for errors related to refactoring
grep -E "(g_sensor_array|GET_SENSOR_ID.*csd)" refactor_build.log
# Expected: 0 matches
```

### Runtime Testing Checklist

- [ ] Test with main app passing icb.i_sd[] pointers
- [ ] Verify GET_SENSOR_ID returns correct csb->id
- [ ] Test sensor activation/deactivation updates tracker
- [ ] Test STM32 RAM exhaustion finds oldest across sensors
- [ ] Test recovery scans correct sensor ID directories
- [ ] Test power abort recovery cleans correct files

---

## File-by-File Change Summary

| File | Changes | Lines Modified |
|:-----|:--------|:---------------|
| mm2_core.h | Fix GET_SENSOR_ID, remove g_sensor_array typedef/extern | ~10 |
| mm2_pool.c | Remove array init/cleanup, remove helper functions | ~100 |
| mm2_api.c | Remove global recovery call | ~5 |
| mm2_startup_recovery.c | New per-sensor API, remove array lookups | ~50 |
| mm2_disk_spooling.c | Add csb params to 12 functions, update calls | ~30 |
| mm2_file_management.c | Add csb params to 8 functions, update calls | ~25 |
| mm2_disk_reading.c | Add csb params to 4 functions, update calls | ~10 |
| mm2_write.c | Add RAM full handling with discard + retry | ~15 |
| mm2_stm32.c | Replace cross-sensor search with per-sensor discard | ~30 |
| mm2_power_abort.c | Change to per-sensor API, remove loops | ~15 |
| mm2_power.c | Add csb params where needed | ~5 |
| mm2_disk.h | Update all function declarations | ~20 |
| mm2_api.h | Add new recovery and power abort APIs | ~20 |

**Total**: ~335 lines across 13 files (REDUCED complexity - no tracker code!)

---

## Migration Sequence (Recommended Order - REVISED)

### Safe Migration Path

1. **Phase 1** (GET_SENSOR_ID macro) - Foundation: change to `csb->id`
2. **Phase 6** (Function signatures) - Add csb parameters to helper functions
3. **Phase 3** (STM32 circular buffer) - Per-sensor RAM exhaustion handling
4. **Phase 2** (Recovery redesign) - Per-sensor recovery API
5. **Phase 4** (Power abort) - Per-sensor power abort API
6. **Phase 5** (Remove g_sensor_array) - Final deletion
7. **Phase 7** (Update headers) - Ensure consistency

**Key Change**: Phase 3 and 4 simplified - NO active sensor tracker needed!

### Alternative: Big Bang Migration

Do all phases simultaneously if confident in analysis. Higher risk but faster.

**Recommended**: Safe migration path with compilation check after each phase.

### Critical Success Factor

**ALL phases rely on**: `upload_source` parameter already present in functions.

**Before starting Phase 1**: Verify upload_source is threaded through all helper functions!

---

## Rollback Strategy

### Git Checkpoints

Create commit after each successful phase:
```bash
git add -u
git commit -m "Phase N: <description> - compiles successfully"
```

### Full Rollback

```bash
git checkout HEAD~7  # Rollback all 7 phases
# Or:
git revert <commit-hash>  # Revert specific phase
```

---

## Expected Benefits

### 1. Architectural Correctness ✓
- MM2 no longer maintains shadow state
- Main app retains full sensor management control
- API contract honored: (upload_source, csb, csd) passed by caller
- **True stateless design**: MM2 only manages global memory pool and per_source_disk state

### 2. Memory Reduction (CORRECTED - No Tracker Needed!)
- **Before**: g_sensor_array = 500 × sizeof(control_sensor_data_t) ≈ 500 × 500 bytes = 250KB
- **After**: **NOTHING** - no replacement tracker needed!
- **Savings**: ~250KB (100% elimination)

**Why no tracker needed**:
- STM32 RAM exhaustion: Per-sensor circular buffer (caller has csd in scope)
- Recovery: Per-sensor API (main app calls for each sensor)
- Power abort: Per-sensor API (main app calls for each sensor)
- **Result**: MM2 never needs to iterate all sensors internally!

### 3. Bug Elimination
- Pointer arithmetic bug fixed
- No more dual state management confusion
- Recovery works with any csd pointer from any upload source array
- Sensor ID collision across upload sources properly handled

### 4. Maintainability
- Clear ownership: main app owns sensors, MM2 provides services
- Simpler mental model: MM2 is truly stateless (just memory pool + per_source_disk)
- Easier debugging: single sensor array per upload source (in main app)
- Consistent API: (upload_source, csb, csd, ...) everywhere

### 5. Multi-Source Support
- Properly handles separate sensor arrays per upload source
- Sensor ID scoped correctly within upload source
- File operations use correct upload source directory
- No conflicts between upload sources with same sensor IDs

---

## Main Application Integration (UPDATED for Multi-Source)

### Required Changes in Main App

#### 1. Call Recovery Per-Upload-Source, Per-Sensor

**Add to initialization** (after `imx_memory_manager_init()`):
```c
// CRITICAL: Recover disk data for EACH upload source's sensors
// Each upload source has its own sensor arrays

// Gateway sensors
for (uint16_t i = 0; i < device_config.no_sensors; i++) {
    imx_result_t result = imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY,
                                                       &icb.i_scb[i],
                                                       &icb.i_sd[i]);
    if (result != IMX_SUCCESS) {
        imx_printf("Gateway sensor %u recovery failed: %d\n", icb.i_scb[i].id, result);
    }
}

#ifdef BLE_PLATFORM
// BLE device sensors (separate array)
for (uint16_t i = 0; i < no_ble_sensors; i++) {
    imx_result_t result = imx_recover_sensor_disk_data(IMX_UPLOAD_BLE_DEVICE,
                                                       &ble_scb[i],
                                                       &ble_sd[i]);
    if (result != IMX_SUCCESS) {
        imx_printf("BLE sensor %u recovery failed: %d\n", ble_scb[i].id, result);
    }
}
#endif

#ifdef CAN_PLATFORM
// CAN device sensors (separate array)
for (uint16_t i = 0; i < no_can_sensors; i++) {
    imx_result_t result = imx_recover_sensor_disk_data(IMX_UPLOAD_CAN_DEVICE,
                                                       &can_scb[i],
                                                       &can_sd[i]);
    if (result != IMX_SUCCESS) {
        imx_printf("CAN sensor %u recovery failed: %d\n", can_scb[i].id, result);
    }
}
#endif
```

#### 2. Verify All MM2 API Calls Include upload_source

MM2 API already receives (upload_source, csb, csd) correctly:
- `imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i], value)` ✓
- `imx_write_tsd(IMX_UPLOAD_BLE_DEVICE, &ble_scb[i], &ble_sd[i], value)` ✓
- `imx_read_next_tsd_evt(upload_source, csb, csd, &data)` ✓
- `imx_activate_sensor(upload_source, csb, csd)` ✓

**No changes needed** - upload_source already threaded through all APIs!

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|:-----|:-----------|:-------|:-----------|
| Missed g_sensor_array reference | Low | High | Automated grep verification |
| Function signature mismatch | Medium | High | Update headers before impl |
| STM32 RAM exhaustion regression | Low | Critical | Comprehensive testing |
| Main app integration issues | Medium | Medium | Clear migration guide |
| GET_SENSOR_ID wrong at call site | Low | High | Compile-time type checking |

---

## Success Criteria

- [ ] Zero references to `g_sensor_array` in mm2_*.c files
- [ ] Zero uses of `GET_SENSOR_ID(csd)`
- [ ] All uses are `GET_SENSOR_ID(csb)` (34 total)
- [ ] Active sensor tracker properly maintained
- [ ] STM32 RAM exhaustion works with tracker
- [ ] Recovery works per-sensor with main app's csd
- [ ] Clean compilation with zero warnings
- [ ] Memory reduced by ~248KB
- [ ] All mm2 API functions receive csb/csd from caller

---

## Estimated Effort

- **Analysis and planning**: 2 hours ✓ (COMPLETE)
- **Phase 1 implementation**: 2 hours
- **Phase 3 implementation**: 2 hours
- **Phase 6 implementation**: 3 hours
- **Phase 2 implementation**: 1 hour
- **Phase 4 implementation**: 1 hour
- **Phase 5 implementation**: 1 hour
- **Testing and verification**: 2 hours

**Total**: ~14 hours

---

## Appendix A: Complete g_sensor_array Reference List

### mm2_pool.c (8 references)
1. Line 60: Definition `sensor_array_t g_sensor_array = {0};`
2. Line 155: Init loop `csd = &g_sensor_array.sensors[i];`
3. Line 175: Cleanup loop `&g_sensor_array.sensors[j]`
4. Line 229: Reset count `g_sensor_array.active_count = 0;`
5. Line 267: Cleanup loop `csd = &g_sensor_array.sensors[i];`
6. Line 311: Memset `memset(&g_sensor_array, ...)`
7. Line 593: get_sensor_data `return &g_sensor_array.sensors[sensor_id];`
8. Line 632: compute count `g_sensor_array.sensors[i].active`
9. Line 655: Pointer arithmetic `csd - g_sensor_array.sensors`

### mm2_startup_recovery.c (4 references)
1. Line 124: `csd = &g_sensor_array.sensors[sensor_id];` (unused!)
2. Line 355: `csd = &g_sensor_array.sensors[sensor_id];` (unused!)
3. Line 466: `csd = &g_sensor_array.sensors[sensor_id];` (unused!)
4. Line 550: `csd = &g_sensor_array.sensors[sensor_id];` (actually used)

### mm2_stm32.c (6 references)
1. Line 75: `owner = &g_sensor_array.sensors[owner_sensor_id];`
2. Line 92: Loop `csd = &g_sensor_array.sensors[i];`
3. Line 135: Loop `csd = &g_sensor_array.sensors[i];`
4. Line 177: `csd = &g_sensor_array.sensors[sensor_id];`
5. Line 218: Loop `csd = &g_sensor_array.sensors[i];`
6. Line 241: `owner = &g_sensor_array.sensors[owner_sensor_id];`

### mm2_power_abort.c (2 references)
1. Line 199: Loop `csd = &g_sensor_array.sensors[i];`
2. Line 361: Loop `csd = &g_sensor_array.sensors[i];`

### mm2_core.h (3 references)
1. Line 186: Typedef definition
2. Line 202: GET_SENSOR_ID macro
3. Line 114: Extern declaration

**Total**: 23 code references + macro definition + typedef

---

## Appendix B: GET_SENSOR_ID Usage Locations

All 34 occurrences of `GET_SENSOR_ID(csd)` in logging/diagnostic code:

### mm2_disk_spooling.c (14 uses)
Lines: 244, 299, 348, 352, 404, 503, 507, 555, 676, 714, 740, 769, 831, 862, 867, 883, 887, 920, 957

### mm2_file_management.c (11 uses)
Lines: 103, 125, 172, 246, 258, 263, 305, 330, 355, 411, 425

### mm2_power.c (2 uses)
Lines: 175, 455

### mm2_disk_reading.c (1 use)
Lines: 271

### mm2_power_abort.c (1 use)
Line: 173

**Pattern**: All uses are for logging sensor ID in debug/info messages.

---

## Appendix C: Multi-Source Verification Commands

### Verify upload_source in All Helper Functions

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl

# Find all function definitions
grep -n "^imx_result_t\|^int\|^uint32_t\|^void" mm2_file_management.c | \
  grep -v "upload_source"

# Expected: Only static/inline functions or functions that genuinely don't need it
```

### Verify Standard Parameter Order

```bash
# Check all public API functions have correct order
grep -A2 "^imx_result_t imx_" mm2_api.c | \
  grep -E "imatrix_upload_source_t|control_sensor_data_t"

# Expected: upload_source always first, then csb/csd in that order
```

### Verify Active Sensor Tracker Has upload_source

```bash
# Check typedef includes upload_source field
grep -A5 "typedef struct.*active_sensor_entry" mm2_core.h | \
  grep "upload_source"

# Expected: imatrix_upload_source_t upload_source; field present
```

### Runtime Verification (After Implementation)

```c
// Test with multiple upload sources
printf("Activating Gateway sensor 5\n");
imx_activate_sensor(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5]);

printf("Activating BLE sensor 5\n");
imx_activate_sensor(IMX_UPLOAD_BLE_DEVICE, &ble_scb[5], &ble_sd[5]);

printf("Active tracker count: %u (should be 2)\n", g_active_sensor_tracker.count);

// Verify tracker has both:
for (i = 0; i < g_active_sensor_tracker.count; i++) {
    printf("  [%u]: source=%d, sensor_id=%u\n",
           i,
           g_active_sensor_tracker.entries[i].upload_source,
           g_active_sensor_tracker.entries[i].sensor_id);
}
// Expected output:
//   [0]: source=0 (GATEWAY), sensor_id=5
//   [1]: source=2 (BLE_DEVICE), sensor_id=5
```

---

## Critical Warnings

### ⚠️ WARNING 1: Sensor ID Collision Across Upload Sources

```
Gateway sensor ID 5 and BLE sensor ID 5 are DIFFERENT sensors!
They may have the same csb->id but belong to different upload sources.
Always use (upload_source, csb->id) tuple for identification.
```

### ⚠️ WARNING 2: upload_source Must Be Passed to ALL Functions

```
Do NOT assume upload_source from context or global state!
Every function that accesses files or per_source_disk[] MUST
receive upload_source as explicit parameter.
```

### ⚠️ WARNING 3: Parameter Order is Critical

```
Standard order: (upload_source, csb, csd, ...other)
Inconsistent order will cause bugs and make code unmaintainable.
```

### ⚠️ WARNING 4: Recovery Must Be Called Per-Source

```
Main app must call imx_recover_sensor_disk_data() separately for:
- Each upload source (gateway, BLE, CAN, etc.)
- Each sensor within that upload source

Missing any upload source = data loss on reboot!
```

---

---

## Final Summary: Pure Stateless MM2 Design

### MM2 Global State (After Refactoring)

**Only 2 global structures**:
1. `g_memory_pool` - Sector storage + chain table + free list
2. `icb.per_source_disk[upload_source]` - Disk spooling state per upload source

**NO internal sensor arrays** - MM2 is truly stateless!

### MM2 API Contract

**Every public function receives**:
```c
(imatrix_upload_source_t upload_source,
 imx_control_sensor_block_t* csb,
 control_sensor_data_t* csd,
 ...operation-specific params...)
```

**MM2 never**:
- Maintains sensor arrays
- Searches across sensors (except per-sensor chain traversal)
- Stores sensor configuration (csb) or data (csd)

**MM2 only**:
- Manages global memory pool (sectors + chains)
- Manages per-upload-source disk state
- Provides services when called with (upload_source, csb, csd) tuple

### Integration Model

**Main app**:
- Maintains separate csb/csd arrays per upload source
- Iterates its own arrays
- Calls MM2 API once per sensor with correct parameters
- Manages sensor lifecycle (activate/deactivate)
- Controls recovery and power-down operations

**MM2**:
- Receives (upload_source, csb, csd) from every call
- Uses csb->id as sensor identifier
- Uses upload_source for file paths and disk state
- Never needs to know about other sensors

**Result**: Clean separation of concerns, zero shadow state!

---

*Document Version: 3.0*
*Created: 2025-10-13*
*Updated: 2025-10-13 - Corrected STM32 RAM design, eliminated active tracker*
*Status: READY FOR IMPLEMENTATION*
*Complexity: REDUCED - Simpler than original plan!*
