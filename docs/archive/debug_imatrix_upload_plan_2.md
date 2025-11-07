# iMatrix Upload Response Processing Debug Plan

**Date**: 2025-11-07
**Task**: Debug and fix event data read failures in iMatrix upload system
**Branches**: iMatrix=Aptera_1, Fleet-Connect-1=Aptera_1
**New Branches**: TBD after approval

---

## Executive Summary

The iMatrix upload system is experiencing a critical bug where event data reads fail with error code 34 (IMX_ERROR_NO_DATA) despite data being available. Analysis reveals that pending data tracking becomes corrupted due to improper management of the `packet_contents.in_use` flag, causing ACK/NACK processing to be skipped.

### Key Error Pattern
```
[00:01:25.366] IMX_UPLOAD: ERROR: Failed to read all event data for: brakePedal_st, result: 34:NO DATA, requested: 1, received: 0
[00:01:25.368] IMX_UPLOAD: ERROR: Failed to read all event data for: SccA_ScState, result: 34:NO DATA, requested: 1, received: 0
```

---

## Background Review - Understanding the System

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Fleet-Connect-1                         │
│                  (Main Application)                      │
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │    iMatrix Upload System                   │         │
│  │    (imatrix_upload/imatrix_upload.c)       │         │
│  │                                            │         │
│  │  State Machine:                            │         │
│  │  ├─ INIT                                   │         │
│  │  ├─ CHECK_FOR_PENDING                      │         │
│  │  ├─ GET_DNS                                │         │
│  │  ├─ GET_PACKET                             │         │
│  │  ├─ LOAD_SAMPLES_PACKET ←─── DATA READ    │         │
│  │  ├─ UPLOAD_DATA                            │         │
│  │  ├─ UPLOAD_WAIT_RSP ←────── RESPONSE      │         │
│  │  └─ UPLOAD_COMPLETE                        │         │
│  │                                            │         │
│  │  packet_contents.in_use: CRITICAL FLAG    │         │
│  └────────────────────────────────────────────┘         │
│                       │                                  │
│                       ↓ API Calls                        │
│  ┌────────────────────────────────────────────┐         │
│  │    iMatrix Core Library                    │         │
│  │    (iMatrix/cs_ctrl/)                      │         │
│  │                                            │         │
│  │  MM2 Read Operations:                      │         │
│  │  ├─ imx_get_new_sample_count()            │         │
│  │  ├─ imx_read_bulk_samples()               │         │
│  │  ├─ imx_erase_all_pending() (ACK)         │         │
│  │  └─ imx_revert_all_pending() (NACK)       │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow - Normal Case (SUCCESS)

```
1. CHECK_FOR_PENDING state
   └─> imx_get_new_sample_count() → Returns available_count > 0

2. LOAD_SAMPLES_PACKET state
   ├─> packet_contents.in_use = true (line 1178)
   ├─> imx_read_bulk_samples()
   │   ├─> Reads data from MM2
   │   ├─> Marks data as PENDING for upload_source
   │   └─> Returns filled_count
   └─> Builds CoAP packet with data

3. UPLOAD_DATA state
   └─> Sends packet to server

4. UPLOAD_WAIT_RSP state
   └─> Waits for ACK/NACK response

5. Response Handler (_imatrix_upload_response_hdl)
   ├─> if (result && packet_contents.in_use) → SUCCESS PATH
   │   └─> imx_erase_all_pending() for each sensor
   │       ├─> Clears pending count
   │       └─> Frees memory
   └─> packet_contents.in_use = false (line 476)

6. UPLOAD_COMPLETE state
   └─> Returns to CHECK_FOR_PENDING
```

### Data Flow - Bug Case (FAILURE)

