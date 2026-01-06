# Lockup Investigation Plan - imatrix_upload() Infinite Loop

**Date**: 2026-01-06
**Status**: IMPLEMENTED v2 - Awaiting 24hr Test (comprehensive fix)
**Priority**: Critical
**Author**: Claude Code Analysis
**Branch**: feature/Lockup_fix_plan_1
**Current Branches**: iMatrix: `Aptera_1_Clean`, Fleet-Connect-1: `Aptera_1_Clean`
**Implementation Date**: 2026-01-06
**Build Date**: 2026-01-06 06:59 UTC

---

## Executive Summary

The FC-1 system experiences a complete main loop lockup approximately 2 hours after boot. The root cause has been identified as an **infinite loop vulnerability** in the `imx_read_bulk_samples()` function in `mm2_read.c`. A sector chain traversal loop lacks a safety counter, allowing corrupted chain data to cause infinite looping while holding a mutex.

---

## Problem Analysis

### Symptoms Observed

| Metric | Value |
|--------|-------|
| **Device** | 10.2.0.169 |
| **Boot Time** | 2026-01-06T04:17:12 UTC |
| **Lock Occurred** | 2026-01-06T06:19:59 UTC |
| **Time to Lockup** | ~2h 2m 47s (7367 sec) |
| **Loop Executions Before Lock** | 48,228 |
| **Blocking Position** | 50 (inside `imatrix_upload()`) |
| **Process State** | `R (running)` - CPU active, in infinite loop |

### Current Device State (as of investigation)

```
FC-1 Process:
  State:    R (running)  <-- Actively executing, NOT blocked on mutex
  VmSize:   17564 kB
  VmRSS:    7544 kB
  Threads:  7

Memory Status:
  RAM Utilization: >= 80%
  Disk Spillover:  Active
```

### Key Log Observations

1. **Last MM2 activity before lockup**: 06:23:21
2. **No main loop activity**: Gap from 06:23:21 to 08:06:17 (1h 43m)
3. **Background threads continue**: GPS NMEA errors logged throughout
4. **Memory pressure**: RAM at 80%, continuous disk spillover for sensor data

---

## Root Cause Analysis

### Identified Issue: Missing Safety Counter in Sector Chain Loop

**File**: `iMatrix/cs_ctrl/mm2_read.c`
**Function**: `imx_read_bulk_samples()`
**Line**: 882-924

```c
// Line 882-924: VULNERABLE LOOP - No safety counter!
while (current_sector != NULL_SECTOR_ID) {
    memory_sector_t* sector = &g_memory_pool.sectors[current_sector];
    sector_chain_entry_t* entry = get_sector_chain_entry(current_sector);

    if (!entry || !entry->in_use) {
        current_sector = get_next_sector_in_chain(current_sector);  // Could loop forever
        current_offset = 0;
        continue;
    }
    // ... processing ...
    current_sector = get_next_sector_in_chain(current_sector);  // Could loop forever
}
```

### Why This Causes Infinite Loop

1. **No iteration limit**: Unlike other loops in the same function (line 777 has `freed_sectors_skipped > g_memory_pool.total_sectors` check), this loop has no maximum iteration counter.

2. **Chain corruption scenarios**:
   - Sector A's `next_sector_id` points to Sector B
   - Sector B's `next_sector_id` points back to Sector A (circular reference)
   - Loop never terminates because `current_sector` never becomes `NULL_SECTOR_ID`

3. **Mutex held during loop**:
   - Mutex acquired at line 619: `pthread_mutex_lock(&csd->mmcb.sensor_lock);`
   - Never released because loop never completes
   - Other threads blocked on same sensor

4. **Trigger conditions**:
   - RAM at 80% capacity triggers disk spillover
   - High frequency of sensor writes (CAN bus data)
   - Chain table corruption during concurrent operations

### Comparison: Protected vs Unprotected Loops

| Loop Location | Safety Counter | Vulnerability |
|---------------|----------------|---------------|
| Line 692-743 | `records_skipped < existing_pending` | Protected |
| Line 777-820 | `freed_sectors_skipped > g_memory_pool.total_sectors` | Protected |
| Line 854-950 | `i < requested_count` (bounded) | Protected |
| **Line 882-924** | **NONE** | **VULNERABLE** |

---

## Proposed Fix

### Phase 1: Add Safety Counter to Vulnerable Loop

**Location**: `iMatrix/cs_ctrl/mm2_read.c`, lines 882-924

