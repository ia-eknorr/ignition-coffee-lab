import wifi
import socketpool
import time
import random
import hashlib
import binascii
import os

# WebSocket constants
WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
WS_OP_TEXT = 0x1
WS_OP_CLOSE = 0x8

def connect_to_wifi():
    """Connect to WiFi using credentials from settings.toml"""
    ssid = os.getenv('WIFI_SSID')
    password = os.getenv('WIFI_PASSWORD')
    
    if not ssid or not password:
        raise ValueError("WIFI_SSID and WIFI_PASSWORD must be set in settings.toml")
    
    print(f"Connecting to {ssid}...")
    wifi.radio.connect(ssid, password)
    
    while not wifi.radio.connected:
        time.sleep(0.1)
    
    print(f"Connected! IP: {wifi.radio.ipv4_address}")
    return wifi.radio.ipv4_address

def create_websocket_accept_key(client_key):
    """Create WebSocket accept key from client key"""
    combined = client_key + WS_MAGIC_STRING
    sha1_hash = hashlib.sha1(combined.encode()).digest()
    return binascii.b2a_base64(sha1_hash).decode().strip()

def parse_websocket_frame(data):
    """Parse a WebSocket frame and return the payload"""
    if len(data) < 2:
        return None
    
    # Get the second byte to check payload length
    payload_len = data[1] & 0x7F
    mask_start = 2
    
    if payload_len == 126:
        payload_len = (data[2] << 8) | data[3]
        mask_start = 4
    elif payload_len == 127:
        # 64-bit length not supported in this simple implementation
        return None
    
    if len(data) < mask_start + 4:
        return None
    
    # Extract mask
    mask = data[mask_start:mask_start + 4]
    payload_start = mask_start + 4
    
    if len(data) < payload_start + payload_len:
        return None
    
    # Unmask payload
    payload = bytearray()
    for i in range(payload_len):
        payload.append(data[payload_start + i] ^ mask[i % 4])
    
    return payload.decode('utf-8')

def create_websocket_frame(text):
    """Create a WebSocket text frame"""
    payload = text.encode('utf-8')
    payload_len = len(payload)
    
    if payload_len < 126:
        frame = bytearray([0x80 | WS_OP_TEXT, payload_len])
    elif payload_len < 65536:
        frame = bytearray([0x80 | WS_OP_TEXT, 126])
        frame.extend([(payload_len >> 8) & 0xFF, payload_len & 0xFF])
    else:
        # Large payloads not supported in this simple implementation
        return None
    
    frame.extend(payload)
    return bytes(frame)

def simple_json_parse(json_str):
    """Very basic JSON parser for simple objects"""
    try:
        # Remove whitespace and check for object
        json_str = json_str.strip()
        if not json_str.startswith('{') or not json_str.endswith('}'):
            return {}
        
        # Extract content between braces
        content = json_str[1:-1].strip()
        if not content:
            return {}
        
        result = {}
        # Split by comma and parse key-value pairs
        pairs = content.split(',')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip()
                
                # Parse value
                if value.startswith('"') and value.endswith('"'):
                    result[key] = value[1:-1]
                elif value.isdigit():
                    result[key] = int(value)
                elif value.replace('.', '').isdigit():
                    result[key] = float(value)
                else:
                    result[key] = value
        
        return result
    except:
        return {}

def simple_json_dumps(obj):
    """Very basic JSON serializer"""
    if isinstance(obj, dict):
        pairs = []
        for key, value in obj.items():
            if isinstance(value, str):
                pairs.append(f'"{key}": "{value}"')
            elif isinstance(value, dict):
                pairs.append(f'"{key}": {simple_json_dumps(value)}')
            else:
                pairs.append(f'"{key}": {value}')
        return '{' + ', '.join(pairs) + '}'
    return str(obj)

def handle_websocket_client(client_socket):
    """Handle WebSocket client connection"""
    print("Client connected")
    
    try:
        # Receive HTTP upgrade request
        request = client_socket.recv(1024).decode('utf-8')
        print("Received request")
        
        # Parse WebSocket key from headers
        ws_key = None
        for line in request.split('\r\n'):
            if line.startswith('Sec-WebSocket-Key:'):
                ws_key = line.split(':', 1)[1].strip()
                break
        
        if not ws_key:
            print("No WebSocket key found")
            client_socket.close()
            return
        
        # Create WebSocket accept key
        accept_key = create_websocket_accept_key(ws_key)
        
        # Send WebSocket handshake response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n"
            "\r\n"
        )
        client_socket.send(response.encode('utf-8'))
        print("WebSocket handshake complete")
        
        # Handle WebSocket messages
        while True:
            try:
                # Receive WebSocket frame
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Parse frame
                message = parse_websocket_frame(data)
                if message:
                    print(f"Received: {message}")
                    
                    # Parse request
                    request_data = simple_json_parse(message)
                    message_id = request_data.get('id', 0)
                    
                    # Generate random number
                    value = round(random.uniform(100, 200), 1)
                    
                    # Create response
                    response = {
                        "id": message_id,
                        "data": {
                            "input1": value
                        }
                    }
                    
                    # Send response
                    response_json = simple_json_dumps(response)
                    frame = create_websocket_frame(response_json)
                    if frame:
                        client_socket.send(frame)
                        print(f"Sent: {value}")
                
            except Exception as e:
                print(f"Error handling message: {e}")
                break
    
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        client_socket.close()
        print("Client disconnected")

def main():
    # Connect to WiFi
    try:
        ip_address = connect_to_wifi()
    except Exception as e:
        print(f"WiFi connection failed: {e}")
        return
    
    # Create socket pool
    pool = socketpool.SocketPool(wifi.radio)
    
    # Create server socket
    server_socket = pool.socket(socketpool.AF_INET, socketpool.SOCK_STREAM)
    server_socket.setsockopt(socketpool.SOL_SOCKET, socketpool.SO_REUSEADDR, 1)
    
    # Bind to address
    host = str(ip_address)
    port = 8765
    server_socket.bind((host, port))
    server_socket.listen(1)
    
    print(f"WebSocket server listening on {host}:{port}")
    print("Server ready")
    
    # Accept connections
    while True:
        try:
            client_socket, client_addr = server_socket.accept()
            print(f"Connection from {client_addr}")
            handle_websocket_client(client_socket)
        except Exception as e:
            print(f"Server error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Fatal error: {e}")