# COMPREHENSIVE REFACTORING PROMPT: MM2 Memory Manager - Architectural Corrections

**CONTEXT and ENVIRONMENT:** You are operating as an AI assistant within a modern IDE environment with full access to the project file system.

**ROLE:** You are a **Principal Embedded Systems Architect** specializing in STM32 and i.MX 6 Linux development. You have deep expertise in stateless service design, multi-tenant architecture patterns, and embedded memory management.

**TASK TYPE:** Comprehensive architectural refactoring addressing multiple related design flaws in the MM2 Memory Manager module.

---

## PART 1: SYSTEM ARCHITECTURE (CRITICAL CONTEXT)

### 1.1 System Component Diagram

```
Main Application (Fleet-Connect-1, iMatrix Core)
├─ Gateway Sensors: icb.i_scb[25], icb.i_sd[25]
├─ BLE Device Sensors: ble_scb[128], ble_sd[128]
└─ CAN Device Sensors: can_scb[N], can_sd[N]
    ↓ (API calls with pointers)
    ↓
MM2 Memory Manager (Stateless Service)
├─ Global Memory Pool (sectors + chains)
└─ Per-Source Disk State: icb.per_source_disk[upload_source]
    ↓ (system calls)
    ↓
Linux Filesystem / STM32 Flash
```

**Key Principle**: Main app owns ALL sensor data, MM2 provides memory management services when called with (upload_source, csb*, csd*) parameters.

### 1.2 Multi-Source Architecture (CRITICAL)

The iMatrix system supports multiple independent upload sources, each with **separate sensor arrays**:

**IMX_UPLOAD_GATEWAY** (0):
- Configuration array: `icb.i_scb[]` (imx_control_sensor_block_t)
- Runtime data array: `icb.i_sd[]` (control_sensor_data_t)
- Directory: `/usr/qk/var/mm2/gateway/`
- Example: Gateway sensor with csb->id = 5

**IMX_UPLOAD_BLE_DEVICE** (2):
- Configuration array: `ble_scb[]`
- Runtime data array: `ble_sd[]`
- Directory: `/usr/qk/var/mm2/ble/`
- Example: BLE sensor with csb->id = 5 (DIFFERENT sensor than gateway!)

**IMX_UPLOAD_CAN_DEVICE** (4):
- Configuration array: `can_scb[]`
- Runtime data array: `can_sd[]`
- Directory: `/usr/qk/var/mm2/can/`
- Example: CAN sensor with csb->id = 5 (DIFFERENT sensor than gateway/BLE!)

**CRITICAL INSIGHT**:
- Sensor ID (csb->id) is unique WITHIN an upload source, NOT globally
- Gateway sensor 5, BLE sensor 5, CAN sensor 5 are three DIFFERENT sensors
- Unique identifier: (upload_source, csb->id) tuple
- Files: `/usr/qk/var/mm2/{gateway|ble|can}/sensor_{id}_seq_{N}.dat`

### 1.3 API Contract Specification

**ALL MM2 public functions follow this pattern**:

```c
imx_result_t mm2_function(
    imatrix_upload_source_t upload_source,  // Which source (GATEWAY, BLE, CAN)
    imx_control_sensor_block_t* csb,        // Sensor config (from caller's array)
    control_sensor_data_t* csd,             // Sensor data (from caller's array)
    ...operation_specific_parameters...
);
```

**Parameter Meanings**:
- **upload_source**: Determines which directory for disk files, which per_source_disk[] entry
- **csb**: Sensor configuration (name, id, sample_rate, etc.) - **csb->id is sensor ID truth source**
- **csd**: Sensor runtime data (last_sample, no_samples, **csd->mmcb** is MM2 per-sensor state)

**Concrete Examples**:

```c
// Gateway sensor 5:
imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], value);

// BLE sensor 10:
imx_write_tsd(IMX_UPLOAD_BLE_DEVICE, &ble_scb[10], &ble_sd[10], value);

// CAN sensor 3:
imx_write_tsd(IMX_UPLOAD_CAN_DEVICE, &can_scb[3], &can_sd[3], value);

// All valid, potentially concurrent!
```

**Critical Requirement**: MM2 must work correctly when called with pointers from **ANY** of the main app's arrays, not just one internal array.

### 1.4 Data Ownership Model

| Structure | Owner | Location | Access | Truth Source |
|-----------|-------|----------|--------|--------------|
| **imx_control_sensor_block_t** (csb) | Main App | icb.i_scb[], ble_scb[], can_scb[] | Passed as param | csb->id for sensor ID |
| **control_sensor_data_t** (csd) | Main App | icb.i_sd[], ble_sd[], can_sd[] | Passed as param | csd->mmcb for MM2 state |
| **imx_mmcb_t** (mmcb) | MM2 | Embedded in csd->mmcb | Direct access | Per-sensor MM2 state |
| **per_source_disk_state_t** | MM2 | icb.per_source_disk[source] | Via extern icb | Per-upload-source disk state |
| **global_memory_pool_t** | MM2 | g_memory_pool | Direct access | Global RAM sectors + chains |
| **iMatrix_Control_Block_t** (icb) | Main App | Global singleton | Via extern icb | Device-level state |

**Ownership Rules**:
- ✅ Main app owns csb/csd arrays, passes pointers to MM2
- ✅ MM2 owns memory pool and per_source_disk state
- ✅ MM2 stores per-sensor state in csd->mmcb (embedded, not separate array)
- ❌ MM2 MUST NOT duplicate csb/csd in internal arrays
- ❌ MM2 MUST NOT assume csb/csd come from specific array

### 1.5 Design Principles for MM2

**1. Stateless Service**:
- MM2 provides memory management services
- Does NOT maintain sensor configuration or sensor data
- Operates on csb/csd passed by caller

**2. No Data Duplication**:
- Main app already has sensor arrays
- MM2 must NOT create shadow copies
- Single source of truth per data item

**3. Multi-Source Support**:
- All operations partitioned by upload_source
- Same sensor ID can exist in different upload sources
- File paths include upload_source directory

**4. Caller Context Utilization**:
- When MM2 needs to operate on a sensor, caller provides (upload_source, csb, csd)
- MM2 should NOT search for sensors or maintain sensor lists
- Per-sensor operations use parameters, not global lookups

**5. Truth Source Identification**:
- Sensor ID: **csb->id** (NOT pointer arithmetic, NOT array index)
- Upload source: **Function parameter** (NOT global state)
- Per-sensor MM2 state: **csd->mmcb** (NOT separate array)
- Per-source disk state: **icb.per_source_disk[upload_source]** (NOT per-sensor)

---

## PART 2: PROBLEM INVENTORY (ALL KNOWN ISSUES)

### 2.1 PRIMARY ISSUE: per_source_disk_state_s Incorrectly Nested

**Current State**:
```c
typedef struct imx_mmcb {
    // ...
    struct per_source_disk_state_s {
        char active_spool_filename[256];
        int active_spool_fd;
        // ... ~3KB of disk state ...
    } per_source[IMX_UPLOAD_NO_SOURCES];  // ← WRONG! Duplicated per-sensor
} imx_mmcb_t;

typedef struct control_sensor_data {
    imx_mmcb_t mmcb;  // ← Contains per_source[] array
} control_sensor_data_t;
```

**Problem**:
- per_source[] is embedded in imx_mmcb_t
- imx_mmcb_t is embedded in control_sensor_data_t
- Result: Each sensor has its own copy of per_source[] (25 sensors × 4 sources × 3KB = 300KB waste)

