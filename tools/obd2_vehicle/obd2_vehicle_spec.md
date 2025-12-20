# OBD2 Vehicle Simulator Specification

**Document Version**: 1.0
**Date**: 2025-12-13
**Author**: Claude Code Analysis
**Status**: Draft

---

## 1. Overview

This document provides a comprehensive specification for implementing an OBD2 vehicle simulator. The simulator responds to OBD2 diagnostic requests from a tester (such as a telematics gateway) and generates appropriate responses based on a vehicle profile.

### 1.1 Purpose

Enable bench testing of telematics gateways by simulating realistic OBD2 responses without requiring an actual vehicle.

### 1.2 Scope

- Standard OBD2 (ISO 15765-4 CAN) request/response protocol
- ISO-TP (ISO 15765-2) multi-frame messaging
- Background broadcast simulation
- Multiple ECU simulation

---

## 2. CAN Bus Configuration

### 2.1 Physical Layer

| Parameter | Value | Notes |
|-----------|-------|-------|
| Bitrate | 500 kbps | Standard OBD2 CAN |
| CAN Version | CAN 2.0A | 11-bit identifiers |
| Termination | 120 ohm | Both ends of bus |

### 2.2 OBD2 CAN Identifiers

| Identifier | Direction | Description |
|------------|-----------|-------------|
| `0x7DF` | Tester → ECUs | Functional broadcast request (all ECUs) |
| `0x7E0` | Tester → ECU | Physical request to ECU 0 (Engine/DME) |
| `0x7E1` | Tester → ECU | Physical request to ECU 1 |
| `0x7E2` - `0x7E7` | Tester → ECU | Physical requests to ECUs 2-7 |
| `0x7E8` | ECU → Tester | Response from ECU 0 (Engine/DME) |
| `0x7E9` | ECU → Tester | Response from ECU 1 |
| `0x7EA` - `0x7EF` | ECU → Tester | Responses from ECUs 2-7 |

### 2.3 Response Timing Requirements

| Parameter | Minimum | Typical | Maximum |
|-----------|---------|---------|---------|
| P2 (Response after request) | - | 8 ms | 50 ms |
| P2* (Extended response) | - | - | 5000 ms |
| Inter-ECU delay | 5 ms | 8 ms | 15 ms |

---

## 3. ISO-TP (ISO 15765-2) Transport Protocol

### 3.1 Frame Types

| PCI Byte | Frame Type | Description |
|----------|------------|-------------|
| `0x0N` | Single Frame (SF) | N = data length (1-7 bytes) |
| `0x1N NN` | First Frame (FF) | NNN = total data length (8-4095 bytes) |
| `0x2N` | Consecutive Frame (CF) | N = sequence number (0-F, wraps) |
| `0x3N` | Flow Control (FC) | N = flow status |

### 3.2 Single Frame Format

```
Byte 0: [0-7] = Data length
Bytes 1-7: Data payload (padded with 0x00 or 0xAA/0xFF)
```

**Example**: Request PID 0x0C (Engine RPM)
```
07DF: 02 01 0C 00 00 00 00 00
      ^^ ^^ ^^
      |  |  +-- PID
      |  +-- Service ID
      +-- Length (2 bytes of data)
```

### 3.3 Multi-Frame Format

**First Frame (FF)**:
```
Byte 0: 0x10 | (length >> 8)
Byte 1: length & 0xFF
Bytes 2-7: First 6 bytes of data
```

**Flow Control (FC)**:
```
Byte 0: 0x30 = Continue to Send (CTS)
Byte 1: Block Size (0 = no limit)
Byte 2: Separation Time (STmin in ms)
Bytes 3-7: Padding (0x00)
```

**Consecutive Frames (CF)**:
```
Byte 0: 0x20 | (sequence_number & 0x0F)
Bytes 1-7: Next 7 bytes of data
```

**Example**: VIN Request/Response
```
Request:  07DF: 02 09 02 ...            (Request VIN)
Response: 07E8: 10 14 49 02 01 35 55 58  (FF: 20 bytes, "5UX")
FlowCtrl: 07E0: 30 00 00 00 00 00 00 00  (FC: CTS)
Response: 07E8: 21 54 53 33 43 35 58 4B  (CF1: "TS3C5XK")
Response: 07E8: 22 30 5A 30 32 36 35 36  (CF2: "0Z02656")
```

---

## 4. OBD2 Service Definitions

### 4.1 Service Overview

| Service | Name | Description |
|---------|------|-------------|
| `0x01` | Current Data | Live powertrain data |
| `0x02` | Freeze Frame | Data snapshot at DTC set |
| `0x03` | Stored DTCs | Read confirmed fault codes |
| `0x04` | Clear DTCs | Clear fault codes and freeze frame |
| `0x07` | Pending DTCs | Read pending fault codes |
| `0x09` | Vehicle Info | VIN, Calibration IDs, etc. |
| `0x0A` | Permanent DTCs | Read permanent fault codes |

### 4.2 Request Format

```
Byte 0: Length (number of significant data bytes)
Byte 1: Service ID
Byte 2: PID (for Services 01, 02, 09)
Bytes 3-7: Additional data or padding (0x00)
```

### 4.3 Response Format

```
Byte 0: Length (number of significant data bytes)
Byte 1: Service ID + 0x40 (positive response)
Byte 2: PID echo
Bytes 3-N: Data
Bytes N+1-7: Padding (0x00, 0xAA, or 0xFF)
```

---

## 5. Service 0x01 - Current Powertrain Data

### 5.1 Supported PIDs Bitmap

PIDs 0x00, 0x20, 0x40, 0x60, 0x80, 0xA0 return 4-byte bitmaps indicating supported PIDs.

