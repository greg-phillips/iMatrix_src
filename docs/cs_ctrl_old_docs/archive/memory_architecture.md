# iMatrix Memory Manager Architecture

## Overview

The iMatrix Memory Manager has been refactored from a monolithic 3969-line file into a modular architecture consisting of 8 specialized modules. This document describes the architecture, module responsibilities, inter-module dependencies, and usage guidelines.

## Architecture Design

### Design Principles

1. **Separation of Concerns**: Each module handles a specific aspect of memory management
2. **Platform Independence**: Core functionality works across all platforms with platform-specific extensions
3. **Safety First**: Safe versions of functions with comprehensive error checking
4. **Tiered Storage**: Automatic RAM-to-disk migration on Linux platforms
5. **Recovery Resilience**: Power failure recovery and journaling for data integrity

### Module Structure

```
memory_manager/
├── memory_manager.h              # Public API (existing, updated)
├── memory_manager_internal.h     # Shared internal structures
├── memory_manager_core.c/h       # Core SAT operations
├── memory_manager_tsd_evt.c/h    # TSD/EVT data operations
├── memory_manager_external.c/h   # External memory (SRAM/SFLASH)
├── memory_manager_tiered.c/h     # Tiered storage (Linux)
├── memory_manager_disk.c/h       # Disk operations (Linux)
├── memory_manager_recovery.c/h   # Recovery system (Linux)
├── memory_manager_stats.c/h      # Statistics and monitoring
└── memory_architecture.md        # This document
```

## Module Responsibilities

### 1. Core Module (memory_manager_core.c)

**Purpose**: Manages the Sector Allocation Table (SAT) and provides fundamental memory operations.

**Key Functions**:
- `imx_sat_init()` - Initialize the SAT
- `imx_get_free_sector()` - Allocate a free sector
- `free_sector()` - Deallocate a sector
- `read_rs()` / `write_rs()` - Raw sector I/O
- `get_next_sector()` - Navigate sector chains

**Dependencies**: None (base module)

### 2. TSD/EVT Module (memory_manager_tsd_evt.c)

**Purpose**: Handles Time Series Data (TSD) and Event (EVT) data operations with GPS integration.

**Key Functions**:
- `write_tsd_evt()` - Write sensor data with optional GPS
- `read_tsd_evt()` - Read sensor data
- `erase_tsd_evt()` - Remove data entries
- `revert_tsd_evt_pending_data()` - Transaction rollback

**Dependencies**: Core module for sector operations

### 3. External Memory Module (memory_manager_external.c)

**Purpose**: Manages external SRAM and SFLASH for WICED platforms.

**Key Functions**:
- `init_ext_memory()` - Initialize external memory
- `init_ext_sram_sat()` - Setup external SRAM allocation table
- SFLASH read/write/erase operations

**Dependencies**: Core module for SAT integration

### 4. Tiered Storage Module (memory_manager_tiered.c)

**Purpose**: Implements automatic RAM-to-disk data migration for Linux platforms.

**Key Functions**:
- `init_disk_storage_system()` - Initialize tiered storage
- `process_memory()` - Main state machine (called from main loop)
- `move_sectors_to_disk()` - Migrate data to disk
- `allocate_disk_sector()` - Create disk-only sectors

**Dependencies**: Core, Disk, and Recovery modules

### 5. Disk Operations Module (memory_manager_disk.c)

**Purpose**: Handles all disk I/O operations including hierarchical directory management.

**Key Functions**:
- `create_disk_file_atomic()` - Atomic file creation
- `read_disk_sector()` / `write_disk_sector()` - Disk I/O
- `get_bucket_directory()` - Hierarchical directory management
- `validate_disk_file()` - File integrity checking

**Dependencies**: Recovery module for journaling

### 6. Recovery Module (memory_manager_recovery.c)

**Purpose**: Provides power failure recovery and journaling for data integrity.

**Key Functions**:
- `perform_power_failure_recovery()` - Main recovery routine
- Journal management functions
- `rebuild_sector_metadata()` - Reconstruct state from disk

**Dependencies**: Disk module for file operations

