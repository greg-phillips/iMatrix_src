# iMatrix Upload Response Processing Debug Plan - REVISED

**Date**: 2025-11-07
**Revision**: 2 (Based on upload6.txt log analysis)
**Task**: Fix event data read failures in MM2 bulk read logic
**Branches**: iMatrix=Aptera_1, Fleet-Connect-1=Aptera_1

---

## Executive Summary - REVISED FINDINGS

Analysis of `logs/upload6.txt` reveals the **actual root cause** is different from initial assessment:

### The Real Bug: Pending Data Blocks New Data Reads

When `imx_read_bulk_samples()` tries to read NEW data, it incorrectly starts from the read position pointing at PENDING data (after NACK revert), and fails to skip over pending records to reach the new data that comes after them in the chain.

**Evidence from upload6.txt**:
```
Line 53:  Entry[54] total_samples=6, pending=5, available=1, will_read=1
Line 54:  ERROR: Failed to read all event data for: brakePedal_st, result: 34:NO DATA, requested: 1, received: 0

(NACK processing reverts read position)

Line 311: Entry[54] total_samples=8, pending=5, available=3, will_read=3
Line 314: ERROR: Failed to read all event data for: brakePedal_st, result: 34:NO DATA, requested: 3, received: 0
```

**Analysis**:
1. First upload: 6 total, 5 pending, 1 available → Read fails
2. NACK revert: Read position reset to pending_start
3. New data arrives: 2 more records written → total now 8
4. Second upload: 8 total, 5 still pending, 3 available (1 old + 2 new)
5. Read still fails → Because read starts at pending position

**The Chain Structure**:
```
RAM Chain: [Pending-1][Pending-2][Pending-3][Pending-4][Pending-5][New-1][New-2][New-3]
                       ↑
             ram_start_sector_id (after NACK revert)

BUG: imx_read_bulk_samples() starts reading HERE (pending data)
     But should skip to HERE → [New-1]
```

---

## Root Cause Analysis - UPDATED

### Primary Issue: imx_read_bulk_samples() Doesn't Skip Pending Data

**Location**: `iMatrix/cs_ctrl/mm2_read.c`, lines 231-422

**The Function's Logic**:
```c
imx_result_t imx_read_bulk_samples(...) {
    // Line 270-271: Save pending start BEFORE reading
    SECTOR_ID_TYPE pending_start_sector = csd->mmcb.ram_start_sector_id;
    uint16_t pending_start_offset = csd->mmcb.ram_read_sector_offset;

    // Line 296-297: Start reading from current read position
    SECTOR_ID_TYPE current_sector = csd->mmcb.ram_start_sector_id;  // ← BUG HERE
    uint16_t current_offset = csd->mmcb.ram_read_sector_offset;

    // Lines 301-343: Read loop
    while (current_sector != NULL_SECTOR_ID) {
        // Reads data at current position
        // But if that position is in PENDING data, this fails!
    }
}
```

**The Problem**:
1. After a NACK revert, `ram_start_sector_id` points to the START of pending data
2. New data is appended AFTER pending data in the chain
3. But `imx_read_bulk_samples()` starts reading from `ram_start_sector_id`
4. It reads pending data (which is already marked as pending)
5. But we want to read NEW data (which comes after pending data)

**Why It Fails**:
- The function tries to read from the pending position
- But the code may have logic that prevents re-reading pending data
- Or the pending data has been partially consumed/erased
- Result: IMX_NO_DATA error

### Secondary Issue: Packet Still Sent Despite Read Failures

**Location**: `iMatrix/imatrix_upload/imatrix_upload.c`, lines 1528-1534 (EVT) and 1573-1580 (TSD)

**Current Code**:
```c
if (imx_result == IMX_SUCCESS && filled_count == actual_samples_to_read) {
    // Copy data to packet
} else {
    imx_cli_log_printf("ERROR: Failed to read...");
    // ← BUG: Code continues! Packet is still sent with empty blocks
}
```

---

## The Fix - REVISED SOLUTION

### Fix 1: Skip Pending Data When Reading New Data

**File**: `iMatrix/cs_ctrl/mm2_read.c`

**Location**: Lines 296-297 in `imx_read_bulk_samples()`

**Change**: Calculate where NEW data starts (after pending data)

