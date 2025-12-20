# CoAP Packet Decoder

A Python tool to decode iMatrix CoAP protocol hex dumps into human-readable format, matching the functionality of `iMatrix/coap/coap_packet_printer.c`.

**Date**: 2025-12-12

## Usage

```bash
python3 coap_packet_printer.py <filename> [-v|--verbose] [--color] [--no-color]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `filename` | File containing CoAP hex dump in `[XX][XX]...` format |
| `-v, --verbose` | Show all samples instead of limiting to first 10 |
| `--color` | Force colored output even when not a TTY |
| `--no-color` | Disable colored output |

### Examples

```bash
# Basic decode (show first 10 samples per block)
python3 coap_packet_printer.py test_packet.txt

# Verbose decode (show all samples)
python3 coap_packet_printer.py test_packet.txt -v

# Force color output when piping
python3 coap_packet_printer.py test_packet.txt --color | less -R

# Save output without colors
python3 coap_packet_printer.py test_packet.txt --no-color > decoded.txt
```

## Input Format

The tool expects hex dumps in bracket format from device logs:
```
[00:05:02.582] UPLOAD Message DATA as hex:   [24][16][92][2f][bd][14]...
```

The timestamp prefix is automatically stripped. Only the `[XX][XX]...` hex bytes are processed.

## Supported Block Types

| Block Type | ID | Description |
|------------|-----|-------------|
| CONTROL | 0 | Control time-series data with sample rate (seconds) |
| SENSOR | 1 | Sensor time-series data with sample rate (seconds) |
| BLE_CLIENTS | 3 | Bluetooth device list |
| EVENT_CONTROL | 10 | Control event data with per-sample timestamps |
| EVENT_SENSOR | 11 | Sensor event data with per-sample timestamps |
| SENSOR_MS | 12 | Sensor data with millisecond precision |
| FLAG_CONTROL_SENSOR | 14 | Notification/warning blocks |
| CONTROL_MS | 15 | Control data with millisecond precision |
| FW_VERSION | 16 | Firmware version string |

## Output

The tool decodes and displays:

1. **CoAP Header**: Version, Type, Code, Message ID, Token
2. **Options**: URI-Path, Content-Format
3. **Data Blocks**: Each block includes:
   - Serial number
   - Sensor ID and name (from internal sensor definitions)
   - Data type (UINT32, INT32, FLOAT, VARIABLE_LENGTH)
   - Payload length and sample count
   - Decoded values with timestamps
4. **Timestamp Validation Summary**: Invalid timestamp detection and analysis

## Internal Sensor Names

The tool includes a lookup table for 150+ iMatrix internal sensors (IDs 2-538):

| Category | Examples |
|----------|----------|
| GPS | Latitude, Longitude, Altitude, HDOP, Satellites, Fix Quality |
| Cellular | RSSI, RSRP, RSRQ, SINR, Carrier, Band, IMEI |
| Vehicle | Speed, Battery Voltage, Odometer, Engine RPM |
| Network | ETH0/WiFi/PPP0 TX/RX Data Rates |
| CAN Bus | CAN0/CAN1 Speed, TX/RX Rates |
| Trip | Distance, Energy, MPGe, Charge Rate |

Unknown sensor IDs are displayed as `Sensor_<ID>`.

## Timestamp Validation

The tool automatically detects and highlights invalid timestamps:

- **Valid range**: 2000-01-01 to 2100-01-01 (Unix epoch)
- **Invalid timestamps** are highlighted in **RED** with raw values (decimal + hex)
- **Summary section** at the end shows:
  - Count of valid vs invalid timestamps
  - Which blocks/sensors have invalid timestamps
  - Example raw values for debugging
  - Possible causes

### Example Invalid Timestamp Output

```
[Block 1] EVENT_SENSOR
  Sensor ID: 2 (GPS_Latitude)
  Events (30 total):
    [1] INVALID: 1977-09-19 18:29:49 UTC [raw: 243541789 = 0x0E84271D]: 38.901821
```

### Validation Summary

```
----------------------------------------
TIMESTAMP VALIDATION
----------------------------------------
WARNING: 40 invalid timestamps detected!
  Valid timestamps: 6
  Invalid timestamps: 40

Invalid timestamp details:
  Block 1 (GPS_Latitude): 10 invalid timestamp(s)
    Example: 243541789 (0x0E84271D) - not a valid UTC second timestamp

Possible causes:
  - Timestamps might be relative (uptime) instead of absolute UTC
  - Device RTC was not synchronized
  - Wrong timestamp format (seconds vs milliseconds)
  - Data corruption
```

This feature helps identify firmware bugs where timestamps use wrong formats or epochs.

## Data Format Notes

| Field | Format |
|-------|--------|
| Multi-byte values | Network byte order (big-endian) |
| Bit fields | Packed little-endian ARM format, byte-swapped for network |
| Float values | IEEE 754 single-precision |
| Timestamps (seconds) | 32-bit Unix epoch |
| Timestamps (milliseconds) | 64-bit Unix epoch in ms (`imx_utc_time_ms_t`) |

### Header Structure (12 bytes)

```
typedef struct __attribute__((__packed__)) {
    uint32_t sn;      // Serial number (bytes 0-3)
    uint32_t id;      // Sensor ID (bytes 4-7)
    bits_t bits;      // Bit field (bytes 8-11)
} header_t;
```

### Bits Field Layout

```
bits 0-5:   block_type (6 bits)
bits 6-7:   data_type (2 bits)
bits 8-17:  payload_length (10 bits)
bits 18-25: no_samples (8 bits)
bits 26-31: unused (6 bits)
```

## Known Issues / Bug Detection

This tool was created to help identify a timestamp bug in EVENT_SENSOR blocks where:
- SENSOR_MS blocks use correct 64-bit `imx_utc_time_ms_t` timestamps (decode to 2025)
- EVENT_SENSOR blocks use 32-bit timestamps that decode to 1977

The raw values (~243 million seconds) suggest the timestamps may be:
1. Device uptime rather than absolute UTC
2. Using a different epoch than Unix (1970)
3. Truncated from a 64-bit value

## Source Reference

Based on: `iMatrix/coap/coap_packet_printer.c`
