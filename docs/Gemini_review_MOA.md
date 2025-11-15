Hello! Based on the MOA Protocol specification, here is a list of all device-to-server message endpoints and the server-to-device messages used for acknowledgment and command, along with relevant details.

---

## 🛰️ MOA Protocol Endpoints Overview

The MOA Protocol primarily uses **Device to Server Messages** for reporting data. [cite_start]These reports, such as the **Event** message, are highly customizable[cite: 100]. [cite_start]**Server to Device Messages** are used for acknowledgments and commands[cite: 35, 65].

---

## ⬆️ Device to Location/Application Server Messages

[cite_start]Device-originated messages are protected by an end-to-end Fletcher checksum[cite: 18, 50].

| Message Type | ID | Description | Key Components & Details |
| :--- | :--- | :--- | :--- |
| **Event** | 1 | [cite_start]The most common message, highly customizable[cite: 96, 98, 100]. | [cite_start]Consists of a **Main Message Body** (required), and optional **Extended Fields** and **Minor Locations** [cite: 101-104]. [cite_start]Used to report events like Ignition ON/OFF, Move, Stop, and I/O changes[cite: 254]. |
| **UDP Response** | 8 | [cite_start]Used by trackers to return the response to a UDP Command back to the report server[cite: 569]. | [cite_start]Includes the **Command Result** (Success/Failure), **Command Length**, echo of the **Command** sent, **Response Length**, and the **Response** string from the device[cite: 573]. |
| **OBDII Report** | 45 | [cite_start]Gathers the **VIN**, supported **PIDs**, and other OBD information[cite: 579]. | [cite_start]Triggered when an OBD-capable device connects to a vehicle and finishes data detection, or on a 4-hour timeout[cite: 580, 582]. [cite_start]Includes fields like **Vehicle VIN**, **OBD Type**, **Mil Status / DTC Count**, and various **PID** support bitmaps[cite: 586, 590]. |
| **Heavy Duty (HD) DTC Report** | 46 | [cite_start]Sent when a change is detected in vehicle DTCs (new DTCs detected or existing ones cleared)[cite: 597, 599]. | [cite_start]More generalized than the OBDII Report to handle heavy-duty (J1939 and J1708) data[cite: 598]. [cite_start]**DTC Data** contains Suspect Parameter Number (SPN), Failure Mode Indicator (FMI), and Occurrence Count (OC) for each DTC[cite: 618]. |
| **Bluetooth Report** | 47 | [cite_start]Sends Bluetooth (BLE) data from the device to the server[cite: 626]. | [cite_start]Sent after 4 beacon IDs are filled, or after a report delay timeout[cite: 627]. [cite_start]Contains up to four variable-length **BLE Data** fields, formatted based on the type (iBeacon, OEMDD, or Unprocessed)[cite: 665, 669]. |
| **CAN Snapshot** | 48 | [cite_start]Obtains raw data from the vehicle CAN bus (currently only for FJ2500 J1939)[cite: 676, 677]. | [cite_start]A full snapshot may be broken into multiple packets, denoted by a **CAN Snapshot Number** and a **CAN Snapshot Sequence**[cite: 707]. [cite_start]Data includes a time **\<delta\>**, **\<CAN ID\>**, and **\<CAN data\>** string for each frame[cite: 698, 700, 701]. |
| **Peripheral Data Message** | 49 | [cite_start]Relays peripheral device payload(s) to the report server[cite: 718]. | [cite_start]Supports **CAN2 data**, **Serial data** (not yet implemented), and **BLE data** (not yet implemented)[cite: 721]. [cite_start]Each message can contain multiple payloads, each with its **Payload Size** and **Raw Payload**[cite: 721]. |
| **J1939 Report** | 50 | [cite_start]Allows for reporting of custom J1939 PGNs (Parameter Group Numbers) at a set interval[cite: 729, 730]. | [cite_start]Includes a **Config ID** and reports multiple **SPN** (Suspect Parameter Number) fields, each containing PGN, SPN, and SPN data in raw hex[cite: 737, 741]. |
| **Modbus Report** | 60 | [cite_start]Delivers raw Modbus data to the location server[cite: 749]. | [cite_start]Contains two types of register data: **On-Change** (reported when value changes) and **Periodic** (reported at a defined interval)[cite: 751, 753, 754]. [cite_start]Data is formatted as `<Function Code>.<Address>.<slave ID>,<Modbus data>`[cite: 774]. |

---

## ⬇️ Location Server to Device Messages

[cite_start]Messages sent from servers to devices are **NOT** protected by a checksum[cite: 20].

| Message Type | ID | Description | Key Components & Details |
| :--- | :--- | :--- | :--- |
| **Acknowledgement** | 42 | [cite_start]Sent from the server to the device to acknowledge receipt of a device-originated message[cite: 67]. | [cite_start]Contains the **Message Type** and **Sequence Number** of the message being acknowledged[cite: 68, 73]. [cite_start]It has an optional third byte for extended Driver ID and Panic/Privacy features[cite: 69, 73]. |
| **UDP Command** | 61 | [cite_start]Allows device serial commands (like `reboot` or `version`) to be sent over the air via UDP[cite: 77, 1043]. | [cite_start]Contains the message type and a null-terminated ASCII string that holds the **Command** to be sent to the device[cite: 77, 83]. |
| **Peripheral Device Pass-through** | 64 | [cite_start]Used to pass a UDP payload to a specified peripheral device attached to the tracker[cite: 88]. | [cite_start]Includes the **Peripheral Type** (e.g., CAN2, Serial, BLE) and a null-terminated string containing the raw data **Payload** for the peripheral[cite: 91]. |

---