### 7. Statistics Module (memory_manager_stats.c)

**Purpose**: Tracks memory usage, provides monitoring, and implements CLI commands.

**Key Functions**:
- `imx_print_memory_statistics()` - Detailed statistics output
- `imx_calculate_fragmentation_level()` - Memory fragmentation analysis
- `cli_memory_sat()` - CLI command handler
- Real-time usage monitoring

**Dependencies**: Core module for SAT access

### 8. Internal Header (memory_manager_internal.h)

**Purpose**: Defines shared structures and global variables used across modules.

**Key Elements**:
- Internal type definitions (tsd_sector_t, evt_tsd_sector_t)
- Global variable declarations (SAT, statistics, state machines)
- Internal helper function prototypes
- Platform-specific macros

## Inter-Module Dependencies

```
                    ┌─────────────────┐
                    │  Application    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ memory_manager.h│ (Public API)
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│   TSD/EVT      │  │     Stats       │  │    Tiered      │
│   Module       │  │     Module      │  │    Storage     │
└───────┬────────┘  └────────┬────────┘  └───────┬────────┘
        │                    │                    │
        └────────────────────┼────────────────────┤
                             │                    │
                    ┌────────▼────────┐  ┌────────▼────────┐
                    │   Core Module   │  │  Disk Module   │
                    │     (SAT)       │  │                │
                    └────────┬────────┘  └────────┬────────┘
                             │                    │
                    ┌────────▼────────┐  ┌────────▼────────┐
                    │External Memory  │  │   Recovery     │
                    │    Module       │  │    Module      │
                    └─────────────────┘  └────────────────┘
```

## Platform-Specific Features

### Linux Platform
- **Extended Addressing**: 32-bit sector numbers (billions of sectors)
- **Tiered Storage**: Automatic RAM-to-disk migration at 80% threshold
- **Hierarchical Directories**: Max 1000 files per directory
- **Recovery Journal**: Power failure recovery
- **Disk Sector Allocation**: Seamless extension beyond RAM

### WICED Platform
- **16-bit Sectors**: Memory-efficient for embedded systems
- **External SRAM**: Optional SPI SRAM support
- **SFLASH Storage**: Serial flash for configuration

## Global Variables Management

Global variables are centralized in `memory_manager_internal.h`:

1. **SAT Bitmap** (`icb.sat`): Sector allocation tracking
2. **Memory Statistics** (`memory_stats`): Usage metrics
3. **Tiered State Machine** (`tiered_state_machine`): Linux-specific
4. **Disk Files Array** (`disk_files`): Disk file tracking
5. **Recovery Journal** (`journal`): Atomic operations log
6. **Sector Lookup Table** (`sector_lookup_table`): Location mapping

## API Reference

### Core Operations

```c
// Initialize memory system
void imx_sat_init(void);

// Allocate a sector
#ifdef LINUX_PLATFORM
int32_t imx_get_free_sector(void);  // Returns extended sector
#else
int16_t imx_get_free_sector(void);  // Returns 16-bit sector
#endif

// Free a sector
void free_sector(platform_sector_t sector);

// Navigate chains
platform_sector_t get_next_sector(platform_sector_t current);
```

### Data Operations

```c
// Write sensor data
void write_tsd_evt(imx_control_sensor_block_t *csb, 
                   control_sensor_data_t *csd,
                   uint16_t entry, uint32_t value, 
                   bool add_gps_location);

// Read sensor data
void read_tsd_evt(imx_control_sensor_block_t *csb,
                  control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value);
```

### Safe Operations

All core functions have "safe" versions with comprehensive error checking:

```c
imx_memory_error_t read_rs_safe(platform_sector_t sector, 
                               uint16_t offset,
                               uint32_t *data, 
                               uint16_t length,
                               uint16_t buffer_size);
```

### Tiered Storage (Linux)

```c
// Initialize tiered storage
void init_disk_storage_system(void);

// Main processing loop (call periodically)
void process_memory(imx_time_t current_time);

// Force data to disk
void flush_all_to_disk(void);
```

## Usage Examples

### Basic Allocation and Write

