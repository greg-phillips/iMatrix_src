# Memory Manager Refactoring - Complete Action Plan

## Executive Summary
Based on the comprehensive analysis, 105 functions were identified in the original memory_manager.c file. Currently:
- ✅ 71 functions (67.6%) are fully implemented
- 🔄 24 functions (22.9%) have been modified/renamed
- ❌ 8 functions (7.6%) are missing
- ⚠️ 2 functions (1.9%) are stubs

## Priority 1: Critical Missing Implementations (Must Fix)

### 1.1 Host Interface Functions (3 functions)
These functions are declared in memory_manager.c but have no implementation:

| Function | Original Line | Action Required |
|----------|---------------|-----------------|
| `get_host_sd()` | 113 | Implement function to return control_sensor_data_t pointer |
| `get_host_sb()` | 114 | Implement function to return imx_control_sensor_block_t pointer |
| `get_host_no_sensors()` | 115 | Implement function to return number of sensors |

**Location**: Implement in memory_manager.c or memory_manager_core.c
**Dependencies**: Need access to host data structures (likely from icb)

### 1.2 Recovery Function Stubs (2 functions)
Currently returning dummy values in memory_manager_stubs.c:

| Function | Stub Location | Actual Implementation | Action |
|----------|---------------|----------------------|---------|
| `process_incomplete_operations()` | stubs.c:179 | memory_manager.c:983 (`_internal`) | Update stub to call internal version |
| `rebuild_sector_metadata()` | stubs.c:188 | memory_manager.c:912 (`_internal`) | Update stub to call internal version |

## Priority 2: Missing Disk Management Functions (5 functions)

These functions are completely missing from the refactored code:

| Function | Original Line | Purpose | Suggested Location |
|----------|---------------|---------|-------------------|
| `get_bucket_number()` | 1897 | Calculate bucket for hierarchical storage | memory_manager_tiered.c (exists at line 1146) |
| `ensure_bucket_directory_exists()` | 1908 | Create bucket directories | memory_manager_tiered.c (exists at line 1160) |
| `get_storage_base_path()` | 1920 | Get test/production storage path | memory_manager_tiered.c (exists at line 1151) |
| `get_hierarchical_disk_file_path()` | 1939 | Generate hierarchical file paths | memory_manager_tiered.c (exists at line 1168) |
| `get_available_disk_space()` | 1992 | Query available disk space | Renamed to `get_available_disk_space_internal()` |

**Note**: Investigation shows these functions actually exist in memory_manager_tiered.c but were marked as static, making them inaccessible from other modules.

## Priority 3: Function Consolidation

### 3.1 Functions with Multiple Versions
Several functions have both public and internal versions:

| Function | Versions | Recommendation |
|----------|----------|----------------|
| `init_recovery_journal` | memory_manager.c (static) | Keep as is - internal use only |
| `read_journal_from_disk` | memory_manager.c (static) | Keep as is - internal use only |
| `journal_begin_operation` | tiered.c (`_internal`) | Consider exposing if needed externally |
| `journal_update_progress` | tiered.c (static) | Keep as is - internal use only |
| `validate_disk_file` | memory_manager.c (static) | Keep as is - internal use only |

### 3.2 Functions Existing in Multiple Files
| Function | Locations | Action |
|----------|-----------|---------|
| `print_sat()` | tsd_evt.c:1119, memory_manager.c (declared) | Remove declaration from memory_manager.c |
| `calculate_checksum()` | stubs.c:163 (impl), internal.h:279 (decl) | Keep in stubs.c as utility |

## Implementation Steps

### Step 1: Implement Missing Host Functions
```c
// In memory_manager.c or memory_manager_core.c
control_sensor_data_t *get_host_sd(void)
{
    extern iMatrix_Control_Block_t icb;
    return icb.csd;
}

imx_control_sensor_block_t *get_host_sb(void)
{
    extern iMatrix_Control_Block_t icb;
    return icb.csb;
}

uint16_t get_host_no_sensors(void)
{
    extern iMatrix_Control_Block_t icb;
    return icb.no_sensors;
}
```

### Step 2: Fix Recovery Function Stubs
```c
// In memory_manager_stubs.c
int process_incomplete_operations(void)
{
    // Call the actual implementation
    return process_incomplete_operations_internal();
}

uint32_t rebuild_sector_metadata(void)
{
    // Call the actual implementation
    return rebuild_sector_metadata_internal();
}
```

### Step 3: Expose Disk Management Functions
For the disk management functions in memory_manager_tiered.c:
1. Remove `static` keyword if they need to be accessed from other modules
2. Add declarations to memory_manager_tiered.h
3. Or keep them static if they're truly internal-only

## Testing Checklist

After implementing all changes:

- [ ] Compile each module independently
- [ ] Link all modules together
- [ ] Test host interface functions return valid pointers
- [ ] Test recovery operations (simulate incomplete operations)
- [ ] Test disk management (create/delete files)
- [ ] Test tiered storage migration
- [ ] Verify memory statistics are accurate
- [ ] Run stress tests for memory allocation/deallocation

## Module Responsibility Summary

| Module | Primary Responsibility | Function Count |
|--------|----------------------|----------------|
| memory_manager_core.c | SAT operations, sector allocation | 20 |
| memory_manager_tsd_evt.c | Time series data operations | 7 |
| memory_manager_external.c | External SRAM management | 3 |
| memory_manager_stats.c | Memory statistics | 21 |
| memory_manager_tiered.c | Tiered storage, disk operations | 29 |
| memory_manager_disk.c | Atomic disk file operations | 1 |
| memory_manager_recovery.c | Power failure recovery | 1 |
| memory_manager.c | Coordination, legacy support | 21 |
| memory_manager_stubs.c | Temporary implementations | 7 |

## Final Notes

1. The refactoring has successfully separated concerns into logical modules
2. Most functionality (90%+) has been preserved
3. The main gaps are in host interface and some disk management functions
4. Once the Priority 1 items are fixed, the system should be fully functional
5. Consider removing memory_manager_stubs.c once all functions are properly implemented