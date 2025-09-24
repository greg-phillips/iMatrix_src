# Thread Safety Plan: data_store_info_t Structures in cs_ctrl

**Document Type:** Thread Safety Implementation Plan
**Date:** 2025-01-27
**Target:** `data_store_info_t` structures and related access functions
**Approach:** Mutex-based synchronization with proper initialization

---

## CURRENT THREADING ANALYSIS

### **Existing Threading Context**
Based on analysis of the codebase, the following components use threading:
- **CAN file sending** (`can_file_send.c`) - Uses `pthread_t` and `pthread_mutex_t`
- **Network processing** (`process_network.c`) - Thread-based network management
- **GPS/Location services** (`ubx_gps.c`) - Background GPS processing
- **Log notification** (`log_notification.c`) - Has `pthread_mutex_t lock`

### **Current Data Store Access Points**

#### **1. Sensor/Control Data Writing** (From multiple threads)
- **HAL sampling threads** → `imx_process_sample_value()` → `write_tsd_evt()`
- **CAN processing threads** → CAN event handlers → `write_tsd_evt()`
- **GPS threads** → Location updates → `write_tsd_evt()`
- **Network threads** → Status updates → `write_tsd_evt()`

#### **2. Upload System Data Reading** (From main thread)
- **iMatrix upload** → `imatrix_upload()` → `read_tsd_evt()`
- **Data transmission** → Packet building → Multiple `read_tsd_evt()` calls

#### **3. Data Management Operations** (From various contexts)
- **Memory manager** → `erase_tsd_evt()` → Sector management
- **Recovery system** → Data cleanup → `reset_csd_entry()`
- **Statistics** → Data counting → Direct access to counters

---

## CRITICAL RACE CONDITIONS IDENTIFIED

### **Race Condition 1: Read vs Write on data_store_info_t**

**Scenario:**
```c
Thread A (Sensor):                  Thread B (Upload):
write_tsd_evt(csb, csd, entry, value)    read_tsd_evt(csb, csd, entry, &data)
├── csd[entry].ds.count++               ├── Read from csd[entry].ds.start_sector
├── csd[entry].ds.end_sector update    ├── csd[entry].ds.start_index access
└── csd[entry].no_samples++             └── csd[entry].no_pending++
```

**Problem:** Concurrent modification of `ds` structure members can cause:
- **Inconsistent sector pointers** during sector allocation
- **Corrupted count values** during simultaneous read/write
- **Invalid memory access** if pointers change during read

### **Race Condition 2: Sector Chain Modification**

**Critical Code Path:** `memory_manager_tsd_evt.c:320-330`
```c
// Thread A modifying sector chain:
csd[entry].ds.end_sector = new_sector;     // ← WRITE
write_sector_next(old_sector, new_sector); // ← LINK

// Thread B reading sector chain:
sector = csd[entry].ds.start_sector;       // ← READ
while (sector != csd[entry].ds.end_sector) // ← READ (may see inconsistent state)
```

### **Race Condition 3: Counter Corruption**

**Multiple Counter Access:**
```c
// Thread A (Write):               Thread B (Read):               Thread C (Erase):
csd[i].no_samples++;             csd[i].no_pending++;           csd[i].no_samples--;
                                                                 csd[i].no_pending--;
```

**Problem:** Non-atomic counter operations can cause data corruption

---

## THREAD SAFETY IMPLEMENTATION PLAN

### **1. Mutex Architecture Design**

#### **Per-Entry Mutex Strategy**
```c
/* Add to common.h - extend control_sensor_data_t */
typedef struct control_sensor_data {
    /* ... existing fields ... */

    pthread_mutex_t data_store_mutex;    /* Protects ds structure and counters */

    /* ... rest of fields ... */
} control_sensor_data_t;
```

**Advantages:**
- **Fine-grained locking** - Each sensor/control entry independently protected
- **High concurrency** - Multiple entries can be accessed simultaneously
- **Minimal contention** - Only conflicts when same entry accessed

#### **Global Mutex Alternative (Simpler)**
```c
/* Add to memory_manager.h */
extern pthread_mutex_t data_store_global_mutex;

/* Global protection for all data store operations */
#define DATA_STORE_LOCK()   pthread_mutex_lock(&data_store_global_mutex)
#define DATA_STORE_UNLOCK() pthread_mutex_unlock(&data_store_global_mutex)
```

