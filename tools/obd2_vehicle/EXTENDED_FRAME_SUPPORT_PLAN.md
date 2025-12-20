# Extended Frame (29-bit CAN ID) Support Plan

**Document Version**: 1.0
**Date**: 2025-12-13
**Author**: Claude Code Analysis
**Status**: Planning

---

## 1. Executive Summary

This plan extends the OBD2 vehicle simulator specifications to support both 11-bit (standard) and 29-bit (extended) CAN identifiers as defined in ISO 15765-4. This enables testing of vehicles that use either addressing mode.

### 1.1 Scope

| Document | Changes Required |
|----------|------------------|
| `obd2_vehicle_spec.md` | Add extended frame protocol details |
| `TRACE_PARSER_SPEC.md` | Add extended frame detection and parsing |
| `profiles/*.json` | Extend schema for 29-bit identifiers |
| Simulator (future) | Handle both frame types |

### 1.2 Standards Reference

- **ISO 15765-4**: OBD on CAN (defines both 11-bit and 29-bit addressing)
- **ISO 11898-1**: CAN data link layer (defines frame formats)
- **SAE J1979**: OBD2 diagnostic services

---

## 2. Background: CAN Frame Formats

### 2.1 Standard Frame (11-bit Identifier)

```
┌─────────┬─────────────┬─────┬─────┬──────────────────┬─────┬─────┐
│   SOF   │  11-bit ID  │ RTR │ IDE │ Control + Data   │ CRC │ EOF │
│  1 bit  │   11 bits   │1 bit│1 bit│   0-64 bits      │15+1 │7 bit│
└─────────┴─────────────┴─────┴─────┴──────────────────┴─────┴─────┘
                              │
                              └── IDE = 0 (Standard Frame)
```

### 2.2 Extended Frame (29-bit Identifier)

```
┌─────────┬───────────┬─────┬─────┬──────────────┬─────┬──────────────────┬─────┬─────┐
│   SOF   │ 11-bit ID │ SRR │ IDE │  18-bit ID   │ RTR │ Control + Data   │ CRC │ EOF │
│  1 bit  │  (base)   │1 bit│1 bit│ (extension)  │1 bit│   0-64 bits      │15+1 │7 bit│
└─────────┴───────────┴─────┴─────┴──────────────┴─────┴──────────────────┴─────┴─────┘
                            │
                            └── IDE = 1 (Extended Frame)

29-bit ID = [Base ID (11 bits)] [Extension ID (18 bits)]
```

### 2.3 OBD2 Addressing Modes (ISO 15765-4)

| Mode | ID Length | Request ID | Response ID | Common Usage |
|------|-----------|------------|-------------|--------------|
| **11-bit Normal** | 11-bit | 0x7DF (func), 0x7E0-7E7 (phys) | 0x7E8-0x7EF | Most passenger vehicles |
| **29-bit Normal** | 29-bit | 0x18DB33F1 (func), 0x18DAxxF1 (phys) | 0x18DAF1xx | Heavy-duty, trucks, some EU vehicles |
| **11-bit Extended** | 11-bit | 0x7DF | 0x7E8-0x7EF | Legacy extended addressing |
| **29-bit Extended** | 29-bit | 0x18DB33F1 | 0x18DAF1xx | Heavy-duty with extended |

---

## 3. Extended Frame OBD2 Identifiers

### 3.1 29-bit Functional Broadcast

```
Request ID: 0x18DB33F1

Breakdown:
┌────────────┬────────────┬────────────┬────────────┐
│  Priority  │    PGN     │   Source   │   Target   │
│   0x18     │   0xDB33   │    0xF1    │    All     │
│  (6 bits)  │ (16 bits)  │  (8 bits)  │            │
└────────────┴────────────┴────────────┴────────────┘

0x18 = Priority 6 (normal)
0xDB33 = OBD Request PGN
0xF1 = External test equipment (tester address)
```

### 3.2 29-bit Physical Addressing

