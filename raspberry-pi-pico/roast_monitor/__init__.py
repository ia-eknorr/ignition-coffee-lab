# roast_monitor/__init__.py - ICL Roast Monitor

"""
Ignition Coffee Lab (ICL) - Roast Monitor

A CircuitPython-based temperature monitoring system for coffee roasting
as part of the Ignition Coffee Lab project.

Features:
- Real-time thermocouple temperature monitoring
- Artisan Scope integration via WebSocket
- MQTT data streaming for Ignition SCADA integration
- LED status indicators
- WiFi connectivity with auto-reconnection

Hardware: Raspberry Pi Pico W + MAX31855 + Type K Thermocouple
Platform: CircuitPython
Project: Ignition Coffee Lab
"""

__version__ = "1.0.0"
__author__ = "Ignition Coffee Lab"
__project__ = "ICL Roast Monitor"

# Import main classes
from .thermocouple import ThermocoupleMonitor
from .controller import RoastController

# Import subpackages
from . import outputs
from . import utils

__all__ = [
    'ThermocoupleMonitor',
    'RoastController', 
    'outputs',
    'utils',
]