```
1. CHECK_FOR_PENDING state
   └─> imx_get_new_sample_count() → Returns available_count > 0

2. LOAD_SAMPLES_PACKET state
   ├─> packet_contents.in_use = true (line 1178)
   ├─> imx_read_bulk_samples()
   │   ├─> Returns IMX_NO_DATA (error 34)
   │   └─> filled_count = 0
   └─> ⚠️ BUG: Packet still sent despite read failure

3. UPLOAD_DATA state
   └─> Sends EMPTY or PARTIAL packet to server

4. UPLOAD_WAIT_RSP state
   └─> Response arrives (may be success or failure)

5. Response Handler (_imatrix_upload_response_hdl)
   ├─> if (result && packet_contents.in_use) → ✓ Condition TRUE
   │   └─> Calls imx_erase_all_pending()
   │       └─> ⚠️ BUG: Tries to erase pending data that was NEVER MARKED PENDING
   │           └─> Because imx_read_bulk_samples() returned error
   │               └─> No data was actually read
   │                   └─> No pending count was incremented
   └─> ⚠️ Result: Pending tracking corrupted
```

---

## Root Cause Analysis

### Primary Issue: Missing Error Handling in LOAD_SAMPLES_PACKET

**Location**: `iMatrix/imatrix_upload/imatrix_upload.c`, lines 1510-1534 (EVT) and 1554-1575 (TSD)

**Current Code**:
```c
imx_result_t imx_result = imx_read_bulk_samples(imatrix.upload_source, &csb[i], &csd[i],
    array, MAX_BULK_READ_SAMPLES, actual_samples_to_read, &filled_count);

if (imx_result == IMX_SUCCESS && filled_count == actual_samples_to_read)
{
    // Copy data to packet
}
else
{
    // Log error
    imx_cli_log_printf(true,"IMX_UPLOAD: ERROR: Failed to read all event data...");
    // ⚠️ BUG: Code continues! Packet is still sent!
}
```

**The Problem**:
1. When `imx_read_bulk_samples()` fails or returns partial data:
   - Error is logged
   - But execution continues
   - Packet is built with zero or partial data
   - `packet_contents.in_use` remains `true`
   - Packet is sent to server

2. When response arrives:
   - Response handler sees `packet_contents.in_use == true`
   - Calls `imx_erase_all_pending()` for ALL sensors
   - But NO data was actually marked as pending (because read failed)
   - Result: Corrupted pending data tracking

### Secondary Issue: Race Condition in Sample Count

**Location**: `iMatrix/cs_ctrl/mm2_read.c`, lines 172-208

**The Race**:
```c
// Thread A (upload check):
available = imx_get_new_sample_count(source, csb, csd);  // Returns 5
→ Time passes
→ Thread B clears data via erase_all_pending()
→ Time passes
// Thread A (data read):
result = imx_read_bulk_samples(source, csb, csd, ...);  // Returns NO_DATA!
```

**Why This Happens**:
- `imx_get_new_sample_count()` is called during CHECK_FOR_PENDING (line 1298)
- But data isn't read until LOAD_SAMPLES_PACKET state (lines 1510/1554)
- Between these states, another upload source may complete and erase data
- Upload source rotation can change the active source

### Tertiary Issue: packet_contents Lifecycle

**Location**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Lifecycle Analysis**:
```
Line 1177: memset(&packet_contents, 0, sizeof(packet_contents));
Line 1178: packet_contents.in_use = true;  ← SET TO TRUE

... data reading happens (may fail) ...

Line 476: packet_contents.in_use = false;  ← CLEARED IN RESPONSE HANDLER
```

**The Issue**:
- Flag is set at START of packet loading
- But if packet send fails before response handler runs:
  - Flag may be cleared elsewhere
  - Or left dangling until next packet

---

## Detailed Investigation Questions

### Questions for Code Review

1. **Q1**: Does `packet_contents.in_use` ever get cleared outside the response handler?
   - **Answer**: Need to search for all references

2. **Q2**: What happens if CoAP transmission fails?
   - **Answer**: Need to trace error paths in UPLOAD_DATA state

