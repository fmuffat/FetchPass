"""
FetchPass - Shared Utilities
"""

import os
import sys


def get_app_dir() -> str:
    """Directory the app runs from — next to the .exe when frozen, else the script dir."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Project root (parent of core/), independent of the launch working directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path() -> str:
    """Path to config.json — always next to the app, regardless of the launch working directory."""
    return os.path.join(get_app_dir(), "config.json")

