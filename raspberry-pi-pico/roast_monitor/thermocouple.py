# roast_monitor/thermocouple.py - Thermocouple Temperature Monitoring

import time
import math
import board
import digitalio
import busio
import adafruit_max31855


class ThermocoupleMonitor:
    """Core temperature monitoring class - hardware abstraction for MAX31855 thermocouple"""

    def __init__(self, logger):
        self.logger = logger
        self.max31855 = None
        self._initialize_hardware()

    def _initialize_hardware(self):
        """Initialize the MAX31855 thermocouple interface"""
        try:
            self.logger.info("Initializing thermocouple...")

            # Configure SPI interface
            # Using GP18 for SCK (clock), GP16 for MISO (data), GP17 for CS (chip select)
            spi = busio.SPI(board.GP18, MISO=board.GP16)  # SCK, MISO
            cs = digitalio.DigitalInOut(board.GP17)

            # Initialize MAX31855 with SPI interface
            self.max31855 = adafruit_max31855.MAX31855(spi, cs)

            # Test reading to verify connection
            test_temp = self.max31855.temperature
            if test_temp is not None:
                self.logger.info(f"Thermocouple ready - Current: {test_temp:.1f}°C")
            else:
                self.logger.warning("Thermocouple may not be connected properly")

        except Exception as e:
            self.logger.error(f"Failed to initialize MAX31855: {e}")
            raise

    def read_temperature(self) -> dict:
        """Read temperature from the thermocouple and return a temperature dict"""
        try:
            # Read temperature from MAX31855
            temp_c = self.max31855.temperature

            if temp_c is None:
                self.logger.error("MAX31855 returned None - check thermocouple connection")
                return self._create_temperature_reading(float('nan'))

            # Create reading dict
            reading = self._create_temperature_reading(temp_c)

            if not reading['is_valid']:
                self.logger.warning(f"Temperature reading seems unrealistic: {temp_c}°C")

            return reading

        except Exception as e:
            self.logger.error(f"Error reading temperature: {e}")
            return self._create_temperature_reading(float('nan'))

    def _create_temperature_reading(self, temp_celsius: float) -> dict:
        """Create a temperature reading dict from celsius temperature"""
        temp_fahrenheit = (temp_celsius * 9/5) + 32
        is_valid = temp_celsius is not None and not math.isnan(temp_celsius) and -50 <= temp_celsius <= 600
        
        return {
            "temp_celsius": temp_celsius,
            "temp_fahrenheit": temp_fahrenheit,
            "timestamp": time.monotonic(),
            "is_valid": is_valid
        }

    def format_reading_to_dict(self, reading: dict) -> dict:
        """Format a temperature reading for JSON output (for MQTT, etc.)"""
        return {
            "temperature_c": round(reading["temp_celsius"], 2) if reading["is_valid"] else None,
            "temperature_f": round(reading["temp_fahrenheit"], 2) if reading["is_valid"] else None,
            "timestamp": reading["timestamp"],
            "status": "good" if reading["is_valid"] else "sensor_error",
            "is_valid": reading["is_valid"]
        }

    def get_internal_temperature(self) -> float:
        """Get the internal temperature of the MAX31855 chip (for diagnostics)"""
        try:
            if self.max31855:
                return self.max31855.reference_temperature
            return None
        except Exception as e:
            self.logger.error(f"Error reading internal temperature: {e}")
            return None

    def check_faults(self) -> dict:
        """Check for thermocouple faults and return status dictionary"""
        faults = {
            "short_to_vcc": False,
            "short_to_ground": False,
            "open_circuit": False,
            "any_fault": False
        }

        try:
            if self.max31855:
                # Note: CircuitPython MAX31855 library may not expose fault detection
                # This is a placeholder for future fault detection implementation
                pass
        except Exception as e:
            self.logger.error(f"Error checking faults: {e}")
            faults["any_fault"] = True

        return faults