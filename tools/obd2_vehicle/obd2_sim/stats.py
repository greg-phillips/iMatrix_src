"""
Statistics Module for OBD2 Vehicle Simulator.

Tracks and reports simulation statistics including request counts,
response times, error rates, and per-ECU metrics.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ECUStats:
    """Statistics for a single ECU."""
    ecu_id: int
    requests_received: int = 0
    responses_sent: int = 0
    multi_frame_responses: int = 0
    unsupported_requests: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'ecu_id': f"0x{self.ecu_id:03X}",
            'requests_received': self.requests_received,
            'responses_sent': self.responses_sent,
            'multi_frame_responses': self.multi_frame_responses,
            'unsupported_requests': self.unsupported_requests,
            'errors': self.errors,
        }


@dataclass
class ServiceStats:
    """Statistics for a service/PID combination."""
    service: int
    pid: Optional[int]
    request_count: int = 0
    response_count: int = 0
    last_request_time: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        pid_str = f"0x{self.pid:02X}" if self.pid is not None else "N/A"
        return {
            'service': f"0x{self.service:02X}",
            'pid': pid_str,
            'request_count': self.request_count,
            'response_count': self.response_count,
        }


@dataclass
class SimulatorStats:
    """
    Comprehensive simulator statistics.

    Tracks global, per-ECU, and per-service metrics.
    """
    # Timing
    start_time: Optional[float] = None
    last_activity_time: Optional[float] = None

    # Global counters
    total_requests: int = 0
    total_responses: int = 0
    total_broadcasts: int = 0
    total_errors: int = 0
    functional_requests: int = 0
    physical_requests: int = 0
    flow_control_received: int = 0
    multi_frame_sessions: int = 0

    # Per-ECU stats
    ecu_stats: Dict[int, ECUStats] = field(default_factory=dict)

    # Per-service stats
    service_stats: Dict[tuple, ServiceStats] = field(default_factory=dict)

    # Lock for thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def start(self) -> None:
        """Mark simulator start time."""
        self.start_time = time.time()
        self.last_activity_time = self.start_time

    def record_request(self, service: int, pid: Optional[int],
                       is_functional: bool, ecu_id: int) -> None:
        """
        Record an OBD2 request.

        Args:
            service: Service ID
            pid: PID number (or None)
            is_functional: True for functional request
            ecu_id: Target ECU ID
        """
        with self._lock:
            self.total_requests += 1
            self.last_activity_time = time.time()

            if is_functional:
                self.functional_requests += 1
            else:
                self.physical_requests += 1

            # Per-ECU stats
            if ecu_id not in self.ecu_stats:
                self.ecu_stats[ecu_id] = ECUStats(ecu_id=ecu_id)
            self.ecu_stats[ecu_id].requests_received += 1

            # Per-service stats
            key = (service, pid)
            if key not in self.service_stats:
                self.service_stats[key] = ServiceStats(service=service, pid=pid)
            self.service_stats[key].request_count += 1
            self.service_stats[key].last_request_time = time.time()

    def record_response(self, ecu_id: int, service: int, pid: Optional[int],
                        is_multi_frame: bool = False) -> None:
        """
        Record an OBD2 response.

        Args:
            ecu_id: Responding ECU ID
            service: Service ID
            pid: PID number (or None)
            is_multi_frame: True for multi-frame response
        """
        with self._lock:
            self.total_responses += 1

            if is_multi_frame:
                self.multi_frame_sessions += 1

            # Per-ECU stats
            if ecu_id not in self.ecu_stats:
                self.ecu_stats[ecu_id] = ECUStats(ecu_id=ecu_id)
            self.ecu_stats[ecu_id].responses_sent += 1
            if is_multi_frame:
                self.ecu_stats[ecu_id].multi_frame_responses += 1

            # Per-service stats
            key = (service, pid)
            if key in self.service_stats:
                self.service_stats[key].response_count += 1

    def record_unsupported(self, ecu_id: int) -> None:
        """Record an unsupported request."""
        with self._lock:
            if ecu_id not in self.ecu_stats:
                self.ecu_stats[ecu_id] = ECUStats(ecu_id=ecu_id)
            self.ecu_stats[ecu_id].unsupported_requests += 1

    def record_broadcast(self) -> None:
        """Record a broadcast message sent."""
        with self._lock:
            self.total_broadcasts += 1

    def record_flow_control(self) -> None:
        """Record a flow control frame received."""
        with self._lock:
            self.flow_control_received += 1

    def record_error(self, ecu_id: Optional[int] = None) -> None:
        """Record an error."""
        with self._lock:
            self.total_errors += 1
            if ecu_id and ecu_id in self.ecu_stats:
                self.ecu_stats[ecu_id].errors += 1

    def get_uptime(self) -> float:
        """Get simulator uptime in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def get_summary(self) -> dict:
        """
        Get summary statistics.

        Returns:
            Dictionary of statistics
        """
        with self._lock:
            uptime = self.get_uptime()
            req_rate = self.total_requests / uptime if uptime > 0 else 0

            return {
                'uptime_seconds': round(uptime, 1),
                'total_requests': self.total_requests,
                'total_responses': self.total_responses,
                'total_broadcasts': self.total_broadcasts,
                'total_errors': self.total_errors,
                'requests_per_second': round(req_rate, 2),
                'functional_requests': self.functional_requests,
                'physical_requests': self.physical_requests,
                'multi_frame_sessions': self.multi_frame_sessions,
                'flow_control_received': self.flow_control_received,
                'ecu_count': len(self.ecu_stats),
                'service_count': len(self.service_stats),
            }

    def get_ecu_summary(self) -> List[dict]:
        """Get per-ECU statistics."""
        with self._lock:
            return [stats.to_dict() for stats in sorted(
                self.ecu_stats.values(), key=lambda s: s.ecu_id
            )]

    def get_service_summary(self) -> List[dict]:
        """Get per-service statistics."""
        with self._lock:
            return [stats.to_dict() for stats in sorted(
                self.service_stats.values(),
                key=lambda s: (s.service, s.pid or 0)
            )]

    def format_report(self) -> str:
        """
        Format a human-readable statistics report.

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 50)
        lines.append("OBD2 Simulator Statistics Report")
        lines.append("=" * 50)

        summary = self.get_summary()
        lines.append(f"Uptime: {summary['uptime_seconds']:.1f} seconds")
        lines.append(f"Request rate: {summary['requests_per_second']:.2f} req/sec")
        lines.append("")

        lines.append("Global Counters:")
        lines.append(f"  Total requests:     {summary['total_requests']}")
        lines.append(f"    Functional:       {summary['functional_requests']}")
        lines.append(f"    Physical:         {summary['physical_requests']}")
        lines.append(f"  Total responses:    {summary['total_responses']}")
        lines.append(f"  Multi-frame:        {summary['multi_frame_sessions']}")
        lines.append(f"  Broadcasts:         {summary['total_broadcasts']}")
        lines.append(f"  Errors:             {summary['total_errors']}")
        lines.append("")

        ecu_stats = self.get_ecu_summary()
        if ecu_stats:
            lines.append("Per-ECU Statistics:")
            for ecu in ecu_stats:
                lines.append(f"  {ecu['ecu_id']}:")
                lines.append(f"    Requests:  {ecu['requests_received']}")
                lines.append(f"    Responses: {ecu['responses_sent']}")
                lines.append(f"    Multi-frame: {ecu['multi_frame_responses']}")
            lines.append("")

        service_stats = self.get_service_summary()
        if service_stats:
            lines.append("Most Requested Services/PIDs:")
            sorted_services = sorted(service_stats,
                                    key=lambda s: s['request_count'],
                                    reverse=True)[:10]
            for svc in sorted_services:
                lines.append(f"  {svc['service']} {svc['pid']}: "
                           f"{svc['request_count']} requests")

        lines.append("=" * 50)
        return "\n".join(lines)


class StatsReporter:
    """
    Periodic statistics reporter.

    Reports statistics at configurable intervals.
    """

    def __init__(self, stats: SimulatorStats, interval_seconds: float = 60.0):
        """
        Initialize reporter.

        Args:
            stats: SimulatorStats instance
            interval_seconds: Reporting interval
        """
        self.stats = stats
        self.interval = interval_seconds
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def start(self) -> None:
        """Start periodic reporting."""
        self._running = True
        self._schedule_report()

    def stop(self) -> None:
        """Stop periodic reporting."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_report(self) -> None:
        """Schedule next report."""
        if not self._running:
            return

        self._timer = threading.Timer(self.interval, self._report)
        self._timer.daemon = True
        self._timer.start()

    def _report(self) -> None:
        """Generate and log report."""
        if not self._running:
            return

        summary = self.stats.get_summary()
        logger.info(f"Stats: {summary['total_requests']} requests, "
                   f"{summary['total_responses']} responses, "
                   f"{summary['requests_per_second']:.1f} req/sec")

        self._schedule_report()