```c
// BEFORE (line 296-297):
SECTOR_ID_TYPE current_sector = csd->mmcb.ram_start_sector_id;
uint16_t current_offset = csd->mmcb.ram_read_sector_offset;

// AFTER:
// Start reading from AFTER pending data, not AT pending data
SECTOR_ID_TYPE current_sector;
uint16_t current_offset;

// Check if we have pending data for this upload source
uint32_t pending_count = csd->mmcb.pending_by_source[upload_source].pending_count;

if (pending_count > 0) {
    // We have pending data - need to skip over it to find new data
    PRINTF("[MM2] read_bulk: sensor=%s has %u pending records, skipping to new data\r\n",
           csb->name, pending_count);

    // Start from the pending start position
    current_sector = csd->mmcb.pending_by_source[upload_source].pending_start_sector;
    current_offset = csd->mmcb.pending_by_source[upload_source].pending_start_offset;

    // Skip over pending_count records to reach new data
    uint32_t records_skipped = 0;
    while (current_sector != NULL_SECTOR_ID && records_skipped < pending_count) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current_sector);
        if (!entry || !entry->in_use) {
            current_sector = get_next_sector_in_chain(current_sector);
            continue;
        }

        if (entry->sector_type == SECTOR_TYPE_TSD) {
            // Skip TSD values
            while (current_offset < TSD_FIRST_UTC_SIZE + (MAX_TSD_VALUES_PER_SECTOR * sizeof(uint32_t)) &&
                   records_skipped < pending_count) {
                records_skipped++;
                current_offset += sizeof(uint32_t);

                if (current_offset >= TSD_FIRST_UTC_SIZE + (MAX_TSD_VALUES_PER_SECTOR * sizeof(uint32_t))) {
                    // Move to next sector
                    current_sector = get_next_sector_in_chain(current_sector);
                    current_offset = TSD_FIRST_UTC_SIZE;
                    break;
                }
            }
        } else if (entry->sector_type == SECTOR_TYPE_EVT) {
            // Skip EVT pairs
            while (current_offset < MAX_EVT_PAIRS_PER_SECTOR * sizeof(evt_data_pair_t) &&
                   records_skipped < pending_count) {
                records_skipped++;
                current_offset += sizeof(evt_data_pair_t);

                if (current_offset >= MAX_EVT_PAIRS_PER_SECTOR * sizeof(evt_data_pair_t)) {
                    // Move to next sector
                    current_sector = get_next_sector_in_chain(current_sector);
                    current_offset = 0;
                    break;
                }
            }
        }
    }

    PRINTF("[MM2] read_bulk: skipped %u pending records, now at sector=%u, offset=%u\r\n",
           records_skipped, current_sector, current_offset);

} else {
    // No pending data - start from normal read position
    current_sector = csd->mmcb.ram_start_sector_id;
    current_offset = csd->mmcb.ram_read_sector_offset;
}

// Now current_sector/current_offset point to FIRST NEW RECORD (or NULL if no new data)
```

**Rationale**:
- NEW data comes AFTER pending data in the chain
- Must skip over pending_count records to reach new data
- After skipping, current_sector points to first new record
- If no new data exists, current_sector will be NULL_SECTOR_ID

### Fix 2: Abort Packet on Read Failure

**File**: `iMatrix/imatrix_upload/imatrix_upload.c`

**Location**: Lines 1528-1534 (EVT) and 1573-1580 (TSD)

**Change**: Add continue/break to skip failed sensors

```c
// EVT Error Handling (line 1528-1534)
if (imx_result == IMX_SUCCESS && filled_count == actual_samples_to_read) {
    // Copy data to packet
    for ( uint16_t j = 0; j < filled_count; j++) {
        packet_contents.entry_counts[type][i]++;
        upload_data->payload.block_event_data.time_data[j].utc_sample_time = htonl(array[j].timestamp);
        upload_data->payload.block_event_data.time_data[j].data = htonl(array[j].value);
    }
} else {
    imx_cli_log_printf(true,"IMX_UPLOAD: ERROR: Failed to read event data for: %s, "
        "result: %u:%s, requested: %u, received: %u\r\n",
        csb[i].name, imx_result, imx_error(imx_result),
        actual_samples_to_read, filled_count);

    // FIX: Skip this sensor and continue with next one
    PRINTF("IMX_UPLOAD: Skipping sensor %s due to read failure\r\n", csb[i].name);
    continue;  // ← ADD THIS: Move to next sensor instead of adding empty block
}
```

**Rationale**:
- Don't add empty blocks to packet
- Skip failed sensors, process successful ones
- Prevents sending packets with missing data

### Fix 3: Add Safety Check in Pending Data Tracking

**File**: `iMatrix/cs_ctrl/mm2_read.c`

**Location**: Line 374-412 in `imx_read_bulk_samples()`

**Change**: Only mark as pending if we actually read from RAM (not from pending position)

