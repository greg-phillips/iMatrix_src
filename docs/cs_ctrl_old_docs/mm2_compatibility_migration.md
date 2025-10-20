# mm2_compatibility.c Migration Plan - Complete Call Site Analysis

**Date**: 2025-10-13
**Task**: Replace all mm2_compatibility wrapper calls with direct MM2 API calls
**Goal**: Remove mm2_compatibility.c from build

---

## Executive Summary

**Total Active Callers**: 7 locations (production code only, excluding tests)

**Functions to Replace**:
1. `write_tsd_evt()` - 5 call sites (production)
2. `read_tsd_evt()` - 2 call sites (production)
3. Test code - handled separately

**Complexity**: LOW to MEDIUM - straightforward API translation

---

## PRODUCTION CODE REPLACEMENTS

### 1. canbus/can_event.c - Line 152

**CURRENT CODE**:
```c
void can_process_event(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                      uint16_t entry, uint8_t *value)
{
    // ... validation and processing ...

    memcpy(&csd[entry].last_value.uint_32bit, value, IMX_SAMPLE_LENGTH);
    write_tsd_evt(csb, csd, entry, csd[entry].last_value.uint_32bit, false);  // ← REPLACE
}
```

**REPLACEMENT**:
```c
void can_process_event(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                      uint16_t entry, uint8_t *value)
{
    // ... validation and processing ...

    memcpy(&csd[entry].last_value.uint_32bit, value, IMX_SAMPLE_LENGTH);

    /* Direct MM2 API call - CAN sensors use IMX_UPLOAD_CAN_DEVICE upload source */
    imx_data_32_t data;
    data.uint_32bit = csd[entry].last_value.uint_32bit;
    imx_write_tsd(IMX_UPLOAD_CAN_DEVICE, &csb[entry], &csd[entry], data);
}
```

**Analysis**:
- Upload source: `IMX_UPLOAD_CAN_DEVICE` (CAN bus sensors)
- csb/csd: Already available as arrays
- No additional context needed

---

### 2. canbus/can_utils.c - Line 732

**CURRENT CODE**:
```c
// Inside canFrameHandler():
#ifdef UNKNOWN_CAN_BUS_ENTRY
    write_tsd_evt(cb.can_controller->csb, cb.can_controller->csd,
                  UNKNOWN_CAN_BUS_ENTRY, can_msg_ptr->can_id, false);  // ← REPLACE
#endif
```

**REPLACEMENT**:
```c
#ifdef UNKNOWN_CAN_BUS_ENTRY
    /* Log unknown CAN ID using direct MM2 API */
    imx_data_32_t data;
    data.uint_32bit = can_msg_ptr->can_id;
    imx_write_tsd(IMX_UPLOAD_CAN_DEVICE,
                  &cb.can_controller->csb[UNKNOWN_CAN_BUS_ENTRY],
                  &cb.can_controller->csd[UNKNOWN_CAN_BUS_ENTRY],
                  data);
#endif
```

**Analysis**:
- Upload source: `IMX_UPLOAD_CAN_DEVICE`
- csb/csd: Available via cb.can_controller
- UNKNOWN_CAN_BUS_ENTRY is an index into the arrays

---

### 3. location/process_location_state.c - Line 142

**CURRENT CODE**:
```c
// Inside location processing:
void write_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry, uint32_t value, bool add_gps_location);  // ← Forward declaration

// Usage (line 142):
write_tsd_evt(icb.i_scb, icb.i_sd, stopped_sensor_entry, stopped_state, true);  // ← REPLACE
```

**REPLACEMENT**:
```c
/* Write vehicle stopped state using direct MM2 API */
imx_data_32_t data;
data.uint_32bit = stopped_state;
imx_write_tsd(IMX_UPLOAD_GATEWAY, &icb.i_scb[stopped_sensor_entry],
              &icb.i_sd[stopped_sensor_entry], data);

/* Note: GPS location (add_gps_location=true) was NOT actually implemented
 * in mm2_compatibility.c, so no functionality lost */
```

**Analysis**:
- Upload source: `IMX_UPLOAD_GATEWAY` (icb.i_scb/i_sd are gateway sensors)
- GPS location parameter was ignored in compatibility function anyway
- Straightforward replacement