| Request | Response Bytes | Indicates Support For |
|---------|---------------|----------------------|
| PID 0x00 | 4 bytes | PIDs 0x01 - 0x20 |
| PID 0x20 | 4 bytes | PIDs 0x21 - 0x40 |
| PID 0x40 | 4 bytes | PIDs 0x41 - 0x60 |
| PID 0x60 | 4 bytes | PIDs 0x61 - 0x80 |
| PID 0x80 | 4 bytes | PIDs 0x81 - 0xA0 |
| PID 0xA0 | 4 bytes | PIDs 0xA1 - 0xC0 |

**Bitmap Interpretation**: Each bit represents one PID. MSB of first byte = next PID after request.

### 5.2 Complete PID Reference

#### PID 0x00 - Supported PIDs [01-20]

| Field | Value |
|-------|-------|
| Request | `02 01 00` |
| Response Length | 6 bytes |
| Data Bytes | 4 (bitmap) |

**Response Structure**:
```
Byte 0: 06 (response length)
Byte 1: 41 (Service 01 + 0x40)
Byte 2: 00 (PID echo)
Bytes 3-6: Supported PID bitmap
```

**Example Response**:
```
ECU 0x7E8: 06 41 00 BE 3F A8 13
                   ^^ ^^ ^^ ^^
Bitmap: BE 3F A8 13 = 1011 1110 0011 1111 1010 1000 0001 0011

Supported PIDs: 01, 03, 04, 05, 06, 07, 0B, 0C, 0D, 0E, 0F, 10, 11, 13, 15, 1C, 20
```

---

#### PID 0x01 - Monitor Status Since DTCs Cleared

| Field | Value |
|-------|-------|
| Request | `02 01 01` |
| Response Length | 6 bytes |
| Data Bytes | 4 |

**Response Structure**:
```
Byte 3: Bit 7: MIL status (0=off, 1=on)
        Bits 0-6: DTC count
Byte 4: Continuous monitors (spark/compression, fuel, misfire)
Byte 5: Non-continuous monitors supported
Byte 6: Non-continuous monitors complete
```

**Example Response**:
```
ECU 0x7E8: 06 41 01 00 07 E5 00
                   ^^ ^^ ^^ ^^
Byte 3: 0x00 = MIL off, 0 DTCs
Byte 4: 0x07 = Spark ignition, all continuous monitors ready
Byte 5: 0xE5 = Cat, Heated Cat, Evap, Sec Air, O2 Sensor, O2 Heater supported
Byte 6: 0x00 = All monitors complete
```

---

#### PID 0x05 - Engine Coolant Temperature

| Field | Value |
|-------|-------|
| Request | `02 01 05` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Temperature = A - 40` (°C) |
| Range | -40 to 215 °C |

**Example Response**:
```
ECU 0x7E8: 03 41 05 5B
                   ^^
Value: 0x5B = 91 decimal
Temperature = 91 - 40 = 51°C (124°F)
```

---

#### PID 0x0C - Engine RPM

| Field | Value |
|-------|-------|
| Request | `02 01 0C` |
| Response Length | 4 bytes |
| Data Bytes | 2 |
| Formula | `RPM = ((A * 256) + B) / 4` |
| Range | 0 to 16,383.75 RPM |

**Example Response**:
```
ECU 0x7E8: 04 41 0C 0A 66
                   ^^ ^^
Value: 0x0A66 = 2662 decimal
RPM = 2662 / 4 = 665.5 RPM (idle)
```

---

#### PID 0x0D - Vehicle Speed

| Field | Value |
|-------|-------|
| Request | `02 01 0D` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Speed = A` (km/h) |
| Range | 0 to 255 km/h |

**Example Response**:
```
ECU 0x7E8: 03 41 0D 00
                   ^^
Value: 0x00 = 0 km/h (stationary)
```

---

#### PID 0x11 - Throttle Position

| Field | Value |
|-------|-------|
| Request | `02 01 11` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Throttle = (A * 100) / 255` (%) |
| Range | 0 to 100% |

**Example Response**:
```
ECU 0x7E8: 03 41 11 25
                   ^^
Value: 0x25 = 37 decimal
Throttle = (37 * 100) / 255 = 14.5%
```

---

#### PID 0x20 - Supported PIDs [21-40]

| Field | Value |
|-------|-------|
| Request | `02 01 20` |
| Response Length | 6 bytes |
| Data Bytes | 4 (bitmap) |

**Example Response**:
```
ECU 0x7E8: 06 41 20 A0 07 B0 11
Bitmap indicates: 21, 23, 2E, 2F, 31, 32, 33, 3C, 40
```

---

#### PID 0x2F - Fuel Tank Level Input

| Field | Value |
|-------|-------|
| Request | `02 01 2F` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Level = (A * 100) / 255` (%) |
| Range | 0 to 100% |

**Example Response**:
```
ECU 0x7E8: 03 41 2F 26
                   ^^
Value: 0x26 = 38 decimal
Fuel Level = (38 * 100) / 255 = 14.9%
```

---

#### PID 0x33 - Absolute Barometric Pressure

| Field | Value |
|-------|-------|
| Request | `02 01 33` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Pressure = A` (kPa) |
| Range | 0 to 255 kPa |

**Example Response**:
```
ECU 0x7E8: 03 41 33 50
                   ^^