**Advantages:**
- **Simple implementation** - Single mutex protects everything
- **Easy to verify** - Clear critical sections
- **Lower memory overhead** - One mutex for entire system

### **2. Mutex Initialization Strategy**

#### **Static Initialization (Recommended)**
```c
/* In memory_manager.c - global mutex approach */
pthread_mutex_t data_store_global_mutex = PTHREAD_MUTEX_INITIALIZER;

/* Or for per-entry mutexes in initialization function */
void init_data_store_mutexes(void)
{
    for (imx_peripheral_type_t type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
    {
        imx_control_sensor_block_t *csb;
        control_sensor_data_t *csd;
        uint16_t no_items;

        imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

        for (uint16_t i = 0; i < no_items; i++)
        {
            pthread_mutex_init(&csd[i].data_store_mutex, NULL);
        }
    }
}
```

#### **Dynamic Initialization with Error Handling**
```c
imx_result_t init_data_store_thread_safety(void)
{
    int result = pthread_mutex_init(&data_store_global_mutex, NULL);
    if (result != 0)
    {
        imx_cli_log_printf("CRITICAL: Failed to initialize data store mutex: %d\r\n", result);
        return IMX_FAILED;
    }

    imx_cli_log_printf("Data store thread safety initialized\r\n");
    return IMX_SUCCESS;
}
```

### **3. Critical Section Protection**

#### **Protected Write Operations**
```c
/* Modify write_tsd_evt_time() in memory_manager_tsd_evt.c */
void write_tsd_evt_time(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                       uint16_t entry, uint32_t value, uint32_t utc_time)
{
    /* Input validation first (before locking) */
    if (csb == NULL || csd == NULL) {
        return;
    }

    DATA_STORE_LOCK();  /* ← CRITICAL SECTION START */

    /* All existing write logic here - protected */

    /* Sector allocation */
    if (csd[entry].ds.start_sector == 0 && csd[entry].ds.end_sector == 0) {
        /* First allocation - protected by mutex */
        platform_sector_t first_sector = get_sector();
        csd[entry].ds.start_sector = first_sector;
        csd[entry].ds.end_sector = first_sector;
        csd[entry].ds.start_index = 0;
        csd[entry].ds.count = 0;
    }

    /* Check if new sector needed - protected */
    if (need_new_sector) {
        platform_sector_t new_sector = get_sector();
        write_sector_next(csd[entry].ds.end_sector, new_sector);
        csd[entry].ds.end_sector = new_sector;
        csd[entry].ds.count = 0;
    }

    /* Write data and update counters - protected */
    write_data_to_sector(value, utc_time);
    csd[entry].ds.count++;
    csd[entry].no_samples++;

    DATA_STORE_UNLOCK();  /* ← CRITICAL SECTION END */
}
```

#### **Protected Read Operations**
```c
/* Modify read_tsd_evt() in memory_manager_tsd_evt.c */
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value)
{
    /* Input validation first (before locking) */
    if (csb == NULL || csd == NULL || value == NULL) {
        return;
    }

    DATA_STORE_LOCK();  /* ← CRITICAL SECTION START */

    /* Check data availability - protected */
    if (csd[entry].no_samples == 0) {
        *value = 0;
        DATA_STORE_UNLOCK();
        return;
    }

    /* Access sector and index - protected */
    platform_sector_t sector = csd[entry].ds.start_sector;
    uint16_t index = csd[entry].ds.start_index;

    /* Read data from storage - protected */
    imx_memory_error_t result = read_data_from_sector(sector, index, value);

    /* Update pending counter - protected */
    if (result == IMX_MEMORY_SUCCESS) {
        csd[entry].no_pending++;
    }

    DATA_STORE_UNLOCK();  /* ← CRITICAL SECTION END */
}
```

