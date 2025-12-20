# EVENT_SENSOR Block Timestamp Bug Report

**Date**: 2025-12-12
**Reported By**: Analysis via CoAP Packet Decoder Tool
**Severity**: Medium - Data Quality Issue
**Component**: iMatrix Upload / Event Sensor Data Serialization

---

## Executive Summary

EVENT_SENSOR blocks in CoAP upload packets contain invalid timestamps that decode to dates in 1977 instead of 2025. Analysis indicates the 32-bit timestamp values (~243 million) represent approximately 7.7 years of seconds, suggesting they are **device uptime values** rather than absolute UTC timestamps.

SENSOR_MS blocks in the same packet use 64-bit `imx_utc_time_ms_t` timestamps that correctly decode to 2025 dates, confirming the issue is isolated to EVENT_SENSOR block timestamp handling.

---

## Evidence

### Packet Analysis

**Source**: Device serial 513973109, captured 2025-12-11
**URI**: `selfreport/250007060/0513973109/0`

#### Valid Timestamps (SENSOR_MS blocks)

| Block | Sensor | Timestamp (ms) | Decoded |
|-------|--------|----------------|---------|
| 4 | Number_of_Satellites | 1733939216423 | 2025-12-11 17:46:56.423 UTC |
| 5 | HDOP | 1733939216524 | 2025-12-11 17:46:56.524 UTC |
| 6 | GPS_Fix_Quality | 1733939216628 | 2025-12-11 17:46:56.628 UTC |
| 7 | 4G_RF_RSSI | 1733939223717 | 2025-12-11 17:47:03.717 UTC |
| 8 | 4G_BER | 1733939224287 | 2025-12-11 17:47:04.287 UTC |
| 10 | ETH0_TX_Data_Rate | 1733939232704 | 2025-12-11 17:47:12.704 UTC |

#### Invalid Timestamps (EVENT_SENSOR blocks)

| Block | Sensor | Raw Timestamp | Hex | Decoded (Wrong) |
|-------|--------|---------------|-----|-----------------|
| 1 | GPS_Latitude | 243541789 | 0x0E84271D | 1977-09-19 18:29:49 UTC |
| 2 | GPS_Longitude | 243541789 | 0x0E84271D | 1977-09-19 18:29:49 UTC |
| 3 | GPS_Altitude | 243541789 | 0x0E84271D | 1977-09-19 18:29:49 UTC |
| 9 | Vehicle_Speed | 243541789 | 0x0E84271D | 1977-09-19 18:29:49 UTC |

### Timestamp Value Analysis

```
Raw value:     243,541,789 seconds
Divided by:    86,400 seconds/day = 2,819 days
Divided by:    365.25 days/year = 7.72 years

This matches device uptime, NOT Unix epoch time (which would be ~1.73 billion for 2025)
```

### Expected vs Actual

| Field | Expected | Actual |
|-------|----------|--------|
| Timestamp type | Absolute UTC (Unix epoch) | Relative (device uptime?) |
| Value range | ~1,733,900,000 (Dec 2025) | ~243,500,000 (~7.7 years) |
| Data type | 32-bit UTC seconds | 32-bit uptime seconds |

---

## Technical Details

### Affected Block Types

- `EVENT_SENSOR` (block_type = 11)
- `EVENT_CONTROL` (block_type = 10) - likely affected, not in test data

### Working Block Types

- `SENSOR_MS` (block_type = 12) - uses 64-bit `imx_utc_time_ms_t`
- `CONTROL_MS` (block_type = 15) - uses 64-bit `imx_utc_time_ms_t`

### Data Structure Reference

From `iMatrix/storage.h`:

```c
// EVENT data structure (affected)
typedef struct __attribute__((__packed__)) {
    uint32_t utc_sample_time;    // <-- THIS IS THE PROBLEM FIELD
    uint32_t data;
} event_data_t;

// TSD_MS data structure (working correctly)
typedef struct __attribute__((__packed__)) {
    imx_utc_time_ms_t last_utc_sample_time;  // 64-bit, correct
    uint32_t sample_rate_ms;
    uint32_t data[];
} upload_data_ms_t;
```

