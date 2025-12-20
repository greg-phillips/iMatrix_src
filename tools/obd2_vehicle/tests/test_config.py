"""
Tests for Configuration module.
"""

import pytest
from argparse import Namespace
from obd2_sim.config import (
    SimulatorConfig,
    UnsupportedPIDMode,
    ValueMode,
    load_config_from_args
)


class TestUnsupportedPIDMode:
    """Tests for UnsupportedPIDMode enum."""

    def test_enum_values(self):
        """Test enum values exist."""
        assert UnsupportedPIDMode.NO_RESPONSE
        assert UnsupportedPIDMode.NRC_12
        assert UnsupportedPIDMode.NRC_11


class TestValueMode:
    """Tests for ValueMode enum."""

    def test_enum_values(self):
        """Test enum values exist."""
        assert ValueMode.STATIC
        assert ValueMode.RANDOM
        assert ValueMode.SCENARIO


class TestSimulatorConfig:
    """Tests for SimulatorConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SimulatorConfig(
            profile_path="test.json"
        )

        assert config.profile_path == "test.json"
        assert config.can_interface == "vcan0"
        assert config.can_bitrate == 500000
        assert config.extended_frames is False
        assert config.value_mode == ValueMode.STATIC
        assert config.unsupported_pid_mode == UnsupportedPIDMode.NO_RESPONSE
        assert config.broadcast_enabled is True
        assert config.response_delay_ms == 0.0
        assert config.log_frames is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SimulatorConfig(
            profile_path="custom.json",
            can_interface="can0",
            can_bitrate=250000,
            extended_frames=True,
            value_mode=ValueMode.RANDOM,
            unsupported_pid_mode=UnsupportedPIDMode.NRC_12,
            broadcast_enabled=False,
            response_delay_ms=5.0,
            log_frames=True
        )

        assert config.can_interface == "can0"
        assert config.can_bitrate == 250000
        assert config.extended_frames is True
        assert config.value_mode == ValueMode.RANDOM
        assert config.unsupported_pid_mode == UnsupportedPIDMode.NRC_12
        assert config.broadcast_enabled is False
        assert config.response_delay_ms == 5.0
        assert config.log_frames is True


class TestLoadConfigFromArgs:
    """Tests for load_config_from_args function."""

    def test_basic_args(self):
        """Test loading config from basic arguments."""
        args = Namespace(
            profile="test.json",
            interface="vcan0",
            bitrate=500000,
            extended=False,
            value_mode="static",
            unsupported_pid="no-response",
            disable_broadcast=False,
            broadcast_ids=None,
            response_delay=None,
            inter_ecu_delay=None,
            jitter=0.0,
            log_level="info",
            log_file=None,
            log_frames=False,
            daemon=False,
            pid_file=None,
            stats_interval=0
        )

        config = load_config_from_args(args)

        assert config.profile_path == "test.json"
        assert config.can_interface == "vcan0"
        assert config.value_mode == ValueMode.STATIC

    def test_unsupported_pid_modes(self):
        """Test unsupported PID mode parsing."""
        for mode_str, expected in [
            ("no-response", UnsupportedPIDMode.NO_RESPONSE),
            ("nrc-12", UnsupportedPIDMode.NRC_12),
            ("nrc-11", UnsupportedPIDMode.NRC_11),
        ]:
            args = Namespace(
                profile="test.json",
                interface="vcan0",
                bitrate=500000,
                extended=False,
                value_mode="static",
                unsupported_pid=mode_str,
                disable_broadcast=False,
                broadcast_ids=None,
                response_delay=None,
                inter_ecu_delay=None,
                jitter=0.0,
                log_level="info",
                log_file=None,
                log_frames=False,
                daemon=False,
                pid_file=None,
                stats_interval=0
            )

            config = load_config_from_args(args)
            assert config.unsupported_pid_mode == expected

    def test_broadcast_ids_parsing(self):
        """Test broadcast IDs parsing."""
        args = Namespace(
            profile="test.json",
            interface="vcan0",
            bitrate=500000,
            extended=False,
            value_mode="static",
            unsupported_pid="no-response",
            disable_broadcast=False,
            broadcast_ids="003C,0130,0200",
            response_delay=None,
            inter_ecu_delay=None,
            jitter=0.0,
            log_level="info",
            log_file=None,
            log_frames=False,
            daemon=False,
            pid_file=None,
            stats_interval=0
        )

        config = load_config_from_args(args)

        assert config.broadcast_ids is not None
        assert 0x003C in config.broadcast_ids
        assert 0x0130 in config.broadcast_ids
        assert 0x0200 in config.broadcast_ids

    def test_disable_broadcast(self):
        """Test broadcast disable."""
        args = Namespace(
            profile="test.json",
            interface="vcan0",
            bitrate=500000,
            extended=False,
            value_mode="static",
            unsupported_pid="no-response",
            disable_broadcast=True,
            broadcast_ids=None,
            response_delay=None,
            inter_ecu_delay=None,
            jitter=0.0,
            log_level="info",
            log_file=None,
            log_frames=False,
            daemon=False,
            pid_file=None,
            stats_interval=0
        )

        config = load_config_from_args(args)
        assert config.broadcast_enabled is False

    def test_timing_overrides(self):
        """Test timing parameter overrides."""
        args = Namespace(
            profile="test.json",
            interface="vcan0",
            bitrate=500000,
            extended=False,
            value_mode="static",
            unsupported_pid="no-response",
            disable_broadcast=False,
            broadcast_ids=None,
            response_delay=10.0,
            inter_ecu_delay=5.0,
            jitter=2.0,
            log_level="info",
            log_file=None,
            log_frames=False,
            daemon=False,
            pid_file=None,
            stats_interval=0
        )

        config = load_config_from_args(args)

        assert config.response_delay_ms == 10.0
        assert config.inter_ecu_delay_ms == 5.0
        assert config.jitter_ms == 2.0
