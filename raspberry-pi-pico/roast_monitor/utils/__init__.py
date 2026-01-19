# roast_monitor/utils/__init__.py - ICL Roast Monitor Utilities

"""
Utility modules for ICL Roast Monitor

Part of the Ignition Coffee Lab (ICL) automation system.

This package provides:
- LEDController: Manage status LED indicators
- WiFiManager: Handle WiFi connections and networking

All utilities designed for reliable operation in CircuitPython
embedded environments.
"""

from .led import LEDController
from .wifi import WiFiManager

# Export these classes when someone imports from utils
__all__ = [
    'LEDController',   # Status LED management
    'WiFiManager'      # WiFi connection handling
]

# ICL Roast Monitor version
__version__ = "1.0.0"