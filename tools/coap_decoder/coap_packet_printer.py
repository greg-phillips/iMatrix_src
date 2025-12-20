#!/usr/bin/env python3
"""
CoAP Packet Printer - Human-readable iMatrix CoAP packet decoder

This script decodes CoAP hex dumps from iMatrix devices and prints them
in a human-readable format, similar to the C implementation in
iMatrix/coap/coap_packet_printer.c

Usage:
    python3 coap_packet_printer.py <filename> [-v|--verbose]

Author: Claude Code
Date: 2025-12-12
"""

import sys
import struct
import re
import argparse
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, List

# ANSI Color codes for terminal output
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    @classmethod
    def disable(cls):
        """Disable colors (for non-TTY output)"""
        cls.RED = ''
        cls.YELLOW = ''
        cls.GREEN = ''
        cls.CYAN = ''
        cls.MAGENTA = ''
        cls.BOLD = ''
        cls.RESET = ''


# Timestamp validation constants
# Valid range: Jan 1, 2000 to Jan 1, 2100
MIN_VALID_TIMESTAMP = 946684800   # 2000-01-01 00:00:00 UTC
MAX_VALID_TIMESTAMP = 4102444800  # 2100-01-01 00:00:00 UTC
MIN_VALID_TIMESTAMP_MS = MIN_VALID_TIMESTAMP * 1000
MAX_VALID_TIMESTAMP_MS = MAX_VALID_TIMESTAMP * 1000


def is_valid_timestamp(utc_time: int) -> bool:
    """Check if a timestamp (seconds) is within valid range (2000-2100)."""
    return MIN_VALID_TIMESTAMP <= utc_time <= MAX_VALID_TIMESTAMP


def is_valid_timestamp_ms(utc_time_ms: int) -> bool:
    """Check if a timestamp (milliseconds) is within valid range (2000-2100)."""
    return MIN_VALID_TIMESTAMP_MS <= utc_time_ms <= MAX_VALID_TIMESTAMP_MS


# CoAP Constants
PAYLOAD_MARKER = 0xFF
URI_PATH_OPTION = 11
CONTENT_FORMAT_OPTION = 12

# CoAP type names
COAP_TYPE_NAMES = ["CON", "NON", "ACK", "RST"]

# Block type names (from common.h imx_block_t enum)
BLOCK_TYPE_NAMES = {
    0: "CONTROL",
    1: "SENSOR",
    2: "MFG_UPDATE",
    3: "BLE_CLIENTS",
    4: "WIFI_RF_SCAN",
    5: "TRACEROUTE",
    6: "GPS_COORDINATES",
    7: "INDOOR_COORDINATES",
    8: "IPV4_DETAILS",
    9: "IPV6_DETAILS",
    10: "EVENT_CONTROL",
    11: "EVENT_SENSOR",
    12: "SENSOR_MS",
    13: "EVENT_SENSOR_MS",
    14: "FLAG_CONTROL_SENSOR",
    15: "CONTROL_MS",
    16: "FW_VERSION",
    17: "SSID",
    18: "BSSID",
    19: "CHANNEL",
    20: "SECURITY",
    21: "VARLENGTH",
    22: "CONFIG_SENSOR",
    23: "CONFIG_THING",
    24: "THING_STATUS",
    25: "HASH_HEADER",
    26: "CALIBRATION",
    27: "EVENT_VARIABLE",
    28: "VARIABLE_MS",
}

# Data type names
DATA_TYPE_NAMES = {
    0: "UINT32",
    1: "INT32",
    2: "FLOAT",
    3: "VARIABLE_LENGTH",
}

# Warning level names
WARNING_LEVEL_NAMES = {
    0: "NONE",
    1: "INFORMATIONAL",
    2: "ADVISORY",
    3: "WARNING",
    4: "ALARM",
    5: "HIGH_ADVISORY",
    6: "HIGH_WARNING",
    7: "HIGH_ALARM",
    8: "RECORD",
}

