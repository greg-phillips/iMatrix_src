# iMatrix Upload System Operation Guide for Test Developers

**Document Type:** Technical Operation Guide
**Audience:** Test Developers and QA Engineers
**Date:** 2025-01-27
**Purpose:** Deep understanding of iMatrix upload system internals for effective testing

---

## SYSTEM OVERVIEW

The iMatrix upload system is responsible for collecting sensor and control data from local storage and transmitting it to the cloud platform using CoAP (Constrained Application Protocol) over UDP. Understanding its operation is critical for testing data integrity and preventing data loss.

### **Key Components:**
- **Data Stores**: Memory sectors holding sensor readings
- **Upload State Machine**: Controls the upload process flow
- **CoAP Messaging**: Handles network communication
- **Memory Management**: Manages storage allocation and cleanup

---

## DATA STORAGE ARCHITECTURE

### **Core Data Structure: `control_sensor_data_t`**

**Location:** `/home/greg/iMatrix/iMatrix_Client/iMatrix/common.h`

```c
typedef struct control_sensor_data {
    imx_utc_time_ms_t last_sample_time;     /* Timestamp of last sample */
    uint16_t no_samples;                    /* TOTAL samples available in storage */
    uint16_t no_pending;                    /* Samples read for upload (marked for erasure) */
    uint32_t errors;                        /* Error count */
    imx_time_t last_poll_time;             /* Last polling time */
    imx_time_t condition_started_time;      /* When current condition started */
    imx_data_32_t last_raw_value;          /* Most recent raw reading */
    imx_data_32_t last_value;              /* Most recent processed value */
    data_store_info_t ds;                  /* Storage sector information */

    /* Status flags (bitfields) */
    unsigned int error                  : 8;    /* Current error state */
    unsigned int last_error             : 8;    /* Previous error state */
    unsigned int update_now             : 1;    /* Force immediate update */
    unsigned int warning                : 2;    /* Warning level */
    unsigned int last_warning           : 2;    /* Previous warning level */
    unsigned int percent_changed        : 1;    /* Value change threshold met */
    unsigned int active                 : 1;    /* Entry is active */
    unsigned int valid                  : 1;    /* Has valid data */
    unsigned int sent_first_reading     : 1;    /* First reading flag */
    unsigned int sensor_auto_updated    : 1;    /* Auto-update enabled */
    unsigned int reset_max_value        : 1;    /* Reset maximum value */
    unsigned int reserved               : 5;    /* Reserved bits */
} control_sensor_data_t;
```

### **Storage Sector Structure: `data_store_info_t`**

```c
typedef struct {
    platform_sector_t start_sector;    /* First sector of data */
    platform_sector_t end_sector;      /* Last sector of data */
    uint16_t start_index;              /* Current read position within sector */
    uint16_t count;                    /* Items in current sector */
} data_store_info_t;
```

### **Critical Counter Semantics:**

#### **`no_samples`**: Total Data Available
- **Incremented**: When `write_tsd_evt()` stores new sensor readings
- **Decremented**: When `erase_tsd_evt()` physically removes data
- **Represents**: Total sensor readings available for upload

#### **`no_pending`**: Data Marked for Erasure
- **Incremented**: When `read_tsd_evt()` reads data for potential upload
- **Decremented**: When data is actually erased or reverted
- **Represents**: Samples that have been read and are "pending erasure"

#### **Critical Understanding:**
```
no_pending != samples_in_packet

no_pending = "samples read from storage"
packet_contents = "subset of read samples that fit in packet"
```

---

## DATA FLOW OPERATION

### **1. Data Writing Process**

**Function:** `write_tsd_evt()` in `memory_manager_tsd_evt.c`

**Process:**
```
Sensor Reading → write_tsd_evt() → Storage Sector
     ↓                ↓               ↓
New measurement   Validates space   Stored in sector
                  Allocates new     Updates counters
                  sector if needed
```

**Counter Updates:**
```c
csd[entry].no_samples++;        /* Total available increments */
csd[entry].no_pending;          /* Unchanged (0) */
```

**Storage Management:**
- Data written to `end_sector` at position `count`
- New sectors allocated when current sector fills
- Sector linking maintained for sequential access

### **2. Data Reading Process**

**Function:** `read_tsd_evt()` in `memory_manager_tsd_evt.c`

