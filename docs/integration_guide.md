# iMatrix Tiered Storage System - Integration Guide

## Quick Start Integration

### Prerequisites Checklist
- [ ] Linux platform with POSIX file system support
- [ ] Storage directory `/usr/qk/etc/sv/FC-1/history/` writable by application
- [ ] Existing iMatrix memory management system operational
- [ ] Access to main application loop for background processing

### Step 1: Directory Setup
```bash
# Create storage directories
sudo mkdir -p /usr/qk/etc/sv/FC-1/history/corrupted
sudo chown $(whoami):$(whoami) /usr/qk/etc/sv/FC-1/history/
sudo chmod 755 /usr/qk/etc/sv/FC-1/history/
```

### Step 2: Main Loop Integration
```c
// Add to your main application loop
void main_loop(void) {
    imx_time_t current_time;
    
    while (system_running) {
        // Get current time
        imx_time_get_time(&current_time);
        
        // *** ADD THIS LINE ***
        process_memory(current_time);
        
        // Your existing processing
        process_sensors();
        process_network();
        
        imx_delay_milliseconds(10);
    }
}
```

### Step 3: Startup Integration
```c
// Add to system initialization
void system_init(void) {
    // Your existing initialization
    init_platform();
    init_memory_manager();
    
    // *** ADD THIS LINE ***
    perform_power_failure_recovery();
    
    printf("System ready with tiered storage\n");
}
```

### Step 4: Shutdown Integration
```c
// Add to shutdown sequence
void system_shutdown(void) {
    printf("Initiating shutdown...\n");
    
    // *** ADD THESE LINES ***
    flush_all_to_disk();
    
    // Wait for completion
    imx_time_t current_time;
    while (get_pending_disk_write_count() > 0) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        imx_delay_milliseconds(100);
    }
    
    printf("Shutdown complete\n");
}
```

### Step 5: Verification
```c
// Add monitoring to verify operation
void monitor_tiered_storage(void) {
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    printf("RAM Usage: %.1f%% (%u/%u sectors)\n", 
           stats->usage_percentage, 
           stats->used_sectors, 
           stats->total_sectors);
    
    printf("Files created: %u, deleted: %u\n",
           tiered_state_machine.total_files_created,
           tiered_state_machine.total_files_deleted);
}
```

## Integration Examples

### Example 1: Basic Integration
```c
#include "memory_manager.h"

int main(void) {
    // Initialize system
    init_platform();
    init_memory_manager();
    perform_power_failure_recovery();
    
    imx_time_t current_time;
    
    // Main loop
    while (1) {
        imx_time_get_time(&current_time);
        
        // Tiered storage processing
        process_memory(current_time);
        
        // Application work
        do_application_work();
        
        imx_delay_milliseconds(10);
    }
    
    // Shutdown
    flush_all_to_disk();
    while (get_pending_disk_write_count() > 0) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        imx_delay_milliseconds(100);
    }
    
    return 0;
}
```

### Example 2: With Error Handling
```c
void robust_integration(void) {
    // Initialize with error checking
    if (init_memory_manager() != IMX_SUCCESS) {
        printf("ERROR: Memory manager initialization failed\n");
        return;
    }
    
    // Perform recovery with status check
    perform_power_failure_recovery();
    printf("Power failure recovery completed\n");
    
    imx_time_t current_time;
    uint32_t error_count = 0;
    
    while (system_running) {
        imx_time_get_time(&current_time);
        
        // Process with error monitoring
        process_memory(current_time);
        
        // Check for storage issues
        if (!is_disk_usage_acceptable()) {
            printf("WARNING: Disk usage high, cleanup in progress\n");
            error_count++;
        }
        
        // Application processing
        do_work();
        
        // Periodic status
        if ((current_time % 60000) == 0) { // Every minute
            monitor_tiered_storage();
        }
        
        imx_delay_milliseconds(10);
    }
    
    // Graceful shutdown
    printf("Shutting down...\n");
    flush_all_to_disk();
    
    uint32_t timeout = 30000; // 30 second timeout
    while (get_pending_disk_write_count() > 0 && timeout > 0) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        imx_delay_milliseconds(100);
        timeout -= 100;
    }
    
    if (timeout == 0) {
        printf("WARNING: Shutdown timeout, some data may not be flushed\n");
    } else {
        printf("Clean shutdown completed\n");
    }
}
```

