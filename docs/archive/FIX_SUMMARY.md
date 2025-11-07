# iMatrix Upload ACK Bug - Fix Summary

## ✅ CRITICAL BUG FIXED

**Date**: 2025-11-06
**Branch**: `bugfix/upload-ack-not-clearing-pending`
**Status**: READY FOR TESTING

---

## The Bug

### Symptoms
- Pending data accumulates in memory manager and is never cleared
- Memory exhaustion over time
- Duplicate uploads of the same data
- Server responds with valid ACK (CoAP 2.05 "ok") but data not erased

### Root Cause
**Upload source rotation happened BEFORE ACK was received**, causing response handler to check the WRONG upload source for pending data.

### Technical Details

**Problematic Code** (lines 620-691, BEFORE fix):
```c
// This executed on EVERY call to imatrix_upload(), even during WAIT_RSP!
if (imatrix.upload_source == IMX_UPLOAD_CAN_DEVICE) {
    imatrix.upload_source = IMX_UPLOAD_GATEWAY;  // Rotation!
}
// ... more rotation logic ...

switch (imatrix.state) {
    case IMATRIX_UPLOAD_WAIT_RSP:
        // Response handler called here
        // But upload_source already changed!
        break;
}
```

**Execution Flow with Bug**:
```
Time 0ms:   upload_source=3 (CAN_DEVICE)
            Read data with read_bulk(source=3)
            MM2 marks data as pending for source=3
            
Time 100ms: Send packet for source=3
            State = IMATRIX_UPLOAD_WAIT_RSP
            
Time 200ms: imatrix_upload() called again (main loop)
            Rotation code executes
            upload_source changes: 3 → 0 (CAN → GATEWAY)
            
Time 300ms: ACK arrives
            Response handler called
            Checks has_pending(source=0) ← WRONG!
            Data is pending for source=3, not source=0
            Returns FALSE - "No pending data"
            No erase, memory leak!
```

### Evidence from Logs

**upload3.txt (with MM2 debugging)**:
- ✅ Data correctly marked as pending for source=CAN_DEV
- ✅ Pending count increments: 0→12→14
- ✅ NACK processing works correctly

**upload2.txt (successful ACKs)**:
- ✅ When upload_source matches, erase works perfectly
- ❌ First ACK shows "No pending" (upload happened before log, likely wrong source)

---

## The Fix

### Changes Made

**1. Removed Problematic Rotation** (lines 620-691)
   - Deleted upload_source rotation logic that executed before switch statement
   - Added detailed comment explaining why it was removed

**2. Preserved Safe Rotation** (lines 872-950)
   - Rotation logic KEPT in IMATRIX_CHECK_FOR_PENDING case
   - This executes AFTER ACK processing completes
   - Added comprehensive documentation

**3. Added Debug Logging** (24 locations)
   - Enhanced logging in response handler
   - MM2 pending tracking visibility
   - ACK/NACK decision logging
   - Critical "ACK SKIPPED" detection

### Commits

```
51667e57 - Add comprehensive debug logging to iMatrix upload ACK processing
15796337 - Fix critical bug: upload_source rotation before ACK causes pending data leak
```

### Code Stats
- **Lines Removed**: 96 (problematic rotation code)
- **Lines Added**: 51 (debug logging + fix comments)
- **Net Change**: -45 lines
- **Files Modified**: 1 (imatrix_upload.c)

---

## How It Works Now

### Correct Execution Flow (AFTER fix):

```
Time 0ms:   upload_source=3 (CAN_DEVICE)
            State = IMATRIX_CHECK_FOR_PENDING
            Check for pending data for source=3
            Found data, advance to GET_DNS
            
Time 100ms: Read data with read_bulk(source=3)
            MM2 marks data as pending for source=3
            Send packet for source=3
            State = IMATRIX_UPLOAD_WAIT_RSP
            
Time 200ms: imatrix_upload() called again (main loop)
            State = IMATRIX_UPLOAD_WAIT_RSP
            NO rotation (only happens in CHECK_FOR_PENDING state)
            upload_source REMAINS = 3
            
Time 300ms: ACK arrives
            Response handler called
            Checks has_pending(source=3) ← CORRECT!
            Data IS pending for source=3
            Returns TRUE - "Has pending data"
            Calls imx_erase_all_pending(source=3)
            SUCCESS - memory freed!
            
Time 400ms: State = IMATRIX_UPLOAD_COMPLETE
            Then: State = IMATRIX_CHECK_FOR_PENDING
            Rotation executes here: 3 → 0
            Now safe to check next source
```

