#!/usr/bin/env python3
"""
Serial port capture utility for FC-1 console monitoring.
Captures all serial output to a timestamped log file.
"""

import serial
import sys
import os
import signal
from datetime import datetime

# Configuration
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
OUTPUT_FILE = "/tmp/fc1_console_capture.log"

running = True

def signal_handler(sig, frame):
    global running
    running = False
    print(f"\nCapture stopped. Output saved to: {OUTPUT_FILE}")

def main():
    global running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        print(f"Opened {SERIAL_PORT} at {BAUD_RATE} baud")
        print(f"Capturing to: {OUTPUT_FILE}")
        print("Press Ctrl+C to stop capture...")

        with open(OUTPUT_FILE, "w") as f:
            f.write(f"=== Serial capture started at {datetime.now().isoformat()} ===\n")
            f.flush()

            while running:
                try:
                    if ser.in_waiting:
                        data = ser.read(ser.in_waiting)
                        text = data.decode('utf-8', errors='replace')
                        f.write(text)
                        f.flush()
                        # Also print to stdout for live monitoring
                        sys.stdout.write(text)
                        sys.stdout.flush()
                except serial.SerialException as e:
                    print(f"Serial error: {e}")
                    break

            f.write(f"\n=== Serial capture ended at {datetime.now().isoformat()} ===\n")

        ser.close()

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)
    except PermissionError:
        print(f"Permission denied for {SERIAL_PORT}. Try running with sudo or add user to dialout group.")
        sys.exit(1)

if __name__ == "__main__":
    main()
