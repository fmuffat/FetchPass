#!/usr/bin/env python3
"""
FetchPass 🐕
Ruckus Unleashed / Ruckus One — Guest Voucher Generator

Requirements:
    pip install -r requirements.txt
"""

import sys
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from core.utils import get_config_path

CONFIG_FILE = get_config_path()

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
        "printer_name": "",
        "codepage": "cp437"
    }
}


def _merge(defaults: dict, saved: dict) -> dict:
    """Recursively merge saved values over defaults, so keys missing from an
    older config.json (at any depth) fall back to their default value."""
    merged = dict(defaults)
    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            merged[key] = _merge(defaults[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> tuple:
    """Returns (config, warning) — warning is None unless config.json was unreadable."""
    defaults = json.loads(json.dumps(DEFAULT_CONFIG))
    if not os.path.exists(CONFIG_FILE):
        return defaults, None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            raise ValueError("top-level value is not an object")
        return _merge(defaults, saved), None
    except Exception as e:
        # Keep the broken file aside instead of silently overwriting it on next save
        backup = f"{CONFIG_FILE}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        try:
            os.replace(CONFIG_FILE, backup)
            where = f"It was renamed to:\n{backup}"
        except OSError:
            where = "It could not be backed up."
        return defaults, (f"config.json could not be read ({str(e)[:100]}).\n\n"
                          f"{where}\n\nDefault settings are loaded.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FetchPass")
    app.setStyle("Fusion")

    config, warning = load_config()
    if warning:
        QMessageBox.warning(None, "FetchPass — Configuration", warning)

    from gui.main_window import MainWindow
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
