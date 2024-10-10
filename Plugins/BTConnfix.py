import subprocess
import logging
import re
from threading import Timer
from pwnagotchi import plugins

class BluetoothAutoFix(plugins.Plugin):
    __author__ = "SagarBanwa'
    __version__ = "1.0.0"
    __license__ = "GPL3"
    __description__ = 'A plugin that monitors Bluetooth connection errors and automatically fixes them.'
'''
# This plugin will work only once you connect the bluethooth correctly 
# before activating just "sudo bluetoothctl"
# Then "scan on", pair <mac> , trust <mac>
# Allow pair inmobile then here
'''
    def __init__(self):
        self.error_check_interval = 30  # Check for errors every 30 seconds
        self.device_mac = "E0:6D:17:2A:98:31"  # Replace with your device's MAC address
        self.error_pattern = re.compile(r"Connection refused \(111\)")
        self.timer = None
        self._start_monitoring()

    def _start_monitoring(self):
        self.timer = Timer(self.error_check_interval, self._check_bluetooth_errors)
        self.timer.start()

    def _check_bluetooth_errors(self):
        try:
            # Check journalctl logs for connection errors
            logs = subprocess.check_output(
                ["journalctl", "-u", "bluetooth", "-n", "50", "--no-pager"],
                universal_newlines=True
            )
            if self.error_pattern.search(logs):
                logging.info("Connection refused (111) detected, fixing...")
                self._fix_bluetooth_connection()

        except subprocess.CalledProcessError as e:
            logging.error(f"Error checking logs: {e}")

        finally:
            self._start_monitoring()

    def _fix_bluetooth_connection(self):
        try:
            # Check bluetooth status
            subprocess.run(["sudo", "systemctl", "status", "bluetooth"], check=True)

            # Attempt to reconnect to the Bluetooth device
            subprocess.run(["sudo", "bluetoothctl"], input=f"connect {self.device_mac}\n", text=True)
            logging.info(f"Attempting to connect to device {self.device_mac}.")

            # Recheck if the device is connected successfully
            result = subprocess.run(["bluetoothctl", "info", self.device_mac], capture_output=True, text=True)
            if "Connected: yes" in result.stdout:
                logging.info(f"Successfully connected to {self.device_mac}.")
            else:
                logging.error(f"Failed to connect to {self.device_mac}. Retrying...")

        except subprocess.CalledProcessError as e:
            logging.error(f"Error fixing Bluetooth connection: {e}")

    def on_unload(self, agent):
        if self.timer:
            self.timer.cancel()