3. **Q3**: Can upload_source change between GET_PACKET and response?
   - **Answer**: YES - previously fixed (see lines 614-668 comments)
   - Rotation now only happens in CHECK_FOR_PENDING state

4. **Q4**: Is there a timeout that could skip response handling?
   - **Answer**: YES - see line 479-481: "Ignoring response since timeout"

5. **Q5**: What if sensor is disabled between read and ACK?
   - **Answer**: Need to check if csb->enabled is checked in erase_all_pending

### Questions for Log Analysis

1. **L1**: Do "Failed to read" errors always correlate with specific sensors?
2. **L2**: Does the error occur more frequently after successful uploads?
3. **L3**: Is there a pattern with upload_source rotation?
4. **L4**: Do the requested counts match expectations?
5. **L5**: Are there any "ACK PROCESSING SKIPPED" messages?

---

## Proposed Solution

### Solution Overview

The fix requires **three coordinated changes**:

1. **Abort packet on read failure** - Don't send empty/partial packets
2. **Validate data before marking in-use** - Only set flag if data successfully read
3. **Add safety checks in response handler** - Verify pending counts before erase

### Detailed Implementation Plan

#### Fix 1: Abort Packet on Read Failure

**File**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Location**: Lines 1528-1534 (EVT) and 1573-1580 (TSD)

**Change**:
```c
// BEFORE:
if (imx_result == IMX_SUCCESS && filled_count == actual_samples_to_read)
{
    // Copy data to packet
}
else
{
    imx_cli_log_printf(true,"IMX_UPLOAD: ERROR: ...");
    // ⚠️ Continues execution
}

// AFTER:
if (imx_result == IMX_SUCCESS && filled_count == actual_samples_to_read)
{
    // Copy data to packet
    packet_contents.entry_counts[type][i]++; // Track samples
}
else
{
    imx_cli_log_printf(true,"IMX_UPLOAD: ERROR: Failed to read data for: %s, "
        "result: %u:%s, requested: %u, received: %u\r\n",
        csb[i].name, imx_result, imx_error(imx_result),
        actual_samples_to_read, filled_count);

    // CRITICAL FIX: Abort packet on read failure
    PRINTF("IMX_UPLOAD: Aborting packet due to read failure\r\n");

    // Mark as data_added to prevent "no data" send
    // But don't actually add the bad data

    // Two options:
    // Option A: Skip this sensor, continue with others
    continue;  // Move to next sensor

    // Option B: Abort entire packet
    packet_full = true;  // Stop adding more data
    break;  // Exit sensor loop
}
```

**Rationale**:
- Prevents sending packets with missing/partial data
- Avoids corrupting pending data tracking
- Allows successful retry on next cycle

**Trade-offs**:
- Option A (skip sensor): May send partial packets with other sensors
- Option B (abort packet): More conservative, delays all uploads

**Recommendation**: Option B (abort entire packet) for data integrity

#### Fix 2: Validate Data Before Marking packet_contents.in_use

**File**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Location**: Lines 1173-1180 and end of LOAD_SAMPLES_PACKET case

**Change**:
```c
// BEFORE (line 1178):
packet_contents.in_use = true;  // Set at START of packet loading

// AFTER:
// Don't set flag at start. Set it AFTER successful data read.

// At line 1178:
packet_contents.in_use = false;  // Initialize to false

// After the sensor loop completes (around line 1600+):
// Check if ANY data was actually added
if (data_added && packet_contents.in_use == false) {
    // At least one sensor successfully read data
    packet_contents.in_use = true;
    PRINTF("[UPLOAD DEBUG] packet_contents.in_use SET TO TRUE after successful reads\r\n");
} else if (!data_added) {
    PRINTF("[UPLOAD DEBUG] NO data added - packet_contents.in_use remains FALSE\r\n");
}

// Update packet_contents.entry_counts only inside success path:
// (Move from current locations to ONLY when memcpy succeeds)
```

**Rationale**:
- Flag only set if data actually read successfully
- Prevents false positives in response handler
- Makes flag meaning precise: "this packet contains valid pending data"