Value: 0x50 = 80 kPa (high altitude)
```

---

#### PID 0x40 - Supported PIDs [41-60]

| Field | Value |
|-------|-------|
| Request | `02 01 40` |
| Response Length | 6 bytes |
| Data Bytes | 4 (bitmap) |

**Example Response**:
```
ECU 0x7E8: 06 41 40 FE D0 84 11
Bitmap indicates: 41, 42, 43, 44, 45, 46, 47, 49, 4A, 4C, 51, 5C, 60
```

---

#### PID 0x46 - Ambient Air Temperature

| Field | Value |
|-------|-------|
| Request | `02 01 46` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Temperature = A - 40` (°C) |
| Range | -40 to 215 °C |

**Example Response**:
```
ECU 0x7E8: 03 41 46 2E
                   ^^
Value: 0x2E = 46 decimal
Temperature = 46 - 40 = 6°C (43°F)
```

---

#### PID 0x51 - Fuel Type

| Field | Value |
|-------|-------|
| Request | `02 01 51` |
| Response Length | 3 bytes |
| Data Bytes | 1 |

**Fuel Type Values**:
| Value | Fuel Type |
|-------|-----------|
| 0x01 | Gasoline |
| 0x02 | Methanol |
| 0x03 | Ethanol |
| 0x04 | Diesel |
| 0x05 | LPG |
| 0x06 | CNG |
| 0x07 | Propane |
| 0x08 | Electric |

**Example Response**:
```
ECU 0x7E8: 03 41 51 01
                   ^^
Value: 0x01 = Gasoline
```

---

#### PID 0x5C - Engine Oil Temperature

| Field | Value |
|-------|-------|
| Request | `02 01 5C` |
| Response Length | 3 bytes |
| Data Bytes | 1 |
| Formula | `Temperature = A - 40` (°C) |
| Range | -40 to 215 °C |

**Example Response**:
```
ECU 0x7E8: 03 41 5C 58
                   ^^
Value: 0x58 = 88 decimal
Temperature = 88 - 40 = 48°C (118°F)
```

---

#### PID 0x60 - Supported PIDs [61-80]

| Field | Value |
|-------|-------|
| Request | `02 01 60` |
| Response Length | 6 bytes |
| Data Bytes | 4 (bitmap) |

**Example Response**:
```
ECU 0x7E8: 06 41 60 61 00 00 01
Bitmap indicates: 61, 63, 80
```

---

#### PID 0x80 - Supported PIDs [81-A0]

| Field | Value |
|-------|-------|
| Request | `02 01 80` |
| Response Length | 6 bytes |
| Data Bytes | 4 (bitmap) |

**Example Response**:
```
ECU 0x7E8: 06 41 80 00 04 00 0D
Bitmap indicates: 96, 9D, 9F, A0
```

---

#### PID 0x9D - Engine Fuel Rate

| Field | Value |
|-------|-------|
| Request | `02 01 9D` |
| Response Length | 6 bytes |
| Data Bytes | 4 |
| Formula | `Rate = ((A * 256) + B) / 20` (L/h) |

**Example Response**:
```
ECU 0x7E8: 06 41 9D 00 0D 00 0D
                   ^^ ^^ ^^ ^^
Value: 0x000D = 13 decimal
Rate = 13 / 20 = 0.65 L/h
```

---

#### PID 0xA0 - Supported PIDs [A1-C0]

| Field | Value |
|-------|-------|
| Request | `02 01 A0` |
| Response Length | 6 bytes |
| Data Bytes | 4 (bitmap) |

**Example Response**:
```
ECU 0x7E8: 06 41 A0 04 00 00 00
Bitmap indicates: A6
```

---

#### PID 0xA6 - Odometer

| Field | Value |
|-------|-------|
| Request | `02 01 A6` |
| Response Length | 6 bytes |
| Data Bytes | 4 |
| Formula | `Odometer = ((A << 24) + (B << 16) + (C << 8) + D) / 10` (km) |

**Example Response**:
```
ECU 0x7E8: 06 41 A6 00 14 53 8E
                   ^^ ^^ ^^ ^^
Value: 0x0014538E = 1,332,110 decimal
Odometer = 1,332,110 / 10 = 133,211 km
```

---

## 6. Service 0x02 - Freeze Frame Data

### 6.1 Request Format

```
Byte 0: 03 (length)
Byte 1: 02 (service)
Byte 2: PID
Byte 3: Frame number (usually 0x00)
```

### 6.2 Example Response

```
Request:  07DF: 03 02 02 00 00 00 00 00
Response: 07E8: 05 42 02 00 00 00 00 00
                ^^ ^^ ^^ ^^ ^^
                |  |  |  +--+-- DTC that triggered freeze frame
                |  |  +-- PID echo
                |  +-- Service + 0x40
                +-- Length
```

---

## 7. Service 0x03 - Stored Diagnostic Trouble Codes

### 7.1 Request Format

```
07DF: 01 03 00 00 00 00 00 00
      ^^ ^^
      |  +-- Service 03
      +-- Length
```

### 7.2 Response Format

```
Byte 0: Length (2 + 2*n, where n = number of DTCs)
Byte 1: 43 (Service 03 + 0x40)
Bytes 2-3: First DTC (or 0x0000 if no DTCs)
Bytes 4-5: Second DTC (if present)
...
```

### 7.3 DTC Encoding

Each DTC is 2 bytes:
```
Byte 0: [7:6] = Category prefix
        [5:0] = First 2 digits (BCD)
Byte 1: Last 2 digits (BCD)
```

| Bits 7:6 | Prefix | System |
|----------|--------|--------|
| 00 | P0 | Powertrain (generic) |
| 01 | P1 | Powertrain (manufacturer) |
| 10 | P2 | Powertrain (generic) |
| 11 | P3 | Powertrain (manufacturer) |
| Same for B (Body), C (Chassis), U (Network) |

