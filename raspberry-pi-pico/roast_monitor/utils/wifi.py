# roast_monitor/utils/wifi.py - WiFi Connection Manager

import time
from os import getenv

# CircuitPython specific imports
import wifi
import socketpool
import ipaddress


class WiFiManager:
    """Manages WiFi connection using CircuitPython with settings.toml"""

    def __init__(self, logger, debug_mode=False):
        self.logger = logger
        self.debug_mode = debug_mode
        self.is_connected = False
        self.socket_pool = None
        self.max_retries = 5
        self.initial_retry_delay = 2  # Faster retries on startup
        self.reconnect_retry_delay = 5  # Slower retries for reconnection
        self._radio_warmed_up = False

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

    def _reset_radio(self):
        """Reset WiFi radio to clear any bad state"""
        try:
            wifi.radio.stop_scanning_networks()
        except Exception:
            pass
        try:
            wifi.radio.stop_station()
        except Exception:
            pass
        # Toggle radio off/on to fully reset
        wifi.radio.enabled = False
        time.sleep(0.5)
        wifi.radio.enabled = True
        time.sleep(0.5)

    def _warmup_radio(self) -> bool:
        """
        Scan for networks to warm up the WiFi radio hardware.
        This fixes the 'No network with that ssid' error on cold boot.
        Returns True if target SSID was found.
        """
        if self._radio_warmed_up:
            return True

        self.logger.info("Scanning for networks...")
        target_found = False

        try:
            # Reset radio first to clear any stale state
            self._reset_radio()

            networks = wifi.radio.start_scanning_networks()
            network_list = []

            # Limit iterations to prevent hanging
            max_networks = 50
            for i, network in enumerate(networks):
                if i >= max_networks:
                    break
                network_list.append((network.ssid, network.rssi))
                if network.ssid == self.ssid:
                    target_found = True

            wifi.radio.stop_scanning_networks()
            self._radio_warmed_up = True

            if self.debug_mode and network_list:
                # Sort by signal strength and show top networks
                network_list.sort(key=lambda x: x[1], reverse=True)
                self.logger.info(f"Found {len(network_list)} networks")
                for ssid, rssi in network_list[:5]:
                    marker = " <--" if ssid == self.ssid else ""
                    self.logger.info(f"  {ssid}: {rssi} dBm{marker}")

            if target_found:
                self.logger.info(f"Target network '{self.ssid}' found")
            else:
                self.logger.warning(f"Target network '{self.ssid}' not found in scan")

        except Exception as e:
            self.logger.warning(f"Network scan failed: {e}")
            # Try to clean up
            try:
                wifi.radio.stop_scanning_networks()
            except Exception:
                pass
            # Still mark as warmed up - the scan attempt itself warms the radio
            self._radio_warmed_up = True

        return target_found

    def connect(self, is_reconnect=False) -> bool:
        """
        Connect to WiFi network.
        Args:
            is_reconnect: If True, use slower retry delay (for mid-session reconnects)
        """
        if self._check_connection():
            self.logger.info("WiFi already connected and working")
            return True

        # Warm up radio on first connection attempt
        if not self._radio_warmed_up:
            self._warmup_radio()
            time.sleep(0.5)  # Brief pause after scan

        retry_delay = self.reconnect_retry_delay if is_reconnect else self.initial_retry_delay

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"WiFi connection attempt {attempt + 1}/{self.max_retries}")
                    time.sleep(retry_delay)
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

            except ConnectionError as e:
                error_msg = str(e)
                if "No network with that ssid" in error_msg:
                    self.logger.warning(f"Network not visible on attempt {attempt + 1}, rescanning...")
                    self._radio_warmed_up = False
                    self._warmup_radio()
                else:
                    self.logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            except OSError as e:
                self.logger.warning(f"OS error on attempt {attempt + 1}: {e}")
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
