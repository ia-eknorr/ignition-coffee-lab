# output_strategies.py - Output strategy implementations for Coffee Roaster Monitor

import time
import json
import asyncio
import hashlib
import binascii
import wifi
from os import getenv

# CircuitPython specific imports
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Local imports
from utilities import WiFiManager


class OutputStrategy:
    """Base strategy for outputting temperature data"""

    def __init__(self, logger, debug_mode=False):
        self.logger = logger
        self.debug_mode = debug_mode

    def debug(self, log_level, message):
        """Debug logging function - only outputs if debug_mode is enabled"""
        if self.debug_mode:
            getattr(self.logger, log_level)(f"[DEBUG] {message}")

    def requires_wifi(self) -> bool:
        raise NotImplementedError("Subclasses must implement requires_wifi()")

    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        raise NotImplementedError("Subclasses must implement initialize()")

    def output_reading(self, reading: dict) -> bool:
        raise NotImplementedError("Subclasses must implement output_reading()")

    def output_status(self, status: dict) -> bool:
        raise NotImplementedError("Subclasses must implement output_status()")

    def cleanup(self):
        raise NotImplementedError("Subclasses must implement cleanup()")


class ConsoleOutputStrategy(OutputStrategy):
    """Output strategy that prints temperature readings to console"""

    def __init__(self, logger, debug_mode=False):
        super().__init__(logger, debug_mode)
        self.debug("info", "Console strategy initialized")

    def requires_wifi(self) -> bool:
        return False

    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        self.debug("info", "Console strategy ready - no initialization required")
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
        self.debug("info", "Console strategy cleanup complete")
        pass


class MQTTOutputStrategy(OutputStrategy):
    """MQTT output strategy - no SSL support"""

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

            self.temp_topic = getenv("MQTT_TEMP_TOPIC", "coffee/roaster/temperature")
            self.status_topic = getenv("MQTT_STATUS_TOPIC", "coffee/roaster/status")

            if not self.broker:
                raise RuntimeError("MQTT broker missing from settings.toml")

            self.logger.info(f"MQTT config loaded - Broker: {self.broker}:{self.port}")
            self.debug("info", f"MQTT topics - Temp: {self.temp_topic}, Status: {self.status_topic}")
            self.debug("info", f"MQTT auth: {'Enabled' if self.username else 'Disabled'}")

        except Exception as e:
            self.logger.error(f"Failed to load MQTT settings: {e}")
            raise

    def requires_wifi(self) -> bool:
        return True

    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        if not wifi_manager or not wifi_manager.is_connected:
            self.logger.error("MQTT strategy requires WiFi connection")
            return False

        try:
            self.logger.info(f"Connecting to MQTT: {self.broker}:{self.port}")
            self.debug("info", "Starting MQTT client initialization...")

            # Create MQTT client with optional authentication
            client_args = {
                "broker": self.broker,
                "port": self.port,
                "socket_pool": wifi_manager.socket_pool,
                "client_id": "coffee_roaster_pico_w",
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
            "device": "thermocouple_pico_w",
            "timestamp": time.monotonic()
        }
        self.output_status(online_status)

    def _on_disconnect(self, client, userdata, rc):
        self.logger.warning(f"🔌 MQTT disconnected (code: {rc})")
        self.debug("warning", f"MQTT disconnect details - Client: {client}, RC: {rc}")

    def _format_reading(self, reading: dict) -> str:
        data = {
            "temperature_c": round(reading["temp_celsius"], 2) if reading["is_valid"] else None,
            "temperature_f": round(reading["temp_fahrenheit"], 2) if reading["is_valid"] else None,
            "timestamp": reading["timestamp"],
            "status": "good" if reading["is_valid"] else "sensor_error",
            "is_valid": reading["is_valid"]
        }
        return json.dumps(data)

    def output_reading(self, reading: dict) -> bool:
        if not self.mqtt_client:
            self.debug("error", "MQTT client not available for publish")
            return False

        try:
            self.mqtt_client.loop()
            json_data = self._format_reading(reading)

            self.debug("info", f"Publishing to topic: {self.temp_topic}")
            self.debug("info", f"Raw JSON payload: {json_data}")

            self.mqtt_client.publish(self.temp_topic, json_data)
            self.message_count += 1

            # Regular output (not debug)
            temp_str = f"{reading['temp_celsius']:.1f}°C ({reading['temp_fahrenheit']:.1f}°F)" if reading["is_valid"] else "INVALID"
            self.logger.info(f"📡 MQTT #{self.message_count}: Sent {temp_str}")

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


