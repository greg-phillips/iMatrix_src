# CS_CTRL Function Reference

## Overview
This document provides a comprehensive reference for all functions in the CS_CTRL (Control Sensor) subsystem of the iMatrix platform. The CS_CTRL subsystem manages memory allocation, sensor data storage, hardware abstraction, and tiered storage operations.

---

## 1. Memory Management Core Functions

### Sector Allocation Table (SAT) Operations

#### `void imx_sat_init(void)`
**Purpose**: Initialize the Sector Allocation Table for memory management
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Called during system initialization to set up memory structures

#### `sram_init_status_t init_sat(void)`
**Purpose**: Initialize internal SAT structures and validate memory integrity
**Parameters**: None
**Returns**: `sram_init_status_t` - Success/failure status
**Platform**: Both Linux and WICED
**Usage**: Low-level SAT initialization with error reporting

#### `int32_t imx_get_free_sector(void)` (Linux) / `int16_t imx_get_free_sector(void)` (WICED)
**Purpose**: Allocate a free sector from the SAT
**Parameters**: None
**Returns**: Sector number or -1 if no free sectors available
**Platform**: Platform-specific return types for extended addressing
**Usage**: Primary sector allocation function

#### `int32_t imx_get_free_sector_safe(void)` (Linux) / `int16_t imx_get_free_sector_safe(void)` (WICED)
**Purpose**: Safe sector allocation with validation and error checking
**Parameters**: None
**Returns**: Sector number or -1 on error
**Platform**: Platform-specific return types
**Usage**: Preferred allocation function with enhanced safety

#### `void free_sector(platform_sector_t sector)`
**Purpose**: Free a previously allocated sector
**Parameters**: `sector` - Sector number to free
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Standard sector deallocation

#### `imx_memory_error_t free_sector_safe(platform_sector_t sector)`
**Purpose**: Safe sector deallocation with validation
**Parameters**: `sector` - Sector number to free
**Returns**: `imx_memory_error_t` - Error status
**Platform**: Both Linux and WICED
**Usage**: Enhanced sector deallocation with error reporting

### Sector Chain Management

#### `platform_sector_t get_next_sector(platform_sector_t current_sector)`
**Purpose**: Get the next sector in a linked chain
**Parameters**: `current_sector` - Current sector in chain
**Returns**: Next sector number or invalid sector marker
**Platform**: Both Linux and WICED
**Usage**: Navigate through linked sector chains

#### `sector_result_t get_next_sector_safe(platform_sector_t current_sector)`
**Purpose**: Safe next sector retrieval with error reporting
**Parameters**: `current_sector` - Current sector in chain
**Returns**: `sector_result_t` structure with next sector and error status
**Platform**: Both Linux and WICED
**Usage**: Enhanced chain navigation with validation

### Raw Sector Read/Write Operations

#### `void read_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)`
**Purpose**: Read raw data from a sector
**Parameters**:
- `sector` - Sector number to read from
- `offset` - Byte offset within sector
- `data` - Buffer to store read data
- `length` - Number of 32-bit words to read
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Low-level sector data access

#### `void write_rs(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length)`
**Purpose**: Write raw data to a sector
**Parameters**:
- `sector` - Sector number to write to
- `offset` - Byte offset within sector
- `data` - Data buffer to write
- `length` - Number of 32-bit words to write
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Low-level sector data modification

#### `imx_memory_error_t read_rs_safe(platform_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length, uint16_t data_buffer_size)`
**Purpose**: Safe sector read with bounds checking
**Parameters**:
- `sector` - Sector number to read from
- `offset` - Byte offset within sector
- `data` - Buffer to store read data
- `length` - Number of 32-bit words to read
- `data_buffer_size` - Size of data buffer for validation
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Enhanced sector read with buffer overflow protection

#### `imx_memory_error_t write_rs_safe(platform_sector_t sector, uint16_t offset, const uint32_t *data, uint16_t length, uint16_t data_buffer_size)`
**Purpose**: Safe sector write with bounds checking
**Parameters**:
- `sector` - Sector number to write to
- `offset` - Byte offset within sector
- `data` - Data buffer to write
- `length` - Number of 32-bit words to write
- `data_buffer_size` - Size of data buffer for validation
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Enhanced sector write with buffer overflow protection

### Sector Metadata Operations

#### `imx_memory_error_t write_sector_id(platform_sector_t sector, uint32_t id)`
**Purpose**: Write sensor ID to sector header
**Parameters**:
- `sector` - Target sector
- `id` - Sensor ID to store
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Associate sectors with specific sensors

#### `imx_memory_error_t write_sector_next(platform_sector_t sector, platform_sector_t next_sector)`
**Purpose**: Write next sector pointer in chain
**Parameters**:
- `sector` - Current sector
- `next_sector` - Next sector in chain
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Build linked sector chains