**Process:**
```
Upload Request → read_tsd_evt() → Data Retrieved
     ↓              ↓               ↓
Packet building   Reads from      Sample returned
                  start_sector    Counters updated
                  at start_index
```

**Counter Updates:**
```c
csd[entry].no_pending++;        /* Pending increments (CRITICAL!) */
csd[entry].no_samples;          /* Unchanged - data still exists */
```

**Storage Pointer Management:**
- Reads from `start_sector` at `start_index`
- **Does NOT advance start_index** during read
- **Pointer advancement happens during erasure**

### **3. Upload State Machine Flow**

**Function:** `imatrix_upload()` in `imatrix_upload.c`

```
IMATRIX_INIT
    ↓ (check timing)
IMATRIX_CHECK_FOR_PENDING
    ↓ (data available)
IMATRIX_GET_DNS
    ↓ (resolve server IP)
IMATRIX_GET_PACKET
    ↓ (allocate message buffer)
IMATRIX_LOAD_SAMPLES_PACKET  ← CRITICAL: Data reading happens here
    ↓ (build packet with samples)
IMATRIX_UPLOAD_WAIT_RSP
    ↓ (wait for server acknowledgment)
IMATRIX_UPLOAD_COMPLETE      ← CRITICAL: Data erasure happens here
```

### **4. Packet Building Process**

**Location:** `imatrix_upload.c:1037-1560`

**Detailed Flow:**
```c
1. Initialize packet contents tracking
   memset(&packet_contents, 0, sizeof(packet_contents));
   packet_contents.in_use = true;

2. Loop through all peripheral types (Controls, Sensors, Variables)
   for (type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)

3. For each type, get data structures
   imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);

4. Loop through all entries of this type
   for (uint16_t i = 0; i < no_items; i++)

5. Check if entry has data to send
   if (csd[i].no_samples > 0)

6. Calculate how many samples fit in remaining packet space
   no_samples = min(csd[i].no_samples, packet_space_available);

7. Read samples and add to packet
   for (uint16_t j = 0; j < no_samples; j++) {
       read_tsd_evt(csb, csd, i, &sample);           /* ← no_pending++ */
       packet_contents.entry_counts[type][i]++;      /* ← Track for erasure */
       add_sample_to_packet(sample);
   }

8. Continue until packet full or no more data
```

**Critical Testing Point:** After step 7, `no_pending` includes ALL read samples, but `packet_contents` tracks only what was actually added to the packet.

---

## ACKNOWLEDGMENT AND ERASURE PROCESS

### **Response Handler Flow**

**Function:** `_imatrix_upload_response_hdl()` in `imatrix_upload.c:257-312`

#### **Success Path (CoAP Class 2 Response):**
```c
if (result && packet_contents.in_use)
{
    /* NEW FIX: Erase only transmitted samples */
    for( type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++ )
    {
        imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);
        for (uint16_t i = 0; i < no_items; i++)
        {
            if (packet_contents.entry_counts[type][i] > 0)
            {
                /* Erase exactly this many samples */
                erase_specific_samples(csb, csd, i, packet_contents.entry_counts[type][i]);
            }
        }
    }
}
```

#### **Failure Path (Error Response or Timeout):**
```c
else if (!result && packet_contents.in_use)
{
    /* NEW FIX: Properly revert read operations */
    revert_packet_reads();
}
```

### **Erasure Implementation**

**Function:** `erase_specific_samples()` in `imatrix_upload.c:2525-2546`

**Process:**
```c
1. Save original pending count
   uint16_t original_pending = csd[entry].no_pending;

2. Set pending to exact count to erase
   csd[entry].no_pending = count;

3. Call existing erase function
   erase_tsd_evt(csb, csd, entry);  /* Erases exactly 'count' samples */

4. Restore remaining pending count
   csd[entry].no_pending = original_pending - count;
```

**Storage Operations in `erase_tsd_evt()`:**
```c
for (; csd[entry].no_pending > 0; csd[entry].no_pending--)
{
    /* Advance read pointer */
    csd[entry].ds.start_index += RECORD_SIZE;

    /* Decrement total available */
    csd[entry].no_samples--;

    /* Manage sector transitions when sector becomes empty */
    if (start_index exceeds sector capacity) {
        free_sector(current_sector);
        advance_to_next_sector();
    }
}
```

---

## DATA TYPES AND STORAGE FORMATS

### **Time Series Data (TSD) vs Event Data (EVT)**

