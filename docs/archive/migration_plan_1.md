# MM2 Migration Plan - Phase 1
**Date:** 2025-10-10
**Version:** 1.0
**Status:** DRAFT - Awaiting Review

---

## Repositories

### Primary Repositories
- **Fleet-Connect-1**: Gateway application that implements the iMatrix client functionality
- **iMatrix**: Core embedded system code with memory management and sensor control

### Migration Branches
- **iMatrix Repository**: `feature/mm2-integration` (from Qconnect-Updates2)
- **Fleet-Connect-1 Repository**: `feature/mm2-integration` (from Qconnect-Updates2)

---

## 1. Old MM Interface Summary

The current memory management system in `iMatrix/cs_ctrl/` provides the following core functions that must be replaced:

### Core Allocation Functions
- `imx_sat_init()` / `init_sat()` - Initialize sector allocation table
- `imx_get_free_sector()` / `imx_get_free_sector_safe()` - Allocate free sectors
- `free_sector()` / `free_sector_safe()` - Free allocated sectors
- `get_next_sector()` / `get_next_sector_safe()` - Traverse sector chains

### Data Operations
- `write_tsd_evt()` / `write_tsd_evt_time()` - Write time series/event data
- `read_tsd_evt()` - Read data from sectors
- `erase_tsd_evt()` / `erase_tsd_evt_pending_data()` - Erase pending data after upload
- `revert_tsd_evt_pending_data()` - Revert pending data on upload failure

### Raw Sector Access
- `read_rs()` / `read_rs_safe()` - Read from sector
- `write_rs()` / `write_rs_safe()` - Write to sector

### Memory Statistics
- `imx_init_memory_statistics()` - Initialize stats tracking
- `imx_update_memory_statistics()` - Update current stats
- `imx_get_memory_statistics()` - Get memory statistics

### Tiered Storage (Linux Only)
- `process_memory()` - Main state machine for tiered storage
- `flush_all_to_disk()` - Shutdown flush operation
- `get_flush_progress()` - Get flush completion percentage

---

## 2. MM2 Interface Summary

The new MM2 system in `/mm2/` provides these replacement functions:

### Core Initialization
- `imx_memory_manager_init()` - Initialize memory pool (replaces `imx_sat_init()`)
- `imx_memory_manager_shutdown()` - Graceful shutdown with data preservation
- `imx_memory_manager_ready()` - Check if ready for operations

### Data Operations (NEW SIGNATURES)
- `imx_write_tsd()` - Write TSD with upload source and CSB/CSD pointers
- `imx_write_evt()` - Write EVT with individual timestamps
- `imx_read_next_tsd_evt()` - Read with upload source and CSB/CSD pointers
- `imx_read_bulk_samples()` - High-performance bulk read
- `imx_erase_all_pending()` - ACK uploaded data
- `imx_revert_all_pending()` - NACK for retry

### Sensor Management (NEW)
- `imx_configure_sensor()` - Configure TSD/EVT mode
- `imx_activate_sensor()` - Activate for data collection
- `imx_deactivate_sensor()` - Deactivate and flush

### Memory Management
- `imx_get_memory_stats()` - Get statistics
- `process_memory_manager()` - Periodic processing (replaces `process_memory()`)

### Power Management (NEW)
- `imx_power_event_detected()` - Handle power loss
- `imx_is_power_down_pending()` - Check power state
- `handle_power_abort_recovery()` - Recovery from aborted shutdown

---

## 3. Core Migration Strategy (High-Level)

### Step 1: Build System Integration
- Add MM2 source directory (`mm2/`) to Fleet-Connect-1 build system
- Link MM2 libraries/objects
- Remove old MM source files from build

### Step 2: Header Migration
- Replace includes of old MM headers with `mm2/include/mm2_api.h`
- Update any direct structure access to use MM2 APIs

### Step 3: Function Call Migration
- Replace `write_tsd_evt()` calls with `imx_write_tsd()`
- Replace `read_tsd_evt()` calls with `imx_read_next_tsd_evt()`
- Replace `erase_tsd_evt_pending_data()` with `imx_erase_all_pending()`
- Replace `revert_tsd_evt_pending_data()` with `imx_revert_all_pending()`

### Step 4: Initialization/Shutdown Updates
- Replace `imx_sat_init()` with `imx_memory_manager_init()`
- Add proper shutdown calls with `imx_memory_manager_shutdown()`
- Update periodic processing from `process_memory()` to `process_memory_manager()`

### Step 5: Remove Old MM Code
- Delete all files in `iMatrix/cs_ctrl/memory_manager*.c/h`
- Remove old MM test code
- Clean up any remaining references

