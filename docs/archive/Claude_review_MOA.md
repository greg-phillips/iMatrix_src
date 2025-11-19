# MOA Protocol Endpoints Reference

## Server to Device Messages

### Message Type 42: Acknowledgement
- **Direction**: Server → Device
- **Size**: 2-3 bytes
- **Purpose**: Acknowledge receipt of device messages
- **Fields**:
  - Msg Type (1 byte): 0x2A
  - Sequence (1 byte): Sequence number being acknowledged
  - Extended ACK (1 byte, optional): For Events 210-215 only (Panic/Privacy/Driver ID)

---

### Message Type 61: UDP Command
- **Direction**: Server → Device
- **Size**: Variable
- **Purpose**: Send serial commands over UDP
- **Platforms**: FJ2500, TM97
- **Fields**:
  - Msg Type (1 byte): 0x3D
  - Command (null-terminated string): ASCII command string

---

### Message Type 64: Peripheral Device Pass-through
- **Direction**: Server → Device
- **Size**: Variable
- **Purpose**: Pass data to peripheral devices via CAN/Serial/BLE
- **Fields**:
  - Msg Type (1 byte): 0x40
  - Peripheral Type (1 byte): Bit 7=Ack indicator, Bits 0-5=Peripheral ID (0=CAN2 29-bit, 1=CAN2 11-bit, 2=Serial, 3=BLE)
  - Message Length (1 byte)
  - Payload (variable): Raw data for peripheral

---

## Device to Server Messages

### Message Type 1: Event
- **Direction**: Device → Server
- **Size**: Variable (50-500+ bytes depending on configuration)
- **Purpose**: Primary tracking message with location and telemetry data
- **Structure**: Header + Main Body + Extended Fields (optional) + Minors (optional)

**Header Fields**:
- Checksum (2 bytes): Fletcher checksum
- IMEI (8 bytes): Device identifier
- Message Type (1 byte): Bit 7=Ack req, Bit 6=Bitmap present, Bits 0-5=0x01
- Bitmap (3 bytes): Field inclusion flags

**Main Body Fields** (24 fields, bitmap-controlled):
- Sequence (us_byte, 1): Message sequence number
- Event ID (us_byte, 1): Event type (0-231)
- Event Date (us_int, 4): Unix timestamp
- GPS Fix Date (us_int, 4): GPS timestamp
- Fix Delay (us_byte, 1): GPS fix delay
- Latitude (s_int, 4): Lat × 10,000,000
- Longitude (s_int, 4): Lon × 10,000,000
- Speed (us_byte, 1): GPS speed (1 kph/bit up to 160, then 5 kph/bit)
- Heading (us_byte, 1): Direction (360/256 degrees per bit)
- Main Power (us_short, 2): Voltage × 100
- Battery Power (us_byte, 1): Voltage × 10
- Sat Count (us_byte, 1): Number of satellites
- HAC (us_byte, 1): Horizontal accuracy × 10 meters
- HDOP (us_byte, 1): Horizontal dilution of precision
- Product ID (us_byte, 1): Device model (0-20)
- RSSI (s_byte, 1): Cellular signal strength
- Input Status (us_byte, 1): 8-bit input map
- Output Status (us_byte, 1): 8-bit output map
- I/O Status (us_byte, 1): 4 inputs + 4 outputs
- Device/Ignition State (us_byte, 1): Power, ignition, and device state flags
- DTC Data (variable): Diagnostic trouble codes
- Reserved (1 byte)
- Minor Map (1 byte): Minor field inclusion flags
- Extended Map (4 bytes): Extended field inclusion flags

**Extended Fields** (32 fields, up to 255 custom values):
- 5× 1-Byte fields (customizable)
- 15× 2-Byte fields (customizable)
- 7× 4-Byte fields (customizable)
- 4× Custom-length fields (customizable)

