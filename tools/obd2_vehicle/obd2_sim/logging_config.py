"""
Logging Configuration for OBD2 Vehicle Simulator.

Provides structured logging with configurable levels, formats, and outputs.
"""

import logging
import sys
from typing import Optional


# Log format strings
VERBOSE_FORMAT = '%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s: %(message)s'
STANDARD_FORMAT = '%(asctime)s [%(levelname)-8s] %(message)s'
SIMPLE_FORMAT = '[%(levelname)s] %(message)s'

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(
    level: int = logging.INFO,
    verbose: bool = False,
    log_file: Optional[str] = None,
    quiet: bool = False,
) -> None:
    """
    Configure logging for the OBD2 simulator.

    Args:
        level: Base logging level
        verbose: Enable verbose output with timestamps and module names
        log_file: Optional file path for log output
        quiet: Suppress console output (only log to file if specified)
    """
    # Determine format
    if verbose:
        log_format = VERBOSE_FORMAT
    else:
        log_format = STANDARD_FORMAT

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=DATE_FORMAT)

    # Get root logger for package
    root_logger = logging.getLogger('obd2_sim')
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except IOError as e:
            print(f"Warning: Could not open log file {log_file}: {e}", file=sys.stderr)

    # Reduce noise from python-can library
    can_logger = logging.getLogger('can')
    can_logger.setLevel(logging.WARNING)


def get_log_level(verbosity: int) -> int:
    """
    Convert verbosity count to logging level.

    Args:
        verbosity: Number of -v flags (0-3)

    Returns:
        Logging level constant
    """
    levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    return levels.get(min(verbosity, 2), logging.DEBUG)


class FrameLogger:
    """
    Specialized logger for CAN frame tracing.

    Provides formatted output for CAN frames with optional
    hex dump and interpretation.
    """

    def __init__(self, enabled: bool = False):
        """
        Initialize frame logger.

        Args:
            enabled: Enable frame logging
        """
        self.enabled = enabled
        self.logger = logging.getLogger('obd2_sim.frames')

    def log_rx(self, can_id: int, data: bytes, extended: bool = False) -> None:
        """Log received frame."""
        if not self.enabled:
            return

        id_str = f"0x{can_id:08X}" if extended else f"0x{can_id:03X}"
        data_str = data.hex(' ').upper() if data else "(empty)"
        self.logger.debug(f"RX {id_str} [{len(data)}] {data_str}")

    def log_tx(self, can_id: int, data: bytes, extended: bool = False) -> None:
        """Log transmitted frame."""
        if not self.enabled:
            return

        id_str = f"0x{can_id:08X}" if extended else f"0x{can_id:03X}"
        data_str = data.hex(' ').upper() if data else "(empty)"
        self.logger.debug(f"TX {id_str} [{len(data)}] {data_str}")

    def log_request(self, service: int, pid: Optional[int], functional: bool) -> None:
        """Log OBD2 request."""
        if not self.enabled:
            return

        req_type = "FUNC" if functional else "PHYS"
        pid_str = f"PID 0x{pid:02X}" if pid is not None else "no PID"
        self.logger.info(f"REQ [{req_type}] Service 0x{service:02X} {pid_str}")

    def log_response(self, ecu_id: int, service: int, pid: Optional[int], data: bytes) -> None:
        """Log OBD2 response."""
        if not self.enabled:
            return

        pid_str = f"PID 0x{pid:02X}" if pid is not None else ""
        data_str = data.hex(' ').upper() if data else ""
        self.logger.info(f"RSP [0x{ecu_id:03X}] Service 0x{service:02X} {pid_str} {data_str}")
