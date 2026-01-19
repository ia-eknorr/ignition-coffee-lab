# roast_monitor/outputs/base.py - Base output handler class

from ..utils import WiFiManager


class Output:
    """Base class for outputting temperature data"""
    
    def __init__(self, logger, debug_mode=False):
        self.logger = logger
        self.debug_mode = debug_mode
    
    def debug(self, log_level, message):
        """Debug logging function - only outputs if debug_mode is enabled"""
        if self.debug_mode:
            getattr(self.logger, log_level)(f"[DEBUG] {message}")
    
    def requires_wifi(self) -> bool:
        """Return True if this output requires WiFi connectivity"""
        raise NotImplementedError("Subclasses must implement requires_wifi()")
    
    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        """Initialize the output handler"""
        raise NotImplementedError("Subclasses must implement initialize()")
    
    def output_reading(self, reading: dict) -> bool:
        """Output a temperature reading"""
        raise NotImplementedError("Subclasses must implement output_reading()")
    
    def output_status(self, status: dict) -> bool:
        """Output status information"""
        raise NotImplementedError("Subclasses must implement output_status()")
    
    def cleanup(self):
        """Clean up resources"""
        raise NotImplementedError("Subclasses must implement cleanup()")