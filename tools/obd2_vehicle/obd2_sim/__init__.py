"""
OBD2 Vehicle Simulator Package.

A Python-based OBD2 vehicle simulator for bench testing telematics gateways.
"""

__version__ = "1.0.0"
__author__ = "Sierra Telecom"

from .simulator import OBD2Simulator
from .profile import VehicleProfile, ECUConfig
from .config import SimulatorConfig, UnsupportedPIDMode, ValueMode

__all__ = [
    "OBD2Simulator",
    "VehicleProfile",
    "ECUConfig",
    "SimulatorConfig",
    "UnsupportedPIDMode",
    "ValueMode",
]
