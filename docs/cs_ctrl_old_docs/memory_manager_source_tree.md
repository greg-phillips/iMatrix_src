# Memory Manager Source Tree and Dependency Analysis

## Module Hierarchy

```
iMatrix/
├── cs_ctrl/
│   ├── memory_manager.c                 [657 lines]  - Main coordinator
│   ├── memory_manager.h                 [Public API header]
│   ├── memory_manager_internal.h        [Internal shared definitions]
│   ├── memory_manager_core.c            [856 lines]  - Core SAT operations
│   ├── memory_manager_core.h            [Core function declarations]
│   ├── memory_manager_tsd_evt.c         [1158 lines] - Event management
│   ├── memory_manager_tsd_evt.h         [Event function declarations]
│   ├── memory_manager_external.c        [186 lines]  - External memory
│   ├── memory_manager_external.h        [External memory declarations]
│   ├── memory_manager_stats.c           [1060 lines] - Statistics
│   ├── memory_manager_stats.h           [Statistics declarations]
│   ├── memory_manager_tiered.c          [1315 lines] - Tiered storage
│   ├── memory_manager_tiered.h          [Tiered storage declarations]
│   ├── memory_manager_disk.c            [155 lines]  - Disk operations
│   ├── memory_manager_disk.h            [Disk operation declarations]
│   ├── memory_manager_recovery.c        [62 lines]   - Recovery
│   ├── memory_manager_recovery.h        [Recovery declarations]
│   └── memory_manager_utils.c           [298 lines]  - Utilities
│
├── canbus/
│   └── can_imx_upload.h                 [Host interface functions]
│
└── device/
    └── icb_def.h                        [iMatrix Control Block definition]
```

## Include Dependencies

### memory_manager.c includes:
```c
#include "imatrix.h"
#include "imx_platform.h"
#include "../cli/interface.h"
#include "../device/icb_def.h"
#include "../storage.h"
#include "../spi_flash_fast_erase/spi_flash_fast_erase.h"
#include "../sflash/sflash.h"
#include "memory_manager.h"
#include "memory_manager_internal.h"
#include "memory_manager_tsd_evt.h"
#include "memory_manager_external.h"
#include "memory_manager_tiered.h"
#include "memory_manager_disk.h"
#include "memory_manager_recovery.h"
#include "../time/ck_time.h"
#ifdef CAN_PLATFORM
#include "../canbus/can_structs.h"
#include "../canbus/can_imx_upload.h"
#endif
```

### Module Include Pattern:
Each module follows this pattern:
```c
#include <system_headers>
#include "imatrix.h"
#include "memory_manager.h"
#include "memory_manager_internal.h"
#include "module_specific.h"
```

## Function Call Graph

### Initialization Flow
```
main()
└── imx_sat_init()
    ├── init_sat() [core.c]
    │   ├── memset(sat, 0x00, sizeof(sat))
    │   ├── mark_sector_allocated() [x SAT_RESERVED_SECTORS]
    │   └── imx_init_memory_statistics() [stats.c]
    └── init_disk_storage_system() [tiered.c] (Linux only)
        ├── ensure_directory_exists() [utils.c]
        ├── calloc(sector_lookup_table)
        ├── init_recovery_journal() [manager.c]
        └── perform_power_failure_recovery() [recovery.c]
            ├── read_journal_from_disk() [manager.c]
            ├── scan_disk_files() [manager.c]
            ├── rebuild_sector_metadata() [utils.c]
            └── process_incomplete_operations() [utils.c]
```

### Memory Allocation Flow
```
Application Request
└── imx_get_free_sector_safe() [core.c]
    ├── is_sector_valid() [core.c]
    ├── find free bit in sat[]
    ├── mark_sector_allocated() [core.c]
    └── imx_update_memory_statistics() [stats.c]
```

### Data Write Flow
```
write_tsd_evt() [tsd_evt.c]
├── validate_parameters()
├── get_ram_sector_address() [core.c]
├── check sector chain
├── allocate new sector if needed
│   └── imx_get_free_sector_safe() [core.c]
├── write_rs_safe() [core.c]
│   ├── validate_memmove_bounds() [core.c]
│   └── memcpy to rs[]
└── update metadata
```

### Tiered Storage Flow
```
process_memory() [tiered.c] - Called periodically
├── State: IDLE
│   └── transition to CHECK_USAGE
├── State: CHECK_USAGE
│   ├── get_memory_pressure()
│   └── if > 80%, transition to MOVE_TO_DISK
├── State: MOVE_TO_DISK
│   ├── select_sensor_for_migration()
│   ├── move_sectors_to_disk()
│   │   ├── create_disk_file_atomic() [disk.c]
│   │   ├── journal_begin_operation() [tiered.c]
│   │   ├── write sectors to temp file
│   │   ├── rename to final file
│   │   ├── update_sector_location() [utils.c]
│   │   ├── free RAM sectors
│   │   └── journal_complete_operation() [manager.c]
│   └── transition back to CHECK_USAGE
└── State: CLEANUP_DISK
    └── manage disk space
```

