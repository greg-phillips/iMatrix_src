# OBD2 Vehicle Simulator - Implementation Plan

**Document Version**: 1.1
**Date**: 2025-12-13
**Last Updated**: 2025-12-13
**Status**: Approved for Implementation
**Author**: Claude Code Analysis

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Trace Analysis Comparison](#2-trace-analysis-comparison)
3. [Simulator Architecture](#3-simulator-architecture)
4. [Command Line Interface](#4-command-line-interface)
5. [Phase 1 Implementation](#5-phase-1-implementation)
6. [Future Enhancements](#6-future-enhancements)
7. [Implementation Todo Lists](#7-implementation-todo-lists)
8. [Testing Strategy](#8-testing-strategy)
9. [File Structure](#9-file-structure)

---

## 1. Executive Summary

### 1.1 Purpose

Develop an OBD2 Vehicle Simulator for bench testing telematics gateways. The simulator will respond to OBD2 requests with pre-captured vehicle responses, supporting multiple vehicle profiles extracted from PCAN trace files.

### 1.2 Key Requirements

- Support both 11-bit standard and 29-bit extended CAN frames
- Support two operating modes observed in traces:
  - **Discovery Mode**: Full PID enumeration (BMW_OneStep.trc pattern)
  - **Polling Mode**: Passive period followed by continuous monitoring (BMW_PUI.trc pattern)
- Configurable dynamic value handling
- Configurable unsupported PID response behavior
- Multi-ECU simulation with correct timing and padding
- Background broadcast message generation

### 1.3 Implementation Phases

| Phase | Scope | Priority |
|-------|-------|----------|
| Phase 1 | Core simulator with static value replay | **Now** |
| Phase 2 | Dynamic value simulation (random/ranges) | Future |
| Phase 3 | Scenario-based simulation (driving profiles) | Future |

---

## 2. Trace Analysis Comparison

### 2.1 BMW_OneStep.trc Characteristics

| Attribute | Value |
|-----------|-------|
| Duration | ~41 seconds |
| Total Messages | 1130 |
| First OBD2 Request | Early in trace (~100ms) |
| Query Pattern | Full sequential PID discovery |
| PIDs Queried | 00, 01, 03, 04, 05, 06, 07, 0B, 0C, 0D, 0E, 0F, 10, 11, 13, 14, 15, 1C, 1F, 20, 21, 2F, 30, 31, 32, 33, 34, 3C, 40, 41, 42, 43, 44, 45, 46, 49, 4A, 4C, 4D, 4E, 51, 52, 53, 5C, 60, 61, 62, 63, 64, 67, 68, 6B, 80, 83, A0, A2 |
| Services Used | 01, 03, 07, 09, 0A |
| VIN Retrieved | Yes (5UXTS3C5XK0Z02656) |
| Operating Mode | **Discovery/Scan** |

### 2.2 BMW_PUI.trc Characteristics

| Attribute | Value |
|-----------|-------|
| Duration | ~40.7 seconds |
| Total Messages | 1117 |
| First OBD2 Request | 11731.7ms (delayed start) |
| Passive Period | ~11.7 seconds of broadcast-only traffic |
| Query Pattern | Limited discovery, then continuous polling |
| PIDs Queried | 00, 20, 40, 60, 80, A0 (discovery), then 0C, 0D, 05, 10, 11, 1F (polling) |
| Polling Interval | ~250ms for RPM, ~500-750ms for Speed |
| Services Used | 01, 09 |
| VIN Retrieved | Yes (same VIN) |
| Operating Mode | **Passive Until Interrogated (PUI)** |

### 2.3 Key Differences

| Aspect | BMW_OneStep.trc | BMW_PUI.trc |
|--------|-----------------|-------------|
| Startup Behavior | Immediate queries | 11.7s passive listening |
| Discovery Scope | Full PID enumeration | Supported PID bitmaps only |
| Monitoring | Single query per PID | Continuous polling loop |
| Dynamic Values | Mostly static snapshots | Varying RPM values observed |
| DTC Services | 03, 07, 0A queried | Not queried |

### 2.4 PUI Mode Operational Phases

The PUI (Passive Until Interrogated) mode operates in distinct phases:

```
Phase 1: Passive Listening (0ms - 11731ms)
├── Broadcast messages only (no OBD2 traffic)
├── 0x003C: ~117 messages @ 100ms interval
├── 0x0130: ~117 messages @ 100ms interval
├── 0x0799: ~23 messages @ 500ms interval
└── 0x07C1: ~11 messages @ 1000ms interval

Phase 2: Limited Discovery (11731ms - ~15000ms)
├── PID 0x00 (Supported PIDs 01-20)
├── PID 0x20 (Supported PIDs 21-40)
├── PID 0x40 (Supported PIDs 41-60)
├── PID 0x60 (Supported PIDs 61-80)
├── PID 0x80 (Supported PIDs 81-A0)
├── PID 0xA0 (Supported PIDs A1-C0)
└── Service 09 PID 0x02 (VIN)

Phase 3: Continuous Polling (~15000ms - end)
├── RPM (0x0C): Polled every ~1250ms, 20+ queries
├── Speed (0x0D): Polled every ~2250ms, 10+ queries
├── Coolant Temp (0x05): Occasional single queries
├── MAF (0x10): Occasional single queries
├── Throttle (0x11): Occasional single queries
└── Run Time (0x1F): Sporadic queries
```

**Simulator Implication**: The simulator responds identically regardless of query timing - it simply answers requests as they arrive. The distinction matters primarily for:
1. Profile generation (parser tracks patterns)
2. Future scenario-based simulation (Phase 3)
3. Understanding expected gateway behavior during testing

### 2.5 Common Elements (Both Traces)

| Element | Value |
|---------|-------|
| CAN Bitrate | 500 kbps |
| Frame Format | 11-bit standard |
| Functional Request ID | 0x7DF |
| ECU 1 Response ID | 0x7E8 (padding: 0x00) |
| ECU 2 Response ID | 0x7E9 (padding: 0xAA) |
| ECU 3 Response ID | 0x7EF (padding: 0xFF) |
| Response Timing | 5-15ms per ECU |
| VIN | 5UXTS3C5XK0Z02656 |
| Broadcast IDs | 0x003C, 0x0130, 0x0799, 0x07C1 |

### 2.6 Broadcast Message Patterns

| CAN ID | DLC | Interval | Pattern Type |
|--------|-----|----------|--------------|
| 0x003C | 8 | ~100ms | Rolling counter (byte 1) |
| 0x0130 | 5 | ~100ms | Static (F7 FF FF FF FF) |
| 0x0799 | 7 | ~500ms | Variable data |
| 0x07C1 | 8 | ~1000ms | Semi-static |

### 2.7 Trace Type Compatibility Verification

The following matrix confirms that all features from both trace types are fully supported:

| Feature | BMW_OneStep.trc | BMW_PUI.trc | Parser Support | Simulator Support |
|---------|-----------------|-------------|----------------|-------------------|
| Operating Mode Detection | Discovery | PUI | ✅ `_detect_operating_mode()` | ✅ Profile metadata |
| Multi-ECU Responses | 0x7E8, 0x7E9, 0x7EF | 0x7E8, 0x7E9, 0x7EF | ✅ Per-ECU tracking | ✅ ResponseGenerator |
| ECU Padding Bytes | 0x00, 0xAA, 0xFF | 0x00, 0xAA, 0xFF | ✅ Auto-detected | ✅ ECUConfig |
| Response Timing | 6-23ms delays | 6-23ms delays | ✅ Delay tracking | ✅ Configurable |
| Single-Frame Responses | Service 01 PIDs | Service 01 PIDs | ✅ Full support | ✅ ISOTPHandler |
| Multi-Frame (VIN) | Service 09 PID 02 | Service 09 PID 02 | ✅ Frame reassembly | ✅ ISOTPHandler |
| Flow Control | 0x7E0 FC frames | 0x7E0 FC frames | ✅ Tracked | ✅ FC handling |
| DTC Services | 03, 07, 0A | Not queried | ✅ When present | ✅ ResponseGenerator |
| Dynamic Value Tracking | Single snapshots | Repeated queries | ✅ `_track_dynamic_value()` | ✅ Phase 2 |
| Polling Pattern Analysis | N/A | RPM, Speed polling | ✅ `get_polling_analysis()` | ✅ Profile metadata |
| Broadcast: Rolling Counter | 0x003C byte 1 | 0x003C byte 1 | ✅ Pattern detection | ✅ BroadcastGenerator |
| Broadcast: Static | 0x0130, 0x07C1 | 0x0130, 0x07C1 | ✅ Pattern detection | ✅ BroadcastGenerator |
| Broadcast: Variable | 0x0799 | 0x0799 | ✅ Pattern detection | ✅ BroadcastGenerator |

**Profile Schema Support**: Both traces generate profiles conforming to schema v1.1 with:
- `trace_characteristics`: Operating mode, passive phase duration, first OBD2 timestamp
- `polling_patterns`: Query frequency analysis per PID (single_query, continuous_polling, sporadic)
- `dynamic_values`: Value ranges for PIDs with observed variation (used in Phase 2)
- `broadcast_messages`: Full pattern details including rolling counter configuration

---

## 3. Simulator Architecture

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    OBD2 Vehicle Simulator                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   CLI       │  │   Config    │  │   Profile Loader        │ │
│  │   Parser    │──│   Manager   │──│   (JSON Parser)         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Simulator Core                           ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ ││
│  │  │ Request       │  │ Response      │  │ Value           │ ││
│  │  │ Matcher       │  │ Generator     │  │ Provider        │ ││
│  │  └───────────────┘  └───────────────┘  └─────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    CAN Interface Layer                      ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ ││
│  │  │ Frame         │  │ ISO-TP        │  │ Broadcast       │ ││
│  │  │ Handler       │  │ Handler       │  │ Generator       │ ││
│  │  └───────────────┘  └───────────────┘  └─────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              SocketCAN / Virtual CAN Driver                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Module Descriptions

#### 3.2.1 CLI Parser
- Parses command line arguments
- Validates options and parameters
- Provides help and usage information

#### 3.2.2 Config Manager
- Manages runtime configuration
- Merges CLI options with profile defaults
- Provides configuration to all modules

#### 3.2.3 Profile Loader
- Loads vehicle profile JSON files
- Validates profile schema
- Builds internal response lookup tables

#### 3.2.4 Request Matcher
- Receives incoming CAN frames
- Identifies OBD2 requests (functional and physical)
- Routes to appropriate response generator

#### 3.2.5 Response Generator
- Looks up responses from profile
- Handles multi-ECU responses with correct timing
- Manages ISO-TP multi-frame sequences

#### 3.2.6 Value Provider (Phase 1: Static)
- Returns captured static values from profile
- Interface designed for future dynamic providers

#### 3.2.7 Frame Handler
- Manages CAN frame transmission/reception
- Handles 11-bit and 29-bit frame formats
- Implements frame queuing and timing

#### 3.2.8 ISO-TP Handler
- Handles multi-frame message segmentation
- Manages flow control frames
- Tracks multi-frame session state

#### 3.2.9 Broadcast Generator
- Generates periodic broadcast messages
- Maintains rolling counters where applicable
- Configurable enable/disable per message

---

## 4. Command Line Interface

### 4.1 Synopsis

```
obd2_sim [OPTIONS] --profile <PROFILE_FILE>
obd2_sim --help
obd2_sim --version
```

### 4.2 Required Arguments

| Argument | Description |
|----------|-------------|
| `--profile <FILE>` | Path to vehicle profile JSON file |

### 4.3 CAN Interface Options

| Option | Default | Description |
|--------|---------|-------------|
| `--interface <IF>` | `vcan0` | CAN interface name |
| `--bitrate <RATE>` | `500000` | CAN bitrate (ignored for vcan) |
| `--extended` | disabled | Enable 29-bit extended frame mode |

### 4.4 Value Mode Options (Phase 1: Static Only)

| Option | Default | Description |
|--------|---------|-------------|
| `--value-mode <MODE>` | `static` | Value generation mode |

**Supported Modes:**
- `static` - Replay captured values from profile **(Phase 1)**
- `random` - Random values within defined ranges **(Future: Phase 2)**
- `scenario` - Scenario-based value sequences **(Future: Phase 3)**

### 4.5 Unsupported PID Handling

| Option | Default | Description |
|--------|---------|-------------|
| `--unsupported-pid <MODE>` | `no-response` | Behavior for unsupported PIDs |

**Supported Modes:**
- `no-response` - Do not respond (timeout) **(Default)**
- `nrc-12` - Return NRC 0x12 (subfunction not supported)
- `nrc-11` - Return NRC 0x11 (service not supported)

### 4.6 Broadcast Options

| Option | Default | Description |
|--------|---------|-------------|
| `--enable-broadcast` | enabled | Enable broadcast message generation |
| `--disable-broadcast` | - | Disable all broadcast messages |
| `--broadcast-ids <IDS>` | all | Comma-separated list of broadcast IDs to enable |

### 4.7 Timing Options

| Option | Default | Description |
|--------|---------|-------------|
| `--response-delay <MS>` | from profile | Base response delay in milliseconds |
| `--inter-ecu-delay <MS>` | from profile | Delay between ECU responses |
| `--jitter <MS>` | `0` | Random jitter to add to delays |

### 4.8 Logging Options

| Option | Default | Description |
|--------|---------|-------------|
| `--log-level <LEVEL>` | `info` | Log level: debug, info, warn, error |
| `--log-file <FILE>` | stdout | Log output file |
| `--log-frames` | disabled | Log all CAN frames |

### 4.9 Operational Options

| Option | Default | Description |
|--------|---------|-------------|
| `--daemon` | disabled | Run as background daemon |
| `--pid-file <FILE>` | none | Write PID to file (daemon mode) |
| `--stats-interval <SEC>` | `0` | Print statistics every N seconds (0=disabled) |

### 4.10 Example Commands

```bash
# Basic usage with virtual CAN
obd2_sim --profile profiles/BMW_X3_2019.json --interface vcan0

# With extended frames and custom timing
obd2_sim --profile profiles/BMW_X3_2019.json --extended --response-delay 10

# Disable broadcast, use NRC for unsupported PIDs
obd2_sim --profile profiles/BMW_X3_2019.json --disable-broadcast --unsupported-pid nrc-12

# Debug mode with frame logging
obd2_sim --profile profiles/BMW_X3_2019.json --log-level debug --log-frames

# Production daemon mode
obd2_sim --profile profiles/BMW_X3_2019.json --daemon --pid-file /var/run/obd2_sim.pid
```

---

## 5. Phase 1 Implementation

### 5.1 Scope

Phase 1 delivers a fully functional simulator with:
- Static value replay from captured profiles
- Support for both 11-bit and 29-bit CAN frames
- Multi-ECU response simulation
- ISO-TP multi-frame support
- Broadcast message generation
- Configurable unsupported PID handling
- Comprehensive logging

### 5.2 Language and Dependencies

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.8+ | Rapid development, SocketCAN support |
| CAN Library | python-can | Cross-platform, well-maintained |
| JSON Library | Built-in json | Standard library |
| Argument Parser | argparse | Standard library |
| Logging | Built-in logging | Standard library |

### 5.3 Core Classes

#### 5.3.1 `VehicleProfile`
```python
class VehicleProfile:
    """
    Loads and manages vehicle profile data from parsed trace files.

    Supports profile schema v1.1 which includes:
    - trace_characteristics: Operating mode, timing metadata
    - polling_patterns: Query frequency analysis per PID
    - dynamic_values: Value ranges for PIDs with variation (Phase 2)
    - broadcast_messages: Background CAN traffic patterns
    """

    def __init__(self, profile_path: str)
    def get_response(self, service: int, pid: int, ecu_id: int) -> Optional[bytes]
    def get_ecus(self) -> List[ECUConfig]
    def get_broadcast_messages(self) -> List[dict]
    def get_vin(self) -> str
    def supports_pid(self, service: int, pid: int) -> bool

    # Profile metadata methods (from trace analysis)
    def get_trace_characteristics(self) -> dict
    def get_polling_patterns(self) -> dict
    def get_dynamic_values(self) -> dict  # For Phase 2 integration

    # Utility methods
    def get_operating_mode(self) -> str  # 'discovery' or 'pui'
    def get_continuously_polled_pids(self) -> List[int]
```

#### 5.3.2 `ECUConfig`
```python
@dataclass
class ECUConfig:
    """Configuration for a single ECU."""
    name: str
    index: int
    physical_request_id: int
    response_id: int
    padding_byte: int
    response_delay_ms: float
    extended_frame: bool = False
```

#### 5.3.3 `OBD2Simulator`
```python
class OBD2Simulator:
    """Main simulator class."""

    def __init__(self, config: SimulatorConfig, profile: VehicleProfile)
    def start(self) -> None
    def stop(self) -> None
    def handle_frame(self, frame: can.Message) -> None
    def send_response(self, ecu: ECUConfig, data: bytes) -> None
```

#### 5.3.4 `RequestMatcher`
```python
class RequestMatcher:
    """Identifies and parses OBD2 requests."""

    def __init__(self, config: SimulatorConfig)
    def is_obd2_request(self, frame: can.Message) -> bool
    def parse_request(self, frame: can.Message) -> Optional[OBD2Request]
    def get_target_ecus(self, request: OBD2Request) -> List[ECUConfig]
```

#### 5.3.5 `ResponseGenerator`
```python
class ResponseGenerator:
    """Generates OBD2 responses."""

    def __init__(self, profile: VehicleProfile, value_provider: ValueProvider)
    def generate_response(self, request: OBD2Request, ecu: ECUConfig) -> Optional[bytes]
    def generate_multi_frame(self, request: OBD2Request, ecu: ECUConfig) -> List[bytes]
```

#### 5.3.6 `ValueProvider` (Abstract Base)
```python
class ValueProvider(ABC):
    """Abstract base for value providers."""

    @abstractmethod
    def get_value(self, service: int, pid: int, ecu_id: int) -> bytes

class StaticValueProvider(ValueProvider):
    """Phase 1: Returns static values from profile."""

    def __init__(self, profile: VehicleProfile)
    def get_value(self, service: int, pid: int, ecu_id: int) -> bytes
```

#### 5.3.7 `ISOTPHandler`
```python
class ISOTPHandler:
    """Handles ISO-TP multi-frame messages."""

    def __init__(self, can_interface: can.Bus)
    def send_single_frame(self, arbitration_id: int, data: bytes) -> None
    def send_multi_frame(self, arbitration_id: int, data: bytes) -> None
    def handle_flow_control(self, frame: can.Message) -> None
```

#### 5.3.8 `BroadcastConfig`
```python
@dataclass
class BroadcastConfig:
    """Configuration for a single broadcast message from parsed trace."""
    can_id: int
    interval_ms: float
    dlc: int
    pattern_type: str  # 'static' or 'dynamic'

    # For static patterns
    static_data: Optional[bytes] = None

    # For dynamic patterns
    template: Optional[bytes] = None  # Base data with placeholders
    static_bytes: List[int] = field(default_factory=list)  # Byte positions that don't change
    varying_bytes: List[dict] = field(default_factory=list)  # Config for each varying byte

    # Runtime state for rolling counters
    counter_values: Dict[int, int] = field(default_factory=dict)  # position -> current value
```

#### 5.3.9 `BroadcastGenerator`
```python
class BroadcastGenerator:
    """
    Generates periodic broadcast messages matching patterns from parsed trace.

    Supports:
    - Static messages (identical data every time)
    - Dynamic messages with rolling counters
    - Dynamic messages with calculated checksums (future)
    """

    def __init__(self, can_interface: can.Bus, config: SimulatorConfig,
                 broadcast_configs: List[BroadcastConfig]):
        self.can_interface = can_interface
        self.config = config
        self.broadcasts = broadcast_configs
        self.timers = {}  # can_id -> timer thread
        self.running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start all broadcast message timers."""
        self.running = True
        for bc in self.broadcasts:
            if self._is_enabled(bc.can_id):
                self._start_broadcast_timer(bc)

    def stop(self) -> None:
        """Stop all broadcast timers."""
        self.running = False
        for timer in self.timers.values():
            timer.cancel()
        self.timers.clear()

    def _start_broadcast_timer(self, bc: BroadcastConfig) -> None:
        """Start periodic timer for a single broadcast message."""
        def send_broadcast():
            if not self.running:
                return
            self._send_message(bc)
            # Reschedule
            timer = threading.Timer(bc.interval_ms / 1000.0, send_broadcast)
            timer.daemon = True
            self.timers[bc.can_id] = timer
            timer.start()

        # Initial send
        send_broadcast()

    def _send_message(self, bc: BroadcastConfig) -> None:
        """Generate and send a single broadcast message."""
        if bc.pattern_type == 'static':
            data = bc.static_data
        else:
            data = self._generate_dynamic_data(bc)

        msg = can.Message(
            arbitration_id=bc.can_id,
            data=data,
            is_extended_id=False
        )

        try:
            self.can_interface.send(msg)
        except can.CanError as e:
            logging.warning(f"Failed to send broadcast 0x{bc.can_id:03X}: {e}")

    def _generate_dynamic_data(self, bc: BroadcastConfig) -> bytes:
        """Generate data for dynamic broadcast message."""
        data = bytearray(bc.template)

        with self._lock:
            for vb in bc.varying_bytes:
                pos = vb['position']

                if vb.get('pattern') == 'rolling_counter':
                    # Update rolling counter
                    if pos not in bc.counter_values:
                        bc.counter_values[pos] = vb['values'][0]  # Start at first observed value

                    data[pos] = bc.counter_values[pos]

                    # Increment for next time
                    increment = vb.get('increment', 1)
                    bc.counter_values[pos] = (bc.counter_values[pos] + increment) % 256

                    # Handle wrap within observed range if specified
                    if 'range' in vb:
                        min_val, max_val = vb['range']
                        if bc.counter_values[pos] > max_val:
                            bc.counter_values[pos] = min_val
                        elif bc.counter_values[pos] < min_val:
                            bc.counter_values[pos] = max_val
                else:
                    # For non-counter varying bytes, use first observed value
                    # (Future: could implement random selection or other patterns)
                    data[pos] = vb['values'][0] if vb['values'] else 0

        return bytes(data)

    def _is_enabled(self, can_id: int) -> bool:
        """Check if broadcast is enabled based on config."""
        if not self.config.broadcast_enabled:
            return False
        if self.config.broadcast_ids:
            return can_id in self.config.broadcast_ids
        return True

    @classmethod
    def from_profile(cls, can_interface: can.Bus, config: SimulatorConfig,
                     profile: VehicleProfile) -> 'BroadcastGenerator':
        """Create BroadcastGenerator from parsed vehicle profile."""
        broadcast_configs = []

        for bc_data in profile.get_broadcast_messages():
            can_id = int(bc_data['can_id'], 16)
            interval_ms = bc_data['interval_ms']
            dlc = bc_data['dlc']
            pattern = bc_data['pattern']

            if pattern['type'] == 'static':
                config_obj = BroadcastConfig(
                    can_id=can_id,
                    interval_ms=interval_ms,
                    dlc=dlc,
                    pattern_type='static',
                    static_data=bytes.fromhex(pattern['data'].replace(' ', ''))
                )
            else:  # dynamic
                template_hex = pattern.get('template', bc_data['sample_data'][0])
                template = bytes.fromhex(template_hex.replace(' ', '').replace('XX', '00'))

                config_obj = BroadcastConfig(
                    can_id=can_id,
                    interval_ms=interval_ms,
                    dlc=dlc,
                    pattern_type='dynamic',
                    template=template,
                    static_bytes=pattern.get('static_bytes', []),
                    varying_bytes=pattern.get('varying_bytes', [])
                )

            broadcast_configs.append(config_obj)

        return cls(can_interface, config, broadcast_configs)
```

### 5.4 Request/Response Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Request Processing Flow                       │
└─────────────────────────────────────────────────────────────────┘

  CAN Frame Received (e.g., 7DF 02 01 0C 00 00 00 00 00)
         │
         ▼
  ┌─────────────────┐
  │ RequestMatcher  │──── Not OBD2 ────► Ignore
  │ is_obd2_request │
  └────────┬────────┘
           │ Yes
           ▼
  ┌─────────────────┐
  │ RequestMatcher  │
  │ parse_request   │
  └────────┬────────┘
           │ OBD2Request(service=0x01, pid=0x0C, functional=True)
           ▼
  ┌─────────────────┐
  │ RequestMatcher  │
  │ get_target_ecus │──► [ECU1(7E8), ECU2(7E9), ECU3(7EF)]
  └────────┬────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────┐
  │ For each ECU (with inter-ECU delay):            │
  │   ┌─────────────────┐                           │
  │   │ profile.        │                           │
  │   │ supports_pid()  │── No ──► Check unsupported│
  │   └────────┬────────┘          PID handling     │
  │            │ Yes                    │           │
  │            ▼                        ▼           │
  │   ┌─────────────────┐    ┌─────────────────┐   │
  │   │ ResponseGen     │    │ no-response:    │   │
  │   │ generate_resp   │    │ skip            │   │
  │   └────────┬────────┘    │ nrc-12: send    │   │
  │            │             │ NRC response    │   │
  │            ▼             └─────────────────┘   │
  │   ┌─────────────────┐                           │
  │   │ ISOTPHandler    │                           │
  │   │ send_frame(s)   │                           │
  │   └─────────────────┘                           │
  └─────────────────────────────────────────────────┘
```

### 5.5 Multi-Frame (ISO-TP) Handling

```
VIN Request Example (Service 09 PID 02):

  Tester Request:
    7DF: 02 09 02 00 00 00 00 00

  Simulator Response (ECU 7E8):

    1. Send First Frame:
       7E8: 10 14 49 02 01 35 55 58
            │  │  │  │  │  └─────── VIN bytes 1-3 ("5UX")
            │  │  │  │  └────────── Message count (1)
            │  │  │  └───────────── PID (02)
            │  │  └──────────────── Service + 0x40 (49)
            │  └─────────────────── Total length (20 bytes)
            └────────────────────── First Frame indicator (0x1X)

    2. Wait for Flow Control:
       7E0: 30 00 00 00 00 00 00 00
            │  │  └───────────────── Block size, ST (0 = send all)
            │  └──────────────────── Flow status (0 = Clear To Send)
            └─────────────────────── Flow Control indicator (0x3X)

    3. Send Consecutive Frames:
       7E8: 21 54 53 33 43 35 58 4B  (seq=1, "TS3C5XK")
       7E8: 22 30 5A 30 32 36 35 36  (seq=2, "0Z02656")
            │
            └── Consecutive Frame indicator (0x2X) + sequence
```

### 5.6 Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Profile file not found | Exit with error message |
| Invalid profile JSON | Exit with validation errors |
| CAN interface not found | Exit with error message |
| CAN send failure | Log error, continue operation |
| Invalid OBD2 request format | Ignore frame, log warning |
| Flow control timeout | Abort multi-frame, log warning |
| Unsupported service | Apply unsupported-pid handling |

---

## 6. Future Enhancements

### 6.1 Phase 2: Dynamic Value Simulation

**Status**: Documented for future implementation

#### 6.1.1 Integration with Trace-Captured Dynamic Values

The parser captures actual value ranges from traces with repeated PID queries (e.g., BMW_PUI.trc):

```json
{
  "dynamic_values": {
    "service_01_pid_0C_0x7E8": {
      "sample_count": 20,
      "min_raw": 2606,
      "max_raw": 2684,
      "samples": [
        {"time_ms": 16265.8, "value": "0A7A"},
        {"time_ms": 17516.0, "value": "0A64"},
        {"time_ms": 18766.4, "value": "0A72"}
      ]
    }
  }
}
```

This captured data provides realistic bounds for dynamic simulation without requiring manual configuration.

#### 6.1.2 Random Value Provider
```python
class RandomValueProvider(ValueProvider):
    """Generates random values within defined ranges."""

    def __init__(self, profile: VehicleProfile, seed: Optional[int] = None)
    def get_value(self, service: int, pid: int, ecu_id: int) -> bytes

    def _get_range_from_profile(self, service: int, pid: int, ecu_id: str) -> Tuple[int, int]:
        """
        Get value range from profile's dynamic_values section.
        Falls back to PID-specific defaults if not captured.
        """
        dynamic = self.profile.get_dynamic_values()
        key = f"service_{service:02X}_pid_{pid:02X}_{ecu_id}"
        if key in dynamic:
            return (dynamic[key]['min_raw'], dynamic[key]['max_raw'])
        return self._get_default_range(pid)
```

**Features:**
- Random values within min/max ranges from captured trace data
- Fallback to PID-specific defaults when no trace data available
- Configurable random seed for reproducibility
- Gaussian distribution option for realistic variation
- Rate-of-change limiting for smooth transitions

#### 6.1.3 Profile Enhancements for Random Mode
```json
{
  "0x0C": {
    "description": "Engine RPM",
    "dynamic": true,
    "min_value": 600,
    "max_value": 7000,
    "default_value": 800,
    "rate_of_change_max": 500,
    "distribution": "gaussian",
    "unit": "rpm"
  }
}
```

**Note**: When `dynamic_values` from trace analysis is available, those ranges take precedence over manually configured ranges, ensuring the simulator matches observed vehicle behavior.

#### 6.1.4 CLI Options
```
--value-mode random
--random-seed <SEED>
--value-update-rate <MS>
```

### 6.2 Phase 3: Scenario-Based Simulation

**Status**: Documented for future implementation

#### 6.2.1 Scenario File Format
```json
{
  "scenario_name": "city_driving",
  "duration_seconds": 300,
  "segments": [
    {
      "name": "idle",
      "duration_seconds": 30,
      "values": {
        "0x0C": {"type": "constant", "value": 800},
        "0x0D": {"type": "constant", "value": 0}
      }
    },
    {
      "name": "acceleration",
      "duration_seconds": 15,
      "values": {
        "0x0C": {"type": "ramp", "start": 800, "end": 4000},
        "0x0D": {"type": "ramp", "start": 0, "end": 60}
      }
    },
    {
      "name": "cruise",
      "duration_seconds": 60,
      "values": {
        "0x0C": {"type": "constant", "value": 2500, "noise": 50},
        "0x0D": {"type": "constant", "value": 60, "noise": 2}
      }
    }
  ]
}
```

#### 6.2.2 Scenario Value Provider
```python
class ScenarioValueProvider(ValueProvider):
    """Generates values based on scenario timeline."""

    def __init__(self, profile: VehicleProfile, scenario_path: str)
    def start_scenario(self) -> None
    def get_value(self, service: int, pid: int, ecu_id: int) -> bytes
    def get_current_segment(self) -> str
```

#### 6.2.3 CLI Options
```
--value-mode scenario
--scenario <SCENARIO_FILE>
--scenario-loop
--scenario-start-offset <SECONDS>
```

### 6.3 Additional Future Enhancements

#### 6.3.1 DTC Simulation
- Configurable active DTCs
- DTC triggering based on conditions
- Pending → Stored → Permanent DTC lifecycle
- Clear DTC support (Service 04)

#### 6.3.2 Freeze Frame Data (Service 02)
- Capture freeze frame data on DTC set
- Return stored freeze frame data

#### 6.3.3 Interactive Mode
- Runtime PID value modification
- Real-time statistics display
- Command interface for testing

#### 6.3.4 Multi-Vehicle Support
- Multiple simultaneous profiles
- Gateway simulation mode
- CAN bus bridging

#### 6.3.5 Trace Recording
- Record all CAN traffic
- Export to PCAN .trc format
- Playback mode

---

## 7. Implementation Todo Lists

### 7.1 Phase 1 Master Checklist

#### 7.1.1 Project Setup
- [ ] Create project directory structure
- [ ] Initialize Python virtual environment
- [ ] Create requirements.txt with dependencies
- [ ] Create setup.py for package installation
- [ ] Create README.md with usage instructions
- [ ] Create .gitignore for Python project

#### 7.1.2 Configuration Module
- [ ] Define SimulatorConfig dataclass
- [ ] Implement argument parser with all CLI options
- [ ] Implement configuration validation
- [ ] Add configuration file support (optional YAML/JSON)
- [ ] Implement help text and usage examples
- [ ] Add version information

#### 7.1.3 Profile Loader Module
- [ ] Define VehicleProfile class
- [ ] Define ECUConfig dataclass
- [ ] Implement JSON profile loading
- [ ] Implement profile schema validation (v1.1)
- [ ] Build response lookup tables (service → pid → ecu → response)
- [ ] Build supported PID bitmaps
- [ ] Implement VIN extraction
- [ ] Add profile validation error reporting
- [ ] Support both 11-bit and 29-bit profile formats
- [ ] Implement `get_broadcast_messages()` method
  - [ ] Return list of broadcast message configurations
  - [ ] Include can_id, interval_ms, dlc, pattern, sample_data
  - [ ] Preserve pattern type (static/dynamic)
  - [ ] Preserve varying_bytes with rolling counter info
- [ ] Implement `get_trace_characteristics()` method
  - [ ] Return operating_mode ('discovery' or 'pui')
  - [ ] Return passive_phase_duration_ms
  - [ ] Return first_obd2_request_ms
  - [ ] Return total_requests count
  - [ ] Return continuously_polled_pids list
- [ ] Implement `get_polling_patterns()` method
  - [ ] Return dict of PIDs with polling analysis
  - [ ] Include query_count, pattern type, interval statistics
- [ ] Implement `get_dynamic_values()` method (for Phase 2)
  - [ ] Return dict of PIDs with value ranges
  - [ ] Include min_raw, max_raw, sample_count
  - [ ] Include sample data points for reference

#### 7.1.4 CAN Identifier Module
- [ ] Define CANIdentifier class
- [ ] Implement 11-bit identifier handling
- [ ] Implement 29-bit extended identifier handling
- [ ] Implement OBD2 request ID detection (functional and physical)
- [ ] Implement OBD2 response ID calculation
- [ ] Add identifier format conversion utilities

#### 7.1.5 Request Matcher Module
- [ ] Define OBD2Request dataclass
- [ ] Implement is_obd2_request() for 11-bit frames
- [ ] Implement is_obd2_request() for 29-bit frames
- [ ] Implement parse_request() - extract service, PID, data
- [ ] Implement get_target_ecus() for functional requests (0x7DF)
- [ ] Implement get_target_ecus() for physical requests (0x7E0-0x7E7)
- [ ] Handle multi-byte PID requests
- [ ] Handle service-only requests (e.g., Service 03)

#### 7.1.6 Value Provider Module
- [ ] Define ValueProvider abstract base class
- [ ] Implement StaticValueProvider class
- [ ] Implement get_value() returning profile data
- [ ] Handle missing values gracefully
- [ ] Add logging for value retrieval

#### 7.1.7 Response Generator Module
- [ ] Define ResponseGenerator class
- [ ] Implement single-frame response generation
- [ ] Implement multi-frame response generation
- [ ] Handle Service 01 (Current Data) responses
- [ ] Handle Service 02 (Freeze Frame) responses
- [ ] Handle Service 03 (Stored DTCs) responses
- [ ] Handle Service 04 (Clear DTCs) responses
- [ ] Handle Service 07 (Pending DTCs) responses
- [ ] Handle Service 09 (Vehicle Info) responses
- [ ] Handle Service 0A (Permanent DTCs) responses
- [ ] Implement negative response generation (NRC)
- [ ] Apply correct padding bytes per ECU
- [ ] Calculate correct response lengths

#### 7.1.8 ISO-TP Handler Module
- [ ] Define ISOTPHandler class
- [ ] Implement send_single_frame() (SF, PCI type 0x0)
- [ ] Implement send_first_frame() (FF, PCI type 0x1)
- [ ] Implement send_consecutive_frame() (CF, PCI type 0x2)
- [ ] Implement handle_flow_control() (FC, PCI type 0x3)
- [ ] Implement flow control timeout handling
- [ ] Implement block size handling
- [ ] Implement separation time (ST) handling
- [ ] Track multi-frame session state
- [ ] Handle concurrent multi-frame sessions

#### 7.1.9 Broadcast Generator Module
- [ ] Define BroadcastConfig dataclass
  - [ ] CAN ID, interval, DLC fields
  - [ ] pattern_type field ('static' or 'dynamic')
  - [ ] static_data field for static patterns
  - [ ] template, static_bytes, varying_bytes for dynamic patterns
  - [ ] counter_values dict for runtime rolling counter state
- [ ] Define BroadcastGenerator class
- [ ] Implement `from_profile()` class method to load from parsed profile
- [ ] Implement `start()` to begin all broadcast timers
- [ ] Implement `stop()` to cancel all timers
- [ ] Implement `_start_broadcast_timer()` for periodic scheduling
- [ ] Implement `_send_message()` for CAN transmission
- [ ] Implement `_generate_dynamic_data()` for dynamic patterns
  - [ ] Handle rolling counter bytes with increment/wrap
  - [ ] Handle non-counter varying bytes
  - [ ] Apply template with static byte positions
- [ ] Implement `_is_enabled()` for broadcast filtering
- [ ] Add thread-safe locking for counter updates
- [ ] Handle CAN send errors gracefully with logging

#### 7.1.10 Main Simulator Module
- [ ] Define OBD2Simulator class
- [ ] Implement CAN bus initialization
- [ ] Implement main receive loop
- [ ] Implement frame routing to RequestMatcher
- [ ] Implement response scheduling with delays
- [ ] Implement inter-ECU delay handling
- [ ] Implement graceful shutdown
- [ ] Add signal handlers (SIGINT, SIGTERM)
- [ ] Implement daemon mode
- [ ] Implement PID file handling

#### 7.1.11 Logging Module
- [ ] Configure Python logging
- [ ] Implement log level control
- [ ] Implement file logging
- [ ] Implement frame logging (optional detailed mode)
- [ ] Add request/response logging
- [ ] Add statistics logging

#### 7.1.12 Statistics Module
- [ ] Track requests received per service/PID
- [ ] Track responses sent per ECU
- [ ] Track unsupported PID requests
- [ ] Track errors and warnings
- [ ] Implement periodic statistics output
- [ ] Implement statistics summary on shutdown

#### 7.1.13 Testing
- [ ] Create unit tests for CANIdentifier
- [ ] Create unit tests for RequestMatcher
- [ ] Create unit tests for ResponseGenerator
- [ ] Create unit tests for ISOTPHandler
- [ ] Create unit tests for VehicleProfile
- [ ] Create integration test with vcan0
- [ ] Create test script for BMW_X3_2019 profile
- [ ] Create test script for full PID discovery
- [ ] Create test script for VIN retrieval
- [ ] Create test script for multi-ECU responses
- [ ] Document test procedures

#### 7.1.14 Documentation
- [ ] Write comprehensive README.md
- [ ] Document CLI options with examples
- [ ] Document profile JSON schema
- [ ] Document supported OBD2 services
- [ ] Create troubleshooting guide
- [ ] Document virtual CAN setup
- [ ] Create quick-start guide

### 7.2 File-by-File Implementation Checklist

#### obd2_sim/\_\_init\_\_.py
- [ ] Define package version
- [ ] Define public API exports

#### obd2_sim/cli.py
- [ ] Import argparse
- [ ] Define create_parser() function
- [ ] Add all argument definitions
- [ ] Implement validate_args() function
- [ ] Implement main() entry point

#### obd2_sim/config.py
- [ ] Import dataclasses
- [ ] Define SimulatorConfig dataclass
- [ ] Define UnsupportedPIDMode enum
- [ ] Define ValueMode enum
- [ ] Implement load_config() function

#### obd2_sim/profile.py
- [ ] Import json, dataclasses
- [ ] Define ECUConfig dataclass
- [ ] Define BroadcastConfig dataclass
- [ ] Define VehicleProfile class
- [ ] Implement load() method with schema v1.1 validation
- [ ] Implement get_response() method
- [ ] Implement get_ecus() method
- [ ] Implement supports_pid() method
- [ ] Implement get_vin() method
- [ ] Implement get_broadcast_messages() method
- [ ] Implement get_trace_characteristics() method
  - [ ] Return operating_mode, passive_phase_duration_ms, etc.
- [ ] Implement get_polling_patterns() method
- [ ] Implement get_dynamic_values() method
- [ ] Implement get_operating_mode() helper method
- [ ] Implement get_continuously_polled_pids() helper method

#### obd2_sim/can_id.py
- [ ] Define CANIdentifier class
- [ ] Define STANDARD_11BIT constant
- [ ] Define EXTENDED_29BIT constant
- [ ] Define OBD2 ID constants (functional, physical, response)
- [ ] Implement is_obd2_request() method
- [ ] Implement is_obd2_response() method
- [ ] Implement get_response_id() method

#### obd2_sim/request.py
- [ ] Define OBD2Request dataclass
- [ ] Define RequestMatcher class
- [ ] Implement match() method
- [ ] Implement parse() method
- [ ] Implement get_target_ecus() method

#### obd2_sim/value_provider.py
- [ ] Import ABC, abstractmethod
- [ ] Define ValueProvider ABC
- [ ] Define StaticValueProvider class
- [ ] Implement get_value() method

#### obd2_sim/response.py
- [ ] Define ResponseGenerator class
- [ ] Implement generate() method
- [ ] Implement generate_single_frame() method
- [ ] Implement generate_multi_frame() method
- [ ] Implement generate_negative_response() method

#### obd2_sim/isotp.py
- [ ] Define ISOTPHandler class
- [ ] Define PCIType enum (SF, FF, CF, FC)
- [ ] Implement send_single() method
- [ ] Implement send_multi() method
- [ ] Implement handle_flow_control() method

#### obd2_sim/broadcast.py
- [ ] Import threading, can, logging, dataclasses
- [ ] Define BroadcastConfig dataclass
  - [ ] can_id: int
  - [ ] interval_ms: float
  - [ ] dlc: int
  - [ ] pattern_type: str
  - [ ] static_data: Optional[bytes]
  - [ ] template: Optional[bytes]
  - [ ] static_bytes: List[int]
  - [ ] varying_bytes: List[dict]
  - [ ] counter_values: Dict[int, int]
- [ ] Define BroadcastGenerator class
- [ ] Implement __init__() with can_interface, config, broadcasts
- [ ] Implement from_profile() class method
  - [ ] Parse broadcast_messages from profile
  - [ ] Create BroadcastConfig for each (static vs dynamic)
  - [ ] Handle pattern type detection
- [ ] Implement start() method
- [ ] Implement stop() method
- [ ] Implement _start_broadcast_timer() method
- [ ] Implement _send_message() method
- [ ] Implement _generate_dynamic_data() method
  - [ ] Handle rolling_counter pattern
  - [ ] Handle increment and wrap logic
  - [ ] Handle range constraints if specified
- [ ] Implement _is_enabled() method

#### obd2_sim/simulator.py
- [ ] Import can, threading
- [ ] Define OBD2Simulator class
- [ ] Implement __init__() method
- [ ] Implement start() method
- [ ] Implement stop() method
- [ ] Implement _receive_loop() method
- [ ] Implement _handle_frame() method
- [ ] Implement _send_response() method
- [ ] Implement _schedule_responses() method

#### obd2_sim/logging_config.py
- [ ] Import logging
- [ ] Define setup_logging() function
- [ ] Define FrameFormatter class
- [ ] Implement log level mapping

#### obd2_sim/stats.py
- [ ] Define Statistics class
- [ ] Implement increment() method
- [ ] Implement get_summary() method
- [ ] Implement print_periodic() method

### 7.3 Testing Checklist

#### Unit Tests (tests/unit/)
- [ ] test_can_id.py - CAN identifier parsing
- [ ] test_request.py - Request matching and parsing
- [ ] test_response.py - Response generation
- [ ] test_isotp.py - ISO-TP framing
- [ ] test_profile.py - Profile loading
- [ ] test_value_provider.py - Value retrieval

#### Integration Tests (tests/integration/)
- [ ] test_simulator_basic.py - Basic request/response
- [ ] test_simulator_multi_ecu.py - Multi-ECU responses
- [ ] test_simulator_isotp.py - Multi-frame messages
- [ ] test_simulator_broadcast.py - Broadcast messages
- [ ] test_simulator_unsupported.py - Unsupported PID handling

#### System Tests (tests/system/)
- [ ] test_discovery_mode.py - Full PID discovery
- [ ] test_polling_mode.py - Continuous polling
- [ ] test_vin_retrieval.py - VIN multi-frame
- [ ] test_dtc_services.py - DTC request/response

---

## 8. Testing Strategy

### 8.1 Virtual CAN Setup

```bash
# Load vcan module
sudo modprobe vcan

# Create virtual CAN interface
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Verify interface
ip link show vcan0
```

### 8.2 Test Methodology

#### 8.2.1 Unit Testing
- Each module tested in isolation
- Mock CAN interface for unit tests
- pytest framework with fixtures
- Minimum 80% code coverage

#### 8.2.2 Integration Testing
- Test module interactions
- Use virtual CAN interface
- Automated test scripts

#### 8.2.3 System Testing
- Full simulator with real profiles
- Compare against captured traces
- Use can-utils for validation

### 8.3 Validation Commands

```bash
# Send OBD2 request and capture response
cansend vcan0 7DF#0201000000000000
candump vcan0 -n 3

# Expected output (for BMW_X3_2019 profile):
# vcan0  7E8   [8]  06 41 00 BE 3F A8 13 00
# vcan0  7E9   [8]  06 41 00 98 18 80 01 AA
# vcan0  7EF   [8]  06 41 00 98 18 80 01 FF

# Request VIN
cansend vcan0 7DF#0209020000000000
candump vcan0 -n 5

# Monitor broadcast messages
candump vcan0 -t A | grep -E "003C|0130|0799|07C1"
```

### 8.4 Test Cases for BMW_X3_2019 Profile

| Test ID | Description | Request | Expected Response(s) |
|---------|-------------|---------|---------------------|
| TC001 | Supported PIDs 01-20 | 7DF#020100 | 7E8: 06 41 00 BE 3F A8 13, 7E9: 06 41 00 98 18 80 01, 7EF: 06 41 00 98 18 80 01 |
| TC002 | Engine RPM | 7DF#02010C | 7E8: 04 41 0C XX XX, 7E9: 04 41 0C XX XX, 7EF: 04 41 0C XX XX |
| TC003 | Vehicle Speed | 7DF#02010D | 7E8: 03 41 0D XX, 7E9: 03 41 0D XX, 7EF: 03 41 0D XX |
| TC004 | VIN Request | 7DF#020902 | Multi-frame: FF + 2 CFs with VIN |
| TC005 | Unsupported PID | 7DF#0201FF | No response (default) or NRC |
| TC006 | Physical Request | 7E0#020100 | 7E8 only responds |

---

## 9. File Structure

```
obd2_vehicle/
├── obd2_sim/                      # Main package
│   ├── __init__.py               # Package init, version
│   ├── cli.py                    # Command line interface
│   ├── config.py                 # Configuration dataclasses
│   ├── profile.py                # Vehicle profile loader
│   ├── can_id.py                 # CAN identifier handling
│   ├── request.py                # Request matching/parsing
│   ├── response.py               # Response generation
│   ├── value_provider.py         # Value providers (static)
│   ├── isotp.py                  # ISO-TP handler
│   ├── broadcast.py              # Broadcast generator
│   ├── simulator.py              # Main simulator class
│   ├── logging_config.py         # Logging configuration
│   └── stats.py                  # Statistics tracking
│
├── profiles/                      # Vehicle profiles
│   ├── TEMPLATE.json             # Profile template
│   ├── BMW_X3_2019.json          # BMW X3 profile
│   └── ...                       # Additional profiles
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py               # pytest fixtures
│   ├── unit/                     # Unit tests
│   │   ├── test_can_id.py
│   │   ├── test_request.py
│   │   ├── test_response.py
│   │   └── ...
│   ├── integration/              # Integration tests
│   │   ├── test_simulator_basic.py
│   │   └── ...
│   └── system/                   # System tests
│       ├── test_discovery_mode.py
│       └── ...
│
├── docs/                          # Documentation
│   ├── obd2_vehicle_spec.md      # Protocol specification
│   ├── TRACE_PARSER_SPEC.md      # Parser specification
│   ├── EXTENDED_FRAME_SUPPORT_PLAN.md
│   └── OBD2_SIMULATOR_IMPLEMENTATION_PLAN.md  # This document
│
├── scripts/                       # Utility scripts
│   ├── setup_vcan.sh             # Virtual CAN setup
│   ├── run_tests.sh              # Test runner
│   └── trace_parser.py           # Trace file parser
│
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
├── README.md                      # Project README
└── .gitignore                    # Git ignore rules
```

---

## Appendix A: Dependencies

### requirements.txt
```
python-can>=4.0.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

### System Requirements
- Python 3.8+
- Linux with SocketCAN support
- can-utils package (for testing)

---

## Appendix B: Profile Schema Reference

See `profiles/TEMPLATE.json` and `obd2_vehicle_spec.md` for complete profile schema documentation.

### Example Profile (Schema v1.1)

```json
{
  "profile_version": "1.1",
  "profile_name": "BMW_X3_2019",
  "created_date": "2025-12-13",
  "source_trace": "BMW_PUI.trc",

  "vehicle_info": {
    "vin": "5UXTS3C5XK0Z02656",
    "make": "BMW",
    "model": "X3",
    "year": 2019
  },

  "can_config": {
    "bitrate": 500000,
    "functional_request_id": "0x7DF",
    "response_base_id": "0x7E8"
  },

  "timing": {
    "p2_response_ms": 6.2,
    "p2_max_ms": 22.8,
    "inter_ecu_delay_ms": 8
  },

  "ecus": [
    {
      "name": "ECU_0",
      "index": 0,
      "response_id": "0x7E8",
      "physical_request_id": "0x7E0",
      "padding_byte": "0x00",
      "response_delay_ms": 6.2
    },
    {
      "name": "ECU_1",
      "index": 1,
      "response_id": "0x7E9",
      "physical_request_id": "0x7E1",
      "padding_byte": "0xAA",
      "response_delay_ms": 14.5
    },
    {
      "name": "ECU_7",
      "index": 7,
      "response_id": "0x7EF",
      "physical_request_id": "0x7E7",
      "padding_byte": "0xFF",
      "response_delay_ms": 22.8
    }
  ],

  "trace_characteristics": {
    "operating_mode": "pui",
    "passive_phase_duration_ms": 11666.4,
    "first_obd2_request_ms": 11731.7,
    "total_requests": 62,
    "continuously_polled_pids": [
      {"service": 1, "pid": "0x0C", "query_count": 20, "avg_interval_ms": 1250},
      {"service": 1, "pid": "0x0D", "query_count": 10, "avg_interval_ms": 2250}
    ]
  },

  "polling_patterns": {
    "service_01_pid_0C": {
      "query_count": 20,
      "pattern": "continuous_polling",
      "avg_interval_ms": 1250.5,
      "min_interval_ms": 1248.2,
      "max_interval_ms": 1252.8
    },
    "service_01_pid_0D": {
      "query_count": 10,
      "pattern": "continuous_polling",
      "avg_interval_ms": 2250.0,
      "min_interval_ms": 2248.1,
      "max_interval_ms": 2251.9
    }
  },

  "dynamic_values": {
    "service_01_pid_0C_0x7E8": {
      "sample_count": 20,
      "min_raw": 2606,
      "max_raw": 2684,
      "samples": [
        {"time_ms": 16265.8, "value": "0A7A"},
        {"time_ms": 17516.0, "value": "0A64"}
      ]
    }
  },

  "responses": {
    "service_01": {
      "0x00": {
        "request": "02 01 00 00 00 00 00 00",
        "0x7E8": "06 41 00 BE 3F A8 13 00",
        "0x7E9": "06 41 00 98 18 80 01 AA",
        "0x7EF": "06 41 00 98 18 80 01 FF"
      },
      "0x0C": {
        "request": "02 01 0C 00 00 00 00 00",
        "0x7E8": "04 41 0C 0A 66 00 00 00",
        "0x7E9": "04 41 0C 0A 6C AA AA AA",
        "0x7EF": "04 41 0C 0A 6C FF FF FF"
      }
    },
    "service_09": {
      "0x02": {
        "request": "02 09 02 00 00 00 00 00",
        "flow_control": {"can_id": "0x7E0", "data": "30 00 00 00 00 00 00 00"},
        "0x7E8": {
          "frames": [
            "10 14 49 02 01 35 55 58",
            "21 54 53 33 43 35 58 4B",
            "22 30 5A 30 32 36 35 36"
          ],
          "multi_frame": true,
          "total_length": 20
        }
      }
    }
  },

  "broadcast_messages": [
    {
      "can_id": "0x003C",
      "interval_ms": 100,
      "dlc": 8,
      "occurrences": 410,
      "pattern": {
        "type": "dynamic",
        "template": "XX XX 02 12 01 00 2A FF",
        "static_bytes": [2, 3, 4, 5, 6, 7],
        "varying_bytes": [
          {"position": 0, "pattern": "checksum", "values": ["AF", "48", "15"]},
          {"position": 1, "pattern": "rolling_counter", "range": [160, 175], "increment": 1}
        ]
      },
      "sample_data": ["AF A1 02 12 01 00 2A FF", "48 A2 02 12 01 00 2A FF"]
    },
    {
      "can_id": "0x0130",
      "interval_ms": 100,
      "dlc": 5,
      "occurrences": 410,
      "pattern": {
        "type": "static",
        "data": "F7 FF FF FF FF"
      }
    }
  ],

  "metadata": {
    "trace_start_time": "2025-12-13T11:41:47.210000",
    "trace_duration_ms": 40700,
    "total_messages": 1117,
    "generator": "PCAN-View v5.3.2.952",
    "analysis_date": "2025-12-13"
  }
}
```

---

## Appendix C: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-13 | Claude Code | Initial release |
| 1.1 | 2025-12-13 | Claude Code | Added PUI mode operational phases (Section 2.4); Added trace type compatibility verification matrix (Section 2.7); Enhanced VehicleProfile class with trace metadata methods; Updated Profile Loader Module checklist with new schema fields; Added Phase 2 integration with trace-captured dynamic values; Added comprehensive example profile (Appendix B) |

---

*End of Document*