**Also remove forward declaration** at line 109

---

### 4. cs_ctrl/hal_sample.c - Line 406

**CURRENT CODE**:
```c
// Inside hal_sample_all():
write_tsd_evt( csb, csd, *active, csd[ *active ].last_value.uint_32bit, false );  // ← REPLACE
csd[*active].reset_max_value = true;
```

**CONTEXT ANALYSIS**:
- Function signature: `void hal_sample_all(imx_peripheral_type_t type, ...)`
- Uses `imx_set_csb_vars()` to get csb/csd arrays
- **Need to determine upload_source based on type**

**REPLACEMENT**:
```c
/* Write sensor sample using direct MM2 API */
imx_data_32_t data;
data.uint_32bit = csd[*active].last_value.uint_32bit;

/* Determine upload source based on peripheral type */
imatrix_upload_source_t upload_source;
if (type == IMX_CONTROLS || type == IMX_SENSORS || type == IMX_VARIABLES) {
    upload_source = IMX_UPLOAD_GATEWAY;  /* Gateway sensors */
} else {
    upload_source = IMX_UPLOAD_GATEWAY;  /* Default to gateway */
}

imx_write_tsd(upload_source, &csb[*active], &csd[*active], data);
csd[*active].reset_max_value = true;
```

**Note**: hal_sample.c processes **gateway** sensors (icb.i_scb/i_sd arrays), so `IMX_UPLOAD_GATEWAY` is correct.

---

### 5. cs_ctrl/hal_sample.c - Line 574

**CURRENT CODE**:
```c
// Inside hal_sample_hybrid():
write_tsd_evt(csb, csd, cs_index, csd[cs_index].last_value.uint_32bit, false);  // ← REPLACE
csd[cs_index].reset_max_value = true;
```

