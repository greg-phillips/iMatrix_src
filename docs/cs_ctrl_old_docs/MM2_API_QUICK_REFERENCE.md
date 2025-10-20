# MM2 API Quick Reference Card

## Initialization & Status

```c
// Initialize (call once at startup)
imx_result_t imx_memory_manager_init(uint32_t pool_size);  // Use 0 for default

// Check if ready (STM32: waits for UTC, Linux: always ready)
int imx_memory_manager_ready(void);  // Returns 1 if ready

// Shutdown single sensor (call for each active sensor on power-down)
imx_result_t imx_memory_manager_shutdown(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    uint32_t timeout_ms);  // Max 60000 ms
```

## Sensor Management

```c
// Configure sensor (set sample_rate: 0=EVT, >0=TSD)
imx_result_t imx_configure_sensor(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,  // Set csb->id, csb->sample_rate
    control_sensor_data_t* csd);

// Activate sensor for data collection
imx_result_t imx_activate_sensor(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

// Deactivate sensor (flushes data)
imx_result_t imx_deactivate_sensor(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);
```

## Write Operations

```c
// Write TSD (Time Series Data) - Regular periodic samples
imx_result_t imx_write_tsd(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value);
// Format: [first_UTC:8][value_0:4][value_1:4]...[value_5:4] = 75% efficiency

// Write EVT (Event Data) - Irregular events with individual timestamps
imx_result_t imx_write_evt(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value,
    imx_utc_time_ms_t utc_time_ms);
// Format: [value_0:4][UTC_0:8][value_1:4][UTC_1:8][padding:8]
```

## Read Operations

```c
// Get count of new (non-pending) samples
uint32_t imx_get_new_sample_count(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

// Read bulk samples (RECOMMENDED - most efficient)
imx_result_t imx_read_bulk_samples(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    tsd_evt_value_t* array,      // Pre-allocated array
    uint32_t array_size,         // Size of array
    uint32_t requested_count,    // How many to read
    uint16_t* filled_count);     // [OUT] Actual count read

// Read single record (legacy compatibility)
imx_result_t imx_read_next_tsd_evt(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    tsd_evt_data_t* data_out);
```

## Upload Management

```c
// Revert pending data (NACK - upload failed, retry later)
imx_result_t imx_revert_all_pending(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

// Erase pending data (ACK - upload successful)
imx_result_t imx_erase_all_pending(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    uint32_t record_count);
```

## Diagnostics

```c
// Get memory statistics
imx_result_t imx_get_memory_stats(mm2_stats_t* stats_out);

// Get sensor state
imx_result_t imx_get_sensor_state(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    mm2_sensor_state_t* state_out);

// Validate chain integrity
imx_result_t imx_validate_sector_chains(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);

// Force garbage collection (dev/test only)
uint32_t imx_force_garbage_collection(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd);
```

## Processing & Power

```c
// Main processing loop (call periodically, completes in <5ms)
imx_result_t process_memory_manager(imx_time_t current_time);

// Power event notification
void imx_power_event_detected(void);  // Call on power-down interrupt

// Power abort recovery
imx_result_t handle_power_abort_recovery(void);

// Get UTC time
imx_utc_time_ms_t mm2_get_utc_time_ms(void);

// Set UTC available (STM32 only)
imx_result_t imx_set_utc_available(int utc_available);
```

## Upload Source Enum

```c
typedef enum {
    IMX_UPLOAD_TELEMETRY = 0,    // Normal telemetry data
    IMX_UPLOAD_DIAGNOSTICS,      // Diagnostic/debug data
    IMX_UPLOAD_GATEWAY,          // Gateway-specific data
    IMX_UPLOAD_HOSTED_DEVICE,    // Hosted device data
    IMX_UPLOAD_BLE_DEVICE,       // BLE device data
    IMX_UPLOAD_NO_SOURCES        // Count (not a valid source)
} imatrix_upload_source_t;
```

## Return Codes

```c
IMX_SUCCESS            //  0 - Operation successful
IMX_ERROR              // -1 - Generic error
IMX_OUT_OF_MEMORY      // -2 - Pool exhausted (spool to disk or clear pending)
IMX_INVALID_PARAMETER  // -3 - Bad parameters
IMX_INVALID_ENTRY      // -4 - Bad sensor ID or inactive sensor
IMX_TIMEOUT            // -5 - Timed out (STM32: waiting for UTC)
IMX_NO_DATA            // -6 - No data available (not an error)
IMX_INIT_ERROR         // -7 - Initialization failed
```

## Data Structures

```c
// Value/timestamp pair (bulk read output)
typedef struct {
    uint32_t value;
    uint64_t timestamp;  // UTC milliseconds
} tsd_evt_value_t;

// Legacy format (single read output)
typedef struct {
    uint32_t value;
    uint64_t utc_time_ms;
} tsd_evt_data_t;

// Memory statistics
typedef struct {
    uint32_t total_sectors;
    uint32_t free_sectors;
    uint32_t active_sensors;
    uint64_t total_allocations;
    uint64_t allocation_failures;
    uint64_t chain_operations;
    uint32_t space_efficiency_percent;  // Should be 75% for TSD
} mm2_stats_t;

// Sensor state
typedef struct {
    uint32_t sensor_id;
    unsigned int active : 1;
    SECTOR_ID_TYPE ram_start_sector;
    SECTOR_ID_TYPE ram_end_sector;
    uint16_t ram_read_offset;
    uint16_t ram_write_offset;
    uint64_t total_records;
    uint64_t last_sample_time;
    uint32_t pending_counts[UPLOAD_SOURCE_MAX];
} mm2_sensor_state_t;
```

## Typical Usage Pattern