#### `imx_memory_error_t read_sector_id(platform_sector_t sector, uint32_t *id)`
**Purpose**: Read sensor ID from sector header
**Parameters**:
- `sector` - Source sector
- `id` - Pointer to store retrieved ID
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Identify which sensor owns a sector

### Memory Validation and Utilities

#### `bool is_sector_valid(platform_sector_t sector)`
**Purpose**: Check if sector number is within valid range
**Parameters**: `sector` - Sector number to validate
**Returns**: `true` if valid, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Input validation for sector operations

#### `uint32_t get_no_free_sat_entries(void)`
**Purpose**: Get count of available free sectors
**Parameters**: None
**Returns**: Number of free sectors
**Platform**: Both Linux and WICED
**Usage**: Memory availability monitoring

#### `bool is_sector_allocated(platform_sector_t sector)`
**Purpose**: Check if sector is currently allocated
**Parameters**: `sector` - Sector number to check
**Returns**: `true` if allocated, `false` if free
**Platform**: Both Linux and WICED
**Usage**: Internal sector state tracking

#### `void mark_sector_allocated(platform_sector_t sector)`
**Purpose**: Mark sector as allocated in SAT
**Parameters**: `sector` - Sector to mark as allocated
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Internal allocation tracking

#### `void mark_sector_free(platform_sector_t sector)`
**Purpose**: Mark sector as free in SAT
**Parameters**: `sector` - Sector to mark as free
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Internal deallocation tracking

---

## 2. TSD/EVT (Time Series Data & Event) Operations

### Core TSD/EVT Functions

#### `void write_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry, uint32_t value, bool add_gps_location)`
**Purpose**: Write time series or event data with optional GPS location
**Parameters**:
- `csb` - Control sensor block configuration
- `csd` - Control sensor data structure
- `entry` - Sensor entry index
- `value` - Data value to store
- `add_gps_location` - Include GPS coordinates if available
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Primary function for logging sensor data with location context

#### `void write_tsd_evt_time(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry, uint32_t value, uint32_t utc_time)`
**Purpose**: Write TSD/EVT data with specific timestamp
**Parameters**:
- `csb` - Control sensor block configuration
- `csd` - Control sensor data structure
- `entry` - Sensor entry index
- `value` - Data value to store
- `utc_time` - Explicit UTC timestamp
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Store historical data with custom timestamps

#### `void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry, uint32_t *value)`
**Purpose**: Read stored TSD/EVT data
**Parameters**:
- `csb` - Control sensor block configuration
- `csd` - Control sensor data structure
- `entry` - Sensor entry index
- `value` - Pointer to store retrieved value
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Retrieve previously stored sensor data

#### `void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry)`
**Purpose**: Erase TSD/EVT data entry
**Parameters**:
- `csb` - Control sensor block configuration
- `csd` - Control sensor data structure
- `entry` - Sensor entry index to erase
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Delete stored sensor data

### Pending Data Management

#### `void revert_tsd_evt_pending_data(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t no_items)`
**Purpose**: Rollback pending TSD/EVT transactions
**Parameters**:
- `csb` - Control sensor block configuration
- `csd` - Control sensor data structure
- `no_items` - Number of pending items to revert
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Transaction rollback for data integrity

#### `void erase_tsd_evt_pending_data(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t no_items)`
**Purpose**: Commit pending TSD/EVT data by clearing pending count
**Parameters**:
- `csb` - Control sensor block configuration
- `csd` - Control sensor data structure
- `no_items` - Number of pending items to commit
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Transaction commit for data persistence

### Host Sensor Access

#### `imx_control_sensor_block_t *get_host_sb(void)`
**Purpose**: Get pointer to host sensor block
**Parameters**: None
**Returns**: Pointer to host control sensor block
**Platform**: Both Linux and WICED
**Usage**: Access host sensor configuration

#### `uint16_t get_host_no_sensors(void)`
**Purpose**: Get count of host sensors
**Parameters**: None
**Returns**: Number of sensors in host
**Platform**: Both Linux and WICED
**Usage**: Iterate through host sensors

### Appliance Gateway Support

#### `void imx_free_app_sectors(control_sensor_data_t *csd)`
**Purpose**: Free all sectors allocated to an appliance
**Parameters**: `csd` - Control sensor data for the appliance
**Returns**: void
**Platform**: APPLIANCE_GATEWAY builds only
**Usage**: Clean up appliance-specific data on disconnect

---

## 3. Tiered Storage System (Linux Platform Only)

### Main State Machine

#### `void process_memory(imx_time_t current_time)`
**Purpose**: Main memory management state machine
**Parameters**: `current_time` - Current system time
**Returns**: void
**Platform**: Linux only
**Usage**: Called from main loop to manage RAM-to-disk migration

#### `void init_disk_storage_system(void)`
**Purpose**: Initialize tiered storage system
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Setup disk storage infrastructure at startup

### Extended Sector Operations

