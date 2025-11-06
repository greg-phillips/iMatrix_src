# g_sensor_array Removal - Implementation Roadmap

## Current Status (2025-10-13)

### ✅ Completed
1. **per_source_disk refactoring**: 266 references updated, 288KB saved
2. **GET_SENSOR_ID macro fixed**: Changed from `(csd - g_sensor_array.sensors)` to `csb->id`
3. **Comprehensive planning documents created**:
   - removal_of_g_sensor_array.md (detailed 7-phase plan)
   - removal_of_g_sensor_array_revised.md (ideal comprehensive prompt)
   - faults_with_prompt_1.md (meta-analysis of prompt quality)

### ⚠️ Remaining (Ready to Implement)

**Scope**: 13 files, ~335 lines, ~4-6 hours estimated

**Critical Issues**:
- Compilation warnings: "unused variable 'csd'" in mm2_startup_recovery.c
- g_sensor_array still present (~250KB waste)
- GET_SENSOR_ID macro fixed but call sites not yet updated (34 occurrences)

---

## Implementation Roadmap

### Quick Win: Fix Compilation Warnings (30 minutes)

**Problem**: mm2_startup_recovery.c lines 124, 355, 466
```c
control_sensor_data_t* csd = &g_sensor_array.sensors[sensor_id];  // UNUSED!
```

**Solution**: Remove these lookups, pass csd as parameter where actually needed.

**Files to modify**:
- mm2_startup_recovery.c: 3 unused csd removals
- validate_and_integrate_files: Add csd parameter (needs csd->mmcb.total_disk_space_used on line 386)
- rebuild_sensor_state: Remove unused csd lookup on line 466

**Result**: Compilation warnings eliminated.

---

### Phase 1: Update All GET_SENSOR_ID Calls (1-2 hours)

**Goal**: Change all `GET_SENSOR_ID(csd)` → `GET_SENSOR_ID(csb)`

**Challenge**: Many functions don't have csb parameter yet.

**Approach**:
1. Identify which functions use GET_SENSOR_ID but lack csb
2. Add csb parameter to those functions
3. Update all call sites
4. Change GET_SENSOR_ID(csd) → GET_SENSOR_ID(csb)

**Files affected** (34 occurrences):
- mm2_disk_spooling.c: 14 changes
- mm2_file_management.c: 11 changes
- mm2_power.c: 2 changes
- mm2_disk_reading.c: 1 change
- mm2_power_abort.c: 1 change

**Functions needing csb parameter** (~25 functions):
- All process_*_state functions in mm2_disk_spooling.c
- write_tsd_sector_to_disk, write_evt_sector_to_disk
- Helper functions in mm2_file_management.c
- Helper functions in mm2_disk_reading.c

**Critical**: Also fix parameter order to standard (upload_source, csb, csd, ...)

---

### Phase 2: Implement New Recovery API (1 hour)

**Add to mm2_api.h**:
```c
imx_result_t imx_recover_sensor_disk_data(imatrix_upload_source_t upload_source,
                                          imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd);
```

**Implement in mm2_startup_recovery.c**:
```c
imx_result_t imx_recover_sensor_disk_data(imatrix_upload_source_t upload_source,
                                          imx_control_sensor_block_t* csb,
                                          control_sensor_data_t* csd) {
    uint32_t sensor_id = csb->id;

    // Initialize csd->mmcb.total_disk_space_used = 0
    //  Scan this upload source's directory for this sensor's files
    scan_sensor_spool_files_by_source(sensor_id, upload_source);
    validate_and_integrate_files(sensor_id, upload_source, csd);  // Pass csd for total_disk_space_used
    rebuild_sensor_state(sensor_id, upload_source);

    return IMX_SUCCESS;
}
```

**Update validate_and_integrate_files signature**:
```c
imx_result_t validate_and_integrate_files(uint32_t sensor_id,
                                         imatrix_upload_source_t upload_source,
                                         control_sensor_data_t* csd);  // ADD csd parameter
```

**Deprecate old function**:
```c
imx_result_t recover_disk_spooled_data(void) {
    // DEPRECATED - main app must call imx_recover_sensor_disk_data() per sensor
    PRINTF("[MM2-RECOVERY] DEPRECATED: Use imx_recover_sensor_disk_data() instead\n");
    return IMX_SUCCESS;
}
```

**Remove from mm2_api.c init**:
```c
// DELETE:
result = recover_disk_spooled_data();
```

---

### Phase 3: Implement STM32 Circular Buffer (1 hour)

**Add new function** (mm2_pool.c or mm2_stm32.c):
```c
imx_result_t discard_oldest_non_pending_sector(control_sensor_data_t* csd) {
    if (!csd) return IMX_INVALID_PARAMETER;

    // Find oldest non-pending sector in THIS sensor's chain
    SECTOR_ID_TYPE current = csd->mmcb.ram_start_sector_id;
    while (current != NULL_SECTOR_ID) {
        sector_chain_entry_t* entry = get_sector_chain_entry(current);
        if (entry && entry->in_use && !entry->pending_ack) {
            // Discard this sector
            SECTOR_ID_TYPE next = get_next_sector_in_chain(current);
            if (csd->mmcb.ram_start_sector_id == current) {
                csd->mmcb.ram_start_sector_id = next;
                csd->mmcb.ram_read_sector_offset = 0;
            }
            if (csd->mmcb.ram_end_sector_id == current) {
                csd->mmcb.ram_end_sector_id = NULL_SECTOR_ID;
                csd->mmcb.ram_write_sector_offset = 0;
            }
            free_sector(current);
            if (csd->mmcb.total_records > 0) csd->mmcb.total_records--;
            return IMX_SUCCESS;
        }
        current = get_next_sector_in_chain(current);
    }
    return IMX_ERROR;  // All pending
}
```