```c
// BEFORE (vulnerable):
while (current_sector != NULL_SECTOR_ID) {
    // ... loop body ...
    current_sector = get_next_sector_in_chain(current_sector);
}

// AFTER (protected):
uint32_t sectors_visited = 0;
const uint32_t max_sectors = g_memory_pool.total_sectors;

while (current_sector != NULL_SECTOR_ID) {
    // Safety limit to prevent infinite loop on corrupted chain
    if (++sectors_visited > max_sectors) {
        LOG_MM2_CORRUPT("read_bulk: CHAIN CORRUPTION - exceeded max sectors (%u) "
                       "during RAM read loop, sensor=%s, current_sector=%u",
                       max_sectors, csb->name, current_sector);
        result = IMX_ERROR_CHAIN_CORRUPTION;
        break;
    }

    // ... existing loop body ...
    current_sector = get_next_sector_in_chain(current_sector);
}
```

### Phase 2: Add Chain Integrity Validation

Add a helper function to detect circular references:

```c
/**
 * @brief Validate sector chain has no cycles using Floyd's algorithm
 * @param start_sector Starting sector of chain
 * @param sensor_name For logging purposes
 * @return true if chain is valid, false if cycle detected
 */
static bool mm2_validate_chain_no_cycles(SECTOR_ID_TYPE start_sector, const char* sensor_name) {
    if (start_sector == NULL_SECTOR_ID) {
        return true;  // Empty chain is valid
    }

    SECTOR_ID_TYPE slow = start_sector;
    SECTOR_ID_TYPE fast = start_sector;
    uint32_t steps = 0;
    const uint32_t max_steps = g_memory_pool.total_sectors;

    while (fast != NULL_SECTOR_ID) {
        // Move slow pointer one step
        slow = get_next_sector_in_chain(slow);

        // Move fast pointer two steps
        fast = get_next_sector_in_chain(fast);
        if (fast != NULL_SECTOR_ID) {
            fast = get_next_sector_in_chain(fast);
        }

        // If they meet, there's a cycle
        if (slow == fast && slow != NULL_SECTOR_ID) {
            LOG_MM2_CORRUPT("validate_chain: CYCLE DETECTED at sector=%u, sensor=%s",
                           slow, sensor_name);
            return false;
        }

        // Safety limit
        if (++steps > max_steps) {
            LOG_MM2_CORRUPT("validate_chain: Chain too long (>%u), sensor=%s",
                           max_steps, sensor_name);
            return false;
        }
    }

    return true;
}
```

### Phase 3: Enhance Existing Validation

Update `mm2_validate_sensor_chain()` to include cycle detection:

```c
bool mm2_validate_sensor_chain(control_sensor_data_t* csd, const char* sensor_name) {
    // Existing validation...

    // Add cycle detection
    if (!mm2_validate_chain_no_cycles(csd->mmcb.ram_start_sector_id, sensor_name)) {
        return false;
    }

    return true;
}
```

---

## Implementation Todo List

### Pre-Implementation
- [ ] Note current branches (iMatrix: `Aptera_1_Clean`, Fleet-Connect-1: `Aptera_1_Clean`)
- [ ] Create feature branch: `git checkout -b feature/Lockup_fix_plan_1`

### Code Changes
- [ ] Add safety counter to loop at line 882-924 in `mm2_read.c`
- [ ] Add `mm2_validate_chain_no_cycles()` helper function
- [ ] Update `mm2_validate_sensor_chain()` to call new validator
- [ ] Add `IMX_ERROR_CHAIN_CORRUPTION` error code if not exists
- [ ] Add appropriate logging for corruption detection

### Testing
- [ ] Build and verify zero warnings/errors
- [ ] Deploy to test device
- [ ] Run for extended period (>2 hours) to verify fix
- [ ] Monitor logs for any corruption warnings

### Documentation
- [ ] Update MM2_Developer_Guide.md with chain corruption handling
- [ ] Update this plan with implementation results

---

## Files to Modify

| File | Change |
|------|--------|
| `iMatrix/cs_ctrl/mm2_read.c` | Add safety counter to loop at line 882-924 |
| `iMatrix/cs_ctrl/mm2_read.c` | Add `mm2_validate_chain_no_cycles()` function |
| `iMatrix/cs_ctrl/mm2_pool.c` | Potentially add cycle detection to chain operations |
| `iMatrix/cs_ctrl/mm2_internal.h` | Add function declaration if needed |
| `iMatrix/common.h` | Add `IMX_ERROR_CHAIN_CORRUPTION` if not exists |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fix introduces new bugs | Low | Small, localized change; extensive testing |
| Performance impact | Very Low | Safety counter adds negligible overhead |
| Chain corruption continues | Medium | Fix prevents infinite loop but not root cause |

---

## Questions for User

1. **Root Cause Investigation**: Should we also investigate WHY the chain corruption occurs, or is preventing the infinite loop sufficient for now?

