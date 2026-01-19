# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ignition Coffee Lab (ICL) - A coffee roasting automation platform using Raspberry Pi Pico W with MAX31855 thermocouple for temperature monitoring. Integrates with Artisan Scope (WebSocket) and industrial SCADA systems (MQTT).

## Development Environment

This is a **CircuitPython** project for Raspberry Pi Pico W. Code runs directly on the microcontroller - there's no build step or traditional test framework.

### Deploying Code

```bash
# Copy project files to the Pico W (mounted as CIRCUITPY drive)
cp -r raspberry-pi-pico/* /Volumes/CIRCUITPY/
```

### Serial Console (for debugging)

```bash
screen /dev/tty.usbmodem* 115200
```

### Linting

```bash
pre-commit run --all-files  # yaml, markdown, trailing whitespace checks
```

## Architecture

### Core Pattern: Strategy-based Output Handlers

The system uses a pluggable output strategy pattern:

```
main.py → RoastController → Output (base class)
                              ├── ConsoleOutput (debugging)
                              ├── MQTTOutput (SCADA integration)
                              └── ArtisanOutput (WebSocket server)
```

- **`RoastController`** (`controller.py`): Orchestrates thermocouple reading, WiFi, LED status, and output handling
- **`ThermocoupleMonitor`** (`thermocouple.py`): Hardware abstraction for MAX31855 SPI interface
- **`Output` subclasses** (`outputs/`): Each implements `requires_wifi()`, `initialize()`, `output_reading()`, `output_status()`, `cleanup()`

### Adding a New Output Handler

1. Create `raspberry-pi-pico/roast_monitor/outputs/your_output.py`
2. Subclass `Output` and implement all abstract methods
3. Export in `outputs/__init__.py`
4. Add to `output_handlers` dict in `main.py`

### Configuration

- **Runtime config**: `main.py` - `OUTPUT_MODE`, `READ_INTERVAL`, `PREFERRED_TEMP_UNIT`, `DEBUG_MODE`
- **Secrets/network**: `settings.toml` - WiFi credentials, MQTT broker, WebSocket port

### Hardware Pin Mapping

GP18=SPI SCK, GP16=SPI MISO, GP17=SPI CS (for MAX31855 thermocouple)

## CircuitPython Constraints

- No pip/package manager - copy `.mpy` files to `lib/` directory
- Limited memory - prefer generators and avoid large data structures
- No threading - uses `asyncio` for concurrent operations
- Libraries in `lib/`: `adafruit_max31855`, `adafruit_minimqtt`, `adafruit_logging`, `asyncio`