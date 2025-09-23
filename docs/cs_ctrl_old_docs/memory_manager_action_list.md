# Memory Manager Refactoring - Action List

## Priority 1: Critical Stub Implementations

### 1. Directory and File Operations (memory_manager_stubs.c)

#### `ensure_directory_exists()` - Lines 58-66
**Original Implementation Location**: memory_manager-original.c:1873-1891
```c
// Current stub - needs replacement with original:
bool ensure_directory_exists(const char *path)
{
    // TODO: Implement directory creation
    imx_cli_log_printf("STUB: ensure_directory_exists(%s)\n", path);
    return true;
}
```
**Action**: Copy original implementation that creates directories recursively with proper permissions (0755)

#### `delete_disk_file_internal()` - Lines 71-79
**Original Implementation Location**: memory_manager-original.c:2081-2095
```c
// Current stub - needs replacement
bool delete_disk_file_internal(const char *filename)
{
    // TODO: Implement file deletion
    imx_cli_log_printf("STUB: delete_disk_file_internal(%s)\n", filename);
    return true;
}
```
**Action**: Copy original implementation that safely deletes files and handles errors

### 2. Sector Location Management (memory_manager_stubs.c)

#### `update_sector_location()` - Lines 84-92
**Original Implementation Location**: memory_manager-original.c:2494-2513
```c
// Current stub - needs full implementation
void update_sector_location(extended_sector_t sector, sector_location_t location, 
                           const char *filename, uint32_t offset)
{
    // TODO: Implement sector location tracking
    imx_cli_log_printf("STUB: update_sector_location(%u, %d, %s, %u)\n", 
                      sector, location, filename ? filename : "NULL", offset);
}
```
**Action**: Implement proper sector lookup table management

#### `get_sector_location()` - Lines 97-103
**Original Implementation Location**: memory_manager-original.c:2474-2489
```c
// Current stub - needs implementation
sector_location_t get_sector_location(extended_sector_t sector)
{
    // TODO: Implement sector location lookup
    imx_cli_log_printf("STUB: get_sector_location(%u)\n", sector);
    return SECTOR_LOCATION_RAM;
}
```
**Action**: Implement lookup from sector_lookup_table

### 3. Journal Operations

These functions have BOTH stub and actual implementations - need to resolve:

#### In memory_manager.c (actual implementations exist):
- `write_journal_to_disk()` - Line 491 (non-static)
- `journal_complete_operation_internal()` - Line 582 (static)
- `journal_rollback_operation()` - Line 611 (static)

#### In memory_manager_stubs.c (stubs that should be removed):
- `journal_rollback_operation()` - Lines 108-115
- `journal_complete_operation_internal()` - Lines 120-127
- `write_journal_to_disk()` - Lines 132-139

**Action**: 
1. Remove the stub versions from memory_manager_stubs.c
2. Keep the actual implementations in memory_manager.c
3. Ensure proper declarations in headers for non-static functions

### 4. Recovery Functions (memory_manager_stubs.c)

#### `process_incomplete_operations()` - Lines 166-171
**Current Implementation**: Returns 0 (success) without doing anything
```c
int process_incomplete_operations(void)
{
    // TODO: Implement recovery of incomplete operations
    imx_cli_log_printf("STUB: process_incomplete_operations()\n");
    return 0;  // Success
}
```
**Note**: The actual implementation `process_incomplete_operations_internal()` exists in memory_manager.c:983-1041

**Action**: 
1. Either remove the stub and use the internal version
2. Or make the stub call the internal version

#### `rebuild_sector_metadata()` - Lines 177-182
**Current Implementation**: Returns 0 without rebuilding
```c
uint32_t rebuild_sector_metadata(void)
{
    // TODO: Implement metadata reconstruction
    imx_cli_log_printf("STUB: rebuild_sector_metadata()\n");
    return 0;  // Return 0 sectors rebuilt
}
```
**Note**: The actual implementation `rebuild_sector_metadata_internal()` exists in memory_manager.c:912-979

**Action**: 
1. Either remove the stub and use the internal version
2. Or make the stub call the internal version

## Priority 2: Code Cleanup

### 1. Remove Duplicate Function Definitions
- Remove stub versions of functions that have actual implementations
- Update memory_manager_stubs.c to only contain true stubs

### 2. Fix Function Visibility
- Functions declared in headers should not be static
- Internal-only functions should be static and not in headers

### 3. Update CMakeLists.txt
- Ensure all new files are included in the build
- Remove any deleted files (like memory_manager_tiered_impl.c)

## Priority 3: Testing and Validation

### 1. Compile Each Module
```bash
gcc -c -I. -I./cs_ctrl -DLINUX_PLATFORM memory_manager.c
gcc -c -I. -I./cs_ctrl -DLINUX_PLATFORM memory_manager_core.c
gcc -c -I. -I./cs_ctrl -DLINUX_PLATFORM memory_manager_disk.c
# ... etc for each module
```

### 2. Link Test
- Ensure no undefined references
- Verify no duplicate symbols

### 3. Functional Testing
- Test basic memory allocation/deallocation
- Test tiered storage migration
- Test recovery after simulated failure

## Implementation Order

1. **First**: Fix the stub implementations that are blocking functionality
   - `ensure_directory_exists()`
   - `delete_disk_file_internal()`
   - `update_sector_location()`
   - `get_sector_location()`

2. **Second**: Resolve duplicate implementations
   - Remove journal operation stubs
   - Connect recovery function stubs to their actual implementations

3. **Third**: Test and validate
   - Compile all modules
   - Run basic functionality tests
   - Verify tiered storage works correctly

## Files to Modify

1. **memory_manager_stubs.c**
   - Replace stub implementations with actual code
   - Remove duplicate stubs for journal operations
   - Update recovery function stubs to call actual implementations

2. **memory_manager_internal.h**
   - Ensure all shared functions are properly declared
   - Remove any static function declarations

3. **memory_manager.c**
   - Ensure journal functions have proper visibility (not static if declared in header)

## Verification Checklist

- [ ] All stub functions have proper implementations
- [ ] No duplicate function definitions exist
- [ ] All modules compile without warnings
- [ ] No undefined references during linking
- [ ] Basic memory operations work correctly
- [ ] Tiered storage migrations work
- [ ] Recovery operations function properly
- [ ] All original functionality is preserved