**Minor Fields** (8 fields per minor, up to ~100 minors):
- GPS Fix Date (us_int, 4)
- Offset Count (us_byte, 1): Time delta from previous location
- Lat Diff (s_short, 2): Latitude delta × 1,000,000
- Lon Diff (s_short, 2): Longitude delta × 1,000,000
- Lat (s_int, 4): Full latitude
- Lon (s_int, 4): Full longitude
- Speed (us_byte, 1)
- Sats/Fix (us_byte, 1): Bit 7=Fix status, Bit 6=Quality, Bits 0-5=Sat count

**Event IDs** (0-231):
- 0: Door Unlock
- 1: Heading Change
- 2: Ignition OFF
- 3: Heartbeat
- 4: Ignition ON
- 5: Move
- 6-21: Input 1-8 HIGH/LOW
- 22-23: Power ON/OFF
- 24-25: Starter OFF/ON (SID)
- 26: Stop
- 27: Minor
- 28-29: Virtual Ignition ON/OFF
- 30: GPS Acquired
- 31: Door Lock
- 32-36: Crash/Hard Accel/Brake/Left/Right
- 39: Cold Boot
- 42: Warm Boot
- 45: Watchdog
- 51: GPS Lost
- 101-114: Communication and system events
- 116-120: Wake/DTC/Tow/Speeding/Power Protect
- 200-203: Engineering events
- 204: OBDII Message
- 205: Pinging
- 206-208: Speed/Turn alerts
- 209: Heavy Duty DTC Report
- 210-215: Panic/Privacy/Driver ID events
- 216: BLE Report
- 217: CAN Snapshot
- 218: Peripheral Data Message
- 219-220: ADC Above/Below
- 222-231: AI Events (security/safety)

---

### Message Type 8: UDP Response
- **Direction**: Device → Server
- **Size**: Variable
- **Purpose**: Return response to UDP Command
- **Platforms**: FJ2500, TM97
- **Fields**:
  - Standard header (11 bytes)
  - Reserved (3 bytes)
  - Command Result (us_byte, 1): 0=Failure, 1=Success
  - Command Length (us_int, 4)
  - Command (string): Echo of command sent
  - Response Length (us_int, 4)
  - Response (string): Device response

---

