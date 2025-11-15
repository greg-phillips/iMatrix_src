Here’s a structured rundown of the *reported* MOA endpoints from the spec you uploaded, focusing on the core Type 1 “Event message” format: header + main body + minors + the way extended fields work.

---

## 1. Message header “endpoints”

These are always present on MOA messages and are more **protocol metadata** than telemetry, but I’m including them so your implementation is complete.

| Field (Endpoint)              | Type / Format     | Length  | Notes / Encoding                                                                                                                                                                                                                    |
| ----------------------------- | ----------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Checksum**                  | Fletcher checksum | 2 bytes | Checksum over the payload (all data except the checksum itself). Used to validate message integrity.                                                                                                                                |
| **IMEI**                      | `us_long`         | 8 bytes | 8-byte representation of the device IMEI.                                                                                                                                                                                           |
| **Message Type**              | `us_byte`         | 1 byte  | Bitmapped: bit 7 = Ack indicator; bit 6 = bitmap present; bits 0–5 = Message Type ID: `1 = Event`, `45 = OBDII Report`, `46 = HD DTC Report`, `48 = CAN Snapshot`, `49 = Peripheral Data`, `50 = Custom J1939`, `60 = Modbus`, etc. |
| **Bitmap (Main Body Bitmap)** | `us_int`          | 3 bytes | 24-bit bitmap. Each bit (0–23) controls whether the corresponding main body field is included in this report.                                                                                                                       |

---

## 2. Main Message Body endpoints (Bitmap-controlled)

These are the primary telemetry “endpoints” for a Type 1 event. Presence is controlled by the **Main Body bitmap**; Bit column below refers to that bitmap.

| Bit        | Field (Endpoint)              | Format          | Bytes                                       | Core Details / Encoding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ---------- | ----------------------------- | --------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| — (header) | **Sequence**                  | `us_byte`       | 1                                           | Sequence ID used in ACKs to uniquely identify the message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 1          | **Event ID**                  | `us_byte`       | 1                                           | Event type (Ignition On/Off, Move, Tow, Panic, Heartbeat, etc.). Full list in Event ID table (Section 3.1.3).                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2          | **Event Date**                | `us_int`        | 4                                           | Event timestamp: seconds since `1970-01-01 00:00:00 UTC`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 3          | **GPS Fix Date**              | `us_int`        | 4                                           | Last GPS fix time: seconds since `1970-01-01 00:00:00 UTC`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 4          | **Fix Delay**                 | `us_byte`       | 1                                           | Encoded delay between event time and GPS fix. Actual fix date = `Event Date – (FixDelay)^2`.                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 5          | **Lat**                       | `s_int`         | 4                                           | Latitude in decimal degrees: `lat = value / 10,000,000`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 6          | **Lon**                       | `s_int`         | 4                                           | Longitude in decimal degrees: `lon = value / 10,000,000`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 7          | **Speed**                     | `us_byte`       | 1                                           | GPS speed. For 1–160, `1 = 1 kph` … `160 = 160 kph`. For >160, each increment adds 5 kph. Example: `163 = 175 kph`, `200 = 360 kph`.                                                                                                                                                                                                                                                                                                                                                                                                               |
| 8          | **Heading**                   | `us_byte`       | 1                                           | Heading: `deg ≈ round(360/256 * value)`. Example: `0=0°`, `10≈14°`, `180≈253°`, `181≈255°`.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 9          | **Main Power (VIN)**          | `us_short`      | 2                                           | Main supply voltage (typically vehicle system). `Volts = value / 100`. Example: `1315 → 13.15 V`.                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 10         | **Battery Power**             | `us_byte`       | 1                                           | Internal backup battery voltage (if present). `Volts = value / 10`. Example: `41 → 4.1 V`.                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 11         | **Sat Count**                 | `us_byte`       | 1                                           | Number of satellites in the GPS fix.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 12         | **HAC (Horizontal Accuracy)** | `us_byte`       | 1                                           | Horizontal accuracy in meters: `HAC = value / 10`. Example: `36 → 3.6 m`. Indicates quality of Lat/Lon fix.                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 13         | **HDOP**                      | `us_byte`       | 1                                           | Horizontal Dilution of Precision value (scaled per GPS spec; used as a quality indicator).                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 14         | **Product ID**                | `us_int`        | 1                                           | Encoded device platform ID (e.g., `1=FJ1500LA`, `2=FJ1500LS`, `3=FJ1500MG`, … `19=FJ2100MW`, `20=TM94MW`, etc.). Allows server to know hardware family.                                                                                                                                                                                                                                                                                                                                                                                            |
| 15         | **RSSI**                      | `s_byte`        | 1                                           | Cellular signal strength of current data connection (signed value; implementation-specific mapping to dBm).                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 16         | **Input Status**              | `us_byte`       | 1                                           | Bitmapped digital input states (typically active-HIGH):<br>Bit 7 = Input 8, Bit 6 = Input 7, Bit 5 = Input 6, Bit 4 = Input 5, Bit 3 = Input 4, Bit 2 = Input 3, Bit 1 = Input 2, Bit 0 = Input 1.                                                                                                                                                                                                                                                                                                                                                 |
| 17         | **Output Status**             | `us_byte`       | 1                                           | Bitmapped digital output states:<br>Bit 7 = Output 8, Bit 6 = Output 7, Bit 5 = Output 6, Bit 4 = Output 5, Bit 3 = Output 4, Bit 2 = Output 3, Bit 1 = Output 2, Bit 0 = Output 1.                                                                                                                                                                                                                                                                                                                                                                |
| 18         | **I/O Status**                | `us_byte`       | 1                                           | Mixed bit-map of key IO lines:<br>Bit 7 = Output 4, Bit 6 = Output 3, Bit 5 = Output 2, Bit 4 = Output 1, Bit 3 = Input 4, Bit 2 = Input 3, Bit 1 = Input 2, Bit 0 = Input 1. Useful if you only care about first 4 inputs/outputs.                                                                                                                                                                                                                                                                                                                |
| 19         | **Device / Ignition State**   | `us_byte`       | 1                                           | Bit-mapped device/ignition/power state:<br>• Bit 0: Stopped (device in Stopped state)<br>• Bit 1: Moving (device in Moving state)<br>• Bit 2: Tow (moving without ignition)<br>• Bit 3: Updating (OTA update in progress)<br>• Bit 4: Power State (0 = on backup battery, 1 = main power connected)<br>• Bit 5: OBD Ignition (ignition detected via OBD algorithm)<br>• Bit 6: Wired Ignition (ignition wire)<br>• Bit 7: Virtual Ignition (detected by voltage).<br>*Note: Virtual ignition is reported independently of other ignition sources.* |
| 20         | **DTC Data**                  | Variable length | Variable (up to 256 bytes including length) | Byte 0 = length N of following DTC event data; bytes 1…N are event-specific payload (e.g., 5-byte DTC codes for “DTC Change Detected”, additional status, etc.).                                                                                                                                                                                                                                                                                                                                                                                   |
| 21         | **Reserved**                  | —               | —                                           | Reserved for future use; ignore / skip if present.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 22         | **Minor Map**                 | `us_byte`       | 1                                           | Bitmap indicating which **Minor fields** are appended after the main body. `0 = no minors`. Bits correspond to Minor Field Bitmap (see Section 3.1.5).                                                                                                                                                                                                                                                                                                                                                                                             |
| 23         | **Extended Map**              | `us_int`        | 4                                           | 32-bit map indicating which extended fields (1-byte / 2-byte / 4-byte / custom) are appended. Actual meanings are defined by Extended Field settings (IDs 126–156).                                                                                                                                                                                                                                                                                                                                                                                |