```
Request to ECU X:  0x18DAxxF1
Response from ECU: 0x18DAF1xx

Where xx = ECU address (00-FF)

Common ECU Addresses:
  0x00 = Engine (equivalent to 0x7E0 in 11-bit)
  0x01 = Transmission
  0x02 = ABS/Brakes
  ...
  0xFF = Broadcast
```

### 3.3 Comparison Table

| Function | 11-bit ID | 29-bit ID |
|----------|-----------|-----------|
| Functional Request | 0x7DF | 0x18DB33F1 |
| Physical to Engine | 0x7E0 | 0x18DA00F1 |
| Physical to Trans | 0x7E1 | 0x18DA01F1 |
| Response from Engine | 0x7E8 | 0x18DAF100 |
| Response from Trans | 0x7E9 | 0x18DAF101 |
| Flow Control to Engine | 0x7E0 | 0x18DA00F1 |

---

## 4. PCAN Trace File Extended Frame Format

### 4.1 Extended ID Representation

PCAN-View represents extended frames with a suffix or different column width:

**Format Option 1: Extended ID Suffix**
```
     1)         6.3  Rx      18DB33F1  8  02 01 00 00 00 00 00 00
```

**Format Option 2: ID with Extended Flag**
```
     1)         6.3  Rx      18DB33F1h  8  02 01 00 00 00 00 00 00
                                     ^
                                     Extended frame indicator
```

**Format Option 3: Separate Column**
```
;   Message Number
;   |         Time Offset (ms)
;   |         |        Type
;   |         |        |     Extended
;   |         |        |     |   ID (hex)
;   |         |        |     |   |           DLC
;   |         |        |     |   |           |   Data
;---+--   ----+----  --+--  -+-  -+------   -+-  -- -- -- -- -- -- -- --
     1)         6.3  Rx      X   18DB33F1   8   02 01 00 00 00 00 00 00
```

### 4.2 Detection Strategy

```python
def detect_frame_type(can_id_str):
    """
    Detect if CAN ID is standard (11-bit) or extended (29-bit).

    Returns: ('standard', id_value) or ('extended', id_value)
    """
    # Remove any suffix indicators
    clean_id = can_id_str.rstrip('hHxX')

    try:
        id_value = int(clean_id, 16)
    except ValueError:
        return None

    # 11-bit IDs: 0x000 - 0x7FF (max 2047)
    # 29-bit IDs: 0x00000000 - 0x1FFFFFFF (max 536,870,911)

    if id_value <= 0x7FF:
        return ('standard', id_value)
    elif id_value <= 0x1FFFFFFF:
        return ('extended', id_value)
    else:
        return None  # Invalid ID
```

---

## 5. Implementation Plan

### Phase 1: Specification Updates

#### 5.1 Update `obd2_vehicle_spec.md`

**Task 1.1: Add Extended Frame Protocol Section**

Location: After Section 2 (CAN Bus Configuration)

```markdown
## 2.5 Extended Frame (29-bit) Configuration

### 2.5.1 29-bit OBD2 Identifiers

| Identifier | Direction | Description |
|------------|-----------|-------------|
| `0x18DB33F1` | Tester → ECUs | Functional broadcast request |
| `0x18DA00F1` | Tester → ECU | Physical request to Engine |
| `0x18DA01F1` | Tester → ECU | Physical request to Transmission |
| `0x18DAF100` | ECU → Tester | Response from Engine |
| `0x18DAF101` | ECU → Tester | Response from Transmission |

### 2.5.2 Address Encoding

29-bit identifiers encode source and target addresses:

```
Request:  0x18DA[Target][Source]
Response: 0x18DA[Source][Target]

Where:
  Source = 0xF1 (external tester)
  Target = 0x00-0xFF (ECU address)
```
```

**Task 1.2: Add Mixed-Mode Support**

Some vehicles use both 11-bit and 29-bit on the same bus:

```markdown
### 2.5.3 Mixed Addressing Mode

Vehicles may support both addressing modes simultaneously. The simulator
must track which mode was used for the request and respond accordingly:

| Request Mode | Response Mode | Notes |
|--------------|---------------|-------|
| 11-bit | 11-bit | Standard OBD2 |
| 29-bit | 29-bit | Extended OBD2 |
| Mixed | Match request | Some heavy-duty vehicles |
```