### Message Type 45: OBDII Report
- **Direction**: Device → Server
- **Size**: Variable (~150-300 bytes)
- **Purpose**: Vehicle identification and OBD-II diagnostic data
- **Trigger**: On OBD detection completion or every 4 hours
- **Fields** (24 fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - RSSI (s_byte, 1)
  - Vehicle VIN (nul_str, variable)
  - OBD Type (us_byte, 1): Protocol (0-12)
  - Mil Status/DTC Count (us_byte, 1): Bit 7=MIL, Bits 0-6=Count
  - DTC Data (nul_str, variable): 5-byte blocks per DTC
  - Vehicle Odometer (us_int, 4): Kilometers
  - Engine Run Time (us_int, 4): Seconds (OBDII) or hours (HD)
  - Fuel Type (us_byte, 1): See fuel type table
  - PID00-PIDA0 (us_int, 4 each): Supported PID bitmaps
  - Reserved fields (7× us_int, 1× nul_str)

**OBD Protocol Types**:
- 0: No protocol
- 1: J1939 (250kbps)
- 2: J1939 (500kbps)
- 3: J1708
- 4: CAN 11-bit/500kbps
- 5: CAN 29-bit/500kbps
- 6: CAN 11-bit/250kbps
- 7: CAN 29-bit/250kbps
- 8: VPW
- 9: PWM
- 10: KWP (Fast)
- 11: KWP (Slow)
- 12: ISO 9141

---

### Message Type 46: Heavy Duty DTC Report
- **Direction**: Device → Server
- **Size**: Variable
- **Purpose**: Report DTC changes for J1939/J1708 vehicles
- **Trigger**: DTC change detection
- **Fields** (10 fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - RSSI (s_byte, 1)
  - Vehicle VIN (nul_str, variable)
  - OBD Type (us_byte, 1): Protocol (0-12)
  - Mil Status (us_byte, 1): 0=off, 1=on
  - DTC Data (nul_str, variable): Format "SPN,FMI,OC;SPN,FMI,OC;..."
  - Vehicle Odometer (us_int, 4): Kilometers
  - Total Engine Hours (us_float, 4): 0.05 hr/bit
  - Fuel Type (us_byte, 1)

---

### Message Type 47: Bluetooth Report
- **Direction**: Device → Server
- **Size**: Variable (150-600 bytes)
- **Purpose**: Report BLE beacon data
- **Trigger**: 4 beacons collected or report delay timeout
- **Fields** (9 fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - Fix Date (us_int, 4)
  - Latitude (s_int, 4)
  - Longitude (s_int, 4)
  - BLE Data 0-3 (nul_str each, variable)

**BLE Data Format**:
- **iBeacon**: `<index>:<UUID>,<MAC>,<Major>,<Minor>,<RSSI>,<Timestamp>,<Batt>,<ExtData>,<Type>`
- **OEMDD**: `<index>:<MAC>,<Payload>,<RSSI>,<Timestamp>,<Type>`
- **Unprocessed**: `<index>:<MAC>,<RawPayload>,<RSSI>,<Timestamp>,<Type>`

---

### Message Type 48: CAN Snapshot
- **Direction**: Device → Server
- **Size**: Variable (typically 200-500 bytes per packet)
- **Purpose**: Capture raw J1939 CAN bus data
- **Platform**: FJ2500 only
- **Fields** (17 fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - Fix Date (us_int, 4)
  - Latitude (s_int, 4)
  - Longitude (s_int, 4)
  - CAN Snapshot Number (us_int, 4): Snapshot index
  - CAN Snapshot Sequence (us_int, 4): Packet sequence within snapshot
  - CAN Data 0-9 (nul_str each): Format "<delta> <CAN_ID> <CAN_data>"

---

### Message Type 49: Peripheral Data Message
- **Direction**: Device → Server
- **Size**: Variable (up to 512 bytes)
- **Purpose**: Relay data from peripheral devices (CAN2/Serial/BLE)
- **Platform**: FJ2500
- **Fields** (7 fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - Fix Date (us_int, 4)
  - Latitude (s_int, 4)
  - Longitude (s_int, 4)
  - Data Type (us_byte, 1): 0=CAN2, 1=Serial, 2=BLE
  - Num of Payloads (us_byte, 1): 1-N
  - Payload N Size (us_short, 2): Max 477 bytes
  - Payload N (us_byte, variable): Raw peripheral data

**CAN2 Payload Format**:
- CAN ID (4 bytes)
- CAN Data Length (2 bytes)
- CAN Data (variable)

---

### Message Type 50: J1939 Report
- **Direction**: Device → Server
- **Size**: Variable (100-500 bytes)
- **Purpose**: Report custom J1939 PGN data
- **Platform**: FJ2500
- **Fields** (42 fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - Fix Date (us_int, 4)
  - Latitude (s_int, 4)
  - Longitude (s_int, 4)
  - Main Power Voltage (us_short, 2): Volts × 100
  - CAN Protocol (us_byte, 1): Protocol (0-12)
  - Config ID (us_int, 4): DMAN configuration ID
  - VIN (nul_str, variable)
  - SPN Count (us_byte, 1): Number of SPNs (max 32)
  - SPN 0-31 (8 bytes each): Format [PGN(2) | SPN(2) | Data(4)]

---

### Message Type 60: Modbus Report
- **Direction**: Device → Server
- **Size**: Variable (150-800 bytes)
- **Purpose**: Report Modbus register data
- **Platform**: FJ2500
- **Trigger**: On-change or periodic interval
- **Fields** (9+ fields, bitmap-controlled):
  - Standard header + bitmap
  - Sequence (us_byte, 1)
  - Event Date (us_int, 4)
  - Fix Date (us_int, 4)
  - Latitude (s_int, 4)
  - Longitude (s_int, 4)
  - Main Power Voltage (us_short, 2)
  - Modbus Status (us_byte, 1): 0=No protocol, 1=Detected
  - Modbus Config (nul_str, variable): Up to 10 chars
  - Modbus Data Count (us_byte, 1): Number of registers (max 20)
  - Modbus Data 0-19 (nul_str each): Format "<FunctionCode>.<Address>.<SlaveID>,<Data>"

---

## Extended Field Data Types

### 1-Byte Fields (20 options):
- OBD: MIL Status/DTC Count (ID 5)
- OBD: Coolant Temp (ID 6): Value - 40°C
- OBD: Vehicle Speed (ID 7): km/h
- OBD: Fuel Level (ID 8): Value × (100/255)%
- OBD: DEF Concentration (ID 9): Value × 0.25%
- OBD: DEF Tank Temp (ID 10): Value - 40°C
- OBD: DEF Volume (ID 11): Value × (100/255)%
- OBD: Fuel Type (ID 12): See fuel type table
- OBD: Engine Oil Temp (ID 13): Value - 40°C
- OBD: Calculated Engine Load (ID 14): Value × (100/255)%
- OBD: Throttle Position (ID 15): Value × (100/255)%
- OBD: Driver Seatbelt (ID 16): 0/1
- OBD: Oil Pressure (ID 17): Value × 4 kPa (HD only)
- OBD: Coolant Level (ID 18): Value × (100/255)% (HD only)
- OBD: Engine Oil Level (ID 19): Value × (100/255)% (HD only)
- OBD: Coolant Pressure (ID 20): Value × 2 kPa (HD only)

### 2-Byte Fields (26 options):
- Mobile Network Code (ID 1)
- Mobile Country Code (ID 2)
- Local Area Code (ID 3)
- Cell Tower ID (ID 4): 2 LSB of cell tower
- ADC 1 (ID 5): Voltage × 1000
- Temperature 1 (ID 10): Signed value / 100°C
- OBD: RPM (ID 18): Value / 4
- OBD: Mass Air Flow (ID 19): Value × 0.01 g/s
- OBD: Fuel Rate (ID 20): Value × 0.05 L/h
- OBD: Distance with MIL On (ID 21): km
- OBD: Time with MIL On (ID 22): minutes
- OBD: Distance Since Codes Cleared (ID 23): km
- OBD: Time Since Codes Cleared (ID 24): minutes
- OBD: HD Engine Oil Temp (ID 25): Value - 273°C (HD only)

### 4-Byte Fields (23 options):
- GPS Odometer (ID 1): meters
- GPS Trip Odometer (ID 2): meters
- Altitude (ID 3): meters
- OBD: Total Engine Run Time (ID 9): hours
- OBD: Total Idle Run Time (ID 10): hours
- OBD: Total PTO Run Time (ID 11): hours
- Cell Tower ID (ID 12): Full 4-byte value
- OBD: Odometer (ID 13): kilometers
- OBD: Calc Odometer (ID 14): meters
- OBD: Calc Trip Odometer (ID 15): meters
- OBD: HD Total Idle Fuel (ID 16): Value × 0.5 L (HD only)
- OBD: HD Total Fuel (ID 17): Value × 0.5 L (HD only)
- DMAN Settings ID (ID 18): Configuration ID
- Input 1-4 Seconds (ID 19-22): Cumulative HIGH time

### Custom-Length Fields (3 options):
- OBD: VIN (ID 2): 1-18 bytes
- OTP Data (ID 3): 20 chars (hardware config)

---

## Data Format Summary

**Numeric Formats**:
- `us_byte`: 1-byte unsigned (0-255)
- `s_byte`: 1-byte signed (-128 to 127)
- `us_short`: 2-byte unsigned (0-65,535)
- `s_short`: 2-byte signed (-32,768 to 32,767)
- `us_int`: 4-byte unsigned (0-4,294,967,295)
- `s_int`: 4-byte signed (-2,147,483,648 to 2,147,483,647)
- `us_long`: 8-byte unsigned
- `us_float`: 4-byte IEEE 754 float
- `nul_str`: Null-terminated string
- `string`: Length-prefixed string

**Checksum**: 2-byte Fletcher checksum (all device messages)

**Byte Order**: Big Endian (MSB first)