#!/usr/bin/env python3
import serial
import sys

try:
    ser = serial.Serial('/dev/cu.usbmodem112401', 115200, timeout=1)
    while True:
        line = ser.readline().decode().strip()
        if line:
            print(line)
            sys.stdout.flush()
except KeyboardInterrupt:
    pass
except Exception as e:
    print(f"Error: {e}")
