# iMatrix Memory Manager v2.8 - Implementation Guide

## Table of Contents
1. [Quick Start Guide](#quick-start-guide)
2. [Common Usage Patterns](#common-usage-patterns)
3. [Memory Efficiency Analysis](#memory-efficiency-analysis)
4. [Code Walkthroughs](#code-walkthroughs)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Testing Strategies](#testing-strategies)
7. [Integration Examples](#integration-examples)
8. [Best Practices](#best-practices)

---

## 1. Quick Start Guide

### 1.1 Basic Initialization

```c
#include "mm2_api.h"

// Initialize memory manager at application startup
imx_result_t result = imx_memory_manager_init(0);  // Use default pool size
if (result != IMX_SUCCESS) {
    printf("ERROR: MM2 initialization failed: %d\n", result);
    return -1;
}

// Check if ready (STM32 waits for UTC)
if (!imx_memory_manager_ready()) {
    printf("WARNING: MM2 waiting for UTC time\n");
}
```

### 1.2 Simple Sensor Setup

```c
// Declare sensor structures (typically in application's sensor array)
imx_control_sensor_block_t sensor_config[MAX_SENSORS];
control_sensor_data_t sensor_data[MAX_SENSORS];

// Configure a temperature sensor (index 0)
uint16_t sensor_idx = 0;
sensor_config[sensor_idx].id = sensor_idx;
sensor_config[sensor_idx].sample_rate = 60000;  // 60 seconds in ms (TSD mode)

// Configure sensor
result = imx_configure_sensor(
    IMX_UPLOAD_TELEMETRY,           // Upload to telemetry endpoint
    &sensor_config[sensor_idx],
    &sensor_data[sensor_idx]
);

// Activate sensor
result = imx_activate_sensor(
    IMX_UPLOAD_TELEMETRY,
    &sensor_config[sensor_idx],
    &sensor_data[sensor_idx]
);
```

### 1.3 Writing Data

```c
// Write temperature reading (TSD format)
imx_data_32_t temperature;
temperature.float_32bit = 23.5f;  // 23.5°C

result = imx_write_tsd(
    IMX_UPLOAD_TELEMETRY,
    &sensor_config[sensor_idx],
    &sensor_data[sensor_idx],
    temperature
);

if (result != IMX_SUCCESS) {
    printf("WARNING: Failed to write TSD: %d\n", result);
}
```

### 1.4 Reading and Uploading Data

```c
// Check how many samples are available
uint32_t available = imx_get_new_sample_count(
    IMX_UPLOAD_TELEMETRY,
    &sensor_config[sensor_idx],
    &sensor_data[sensor_idx]
);

if (available > 0) {
    // Allocate array for bulk read
    tsd_evt_value_t* samples = malloc(available * sizeof(tsd_evt_value_t));
    uint16_t filled_count = 0;

    // Read samples
    result = imx_read_bulk_samples(
        IMX_UPLOAD_TELEMETRY,
        &sensor_config[sensor_idx],
        &sensor_data[sensor_idx],
        samples,
        available,
        available,
        &filled_count
    );

    if (result == IMX_SUCCESS && filled_count > 0) {
        // Upload to cloud
        if (upload_to_cloud(samples, filled_count) == SUCCESS) {
            // Acknowledge successful upload
            imx_erase_all_pending(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[sensor_idx],
                &sensor_data[sensor_idx],
                filled_count
            );
        } else {
            // Upload failed - revert for retry
            imx_revert_all_pending(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[sensor_idx],
                &sensor_data[sensor_idx]
            );
        }
    }

    free(samples);
}
```

---

## 2. Common Usage Patterns

### 2.1 TSD (Time Series Data) Pattern

**Use Case**: Regular periodic samples (temperature, pressure, voltage)

```c
// Setup
sensor_config[idx].sample_rate = 10000;  // 10 seconds
imx_configure_sensor(IMX_UPLOAD_TELEMETRY, &sensor_config[idx], &sensor_data[idx]);

// Periodic sampling (called every 10 seconds)
void on_timer_10sec(void) {
    imx_data_32_t value;
    value.uint_32bit = read_sensor_value();

    imx_write_tsd(
        IMX_UPLOAD_TELEMETRY,
        &sensor_config[idx],
        &sensor_data[idx],
        value
    );
}

// Memory efficiency: 6 values per 32-byte sector
// Overhead per value: 8 bytes (first_UTC) / 6 = 1.33 bytes
// Data per value: 4 bytes
// Efficiency: 4 / (4 + 1.33) = 75%
```

### 2.2 EVT (Event Data) Pattern

**Use Case**: Irregular events (alarms, state changes, button presses)

```c
// Setup (sample_rate = 0 for EVT mode)
sensor_config[idx].sample_rate = 0;  // EVT mode
imx_configure_sensor(IMX_UPLOAD_DIAGNOSTICS, &sensor_config[idx], &sensor_data[idx]);

// Event-driven writing
void on_alarm_triggered(uint32_t alarm_code) {
    imx_data_32_t value;
    value.uint_32bit = alarm_code;

    imx_utc_time_ms_t event_time = mm2_get_utc_time_ms();

    imx_write_evt(
        IMX_UPLOAD_DIAGNOSTICS,
        &sensor_config[idx],
        &sensor_data[idx],
        value,
        event_time
    );
}

// Memory efficiency: 2 pairs per 32-byte sector
// Overhead per value: 8 bytes padding / 2 = 4 bytes
// Data per value: 4 + 8 = 12 bytes
// Efficiency: 12 / (12 + 4) = 75%
```

### 2.3 Multi-Source Upload Pattern

**Use Case**: Same sensor data uploaded to multiple destinations

```c
// Write to primary destination
imx_write_tsd(IMX_UPLOAD_TELEMETRY, &csb, &csd, value);

// For critical data, also log to diagnostics
if (is_critical_reading(value)) {
    imx_write_evt(
        IMX_UPLOAD_DIAGNOSTICS,
        &csb_diagnostic,
        &csd_diagnostic,
        value,
        mm2_get_utc_time_ms()
    );
}
```

### 2.4 Batched Upload Pattern

**Use Case**: Efficient network utilization with bulk transfers

```c
#define UPLOAD_BATCH_SIZE 100

void periodic_upload_task(void) {
    for (int sensor_idx = 0; sensor_idx < active_sensor_count; sensor_idx++) {
        uint32_t available = imx_get_new_sample_count(
            IMX_UPLOAD_TELEMETRY,
            &sensor_config[sensor_idx],
            &sensor_data[sensor_idx]
        );

        while (available > 0) {
            uint32_t batch_size = (available > UPLOAD_BATCH_SIZE) ?
                                  UPLOAD_BATCH_SIZE : available;

            tsd_evt_value_t batch[UPLOAD_BATCH_SIZE];
            uint16_t filled = 0;

            imx_read_bulk_samples(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[sensor_idx],
                &sensor_data[sensor_idx],
                batch,
                UPLOAD_BATCH_SIZE,
                batch_size,
                &filled
            );

            if (filled > 0) {
                if (upload_batch(sensor_idx, batch, filled) == SUCCESS) {
                    imx_erase_all_pending(
                        IMX_UPLOAD_TELEMETRY,
                        &sensor_config[sensor_idx],
                        &sensor_data[sensor_idx],
                        filled
                    );
                    available -= filled;
                } else {
                    imx_revert_all_pending(
                        IMX_UPLOAD_TELEMETRY,
                        &sensor_config[sensor_idx],
                        &sensor_data[sensor_idx]
                    );
                    break;  // Retry later
                }
            }
        }
    }
}
```

### 2.5 Graceful Shutdown Pattern

```c
void application_shutdown_handler(void) {
    printf("Power-down detected - initiating graceful shutdown\n");

    // Notify MM2 of power event
    imx_power_event_detected();

    // Flush each active sensor
    uint64_t deadline = mm2_get_utc_time_ms() + 60000;  // 60 second window

    for (int i = 0; i < MAX_SENSORS; i++) {
        if (sensor_data[i].active) {
            uint32_t remaining_time = deadline - mm2_get_utc_time_ms();

            imx_result_t result = imx_memory_manager_shutdown(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[i],
                &sensor_data[i],
                remaining_time
            );

            if (result != IMX_SUCCESS) {
                printf("WARNING: Sensor %d flush failed: %d\n", i, result);
            }
        }
    }

    printf("Shutdown complete - safe to power off\n");
}
```

---

## 3. Memory Efficiency Analysis

### 3.1 Space Efficiency Proof for TSD

**Traditional Approach (Embedded Pointers)**:
```
Sector Layout:
[next_ptr:4][first_utc:8][value_0:4][value_1:4][value_2:4][value_3:4][value_4:4]
Total: 32 bytes
Data: 20 bytes (5 values × 4 bytes)
Metadata: 12 bytes (next_ptr + first_utc)
Efficiency: 20/32 = 62.5%
```

**MM2 Approach (Separated Chain Table)**:
```
Sector Layout (data only):
[first_utc:8][value_0:4][value_1:4][value_2:4][value_3:4][value_4:4][value_5:4]
Total: 32 bytes
Data: 24 bytes (6 values × 4 bytes)
Metadata: 8 bytes (first_utc only)
Efficiency: 24/32 = 75%

Chain Table (separate):
Per-sector overhead: 32 bytes (on 64-bit systems)
But this is amortized across ALL sectors, not per-sensor
```

**Efficiency Gain**:
- Traditional: 62.5% (5 values per sector)
- MM2: 75% (6 values per sector)
- Improvement: 20% more data capacity
- Additional benefit: Chain table shared across all sensors

### 3.2 Memory Overhead Calculation

**For 64KB pool on Linux**:
```
Total pool: 64KB = 65,536 bytes
Sector size: 32 bytes
Number of sectors: 2,048 sectors

Data sectors: 2,048 × 32 = 65,536 bytes
Chain table: 2,048 × 32 = 65,536 bytes (separate allocation)
Free list: 2,048 × 4 = 8,192 bytes

Total memory usage: 65,536 + 65,536 + 8,192 = 139,264 bytes
Overhead: 73,728 / 65,536 = 112% overhead

BUT: This overhead enables:
- 75% space efficiency within sectors
- Thread-safe operations
- Efficient allocation/deallocation
- Chain validation
- Per-sensor metadata
```

### 3.3 Actual Space Savings Example

**Scenario**: 100 sensors, each producing 1 sample/minute for 1 hour

**Traditional Approach**:
```
Samples per sensor: 60
Total samples: 6,000
Samples per sector: 5
Sectors needed: 6,000 / 5 = 1,200 sectors
Memory used: 1,200 × 32 = 38,400 bytes
```

**MM2 Approach**:
```
Samples per sensor: 60
Total samples: 6,000
Samples per sector: 6
Sectors needed: 6,000 / 6 = 1,000 sectors
Memory used: 1,000 × 32 = 32,000 bytes
```

**Savings**: 38,400 - 32,000 = 6,400 bytes (16.7% reduction)

---

## 4. Code Walkthroughs

### 4.1 Write Operation Deep Dive

```c
imx_result_t imx_write_tsd(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value)
{
    // Step 1: Validate parameters
    if (upload_source >= IMX_UPLOAD_NO_SOURCES) return IMX_INVALID_PARAMETER;
    if (!csb || !csd) return IMX_INVALID_PARAMETER;
    if (csb->id >= MAX_SENSORS) return IMX_INVALID_ENTRY;

    // Step 2: Check shutdown state
    if (g_power_state.shutdown_requested) return IMX_INVALID_PARAMETER;

    // Step 3: Platform-specific UTC check (STM32 only)
    #ifndef LINUX_PLATFORM
    if (!g_time_rollover.utc_established) return IMX_TIMEOUT;
    #endif

    // Step 4: Thread safety (Linux only)
    #ifdef LINUX_PLATFORM
    pthread_mutex_lock(&csd->mmcb.sensor_lock);
    #endif

    // Step 5: Calculate current sector usage
    uint32_t values_in_sector = 0;
    if (csd->mmcb.ram_end_sector_id != NULL_SECTOR_ID) {
        // MM2 format: subtract first_UTC (8 bytes) and divide by value size (4 bytes)
        values_in_sector = (csd->mmcb.ram_write_sector_offset - TSD_FIRST_UTC_SIZE)
                          / sizeof(uint32_t);
    }

    // Step 6: Allocate new sector if current is full or doesn't exist
    if (csd->mmcb.ram_end_sector_id == NULL_SECTOR_ID ||
        values_in_sector >= MAX_TSD_VALUES_PER_SECTOR)  // 6 values max
    {
        SECTOR_ID_TYPE new_sector_id = allocate_sector_for_sensor(
            csb->id,
            SECTOR_TYPE_TSD
        );

        if (new_sector_id == NULL_SECTOR_ID) {
            #ifdef LINUX_PLATFORM
            pthread_mutex_unlock(&csd->mmcb.sensor_lock);
            #endif
            return IMX_OUT_OF_MEMORY;
        }

        // Link new sector to chain
        if (csd->mmcb.ram_end_sector_id != NULL_SECTOR_ID) {
            set_next_sector_in_chain(csd->mmcb.ram_end_sector_id, new_sector_id);
        }

        // Update sensor pointers
        if (csd->mmcb.ram_start_sector_id == NULL_SECTOR_ID) {
            csd->mmcb.ram_start_sector_id = new_sector_id;
            csd->mmcb.ram_read_sector_offset = TSD_FIRST_UTC_SIZE;
        }
        csd->mmcb.ram_end_sector_id = new_sector_id;
        csd->mmcb.ram_write_sector_offset = TSD_FIRST_UTC_SIZE;

        // Initialize sector with first_UTC
        memory_sector_t* sector = &g_memory_pool.sectors[new_sector_id];
        uint64_t current_utc = mm2_get_utc_time_ms();
        set_tsd_first_utc(sector->data, current_utc);

        values_in_sector = 0;
    }

    // Step 7: Write value to current sector
    memory_sector_t* sector = &g_memory_pool.sectors[csd->mmcb.ram_end_sector_id];
    uint32_t* values_array = get_tsd_values_array(sector->data);
    values_array[values_in_sector] = value.value;

    // Step 8: Update offsets and statistics
    csd->mmcb.ram_write_sector_offset += sizeof(uint32_t);
    csd->mmcb.total_records++;
    csd->mmcb.last_sample_time = mm2_get_utc_time_ms();

    // Step 9: Unlock and return
    #ifdef LINUX_PLATFORM
    pthread_mutex_unlock(&csd->mmcb.sensor_lock);
    #endif

    return IMX_SUCCESS;
}
```

**Key Observations**:
1. Lock held for entire operation (could be optimized with lock-free techniques)
2. Sector allocation triggers chain updates
3. First write to new sector initializes UTC timestamp
4. Offsets tracked in bytes for flexibility
5. Statistics updated atomically with data write

### 4.2 Read Operation with Timestamp Calculation

```c
static imx_result_t read_tsd_from_sector(
    const memory_sector_t* sector,
    const sector_chain_entry_t* entry,
    imx_control_sensor_block_t* csb,
    uint16_t offset,
    tsd_evt_data_t* data_out)
{
    // Validate offset is in data range
    if (offset < TSD_FIRST_UTC_SIZE ||
        offset >= TSD_FIRST_UTC_SIZE + (MAX_TSD_VALUES_PER_SECTOR * sizeof(uint32_t))) {
        return IMX_NO_DATA;
    }

    // Calculate which value index we're reading
    uint32_t value_index = (offset - TSD_FIRST_UTC_SIZE) / sizeof(uint32_t);

    // Get the first UTC timestamp from sector
    uint64_t first_utc = get_tsd_first_utc(sector->data);

    // Get values array pointer
    const uint32_t* values = (const uint32_t*)(sector->data + TSD_FIRST_UTC_SIZE);

    // CRITICAL: Calculate individual timestamp
    // Formula: timestamp = first_utc + (index * sample_rate_ms)
    // Example: If first_utc = 1000000, sample_rate = 60000, index = 2
    //          timestamp = 1000000 + (2 * 60000) = 1120000
    uint64_t individual_timestamp = first_utc;
    if (csb->sample_rate > 0) {
        individual_timestamp = first_utc + (value_index * csb->sample_rate);
    }

    // Fill output structure
    data_out->value = values[value_index];
    data_out->utc_time_ms = individual_timestamp;

    return IMX_SUCCESS;
}
```

**Key Observations**:
1. Timestamp reconstruction from stored first_UTC
2. No need to store individual timestamps (space savings!)
3. Sample rate from configuration block used for calculation
4. Each value gets accurate timestamp based on its position

### 4.3 Chain Traversal Pattern

```c
// Example: Count total records in a sensor's chain
uint32_t count_records_in_chain(control_sensor_data_t* csd) {
    uint32_t total_records = 0;
    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;

    while (current != NULL_SECTOR_ID) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current);

        if (entry && entry->in_use) {
            if (entry->sector_type == SECTOR_TYPE_TSD) {
                // For TSD: count values based on write offset
                if (current == csd->mmcb.ram_end_sector_id) {
                    // Last sector: use actual write position
                    uint32_t values = (csd->mmcb.ram_write_sector_offset - TSD_FIRST_UTC_SIZE)
                                     / sizeof(uint32_t);
                    total_records += values;
                } else {
                    // Full sector: maximum values
                    total_records += MAX_TSD_VALUES_PER_SECTOR;
                }
            } else if (entry->sector_type == SECTOR_TYPE_EVT) {
                // For EVT: count pairs
                if (current == csd->mmcb.ram_end_sector_id) {
                    uint32_t pairs = csd->mmcb.ram_write_sector_offset
                                   / sizeof(evt_data_pair_t);
                    total_records += pairs;
                } else {
                    total_records += MAX_EVT_PAIRS_PER_SECTOR;
                }
            }
        }

        // Move to next sector in chain
        current = get_next_sector_in_chain(current);
    }

    return total_records;
}
```

---

## 5. Error Handling Patterns

### 5.1 Comprehensive Error Checking

```c
imx_result_t safe_write_tsd_with_retry(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd,
    imx_data_32_t value)
{
    // Pre-flight checks
    if (!csb || !csd) {
        printf("ERROR: NULL pointer passed to write_tsd\n");
        return IMX_INVALID_PARAMETER;
    }

    // Check sensor is active
    if (!csd->active) {
        printf("WARNING: Attempting to write to inactive sensor %d\n", csb->id);
        return IMX_INVALID_ENTRY;
    }

    // Check memory manager is ready (STM32)
    if (!imx_memory_manager_ready()) {
        printf("WARNING: MM2 not ready - waiting for UTC\n");
        return IMX_TIMEOUT;
    }

    // Attempt write with retry
    int retry_count = 0;
    const int MAX_RETRIES = 3;

    while (retry_count < MAX_RETRIES) {
        imx_result_t result = imx_write_tsd(upload_source, csb, csd, value);

        switch (result) {
            case IMX_SUCCESS:
                return IMX_SUCCESS;

            case IMX_OUT_OF_MEMORY:
                // Memory full - try spooling to disk (Linux only)
                #ifdef LINUX_PLATFORM
                printf("WARNING: Memory full, attempting disk spool\n");
                process_normal_disk_spooling(csd, upload_source);
                retry_count++;
                break;
                #else
                // STM32: Cannot spool to disk
                printf("ERROR: RAM exhausted on STM32\n");
                return IMX_OUT_OF_MEMORY;
                #endif

            case IMX_TIMEOUT:
                // UTC not available yet (STM32)
                printf("WARNING: Waiting for UTC time\n");
                usleep(100000);  // Wait 100ms
                retry_count++;
                break;

            case IMX_INVALID_PARAMETER:
                // Bad parameters - cannot retry
                printf("ERROR: Invalid parameters\n");
                return result;

            default:
                printf("ERROR: Unexpected error: %d\n", result);
                return result;
        }
    }

    printf("ERROR: Write failed after %d retries\n", MAX_RETRIES);
    return IMX_ERROR;
}
```

### 5.2 Upload Error Recovery

```c
typedef enum {
    UPLOAD_SUCCESS,
    UPLOAD_TIMEOUT,
    UPLOAD_NETWORK_ERROR,
    UPLOAD_SERVER_ERROR
} upload_result_t;

imx_result_t upload_with_error_recovery(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd)
{
    uint32_t available = imx_get_new_sample_count(upload_source, csb, csd);
    if (available == 0) {
        return IMX_SUCCESS;  // Nothing to upload
    }

    // Allocate buffer
    tsd_evt_value_t* buffer = malloc(available * sizeof(tsd_evt_value_t));
    if (!buffer) {
        printf("ERROR: Memory allocation failed for upload buffer\n");
        return IMX_OUT_OF_MEMORY;
    }

    // Read data (marks as pending)
    uint16_t filled = 0;
    imx_result_t result = imx_read_bulk_samples(
        upload_source, csb, csd,
        buffer, available, available, &filled
    );

    if (result != IMX_SUCCESS || filled == 0) {
        free(buffer);
        return result;
    }

    // Attempt upload
    upload_result_t upload_result = upload_to_server(
        csb->id,
        upload_source,
        buffer,
        filled
    );

    switch (upload_result) {
        case UPLOAD_SUCCESS:
            // Acknowledge successful upload
            printf("Upload successful: %d records\n", filled);
            imx_erase_all_pending(upload_source, csb, csd, filled);
            result = IMX_SUCCESS;
            break;

        case UPLOAD_TIMEOUT:
        case UPLOAD_NETWORK_ERROR:
            // Temporary error - revert for retry
            printf("Upload failed (transient): reverting data\n");
            imx_revert_all_pending(upload_source, csb, csd);
            result = IMX_ERROR;
            break;

        case UPLOAD_SERVER_ERROR:
            // Permanent error - data may be corrupted
            printf("WARNING: Server rejected data - discarding\n");
            imx_erase_all_pending(upload_source, csb, csd, filled);
            result = IMX_ERROR;
            break;
    }

    free(buffer);
    return result;
}
```

### 5.3 Memory Leak Prevention

```c
// RAII-style cleanup helper
typedef struct {
    tsd_evt_value_t* buffer;
    uint32_t size;
} buffer_guard_t;

static void cleanup_buffer(buffer_guard_t* guard) {
    if (guard && guard->buffer) {
        free(guard->buffer);
        guard->buffer = NULL;
    }
}

// Usage with automatic cleanup
imx_result_t safe_bulk_read_example(
    imatrix_upload_source_t upload_source,
    imx_control_sensor_block_t* csb,
    control_sensor_data_t* csd)
{
    buffer_guard_t guard = { .buffer = NULL, .size = 0 };
    imx_result_t result = IMX_ERROR;

    // Allocate buffer
    uint32_t count = imx_get_new_sample_count(upload_source, csb, csd);
    if (count == 0) {
        return IMX_NO_DATA;
    }

    guard.buffer = malloc(count * sizeof(tsd_evt_value_t));
    guard.size = count;

    if (!guard.buffer) {
        result = IMX_OUT_OF_MEMORY;
        goto cleanup;
    }

    // Read data
    uint16_t filled = 0;
    result = imx_read_bulk_samples(
        upload_source, csb, csd,
        guard.buffer, guard.size, count, &filled
    );

    if (result != IMX_SUCCESS) {
        goto cleanup;
    }

    // Process data...

cleanup:
    cleanup_buffer(&guard);
    return result;
}
```

---

## 6. Testing Strategies

### 6.1 Unit Test Examples

```c
// Test: Verify 75% space efficiency
void test_tsd_space_efficiency(void) {
    // Setup
    imx_memory_manager_init(4096);  // Small pool for testing

    imx_control_sensor_block_t csb = {
        .id = 0,
        .sample_rate = 1000  // TSD mode
    };
    control_sensor_data_t csd = {0};

    imx_configure_sensor(IMX_UPLOAD_TELEMETRY, &csb, &csd);
    imx_activate_sensor(IMX_UPLOAD_TELEMETRY, &csb, &csd);

    // Write 6 values (should fit in one sector)
    for (int i = 0; i < 6; i++) {
        imx_data_32_t value = { .uint_32bit = i };
        imx_result_t result = imx_write_tsd(IMX_UPLOAD_TELEMETRY, &csb, &csd, value);
        assert(result == IMX_SUCCESS);
    }

    // Verify only 1 sector allocated
    mm2_sensor_state_t state;
    imx_get_sensor_state(IMX_UPLOAD_TELEMETRY, &csb, &csd, &state);
    assert(state.ram_start_sector == state.ram_end_sector);  // Same sector

    // Verify space efficiency
    mm2_stats_t stats;
    imx_get_memory_stats(&stats);
    assert(stats.space_efficiency_percent == 75);

    printf("✓ TSD space efficiency test passed\n");
}

// Test: Verify timestamp calculation accuracy
void test_tsd_timestamp_calculation(void) {
    imx_control_sensor_block_t csb = {
        .id = 0,
        .sample_rate = 60000  // 60 seconds
    };
    control_sensor_data_t csd = {0};

    imx_configure_sensor(IMX_UPLOAD_TELEMETRY, &csb, &csd);
    imx_activate_sensor(IMX_UPLOAD_TELEMETRY, &csb, &csd);

    uint64_t start_time = mm2_get_utc_time_ms();

    // Write 3 values
    for (int i = 0; i < 3; i++) {
        imx_data_32_t value = { .uint_32bit = 100 + i };
        imx_write_tsd(IMX_UPLOAD_TELEMETRY, &csb, &csd, value);
    }

    // Read back and verify timestamps
    tsd_evt_value_t samples[3];
    uint16_t filled = 0;
    imx_read_bulk_samples(IMX_UPLOAD_TELEMETRY, &csb, &csd,
                         samples, 3, 3, &filled);

    assert(filled == 3);

    // Verify timestamp progression
    uint64_t expected_time = start_time;
    for (int i = 0; i < 3; i++) {
        // Allow small variance due to execution time
        uint64_t diff = (samples[i].timestamp > expected_time) ?
                        (samples[i].timestamp - expected_time) :
                        (expected_time - samples[i].timestamp);
        assert(diff < 100);  // Within 100ms

        expected_time += csb.sample_rate;
    }

    printf("✓ Timestamp calculation test passed\n");
}
```

### 6.2 Integration Test Examples

```c
// Test: Multi-sensor concurrent writes (Linux)
void test_concurrent_sensor_writes(void) {
    #ifdef LINUX_PLATFORM
    const int NUM_SENSORS = 10;
    const int WRITES_PER_SENSOR = 100;

    pthread_t threads[NUM_SENSORS];

    // Thread function
    void* writer_thread(void* arg) {
        int sensor_id = (int)(intptr_t)arg;

        for (int i = 0; i < WRITES_PER_SENSOR; i++) {
            imx_data_32_t value = { .uint_32bit = i };
            imx_write_tsd(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[sensor_id],
                &sensor_data[sensor_id],
                value
            );
        }

        return NULL;
    }

    // Launch threads
    for (int i = 0; i < NUM_SENSORS; i++) {
        pthread_create(&threads[i], NULL, writer_thread, (void*)(intptr_t)i);
    }

    // Wait for completion
    for (int i = 0; i < NUM_SENSORS; i++) {
        pthread_join(threads[i], NULL);
    }

    // Verify all writes succeeded
    for (int i = 0; i < NUM_SENSORS; i++) {
        uint32_t count = imx_get_new_sample_count(
            IMX_UPLOAD_TELEMETRY,
            &sensor_config[i],
            &sensor_data[i]
        );
        assert(count == WRITES_PER_SENSOR);
    }

    printf("✓ Concurrent write test passed\n");
    #endif
}

// Test: ACK/NACK retry logic
void test_upload_retry_logic(void) {
    // Write test data
    for (int i = 0; i < 10; i++) {
        imx_data_32_t value = { .uint_32bit = i };
        imx_write_tsd(IMX_UPLOAD_TELEMETRY, &csb, &csd, value);
    }

    // First upload attempt (will fail)
    tsd_evt_value_t buffer[10];
    uint16_t filled = 0;
    imx_read_bulk_samples(IMX_UPLOAD_TELEMETRY, &csb, &csd,
                         buffer, 10, 10, &filled);
    assert(filled == 10);

    // Simulate upload failure
    imx_revert_all_pending(IMX_UPLOAD_TELEMETRY, &csb, &csd);

    // Verify data still available
    uint32_t count = imx_get_new_sample_count(IMX_UPLOAD_TELEMETRY, &csb, &csd);
    assert(count == 10);

    // Second attempt (will succeed)
    imx_read_bulk_samples(IMX_UPLOAD_TELEMETRY, &csb, &csd,
                         buffer, 10, 10, &filled);
    assert(filled == 10);

    // ACK successful upload
    imx_erase_all_pending(IMX_UPLOAD_TELEMETRY, &csb, &csd, 10);

    // Verify data cleared
    count = imx_get_new_sample_count(IMX_UPLOAD_TELEMETRY, &csb, &csd);
    assert(count == 0);

    printf("✓ ACK/NACK retry test passed\n");
}
```

---

## 7. Integration Examples

### 7.1 Fleet-Connect Integration

```c
// In Fleet-Connect main loop
void fleet_connect_sensor_integration(void) {
    // Configure OBD2 sensors
    for (int i = 0; i < obd2_sensor_count; i++) {
        sensor_config[i].id = i;
        sensor_config[i].sample_rate = obd2_sensors[i].update_rate;

        imx_configure_sensor(
            IMX_UPLOAD_GATEWAY,
            &sensor_config[i],
            &sensor_data[i]
        );

        imx_activate_sensor(
            IMX_UPLOAD_GATEWAY,
            &sensor_config[i],
            &sensor_data[i]
        );
    }
}

// OBD2 data callback
void on_obd2_data_received(uint16_t pid, uint32_t value) {
    int sensor_idx = pid_to_sensor_index(pid);

    imx_data_32_t data;
    data.uint_32bit = value;

    imx_result_t result = imx_write_tsd(
        IMX_UPLOAD_GATEWAY,
        &sensor_config[sensor_idx],
        &sensor_data[sensor_idx],
        data
    );

    if (result != IMX_SUCCESS) {
        printf("WARNING: Failed to write OBD2 data for PID 0x%04X\n", pid);
    }
}
```

### 7.2 Process Manager Integration

```c
// In process_memory_manager() integration
void application_main_loop(void) {
    imx_time_t current_time = imx_time_get_system_time();

    // Call MM2 processing
    process_memory_manager(current_time);

    // Check memory pressure and trigger spooling (Linux)
    #ifdef LINUX_PLATFORM
    for (int i = 0; i < MAX_SENSORS; i++) {
        if (sensor_data[i].active) {
            // Check if spooling needed for each upload source
            for (int source = 0; source < IMX_UPLOAD_NO_SOURCES; source++) {
                mm2_stats_t stats;
                imx_get_memory_stats(&stats);

                // Trigger spooling at 80% usage
                uint32_t usage_percent = ((stats.total_sectors - stats.free_sectors) * 100)
                                        / stats.total_sectors;

                if (usage_percent >= 80) {
                    process_normal_disk_spooling(&sensor_data[i], source);
                }
            }
        }
    }
    #endif
}
```

---

## 8. Best Practices

### 8.1 Sensor Configuration

**DO**:
- Set appropriate sample rates for TSD sensors
- Use EVT mode (sample_rate=0) for irregular events
- Configure upload source based on data criticality
- Activate sensors only when needed

**DON'T**:
- Change sample_rate after activation
- Mix TSD and EVT writes to same sensor
- Forget to deactivate sensors when done
- Use sample_rate < 100ms (too frequent)

### 8.2 Memory Management

**DO**:
- Monitor memory statistics regularly
- Implement disk spooling triggers (Linux)
- Handle IMX_OUT_OF_MEMORY gracefully
- Free resources in reverse allocation order

**DON'T**:
- Ignore allocation failures
- Write during shutdown
- Leak buffers on error paths
- Skip chain validation in debug builds

### 8.3 Upload Handling

**DO**:
- Use bulk reads for efficiency
- Implement retry logic for transient errors
- Revert on NACK, erase on ACK
- Batch uploads for network efficiency

**DON'T**:
- Read without marking as pending
- Forget to call erase_all_pending
- Upload during shutdown
- Retry permanently failed data

### 8.4 Power Management

**DO**:
- Register shutdown callback early
- Flush all active sensors
- Respect 60-second deadline
- Test power abort recovery

**DON'T**:
- Skip sensor shutdown calls
- Block during shutdown
- Write after shutdown_requested
- Ignore emergency mode flag

---

## Conclusion

This implementation guide provides practical patterns and examples for integrating MM2 into iMatrix applications. The key to successful integration is understanding the trade-offs between space efficiency, real-time constraints, and reliability requirements.

Remember:
- MM2 achieves 75% space efficiency through clever data layout
- Platform-specific behaviors require careful handling
- Upload source segregation enables flexible data routing
- Proper error handling is critical for embedded reliability
- Testing should cover concurrent access, power loss, and memory pressure scenarios

For additional support, refer to:
- MM2_TECHNICAL_DOCUMENTATION.md for API reference
- Test framework in memory_test_framework.c/h
- Example test suites in memory_test_suites.c/h
