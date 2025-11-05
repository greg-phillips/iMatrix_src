# MM2 Comprehensive Test Expansion Plan

## Executive Summary

This document provides a detailed plan for expanding the MM2 memory manager test suite to achieve **100% API coverage** and **comprehensive integration testing**. The current test suite has 23 test functions covering basic operations, but significant gaps exist in disk operations, power management, multi-source scenarios, and edge cases.

**Current Coverage**: ~60% of MM2 API functions
**Target Coverage**: 100% of public API + critical internal functions
**New Tests Required**: 45+ new test functions
**Estimated Implementation**: 2-3 weeks full-time

---

## Table of Contents

1. [Current Test Coverage Analysis](#current-test-coverage-analysis)
2. [Coverage Gaps Identified](#coverage-gaps-identified)
3. [Detailed New Test Specifications](#detailed-new-test-specifications)
4. [Test Infrastructure Enhancements](#test-infrastructure-enhancements)
5. [Implementation Priority](#implementation-priority)
6. [Success Metrics](#success-metrics)

---

## Current Test Coverage Analysis

### Existing Tests (23 functions)

#### ✅ Basic Operations (Good Coverage)
1. **test_validate_allocated_sectors()** - Validates pre-allocated sector chains
2. **test_sector_chains()** - Tests chain creation and traversal
3. **test_tsd_operations()** - Tests TSD write/read operations
4. **test_evt_operations()** - Tests EVT write/read operations
5. **test_error_recovery()** - Tests error handling mechanisms

#### ✅ Stress and Performance (Good Coverage)
6. **test_stress_allocation()** - Stress tests memory allocation
7. **test_performance_benchmark()** - Benchmarks operation performance
8. **test_corner_cases()** - Tests edge scenarios

#### ✅ Transaction Management (Partial Coverage)
9. **test_pending_transactions()** - Tests pending data management
10. **test_upload_data_integrity()** - Tests data integrity during upload
11. **test_data_lifecycle()** - Tests write-read-send-erase cycle

#### ⚠️ Disk Operations (Limited Coverage)
12. **test_disk_overflow()** - Tests disk spooling (Linux only)
13. **test_file_system_operations()** - Tests file system ops (STUB)

#### ⚠️ Power Management (Stub Only)
14. **test_normal_shutdown()** - Normal shutdown (STUB)
15. **test_power_failure_mid_cycle()** - Power failure (STUB)
16. **test_power_up_recovery()** - Recovery on startup (STUB)
17. **test_stress_recovery()** - Stress recovery (STUB)
18. **test_multi_csd_validation()** - Multi-sensor flush (STUB)

#### ✅ Debugging/Isolation (Good Coverage)
19. **test_simple_isolation()** - Simple isolation test
20. **test_ultra_simple()** - Ultra-simple 4-record test
21. **test_underflow_trigger()** - Underflow bug reproduction
22. **test_corruption_reproduction()** - CSD corruption test
23. **test_comprehensive_validation()** - Multi-device validation

### MM2 Public API Functions (33 total)

#### Initialization and Lifecycle
1. ✅ `imx_memory_manager_init()` - Tested indirectly
2. ⚠️ `imx_memory_manager_shutdown()` - STUB only
3. ✅ `imx_memory_manager_ready()` - Tested indirectly

#### Data Write Operations
4. ✅ `imx_write_tsd()` - Well tested
5. ✅ `imx_write_evt()` - Well tested
6. ❌ `imx_write_event_with_gps()` - **NOT TESTED**

#### Data Read Operations
7. ✅ `imx_read_next_tsd_evt()` - Well tested (just fixed bugs)
8. ✅ `imx_read_bulk_samples()` - Tested
9. ⚠️ `imx_peek_next_tsd_evt()` - Limited testing
10. ⚠️ `imx_peek_bulk_samples()` - Limited testing

#### Sample Count Functions
11. ✅ `imx_get_new_sample_count()` - Well tested
12. ✅ `imx_get_total_sample_count()` - Well tested
13. ❌ `imx_has_pending_data()` - **NOT TESTED**

#### Transaction Management
14. ✅ `imx_revert_all_pending()` - Tested (just fixed)
15. ✅ `imx_erase_all_pending()` - Well tested

#### Sensor Lifecycle
16. ⚠️ `imx_configure_sensor()` - Indirect testing only
17. ⚠️ `imx_activate_sensor()` - Indirect testing only
18. ⚠️ `imx_deactivate_sensor()` - Indirect testing only

#### Statistics and Diagnostics
19. ⚠️ `imx_get_memory_stats()` - Limited testing
20. ⚠️ `imx_validate_sector_chains()` - Limited testing
21. ❌ `imx_get_sensor_state()` - **NOT TESTED**
22. ❌ `imx_force_garbage_collection()` - **NOT TESTED**

#### Power Management
23. ❌ `imx_power_event_detected()` - **NOT TESTED**
24. ❌ `handle_power_abort_recovery()` - **NOT TESTED**
25. ❌ `get_power_abort_statistics()` - **NOT TESTED**

#### Disk Recovery
26. ❌ `imx_recover_sensor_disk_data()` - **NOT TESTED**

#### Time Management
27. ⚠️ `imx_set_utc_available()` - STM32 only, no testing
28. ❌ `imx_time_get_system_time()` - **NOT TESTED**

#### Background Processing
29. ⚠️ `process_memory_manager()` - Indirect testing only

### Coverage Summary
- **Well Tested**: 11/33 (33%)
- **Limited/Indirect Testing**: 11/33 (33%)
- **Not Tested**: 11/33 (33%)

---

## Coverage Gaps Identified

### Critical Gaps (Must Fix)

#### 1. GPS-Enhanced Event Writing
- **Missing**: `imx_write_event_with_gps()` testing
- **Impact**: HIGH - Critical for geofenced events
- **Scenarios needed**:
  - Event with all GPS sensors present
  - Event with partial GPS data (lat/lon only)
  - Event with invalid GPS sensor IDs
  - Timestamp synchronization across sensors

#### 2. Power Management Lifecycle
- **Missing**: All power management functions
- **Impact**: CRITICAL - Data loss prevention
- **Scenarios needed**:
  - Normal graceful shutdown
  - Emergency power-down detection
  - Power abort recovery
  - Mid-cycle interruption
  - Multiple power cycles

#### 3. Disk Operations (Linux)
- **Missing**: Comprehensive disk spooling and recovery
- **Impact**: CRITICAL - Data persistence
- **Scenarios needed**:
  - Normal RAM→disk spooling
  - Disk→RAM reading
  - Multi-file management
  - File corruption recovery
  - Disk space exhaustion
  - Disk I/O errors

#### 4. Multi-Source Operations
- **Missing**: Testing across multiple upload sources
- **Impact**: HIGH - Multi-device support
- **Scenarios needed**:
  - Gateway + BLE + CAN simultaneous operation
  - Source isolation verification
  - Directory separation validation
  - Cross-source interference testing

#### 5. Peek Operations
- **Missing**: Non-destructive read testing
- **Impact**: MEDIUM - CLI and diagnostics
- **Scenarios needed**:
  - Peek without affecting read position
  - Peek vs read consistency
  - Peek beyond available data
  - Bulk peek operations

### Important Gaps (Should Fix)

#### 6. Sensor Lifecycle Management
- **Missing**: Explicit sensor activate/deactivate testing
- **Scenarios needed**:
  - Activate inactive sensor
  - Deactivate active sensor with data
  - Rapid activate/deactivate cycling
  - Lifecycle state transitions

#### 7. Garbage Collection
- **Missing**: Forced garbage collection testing
- **Scenarios needed**:
  - Manual GC trigger
  - GC effectiveness measurement
  - GC with pending data
  - Multi-sensor GC coordination

#### 8. Chain Validation
- **Missing**: Comprehensive chain validation
- **Scenarios needed**:
  - Circular chain detection
  - Broken chain detection
  - Orphaned sector detection
  - Chain length verification

#### 9. Statistics and State
- **Missing**: Detailed state inspection
- **Scenarios needed**:
  - Memory statistics accuracy
  - Sensor state enumeration
  - Pool utilization tracking
  - Performance metrics

### Nice-to-Have Gaps

#### 10. Time Management (STM32)
- **Missing**: UTC availability testing
- **Impact**: LOW (Linux testing only)
- **Scenarios needed**: STM32-specific UTC blocking

#### 11. Background Processing
- **Missing**: Explicit process_memory_manager() testing
- **Impact**: LOW (tested indirectly)
- **Scenarios needed**: State machine progression

---

## Detailed New Test Specifications

### Category 1: GPS-Enhanced Event Operations (3 tests)

#### Test 1.1: GPS Event with Complete Location Data
```c
test_result_t test_gps_event_complete_location(void)
```
**Purpose**: Verify synchronized GPS data writing with events

**Test Steps**:
1. Configure event sensor + GPS sensors (lat, lon, speed)
2. Write event with GPS data
3. Verify all sensors received data with same timestamp
4. Read back and verify timestamp synchronization
5. Verify data integrity across all sensors

**Success Criteria**:
- All GPS sensors written successfully
- Timestamps match exactly (±1ms tolerance)
- Values match expected GPS data
- Pending counts update correctly

**Edge Cases**:
- GPS data at limits (±180° lon, ±90° lat)
- Zero speed
- High speed values

---

#### Test 1.2: GPS Event with Partial Location Data
```c
test_result_t test_gps_event_partial_location(void)
```
**Purpose**: Verify graceful handling of missing GPS sensors

**Test Steps**:
1. Configure event sensor + partial GPS (lat/lon only, no speed)
2. Pass `IMX_INVALID_SENSOR_ID` for missing sensors
3. Write event with partial GPS
4. Verify only provided sensors were written
5. Verify missing sensors unaffected

**Success Criteria**:
- Event written successfully
- Provided GPS sensors updated
- Missing sensors unchanged
- No crashes or errors

**Edge Cases**:
- All GPS sensors invalid
- Only one GPS sensor valid
- GPS sensors not activated

---

#### Test 1.3: GPS Event Error Handling
```c
test_result_t test_gps_event_error_handling(void)
```
**Purpose**: Test GPS event failure scenarios

**Test Steps**:
1. Test invalid event sensor
2. Test invalid GPS sensor IDs (out of range)
3. Test GPS sensor not activated
4. Test memory exhaustion during GPS write
5. Test partial write failure recovery

**Success Criteria**:
- Errors detected and returned correctly
- No partial writes committed
- System state remains consistent
- No memory leaks

---

### Category 2: Power Management Operations (8 tests)

#### Test 2.1: Normal Graceful Shutdown
```c
test_result_t test_normal_graceful_shutdown(void)
```
**Purpose**: Test orderly shutdown with data preservation

**Test Steps**:
1. Write data to multiple sensors
2. Call `imx_memory_manager_shutdown()` for each sensor
3. Verify all data spooled to disk
4. Verify files created correctly
5. Verify RAM sectors freed
6. Restart and verify recovery

**Success Criteria**:
- All data preserved to disk
- Files properly formatted
- Shutdown completes within timeout
- Recovery successful

---

#### Test 2.2: Emergency Power-Down Detection
```c
test_result_t test_emergency_power_down(void)
```
**Purpose**: Test emergency shutdown with power loss imminent

**Test Steps**:
1. Write data to sensors
2. Call `imx_power_event_detected()`
3. Verify emergency spooling initiated
4. Verify partial data saved
5. Verify emergency file format
6. Test recovery from emergency files

**Success Criteria**:
- Emergency mode activated immediately
- Critical data preserved
- Emergency format correct
- Recovery restores maximum data

---

#### Test 2.3: Power Abort Recovery
```c
test_result_t test_power_abort_recovery(void)
```
**Purpose**: Test recovery from aborted power-down

**Test Steps**:
1. Initiate power-down sequence
2. Abort mid-sequence
3. Call `handle_power_abort_recovery()`
4. Verify emergency files cleaned
5. Verify normal operation restored
6. Verify data integrity maintained

**Success Criteria**:
- Emergency files deleted
- Normal mode restored
- No data loss
- Statistics updated correctly

---

#### Test 2.4: Power-Down Mid-Cycle Interruption
```c
test_result_t test_power_down_mid_cycle(void)
```
**Purpose**: Test power loss during active operations

**Test Steps**:
1. Start writing large dataset
2. Trigger power-down mid-write
3. Verify partial data preserved
4. Restart and verify recovery
5. Verify data consistency

**Success Criteria**:
- Partial data not corrupted
- Recovery completes successfully
- No orphaned sectors
- Chain integrity maintained

---

#### Test 2.5: Multiple Power Cycle Stress Test
```c
test_result_t test_multiple_power_cycles(void)
```
**Purpose**: Test repeated power loss scenarios

**Test Steps**:
1. Write data
2. Trigger shutdown → Recovery cycle (10 times)
3. Verify data accumulation correct
4. Verify no resource leaks
5. Verify performance degradation acceptable

**Success Criteria**:
- Data preserved across all cycles
- No memory leaks
- File count stays reasonable
- Recovery time consistent

---

#### Test 2.6: Timeout Handling During Shutdown
```c
test_result_t test_shutdown_timeout_handling(void)
```
**Purpose**: Test behavior when shutdown exceeds timeout

**Test Steps**:
1. Write massive dataset
2. Shutdown with short timeout (1 second)
3. Verify partial preservation
4. Verify timeout respected
5. Verify system state valid after timeout

**Success Criteria**:
- Shutdown exits at timeout
- Maximum data saved within time
- System state consistent
- No hangs or deadlocks

---

#### Test 2.7: Power Abort Statistics Tracking
```c
test_result_t test_power_abort_statistics(void)
```
**Purpose**: Verify abort statistics accuracy

**Test Steps**:
1. Perform several power abort scenarios
2. Call `get_power_abort_statistics()`
3. Verify counts match actual aborts
4. Verify file deletion counts correct
5. Test statistics persistence

**Success Criteria**:
- Abort count accurate
- File deletion count accurate
- Statistics survive power cycles
- Statistics reset when appropriate

---

#### Test 2.8: Concurrent Sensor Shutdown
```c
test_result_t test_concurrent_sensor_shutdown(void)
```
**Purpose**: Test shutting down multiple sensors simultaneously

**Test Steps**:
1. Activate 50+ sensors with data
2. Shutdown all sensors concurrently
3. Verify all data preserved
4. Verify no race conditions
5. Verify file system handles load

**Success Criteria**:
- All sensors shut down successfully
- All data preserved
- No file corruption
- Timeout sufficient for all

---

### Category 3: Disk Operations (Linux) (10 tests)

#### Test 3.1: Normal RAM to Disk Spooling
```c
test_result_t test_normal_ram_to_disk_spool(void)
```
**Purpose**: Test automatic spooling at memory pressure

**Test Steps**:
1. Fill RAM to 80% capacity
2. Verify spooling triggered automatically
3. Verify sectors moved to disk
4. Verify RAM sectors freed
5. Verify disk files created correctly

**Success Criteria**:
- Spooling triggers at threshold
- Data preserved correctly
- File format valid
- RAM freed appropriately

---

#### Test 3.2: Disk to RAM Reading
```c
test_result_t test_disk_to_ram_reading(void)
```
**Purpose**: Test reading spooled data back from disk

**Test Steps**:
1. Spool data to disk
2. Attempt to read spooled data
3. Verify data loaded from disk
4. Verify data integrity maintained
5. Verify read position updated correctly

**Success Criteria**:
- Disk data loaded successfully
- Data matches original
- Performance acceptable
- No file leaks

---

#### Test 3.3: Multi-File Management
```c
test_result_t test_multi_file_management(void)
```
**Purpose**: Test managing multiple spool files per sensor

**Test Steps**:
1. Write enough data to create multiple files
2. Verify file rotation occurs
3. Verify file sequence numbers correct
4. Verify reading spans multiple files
5. Verify old files cleaned up

**Success Criteria**:
- Files rotate at size limit
- Sequence numbers sequential
- Reading works across files
- Cleanup prevents unbounded growth

---

#### Test 3.4: Disk File Corruption Recovery
```c
test_result_t test_disk_file_corruption_recovery(void)
```
**Purpose**: Test recovery from corrupted spool files

**Test Steps**:
1. Create spool files
2. Corrupt file header/CRC
3. Attempt recovery
4. Verify corrupted file detected
5. Verify other files still readable

**Success Criteria**:
- Corruption detected via CRC
- Corrupted file quarantined or deleted
- Other data unaffected
- Error logged appropriately

---

#### Test 3.5: Disk Space Exhaustion
```c
test_result_t test_disk_space_exhaustion(void)
```
**Purpose**: Test behavior when disk fills up

**Test Steps**:
1. Fill disk to near capacity
2. Attempt to spool more data
3. Verify error handling
4. Verify oldest files deleted (if configured)
5. Verify system remains operational

**Success Criteria**:
- Disk full detected
- Error returned gracefully
- Optional oldest-file deletion works
- System doesn't crash

---

#### Test 3.6: Disk I/O Error Handling
```c
test_result_t test_disk_io_error_handling(void)
```
**Purpose**: Test handling of disk I/O failures

**Test Steps**:
1. Simulate disk write failure
2. Simulate disk read failure
3. Verify error detection
4. Verify retry logic
5. Verify fallback behavior

**Success Criteria**:
- I/O errors detected
- Retries attempted (if configured)
- Errors propagated correctly
- No infinite loops

---

#### Test 3.7: Concurrent Disk Access
```c
test_result_t test_concurrent_disk_access(void)
```
**Purpose**: Test thread safety of disk operations

**Test Steps**:
1. Spawn multiple threads writing to disk
2. Spawn threads reading from disk
3. Verify no race conditions
4. Verify data integrity
5. Verify file handles managed correctly

**Success Criteria**:
- No crashes
- No data corruption
- Locks prevent races
- File handles don't leak

---

#### Test 3.8: Spool File Format Validation
```c
test_result_t test_spool_file_format_validation(void)
```
**Purpose**: Verify disk file format correctness

**Test Steps**:
1. Write data to disk
2. Read file directly (not via API)
3. Verify magic number
4. Verify header fields
5. Verify CRC calculation
6. Verify data section format

**Success Criteria**:
- Magic number correct
- All header fields populated
- CRC matches data
- Format matches specification

---

#### Test 3.9: Recovery File Management
```c
test_result_t test_recovery_file_management(void)
```
**Purpose**: Test management of recovery files

**Test Steps**:
1. Create spool files
2. Simulate crash/restart
3. Call `imx_recover_sensor_disk_data()`
4. Verify files discovered
5. Verify data reloaded
6. Verify files cleaned after recovery

**Success Criteria**:
- Recovery finds all files
- Data loaded correctly
- Files deleted post-recovery
- Recovery idempotent

---

#### Test 3.10: Spool State Machine Progression
```c
test_result_t test_spool_state_machine(void)
```
**Purpose**: Test disk spooling state machine

**Test Steps**:
1. Trigger spooling
2. Monitor state transitions
3. Verify: IDLE → SELECTING → WRITING → VERIFYING → CLEANUP → IDLE
4. Test state machine timeouts
5. Test error state handling

**Success Criteria**:
- All states reachable
- Transitions correct
- Timeouts prevent hangs
- Error recovery works

---

### Category 4: Multi-Source Operations (5 tests)

#### Test 4.1: Simultaneous Multi-Source Writing
```c
test_result_t test_multi_source_simultaneous_writes(void)
```
**Purpose**: Test Gateway + BLE + CAN writing concurrently

**Test Steps**:
1. Activate sensors in all upload sources
2. Write data to all sources simultaneously
3. Verify data isolation
4. Verify no cross-contamination
5. Verify directories created correctly

**Success Criteria**:
- All sources write successfully
- Data separated by source
- Directories: /mm2/gateway/, /mm2/ble/, /mm2/can/
- Pending counts per-source correct

---

#### Test 4.2: Source Isolation Verification
```c
test_result_t test_upload_source_isolation(void)
```
**Purpose**: Verify upload sources don't interfere

**Test Steps**:
1. Write to Gateway source
2. Read from BLE source (should be empty)
3. Write to BLE source
4. Verify Gateway unaffected
5. Test pending data isolation

**Success Criteria**:
- Sources completely isolated
- Pending data tracked per-source
- Reading from wrong source returns no data
- ACK/NACK affects only correct source

---

#### Test 4.3: Multi-Source Pending Transaction Management
```c
test_result_t test_multi_source_pending_transactions(void)
```
**Purpose**: Test pending data across multiple sources

**Test Steps**:
1. Write data to sensor in Gateway source
2. Read data (marks pending)
3. Write same sensor from BLE source
4. Read from BLE (marks pending separately)
5. ACK Gateway, verify BLE still pending
6. ACK BLE, verify Gateway unaffected

**Success Criteria**:
- Pending tracked independently per source
- ACK affects only target source
- NACK restores correct source
- No cross-source interference

---

#### Test 4.4: Multi-Source Disk Spooling
```c
test_result_t test_multi_source_disk_spooling(void)
```
**Purpose**: Verify disk spooling with multiple sources

**Test Steps**:
1. Fill RAM with Gateway data
2. Verify Gateway data spools to /mm2/gateway/
3. Fill RAM with BLE data
4. Verify BLE data spools to /mm2/ble/
5. Verify directories independent

**Success Criteria**:
- Each source has own spool directory
- Files named with source identifier
- Recovery reads from correct directory
- Quota management per-source

---

#### Test 4.5: Multi-Source Recovery
```c
test_result_t test_multi_source_recovery(void)
```
**Purpose**: Test recovery with multiple sources

**Test Steps**:
1. Spool data from all sources
2. Simulate restart
3. Recover each source separately
4. Verify data restored to correct source
5. Verify no cross-source pollution

**Success Criteria**:
- Each source recovers independently
- Data restored to correct sensors
- File cleanup per-source
- No directory confusion

---

### Category 5: Peek Operations (4 tests)

#### Test 5.1: Peek Without Side Effects
```c
test_result_t test_peek_no_side_effects(void)
```
**Purpose**: Verify peek doesn't affect read position

**Test Steps**:
1. Write 10 records
2. Peek record 0
3. Peek record 5
4. Read record 0 (should still be available)
5. Verify pending count unchanged

**Success Criteria**:
- Peek returns correct data
- Read position unchanged
- Pending count unchanged
- Data still available for reading

---

#### Test 5.2: Peek vs Read Consistency
```c
test_result_t test_peek_read_consistency(void)
```
**Purpose**: Verify peek and read return same data

**Test Steps**:
1. Write data
2. Peek record N
3. Read record N
4. Verify values match
5. Test across multiple records

**Success Criteria**:
- Peek and read data identical
- Timestamps match
- Works for both TSD and EVT

---

#### Test 5.3: Peek Beyond Available Data
```c
test_result_t test_peek_beyond_available(void)
```
**Purpose**: Test peek at invalid indices

**Test Steps**:
1. Write 5 records
2. Peek record 10 (beyond available)
3. Verify error returned
4. Peek record -1 (invalid)
5. Verify error handling

**Success Criteria**:
- Errors returned gracefully
- No crashes
- No undefined behavior

---

#### Test 5.4: Bulk Peek Operations
```c
test_result_t test_bulk_peek_operations(void)
```
**Purpose**: Test `imx_peek_bulk_samples()`

**Test Steps**:
1. Write 100 records
2. Peek bulk starting at index 20, count 10
3. Verify correct records returned
4. Verify read position unchanged
5. Test peek across sector boundaries

**Success Criteria**:
- Correct records returned
- Read position unchanged
- Works across sectors
- Performance acceptable

---

### Category 6: Sensor Lifecycle Management (4 tests)

#### Test 6.1: Sensor Activation
```c
test_result_t test_sensor_activation(void)
```
**Purpose**: Test `imx_activate_sensor()`

**Test Steps**:
1. Configure sensor
2. Call `imx_activate_sensor()`
3. Verify sensor active
4. Verify resources allocated
5. Test writing to activated sensor

**Success Criteria**:
- Sensor marked active
- Memory allocated
- Writes succeed
- State correct

---

#### Test 6.2: Sensor Deactivation with Data
```c
test_result_t test_sensor_deactivation_with_data(void)
```
**Purpose**: Test `imx_deactivate_sensor()` when data present

**Test Steps**:
1. Activate sensor and write data
2. Call `imx_deactivate_sensor()`
3. Verify data flushed to disk
4. Verify sectors freed
5. Verify sensor marked inactive

**Success Criteria**:
- Data preserved
- Memory freed
- Sensor inactive
- Files created if needed

---

#### Test 6.3: Rapid Activate/Deactivate Cycling
```c
test_result_t test_rapid_sensor_cycling(void)
```
**Purpose**: Test rapid activation/deactivation

**Test Steps**:
1. Activate sensor
2. Deactivate immediately
3. Repeat 100 times
4. Verify no resource leaks
5. Verify state consistency

**Success Criteria**:
- No memory leaks
- No file handle leaks
- State always consistent
- Performance acceptable

---

#### Test 6.4: Sensor Configuration Changes
```c
test_result_t test_sensor_reconfiguration(void)
```
**Purpose**: Test `imx_configure_sensor()` with changes

**Test Steps**:
1. Configure sensor as TSD (sample_rate > 0)
2. Write TSD data
3. Reconfigure as EVT (sample_rate = 0)
4. Verify old data handled correctly
5. Write EVT data

**Success Criteria**:
- Reconfiguration succeeds
- Old data preserved or flushed
- New writes use new format
- No corruption

---

### Category 7: Chain and Memory Management (5 tests)

#### Test 7.1: Chain Circular Reference Detection
```c
test_result_t test_chain_circular_detection(void)
```
**Purpose**: Test detection of circular chain references

**Test Steps**:
1. Create chain artificially: A→B→C→A
2. Call `imx_validate_sector_chains()`
3. Verify circular reference detected
4. Test chain traversal limits
5. Verify error reported

**Success Criteria**:
- Circular reference detected
- Error returned
- System doesn't hang
- Chain traversal terminates

---

#### Test 7.2: Broken Chain Detection
```c
test_result_t test_broken_chain_detection(void)
```
**Purpose**: Test detection of broken chains

**Test Steps**:
1. Create chain: A→B→INVALID_ID
2. Validate chain
3. Verify broken link detected
4. Test recovery options

**Success Criteria**:
- Broken link detected
- Error reported clearly
- No crashes
- Recovery possible

---

#### Test 7.3: Orphaned Sector Detection
```c
test_result_t test_orphaned_sector_detection(void)
```
**Purpose**: Detect sectors not in any chain

**Test Steps**:
1. Allocate sector but don't link to chain
2. Run garbage collection
3. Verify orphaned sector found
4. Verify orphan cleaned up

**Success Criteria**:
- Orphans detected
- Orphans freed
- Statistics updated
- No memory leaks

---

#### Test 7.4: Forced Garbage Collection
```c
test_result_t test_forced_garbage_collection(void)
```
**Purpose**: Test `imx_force_garbage_collection()`

**Test Steps**:
1. Write and ACK data (creates freeable sectors)
2. Call forced GC
3. Verify sectors freed
4. Verify statistics updated
5. Test GC with pending data (should preserve)

**Success Criteria**:
- Freeable sectors freed
- Pending sectors preserved
- Return count accurate
- Performance acceptable

---

#### Test 7.5: Memory Pool Exhaustion and Recovery
```c
test_result_t test_pool_exhaustion_recovery(void)
```
**Purpose**: Test system behavior when pool full

**Test Steps**:
1. Fill entire memory pool
2. Attempt to write more data
3. On Linux: verify spooling triggers
4. On STM32: verify oldest data discarded
5. Verify system remains operational

**Success Criteria**:
- Exhaustion detected
- Platform-appropriate handling
- System recovers
- No crashes

---

### Category 8: Statistics and Diagnostics (4 tests)

#### Test 8.1: Memory Statistics Accuracy
```c
test_result_t test_memory_statistics_accuracy(void)
```
**Purpose**: Verify `imx_get_memory_stats()` correctness

**Test Steps**:
1. Get baseline statistics
2. Write data and check stats update
3. Free data and check stats update
4. Verify all fields accurate

**Success Criteria**:
- Total sectors correct
- Free sectors correct
- Used sectors = total - free
- Percentage calculations correct

---

#### Test 8.2: Sensor State Inspection
```c
test_result_t test_sensor_state_inspection(void)
```
**Purpose**: Test `imx_get_sensor_state()`

**Test Steps**:
1. Activate sensor and write data
2. Get sensor state
3. Verify all fields populated
4. Verify counts accurate
5. Test across different sensor states

**Success Criteria**:
- State structure populated
- Sample counts correct
- Pending counts correct
- Sector pointers valid

---

#### Test 8.3: Performance Metrics Tracking
```c
test_result_t test_performance_metrics(void)
```
**Purpose**: Verify performance tracking

**Test Steps**:
1. Perform operations
2. Get statistics
3. Verify timing metrics populated
4. Verify operation counts correct

**Success Criteria**:
- Metrics tracked
- Counts accurate
- Timing reasonable
- No overflow issues

---

#### Test 8.4: Space Efficiency Calculation
```c
test_result_t test_space_efficiency_calculation(void)
```
**Purpose**: Verify 75% space efficiency achieved

**Test Steps**:
1. Write TSD data
2. Calculate actual space usage
3. Verify 75% efficiency (24/32 bytes)
4. Test with EVT data

**Success Criteria**:
- TSD achieves 75% efficiency
- EVT efficiency measured
- Overhead acceptable
- Calculations correct

---

### Category 9: Time Management and UTC (3 tests)

#### Test 9.1: System Time Functions
```c
test_result_t test_system_time_functions(void)
```
**Purpose**: Test `imx_time_get_system_time()`

**Test Steps**:
1. Get system time
2. Verify time advances
3. Verify no backwards jumps
4. Test time rollover handling

**Success Criteria**:
- Time monotonically increasing
- Rollover handled correctly
- Performance acceptable

---

#### Test 9.2: UTC Availability (STM32)
```c
test_result_t test_utc_availability_stm32(void)
```
**Purpose**: Test `imx_set_utc_available()` blocking

**Test Steps**:
1. Mark UTC unavailable
2. Attempt TSD write
3. Verify write blocks
4. Mark UTC available
5. Verify write proceeds

**Success Criteria**:
- Writes block when UTC unavailable
- Writes proceed when available
- No deadlocks

**Note**: STM32 platform only

---

#### Test 9.3: Timestamp Synchronization
```c
test_result_t test_timestamp_synchronization(void)
```
**Purpose**: Verify timestamp consistency

**Test Steps**:
1. Write multiple sensors at same time
2. Verify timestamps close (±1ms)
3. Test GPS event timestamp sync
4. Verify TSD timestamp calculation correct

**Success Criteria**:
- Timestamps within tolerance
- GPS events perfectly synced
- TSD timestamps = first_utc + (index * sample_rate)

---

## Test Infrastructure Enhancements

### Enhancement 1: Test Fixtures and Setup/Teardown

**Current Issue**: Tests manually manage setup/cleanup

**Proposal**: Add test fixture support
```c
typedef struct {
    void (*setup)(void);
    void (*teardown)(void);
    test_result_t (*test_function)(void);
    const char* test_name;
} test_fixture_t;
```

**Benefits**:
- Consistent initialization
- Automatic cleanup
- Reduced code duplication

---

### Enhancement 2: Parameterized Testing

**Proposal**: Support running same test with different parameters
```c
typedef struct {
    test_data_group_t data_group;
    uint32_t iteration_count;
    const char* description;
} test_parameters_t;

test_result_t test_with_params(test_parameters_t* params);
```

**Use Cases**:
- Test all upload sources
- Test different data volumes
- Test various configurations

---

### Enhancement 3: Mock/Stub Framework

**Proposal**: Add mocking for external dependencies
```c
typedef struct {
    imx_result_t (*mock_disk_write)(const void* data, size_t size);
    imx_result_t (*mock_disk_read)(void* data, size_t size);
    void (*mock_power_event)(void);
} test_mocks_t;
```

**Benefits**:
- Test error paths
- Simulate disk full
- Simulate power loss
- Inject failures

---

### Enhancement 4: Code Coverage Reporting

**Proposal**: Integrate gcov/lcov for coverage reporting
```bash
# Compile with coverage
gcc -fprofile-arcs -ftest-coverage ...

# Run tests
./comprehensive_memory_test

# Generate report
gcov memory_*.c
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_report
```

**Metrics Tracked**:
- Line coverage
- Branch coverage
- Function coverage

---

### Enhancement 5: Performance Regression Testing

**Proposal**: Track performance metrics over time
```c
typedef struct {
    const char* operation_name;
    uint64_t baseline_time_us;
    uint64_t current_time_us;
    double percent_change;
    bool regression_detected;
} perf_metric_t;
```

**Use Cases**:
- Detect performance regressions
- Optimize bottlenecks
- Track improvements

---

### Enhancement 6: Continuous Integration Support

**Proposal**: Add CI-friendly test execution
```bash
# Run tests with machine-readable output
./comprehensive_memory_test --format=junit --output=test-results.xml

# Exit code: 0=pass, 1=fail
echo $?
```

**Benefits**:
- Automated testing
- Early bug detection
- Regression prevention

---

## Implementation Priority

### Phase 1: Critical Gaps (2 weeks)
**Focus**: Power management and disk operations

1. ✅ Power Management Tests (Tests 2.1-2.8) - **PRIORITY 1**
   - **Rationale**: Data loss prevention is critical
   - **Estimated**: 5 days
   - **Dependencies**: None

2. ✅ Disk Operations Tests (Tests 3.1-3.10) - **PRIORITY 1**
   - **Rationale**: Linux platform data persistence
   - **Estimated**: 5 days
   - **Dependencies**: None

3. ✅ Multi-Source Tests (Tests 4.1-4.5) - **PRIORITY 2**
   - **Rationale**: Multi-device support validation
   - **Estimated**: 3 days
   - **Dependencies**: Disk tests complete

**Deliverables**: 23 new tests, 75% coverage increase

---

### Phase 2: Important Gaps (1 week)
**Focus**: Sensor lifecycle and validation

4. ✅ GPS Event Tests (Tests 1.1-1.3) - **PRIORITY 2**
   - **Estimated**: 2 days
   - **Dependencies**: None

5. ✅ Sensor Lifecycle Tests (Tests 6.1-6.4) - **PRIORITY 3**
   - **Estimated**: 2 days
   - **Dependencies**: None

6. ✅ Chain Management Tests (Tests 7.1-7.5) - **PRIORITY 3**
   - **Estimated**: 2 days
   - **Dependencies**: None

**Deliverables**: 12 new tests, 90% coverage

---

### Phase 3: Nice-to-Have (1 week)
**Focus**: Peek operations and diagnostics

7. ✅ Peek Operation Tests (Tests 5.1-5.4) - **PRIORITY 4**
   - **Estimated**: 2 days
   - **Dependencies**: None

8. ✅ Statistics Tests (Tests 8.1-8.4) - **PRIORITY 4**
   - **Estimated**: 2 days
   - **Dependencies**: None

9. ✅ Time Management Tests (Tests 9.1-9.3) - **PRIORITY 4**
   - **Estimated**: 1 day
   - **Dependencies**: None

**Deliverables**: 11 new tests, 98% coverage

---

### Phase 4: Infrastructure (Ongoing)
**Focus**: Test framework improvements

10. ✅ Test Fixtures - **PRIORITY 2**
    - **Estimated**: 2 days
    - **Benefit**: Reduces code duplication

11. ✅ Mock Framework - **PRIORITY 3**
    - **Estimated**: 3 days
    - **Benefit**: Error path testing

12. ✅ Coverage Reporting - **PRIORITY 3**
    - **Estimated**: 1 day
    - **Benefit**: Metrics visibility

**Deliverables**: Enhanced test infrastructure

---

## Success Metrics

### Coverage Metrics
- **API Function Coverage**: Target 100% (currently ~60%)
- **Line Coverage**: Target 90%+ (measure with gcov)
- **Branch Coverage**: Target 85%+ (error paths included)

### Quality Metrics
- **Test Pass Rate**: 100% (0 failures)
- **False Positive Rate**: 0% (no flaky tests)
- **Test Execution Time**: < 5 minutes for full suite

### Defect Metrics
- **Bugs Found**: Track pre-release bugs caught by new tests
- **Regression Prevention**: Track regressions caught by CI
- **Production Bugs**: Target 0 memory-related production issues

### Performance Metrics
- **Test Maintenance**: < 10% time spent fixing tests after changes
- **CI Build Time**: < 10 minutes including tests
- **Developer Productivity**: Bugs caught in minutes, not days

---

## Conclusion

This comprehensive test expansion plan provides:

1. **45+ new test functions** covering all MM2 API gaps
2. **Detailed specifications** for each test
3. **Infrastructure improvements** for maintainability
4. **Phased implementation** with clear priorities
5. **Success metrics** for measuring effectiveness

**Estimated Effort**: 4-5 weeks full-time development

**Expected Outcome**:
- 100% MM2 API coverage
- 90%+ code coverage
- Zero known critical bugs
- Production-ready memory manager
- Comprehensive regression prevention

---

*Document Version: 1.0*
*Created: 2025-10-16*
*Author: Claude Code (with human review)*
