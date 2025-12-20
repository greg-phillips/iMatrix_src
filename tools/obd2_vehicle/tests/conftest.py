"""
Pytest fixtures for OBD2 Vehicle Simulator tests.
"""

import json
import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def sample_profile_data():
    """Sample vehicle profile data for testing."""
    return {
        "profile_version": "1.1",
        "vehicle_info": {
            "make": "BMW",
            "model": "X3",
            "year": 2019,
            "vin": "WBXHT3C34K5J12345"
        },
        "trace_characteristics": {
            "source_trace": "BMW_Test.trc",
            "operating_mode": "discovery"
        },
        "ecus": [
            {
                "name": "ECM",
                "response_id": "0x7E8",
                "physical_request_id": "0x7E0",
                "index": 0,
                "padding_byte": "0x00"
            },
            {
                "name": "TCM",
                "response_id": "0x7E9",
                "physical_request_id": "0x7E1",
                "index": 1,
                "padding_byte": "0xAA"
            }
        ],
        "obd2_responses": {
            "0x7E8": {
                "0x01": {
                    "0x00": {
                        "response": "06 41 00 BE 3F B8 13",
                        "description": "Supported PIDs 01-20"
                    },
                    "0x0C": {
                        "response": "04 41 0C 0B E8",
                        "description": "Engine RPM"
                    },
                    "0x0D": {
                        "response": "03 41 0D 00",
                        "description": "Vehicle Speed"
                    }
                },
                "0x09": {
                    "0x02": {
                        "multi_frame": True,
                        "total_length": 20,
                        "frames": [
                            "10 14 49 02 01 57 42 58",
                            "21 48 54 33 43 33 34 4B",
                            "22 35 4A 31 32 33 34 35"
                        ],
                        "description": "VIN"
                    }
                }
            },
            "0x7E9": {
                "0x01": {
                    "0x00": {
                        "response": "06 41 00 80 00 00 00",
                        "description": "Supported PIDs 01-20"
                    }
                }
            }
        },
        "broadcast_messages": [
            {
                "can_id": "0x003C",
                "interval_ms": 100,
                "dlc": 8,
                "pattern_type": "static",
                "static_data": "00 00 00 00 00 00 00 00"
            },
            {
                "can_id": "0x0130",
                "interval_ms": 50,
                "dlc": 8,
                "pattern_type": "dynamic",
                "template": "00 00 00 00 00 00 00 00",
                "varying_bytes": [
                    {
                        "position": 0,
                        "pattern": "rolling_counter",
                        "range": [0, 15]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_profile_path(sample_profile_data, tmp_path):
    """Create a temporary profile file."""
    profile_path = tmp_path / "test_profile.json"
    with open(profile_path, 'w') as f:
        json.dump(sample_profile_data, f, indent=2)
    return str(profile_path)


@pytest.fixture
def minimal_profile_data():
    """Minimal valid profile data."""
    return {
        "profile_version": "1.0",
        "vehicle_info": {
            "make": "Test",
            "model": "Vehicle",
            "year": 2020
        },
        "ecus": [
            {
                "name": "ECM",
                "response_id": "0x7E8",
                "physical_request_id": "0x7E0",
                "index": 0
            }
        ],
        "obd2_responses": {}
    }


@pytest.fixture
def minimal_profile_path(minimal_profile_data, tmp_path):
    """Create a minimal temporary profile file."""
    profile_path = tmp_path / "minimal_profile.json"
    with open(profile_path, 'w') as f:
        json.dump(minimal_profile_data, f, indent=2)
    return str(profile_path)


class MockCANBus:
    """Mock CAN bus for testing without hardware."""

    def __init__(self):
        self.sent_messages = []
        self.receive_queue = []

    def send(self, msg):
        """Record sent message."""
        self.sent_messages.append(msg)

    def recv(self, timeout=None):
        """Return queued message or None."""
        if self.receive_queue:
            return self.receive_queue.pop(0)
        return None

    def shutdown(self):
        """Clean up."""
        pass

    def queue_message(self, msg):
        """Add message to receive queue."""
        self.receive_queue.append(msg)


@pytest.fixture
def mock_can_bus():
    """Create mock CAN bus."""
    return MockCANBus()


class MockCANMessage:
    """Mock CAN message for testing."""

    def __init__(self, arbitration_id, data, is_extended_id=False):
        self.arbitration_id = arbitration_id
        self.data = bytes(data) if not isinstance(data, bytes) else data
        self.is_extended_id = is_extended_id


@pytest.fixture
def mock_message_factory():
    """Factory for creating mock CAN messages."""
    def create_message(can_id, data, extended=False):
        return MockCANMessage(can_id, data, extended)
    return create_message