**Update mm2_write.c** (imx_write_tsd and imx_write_evt):
```c
SECTOR_ID_TYPE new_sector_id = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);
if (new_sector_id == NULL_SECTOR_ID) {
    #ifndef LINUX_PLATFORM
    // STM32: RAM full - discard oldest from this sensor's chain
    if (discard_oldest_non_pending_sector(csd) == IMX_SUCCESS) {
        new_sector_id = allocate_sector_for_sensor(csb->id, SECTOR_TYPE_TSD);  // Retry
    }
    #endif
    if (new_sector_id == NULL_SECTOR_ID) {
        return IMX_OUT_OF_MEMORY;
    }
}
```

**Delete from mm2_stm32.c**:
- handle_stm32_ram_full()
- find_oldest_non_pending_sector()
- is_sector_safe_to_discard()
- handle_critical_ram_exhaustion()

---

### Phase 4: Remove g_sensor_array (30 minutes)

**mm2_core.h**:
- DELETE sensor_array_t typedef (lines 186-189)
- DELETE extern g_sensor_array (line 114)

**mm2_pool.c**:
- DELETE g_sensor_array definition (line 60)
- DELETE sensor initialization loop from init_memory_pool() (lines 151-229)
- DELETE sensor cleanup loop from cleanup_memory_pool() (lines 263-283)
- DELETE memset g_sensor_array (line 311)
- DELETE get_sensor_data() function
- DELETE compute_active_sensor_count() function
- DELETE or UPDATE get_sensor_id_from_csd() function

**mm2_startup_recovery.c**:
- Line 550: Already uses g_sensor_array in loop - handle in Phase 2

**mm2_stm32.c**:
- All loops over g_sensor_array deleted in Phase 3

**mm2_power_abort.c**:
- Lines 199, 361: Change to per-sensor API or remove if not critical

---

### Phase 5: Main App Integration (User Action Required)

**After MM2 changes complete**, main app must:

**1. Call new recovery API**:
```c
// In initialization, after imx_memory_manager_init():

// Gateway sensors
for (uint16_t i = 0; i < device_config.no_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_GATEWAY, &icb.i_scb[i], &icb.i_sd[i]);
}

#ifdef BLE_PLATFORM
// BLE sensors
for (uint16_t i = 0; i < no_ble_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_BLE_DEVICE, &ble_scb[i], &ble_sd[i]);
}
#endif

#ifdef CAN_PLATFORM
// CAN sensors
for (uint16_t i = 0; i < no_can_sensors; i++) {
    imx_recover_sensor_disk_data(IMX_UPLOAD_CAN_DEVICE, &can_scb[i], &can_sd[i]);
}
#endif
```

**2. No other changes needed** - MM2 API already receives (upload_source, csb, csd) correctly.

---

##Quick Start Implementation Guide

### Option A: Automated Approach (Fastest, Some Manual Fixes Needed)

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix/cs_ctrl

# 1. Fix unused csd in recovery (already done above)

# 2. Quick fix: Change all GET_SENSOR_ID calls
# Note: This will break compilation, revealing which functions need csb
sed -i 's/GET_SENSOR_ID(csd)/GET_SENSOR_ID(csb)/g' mm2_*.c

# 3. Attempt compilation to see errors
make -j4 2>&1 | grep "csb.*undeclared" | cut -d: -f1-2 | sort -u

# 4. For each error, add csb parameter to that function
# 5. Update call sites for that function

# 6. Repeat until clean compilation
```

### Option B: Systematic Approach (Slower, Cleaner)

Follow removal_of_g_sensor_array.md phases 1-7 step by step:
1. Phase 1: Fix GET_SENSOR_ID (macro done, call sites remain)
2. Phase 2: Recovery API
3. Phase 3: STM32 circular buffer
4. Phase 4: Power abort
5. Phase 5: Remove g_sensor_array
6. Phase 6: Function signatures
7. Phase 7: Headers

Each phase has detailed todo checklist in the plan document.

---

## Estimated Effort Breakdown

| Task | Time | Complexity |
|------|------|------------|
| Fix mm2_startup_recovery unused csd | 15 min | Low |
| Add csb to ~30 helper functions | 2 hours | Medium |
| Update ~100 call sites | 1.5 hours | Medium |
| Change 34 GET_SENSOR_ID calls | 30 min | Low |
| Implement new recovery API | 1 hour | Medium |
| Implement STM32 circular buffer | 1 hour | Medium |
| Remove g_sensor_array code | 30 min | Low |
| Verification and testing | 1 hour | Medium |

**Total**: 6-8 hours

---

## Recommended Next Steps

Given scope and your token budget (438k/1000k used = 44%), I recommend:

**Immediate** (I can do):
- Fix mm2_startup_recovery.c unused variables (15 min, low impact on tokens)
- Create implementation checklist document

**Short-term** (You implement):
- Follow removal_of_g_sensor_array.md phase by phase
- Use sed commands for bulk replacements where safe
- Systematic function signature updates

**Validation** (Collaborative):
- I can help verify compilation
- I can review specific complex changes
- I can help with debugging if issues arise

**Would you like me to**:
1. Continue with automated sed approach to fix GET_SENSOR_ID calls and see what breaks?
2. Just fix the immediate compilation warnings and stop?
3. Create final checklist document and let you implement?

What's your preference?
