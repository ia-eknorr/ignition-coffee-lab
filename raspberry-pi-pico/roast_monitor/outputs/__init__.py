# roast_monitor/outputs/__init__.py - ICL Roast Monitor Output Handlers

"""
Output handlers for ICL Roast Monitor

Part of the Ignition Coffee Lab (ICL) automation system.

Available output types:
- ConsoleOutput: Print to console/serial for debugging
- MQTTOutput: Publish to MQTT broker for ICL system integration  
- ArtisanOutput: WebSocket server for Artisan Scope integration

All outputs designed for industrial-grade reliability and 
integration with Ignition SCADA systems.
"""

from .base import Output
from .console import ConsoleOutput
from .mqtt import MQTTOutput
from .artisan import ArtisanOutput

# Control what gets imported with "from roast_monitor.outputs import *"
__all__ = [
    'Output',           # Base class
    'ConsoleOutput',    # Console/serial output
    'MQTTOutput',       # MQTT publishing for ICL integration
    'ArtisanOutput'     # Artisan Scope WebSocket server
]

# ICL Roast Monitor version
__version__ = "1.0.0"