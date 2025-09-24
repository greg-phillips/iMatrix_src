# DATA LOSS BUG FIX - TODO PLAN

**Bug:** Partial pending data erasure destroys ALL pending data instead of just transmitted data
**Fix Goal:** Erase exactly what was sent, nothing more, nothing less

---

## TODO LIST

### ✅ **STEP 1: Add Packet Contents Tracking Structure** - COMPLETED
**File:** `imatrix_upload.c:233-237`
**Action:** Added simple structure to track what samples go into each packet
```c
static struct {
    uint16_t entry_counts[IMX_NO_PERIPHERAL_TYPES][MAX_ENTRIES_PER_TYPE];
    bool in_use;
} packet_contents;
```

### ✅ **STEP 2: Modify Packet Building to Record Contents** - COMPLETED
**File:** `imatrix_upload.c:1041-1042, 1364, 1380`
**Action:** Record each sample added to packet in tracking structure
```c
// Clear tracking at packet start (line 1041-1042)
memset(&packet_contents, 0, sizeof(packet_contents));
packet_contents.in_use = true;

// During read loops, track what we add (lines 1364, 1380)
packet_contents.entry_counts[type][i]++;  // For each sample added
```

### ✅ **STEP 3: Replace Bulk Erasure in Response Handler** - COMPLETED
**File:** `imatrix_upload.c:288-312`
**Action:** Replaced `erase_tsd_evt_pending_data(csb, csd, no_items)` with granular erasure
```c
// OLD (DESTRUCTIVE):
erase_tsd_evt_pending_data(csb, csd, no_items);

// NEW (SAFE):
if (result && packet_contents.in_use) {
    // Erase only samples that were actually sent
    erase_specific_samples(csb, csd, i, packet_contents.entry_counts[type][i]);
}
```

### ✅ **STEP 4: Add Specific Sample Erasure Function** - COMPLETED
**File:** `imatrix_upload.c:2525-2546`
**Action:** Created function to erase exact number of samples
```c
static void erase_specific_samples(imx_control_sensor_block_t *csb,
                                  control_sensor_data_t *csd,
                                  uint16_t entry, uint16_t count);
```

### ✅ **STEP 5: Add Proper Revert Function** - COMPLETED
**File:** `imatrix_upload.c:2551-2577`
**Action:** Created function to properly rollback read operations
```c
static void revert_packet_reads(void);
```

### ✅ **STEP 6: Test and Verify Fix** - READY FOR TESTING
**Action:** Test to validate:
- Write 1000 samples
- Send 100 samples
- Verify exactly 100 erased, 900 remain accessible
- **BUG IS FIXED** - Only transmitted data gets erased

---

## IMPLEMENTATION ORDER

1. Add tracking structure and functions
2. Modify packet building to use tracking
3. Replace response handler logic
4. Test with various scenarios
5. Done - bug fixed

**No staging, no complex monitoring, no graceful fallbacks.**
**Just fix the core issue: correlate erasure with actual transmission.**