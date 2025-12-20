"""
Tests for Response Generator module.
"""

import pytest
from obd2_sim.response import ResponseGenerator
from obd2_sim.value_provider import StaticValueProvider
from obd2_sim.profile import VehicleProfile, ECUConfig
from obd2_sim.request import OBD2Request
from obd2_sim.config import SimulatorConfig, UnsupportedPIDMode


class TestResponseGenerator:
    """Tests for ResponseGenerator class."""

    @pytest.fixture
    def generator(self, sample_profile_path):
        """Create response generator with sample profile."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)
        config = SimulatorConfig(
            profile_path=sample_profile_path,
            can_interface="vcan0"
        )
        return ResponseGenerator(profile, provider, config)

    @pytest.fixture
    def generator_nrc12(self, sample_profile_path):
        """Create response generator with NRC-12 mode."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)
        config = SimulatorConfig(
            profile_path=sample_profile_path,
            can_interface="vcan0",
            unsupported_pid_mode=UnsupportedPIDMode.NRC_12
        )
        return ResponseGenerator(profile, provider, config)

    @pytest.fixture
    def ecu_ecm(self):
        """Sample ECM ECU."""
        return ECUConfig(
            name="ECM",
            response_id=0x7E8,
            physical_request_id=0x7E0,
            index=0,
            padding_byte=0x00,
            response_delay_ms=8.0
        )

    @pytest.fixture
    def request_pid_0c(self):
        """Sample request for PID 0x0C."""
        return OBD2Request(
            service=0x01,
            pid=0x0C,
            data=b'',
            is_functional=True,
            target_ecu_index=None,
            raw_frame=bytes([0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00]),
            can_id=0x7DF,
            extended=False
        )

    @pytest.fixture
    def request_unsupported(self):
        """Sample request for unsupported PID."""
        return OBD2Request(
            service=0x01,
            pid=0xFF,
            data=b'',
            is_functional=True,
            target_ecu_index=None,
            raw_frame=bytes([0x02, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]),
            can_id=0x7DF,
            extended=False
        )

    @pytest.fixture
    def request_vin(self):
        """Sample request for VIN."""
        return OBD2Request(
            service=0x09,
            pid=0x02,
            data=b'',
            is_functional=True,
            target_ecu_index=None,
            raw_frame=bytes([0x02, 0x09, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]),
            can_id=0x7DF,
            extended=False
        )

    def test_generate_response_single_frame(self, generator, request_pid_0c, ecu_ecm):
        """Test generating single-frame response."""
        response = generator.generate_response(request_pid_0c, ecu_ecm)

        assert response is not None
        assert isinstance(response, bytes)

    def test_generate_response_unsupported_no_response(self, generator, request_unsupported, ecu_ecm):
        """Test unsupported PID with no-response mode."""
        response = generator.generate_response(request_unsupported, ecu_ecm)

        assert response is None

    def test_generate_response_unsupported_nrc12(self, generator_nrc12, request_unsupported, ecu_ecm):
        """Test unsupported PID with NRC-12 mode."""
        response = generator_nrc12.generate_response(request_unsupported, ecu_ecm)

        assert response is not None
        assert isinstance(response, bytes)
        assert len(response) == 8
        # Check NRC format: [03, 7F, Service, NRC, ...]
        assert response[0] == 0x03
        assert response[1] == 0x7F
        assert response[2] == 0x01  # Service
        assert response[3] == 0x12  # NRC

    def test_is_multi_frame_response(self, generator, request_vin, ecu_ecm):
        """Test multi-frame response detection."""
        assert generator.is_multi_frame_response(request_vin, ecu_ecm) is True

    def test_is_not_multi_frame_response(self, generator, request_pid_0c, ecu_ecm):
        """Test single-frame is not detected as multi-frame."""
        assert generator.is_multi_frame_response(request_pid_0c, ecu_ecm) is False

    def test_get_multi_frame_data(self, generator, request_vin, ecu_ecm):
        """Test getting multi-frame data."""
        mf_data = generator.get_multi_frame_data(request_vin, ecu_ecm)

        assert mf_data is not None
        assert "frames" in mf_data
        assert mf_data["multi_frame"] is True
        assert len(mf_data["frames"]) > 0

    def test_generate_single_frame(self, generator, ecu_ecm):
        """Test manual single-frame generation."""
        response = generator.generate_single_frame(
            service=0x01,
            pid=0x0C,
            data=bytes([0x0B, 0xE8]),  # 3000 RPM
            ecu=ecu_ecm
        )

        assert len(response) == 8
        # Format: [Len, 0x41, PID, Data..., Padding...]
        assert response[0] == 4  # Length: response + pid + 2 data bytes
        assert response[1] == 0x41  # Service + 0x40
        assert response[2] == 0x0C  # PID
        assert response[3] == 0x0B  # Data byte 1
        assert response[4] == 0xE8  # Data byte 2

    def test_generate_single_frame_with_padding(self, generator):
        """Test single-frame generation with custom padding."""
        ecu = ECUConfig(
            name="TCM",
            response_id=0x7E9,
            physical_request_id=0x7E1,
            index=1,
            padding_byte=0xAA,
            response_delay_ms=8.0
        )

        response = generator.generate_single_frame(
            service=0x01,
            pid=0x00,
            data=bytes([0x80, 0x00, 0x00, 0x00]),
            ecu=ecu
        )

        # Check padding is 0xAA
        assert response[7] == 0xAA