#### **TSD (Time Series Data):**
- **Fixed sample rate** (e.g., every 1000ms)
- **Sample size**: `TSD_RECORD_SIZE` (typically 4 bytes)
- **Storage**: Sequential values with implied timestamps
- **Use case**: Temperature readings, voltage measurements

#### **EVT (Event Data):**
- **Event-driven** (csb[entry].sample_rate == 0)
- **Sample size**: `EVT_RECORD_SIZE` (typically 8 bytes: timestamp + value)
- **Storage**: Timestamp + value pairs
- **Use case**: Alarms, state changes, error conditions

### **Sector Organization**

```
Sector Structure:
┌─────────────────────────────────────────────────────────────┐
│ evt_tsd_sector_t header                                     │
├─────────────────────────────────────────────────────────────┤
│ Sample 1 (TSD: 4 bytes, EVT: 8 bytes)                     │
│ Sample 2                                                    │
│ Sample 3                                                    │
│ ...                                                         │
│ Sample N (up to NO_TSD_ENTRIES_PER_SECTOR)                │
├─────────────────────────────────────────────────────────────┤
│ next_sector pointer                                         │
│ CRC checksum                                               │
└─────────────────────────────────────────────────────────────┘
```

**Constants:**
- `NO_TSD_ENTRIES_PER_SECTOR`: Maximum TSD samples per sector
- `NO_EVT_ENTRIES_PER_SECTOR`: Maximum EVT samples per sector
- `TSD_RECORD_SIZE`: Bytes per TSD sample
- `EVT_RECORD_SIZE`: Bytes per EVT sample (timestamp + value)

---

## PERIPHERAL TYPE SYSTEM

### **Peripheral Type Enumeration**
```c
typedef enum {
    IMX_CONTROLS = 0,    /* Controllable outputs (relays, actuators) */
    IMX_SENSORS = 1,     /* Sensor inputs (temperature, pressure, etc.) */
    IMX_VARIABLES = 2,   /* Internal variables and calculations */
    IMX_NO_PERIPHERAL_TYPES
} imx_peripheral_type_t;
```

### **Data Structure Access**

**Function:** `imx_set_csb_vars()` in `imatrix_interface.c:1749`

**Purpose:** Get pointers to data structures for a specific peripheral type

```c
void imx_set_csb_vars(imx_peripheral_type_t type,
                     imx_control_sensor_block_t **csb,    /* Configuration blocks */
                     control_sensor_data_t **csd,         /* Data storage info */
                     uint16_t *no_items,                  /* Number of entries */
                     device_updates_t *device_updates)    /* Update tracking */
```

**What `no_items` Represents:**
- **For IMX_CONTROLS**: `device_config.no_controls`
- **For IMX_SENSORS**: `device_config.no_sensors`
- **For IMX_VARIABLES**: `device_config.no_variables`

**Critical for Testing:** `no_items` is the TOTAL number of entries of that type, not the number with data or the number being uploaded.

---

## UPLOAD OPERATION DEEP DIVE

### **Data Discovery Process**

**Location:** `imatrix_upload.c:564-850` (`IMATRIX_CHECK_FOR_PENDING`)

**Process:**
```c
/* Scan all peripheral types for data ready to upload */
for (type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
{
    imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);

    for (uint16_t i = 0; i < no_items; i++)
    {
        /* Check for various upload triggers */
        if (csd[i].no_samples != 0)                    /* Has data */
        {
            device_updates.send_batch = true;          /* Mark for upload */
        }

        if (csd[i].error != csd[i].last_error)        /* Error state changed */
        {
            imatrix.imx_error = true;                  /* Flag error upload */
        }

        if (csd[i].warning != csd[i].last_warning)    /* Warning state changed */
        {
            imatrix.imx_warning = true;                /* Flag warning upload */
        }
    }
}
```

**Key for Testing:** System scans ALL entries but only uploads those with `no_samples > 0` or state changes.

### **Packet Building Process**

**Location:** `imatrix_upload.c:1037-1560` (`IMATRIX_LOAD_SAMPLES_PACKET`)

#### **Phase 1: Packet Initialization**
```c
/* Initialize packet contents tracking (NEW FIX) */
memset(&packet_contents, 0, sizeof(packet_contents));
packet_contents.in_use = true;

/* Get message buffer */
imatrix.msg = msg_get(packet_length);

/* Setup CoAP headers */
imx_setup_coap_sync_packet_header(imatrix.msg);
```

