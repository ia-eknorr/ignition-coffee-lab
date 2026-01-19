# roast_monitor/outputs/console.py - Console output handler

from .base import Output


class ConsoleOutput(Output):
    """Output handler that prints temperature readings to console"""
    
    def __init__(self, logger, debug_mode=False):
        super().__init__(logger, debug_mode)
        self.debug("info", "Console output handler initialized")
    
    def requires_wifi(self) -> bool:
        return False
    
    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        self.debug("info", "Console output handler ready - no initialization required")
        return True
    
    def _format_reading(self, reading: dict) -> str:
        if reading["is_valid"]:
            return f"✓ Temp: {reading['temp_celsius']:.1f}°C ({reading['temp_fahrenheit']:.1f}°F)"
        else:
            return "⚠ ERROR: Invalid temperature reading"
    
    def output_reading(self, reading: dict) -> bool:
        try:
            formatted_output = self._format_reading(reading)
            print(formatted_output)
            self.debug("info", f"Console output: {formatted_output}")
            return True
        except Exception as e:
            self.logger.error(f"Console output error: {e}")
            return False
    
    def output_status(self, status: dict) -> bool:
        try:
            status_str = ", ".join([f"{k}: {v}" for k, v in status.items()])
            print(f"Status: {status_str}")
            self.debug("info", f"Console status: {status_str}")
            return True
        except Exception as e:
            self.logger.error(f"Console status output error: {e}")
            return False
    
    def cleanup(self):
        self.debug("info", "Console output handler cleanup complete")
        pass