**Correct State**:
```c
// Standalone typedef:
typedef struct per_source_disk_state_s {
    char active_spool_filename[256];
    int active_spool_fd;
    // ... disk state ...
} per_source_disk_state_t;

// Device-level, NOT per-sensor:
typedef struct icb_data_ {
    // ...
    per_source_disk_state_t per_source_disk[IMX_UPLOAD_NO_SOURCES];  // ← Correct location
} iMatrix_Control_Block_t;
```

**Impact**:
- Memory waste: 288KB
- Logical error: Disk state is device-level, not per-sensor
- Already partially fixed in previous refactoring

**Status**: ✅ FIXED in prior refactoring (included here for completeness)

### 2.2 RELATED ISSUE: g_sensor_array Shadow Duplicate

**Current State**:
```c
// In mm2_core.h:
typedef struct {
    control_sensor_data_t sensors[MAX_SENSORS];  // 500 sensors!
    uint32_t active_count;
} sensor_array_t;

extern sensor_array_t g_sensor_array;

// In mm2_pool.c:
sensor_array_t g_sensor_array = {0};  // Allocates 500 × 500 bytes = 250KB

// In mm2_pool.c init_memory_pool():
for (uint32_t i = 0; i < MAX_SENSORS; i++) {
    control_sensor_data_t* csd = &g_sensor_array.sensors[i];
    // Initialize each entry...
}
```

**Problem**:
- MM2 maintains internal array of 500 control_sensor_data_t structures
- Main app already has separate arrays: icb.i_sd[], ble_sd[], can_sd[]
- **Shadow duplicate**: Two copies of sensor data!
- **API violation**: MM2 API receives csb/csd from caller but uses internal array

**Why This Is Wrong**:
1. **Duplication**: Main app and MM2 both store sensor data
2. **Inconsistency**: Which is truth source? Main app's or MM2's?
3. **Waste**: 250KB for unused array (main app doesn't use g_sensor_array)
4. **Multi-source violation**: Single 500-element array can't represent separate per-source arrays

**Correct State**:
- **NO g_sensor_array** - delete completely
- MM2 uses csb/csd pointers passed by caller
- Main app manages sensor arrays, MM2 provides services

**Impact**:
- Memory waste: 250KB
- API contract violation: Critical
- Runtime crash risk: High (see next issue)

**Status**: ❌ NOT YET FIXED - Primary target of this refactoring

### 2.3 DEPENDENT BUG: GET_SENSOR_ID Pointer Arithmetic

**Current State**:
```c
// mm2_core.h line 202:
#define GET_SENSOR_ID(csd) ((uint32_t)((csd) - g_sensor_array.sensors))
```

**Problem**:
- Macro assumes csd pointer originates from g_sensor_array
- Uses pointer subtraction to calculate array index
- **FAILS** when main app passes csd from icb.i_sd[], ble_sd[], or can_sd[]

**Failure Example**:
```c
// Main app code:
imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], value);

// Inside MM2 (somewhere deep in call stack):
uint32_t sensor_id = GET_SENSOR_ID(csd);
// Expands to: ((icb.i_sd[5]) - g_sensor_array.sensors)
// Result: GARBAGE! Undefined pointer arithmetic across different arrays
// Crash, corruption, or wrong sensor ID
```

**Correct State**:
```c
// mm2_core.h:
#define GET_SENSOR_ID(csb) ((csb)->id)  // Truth source!
```

**Impact**:
- Runtime crash: High probability
- Data corruption: Possible
- Undefined behavior: Certain

**Usage**: 34 occurrences across 7 mm2 files (all for logging/diagnostics)

**Status**: ❌ NOT YET FIXED - Must fix as part of g_sensor_array removal

### 2.4 DEPENDENT ISSUE: Recovery Functions Use Internal Array

**Current State**:
```c
// mm2_startup_recovery.c:
imx_result_t recover_disk_spooled_data(void) {  // NO PARAMETERS!
    for (uint32_t sensor_id = 0; sensor_id < MAX_SENSORS; sensor_id++) {
        control_sensor_data_t* csd = &g_sensor_array.sensors[sensor_id];
        // Scan files for this sensor...
    }
}
```

**Problem**:
- Loops over MM2's internal array (which main app doesn't use)
- No parameters - can't be called per-sensor by main app
- Doesn't respect multi-source architecture
- Assumes sensor_id as array index, not csb->id

**Multi-Source Violation**:
- Should scan Gateway sensors' directories: `/usr/qk/var/mm2/gateway/sensor_{id}_...`
- Should scan BLE sensors' directories: `/usr/qk/var/mm2/ble/sensor_{id}_...`
- Current design can't distinguish upload sources

**Correct State**:
```c
// Per-sensor, per-source API:
imx_result_t imx_recover_sensor_disk_data(
    imatrix_upload_source_t upload_source,  // Which source's directory to scan
    imx_control_sensor_block_t* csb,        // Sensor config (csb->id is sensor ID)
    control_sensor_data_t* csd              // Sensor data (csd->mmcb state)
);

// Main app calls:
for (i = 0; i < device_config.no_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i]);
}
```

**Impact**:
- Functional incorrectness: Won't scan correct directories
- Multi-source support: Broken
- Integration: Requires main app changes

**Status**: ❌ NOT YET FIXED - Redesign required

### 2.5 DEPENDENT ISSUE: STM32 RAM Exhaustion Cross-Sensor Search

**Current State**:
```c
// mm2_stm32.c:
imx_result_t handle_stm32_ram_full(uint32_t requesting_sensor_id) {
    // Search ALL sensors to find oldest data to discard
    for (uint32_t i = 0; i < MAX_SENSORS; i++) {
        control_sensor_data_t* csd = &g_sensor_array.sensors[i];
        // ... find oldest sector across all sensors ...
    }
}
```

**Problem**:
- Searches MM2's internal array (violates statelessness)
- Over-engineered: caller already has (upload_source, csb, csd) in scope!
- When allocation fails in imx_write_tsd(), the CALLER knows which sensor needs space

**Correct State (Per-Sensor Circular Buffer)**:
```c
// In imx_write_tsd (caller already has upload_source, csb, csd):
SECTOR_ID_TYPE new_sector = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
if (new_sector == NULL_SECTOR_ID) {
    #ifndef LINUX_PLATFORM
    // STM32: RAM full - discard oldest from THIS sensor's chain
    imx_result_t result = discard_oldest_non_pending_sector(csd);
    if (result == IMX_SUCCESS) {
        new_sector = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);  // Retry
    }
    #endif
}
```

**Benefits of Correction**:
- Simpler: No cross-sensor search
- Correct: Uses caller's context
- Fair: Each sensor manages its own quota
- No global state needed

**Impact**:
- Architectural correctness: Critical
- Complexity reduction: Significant

**Status**: ❌ NOT YET FIXED - Redesign required

### 2.6 Summary of All Issues

| Issue | Type | Memory Impact | Severity | Dependency |
|-------|------|---------------|----------|------------|
| 1. per_source_disk nesting | Structure | 288KB waste | High | None |
| 2. g_sensor_array duplicate | Architecture | 250KB waste | Critical | None |
| 3. GET_SENSOR_ID bug | Runtime bug | 0KB | Critical | Depends on #2 |
| 4. Recovery function | Functional | 0KB | High | Depends on #2 |
| 5. STM32 RAM exhaustion | Design | 0KB | Medium | Depends on #2 |

**Total Memory Waste**: 538KB (288KB + 250KB)
**Critical Bugs**: 2 (g_sensor_array, GET_SENSOR_ID)
**Related Issues**: 3 (recovery, STM32, power abort)

