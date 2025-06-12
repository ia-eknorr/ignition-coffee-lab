# utilities.py - Infrastructure and utility classes for Coffee Roaster Monitor

import time
import board
import digitalio
import busio
import asyncio
import supervisor
import microcontroller
import math
from os import getenv

# CircuitPython specific imports
import wifi
import socketpool
import ipaddress


class LEDController:
    """Onboard LED controller for status indication"""

    def __init__(self, logger):
        self.logger = logger
        self.led = None
        self.led_available = False
        self.current_task = None
        self.should_stop = False

        self._initialize_led()

    def _initialize_led(self):
        """Initialize the onboard LED"""
        try:
            # Disable any existing status LED control
            try:
                supervisor.set_rgb_status_brightness(0)
            except:
                pass

            self.led = digitalio.DigitalInOut(board.LED)
            self.led.direction = digitalio.Direction.OUTPUT
            self.led.value = False

            self.led_available = True

        except Exception as e:
            self.logger.error(f"LED init failed: {e}")
            self.led_available = False

    def on(self):
        """Turn LED on"""
        if self.led_available:
            self.led.value = True

    def off(self):
        """Turn LED off"""
        if self.led_available:
            self.led.value = False

    def blink_once(self, duration=0.15):
        """Single quick blink"""
        if self.led_available:
            self.led.value = True
            time.sleep(duration)
            self.led.value = False

    async def blink_pattern(self, pattern, repeat=True):
        """Blink with custom pattern: [(on_time, off_time), ...]"""
        if not self.led_available:
            return

        while not self.should_stop:
            for on_time, off_time in pattern:
                if self.should_stop:
                    break
                self.led.value = True
                await asyncio.sleep(on_time)
                self.led.value = False
                await asyncio.sleep(off_time)

            if not repeat:
                break

    def blink_sync_pattern(self, pattern, count=3):
        """Synchronous blink pattern for initialization (no async required)"""
        if not self.led_available:
            return

        for _ in range(count):
            for on_time, off_time in pattern:
                self.led.value = True
                time.sleep(on_time)
                self.led.value = False
                time.sleep(off_time)

    def start_init_pattern(self):
        """Start initialization pattern that works without async event loop"""
        if self.led_available:
            # Show we're starting with a few short-short-pause cycles
            self.blink_sync_pattern([(0.2, 0.2), (0.2, 0.8)], count=3)

    def start_pattern(self, pattern, repeat=True):
        """Start an async blink pattern"""
        self.stop_pattern()
        self.current_task = asyncio.create_task(self.blink_pattern(pattern, repeat))

    def stop_pattern(self):
        """Stop current pattern"""
        self.should_stop = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        self.should_stop = False
        self.off()

    def cleanup(self):
        """Clean up LED controller"""
        self.stop_pattern()
        if self.led_available and self.led:
            try:
                self.led.deinit()
            except:
                pass


class WiFiManager:
    """Manages WiFi connection using CircuitPython with settings.toml"""

    def __init__(self, logger):
        self.logger = logger
        self.is_connected = False
        self.socket_pool = None
        self.max_retries = 5
        self.retry_delay = 5

        # Get WiFi credentials from settings.toml
        try:
            self.ssid = getenv("WIFI_SSID")
            self.password = getenv("WIFI_PASSWORD")

            if None in [self.ssid, self.password]:
                raise RuntimeError(
                    "WiFi settings are kept in settings.toml, "
                    "please add them there. The settings file must contain "
                    "'WIFI_SSID', 'WIFI_PASSWORD', "
                    "at a minimum."
                )
        except Exception as e:
            self.logger.error(f"Failed to load WiFi settings: {e}")
            raise

    def connect(self) -> bool:
        if self._check_connection():
            self.logger.info("WiFi already connected and working")
            return True

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"WiFi connection attempt {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.info(f"Connecting to WiFi: {self.ssid}")

                # Disconnect if already connected
                if wifi.radio.connected:
                    wifi.radio.stop_station()
                    time.sleep(1)

                wifi.radio.connect(self.ssid, self.password)
                time.sleep(2)

                if wifi.radio.connected and wifi.radio.ipv4_address:
                    self.logger.info(f"Connected! IP: {wifi.radio.ipv4_address}")

                    self.socket_pool = socketpool.SocketPool(wifi.radio)

                    try:
                        ipv4 = ipaddress.ip_address("8.8.8.8")
                        ping_time = wifi.radio.ping(ipv4) * 1000
                        self.logger.info(f"Ping: {ping_time:.0f}ms")
                    except Exception:
                        pass

                    self.is_connected = True
                    return True
                self.logger.warning(f"Attempt {attempt + 1} failed - no IP address")

            except (ConnectionError, OSError) as e:
                self.logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            except Exception as e:
                self.logger.warning(f"WiFi connection attempt {attempt + 1} failed: {e}")

        self.logger.error(f"Failed to connect to WiFi after {self.max_retries} attempts")
        return False

    def _check_connection(self) -> bool:
        try:
            connected = wifi.radio.connected and wifi.radio.ipv4_address is not None
            self.is_connected = connected
            return connected
        except Exception:
            self.is_connected = False
            return False

    def disconnect(self):
        if self.is_connected:
            try:
                wifi.radio.stop_station()
                self.is_connected = False
                self.socket_pool = None
                self.logger.info("WiFi disconnected")
            except Exception as e:
                self.logger.error(f"WiFi disconnect error: {e}")

    def get_signal_strength(self) -> int:
        """Get WiFi signal strength if connected"""
        if self.is_connected:
            try:
                if wifi.radio.connected:
                    ap_info = wifi.radio.ap_info
                    if ap_info:
                        return ap_info.rssi
            except Exception:
                pass
        return None