```c
// 1. Initialization (once at startup)
imx_memory_manager_init(0);

// 2. Configure sensor
sensor_config[0].id = 0;
sensor_config[0].sample_rate = 60000;  // 60 sec for TSD, 0 for EVT
imx_configure_sensor(IMX_UPLOAD_TELEMETRY, &sensor_config[0], &sensor_data[0]);
imx_activate_sensor(IMX_UPLOAD_TELEMETRY, &sensor_config[0], &sensor_data[0]);

// 3. Write data
imx_data_32_t value;
value.float_32bit = 23.5f;
imx_write_tsd(IMX_UPLOAD_TELEMETRY, &sensor_config[0], &sensor_data[0], value);

// 4. Upload loop
uint32_t count = imx_get_new_sample_count(IMX_UPLOAD_TELEMETRY,
                                          &sensor_config[0],
                                          &sensor_data[0]);
if (count > 0) {
    tsd_evt_value_t* buffer = malloc(count * sizeof(tsd_evt_value_t));
    uint16_t filled;

    imx_read_bulk_samples(IMX_UPLOAD_TELEMETRY, &sensor_config[0],
                         &sensor_data[0], buffer, count, count, &filled);

    if (upload_to_cloud(buffer, filled) == SUCCESS) {
        imx_erase_all_pending(IMX_UPLOAD_TELEMETRY, &sensor_config[0],
                             &sensor_data[0], filled);
    } else {
        imx_revert_all_pending(IMX_UPLOAD_TELEMETRY, &sensor_config[0],
                              &sensor_data[0]);
    }

    free(buffer);
}

// 5. Shutdown
imx_deactivate_sensor(IMX_UPLOAD_TELEMETRY, &sensor_config[0], &sensor_data[0]);
```

## Platform Differences

| Feature | Linux | STM32 |
|---------|-------|-------|
| Pool Size | 64KB | 4KB |
| Sector ID | 32-bit | 16-bit |
| Thread Safety | pthread_mutex | Single-threaded |
| Disk Spooling | Yes (automatic) | No |
| UTC Requirement | Optional | Required |
| Write Blocking | Non-blocking | Blocks until UTC |
| Memory Full | Spools to disk | Discards oldest |

## Memory Efficiency

**TSD Format** (75% efficiency):
- Sector: 32 bytes
- Header: 8 bytes (first_UTC)
- Data: 24 bytes (6 × 4-byte values)
- Efficiency: 24/32 = 75%

**EVT Format** (75% efficiency with padding):
- Sector: 32 bytes
- Pairs: 24 bytes (2 × 12-byte pairs)
- Padding: 8 bytes
- Efficiency: 24/32 = 75%

## Common Pitfalls

❌ **DON'T**:
```c
// Forget to check return values
imx_write_tsd(source, &csb, &csd, value);  // BAD - no error check

// Mix TSD and EVT for same sensor
imx_write_tsd(source, &csb, &csd, value1);  // sample_rate = 60000
imx_write_evt(source, &csb, &csd, value2, time);  // WRONG!

// Read without checking count first
imx_read_bulk_samples(...);  // May return IMX_NO_DATA

// Forget to erase after successful upload
upload_data();  // Success but forgot to call imx_erase_all_pending()
```

✅ **DO**:
```c
// Always check return values
if (imx_write_tsd(source, &csb, &csd, value) != IMX_SUCCESS) {
    // Handle error
}

// Use consistent mode for each sensor
if (csb.sample_rate > 0) {
    imx_write_tsd(source, &csb, &csd, value);  // TSD mode
} else {
    imx_write_evt(source, &csb, &csd, value, time);  // EVT mode
}

// Check count before reading
uint32_t count = imx_get_new_sample_count(source, &csb, &csd);
if (count > 0) {
    // Safe to read
}

// Always ACK or NACK
if (upload_success) {
    imx_erase_all_pending(source, &csb, &csd, count);
} else {
    imx_revert_all_pending(source, &csb, &csd);
}
```

## Performance Tips

- ✅ Use `imx_read_bulk_samples()` instead of multiple `imx_read_next_tsd_evt()` calls
- ✅ Upload data frequently to keep pending counts low
- ✅ Monitor memory usage and trigger spooling at 80% (Linux)
- ✅ Use appropriate sample_rate (avoid <100ms)
- ✅ Call `process_memory_manager()` regularly (<5ms execution)
- ❌ Don't write during shutdown (after `imx_power_event_detected()`)
- ❌ Don't hold locks for extended periods
- ❌ Don't skip chain validation in debug builds

## Debug Helpers

```c
// Print memory status
mm2_stats_t stats;
imx_get_memory_stats(&stats);
printf("Memory: %u/%u sectors free (%.1f%% used)\n",
       stats.free_sectors, stats.total_sectors,
       ((stats.total_sectors - stats.free_sectors) * 100.0) / stats.total_sectors);

// Validate chain
if (imx_validate_sector_chains(source, &csb, &csd) != IMX_SUCCESS) {
    printf("ERROR: Chain corrupted!\n");
}

// Check sensor state
mm2_sensor_state_t state;
imx_get_sensor_state(source, &csb, &csd, &state);
printf("Sensor %u: %llu records, %u pending\n",
       state.sensor_id, state.total_records,
       state.pending_counts[source]);
```

## Links

- **Complete API Reference**: MM2_TECHNICAL_DOCUMENTATION.md
- **Usage Examples**: MM2_IMPLEMENTATION_GUIDE.md
- **Troubleshooting**: MM2_TROUBLESHOOTING_GUIDE.md

---

**Version**: MM2 v2.8
**Last Updated**: 2025-01-10
**Platform Support**: Linux (Ubuntu/Debian), STM32F4/F7
