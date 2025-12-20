"""
Tests for Statistics module.
"""

import pytest
import time
from obd2_sim.stats import SimulatorStats, ECUStats, ServiceStats, StatsReporter


class TestECUStats:
    """Tests for ECUStats dataclass."""

    def test_initial_values(self):
        """Test initial ECU stats values."""
        stats = ECUStats(ecu_id=0x7E8)

        assert stats.ecu_id == 0x7E8
        assert stats.requests_received == 0
        assert stats.responses_sent == 0
        assert stats.multi_frame_responses == 0
        assert stats.errors == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = ECUStats(ecu_id=0x7E8)
        stats.requests_received = 10
        stats.responses_sent = 8

        d = stats.to_dict()

        assert d['ecu_id'] == '0x7E8'
        assert d['requests_received'] == 10
        assert d['responses_sent'] == 8


class TestServiceStats:
    """Tests for ServiceStats dataclass."""

    def test_initial_values(self):
        """Test initial service stats values."""
        stats = ServiceStats(service=0x01, pid=0x0C)

        assert stats.service == 0x01
        assert stats.pid == 0x0C
        assert stats.request_count == 0
        assert stats.response_count == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = ServiceStats(service=0x01, pid=0x0C)
        stats.request_count = 5

        d = stats.to_dict()

        assert d['service'] == '0x01'
        assert d['pid'] == '0x0C'
        assert d['request_count'] == 5

    def test_to_dict_no_pid(self):
        """Test conversion with no PID."""
        stats = ServiceStats(service=0x04, pid=None)

        d = stats.to_dict()

        assert d['pid'] == 'N/A'


class TestSimulatorStats:
    """Tests for SimulatorStats class."""

    def test_initial_state(self):
        """Test initial statistics state."""
        stats = SimulatorStats()

        assert stats.total_requests == 0
        assert stats.total_responses == 0
        assert stats.start_time is None

    def test_start(self):
        """Test start recording."""
        stats = SimulatorStats()
        stats.start()

        assert stats.start_time is not None
        assert stats.get_uptime() >= 0

    def test_record_request(self):
        """Test recording a request."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)

        assert stats.total_requests == 1
        assert stats.functional_requests == 1
        assert stats.physical_requests == 0
        assert 0x7E8 in stats.ecu_stats
        assert (0x01, 0x0C) in stats.service_stats

    def test_record_request_physical(self):
        """Test recording a physical request."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, False, 0x7E8)

        assert stats.functional_requests == 0
        assert stats.physical_requests == 1

    def test_record_response(self):
        """Test recording a response."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)
        stats.record_response(0x7E8, 0x01, 0x0C)

        assert stats.total_responses == 1
        assert stats.ecu_stats[0x7E8].responses_sent == 1

    def test_record_multi_frame_response(self):
        """Test recording a multi-frame response."""
        stats = SimulatorStats()
        stats.start()
        stats.record_response(0x7E8, 0x09, 0x02, is_multi_frame=True)

        assert stats.multi_frame_sessions == 1
        assert stats.ecu_stats[0x7E8].multi_frame_responses == 1

    def test_record_broadcast(self):
        """Test recording broadcast."""
        stats = SimulatorStats()
        stats.start()
        stats.record_broadcast()
        stats.record_broadcast()

        assert stats.total_broadcasts == 2

    def test_record_error(self):
        """Test recording error."""
        stats = SimulatorStats()
        stats.start()
        stats.record_error()

        assert stats.total_errors == 1

    def test_record_error_with_ecu(self):
        """Test recording error for specific ECU."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)
        stats.record_error(0x7E8)

        assert stats.total_errors == 1
        assert stats.ecu_stats[0x7E8].errors == 1

    def test_get_summary(self):
        """Test getting summary."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)
        stats.record_response(0x7E8, 0x01, 0x0C)

        summary = stats.get_summary()

        assert summary['total_requests'] == 1
        assert summary['total_responses'] == 1
        assert 'uptime_seconds' in summary
        assert 'requests_per_second' in summary

    def test_get_ecu_summary(self):
        """Test getting ECU summary."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)
        stats.record_request(0x01, 0x00, True, 0x7E9)

        ecu_summary = stats.get_ecu_summary()

        assert len(ecu_summary) == 2
        # Should be sorted by ECU ID
        assert ecu_summary[0]['ecu_id'] == '0x7E8'
        assert ecu_summary[1]['ecu_id'] == '0x7E9'

    def test_get_service_summary(self):
        """Test getting service summary."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)
        stats.record_request(0x01, 0x0D, True, 0x7E8)
        stats.record_request(0x09, 0x02, True, 0x7E8)

        service_summary = stats.get_service_summary()

        assert len(service_summary) == 3

    def test_format_report(self):
        """Test formatting statistics report."""
        stats = SimulatorStats()
        stats.start()
        stats.record_request(0x01, 0x0C, True, 0x7E8)
        stats.record_response(0x7E8, 0x01, 0x0C)

        report = stats.format_report()

        assert "OBD2 Simulator Statistics" in report
        assert "Total requests:" in report
        assert "Total responses:" in report

    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading

        stats = SimulatorStats()
        stats.start()

        def record_requests():
            for _ in range(100):
                stats.record_request(0x01, 0x0C, True, 0x7E8)

        threads = [threading.Thread(target=record_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.total_requests == 500


class TestStatsReporter:
    """Tests for StatsReporter class."""

    def test_start_stop(self):
        """Test starting and stopping reporter."""
        stats = SimulatorStats()
        reporter = StatsReporter(stats, interval_seconds=1.0)

        reporter.start()
        assert reporter._running

        reporter.stop()
        assert not reporter._running
