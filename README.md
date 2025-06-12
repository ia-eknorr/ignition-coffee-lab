# Ignition Coffee Lab (ICL)

A comprehensive system combining embedded hardware monitoring, industrial SCADA visualization, and professional roast profiling tools for data-driven coffee roasting operations.

## Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Integration Guides](#integration-guides)
- [LED Status Codes](#led-status-codes)
- [Repository Structure](#repository-structure)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Project Overview

**Ignition Coffee Lab** is a complete coffee roasting automation platform that bridges the gap between artisanal roasting and industrial process control, providing:

- **Real-time Temperature Monitoring** via Raspberry Pi Pico W and MAX31855 thermocouple
- **Professional Roast Profiling** with direct Artisan Scope WebSocket integration
- **Industrial SCADA Systems** for process automation and data logging via MQTT
- **Comprehensive Analytics** for roast optimization and quality control

### Use Cases

#### Home Roasting

- Connect to **Artisan Scope** for professional roast profiling
- Log temperature data for consistency analysis
- Monitor multiple roasters simultaneously

#### Commercial Operations

- Integrate with **Ignition SCADA** for full process automation
- Implement quality control and batch tracking
- Generate compliance reports and trend analysis

#### Research & Development

- Collect high-resolution temperature data
- Analyze roast profiles with machine learning
- Optimize roast parameters for specific bean varieties

## System Architecture

```text
┌─────────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  Hardware Layer     │    │  Data Layer      │    │  Application Layer  │
│                     │    │                  │    │                     │
│  Raspberry Pi       │───▶│  MQTT Broker     │───▶│  Ignition SCADA     │
│  Pico W             │    │                  │    │  - HMI              │
│  MAX31855           │    │  InfluxDB        │    │  - Trending         │
│  Type K Probe       │    │  (optional)      │    │  - Alarms           │
│  WiFi               │    │                  │    │  - Reports          │
└─────────────────────┘    └──────────────────┘    └─────────────────────┘
         │                           │                         │
         │                           │                         │
         ▼                           ▼                         ▼
┌─────────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  Artisan Scope      │    │  Analytics       │    │  Mobile/Web         │
│  - Roast Curves     │    │  - ML Models     │    │  - Dashboards       │
│  - Profile Mgmt     │    │  - Quality       │    │  - Remote Mon.      │
│  - Real-time        │    │  - Insights      │    │  - Notifications    │
└─────────────────────┘    └──────────────────┘    └─────────────────────┘
```

## Hardware Requirements

### Essential Components

- **Raspberry Pi Pico W** - CircuitPython compatible microcontroller ($6)
- **MAX31855 Thermocouple Amplifier** - SPI temperature interface ($15)
- **Type K Thermocouple Probe** - High-temperature sensor ($10-30)
- **Breadboard & Jumper Wires** - For prototyping connections ($5)

### Wiring Diagram

```text
 Raspberry Pi Pico W          MAX31855 Amplifier
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  GP18 (SPI SCK)     │────▶ │ SCK  (Clock)        │
│  GP16 (SPI MISO)    │◀──── │ SO   (Data Out)     │
│  GP17 (SPI CS)      │────▶ │ CS   (Chip Select)  │
│  3V3  (Power)       │────▶ │ VCC  (3.3V)         │
│  GND  (Ground)      │────▶ │ GND  (Ground)       │
│                     │      │                     │
│  LED  (Status)      │      │ T+   ──┐            │
│                     │      │ T-   ──┘ Type K     │
└─────────────────────┘      └─────── Thermocouple ┘
```

### Pin Assignments

| Pico W Pin | MAX31855 Pin | Function | Wire Color Suggestion |
|------------|--------------|----------|----------------------|
| GP18 | SCK | SPI Clock | Yellow |
| GP16 | SO (MISO) | SPI Data Out | Blue |
| GP17 | CS | Chip Select | Green |
| 3V3 | VCC | 3.3V Power | Red |
| GND | GND | Ground | Black |

## Quick Start

### 1. Prepare Hardware

```bash
# Download CircuitPython 9.0+ for Pico W from circuitpython.org
# Hold BOOTSEL button while connecting USB
# Copy .uf2 file to RPI-RP2 drive
# Pico will reboot and mount as CIRCUITPY drive
```

### 2. Install Project Files

```bash
# Clone this repository
git clone https://github.com/ia-eknorr/ignition-coffee-lab.git
cd ignition-coffee-lab

# Copy raspberry-pi-pico contents to CIRCUITPY drive
cp -r raspberry-pi-pico/* /Volumes/CIRCUITPY/
```

### 3. Install Required Libraries

The following CircuitPython libraries are required (included in `raspberry-pi-pico/lib/`):

```text
lib/
├── adafruit_minimqtt/                    # MQTT client library
├── asyncio/                              # Asynchronous programming library
├── adafruit_connection_manager.mpy       # WiFi connection manager
├── adafruit_logging.mpy                  # Logging functionality
├── adafruit_max31855.mpy                 # Thermocouple interface
└── adafruit_ticks.mpy                    # Time management
```

Download from [Adafruit CircuitPython Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle) if needed.

### 4. Configure WiFi & Settings

Edit `raspberry-pi-pico/settings.toml`:

```toml
# WiFi Configuration
WIFI_SSID = "YourNetworkName"
WIFI_PASSWORD = "YourPassword"

# MQTT Configuration (for ICL System Integration)
MQTT_BROKER = "192.168.1.100"        # Your MQTT broker IP
MQTT_TEMP_TOPIC = "icl/roast_monitor/pico01/temperature"
MQTT_STATUS_TOPIC = "icl/roast_monitor/pico01/status"

# Artisan Scope Integration
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765
```

### 5. Choose Output Mode

Edit `raspberry-pi-pico/main.py`:

```python
OUTPUT_MODE = "artisan"    # For Artisan Scope
# OUTPUT_MODE = "mqtt"     # For ICL SCADA system
# OUTPUT_MODE = "console"  # For debugging

PREFERRED_TEMP_UNIT = "F"  # "C" or "F"
DEBUG_MODE = False         # Set True for verbose logging
```

### 6. Connect Hardware & Test

1. **Wire components** according to diagram above
2. **Insert thermocouple** into MAX31855 terminals (polarity doesn't matter for Type K)
3. **Power on Pico W** - LED will show initialization pattern
4. **Monitor serial output** for connection status and IP address
5. **Verify temperature readings** in console output

## Configuration

### Basic Settings (`raspberry-pi-pico/settings.toml`)

```toml
# ═══════════════════════════════════════════════════════════
#                  IGNITION COFFEE LAB
#                   Roast Monitor v1.0
# ═══════════════════════════════════════════════════════════

# Network Configuration
WIFI_SSID = "YourNetworkName"
WIFI_PASSWORD = "YourNetworkPassword"

# MQTT Settings (for ICL System Integration)
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = "1883"
MQTT_USERNAME = ""                                    # Optional
MQTT_PASSWORD = ""                                    # Optional
MQTT_TEMP_TOPIC = "icl/roast_monitor/pico01/temperature"
MQTT_STATUS_TOPIC = "icl/roast_monitor/pico01/status"

# Artisan Scope Integration
WEBSOCKET_HOST = "0.0.0.0"                          # Listen on all interfaces
WEBSOCKET_PORT = 8765                                # Standard WebSocket port
```

### Advanced Configuration (`raspberry-pi-pico/main.py`)

```python
# Output Mode Selection
OUTPUT_MODE = "artisan"          # "console", "mqtt", "artisan"

# Measurement Settings
READ_INTERVAL = 1.0              # Seconds between readings
PREFERRED_TEMP_UNIT = "F"        # "C" or "F" for single-unit outputs

# Development Settings
DEBUG_MODE = False               # Enable verbose logging
```

### Multi-Device Deployment

For multiple roasting stations, customize device IDs:

```toml
# Station 1 (Pico01)
MQTT_TEMP_TOPIC = "icl/roast_monitor/pico01/temperature"
MQTT_STATUS_TOPIC = "icl/roast_monitor/pico01/status"

# Station 2 (Pico02)
MQTT_TEMP_TOPIC = "icl/roast_monitor/pico02/temperature"
MQTT_STATUS_TOPIC = "icl/roast_monitor/pico02/status"
```

## Integration Guides

### Artisan Scope Integration

1. **Configure Roast Monitor**

   ```python
   OUTPUT_MODE = "artisan"
   PREFERRED_TEMP_UNIT = "C"  # or "F"
   ```

2. **Setup Artisan Scope**
   - Open Artisan → **Config** → **Device** → **WebSocket**
   - Set URL: `ws://[pico_ip_address]:8765`
   - Configure **BT (Bean Temperature)** as **input1**
   - Leave **ET (Environmental Temperature)** unconfigured

3. **Start Monitoring**
   - Click **ON** in Artisan to connect
   - Begin logging to capture temperature curves
   - Monitor real-time temperature during roasting

4. **Data Format**

   ```json
   {
     "id": 1,
     "data": {
       "temp1": 150.5,    // Bean Temperature (BT)
       "temp2": 0.0       // Environmental Temperature (unused)
     }
   }
   ```

### ICL SCADA Integration (MQTT)

1. **Configure Roast Monitor**

   ```python
   OUTPUT_MODE = "mqtt"
   ```

2. **MQTT Broker Setup**
   - Install Mosquitto, HiveMQ, or similar
   - Configure authentication (optional)
   - Ensure network connectivity

3. **Topic Structure**

   ```text
   icl/roast_monitor/[device_id]/temperature
   icl/roast_monitor/[device_id]/status
   ```

4. **Data Format**

   ```json
   {
     "temperature_c": 150.5,
     "temperature_f": 302.9,
     "timestamp": 1699123456.78,
     "device_id": "pico01",
     "status": "good",
     "is_valid": true
   }
   ```

5. **Ignition SCADA Setup** *(Future)*
   - Create MQTT connection in Ignition
   - Subscribe to `icl/roast_monitor/+/temperature`
   - Build HMI screens for monitoring
   - Configure trending and alarms

## LED Status Codes

The onboard LED provides visual feedback for system status:

| LED Pattern | Status | Description |
|-------------|--------|-------------|
| **Short-Short-Pause** (repeating) | Initializing | System starting up, connecting to WiFi |
| **3 Blinks → Solid 3sec** | Connected | Successfully connected to network/service |
| **Single Quick Blink** | Data Sent | Temperature reading transmitted successfully |
| **Fast Blinking** | Error | Connection problem or hardware fault |
| **Solid On** | Startup Complete | Initialization successful (brief) |
| **Off** | Normal Operation | Steady state monitoring |

### LED Troubleshooting

- **Continuous fast blinking**: Check WiFi credentials or MQTT broker
- **No LED activity**: Verify CircuitPython installation and main.py
- **Short-Short-Pause forever**: WiFi connection failing
- **Single blinks stopped**: Check thermocouple connection

## Repository Structure

```text
ignition-coffee-lab/                    # Monorepo root
├── README.md                           # This comprehensive guide
├── raspberry-pi-pico/                  # Hardware monitoring system
│   ├── main.py                        # Application entry point
│   ├── settings.toml                  # Configuration file
│   ├── roast_monitor/                 # Main Python package
│   │   ├── __init__.py               # Package initialization
│   │   ├── thermocouple.py           # ThermocoupleMonitor class
│   │   ├── controller.py             # RoastController orchestration
│   │   ├── outputs/                  # Output handler modules
│   │   │   ├── __init__.py          # Output package exports
│   │   │   ├── base.py              # Abstract Output base class
│   │   │   ├── console.py           # Console/serial output
│   │   │   ├── mqtt.py              # MQTT publishing
│   │   │   └── artisan.py           # Artisan WebSocket server
│   │   └── utils/                    # Utility modules
│   │       ├── __init__.py          # Utility package exports
│   │       ├── led.py               # LED status controller
│   │       └── wifi.py              # WiFi connection manager
│   ├── lib/                          # CircuitPython libraries
│   │   ├── adafruit_max31855.mpy    # Thermocouple interface
│   │   ├── adafruit_minimqtt/        # MQTT client library
│   │   └── adafruit_logging.mpy     # Logging functionality
│   └── docs/                         # Hardware-specific documentation
├── ignition-scada/                    # Future: SCADA project files
└── docs/                             # Shared project documentation
```

### Key Components

**`raspberry-pi-pico/roast_monitor/`** - Main monitoring package

- **`thermocouple.py`** - Core temperature monitoring with MAX31855
- **`controller.py`** - System orchestration and coordination
- **`outputs/`** - Pluggable output handlers for different integrations
- **`utils/`** - Supporting utilities for LED and WiFi management

## Troubleshooting

### Common Issues

#### No Temperature Readings

```text
Symptoms: Console shows "Invalid temperature reading"
Root Causes:
- Loose thermocouple connections
- Incorrect SPI wiring between Pico W and MAX31855
- Faulty MAX31855 chip or thermocouple
- Power supply issues (check 3.3V)

Solutions:
1. Verify all wiring connections with multimeter
2. Check thermocouple polarity (though Type K is non-polarized)
3. Test with known good thermocouple probe
4. Measure 3.3V power supply voltage
5. Try different MAX31855 breakout board
```

#### WiFi Connection Fails

```text
Symptoms: LED shows continuous Short-Short-Pause pattern
Root Causes:
- Incorrect WiFi credentials in settings.toml
- Network out of range or interference
- Router firewall or security settings
- CircuitPython WiFi driver issues

Solutions:
1. Double-check SSID and password in settings.toml
2. Move Pico W closer to router for testing
3. Try connecting to different WiFi network
4. Check for special characters in WiFi password
5. Reset Pico W and re-flash CircuitPython
6. Verify network allows IoT device connections
```

#### MQTT Connection Issues

```text
Symptoms: "MQTT connection failed" errors in console
Root Causes:
- MQTT broker unreachable or down
- Incorrect broker IP address or port
- Authentication failures
- Network firewall blocking MQTT port 1883
- Broker at capacity or rejecting connections

Solutions:
1. Ping MQTT broker from same network
2. Verify broker IP and port (usually 1883 for non-SSL)
3. Check username/password if authentication enabled
4. Test MQTT broker with desktop client (MQTT Explorer, mosquitto_pub)
5. Check broker logs for connection rejections
6. Verify firewall allows port 1883
```

#### Artisan Can't Connect

```text
Symptoms: Artisan shows "Connection failed" when trying to connect
Root Causes:
- Incorrect WebSocket URL in Artisan
- Port 8765 blocked by firewall
- Pico W and computer on different network segments
- Artisan device configuration error

Solutions:
1. Verify Pico W IP address from serial console output
2. Test WebSocket manually: ws://[pico_ip]:8765
3. Ensure both devices on same network/VLAN
4. Check computer firewall allows outbound port 8765
5. Verify Artisan WebSocket device configuration
6. Try connecting from different computer on same network
```

#### Temperature Readings Seem Wrong

```text
Symptoms: Temperature values are unrealistic or unstable
Root Causes:
- Thermocouple not properly inserted in coffee beans
- Electrical interference from roaster or other equipment
- Poor connections causing noise
- Thermocouple damaged or degraded

Solutions:
1. Ensure thermocouple probe is fully inserted in bean mass
2. Check for loose connections on breadboard
3. Route thermocouple wire away from power cables
4. Test thermocouple with multimeter (should read ~0V at room temp)
5. Try different thermocouple probe
6. Add ferrite bead to thermocouple cable if interference suspected
```

### Advanced Debugging

#### Enable Debug Mode

```python
# In raspberry-pi-pico/main.py
DEBUG_MODE = True
```

#### Serial Console Monitoring

```bash
# macOS/Linux
screen /dev/tty.usbmodem* 115200

# Windows
# Use PuTTY or Tera Term
# Port: COMx, Baud: 115200
```

#### Network Diagnostics

```python
# Add to main.py for network testing
import wifi
print(f"IP Address: {wifi.radio.ipv4_address}")
print(f"Signal Strength: {wifi.radio.ap_info.rssi} dBm")
print(f"MAC Address: {wifi.radio.mac_address}")
```

#### MQTT Testing

```bash
# Test MQTT broker connectivity
mosquitto_pub -h [broker_ip] -t "test/topic" -m "test message"
mosquitto_sub -h [broker_ip] -t "icl/roast_monitor/+/temperature"
```

## Development

### Setting Up Development Environment

1. **CircuitPython Installation**
   - Download latest CircuitPython for Pico W from [circuitpython.org](https://circuitpython.org)
   - Hold BOOTSEL while connecting USB to enter bootloader mode
   - Copy .uf2 file to mounted drive

2. **Library Management**
   - Download [Adafruit CircuitPython Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle)
   - Copy required .mpy files to lib/ directory

3. **Code Editor Setup**
   - **VS Code** with CircuitPython extension (recommended)
   - **Thonny** for beginners
   - **Mu Editor** for educational use

### Adding New Features

#### Custom Output Handler

```python
# Create new file: raspberry-pi-pico/roast_monitor/outputs/custom.py
from .base import Output

class CustomOutput(Output):
    def requires_wifi(self) -> bool:
        return True  # or False

    def initialize(self, wifi_manager=None) -> bool:
        # Setup code here
        return True

    def output_reading(self, reading: dict) -> bool:
        # Handle temperature data
        return True

    def cleanup(self):
        # Cleanup code here
        pass

# Add to raspberry-pi-pico/roast_monitor/outputs/__init__.py
from .custom import CustomOutput
__all__.append('CustomOutput')
```

#### Additional Sensors

```python
# Extend raspberry-pi-pico/roast_monitor/thermocouple.py
class MultiSensorMonitor(ThermocoupleMonitor):
    def __init__(self, logger):
        super().__init__(logger)
        # Initialize additional sensors (humidity, pressure, etc.)

    def read_temperature(self) -> dict:
        # Read from multiple sensors and combine data
        pass
```

### Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-sensor`
3. **Make changes** with proper documentation and comments
4. **Test thoroughly** on actual hardware setup
5. **Submit pull request** with clear description and test results

## Community & Support

### Getting Help

- **Hardware Issues**: Check troubleshooting section above
- **Software Bugs**: [GitHub Issues](https://github.com/your-org/ignition-coffee-lab/issues)
- **General Questions**: [GitHub Discussions](https://github.com/your-org/ignition-coffee-lab/discussions)
- **Feature Requests**: [GitHub Issues](https://github.com/your-org/ignition-coffee-lab/issues) with "enhancement" label

### Documentation

- **Hardware Guides**: Additional wiring diagrams and assembly instructions
- **Software Tutorials**: Video walkthroughs of setup and configuration
- **Integration Examples**: Sample configurations for popular setups

### Hardware Support

- **CircuitPython**: [Official Documentation](https://circuitpython.org/)
- **Raspberry Pi**: [Pico W Documentation](https://www.raspberrypi.org/documentation/microcontrollers/)
- **Adafruit**: [MAX31855 Learning Guide](https://learn.adafruit.com/thermocouple)

## License

MIT License - Open source for the coffee community

Full license text available in [LICENSE](./LICENSE) file.

---

**Ignition Coffee Lab** - *Precision monitoring for data-driven coffee roasting*

*Bridging artisanal craft with industrial automation* ☕