```c
// Allocate a sector
int32_t sector = imx_get_free_sector();
if (sector < 0) {
    printf("Allocation failed\n");
    return;
}

// Write data
uint32_t data[4] = {0x12345678, 0x9ABCDEF0, 0xDEADBEEF, 0xCAFEBABE};
write_rs(sector, 0, data, 4);

// Free when done
free_sector(sector);
```

### TSD Data Storage

```c
// Write time series data with GPS
write_tsd_evt(&sensor_blocks[0], &sensor_data[0], 
              entry_index, sensor_value, true);

// Read it back
uint32_t value;
read_tsd_evt(&sensor_blocks[0], &sensor_data[0], 
             entry_index, &value);
```

### Safe Operations with Error Checking

```c
uint32_t buffer[10];
imx_memory_error_t result = read_rs_safe(sector, 0, buffer, 
                                        10, sizeof(buffer));
if (result != IMX_MEMORY_SUCCESS) {
    printf("Read failed: %d\n", result);
}
```

## Migration Guide

### From Monolithic to Modular

1. **Include Headers**: Replace `#include "memory_manager.h"` with specific module headers as needed
2. **No API Changes**: Public APIs remain the same
3. **Link All Modules**: Update build system to include all module source files
4. **Platform Defines**: Ensure LINUX_PLATFORM or WICED_PLATFORM is defined

### CMakeLists.txt Update

Replace:
```cmake
cs_ctrl/memory_manager.c
```

With:
```cmake
cs_ctrl/memory_manager_core.c
cs_ctrl/memory_manager_tsd_evt.c
cs_ctrl/memory_manager_external.c
cs_ctrl/memory_manager_stats.c
# Linux-specific modules
$<$<BOOL:${LINUX_PLATFORM}>:cs_ctrl/memory_manager_tiered.c>
$<$<BOOL:${LINUX_PLATFORM}>:cs_ctrl/memory_manager_disk.c>
$<$<BOOL:${LINUX_PLATFORM}>:cs_ctrl/memory_manager_recovery.c>
```

## Testing and Validation

### Unit Testing
Each module can be tested independently:
- Core: Test SAT allocation/deallocation
- TSD/EVT: Test data storage and retrieval
- Stats: Verify statistics accuracy
- Tiered: Test migration thresholds

### Integration Testing
- Full system test with all modules
- Power failure recovery testing
- Memory pressure testing (fill to 80%+)
- Performance benchmarking

### Existing Tests
The following tests have been updated for the new architecture:
- `spillover_test.c` - Tests 80% spillover with up to 10M records
- `diagnostic_test.c` - Extended sector diagnostics
- `simple_memory_test.c` - Basic allocation tests
- `tiered_storage_test.c` - Tiered storage validation

## Performance Considerations

1. **Reduced Context**: Each module loads only required code
2. **Cache Efficiency**: Better locality of reference
3. **Parallel Development**: Teams can work on different modules
4. **Conditional Compilation**: Platform-specific code only when needed
5. **Optimized Includes**: Reduced compilation dependencies

## Future Enhancements

1. **Compression**: Add data compression for disk storage
2. **Encryption**: Encrypt sensitive data at rest
3. **Remote Storage**: Network-attached storage support
4. **Hot/Cold Tiers**: Multiple storage tiers based on access patterns
5. **Predictive Migration**: ML-based migration decisions

## Troubleshooting

### Common Issues

1. **Linking Errors**: Ensure all module source files are included in build
2. **Undefined Symbols**: Check module dependencies and link order
3. **Platform Mismatch**: Verify correct platform defines
4. **Recovery Loops**: Check journal corruption, delete journal file

### Debug Techniques

1. Enable debug logging: `#define PRINT_DEBUGS_ADD_TSD_EVT`
2. Use CLI commands: `memory sat 1` for statistics
3. Check fragmentation: High fragmentation indicates allocation patterns
4. Monitor disk usage: Ensure sufficient disk space for tiered storage

## Conclusion

The modular architecture provides better maintainability, testability, and scalability while preserving the original API. The separation allows for platform-specific optimizations and easier debugging of specific subsystems.