#### Fix 3: Add Safety Checks in Response Handler

**File**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Location**: Lines 401-439 (ACK processing)

**Change**:
```c
// BEFORE:
if (result && packet_contents.in_use)
{
    /* SUCCESS: Erase pending data */
    for( type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++ )
    {
        imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);
        for (uint16_t i = 0; i < no_items; i++)
        {
            if (imx_has_pending_data(imatrix.upload_source, &csb[i], &csd[i]))
            {
                imx_result_t imx_result = imx_erase_all_pending(...);
                if (imx_result != IMX_SUCCESS) {
                    PRINTF("ERROR: Failed to erase...");
                }
            }
        }
    }
}

// AFTER:
if (result && packet_contents.in_use)
{
    /* SUCCESS: Erase pending data */
    PRINTF("[UPLOAD DEBUG] ACK processing: packet_contents.in_use=TRUE\r\n");

    uint32_t sensors_with_pending = 0;
    uint32_t sensors_erased = 0;
    uint32_t erase_errors = 0;

    for( type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++ )
    {
        imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);
        for (uint16_t i = 0; i < no_items; i++)
        {
            // SAFETY CHECK: Only erase if we actually added this sensor to packet
            if (packet_contents.entry_counts[type][i] == 0) {
                // This sensor wasn't in the packet - don't erase
                continue;
            }

            if (imx_has_pending_data(imatrix.upload_source, &csb[i], &csd[i]))
            {
                sensors_with_pending++;

                PRINTF("[ACK] Erasing pending for type=%u, i=%u, sensor=%s, "
                       "entry_count=%u\r\n",
                       type, i, csb[i].name,
                       packet_contents.entry_counts[type][i]);

                imx_result_t imx_result = imx_erase_all_pending(
                    imatrix.upload_source, &csb[i], &csd[i]);

                if (imx_result == IMX_SUCCESS) {
                    sensors_erased++;
                } else {
                    erase_errors++;
                    PRINTF("ERROR: Failed to erase all pending data for "
                           "type %d, entry %u, result: %u:%s\r\n",
                           type, i, imx_result, imx_error(imx_result));
                }
            } else {
                // WARNING: Sensor was in packet but has no pending data!
                PRINTF("WARNING: type=%u, i=%u, sensor=%s was in packet "
                       "(entry_count=%u) but has NO pending data!\r\n",
                       type, i, csb[i].name,
                       packet_contents.entry_counts[type][i]);
            }
        }
    }

    PRINTF("[ACK] ACK complete: sensors_with_pending=%u, sensors_erased=%u, "
           "erase_errors=%u\r\n",
           sensors_with_pending, sensors_erased, erase_errors);
}
```

**Rationale**:
- Cross-checks packet_contents.entry_counts with has_pending_data
- Only erases sensors that were actually in the packet
- Detects inconsistencies and logs warnings
- Provides detailed statistics for debugging

---

## Implementation Todo List

### Phase 1: Analysis & Branch Creation
- [x] Note current branches (iMatrix=Aptera_1, Fleet-Connect-1=Aptera_1)
- [ ] Create new feature branch: `feature/debug-upload-response-processing`
  ```bash
  cd iMatrix
  git checkout -b feature/debug-upload-response-processing Aptera_1
  cd ../Fleet-Connect-1
  git checkout -b feature/debug-upload-response-processing Aptera_1
  ```

### Phase 2: Code Investigation
- [ ] Search for all references to `packet_contents.in_use`
  ```bash
  grep -rn "packet_contents.in_use" iMatrix/imatrix_upload/
  ```
- [ ] Trace CoAP transmission error paths
- [ ] Review timeout handling in UPLOAD_WAIT_RSP
- [ ] Check if csb->enabled affects erase_all_pending

