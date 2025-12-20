"""
OBD2 Vehicle Simulator - Main Simulator Module.

Core simulator that integrates all components to emulate an OBD2-compliant
vehicle on a CAN bus. Handles request processing, response generation,
broadcast messages, and multi-frame communication.
"""

import logging
import threading
import time
from typing import Optional, TYPE_CHECKING

try:
    import can
except ImportError:
    can = None

from .config import SimulatorConfig
from .profile import VehicleProfile
from .request import RequestMatcher, OBD2Request
from .response import ResponseGenerator
from .value_provider import StaticValueProvider, ValueProvider
from .isotp import ISOTPHandler
from .broadcast import BroadcastGenerator

if TYPE_CHECKING:
    from .visualization.tui import SimulatorTUI

logger = logging.getLogger(__name__)


class OBD2Simulator:
    """
    Main OBD2 Vehicle Simulator.

    Integrates all components to provide a complete vehicle simulation:
    - Request matching and parsing
    - Response generation from profile data
    - Multi-frame ISO-TP handling
    - Periodic broadcast messages
    - Statistics tracking
    """

    def __init__(self, config: SimulatorConfig, profile: VehicleProfile,
                 tui: Optional['SimulatorTUI'] = None):
        """
        Initialize the OBD2 simulator.

        Args:
            config: Simulator configuration
            profile: Loaded vehicle profile
            tui: Optional TUI for visualization
        """
        self.config = config
        self.profile = profile
        self.tui = tui
        self.can_bus: Optional[can.Bus] = None
        self.running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Statistics
        self.stats = {
            'requests_received': 0,
            'responses_sent': 0,
            'broadcasts_sent': 0,
            'errors': 0,
            'multi_frame_sessions': 0,
            'start_time': None,
        }

        # Components initialized on start
        self.request_matcher: Optional[RequestMatcher] = None
        self.response_generator: Optional[ResponseGenerator] = None
        self.value_provider: Optional[ValueProvider] = None
        self.isotp_handler: Optional[ISOTPHandler] = None
        self.broadcast_generator: Optional[BroadcastGenerator] = None

        logger.info(f"OBD2Simulator initialized for profile: {profile.name}")

    def start(self) -> None:
        """Start the simulator."""
        if self.running:
            logger.warning("Simulator already running")
            return

        logger.info("Starting OBD2 simulator...")

        # Initialize CAN bus
        self._init_can_bus()

        # Initialize components
        self._init_components()

        # Start receive thread
        self.running = True
        self.stats['start_time'] = time.time()
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

        # Start broadcast generator
        if self.broadcast_generator:
            self.broadcast_generator.start()

        logger.info(f"Simulator started on {self.config.can_interface}")
        logger.info(f"Operating mode: {self.profile.get_operating_mode()}")
        logger.info(f"ECUs configured: {len(self.profile.get_ecus())}")

    def stop(self) -> None:
        """Stop the simulator."""
        if not self.running:
            return

        logger.info("Stopping OBD2 simulator...")

        self.running = False

        # Stop broadcast generator
        if self.broadcast_generator:
            self.broadcast_generator.stop()

        # Wait for receive thread
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)

        # Close CAN bus
        if self.can_bus:
            try:
                self.can_bus.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down CAN bus: {e}")
            self.can_bus = None

        self._log_stats()
        logger.info("Simulator stopped")

    def _init_can_bus(self) -> None:
        """Initialize the CAN bus interface."""
        if can is None:
            raise ImportError("python-can library not installed")

        try:
            self.can_bus = can.Bus(
                interface=self.config.can_interface_type,
                channel=self.config.can_interface,
                bitrate=self.config.can_bitrate,
            )
            logger.info(f"CAN bus initialized: {self.config.can_interface} @ {self.config.can_bitrate} bps")
        except can.CanError as e:
            logger.error(f"Failed to initialize CAN bus: {e}")
            raise

    def _init_components(self) -> None:
        """Initialize simulator components."""
        ecus = self.profile.get_ecus()

        # Request matcher
        self.request_matcher = RequestMatcher(self.config, ecus)

        # Value provider (Phase 1: static)
        self.value_provider = StaticValueProvider(self.profile)

        # Response generator
        self.response_generator = ResponseGenerator(
            self.profile, self.value_provider, self.config
        )

        # ISO-TP handler
        self.isotp_handler = ISOTPHandler(
            self.can_bus, extended=self.config.extended_frames
        )

        # Broadcast generator
        self.broadcast_generator = BroadcastGenerator.from_profile(
            self.can_bus, self.config, self.profile
        )

        logger.debug("All components initialized")

    def _receive_loop(self) -> None:
        """Main loop for receiving and processing CAN messages."""
        logger.debug("Receive loop started")

        while self.running:
            try:
                msg = self.can_bus.recv(timeout=0.1)
                if msg is not None:
                    self._process_message(msg)
            except can.CanError as e:
                logger.error(f"CAN receive error: {e}")
                with self._lock:
                    self.stats['errors'] += 1
            except Exception as e:
                logger.exception(f"Unexpected error in receive loop: {e}")
                with self._lock:
                    self.stats['errors'] += 1

        logger.debug("Receive loop stopped")

    def _process_message(self, msg: can.Message) -> None:
        """
        Process a received CAN message.

        Args:
            msg: Received CAN message
        """
        if self.config.log_frames:
            logger.debug(f"RX 0x{msg.arbitration_id:03X}: {msg.data.hex(' ').upper()}")

        # Check for flow control (for multi-frame responses)
        if self.request_matcher.is_flow_control(msg):
            self.isotp_handler.handle_flow_control(msg.arbitration_id, msg.data)
            return

        # Check if this is an OBD2 request
        if not self.request_matcher.is_obd2_request(msg):
            return

        # Parse the request
        request = self.request_matcher.parse_request(msg)
        if request is None:
            return

        with self._lock:
            self.stats['requests_received'] += 1

        # Report to TUI
        if self.tui:
            self.tui.record_request(
                msg.arbitration_id,
                msg.data,
                msg.is_extended_id
            )

        if self.config.log_frames:
            pid_str = f"0x{request.pid:02X}" if request.pid is not None else "N/A"
            logger.info(f"Request: Service 0x{request.service:02X}, PID {pid_str}, "
                       f"{'Functional' if request.is_functional else 'Physical'}")

        # Get target ECUs
        target_ecus = self.request_matcher.get_target_ecus(request)

        # Generate and send responses
        for ecu in target_ecus:
            self._handle_ecu_response(request, ecu)

    def _handle_ecu_response(self, request: OBD2Request, ecu) -> None:
        """
        Generate and send response from a specific ECU.

        Args:
            request: Parsed OBD2 request
            ecu: ECU configuration
        """
        # Check if this is a multi-frame response
        if self.response_generator.is_multi_frame_response(request, ecu):
            self._send_multi_frame_response(request, ecu)
        else:
            self._send_single_frame_response(request, ecu)

    def _send_single_frame_response(self, request: OBD2Request, ecu) -> None:
        """
        Send a single-frame response.

        Args:
            request: OBD2 request
            ecu: ECU configuration
        """
        response_data = self.response_generator.generate_response(request, ecu)

        if response_data is None:
            logger.debug(f"No response from ECU 0x{ecu.response_id:03X}")
            return

        if isinstance(response_data, dict):
            # This is actually a multi-frame response marker
            self._send_multi_frame_response(request, ecu)
            return

        # Add inter-ECU delay for functional requests
        if request.is_functional and ecu.index > 0:
            time.sleep(self.config.response_delay_ms / 1000.0)

        # Send response
        success = self.isotp_handler.send_single_frame(ecu.response_id, response_data)

        if success:
            with self._lock:
                self.stats['responses_sent'] += 1

            # Report to TUI
            if self.tui:
                self.tui.record_response(
                    ecu.response_id,
                    response_data,
                    ecu.name,
                    self.config.extended_frames
                )

            if self.config.log_frames:
                logger.info(f"Response 0x{ecu.response_id:03X}: {response_data.hex(' ').upper()}")

    def _send_multi_frame_response(self, request: OBD2Request, ecu) -> None:
        """
        Send a multi-frame response using ISO-TP.

        Args:
            request: OBD2 request
            ecu: ECU configuration
        """
        mf_data = self.response_generator.get_multi_frame_data(request, ecu)

        if mf_data is None:
            logger.warning(f"No multi-frame data for ECU 0x{ecu.response_id:03X}")
            return

        frames = mf_data.get('frames', [])
        total_length = mf_data.get('total_length', 0)

        if not frames:
            logger.warning("Empty frames list for multi-frame response")
            return

        with self._lock:
            self.stats['multi_frame_sessions'] += 1

        # Start multi-frame transmission
        success = self.isotp_handler.start_multi_frame(ecu, frames, total_length)

        if success:
            with self._lock:
                self.stats['responses_sent'] += 1

            if self.config.log_frames:
                logger.info(f"Multi-frame started 0x{ecu.response_id:03X}: {len(frames)} frames")

    def get_stats(self) -> dict:
        """
        Get current simulator statistics.

        Returns:
            Dictionary of statistics
        """
        with self._lock:
            stats = dict(self.stats)

        if stats['start_time']:
            stats['uptime_seconds'] = time.time() - stats['start_time']
        else:
            stats['uptime_seconds'] = 0

        return stats

    def _log_stats(self) -> None:
        """Log final statistics."""
        stats = self.get_stats()
        logger.info("=== Simulator Statistics ===")
        logger.info(f"  Uptime: {stats['uptime_seconds']:.1f} seconds")
        logger.info(f"  Requests received: {stats['requests_received']}")
        logger.info(f"  Responses sent: {stats['responses_sent']}")
        logger.info(f"  Multi-frame sessions: {stats['multi_frame_sessions']}")
        logger.info(f"  Errors: {stats['errors']}")

    def set_tui(self, tui: 'SimulatorTUI') -> None:
        """
        Set the TUI for visualization.

        Args:
            tui: SimulatorTUI instance
        """
        self.tui = tui

    @classmethod
    def from_config(cls, config: SimulatorConfig,
                    tui: Optional['SimulatorTUI'] = None) -> 'OBD2Simulator':
        """
        Create simulator from configuration.

        Args:
            config: Simulator configuration with profile path
            tui: Optional TUI for visualization

        Returns:
            Configured OBD2Simulator instance
        """
        # Load profile
        profile = VehicleProfile.load(config.profile_path)

        return cls(config, profile, tui)


def run_simulator(config: SimulatorConfig, use_tui: bool = False) -> None:
    """
    Run the OBD2 simulator with the given configuration.

    This is the main entry point called from the CLI.

    Args:
        config: Simulator configuration
        use_tui: Enable terminal UI visualization
    """
    tui = None

    try:
        # Load profile first to get info for TUI
        profile = VehicleProfile.load(config.profile_path)

        # Create TUI if enabled
        if use_tui:
            from .visualization.tui import SimulatorTUI
            tui = SimulatorTUI(
                profile_name=profile.name,
                vin=profile.get_vin(),
                interface=config.can_interface,
            )
            tui.register_ecus(profile.get_ecus())

        # Create simulator
        simulator = OBD2Simulator(config, profile, tui)

        # Start simulator
        simulator.start()

        if use_tui:
            # Run TUI in main thread (takes over terminal)
            try:
                tui.start()
            except KeyboardInterrupt:
                pass
        else:
            # Keep running until interrupted
            logger.info("Simulator running. Press Ctrl+C to stop.")
            while simulator.running:
                time.sleep(1.0)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Simulator error: {e}")
        raise
    finally:
        if 'simulator' in locals():
            simulator.stop()
        if tui:
            tui.stop()
            tui.print_summary()
