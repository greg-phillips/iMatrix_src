"""
ISO-TP (ISO 15765-2) Handler for OBD2 Vehicle Simulator.

Handles multi-frame message segmentation and flow control for
messages larger than 7 bytes (like VIN retrieval).
"""

import logging
import threading
import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum

try:
    import can
except ImportError:
    can = None

from .profile import ECUConfig
from .can_id import (OBD2_RESPONSE_BASE, OBD2_EXT_RESPONSE_BASE,
                     OBD2_PHYSICAL_REQUEST_BASE, OBD2_EXT_PHYSICAL_REQUEST_BASE)

logger = logging.getLogger(__name__)


class PCIType(Enum):
    """ISO-TP Protocol Control Information types."""
    SINGLE_FRAME = 0x00
    FIRST_FRAME = 0x10
    CONSECUTIVE_FRAME = 0x20
    FLOW_CONTROL = 0x30


class FlowStatus(Enum):
    """Flow control status codes."""
    CLEAR_TO_SEND = 0
    WAIT = 1
    OVERFLOW = 2


@dataclass
class MultiFrameSession:
    """Tracks state for a multi-frame transmission."""
    ecu_id: int
    tester_id: int  # Where to expect flow control from
    frames: List[bytes]
    total_length: int
    current_index: int = 0
    sequence_number: int = 1
    waiting_for_fc: bool = True
    block_size: int = 0
    separation_time_ms: float = 0
    frames_in_block: int = 0