**Example**: No DTCs stored
```
ECU 0x7E8: 02 43 00 00 00 00 00 00
              ^^ ^^
              |  +-- No DTCs (0x0000)
              +-- Service response
```

---

## 8. Service 0x07 - Pending Diagnostic Trouble Codes

Same format as Service 0x03, but returns pending (not yet confirmed) DTCs.

```
Request:  07DF: 01 07 00 00 00 00 00 00
Response: 07E8: 02 47 00 00 00 00 00 00  (No pending DTCs)
```

---

## 9. Service 0x09 - Vehicle Information

### 9.1 PID 0x02 - Vehicle Identification Number (VIN)

| Field | Value |
|-------|-------|
| Request | `02 09 02` |
| Response | Multi-frame (20 bytes total) |
| VIN Length | 17 characters ASCII |

**Multi-Frame Sequence**:

```
Request:    07DF: 02 09 02 00 00 00 00 00

First Frame:
            07E8: 10 14 49 02 01 35 55 58
                  ^^ ^^ ^^ ^^ ^^ ^^ ^^ ^^
                  |  |  |  |  |  +--+--+-- VIN chars 1-3 ("5UX")
                  |  |  |  |  +-- Number of data items (01)
                  |  |  |  +-- PID echo
                  |  |  +-- Service + 0x40
                  +--+-- Total length (0x14 = 20 bytes)

Flow Control (Tester sends):
            07E0: 30 00 00 00 00 00 00 00
                  ^^ ^^ ^^
                  |  |  +-- STmin (0 = no delay)
                  |  +-- Block size (0 = no limit)
                  +-- Flow status (0 = Continue To Send)

Consecutive Frame 1:
            07E8: 21 54 53 33 43 35 58 4B
                  ^^ ^^ ^^ ^^ ^^ ^^ ^^ ^^
                  |  +--+--+--+--+--+--+-- VIN chars 4-10 ("TS3C5XK")
                  +-- Sequence number 1

Consecutive Frame 2:
            07E8: 22 30 5A 30 32 36 35 36
                  ^^ ^^ ^^ ^^ ^^ ^^ ^^ ^^
                  |  +--+--+--+--+--+--+-- VIN chars 11-17 ("0Z02656")
                  +-- Sequence number 2
```

**Complete VIN**: `5UXTS3C5XK0Z02656`

---

## 10. Service 0x0A - Permanent Diagnostic Trouble Codes

Same format as Service 0x03, but returns permanent DTCs that cannot be cleared by Service 0x04.

```
Request:  07DF: 01 0A 00 00 00 00 00 00
Response: 07E8: 02 4A 00 00 00 00 00 00  (No permanent DTCs)
```

---

## 11. Multiple ECU Response Handling

### 11.1 ECU Configuration

| ECU ID | Response ID | Role | Padding Byte |
|--------|-------------|------|--------------|
| ECU 0 | 0x7E8 | Primary (Engine/DME) | 0x00 |
| ECU 1 | 0x7E9 | Secondary | 0xAA |
| ECU 7 | 0x7EF | Tertiary | 0xFF |

### 11.2 Response Timing Sequence

When multiple ECUs respond to a functional broadcast (0x7DF):

```
Time (ms)    Event
---------    -----
0.0          Request sent on 0x7DF
8.0          ECU 0 responds on 0x7E8
16.0         ECU 1 responds on 0x7E9
24.0         ECU 7 responds on 0x7EF
```

### 11.3 ECU-Specific Support

Not all ECUs support all PIDs. Track per-ECU capability:

| PID | ECU 0 (0x7E8) | ECU 1 (0x7E9) | ECU 7 (0x7EF) |
|-----|---------------|---------------|---------------|
| 0x00 | Yes | Yes | Yes |
| 0x01 | Yes | Yes | Yes |
| 0x05 | Yes | Yes | Yes |
| 0x0C | Yes | Yes | Yes |
| 0x0D | Yes | Yes | Yes |
| 0x11 | Yes | Yes | Yes |
| 0x20 | Yes | Yes | Yes |
| 0x33 | Yes | No | No |
| 0x40 | Yes | Yes | Yes |
| 0x46 | Yes | No | No |
| 0x51 | Yes | No | No |
| 0x5C | Yes | No | No |
| 0x60 | Yes | No | No |
| 0x80 | Yes | No | No |
| 0x9D | Yes | No | No |
| 0xA0 | Yes | No | No |
| 0xA6 | Yes | No | No |
| 0x2F | Yes | No | No |

---

## 12. Background Broadcast Messages

### 12.1 Overview

Vehicles continuously broadcast status messages regardless of diagnostic activity. A realistic simulator should include these.

### 12.2 Broadcast Message Definitions

#### CAN ID 0x003C - Status Message 1

| Field | Value |
|-------|-------|
| Interval | 100 ms |
| DLC | 8 bytes |
| Data Pattern | Rolling counter in bytes 0-1 |

**Data Structure**:
```
Byte 0: Checksum/Counter (varies)
Byte 1: Counter (A0-AF, rolling)
Byte 2: 02
Byte 3: 12
Byte 4: 01
Byte 5: 00
Byte 6: 2A
Byte 7: FF
```

---

#### CAN ID 0x0130 - Status Message 2

| Field | Value |
|-------|-------|
| Interval | 100 ms (paired with 0x003C) |
| DLC | 5 bytes |

**Data Structure**:
```
Bytes 0-4: F7 FF FF FF FF (constant)
```

---

#### CAN ID 0x0799 - Periodic Status

| Field | Value |
|-------|-------|
| Interval | ~500 ms |
| DLC | 7 bytes |

