# iMatrix Upload Read Bugs - Implementation Summary

**Date**: 2025-11-07
**Branch**: feature/fix-upload-read-bugs (iMatrix and Fleet-Connect-1)
**Status**: ✅ IMPLEMENTED with enhanced debug logging
**Updated**: Added MM2-READ-DEBUG messages for troubleshooting (lines 285-294, 362-368, 462-464)

---

## Bugs Fixed

### Bug #1: Unnecessary Disk Read Attempts
**Severity**: MEDIUM (Performance Impact)
**Symptom**: 15+ calls to `read_record_from_disk()` even when data is RAM-only
**Root Cause**: Code checked `!disk_exhausted` flag without verifying actual disk data exists

**Fix**: Added check for `total_disk_records > 0` before attempting disk reads

**File**: `iMatrix/cs_ctrl/mm2_read.c:365-377`

**Changes**:
```c
// BEFORE:
if (!icb.per_source_disk[upload_source].disk_exhausted) {
    result = read_record_from_disk(...);
}

// AFTER:
#ifdef LINUX_PLATFORM
if (csd->mmcb.total_disk_records > 0 &&
    !icb.per_source_disk[upload_source].disk_exhausted) {
    result = read_record_from_disk(...);
}
#endif
```

**Impact**: Eliminates 15+ unnecessary function calls per bulk read operation

---

### Bug #2: Read Fails When Pending Data Exists
**Severity**: CRITICAL (Data Loss)
**Symptom**: `imx_read_bulk_samples()` returns NO_DATA when `pending > 0` and new data available
**Root Cause**: After NACK revert, `ram_start_sector_id` points to PENDING data start. NEW data is AFTER pending in the chain, but bulk read started at pending position instead of skipping over it.

**Evidence from logs**:
```
upload6.txt line 53:  Entry[54] total=6, pending=5, available=1 → Read FAILS
upload6.txt line 311: Entry[54] total=8, pending=5, available=3 → Read STILL FAILS
```

**Fix**: Calculate read start position by skipping over existing pending records

**File**: `iMatrix/cs_ctrl/mm2_read.c:280-356`

**Changes**:
```c
// BEFORE:
SECTOR_ID_TYPE current_sector = csd->mmcb.ram_start_sector_id;  // Starts at PENDING position
uint16_t current_offset = csd->mmcb.ram_read_sector_offset;

// AFTER:
// Calculate starting position for reading NEW (non-pending) data
SECTOR_ID_TYPE read_start_sector;
uint16_t read_start_offset;
uint32_t existing_pending = csd->mmcb.pending_by_source[upload_source].pending_count;

if (existing_pending > 0) {
    // Skip over existing pending records to reach NEW data
    read_start_sector = csd->mmcb.pending_by_source[upload_source].pending_start_sector;
    read_start_offset = csd->mmcb.pending_by_source[upload_source].pending_start_offset;

    // Skip existing_pending records
    [... skipping logic for TSD and EVT ...]

} else {
    // No pending - start from normal position
    read_start_sector = csd->mmcb.ram_start_sector_id;
    read_start_offset = csd->mmcb.ram_read_sector_offset;
}
```

**Logic Flow**:
```
Chain: [Pending₁][Pending₂][Pending₃][Pending₄][Pending₅][New₁][New₂][New₃]
              ↑                                         ↑
     pending_start (saved)                   read_start (calculated)

1. existing_pending = 5
2. Start from pending_start position
3. Skip 5 records
4. read_start now points to New₁
5. Read 3 records (New₁, New₂, New₃)
6. Success! pending_count becomes 8
```

**Impact**: Fixes NO_DATA errors when sensors have pending data and new data arrives

---

### Bug #3: Packets Sent Despite Read Failures
**Severity**: HIGH (Data Integrity)
**Symptom**: Empty or partial blocks added to upload packets when `imx_read_bulk_samples()` fails
**Root Cause**: Error logged but execution continued, adding block header with zero/partial data

**Fix**: Added `continue` statement to skip failed sensors instead of adding empty blocks

**File**: `iMatrix/imatrix_upload/imatrix_upload.c:1530-1539` (EVT) and `1580-1589` (TSD)

**Changes**:
```c
// BEFORE (lines 1528-1534):
else {
    imx_cli_log_printf(true,"IMX_UPLOAD: ERROR: Failed to read...");
    // ⚠️ Code continues - adds empty block!
}

// AFTER:
else {
    imx_cli_log_printf(true,"IMX_UPLOAD: ERROR: Failed to read...");
    PRINTF("IMX_UPLOAD: Skipping sensor %s - will retry next cycle\r\n", csb[i].name);
    continue;  /* Skip to next sensor instead of adding empty block */
}
```

**Impact**:
- Prevents sending packets with missing/corrupted data
- Allows clean retry on next upload cycle
- Maintains packet integrity

---

## Testing Instructions