**REPLACEMENT** (same pattern as #4):
```c
/* Write hybrid sensor sample using direct MM2 API */
imx_data_32_t data;
data.uint_32bit = csd[cs_index].last_value.uint_32bit;
imx_write_tsd(IMX_UPLOAD_GATEWAY, &csb[cs_index], &csd[cs_index], data);
csd[cs_index].reset_max_value = true;
```

**Analysis**: Same as #4 - gateway sensors

---

### 6. imatrix_upload/imatrix_upload.c - Line 1488

**CURRENT CODE**:
```c
// Inside data upload loop:
read_tsd_evt(csb, csd, i, (uint32_t*)&event_sample);  // ← REPLACE
```

**CONTEXT**: Need to check what upload_source is being used in imatrix_upload.c

**REPLACEMENT**:
```c
/* Read next record using MM2 API */
tsd_evt_data_t record;
imatrix_upload_source_t upload_source = /* determine from context */;
imx_result_t result = imx_read_next_tsd_evt(upload_source, &csb[i], &csd[i], &record);
if (result == IMX_SUCCESS) {
    event_sample = record.value;
}
```

**ISSUE**: read_tsd_evt() just reads `csd[i].last_value`, doesn't actually read from MM2!
**Solution**: Determine if this is correct behavior or if it should use imx_read_next_tsd_evt()

---

### 7. imatrix_upload/imatrix_upload.c - Line 1504

**CURRENT CODE**:
```c
// Inside data upload loop:
read_tsd_evt(csb, csd, i, &tsd_sample_value);  // ← REPLACE
```

**REPLACEMENT** (same pattern as #6):
```c
/* Read sensor value - mm2_compatibility just returns last_value */
tsd_sample_value = csd[i].last_value.uint_32bit;

/* OR if should read from MM2 queue:
tsd_evt_data_t record;
imatrix_upload_source_t upload_source = ;  // determine from context
imx_result_t result = imx_read_next_tsd_evt(upload_source, &csb[i], &csd[i], &record);
if (result == IMX_SUCCESS) {
    tsd_sample_value = record.value;
}
*/
```

---

## TEST CODE REPLACEMENTS

### memory_test_suites.c - Multiple Locations

**Lines**: 690, 794, 1299, 1371, 1540, 1944, 2212, 2423, 2510, 2631, etc.

**Pattern**:
```c
// CURRENT:
write_tsd_evt(csb, csd, entry, test_value, false);

// REPLACEMENT:
imx_data_32_t data;
data.uint_32bit = test_value;
imx_write_tsd(IMX_UPLOAD_GATEWAY, &csb[entry], &csd[entry], data);
```

**Analysis**: All test code uses gateway sensors, so `IMX_UPLOAD_GATEWAY` is correct.

**Count**: ~12 occurrences in test code

---

## SPECIAL CASES

### read_tsd_evt() Analysis

**Current implementation** (mm2_compatibility.c line 127-133):
```c
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value)
{
    if (value != NULL && entry < MAX_SENSORS) {
        /* Read from sensor's last value */
        *value = csd[entry].last_value.uint_32bit;
    }
}
```

**This function does NOT read from MM2 queue!**
It just returns the cached `last_value`.

**Options for replacement**:
1. **Simple**: `*value = csd[entry].last_value.uint_32bit;` (what it does now)
2. **Proper**: Use `imx_read_next_tsd_evt()` to read from MM2 queue

**Recommendation**: Check imatrix_upload.c context to determine correct behavior.

---

## UPLOAD SOURCE DETERMINATION

### By File Location

| File | Sensor Arrays | Upload Source |
|------|---------------|---------------|
| canbus/can_event.c | CAN controller arrays | IMX_UPLOAD_CAN_DEVICE |
| canbus/can_utils.c | cb.can_controller | IMX_UPLOAD_CAN_DEVICE |
| location/process_location_state.c | icb.i_scb/i_sd | IMX_UPLOAD_GATEWAY |
| cs_ctrl/hal_sample.c | icb.i_scb/i_sd | IMX_UPLOAD_GATEWAY |
| imatrix_upload/imatrix_upload.c | ??? (need to check) | ??? |

**Critical**: imatrix_upload.c needs investigation to determine which arrays it uses.

---

## MIGRATION SEQUENCE

### Phase 1: Production Code (5 locations - 30 minutes)

1. **canbus/can_event.c:152** - CAN upload source
2. **canbus/can_utils.c:732** - CAN upload source
3. **location/process_location_state.c:142** - Gateway upload source
4. **cs_ctrl/hal_sample.c:406** - Gateway upload source
5. **cs_ctrl/hal_sample.c:574** - Gateway upload source

### Phase 2: imatrix_upload.c Analysis (15 minutes)

- Determine upload_source context
- Check if read_tsd_evt should use MM2 queue or just last_value
- Update 2 call sites

### Phase 3: Test Code (30 minutes)

- Update ~12 call sites in memory_test_suites.c
- All use IMX_UPLOAD_GATEWAY

### Phase 4: Remove from Build (5 minutes)

- Comment out from CMakeLists.txt line 159
- Remove forward declarations from headers
- Test compilation

**Total Estimated Time**: 1.5 hours

---

## VERIFICATION CHECKLIST

Before making changes:
- [ ] Identify upload_source for each call site
- [ ] Verify csb/csd array types match upload_source
- [ ] Check if read_tsd_evt should use MM2 queue

After each file:
- [ ] Compile file
- [ ] Verify no undefined references
- [ ] Check logic is equivalent

After all changes:
- [ ] Full system compile
- [ ] Verify mm2_compatibility.c not linked
- [ ] Runtime test if possible

---

## RISK ASSESSMENT

| Location | Risk | Reason |
|----------|------|--------|
| canbus/can_event.c | LOW | Clear CAN upload source |
| canbus/can_utils.c | LOW | Clear CAN upload source |
| location/process_location_state.c | LOW | Clear gateway upload source |
| hal_sample.c:406 | LOW | Gateway sensors |
| hal_sample.c:574 | LOW | Gateway sensors |
| imatrix_upload.c:1488 | MEDIUM | Need to verify upload_source |
| imatrix_upload.c:1504 | MEDIUM | Need to verify behavior |
| Test code | LOW | Isolated test environment |

---

**Status**: READY FOR REVIEW - Please verify upload source assignments before I proceed with replacements.
