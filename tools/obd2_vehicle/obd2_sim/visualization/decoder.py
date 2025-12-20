"""
OBD2 PID Decoder for human-readable transaction display.

Decodes OBD2 service requests and responses into human-readable format.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DecodedMessage:
    """Decoded OBD2 message."""
    service: int
    pid: Optional[int]
    service_name: str
    pid_name: str
    value: Optional[str] = None
    unit: str = ""
    raw_value: Optional[int] = None


# OBD2 Service names
SERVICE_NAMES = {
    0x01: "Current Data",
    0x02: "Freeze Frame",
    0x03: "Stored DTCs",
    0x04: "Clear DTCs",
    0x05: "O2 Monitor",
    0x06: "Test Results",
    0x07: "Pending DTCs",
    0x08: "Control",
    0x09: "Vehicle Info",
    0x0A: "Permanent DTCs",
}

# Common PID names and decoders for Service 01
PID_INFO = {
    0x00: ("Supported PIDs [01-20]", None, ""),
    0x01: ("Monitor Status", None, ""),
    0x02: ("Freeze DTC", None, ""),
    0x03: ("Fuel System Status", None, ""),
    0x04: ("Engine Load", lambda a: a * 100 / 255, "%"),
    0x05: ("Coolant Temp", lambda a: a - 40, "°C"),
    0x06: ("Short Fuel Trim B1", lambda a: (a - 128) * 100 / 128, "%"),
    0x07: ("Long Fuel Trim B1", lambda a: (a - 128) * 100 / 128, "%"),
    0x08: ("Short Fuel Trim B2", lambda a: (a - 128) * 100 / 128, "%"),
    0x09: ("Long Fuel Trim B2", lambda a: (a - 128) * 100 / 128, "%"),
    0x0A: ("Fuel Pressure", lambda a: a * 3, "kPa"),
    0x0B: ("Intake MAP", lambda a: a, "kPa"),
    0x0C: ("Engine RPM", lambda a, b: (a * 256 + b) / 4, "RPM"),
    0x0D: ("Vehicle Speed", lambda a: a, "km/h"),
    0x0E: ("Timing Advance", lambda a: a / 2 - 64, "°"),
    0x0F: ("Intake Air Temp", lambda a: a - 40, "°C"),
    0x10: ("MAF Rate", lambda a, b: (a * 256 + b) / 100, "g/s"),
    0x11: ("Throttle Position", lambda a: a * 100 / 255, "%"),
    0x1C: ("OBD Standard", None, ""),
    0x1F: ("Run Time", lambda a, b: a * 256 + b, "sec"),
    0x20: ("Supported PIDs [21-40]", None, ""),
    0x21: ("Distance w/ MIL", lambda a, b: a * 256 + b, "km"),
    0x2F: ("Fuel Level", lambda a: a * 100 / 255, "%"),
    0x31: ("Distance Since Clear", lambda a, b: a * 256 + b, "km"),
    0x33: ("Barometric Pressure", lambda a: a, "kPa"),
    0x40: ("Supported PIDs [41-60]", None, ""),
    0x42: ("Control Module Voltage", lambda a, b: (a * 256 + b) / 1000, "V"),
    0x43: ("Absolute Load", lambda a, b: (a * 256 + b) * 100 / 255, "%"),
    0x45: ("Relative Throttle", lambda a: a * 100 / 255, "%"),
    0x46: ("Ambient Air Temp", lambda a: a - 40, "°C"),
    0x49: ("Accelerator Pedal D", lambda a: a * 100 / 255, "%"),
    0x4A: ("Accelerator Pedal E", lambda a: a * 100 / 255, "%"),
    0x4C: ("Commanded Throttle", lambda a: a * 100 / 255, "%"),
    0x51: ("Fuel Type", None, ""),
    0x5C: ("Oil Temp", lambda a: a - 40, "°C"),
    0x5E: ("Fuel Rate", lambda a, b: (a * 256 + b) / 20, "L/h"),
    0x60: ("Supported PIDs [61-80]", None, ""),
}

# Service 09 PID names
SERVICE_09_PIDS = {
    0x00: "Supported PIDs",
    0x02: "VIN",
    0x04: "Calibration ID",
    0x06: "CVN",
    0x0A: "ECU Name",
}


class OBD2Decoder:
    """Decoder for OBD2 messages to human-readable format."""

    @staticmethod
    def decode_request(data: bytes) -> DecodedMessage:
        """
        Decode an OBD2 request message.

        Args:
            data: Raw CAN data bytes (8 bytes)

        Returns:
            DecodedMessage with service and PID info
        """
        if len(data) < 2:
            return DecodedMessage(0, None, "Invalid", "Too short")

        length = data[0]
        service = data[1]

        service_name = SERVICE_NAMES.get(service, f"Service 0x{service:02X}")

        # Services without PIDs
        if service in (0x03, 0x04, 0x07, 0x0A):
            return DecodedMessage(
                service=service,
                pid=None,
                service_name=service_name,
                pid_name="",
            )

        # Services with PIDs
        pid = data[2] if length >= 2 and len(data) > 2 else None

        if service == 0x01 and pid is not None:
            pid_info = PID_INFO.get(pid, (f"PID 0x{pid:02X}", None, ""))
            pid_name = pid_info[0]
        elif service == 0x09 and pid is not None:
            pid_name = SERVICE_09_PIDS.get(pid, f"PID 0x{pid:02X}")
        elif pid is not None:
            pid_name = f"PID 0x{pid:02X}"
        else:
            pid_name = ""

        return DecodedMessage(
            service=service,
            pid=pid,
            service_name=service_name,
            pid_name=pid_name,
        )

    @staticmethod
    def decode_response(data: bytes) -> DecodedMessage:
        """
        Decode an OBD2 response message.

        Args:
            data: Raw CAN data bytes (8 bytes)

        Returns:
            DecodedMessage with decoded value if possible
        """
        if len(data) < 2:
            return DecodedMessage(0, None, "Invalid", "Too short")

        length = data[0]
        response_sid = data[1]

        # Check for negative response
        if response_sid == 0x7F:
            nrc = data[3] if len(data) > 3 else 0
            nrc_names = {
                0x10: "General Reject",
                0x11: "Service Not Supported",
                0x12: "SubFunction Not Supported",
                0x13: "Invalid Format",
                0x14: "Response Too Long",
                0x22: "Conditions Not Correct",
                0x31: "Request Out Of Range",
            }
            return DecodedMessage(
                service=data[2] if len(data) > 2 else 0,
                pid=None,
                service_name="Negative Response",
                pid_name=nrc_names.get(nrc, f"NRC 0x{nrc:02X}"),
            )

        # Positive response (SID + 0x40)
        service = response_sid - 0x40

        # Service 03/07/0A: DTC responses
        if service in (0x03, 0x07, 0x0A):
            num_dtcs = data[2] if len(data) > 2 else 0
            return DecodedMessage(
                service=service,
                pid=None,
                service_name=SERVICE_NAMES.get(service, f"Service 0x{service:02X}"),
                pid_name="",
                value=f"{num_dtcs} DTCs" if num_dtcs else "No DTCs",
            )

        # Service 01/02: PID responses
        if service in (0x01, 0x02) and len(data) >= 3:
            pid = data[2]
            pid_info = PID_INFO.get(pid, (f"PID 0x{pid:02X}", None, ""))
            pid_name, decoder, unit = pid_info

            value = None
            raw_value = None

            if decoder and len(data) >= 4:
                try:
                    # Determine number of data bytes based on decoder signature
                    import inspect
                    sig = inspect.signature(decoder)
                    num_params = len(sig.parameters)

                    if num_params == 1 and len(data) >= 4:
                        raw_value = data[3]
                        value = f"{decoder(data[3]):.1f}"
                    elif num_params == 2 and len(data) >= 5:
                        raw_value = data[3] * 256 + data[4]
                        value = f"{decoder(data[3], data[4]):.1f}"
                except Exception:
                    pass

            return DecodedMessage(
                service=service,
                pid=pid,
                service_name=SERVICE_NAMES.get(service, f"Service 0x{service:02X}"),
                pid_name=pid_name,
                value=value,
                unit=unit,
                raw_value=raw_value,
            )

        # Service 09: Vehicle Info
        if service == 0x09 and len(data) >= 3:
            pid = data[2]
            pid_name = SERVICE_09_PIDS.get(pid, f"PID 0x{pid:02X}")
            return DecodedMessage(
                service=service,
                pid=pid,
                service_name="Vehicle Info",
                pid_name=pid_name,
            )

        # Generic response
        return DecodedMessage(
            service=service,
            pid=data[2] if len(data) > 2 else None,
            service_name=SERVICE_NAMES.get(service, f"Service 0x{service:02X}"),
            pid_name="",
        )

    @staticmethod
    def format_request_short(data: bytes) -> str:
        """Format request as short description."""
        decoded = OBD2Decoder.decode_request(data)
        if decoded.pid is not None:
            return f"Req: {decoded.pid_name}"
        return f"Req: {decoded.service_name}"

    @staticmethod
    def format_response_short(data: bytes) -> str:
        """Format response as short description with value."""
        decoded = OBD2Decoder.decode_response(data)

        if decoded.value:
            if decoded.unit:
                return f"Rsp: {decoded.value} {decoded.unit}"
            return f"Rsp: {decoded.value}"

        if decoded.pid_name:
            return f"Rsp: {decoded.pid_name}"

        return f"Rsp: {decoded.service_name}"

    @staticmethod
    def format_broadcast_short(can_id: int, data: bytes) -> str:
        """Format broadcast message as short description."""
        # Simple description based on CAN ID patterns
        if can_id < 0x100:
            return "Broadcast: High Priority"
        elif can_id < 0x400:
            return "Broadcast: Status"
        elif can_id < 0x700:
            return "Broadcast: Data"
        else:
            return "Broadcast: Info"