### Phase 3: Implement Fix 1 - Abort on Read Failure
- [ ] Edit `iMatrix/imatrix_upload/imatrix_upload.c`
- [ ] Modify EVT read error handling (lines 1528-1534)
- [ ] Modify TSD read error handling (lines 1573-1580)
- [ ] Add abort logic: `packet_full = true; break;`
- [ ] Test with intentional read failures

### Phase 4: Implement Fix 2 - Validate Before Marking
- [ ] Edit `iMatrix/imatrix_upload/imatrix_upload.c`
- [ ] Change line 1178: `packet_contents.in_use = false;`
- [ ] Add validation at end of sensor loop
- [ ] Set flag only if `data_added == true`
- [ ] Update entry_counts tracking

### Phase 5: Implement Fix 3 - Safety Checks in Handler
- [ ] Edit `iMatrix/imatrix_upload/imatrix_upload.c`
- [ ] Add entry_counts cross-check in ACK handler
- [ ] Add detailed logging
- [ ] Add warning for inconsistencies
- [ ] Add statistics tracking

### Phase 6: Testing
- [ ] Compile with debug logging enabled
- [ ] Run with test data
- [ ] Monitor logs for "Failed to read" errors
- [ ] Verify packet_contents.in_use is set correctly
- [ ] Verify ACK processing statistics
- [ ] Test error recovery (NACK handling)

### Phase 7: Log Analysis
- [ ] Collect new log files with fixes applied
- [ ] Compare error rates before/after
- [ ] Verify no "ACK PROCESSING SKIPPED" messages
- [ ] Check for new warnings

### Phase 8: Documentation & Merge
- [ ] Update this plan with results
- [ ] Document token usage and time spent
- [ ] Create pull request with detailed description
- [ ] Merge to Aptera_1 after approval

---

## Testing Strategy

### Unit Testing
1. **Test Read Failures**:
   - Inject IMX_NO_DATA errors
   - Verify packet is aborted
   - Verify packet_contents.in_use remains false

2. **Test Partial Reads**:
   - Request 10 samples, return only 5
   - Verify packet is aborted
   - Verify no pending data corruption

3. **Test ACK with Empty Packet**:
   - Send packet with no data
   - Verify no erase operations
   - Verify clean state transition

### Integration Testing
1. **Multi-Sensor Upload**:
   - Mix successful and failed reads
   - Verify only successful sensors in packet
   - Verify correct ACK handling

2. **Upload Source Rotation**:
   - Test rotation after successful upload
   - Test rotation after failed upload
   - Verify source stability during upload cycle

3. **Timeout Scenarios**:
   - Simulate response timeout
   - Verify proper cleanup
   - Verify retry mechanism

### Stress Testing
1. **High Data Rate**:
   - Generate continuous sensor data
   - Monitor for "NO DATA" errors
   - Verify no pending data leaks

2. **Network Instability**:
   - Simulate packet loss
   - Verify NACK handling
   - Verify retry success

---

## Risk Assessment

### Risks & Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| Fix causes different bug | HIGH | Extensive testing before merge |
| Performance degradation | MEDIUM | Profile before/after |
| Backward compatibility | LOW | Changes internal only |
| Data loss during fix | MEDIUM | Backup logs before testing |

### Rollback Plan

If fixes cause regressions:
1. Revert commits on feature branch
2. Return to Aptera_1 baseline
3. Analyze test failures
4. Revise fixes and retry

---

## Success Criteria

### Fix is successful if:
1. ✓ "Failed to read all event data" errors eliminated
2. ✓ packet_contents.in_use always accurate
3. ✓ No "ACK PROCESSING SKIPPED" warnings
4. ✓ Pending data tracking remains consistent
5. ✓ Upload success rate improves
6. ✓ No new errors introduced

### Metrics to Track:
- Error rate: failed reads per 1000 uploads
- ACK success rate: successful erases per upload
- Memory leak rate: growth in pending_count over time
- Upload latency: time from CHECK to COMPLETE

---

## Appendix A: Code Locations Reference

