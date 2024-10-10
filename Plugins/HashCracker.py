import os
import logging
import subprocess
import re
import pwnagotchi.plugins as plugins
import io

class HashCracker(plugins.Plugin):
    __GitHub__ = ""
    __author__ = 'SagarBanwa'
    __modified_by__ = '@sagarbanwa'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Crack .22000 (EAPOL) and .16800 (PMKID) handshakes'
    __name__ = 'HashCracker'
    __help__ = 'Crack .22000 (EAPOL) and .16800 (PMKID) handshakes using hashcat'
    __dependencies__ = {
        "apt": ["hashcat"],
        "pip": [],
    }
    __defaults__ = {
        "enabled": False,
        "wordlist": "/home/pi/wordlist/rockyou.txt",
        "handshake_folder": "/root/handshakes/",
        "status_file": "/root/handshakes/crack_status.txt",
        "face": "(·ω·)"
    }

    def __init__(self):
        self.ready = False
        logging.debug(f"[{self.__class__.__name__}] Plugin initialized.")
        self.text_to_set = ""

    def on_loaded(self):
        logging.info(f"[{self.__class__.__name__}] Plugin loaded.")
        self.options.setdefault("wordlist", "/home/pi/wordlist/rockyou.txt")
        self.options.setdefault("handshake_folder", "/root/handshakes/")
        self.options.setdefault("status_file", "/root/handshakes/crack_status.txt")
        self.options.setdefault("enabled", False)

        # Create the status file if it doesn't exist
        if not os.path.exists(self.options["status_file"]):
            with open(self.options["status_file"], "w") as status_file:
                status_file.write("")

    def on_webhook(self, path, request):
        logging.info(f"[{self.__class__.__name__}] Webhook pressed at path: {path}.")
        handshake_folder = self.options["handshake_folder"]

        # Find all handshake files (.16800 and .22000)
        handshakes = [f for f in os.listdir(handshake_folder) if f.endswith('.16800') or f.endswith('.22000')]

        if not handshakes:
            return 'No handshakes found.', 200

        for handshake_file in handshakes:
            handshake_path = os.path.join(handshake_folder, handshake_file)
            if self._already_cracked(handshake_file):
                logging.info(f"[{self.__class__.__name__}] Handshake {handshake_file} already cracked.")
                continue

            self._crack_handshake(handshake_path)

        return 'Handshake cracking in progress.', 200

    def _already_cracked(self, handshake_file):
        # Check the status file to see if this handshake has already been cracked
        with open(self.options["status_file"], "r") as status_file:
            cracked_handshakes = status_file.read().splitlines()
        return handshake_file in cracked_handshakes

    def _crack_handshake(self, handshake_path):
        # Determine the mode for Hashcat (22000 for EAPOL, 16800 for PMKID)
        if handshake_path.endswith('.22000'):
            mode = '22000'
        elif handshake_path.endswith('.16800'):
            mode = '16800'
        else:
            logging.error(f"[{self.__class__.__name__}] Invalid handshake file: {handshake_path}")
            return

        wordlist = self.options["wordlist"]
        output_file = handshake_path + ".cracked"

        # Run hashcat to crack the handshake
        command = [
            'hashcat', '-m', mode, handshake_path, wordlist, '--outfile', output_file, '--quiet'
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0 and os.path.exists(output_file):
            logging.info(f"[{self.__class__.__name__}] Handshake {handshake_path} cracked.")
            self._store_cracked_handshake(handshake_path)
            self._display_crack_result(output_file)
        else:
            logging.info(f"[{self.__class__.__name__}] Failed to crack {handshake_path}.")

    def _store_cracked_handshake(self, handshake_path):
        # Store the cracked handshake in the status file
        with open(self.options["status_file"], "a") as status_file:
            status_file.write(f"{os.path.basename(handshake_path)}\n")

    def _display_crack_result(self, output_file):
        # Display the result on the Pwnagotchi UI and store it
        with open(output_file, "r") as result_file:
            result = result_file.read().strip()
        
        if result:
            self.text_to_set = f"Cracked: {result}"
            logging.info(f"[{self.__class__.__name__}] Cracked password: {result}")
        else:
            logging.info(f"[{self.__class__.__name__}] No password found in {output_file}")

    def on_ui_update(self, ui):
        if self.text_to_set:
            ui.set("face", self.options["face"])
            ui.set("status", self.text_to_set)
            self.text_to_set = ""