#### **Protected Erase Operations**
```c
/* Modify erase_tsd_evt() in memory_manager_tsd_evt.c */
void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry)
{
    if (csb == NULL || csd == NULL) {
        return;
    }

    DATA_STORE_LOCK();  /* ← CRITICAL SECTION START */

    /* Check if anything to erase - protected */
    if (csd[entry].no_pending == 0) {
        DATA_STORE_UNLOCK();
        return;
    }

    /* Erase loop with pointer advancement - protected */
    for (; csd[entry].no_pending > 0; csd[entry].no_pending--)
    {
        /* Advance start pointer - protected */
        if (csb[entry].sample_rate == 0) {
            csd[entry].ds.start_index += EVT_RECORD_SIZE;
        } else {
            csd[entry].ds.start_index += TSD_RECORD_SIZE;
        }

        /* Sector management - protected */
        if (sector_transition_needed) {
            free_sector(csd[entry].ds.start_sector);
            csd[entry].ds.start_sector = next_sector;
            csd[entry].ds.start_index = 0;
        }

        /* Update counters - protected */
        csd[entry].no_samples--;
    }

    DATA_STORE_UNLOCK();  /* ← CRITICAL SECTION END */
}
```

### **4. Initialization Integration**

#### **System Initialization Sequence**
```c
/* Add to memory_manager.c initialization */
imx_result_t imx_memory_manager_init(void)
{
    /* Initialize thread safety first */
    if (init_data_store_thread_safety() != IMX_SUCCESS) {
        return IMX_FAILED;
    }

    /* Continue with existing initialization */
    /* ... existing memory manager init code ... */

    return IMX_SUCCESS;
}
```

#### **Cleanup on Shutdown**
```c
void imx_memory_manager_cleanup(void)
{
    /* Cleanup data store thread safety */
    pthread_mutex_destroy(&data_store_global_mutex);

    /* Continue with existing cleanup */
    /* ... existing cleanup code ... */
}
```

---

## LOCKING STRATEGY ANALYSIS

### **Recommended Approach: Global Mutex**

**Rationale:**
1. **Simplicity** - Single mutex is easier to implement and debug
2. **Correctness** - Lower chance of deadlocks or race conditions
3. **Embedded system appropriate** - Lower memory overhead
4. **Clear critical sections** - Easy to identify protected regions

#### **Global Mutex Implementation**
```c
/* Add to memory_manager.h */
#include <pthread.h>

extern pthread_mutex_t data_store_global_mutex;

/* Thread-safe data store access macros */
#define DATA_STORE_LOCK() do { \
    int lock_result = pthread_mutex_lock(&data_store_global_mutex); \
    if (lock_result != 0) { \
        imx_cli_log_printf("ERROR: Data store lock failed: %d\r\n", lock_result); \
    } \
} while(0)

#define DATA_STORE_UNLOCK() do { \
    int unlock_result = pthread_mutex_unlock(&data_store_global_mutex); \
    if (unlock_result != 0) { \
        imx_cli_log_printf("ERROR: Data store unlock failed: %d\r\n", unlock_result); \
    } \
} while(0)

/* Initialization function */
imx_result_t init_data_store_thread_safety(void);
void cleanup_data_store_thread_safety(void);
```

### **Alternative: Per-Entry Mutex (Higher Performance)**

**For high-concurrency scenarios:**
```c
/* Extend control_sensor_data_t in common.h */
typedef struct control_sensor_data {
    /* ... existing fields ... */

    #ifdef LINUX_PLATFORM
    pthread_mutex_t entry_mutex;           /* Per-entry protection */
    #endif

    /* ... rest of fields ... */
} control_sensor_data_t;

/* Access macros */
#define ENTRY_LOCK(csd, entry) pthread_mutex_lock(&csd[entry].entry_mutex)
#define ENTRY_UNLOCK(csd, entry) pthread_mutex_unlock(&csd[entry].entry_mutex)
```

---

## SPECIFIC FUNCTION MODIFICATIONS

### **1. write_tsd_evt_time() - High Priority**

**Current Race Conditions:**
- Sector allocation (`csd[entry].ds.start_sector = first_sector`)
- Sector linking (`csd[entry].ds.end_sector = new_sector`)
- Counter updates (`csd[entry].no_samples++`)
- Index management (`csd[entry].ds.count++`)

**Thread-Safe Implementation:**
```c
void write_tsd_evt_time(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                       uint16_t entry, uint32_t value, uint32_t utc_time)
{
    /* Input validation before locking */
    if (csb == NULL) {
        imx_cli_log_printf("ERROR: write_tsd_evt_time - csb pointer is NULL\r\n");
        return;
    }

    if (csd == NULL) {
        imx_cli_log_printf("ERROR: write_tsd_evt_time - csd pointer is NULL\r\n");
        return;
    }

    DATA_STORE_LOCK();  /* ← PROTECT ENTIRE OPERATION */

    /* Original implementation here - now thread-safe */
    /* All ds structure modifications protected */

    DATA_STORE_UNLOCK();
}
```