### Example 3: Multi-threaded Integration
```c
// Background thread for tiered storage
void* tiered_storage_thread(void* arg) {
    imx_time_t current_time;
    
    while (storage_thread_running) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        imx_delay_milliseconds(100);
    }
    
    return NULL;
}

// Main application
int main(void) {
    // Initialize
    init_platform();
    init_memory_manager();
    perform_power_failure_recovery();
    
    // Start background thread
    pthread_t storage_thread;
    storage_thread_running = true;
    pthread_create(&storage_thread, NULL, tiered_storage_thread, NULL);
    
    // Main application loop (no tiered storage calls needed)
    while (application_running) {
        do_application_work();
        imx_delay_milliseconds(10);
    }
    
    // Shutdown
    flush_all_to_disk();
    
    // Wait for flush completion
    while (get_pending_disk_write_count() > 0) {
        imx_delay_milliseconds(100);
    }
    
    // Stop background thread
    storage_thread_running = false;
    pthread_join(storage_thread, NULL);
    
    return 0;
}
```

## Migration from Existing Code

### No Changes Required for Existing Functions
The tiered storage system maintains 100% backward compatibility:

```c
// All existing code continues to work unchanged
write_tsd_evt(csb, csd, entry, value, add_gps);
read_tsd_evt(csb, csd, entry, &value);
platform_sector_t sector = imx_get_free_sector();
free_sector(sector);
```

### Optional: Use Enhanced Functions
For new code, consider using the enhanced secure functions:

```c
// Enhanced functions with better error handling
imx_memory_error_t result = read_rs_safe(sector, offset, data, length, buffer_size);
if (result != IMX_MEMORY_SUCCESS) {
    printf("Read error: %d\n", result);
}

result = write_rs_safe(sector, offset, data, length, buffer_size);
if (result != IMX_MEMORY_SUCCESS) {
    printf("Write error: %d\n", result);
}
```

### Extended Sector Operations
Use extended operations for cross-storage chains:

```c
// Works with both RAM and disk sectors
extended_sector_result_t result = get_next_sector_extended(current_sector);
if (result.error == IMX_MEMORY_SUCCESS) {
    extended_sector_t next = result.next_sector;
    
    // Read from RAM or disk transparently
    imx_memory_error_t read_result = read_sector_extended(
        next, 0, buffer, sizeof(buffer), sizeof(buffer));
}
```

## Configuration and Tuning

### Adjust Processing Intervals
```c
// In memory_manager.h, modify for different timing
#define MEMORY_PROCESS_INTERVAL_TIME    (500)       // 0.5 second (more responsive)
#define MEMORY_PROCESS_INTERVAL_TIME    (2000)      // 2 seconds (less overhead)
```

### Adjust Migration Threshold
```c
// In memory_manager.h, modify for different thresholds
#define MEMORY_TO_DISK_THRESHOLD        (70)        // More aggressive (70%)
#define MEMORY_TO_DISK_THRESHOLD        (90)        // Less aggressive (90%)
```

### Adjust Batch Sizes
```c
// In memory_manager.h, modify for different performance
#define MAX_TSD_SECTORS_PER_ITERATION   (12)        // Larger batches
#define MAX_EVT_SECTORS_PER_ITERATION   (6)         // Larger batches
```

### Custom Storage Path
```c
// In memory_manager.h, modify for different location
#define DISK_STORAGE_PATH              "/custom/path/storage/"
```

## Testing and Validation

### Basic Functionality Test
```c
void test_basic_functionality(void) {
    // Initialize system
    init_memory_manager();
    perform_power_failure_recovery();
    
    // Allocate some sectors
    platform_sector_t sector1 = imx_get_free_sector();
    platform_sector_t sector2 = imx_get_free_sector();
    
    printf("Allocated sectors: %d, %d\n", sector1, sector2);
    
    // Write test data
    uint32_t test_data[] = {0xDEADBEEF, 0xCAFEBABE};
    write_rs(sector1, 0, test_data, 2);  // Write 2 uint32_t values (not sizeof)
    
    // Force migration by filling RAM
    // ... allocate many sectors to trigger 80% threshold ...
    
    // Process for migration
    imx_time_t current_time;
    for (int i = 0; i < 100; i++) {
        imx_time_get_time(&current_time);
        process_memory(current_time);
        imx_delay_milliseconds(100);
    }
    
    // Verify data still accessible
    uint32_t read_data[2];
    read_rs(sector1, 0, read_data, 2);  // Read 2 uint32_t values (not sizeof)
    
    if (read_data[0] == 0xDEADBEEF && read_data[1] == 0xCAFEBABE) {
        printf("SUCCESS: Data preserved across migration\n");
    } else {
        printf("ERROR: Data corruption detected\n");
    }
}
```

