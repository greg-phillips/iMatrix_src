"""
OBD2 Request Matcher for Vehicle Simulator.

Identifies and parses incoming OBD2 requests from CAN frames,
extracting service, PID, and routing information.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List

try:
    import can
except ImportError:
    can = None

from .can_id import CANIdentifier, OBD2_FUNCTIONAL_REQUEST_ID, OBD2_PHYSICAL_REQUEST_BASE
from .profile import ECUConfig
from .config import SimulatorConfig

logger = logging.getLogger(__name__)


@dataclass
class OBD2Request:
    """Parsed OBD2 request."""
    service: int                    # Service ID (e.g., 0x01)
    pid: Optional[int]              # PID number (None for service-only)
    data: bytes                     # Additional data bytes
    is_functional: bool             # True for broadcast (0x7DF)
    target_ecu_index: Optional[int] # Target ECU for physical requests
    raw_frame: bytes                # Original frame data
    can_id: int                     # Original CAN ID
    extended: bool                  # 29-bit extended frame

    @property
    def is_physical(self) -> bool:
        """Check if this is a physical (direct) request."""
        return not self.is_functional


class RequestMatcher:
    """
    Identifies and parses OBD2 requests from CAN frames.

    Handles both functional (broadcast) and physical (direct) requests,
    for 11-bit standard and 29-bit extended frame formats.
    """

    # ISO-TP frame type masks
    FRAME_TYPE_MASK = 0xF0
    FRAME_TYPE_SINGLE = 0x00
    FRAME_TYPE_FIRST = 0x10
    FRAME_TYPE_CONSECUTIVE = 0x20
    FRAME_TYPE_FLOW_CONTROL = 0x30

    def __init__(self, config: SimulatorConfig, ecus: List[ECUConfig]):
        """
        Initialize request matcher.

        Args:
            config: Simulator configuration
            ecus: List of ECU configurations
        """
        self.config = config
        self.ecus = ecus
        self.extended = config.extended_frames

        # Build ECU lookup by response ID
        self._ecu_by_response_id = {ecu.response_id: ecu for ecu in ecus}
        self._ecu_by_physical_id = {ecu.physical_request_id: ecu for ecu in ecus}

    def is_obd2_request(self, frame) -> bool:
        """
        Check if a CAN frame is an OBD2 request.

        Args:
            frame: can.Message object

        Returns:
            True if this is an OBD2 request
        """
        can_id = CANIdentifier(frame.arbitration_id, frame.is_extended_id)
        return can_id.is_obd2_request()

    def is_flow_control(self, frame) -> bool:
        """
        Check if a CAN frame is a flow control message.

        Args:
            frame: can.Message object

        Returns:
            True if this is a flow control frame
        """
        if len(frame.data) < 1:
            return False

        # Flow control uses physical request IDs (0x7E0-0x7E7)
        can_id = CANIdentifier(frame.arbitration_id, frame.is_extended_id)
        if not can_id.is_obd2_physical_request():
            return False

        # Check ISO-TP frame type
        return (frame.data[0] & self.FRAME_TYPE_MASK) == self.FRAME_TYPE_FLOW_CONTROL

    def parse_request(self, frame) -> Optional[OBD2Request]:
        """
        Parse a CAN frame into an OBD2Request.

        Args:
            frame: can.Message object

        Returns:
            OBD2Request if valid, None otherwise
        """
        if len(frame.data) < 2:
            return None

        can_id = CANIdentifier(frame.arbitration_id, frame.is_extended_id)

        # Check if this is an OBD2 request
        if not can_id.is_obd2_request():
            return None

        # Parse ISO-TP frame
        frame_type = frame.data[0] & self.FRAME_TYPE_MASK

        if frame_type == self.FRAME_TYPE_SINGLE:
            return self._parse_single_frame(frame, can_id)
        elif frame_type == self.FRAME_TYPE_FIRST:
            # Multi-frame request - not common for OBD2 requests
            logger.debug("Received multi-frame request (unusual)")
            return None
        else:
            # Not a request frame type
            return None

    def _parse_single_frame(self, frame, can_id: CANIdentifier) -> Optional[OBD2Request]:
        """
        Parse a single-frame OBD2 request.

        Single frame format: [Length, Service, PID, Data..., Padding...]
        """
        data = frame.data
        length = data[0] & 0x0F

        if length < 1 or length > 7:
            logger.debug(f"Invalid single frame length: {length}")
            return None

        service = data[1]
        pid = data[2] if length >= 2 else None
        extra_data = bytes(data[3:1+length]) if length > 2 else b''

        # Determine if functional or physical
        is_functional = can_id.is_obd2_functional_request()
        target_ecu = can_id.get_target_ecu_index() if not is_functional else None

        return OBD2Request(
            service=service,
            pid=pid,
            data=extra_data,
            is_functional=is_functional,
            target_ecu_index=target_ecu,
            raw_frame=bytes(frame.data),
            can_id=frame.arbitration_id,
            extended=frame.is_extended_id,
        )

    def get_target_ecus(self, request: OBD2Request) -> List[ECUConfig]:
        """
        Get list of ECUs that should respond to a request.

        Args:
            request: Parsed OBD2 request

        Returns:
            List of ECU configurations that should respond
        """
        if request.is_functional:
            # Functional request - all ECUs may respond
            return list(self.ecus)
        else:
            # Physical request - only target ECU responds
            if request.target_ecu_index is not None:
                # Find ECU by index
                for ecu in self.ecus:
                    if ecu.index == request.target_ecu_index:
                        return [ecu]

                # Try by physical request ID
                physical_id = OBD2_PHYSICAL_REQUEST_BASE + request.target_ecu_index
                if physical_id in self._ecu_by_physical_id:
                    return [self._ecu_by_physical_id[physical_id]]

            return []

    def parse_flow_control(self, frame) -> Optional[dict]:
        """
        Parse a flow control frame.

        Args:
            frame: can.Message object

        Returns:
            Flow control parameters or None if invalid
        """
        if not self.is_flow_control(frame):
            return None

        data = frame.data
        flow_status = data[0] & 0x0F
        block_size = data[1] if len(data) > 1 else 0
        separation_time = data[2] if len(data) > 2 else 0

        # Get source ECU index from physical request ID
        can_id = CANIdentifier(frame.arbitration_id, frame.is_extended_id)
        ecu_index = can_id.get_target_ecu_index()

        return {
            'flow_status': flow_status,  # 0=CTS, 1=Wait, 2=Overflow
            'block_size': block_size,
            'separation_time_ms': self._decode_separation_time(separation_time),
            'ecu_index': ecu_index,
        }

    def _decode_separation_time(self, st_byte: int) -> float:
        """
        Decode ISO-TP separation time byte to milliseconds.

        Args:
            st_byte: Separation time byte from flow control

        Returns:
            Separation time in milliseconds
        """
        if st_byte <= 0x7F:
            # 0x00-0x7F: 0-127 ms
            return float(st_byte)
        elif 0xF1 <= st_byte <= 0xF9:
            # 0xF1-0xF9: 100-900 microseconds
            return (st_byte - 0xF0) * 0.1
        else:
            # Reserved or invalid - default to 0
            return 0.0