**Task 1.3: Update Timing Section**

29-bit frames have slightly different timing due to longer arbitration:

```markdown
### 2.3.1 Extended Frame Timing

| Parameter | 11-bit Frame | 29-bit Frame |
|-----------|--------------|--------------|
| Arbitration time | ~47 bits | ~67 bits |
| Frame overhead | ~47 bits | ~67 bits |
| Max latency increase | - | ~10% |
```

---

#### 5.2 Update `TRACE_PARSER_SPEC.md`

**Task 2.1: Update Message Line Regex**

```python
# Updated regex to handle both 11-bit and 29-bit IDs
MESSAGE_PATTERN = re.compile(
    r'^\s*(\d+)\)\s+'                    # Message number
    r'([\d.]+)\s+'                        # Time offset (ms)
    r'(Rx|Tx)\s+'                         # Direction
    r'([0-9A-Fa-f]{3,8})[hHxX]?\s+'       # CAN ID (3-8 hex chars, optional suffix)
    r'(\d+)\s+'                           # DLC
    r'((?:[0-9A-Fa-f]{2}\s*)+)'           # Data bytes
    r'\s*$'
)
```

**Task 2.2: Add Frame Type Classification**

```python
class CANIdentifier:
    """Represents a CAN identifier with type information."""

    STANDARD_MAX = 0x7FF
    EXTENDED_MAX = 0x1FFFFFFF

    # 11-bit OBD2 ranges
    STD_FUNCTIONAL_REQUEST = 0x7DF
    STD_PHYSICAL_REQUEST_RANGE = range(0x7E0, 0x7E8)
    STD_RESPONSE_RANGE = range(0x7E8, 0x7F0)

    # 29-bit OBD2 patterns
    EXT_FUNCTIONAL_REQUEST = 0x18DB33F1
    EXT_PHYSICAL_REQUEST_MASK = 0x18DA00F1
    EXT_RESPONSE_MASK = 0x18DAF100

    def __init__(self, raw_value, raw_string=None):
        self.raw_value = raw_value
        self.raw_string = raw_string

        if raw_value <= self.STANDARD_MAX:
            self.frame_type = 'standard'
            self.bit_length = 11
        else:
            self.frame_type = 'extended'
            self.bit_length = 29

    def is_obd2_request(self):
        """Check if this ID is an OBD2 request."""
        if self.frame_type == 'standard':
            return (self.raw_value == self.STD_FUNCTIONAL_REQUEST or
                    self.raw_value in self.STD_PHYSICAL_REQUEST_RANGE)
        else:
            # 29-bit: functional or physical pattern
            if self.raw_value == self.EXT_FUNCTIONAL_REQUEST:
                return True
            # Physical: 0x18DAxxF1 where xx is target ECU
            if (self.raw_value & 0xFFFF00FF) == 0x18DA00F1:
                return True
            return False

    def is_obd2_response(self):
        """Check if this ID is an OBD2 response."""
        if self.frame_type == 'standard':
            return self.raw_value in self.STD_RESPONSE_RANGE
        else:
            # 29-bit: 0x18DAF1xx where xx is source ECU
            return (self.raw_value & 0xFFFFFF00) == 0x18DAF100

    def get_ecu_address(self):
        """Extract ECU address from response ID."""
        if self.frame_type == 'standard':
            return self.raw_value - 0x7E8
        else:
            return self.raw_value & 0xFF

    def get_physical_request_id(self, ecu_address):
        """Get physical request ID for an ECU address."""
        if self.frame_type == 'standard':
            return 0x7E0 + ecu_address
        else:
            return 0x18DA00F1 | (ecu_address << 8)

    def to_hex_string(self):
        """Format as hex string."""
        if self.frame_type == 'standard':
            return f"0x{self.raw_value:03X}"
        else:
            return f"0x{self.raw_value:08X}"
```

