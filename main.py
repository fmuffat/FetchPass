#!/usr/bin/env python3
"""
FetchPass 🐕
Ruckus Unleashed / Ruckus One — Guest Voucher Generator

Requirements:
    pip install PyQt6 selenium webdriver-manager
"""

import sys
import json
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "mode": "unleashed",
    "unleashed": {
        "ip": "",
        "username": "",
        "password": "",
        "account_type": "guestadmin",
        "ssid": ""
    },
    "ruckus_one": {
        "region": "eu",
        "tenant_id": "",
        "client_id": "",
        "client_secret": "",
        "ssid": ""
    },
    "smartzone": {
        "host": "",
        "username": "",
        "password": "",
        "zone": "",
        "wlan": ""
    },
    "buttons": [
        {"label": "Short Visit",  "duration": 4,  "unit": "hour"},
        {"label": "Full Day",     "duration": 1,  "unit": "day"},
        {"label": "Weekly Pass",  "duration": 1,  "unit": "week"}
    ],
    "ticket": {
        "header1": "WiFi Guest Pass",
        "header2": "",
        "footer": "Thank you for visiting",
        "language": "en"
    },
    "printer": {
        "type": "simulation",
        "connection": "usb",
        "usb_port": "",
        "brother_model": "QL-800",
        "ip": "",
        "port": 9100
    }
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            # Merge with defaults to handle missing keys
            config = json.loads(json.dumps(DEFAULT_CONFIG))
            config.update(saved)
            return config
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FetchPass")
    app.setStyle("Fusion")

    config = load_config()

    from gui.main_window import MainWindow
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