# Internal sensor names (from internal_sensors_def.h)
INTERNAL_SENSOR_NAMES = {
    2: "GPS_Latitude",
    3: "GPS_Longitude",
    4: "GPS_Altitude",
    5: "Indoor_Building_ID",
    6: "Indoor_Level_ID",
    7: "Indoor_X",
    8: "Indoor_Y",
    9: "Indoor_Z",
    10: "Private_IPv4_Address",
    11: "Gateway_IPv4_Address",
    12: "Public_IPv4_Address",
    13: "Private_IPv6_Address",
    14: "Gateway_IPv6_Address",
    15: "Public_IPv6_Address",
    16: "Network_Traceroute",
    17: "BLE_Active_Clients",
    18: "WiFi_RF_Scan",
    19: "WiFi_RF_Channel",
    20: "WiFi_RF_RSSI",
    21: "WiFi_RF_Noise",
    22: "WiFi_RF_SSID",
    23: "WiFi_RF_BSSID",
    24: "WiFi_RF_Security",
    25: "Battery_Level",
    26: "Software_Version",
    27: "BLE_RF_RSSI",
    28: "Boot_Count",
    29: "4G_RF_RSSI",
    30: "Thing_Report",
    31: "4G_RF_RSRP",
    32: "4G_RF_RSRQ",
    33: "4G_RF_SINR",
    34: "4G_Carrier",
    35: "4G_Band",
    36: "IMEI",
    37: "SIM_Card_State",
    38: "SIM_Card_IMSI",
    39: "SIM_Card_ICCID",
    40: "4G_Network_Type",
    41: "Geofence_Enter",
    42: "Host_Controller",
    43: "4G_BER",
    44: "HDOP",
    45: "Number_of_Satellites",
    46: "GPS_Fix_Quality",
    47: "GPS_Speed",
    48: "Direction",
    49: "Idle_State",
    50: "Vehicle_Stopped",
    51: "Hard_Brake",
    52: "Hard_Acceleration",
    53: "Hard_Turn",
    54: "Hard_Bump",
    55: "Hard_Pothole",
    56: "Speeding",
    57: "Refueling",
    58: "Fuel_Level",
    59: "Fuel_Consumption",
    60: "Fuel_Consumption_Average",
    61: "Fuel_Economy",
    62: "Fuel_Economy_Average",
    63: "Daily_Hours_of_Operation",
    64: "Odometer",
    65: "ETH0_TX_Data_Rate",
    66: "ETH0_RX_Data_Rate",
    67: "WiFi_TX_Data_Rate",
    68: "WiFi_RX_Data_Rate",
    69: "PPP0_TX_Data_Rate",
    70: "PPP0_RX_Data_Rate",
    71: "G_Force_X",
    72: "G_Force_Y",
    73: "G_Force_Z",
    74: "G_Force_Max",
    75: "Accelerometer_X",
    76: "Accelerometer_Y",
    77: "Accelerometer_Z",
    78: "Gyroscope_X",
    79: "Gyroscope_Y",
    80: "Gyroscope_Z",
    81: "Magnetometer_X",
    82: "Magnetometer_Y",
    83: "Magnetometer_Z",
    84: "Number_CAN_Bus_Entries",
    85: "Number_Active_CAN_Bus_Entries",
    86: "Unknown_CAN_Bus_Entry",
    87: "CAN0_TX_Data_Rate",
    88: "CAN0_RX_Data_Rate",
    89: "CAN1_TX_Data_Rate",
    90: "CAN1_RX_Data_Rate",
    91: "CANE_TX_Data_Rate",
    92: "CANE_RX_Data_Rate",
    93: "Ignition_Status",
    94: "Number_BLE_Devices",
    95: "Number_Active_BLE_Devices",
    96: "Input_1",
    97: "Input_2",
    98: "Input_3",
    99: "Input_4",
    100: "Input_5",
    101: "Input_6",
    102: "Input_7",
    103: "Output_1",
    104: "Output_2",
    105: "Output_3",
    106: "Output_4",
    107: "Output_5",
    108: "Output_6",
    109: "Output_7",
    110: "GPIO_Config",
    111: "GW_Battery_Gas_Gauge",
    112: "GW_Battery_Temperature",
    113: "Analog_Input_1",
    114: "Analog_Input_2",
    115: "Geofence_Buffer_In",
    116: "Hard_Impact",
    117: "Geofence_Exit",
    118: "Geofence_Enter_Buffer",
    119: "Geofence_Exit_Buffer",
    120: "Geofence_In",
    121: "Geo_Point",
    122: "CAN_0_Speed",
    123: "Battery_Voltage",
    124: "Battery_Current",
    125: "Battery_Temperature",
    126: "Battery_State_of_Charge",
    127: "Battery_Capacity",
    128: "Battery_Status",
    129: "Battery_Health",
    130: "Battery_Cycle_Count",
    131: "Battery_Time_to_Full",
    132: "Battery_Time_to_Empty",
    133: "Battery_Power",
    134: "Battery_Voltage_Min",
    135: "Battery_Voltage_Max",
    136: "Battery_Current_Min",
    137: "Battery_Current_Max",
    138: "Battery_Temperature_Min",
    139: "Battery_Temperature_Max",
    140: "Battery_Charge_Min",
    141: "Battery_Charge_Max",
    142: "Vehicle_Speed",
    143: "Power_Use",
    144: "Comm_Link_Type",
    145: "CANbus_Status",
    146: "CAN_1_Speed",
    147: "Engine_RPM",
    148: "Engine_Oil_Temperature",
    149: "Throttle_Position",
    150: "Engine_Coolant_Temperature",
    500: "Cumulative_Throughput",
    501: "Charge_Rate",
    502: "Estimated_Range",
    503: "Battery_State_of_Health",
    504: "Trip_Distance",
    505: "Charging_Status",
    506: "Trip_Meter",
    507: "Out_of_Range_Sensor_Data_ID",
    508: "Out_of_Range_Sensor_Data_Value",
    509: "MPGe",
    510: "Trip_UTC_Start_Time",
    511: "Trip_UTC_End_Time",
    512: "Trip_idle_time",
    513: "Trip_Wh_km",
    514: "Trip_MPGe",
    515: "Trip_l_100km",
    516: "Trip_CO2_Emissions",
    517: "Trip_Power",
    518: "Trip_Energy_Recovered",
    519: "Trip_Charge",
    520: "Trip_Average_Charge_Rate",
    521: "Trip_Peak_Charge_Rate",
    522: "Trip_Average_Speed",
    523: "Trip_Maximum_Speed",
    524: "Trip_number_hard_accelerations",
    525: "Trip_number_hard_braking",
    526: "Trip_number_hard_turns",
    527: "Maximum_deceleration",
    528: "Trip_fault_Codes",
    529: "Peak_power",
    530: "Range_gained_per_minute",
    531: "Peak_Regerative_Power",
    532: "Peak_Brake_Pedal",
    533: "Peak_Accel_Pedal",
    534: "DTC_OBD2_Codes",
    535: "DTC_J1939_Codes",
    536: "DTC_HM_Truck_Codes",
    537: "DTC_Echassie_Codes",
    538: "Driver_Score",
}