**Task 2.3: Update OBD2Extractor Class**

```python
class OBD2Extractor:
    """Extract OBD2 request/response pairs with extended frame support."""

    def __init__(self):
        self.requests = []
        self.responses = {}
        self.current_request = None
        self.detected_frame_type = None  # 'standard', 'extended', or 'mixed'

    def process_message(self, msg):
        can_id = CANIdentifier(msg['can_id'])

        # Track frame type usage
        if self.detected_frame_type is None:
            self.detected_frame_type = can_id.frame_type
        elif self.detected_frame_type != can_id.frame_type:
            self.detected_frame_type = 'mixed'

        if can_id.is_obd2_request():
            self._handle_request(msg, can_id)
        elif can_id.is_obd2_response():
            self._handle_response(msg, can_id)
        elif self._is_flow_control(msg, can_id):
            self._handle_flow_control(msg, can_id)

    def _is_flow_control(self, msg, can_id):
        """Check if message is flow control (physical request with FC PCI)."""
        if can_id.frame_type == 'standard':
            if can_id.raw_value not in range(0x7E0, 0x7E8):
                return False
        else:
            if (can_id.raw_value & 0xFFFF00FF) != 0x18DA00F1:
                return False

        # Check for flow control PCI
        return (msg['data'][0] >> 4) == 3
```

**Task 2.4: Update Profile Generation**

```python
def generate_profile(self):
    profile = {
        # ... existing fields ...

        'can_config': {
            'bitrate': 500000,
            'frame_type': self.detected_frame_type,  # NEW
            'id_format': self._get_id_format(),       # NEW

            # 11-bit identifiers (if applicable)
            'standard_ids': {
                'functional_request': '0x7DF',
                'physical_request_base': '0x7E0',
                'response_base': '0x7E8'
            } if self.detected_frame_type in ['standard', 'mixed'] else None,

            # 29-bit identifiers (if applicable)
            'extended_ids': {
                'functional_request': '0x18DB33F1',
                'physical_request_pattern': '0x18DAxxF1',
                'response_pattern': '0x18DAF1xx'
            } if self.detected_frame_type in ['extended', 'mixed'] else None
        }
    }
    return profile

def _get_id_format(self):
    if self.detected_frame_type == 'standard':
        return '11-bit'
    elif self.detected_frame_type == 'extended':
        return '29-bit'
    else:
        return 'mixed'
```

---

#### 5.3 Update JSON Profile Schema

**Task 3.1: Extended CAN Config**

```json
{
  "can_config": {
    "bitrate": 500000,
    "frame_type": "standard | extended | mixed",

    "standard_ids": {
      "functional_request": "0x7DF",
      "physical_request_base": "0x7E0",
      "response_base": "0x7E8"
    },

    "extended_ids": {
      "functional_request": "0x18DB33F1",
      "physical_request_pattern": "0x18DAxxF1",
      "response_pattern": "0x18DAF1xx",
      "tester_address": "0xF1"
    }
  }
}
```

**Task 3.2: Extended ECU Definition**

```json
{
  "ecus": [
    {
      "name": "Engine_DME",
      "index": 0,

      "standard_ids": {
        "physical_request": "0x7E0",
        "response": "0x7E8"
      },

      "extended_ids": {
        "address": "0x00",
        "physical_request": "0x18DA00F1",
        "response": "0x18DAF100"
      },

      "padding_byte": "0x00",
      "response_delay_ms": 8
    }
  ]
}
```

**Task 3.3: Extended Response Format**

```json
{
  "responses": {
    "service_01": {
      "0x0C": {
        "description": "Engine RPM",
        "frame_type": "standard",
        "request": {
          "standard": "02 01 0C 00 00 00 00 00",
          "extended": "02 01 0C 00 00 00 00 00"
        },
        "responses": {
          "0x7E8": "04 41 0C 0A 66 00 00 00",
          "0x18DAF100": "04 41 0C 0A 66 00 00 00"
        }
      }
    }
  }
}
```

---

### Phase 2: Parser Implementation

