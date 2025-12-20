"""
Tests for Vehicle Profile module.
"""

import pytest
from obd2_sim.profile import VehicleProfile, ECUConfig, BroadcastConfig


class TestECUConfig:
    """Tests for ECUConfig dataclass."""

    def test_from_dict_full(self):
        """Test creating ECUConfig from complete dictionary."""
        data = {
            "name": "ECM",
            "response_id": "0x7E8",
            "physical_request_id": "0x7E0",
            "index": 0,
            "padding_byte": "0xAA"
        }
        ecu = ECUConfig.from_dict(data)

        assert ecu.name == "ECM"
        assert ecu.response_id == 0x7E8
        assert ecu.physical_request_id == 0x7E0
        assert ecu.index == 0
        assert ecu.padding_byte == 0xAA

    def test_from_dict_defaults(self):
        """Test ECUConfig with default values."""
        data = {
            "name": "ECM",
            "response_id": "0x7E8",
            "physical_request_id": "0x7E0",
            "index": 0
        }
        ecu = ECUConfig.from_dict(data)

        assert ecu.padding_byte == 0x00  # Default

    def test_from_dict_integer_ids(self):
        """Test ECUConfig with integer IDs."""
        data = {
            "name": "ECM",
            "response_id": 0x7E8,
            "physical_request_id": 0x7E0,
            "index": 0
        }
        ecu = ECUConfig.from_dict(data)

        assert ecu.response_id == 0x7E8
        assert ecu.physical_request_id == 0x7E0


class TestBroadcastConfig:
    """Tests for BroadcastConfig dataclass."""

    def test_static_broadcast(self):
        """Test static broadcast configuration."""
        config = BroadcastConfig(
            can_id=0x003C,
            interval_ms=100,
            dlc=8,
            pattern_type="static",
            static_data=bytes.fromhex("00112233445566 77")
        )

        assert config.can_id == 0x003C
        assert config.interval_ms == 100
        assert config.pattern_type == "static"
        assert config.static_data is not None

    def test_dynamic_broadcast(self):
        """Test dynamic broadcast configuration."""
        config = BroadcastConfig(
            can_id=0x0130,
            interval_ms=50,
            dlc=8,
            pattern_type="dynamic",
            template=bytes(8),
            varying_bytes=[
                {"position": 0, "pattern": "rolling_counter", "range": [0, 15]}
            ]
        )

        assert config.pattern_type == "dynamic"
        assert config.template is not None
        assert len(config.varying_bytes) == 1


class TestVehicleProfile:
    """Tests for VehicleProfile class."""

    def test_load_profile(self, sample_profile_path):
        """Test loading a complete profile."""
        profile = VehicleProfile.load(sample_profile_path)

        assert profile.name == "BMW_X3_2019"
        assert profile.version == "1.1"

    def test_get_vehicle_info(self, sample_profile_path):
        """Test vehicle info retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        info = profile.get_vehicle_info()

        assert info["make"] == "BMW"
        assert info["model"] == "X3"
        assert info["year"] == 2019

    def test_get_vin(self, sample_profile_path):
        """Test VIN retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        vin = profile.get_vin()

        assert vin == "WBXHT3C34K5J12345"

    def test_get_ecus(self, sample_profile_path):
        """Test ECU list retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        ecus = profile.get_ecus()

        assert len(ecus) == 2
        assert ecus[0].name == "ECM"
        assert ecus[1].name == "TCM"

    def test_get_response_single_frame(self, sample_profile_path):
        """Test single-frame response retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        response = profile.get_response(0x01, 0x0C, 0x7E8)

        assert response is not None
        assert isinstance(response, bytes)
        # Should contain response data: 04 41 0C 0B E8
        assert len(response) >= 5

    def test_get_response_multi_frame(self, sample_profile_path):
        """Test multi-frame response retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        response = profile.get_response(0x09, 0x02, 0x7E8)

        assert response is not None
        assert isinstance(response, dict)
        assert "frames" in response
        assert response["multi_frame"] is True

    def test_get_response_not_found(self, sample_profile_path):
        """Test response for unsupported PID."""
        profile = VehicleProfile.load(sample_profile_path)
        response = profile.get_response(0x01, 0xFF, 0x7E8)

        assert response is None

    def test_get_broadcast_messages(self, sample_profile_path):
        """Test broadcast message retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        broadcasts = profile.get_broadcast_messages()

        assert len(broadcasts) == 2
        assert broadcasts[0].can_id == 0x003C
        assert broadcasts[1].can_id == 0x0130

    def test_get_operating_mode(self, sample_profile_path):
        """Test operating mode retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        mode = profile.get_operating_mode()

        assert mode == "discovery"

    def test_get_trace_characteristics(self, sample_profile_path):
        """Test trace characteristics retrieval."""
        profile = VehicleProfile.load(sample_profile_path)
        chars = profile.get_trace_characteristics()

        assert "source_trace" in chars
        assert chars["operating_mode"] == "discovery"

    def test_minimal_profile(self, minimal_profile_path):
        """Test loading a minimal profile."""
        profile = VehicleProfile.load(minimal_profile_path)

        assert profile.version == "1.0"
        ecus = profile.get_ecus()
        assert len(ecus) == 1

    def test_profile_not_found(self, tmp_path):
        """Test loading non-existent profile."""
        fake_path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            VehicleProfile.load(str(fake_path))
