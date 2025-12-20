"""
Tests for Request Matcher module.
"""

import pytest
from obd2_sim.request import RequestMatcher, OBD2Request
from obd2_sim.profile import ECUConfig
from obd2_sim.config import SimulatorConfig


class TestOBD2Request:
    """Tests for OBD2Request dataclass."""

    def test_functional_request(self):
        """Test functional request properties."""
        req = OBD2Request(
            service=0x01,
            pid=0x0C,
            data=b'',
            is_functional=True,
            target_ecu_index=None,
            raw_frame=bytes([0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00]),
            can_id=0x7DF,
            extended=False
        )

        assert req.is_functional
        assert not req.is_physical
        assert req.service == 0x01
        assert req.pid == 0x0C

    def test_physical_request(self):
        """Test physical request properties."""
        req = OBD2Request(
            service=0x01,
            pid=0x0C,
            data=b'',
            is_functional=False,
            target_ecu_index=0,
            raw_frame=bytes([0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00]),
            can_id=0x7E0,
            extended=False
        )

        assert not req.is_functional
        assert req.is_physical
        assert req.target_ecu_index == 0


class TestRequestMatcher:
    """Tests for RequestMatcher class."""

    @pytest.fixture
    def ecus(self):
        """Sample ECU list."""
        return [
            ECUConfig(
                name="ECM",
                response_id=0x7E8,
                physical_request_id=0x7E0,
                index=0,
                padding_byte=0x00,
                response_delay_ms=8.0
            ),
            ECUConfig(
                name="TCM",
                response_id=0x7E9,
                physical_request_id=0x7E1,
                index=1,
                padding_byte=0xAA,
                response_delay_ms=8.0
            )
        ]

    @pytest.fixture
    def config(self):
        """Sample configuration."""
        return SimulatorConfig(
            profile_path="test.json",
            can_interface="vcan0"
        )

    @pytest.fixture
    def matcher(self, config, ecus):
        """Request matcher instance."""
        return RequestMatcher(config, ecus)

    def test_is_obd2_request_functional(self, matcher, mock_message_factory):
        """Test functional request detection."""
        msg = mock_message_factory(0x7DF, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert matcher.is_obd2_request(msg)

    def test_is_obd2_request_physical(self, matcher, mock_message_factory):
        """Test physical request detection."""
        msg = mock_message_factory(0x7E0, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert matcher.is_obd2_request(msg)

    def test_is_not_obd2_request(self, matcher, mock_message_factory):
        """Test non-OBD2 message detection."""
        msg = mock_message_factory(0x100, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert not matcher.is_obd2_request(msg)

    def test_parse_single_frame_functional(self, matcher, mock_message_factory):
        """Test parsing functional single-frame request."""
        # Service 01, PID 0C
        msg = mock_message_factory(0x7DF, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        request = matcher.parse_request(msg)

        assert request is not None
        assert request.service == 0x01
        assert request.pid == 0x0C
        assert request.is_functional
        assert request.target_ecu_index is None

    def test_parse_single_frame_physical(self, matcher, mock_message_factory):
        """Test parsing physical single-frame request."""
        msg = mock_message_factory(0x7E0, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        request = matcher.parse_request(msg)

        assert request is not None
        assert request.service == 0x01
        assert request.pid == 0x0C
        assert not request.is_functional
        assert request.target_ecu_index == 0

    def test_parse_service_only_request(self, matcher, mock_message_factory):
        """Test parsing service-only request (no PID)."""
        # Service 04 (clear DTCs) has no PID
        msg = mock_message_factory(0x7DF, [0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        request = matcher.parse_request(msg)

        assert request is not None
        assert request.service == 0x04
        assert request.pid is None

    def test_parse_invalid_length(self, matcher, mock_message_factory):
        """Test parsing frame with invalid length."""
        # Length 0 is invalid
        msg = mock_message_factory(0x7DF, [0x00, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        request = matcher.parse_request(msg)

        assert request is None

    def test_get_target_ecus_functional(self, matcher, ecus, mock_message_factory):
        """Test target ECUs for functional request."""
        msg = mock_message_factory(0x7DF, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        request = matcher.parse_request(msg)

        targets = matcher.get_target_ecus(request)

        # Functional request should target all ECUs
        assert len(targets) == 2

    def test_get_target_ecus_physical(self, matcher, ecus, mock_message_factory):
        """Test target ECUs for physical request."""
        msg = mock_message_factory(0x7E0, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        request = matcher.parse_request(msg)

        targets = matcher.get_target_ecus(request)

        # Physical request should target only ECU 0
        assert len(targets) == 1
        assert targets[0].index == 0

    def test_is_flow_control(self, matcher, mock_message_factory):
        """Test flow control frame detection."""
        # FC from tester at physical request ID
        fc_msg = mock_message_factory(0x7E0, [0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert matcher.is_flow_control(fc_msg)

        # Regular request is not FC
        req_msg = mock_message_factory(0x7E0, [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert not matcher.is_flow_control(req_msg)

    def test_parse_flow_control(self, matcher, mock_message_factory):
        """Test flow control parsing."""
        # FC: CTS, BS=0, STmin=10ms
        fc_msg = mock_message_factory(0x7E0, [0x30, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00])
        fc_params = matcher.parse_flow_control(fc_msg)

        assert fc_params is not None
        assert fc_params['flow_status'] == 0  # CTS
        assert fc_params['block_size'] == 0
        assert fc_params['separation_time_ms'] == 10.0