#### 5.4 Implementation Tasks

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| P2.1 | Update regex for 29-bit IDs | High | Low |
| P2.2 | Implement CANIdentifier class | High | Medium |
| P2.3 | Update OBD2Extractor for 29-bit | High | Medium |
| P2.4 | Update BroadcastAnalyzer for 29-bit | Medium | Low |
| P2.5 | Update profile JSON generation | High | Medium |
| P2.6 | Add frame type auto-detection | High | Low |
| P2.7 | Add unit tests for 29-bit parsing | High | Medium |
| P2.8 | Update CLI output for frame type | Low | Low |

---

### Phase 3: Simulator Updates

#### 5.5 Simulator Changes

**Task 4.1: Request Handler**

```python
class OBD2Simulator:
    def __init__(self, profile):
        self.profile = profile
        self.frame_type = profile['can_config']['frame_type']

    def handle_request(self, can_id, data):
        """Handle incoming OBD2 request."""
        id_obj = CANIdentifier(can_id)

        if not id_obj.is_obd2_request():
            return None

        # Find matching response
        service = data[1]
        pid = data[2] if len(data) > 2 else None

        response_data = self._lookup_response(service, pid)
        if response_data is None:
            return self._negative_response(service, 0x12)

        # Generate response with matching frame type
        response_id = self._get_response_id(id_obj)
        return (response_id, response_data)

    def _get_response_id(self, request_id):
        """Get response ID matching request frame type."""
        if request_id.frame_type == 'standard':
            # 0x7DF -> 0x7E8, 0x7E0 -> 0x7E8, etc.
            if request_id.raw_value == 0x7DF:
                return 0x7E8  # Primary ECU responds to broadcast
            else:
                return request_id.raw_value + 8
        else:
            # 29-bit: swap source/target
            if request_id.raw_value == 0x18DB33F1:
                return 0x18DAF100  # Primary ECU
            else:
                # 0x18DAxxF1 -> 0x18DAF1xx
                target = (request_id.raw_value >> 8) & 0xFF
                return 0x18DAF100 | target
```

**Task 4.2: Response Transmission**

```python
def send_response(self, can_interface, response_id, data, frame_type):
    """Send response with correct frame format."""
    if frame_type == 'extended':
        can_interface.send_extended(response_id, data)
    else:
        can_interface.send_standard(response_id, data)
```

---

### Phase 4: Testing

#### 5.6 Test Cases

**Test Case 1: 11-bit Trace Parsing**
- Input: Existing BMW_OneStep.trc (11-bit)
- Expected: frame_type = 'standard', all IDs in 0x000-0x7FF range

**Test Case 2: 29-bit Trace Parsing**
- Input: Heavy-duty vehicle trace with 29-bit IDs
- Expected: frame_type = 'extended', functional request = 0x18DB33F1

**Test Case 3: Mixed Mode Trace**
- Input: Trace with both 11-bit and 29-bit frames
- Expected: frame_type = 'mixed', both ID sets populated

**Test Case 4: ECU Address Extraction**
- Input: 0x18DAF105
- Expected: ECU address = 0x05

**Test Case 5: Physical Request ID Generation**
- Input: ECU address 0x03, frame_type = 'extended'
- Expected: 0x18DA03F1

---

## 6. File Changes Summary

### 6.1 Modified Files

| File | Changes |
|------|---------|
| `obd2_vehicle_spec.md` | Add Section 2.5 (Extended Frame Configuration) |
| | Update Section 2.2 (add extended ID table) |
| | Update Section 11 (multi-ECU with extended) |
| | Add Appendix C (29-bit ID reference) |
| `TRACE_PARSER_SPEC.md` | Update Section 2.2 (line format for extended) |
| | Update Section 3.1 (classification for 29-bit) |
| | Add CANIdentifier class |
| | Update OBD2Extractor class |
| | Update profile generation |
| | Add extended frame test cases |
| `profiles/TEMPLATE.json` | Add extended_ids section |
| | Add frame_type field |

### 6.2 New Files