**Data Structure**:
```
Byte 0: 18-1F (rolling)
Byte 1: 01
Byte 2: 16 or 17
Byte 3: 04
Byte 4: 0E-13 (varies)
Byte 5: 03
Byte 6: 0A
```

---

#### CAN ID 0x07C1 - Heartbeat

| Field | Value |
|-------|-------|
| Interval | 1000 ms |
| DLC | 8 bytes |

**Data Structure**:
```
Bytes 0-7: 0C 18 00 0C FF 00 01 00 (constant)
```

---

## 13. Negative Response Handling

### 13.1 Negative Response Format

```
Byte 0: 03
Byte 1: 7F (Negative Response Service ID)
Byte 2: Rejected Service ID
Byte 3: Negative Response Code (NRC)
```

### 13.2 Common NRC Values

| NRC | Name | Description |
|-----|------|-------------|
| 0x10 | General Reject | General rejection |
| 0x11 | Service Not Supported | Service not implemented |
| 0x12 | Sub-Function Not Supported | PID not supported |
| 0x13 | Incorrect Message Length | Wrong data length |
| 0x14 | Response Too Long | Response exceeds buffer |
| 0x22 | Conditions Not Correct | Prerequisites not met |

**Example**: Unsupported PID
```
Request:  07DF: 02 01 99 00 00 00 00 00
Response: 07E8: 03 7F 01 12 00 00 00 00
                   ^^ ^^ ^^
                   |  |  +-- NRC: Sub-Function Not Supported
                   |  +-- Rejected Service
                   +-- Negative Response indicator
```

---

## 14. Vehicle Profile JSON Schema

### 14.1 Profile Structure