#### **Phase 2: Data Collection Loop**
```c
/* Loop through all peripheral types */
for (type = IMX_CONTROLS; ((type < IMX_NO_PERIPHERAL_TYPES) && (packet_full == false)); type++)
{
    imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);

    /* Loop through all entries of this type */
    for (uint16_t i = 0; ((i < no_items) && (packet_full == false)); i++)
    {
        if (csd[i].no_samples > 0)  /* Entry has data */
        {
            /* Calculate how many samples fit in remaining packet space */
            remaining_data_length = coap_msg_data_size(&imatrix.msg->coap) - imatrix.msg->coap.msg_length;

            if (remaining_data_length >= (sizeof(header_t) + payload_base_length + sample_length))
            {
                /* Calculate samples that fit */
                if (remaining_data_length >= (sizeof(header_t) + payload_base_length + (sample_length * csd[i].no_samples)))
                {
                    no_samples = csd[i].no_samples;     /* All samples fit */
                }
                else
                {
                    no_samples = (remaining_data_length - sizeof(header_t) - payload_base_length) / sample_length;
                    packet_full = true;                  /* Packet will be full after this */
                }

                /* Read samples and add to packet */
                for (uint16_t j = 0; j < no_samples; j++)
                {
                    read_tsd_evt(csb, csd, i, &sample);               /* ← no_pending++ */
                    packet_contents.entry_counts[type][i]++;          /* ← Track for erasure (NEW FIX) */
                    add_sample_to_packet(sample);
                }
            }
        }
    }
}
```

**Critical Testing Points:**
1. **Packet size limits** determine how many samples fit
2. **`no_pending` increments** for every `read_tsd_evt()` call
3. **`packet_contents` tracks** only samples actually added to packet
4. **These two counts can differ** when packet size is limited

### **3. Network Transmission**

**Location:** `imatrix_upload.c:1557-1560`

```c
/* Send packet via CoAP */
coap_xmit_msg(imatrix.msg);
imatrix.msg = NULL;

/* Set state to wait for response */
imatrix.state = IMATRIX_UPLOAD_WAIT_RSP;
imx_upload_request_time = current_time;
imx_upload_completed = !packet_full;  /* Flag if more data pending */
```

### **4. Response Processing**

**Location:** `imatrix_upload.c:1561-1568` (`IMATRIX_UPLOAD_WAIT_RSP`)

**Timeout Handling:**
```c
if (imx_is_later(current_time, imx_upload_request_time + IMX_UPLOAD_REQUEST_TIMEOUT))
{
    /* 30-second timeout - call response handler with NULL */
    _imatrix_upload_response_hdl(NULL);
    icb.last_sent_time = imx_upload_request_time;
}
```

**Response Handler** (`_imatrix_upload_response_hdl()`):
```c
/* Determine if upload was successful */
bool result = (recv != NULL);
if (result && (MSG_CLASS(recv->coap.header.mode.udp.code) != 2)) {
    result = false;  /* Server error response */
}

/* NEW FIX: Use packet contents tracking for precise erasure */
if (result && packet_contents.in_use) {
    /* SUCCESS: Erase only transmitted samples */
    erase_only_transmitted_samples();
} else if (!result && packet_contents.in_use) {
    /* FAILURE: Revert read operations */
    revert_packet_reads();
}
```

---

## MEMORY MANAGEMENT INTERNALS

### **Sector Allocation System**

**Function:** `get_ram_sector_address()` in memory management

**Sector Types:**
- **RAM Sectors**: Fast access, limited quantity
- **Disk Sectors**: Larger capacity, slower access (spillover)
- **Sector Linking**: Sectors linked together for large datasets

**Sector Transition Logic:**
```c
/* When reading across sector boundaries */
if (((index / record_size) + 1) >= no_entries_per_sector)
{
    /* Move to next sector */
    sector = next_sector_from_current;
    index = 0;  /* Reset index in new sector */
}
```

### **Data Access Patterns**

#### **Sequential Read Access:**
```
start_sector:start_index → Sample 1
start_sector:start_index+1 → Sample 2
...
start_sector:start_index+N → Sample N
(if sector full) → next_sector:0 → Sample N+1
```

#### **Write Access:**
```
end_sector:count → New Sample
count++
(if sector full) → allocate new end_sector, count = 0
```

