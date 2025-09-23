# Fix for rs Array Usage in Tiered Storage System

## Issue
The `rs` array (record store) defined at line 130 of memory_manager.c was not being properly utilized in the tiered storage system's `move_sectors_to_disk()` function. The function had placeholder code that created empty sectors instead of reading actual data from RAM.

## Root Cause
The `move_sectors_to_disk()` function in memory_manager_tiered.c had simplified placeholder logic that:
1. Did not access the control/sensor data structures to find sectors
2. Did not read actual sector data from the `rs` array
3. Created empty sectors with only sensor_id filled

## Solution Implemented

### 1. Added Access to Control/Sensor Data Structures
- Added code to access the iMatrix Control Block (icb) structure
- Implemented lookup logic to find the control_sensor_data_t for a given sensor_id
- Searches both controls (i_ccb/i_cd) and sensors (i_scb/i_sd)

### 2. Implemented Proper Sector Chain Traversal
- Uses the data_store_info_t structure (ds) to find start_sector and end_sector
- Traverses the sector chain using next_sector pointers
- Validates sector numbers before accessing

### 3. Reads Actual Data from rs Array
- Directly accesses the rs array to read sector data:
  ```c
  evt_tsd_sector_t *ram_sector = (evt_tsd_sector_t *)&rs[current_sector * SRAM_SECTOR_SIZE];
  ```
- Copies the entire sector including:
  - Data payload (sensor/control readings)
  - Sector ID
  - Next sector pointer

### 4. Properly Frees RAM Sectors After Migration
- After successful disk write, frees the migrated RAM sectors
- Updates the control/sensor data structure to point to disk sectors
- Updates memory statistics to reflect freed RAM

## Code Changes

### memory_manager_tiered.c
1. Added extern declaration for `rs` array
2. Added includes for required headers (common.h, icb_def.h)
3. Replaced placeholder sector collection with actual implementation
4. Added proper RAM sector freeing after migration
5. Updated control/sensor data structures with new disk sector addresses

## Benefits
1. **Correct Memory Usage**: Now properly uses the rs array for RAM storage
2. **Data Preservation**: Actual sensor/control data is migrated to disk, not lost
3. **Memory Reclamation**: RAM sectors are properly freed after migration
4. **Statistics Accuracy**: Memory usage statistics correctly reflect freed RAM

## Testing Recommendations
1. Verify sectors are properly read from rs array before migration
2. Confirm data integrity after migration to disk
3. Check that RAM sectors are freed and reusable
4. Monitor memory statistics during migration

## Architecture Confirmation
The implementation confirms the intended architecture:
- `rs` array = RAM storage (first tier)
- Disk files = Disk storage (second tier)
- Migration occurs when RAM usage exceeds 80% threshold
- Sector addressing properly distinguishes RAM (< SAT_NO_SECTORS) from disk (>= DISK_SECTOR_BASE)