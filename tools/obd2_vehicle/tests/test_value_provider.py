"""
Tests for Value Provider module.
"""

import pytest
from obd2_sim.value_provider import StaticValueProvider, RandomValueProvider, ScenarioValueProvider
from obd2_sim.profile import VehicleProfile


class TestStaticValueProvider:
    """Tests for StaticValueProvider."""

    def test_get_value_single_frame(self, sample_profile_path):
        """Test getting single-frame response value."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        # Service 01, PID 0C (Engine RPM) from ECU 0x7E8
        value = provider.get_value(0x01, 0x0C, 0x7E8)

        assert value is not None
        assert isinstance(value, bytes)

    def test_get_value_multi_frame(self, sample_profile_path):
        """Test getting multi-frame response value."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        # Service 09, PID 02 (VIN) from ECU 0x7E8
        value = provider.get_value(0x09, 0x02, 0x7E8)

        assert value is not None
        assert isinstance(value, dict)
        assert "frames" in value
        assert value.get("multi_frame") is True

    def test_get_value_not_found(self, sample_profile_path):
        """Test getting value for unsupported PID."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        value = provider.get_value(0x01, 0xFF, 0x7E8)

        assert value is None

    def test_get_value_wrong_ecu(self, sample_profile_path):
        """Test getting value from wrong ECU."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        # PID 0C exists for ECU 0x7E8 but not 0x7E9
        value = provider.get_value(0x01, 0x0C, 0x7E9)

        assert value is None

    def test_supports_existing_pid(self, sample_profile_path):
        """Test supports() for existing PID."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        assert provider.supports(0x01, 0x0C, 0x7E8) is True

    def test_supports_missing_pid(self, sample_profile_path):
        """Test supports() for missing PID."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        assert provider.supports(0x01, 0xFF, 0x7E8) is False

    def test_get_value_different_ecus(self, sample_profile_path):
        """Test getting values from different ECUs."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = StaticValueProvider(profile)

        # ECU 0x7E8 has supported PIDs
        value_e8 = provider.get_value(0x01, 0x00, 0x7E8)
        assert value_e8 is not None

        # ECU 0x7E9 also has supported PIDs
        value_e9 = provider.get_value(0x01, 0x00, 0x7E9)
        assert value_e9 is not None

        # Values should be different (different ECU responses)
        # Both should be bytes for single-frame
        assert isinstance(value_e8, bytes)
        assert isinstance(value_e9, bytes)


class TestRandomValueProvider:
    """Tests for RandomValueProvider (Phase 2 placeholder)."""

    def test_not_implemented(self, sample_profile_path):
        """Test that RandomValueProvider raises NotImplementedError."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = RandomValueProvider(profile)

        with pytest.raises(NotImplementedError):
            provider.get_value(0x01, 0x0C, 0x7E8)

        with pytest.raises(NotImplementedError):
            provider.supports(0x01, 0x0C, 0x7E8)


class TestScenarioValueProvider:
    """Tests for ScenarioValueProvider (Phase 3 placeholder)."""

    def test_not_implemented(self, sample_profile_path):
        """Test that ScenarioValueProvider raises NotImplementedError."""
        profile = VehicleProfile.load(sample_profile_path)
        provider = ScenarioValueProvider(profile, "scenario.json")

        with pytest.raises(NotImplementedError):
            provider.get_value(0x01, 0x0C, 0x7E8)

        with pytest.raises(NotImplementedError):
            provider.supports(0x01, 0x0C, 0x7E8)
