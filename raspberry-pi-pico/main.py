# main.py - Main execution script for Coffee Roaster Temperature Monitor

import adafruit_logging

# Local imports
from output_strategies import ConsoleOutputStrategy, MQTTOutputStrategy, WebSocketOutputStrategy
from roaster import RoasterController


# Configuration
OUTPUT_MODE = "websocket"    # Options: "console", "mqtt", "websocket"
READ_INTERVAL = 1.0  		# Seconds between readings
PREFERRED_TEMP_UNIT = "F"   # Temperature unit for single-unit strategies: "C" or "F"
                            # Note: Console and MQTT strategies send both units regardless
DEBUG_MODE = False

# LED Status Indicators:
# - Short-Short-Pause pattern: Initializing/connecting (starts immediately)
# - Three blinks + 3s solid: Successfully connected  
# - Single blink: Data sent
# - Fast blinking: Error/problem
# - Use Ctrl+C to stop the program gracefully

if __name__ == "__main__":
    print("Ignition Coffee Lab Temperature Monitor")
    print("======================================================")

    # Set up clean logging
    logger = adafruit_logging.getLogger("CoffeeRoaster")
    logger.setLevel(adafruit_logging.INFO)

    handler = adafruit_logging.StreamHandler()
    formatter = adafruit_logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Remove the default handler to avoid duplicate messages
    logger.handlers = [handler]

    try:
        if OUTPUT_MODE == "console":
            strategy = ConsoleOutputStrategy(logger, debug_mode=DEBUG_MODE)
        elif OUTPUT_MODE == "mqtt":
            strategy = MQTTOutputStrategy(logger, debug_mode=DEBUG_MODE)
        elif OUTPUT_MODE == "websocket":
            strategy = WebSocketOutputStrategy(logger, temp_unit=PREFERRED_TEMP_UNIT, debug_mode=DEBUG_MODE)
        else:
            raise ValueError(f"Unknown output mode: {OUTPUT_MODE}")

        controller = RoasterController(
            output_strategy=strategy,
            logger=logger
        )

        print(f"Using {strategy.__class__.__name__}")
        if strategy.requires_wifi():
            print("WiFi credentials loaded from settings.toml")
        print("LED indicates status - Use Ctrl+C to exit")
        print("---")

        controller.run_continuous(read_interval=READ_INTERVAL)

    except Exception as e:
        print(f"Failed to start: {e}")
        print("Check your configuration and hardware connections")