### **Storage State Diagram**
```
Empty Entry:
├── no_samples = 0
├── no_pending = 0
├── start_sector = end_sector
└── start_index = count = 0

Data Written:
├── no_samples++
├── no_pending = 0 (unchanged)
├── end_sector may advance
└── count increases

Data Read for Upload:
├── no_samples (unchanged)
├── no_pending++
├── start pointers unchanged
└── end pointers unchanged

Data Erased (Fixed Logic):
├── no_samples-- (for each erased)
├── no_pending-- (for each erased)
├── start_index advances
└── start_sector may advance
```

---

## TESTING IMPLICATIONS

### **Critical Test Scenarios**

#### **Scenario 1: Partial Upload Validation**
```
Test Setup:
1. Write 1000 samples to sensor entry 0
2. Force packet size limit to 100 samples
3. Execute upload with success response

Expected Results:
- packet_contents.entry_counts[IMX_SENSORS][0] = 100
- csd[0].no_pending should have been 100 during upload
- After erase: csd[0].no_samples = 900
- Remaining 900 samples should be accessible via read_tsd_evt()

Validation:
- Verify exactly 100 samples erased
- Verify 900 samples remain accessible
- Verify no other entries affected
```

#### **Scenario 2: Multi-Entry Upload**
```
Test Setup:
1. Write 500 samples to sensor 0, 300 to sensor 1, 200 to sensor 2
2. Force packet to take 100 from each sensor (300 total)
3. Execute upload with success response

Expected Results:
- packet_contents.entry_counts[IMX_SENSORS][0] = 100
- packet_contents.entry_counts[IMX_SENSORS][1] = 100
- packet_contents.entry_counts[IMX_SENSORS][2] = 100
- After erase: sensor 0 has 400, sensor 1 has 200, sensor 2 has 100

Critical Validation:
- Each sensor loses exactly what was transmitted
- No cross-contamination between sensors
- Total system data loss = total transmitted (300)
```

#### **Scenario 3: Failure Rollback**
```
Test Setup:
1. Write 800 samples to control entry 0
2. Start upload (reads 200 samples, no_pending = 200)
3. Simulate network timeout

Expected Results:
- revert_packet_reads() called
- csd[0].no_pending reduced by 200
- csd[0].no_samples unchanged (800)
- All 800 samples still accessible

Critical Validation:
- No data lost on failure
- Read pointers properly managed
- Subsequent uploads can access all data
```

### **Test Data Generation**

#### **Creating Test Data:**
```c
void create_test_data_pattern(imx_peripheral_type_t type, uint16_t entry, uint16_t count)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    /* Clear existing data */
    clear_entry_data(csd, entry);

    /* Write known test pattern */
    for (uint16_t i = 0; i < count; i++)
    {
        uint32_t test_value = (0x1000 << 16) | i;  /* Recognizable pattern */
        write_tsd_evt(csb, csd, entry, test_value, false);
    }

    printf("Created %u test samples in %s[%u] with pattern 0x1000XXXX\r\n",
           count, imx_peripheral_name(type), entry);
}
```

#### **Validating Test Data:**
```c
bool validate_test_data_pattern(imx_peripheral_type_t type, uint16_t entry, uint16_t expected_count)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    if (csd[entry].no_samples != expected_count)
    {
        printf("VALIDATION FAIL: Expected %u samples, found %u\r\n", expected_count, csd[entry].no_samples);
        return false;
    }

    /* Read a few samples to verify pattern */
    for (uint16_t i = 0; i < min(5, expected_count); i++)
    {
        uint32_t value;
        read_tsd_evt(csb, csd, entry, &value);

        uint32_t expected_pattern = (0x1000 << 16) | i;
        if (value != expected_pattern)
        {
            printf("VALIDATION FAIL: Sample %u pattern mismatch. Expected 0x%08X, got 0x%08X\r\n",
                   i, expected_pattern, value);
            csd[entry].no_pending -= (i + 1);  /* Restore pending count */
            return false;
        }
    }

    /* Restore pending count after validation reads */
    csd[entry].no_pending -= min(5, expected_count);

    return true;
}
```

---

## MOCK SYSTEM ARCHITECTURE

### **CoAP Message Mocking**