> **Implementation tip:** In code/DB, you can treat each row above as a telemetry endpoint keyed by (message_type=1, bitmap_bit=X), with additional per-field decoding functions for Speed, Heading, HAC, etc.

---

## 3. Minor Location endpoints (per-Minor bitmap)

**Minors** are compact “between major points” locations appended after the main body. Their presence is controlled per Minor by:

* **Minor Map** (Main body bit 22), and
* **Minor Bitmap (Setting[125])** on the device.

Each Minor can contain some or all of the following fields:

| Minor Bit | Field (Endpoint)                      | Format    | Bytes | Core Details / Encoding                                                                                                                                                                                                                                                                                 |
| --------- | ------------------------------------- | --------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0         | **GPS Fix Date**                      | `us_int`  | 4     | Last GPS fix time for this minor, in seconds since `1970-01-01 00:00:00 UTC`.                                                                                                                                                                                                                           |
| 1         | **Offset Count**                      | `us_byte` | 1     | Time delta (seconds) from the previous **major or minor** location. Lets you reconstruct full time series without repeating absolute timestamps.                                                                                                                                                        |
| 2         | **Latitude Differential (Lat Diff)**  | `s_int`   | 2     | Signed delta from previous major/minor latitude. `LatDiff = value / 1,000,000` degrees.                                                                                                                                                                                                                 |
| 3         | **Longitude Differential (Lon Diff)** | `s_int`   | 2     | Signed delta from previous major/minor longitude. `LonDiff = value / 1,000,000` degrees.                                                                                                                                                                                                                |
| 4         | **Lat (full)**                        | `s_int`   | 4     | Full latitude: `lat = value / 10,000,000` degrees. Used when you want an absolute position rather than a delta.                                                                                                                                                                                         |
| 5         | **Lon (full)**                        | `s_int`   | 4     | Full longitude: `lon = value / 10,000,000` degrees.                                                                                                                                                                                                                                                     |
| 6         | **Speed**                             | `us_byte` | 1     | Same encoding as main body Speed: 1–160 = kph; >160 adds 5 kph per step (e.g., 163 → 175 kph, 200 → 360 kph).                                                                                                                                                                                           |
| 7         | **Sats / Fix**                        | `us_byte` | 1     | Packed satellites and fix quality:<br>• Bit 7: Fix Status (`0 = GPS Acquired`, `1 = GPS Not Acquired`)<br>• Bit 6: Quality (`0 = not a “quality” fix`, `1 = quality fix`, per config)<br>• Bits 5–0: satellite count (0–63). Example: value 73 (`0100 1001`) → GPS acquired, quality fix, 9 satellites. |