class WebSocketOutputStrategy(OutputStrategy):
    """WebSocket output strategy for Artisan Scope integration"""

    # WebSocket constants
    WEBSOCKET_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, logger, temp_unit="C", debug_mode=False):
        super().__init__(logger, debug_mode)
        self.server_socket = None
        self.server_task = None
        self.latest_reading = None
        self.is_running = False
        self.client_count = 0
        self.temp_unit = temp_unit.upper()  # Ensure uppercase

        # Validate temperature unit
        if self.temp_unit not in ["C", "F"]:
            raise ValueError(f"Invalid temperature unit: {temp_unit}. Must be 'C' or 'F'")

        # Load WebSocket configuration from settings.toml
        try:
            self.host = getenv("WEBSOCKET_HOST", "0.0.0.0")
            self.port = int(getenv("WEBSOCKET_PORT", "8765"))

            self.logger.info(f"WebSocket config loaded - Host: {self.host}:{self.port}")
            self.logger.info(f"Preferred temperature unit: {self.temp_unit}")
            self.logger.info(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
            self.debug("info", "WebSocket strategy initialized")

        except Exception as e:
            self.logger.error(f"Failed to load WebSocket settings: {e}")
            raise

    def requires_wifi(self) -> bool:
        return True

    def initialize(self, wifi_manager: WiFiManager = None) -> bool:
        if not wifi_manager or not wifi_manager.is_connected:
            self.logger.error("WebSocket strategy requires WiFi connection")
            return False

        try:
            self.wifi_manager = wifi_manager
            self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

            # Start the WebSocket server task
            self.server_task = asyncio.create_task(self._run_websocket_server())
            self.is_running = True

            self.logger.info("WebSocket server started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket server: {e}")
            return False

    def output_reading(self, reading: dict) -> bool:
        """Store the latest temperature reading for WebSocket clients"""
        try:
            self.latest_reading = reading
            temp_val = reading["temp_celsius"] if self.temp_unit == "C" else reading["temp_fahrenheit"]
            self.debug("info", f"WebSocket: Updated reading to {temp_val:.1f}°{self.temp_unit}")
            return True
        except Exception as e:
            self.logger.error(f"WebSocket reading storage error: {e}")
            return False

    def output_status(self, status: dict) -> bool:
        """Log status information"""
        try:
            status_str = ", ".join([f"{k}: {v}" for k, v in status.items()])
            self.logger.info(f"Status: {status_str}")
            return True
        except Exception as e:
            self.logger.error(f"WebSocket status output error: {e}")
            return False

    def cleanup(self):
        """Clean up WebSocket server resources"""
        self.logger.info("Shutting down WebSocket server...")
        self.debug("info", "Starting WebSocket cleanup...")
        self.is_running = False

        if self.server_task and not self.server_task.done():
            self.server_task.cancel()
            self.debug("info", "WebSocket server task cancelled")

        if self.server_socket:
            try:
                self.server_socket.close()
                self.debug("info", "WebSocket server socket closed")
            except Exception as e:
                self.logger.error(f"Error closing server socket: {e}")

        self.logger.info("🔌 WebSocket server stopped")
        self.debug("info", "WebSocket cleanup complete")

    async def _run_websocket_server(self):
        """Main WebSocket server loop"""
        try:
            # Create server socket
            self.server_socket = self.wifi_manager.socket_pool.socket(
                self.wifi_manager.socket_pool.AF_INET,
                self.wifi_manager.socket_pool.SOCK_STREAM
            )
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)

            self.logger.info(f"✅ WebSocket server listening on {wifi.radio.ipv4_address}:{self.port}")
            self.logger.info("Waiting for Artisan to connect...")

            while self.is_running:
                try:
                    # Accept connections with timeout
                    self.server_socket.settimeout(1.0)
                    client_socket, client_addr = self.server_socket.accept()

                    # Handle client in separate task
                    client_task = asyncio.create_task(
                        self._handle_client(client_socket, client_addr)
                    )

                    # Yield control to allow other tasks to run
                    await asyncio.sleep(0.01)

                except OSError:
                    # Timeout or other socket error - continue loop
                    await asyncio.sleep(0.1)
                    continue
                except Exception as e:
                    if self.is_running:
                        self.logger.error(f"Server error: {e}")
                    break

        except Exception as e:
            self.logger.error(f"WebSocket server failed: {e}")
        finally:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass

    async def _handle_client(self, client_socket, client_addr):
        """Handle individual WebSocket client connection"""
        self.client_count += 1
        client_id = self.client_count

        self.logger.info(f"✅ Client #{client_id} connected from {client_addr}")

        try:
            # Handle WebSocket handshake
            if not await self._handle_handshake(client_socket):
                return

            self.logger.info(f"[Client #{client_id}] WebSocket handshake complete")

            # Main communication loop
            message_count = 0
            buffer = bytearray(1024)

            while self.is_running:
                try:
                    client_socket.settimeout(1.0)  # Shorter timeout to prevent blocking
                    bytes_read = client_socket.recv_into(buffer)

                    if bytes_read == 0:
                        self.debug("info", f"[Client #{client_id}] Connection closed by client")
                        break

                    data = bytes(buffer[:bytes_read])
                    message_count += 1

                    # Parse and handle WebSocket frame
                    await self._handle_websocket_frame(client_socket, client_id, data, message_count)

                    # Yield control to allow other async tasks to run
                    await asyncio.sleep(0.01)

                except OSError:
                    # Timeout or connection error - yield control and continue
                    await asyncio.sleep(0.01)
                    continue
                except Exception as e:
                    self.logger.error(f"[Client #{client_id}] Error: {e}")
                    break

        except Exception as e:
            self.logger.error(f"[Client #{client_id}] Handler error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            self.logger.info(f"🔌 Client #{client_id} disconnected (processed {message_count} messages)")

    async def _handle_handshake(self, client_socket):
        """Handle WebSocket handshake"""
        try:
            # Read HTTP upgrade request
            request = b""
            buffer = bytearray(1024)
            start_time = time.monotonic()

            while b"\r\n\r\n" not in request and time.monotonic() - start_time < 5:
                client_socket.settimeout(0.5)  # Shorter timeout
                bytes_read = client_socket.recv_into(buffer)

                if bytes_read == 0:
                    return False

                request += bytes(buffer[:bytes_read])

                # Yield control periodically during handshake
                await asyncio.sleep(0.01)

            if not request:
                self.logger.error("No HTTP request received")
                return False

            # Parse headers
            request_text = request.decode('utf-8')
            headers = self._parse_http_headers(request_text)
            websocket_key = headers.get('sec-websocket-key')

            if not websocket_key:
                self.logger.error("No Sec-WebSocket-Key found in request")
                return False

            # Calculate accept key and send response
            accept_key = self._calculate_websocket_accept(websocket_key)
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )

            client_socket.send(response.encode())
            return True

        except Exception as e:
            self.logger.error(f"Handshake failed: {e}")
            return False

    async def _handle_websocket_frame(self, client_socket, client_id, data, message_count):
        """Handle incoming WebSocket frame"""
        frame_type, payload = self._parse_websocket_frame(data)

        if frame_type is None:
            self.debug("info", f"[Client #{client_id}] Failed to parse frame")
            return

        if frame_type == "ping":
            # Respond with pong
            pong_frame = self._create_websocket_frame(payload, "pong")
            client_socket.send(pong_frame)
            self.debug("info", f"[Client #{client_id}] Ping/Pong exchange")

        elif frame_type == "pong":
            self.debug("info", f"[Client #{client_id}] Received pong")

        elif frame_type == "close":
            self.logger.info(f"[Client #{client_id}] Received close frame")
            close_frame = self._create_websocket_frame(b"", "close")
            client_socket.send(close_frame)
            return False

        elif frame_type == "text":
            # Handle JSON request from Artisan
            try:
                request_data = json.loads(payload)
                message_id = request_data.get('id', 0)

                self.debug("info", f"[Client #{client_id}] JSON request: {payload}")

                # Get current temperature data in configured unit
                temp_value = 0.0
                if self.latest_reading and self.latest_reading["is_valid"]:
                    if self.temp_unit == "C":
                        temp_value = self.latest_reading["temp_celsius"]
                    else:  # "F"
                        temp_value = self.latest_reading["temp_fahrenheit"]

                    self.debug("info", f"[Client #{client_id}] Using reading: {temp_value:.1f}°{self.temp_unit} (timestamp: {self.latest_reading['timestamp']})")
                else:
                    self.debug("info", f"[Client #{client_id}] No valid reading available")

                # Create response in Artisan's expected format
                # temp1 = Bean Temperature from thermocouple
                # temp2 = 0 (no Environmental Temperature sensor)
                response = {
                    "id": message_id,
                    "data": {
                        "temp1": temp_value,  # BT (Bean Temperature) - input1 in Artisan
                        "temp2": 0.0          # No Environmental Temperature sensor
                    }
                }

                # Send response
                response_json = json.dumps(response)
                self.debug("info", f"[Client #{client_id}] JSON response: {response_json}")

                ws_frame = self._create_websocket_frame(response_json, "text")
                client_socket.send(ws_frame)

                self.logger.info(f"🌐 [Client #{client_id}] Sent: BT={temp_value:.1f}°{self.temp_unit} (temp1)")

            except json.JSONDecodeError as e:
                self.logger.error(f"[Client #{client_id}] JSON parse error: {e}")
                self.debug("error", f"[Client #{client_id}] Raw message was: {payload}")

        return True

    def _base64_encode(self, data):
        """Base64 encoding for CircuitPython"""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        result = ""

        for i in range(0, len(data), 3):
            chunk = data[i:i+3]
            while len(chunk) < 3:
                chunk += b'\x00'

            b1, b2, b3 = chunk[0], chunk[1], chunk[2]
            n = (b1 << 16) | (b2 << 8) | b3

            result += alphabet[(n >> 18) & 63]
            result += alphabet[(n >> 12) & 63]
            result += alphabet[(n >> 6) & 63]
            result += alphabet[n & 63]

        padding_needed = len(data) % 3
        if padding_needed == 1:
            result = result[:-2] + "=="
        elif padding_needed == 2:
            result = result[:-1] + "="

        return result

    def _calculate_websocket_accept(self, websocket_key):
        """Calculate the Sec-WebSocket-Accept value"""
        combined = websocket_key + self.WEBSOCKET_MAGIC_STRING
        sha1 = hashlib.new('sha1')
        sha1.update(combined.encode('utf-8'))
        hash_bytes = sha1.digest()
        return self._base64_encode(hash_bytes)

    def _parse_http_headers(self, request_text):
        """Parse HTTP headers from request"""
        headers = {}
        lines = request_text.split('\r\n')

        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()

        return headers

    def _parse_websocket_frame(self, data):
        """Parse incoming WebSocket frame"""
        if len(data) < 2:
            return None, None

        first_byte = data[0]
        second_byte = data[1]

        fin = (first_byte & 0x80) != 0
        opcode = first_byte & 0x0F
        masked = (second_byte & 0x80) != 0
        payload_len = second_byte & 0x7F

        # Handle extended payload length
        mask_start = 2
        if payload_len == 126:
            if len(data) < 4:
                return None, None
            payload_len = int.from_bytes(data[2:4], 'big')
            mask_start = 4
        elif payload_len == 127:
            if len(data) < 10:
                return None, None
            payload_len = int.from_bytes(data[2:10], 'big')
            mask_start = 10

        # Extract payload
        if masked:
            if len(data) < mask_start + 4 + payload_len:
                return None, None
            mask = data[mask_start:mask_start + 4]
            payload_start = mask_start + 4
            payload = bytearray(data[payload_start:payload_start + payload_len])

            # Unmask payload
            for i in range(len(payload)):
                payload[i] ^= mask[i % 4]
        else:
            if len(data) < mask_start + payload_len:
                return None, None
            payload_start = mask_start
            payload = data[payload_start:payload_start + payload_len]

        # Return frame type and payload
        if opcode == 0x1:  # Text frame
            return "text", payload.decode('utf-8')
        elif opcode == 0x9:  # Ping frame
            return "ping", payload
        elif opcode == 0xA:  # Pong frame
            return "pong", payload
        elif opcode == 0x8:  # Close frame
            return "close", payload
        else:
            return "unknown", payload

    def _create_websocket_frame(self, payload, frame_type="text"):
        """Create a WebSocket frame"""
        if frame_type == "text":
            opcode = 0x81  # Text frame, FIN=1
            payload_bytes = payload.encode('utf-8')
        elif frame_type == "pong":
            opcode = 0x8A  # Pong frame, FIN=1
            payload_bytes = payload if isinstance(payload, bytes) else bytes(payload)
        elif frame_type == "close":
            opcode = 0x88  # Close frame, FIN=1
            payload_bytes = payload if isinstance(payload, bytes) else bytes(payload)
        else:
            raise ValueError(f"Unsupported frame type: {frame_type}")

        payload_len = len(payload_bytes)

        if payload_len < 126:
            header = bytes([opcode, payload_len])
        elif payload_len < 65536:
            header = bytes([opcode, 126]) + payload_len.to_bytes(2, 'big')
        else:
            header = bytes([opcode, 127]) + payload_len.to_bytes(8, 'big')

        return header + payload_bytes