class ISOTPHandler:
    """
    Handles ISO-TP multi-frame message transmission.

    Implements:
    - Single Frame (SF) - messages up to 7 bytes
    - First Frame (FF) - start of multi-frame message
    - Consecutive Frame (CF) - continuation frames
    - Flow Control (FC) - handling from tester
    """

    # Default timing
    DEFAULT_CF_SEPARATION_MS = 5.0
    FC_TIMEOUT_MS = 1000.0

    def __init__(self, can_bus, extended: bool = False):
        """
        Initialize ISO-TP handler.

        Args:
            can_bus: python-can bus interface
            extended: Use 29-bit extended frames
        """
        self.can_bus = can_bus
        self.extended = extended
        self._sessions: Dict[int, MultiFrameSession] = {}  # keyed by ECU response ID
        self._lock = threading.Lock()

    def _get_tx_arbitration_id(self, ecu_response_id: int) -> int:
        """
        Get the correct CAN arbitration ID for transmission.

        Converts 11-bit ECU response IDs to 29-bit format when in extended mode.

        Args:
            ecu_response_id: ECU response ID from profile (e.g., 0x7E8)

        Returns:
            Correct arbitration ID for current mode
        """
        if not self.extended:
            return ecu_response_id

        # Convert 11-bit response ID to 29-bit format
        # 0x7E8 -> 0x18DAF100, 0x7E9 -> 0x18DAF101, etc.
        if OBD2_RESPONSE_BASE <= ecu_response_id <= (OBD2_RESPONSE_BASE + 7):
            ecu_index = ecu_response_id - OBD2_RESPONSE_BASE
            return OBD2_EXT_RESPONSE_BASE | ecu_index

        # Already extended or non-standard ID - use as-is
        return ecu_response_id

    def _normalize_fc_arbitration_id(self, arbitration_id: int) -> int:
        """
        Normalize incoming flow control ID to 11-bit format for session matching.

        When in extended mode, converts 29-bit physical request IDs to 11-bit.

        Args:
            arbitration_id: Incoming flow control CAN ID

        Returns:
            Normalized 11-bit physical request ID
        """
        # Check if this is a 29-bit extended physical request ID
        # Format: 0x18DAxxF1 where xx is target ECU (00-07)
        if (arbitration_id & 0xFFFF00FF) == OBD2_EXT_PHYSICAL_REQUEST_BASE:
            ecu_index = (arbitration_id >> 8) & 0xFF
            return OBD2_PHYSICAL_REQUEST_BASE + ecu_index

        return arbitration_id

    def send_single_frame(self, arbitration_id: int, data: bytes) -> bool:
        """
        Send a single-frame message.

        Args:
            arbitration_id: CAN arbitration ID (will be converted for extended mode)
            data: Frame data (already formatted with PCI)

        Returns:
            True if sent successfully
        """
        if len(data) > 8:
            logger.error(f"Single frame data too long: {len(data)}")
            return False

        # Convert arbitration ID for extended mode if needed
        tx_id = self._get_tx_arbitration_id(arbitration_id)

        # Ensure 8 bytes
        padded_data = bytearray(data)
        while len(padded_data) < 8:
            padded_data.append(0x00)

        msg = can.Message(
            arbitration_id=tx_id,
            data=bytes(padded_data),
            is_extended_id=self.extended,
        )

        try:
            self.can_bus.send(msg)
            if self.extended:
                logger.debug(f"Sent SF to 0x{tx_id:08X}: {data.hex(' ').upper()}")
            else:
                logger.debug(f"Sent SF to 0x{tx_id:03X}: {data.hex(' ').upper()}")
            return True
        except can.CanError as e:
            logger.error(f"Failed to send single frame: {e}")
            return False

    def start_multi_frame(self, ecu: ECUConfig, frames_hex: List[str],
                          total_length: int) -> bool:
        """
        Start a multi-frame transmission.

        Sends the First Frame and waits for Flow Control.

        Args:
            ecu: ECU configuration
            frames_hex: List of frame data strings from profile
            total_length: Total payload length

        Returns:
            True if first frame sent successfully
        """
        # Convert hex strings to bytes
        frames = []
        for frame_hex in frames_hex:
            frame_bytes = bytes.fromhex(frame_hex.replace(' ', ''))
            frames.append(frame_bytes)

        if not frames:
            logger.error("No frames to send")
            return False

        # Create session
        session = MultiFrameSession(
            ecu_id=ecu.response_id,
            tester_id=ecu.physical_request_id,
            frames=frames,
            total_length=total_length,
            current_index=0,
            sequence_number=1,
            waiting_for_fc=True,
        )

        with self._lock:
            self._sessions[ecu.response_id] = session

        # Send first frame
        first_frame = frames[0]
        return self._send_frame(ecu.response_id, first_frame)

    def handle_flow_control(self, arbitration_id: int, data: bytes) -> None:
        """
        Handle incoming flow control frame from tester.

        Args:
            arbitration_id: CAN ID of flow control frame (tester's physical ID)
            data: Flow control frame data
        """
        if len(data) < 3:
            logger.warning(f"Flow control frame too short: {len(data)}")
            return

        # Parse flow control
        pci = data[0]
        if (pci & 0xF0) != PCIType.FLOW_CONTROL.value:
            return

        flow_status = FlowStatus(pci & 0x0F)
        block_size = data[1]
        st_byte = data[2]
        separation_time = self._decode_separation_time(st_byte)

        # Normalize the incoming ID (convert 29-bit to 11-bit for matching)
        normalized_id = self._normalize_fc_arbitration_id(arbitration_id)

        # Find matching session (arbitration_id is tester's physical ID)
        # We need to find which ECU session this FC is for
        with self._lock:
            for ecu_id, session in self._sessions.items():
                if session.tester_id == normalized_id and session.waiting_for_fc:
                    logger.debug(f"Flow control received from 0x{arbitration_id:X} for ECU 0x{ecu_id:03X}")
                    self._process_flow_control(session, flow_status, block_size, separation_time)
                    return

        if self.extended:
            logger.debug(f"No session waiting for FC from 0x{arbitration_id:08X}")
        else:
            logger.debug(f"No session waiting for FC from 0x{arbitration_id:03X}")

    def _process_flow_control(self, session: MultiFrameSession, flow_status: FlowStatus,
                              block_size: int, separation_time: float) -> None:
        """Process flow control and send consecutive frames."""
        if flow_status == FlowStatus.CLEAR_TO_SEND:
            session.waiting_for_fc = False
            session.block_size = block_size
            session.separation_time_ms = separation_time
            session.frames_in_block = 0

            # Send consecutive frames
            self._send_consecutive_frames(session)

        elif flow_status == FlowStatus.WAIT:
            logger.debug(f"Flow control WAIT for ECU 0x{session.ecu_id:03X}")
            # Keep waiting for next FC

        elif flow_status == FlowStatus.OVERFLOW:
            logger.warning(f"Flow control OVERFLOW for ECU 0x{session.ecu_id:03X}")
            # Abort session
            with self._lock:
                if session.ecu_id in self._sessions:
                    del self._sessions[session.ecu_id]

    def _send_consecutive_frames(self, session: MultiFrameSession) -> None:
        """Send remaining consecutive frames respecting block size and timing."""
        # Start from index 1 (first frame already sent)
        start_index = session.current_index + 1

        for i in range(start_index, len(session.frames)):
            # Check block size
            if session.block_size > 0:
                if session.frames_in_block >= session.block_size:
                    # Need to wait for another FC
                    session.current_index = i - 1
                    session.waiting_for_fc = True
                    return

            # Apply separation time
            if session.separation_time_ms > 0 and i > start_index:
                time.sleep(session.separation_time_ms / 1000.0)

            # Send frame
            frame = session.frames[i]
            self._send_frame(session.ecu_id, frame)
            session.frames_in_block += 1

        # All frames sent - clean up session
        with self._lock:
            if session.ecu_id in self._sessions:
                del self._sessions[session.ecu_id]

        logger.debug(f"Multi-frame complete for ECU 0x{session.ecu_id:03X}")

    def _send_frame(self, arbitration_id: int, data: bytes) -> bool:
        """Send a single CAN frame."""
        # Convert arbitration ID for extended mode if needed
        tx_id = self._get_tx_arbitration_id(arbitration_id)

        # Ensure 8 bytes
        padded_data = bytearray(data)
        while len(padded_data) < 8:
            padded_data.append(0x00)

        msg = can.Message(
            arbitration_id=tx_id,
            data=bytes(padded_data[:8]),
            is_extended_id=self.extended,
        )

        try:
            self.can_bus.send(msg)
            if self.extended:
                logger.debug(f"Sent to 0x{tx_id:08X}: {data.hex(' ').upper()}")
            else:
                logger.debug(f"Sent to 0x{tx_id:03X}: {data.hex(' ').upper()}")
            return True
        except can.CanError as e:
            logger.error(f"Failed to send frame: {e}")
            return False

    def _decode_separation_time(self, st_byte: int) -> float:
        """Decode ISO-TP separation time byte to milliseconds."""
        if st_byte <= 0x7F:
            return float(st_byte)
        elif 0xF1 <= st_byte <= 0xF9:
            return (st_byte - 0xF0) * 0.1
        else:
            return self.DEFAULT_CF_SEPARATION_MS

    def has_pending_session(self, ecu_id: int) -> bool:
        """Check if there's a pending multi-frame session for an ECU."""
        with self._lock:
            return ecu_id in self._sessions

    def cancel_session(self, ecu_id: int) -> None:
        """Cancel a multi-frame session."""
        with self._lock:
            if ecu_id in self._sessions:
                del self._sessions[ecu_id]