### **2. read_tsd_evt() - High Priority**

**Current Race Conditions:**
- Reading sector pointers while they're being modified
- Accessing `start_index` during pointer advancement
- Counter increment (`no_pending++`) during concurrent operations

**Thread-Safe Implementation:**
```c
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value)
{
    /* Input validation before locking */
    if (csb == NULL || csd == NULL || value == NULL) {
        return;
    }

    DATA_STORE_LOCK();  /* ← PROTECT ENTIRE OPERATION */

    /* Check data availability */
    if (csd[entry].no_samples == 0) {
        *value = 0;
        DATA_STORE_UNLOCK();
        return;
    }

    /* Access storage pointers - now protected */
    platform_sector_t sector = csd[entry].ds.start_sector;
    uint16_t index = csd[entry].ds.start_index;

    /* Read data from sector */
    imx_memory_error_t result = read_data_from_sector(sector, index, value);

    /* Update counter - protected */
    if (result == IMX_MEMORY_SUCCESS) {
        csd[entry].no_pending++;
    }

    DATA_STORE_UNLOCK();
}
```

### **3. erase_tsd_evt() - High Priority**

**Current Race Conditions:**
- Sector pointer advancement during reads
- Counter decrements during concurrent access
- Sector deallocation during active reads

**Thread-Safe Implementation:**
```c
void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry)
{
    if (csb == NULL || csd == NULL) {
        return;
    }

    DATA_STORE_LOCK();  /* ← PROTECT ENTIRE OPERATION */

    /* Check pending data */
    if (csd[entry].no_pending == 0) {
        DATA_STORE_UNLOCK();
        return;
    }

    /* Erasure loop - all pointer operations protected */
    for (; csd[entry].no_pending > 0; csd[entry].no_pending--)
    {
        /* Advance pointers - protected */
        if (csb[entry].sample_rate == 0) {
            csd[entry].ds.start_index += EVT_RECORD_SIZE;
        } else {
            csd[entry].ds.start_index += TSD_RECORD_SIZE;
        }

        /* Sector management - protected */
        if (sector_needs_release) {
            platform_sector_t next_sector = get_next_sector(csd[entry].ds.start_sector);
            free_sector(csd[entry].ds.start_sector);
            csd[entry].ds.start_sector = next_sector;
            csd[entry].ds.start_index = 0;
        }

        /* Counter updates - protected */
        csd[entry].no_samples--;
    }

    DATA_STORE_UNLOCK();
}
```

### **4. High-Level Access Functions**

#### **Thread-Safe imx_process_sample_value()**
```c
/* In hal_sample_common.c */
void imx_process_sample_value(imx_control_sensor_block_t *csb,
                             control_sensor_data_t *csd,
                             imx_data_32_t *sampled_value,
                             uint16_t index,
                             imx_time_t current_time)
{
    /* Validate inputs before locking */
    if (csb == NULL || csd == NULL || sampled_value == NULL) {
        return;
    }

    DATA_STORE_LOCK();  /* ← PROTECT SAMPLE PROCESSING */

    /* Update max value if needed - protected */
    imx_update_max_value(csb, csd, sampled_value, index);

    /* Apply calibration - protected */
    imx_apply_calibration(csb, csd, index);

    /* Check warning levels - protected */
    imx_check_warning_levels(csb, csd, index);

    /* Check percentage change - protected */
    imx_check_percent_change_wrapper(csb, csd, index);

    /* Write to storage if conditions met - protected */
    if (should_store_sample) {
        write_tsd_evt(csb, csd, index, sampled_value->uint_32bit, false);
    }

    DATA_STORE_UNLOCK();
}
```

---

## IMPLEMENTATION ROADMAP

### **Phase 1: Core Infrastructure (Day 1)**

#### **Add Mutex Declaration**
```c
/* File: memory_manager.h */
#ifdef LINUX_PLATFORM
#include <pthread.h>
extern pthread_mutex_t data_store_global_mutex;
extern bool data_store_thread_safety_initialized;

/* Thread safety functions */
imx_result_t init_data_store_thread_safety(void);
void cleanup_data_store_thread_safety(void);

/* Protection macros */
#define DATA_STORE_LOCK() pthread_mutex_lock(&data_store_global_mutex)
#define DATA_STORE_UNLOCK() pthread_mutex_unlock(&data_store_global_mutex)
#else
/* No threading on embedded platforms */
#define DATA_STORE_LOCK()
#define DATA_STORE_UNLOCK()
#endif
```

