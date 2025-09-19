#!/usr/bin/env python3
"""
PCAN TRC Logger - CAN Bus Traffic Logger for PEAK-System PCAN Devices

This script logs CAN bus traffic from PCAN-USB interfaces to TRC format files.
Supports both classic CAN and CAN-FD (with additional configuration).

Author: iMatrix Systems
Version: 1.1.0
License: MIT
"""

import argparse
import datetime as dt
import sys
import signal
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import can
from can.io import TRCWriter


# Configure logging
logger = logging.getLogger(__name__)

# Valid PCAN channels
VALID_CHANNELS = [
    "PCAN_USBBUS1", "PCAN_USBBUS2", "PCAN_USBBUS3", "PCAN_USBBUS4",
    "PCAN_USBBUS5", "PCAN_USBBUS6", "PCAN_USBBUS7", "PCAN_USBBUS8",
    "PCAN_PCIBUS1", "PCAN_PCIBUS2", "PCAN_LANBUS1", "PCAN_LANBUS2"
]

# Common CAN bitrates
COMMON_BITRATES = [
    10000, 20000, 50000, 100000, 125000, 
    250000, 500000, 800000, 1000000
]


class Statistics:
    """Track logging statistics."""
    def __init__(self):
        self.frame_count = 0
        self.error_count = 0
        self.start_time = dt.datetime.now()
        self.bytes_logged = 0
    
    def update(self, frame_size: int = 0):
        self.frame_count += 1
        self.bytes_logged += frame_size
    
    def get_summary(self) -> str:
        duration = (dt.datetime.now() - self.start_time).total_seconds()
        rate = self.frame_count / duration if duration > 0 else 0
        return (f"Frames: {self.frame_count}, Errors: {self.error_count}, "
                f"Duration: {duration:.1f}s, Rate: {rate:.1f} fps")


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command-line arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Raises:
        ValueError: If arguments are invalid
    """
    # Validate bitrate
    if args.bitrate <= 0 or args.bitrate > 1000000:
        raise ValueError(f"Invalid bitrate: {args.bitrate}. Must be between 1 and 1000000.")
    
    if args.bitrate not in COMMON_BITRATES:
        logger.warning(f"Non-standard bitrate {args.bitrate}. Common rates: {COMMON_BITRATES}")
    
    # Validate channel
    if args.channel not in VALID_CHANNELS and args.device_id is None:
        logger.warning(f"Non-standard channel '{args.channel}'. Common channels: {VALID_CHANNELS[:4]}")
    
    # Validate output file
    if args.outfile:
        outpath = Path(args.outfile)
        if outpath.exists() and not args.append:
            logger.warning(f"Output file {args.outfile} exists and will be overwritten.")


def create_bus(args: argparse.Namespace) -> can.Bus:
    """
    Create a python-can Bus for PCAN device.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Configured CAN bus instance
        
    Raises:
        Exception: If bus creation fails
    """
    bus_kwargs: Dict[str, Any] = {
        "interface": "pcan",
        "bitrate": args.bitrate,
        "receive_own_messages": args.receive_own
    }
    
    # Handle device ID vs channel selection
    if args.device_id is not None:
        bus_kwargs["device_id"] = args.device_id
        logger.info(f"Using device_id={args.device_id}")
    else:
        bus_kwargs["channel"] = args.channel
        logger.info(f"Using channel={args.channel}")
    
    # Handle CAN-FD configuration
    if args.fd:
        logger.warning("CAN-FD mode requested but not fully implemented. "
                      "See docs/CAN_FD_SETUP.md for configuration.")
        # TODO: Add proper FD timing parameters
        # bus_kwargs["fd"] = True
        # bus_kwargs["f_clock"] = args.f_clock
        # bus_kwargs["nom_brp"] = args.nom_brp
        # bus_kwargs["data_brp"] = args.data_brp
    
    return can.Bus(**bus_kwargs)


def main():
    """Main entry point for the PCAN TRC logger."""
    parser = argparse.ArgumentParser(
        description="Log CAN traffic from PCAN interfaces to TRC format files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Log at 500kbps for 60 seconds
  %(prog)s --bitrate 500000 --duration 60
  
  # Log to specific file with append mode
  %(prog)s --bitrate 250000 --outfile session.trc --append
  
  # Use specific device by ID
  %(prog)s --bitrate 500000 --device-id 0x51
"""
    )
    parser.add_argument(
        "--bitrate",
        type=int,
        required=True,
        help="Classic CAN bitrate in bit/s (e.g. 500000).",
    )
    parser.add_argument(
        "--channel",
        default="PCAN_USBBUS1",
        help="PCAN channel name (PCAN_USBBUS1, PCAN_USBBUS2, ...).",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=None,
        help="Optional PCAN device ID to pick a specific adapter (overrides --channel).",
    )
    parser.add_argument(
        "--outfile",
        default=None,
        help="Output .trc path. Default: ./pcan_<YYYYmmdd_HHMMSS>.trc",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the output file instead of truncating.",
    )
    parser.add_argument(
        "--receive-own",
        action="store_true",
        help="Also log frames transmitted by this interface.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG).",
    )
    parser.add_argument(
        "--stats-interval",
        type=float,
        default=10.0,
        help="Statistics display interval in seconds (0 to disable).",
    )
    parser.add_argument(
        "--channel-number",
        type=int,
        default=1,
        help="Channel number written into TRC header (integer). Default: 1.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional logging duration in seconds (otherwise runs until Ctrl+C).",
    )

    # (Advanced) CAN-FD timing options:
    # python-can’s PCAN backend supports CAN-FD, but timing must be provided explicitly.
    # If you truly need FD, consider switching this script to configure fd+timing per docs.
    parser.add_argument(
        "--fd",
        action="store_true",
        help="(Advanced) Enable CAN-FD mode (requires adding timing params in code).",
    )

    args = parser.parse_args()
    
    # Configure logging based on verbosity
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate arguments
    try:
        validate_arguments(args)
    except ValueError as e:
        parser.error(str(e))
    
    # Build output filename if not specified
    if args.outfile is None:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.outfile = f"pcan_{stamp}.trc"
        logger.info(f"Using auto-generated filename: {args.outfile}")

    # Statistics tracking
    stats = Statistics()
    
    # Allow graceful shutdown on Ctrl+C
    stop = False

    def _handle_sigint(signum, frame):
        nonlocal stop
        stop = True
        logger.info("Received interrupt signal, shutting down gracefully...")

    signal.signal(signal.SIGINT, _handle_sigint)

    # Create CAN bus
    try:
        bus = create_bus(args)
    except Exception as e:
        logger.error(f"Failed to open PCAN bus: {e}")
        sys.exit(2)

    # Display startup information
    channel_info = args.channel if args.device_id is None else f"device_id={args.device_id}"
    print(f"\n{'='*60}")
    print(f"PCAN TRC Logger v1.1.0")
    print(f"{'='*60}")
    print(f"Channel:  {channel_info}")
    print(f"Bitrate:  {args.bitrate} bit/s")
    print(f"Output:   {args.outfile} {'(append)' if args.append else '(new)'}")
    print(f"Duration: {args.duration if args.duration else 'Until Ctrl+C'}")
    print(f"{'='*60}\n")

    # Set up TRC writer and notifier
    writer = TRCWriter(args.outfile, channel=args.channel_number)
    notifier = can.Notifier(bus, [writer], timeout=1.0)

    # Track timing
    start_time = dt.datetime.now()
    last_stats_time = start_time
    
    try:
        while not stop:
            # Check duration limit
            if args.duration is not None:
                elapsed = (dt.datetime.now() - start_time).total_seconds()
                if elapsed >= args.duration:
                    logger.info(f"Duration limit reached ({args.duration}s)")
                    break
            
            # Display statistics periodically
            if args.stats_interval > 0:
                now = dt.datetime.now()
                if (now - last_stats_time).total_seconds() >= args.stats_interval:
                    print(f"[Stats] {stats.get_summary()}")
                    last_stats_time = now
            
            # Brief sleep to yield CPU
            can.util.sleep(0.05)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error during logging: {e}")
        stats.error_count += 1
    finally:
        # Clean shutdown
        logger.debug("Shutting down notifier...")
        try:
            notifier.stop()
        except Exception as e:
            logger.error(f"Error stopping notifier: {e}")
        
        logger.debug("Closing TRC writer...")
        try:
            writer.stop()
        except Exception as e:
            logger.error(f"Error stopping writer: {e}")
        
        logger.debug("Shutting down CAN bus...")
        try:
            bus.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down bus: {e}")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"Logging completed!")
    print(f"Final statistics: {stats.get_summary()}")
    print(f"Output file: {args.outfile}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