**Replace Real Network Functions:**
```c
/* During testing, replace real functions with mocks */
#ifdef TESTING_MODE
    #define coap_xmit_msg(msg) mock_coap_xmit_msg(msg)
    #define get_imatrix_ip_address(x) mock_get_ip_address(x)
#endif

/* Mock CoAP transmission */
void mock_coap_xmit_msg(message_t *msg)
{
    /* Store message for response simulation */
    store_pending_mock_message(msg);

    /* Schedule response based on test configuration */
    schedule_mock_response(get_mock_delay(), get_mock_response_type());
}

/* Mock response scheduling */
void schedule_mock_response(uint32_t delay_ms, mock_response_type_t type)
{
    /* After delay, trigger appropriate response */
    if (delay_ms == 0)
    {
        trigger_immediate_response(type);
    }
    else
    {
        schedule_delayed_response(delay_ms, type);
    }
}
```

### **State Machine Control for Testing**

```c
/* Force state machine into specific states for testing */
void force_upload_state(imatrix_upload_state_t state)
{
    extern imatrix_data_t imatrix;
    imatrix.state = state;
    printf("Forced upload state to %u for testing\r\n", state);
}

/* Get current state for validation */
imatrix_upload_state_t get_current_upload_state(void)
{
    extern imatrix_data_t imatrix;
    return imatrix.state;
}

/* Check if upload is waiting for response */
bool is_waiting_for_response(void)
{
    return (get_current_upload_state() == IMATRIX_UPLOAD_WAIT_RSP);
}
```

---

## DATA INTEGRITY VALIDATION METHODS

### **Before/After Comparison**

```c
typedef struct data_state_snapshot {
    uint16_t total_samples;
    uint16_t pending_samples;
    uint16_t sector_count;
    uint32_t first_sample_value;
    uint32_t last_sample_value;
    platform_sector_t start_sector;
    uint16_t start_index;
} data_state_snapshot_t;

/* Take comprehensive snapshot */
void take_data_state_snapshot(imx_peripheral_type_t type, uint16_t entry, data_state_snapshot_t *snapshot)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    snapshot->total_samples = csd[entry].no_samples;
    snapshot->pending_samples = csd[entry].no_pending;
    snapshot->start_sector = csd[entry].ds.start_sector;
    snapshot->start_index = csd[entry].ds.start_index;

    /* Read first and last accessible samples for validation */
    if (csd[entry].no_samples > 0)
    {
        uint32_t temp_value;

        /* Read first sample */
        read_tsd_evt(csb, csd, entry, &temp_value);
        snapshot->first_sample_value = temp_value;

        /* If more than one sample, read second to get pattern */
        if (csd[entry].no_samples > 1)
        {
            read_tsd_evt(csb, csd, entry, &temp_value);
            snapshot->last_sample_value = temp_value;
        }

        /* Restore pending count after validation reads */
        csd[entry].no_pending -= (csd[entry].no_samples > 1) ? 2 : 1;
    }
}
```

### **Data Accessibility Verification**

```c
/**
 * @brief Verify that data is accessible in expected order
 */
bool verify_data_order_integrity(imx_peripheral_type_t type, uint16_t entry, uint16_t expected_count)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    if (csd[entry].no_samples != expected_count)
    {
        printf("Count mismatch: expected %u, actual %u\r\n", expected_count, csd[entry].no_samples);
        return false;
    }

    /* Read a few samples to verify they're in expected order */
    uint16_t samples_to_check = min(10, expected_count);
    for (uint16_t i = 0; i < samples_to_check; i++)
    {
        uint32_t value;
        read_tsd_evt(csb, csd, entry, &value);

        /* Verify sample follows expected pattern */
        if (!is_valid_test_pattern(value, i))
        {
            printf("Sample order integrity failed at position %u\r\n", i);
            csd[entry].no_pending -= (i + 1);  /* Restore count */
            return false;
        }
    }

    /* Restore pending count */
    csd[entry].no_pending -= samples_to_check;

    return true;
}
```

---

## TEST FRAMEWORK INTEGRATION

### **Integration with Existing Test System**

**File:** `test_scripts/CMakeLists.txt` - Add new test target
```cmake
add_executable(data_loss_fix_test
    test_data_loss_fix.c
    mock_coap_responses.c
    data_integrity_validator.c
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

target_include_directories(data_loss_fix_test PRIVATE ${INCLUDE_DIRS})
target_link_libraries(data_loss_fix_test PRIVATE c pthread m rt)
```

### **Test Execution Script**