```c
// BEFORE (line 374-412):
if (*filled_count > 0) {
    // Always mark as pending
    csd->mmcb.pending_by_source[upload_source].pending_count += *filled_count;
    // ...
}

// AFTER:
if (*filled_count > 0) {
    // Safety check: Only mark as pending if we read NEW data (not re-reading pending data)
    uint32_t old_pending = csd->mmcb.pending_by_source[upload_source].pending_count;

    csd->mmcb.pending_by_source[upload_source].pending_count += *filled_count;

    PRINTF("[MM2] read_bulk: sensor=%s, marked %u records as pending (pending_count: %u -> %u)\r\n",
           csb->name, *filled_count, old_pending,
           csd->mmcb.pending_by_source[upload_source].pending_count);

    // Set pending start ONLY if this is first pending data for this source
    if (old_pending == 0) {
        csd->mmcb.pending_by_source[upload_source].pending_start_sector = pending_start_sector;
        csd->mmcb.pending_by_source[upload_source].pending_start_offset = pending_start_offset;

        PRINTF("[MM2] read_bulk: set pending_start to sector=%u, offset=%u\r\n",
               pending_start_sector, pending_start_offset);
    }
}
```

---

## Implementation Checklist - UPDATED

### Phase 1: Implement Fix 1 - Skip Pending Data
- [ ] Edit `iMatrix/cs_ctrl/mm2_read.c`
- [ ] Modify `imx_read_bulk_samples()` at lines 296-297
- [ ] Add pending data skip logic
- [ ] Add debug logging for skip operation
- [ ] Test with sensors that have pending data

### Phase 2: Implement Fix 2 - Abort on Read Failure
- [ ] Edit `iMatrix/imatrix_upload/imatrix_upload.c`
- [ ] Add `continue` statement in EVT error path (line 1534)
- [ ] Add `continue` statement in TSD error path (line 1580)
- [ ] Verify packet only contains successful reads

### Phase 3: Implement Fix 3 - Safety Checks
- [ ] Edit `iMatrix/cs_ctrl/mm2_read.c`
- [ ] Add detailed logging in pending tracking (lines 374-412)
- [ ] Add validation checks

### Phase 4: Testing
- [ ] Test scenario: Sensor with pending=5, available=3
- [ ] Verify: Read returns 3 new records (not NO_DATA)
- [ ] Verify: Pending count increases to 8 (5+3)
- [ ] Test NACK: Verify revert resets pending correctly
- [ ] Test ACK: Verify all 8 records are erased

### Phase 5: Log Validation
- [ ] Collect new logs with fixes
- [ ] Verify no "Failed to read" errors
- [ ] Verify correct pending data tracking
- [ ] Compare before/after error rates

---

## Test Scenarios

### Scenario 1: Pending Data with New Data

**Setup**:
- Sensor has 5 pending records (from previous failed upload)
- 3 new records arrive
- Total=8, pending=5, available=3

**Expected Before Fix**:
- `imx_get_new_sample_count()` returns 3
- `imx_read_bulk_samples()` returns NO_DATA (BUG!)

**Expected After Fix**:
- `imx_get_new_sample_count()` returns 3
- `imx_read_bulk_samples()` skips 5 pending records
- Returns 3 new records successfully
- Pending count increases to 8

### Scenario 2: NACK Revert

**Setup**:
- Upload fails, NACK received
- Pending data must be retried

**Expected After Fix**:
- `imx_revert_all_pending()` resets read position
- Next upload reads from pending_start
- All 8 records (5 old + 3 new) are uploaded

### Scenario 3: ACK Success

**Setup**:
- Upload succeeds, ACK received
- All pending data must be erased

**Expected After Fix**:
- `imx_erase_all_pending()` erases all 8 records
- Pending count resets to 0
- Memory is freed

---

## Questions for User

Before proceeding with implementation:

1. **Log Analysis**: Does the upload6.txt analysis match your understanding of the problem?

2. **Fix Approach**: Do you agree with the "skip pending data" solution in Fix 1?

3. **Testing**: Should I:
   - Create the fixes first, then test?
   - Or do you want to generate more logs to validate the analysis?

4. **Branch Strategy**: Create `feature/fix-bulk-read-pending-skip` branches?

5. **Priority**: Is this fix urgent, or can we take time to thoroughly test?

---

## Summary of Changes from Original Plan

**Original Assessment**:
- Thought the bug was in ACK/NACK processing
- Thought packet_contents.in_use was being mismanaged

**Revised Assessment** (based on logs):
- Real bug is in `imx_read_bulk_samples()` not skipping pending data
- Secondary bug is packet being sent despite read failures
- ACK/NACK processing is actually working correctly (NACK revert is working)

**Key Insight from Logs**:
- Entry[54] shows pending increased from 5 to 8 across multiple uploads
- But read keeps failing because it starts at pending position
- Need to skip OVER pending data to reach NEW data

---

**Status**: Awaiting user approval to proceed with REVISED implementation plan
**Next Step**: Implement Fix 1 (skip pending data logic) in mm2_read.c