#### `extended_sector_result_t get_next_sector_extended(extended_sector_t current_sector)`
**Purpose**: Get next sector in extended addressing mode
**Parameters**: `current_sector` - Current sector (32-bit)
**Returns**: `extended_sector_result_t` with next sector and error status
**Platform**: Linux only
**Usage**: Navigate chains across RAM and disk storage

#### `imx_memory_error_t read_sector_extended(extended_sector_t sector, uint16_t offset, uint32_t *data, uint16_t length, uint16_t data_buffer_size)`
**Purpose**: Read data from RAM or disk sector
**Parameters**:
- `sector` - Extended sector number
- `offset` - Byte offset within sector
- `data` - Buffer for read data
- `length` - Number of 32-bit words to read
- `data_buffer_size` - Buffer size for validation
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Linux only
**Usage**: Unified read operation across storage tiers

#### `imx_memory_error_t write_sector_extended(extended_sector_t sector, uint16_t offset, const uint32_t *data, uint16_t length, uint16_t data_buffer_size)`
**Purpose**: Write data to RAM or disk sector
**Parameters**:
- `sector` - Extended sector number
- `offset` - Byte offset within sector
- `data` - Data to write
- `length` - Number of 32-bit words to write
- `data_buffer_size` - Buffer size for validation
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Linux only
**Usage**: Unified write operation across storage tiers

#### `imx_memory_error_t free_sector_extended(extended_sector_t sector)`
**Purpose**: Free RAM or disk sector
**Parameters**: `sector` - Extended sector number to free
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Linux only
**Usage**: Unified sector deallocation across storage tiers

### Disk Sector Management

#### `extended_sector_t allocate_disk_sector(uint16_t sensor_id)`
**Purpose**: Allocate a new disk sector
**Parameters**: `sensor_id` - Sensor ID for tracking
**Returns**: Allocated disk sector number or invalid sector on failure
**Platform**: Linux only
**Usage**: Extend storage capacity to disk

#### `imx_memory_error_t move_sectors_to_disk(uint16_t sensor_id, uint16_t max_sectors, bool force_all)`
**Purpose**: Move sensor data from RAM to disk
**Parameters**:
- `sensor_id` - Sensor whose data to migrate
- `max_sectors` - Maximum sectors to move in this operation
- `force_all` - Force migration regardless of thresholds
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Linux only
**Usage**: RAM pressure relief and data archival

### Flush Operations

#### `void flush_all_to_disk(void)`
**Purpose**: Start flushing all RAM data to disk for shutdown
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Prepare for clean system shutdown

#### `uint8_t get_flush_progress(void)`
**Purpose**: Get percentage completion of flush operation
**Parameters**: None
**Returns**: Completion percentage (0-100)
**Platform**: Linux only
**Usage**: Monitor shutdown progress

#### `bool is_all_ram_empty(void)`
**Purpose**: Check if all RAM has been flushed to disk
**Parameters**: None
**Returns**: `true` if RAM is empty, `false` otherwise
**Platform**: Linux only
**Usage**: Determine when shutdown can proceed

#### `uint32_t get_pending_disk_write_count(void)`
**Purpose**: Get count of sectors pending disk write
**Parameters**: None
**Returns**: Number of sectors waiting to be written to disk
**Platform**: Linux only
**Usage**: Monitor memory pressure and flush progress

#### `void cancel_memory_flush(void)`
**Purpose**: Cancel in-progress flush operation
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Abort shutdown sequence if needed

### Disk File Operations

#### `imx_memory_error_t create_disk_file_atomic(uint16_t sensor_id, extended_sector_t *sectors, uint16_t sector_count, const char *filename)`
**Purpose**: Atomically create disk file with multiple sectors
**Parameters**:
- `sensor_id` - Sensor ID for file
- `sectors` - Array of sector numbers to write
- `sector_count` - Number of sectors in array
- `filename` - Target filename
**Returns**: `imx_memory_error_t` - Operation status
**Platform**: Linux only
**Usage**: Safe multi-sector file creation with transaction support

#### `bool read_disk_sector(const char *filename, uint16_t sector_index, extended_evt_tsd_sector_t *sector_data)`
**Purpose**: Read specific sector from disk file
**Parameters**:
- `filename` - Source disk file
- `sector_index` - Index within file
- `sector_data` - Buffer for sector data
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Random access to archived data

#### `bool write_disk_sector(const char *filename, uint16_t sector_index, const extended_evt_tsd_sector_t *sector_data)`
**Purpose**: Write specific sector to disk file
**Parameters**:
- `filename` - Target disk file
- `sector_index` - Index within file
- `sector_data` - Sector data to write
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Update archived data

### Disk Space Management

#### `uint64_t get_available_disk_space(void)`
**Purpose**: Get available disk space in bytes
**Parameters**: None
**Returns**: Available disk space in bytes
**Platform**: Linux only
**Usage**: Monitor disk capacity for storage decisions

#### `uint64_t get_total_disk_space(void)`
**Purpose**: Get total disk space in bytes
**Parameters**: None
**Returns**: Total disk space in bytes
**Platform**: Linux only
**Usage**: Calculate disk usage percentages