2. **Logging Level**: Should corruption warnings trigger any additional alerts (LED, network notification)?

3. **Recovery Strategy**: When corruption is detected, should we:
   - (a) Skip the corrupted sensor and continue
   - (b) Reset the corrupted sensor's chain entirely
   - (c) Both, with option to configure behavior

4. **Testing Duration**: How long should the fix be tested before merging (2 hours? 24 hours? longer)?

---

## References

- Previous investigation: `/home/greg/iMatrix/iMatrix_Client/docs/loop_stuck_investigation.md`
- MM2 Developer Guide: `iMatrix/cs_ctrl/MM2_Developer_Guide.md`
- MM2 API Guide: `iMatrix/cs_ctrl/docs/MM2_API_GUIDE.md`

---

## Implementation Summary (2026-01-06)

### Changes Made

**File**: `iMatrix/cs_ctrl/mm2_read.c` (lines 882-924)

Added safety counter to the vulnerable loop in `imx_read_bulk_samples()`:

```c
/*
 * LOCKUP FIX: Safety counter to prevent infinite loop on corrupted chain
 * Without this counter, a circular chain reference could cause the main
 * loop to lock up indefinitely (see Lockup_fix_1_plan.md for details).
 */
uint32_t sectors_visited = 0;
const uint32_t max_sectors = g_memory_pool.total_sectors;

while (current_sector != NULL_SECTOR_ID) {
    /*
     * LOCKUP FIX: Check safety counter before processing
     * If we've visited more sectors than exist, chain is corrupted
     */
    if (++sectors_visited > max_sectors) {
        LOG_MM2_CORRUPT("read_bulk: CHAIN CORRUPTION - exceeded max sectors (%u) "
                       "during RAM read loop, sensor=%s, start_sector=%u, current=%u",
                       max_sectors, csb->name, read_start_sector, current_sector);
        /*
         * Reset corrupted chain to prevent further issues
         * Per user requirement: reset chain entirely when corruption detected
         */
        csd->mmcb.ram_start_sector_id = NULL_SECTOR_ID;
        csd->mmcb.ram_end_sector_id = NULL_SECTOR_ID;
        csd->mmcb.ram_read_sector_offset = 0;
        csd->mmcb.ram_write_sector_offset = 0;
        csd->mmcb.total_records = 0;
        result = IMX_ERROR;
        break;
    }
    // ... existing loop body ...
}
```

### Root Cause Analysis Findings

Investigation revealed potential race condition between disk spooling and read operations:

1. **Disk spooling** calls `free_sector()` WITHOUT holding `sensor_lock` mutex
2. **Read operations** hold `sensor_lock` but iterate through chain
3. `free_sector()` clears `next_sector_id = NULL_SECTOR_ID` which should terminate chains
4. However, sector re-allocation can create new chain links
5. Circular reference can occur when chains cross due to race timing

The fix is defensive - it prevents infinite loops regardless of the specific corruption mechanism.

### Build Status

- **Build Date**: 2026-01-06 06:59 UTC
- **Compiler**: arm-linux-gcc (QConnect SDK)
- **Warnings**: Zero new warnings
- **Errors**: Zero
- **Binary Size**: 12,697,484 bytes

### Implementation Checklist

- [x] Add safety counter to loop at line 882-924 in `mm2_read.c`
- [x] Add corruption logging using existing `LOG_MM2_CORRUPT` macro
- [x] Reset chain when corruption detected (per user requirement)
- [x] Build and verify zero warnings/errors
- [x] Deploy to test devices
- [ ] Run for 24 hours to verify fix
- [ ] Monitor logs for any corruption warnings

### Deployment Status (2026-01-06 15:16 UTC)

| Device | Boot Time | Status | Notes |
|--------|-----------|--------|-------|
| 10.2.0.169 | 2026-01-06T15:13:43 UTC | Running | Primary test device |
| 10.2.0.179 | 2026-01-06T15:15:31 UTC | Running | Secondary test device |

**24-Hour Test Period**: 2026-01-06 15:16 UTC to 2026-01-07 15:16 UTC

### Notes

- Used existing `IMX_ERROR` instead of adding new `IMX_ERROR_CHAIN_CORRUPTION` (simpler approach)
- Chain validation function already exists and is called at entry to `imx_read_bulk_samples()`
- Fix is minimal and localized to reduce risk of introducing new bugs

---

## Implementation v2 (2026-01-06 17:00 UTC)

### Issue: First Fix Incomplete