| File | Purpose |
|------|---------|
| `profiles/TEMPLATE_29BIT.json` | Template for 29-bit vehicles |
| `test_traces/extended_frame_sample.trc` | Test trace with 29-bit IDs |

---

## 7. Validation Checklist

### 7.1 Specification Validation

- [ ] 29-bit ID format documented correctly
- [ ] ECU address encoding explained
- [ ] Mixed mode handling defined
- [ ] Timing differences noted

### 7.2 Parser Validation

- [ ] Regex handles 3-8 hex digit IDs
- [ ] Frame type auto-detected correctly
- [ ] ECU addresses extracted properly
- [ ] Flow control works for both types
- [ ] Multi-frame reassembly works for both

### 7.3 Profile Validation

- [ ] JSON schema updated
- [ ] Both ID formats stored when mixed
- [ ] ECU definitions include both formats
- [ ] Response lookup works for both

### 7.4 Simulator Validation

- [ ] Responds with matching frame type
- [ ] Correct response ID calculation
- [ ] Broadcast responses use correct format

---

## 8. Implementation Schedule

| Phase | Tasks | Dependencies |
|-------|-------|--------------|
| **Phase 1** | Specification updates | None |
| **Phase 2** | Parser implementation | Phase 1 |
| **Phase 3** | Simulator updates | Phase 2 |
| **Phase 4** | Testing & validation | Phase 3 |

---

## 9. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PCAN extended format varies by version | Medium | Support multiple format variants |
| Mixed mode vehicles rare | Low | Test with synthetic traces |
| 29-bit timing differences | Low | Document but don't enforce |
| Backwards compatibility | Medium | Default to 11-bit if not specified |

---

## Appendix A: 29-bit ID Quick Reference

### Common 29-bit OBD2 Identifiers

| Purpose | ID | Binary Breakdown |
|---------|-----|------------------|
| Functional Request | 0x18DB33F1 | `000 11000 11011011 00110011 11110001` |
| Engine Request | 0x18DA00F1 | `000 11000 11011010 00000000 11110001` |
| Engine Response | 0x18DAF100 | `000 11000 11011010 11110001 00000000` |
| Trans Request | 0x18DA01F1 | `000 11000 11011010 00000001 11110001` |
| Trans Response | 0x18DAF101 | `000 11000 11011010 11110001 00000001` |

### J1939 PGN Mapping

```
29-bit ID: PPP RR PPPPPPPP SSSSSSSS DDDDDDDD
           │   │  │         │         │
           │   │  │         │         └── Destination Address
           │   │  │         └── Source Address
           │   │  └── PGN (Parameter Group Number)
           │   └── Reserved / Data Page
           └── Priority (0-7)

OBD Request PGN:  0xDB33 (56115)
OBD Response PGN: 0xDA00 (55808) base
```

---

## Appendix B: Sample 29-bit Trace

```
;$FILEVERSION=1.1
;$STARTTIME=46004.5
;
;   Start time: 12/13/2025 12:00:00.000.0
;   Generated by PCAN-View v5.3.2.952
;
;---+--   ----+----  --+--  ----+-------  +  -+ -- -- -- -- -- -- --
     1)         0.0  Rx      18DB33F1  8  02 01 00 00 00 00 00 00
     2)         8.2  Rx      18DAF100  8  06 41 00 BE 3F A8 13 00
     3)        16.5  Rx      18DAF101  8  06 41 00 98 18 80 01 AA
     4)       100.0  Rx      18DB33F1  8  02 01 0C 00 00 00 00 00
     5)       108.1  Rx      18DAF100  8  04 41 0C 0A 66 00 00 00
     6)       200.0  Rx      18DB33F1  8  02 09 02 00 00 00 00 00
     7)       208.3  Rx      18DAF100  8  10 14 49 02 01 35 55 58
     8)       209.0  Rx      18DA00F1  8  30 00 00 00 00 00 00 00
     9)       212.1  Rx      18DAF100  8  21 54 53 33 43 35 58 4B
    10)       213.0  Rx      18DAF100  8  22 30 5A 30 32 36 35 36
```

---

**Document End**
