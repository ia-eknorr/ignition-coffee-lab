# roaster.py - Coffee Roaster Monitor and Controller Classes

import time
import asyncio
import math
import board
import digitalio
import busio
import adafruit_max31855

# Local imports
from utilities import LEDController, WiFiManager
from output_strategies import OutputStrategy


class CoffeeRoasterMonitor:
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


class RoasterController:
    """Main controller that orchestrates monitor and output strategies"""

    def __init__(self, output_strategy: OutputStrategy, logger):
        self.output_strategy = output_strategy
        self.logger = logger
        self.monitor = CoffeeRoasterMonitor(logger)
        self.led_controller = LEDController(logger)

        # Show initialization started with synchronous LED pattern
        self.led_controller.start_init_pattern()

        # Initialize WiFi manager if needed
        self.wifi_manager = None
        if output_strategy.requires_wifi():
            try:
                self.wifi_manager = WiFiManager(logger)

                # Start continuous blinking during WiFi connection
                self.led_controller.start_pattern([(0.2, 0.2), (0.2, 0.8)])

                if not self.wifi_manager.connect():
                    # Error pattern: fast blink
                    self.led_controller.start_pattern([(0.1, 0.1)])
                    raise RuntimeError("Failed to connect to WiFi after multiple attempts")

                signal = self.wifi_manager.get_signal_strength()
                if signal:
                    self.logger.info(f"Signal strength: {signal} dBm")

            except Exception as e:
                self.logger.error(f"WiFi initialization failed: {e}")
                self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
                raise RuntimeError(f"WiFi setup failed: {e}")

        # Initialize output strategy with LED indication
        self.led_controller.start_pattern([(0.2, 0.2), (0.2, 0.8)])
        if not self.output_strategy.initialize(self.wifi_manager):
            self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
            raise RuntimeError("Failed to initialize output strategy")

        # Success! Three blinks then solid for 3 seconds
        self.led_controller.stop_pattern()
        for _ in range(3):
            self.led_controller.blink_once(0.2)
            time.sleep(0.2)
        self.led_controller.on()
        time.sleep(3.0)
        self.led_controller.off()

        self.logger.info("Initialization complete - monitoring started")

    async def run_continuous_async(self, read_interval: float = 1.0, max_errors: int = 10):
        """Async version of continuous monitoring loop"""
        self.logger.info("=== Coffee Roaster Monitor Starting ===")
        self.logger.info(f"Strategy: {self.output_strategy.__class__.__name__}")

        error_count = 0
        wifi_check_interval = 30
        last_wifi_check = time.monotonic()

        startup_status = {
            "status": "starting",
            "strategy": self.output_strategy.__class__.__name__,
            "wifi_connected": self.wifi_manager.is_connected if self.wifi_manager else False
        }
        self.output_strategy.output_status(startup_status)

        try:
            while True:
                # Periodic WiFi connection check
                if self.wifi_manager and (time.monotonic() - last_wifi_check > wifi_check_interval):
                    if not self.wifi_manager._check_connection():
                        self.logger.warning("WiFi connection lost, attempting to reconnect...")
                        self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
                        if self.wifi_manager.connect():
                            self.logger.info("WiFi reconnected successfully")
                            self.led_controller.stop_pattern()
                        else:
                            self.logger.error("Failed to reconnect WiFi")
                            continue  # Keep error pattern
                    last_wifi_check = time.monotonic()

                reading = self.monitor.read_temperature()

                if reading["is_valid"]:
                    success = self.output_strategy.output_reading(reading)
                    if success:
                        # Clear error pattern if we had one and reset counter
                        if error_count >= 3:
                            self.led_controller.stop_pattern()
                        error_count = 0
                        # Quick blink when data is sent
                        self.led_controller.blink_once()
                    else:
                        error_count += 1
                        self.logger.warning(f"Output failed, error count: {error_count}")
                        if error_count >= 3:  # Start error pattern after 3 failures
                            self.led_controller.start_pattern([(0.1, 0.1)])
                else:
                    self.logger.error("Failed to read valid temperature")
                    error_count += 1
                    if error_count >= 3:
                        self.led_controller.start_pattern([(0.1, 0.1)])

                if error_count >= max_errors:
                    self.logger.error(f"Too many consecutive errors ({max_errors}). Stopping.")
                    self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
                    self.output_strategy.output_status({
                        "status": "error", 
                        "reason": "max_errors_reached",
                        "error_count": error_count
                    })
                    break

                await asyncio.sleep(read_interval)

        except KeyboardInterrupt:
            self.logger.info("Shutting down gracefully...")
            self.output_strategy.output_status({"status": "shutdown", "reason": "user_interrupt"})
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
            self.output_strategy.output_status({"status": "error", "reason": "unexpected_exception"})
        finally:
            await self.cleanup_async()

    def run_continuous(self, read_interval: float = 1.0, max_errors: int = 10):
        """Synchronous wrapper for async continuous monitoring"""
        asyncio.run(self.run_continuous_async(read_interval, max_errors))

    async def cleanup_async(self):
        """Async cleanup of resources"""
        self.output_strategy.cleanup()
        if self.wifi_manager:
            self.wifi_manager.disconnect()
        self.led_controller.cleanup()

    def cleanup(self):
        """Synchronous cleanup of resources"""
        self.output_strategy.cleanup()
        if self.wifi_manager:
            self.wifi_manager.disconnect()
        self.led_controller.cleanup()