```json
{
  "profile_version": "1.0",
  "profile_name": "BMW_X3_2019",
  "created_date": "2025-12-13",
  "source_trace": "BMW_OneStep.trc",

  "vehicle_info": {
    "vin": "5UXTS3C5XK0Z02656",
    "make": "BMW",
    "model": "X3",
    "year": 2019,
    "fuel_type": "gasoline"
  },

  "can_config": {
    "bitrate": 500000,
    "request_id": "0x7DF",
    "physical_request_base": "0x7E0"
  },

  "ecus": [
    {
      "name": "Engine (DME)",
      "response_id": "0x7E8",
      "physical_request_id": "0x7E0",
      "padding_byte": "0x00",
      "response_delay_ms": 8
    },
    {
      "name": "Secondary",
      "response_id": "0x7E9",
      "physical_request_id": "0x7E1",
      "padding_byte": "0xAA",
      "response_delay_ms": 16
    },
    {
      "name": "Tertiary",
      "response_id": "0x7EF",
      "physical_request_id": "0x7E7",
      "padding_byte": "0xFF",
      "response_delay_ms": 24
    }
  ],

  "supported_services": ["0x01", "0x02", "0x03", "0x07", "0x09", "0x0A"],

  "service_01_pids": {
    "0x00": {
      "description": "Supported PIDs [01-20]",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 00 BE 3F A8 13 00",
        "0x7E9": "06 41 00 98 18 80 01 AA",
        "0x7EF": "06 41 00 98 18 80 01 FF"
      }
    },
    "0x01": {
      "description": "Monitor Status",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 01 00 07 E5 00 00",
        "0x7E9": "06 41 01 00 04 00 00 AA",
        "0x7EF": "06 41 01 00 04 00 00 FF"
      }
    },
    "0x05": {
      "description": "Engine Coolant Temperature",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "A - 40",
      "unit": "°C",
      "static_value": "0x5B",
      "responses": {
        "0x7E8": "03 41 05 5B 00 00 00 00",
        "0x7E9": "03 41 05 5B AA AA AA AA",
        "0x7EF": "03 41 05 5B FF FF FF FF"
      }
    },
    "0x0C": {
      "description": "Engine RPM",
      "response_length": 4,
      "data_bytes": 2,
      "formula": "((A * 256) + B) / 4",
      "unit": "RPM",
      "dynamic": true,
      "default_value": "0x0A66",
      "responses": {
        "0x7E8": "04 41 0C 0A 66 00 00 00",
        "0x7E9": "04 41 0C 0A 6C AA AA AA",
        "0x7EF": "04 41 0C 0A 6C FF FF FF"
      }
    },
    "0x0D": {
      "description": "Vehicle Speed",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "A",
      "unit": "km/h",
      "dynamic": true,
      "default_value": "0x00",
      "responses": {
        "0x7E8": "03 41 0D 00 00 00 00 00",
        "0x7E9": "03 41 0D 00 AA AA AA AA",
        "0x7EF": "03 41 0D 00 FF FF FF FF"
      }
    },
    "0x11": {
      "description": "Throttle Position",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "(A * 100) / 255",
      "unit": "%",
      "dynamic": true,
      "default_value": "0x25",
      "responses": {
        "0x7E8": "03 41 11 25 00 00 00 00",
        "0x7E9": "03 41 11 24 AA AA AA AA",
        "0x7EF": "03 41 11 24 FF FF FF FF"
      }
    },
    "0x20": {
      "description": "Supported PIDs [21-40]",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 20 A0 07 B0 11 00",
        "0x7E9": "06 41 20 80 00 00 01 AA",
        "0x7EF": "06 41 20 80 00 00 01 FF"
      }
    },
    "0x2F": {
      "description": "Fuel Tank Level",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "(A * 100) / 255",
      "unit": "%",
      "static_value": "0x26",
      "responses": {
        "0x7E8": "03 41 2F 26 00 00 00 00"
      }
    },
    "0x33": {
      "description": "Barometric Pressure",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "A",
      "unit": "kPa",
      "static_value": "0x50",
      "responses": {
        "0x7E8": "03 41 33 50 00 00 00 00"
      }
    },
    "0x40": {
      "description": "Supported PIDs [41-60]",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 40 FE D0 84 11 00",
        "0x7E9": "06 41 40 C0 00 00 00 AA",
        "0x7EF": "06 41 40 C0 00 00 00 FF"
      }
    },
    "0x46": {
      "description": "Ambient Air Temperature",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "A - 40",
      "unit": "°C",
      "static_value": "0x2E",
      "responses": {
        "0x7E8": "03 41 46 2E 00 00 00 00"
      }
    },
    "0x51": {
      "description": "Fuel Type",
      "response_length": 3,
      "data_bytes": 1,
      "static_value": "0x01",
      "responses": {
        "0x7E8": "03 41 51 01 00 00 00 00"
      }
    },
    "0x5C": {
      "description": "Engine Oil Temperature",
      "response_length": 3,
      "data_bytes": 1,
      "formula": "A - 40",
      "unit": "°C",
      "static_value": "0x58",
      "responses": {
        "0x7E8": "03 41 5C 58 00 00 00 00"
      }
    },
    "0x60": {
      "description": "Supported PIDs [61-80]",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 60 61 00 00 01 00"
      }
    },
    "0x80": {
      "description": "Supported PIDs [81-A0]",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 80 00 04 00 0D 00"
      }
    },
    "0x9D": {
      "description": "Engine Fuel Rate",
      "response_length": 6,
      "data_bytes": 4,
      "formula": "((A * 256) + B) / 20",
      "unit": "L/h",
      "static_value": "0x000D000D",
      "responses": {
        "0x7E8": "06 41 9D 00 0D 00 0D 00"
      }
    },
    "0xA0": {
      "description": "Supported PIDs [A1-C0]",
      "response_length": 6,
      "responses": {
        "0x7E8": "06 41 A0 04 00 00 00 00"
      }
    },
    "0xA6": {
      "description": "Odometer",
      "response_length": 6,
      "data_bytes": 4,
      "formula": "((A << 24) + (B << 16) + (C << 8) + D) / 10",
      "unit": "km",
      "static_value": "0x0014538E",
      "responses": {
        "0x7E8": "06 41 A6 00 14 53 8E 00"
      }
    }
  },

  "service_02_pids": {
    "0x02": {
      "description": "Freeze Frame DTC",
      "responses": {
        "0x7E8": "05 42 02 00 00 00 00 00",
        "0x7E9": "05 42 02 00 00 00 AA AA",
        "0x7EF": "05 42 02 00 00 00 FF FF"
      }
    }
  },

  "service_03": {
    "description": "Stored DTCs",
    "dtc_count": 0,
    "responses": {
      "0x7E8": "02 43 00 00 00 00 00 00",
      "0x7E9": "02 43 00 AA AA AA AA AA",
      "0x7EF": "02 43 00 FF FF FF FF FF"
    }
  },

  "service_07": {
    "description": "Pending DTCs",
    "dtc_count": 0,
    "responses": {
      "0x7E8": "02 47 00 00 00 00 00 00",
      "0x7E9": "02 47 00 AA AA AA AA AA",
      "0x7EF": "02 47 00 FF FF FF FF FF"
    }
  },

  "service_09_pids": {
    "0x02": {
      "description": "VIN",
      "multi_frame": true,
      "total_length": 20,
      "vin": "5UXTS3C5XK0Z02656",
      "frames": [
        {"type": "FF", "ecu": "0x7E8", "data": "10 14 49 02 01 35 55 58"},
        {"type": "CF", "ecu": "0x7E8", "seq": 1, "data": "21 54 53 33 43 35 58 4B"},
        {"type": "CF", "ecu": "0x7E8", "seq": 2, "data": "22 30 5A 30 32 36 35 36"}
      ],
      "flow_control": {
        "request_id": "0x7E0",
        "data": "30 00 00 00 00 00 00 00"
      }
    }
  },

  "service_0A": {
    "description": "Permanent DTCs",
    "dtc_count": 0,
    "responses": {
      "0x7E8": "02 4A 00 00 00 00 00 00",
      "0x7E9": "02 4A 00 AA AA AA AA AA",
      "0x7EF": "02 4A 00 FF FF FF FF FF"
    }
  },

  "broadcast_messages": [
    {
      "can_id": "0x003C",
      "interval_ms": 100,
      "dlc": 8,
      "pattern": "rolling_counter",
      "data_template": "XX YY 02 12 01 00 2A FF",
      "notes": "XX=checksum, YY=counter A0-AF"
    },
    {
      "can_id": "0x0130",
      "interval_ms": 100,
      "dlc": 5,
      "data": "F7 FF FF FF FF"
    },
    {
      "can_id": "0x0799",
      "interval_ms": 500,
      "dlc": 7,
      "data_template": "XX 01 16 04 YY 03 0A",
      "notes": "XX=18-1F rolling, YY=0E-13 varies"
    },
    {
      "can_id": "0x07C1",
      "interval_ms": 1000,
      "dlc": 8,
      "data": "0C 18 00 0C FF 00 01 00"
    }
  ]
}
```

---

## 15. Complete Request/Response Packet Reference

### 15.1 All Captured Request/Response Pairs

This section provides the exact byte sequences for all requests and responses.

#### Service 0x01 - Current Data