**Refactoring Scope**: Must fix ALL issues, not just #1.

---

## PART 3: DESIGN GOALS AND PRINCIPLES

### 3.1 Architectural Principles (Must Follow)

**1. MM2 is a Stateless Service**:
- Provides memory management services
- Does NOT own sensor configuration or data
- Only owns: memory pool + per_source_disk state

**2. Zero Data Duplication**:
- Each piece of data has ONE owner
- Main app owns sensors, MM2 provides services
- NO shadow arrays, NO internal copies

**3. Caller Context Utilization**:
- Caller provides (upload_source, csb, csd) with every call
- MM2 uses these parameters, not internal lookups
- Per-sensor operations: use csd parameter
- Cross-sensor operations: redesign as per-sensor APIs called by main app

**4. Multi-Source Correctness**:
- Support separate sensor arrays per upload source
- (upload_source, csb->id) tuple uniquely identifies sensors
- File operations use upload_source for directory selection
- No global sensor ID assumptions

### 3.2 Truth Sources (Authoritative)

**Sensor ID**:
- **Truth source**: `csb->id` (field in sensor configuration)
- **Access**: Direct field access
- **Scope**: Unique within upload_source
- ❌ **NOT**: Pointer arithmetic from array
- ❌ **NOT**: Array index

**Upload Source**:
- **Truth source**: Function parameter passed by caller
- **Access**: Function parameter
- **Scope**: Determines which directory, which per_source_disk[] entry
- ❌ **NOT**: Global variable
- ❌ **NOT**: Inferred from context

**Sensor Configuration**:
- **Truth source**: csb parameter from caller
- **Access**: Passed as pointer
- **Owner**: Main application
- ❌ **NOT**: Internal MM2 copy

**Sensor Runtime Data**:
- **Truth source**: csd parameter from caller
- **Access**: Passed as pointer
- **Owner**: Main application (but csd->mmcb owned by MM2)
- ❌ **NOT**: Internal MM2 copy

### 3.3 Success Metrics

**Memory**:
- [ ] Total savings ≥ 538KB (288KB + 250KB)
- [ ] per_source_disk: Device-level (4 instances, not 100)
- [ ] g_sensor_array: Deleted (0 bytes, not 250KB)
- [ ] No shadow state remaining

**Correctness**:
- [ ] MM2 works with csb/csd from ANY main app array
- [ ] Multi-source operation (gateway + BLE + CAN simultaneously)
- [ ] Sensor ID collision handled correctly (source 0 sensor 5 ≠ source 2 sensor 5)
- [ ] Zero pointer arithmetic bugs

**API Compliance**:
- [ ] All functions receive (upload_source, csb, csd) from caller
- [ ] MM2 never maintains internal sensor arrays
- [ ] Per-sensor APIs replace global loops

**Code Quality**:
- [ ] Clean compilation (zero warnings)
- [ ] Zero references to g_sensor_array in code
- [ ] Standard parameter order: (upload_source, csb, csd, ...)

---

## PART 4: COMPREHENSIVE REFACTORING REQUIREMENTS

### 4.1 Issue #1: Move per_source_disk_state_s (ALREADY COMPLETED)

**Note**: This was completed in prior refactoring. Including here for completeness.

**Changes Made**:
- ✅ Created standalone `per_source_disk_state_t` typedef in common.h
- ✅ Added `per_source_disk[IMX_UPLOAD_NO_SOURCES]` to iMatrix_Control_Block_t
- ✅ Removed nested `per_source[]` from imx_mmcb_t
- ✅ Updated 266 code references: `csd->mmcb.per_source[]` → `icb.per_source_disk[]`
- ✅ Added `init_global_disk_state()` initialization function

**Result**: 288KB memory saved, compilation successful.

### 4.2 Issue #2: Remove g_sensor_array (PRIMARY TASK)

**Structural Changes Required**:

