# roast_monitor/controller.py - ICL Roast Controller and Orchestration

import time
import asyncio

# Local imports
from .utils import LEDController, WiFiManager
from .thermocouple import ThermocoupleMonitor
from .outputs.base import Output


class RoastController:
    """Main controller that orchestrates monitor and output handlers"""

    def __init__(self, output_handler: Output, logger, debug_mode=False):
        self.output_handler = output_handler
        self.logger = logger
        self.debug_mode = debug_mode
        self.monitor = ThermocoupleMonitor(logger)
        self.led_controller = LEDController(logger)

        # Show initialization started with synchronous LED pattern
        self.led_controller.start_init_pattern()

        # Initialize WiFi manager if needed
        self.wifi_manager = None
        if output_handler.requires_wifi():
            try:
                self.wifi_manager = WiFiManager(logger, debug_mode=debug_mode)

                # Blink pattern before WiFi connection (sync - no event loop yet)
                self.led_controller.blink_sync_pattern([(0.2, 0.2), (0.2, 0.8)], count=2)

                if not self.wifi_manager.connect():
                    # Error pattern: fast blink (sync)
                    self.led_controller.blink_sync_pattern([(0.1, 0.1)], count=5)
                    raise RuntimeError("Failed to connect to WiFi after multiple attempts")

                signal = self.wifi_manager.get_signal_strength()
                if signal:
                    self.logger.info(f"Signal strength: {signal} dBm")

            except Exception as e:
                self.logger.error(f"WiFi initialization failed: {e}")
                self.led_controller.blink_sync_pattern([(0.1, 0.1)], count=5)  # Error pattern
                raise RuntimeError(f"WiFi setup failed: {e}")

        # Blink before output handler init (sync - no event loop yet)
        self.led_controller.blink_sync_pattern([(0.2, 0.2), (0.2, 0.8)], count=2)
        if not self.output_handler.initialize(self.wifi_manager):
            self.led_controller.blink_sync_pattern([(0.1, 0.1)], count=5)  # Error pattern
            raise RuntimeError("Failed to initialize output handler")

        # Success! Three blinks then solid for 3 seconds
        for _ in range(3):
            self.led_controller.blink_once(0.2)
            time.sleep(0.2)
        self.led_controller.on()
        time.sleep(3.0)
        self.led_controller.off()

        self.logger.info("Initialization complete - monitoring started")

    async def run_continuous_async(self, read_interval: float = 1.0, max_errors: int = 10):
        """Async version of continuous monitoring loop"""
        self.logger.info("=== ICL Roast Monitor Starting ===")
        self.logger.info(f"Output Handler: {self.output_handler.__class__.__name__}")

        error_count = 0
        wifi_check_interval = 30
        last_wifi_check = time.monotonic()

        startup_status = {
            "status": "starting",
            "handler": self.output_handler.__class__.__name__,
            "wifi_connected": self.wifi_manager.is_connected if self.wifi_manager else False
        }
        self.output_handler.output_status(startup_status)

        try:
            while True:
                # Periodic WiFi connection check
                if self.wifi_manager and (time.monotonic() - last_wifi_check > wifi_check_interval):
                    if not self.wifi_manager._check_connection():
                        self.logger.warning("WiFi connection lost, attempting to reconnect...")
                        self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
                        if self.wifi_manager.connect(is_reconnect=True):
                            self.logger.info("WiFi reconnected successfully")
                            self.led_controller.stop_pattern()
                        else:
                            self.logger.error("Failed to reconnect WiFi")
                            continue  # Keep error pattern
                    last_wifi_check = time.monotonic()

                reading = self.monitor.read_temperature()

                if reading["is_valid"]:
                    success = self.output_handler.output_reading(reading)
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
                    self.output_handler.output_status({
                        "status": "error", 
                        "reason": "max_errors_reached",
                        "error_count": error_count
                    })
                    break

                await asyncio.sleep(read_interval)

        except KeyboardInterrupt:
            self.logger.info("Shutting down gracefully...")
            self.output_handler.output_status({"status": "shutdown", "reason": "user_interrupt"})
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.led_controller.start_pattern([(0.1, 0.1)])  # Error pattern
            self.output_handler.output_status({"status": "error", "reason": "unexpected_exception"})
        finally:
            await self.cleanup_async()

    def run_continuous(self, read_interval: float = 1.0, max_errors: int = 10):
        """Synchronous wrapper for async continuous monitoring"""
        asyncio.run(self.run_continuous_async(read_interval, max_errors))

    async def cleanup_async(self):
        """Async cleanup of resources"""
        self.output_handler.cleanup()
        if self.wifi_manager:
            self.wifi_manager.disconnect()
        self.led_controller.cleanup()

    def cleanup(self):
        """Synchronous cleanup of resources"""
        self.output_handler.cleanup()
        if self.wifi_manager:
            self.wifi_manager.disconnect()
        self.led_controller.cleanup()