| PID | Request (0x7DF) | Response (0x7E8) | Response (0x7E9) | Response (0x7EF) |
|-----|-----------------|------------------|------------------|------------------|
| 0x00 | `02 01 00 00 00 00 00 00` | `06 41 00 BE 3F A8 13 00` | `06 41 00 98 18 80 01 AA` | `06 41 00 98 18 80 01 FF` |
| 0x01 | `02 01 01 00 00 00 00 00` | `06 41 01 00 07 E5 00 00` | `06 41 01 00 04 00 00 AA` | `06 41 01 00 04 00 00 FF` |
| 0x05 | `02 01 05 00 00 00 00 00` | `03 41 05 5B 00 00 00 00` | `03 41 05 5B AA AA AA AA` | `03 41 05 5B FF FF FF FF` |
| 0x0C | `02 01 0C 00 00 00 00 00` | `04 41 0C 0A 66 00 00 00` | `04 41 0C 0A 6C AA AA AA` | `04 41 0C 0A 6C FF FF FF` |
| 0x0D | `02 01 0D 00 00 00 00 00` | `03 41 0D 00 00 00 00 00` | `03 41 0D 00 AA AA AA AA` | `03 41 0D 00 FF FF FF FF` |
| 0x11 | `02 01 11 00 00 00 00 00` | `03 41 11 25 00 00 00 00` | `03 41 11 24 AA AA AA AA` | `03 41 11 24 FF FF FF FF` |
| 0x20 | `02 01 20 00 00 00 00 00` | `06 41 20 A0 07 B0 11 00` | `06 41 20 80 00 00 01 AA` | `06 41 20 80 00 00 01 FF` |
| 0x2F | `02 01 2F 00 00 00 00 00` | `03 41 2F 26 00 00 00 00` | - | - |
| 0x33 | `02 01 33 00 00 00 00 00` | `03 41 33 50 00 00 00 00` | - | - |
| 0x40 | `02 01 40 00 00 00 00 00` | `06 41 40 FE D0 84 11 00` | `06 41 40 C0 00 00 00 AA` | `06 41 40 C0 00 00 00 FF` |
| 0x46 | `02 01 46 00 00 00 00 00` | `03 41 46 2E 00 00 00 00` | - | - |
| 0x51 | `02 01 51 00 00 00 00 00` | `03 41 51 01 00 00 00 00` | - | - |
| 0x5C | `02 01 5C 00 00 00 00 00` | `03 41 5C 58 00 00 00 00` | - | - |
| 0x60 | `02 01 60 00 00 00 00 00` | `06 41 60 61 00 00 01 00` | - | - |
| 0x80 | `02 01 80 00 00 00 00 00` | `06 41 80 00 04 00 0D 00` | - | - |
| 0x9D | `02 01 9D 00 00 00 00 00` | `06 41 9D 00 0D 00 0D 00` | - | - |
| 0xA0 | `02 01 A0 00 00 00 00 00` | `06 41 A0 04 00 00 00 00` | - | - |
| 0xA6 | `02 01 A6 00 00 00 00 00` | `06 41 A6 00 14 53 8E 00` | - | - |

#### Service 0x02 - Freeze Frame

| PID | Request (0x7DF) | Response (0x7E8) | Response (0x7E9) | Response (0x7EF) |
|-----|-----------------|------------------|------------------|------------------|
| 0x02 | `03 02 02 00 00 00 00 00` | `05 42 02 00 00 00 00 00` | `05 42 02 00 00 00 AA AA` | `05 42 02 00 00 00 FF FF` |

#### Service 0x03 - Stored DTCs

| Request (0x7DF) | Response (0x7E8) | Response (0x7E9) | Response (0x7EF) |
|-----------------|------------------|------------------|------------------|
| `01 03 00 00 00 00 00 00` | `02 43 00 00 00 00 00 00` | `02 43 00 AA AA AA AA AA` | `02 43 00 FF FF FF FF FF` |

#### Service 0x07 - Pending DTCs

| Request (0x7DF) | Response (0x7E8) | Response (0x7E9) | Response (0x7EF) |
|-----------------|------------------|------------------|------------------|
| `01 07 00 00 00 00 00 00` | `02 47 00 00 00 00 00 00` | `02 47 00 AA AA AA AA AA` | `02 47 00 FF FF FF FF FF` |

#### Service 0x09 - Vehicle Information (VIN)

| Frame | CAN ID | Data |
|-------|--------|------|
| Request | 0x7DF | `02 09 02 00 00 00 00 00` |
| First Frame | 0x7E8 | `10 14 49 02 01 35 55 58` |
| Flow Control | 0x7E0 | `30 00 00 00 00 00 00 00` |
| Consecutive 1 | 0x7E8 | `21 54 53 33 43 35 58 4B` |
| Consecutive 2 | 0x7E8 | `22 30 5A 30 32 36 35 36` |

#### Service 0x0A - Permanent DTCs

| Request (0x7DF) | Response (0x7E8) | Response (0x7E9) | Response (0x7EF) |
|-----------------|------------------|------------------|------------------|
| `01 0A 00 00 00 00 00 00` | `02 4A 00 00 00 00 00 00` | `02 4A 00 AA AA AA AA AA` | `02 4A 00 FF FF FF FF FF` |

---

## 16. Implementation Guidelines

### 16.1 Simulator State Machine