def parse_hex_dump(hex_string: str) -> bytes:
    """
    Parse hex dump in [XX][XX] format to bytes.
    Automatically strips timestamp prefixes.
    """
    # Strip timestamp prefix like "[00:05:02.582] UPLOAD Message DATA as hex:"
    # Look for the pattern and remove everything before the first [XX] hex byte
    match = re.search(r'\[([0-9a-fA-F]{2})\]', hex_string)
    if match:
        hex_string = hex_string[match.start():]

    # Extract all hex bytes in [XX] format
    hex_bytes = re.findall(r'\[([0-9a-fA-F]{2})\]', hex_string)
    return bytes(int(b, 16) for b in hex_bytes)


def format_timestamp(utc_time: int, show_raw: bool = True) -> str:
    """Format UTC timestamp to readable string with invalid detection."""
    if utc_time == 0:
        return "No timestamp"
    try:
        dt = datetime.fromtimestamp(utc_time, tz=timezone.utc)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        if not is_valid_timestamp(utc_time):
            # Invalid timestamp - show in red with raw value
            raw_info = f" [raw: {utc_time} = 0x{utc_time:08X}]"
            return f"{Colors.RED}{Colors.BOLD}INVALID: {formatted}{raw_info}{Colors.RESET}"
        return formatted
    except (ValueError, OSError):
        return f"{Colors.RED}Invalid time (raw: {utc_time} = 0x{utc_time:08X}){Colors.RESET}"


def format_timestamp_ms(utc_time_ms: int, show_raw: bool = True) -> str:
    """Format millisecond UTC timestamp to readable string with invalid detection."""
    if utc_time_ms == 0:
        return "No timestamp"
    try:
        seconds = utc_time_ms // 1000
        milliseconds = utc_time_ms % 1000
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S") + f".{milliseconds:03d} UTC"

        if not is_valid_timestamp_ms(utc_time_ms):
            # Invalid timestamp - show in red with raw value
            raw_info = f" [raw: {utc_time_ms} = 0x{utc_time_ms:016X}]"
            return f"{Colors.RED}{Colors.BOLD}INVALID: {formatted}{raw_info}{Colors.RESET}"
        return formatted
    except (ValueError, OSError):
        return f"{Colors.RED}Invalid time (raw: {utc_time_ms} = 0x{utc_time_ms:016X}){Colors.RESET}"


