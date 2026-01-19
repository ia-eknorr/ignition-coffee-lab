# roast_monitor/outputs/mqtt.py - MQTT output handler for ICL integration

import time
import json
from os import getenv

# CircuitPython specific imports
import adafruit_minimqtt.adafruit_minimqtt as MQTT

from .base import Output
from ..utils import WiFiManager


class MQTTOutput(Output):
    """MQTT output handler for ICL system integration - no SSL support"""
    
    def __init__(self, logger, debug_mode=False):
        super().__init__(logger, debug_mode)
        self.mqtt_client = None
        self.message_count = 0
        
        # Load MQTT configuration from settings.toml
        try:
            self.broker = getenv("MQTT_BROKER")
            self.port = int(getenv("MQTT_PORT", "1883"))
            self.username = getenv("MQTT_USERNAME")
            self.password = getenv("MQTT_PASSWORD")
            
            # Base topic for all device data (individual values published as sub-topics)
            self.base_topic = getenv("MQTT_BASE_TOPIC", "icl/roast_monitor/pico01")
            self.status_topic = getenv("MQTT_STATUS_TOPIC", f"{self.base_topic}/status")

            if not self.broker:
                raise RuntimeError("MQTT broker missing from settings.toml")

            self.logger.info(f"MQTT config loaded - Broker: {self.broker}:{self.port}")
            self.debug("info", f"MQTT base topic: {self.base_topic}")
            self.debug("info", f"MQTT auth: {'Enabled' if self.username else 'Disabled'}")
            
        except Exception as e:
            self.logger.error(f"Failed to load MQTT settings: {e}")
            raise
    
    def requires_wifi(self) -> bool:
        return True
    
    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        if not wifi_manager or not wifi_manager.is_connected:
            self.logger.error("MQTT output handler requires WiFi connection")
            return False
        
        try:
            self.logger.info(f"Connecting to MQTT: {self.broker}:{self.port}")
            self.debug("info", "Starting MQTT client initialization...")
            
            # Create MQTT client with optional authentication
            client_args = {
                "broker": self.broker,
                "port": self.port,
                "socket_pool": wifi_manager.socket_pool,
                "client_id": "icl_roast_monitor_pico_w",
                "keep_alive": 60
            }
            
            if self.username and self.password:
                client_args.update({"username": self.username, "password": self.password})
                self.logger.info(f"Using authentication for user: {self.username}")
                self.debug("info", f"MQTT client args with auth: {client_args}")
            else:
                self.debug("info", f"MQTT client args (no auth): {client_args}")
            
            self.mqtt_client = MQTT.MQTT(**client_args)
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            
            self.debug("info", "Attempting MQTT connection...")
            self.mqtt_client.connect()
            time.sleep(2)
            
            self.debug("info", "MQTT initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MQTT: {e}")
            self.debug("error", f"MQTT init exception details: {type(e).__name__}: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info(f"✅ MQTT connected (code: {rc})")
        self.debug("info", f"MQTT connection details - Client: {client}, Flags: {flags}, RC: {rc}")
        online_status = {
            "status": "online", 
            "device": "icl_roast_monitor_pico_w",
            "timestamp": time.monotonic()
        }
        self.output_status(online_status)
    
    def _on_disconnect(self, client, userdata, rc):
        self.logger.warning(f"🔌 MQTT disconnected (code: {rc})")
        self.debug("warning", f"MQTT disconnect details - Client: {client}, RC: {rc}")
    
    def output_reading(self, reading: dict) -> bool:
        """Publish temperature reading as individual topics for clean Ignition tags."""
        if not self.mqtt_client:
            self.debug("error", "MQTT client not available for publish")
            return False

        try:
            self.mqtt_client.loop()

            # Publish individual values to separate topics
            is_valid = reading["is_valid"]
            topics = {
                "temperature_c": round(reading["temp_celsius"], 2) if is_valid else None,
                "temperature_f": round(reading["temp_fahrenheit"], 2) if is_valid else None,
                "is_valid": is_valid,
                "quality": "good" if is_valid else "sensor_error",
            }

            for name, value in topics.items():
                topic = f"{self.base_topic}/{name}"
                # Convert Python types to MQTT-friendly strings
                if isinstance(value, bool):
                    payload = "true" if value else "false"
                elif value is None:
                    payload = ""
                else:
                    payload = str(value)
                self.mqtt_client.publish(topic, payload)
                self.debug("info", f"Published {topic} = {payload}")

            self.message_count += 1
            temp_str = f"{reading['temp_celsius']:.1f}°C ({reading['temp_fahrenheit']:.1f}°F)" if is_valid else "INVALID"
            self.logger.info(f"📡 MQTT #{self.message_count}: {temp_str}")

            return True
        except Exception as e:
            self.logger.error(f"MQTT publish error: {e}")
            self.debug("error", f"MQTT publish exception: {type(e).__name__}: {e}")
            return False
    
    def output_status(self, status: dict) -> bool:
        if not self.mqtt_client:
            self.debug("error", "MQTT client not available for status publish")
            return False
        
        try:
            json_data = json.dumps(status)
            self.debug("info", f"Publishing status to: {self.status_topic}")
            self.debug("info", f"Status payload: {json_data}")
            
            self.mqtt_client.publish(self.status_topic, json_data)
            self.logger.info(f"📊 MQTT Status: {status.get('status', 'unknown')}")
            
            return True
        except Exception as e:
            self.logger.error(f"MQTT status publish error: {e}")
            self.debug("error", f"MQTT status exception: {type(e).__name__}: {e}")
            return False
    
    def cleanup(self):
        if self.mqtt_client:
            try:
                self.debug("info", "Starting MQTT cleanup...")
                offline_status = {
                    "status": "offline", 
                    "reason": "shutdown",
                    "timestamp": time.monotonic()
                }
                self.output_status(offline_status)
                time.sleep(0.5)
                self.mqtt_client.disconnect()
                self.logger.info("🔌 MQTT disconnected")
                self.debug("info", "MQTT cleanup complete")
            except Exception as e:
                self.logger.error(f"MQTT cleanup error: {e}")
                self.debug("error", f"MQTT cleanup exception: {type(e).__name__}: {e}")