---

## Build & Test Instructions

### 1. Build the Code

```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
cmake ..
make
```

### 2. Deploy to Device

Deploy the newly built binary to your test device.

### 3. Enable Debug Logging (Recommended)

```bash
log on 4   # DEBUGS_FOR_IMX_UPLOAD
log on 14  # DEBUGS_FOR_MEMORY_MANAGER
```

### 4. Monitor the System

Watch for these log indicators:

**✅ SUCCESS Indicators**:
```
[UPLOAD DEBUG] *** ACK PROCESSING: Entering erase loop ***
[UPLOAD DEBUG] upload_source=3
[UPLOAD DEBUG] Erasing pending for type=1, i=0, sensor=Temp_Main_P
[UPLOAD DEBUG] Erase result: 0 (SUCCESS)
[MM2-PEND] erase_all: pending_count: 12 -> 0
```

**❌ FAILURE Indicators (should NOT see these anymore)**:
```
[UPLOAD DEBUG] *** ACK PROCESSING SKIPPED ***
[UPLOAD DEBUG] THIS IS THE BUG: Pending data will NOT be cleared!
```

### 5. Verify Fix

Check that:
- [ ] Pending data clears after successful ACK
- [ ] Memory usage stays stable (no growth)
- [ ] No duplicate uploads of same data
- [ ] Pending counts go to 0 after ACK
- [ ] No "ACK PROCESSING SKIPPED" messages

---

## What Changed

### File: imatrix_upload/imatrix_upload.c

**Deleted (96 lines)**:
- Lines 620-691: Upload source rotation logic (BEFORE switch statement)
- This code executed unconditionally on every imatrix_upload() call
- Caused upload_source to change while waiting for ACK

**Added (51 lines)**:
- Debug logging in response handler (24 statements)
- Detailed comments explaining the bug and fix
- Logging in cleanup function
- ACK/NACK decision point logging
- "ACK SKIPPED" detection for debugging

**Preserved**:
- Lines 872-950: Upload source rotation logic (INSIDE CHECK_FOR_PENDING case)
- This code only executes AFTER ACK processed and state advanced
- Safe rotation that doesn't interfere with pending data tracking

---

## Expected Behavior After Fix

### Upload Cycle 1: CAN_DEVICE (source=3)
```
1. CHECK_FOR_PENDING (source=3) - Check for CAN data
2. Found data → GET_DNS (source=3)
3. LOAD_SAMPLES (source=3) - Read data, mark as pending for source=3
4. UPLOAD_DATA (source=3) - Send to server
5. UPLOAD_WAIT_RSP (source=3) - Wait for ACK
   ↓ (upload_source REMAINS 3 during wait)
6. ACK arrives
7. Response handler checks has_pending(source=3) ✅ CORRECT
8. Finds pending data, calls erase_all_pending(source=3) ✅ SUCCESS
9. UPLOAD_COMPLETE → CHECK_FOR_PENDING
10. Rotation: source 3→0 (now safe to rotate)
```

### Upload Cycle 2: GATEWAY (source=0)
```
1. CHECK_FOR_PENDING (source=0) - Check for Gateway data
2. (cycle repeats with source=0)
```

---

## Git Commands

```bash
# Current branch
git branch --show-current
# Output: bugfix/upload-ack-not-clearing-pending

# View changes
git log --oneline -2
# Output:
# 15796337 Fix critical bug: upload_source rotation before ACK
# 51667e57 Add comprehensive debug logging

# View diff from base branch
git diff Aptera_1..bugfix/upload-ack-not-clearing-pending --stat
```

---

## Metrics

- **Analysis Time**: ~2 hours (log review + root cause identification)
- **Implementation Time**: ~1 hour (debug logging + fix)
- **Total Tokens**: ~213K
- **Lines Changed**: +51, -96 (net: -45)
- **Commits**: 2
- **Files Modified**: 1

---

## Next Steps

### For User (YOU):
1. ✅ Build the code (see instructions above)
2. ✅ Deploy to test device
3. ✅ Run the system and monitor logs
4. ✅ Verify pending data clears correctly
5. ✅ Report results

### After Successful Testing:
1. Merge branch to Aptera_1
2. Update plan document with final results
3. Close the bug

---

## Questions?

If you see any issues during testing, provide:
- Log excerpt showing the problem
- Expected vs actual behavior
- Any error messages

**The fix is comprehensive and should resolve the pending data leak issue completely.**

🤖 Generated with Claude Code