def format_data_value(raw_value: int, data_type: int) -> str:
    """Format data value based on type."""
    if data_type == 0:  # UINT32
        return str(raw_value)
    elif data_type == 1:  # INT32
        # Convert to signed
        if raw_value >= 0x80000000:
            raw_value -= 0x100000000
        return str(raw_value)
    elif data_type == 2:  # FLOAT
        # Interpret bytes as IEEE 754 float
        float_val = struct.unpack('>f', struct.pack('>I', raw_value))[0]
        return f"{float_val:.6f}"
    elif data_type == 3:  # VARIABLE_LENGTH
        return "VARLEN"
    else:
        return f"0x{raw_value:08X}"


def get_sensor_name(sensor_id: int) -> str:
    """Look up sensor name by ID."""
    if sensor_id in INTERNAL_SENSOR_NAMES:
        return INTERNAL_SENSOR_NAMES[sensor_id]
    return f"Sensor_{sensor_id}"


def get_block_type_name(block_type: int) -> str:
    """Get string name for block type."""
    return BLOCK_TYPE_NAMES.get(block_type, f"UNKNOWN({block_type})")


def get_data_type_name(data_type: int) -> str:
    """Get string name for data type."""
    return DATA_TYPE_NAMES.get(data_type, f"UNKNOWN({data_type})")


def get_warning_level_name(warning: int) -> str:
    """Get string name for warning level."""
    return WARNING_LEVEL_NAMES.get(warning, f"UNKNOWN({warning})")