### Likely Code Location

The bug is likely in one of these areas:

1. **Event recording** (`cs_ctrl/memory_manager*.c`):
   - When events are recorded, `utc_sample_time` may be set from uptime instead of `ck_time_get_utc()`

2. **Upload serialization** (`imatrix_upload/`):
   - When packing EVENT_SENSOR blocks, wrong time source used

3. **Time source confusion**:
   ```c
   // WRONG - using uptime
   event->utc_sample_time = imx_get_uptime_ms() / 1000;

   // CORRECT - using UTC time
   event->utc_sample_time = ck_time_get_utc();
   ```

---

## Suggested Investigation

### 1. Search for Event Timestamp Assignment

```bash
grep -rn "utc_sample_time" iMatrix/
grep -rn "event_data_t" iMatrix/
grep -rn "EVENT_SENSOR\|EVENT_CONTROL" iMatrix/
```

### 2. Check Time Source in Event Recording

Look for code that populates `event_data_t.utc_sample_time` and verify it uses:
- `ck_time_get_utc()` - correct
- NOT `imx_get_uptime_ms()` or similar uptime functions

### 3. Compare with TSD_MS Implementation

The SENSOR_MS blocks work correctly. Compare how `last_utc_sample_time` is set in TSD_MS vs how `utc_sample_time` is set in EVENT blocks.

---

## Suggested Fix

### Option A: Fix at Event Recording Time

```c
// In event recording code (likely in memory_manager or sensor processing)
void record_sensor_event(uint32_t sensor_id, uint32_t value) {
    event_data_t event;
    event.utc_sample_time = ck_time_get_utc();  // Use UTC, not uptime
    event.data = value;
    // ... store event
}
```

### Option B: Fix at Upload Serialization Time

```c
// In upload packet building code
// If events are stored with uptime, convert to UTC during upload
uint32_t utc_offset = ck_time_get_utc() - (imx_get_uptime_ms() / 1000);
event->utc_sample_time = stored_uptime + utc_offset;
```

---

## Impact

### Data Quality
- Historical event timestamps are incorrect in the cloud database
- Time-based queries and analysis will return wrong results
- Event correlation with other data sources is broken

### Affected Sensors (from test data)
- GPS_Latitude (sensor 2)
- GPS_Longitude (sensor 3)
- GPS_Altitude (sensor 4)
- Vehicle_Speed (sensor 142)
- Any other sensor using EVENT_SENSOR block type

### Not Affected
- Sensors using SENSOR_MS blocks (Number_of_Satellites, HDOP, GPS_Fix_Quality, etc.)
- Real-time data display (only affects uploaded historical data)

---

## Test Data

Test packet file: `tools/coap_decoder/test_packet.txt`

To reproduce the analysis:
```bash
cd tools/coap_decoder
python3 coap_packet_printer.py test_packet.txt
```

Output will show:
- 40 invalid timestamps (EVENT_SENSOR blocks)
- 6 valid timestamps (SENSOR_MS blocks)
- Detailed breakdown by sensor

---

## Appendix: Raw Hex Data (First EVENT_SENSOR Block)

```
Block 1 Header (12 bytes):
  [1e][a2][9b][75]  Serial: 513973109
  [00][00][00][02]  Sensor ID: 2 (GPS_Latitude)
  [00][78][f0][8b]  Bits: block_type=11, data_type=2(FLOAT), payload=240, samples=30

First Event (8 bytes):
  [0e][84][27][1d]  Timestamp: 243541789 (INVALID - decodes to 1977)
  [42][1b][9b][77]  Value: 38.901821 (float, correct)
```

---

## References

- `iMatrix/storage.h` - Data structures
- `iMatrix/coap/coap_packet_printer.c` - C implementation reference
- `iMatrix/cs_ctrl/memory_manager*.c` - Event storage
- `iMatrix/time/ck_time.c` - Time functions
