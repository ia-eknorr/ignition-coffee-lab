# main.py - ICL Roast Monitor

import adafruit_logging

from roast_monitor.outputs import ConsoleOutput, MQTTOutput, ArtisanOutput
from roast_monitor.controller import RoastController


# Configuration
OUTPUT_MODE = "artisan"     # Options: "console", "mqtt", "artisan"
READ_INTERVAL = 1.0         # Seconds between readings
PREFERRED_TEMP_UNIT = "F"   # Temperature unit for single-unit outputs: "C" or "F"
DEBUG_MODE = True

# LED Status Indicators:
# - Short-Short-Pause pattern: Initializing/connecting
# - Three blinks + 3s solid: Successfully connected  
# - Single blink: Data sent successfully
# - Fast blinking: Error/connection problem
# - Use Ctrl+C to stop gracefully

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║              IGNITION COFFEE LAB                     ║")
    print("║                 Roast Monitor v1.0                   ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Set up logging
    logger = adafruit_logging.getLogger("ICL-RoastMonitor")
    logger.setLevel(adafruit_logging.INFO)

    handler = adafruit_logging.StreamHandler()
    formatter = adafruit_logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.handlers = [handler]  # Remove default handler

    try:
        # Initialize output handler
        output_handlers = {
            "console": lambda: ConsoleOutput(logger, debug_mode=DEBUG_MODE),
            "mqtt": lambda: MQTTOutput(logger, debug_mode=DEBUG_MODE),
            "artisan": lambda: ArtisanOutput(logger, temp_unit=PREFERRED_TEMP_UNIT, debug_mode=DEBUG_MODE)
        }
        
        if OUTPUT_MODE not in output_handlers:
            raise ValueError(f"Unknown output mode: {OUTPUT_MODE}. Available: {list(output_handlers.keys())}")
        
        output_handler = output_handlers[OUTPUT_MODE]()

        # Initialize ICL Roast Controller
        controller = RoastController(
            output_handler=output_handler,
            logger=logger,
            debug_mode=DEBUG_MODE
        )

        print(f"🌡️  Output Mode: {output_handler.__class__.__name__}")
        if output_handler.requires_wifi():
            print("📡 WiFi credentials loaded from settings.toml")
        print("💡 LED indicates status - Use Ctrl+C to exit")
        print("🔥 Part of Ignition Coffee Lab automation system")
        print("─" * 54)

        controller.run_continuous(read_interval=READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        print("🔧 Check your configuration and hardware connections")


if __name__ == "__main__":
    main()