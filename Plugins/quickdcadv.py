import os
import logging
import subprocess
import string
import re
import pwnagotchi.plugins as plugins
import qrcode
import io

class QuickDic(plugins.Plugin):
    __GitHub__ = "https://github.com/sagarbanwa/pwnagotchi/"
    __author__ = 'Sagar Banwa'
    __modified_by__ = '@sagarbanwa'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Run a small aircrack scan against captured handshakes and PMKID'
    __name__ = 'QuickDic'
    __help__ = 'Run a small aircrack scan against captured handshakes and PMKID'
    __dependencies__ = {
        "apt": ["aircrack-ng"],
        "pip": ["scapy", "qrcode"],  # Ensure qrcode is included as a dependency
    }
    __defaults__ = {
        "enabled": False,
        "wordlist_folder": "/home/pi/wordlist/",
        "handshake_folder": "/root/handshakes/",
        "cracked_folder": "/home/pi/cracked/",
        "tracking_file": "/home/pi/handshake_tracking.txt",
        "face": "(·ω·)",
        "api": None,
        "id": None,
    }

    def __init__(self):
        self.ready = False
        logging.debug(f"[{self.__class__.__name__}] Plugin initialized.")
        self.title = ""
        self.text_to_set = ""

    def on_loaded(self):
        logging.info(f"[{self.__class__.__name__}] Plugin loaded.")
        self.options.setdefault("face", "(·ω·)")
        self.options.setdefault("wordlist_folder", "/home/pi/wordlist/")
        self.options.setdefault("handshake_folder", "/root/handshakes/")
        self.options.setdefault("cracked_folder", "/home/pi/cracked/")
        self.options.setdefault("tracking_file", "/home/pi/handshake_tracking.txt")
        self.options.setdefault("enabled", False)
        self.options.setdefault("api", None)
        self.options.setdefault("id", None)

        # Ensure directories exist
        os.makedirs(self.options["cracked_folder"], exist_ok=True)

        # Check if aircrack-ng is installed
        try:
            check = subprocess.run(
                ["/usr/bin/dpkg", "-l", "aircrack-ng"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if "aircrack-ng" in check.stdout.decode():
                logging.info(f"[{self.__class__.__name__}] aircrack-ng is installed.")
            else:
                logging.warning(f"[{self.__class__.__name__}] aircrack-ng is not installed!")
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Error checking aircrack-ng: {str(e)}")

    def on_handshake(self, agent, filename=None, access_point=None, client_station=None):
        display = agent.view()

        handshake_folder = self.options["handshake_folder"]
        wordlist_folder = self.options["wordlist_folder"]
        cracked_folder = self.options["cracked_folder"]
        tracking_file = self.options["tracking_file"]

        cracked_handshakes = set()
        if os.path.exists(tracking_file):
            with open(tracking_file, "r") as f:
                cracked_handshakes = set(line.strip() for line in f.readlines())

        handshake_files = [f for f in os.listdir(handshake_folder) if f.endswith(".cap") or f.endswith(".pcap")]

        for handshake_file in handshake_files:
            full_handshake_path = os.path.join(handshake_folder, handshake_file)

            if handshake_file in cracked_handshakes:
                logging.info(f"[{self.__class__.__name__}] Handshake {handshake_file} already cracked, skipping.")
                continue

            try:
                logging.info(f"[{self.__class__.__name__}] Processing handshake: {handshake_file}")
                
                # Extract BSSID from the handshake file
                list_command = ["aircrack-ng", "-J", full_handshake_path]
                result_list = subprocess.run(list_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result_output = result_list.stdout.decode()

                # Search for the BSSID in aircrack-ng output (a valid MAC address pattern)
                bssid_match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", result_output)
                if not bssid_match:
                    logging.error(f"[{self.__class__.__name__}] No valid BSSID found for {handshake_file}. Skipping.")
                    continue

                bssid = bssid_match.group(0)
                logging.info(f"[{self.__class__.__name__}] Found BSSID: {bssid}")

                wordlist_files = [os.path.join(wordlist_folder, f) for f in os.listdir(wordlist_folder) if f.endswith(".txt")]

                for wordlist in wordlist_files:
                    crack_command = [
                        "aircrack-ng", "-w", wordlist, "-l", os.path.join(cracked_folder, handshake_file + ".cracked"),
                        "-q", "-b", bssid, full_handshake_path
                    ]
                    result_crack = subprocess.run(crack_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    result_crack_output = result_crack.stdout.decode()

                    logging.info(f"[{self.__class__.__name__}] {result_crack_output}")

                    if "KEY NOT FOUND" not in result_crack_output:
                        key = re.search(r"\[(.*)\]", result_crack_output)
                        if key:
                            pwd = key.group(1)
                            logging.info(f"[{self.__class__.__name__}] Cracked password for {handshake_file}: {pwd}")
                            
                            with open(tracking_file, "a") as f:
                                f.write(handshake_file + "\n")
                            break  # Stop after finding the password
                    else:
                        logging.info(f"[{self.__class__.__name__}] Key not found for {handshake_file}. Trying next wordlist.")

            except Exception as e:
                logging.error(f"[{self.__class__.__name__}] Error processing handshake: {str(e)}")
                display.set("status", "Error processing handshake. Check logs.")
                display.update(force=True)

    def _send_message(self, filename, pwd):
        try:
            base_filename = os.path.splitext(os.path.basename(filename))[0]
            ssid = base_filename.split("_")[0]  # Extract SSID from filename
            security = "WPA"
            wifi_config = f"WIFI:S:{ssid};T:{security};P:{pwd};;"

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(wifi_config)
            qr.make(fit=True)

            q = io.StringIO()
            qr.print_ascii(out=q)
            q.seek(0)

            message_text = f"\nSSID: {ssid}\nPassword: {pwd}\n```\n{q.read()}\n```"
            # Uncomment and configure the below when you have Telegram bot ready:
            #bot = Bot(token=self.options["9999999:AAHe8DwoM7AAAXbDvlCggHtoAAAAA92bRq0"])
            #bot.send_message(chat_id=self.options["99999999"], text=message_text, parse_mode="Markdown")

            logging.info(f"[{self.__class__.__name__}] QR code content sent to Telegram.")
            logging.info(message_text)
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Error sending QR code to Telegram: {str(e)}")

    def on_ui_update(self, ui):
        if self.text_to_set:
            ui.set("face", self.options["face"])
            ui.set("status", self.text_to_set)
            self.text_to_set = ""

    def on_unload(self, ui):
        with ui._lock:
            logging.info(f"[{self.__class__.__name__}] Plugin unloaded.")

    def on_webhook(self, path, request):
        logging.info(f"[{self.__class__.__name__}] Webhook pressed at path: {path}.")
        return f"Cracking handshakes... Check logs for updates.", 200  # Show the current cracking status
