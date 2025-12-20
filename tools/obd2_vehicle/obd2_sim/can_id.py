"""
CAN Identifier handling for OBD2 Vehicle Simulator.

Handles both 11-bit standard and 29-bit extended CAN frame identifiers,
with specific support for OBD2 functional and physical addressing.
"""

from enum import Enum
from typing import Optional


class CANFormat(Enum):
    """CAN identifier format."""
    STANDARD_11BIT = "standard"
    EXTENDED_29BIT = "extended"


# Standard OBD2 CAN IDs (11-bit)
OBD2_FUNCTIONAL_REQUEST_ID = 0x7DF       # Functional broadcast request
OBD2_PHYSICAL_REQUEST_BASE = 0x7E0       # Physical request base (0x7E0-0x7E7)
OBD2_RESPONSE_BASE = 0x7E8               # Response base (0x7E8-0x7EF)

# Extended OBD2 CAN IDs (29-bit) - ISO 15765-4
OBD2_EXT_FUNCTIONAL_REQUEST = 0x18DB33F1  # Functional broadcast (29-bit)
OBD2_EXT_PHYSICAL_REQUEST_BASE = 0x18DA00F1  # Physical request base
OBD2_EXT_RESPONSE_BASE = 0x18DAF100      # Response base


class CANIdentifier:
    """
    CAN identifier handling with OBD2 awareness.

    Supports both 11-bit standard and 29-bit extended identifiers,
    with methods to identify OBD2 request/response frames.
    """

    def __init__(self, can_id: int, extended: bool = False):
        """
        Create a CAN identifier.

        Args:
            can_id: CAN arbitration ID
            extended: True for 29-bit extended, False for 11-bit standard
        """
        self.can_id = can_id
        self.extended = extended

        # Validate ID range
        if extended:
            if can_id < 0 or can_id > 0x1FFFFFFF:
                raise ValueError(f"Extended CAN ID out of range: 0x{can_id:08X}")
        else:
            if can_id < 0 or can_id > 0x7FF:
                raise ValueError(f"Standard CAN ID out of range: 0x{can_id:03X}")

    @property
    def format(self) -> CANFormat:
        """Get CAN format."""
        return CANFormat.EXTENDED_29BIT if self.extended else CANFormat.STANDARD_11BIT

    @property
    def raw_id(self) -> int:
        """Get raw CAN ID value."""
        return self.can_id

    def is_obd2_functional_request(self) -> bool:
        """Check if this is an OBD2 functional (broadcast) request."""
        if self.extended:
            return self.can_id == OBD2_EXT_FUNCTIONAL_REQUEST
        else:
            return self.can_id == OBD2_FUNCTIONAL_REQUEST_ID

    def is_obd2_physical_request(self) -> bool:
        """Check if this is an OBD2 physical (direct) request."""
        if self.extended:
            # Extract target ECU from 29-bit ID
            # Format: 0x18DAxxF1 where xx is target ECU (00-07)
            base = self.can_id & 0xFFFF00FF
            return base == OBD2_EXT_PHYSICAL_REQUEST_BASE
        else:
            return OBD2_PHYSICAL_REQUEST_BASE <= self.can_id <= (OBD2_PHYSICAL_REQUEST_BASE + 7)

    def is_obd2_request(self) -> bool:
        """Check if this is any OBD2 request (functional or physical)."""
        return self.is_obd2_functional_request() or self.is_obd2_physical_request()

    def is_obd2_response(self) -> bool:
        """Check if this is an OBD2 response."""
        if self.extended:
            # Format: 0x18DAF1xx where xx is source ECU (00-07)
            base = self.can_id & 0xFFFFFF00
            return base == OBD2_EXT_RESPONSE_BASE
        else:
            return OBD2_RESPONSE_BASE <= self.can_id <= (OBD2_RESPONSE_BASE + 7)

    def is_flow_control(self) -> bool:
        """
        Check if this could be a flow control frame.

        Flow control is sent from tester to ECU, so it uses
        physical request IDs (0x7E0-0x7E7).
        """
        return self.is_obd2_physical_request()

    def get_target_ecu_index(self) -> Optional[int]:
        """
        Get target ECU index for physical requests.

        Returns:
            ECU index (0-7) or None for functional requests
        """
        if not self.is_obd2_physical_request():
            return None

        if self.extended:
            # Extract from 29-bit: 0x18DAxxF1
            return (self.can_id >> 8) & 0xFF
        else:
            return self.can_id - OBD2_PHYSICAL_REQUEST_BASE

    def get_response_id(self, ecu_index: int) -> int:
        """
        Get the response ID for a given ECU index.

        Args:
            ecu_index: ECU index (0-7)

        Returns:
            Response CAN ID
        """
        if self.extended:
            return OBD2_EXT_RESPONSE_BASE | ecu_index
        else:
            return OBD2_RESPONSE_BASE + ecu_index

    def get_physical_request_id(self, ecu_index: int) -> int:
        """
        Get the physical request ID for a given ECU index.

        Args:
            ecu_index: ECU index (0-7)

        Returns:
            Physical request CAN ID
        """
        if self.extended:
            return OBD2_EXT_PHYSICAL_REQUEST_BASE | (ecu_index << 8)
        else:
            return OBD2_PHYSICAL_REQUEST_BASE + ecu_index

    def get_response_id_for_request(self) -> Optional[int]:
        """
        Get the response ID for this request.

        Returns:
            Response CAN ID or None if not a physical request
        """
        ecu_index = self.get_target_ecu_index()
        if ecu_index is None:
            return None
        return self.get_response_id(ecu_index)

    def __str__(self) -> str:
        if self.extended:
            return f"0x{self.can_id:08X}"
        else:
            return f"0x{self.can_id:03X}"

    def __repr__(self) -> str:
        if self.extended:
            return f"CANIdentifier(0x{self.can_id:08X}, extended=True)"
        else:
            return f"CANIdentifier(0x{self.can_id:03X})"

    def __eq__(self, other) -> bool:
        if isinstance(other, CANIdentifier):
            return self.can_id == other.can_id and self.extended == other.extended
        return False

    def __hash__(self) -> int:
        return hash((self.can_id, self.extended))


def is_obd2_request_id(can_id: int, extended: bool = False) -> bool:
    """
    Quick check if a CAN ID is an OBD2 request.

    Args:
        can_id: CAN arbitration ID
        extended: True for 29-bit mode

    Returns:
        True if this is an OBD2 request ID
    """
    return CANIdentifier(can_id, extended).is_obd2_request()


def is_obd2_response_id(can_id: int, extended: bool = False) -> bool:
    """
    Quick check if a CAN ID is an OBD2 response.

    Args:
        can_id: CAN arbitration ID
        extended: True for 29-bit mode

    Returns:
        True if this is an OBD2 response ID
    """
    return CANIdentifier(can_id, extended).is_obd2_response()


def get_ecu_index_from_response_id(response_id: int, extended: bool = False) -> int:
    """
    Extract ECU index from response ID.

    Args:
        response_id: OBD2 response CAN ID
        extended: True for 29-bit mode

    Returns:
        ECU index (0-7)
    """
    if extended:
        return response_id & 0xFF
    else:
        return response_id - OBD2_RESPONSE_BASE