### Key Files
- **iMatrix/imatrix_upload/imatrix_upload.c** (main file)
  - Line 1178: packet_contents.in_use = true
  - Line 1298: imx_get_new_sample_count()
  - Line 1510: imx_read_bulk_samples() for EVT
  - Line 1530-1531: Error logging for EVT
  - Line 1554: imx_read_bulk_samples() for TSD
  - Line 1573-1580: Error logging for TSD
  - Line 351-488: _imatrix_upload_response_hdl()
  - Line 401-439: ACK processing loop
  - Line 441-462: NACK processing loop
  - Line 464-472: Bug condition (ACK skipped)
  - Line 476: packet_contents.in_use = false

- **iMatrix/cs_ctrl/mm2_read.c** (memory manager)
  - Line 172-208: imx_get_new_sample_count()
  - Line 231-422: imx_read_bulk_samples()
  - Line 706-949: imx_erase_all_pending()
  - Line 968-1025: imx_revert_all_pending()

### Key Data Structures
```c
// iMatrix/imatrix_upload/imatrix_upload.c
static struct {
    uint16_t entry_counts[IMX_NO_PERIPHERAL_TYPES][MAX_ENTRIES_PER_TYPE];
    bool in_use;
} packet_contents;

// iMatrix/cs_ctrl/mm2_core.h
typedef struct {
    uint32_t pending_count;
    SECTOR_ID_TYPE pending_start_sector;
    uint16_t pending_start_offset;
} pending_by_source_t;
```

---

## Appendix B: Error Codes

```c
#define IMX_SUCCESS              0
#define IMX_INVALID_PARAMETER   -1
#define IMX_NO_MEMORY           -2
#define IMX_NO_DATA             34   // ← The error we're seeing
#define IMX_TIMEOUT             -4
```

---

## Appendix C: State Machine Diagram

```
┌──────────────────┐
│   INIT           │
│  (Check timer)   │
└────────┬─────────┘
         │ Timer expired
         ↓
┌──────────────────┐
│ CHECK_FOR_PENDING│
│  (Scan sensors)  │←────────────────────┐
└────────┬─────────┘                     │
         │ Data found                     │
         ↓                                │
┌──────────────────┐                     │
│   GET_DNS        │                     │
│ (Resolve server) │                     │
└────────┬─────────┘                     │
         │ DNS OK                         │
         ↓                                │
┌──────────────────┐                     │
│   GET_PACKET     │                     │
│ (Allocate msg)   │                     │
└────────┬─────────┘                     │
         │ Packet ready                   │
         ↓                                │
┌──────────────────┐                     │
│ LOAD_SAMPLES     │ ←── BUG HERE!       │
│ (Read data)      │                     │
└────────┬─────────┘                     │
         │ Data loaded                    │
         ↓                                │
┌──────────────────┐                     │
│  UPLOAD_DATA     │                     │
│  (Send packet)   │                     │
└────────┬─────────┘                     │
         │ Sent                           │
         ↓                                │
┌──────────────────┐                     │
│ UPLOAD_WAIT_RSP  │ ←── RESPONSE HERE   │
│ (Wait for ACK)   │                     │
└────────┬─────────┘                     │
         │ ACK received                   │
         ↓                                │
┌──────────────────┐                     │
│ UPLOAD_COMPLETE  │                     │
│ (Process ACK)    │                     │
└────────┬─────────┘                     │
         │                                │
         └────────────────────────────────┘
```

---

## Questions for User Review

Before proceeding with implementation, please confirm:

1. **Branch Strategy**: Create `feature/debug-upload-response-processing` branches in both repos?
2. **Fix Approach**: Use Option B (abort entire packet on read failure)?
3. **Testing**: Run on VM only, or also test on hardware?
4. **Log Files**: Can you provide upload logs showing the errors for analysis?
5. **Timeline**: Any urgency or deadline for this fix?

---

**Status**: Awaiting user approval to proceed with implementation
**Next Step**: Answer questions, then create feature branches and begin Phase 3

