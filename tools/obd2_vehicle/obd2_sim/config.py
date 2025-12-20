"""
Configuration dataclasses and enums for OBD2 Vehicle Simulator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class UnsupportedPIDMode(Enum):
    """Behavior for unsupported PID requests."""
    NO_RESPONSE = "no-response"     # Do not respond (timeout)
    NRC_12 = "nrc-12"               # Return NRC 0x12 (subfunction not supported)
    NRC_11 = "nrc-11"               # Return NRC 0x11 (service not supported)


class ValueMode(Enum):
    """Value generation mode."""
    STATIC = "static"               # Replay captured values from profile
    RANDOM = "random"               # Random values within defined ranges (Phase 2)
    SCENARIO = "scenario"           # Scenario-based value sequences (Phase 3)


@dataclass
class SimulatorConfig:
    """
    Configuration for the OBD2 simulator.

    Attributes:
        profile_path: Path to vehicle profile JSON file
        interface: CAN interface name (e.g., 'vcan0', 'can0')
        bitrate: CAN bitrate in bps (ignored for virtual CAN)
        extended_frames: Enable 29-bit extended frame mode
        value_mode: Value generation mode
        unsupported_pid_mode: Behavior for unsupported PIDs
        broadcast_enabled: Enable broadcast message generation
        broadcast_ids: Specific broadcast IDs to enable (None = all)
        response_delay_ms: Override base response delay (None = from profile)
        inter_ecu_delay_ms: Override inter-ECU delay (None = from profile)
        jitter_ms: Random jitter to add to delays
        log_level: Logging level
        log_file: Log output file path (None = stdout)
        log_frames: Enable detailed frame logging
        daemon: Run as background daemon
        pid_file: PID file path for daemon mode
        stats_interval: Statistics output interval in seconds (0 = disabled)
    """
    # Required
    profile_path: str

    # CAN interface
    can_interface: str = "vcan0"
    can_interface_type: str = "socketcan"
    can_bitrate: int = 500000
    extended_frames: bool = False

    # Value generation
    value_mode: ValueMode = ValueMode.STATIC

    # Unsupported PID handling
    unsupported_pid_mode: UnsupportedPIDMode = UnsupportedPIDMode.NO_RESPONSE

    # Broadcast
    broadcast_enabled: bool = True
    broadcast_ids: Optional[List[int]] = None

    # Timing overrides
    response_delay_ms: float = 0.0
    inter_ecu_delay_ms: float = 0.0
    jitter_ms: float = 0.0

    # Logging
    log_level: str = "info"
    log_file: Optional[str] = None
    log_frames: bool = False

    # Daemon mode
    daemon: bool = False
    pid_file: Optional[str] = None

    # Statistics
    stats_interval: int = 0


def load_config_from_args(args) -> SimulatorConfig:
    """
    Create SimulatorConfig from parsed command line arguments.

    Args:
        args: Parsed argparse namespace

    Returns:
        SimulatorConfig instance
    """
    # Parse broadcast IDs if provided
    broadcast_ids = None
    if hasattr(args, 'broadcast_ids') and args.broadcast_ids:
        broadcast_ids = [int(x.strip(), 16) for x in args.broadcast_ids.split(',')]

    # Get interface type, handling both old and new arg names
    interface_type = getattr(args, 'interface_type', 'socketcan')

    return SimulatorConfig(
        profile_path=args.profile,
        can_interface=args.interface,
        can_interface_type=interface_type,
        can_bitrate=args.bitrate,
        extended_frames=args.extended,
        value_mode=ValueMode(args.value_mode),
        unsupported_pid_mode=UnsupportedPIDMode(args.unsupported_pid),
        broadcast_enabled=not args.disable_broadcast,
        broadcast_ids=broadcast_ids,
        response_delay_ms=args.response_delay if args.response_delay else 0.0,
        inter_ecu_delay_ms=args.inter_ecu_delay if args.inter_ecu_delay else 0.0,
        jitter_ms=args.jitter,
        log_level=args.log_level,
        log_file=args.log_file,
        log_frames=args.log_frames,
        daemon=args.daemon,
        pid_file=args.pid_file,
        stats_interval=args.stats_interval,
    )