> **Note:** The spec emphasizes Minors are optimized for low overhead; use Lat/Lon Diff when possible for compact storage, falling back to full Lat/Lon when needed.

---

## 4. Extended Field endpoints (high-level)

Extended fields are **additional optional endpoints** tied to the **Extended Map** (bit 23) and configured via Settings[126–156]. There are four types:

* **1-byte extended fields** (IDs for things like MIL status / DTC count, OBD coolant temp, vehicle speed, fuel level, DEF concentration, various OBD counters, etc.)
* **2-byte extended fields** (e.g., MCC/MNC/LAC/Cell ID in 16-bit form, some OBD scalar values)
* **4-byte extended fields** (e.g., GPS odometer, trip odometer, cumulative counters like engine hours or Input1–4 seconds)
* **Custom-length fields** (e.g., OBD VIN)

The spec’s tables (Section 4.x) give a long list; a few notable examples so you can model them as endpoints:

### 4.1 One-byte Extended Field examples

Each row is: **Name / ID / Description / Light-duty support / Heavy-duty support**. All are 1 byte in the payload, with field-specific scaling.

Some key ones:

* **Disabled (ID 0)** – field not used; value is `0x00`.
* **OBD: MIL Status / DTC Count** – bit-packed MIL active + number of emission-related DTCs.
* **OBD: Coolant Temp** – `temp(°C) = value – 40`.
* **OBD: Vehicle Speed** – `speed(kph) = value`.
* **OBD: Fuel Level %** – `% = value * (100/255)`.
* **OBD: Diesel Exhaust Fluid Concentration** – `% = value * 0.25`.
* **OBD: Total Engine Hours** – engine run time from OBD, granularity 0.05 hr/bit.
* **OBD: Total Idle Run Time / Total Run Time with PTO Active** – hours counters.
* **Cell Tower ID (1-byte variant)** – compressed or partial representation of the serving cell.
* **OBD: Odometer / Calculated Odometer / Calculated Trip Odometer** – distance counters (often meters or km depending on ID).
* **HD-only fuel counters** – e.g., total idle fuel, total fuel at 0.5 L/bit.

Each of these is an **endpoint** you can map as `<extended_1b_id=N>` with its own decoding rule.

### 4.2 Two-byte Extended Field examples

Payload is 2 bytes; examples include:

* **Mobile Network Code (MNC)** – identifies mobile operator.
* **Mobile Country Code (MCC)** – subscriber country.
* **Local Area Code (LAC)**.
* **Cell Tower ID (full 2-byte variant)**.
* A set of OBD scalar values: Mass Air Flow, Fuel Rate, Distance/time with MIL on, distance since codes cleared, HD oil temperature, etc., each with explicit scaling (e.g., `Fuel Rate = value * 0.05 L/h`).

### 4.3 Four-byte Extended Field examples

Payload is 4 bytes:

* **GPS Odometer** – total distance moved (meters) since device install, using GPS while in motion states; stopped states are excluded.
* **GPS Trip Odometer** – per-trip distance (meters) from trip start to trip end.
* Additional counters such as total HD fuel, total idle fuel, DMAN settings ID, and:

  * **Input 1/2/3/4 Seconds** – cumulative time in seconds each input has been HIGH.

### 4.4 Custom-length Extended Field example

* **OBD: VIN (ID 2)** – vehicle Identification Number read via OBD, variable length field.

> From an integration standpoint, it’s usually easiest to treat **each Extended Field ID** as its own endpoint, with metadata: `id`, size (1/2/4/custom), light/heavy support flags, and a decode function.

---

## 5. How to think about this for your system

If you’re building a DB/API around this:

* **Core MOA telemetry endpoints** = all fields in Sections 2 and 3 above (Main Body + Minors) + each **Extended Field ID** you choose to enable.
* The **protocol metadata endpoints** (Checksum, IMEI, Message Type, Bitmap, Sequence) are needed for message handling but not necessarily exposed as “business metrics”.
* Event ID, DTC Data, and the Extended Fields together are how you expose **OBD / J1939 / HD** data without needing to parse separate message types in most cases.

If you’d like, next step I can do is:

* Generate a **machine-readable schema** (e.g., JSON or SQL CREATE TABLE) for:

  * Main MOA Event
  * Minor positions
  * A generic ExtendedField table keyed by (device, event_seq, extended_id).

---

**Side note about files:** some of your previously uploaded files (in older chats) may have expired on the server. If you want me to cross-reference this MOA spec with any of those older documents (e.g., DBCs, DB schemas, etc.), please re-upload them and I’ll fold them into the same endpoint list.
