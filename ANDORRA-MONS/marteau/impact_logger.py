#!/usr/bin/env python3
"""
Impact Logger - Monitors Teensy serial output and logs impact filenames to CSV
"""

import serial
import csv
import time
import re
import os
from datetime import datetime
import argparse

class ImpactLogger:
    def __init__(self, port, baudrate=115200, csv_file="impact_log.csv"):
        self.port = port
        self.baudrate = baudrate
        self.csv_file = csv_file
        self.impact_count = 0
        self.ser = None

        # Initialize CSV file with headers if it doesn't exist
        self.init_csv()

    def init_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['impact_number', 'filename', 'timestamp', 'datetime'])
            print(f"Created new CSV file: {self.csv_file}")

    def connect_serial(self):
        """Connect to the Teensy via serial"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False

    def log_impact(self, filename):
        """Log impact data to CSV"""
        self.impact_count += 1
        timestamp = time.time()
        dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        with open(self.csv_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.impact_count, filename, timestamp, dt])

        print(f"Impact #{self.impact_count}: {filename} logged at {dt}")

    def monitor_impacts(self):
        """Monitor serial output for impact filenames"""
        if not self.connect_serial():
            return

        print("Monitoring for impacts... Press Ctrl+C to stop")
        print(f"Logging to: {self.csv_file}")
        print("-" * 50)

        try:
            while True:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()

                    # Look for FILENAME: pattern
                    if line.startswith("FILENAME:"):
                        filename = line.replace("FILENAME:", "").strip()
                        self.log_impact(filename)

                time.sleep(0.01)  # Small delay to prevent excessive CPU usage

        except KeyboardInterrupt:
            print("\nStopping impact logger...")
        except Exception as e:
            print(f"Error during monitoring: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("Serial connection closed")

def main():
    parser = argparse.ArgumentParser(description='Monitor Teensy for impact detection and log filenames')
    parser.add_argument('--port', '-p', required=True, help='Serial port (e.g., /dev/ttyACM0 or COM3)')
    parser.add_argument('--baudrate', '-b', default=115200, type=int, help='Serial baudrate (default: 115200)')
    parser.add_argument('--csv', '-c', default='impact_log.csv', help='CSV output file (default: impact_log.csv)')

    args = parser.parse_args()

    logger = ImpactLogger(args.port, args.baudrate, args.csv)
    logger.monitor_impacts()

if __name__ == "__main__":
    main()