After deploying the initial fix, both devices locked up again (within 11 minutes vs original 2 hours). Investigation revealed:
- No "CHAIN CORRUPTION" messages in logs
- The fixed loop (line 882-924) was NOT the one causing the lockup
- Additional vulnerable loops existed in mm2_read.c without safety counters

### Additional Loops Fixed

All sector chain traversal loops in `mm2_read.c` now have safety counters:

| Location | Function | Line | Fixed |
|----------|----------|------|-------|
| 1 | `imx_read_bulk_samples()` | ~890 | Previously fixed |
| 2 | `imx_read_next_tsd_evt()` | ~1113 | **NEW** |
| 3 | `imx_erase_all_pending()` scan | ~1618 | **NEW** |
| 4 | `free_sector_and_update_chain()` | ~1753 | **NEW** |
| 5 | `imx_peek_next_tsd_evt()` | ~1975 | **NEW** |
| 6 | `imx_peek_bulk_samples()` skip | ~2085 | **NEW** |
| 7 | `imx_peek_bulk_samples()` read | ~2172 | **NEW** |

### Fix Pattern Applied

```c
/*
 * LOCKUP FIX: Safety counter to prevent infinite loop on corrupted chain
 */
uint32_t sectors_visited = 0;
const uint32_t max_sectors = g_memory_pool.total_sectors;

while (current_sector != NULL_SECTOR_ID) {
    /*
     * LOCKUP FIX: Check safety counter before processing
     */
    if (++sectors_visited > max_sectors) {
        LOG_MM2_CORRUPT("function_name: CHAIN CORRUPTION - exceeded max sectors (%u) "
                       "sensor=%s",
                       max_sectors, csb->name);
        #ifdef LINUX_PLATFORM
        pthread_mutex_unlock(&csd->mmcb.sensor_lock);
        #endif
        return IMX_ERROR;
    }
    // ... existing loop body ...
}
```

### Additional Fix: ubx_gps.c

Fixed pre-existing uninitialized variable warning in `ubx_print_statistics()`:
```c
ubx_status_t status = {0};  /* Initialize to zero in case ubx_get_status returns early */
```

### Build Status v2

- **Build Date**: 2026-01-06 16:56 UTC
- **Binary Size**: 13,350,968 bytes
- **Warnings**: Zero new warnings
- **Errors**: Zero

### Deployment Status v2 (2026-01-06 17:03 UTC)

| Device | PID | Status | Notes |
|--------|-----|--------|-------|
| 10.2.0.169 | 8916 | Running | Restarted with new binary |
| 10.2.0.179 | 13694 | Running | Restarted with new binary |

**Note**: Previous processes (PID 27753 and 2952) required SIGKILL - consistent with infinite loop lockup.

**24-Hour Test Period v2**: 2026-01-06 17:03 UTC to 2026-01-07 17:03 UTC

---

## Investigation v3 (2026-01-06 17:44 UTC)

### Issue Discovered: Incorrect Binary Deployed

After enabling automated monitoring, a lockup was detected on device 10.2.0.179 at 17:34:13 UTC (28 minutes after boot). Analysis revealed:

1. **No CHAIN CORRUPTION messages** in logs - safety counters never triggered
2. **Binary MD5 mismatch**: Devices had old binary (`a7eff929992d9d15bc6728eebc7dc548`, 12.7MB) instead of fixed binary (`1c3395d08272992f189bfd6047260b90`, 13.3MB)
3. **Root cause**: Previous `fc1 restart` commands didn't update the binary - only `fc1 push -run` deploys new code

### Log Evidence

Last activity before lockup showed heavy disk spillover:
```
[00:34:34.632] [MM2-WR] RAM >= 80%, routing EVT to disk for sensor=Vehicle_Speed
[00:34:34.632] [TIERED] Flushed 2 EVT pairs to disk for sensor 142
```

Process state confirmed infinite loop:
```
State:	R (running)
Pid:	13694
nonvoluntary_ctxt_switches:	800186  <-- high count indicates busy loop
```

### Corrective Action

Re-deployed correct binary to both devices using `fc1 push -run`:
- 10.2.0.169: Deployed 17:45 UTC
- 10.2.0.179: Deployed 17:44 UTC

Verified MD5 matches on both devices: `1c3395d08272992f189bfd6047260b90`

### Lesson Learned

**Always verify binary deployment with MD5 checksum** - `fc1 restart` only restarts the service, it does NOT update the binary. Use `fc1 push -run` to deploy new code.

**24-Hour Test Period v3**: 2026-01-06 17:45 UTC to 2026-01-07 17:45 UTC

---

**Plan Created By:** Claude Code
**Generated:** 2026-01-06
**Implemented:** 2026-01-06
**Updated:** 2026-01-06 (v2 - comprehensive loop fixes)
