import time
import subprocess
import logging
import re
from datetime import datetime, timedelta
from threading import Timer
from pwnagotchi.plugins import Plugin

class BluetoothAutoFix(Plugin):
    __author__ = "Sagar"
    __version__ = "2.0.0"
    __license__ = "GPL3"
    __description__ = "Monitors and fixes Bluetooth connection errors, and restarts Pwnagotchi if Bluetooth is disconnected for too long."

    def __init__(self):
        self.error_check_interval = 30  # Check every 30 seconds for errors
        self.device_mac = "AA:AA:AA:AA:AA:AA"  # Replace with your device's MAC address
        self.error_pattern = re.compile(r"Connection refused \(111\)")
        self.timer = None
        self.timeout_minutes = 4  # Restart Pwnagotchi if Bluetooth is disconnected for 10 minutes
        self.was_connected = False
        self.selfrunning = True
        self.last_connected = datetime.now()
        self.remaining_timeout = None
        self._start_monitoring()

    def on_loaded(self):
        logging.info("[BluetoothAutoFix] Plugin loaded.")
        self.selfrunning = True
        self._start_monitoring()

    def on_unload(self, *args):
        self.selfrunning = False
        if self.timer:
            self.timer.cancel()
        logging.info("[BluetoothAutoFix] Plugin unloaded.")

    def _start_monitoring(self):
        self.timer = Timer(self.error_check_interval, self._check_bluetooth_status_and_errors)
        self.timer.start()

    def _check_bluetooth_status_and_errors(self):
        self._check_bluetooth_errors()
        self._check_bluetooth_status()

        # Schedule the next check
        if self.selfrunning:
            self._start_monitoring()

    def _check_bluetooth_errors(self):
        try:
            logs = subprocess.check_output(
                ["journalctl", "-u", "bluetooth", "-n", "50", "--no-pager"],
                universal_newlines=True
            )
            if self.error_pattern.search(logs):
                logging.info("[BluetoothAutoFix] Connection refused (111) detected, attempting to reconnect...")
                self._fix_bluetooth_connection()
        except subprocess.CalledProcessError as e:
            logging.error(f"[BluetoothAutoFix] Error checking Bluetooth logs: {e}")

    def _fix_bluetooth_connection(self):
        try:
            subprocess.run(["sudo", "systemctl", "status", "bluetooth"], check=True)
            subprocess.run(["sudo", "bluetoothctl"], input=f"connect {self.device_mac}\n", text=True)
            logging.info(f"[BluetoothAutoFix] Attempting to connect to device {self.device_mac}.")
            result = subprocess.run(["bluetoothctl", "info", self.device_mac], capture_output=True, text=True)
            if "Connected: yes" in result.stdout:
                logging.info(f"[BluetoothAutoFix] Successfully connected to {self.device_mac}.")
                self.last_connected = datetime.now()
                self.was_connected = True
            else:
                logging.error(f"[BluetoothAutoFix] Failed to connect to {self.device_mac}.")
        except subprocess.CalledProcessError as e:
            logging.error(f"[BluetoothAutoFix] Error reconnecting Bluetooth: {e}")

    def _check_bluetooth_status(self):
        try:
            result = subprocess.run(['bluetoothctl', 'info', self.device_mac], capture_output=True, text=True)
            if 'Connected: yes' in result.stdout:
                self.last_connected = datetime.now()
                if not self.was_connected:
                    logging.info("[BluetoothAutoFix] Bluetooth is connected. Updating last connected time.")
                    self.was_connected = True
                    self.remaining_timeout = None
            else:
                time_disconnected = datetime.now() - self.last_connected
                logging.info(f"[BluetoothAutoFix] Bluetooth disconnected for {time_disconnected}.")
                self.remaining_timeout = self.timeout_minutes * 60 - time_disconnected.total_seconds()
                if self.was_connected:
                    logging.info("[BluetoothAutoFix] Bluetooth has been disconnected.")
                    self.was_connected = False
                if self.remaining_timeout <= 0:
                    logging.info(f"[BluetoothAutoFix] Bluetooth not connected for {self.timeout_minutes} minutes. Restarting Pwnagotchi service.")
                    subprocess.run(['sudo', 'systemctl', 'restart', 'pwnagotchi'], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"[BluetoothAutoFix] Error checking Bluetooth status: {e}")