**File:** `test_scripts/run_data_loss_tests.sh`
```bash
#!/bin/bash

echo "Building data loss fix tests..."
cmake .
make data_loss_fix_test

if [ $? -ne 0 ]; then
    echo "❌ BUILD FAILED"
    exit 1
fi

echo "Running data loss fix validation..."
./data_loss_fix_test

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "🎉 DATA LOSS FIX VALIDATION SUCCESSFUL"
    echo "✅ Safe to use in development"
else
    echo "⚠️  DATA LOSS FIX VALIDATION FAILED"
    echo "❌ Additional fixes required"
fi

exit $TEST_RESULT
```

---

## DEBUGGING AND TROUBLESHOOTING

### **Debug Output Configuration**

**Enable Debug Logging:**
```c
/* Add to test compilation */
#define PRINT_DEBUGS_FOR_IMX_UPLOAD 1
#define LOGS_ENABLED(x) 1

/* This enables detailed debug output showing: */
// - Which samples are read for upload
// - Packet building progress
// - Erasure operations
// - Counter updates
```

**Key Debug Messages to Watch:**
```c
"[IMX Upload: Processing for: ..."     /* Shows what's being processed */
"Adding Data: @..."                    /* Shows samples added to packet */
"Erase EVT Entry: ..."                 /* Shows erasure operations */
"Erased exactly %u samples..."         /* Shows precise erasure (NEW) */
"Reverted %u read samples..."          /* Shows revert operations (NEW) */
```

### **Manual Inspection Tools**

**Data State Inspector:**
```c
void print_entry_state(imx_peripheral_type_t type, uint16_t entry)
{
    imx_control_sensor_block_t *csb;
    control_sensor_data_t *csd;
    uint16_t no_items;

    imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);

    printf("=== %s Entry %u State ===\r\n", imx_peripheral_name(type), entry);
    printf("Total Samples: %u\r\n", csd[entry].no_samples);
    printf("Pending Count: %u\r\n", csd[entry].no_pending);
    printf("Start Sector: %u, Index: %u\r\n", csd[entry].ds.start_sector, csd[entry].ds.start_index);
    printf("End Sector: %u, Count: %u\r\n", csd[entry].ds.end_sector, csd[entry].ds.count);
    printf("Enabled: %s\r\n", csb[entry].enabled ? "Yes" : "No");
    printf("Send to iMatrix: %s\r\n", csb[entry].send_imatrix ? "Yes" : "No");
}
```

**Packet Contents Inspector:**
```c
void print_packet_contents_state(void)
{
    printf("=== Packet Contents Tracking ===\r\n");
    printf("In Use: %s\r\n", packet_contents.in_use ? "Yes" : "No");

    for (imx_peripheral_type_t type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
    {
        printf("%s entries:\r\n", imx_peripheral_name(type));
        for (uint16_t i = 0; i < 10; i++)  /* Show first 10 entries */
        {
            if (packet_contents.entry_counts[type][i] > 0)
            {
                printf("  Entry %u: %u samples\r\n", i, packet_contents.entry_counts[type][i]);
            }
        }
    }
}
```

---

## CONCLUSION FOR TEST DEVELOPERS

### **Understanding the Fix**

**The Original Bug:**
- `erase_tsd_evt_pending_data(csb, csd, no_items)` erased ALL pending data
- `no_items` = total entries, not just entries with transmitted data
- Result: Massive data loss even on successful uploads

**The Fix:**
- `packet_contents.entry_counts[type][i]` tracks exactly what goes in each packet
- `erase_specific_samples()` erases only the tracked count
- Result: Perfect correlation between transmitted and erased data

### **Critical Testing Focus:**

1. **Validate packet tracking accuracy** - Does `packet_contents` exactly match packet?
2. **Verify precise erasure** - Are exactly the right samples erased?
3. **Check data preservation** - Do untransmitted samples remain accessible?
4. **Test failure handling** - Are read operations properly reverted?

### **Success Criteria:**

✅ **Zero data loss** in any scenario
✅ **Exact correlation** between transmitted and erased data
✅ **Proper failure recovery** with no orphaned data
✅ **All existing functionality** continues to work

**The fix ensures the system follows the principle:** *"Erase exactly what was sent, nothing more, nothing less."*

This guide provides test developers with complete understanding of the system internals and comprehensive testing approaches to validate the critical data loss bug fix.