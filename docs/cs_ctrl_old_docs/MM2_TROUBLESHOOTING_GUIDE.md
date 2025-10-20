# iMatrix Memory Manager v2.8 - Troubleshooting and Debugging Guide

## Table of Contents
1. [Common Issues and Solutions](#common-issues-and-solutions)
2. [Debugging Techniques](#debugging-techniques)
3. [Error Code Reference](#error-code-reference)
4. [Platform-Specific Issues](#platform-specific-issues)
5. [Performance Problems](#performance-problems)
6. [Data Corruption Investigation](#data-corruption-investigation)
7. [Memory Leak Detection](#memory-leak-detection)
8. [Diagnostic Tools](#diagnostic-tools)

---

## 1. Common Issues and Solutions

### Issue 1.1: Write Operations Fail with IMX_OUT_OF_MEMORY

**Symptoms**:
```c
imx_result_t result = imx_write_tsd(source, &csb, &csd, value);
// Returns: IMX_OUT_OF_MEMORY
```

**Possible Causes**:
1. Memory pool exhausted
2. Disk spooling not configured (Linux)
3. Too many active sensors
4. Pending data not being cleared

**Solutions**:

```c
// Solution 1: Check memory statistics
mm2_stats_t stats;
imx_get_memory_stats(&stats);
printf("Free: %u/%u sectors (%.1f%% used)\n",
       stats.free_sectors, stats.total_sectors,
       ((stats.total_sectors - stats.free_sectors) * 100.0) / stats.total_sectors);

if (stats.free_sectors < 100) {
    printf("WARNING: Low memory!\n");
}

// Solution 2: Trigger disk spooling manually (Linux)
#ifdef LINUX_PLATFORM
for (int i = 0; i < active_sensors; i++) {
    if (sensor_data[i].active) {
        process_normal_disk_spooling(&sensor_data[i], IMX_UPLOAD_TELEMETRY);
    }
}
#endif

// Solution 3: Clear acknowledged data
if (last_upload_successful) {
    imx_erase_all_pending(source, &csb, &csd, uploaded_count);
}

// Solution 4: STM32 - Check for pending data blocking
#ifndef LINUX_PLATFORM
mm2_sensor_state_t state;
imx_get_sensor_state(source, &csb, &csd, &state);
uint32_t total_pending = 0;
for (int i = 0; i < UPLOAD_SOURCE_MAX; i++) {
    total_pending += state.pending_counts[i];
}
if (total_pending > state.total_records * 0.5) {
    printf("WARNING: Too much pending data - upload stuck?\n");
}
#endif
```

### Issue 1.2: IMX_TIMEOUT on STM32 Writes

**Symptoms**:
```c
imx_write_tsd(source, &csb, &csd, value);
// Returns: IMX_TIMEOUT
```

**Cause**: UTC time not yet established on STM32

**Solutions**:

```c
// Solution 1: Check UTC availability
if (!imx_memory_manager_ready()) {
    printf("Waiting for UTC time establishment...\n");

    // Wait for time sync (implement in your time module)
    while (!imx_system_time_syncd()) {
        osDelay(100);  // FreeRTOS delay
    }

    // Notify MM2 that UTC is now available
    imx_set_utc_available(1);
}

// Solution 2: Use EVT mode temporarily
// EVT mode can write with provided timestamps
imx_data_32_t value;
value.uint_32bit = sensor_reading;

// Use local time for now (will convert to UTC later)
imx_utc_time_ms_t local_time = HAL_GetTick();

imx_write_evt(source, &csb, &csd, value, local_time);
```

### Issue 1.3: Data Loss After Power Cycle

**Symptoms**: Data written before power cycle is not recovered

**Cause**: Emergency shutdown not called or files not recovered

**Solutions**:

```c
// Solution 1: Ensure shutdown callback registered
void power_down_interrupt_handler(void) {
    // Notify MM2
    imx_power_event_detected();

    // Application must flush each sensor
    for (int i = 0; i < MAX_SENSORS; i++) {
        if (sensor_data[i].active) {
            imx_memory_manager_shutdown(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[i],
                &sensor_data[i],
                60000  // 60 second deadline
            );
        }
    }
}

// Solution 2: Check for emergency files on startup (Linux)
#ifdef LINUX_PLATFORM
// MM2 automatically calls this during init:
// recover_disk_spooled_data();

// Manually check for emergency files:
DIR* dir = opendir("/tmp/mm2");
if (dir) {
    struct dirent* entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strstr(entry->d_name, "emergency")) {
            printf("Found emergency file: %s\n", entry->d_name);
        }
    }
    closedir(dir);
}
#endif
```

### Issue 1.4: Incorrect Timestamps on Read

**Symptoms**: Timestamps don't match expected sample times

**Cause**: Wrong sample_rate or mismatched TSD/EVT mode

**Solutions**:

```c
// Solution 1: Verify sensor configuration
imx_control_sensor_block_t* csb = &sensor_config[sensor_idx];

if (csb->sample_rate == 0) {
    printf("ERROR: Sensor %d configured as EVT but writing TSD!\n", sensor_idx);
    // Fix: Set correct sample rate
    csb->sample_rate = 60000;  // 60 seconds
}

// Solution 2: Verify timestamp calculation
tsd_evt_value_t sample;
uint16_t filled;
imx_read_bulk_samples(source, csb, csd, &sample, 1, 1, &filled);

uint64_t expected_timestamp = first_sample_time + (sample_index * csb->sample_rate);
uint64_t actual_timestamp = sample.timestamp;

if (abs(expected_timestamp - actual_timestamp) > 1000) {
    printf("WARNING: Timestamp drift detected!\n");
    printf("Expected: %llu, Actual: %llu\n", expected_timestamp, actual_timestamp);
}
```

### Issue 1.5: Disk Files Not Being Cleaned Up

**Symptoms**: Disk space grows indefinitely on Linux

**Cause**: ACK not being called after successful upload

**Solutions**:

```c
// Solution 1: Always ACK after successful upload
if (upload_to_cloud(samples, count) == SUCCESS) {
    imx_erase_all_pending(source, &csb, &csd, count);
    // This triggers cleanup_fully_acked_files()
}

// Solution 2: Manual cleanup check
#ifdef LINUX_PLATFORM
// Check disk usage
mm2_sensor_state_t state;
imx_get_sensor_state(source, &csb, &csd, &state);

printf("Total disk space used: %llu bytes\n",
       (unsigned long long)csd.mmcb.total_disk_space_used);

// Force cleanup if needed
for (int src = 0; src < IMX_UPLOAD_NO_SOURCES; src++) {
    cleanup_fully_acked_files(&csd, src);
}
#endif
```

---

## 2. Debugging Techniques

### 2.1 Enable Debug Logging

**Compile-time Debug**:
```cmake
# In CMakeLists.txt
add_definitions(-DDEBUG_ENABLED=1)
```

**Runtime Verbose Mode**:
```c
// Add to mm2_api.c or your code
#define MM2_VERBOSE 1

#if MM2_VERBOSE
#define MM2_DEBUG(fmt, ...) printf("[MM2] " fmt "\n", ##__VA_ARGS__)
#else
#define MM2_DEBUG(fmt, ...)
#endif

// Use in operations
MM2_DEBUG("Writing TSD: sensor=%u, value=%u", sensor_id, value.uint_32bit);
MM2_DEBUG("Sector allocated: id=%u, type=%u", sector_id, sector_type);
```

### 2.2 Chain Validation

**Validate Chain Integrity**:
```c
void debug_validate_all_chains(void) {
    printf("=== Chain Validation Report ===\n");

    for (int i = 0; i < MAX_SENSORS; i++) {
        if (sensor_data[i].active) {
            imx_result_t result = imx_validate_sector_chains(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[i],
                &sensor_data[i]
            );

            if (result != IMX_SUCCESS) {
                printf("ERROR: Sensor %d chain corrupted!\n", i);

                // Dump chain details
                dump_sensor_chain(&sensor_data[i]);
            } else {
                printf("✓ Sensor %d chain valid\n", i);
            }
        }
    }
}

void dump_sensor_chain(control_sensor_data_t* csd) {
    printf("Chain dump for sensor:\n");
    printf("  Start: %u, End: %u\n",
           csd->mmcb.ram_start_sector_id,
           csd->mmcb.ram_end_sector_id);

    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;
    int sector_count = 0;

    while (current != NULL_SECTOR_ID && sector_count < 100) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current);

        printf("  [%d] Sector %u: type=%u, in_use=%u, next=%u\n",
               sector_count,
               current,
               entry ? entry->sector_type : 255,
               entry ? entry->in_use : 0,
               entry ? entry->next_sector_id : NULL_SECTOR_ID);

        if (entry) {
            current = entry->next_sector_id;
        } else {
            printf("  ERROR: NULL chain entry!\n");
            break;
        }

        sector_count++;
    }

    if (sector_count >= 100) {
        printf("  ERROR: Chain too long or circular!\n");
    }
}
```

### 2.3 Memory Pool Visualization

```c
void print_memory_pool_map(void) {
    printf("\n=== Memory Pool Map ===\n");
    printf("Total sectors: %u, Free: %u\n",
           g_memory_pool.total_sectors,
           g_memory_pool.free_sectors);

    // Print grid of sector usage
    for (uint32_t i = 0; i < g_memory_pool.total_sectors; i++) {
        sector_chain_entry_t* entry = &g_memory_pool.chain_table[i];

        if (i % 64 == 0) {
            printf("\n%04u: ", i);
        }

        if (!entry->in_use) {
            printf(".");  // Free
        } else if (entry->pending_ack) {
            printf("P");  // Pending
        } else if (entry->spooled_to_disk) {
            printf("D");  // Disk
        } else if (entry->sector_type == SECTOR_TYPE_TSD) {
            printf("T");  // TSD
        } else {
            printf("E");  // EVT
        }
    }
    printf("\n\n");
    printf("Legend: . = Free, T = TSD, E = EVT, P = Pending, D = Disk\n");
}
```

### 2.4 Pending Data Tracking

```c
void debug_pending_data_report(void) {
    printf("\n=== Pending Data Report ===\n");

    for (int sensor_idx = 0; sensor_idx < MAX_SENSORS; sensor_idx++) {
        if (!sensor_data[sensor_idx].active) continue;

        printf("Sensor %d:\n", sensor_idx);

        for (int src = 0; src < UPLOAD_SOURCE_MAX; src++) {
            uint32_t pending = sensor_data[sensor_idx].mmcb
                              .pending_by_source[src].pending_count;

            if (pending > 0) {
                SECTOR_ID_TYPE start = sensor_data[sensor_idx].mmcb
                                      .pending_by_source[src].pending_start_sector;
                uint16_t offset = sensor_data[sensor_idx].mmcb
                                 .pending_by_source[src].pending_start_offset;

                printf("  Source %d: %u pending records (start: sector=%u, offset=%u)\n",
                       src, pending, start, offset);
            }
        }
    }
}
```

### 2.5 Performance Profiling

```c
typedef struct {
    const char* operation;
    uint64_t start_time;
    uint64_t total_time;
    uint32_t call_count;
} perf_counter_t;

static perf_counter_t perf_counters[10];
static int perf_counter_count = 0;

#define PERF_START(name) \
    int __perf_idx = -1; \
    for (int i = 0; i < perf_counter_count; i++) { \
        if (strcmp(perf_counters[i].operation, name) == 0) { \
            __perf_idx = i; \
            break; \
        } \
    } \
    if (__perf_idx == -1) { \
        __perf_idx = perf_counter_count++; \
        perf_counters[__perf_idx].operation = name; \
        perf_counters[__perf_idx].total_time = 0; \
        perf_counters[__perf_idx].call_count = 0; \
    } \
    perf_counters[__perf_idx].start_time = mm2_get_utc_time_ms();

#define PERF_END() \
    perf_counters[__perf_idx].total_time += \
        mm2_get_utc_time_ms() - perf_counters[__perf_idx].start_time; \
    perf_counters[__perf_idx].call_count++;

// Usage
imx_result_t debug_write_tsd(/* params */) {
    PERF_START("write_tsd");
    imx_result_t result = imx_write_tsd(/* params */);
    PERF_END();
    return result;
}

void print_performance_report(void) {
    printf("\n=== Performance Report ===\n");
    for (int i = 0; i < perf_counter_count; i++) {
        perf_counter_t* pc = &perf_counters[i];
        printf("%s: %u calls, %llu ms total, %.2f ms avg\n",
               pc->operation,
               pc->call_count,
               (unsigned long long)pc->total_time,
               (double)pc->total_time / pc->call_count);
    }
}
```

---

## 3. Error Code Reference

| Error Code | Value | Meaning | Action |
|------------|-------|---------|--------|
| IMX_SUCCESS | 0 | Operation successful | Continue |
| IMX_ERROR | -1 | Generic error | Check logs |
| IMX_OUT_OF_MEMORY | -2 | Pool exhausted | Spool to disk or clear pending |
| IMX_INVALID_PARAMETER | -3 | Bad input | Check parameters |
| IMX_INVALID_ENTRY | -4 | Bad sensor ID or inactive | Verify sensor state |
| IMX_TIMEOUT | -5 | Operation timed out | Wait and retry (STM32 UTC) |
| IMX_NO_DATA | -6 | No data available | Normal, not an error |
| IMX_INIT_ERROR | -7 | Initialization failed | Check system resources |

---

## 4. Platform-Specific Issues

### 4.1 Linux-Specific

**Issue**: Disk spooling not triggering

**Debug**:
```c
// Check memory pressure
mm2_stats_t stats;
imx_get_memory_stats(&stats);
uint32_t usage = ((stats.total_sectors - stats.free_sectors) * 100)
                / stats.total_sectors;

printf("Memory usage: %u%%\n", usage);

if (usage < 80) {
    printf("Below threshold - spooling not needed\n");
} else {
    printf("Above threshold - should be spooling\n");

    // Check spool state
    for (int src = 0; src < IMX_UPLOAD_NO_SOURCES; src++) {
        normal_spool_state_t* state = &csd.mmcb.per_source[src].spool_state;
        printf("Source %d: state=%d, errors=%u\n",
               src,
               state->current_state,
               state->consecutive_errors);
    }
}
```

**Issue**: File handle leaks

**Debug**:
```bash
# Check open file descriptors
ls -l /proc/$(pidof your_app)/fd | grep mm2

# Expected: 1-2 files per active sensor
# Problem: Many more than expected
```

**Fix**:
```c
// Ensure cleanup on deactivate
imx_deactivate_sensor(source, &csb, &csd);

// Verify files closed
for (int src = 0; src < IMX_UPLOAD_NO_SOURCES; src++) {
    if (csd.mmcb.per_source[src].active_spool_fd >= 0) {
        printf("WARNING: File still open for source %d\n", src);
    }
}
```

### 4.2 STM32-Specific

**Issue**: RAM exhaustion despite small data

**Debug**:
```c
// Check for pending data blocking
mm2_sensor_state_t state;
imx_get_sensor_state(IMX_UPLOAD_TELEMETRY, &csb, &csd, &state);

uint32_t total_pending = 0;
for (int i = 0; i < UPLOAD_SOURCE_MAX; i++) {
    total_pending += state.pending_counts[i];
}

printf("Total records: %u, Pending: %u (%.1f%%)\n",
       state.total_records,
       total_pending,
       (total_pending * 100.0) / state.total_records);

if (total_pending > state.total_records * 0.7) {
    printf("ERROR: Upload stalled - too much pending data\n");
    printf("Check upload task - may be blocked\n");
}
```

**Issue**: UTC time never established

**Debug**:
```c
// Check time sync status
extern int g_time_sync_complete;  // From your time module

if (!g_time_sync_complete) {
    printf("ERROR: Time sync not complete\n");
    // Check NTP/GPS/RTC initialization
}

// Force UTC available for testing (NOT for production!)
#ifdef DEBUG_BUILD
imx_set_utc_available(1);
#endif
```

---

## 5. Performance Problems

### Issue 5.1: Slow Write Operations

**Diagnosis**:
```c
uint64_t start = mm2_get_utc_time_ms();
imx_write_tsd(source, &csb, &csd, value);
uint64_t elapsed = mm2_get_utc_time_ms() - start;

if (elapsed > 10) {
    printf("WARNING: Write took %llu ms (expected <1 ms)\n", elapsed);
}
```

**Possible Causes**:
1. Disk I/O blocking (Linux)
2. Mutex contention (Linux)
3. Chain traversal overhead
4. Sector allocation overhead

**Solutions**:
```c
// Solution 1: Pre-allocate sectors
// Not directly supported, but can reduce allocation overhead by
// clearing old data more aggressively

// Solution 2: Reduce mutex hold time
// Already optimized in MM2, but check for deadlocks:
#ifdef LINUX_PLATFORM
pthread_mutex_trylock(&csd->mmcb.sensor_lock);
// If fails immediately, mutex may be held too long
#endif

// Solution 3: Batch writes
for (int i = 0; i < batch_size; i++) {
    imx_write_tsd(source, &csb, &csd, values[i]);
}
```

### Issue 5.2: Slow Read Operations

**Diagnosis**:
```c
uint64_t start = mm2_get_utc_time_ms();
imx_read_bulk_samples(source, &csb, &csd, buffer, size, count, &filled);
uint64_t elapsed = mm2_get_utc_time_ms() - start;

printf("Read %u samples in %llu ms (%.2f ms/sample)\n",
       filled, elapsed, (double)elapsed / filled);
```

**Solutions**:
```c
// Solution 1: Use bulk reads instead of single reads
// SLOW:
for (int i = 0; i < count; i++) {
    imx_read_next_tsd_evt(source, &csb, &csd, &data[i]);
}

// FAST:
imx_read_bulk_samples(source, &csb, &csd, data, count, count, &filled);

// Solution 2: Reduce chain traversal
// Keep read position closer to write position by uploading more frequently
```

---

## 6. Data Corruption Investigation

### 6.1 Detecting Corruption

```c
imx_result_t check_data_integrity(control_sensor_data_t* csd) {
    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;
    int sector_count = 0;

    while (current != NULL_SECTOR_ID) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current);

        if (!entry) {
            printf("ERROR: NULL chain entry at sector %u\n", current);
            return IMX_ERROR;
        }

        if (!entry->in_use) {
            printf("ERROR: Inactive sector %u in chain\n", current);
            return IMX_ERROR;
        }

        // Validate sector data
        memory_sector_t* sector = &g_memory_pool.sectors[current];
        uint32_t checksum = calculate_sector_checksum(sector->data);

        // Check for all-zero sector (may indicate corruption)
        int is_zero = 1;
        for (int i = 0; i < SECTOR_SIZE; i++) {
            if (sector->data[i] != 0) {
                is_zero = 0;
                break;
            }
        }

        if (is_zero) {
            printf("WARNING: All-zero sector at %u\n", current);
        }

        current = entry->next_sector_id;
        sector_count++;

        if (sector_count > g_memory_pool.total_sectors) {
            printf("ERROR: Circular chain detected\n");
            return IMX_ERROR;
        }
    }

    return IMX_SUCCESS;
}
```

### 6.2 Corruption Recovery

```c
imx_result_t attempt_corruption_recovery(control_sensor_data_t* csd) {
    printf("Attempting corruption recovery...\n");

    // Step 1: Break circular chains
    SECTOR_ID_TYPE visited[MAX_SECTORS] = {0};
    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;

    while (current != NULL_SECTOR_ID) {
        if (visited[current]) {
            printf("Breaking circular chain at sector %u\n", current);
            // Find previous sector and set its next to NULL
            for (int i = 0; i < MAX_SECTORS; i++) {
                if (visited[i] && get_next_sector_in_chain(i) == current) {
                    set_next_sector_in_chain(i, NULL_SECTOR_ID);
                    break;
                }
            }
            break;
        }
        visited[current] = 1;
        current = get_next_sector_in_chain(current);
    }

    // Step 2: Rebuild chain end pointer
    current = csd->mmcb.ram_start_sector_id;
    while (current != NULL_SECTOR_ID) {
        SECTOR_ID_TYPE next = get_next_sector_in_chain(current);
        if (next == NULL_SECTOR_ID) {
            csd->mmcb.ram_end_sector_id = current;
            break;
        }
        current = next;
    }

    // Step 3: Revalidate
    return imx_validate_sector_chains(IMX_UPLOAD_TELEMETRY,
                                     &sensor_config[0],  // Dummy
                                     csd);
}
```

---

## 7. Memory Leak Detection

### 7.1 Sector Leak Detection

```c
void check_for_sector_leaks(void) {
    printf("\n=== Sector Leak Check ===\n");

    // Count sectors in use
    uint32_t sectors_in_use = 0;
    for (uint32_t i = 0; i < g_memory_pool.total_sectors; i++) {
        if (g_memory_pool.chain_table[i].in_use) {
            sectors_in_use++;
        }
    }

    // Count sectors in all sensor chains
    uint32_t sectors_in_chains = 0;
    for (int sensor_idx = 0; sensor_idx < MAX_SENSORS; sensor_idx++) {
        if (sensor_data[sensor_idx].active) {
            SECTOR_ID_TYPE current = sensor_data[sensor_idx].mmcb.ram_start_sector_id;
            while (current != NULL_SECTOR_ID) {
                sectors_in_chains++;
                current = get_next_sector_in_chain(current);
            }
        }
    }

    printf("Sectors marked in_use: %u\n", sectors_in_use);
    printf("Sectors in chains: %u\n", sectors_in_chains);
    printf("Free list: %u\n", g_memory_pool.free_sectors);

    uint32_t accounted = sectors_in_chains + g_memory_pool.free_sectors;
    if (accounted != g_memory_pool.total_sectors) {
        printf("ERROR: Sector leak detected!\n");
        printf("  Missing: %u sectors\n",
               g_memory_pool.total_sectors - accounted);
    } else {
        printf("✓ No leaks detected\n");
    }
}
```

### 7.2 Disk Space Leak Detection (Linux)

```c
#ifdef LINUX_PLATFORM
void check_disk_space_leaks(void) {
    printf("\n=== Disk Space Leak Check ===\n");

    // Scan mm2 directory
    struct dirent *entry;
    DIR *dir = opendir("/tmp/mm2");

    if (!dir) {
        printf("ERROR: Cannot open mm2 directory\n");
        return;
    }

    uint64_t total_disk_usage = 0;
    int file_count = 0;

    while ((entry = readdir(dir)) != NULL) {
        if (strstr(entry->d_name, ".spool")) {
            char path[512];
            snprintf(path, sizeof(path), "/tmp/mm2/%s", entry->d_name);

            struct stat st;
            if (stat(path, &st) == 0) {
                total_disk_usage += st.st_size;
                file_count++;

                // Check file age
                time_t age = time(NULL) - st.st_mtime;
                if (age > 86400) {  // 24 hours
                    printf("WARNING: Old file: %s (age: %lu sec)\n",
                           entry->d_name, age);
                }
            }
        }
    }

    closedir(dir);

    printf("Total disk usage: %llu bytes (%d files)\n",
           total_disk_usage, file_count);

    if (total_disk_usage > 256 * 1024 * 1024) {
        printf("WARNING: Disk usage exceeds limit!\n");
    }
}
#endif
```

---

## 8. Diagnostic Tools

### 8.1 Complete System Health Check

```c
void mm2_health_check(void) {
    printf("\n");
    printf("╔═══════════════════════════════════════╗\n");
    printf("║   MM2 System Health Check             ║\n");
    printf("╚═══════════════════════════════════════╝\n\n");

    // 1. Memory statistics
    mm2_stats_t stats;
    imx_get_memory_stats(&stats);
    printf("Memory Pool:\n");
    printf("  Total sectors: %u\n", stats.total_sectors);
    printf("  Free sectors: %u (%.1f%%)\n",
           stats.free_sectors,
           (stats.free_sectors * 100.0) / stats.total_sectors);
    printf("  Active sensors: %u\n", stats.active_sensors);
    printf("  Space efficiency: %u%%\n", stats.space_efficiency_percent);
    printf("  Allocation failures: %llu\n", stats.allocation_failures);
    printf("\n");

    // 2. Active sensors
    printf("Active Sensors:\n");
    for (int i = 0; i < MAX_SENSORS; i++) {
        if (sensor_data[i].active) {
            mm2_sensor_state_t state;
            imx_get_sensor_state(IMX_UPLOAD_TELEMETRY,
                               &sensor_config[i], &sensor_data[i], &state);

            printf("  Sensor %d: %llu records\n", i, state.total_records);
        }
    }
    printf("\n");

    // 3. Chain validation
    printf("Chain Integrity:\n");
    int chains_valid = 1;
    for (int i = 0; i < MAX_SENSORS; i++) {
        if (sensor_data[i].active) {
            imx_result_t result = imx_validate_sector_chains(
                IMX_UPLOAD_TELEMETRY,
                &sensor_config[i],
                &sensor_data[i]
            );
            if (result != IMX_SUCCESS) {
                printf("  ✗ Sensor %d: CORRUPTED\n", i);
                chains_valid = 0;
            }
        }
    }
    if (chains_valid) {
        printf("  ✓ All chains valid\n");
    }
    printf("\n");

    // 4. Leak check
    check_for_sector_leaks();
    printf("\n");

    // 5. Platform-specific checks
    #ifdef LINUX_PLATFORM
    check_disk_space_leaks();
    #else
    printf("Platform: STM32 (RAM only)\n");
    #endif

    printf("\n");
    printf("═══════════════════════════════════════\n");
    printf("Health check complete.\n");
    printf("═══════════════════════════════════════\n\n");
}
```

### 8.2 Automated Test Suite

```c
int run_mm2_diagnostic_tests(void) {
    int passed = 0;
    int failed = 0;

    printf("\n*** Running MM2 Diagnostic Tests ***\n\n");

    // Test 1: Write and read
    printf("[TEST 1] Write and read...");
    imx_data_32_t value = { .uint_32bit = 0x12345678 };
    if (imx_write_tsd(IMX_UPLOAD_TELEMETRY, &sensor_config[0],
                     &sensor_data[0], value) == IMX_SUCCESS) {
        tsd_evt_value_t read_value;
        uint16_t filled;
        if (imx_read_bulk_samples(IMX_UPLOAD_TELEMETRY, &sensor_config[0],
                                 &sensor_data[0], &read_value, 1, 1,
                                 &filled) == IMX_SUCCESS &&
            read_value.value == 0x12345678) {
            printf(" PASS\n");
            passed++;
        } else {
            printf(" FAIL\n");
            failed++;
        }
    } else {
        printf(" FAIL\n");
        failed++;
    }

    // Test 2: Chain integrity
    printf("[TEST 2] Chain integrity...");
    if (imx_validate_sector_chains(IMX_UPLOAD_TELEMETRY,
                                   &sensor_config[0],
                                   &sensor_data[0]) == IMX_SUCCESS) {
        printf(" PASS\n");
        passed++;
    } else {
        printf(" FAIL\n");
        failed++;
    }

    // Test 3: ACK/NACK
    printf("[TEST 3] ACK/NACK cycle...");
    imx_revert_all_pending(IMX_UPLOAD_TELEMETRY,
                          &sensor_config[0], &sensor_data[0]);
    uint32_t count_after_nack = imx_get_new_sample_count(
        IMX_UPLOAD_TELEMETRY, &sensor_config[0], &sensor_data[0]
    );
    if (count_after_nack > 0) {
        printf(" PASS\n");
        passed++;
    } else {
        printf(" FAIL\n");
        failed++;
    }

    // Test 4: Memory statistics
    printf("[TEST 4] Memory statistics...");
    mm2_stats_t stats;
    if (imx_get_memory_stats(&stats) == IMX_SUCCESS &&
        stats.space_efficiency_percent == 75) {
        printf(" PASS\n");
        passed++;
    } else {
        printf(" FAIL (efficiency = %u%%)\n",
               stats.space_efficiency_percent);
        failed++;
    }

    printf("\n*** Results: %d passed, %d failed ***\n\n", passed, failed);
    return (failed == 0) ? 0 : -1;
}
```

---

## Conclusion

This troubleshooting guide provides comprehensive diagnostic tools and solutions for common MM2 issues. Key takeaways:

1. **Always validate chains** after suspected corruption
2. **Monitor memory statistics** to prevent exhaustion
3. **Check pending data** regularly to avoid upload stalls
4. **Use debugging tools** to identify root causes quickly
5. **Test recovery paths** before deploying to production

For additional support:
- Review MM2_TECHNICAL_DOCUMENTATION.md for API details
- Check MM2_IMPLEMENTATION_GUIDE.md for usage examples
- Run automated diagnostic tests regularly
- Enable debug logging for detailed trace information
