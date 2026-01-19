# roast_monitor/utils/led.py - LED Status Controller

import time
import board
import digitalio
import asyncio
import supervisor


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