### Power Failure Recovery Test
```c
void test_power_failure_recovery(void) {
    // Simulate power failure during operation
    init_memory_manager();
    perform_power_failure_recovery();
    
    // Check that recovery completed successfully
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    printf("Power failure recoveries: %u\n", 
           tiered_state_machine.power_failure_recoveries);
    
    // Verify file integrity
    // Check /usr/qk/etc/sv/FC-1/history/ for files
    // Verify no files in corrupted/ directory
}
```

### Performance Test
```c
void test_performance(void) {
    imx_time_t start_time, end_time;
    
    // Measure processing overhead
    imx_time_get_time(&start_time);
    
    for (int i = 0; i < 1000; i++) {
        imx_time_t current_time;
        imx_time_get_time(&current_time);
        process_memory(current_time);
    }
    
    imx_time_get_time(&end_time);
    
    uint32_t elapsed = end_time - start_time;
    printf("1000 process_memory() calls took %u ms\n", elapsed);
    printf("Average overhead: %u us per call\n", elapsed);
}
```

## Monitoring and Maintenance

### Real-time Monitoring
```c
void monitor_system_status(void) {
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    
    printf("=== Memory Statistics ===\n");
    printf("Usage: %.1f%% (%u/%u sectors)\n", 
           stats->usage_percentage, stats->used_sectors, stats->total_sectors);
    printf("Peak Usage: %.1f%% (%u sectors)\n",
           stats->peak_usage_percentage, stats->peak_usage);
    printf("Allocations: %u, Deallocations: %u, Failures: %u\n",
           stats->allocation_count, stats->deallocation_count, stats->allocation_failures);
    printf("Fragmentation: %u%%\n", stats->fragmentation_level);
    
    printf("\n=== Tiered Storage Statistics ===\n");
    printf("State: %d\n", tiered_state_machine.state);
    printf("Files Created: %u, Deleted: %u\n",
           tiered_state_machine.total_files_created,
           tiered_state_machine.total_files_deleted);
    printf("Bytes Written: %llu\n", tiered_state_machine.total_bytes_written);
    printf("Power Failure Recoveries: %u\n",
           tiered_state_machine.power_failure_recoveries);
    printf("Pending Shutdown Sectors: %u\n",
           tiered_state_machine.pending_sectors_for_shutdown);
}
```

### Log File Analysis
```bash
# Monitor storage directory
watch -n 5 'ls -la /usr/qk/etc/sv/FC-1/history/'

# Check disk usage
df -h /usr/qk/etc/sv/FC-1/history/

# Monitor for errors
tail -f /var/log/imatrix.log | grep -E "(ERROR|WARNING|recovery|migration)"
```

### Maintenance Commands
```bash
# Clean old files (if needed)
find /usr/qk/etc/sv/FC-1/history/ -name "*.dat" -mtime +30 -delete

# Check for corrupted files
ls -la /usr/qk/etc/sv/FC-1/history/corrupted/

# Verify file integrity
for file in /usr/qk/etc/sv/FC-1/history/*.dat; do
    echo "Checking $file..."
    hexdump -C "$file" | head -2
done
```

## Troubleshooting Common Issues

### Issue: High CPU Usage
**Solution:**
```c
// Reduce processing frequency
#define MEMORY_PROCESS_INTERVAL_TIME    (2000)  // 2 seconds instead of 1

// Or reduce batch sizes
#define MAX_TSD_SECTORS_PER_ITERATION   (3)     // Smaller batches
```

### Issue: Disk Space Full
**Solution:**
```bash
# Check disk usage
df -h /usr/qk/etc/sv/FC-1/history/

# Clean old files manually if needed
find /usr/qk/etc/sv/FC-1/history/ -name "*.dat" -mtime +7 -delete
```

### Issue: Files in Corrupted Directory
**Solution:**
```bash
# Investigate corrupted files
ls -la /usr/qk/etc/sv/FC-1/history/corrupted/

# Check for patterns (power failure, disk issues, etc.)
# Consider manual data recovery if needed
```

## Summary

The tiered storage integration is designed to be simple and non-intrusive:

1. **Add 3 function calls** to your existing application
2. **No changes to existing memory code** required
3. **Automatic operation** with minimal configuration
4. **Robust error handling** and recovery

The system will automatically:
- Monitor RAM usage and migrate data when needed
- Handle power failures with complete recovery
- Manage disk space and file organization
- Provide comprehensive statistics and monitoring

For advanced use cases, extensive configuration options and monitoring capabilities are available.