```
                    ┌─────────────┐
                    │    IDLE     │
                    └──────┬──────┘
                           │ CAN frame received
                           ▼
                    ┌─────────────┐
                    │   PARSE     │
                    │   REQUEST   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ SINGLE   │ │ MULTI    │ │ UNKNOWN  │
        │ FRAME    │ │ FRAME    │ │ SERVICE  │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ LOOKUP   │ │ WAIT FOR │ │ SEND NRC │
        │ RESPONSE │ │ FLOW CTL │ │ RESPONSE │
        └────┬─────┘ └────┬─────┘ └──────────┘
             │            │
             ▼            ▼
        ┌──────────┐ ┌──────────┐
        │ SEND     │ │ SEND     │
        │ RESPONSE │ │ CF FRAMES│
        └────┬─────┘ └────┬─────┘
             │            │
             └─────┬──────┘
                   ▼
            ┌─────────────┐
            │    IDLE     │
            └─────────────┘
```

### 16.2 Request Processing Algorithm

```python
def process_request(can_id, data):
    if can_id == 0x7DF:  # Functional broadcast
        process_functional_request(data)
    elif 0x7E0 <= can_id <= 0x7E7:  # Physical request
        process_physical_request(can_id, data)
    elif can_id == 0x7E0:  # Flow control
        process_flow_control(data)

def process_functional_request(data):
    length = data[0]
    service = data[1]

    if service == 0x01:
        pid = data[2]
        responses = lookup_service_01_responses(pid)
        for ecu_id, response in responses:
            schedule_response(ecu_id, response, get_delay(ecu_id))

    elif service == 0x03:
        send_dtc_responses(SERVICE_03)

    elif service == 0x09:
        pid = data[2]
        if pid == 0x02:
            initiate_vin_multiframe()
```

### 16.3 Multi-ECU Response Timing

```python
ECU_DELAYS = {
    0x7E8: 8,   # Primary ECU: 8ms delay
    0x7E9: 16,  # Secondary ECU: 16ms delay
    0x7EF: 24,  # Tertiary ECU: 24ms delay
}

def schedule_response(ecu_id, response, delay_ms):
    timer = Timer(delay_ms / 1000.0, send_can_frame, args=[ecu_id, response])
    timer.start()
```

### 16.4 Background Broadcast Generator

```python
import threading
import time

class BroadcastGenerator:
    def __init__(self, can_interface):
        self.can = can_interface
        self.running = False
        self.counter = 0xA0

    def start(self):
        self.running = True
        threading.Thread(target=self._broadcast_loop).start()

    def _broadcast_loop(self):
        last_003c = time.time()
        last_0799 = time.time()
        last_07c1 = time.time()

        while self.running:
            now = time.time()

            # 100ms interval for 0x003C and 0x0130
            if now - last_003c >= 0.1:
                self._send_003c()
                self._send_0130()
                last_003c = now

            # 500ms interval for 0x0799
            if now - last_0799 >= 0.5:
                self._send_0799()
                last_0799 = now

            # 1000ms interval for 0x07C1
            if now - last_07c1 >= 1.0:
                self._send_07c1()
                last_07c1 = now

            time.sleep(0.001)  # 1ms resolution

    def _send_003c(self):
        checksum = self._calc_checksum(self.counter)
        data = bytes([checksum, self.counter, 0x02, 0x12, 0x01, 0x00, 0x2A, 0xFF])
        self.can.send(0x003C, data)
        self.counter = 0xA0 if self.counter == 0xAF else self.counter + 1

    def _send_0130(self):
        self.can.send(0x0130, bytes([0xF7, 0xFF, 0xFF, 0xFF, 0xFF]))

    def _send_0799(self):
        self.can.send(0x0799, bytes([0x1B, 0x01, 0x16, 0x04, 0x12, 0x03, 0x0A]))

    def _send_07c1(self):
        self.can.send(0x07C1, bytes([0x0C, 0x18, 0x00, 0x0C, 0xFF, 0x00, 0x01, 0x00]))
```

---

## 17. Testing Recommendations

### 17.1 Validation Checklist

- [ ] All supported PIDs respond correctly
- [ ] Multi-ECU timing is within spec (P2 < 50ms)
- [ ] ISO-TP multi-frame works for VIN
- [ ] Flow control handled correctly
- [ ] Unsupported PIDs return NRC 0x12
- [ ] Background broadcasts at correct intervals
- [ ] Response padding matches ECU signature

### 17.2 Test Scenarios

1. **Basic Connectivity**: Request PID 0x00, verify 3 ECU responses
2. **Live Data**: Poll RPM, Speed, Throttle in sequence
3. **VIN Retrieval**: Full multi-frame VIN exchange
4. **DTC Read**: Services 03, 07, 0A return correct format
5. **Error Handling**: Request unsupported PID, expect NRC

---

## Appendix A: Decoded Values from Trace

| Parameter | Raw Value | Decoded Value |
|-----------|-----------|---------------|
| VIN | `35 55 58 54 53 33 43 35 58 4B 30 5A 30 32 36 35 36` | 5UXTS3C5XK0Z02656 |
| Engine RPM | `0A 66` | 665.5 RPM |
| Vehicle Speed | `00` | 0 km/h |
| Coolant Temp | `5B` | 51°C |
| Throttle Position | `25` | 14.5% |
| Fuel Level | `26` | 14.9% |
| Ambient Temp | `2E` | 6°C |
| Oil Temp | `58` | 48°C |
| Barometric | `50` | 80 kPa |
| Odometer | `00 14 53 8E` | 133,211 km |
| Fuel Type | `01` | Gasoline |
| Stored DTCs | `00` | None |
| Pending DTCs | `00` | None |
| Permanent DTCs | `00` | None |

---

## Appendix B: References

- ISO 15765-2: Road vehicles — Diagnostic communication over CAN (Transport Protocol)
- ISO 15765-4: Road vehicles — Diagnostic communication over CAN (OBD2)
- SAE J1979: E/E Diagnostic Test Modes
- SAE J2012: Diagnostic Trouble Code Definitions

---

**Document End**
