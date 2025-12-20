"""
Tests for CAN ID module.
"""

import pytest
from obd2_sim.can_id import (
    CANIdentifier,
    CANFormat,
    OBD2_FUNCTIONAL_REQUEST_ID,
    OBD2_PHYSICAL_REQUEST_BASE,
    OBD2_RESPONSE_BASE,
)


class TestCANIdentifier:
    """Tests for CANIdentifier class."""

    def test_standard_frame(self):
        """Test standard 11-bit frame identification."""
        can_id = CANIdentifier(0x7DF, extended=False)
        assert can_id.format == CANFormat.STANDARD_11BIT
        assert can_id.raw_id == 0x7DF

    def test_extended_frame(self):
        """Test extended 29-bit frame identification."""
        can_id = CANIdentifier(0x18DB33F1, extended=True)
        assert can_id.format == CANFormat.EXTENDED_29BIT
        assert can_id.raw_id == 0x18DB33F1

    def test_is_obd2_functional_request(self):
        """Test functional request identification."""
        func_req = CANIdentifier(OBD2_FUNCTIONAL_REQUEST_ID, extended=False)
        assert func_req.is_obd2_functional_request()
        assert func_req.is_obd2_request()

        # Not functional
        phys_req = CANIdentifier(0x7E0, extended=False)
        assert not phys_req.is_obd2_functional_request()

    def test_is_obd2_physical_request(self):
        """Test physical request identification."""
        for i in range(8):
            phys_req = CANIdentifier(OBD2_PHYSICAL_REQUEST_BASE + i, extended=False)
            assert phys_req.is_obd2_physical_request()
            assert phys_req.is_obd2_request()

        # Not physical
        func_req = CANIdentifier(OBD2_FUNCTIONAL_REQUEST_ID, extended=False)
        assert not func_req.is_obd2_physical_request()

    def test_is_obd2_response(self):
        """Test response identification."""
        for i in range(8):
            response = CANIdentifier(OBD2_RESPONSE_BASE + i, extended=False)
            assert response.is_obd2_response()

        # Not response
        request = CANIdentifier(OBD2_FUNCTIONAL_REQUEST_ID, extended=False)
        assert not request.is_obd2_response()

    def test_get_target_ecu_index_physical(self):
        """Test ECU index extraction from physical request."""
        for i in range(8):
            phys_req = CANIdentifier(OBD2_PHYSICAL_REQUEST_BASE + i, extended=False)
            assert phys_req.get_target_ecu_index() == i

    def test_get_target_ecu_index_functional(self):
        """Test ECU index extraction from functional request."""
        func_req = CANIdentifier(OBD2_FUNCTIONAL_REQUEST_ID, extended=False)
        assert func_req.get_target_ecu_index() is None

    def test_get_response_id_for_request(self):
        """Test response ID calculation."""
        for i in range(8):
            phys_req = CANIdentifier(OBD2_PHYSICAL_REQUEST_BASE + i, extended=False)
            assert phys_req.get_response_id_for_request() == OBD2_RESPONSE_BASE + i

        func_req = CANIdentifier(OBD2_FUNCTIONAL_REQUEST_ID, extended=False)
        assert func_req.get_response_id_for_request() is None

    def test_non_obd2_ids(self):
        """Test non-OBD2 CAN IDs."""
        other_id = CANIdentifier(0x100, extended=False)
        assert not other_id.is_obd2_request()
        assert not other_id.is_obd2_response()

    def test_str_representation(self):
        """Test string representation."""
        can_id = CANIdentifier(0x7DF, extended=False)
        assert "0x7DF" in str(can_id) or "0x7df" in str(can_id).lower()

    def test_repr(self):
        """Test repr."""
        can_id = CANIdentifier(0x7DF, extended=False)
        assert "CANIdentifier" in repr(can_id)
