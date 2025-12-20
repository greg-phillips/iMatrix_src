"""
Value Providers for OBD2 Vehicle Simulator.

Provides data values for OBD2 responses. Phase 1 implements static values
from captured profiles. Future phases will add random and scenario-based
value generation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from .profile import VehicleProfile

logger = logging.getLogger(__name__)


class ValueProvider(ABC):
    """
    Abstract base class for value providers.

    Value providers determine the data content of OBD2 responses.
    Different implementations support static replay, random generation,
    or scenario-based simulation.
    """

    @abstractmethod
    def get_value(self, service: int, pid: Optional[int], ecu_id: int) -> Optional[bytes]:
        """
        Get value for a specific service/PID from a specific ECU.

        Args:
            service: OBD2 service number
            pid: PID number (None for service-only requests)
            ecu_id: ECU response ID (e.g., 0x7E8)

        Returns:
            Response bytes or None if not available
        """
        pass

    @abstractmethod
    def supports(self, service: int, pid: Optional[int], ecu_id: int) -> bool:
        """
        Check if this provider can provide a value for the given parameters.

        Args:
            service: OBD2 service number
            pid: PID number
            ecu_id: ECU response ID

        Returns:
            True if value is available
        """
        pass


class StaticValueProvider(ValueProvider):
    """
    Phase 1 Static Value Provider.

    Returns static values captured from trace files and stored in the
    vehicle profile. This provides exact replay of captured vehicle responses.
    """

    def __init__(self, profile: VehicleProfile):
        """
        Initialize static value provider.

        Args:
            profile: Vehicle profile with captured responses
        """
        self.profile = profile

    def get_value(self, service: int, pid: Optional[int], ecu_id: int) -> Optional[bytes]:
        """
        Get static value from profile.

        Returns the exact response captured in the trace file.
        """
        response = self.profile.get_response(service, pid, ecu_id)

        if response is None:
            pid_str = f"0x{pid:02X}" if pid is not None else "N/A"
            logger.debug(f"No response for service 0x{service:02X} "
                        f"PID {pid_str} ECU 0x{ecu_id:03X}")
            return None

        # Handle both single-frame (bytes) and multi-frame (dict) responses
        if isinstance(response, bytes):
            return response
        elif isinstance(response, dict):
            # Multi-frame response - return the dict for special handling
            return response
        else:
            logger.warning(f"Unexpected response type: {type(response)}")
            return None

    def supports(self, service: int, pid: Optional[int], ecu_id: int) -> bool:
        """Check if value exists in profile."""
        return self.profile.get_response(service, pid, ecu_id) is not None


# Future Phase 2: Random Value Provider
class RandomValueProvider(ValueProvider):
    """
    Phase 2 Random Value Provider (Placeholder).

    Generates random values within defined ranges from the profile.
    This allows for more realistic simulation with varying data.
    """

    def __init__(self, profile: VehicleProfile, seed: Optional[int] = None):
        """
        Initialize random value provider.

        Args:
            profile: Vehicle profile with value ranges
            seed: Random seed for reproducibility
        """
        self.profile = profile
        self.seed = seed
        # TODO: Initialize random generator in Phase 2

    def get_value(self, service: int, pid: Optional[int], ecu_id: int) -> Optional[bytes]:
        """Get random value within profile ranges (not implemented)."""
        raise NotImplementedError("RandomValueProvider is Phase 2")

    def supports(self, service: int, pid: Optional[int], ecu_id: int) -> bool:
        """Check if random value can be generated."""
        raise NotImplementedError("RandomValueProvider is Phase 2")


# Future Phase 3: Scenario Value Provider
class ScenarioValueProvider(ValueProvider):
    """
    Phase 3 Scenario Value Provider (Placeholder).

    Generates values based on scenario timeline files,
    simulating driving patterns like idle, acceleration, cruise.
    """

    def __init__(self, profile: VehicleProfile, scenario_path: str):
        """
        Initialize scenario value provider.

        Args:
            profile: Vehicle profile
            scenario_path: Path to scenario file
        """
        self.profile = profile
        self.scenario_path = scenario_path
        # TODO: Load scenario in Phase 3

    def get_value(self, service: int, pid: Optional[int], ecu_id: int) -> Optional[bytes]:
        """Get scenario-based value (not implemented)."""
        raise NotImplementedError("ScenarioValueProvider is Phase 3")

    def supports(self, service: int, pid: Optional[int], ecu_id: int) -> bool:
        """Check if scenario provides value."""
        raise NotImplementedError("ScenarioValueProvider is Phase 3")