#### `bool is_disk_usage_acceptable(void)`
**Purpose**: Check if disk usage is within acceptable limits
**Parameters**: None
**Returns**: `true` if usage is acceptable, `false` if approaching limits
**Platform**: Linux only
**Usage**: Determine when to start freeing old data

#### `bool free_oldest_disk_data(uint64_t bytes_needed)`
**Purpose**: Free oldest disk data to reclaim space
**Parameters**: `bytes_needed` - Minimum bytes to free
**Returns**: `true` if successful, `false` if insufficient data to free
**Platform**: Linux only
**Usage**: Automatic disk space management

### Disk Sector Recycling

#### `void init_disk_sector_recycling(void)`
**Purpose**: Initialize disk sector recycling system
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Setup for efficient sector reuse

#### `void cleanup_disk_sector_recycling(void)`
**Purpose**: Cleanup disk sector recycling structures
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Shutdown cleanup

#### `void add_sector_to_free_list(extended_sector_t sector)`
**Purpose**: Add sector to recycling free list
**Parameters**: `sector` - Sector to add to free list
**Returns**: void
**Platform**: Linux only
**Usage**: Track freed sectors for reuse

#### `extended_sector_t get_recycled_sector(void)`
**Purpose**: Get a recycled sector from free list
**Parameters**: None
**Returns**: Recycled sector number or invalid sector if none available
**Platform**: Linux only
**Usage**: Reuse previously allocated sectors

#### `bool is_sector_in_free_list(extended_sector_t sector)`
**Purpose**: Check if sector is in recycling free list
**Parameters**: `sector` - Sector to check
**Returns**: `true` if in free list, `false` otherwise
**Platform**: Linux only
**Usage**: Avoid double-free operations

#### `uint32_t get_recycled_sector_count(void)`
**Purpose**: Get count of sectors available for recycling
**Parameters**: None
**Returns**: Number of sectors in free list
**Platform**: Linux only
**Usage**: Monitor recycling efficiency

### File Management

#### `void check_and_cleanup_disk_file(const char *filename)`
**Purpose**: Check disk file integrity and cleanup if corrupted
**Parameters**: `filename` - File to check
**Returns**: void
**Platform**: Linux only
**Usage**: Maintain data integrity

#### `void cleanup_freed_disk_files(void)`
**Purpose**: Remove disk files that have been completely freed
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Reclaim disk space from obsolete files

---

## 4. Power Failure Recovery & Journaling (Linux Platform Only)

### Recovery System

#### `void perform_power_failure_recovery(void)`
**Purpose**: Perform complete power failure recovery sequence
**Parameters**: None
**Returns**: void
**Platform**: Linux only
**Usage**: Called at startup to recover from unclean shutdown

#### `bool is_recovery_needed(void)`
**Purpose**: Check if recovery is needed
**Parameters**: None
**Returns**: `true` if recovery required, `false` otherwise
**Platform**: Linux only
**Usage**: Determine if clean shutdown occurred

#### `recovery_state_t get_recovery_state(void)`
**Purpose**: Get current recovery state
**Parameters**: None
**Returns**: Current recovery state
**Platform**: Linux only
**Usage**: Monitor recovery progress

### Journal Operations

#### `int init_recovery_journal(void)`
**Purpose**: Initialize recovery journal system
**Parameters**: None
**Returns**: 0 on success, negative on error
**Platform**: Linux only
**Usage**: Setup transaction logging

#### `bool write_journal_to_disk(void)`
**Purpose**: Write journal data to disk
**Parameters**: None
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Persist transaction log

#### `bool read_journal_from_disk(void)`
**Purpose**: Read journal data from disk
**Parameters**: None
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Load transaction log for recovery

#### `uint32_t journal_begin_operation(const char *temp_filename, const char *final_filename, extended_sector_t *sectors, uint32_t sector_count)`
**Purpose**: Begin journaled file operation
**Parameters**:
- `temp_filename` - Temporary file being created
- `final_filename` - Final filename after completion
- `sectors` - Array of sectors involved
- `sector_count` - Number of sectors
**Returns**: Sequence number for operation tracking
**Platform**: Linux only
**Usage**: Start atomic file operations

#### `bool journal_update_progress(uint32_t sequence, file_operation_state_t new_state)`
**Purpose**: Update operation progress in journal
**Parameters**:
- `sequence` - Operation sequence number
- `new_state` - New state of operation
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Track operation progress for recovery

#### `bool journal_complete_operation(uint32_t sequence)`
**Purpose**: Mark operation as completed in journal
**Parameters**: `sequence` - Operation sequence number
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Commit successful operations

#### `bool journal_rollback_operation(uint32_t sequence)`
**Purpose**: Rollback failed operation
**Parameters**: `sequence` - Operation sequence number
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Clean up failed operations

### Validation and Repair