#### **Add Mutex Implementation**
```c
/* File: memory_manager.c */
#ifdef LINUX_PLATFORM
pthread_mutex_t data_store_global_mutex = PTHREAD_MUTEX_INITIALIZER;
bool data_store_thread_safety_initialized = true;  /* Static initializer used */

imx_result_t init_data_store_thread_safety(void)
{
    /* Already initialized statically */
    imx_cli_log_printf("Data store thread safety enabled (static initialization)\r\n");
    return IMX_SUCCESS;
}

void cleanup_data_store_thread_safety(void)
{
    if (data_store_thread_safety_initialized) {
        pthread_mutex_destroy(&data_store_global_mutex);
        data_store_thread_safety_initialized = false;
        imx_cli_log_printf("Data store thread safety cleaned up\r\n");
    }
}
#endif
```

### **Phase 2: Core Functions (Day 2)**

#### **Priority Order:**
1. **`write_tsd_evt_time()`** - Highest priority (data corruption risk)
2. **`read_tsd_evt()`** - High priority (upload system dependency)
3. **`erase_tsd_evt()`** - High priority (data loss prevention)
4. **`reset_csd_entry()`** - Medium priority (cleanup operations)

### **Phase 3: High-Level Functions (Day 3)**

#### **Protected High-Level Operations:**
1. **`imx_process_sample_value()`** - Sensor data processing
2. **Upload system functions** - Already partially protected in our fix
3. **Memory management functions** - Sector allocation/deallocation
4. **Statistics functions** - Data counting and reporting

### **Phase 4: Validation (Day 4)**

#### **Thread Safety Testing:**
```c
/* Test concurrent access */
void test_concurrent_data_access(void)
{
    /* Create multiple threads accessing same data structures */
    pthread_t writer_thread, reader_thread, eraser_thread;

    /* Writer thread - continuous data writing */
    pthread_create(&writer_thread, NULL, continuous_write_test, NULL);

    /* Reader thread - continuous data reading */
    pthread_create(&reader_thread, NULL, continuous_read_test, NULL);

    /* Eraser thread - periodic data cleanup */
    pthread_create(&eraser_thread, NULL, periodic_erase_test, NULL);

    /* Run for extended period */
    sleep(60);

    /* Validate data integrity */
    if (validate_no_corruption()) {
        printf("✅ Thread safety validation PASSED\r\n");
    } else {
        printf("❌ Thread safety validation FAILED\r\n");
    }
}
```

---

## DEADLOCK PREVENTION

### **Locking Order Rules**

#### **Rule 1: Single Global Mutex**
- **No nested locking** - DATA_STORE_LOCK() never called within critical section
- **Short critical sections** - Minimize time holding mutex
- **No blocking operations** - No network I/O or file operations while locked

#### **Rule 2: Input Validation Before Locking**
```c
/* CORRECT: Validate first, then lock */
if (csb == NULL || csd == NULL) {
    return;  /* Return without locking */
}
DATA_STORE_LOCK();

/* INCORRECT: Lock before validation */
DATA_STORE_LOCK();
if (csb == NULL || csd == NULL) {
    /* Would need to unlock here - error prone */
    DATA_STORE_UNLOCK();
    return;
}
```

#### **Rule 3: Error Handling**
```c
/* Always unlock on error paths */
DATA_STORE_LOCK();

if (error_condition) {
    imx_cli_log_printf("Error occurred\r\n");
    DATA_STORE_UNLOCK();  /* ← CRITICAL: Always unlock */
    return;
}

/* Normal processing */
DATA_STORE_UNLOCK();
```

---

## PERFORMANCE CONSIDERATIONS

### **Lock Contention Minimization**

#### **Reduce Critical Section Size:**
```c
/* BAD: Large critical section */
DATA_STORE_LOCK();
prepare_data();           /* Long operation */
validate_data();          /* Long operation */
write_to_storage();       /* Quick operation */
DATA_STORE_UNLOCK();

/* GOOD: Minimal critical section */
prepare_data();           /* Outside lock */
validate_data();          /* Outside lock */
DATA_STORE_LOCK();
write_to_storage();       /* Only storage access protected */
DATA_STORE_UNLOCK();
```