class CoAPPacketPrinter:
    """Decodes and prints iMatrix CoAP packets."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.max_samples_display = 0 if verbose else 10
        # Track invalid timestamps for summary
        self.invalid_timestamps = []
        self.valid_timestamps = 0

    def _track_timestamp(self, timestamp: int, sensor_name: str, block_num: int, is_ms: bool = False) -> None:
        """Track a timestamp for validity statistics."""
        if is_ms:
            if is_valid_timestamp_ms(timestamp):
                self.valid_timestamps += 1
            else:
                self.invalid_timestamps.append((timestamp, sensor_name, block_num, True))
        else:
            if is_valid_timestamp(timestamp):
                self.valid_timestamps += 1
            else:
                self.invalid_timestamps.append((timestamp, sensor_name, block_num, False))

    def print_packet(self, data: bytes) -> None:
        """Print CoAP packet in human-readable format."""
        if len(data) < 4:
            print("=== Invalid or too short packet ===")
            return

        # Reset tracking
        self.invalid_timestamps = []
        self.valid_timestamps = 0

        print("\n" + "=" * 60)
        print("CoAP Message (Human Readable)")
        print("=" * 60)

        # Parse CoAP header
        offset = self._print_coap_header(data)

        # Parse options and find payload
        payload_offset = self._parse_options(data, offset)

        # Print data blocks
        if payload_offset > 0 and payload_offset < len(data):
            print("\n" + "-" * 40)
            print("DATA BLOCKS")
            print("-" * 40)
            self._print_data_blocks(data, payload_offset)
        else:
            print("\nNo payload data found")

        # Print timestamp validity summary
        self._print_timestamp_summary()

        print("\n" + "=" * 60)
        print(f"Total Message Size: {len(data)} bytes")
        print("=" * 60 + "\n")

    def _print_timestamp_summary(self) -> None:
        """Print summary of timestamp validity."""
        total = self.valid_timestamps + len(self.invalid_timestamps)
        if total == 0:
            return

        print("\n" + "-" * 40)
        print("TIMESTAMP VALIDATION")
        print("-" * 40)

        if self.invalid_timestamps:
            print(f"{Colors.RED}{Colors.BOLD}WARNING: {len(self.invalid_timestamps)} invalid timestamps detected!{Colors.RESET}")
            print(f"  Valid timestamps: {self.valid_timestamps}")
            print(f"  Invalid timestamps: {len(self.invalid_timestamps)}")
            print(f"\n{Colors.YELLOW}Invalid timestamp details:{Colors.RESET}")

            # Group by block
            blocks_with_invalid = {}
            for ts, sensor, block, is_ms in self.invalid_timestamps:
                if block not in blocks_with_invalid:
                    blocks_with_invalid[block] = []
                blocks_with_invalid[block].append((ts, sensor, is_ms))

            for block, timestamps in sorted(blocks_with_invalid.items()):
                sensor = timestamps[0][1]  # Get sensor name from first entry
                print(f"  Block {block} ({sensor}): {len(timestamps)} invalid timestamp(s)")
                # Show first invalid timestamp as example
                ts, _, is_ms = timestamps[0]
                if is_ms:
                    print(f"    Example: {ts} (0x{ts:016X}) - not a valid UTC millisecond timestamp")
                else:
                    print(f"    Example: {ts} (0x{ts:08X}) - not a valid UTC second timestamp")

            print(f"\n{Colors.CYAN}Possible causes:{Colors.RESET}")
            print("  - Timestamps might be relative (uptime) instead of absolute UTC")
            print("  - Device RTC was not synchronized")
            print("  - Wrong timestamp format (seconds vs milliseconds)")
            print("  - Data corruption")
        else:
            print(f"{Colors.GREEN}All {total} timestamps are valid (within 2000-2100 range){Colors.RESET}")

    def _print_coap_header(self, data: bytes) -> int:
        """Print CoAP header information. Returns offset after header."""
        print("\nCoAP HEADER:")

        # First byte: Ver (2 bits) | Type (2 bits) | Token Length (4 bits)
        first_byte = data[0]
        version = (first_byte >> 6) & 0x03
        msg_type = (first_byte >> 4) & 0x03
        token_length = first_byte & 0x0F

        # Second byte: Code (class.detail)
        code = data[1]
        msg_class = (code >> 5) & 0x07
        msg_detail = code & 0x1F

        # Message ID (2 bytes, big endian)
        msg_id = struct.unpack('>H', data[2:4])[0]

        # Decode common codes
        code_name = ""
        if msg_class == 0:
            if msg_detail == 1:
                code_name = " (GET)"
            elif msg_detail == 2:
                code_name = " (POST)"
            elif msg_detail == 3:
                code_name = " (PUT)"
            elif msg_detail == 4:
                code_name = " (DELETE)"

        type_name = COAP_TYPE_NAMES[msg_type] if msg_type < len(COAP_TYPE_NAMES) else f"UNKNOWN({msg_type})"
        print(f"  Version: {version}")
        print(f"  Type: {type_name}")
        print(f"  Code: {msg_class}.{msg_detail:02d}{code_name}")
        print(f"  Message ID: {msg_id} (0x{msg_id:04X})")

        # Print token if present
        if token_length > 0 and len(data) >= 4 + token_length:
            token_bytes = data[4:4 + token_length]
            token_hex = ''.join(f'{b:02x}' for b in token_bytes)
            print(f"  Token ({token_length} bytes): 0x{token_hex}")

        return 4 + token_length

    def _parse_options(self, data: bytes, offset: int) -> int:
        """Parse CoAP options. Returns offset to payload start."""
        uri_path_parts = []
        content_format = None
        current_option = 0
        start_offset = offset

        # First, find the payload marker to establish bounds
        payload_marker_pos = -1
        for i in range(offset, len(data)):
            if data[i] == PAYLOAD_MARKER:
                payload_marker_pos = i
                break

        if payload_marker_pos == -1:
            # No payload marker found - try to extract URI from raw data
            uri_parts = self._try_extract_uri_from_raw(data, offset, len(data))
            if uri_parts:
                print(f"\nURI Path (extracted): /{'/'.join(uri_parts)}")
            return len(data)  # No payload

        # Parse options between header and payload marker
        try:
            while offset < payload_marker_pos:
                option_byte = data[offset]
                option_delta = (option_byte >> 4) & 0x0F
                option_length = option_byte & 0x0F
                offset += 1

                # Handle extended option delta
                if option_delta == 13:
                    if offset >= payload_marker_pos:
                        break
                    option_delta = data[offset] + 13
                    offset += 1
                elif option_delta == 14:
                    if offset + 1 >= payload_marker_pos:
                        break
                    option_delta = struct.unpack('>H', data[offset:offset+2])[0] + 269
                    offset += 2
                elif option_delta == 15:
                    break  # Reserved/error

                # Handle extended option length
                if option_length == 13:
                    if offset >= payload_marker_pos:
                        break
                    option_length = data[offset] + 13
                    offset += 1
                elif option_length == 14:
                    if offset + 1 >= payload_marker_pos:
                        break
                    option_length = struct.unpack('>H', data[offset:offset+2])[0] + 269
                    offset += 2
                elif option_length == 15:
                    break  # Reserved/error

                # Validate we have enough data
                if offset + option_length > payload_marker_pos:
                    break

                current_option += option_delta

                # Extract option value
                if current_option == URI_PATH_OPTION and option_length > 0:
                    try:
                        uri_path_parts.append(data[offset:offset + option_length].decode('utf-8', errors='replace'))
                    except:
                        pass
                elif current_option == CONTENT_FORMAT_OPTION and option_length > 0:
                    if option_length == 1:
                        content_format = data[offset]
                    elif option_length == 2:
                        content_format = struct.unpack('>H', data[offset:offset+2])[0]

                offset += option_length

        except (IndexError, struct.error):
            pass  # Fall through to raw extraction

        # If standard parsing didn't find URI, try raw extraction
        if not uri_path_parts:
            uri_path_parts = self._try_extract_uri_from_raw(data, start_offset, payload_marker_pos)

        # Print OPTIONS section
        print("\nOPTIONS:")

        # Print URI path
        if uri_path_parts:
            print(f"  URI-Path: /{'/'.join(uri_path_parts)}")
        else:
            print("  URI-Path: (not found)")

        # Print content format
        if content_format is not None:
            fmt_name = ""
            if content_format == 42:
                fmt_name = " (application/octet-stream)"
            elif content_format == 0:
                fmt_name = " (text/plain)"
            elif content_format == 50:
                fmt_name = " (application/json)"
            print(f"  Content-Format: {content_format}{fmt_name}")

        # Return position after payload marker
        return payload_marker_pos + 1

    def _try_extract_uri_from_raw(self, data: bytes, start: int, end: int) -> List[str]:
        """Try to extract URI path from raw bytes by looking for printable ASCII."""
        try:
            raw_bytes = data[start:end]
            # Look for "selfreport" or similar URI patterns
            raw_str = raw_bytes.decode('latin-1')  # Use latin-1 to avoid decode errors

            # Find URI-like patterns
            match = re.search(r'(selfreport/\d+/\d+/\d+)', raw_str)
            if match:
                return match.group(1).split('/')

            # Try other patterns
            match = re.search(r'([a-z]+/\d+/\d+/\d+)', raw_str)
            if match:
                return match.group(1).split('/')

            match = re.search(r'([a-z]+/\d+/\d+)', raw_str)
            if match:
                return match.group(1).split('/')
        except:
            pass
        return []

    def _print_data_blocks(self, data: bytes, offset: int) -> None:
        """Print all data blocks in the payload."""
        block_num = 1
        payload_start = offset

        print(f"\nPayload starts at byte {offset} ({len(data) - offset} bytes)")

        while offset < len(data):
            consumed = self._process_single_block(data, offset, block_num)
            if consumed == 0:
                # Show remaining bytes if any
                remaining = len(data) - offset
                if remaining > 0:
                    print(f"\n[!] {remaining} unparsed bytes remaining at offset {offset}")
                break
            offset += consumed
            block_num += 1

    def _process_single_block(self, data: bytes, offset: int, block_num: int) -> int:
        """Process and print a single data block. Returns bytes consumed."""
        remaining = len(data) - offset
        header_size = 12  # 4 (sn) + 4 (id) + 4 (bits)

        if remaining < header_size:
            if remaining > 0:
                print(f"\n[{block_num}] Incomplete block header ({remaining} bytes remaining)")
            return 0

        # Parse header - iMatrix uses big-endian (network byte order)
        serial_number = struct.unpack('>I', data[offset:offset+4])[0]
        sensor_id = struct.unpack('>I', data[offset+4:offset+8])[0]

        # Get the raw bits bytes - sent in network order (big-endian) but originally
        # packed on little-endian ARM, so we need to byte-swap to get original layout
        bits_bytes = data[offset+8:offset+12]
        # Swap bytes: network[0,1,2,3] -> ARM[3,2,1,0]
        arm_bytes = bytes([bits_bytes[3], bits_bytes[2], bits_bytes[1], bits_bytes[0]])

        # Now decode from the ARM byte layout:
        # Byte 0 (arm_bytes[0]): bits 0-7
        #   block_type: bits 0-5
        #   data_type: bits 6-7
        # Byte 1 (arm_bytes[1]): bits 8-15
        #   payload_length bits 0-7
        # Byte 2 (arm_bytes[2]): bits 16-23
        #   payload_length bits 8-9 (bits 0-1 of this byte)
        #   no_samples bits 0-5 (bits 2-7 of this byte)
        # Byte 3 (arm_bytes[3]): bits 24-31
        #   no_samples bits 6-7 (bits 0-1 of this byte)
        #   unused bits 0-5 (bits 2-7 of this byte)

        block_type = arm_bytes[0] & 0x3F
        data_type = (arm_bytes[0] >> 6) & 0x03
        payload_length = arm_bytes[1] | ((arm_bytes[2] & 0x03) << 8)
        no_samples = ((arm_bytes[2] >> 2) & 0x3F) | ((arm_bytes[3] & 0x03) << 6)

        # For notification blocks, bits 18-28 have different meaning
        warning_level = 0
        sensor_error = 0
        if block_type == 14:  # FLAG_CONTROL_SENSOR (notification)
            # warning: bits 18-20 (3 bits), sensor_error: bits 21-28 (8 bits)
            warning_level = (arm_bytes[2] >> 2) & 0x07
            sensor_error = ((arm_bytes[2] >> 5) & 0x07) | ((arm_bytes[3] & 0x1F) << 3)
            no_samples = 1

        # Validate payload
        total_size = header_size + payload_length
        if remaining < total_size:
            print(f"\n[{block_num}] Incomplete block (need {total_size}, have {remaining})")
            return 0

        # Get sensor name
        sensor_name = get_sensor_name(sensor_id)

        # Print block header
        print(f"\n[Block {block_num}] {get_block_type_name(block_type)}")
        print(f"  Serial Number: {serial_number}")
        print(f"  Sensor ID: {sensor_id} ({sensor_name})")
        print(f"  Data Type: {get_data_type_name(data_type)}")
        print(f"  Payload: {payload_length} bytes, {no_samples} sample(s)")

        # Process based on block type
        payload_start = offset + header_size

        if block_type in (0, 1):  # CONTROL or SENSOR (TSD with sample rate)
            self._print_tsd_block(data, payload_start, data_type, no_samples, payload_length, sensor_name, block_num)

        elif block_type in (12, 15):  # SENSOR_MS or CONTROL_MS
            self._print_tsd_ms_block(data, payload_start, data_type, no_samples, payload_length, sensor_name, block_num)

        elif block_type in (10, 11):  # EVENT_CONTROL or EVENT_SENSOR
            self._print_event_block(data, payload_start, data_type, no_samples, sensor_name, block_num)

        elif block_type == 14:  # FLAG_CONTROL_SENSOR (notification)
            self._print_notification_block(data, payload_start, data_type, warning_level, sensor_error, sensor_name, block_num)

        elif block_type == 16:  # FW_VERSION
            fw_version = data[payload_start:payload_start + payload_length].decode('utf-8', errors='replace').rstrip('\x00')
            print(f"  Firmware Version: {fw_version}")

        elif block_type == 3:  # BLE_CLIENTS
            self._print_ble_clients_block(data, payload_start, no_samples)

        return total_size

    def _print_tsd_block(self, data: bytes, offset: int, data_type: int, no_samples: int,
                         payload_length: int, sensor_name: str, block_num: int) -> None:
        """Print TSD (Time Series Data) block with sample rate."""
        if payload_length < 6:
            print("  [Invalid TSD block - too short]")
            return

        # last_utc_sample_time (4 bytes) + sample_rate (2 bytes) + data[]
        last_time = struct.unpack('>I', data[offset:offset+4])[0]
        sample_rate = struct.unpack('>H', data[offset+4:offset+6])[0]

        # Track the last timestamp
        self._track_timestamp(last_time, sensor_name, block_num, is_ms=False)

        print(f"  Sample Rate: {sample_rate} seconds")
        print(f"  Last Sample Time: {format_timestamp(last_time)}")

        # Print values
        data_offset = offset + 6
        available_data = payload_length - 6
        expected_samples = available_data // 4

        if no_samples > expected_samples:
            no_samples = expected_samples

        max_display = no_samples if self.max_samples_display == 0 else min(no_samples, self.max_samples_display)

        if max_display > 0:
            print(f"  Values ({no_samples} total):")
            for i in range(max_display):
                if data_offset + (i+1)*4 <= offset + payload_length + 6:
                    raw_value = struct.unpack('>I', data[data_offset + i*4:data_offset + (i+1)*4])[0]
                    # Calculate timestamp for this sample (going backwards from last_time)
                    sample_time = last_time - (no_samples - 1 - i) * sample_rate
                    print(f"    [{i+1}] {format_timestamp(sample_time)}: {format_data_value(raw_value, data_type)}")

            if self.max_samples_display > 0 and no_samples > self.max_samples_display:
                print(f"    ... ({no_samples - self.max_samples_display} more samples)")

    def _print_tsd_ms_block(self, data: bytes, offset: int, data_type: int, no_samples: int,
                           payload_length: int, sensor_name: str, block_num: int) -> None:
        """Print TSD block with millisecond precision."""
        if payload_length < 12:
            print("  [Invalid TSD-MS block - too short]")
            return

        # last_utc_sample_time_ms (8 bytes) + sample_rate_ms (4 bytes) + data[]
        last_time_ms = struct.unpack('>Q', data[offset:offset+8])[0]
        sample_rate_ms = struct.unpack('>I', data[offset+8:offset+12])[0]

        # Track the last timestamp
        self._track_timestamp(last_time_ms, sensor_name, block_num, is_ms=True)

        print(f"  Sample Rate: {sample_rate_ms} ms")
        print(f"  Last Sample Time: {format_timestamp_ms(last_time_ms)}")

        # Print values
        data_offset = offset + 12
        max_display = no_samples if self.max_samples_display == 0 else min(no_samples, self.max_samples_display)

        if max_display > 0:
            print(f"  Values ({no_samples} total):")
            for i in range(max_display):
                raw_value = struct.unpack('>I', data[data_offset + i*4:data_offset + (i+1)*4])[0]
                print(f"    [{i+1}] {format_data_value(raw_value, data_type)}")

            if self.max_samples_display > 0 and no_samples > self.max_samples_display:
                print(f"    ... ({no_samples - self.max_samples_display} more samples)")

    def _print_event_block(self, data: bytes, offset: int, data_type: int, no_samples: int,
                          sensor_name: str, block_num: int) -> None:
        """Print event block with timestamps."""
        print(f"  Events ({no_samples} total):")

        max_display = no_samples if self.max_samples_display == 0 else min(no_samples, self.max_samples_display)

        for i in range(max_display):
            event_offset = offset + i * 8  # Each event: 4 bytes time + 4 bytes data
            event_time = struct.unpack('>I', data[event_offset:event_offset+4])[0]
            raw_value = struct.unpack('>I', data[event_offset+4:event_offset+8])[0]

            # Track each event timestamp
            self._track_timestamp(event_time, sensor_name, block_num, is_ms=False)

            print(f"    [{i+1}] {format_timestamp(event_time)}: {format_data_value(raw_value, data_type)}")

        if self.max_samples_display > 0 and no_samples > self.max_samples_display:
            print(f"    ... ({no_samples - self.max_samples_display} more events)")

    def _print_notification_block(self, data: bytes, offset: int, data_type: int,
                                   warning_level: int, sensor_error: int,
                                   sensor_name: str, block_num: int) -> None:
        """Print notification/warning block."""
        # time_data: utc_sample_time (4 bytes) + data (4 bytes)
        event_time = struct.unpack('>I', data[offset:offset+4])[0]
        raw_value = struct.unpack('>I', data[offset+4:offset+8])[0]

        # Track the notification timestamp
        self._track_timestamp(event_time, sensor_name, block_num, is_ms=False)

        print(f"  Warning Level: {get_warning_level_name(warning_level)}")
        if sensor_error != 0:
            print(f"  Error Code: {sensor_error}")
        print(f"  Time: {format_timestamp(event_time)}")
        print(f"  Value: {format_data_value(raw_value, data_type)}")

    def _print_ble_clients_block(self, data: bytes, offset: int, no_samples: int) -> None:
        """Print BLE client list block."""
        print(f"  Active BLE Devices ({no_samples}):")

        max_display = no_samples if self.max_samples_display == 0 else min(no_samples, self.max_samples_display)

        for i in range(max_display):
            thing_serial = struct.unpack('>I', data[offset + i*4:offset + (i+1)*4])[0]
            print(f"    Device {i + 1}: SN {thing_serial}")

        if self.max_samples_display > 0 and no_samples > self.max_samples_display:
            print(f"    ... ({no_samples - self.max_samples_display} more devices)")


def main():
    parser = argparse.ArgumentParser(
        description='Decode and print iMatrix CoAP packets in human-readable format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s packet.txt              # Decode packet from file
  %(prog)s packet.txt -v           # Verbose output (show all samples)
  %(prog)s packet.txt --no-color   # Disable color output
        '''
    )
    parser.add_argument('filename', help='File containing CoAP hex dump in [XX][XX] format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output - show all samples instead of limiting to 10')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output')
    parser.add_argument('--color', action='store_true',
                        help='Force colored output even when not a TTY')

    args = parser.parse_args()

    # Handle color settings
    if args.no_color:
        Colors.disable()
    elif not args.color and not sys.stdout.isatty():
        # Disable colors if not outputting to a TTY (unless --color is specified)
        Colors.disable()

    try:
        with open(args.filename, 'r') as f:
            hex_string = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.filename}' not found", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse hex dump
    try:
        packet_data = parse_hex_dump(hex_string)
    except Exception as e:
        print(f"Error parsing hex dump: {e}", file=sys.stderr)
        sys.exit(1)

    if len(packet_data) == 0:
        print("Error: No valid hex data found in file", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(packet_data)} bytes from hex dump")

    # Print packet
    printer = CoAPPacketPrinter(verbose=args.verbose)
    printer.print_packet(packet_data)


if __name__ == '__main__':
    main()
