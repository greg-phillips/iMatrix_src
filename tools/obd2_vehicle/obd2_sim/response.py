"""
Response Generator for OBD2 Vehicle Simulator.

Generates OBD2 response frames based on requests, profile data,
and value provider output. Handles both single-frame and multi-frame responses.
"""

import logging
from typing import Optional, List, Dict, Any

from .profile import VehicleProfile, ECUConfig
from .request import OBD2Request
from .value_provider import ValueProvider
from .config import SimulatorConfig, UnsupportedPIDMode

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates OBD2 responses for incoming requests.

    Handles:
    - Single-frame responses (most PIDs)
    - Multi-frame responses (VIN, DTCs)
    - Negative responses (NRC)
    - Correct padding per ECU
    """

    # Service response offset
    POSITIVE_RESPONSE_OFFSET = 0x40

    # Negative Response Codes
    NRC_SERVICE_NOT_SUPPORTED = 0x11
    NRC_SUBFUNCTION_NOT_SUPPORTED = 0x12

    def __init__(self, profile: VehicleProfile, value_provider: ValueProvider,
                 config: SimulatorConfig):
        """
        Initialize response generator.

        Args:
            profile: Vehicle profile
            value_provider: Value provider for response data
            config: Simulator configuration
        """
        self.profile = profile
        self.value_provider = value_provider
        self.config = config

    def generate_response(self, request: OBD2Request, ecu: ECUConfig) -> Optional[bytes]:
        """
        Generate a response for a request from a specific ECU.

        Args:
            request: Parsed OBD2 request
            ecu: ECU configuration

        Returns:
            Response frame data (8 bytes) or None if no response
        """
        # Get value from provider
        value = self.value_provider.get_value(request.service, request.pid, ecu.response_id)

        if value is None:
            # No value available - handle based on config
            return self._handle_unsupported(request, ecu)

        if isinstance(value, dict):
            # Multi-frame response - return special marker
            # Actual multi-frame handling is done in ISOTPHandler
            return value
        else:
            # Single-frame response - value is already the complete frame
            return value

    def _handle_unsupported(self, request: OBD2Request, ecu: ECUConfig) -> Optional[bytes]:
        """
        Handle unsupported PID based on configuration.

        Returns:
            NRC response or None (for no-response mode)
        """
        mode = self.config.unsupported_pid_mode

        if mode == UnsupportedPIDMode.NO_RESPONSE:
            logger.debug(f"No response for unsupported PID 0x{request.pid or 0:02X}")
            return None

        elif mode == UnsupportedPIDMode.NRC_12:
            return self._generate_nrc(request.service, self.NRC_SUBFUNCTION_NOT_SUPPORTED, ecu)

        elif mode == UnsupportedPIDMode.NRC_11:
            return self._generate_nrc(request.service, self.NRC_SERVICE_NOT_SUPPORTED, ecu)

        return None

    def _generate_nrc(self, service: int, nrc: int, ecu: ECUConfig) -> bytes:
        """
        Generate a Negative Response Code frame.

        NRC format: [03, 7F, Service, NRC, Padding...]

        Args:
            service: Original service ID
            nrc: Negative Response Code
            ecu: ECU configuration for padding

        Returns:
            8-byte response frame
        """
        response = bytearray(8)
        response[0] = 0x03  # Length
        response[1] = 0x7F  # Negative response
        response[2] = service
        response[3] = nrc

        # Apply padding
        for i in range(4, 8):
            response[i] = ecu.padding_byte

        return bytes(response)

    def generate_single_frame(self, service: int, pid: Optional[int],
                              data: bytes, ecu: ECUConfig) -> bytes:
        """
        Generate a single-frame positive response.

        Args:
            service: Service ID
            pid: PID number (optional)
            data: Data bytes
            ecu: ECU configuration

        Returns:
            8-byte response frame
        """
        response = bytearray(8)

        # Calculate length
        length = 1  # Service response
        if pid is not None:
            length += 1  # PID
        length += len(data)  # Data bytes

        response[0] = length
        response[1] = service + self.POSITIVE_RESPONSE_OFFSET

        offset = 2
        if pid is not None:
            response[offset] = pid
            offset += 1

        # Copy data bytes
        for i, b in enumerate(data):
            if offset + i < 8:
                response[offset + i] = b

        # Apply padding
        for i in range(offset + len(data), 8):
            response[i] = ecu.padding_byte

        return bytes(response)

    def get_multi_frame_data(self, request: OBD2Request, ecu: ECUConfig) -> Optional[Dict[str, Any]]:
        """
        Get multi-frame response data for special handling.

        Args:
            request: OBD2 request
            ecu: ECU configuration

        Returns:
            Dict with frames list and metadata, or None
        """
        value = self.value_provider.get_value(request.service, request.pid, ecu.response_id)

        if isinstance(value, dict) and 'frames' in value:
            return {
                'frames': value['frames'],
                'multi_frame': True,
                'total_length': value.get('total_length', 0),
            }

        return None

    def is_multi_frame_response(self, request: OBD2Request, ecu: ECUConfig) -> bool:
        """
        Check if a request requires a multi-frame response.

        Args:
            request: OBD2 request
            ecu: ECU configuration

        Returns:
            True if multi-frame response required
        """
        value = self.value_provider.get_value(request.service, request.pid, ecu.response_id)
        return isinstance(value, dict) and 'frames' in value
