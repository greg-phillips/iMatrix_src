#!/usr/bin/env python3
"""
Command Line Interface for OBD2 Vehicle Simulator.
"""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from . import __version__
from .config import SimulatorConfig, UnsupportedPIDMode, ValueMode, load_config_from_args
from .profile import VehicleProfile
from .simulator import OBD2Simulator
from .logging_config import setup_logging


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog="obd2_sim",
        description="OBD2 Vehicle Simulator for bench testing telematics gateways",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with virtual CAN
  obd2_sim --profile profiles/BMW_X3_2019.json --interface vcan0

  # With extended frames and custom timing
  obd2_sim --profile profiles/BMW_X3_2019.json --extended --response-delay 10

  # Disable broadcast, use NRC for unsupported PIDs
  obd2_sim --profile profiles/BMW_X3_2019.json --disable-broadcast --unsupported-pid nrc-12

  # Debug mode with frame logging
  obd2_sim --profile profiles/BMW_X3_2019.json --log-level debug --log-frames

  # Production daemon mode
  obd2_sim --profile profiles/BMW_X3_2019.json --daemon --pid-file /var/run/obd2_sim.pid
"""
    )

    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    # Required arguments
    parser.add_argument(
        "--profile", "-p",
        required=True,
        help="Path to vehicle profile JSON file"
    )

    # CAN interface options
    can_group = parser.add_argument_group("CAN Interface Options")
    can_group.add_argument(
        "--interface", "-i",
        default="vcan0",
        help="CAN interface name (default: vcan0)"
    )
    can_group.add_argument(
        "--interface-type",
        default="socketcan",
        help="CAN interface type (default: socketcan, use 'virtual' for testing)"
    )
    can_group.add_argument(
        "--bitrate", "-b",
        type=int,
        default=500000,
        help="CAN bitrate in bps (default: 500000, ignored for vcan)"
    )
    can_group.add_argument(
        "--extended",
        action="store_true",
        help="Enable 29-bit extended frame mode"
    )

    # Value mode options
    value_group = parser.add_argument_group("Value Mode Options")
    value_group.add_argument(
        "--value-mode",
        choices=["static", "random", "scenario"],
        default="static",
        help="Value generation mode (default: static)"
    )
    value_group.add_argument(
        "--unsupported-pid",
        choices=["no-response", "nrc-12", "nrc-11"],
        default="no-response",
        help="Behavior for unsupported PIDs (default: no-response)"
    )

    # Broadcast options
    broadcast_group = parser.add_argument_group("Broadcast Options")
    broadcast_group.add_argument(
        "--disable-broadcast",
        action="store_true",
        help="Disable all broadcast messages"
    )
    broadcast_group.add_argument(
        "--broadcast-ids",
        help="Comma-separated list of broadcast IDs to enable (hex, e.g., '003C,0130')"
    )

    # Timing options
    timing_group = parser.add_argument_group("Timing Options")
    timing_group.add_argument(
        "--response-delay",
        type=float,
        default=None,
        help="Override base response delay in milliseconds"
    )
    timing_group.add_argument(
        "--inter-ecu-delay",
        type=float,
        default=None,
        help="Override delay between ECU responses in milliseconds"
    )
    timing_group.add_argument(
        "--jitter",
        type=float,
        default=0.0,
        help="Random jitter to add to delays in milliseconds (default: 0)"
    )

    # Logging options
    log_group = parser.add_argument_group("Logging Options")
    log_group.add_argument(
        "--log-level",
        choices=["debug", "info", "warn", "error"],
        default="info",
        help="Log level (default: info)"
    )
    log_group.add_argument(
        "--log-file",
        default=None,
        help="Log output file (default: stdout)"
    )
    log_group.add_argument(
        "--log-frames",
        action="store_true",
        help="Log all CAN frames (verbose)"
    )

    # Display options
    display_group = parser.add_argument_group("Display Options")
    display_group.add_argument(
        "--tui",
        action="store_true",
        help="Enable terminal UI with live transaction display"
    )
    display_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode - minimal output"
    )

    # Operational options
    ops_group = parser.add_argument_group("Operational Options")
    ops_group.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon"
    )
    ops_group.add_argument(
        "--pid-file",
        default=None,
        help="Write PID to file (daemon mode)"
    )
    ops_group.add_argument(
        "--stats-interval",
        type=int,
        default=0,
        help="Print statistics every N seconds (0 = disabled)"
    )

    return parser


def validate_args(args) -> bool:
    """
    Validate command line arguments.

    Args:
        args: Parsed argparse namespace

    Returns:
        True if valid, False otherwise
    """
    # Check profile file exists
    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"Error: Profile file not found: {args.profile}", file=sys.stderr)
        return False

    if not profile_path.suffix == ".json":
        print(f"Warning: Profile file does not have .json extension: {args.profile}",
              file=sys.stderr)

    # Validate broadcast IDs format if provided
    if args.broadcast_ids:
        try:
            for id_str in args.broadcast_ids.split(','):
                int(id_str.strip(), 16)
        except ValueError:
            print(f"Error: Invalid broadcast ID format: {args.broadcast_ids}",
                  file=sys.stderr)
            print("  Expected: comma-separated hex values (e.g., '003C,0130')",
                  file=sys.stderr)
            return False

    # Validate timing values
    if args.response_delay is not None and args.response_delay < 0:
        print("Error: response-delay must be non-negative", file=sys.stderr)
        return False

    if args.inter_ecu_delay is not None and args.inter_ecu_delay < 0:
        print("Error: inter-ecu-delay must be non-negative", file=sys.stderr)
        return False

    if args.jitter < 0:
        print("Error: jitter must be non-negative", file=sys.stderr)
        return False

    # Daemon mode requires pid-file to be recommended
    if args.daemon and not args.pid_file:
        print("Warning: Running in daemon mode without --pid-file", file=sys.stderr)

    return True


def main() -> int:
    """
    Main entry point for the OBD2 simulator.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Validate arguments
    if not validate_args(args):
        return 1

    # Create configuration
    config = load_config_from_args(args)

    # Setup logging (suppress for TUI mode or quiet mode)
    if args.tui:
        log_level = logging.WARNING  # Minimal logging in TUI mode
    elif args.quiet:
        log_level = logging.ERROR
    else:
        log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    setup_logging(
        level=log_level,
        verbose=(log_level == logging.DEBUG),
        log_file=config.log_file,
        quiet=args.tui or args.quiet,
    )
    logger = logging.getLogger('obd2_sim')

    # Print startup info if not in TUI mode
    if not args.tui:
        logger.info(f"OBD2 Vehicle Simulator v{__version__}")
        logger.info(f"Profile: {config.profile_path}")
        logger.info(f"Interface: {config.can_interface}")

    # Load vehicle profile
    try:
        profile = VehicleProfile(config.profile_path)
        if not args.tui:
            logger.info(f"Loaded profile: {profile.profile_name}")
            logger.info(f"  VIN: {profile.get_vin()}")
            logger.info(f"  ECUs: {len(profile.get_ecus())}")
            logger.info(f"  Operating Mode: {profile.get_operating_mode()}")
    except Exception as e:
        logger.error(f"Failed to load profile: {e}")
        return 1

    # TUI setup
    tui = None
    if args.tui:
        try:
            from .visualization.tui import SimulatorTUI
            tui = SimulatorTUI(
                profile_name=profile.profile_name,
                vin=profile.get_vin(),
                interface=config.can_interface,
            )
            tui.register_ecus(profile.get_ecus())
        except ImportError as e:
            logger.error(f"TUI requires 'rich' library: {e}")
            logger.error("Install with: pip install rich")
            return 1

    # Create simulator
    try:
        simulator = OBD2Simulator(config, profile, tui)
    except Exception as e:
        logger.error(f"Failed to create simulator: {e}")
        return 1

    # Setup signal handlers
    def signal_handler(signum, frame):
        if not args.tui:
            logger.info(f"Received signal {signum}, shutting down...")
        simulator.stop()
        if tui:
            tui.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Write PID file if in daemon mode
    if config.pid_file:
        try:
            with open(config.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.debug(f"Wrote PID file: {config.pid_file}")
        except Exception as e:
            logger.warning(f"Failed to write PID file: {e}")

    # Start simulator
    try:
        if not args.tui:
            logger.info("Starting simulator...")

        simulator.start()

        if args.tui:
            # Run TUI in main thread (takes over terminal)
            tui.start()
        else:
            # Keep running until interrupted
            logger.info("Simulator running. Press Ctrl+C to stop.")
            while simulator.running:
                import time
                time.sleep(0.5)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Simulator error: {e}")
        return 1
    finally:
        simulator.stop()
        if tui:
            tui.stop()
            tui.print_summary()

        # Clean up PID file
        if config.pid_file:
            try:
                os.remove(config.pid_file)
            except Exception:
                pass

        if not args.tui:
            logger.info("Simulator stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