#### `imx_memory_error_t validate_all_sector_chains(void)`
**Purpose**: Validate integrity of all sector chains
**Parameters**: None
**Returns**: `imx_memory_error_t` - Validation results
**Platform**: Linux only
**Usage**: Comprehensive data integrity check

#### `int process_incomplete_operations(void)`
**Purpose**: Process incomplete operations from journal
**Parameters**: None
**Returns**: Number of operations processed
**Platform**: Linux only
**Usage**: Complete or rollback interrupted operations

#### `uint32_t rebuild_sector_metadata(void)`
**Purpose**: Rebuild sector metadata from disk files
**Parameters**: None
**Returns**: Number of sectors processed
**Platform**: Linux only
**Usage**: Reconstruct metadata after corruption

#### `uint32_t calculate_checksum(const void *data, size_t size)`
**Purpose**: Calculate checksum for data validation
**Parameters**:
- `data` - Data to checksum
- `size` - Size of data in bytes
**Returns**: Calculated checksum
**Platform**: Linux only
**Usage**: Data integrity verification

---

## 5. Hardware Abstraction Layer (HAL)

### Core HAL Functions

#### `void hal_sample_init(void)`
**Purpose**: Initialize hardware sampling system
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup sampling infrastructure at startup

#### `void hal_sample(imx_peripheral_type_t type, imx_time_t current_time)`
**Purpose**: Perform sampling for specified peripheral type
**Parameters**:
- `type` - Peripheral type to sample
- `current_time` - Current system time
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Called periodically to sample sensors

#### `void hal_event(imx_peripheral_type_t type, uint16_t entry, void *value)`
**Purpose**: Process hardware event
**Parameters**:
- `type` - Peripheral type generating event
- `entry` - Sensor entry index
- `value` - Event data
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Handle asynchronous hardware events

#### `void imx_hal_event(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, imx_peripheral_type_t type, uint16_t entry, void *value)`
**Purpose**: Process HAL event with sensor context
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `type` - Peripheral type
- `entry` - Sensor entry index
- `value` - Event data
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Enhanced event processing with full sensor context

### Sample Processing

#### `void imx_sample_csd_data(imx_time_t current_time, uint16_t cs_index, imx_control_sensor_block_t *csb, control_sensor_data_t *csd, device_updates_t *check_in)`
**Purpose**: Process sampled control sensor data
**Parameters**:
- `current_time` - Current system time
- `cs_index` - Control sensor index
- `csb` - Control sensor block
- `csd` - Control sensor data
- `check_in` - Device update structure
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Core sample processing pipeline

#### `bool imx_should_save_sample(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t cs_index, imx_data_32_t *new_value)`
**Purpose**: Determine if sample should be saved based on change thresholds
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `cs_index` - Sensor index
- `new_value` - New sample value
**Returns**: `true` if sample should be saved, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Optimize storage by filtering insignificant changes

#### `void imx_process_sample_value(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t cs_index, imx_data_32_t *value, imx_time_t current_time, device_updates_t *check_in)`
**Purpose**: Process and store a sample value
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `cs_index` - Sensor index
- `value` - Sample value to process
- `current_time` - Current system time
- `check_in` - Device update structure
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Complete sample processing including storage and notifications

### Calibration and Processing

#### `void imx_apply_calibration(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t cs_index, imx_data_32_t *value)`
**Purpose**: Apply calibration to sensor value
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `cs_index` - Sensor index
- `value` - Value to calibrate (modified in place)
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Convert raw sensor readings to calibrated values

#### `bool imx_update_max_value(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t cs_index, imx_data_32_t *value)`
**Purpose**: Update maximum value tracking for sensor
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `cs_index` - Sensor index
- `value` - Current value
**Returns**: `true` if new maximum detected, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Track peak values for analysis

#### `void imx_check_warning_levels(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t cs_index, imx_data_32_t *value)`
**Purpose**: Check if value exceeds warning thresholds
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `cs_index` - Sensor index
- `value` - Value to check
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Generate alerts for out-of-range conditions

### Change Detection

#### `bool imx_check_percent_change_wrapper(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t cs_index, imx_data_32_t *new_value)`
**Purpose**: Check if value change exceeds percentage threshold
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `cs_index` - Sensor index
- `new_value` - New value to compare
**Returns**: `true` if change exceeds threshold, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Determine significant value changes

#### `bool check_int_percent(int32_t ref_value, int32_t last_value, uint16_t percentage)`
**Purpose**: Check percentage change for signed integer values
**Parameters**:
- `ref_value` - Reference value
- `last_value` - Previous value
- `percentage` - Change threshold percentage
**Returns**: `true` if change exceeds threshold, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Integer change detection

#### `bool check_uint_percent(uint32_t ref_value, uint32_t last_value, uint16_t percentage)`
**Purpose**: Check percentage change for unsigned integer values
**Parameters**:
- `ref_value` - Reference value
- `last_value` - Previous value
- `percentage` - Change threshold percentage
**Returns**: `true` if change exceeds threshold, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Unsigned integer change detection