### Recovery Flow
```
perform_power_failure_recovery() [recovery.c]
├── scan_disk_files() [manager.c]
│   └── scan_hierarchical_directories()
├── rebuild_sector_metadata() [utils.c]
│   ├── for each disk file
│   ├── extract sector info from filename
│   └── update sector_lookup_table
└── process_incomplete_operations() [utils.c]
    ├── read journal entries
    ├── for each incomplete operation
    │   ├── if write incomplete → rollback
    │   └── if rename incomplete → check and complete/rollback
    └── update journal
```

## Global Variable Access Patterns

### sat[] (Sector Allocation Table)
```
Writers:
- mark_sector_allocated() [core.c]
- mark_sector_free() [core.c]

Readers:
- imx_get_free_sector_safe() [core.c]
- is_sector_allocated() [core.c]
- get_no_free_sat_entries() [core.c]
- print_sat() [tsd_evt.c]
```

### rs[] (RAM Sectors)
```
Writers:
- write_rs() [core.c]
- write_rs_safe() [core.c]

Readers:
- read_rs() [core.c]
- read_rs_safe() [core.c]
- get_ram_sector_address() [core.c]
```

### memory_stats
```
Writers:
- imx_init_memory_statistics() [stats.c]
- imx_update_memory_statistics() [stats.c]
- imx_reset_memory_statistics() [stats.c]

Readers:
- imx_get_memory_statistics() [stats.c]
- imx_print_memory_statistics() [stats.c]
- imx_calculate_fragmentation_level() [stats.c]
```

### tiered_module_state
```
Definition: memory_manager.c:130

Writers:
- init_disk_storage_system() [tiered.c]
- allocate_disk_sector() [tiered.c]
- rebuild_sector_metadata() [utils.c]

Readers:
- process_incomplete_operations() [utils.c]
- write_journal_to_disk() [manager.c]
- All tiered storage functions
```

### sector_lookup_table
```
Definition: memory_manager_tiered.c:88

Writers:
- update_sector_location() [utils.c]
- rebuild_sector_metadata() [utils.c]
- move_sectors_to_disk() [tiered.c]

Readers:
- get_sector_location() [utils.c]
- read_sector_extended() [tiered.c]
- write_sector_extended() [tiered.c]
```

## Cross-Module Dependencies

### Strong Dependencies
```
core.c ← All modules (foundation)
internal.h ← All modules (shared definitions)
manager.c ← tiered.c (journal operations)
utils.c ← tiered.c (directory/file operations)
```

### Weak Dependencies
```
stats.c → Other modules (monitoring only)
external.c → core.c (extends functionality)
recovery.c → manager.c, utils.c (recovery only)
```

## Platform-Specific Code

### Linux Platform (#ifdef LINUX_PLATFORM)
- memory_manager_tiered.c (entire module)
- memory_manager_disk.c (entire module)
- Extended sector operations in manager.c
- Recovery journal in manager.c
- All functions in utils.c

### WICED Platform (#ifdef WICED_PLATFORM)
- External SRAM operations in external.c
- 16-bit sector numbers (platform_sector_t)
- No tiered storage support

## Critical Paths

### Performance Critical
1. `read_rs_safe()` / `write_rs_safe()` - Direct memory access
2. `imx_get_free_sector_safe()` - Sector allocation
3. `get_sector_location()` - Location lookup

### Reliability Critical
1. `journal_*` operations - Data integrity
2. `create_disk_file_atomic()` - Atomic operations
3. `process_incomplete_operations()` - Recovery

### Memory Critical
1. `sector_lookup_table` - Scales with disk sectors
2. `disk_files` array - Scales with file count
3. `rs[]` array - Main RAM storage

## Module Cohesion Analysis

### High Cohesion Modules
- **memory_manager_core.c**: All SAT operations
- **memory_manager_stats.c**: All statistics
- **memory_manager_external.c**: All external memory

### Medium Cohesion Modules
- **memory_manager_tiered.c**: State machine + disk operations
- **memory_manager_utils.c**: Mixed utilities

### Low Cohesion Modules
- **memory_manager.c**: Coordinator + legacy functions

## Recommendations

1. **API Documentation**: Create comprehensive API docs for each module
2. **Unit Testing**: Implement module-specific unit tests
3. **Performance Profiling**: Add hooks for critical paths
4. **Further Refactoring**: Consider splitting manager.c further
5. **Error Handling**: Standardize error codes across modules