### Test Scenario 1: Normal Operation (No Pending)
**Setup**: Clean system, no pending data
**Expected**:
- No disk read attempts (Bug #1 fixed)
- All sensors read successfully
- Packet sent with complete data
- ACK received, data erased

**Validation**:
```bash
grep "DISK-READ-DEBUG" logs/upload_test.txt
# Should be EMPTY (no disk reads)

grep "read_bulk.*filled=" logs/upload_test.txt
# All should show filled=requested
```

### Test Scenario 2: NACK with Retry (Pending Data)
**Setup**:
1. Upload 5 records
2. Simulate NACK (disconnect network)
3. Add 3 more records
4. Retry upload

**Expected**:
- `imx_get_new_sample_count()` returns 3 (new data)
- `imx_read_bulk_samples()` skips 5 pending, reads 3 new
- pending_count becomes 8 (5 + 3)
- On next ACK: all 8 erased

**Validation**:
```bash
grep "skipping to find NEW data" logs/upload_test.txt
# Should show: "sensor=X has 5 existing pending records, skipping..."

grep "skipped.*pending records" logs/upload_test.txt
# Should show: "skipped 5 pending records, now at sector=..."

grep "pending_count:.*->.*8" logs/upload_test.txt
# Should show pending growing from 5 to 8
```

### Test Scenario 3: Read Failure Handling
**Setup**: Inject error condition that causes read to fail

**Expected**:
- Error logged: "Failed to read all event data"
- Message logged: "Skipping sensor X - will retry"
- Sensor NOT added to packet
- Next cycle retries successfully

**Validation**:
```bash
grep "Skipping sensor.*due to read failure" logs/upload_test.txt
# Should show sensors being skipped on failure

grep "Added.*Bytes.*total length" logs/upload_test.txt
# Should NOT show blocks added after "Skipping sensor" messages
```

---

## Code Changes Summary

### Files Modified

1. **iMatrix/cs_ctrl/mm2_read.c**
   - Lines 273-278: Added comments for fixes #1 and #2
   - Lines 280-356: NEW - Calculate read_start by skipping pending data
   - Lines 365-378: CHANGED - Only attempt disk read if actual disk data exists
   - Lines 383-385: CHANGED - Use read_start instead of ram_start
   - Lines 430-437: NEW - Update read_start in loop for multi-record reads
   - Lines 440-442: ENHANCED - Added debug logging for no-data case
   - Lines 451-462: NEW - Update ram_start after successful NEW data read

2. **iMatrix/imatrix_upload/imatrix_upload.c**
   - Lines 1530-1539: ADDED - continue statement for EVT read failure
   - Lines 1580-1589: ADDED - continue statement for TSD read failure

### Lines of Code Changed
- **mm2_read.c**: ~90 lines added/modified
- **imatrix_upload.c**: ~10 lines added/modified
- **Total**: ~100 lines

---

## Expected Behavior Changes

### Before Fixes:
```
1. Check for new data → available=3
2. Try disk read (15 times) → all fail
3. Start RAM read at pending position
4. Find pending data, not NEW data
5. Return NO_DATA error
6. Log error but continue
7. Add empty block to packet
8. Send packet with empty blocks
9. Get ACK/NACK
10. Try to erase, but no pending data was actually added
11. Pending tracking corrupted
```

### After Fixes:
```
1. Check for new data → available=3
2. Check total_disk_records=0 → Skip disk reads entirely ✓
3. Check existing_pending=5 → Skip 5 pending records ✓
4. Start RAM read at NEW data position
5. Read 3 NEW records successfully ✓
6. pending_count: 5 → 8 ✓
7. Add valid blocks to packet ✓
8. Send packet with complete data ✓
9. Get ACK
10. Erase all 8 pending records ✓
11. pending_count: 8 → 0, memory freed ✓
```

---

## Debugging Output

With fixes applied, new logs will show:

**Bug #1 Fix Output**:
```
[MM2] read_bulk: no pending data, starting from sector=X, offset=Y
[MM2] read_bulk: COMPLETE - requested=15, filled=15
```
(No DISK-READ-DEBUG messages!)

**Bug #2 Fix Output**:
```
[MM2] read_bulk: sensor=brakePedal_st has 5 existing pending records, skipping to find NEW data
[MM2] read_bulk: skipped 5 pending records, now at sector=10, offset=12
[MM2] read_bulk: COMPLETE - requested=3, filled=3
[MM2-PEND] read_bulk: pending_count: 5 -> 8
```

**Bug #3 Fix Output**:
```
IMX_UPLOAD: ERROR: Failed to read all event data for: sensor_X...
IMX_UPLOAD: Skipping sensor sensor_X (entry 54) due to read failure - will retry next cycle
```
(No "Added X Bytes" message after this)

---

## Risk Assessment

### Low Risk Changes:
- Bug #1 fix: Simple conditional check, no logic changes
- Bug #3 fix: Simple control flow (continue), no state changes

### Medium Risk Changes:
- Bug #2 fix: Complex skip logic, modifies read behavior
  - Risk: Skip logic might have off-by-one errors
  - Mitigation: Extensive logging added for debugging

### Testing Priority:
1. **High**: Bug #2 (pending skip logic) - needs thorough testing
2. **Medium**: Bug #3 (packet abort) - verify clean retry
3. **Low**: Bug #1 (disk skip) - simple optimization

---

## Rollback Plan

If issues arise:
```bash
cd iMatrix
git checkout Aptera_1
cd ../Fleet-Connect-1
git checkout Aptera_1
```

---

## Next Steps for User

1. **Build**: Compile on VM with fixes applied
   ```bash
   cd /path/to/build
   make clean && make
   ```

2. **Test**: Run with debug logging enabled
   - Enable `DEBUGS_FOR_MEMORY_MANAGER`
   - Enable `DEBUGS_FOR_IMX_UPLOAD`
   - Capture logs to `upload_test_fixed.txt`

3. **Validate**: Check for:
   - Zero "Failed to read" errors ✓
   - Zero "DISK-READ-DEBUG" messages ✓
   - "skipped X pending records" when retrying after NACK ✓
   - "Skipping sensor" on any failures ✓
   - Correct pending_count growth and cleanup ✓

4. **Stress Test**: Run for extended period (hours)
   - Monitor for memory leaks
   - Check pending_count returns to 0 after uploads
   - Verify no accumulation over time

---

**Implementation Complete** - Ready for build and test by user
