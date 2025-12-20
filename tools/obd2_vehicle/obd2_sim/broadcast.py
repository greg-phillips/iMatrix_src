"""
Broadcast Message Generator for OBD2 Vehicle Simulator.

Generates periodic broadcast messages matching patterns from parsed trace files.
Supports static messages and dynamic messages with rolling counters.
"""

import logging
import threading
import time
from typing import List, Dict, Optional

try:
    import can
except ImportError:
    can = None

from .profile import VehicleProfile, BroadcastConfig
from .config import SimulatorConfig

logger = logging.getLogger(__name__)


class BroadcastGenerator:
    """
    Generates periodic broadcast messages matching patterns from parsed trace.

    Supports:
    - Static messages (identical data every time)
    - Dynamic messages with rolling counters
    - Dynamic messages with varying byte patterns
    """

    def __init__(self, can_bus, config: SimulatorConfig,
                 broadcast_configs: List[BroadcastConfig]):
        """
        Initialize broadcast generator.

        Args:
            can_bus: python-can bus interface
            config: Simulator configuration
            broadcast_configs: List of broadcast configurations
        """
        self.can_bus = can_bus
        self.config = config
        self.broadcasts = broadcast_configs
        self.timers: Dict[int, threading.Timer] = {}
        self.running = False
        self._lock = threading.Lock()

        logger.debug(f"BroadcastGenerator initialized with {len(broadcast_configs)} messages")

    def start(self) -> None:
        """Start all broadcast message timers."""
        if not self.config.broadcast_enabled:
            logger.info("Broadcast messages disabled")
            return

        self.running = True

        for bc in self.broadcasts:
            if self._is_enabled(bc.can_id):
                self._start_broadcast_timer(bc)
                logger.debug(f"Started broadcast 0x{bc.can_id:04X} @ {bc.interval_ms}ms")

        logger.info(f"Started {len(self.timers)} broadcast generators")

    def stop(self) -> None:
        """Stop all broadcast timers."""
        self.running = False

        with self._lock:
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()

        logger.info("Stopped broadcast generators")

    def _start_broadcast_timer(self, bc: BroadcastConfig) -> None:
        """Start periodic timer for a single broadcast message."""
        def send_broadcast():
            if not self.running:
                return

            self._send_message(bc)

            # Reschedule
            if self.running:
                timer = threading.Timer(bc.interval_ms / 1000.0, send_broadcast)
                timer.daemon = True
                with self._lock:
                    self.timers[bc.can_id] = timer
                timer.start()

        # Initial send after first interval
        timer = threading.Timer(bc.interval_ms / 1000.0, send_broadcast)
        timer.daemon = True
        with self._lock:
            self.timers[bc.can_id] = timer
        timer.start()

    def _send_message(self, bc: BroadcastConfig) -> None:
        """Generate and send a single broadcast message."""
        if bc.pattern_type == 'static':
            data = bc.static_data
        else:
            data = self._generate_dynamic_data(bc)

        if data is None:
            return

        # Ensure correct DLC
        if len(data) < bc.dlc:
            data = data + bytes(bc.dlc - len(data))
        elif len(data) > bc.dlc:
            data = data[:bc.dlc]

        msg = can.Message(
            arbitration_id=bc.can_id,
            data=data,
            is_extended_id=False,
        )

        try:
            self.can_bus.send(msg)
            if self.config.log_frames:
                logger.debug(f"Broadcast 0x{bc.can_id:04X}: {data.hex(' ').upper()}")
        except can.CanError as e:
            logger.warning(f"Failed to send broadcast 0x{bc.can_id:04X}: {e}")

    def _generate_dynamic_data(self, bc: BroadcastConfig) -> bytes:
        """
        Generate data for dynamic broadcast message.

        Handles:
        - Rolling counters with configurable increment and wrap
        - Varying bytes with value selection
        - Static byte preservation
        """
        if bc.template is None:
            logger.warning(f"No template for dynamic broadcast 0x{bc.can_id:04X}")
            return None

        data = bytearray(bc.template)

        with self._lock:
            for vb in bc.varying_bytes:
                pos = vb.get('position')
                if pos is None or pos >= len(data):
                    continue

                pattern = vb.get('pattern', '')

                if pattern == 'rolling_counter':
                    # Update rolling counter
                    if pos not in bc.counter_values:
                        # Initialize from first observed value or range start
                        values = vb.get('values', [])
                        range_vals = vb.get('range', [])
                        if values:
                            # Values might be hex strings
                            if isinstance(values[0], str):
                                bc.counter_values[pos] = int(values[0], 16)
                            else:
                                bc.counter_values[pos] = values[0]
                        elif range_vals:
                            bc.counter_values[pos] = range_vals[0]
                        else:
                            bc.counter_values[pos] = 0

                    data[pos] = bc.counter_values[pos]

                    # Increment for next time
                    increment = vb.get('increment', 1)
                    bc.counter_values[pos] = (bc.counter_values[pos] + increment) % 256

                    # Handle wrap within specified range
                    range_vals = vb.get('range', [])
                    if len(range_vals) >= 2:
                        min_val, max_val = range_vals[0], range_vals[1]
                        if bc.counter_values[pos] > max_val:
                            bc.counter_values[pos] = min_val
                        elif bc.counter_values[pos] < min_val:
                            bc.counter_values[pos] = max_val

                elif pattern == 'checksum':
                    # Checksum calculation - placeholder
                    # Real implementation would depend on checksum algorithm
                    # For now, use first observed value or calculate simple sum
                    values = vb.get('values', [])
                    if values:
                        if isinstance(values[0], str):
                            data[pos] = int(values[0], 16)
                        else:
                            data[pos] = values[0]

                else:
                    # Generic varying byte - use first observed value
                    values = vb.get('values', [])
                    if values:
                        if isinstance(values[0], str):
                            data[pos] = int(values[0], 16)
                        else:
                            data[pos] = values[0]

        return bytes(data)

    def _is_enabled(self, can_id: int) -> bool:
        """Check if broadcast is enabled based on config."""
        if not self.config.broadcast_enabled:
            return False
        if self.config.broadcast_ids:
            return can_id in self.config.broadcast_ids
        return True

    @classmethod
    def from_profile(cls, can_bus, config: SimulatorConfig,
                     profile: VehicleProfile) -> 'BroadcastGenerator':
        """
        Create BroadcastGenerator from parsed vehicle profile.

        Args:
            can_bus: python-can bus interface
            config: Simulator configuration
            profile: Vehicle profile with broadcast configurations

        Returns:
            Configured BroadcastGenerator instance
        """
        broadcast_configs = profile.get_broadcast_messages()
        return cls(can_bus, config, broadcast_configs)