#### `bool check_float_percent(float ref_value, float last_value, uint16_t percentage)`
**Purpose**: Check percentage change for floating-point values
**Parameters**:
- `ref_value` - Reference value
- `last_value` - Previous value
- `percentage` - Change threshold percentage
**Returns**: `true` if change exceeds threshold, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Floating-point change detection

---

## 6. Configuration Management

### System Configuration

#### `void cs_reset_defaults(void)`
**Purpose**: Reset control and sensor configurations to defaults
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Restore factory configuration settings

#### `void cs_init(void)`
**Purpose**: Initialize control and sensor system
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup CS subsystem at startup

#### `void cs_build_config(void)`
**Purpose**: Build control and sensor configuration structures
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Construct runtime configuration from defaults

#### `void cs_memory_init(void)`
**Purpose**: Initialize CS memory management
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup memory structures for CS operations

#### `void flush_all_devices(void)`
**Purpose**: Flush pending data for all devices
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Force data persistence before shutdown

### Configuration Display

#### `void print_common_config(imx_peripheral_type_t type, imx_control_sensor_block_t *csb)`
**Purpose**: Print common configuration for peripheral type
**Parameters**:
- `type` - Peripheral type to display
- `csb` - Control sensor block to display
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Debug and configuration verification

#### `void imx_print_csb_entry(imx_peripheral_type_t type, imx_control_sensor_block_t *csb, uint16_t entry)`
**Purpose**: Print control sensor block entry details
**Parameters**:
- `type` - Peripheral type
- `csb` - Control sensor block
- `entry` - Entry index to display
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Detailed sensor configuration display

#### `void imx_print_csb_entry_with_ranges(imx_peripheral_type_t type, imx_control_sensor_block_t *csb, uint16_t entry)`
**Purpose**: Print CSB entry with value ranges
**Parameters**:
- `type` - Peripheral type
- `csb` - Control sensor block
- `entry` - Entry index to display
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Show sensor limits and thresholds

#### `void imx_print_csb_entry_with_monitor(imx_peripheral_type_t type, imx_control_sensor_block_t *csb, uint16_t entry)`
**Purpose**: Print CSB entry with monitoring information
**Parameters**:
- `type` - Peripheral type
- `csb` - Control sensor block
- `entry` - Entry index to display
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Show monitoring and alert configuration

#### `void imx_print_status_entry(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t i, bool display_all)`
**Purpose**: Print sensor status entry with timing information
**Parameters**:
- `csb` - Control sensor block
- `csd` - Control sensor data
- `i` - Entry index
- `display_all` - Show all entries or only valid ones
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Monitor sensor status and sampling times

### Data Conversion

#### `bool imx_data_32_to_str(imx_data_32_t value, imx_data_types_t data_type, char str[PRINT_STR_SIZE])`
**Purpose**: Convert 32-bit data value to string representation
**Parameters**:
- `value` - Data value to convert
- `data_type` - Type of data (uint32, int32, float)
- `str` - Output string buffer
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Format sensor values for display

### Configuration Modification

#### `bool imx_set_poll_rate(imx_peripheral_type_t type, uint16_t entry, uint32_t new_rate)`
**Purpose**: Set polling rate for sensor entry
**Parameters**:
- `type` - Peripheral type
- `entry` - Sensor entry index
- `new_rate` - New polling rate in milliseconds
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Runtime configuration adjustment

#### `uint32_t imx_get_sensor_poll_rate(uint16_t entry)`
**Purpose**: Get current polling rate for sensor
**Parameters**: `entry` - Sensor entry index
**Returns**: Current polling rate in milliseconds
**Platform**: Both Linux and WICED
**Usage**: Query current configuration

### Default Configuration Loading

#### `void load_config_defaults_generic_scb(uint16_t arg)`
**Purpose**: Load default sensor configuration
**Parameters**: `arg` - Configuration argument
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Initialize sensor defaults

#### `void load_config_defaults_generic_ccb(uint16_t arg)`
**Purpose**: Load default control configuration
**Parameters**: `arg` - Configuration argument
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Initialize control defaults

---

## 7. External Memory Management

### External SRAM Operations

#### `void init_ext_memory(uint32_t ext_sram_size)`
**Purpose**: Initialize external memory system
**Parameters**: `ext_sram_size` - Size of external SRAM in bytes
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup external memory for expanded storage

#### `void init_ext_sram_sat(void)`
**Purpose**: Initialize external SRAM sector allocation table
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup SAT for external SRAM management

#### `sram_init_status_t process_external_sat_init(void)`
**Purpose**: Process external SRAM SAT initialization
**Parameters**: None
**Returns**: `sram_init_status_t` - Initialization status
**Platform**: Both Linux and WICED
**Usage**: Complete external SRAM setup with error reporting

#### `uint32_t get_ext_sram_size(void)`
**Purpose**: Get size of external SRAM
**Parameters**: None
**Returns**: External SRAM size in bytes
**Platform**: Both Linux and WICED
**Usage**: Query external memory capacity

