import os
import logging
import re
from pwnagotchi import plugins
from threading import Timer

class BettercapFixer(plugins.Plugin):
    __author__ = "Sagar"
    __version__ = "1.0.0"
    __license__ = "GPL3"
    __description__ = "A plugin that automatically restarts Bettercap if it fails to connect repeatedly."
    
    BETTERCAP_SERV = """
[Unit]
Description=Bettercap service for automatic network attacks
After=default.target

[Service]
ExecStart=/bin/bash -c '/usr/bin/bettercap-launcher; /usr/local/bin/bettercap -log /var/log/bettercap.log'
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
"""

    SERV_PATH = '/etc/systemd/system/bettercap.service'

    def __init__(self):
        self.error_count = 0
        self.max_errors = 5  # Max retries before restarting Bettercap
        self.restart_timer = None
        self.restart_interval = 60  # Time in seconds between automatic restarts if issues persist
        self.api_unavailable_count = 0  # Count of consecutive unavailable API messages
        self.api_check_interval = 30  # Interval to check for API availability (seconds)
        self.api_timeout_limit = 3  # Number of consecutive logs before action is taken
        self.setup_service_file()

    def setup_service_file(self):
        # Write the service file if it doesn't exist
        if not os.path.exists(self.SERV_PATH):
            with open(self.SERV_PATH, 'w') as service_file:
                service_file.write(self.BETTERCAP_SERV)
            logging.info("Created Bettercap service file at /etc/systemd/system/bettercap.service")
        else:
            logging.info("Bettercap service file already exists.")

    def _check_for_errors(self, log_message):
        """Check the log message for connection error patterns."""
        error_patterns = [
            r"can't run my request.*connection to the bettercap endpoint failed",
            r"nobody seems to be listening at the bettercap endpoint",
            r"ConnectionError\(MaxRetryError"
        ]
        return any(re.search(pattern, log_message) for pattern in error_patterns)

    def _check_for_api_unavailability(self, log_message):
        """Check the log message for API unavailability messages."""
        if "waiting for bettercap API to be available" in log_message:
            self.api_unavailable_count += 1
            logging.warning(f"Detected Bettercap API unavailability ({self.api_unavailable_count}/{self.api_timeout_limit}).")
            if self.api_unavailable_count >= self.api_timeout_limit:
                logging.warning(" Bettercap API has been unavailable for too long. Restarting Bettercap...")
                self._restart_bettercap()
        else:
            self.api_unavailable_count = 0  # Reset the counter if the API is available

    def _restart_bettercap(self):
        logging.info("Restarting Bettercap service...")
        os.system(f"systemctl restart {self.bettercap_service}")
        self.error_count = 0  # Reset the error counter after restarting Bettercap
    
    def _schedule_restart(self):
        if self.restart_timer:
            self.restart_timer.cancel()  # Cancel any previous timer
        self.restart_timer = Timer(self.restart_interval, self._restart_bettercap)
        self.restart_timer.start()
        logging.info(f"Scheduled a restart in {self.restart_interval} seconds.")

    def on_internet_available(self, agent):
        logging.info("Internet available, resetting error count.")
        self.error_count = 0  # Reset the error count when the internet is back

    def on_bettercap_connection_error(self, log_message):
        if self._check_for_errors(log_message):
            self.error_count += 1
            logging.warning(f"Detected Bettercap connection error ({self.error_count}/{self.max_errors}).")
            
            if self.error_count >= self.max_errors:
                logging.warning(f" Maximum error threshold reached. Restarting Bettercap.")
                self._restart_bettercap()
            else:
                self._schedule_restart()
        
        # Check for API availability messages
        self._check_for_api_unavailability(log_message)

    def on_unload(self, agent):
        if self.restart_timer:
            self.restart_timer.cancel()
