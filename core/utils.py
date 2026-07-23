"""
FetchPass - Shared Utilities
"""

import os
import sys
import ctypes


def get_app_dir() -> str:
    """Directory the app runs from — next to the .exe when frozen, else the script dir."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def get_config_path() -> str:
    """Path to config.json — always next to the app, regardless of the launch working directory."""
    return os.path.join(get_app_dir(), "config.json")


def get_desktop_path() -> str:
    """Resolve the real Desktop folder, respecting OneDrive Known Folder redirection."""
    try:
        CSIDL_DESKTOPDIRECTORY = 0x0010
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf)
        if buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")