#### `bool is_ext_sram_available(void)`
**Purpose**: Check if external SRAM is available
**Parameters**: None
**Returns**: `true` if available, `false` otherwise
**Platform**: Both Linux and WICED
**Usage**: Determine if external memory can be used

#### `uint32_t get_total_external_memory(void)`
**Purpose**: Get total external memory size
**Parameters**: None
**Returns**: Total external memory in bytes
**Platform**: Both Linux and WICED
**Usage**: Calculate total storage capacity

#### `uint32_t get_free_external_memory(void)`
**Purpose**: Get available external memory
**Parameters**: None
**Returns**: Free external memory in bytes
**Platform**: Both Linux and WICED
**Usage**: Monitor external memory usage

#### `void print_external_memory_stats(void)`
**Purpose**: Print external memory statistics
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Debug and monitoring

### Serial Flash Operations

#### `bool init_sflash_storage(void)`
**Purpose**: Initialize serial flash storage
**Parameters**: None
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Setup serial flash for data storage

#### `bool erase_sflash_sector(uint32_t sector_address)`
**Purpose**: Erase serial flash sector
**Parameters**: `sector_address` - Address of sector to erase
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Prepare flash for writing

#### `bool write_sflash_data(uint32_t address, const uint8_t *data, uint32_t length)`
**Purpose**: Write data to serial flash
**Parameters**:
- `address` - Flash address to write to
- `data` - Data to write
- `length` - Length of data in bytes
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Store data in non-volatile memory

#### `bool read_sflash_data(uint32_t address, uint8_t *data, uint32_t length)`
**Purpose**: Read data from serial flash
**Parameters**:
- `address` - Flash address to read from
- `data` - Buffer for read data
- `length` - Length of data to read
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Retrieve stored data

#### `bool get_sflash_info(uint8_t *manufacturer_id, uint16_t *device_id)`
**Purpose**: Get serial flash device information
**Parameters**:
- `manufacturer_id` - Pointer to store manufacturer ID
- `device_id` - Pointer to store device ID
**Returns**: `true` on success, `false` on error
**Platform**: Both Linux and WICED
**Usage**: Identify flash device for proper operation

---

## 8. Interface Functions

### Control/Sensor Interface