**File: mm2_core.h**
- [ ] DELETE typedef sensor_array_t (lines 186-189)
- [ ] DELETE extern g_sensor_array declaration (line 114)
- [ ] ADD active sensor tracker typedef (optional, see Issue #5)

**File: mm2_pool.c**
- [ ] DELETE g_sensor_array definition (line 60)
- [ ] DELETE sensor initialization loop from init_memory_pool() (lines 151-229)
- [ ] DELETE sensor cleanup loop from cleanup_memory_pool() (lines 263-283)
- [ ] DELETE memset g_sensor_array (line 311)
- [ ] DELETE function: get_sensor_data() (lines 593-594)
- [ ] DELETE function: compute_active_sensor_count() (lines 632-635)
- [ ] UPDATE or DELETE: get_sensor_id_from_csd() (lines 655-658)

**File: mm2_startup_recovery.c**
- [ ] DELETE unused csd lookups: `csd = &g_sensor_array.sensors[sensor_id]` (lines 124, 355, 466)
- [ ] UPDATE line 550 to use csd parameter instead of lookup

**File: mm2_stm32.c**
- [ ] UPDATE all loops over g_sensor_array (lines 75, 92, 135, 177, 218, 241)
- [ ] See Issue #5 for redesign

**File: mm2_power_abort.c**
- [ ] UPDATE loops over g_sensor_array (lines 199, 361)
- [ ] See Issue #4 for redesign

**Expected Result**:
- 250KB memory freed
- API contract honored
- No shadow state

### 4.3 Issue #3: Fix GET_SENSOR_ID Macro (DEPENDS ON #2)

**Change Required**:

**File: mm2_core.h line 202**

```c
// OLD (pointer arithmetic - BROKEN):
#define GET_SENSOR_ID(csd) ((uint32_t)((csd) - g_sensor_array.sensors))

// NEW (truth source - CORRECT):
/**
 * @brief Get sensor ID from configuration block
 *
 * TRUTH SOURCE: csb->id field
 * SCOPE: Unique within upload_source, not globally
 * USAGE: For logging, file naming, diagnostics
 *
 * @param csb Sensor configuration block (contains id field)
 * @return Sensor ID (unique within upload_source context)
 */
#define GET_SENSOR_ID(csb) ((csb)->id)
```

**Update All Call Sites** (34 occurrences):

Pattern: `GET_SENSOR_ID(csd)` → `GET_SENSOR_ID(csb)`

**Files Affected**:
- mm2_disk_spooling.c: 14 uses (all in LOG_SPOOL_* macros)
- mm2_file_management.c: 11 uses (all in LOG_FILE_* macros)
- mm2_power.c: 2 uses
- mm2_disk_reading.c: 1 use
- mm2_power_abort.c: 1 use

**Function Signature Updates Needed**:
Many helper functions only have `csd` parameter but use GET_SENSOR_ID. Must add `csb` parameter.

**Standard Parameter Order** (ENFORCE):
```c
function(upload_source, csb, csd, ...other_params...)
```

### 4.4 Issue #4: Redesign Recovery Functions (DEPENDS ON #2)

**Change Required**:

**File: mm2_api.h / mm2_disk.h**

**ADD new per-sensor API**:
```c
/**
 * @brief Recover disk-spooled data for specific sensor in specific upload source
 *
 * CRITICAL: Main application must call this for EACH active sensor in EACH upload source.
 * Scans the upload source's directory for this sensor's spool files.
 *
 * Multi-source usage:
 * - Gateway sensors: imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i])
 * - BLE sensors: imx_recover_sensor_disk_data(IMX_UPLOAD_BLE_DEVICE, &ble_scb[i], &ble_sd[i])
 * - CAN sensors: imx_recover_sensor_disk_data(IMX_UPLOAD_CAN_DEVICE, &can_scb[i], &can_sd[i])
 *
 * @param upload_source Upload source (determines directory: /usr/qk/var/mm2/{gateway|ble|can}/)
 * @param csb Sensor configuration (csb->id identifies sensor within this upload source)
 * @param csd Sensor data (csd->mmcb contains MM2 state for this sensor)
 * @return IMX_SUCCESS on success, error code (non-fatal) on failure
 */
imx_result_t imx_recover_sensor_disk_data(imatrix_upload_source_t upload_source,
                                          imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd);
```

**File: mm2_startup_recovery.c**

**IMPLEMENT new function**:
```c
imx_result_t imx_recover_sensor_disk_data(imatrix_upload_source_t upload_source,
                                          imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd) {
    if (upload_source >= IMX_UPLOAD_NO_SOURCES || !csb || !csd) {
        return IMX_INVALID_PARAMETER;
    }

    uint32_t sensor_id = csb->id;

    PRINTF("[MM2-RECOVERY] Recovering source %d, sensor %u (%s)\n",
           upload_source, sensor_id, csb->name);

    // Scan THIS upload source's directory for THIS sensor's files
    scan_sensor_spool_files_by_source(sensor_id, upload_source);
    validate_and_integrate_files(sensor_id, upload_source);
    rebuild_sensor_state(sensor_id, upload_source);

    return IMX_SUCCESS;
}
```

**DELETE or DEPRECATE old function**:
```c
imx_result_t recover_disk_spooled_data(void) {
    // DEPRECATED - use imx_recover_sensor_disk_data() per sensor
    return IMX_SUCCESS;
}
```

**File: mm2_api.c**

**REMOVE call to old recovery**:
```c
// OLD:
result = recover_disk_spooled_data();

// NEW (or remove entirely):
// Recovery deferred to main app - call imx_recover_sensor_disk_data() per sensor
```

### 4.5 Issue #5: Redesign STM32 RAM Exhaustion (DEPENDS ON #2)

**Change Required**:

**File: mm2_pool.c or mm2_stm32.c**

**ADD new per-sensor discard function**:
```c
/**
 * @brief Discard oldest non-pending sector from sensor's own chain
 *
 * CRITICAL: Implements per-sensor circular buffer.
 * When this sensor runs out of RAM, it sacrifices its own oldest data.
 *
 * @param csd Sensor data (contains mmcb with this sensor's sector chain)
 * @return IMX_SUCCESS if sector freed, IMX_ERROR if all data pending
 */
imx_result_t discard_oldest_non_pending_sector(control_sensor_data_t* csd) {
    if (!csd) return IMX_INVALID_PARAMETER;

    // Find oldest non-pending sector in THIS sensor's chain
    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;
    while (current != NULL_SECTOR_ID) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current);
        if (entry && entry->in_use && !entry->pending_ack) {
            // Found oldest non-pending - discard it
            SECTOR_ID_TYPE next = get_next_sector_in_chain(current);
            if (csd->mmcb.ram_start_sector_id == current) {
                csd->mmcb.ram_start_sector_id = next;
            }
            free_sector(current);
            if (csd->mmcb.total_records > 0) csd->mmcb.total_records--;
            return IMX_SUCCESS;
        }
        current = get_next_sector_in_chain(current);
    }
    return IMX_ERROR;  // All pending
}
```

**File: mm2_write.c**

**UPDATE imx_write_tsd() and imx_write_evt()**:
```c
// After: allocate_sector_for_sensor(...) returns NULL
#ifndef LINUX_PLATFORM
// STM32: RAM full - discard oldest from this sensor, retry
if (discard_oldest_non_pending_sector(csd) == IMX_SUCCESS) {
    new_sector = allocate_sector_for_sensor(csb->id, sector_type);  // Retry
}
#endif
```

**File: mm2_stm32.c**

**DELETE old cross-sensor search functions**:
- [ ] handle_stm32_ram_full()
- [ ] find_oldest_non_pending_sector()
- [ ] is_sector_safe_to_discard()
- [ ] handle_critical_ram_exhaustion()

**File: mm2_pool.c**

**REMOVE embedded call**:
```c
// DELETE from allocate_sector_for_sensor():
#ifndef LINUX_PLATFORM
if (handle_stm32_ram_full(sensor_id) != IMX_SUCCESS) {
    return NULL_SECTOR_ID;
}
#endif
```

**Rationale**: Caller handles RAM full with full context.

---

## PART 5: IMPLEMENTATION PHASES

### Phase 1: Fix GET_SENSOR_ID Macro and Add csb Parameters

**Objective**: Change GET_SENSOR_ID from pointer arithmetic to field access.

**Steps**:
1. [ ] Update macro definition: `GET_SENSOR_ID(csb)` = `csb->id`
2. [ ] Add csb parameter to ALL helper functions using GET_SENSOR_ID
3. [ ] Update all 34 call sites: `GET_SENSOR_ID(csd)` → `GET_SENSOR_ID(csb)`
4. [ ] Update all function call sites to pass csb
5. [ ] Verify standard parameter order: (upload_source, csb, csd, ...)

**Verification**:
```bash
grep -rn "GET_SENSOR_ID(csd)" mm2_*.c  # Expected: 0
grep -rn "GET_SENSOR_ID(csb)" mm2_*.c  # Expected: 34
```

### Phase 2: Redesign Recovery as Per-Sensor API

**Objective**: Change from global loop to per-sensor function.

**Steps**:
1. [ ] Add `imx_recover_sensor_disk_data(upload_source, csb, csd)` to mm2_api.h
2. [ ] Implement function in mm2_startup_recovery.c
3. [ ] Remove/deprecate old `recover_disk_spooled_data(void)` function
4. [ ] Remove call from mm2_api.c initialization
5. [ ] Update helper functions to remove g_sensor_array lookups

**Main App Integration**:
```c
// Gateway sensors
for (i = 0; i < device_config.no_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i]);
}
// Repeat for BLE, CAN sources...
```

### Phase 3: Redesign STM32 RAM Exhaustion as Per-Sensor Circular Buffer

**Objective**: Replace cross-sensor search with per-sensor discard.

**Steps**:
1. [ ] Create `discard_oldest_non_pending_sector(csd)` function
2. [ ] Update `imx_write_tsd()` to handle NULL sector: discard, retry
3. [ ] Update `imx_write_evt()` to handle NULL sector: discard, retry
4. [ ] Remove embedded `handle_stm32_ram_full()` call from allocate_sector_for_sensor()
5. [ ] DELETE old cross-sensor search functions

**Benefits**: Simpler, no global state, uses caller's context.

### Phase 4: Redesign Power Abort Recovery as Per-Sensor API

**Objective**: Remove loops over internal array.

**Steps**:
1. [ ] Create `imx_recover_power_abort_for_sensor(upload_source, csb, csd)` API
2. [ ] Implement function to cleanup emergency files for ONE sensor
3. [ ] Add to mm2_api.h public interface
4. [ ] Update mm2_power_abort.c to remove g_sensor_array loops
5. [ ] Main app integration: call per sensor during startup

**Alternative**: If only used during init, may not need separate API.

### Phase 5: Remove g_sensor_array Completely

**Objective**: Delete all traces of internal sensor array.

**Steps**:
1. [ ] Remove sensor_array_t typedef from mm2_core.h
2. [ ] Remove extern g_sensor_array from mm2_core.h
3. [ ] Remove g_sensor_array definition from mm2_pool.c
4. [ ] Remove sensor initialization from init_memory_pool()
5. [ ] Remove sensor cleanup from cleanup_memory_pool()
6. [ ] Delete get_sensor_data() function
7. [ ] Delete compute_active_sensor_count() function
8. [ ] Update or delete get_sensor_id_from_csd() function

**Verification**:
```bash
grep -rn "g_sensor_array" mm2_*.c mm2_*.h
# Expected: 0 (except in comments/documentation)
```

### Phase 6: Update All Function Signatures for Consistency

**Objective**: Ensure ALL functions follow standard parameter order.

**Audit Requirement**: Before adding csb, verify upload_source already present!

**Standard Order**: `(upload_source, csb, csd, ...other)`

**Functions to Update** (estimated ~30 functions):
- mm2_file_management.c: ~8 functions
- mm2_disk_spooling.c: ~12 functions
- mm2_disk_reading.c: ~4 functions
- mm2_power.c: As needed

**Steps**:
1. [ ] Audit each helper function for upload_source parameter
2. [ ] If missing, add upload_source as FIRST parameter
3. [ ] Add csb as SECOND parameter (after upload_source)
4. [ ] Update function documentation
5. [ ] Find all call sites
6. [ ] Update call sites to pass (upload_source, csb, csd, ...)

### Phase 7: Update Header Declarations

**Objective**: Ensure headers match implementations.

**Steps**:
1. [ ] Update mm2_disk.h function declarations
2. [ ] Update mm2_api.h function declarations
3. [ ] Update mm2_internal.h function declarations
4. [ ] Add deprecation warnings to old APIs
5. [ ] Verify signatures match implementations

---

## PART 6: DELIVERABLES

### 6.1 Documentation

**Required Documents**:
1. **removal_of_g_sensor_array.md**: Detailed migration plan
   - File-by-file change list
   - Before/after code snippets
   - Line number references
   - Verification commands

2. **Implementation completion report**: Summary of changes
   - Files modified count
   - Lines changed count
   - Memory savings achieved
   - Compilation results
   - Known issues remaining

### 6.2 Code Changes

**Expected Modifications**:
- Files: ~13 (including headers)
- Lines: ~335 lines modified
- Functions: ~30 signatures updated
- Deletions: ~100 lines (g_sensor_array code)
- Additions: ~50 lines (new per-sensor APIs)

### 6.3 Verification Results

**Compilation**:
```bash
make clean
make -j4 2>&1 | tee g_sensor_array_removal_build.log

# Verify zero errors related to refactoring:
grep -E "(g_sensor_array|GET_SENSOR_ID.*csd|sensor_array_t)" g_sensor_array_removal_build.log
# Expected: 0 matches
```

**Static Analysis**:
```bash
# Verify removal:
grep -rn "g_sensor_array" mm2_*.c mm2_*.h
# Expected: 0 (except comments)

# Verify macro fix:
grep -rn "GET_SENSOR_ID(csd)" mm2_*.c
# Expected: 0

grep -rn "GET_SENSOR_ID(csb)" mm2_*.c
# Expected: 34
```

**Runtime Testing**:
- [ ] Test main app calling MM2 with icb.i_sd[] pointers
- [ ] Test multi-source operation (gateway + BLE + CAN simultaneously)
- [ ] Test sensor ID collision (same ID in different upload sources)
- [ ] Test STM32 RAM exhaustion per-sensor circular buffer
- [ ] Test recovery per-sensor per-source

---

## PART 7: CONSTRAINTS AND WARNINGS

### 7.1 Must Not Change

**Sacred Cows** (do NOT modify):
- Main app's sensor array structures (icb.i_scb[], icb.i_sd[], etc.)
- MM2 API function names (imx_write_tsd, imx_read_next_tsd_evt, etc.)
- Parameter order in existing APIs (upload_source always first)
- File format on disk (disk_sector_header_t structure)
- Sector chain management (already optimized to 75%)

### 7.2 Breaking Changes Allowed

**Acceptable main app impact**:
- [ ] Must call new recovery API: `imx_recover_sensor_disk_data()` per sensor
- [ ] May need to call new power abort API: `imx_recover_power_abort_for_sensor()` per sensor
- [ ] Must verify upload_source passed correctly in all MM2 calls

**NOT acceptable**:
- ✗ Changing existing write/read API signatures
- ✗ Modifying on-disk file formats
- ✗ Breaking multi-source support

### 7.3 Critical Warnings

**⚠️ WARNING 1: Sensor ID Scope**
```
csb->id is unique WITHIN an upload source, NOT globally.
Gateway sensor 5 ≠ BLE sensor 5 ≠ CAN sensor 5 (three different sensors!)
Always use (upload_source, csb->id) tuple for unique identification.
```

**⚠️ WARNING 2: Parameter Order**
```
Standard order is MANDATORY: (upload_source, csb, csd, ...other)
Inconsistent order causes bugs and maintenance nightmares.
Verify ALL functions follow this pattern.
```

**⚠️ WARNING 3: Pointer Arithmetic**
```
NEVER use pointer arithmetic to derive sensor ID or array index.
Truth source is csb->id field. Period.
```

**⚠️ WARNING 4: Internal State**
```
MM2 must NOT duplicate sensor state.
If you see MM2 storing copies of csb or csd, it's wrong.
Only exception: csd->mmcb is per-sensor MM2 state (embedded, not separate).
```

---

## PART 8: VERIFICATION REQUIREMENTS

### 8.1 Compilation Tests

**Requirement**: Zero errors and zero warnings related to this refactoring.

**Commands**:
```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl

# Clean build:
make clean
make -j4 2>&1 | tee refactor_build.log

# Check for refactoring-related errors:
grep -iE "(g_sensor_array|GET_SENSOR_ID|sensor_array_t)" refactor_build.log
# Expected: 0 matches

# Check for unused variable warnings:
grep "unused variable.*csd" refactor_build.log
# Expected: 0 (csd should be used or parameter removed)
```

### 8.2 Static Analysis Tests

**Code Pattern Verification**:
```bash
# 1. Verify g_sensor_array removed:
grep -rn "g_sensor_array" mm2_*.c mm2_*.h
# Expected: 0 in code (comments OK)

# 2. Verify GET_SENSOR_ID fixed:
grep -rn "GET_SENSOR_ID(csd)" mm2_*.c
# Expected: 0

grep -rn "GET_SENSOR_ID(csb)" mm2_*.c
# Expected: 34

# 3. Verify standard parameter order:
grep -n "^imx_result_t" mm2_*.c | head -20
# Manually verify: upload_source first, csb second, csd third

# 4. Verify upload_source threading:
grep -n "imatrix_upload_source_t upload_source" mm2_file_management.c
# Expected: All public/helper functions have it
```

### 8.3 Runtime Tests

**Test Scenario 1: Multi-Source Operation**
```c
// Activate sensors from different sources:
imx_activate_sensor(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5]);
imx_activate_sensor(IMX_UPLOAD_BLE_DEVICE, &ble_scb[5], &ble_sd[5]);
imx_activate_sensor(IMX_UPLOAD_CAN_DEVICE, &can_scb[5], &can_sd[5]);

// Write data to each:
imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], value1);
imx_write_tsd(IMX_UPLOAD_BLE_DEVICE, &ble_scb[5], &ble_sd[5], value2);
imx_write_tsd(IMX_UPLOAD_CAN_DEVICE, &can_scb[5], &can_sd[5], value3);

// Verify files created in correct directories:
// /usr/qk/var/mm2/gateway/sensor_5_seq_0.dat
// /usr/qk/var/mm2/ble/sensor_5_seq_0.dat
// /usr/qk/var/mm2/can/sensor_5_seq_0.dat
```

**Test Scenario 2: STM32 RAM Exhaustion**
```c
// Fill RAM for one sensor:
for (i = 0; i < 1000; i++) {
    imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], i);
}

// Verify: Oldest data from sensor 5 was discarded (circular buffer)
// Verify: Other sensors' data NOT affected
```

**Test Scenario 3: Recovery Per-Source**
```c
// Reboot, then recover:
for (i = 0; i < no_gateway_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i]);
}

for (i = 0; i < no_ble_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_BLE_DEVICE, &ble_scb[i], &ble_sd[i]);
}

// Verify: Files discovered from correct directories
// Verify: State properly reconstructed per sensor per source
```

### 8.4 Integration Tests

**Test 1**: Main app with icb arrays
```c
// Ensure MM2 works with main app's actual arrays:
for (i = 0; i < device_config.no_sensors; i++) {
    imx_activate_sensor(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i]);
    imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i], value);
}
// Expected: No crashes, correct sensor IDs in logs
```

**Test 2**: Sensor ID collision across sources
```c
// Same sensor ID in different sources:
imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[5], &icb.i_sd[5], 100);
imx_write_tsd(IMX_UPLOAD_BLE_DEVICE, &ble_scb[5], &ble_sd[5], 200);

// Verify files:
// gateway/sensor_5_seq_0.dat contains 100
// ble/sensor_5_seq_0.dat contains 200
// No collision, no confusion
```

### 8.5 Success Criteria (ALL Must Pass)

**Memory**:
- [ ] g_sensor_array deleted: 250KB saved
- [ ] per_source_disk device-level: 288KB saved (already done)
- [ ] Total savings: ≥ 538KB
- [ ] No replacement tracker needed

**Correctness**:
- [ ] MM2 works with csb/csd from any main app array
- [ ] GET_SENSOR_ID returns csb->id correctly
- [ ] Multi-source operation verified
- [ ] Sensor ID collision handled correctly

**API Compliance**:
- [ ] All functions receive (upload_source, csb, csd) from caller
- [ ] Zero internal sensor arrays
- [ ] Per-sensor APIs for recovery and power abort

**Code Quality**:
- [ ] Clean compilation, zero warnings
- [ ] Zero g_sensor_array references
- [ ] All functions follow standard parameter order
- [ ] Consistent coding style

---

## PART 9: STEP-BY-STEP EXECUTION PLAN

### Step 1: Analyze Current State

**Read and analyze**:
- [ ] mm2_core.h - GET_SENSOR_ID macro, g_sensor_array typedef
- [ ] mm2_pool.c - g_sensor_array usage, initialization, helper functions
- [ ] mm2_startup_recovery.c - recovery function implementation
- [ ] mm2_stm32.c - RAM exhaustion handling
- [ ] mm2_power_abort.c - power abort recovery
- [ ] All mm2 files using GET_SENSOR_ID

**Create inventory**:
- List all g_sensor_array references (expect ~23)
- List all GET_SENSOR_ID(csd) uses (expect ~34)
- List all functions needing csb parameter
- List all functions needing upload_source verification

### Step 2: Create Migration Plan Document

**Create**: `removal_of_g_sensor_array.md`

**Contents**:
- Executive summary
- Current vs target architecture diagrams
- File-by-file change list with line numbers
- Before/after code for complex changes
- Verification commands
- Todo checklist for each phase

### Step 3: Execute Refactoring Phases

**Phase 1**: GET_SENSOR_ID macro and csb parameters
- Change macro definition
- Add csb to ~30 helper functions
- Update all call sites
- Verify compilation

**Phase 2**: Recovery API redesign
- Implement per-sensor recovery
- Update mm2_api.c initialization
- Verify integration pattern

**Phase 3**: STM32 circular buffer
- Implement discard function
- Update write functions
- Remove old cross-sensor code
- Verify STM32 behavior

**Phase 4**: Power abort API
- Implement per-sensor power abort recovery
- Update mm2_power_abort.c
- Verify integration

**Phase 5**: Delete g_sensor_array
- Remove all definitions, declarations
- Remove initialization/cleanup code
- Remove helper functions
- Final verification

**Phase 6**: Signature consistency
- Audit all functions
- Enforce standard parameter order
- Update documentation

**Phase 7**: Header updates
- Update all declarations
- Add deprecation warnings
- Final compilation check

### Step 4: Comprehensive Verification

**Run all verification commands** from Part 8.

**Create completion report** documenting:
- All changes made
- All tests passed
- Memory savings achieved
- Known issues remaining (if any)

### Step 5: User Review

**Present for review**:
- Migration plan document
- Completion report
- Compilation logs
- Test results

**Wait for approval** before considering task complete.

---

## PART 10: SPECIFIC IMPLEMENTATION GUIDANCE

### 10.1 Handling GET_SENSOR_ID Macro Calls

**Current pattern** (example from mm2_disk_spooling.c:244):
```c
LOG_SPOOL_INFO("Sensor %u: Memory pressure detected",
               GET_SENSOR_ID(csd), ...);
```

**Problem**: Function has (csd, upload_source) but GET_SENSOR_ID needs csb.

**Solution Process**:
1. Check function signature - does it have csb parameter?
2. If NO: Add csb parameter after upload_source
3. Update macro call: `GET_SENSOR_ID(csd)` → `GET_SENSOR_ID(csb)`
4. Find all call sites of this function
5. Update call sites to pass csb

**After**:
```c
// Function signature:
static imx_result_t process_idle_state(imatrix_upload_source_t upload_source,
                                       imx_control_sensor_block_t* csb,  // ADDED
                                       control_sensor_data_t* csd) {
    LOG_SPOOL_INFO("Sensor %u: Memory pressure detected",
                   GET_SENSOR_ID(csb), ...);  // FIXED
}

// Call site update:
result = process_idle_state(upload_source, csb, csd);  // Pass csb
```

### 10.2 Handling Functions That Loop Over g_sensor_array

**Current pattern** (example from mm2_stm32.c:92):
```c
for (uint32_t i = 0; i < MAX_SENSORS; i++) {
    control_sensor_data_t* csd = &g_sensor_array.sensors[i];
    if (!csd->active) continue;
    // ... operate on csd ...
}
```

**Redesign Decision Tree**:

**Question 1**: Can this be a per-sensor API?
- If YES: Redesign as `function(upload_source, csb, csd)`, main app calls in loop
- If NO: Continue to Question 2

**Question 2**: Does caller context have what we need?
- If YES: Use caller's csd parameter (e.g., STM32 RAM exhaustion)
- If NO: Continue to Question 3

**Question 3**: Must we really iterate all sensors?
- If YES: Minimal active sensor tracker (last resort)
- If NO: Redesign to avoid iteration

**For this refactoring**:
- Recovery: YES can be per-sensor API (recommended)
- STM32 RAM exhaustion: YES use caller's csd (recommended)
- Power abort: YES can be per-sensor API (recommended)
- **Result**: NO iteration needed, NO tracker needed!

### 10.3 Handling upload_source Parameter

**Verification at each helper function**:

```c
// Before adding csb, verify upload_source present:
imx_result_t helper_function(control_sensor_data_t* csd,
                            imatrix_upload_source_t upload_source,  // Present?
                            ...other_params...) {
    // ...
}

// If upload_source MISSING, add as FIRST parameter!
// If upload_source OUT OF ORDER, fix order to (upload_source, csb, csd, ...)
```

**Standard order is NON-NEGOTIABLE**: `(upload_source, csb, csd, ...)`

### 10.4 Handling Per-Source Disk State Access

**Already correct pattern** (from prior refactoring):
```c
// Use upload_source to index into per_source_disk:
icb.per_source_disk[upload_source].active_spool_fd
icb.per_source_disk[upload_source].spool_state.current_state
icb.per_source_disk[upload_source].spool_files[i].filename
```

**Verify**: upload_source parameter available in function scope!

**File paths**:
```c
// Build path using upload_source:
char source_path[256];
get_upload_source_path(upload_source, source_path, sizeof(source_path));
// Returns: "/usr/qk/var/mm2/gateway/" or "/ble/" or "/can/"

// Then append sensor-specific file:
snprintf(filename, sizeof(filename), "%s/sensor_%u_seq_%u.dat",
         source_path, csb->id, sequence);
```

---

## PART 11: EXPECTED RESULTS AND VALIDATION

### 11.1 Before vs After Comparison

**Before Refactoring (Current Broken State)**:

Memory usage:
- per_source_disk in csd: 25 sensors × 4 sources × 3KB = 300KB (FIXED IN PRIOR REFACTORING)
- g_sensor_array: 500 × 500 bytes = 250KB (TO BE FIXED)
- **Total waste**: 550KB (prior refactoring saved 288KB, 250KB remains)

Code patterns:
- GET_SENSOR_ID(csd): Pointer arithmetic, undefined behavior ❌
- g_sensor_array lookups: Shadow state, API violation ❌
- Global recovery loop: Doesn't respect multi-source ❌
- Cross-sensor RAM search: Over-engineered ❌

**After Refactoring (Target Correct State)**:

Memory usage:
- per_source_disk in icb: 4 sources × 3KB = 12KB ✅ (already fixed)
- g_sensor_array: DELETED = 0KB ✅ (this refactoring)
- **Total savings**: 538KB

Code patterns:
- GET_SENSOR_ID(csb): Direct field access, always correct ✅
- Use caller's csb/csd: No shadow state, API compliant ✅
- Per-sensor recovery API: Respects multi-source ✅
- Per-sensor circular buffer: Simple, uses caller's context ✅

### 11.2 Success Validation Checklist

**Structural**:
- [ ] per_source_disk_state_t defined standalone (common.h)
- [ ] icb.per_source_disk[upload_source] in iMatrix_Control_Block_t
- [ ] NO sensor_array_t typedef in mm2_core.h
- [ ] NO g_sensor_array extern or definition

**Functional**:
- [ ] GET_SENSOR_ID(csb) macro uses csb->id
- [ ] imx_recover_sensor_disk_data(upload_source, csb, csd) API exists
- [ ] discard_oldest_non_pending_sector(csd) function exists
- [ ] imx_write_tsd/evt handle NULL sector with discard+retry

**Code Quality**:
- [ ] Zero g_sensor_array references in code
- [ ] Zero GET_SENSOR_ID(csd) uses
- [ ] All functions follow standard parameter order
- [ ] Zero unused variable warnings

**Integration**:
- [ ] Main app can call MM2 with icb.i_sd[] pointers
- [ ] Multi-source operation works (gateway + BLE + CAN)
- [ ] Recovery called per-sensor per-source
- [ ] No runtime crashes or undefined behavior

### 11.3 Performance Validation

**Memory**:
```bash
# Check structure sizes:
sizeof(iMatrix_Control_Block_t) before vs after
# Expected reduction: ~250KB

# Verify per_source_disk is device-level:
sizeof(per_source_disk_state_t) × IMX_UPLOAD_NO_SOURCES
# Expected: ~12KB (not 300KB)
```

**Runtime**:
- STM32 circular buffer should be fast (O(1) discard)
- No performance regression in write/read operations
- Recovery startup time reasonable (depends on file count)

---

## PART 12: ROLLBACK AND SAFETY

### 12.1 Git Strategy

**Checkpoint after each phase**:
```bash
# After Phase 1:
git add -u
git commit -m "Phase 1: Fix GET_SENSOR_ID macro and add csb parameters"

# After Phase 2:
git commit -m "Phase 2: Redesign recovery as per-sensor API"

# ... and so on for each phase
```

**Benefit**: Can rollback individual phases if issues found.

### 12.2 Rollback Procedure

**Rollback entire refactoring**:
```bash
git log --oneline | grep "Phase"  # Find commit hashes
git revert <hash>  # Revert specific phase
# Or:
git checkout HEAD~7  # Rollback all 7 phases at once
```

**Partial rollback** (keep some phases):
```bash
# Keep Phases 1-3, rollback 4-7:
git revert HEAD~4..HEAD
```

### 12.3 Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed g_sensor_array reference | Low | High | Automated grep verification |
| GET_SENSOR_ID call site error | Low | High | Compile-time parameter type mismatch |
| Function signature inconsistency | Medium | High | Update headers before implementation |
| STM32 RAM exhaustion regression | Low | Critical | Comprehensive testing on hardware |
| Multi-source file collision | Low | High | Test with all sources active |
| Main app integration difficulty | Medium | Medium | Clear migration guide, code examples |
| Recovery fails on reboot | Low | High | Test recovery with multiple sources |

---

## PART 13: CONTEXT FOR AI REASONING

### 13.1 Why g_sensor_array Exists (Historical Context)

**Original design intent** (likely):
- MM2 needed to manage multiple sensors
- Created internal array for convenience
- Seemed reasonable at the time

**Why it's wrong NOW**:
- Main app already manages sensor arrays
- API design changed to pass csb/csd
- Multi-source architecture added
- Stateless design goal established

**Lesson**: Code that made sense in v1 may violate principles in v2.

### 13.2 Why This Refactoring Is Important

**Immediate Benefits**:
- 538KB memory savings (critical on embedded systems)
- Bug fix: GET_SENSOR_ID pointer arithmetic
- API contract compliance
- Multi-source support correctness

**Long-Term Benefits**:
- Architectural clarity (stateless service)
- Maintainability (single source of truth)
- Scalability (supports more upload sources easily)
- Debuggability (one sensor array per source, not multiple)

**Risk of NOT Fixing**:
- Runtime crashes when main app calls API
- Memory exhaustion on resource-constrained devices
- Confusion about sensor state ownership
- Difficulty adding new upload sources

### 13.3 Multi-Source Architecture Deep Dive

**Why separate arrays per upload source?**

Each upload source has different characteristics:
- **Gateway**: Internal sensors (temperature, voltage, etc.)
- **BLE**: External BLE devices (100+ possible)
- **CAN**: CAN bus signals (vehicle data)

Each needs:
- Different sensor counts (25 vs 128 vs N)
- Different directories for disk files
- Different upload schedules/priorities
- Separate configuration management

**Implications for MM2**:
- Can't assume single sensor array
- Can't use global sensor ID numbering
- Must partition everything by upload_source
- Per-source disk state already correct (prior refactoring)
- Per-sensor state (mmcb) already correct (embedded in csd)
- **Problem**: g_sensor_array assumes single global array!

### 13.4 Truth Sources - Deep Explanation

**Why csb->id is truth source for sensor ID**:

```c
typedef struct control_sensor_block {
    char name[65];
    uint8_t hash_id;
    uint32_t id;  // ← THIS is the sensor ID!
    uint32_t sample_rate;
    // ...
} imx_control_sensor_block_t;
```

- Main app sets csb->id when creating sensor
- Same ID used in iMatrix cloud platform
- Persistent across reboots
- Unique within upload source context
- Used in file names, logs, uploads

**Why pointer arithmetic is WRONG**:
```c
// WRONG:
#define GET_SENSOR_ID(csd) ((csd) - some_array)
// Problems:
// 1. Only works if csd from specific array
// 2. Undefined behavior across different arrays
// 3. No relationship to actual sensor ID (csb->id)
// 4. Breaks with multi-source (which array?)
```

**Why NOT to use array index**:
- Sensor's array index may not match csb->id
- Different upload sources have different arrays
- Array index is implementation detail, csb->id is interface

---

## PART 14: FINAL INSTRUCTIONS

### 14.1 Your Task

**Execute comprehensive refactoring to**:
1. ✅ Verify per_source_disk refactoring from prior work (should be complete)
2. Remove g_sensor_array completely
3. Fix GET_SENSOR_ID macro to use csb->id
4. Update all function signatures for consistency
5. Redesign recovery as per-sensor API
6. Redesign STM32 RAM exhaustion as per-sensor circular buffer
7. Redesign power abort (if needed) as per-sensor API
8. Verify all changes compile and pass tests

### 14.2 Documentation Requirements

**Create these documents**:
1. **removal_of_g_sensor_array.md**: Migration plan with step-by-step todos
2. **g_sensor_array_refactoring_complete.md**: Completion report with verification results

**Each document must include**:
- File-by-file change list
- Line number references
- Before/after code snippets
- Verification commands
- Success criteria checklist

### 14.3 Verification Requirements

**YOU must verify**:
- Compilation: `make clean && make -j4`
- Static analysis: Grep for antipatterns
- Code review: Check standard parameter order

**I will verify** (on target hardware):
- Runtime behavior
- Multi-source operation
- STM32 circular buffer
- Recovery correctness

### 14.4 Communication Style

**During execution**:
- Explain architectural reasoning for each change
- Flag any concerns or ambiguities
- Ask questions if context insufficient
- Propose alternatives if better design found

**In deliverables**:
- Clear, concise technical writing
- Concrete code examples
- Precise line number references
- Grep commands for verification

---

## PART 15: SUCCESS DEFINITION

**This refactoring is COMPLETE when**:

**ALL of these are true**:
1. ✅ per_source_disk is device-level in icb.per_source_disk[]
2. ✅ g_sensor_array deleted from all code
3. ✅ GET_SENSOR_ID uses csb->id, not pointer arithmetic
4. ✅ All functions receive (upload_source, csb, csd) from caller
5. ✅ Recovery is per-sensor API
6. ✅ STM32 uses per-sensor circular buffer
7. ✅ Clean compilation, zero warnings
8. ✅ ~538KB memory savings achieved
9. ✅ Multi-source test passes
10. ✅ No shadow state remains

**And NONE of these are true**:
1. ❌ Any reference to g_sensor_array in mm2 code
2. ❌ Any use of GET_SENSOR_ID(csd)
3. ❌ Any pointer arithmetic for sensor ID
4. ❌ Any internal sensor array duplication
5. ❌ Any cross-sensor search loops
6. ❌ Any global recovery function
7. ❌ Any compilation errors or warnings
8. ❌ Any unused variable warnings for csd

**Verification**: Run ALL commands in Part 8, ALL must pass.

---

## APPENDIX A: Key Files and Their Roles

**mm2_core.h**: Core data structures, macros, typedefs
- Currently: Contains g_sensor_array typedef and GET_SENSOR_ID macro
- After: NO g_sensor_array, fixed GET_SENSOR_ID macro

**mm2_pool.c**: Memory pool management, initialization, cleanup
- Currently: Initializes g_sensor_array in init_memory_pool()
- After: NO g_sensor_array initialization or cleanup

**mm2_api.c**: Public API implementation, entry points
- Currently: Calls recover_disk_spooled_data() during init
- After: Defers recovery to main app's per-sensor calls

**mm2_startup_recovery.c**: Disk recovery on reboot
- Currently: Loops over g_sensor_array
- After: Per-sensor API, main app calls with its own csb/csd

**mm2_stm32.c**: STM32-specific RAM exhaustion handling
- Currently: Searches across g_sensor_array for oldest data
- After: Per-sensor discard using csd from caller

**mm2_write.c**: Write operations (imx_write_tsd, imx_write_evt)
- Currently: Assumes allocate_sector handles RAM full
- After: Explicitly handles NULL sector with discard+retry

**mm2_disk_spooling.c, mm2_file_management.c, mm2_disk_reading.c**: Disk operations
- Currently: Use GET_SENSOR_ID(csd) for logging
- After: Use GET_SENSOR_ID(csb) for logging

---

## APPENDIX B: Quick Reference - Parameter Meanings

**imatrix_upload_source_t upload_source**:
- Which upload source (GATEWAY=0, BLE=2, CAN=4, etc.)
- Determines directory: `/usr/qk/var/mm2/{gateway|ble|can}/`
- Determines per_source_disk array index: `icb.per_source_disk[upload_source]`
- Scope: Must be passed to ALL helper functions

**imx_control_sensor_block_t* csb**:
- Sensor configuration (name, id, sample_rate, poll_rate, warnings, etc.)
- **Truth source**: csb->id is the sensor ID
- Owner: Main application's array (icb.i_scb[], ble_scb[], can_scb[])
- Access: Read-only (MM2 doesn't modify configuration)
- Usage: Logging, file naming, sensor identification

**control_sensor_data_t* csd**:
- Sensor runtime data (last_sample, no_samples, errors, warnings, etc.)
- **Contains**: csd->mmcb (MM2 per-sensor state)
- Owner: Main application's array (icb.i_sd[], ble_sd[], can_sd[])
- Access: MM2 modifies csd->mmcb fields
- Usage: Chain management, statistics, state tracking

**Relationship**:
- csb and csd at same array index refer to same sensor
- Example: icb.i_scb[5] and icb.i_sd[5] both describe gateway sensor 5
- MM2 receives both pointers, uses csb for ID, csd for state

---

## APPENDIX C: Grep Patterns for Verification

**Find g_sensor_array references**:
```bash
grep -rn "g_sensor_array" mm2_*.c mm2_*.h
# During refactoring: ~23 matches
# After refactoring: 0 matches (except comments)
```

**Find GET_SENSOR_ID macro calls**:
```bash
grep -rn "GET_SENSOR_ID(csd)" mm2_*.c
# During refactoring: 34 matches
# After refactoring: 0 matches

grep -rn "GET_SENSOR_ID(csb)" mm2_*.c
# After refactoring: 34 matches
```

**Find functions missing upload_source**:
```bash
grep -n "^imx_result_t\|^static imx_result_t" mm2_*.c | \
  grep -v "upload_source"
# Review each: should it have upload_source parameter?
```

**Find functions missing csb**:
```bash
grep -n "GET_SENSOR_ID" mm2_*.c | cut -d: -f1 | sort -u | \
  while read file; do
    grep -n "GET_SENSOR_ID" "$file" | \
    grep -v "csb" && echo "  ^ Missing csb in $file"
  done
```

---

*Prompt Version: 1.0*
*Created: 2025-10-13*
*Purpose: Comprehensive refactoring prompt for MM2 architectural corrections*
*Scope: Complete fix for per_source_disk + g_sensor_array + GET_SENSOR_ID + recovery + STM32*
*Estimated Result: 538KB savings, zero shadow state, API compliant, multi-source correct*
*Complexity: High, but ensures complete solution on first execution*
