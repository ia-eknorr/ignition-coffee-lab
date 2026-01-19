# roast_monitor/utils/wifi.py - WiFi Connection Manager

import time
from os import getenv

# CircuitPython specific imports
import wifi
import socketpool
import ipaddress


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

    def get_ip_address(self) -> str:
        """Get current IP address if connected"""
        if self.is_connected and wifi.radio.connected:
            return str(wifi.radio.ipv4_address)
        return None