#### `imx_status_t imx_get_control_sensor(imx_peripheral_type_t type, uint16_t entry, void *value)`
**Purpose**: Get control or sensor value
**Parameters**:
- `type` - Peripheral type
- `entry` - Entry index
- `value` - Pointer to store retrieved value
**Returns**: `imx_status_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Read current sensor value or control state

#### `imx_status_t imx_set_control_sensor(imx_peripheral_type_t type, uint16_t entry, void *value)`
**Purpose**: Set control or sensor value
**Parameters**:
- `type` - Peripheral type
- `entry` - Entry index
- `value` - Pointer to value to set
**Returns**: `imx_status_t` - Operation status
**Platform**: Both Linux and WICED
**Usage**: Write control value or configure sensor

#### `bool imx_parse_value(imx_peripheral_type_t type, uint16_t entry, char *string, imx_data_32_t *value)`
**Purpose**: Parse string to appropriate data type
**Parameters**:
- `type` - Peripheral type
- `entry` - Entry index
- `string` - String to parse
- `value` - Parsed value output
**Returns**: `true` on success, `false` on parse error
**Platform**: Both Linux and WICED
**Usage**: Convert user input to typed values

#### `uint16_t imx_get_no_imatrix_entries(imx_peripheral_type_t type, uint16_t entry)`
**Purpose**: Get number of iMatrix entries for type
**Parameters**:
- `type` - Peripheral type
- `entry` - Entry index
**Returns**: Number of iMatrix entries
**Platform**: Both Linux and WICED
**Usage**: Determine array sizes for data transfer

---

## 9. Statistics and Monitoring

### Memory Statistics

#### `void imx_init_memory_statistics(void)`
**Purpose**: Initialize memory statistics tracking
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup statistics collection at startup

#### `void imx_update_memory_statistics(void)`
**Purpose**: Update memory usage statistics
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Refresh statistics for monitoring

#### `void imx_reset_memory_statistics(void)`
**Purpose**: Reset memory statistics to initial state
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Clear statistics counters

#### `imx_memory_statistics_t* imx_get_memory_statistics(void)`
**Purpose**: Get current memory statistics
**Parameters**: None
**Returns**: Pointer to memory statistics structure
**Platform**: Both Linux and WICED
**Usage**: Access statistics for monitoring or reporting

#### `uint32_t imx_calculate_fragmentation_level(void)`
**Purpose**: Calculate memory fragmentation level
**Parameters**: None
**Returns**: Fragmentation level (0-100 percentage)
**Platform**: Both Linux and WICED
**Usage**: Monitor memory efficiency

#### `void imx_print_memory_statistics(void)`
**Purpose**: Print detailed memory statistics
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Debug and performance monitoring

#### `void imx_print_memory_summary(void)`
**Purpose**: Print summary of memory usage
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Quick memory status overview

#### `void print_sflash_life(void)`
**Purpose**: Print serial flash life statistics
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Monitor flash wear leveling

#### `void cli_memory_sat(uint16_t arg)`
**Purpose**: CLI command for memory SAT operations
**Parameters**: `arg` - Command argument
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Interactive memory management

### Notification System

#### `void init_notification_queue(void)`
**Purpose**: Initialize notification queue system
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Setup event notification infrastructure

#### `void log_notification(uint32_t sensor_id, imx_notifications_t notification_type)`
**Purpose**: Log notification event
**Parameters**:
- `sensor_id` - Sensor generating notification
- `notification_type` - Type of notification
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Record events for later processing

#### `void print_notifications(void)`
**Purpose**: Print logged notifications
**Parameters**: None
**Returns**: void
**Platform**: Both Linux and WICED
**Usage**: Review system events and alerts

---

## 10. Utility Functions

### File and Directory Operations (Linux Platform Only)

#### `bool ensure_directory_exists(const char *path)`
**Purpose**: Create directory if it doesn't exist
**Parameters**: `path` - Directory path to ensure
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Setup directory structure for file operations

#### `bool delete_disk_file_internal(const char *filename)`
**Purpose**: Safely delete disk file
**Parameters**: `filename` - File to delete
**Returns**: `true` on success, `false` on error
**Platform**: Linux only
**Usage**: Clean up obsolete data files

#### `void update_sector_location(extended_sector_t sector, sector_location_t location, const char *filename, uint32_t file_offset, uint16_t sensor_id)`
**Purpose**: Update sector location tracking
**Parameters**:
- `sector` - Sector to update
- `location` - New location (RAM/DISK/FREED)
- `filename` - Filename if on disk
- `file_offset` - Offset within file
- `sensor_id` - Associated sensor ID
**Returns**: void
**Platform**: Linux only
**Usage**: Track sector locations across storage tiers

#### `sector_location_t get_sector_location(extended_sector_t sector)`
**Purpose**: Get current location of sector
**Parameters**: `sector` - Sector to query
**Returns**: Current sector location
**Platform**: Linux only
**Usage**: Determine where sector data is stored

### Legacy Compatibility

#### `uint16_t get_next_sector_compatible(uint16_t current_sector)`
**Purpose**: Get next sector with 16-bit compatibility
**Parameters**: `current_sector` - Current sector (16-bit)
**Returns**: Next sector number (16-bit)
**Platform**: Both Linux and WICED
**Usage**: Maintain compatibility with legacy code

---

## Error Codes and Return Values

### Common Error Types

- **IMX_MEMORY_SUCCESS**: Operation completed successfully
- **IMX_MEMORY_ERROR_INVALID_SECTOR**: Sector number out of range
- **IMX_MEMORY_ERROR_INVALID_OFFSET**: Offset exceeds sector boundaries
- **IMX_MEMORY_ERROR_INVALID_LENGTH**: Length parameter invalid
- **IMX_MEMORY_ERROR_BUFFER_TOO_SMALL**: Output buffer insufficient
- **IMX_MEMORY_ERROR_OUT_OF_BOUNDS**: Access beyond valid range
- **IMX_MEMORY_ERROR_NULL_POINTER**: NULL pointer passed to function
- **IMX_MEMORY_ERROR_EXT_SRAM_NOT_SUPPORTED**: External SRAM not available

### Platform-Specific Constants

- **LINUX_PLATFORM**: 32-bit extended addressing, PLATFORM_MAX_SECTORS = 0xFFFFFFFF
- **WICED_PLATFORM**: 16-bit addressing, PLATFORM_MAX_SECTORS = 0xFFFF

---

## Integration Notes

### Initialization Sequence
1. `imx_sat_init()` - Initialize sector allocation table
2. `init_ext_memory()` - Setup external memory if available
3. `cs_memory_init()` - Initialize CS memory management
4. `hal_sample_init()` - Setup hardware sampling
5. `init_notification_queue()` - Initialize notifications
6. `imx_init_memory_statistics()` - Setup statistics tracking
7. `init_disk_storage_system()` - Initialize tiered storage (Linux only)

### Main Loop Integration
- Call `hal_sample()` periodically for each peripheral type
- Call `process_memory()` regularly for tiered storage management (Linux only)
- Call `imx_update_memory_statistics()` for monitoring

### Shutdown Sequence
1. `flush_all_devices()` - Ensure all data is persistent
2. `flush_all_to_disk()` - Move all RAM data to disk (Linux only)
3. Monitor `get_flush_progress()` until complete (Linux only)
4. `cleanup_disk_sector_recycling()` - Clean up resources (Linux only)

This comprehensive reference covers all major functions in the CS_CTRL subsystem, providing the information needed to understand and use the iMatrix memory management and sensor control system effectively.