#### **Batch Operations:**
```c
/* Batch multiple operations under single lock */
DATA_STORE_LOCK();
for (int i = 0; i < batch_size; i++) {
    write_single_sample(samples[i]);
}
DATA_STORE_UNLOCK();
```

### **Memory Access Optimization**

#### **Local Variable Caching:**
```c
/* Cache structure values to reduce memory access under lock */
DATA_STORE_LOCK();

/* Read once under lock */
platform_sector_t local_sector = csd[entry].ds.start_sector;
uint16_t local_index = csd[entry].ds.start_index;

DATA_STORE_UNLOCK();

/* Use local copies for processing */
process_data_using_local_copies(local_sector, local_index);
```

---

## IMPLEMENTATION CHECKLIST

### **Phase 1: Infrastructure Setup**
```
□ Add pthread.h include to memory_manager.h
□ Declare global mutex with PTHREAD_MUTEX_INITIALIZER
□ Add DATA_STORE_LOCK/UNLOCK macros
□ Add initialization and cleanup functions
□ Add thread safety to memory manager initialization
```

### **Phase 2: Core Function Protection**
```
□ Protect write_tsd_evt_time() with mutex
□ Protect read_tsd_evt() with mutex
□ Protect erase_tsd_evt() with mutex
□ Protect reset_csd_entry() with mutex
□ Add error handling for lock failures
```

### **Phase 3: High-Level Function Protection**
```
□ Protect imx_process_sample_value() with mutex
□ Protect sector allocation functions
□ Protect memory manager utility functions
□ Update statistics functions for thread safety
```

### **Phase 4: Testing and Validation**
```
□ Create concurrent access test cases
□ Validate no deadlocks occur
□ Test performance impact
□ Verify data integrity under concurrent load
□ Test error handling paths
```

---

## RISK ASSESSMENT

### **Implementation Risks**

#### **Risk 1: Deadlock**
**Mitigation:**
- Use single global mutex (no lock ordering issues)
- Keep critical sections small
- Never call blocking functions while locked

#### **Risk 2: Performance Impact**
**Mitigation:**
- Minimize critical section size
- Use local variable caching
- Batch operations when possible

#### **Risk 3: Platform Compatibility**
**Mitigation:**
- Use `#ifdef LINUX_PLATFORM` guards
- Provide no-op macros for embedded platforms
- Test on both platforms

### **Benefits**

#### **Data Integrity Protection:**
- **Prevents sector pointer corruption** during concurrent access
- **Protects counter consistency** (no_samples, no_pending)
- **Ensures atomic sector operations** (allocation, linking, deallocation)

#### **System Reliability:**
- **Eliminates race conditions** in data store access
- **Prevents memory corruption** from concurrent modifications
- **Enables safe multi-threaded operation**

---

## TESTING STRATEGY

### **Unit Tests for Thread Safety**

```c
/* File: test_scripts/test_thread_safety.c */

void test_concurrent_write_read(void)
{
    /* Test simultaneous write and read operations */
    /* Validate data consistency */
}

void test_concurrent_read_erase(void)
{
    /* Test reading while erasure is occurring */
    /* Validate no data corruption */
}

void test_sector_allocation_concurrency(void)
{
    /* Test multiple threads triggering sector allocation */
    /* Validate proper sector linking */
}
```

### **Stress Testing**

```c
void stress_test_data_store_threading(void)
{
    /* Run multiple threads for extended periods */
    /* High-frequency operations on same data structures */
    /* Validate system stability and data integrity */
}
```

---

## CONCLUSION

This thread safety plan addresses all identified race conditions in `data_store_info_t` access using a simple, robust mutex-based approach. The implementation prioritizes correctness and simplicity over maximum performance, making it suitable for the embedded IoT context of the iMatrix system.

**Key Benefits:**
✅ **Eliminates all identified race conditions**
✅ **Simple global mutex strategy** (easy to implement and debug)
✅ **Proper initialization** with static PTHREAD_MUTEX_INITIALIZER
✅ **Platform compatibility** with embedded systems
✅ **Minimal performance impact** with optimized critical sections

The plan ensures that concurrent access to sensor data structures is safe while maintaining the system's performance characteristics.