---

## 4. Configuration Changes

### Fleet-Connect-1 Build System (CMakeLists.txt)

**Add MM2 Sources:**
```cmake
# Add MM2 source directory
set(MM2_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../mm2)
include_directories(${MM2_DIR}/include)

# Add MM2 source files
file(GLOB MM2_SOURCES ${MM2_DIR}/src/*.c)
list(REMOVE_ITEM MM2_SOURCES ${MM2_DIR}/src/mm2_test_main.c)

# Add to target
add_executable(fleet-connect
    ${EXISTING_SOURCES}
    ${MM2_SOURCES}
)
```

**Remove Old MM Sources:**
```cmake
# Remove old memory manager files
list(REMOVE_ITEM IMATRIX_SOURCES
    ${IMATRIX_DIR}/cs_ctrl/memory_manager.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_core.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_tsd_evt.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_tiered.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_stats.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_disk.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_recovery.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_external.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_utils.c
)
```

### Include Path Updates

**Old includes to remove:**
```c
#include "cs_ctrl/memory_manager.h"
#include "cs_ctrl/memory_manager_core.h"
#include "cs_ctrl/memory_manager_tsd_evt.h"
```

**New includes to add:**
```c
#include "mm2_api.h"
```

---

## 5. Critical API Changes

### IMPORTANT: Function Signature Changes

The MM2 API has significant signature changes that require careful migration:

**Old API:**
```c
// No upload_source parameter, sensor_id was implicit
write_tsd_evt(csb, csd, entry, value, add_gps);
read_tsd_evt(csb, csd, entry, &value);
erase_tsd_evt_pending_data(csb, csd, no_items);
```

**New MM2 API:**
```c
// upload_source is REQUIRED, CSB/CSD passed by pointer
imx_write_tsd(upload_source, &csb, &csd, value);
imx_read_next_tsd_evt(upload_source, &csb, &csd, &data_out);
imx_erase_all_pending(upload_source, &csb, &csd, record_count);
```

### Key Changes:
1. **upload_source parameter is MANDATORY** - Must specify IMX_UPLOAD_GATEWAY, IMX_HOSTED_DEVICE, etc.
2. **CSB/CSD passed by pointer** - Main app owns these structures
3. **No entry parameter** - Sensor ID is in csb->id
4. **Different return types** - MM2 uses imx_result_t error codes

---

## 6. Data Structure Compatibility

### Compatible Structures (No Changes Needed)
- `imx_control_sensor_block_t` - Used by both systems
- `control_sensor_data_t` - Used by both systems
- `imatrix_upload_source_t` - Shared enum

### New MM2 Structures
- `mm2_stats_t` - Replaces `imx_memory_statistics_t`
- `tsd_evt_data_t` - Output format for reads
- `tsd_evt_value_t` - Bulk read format
- `mm2_sensor_state_t` - Sensor state info

---

## 7. Platform-Specific Considerations

### Linux Platform
- MM2 supports disk spooling (same as old MM)
- Directory structure: `/tmp/mm2_spool/` instead of old paths
- Recovery journal maintained for crash safety

### STM32 Platform
- RAM-only operation (no changes)
- UTC synchronization required before writes
- Must call `imx_set_utc_available()` after time sync

---

## 8. Risk Assessment

### High Risk Areas
1. **Upload Source Parameter** - Missing this will cause compilation errors
2. **Shutdown Sequence** - Must call shutdown for EACH sensor
3. **Power Management** - New power event handling required

### Medium Risk Areas
1. **Statistics Interface** - Different structure format
2. **Bulk Operations** - New APIs may require refactoring
3. **Error Codes** - Different error code enum values

### Low Risk Areas
1. **Basic read/write** - Core functionality unchanged
2. **Sensor management** - Similar concepts
3. **Memory efficiency** - Improved (75% vs old system)

---

## 9. Testing Requirements

### Unit Tests
- Verify all MM2 APIs work correctly
- Test migration of existing data patterns
- Validate ACK/NACK mechanisms

### Integration Tests
- Fleet-Connect-1 builds successfully
- Data upload to iMatrix cloud works
- Power management scenarios

### Performance Tests
- Memory efficiency meets 75% target
- Upload/download throughput maintained
- Startup/shutdown times acceptable

---

## Next Steps

1. **Review this plan** - Confirm approach is acceptable
2. **Create detailed todo list** - Break down into specific tasks
3. **Begin implementation** - Start with build system changes
4. **Test incrementally** - Validate each module as migrated
5. **Full system test** - End-to-end validation

---

**END OF MIGRATION PLAN v1.0**