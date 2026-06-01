"""
FetchPass - Main Window
Main application window with 3 voucher generation buttons.
"""

import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor


class VoucherThread(QThread):
    success = pyqtSignal(dict)
    error   = pyqtSignal(str)

    def __init__(self, config: dict, duration: int, unit: str):
        super().__init__()
        self.config   = config
        self.duration = duration
        self.unit     = unit

    def run(self):
        try:
            if self.config["mode"] == "unleashed":
                from core.unleashed import UnleashedClient
                uc = self.config["unleashed"]
                client = UnleashedClient(
                    ip=uc["ip"], username=uc["username"],
                    password=uc["password"], ssid=uc["ssid"],
                    account_type=uc["account_type"]
                )
            else:
                from core.ruckus_one import RuckusOneClient
                r1 = self.config["ruckus_one"]
                client = RuckusOneClient(
                    region=r1["region"], tenant_id=r1["tenant_id"],
                    client_id=r1["client_id"], client_secret=r1["client_secret"],
                    ssid=r1["ssid"]
                )
            voucher = client.create_voucher(self.duration, self.unit)
            self.success.emit(voucher)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setWindowTitle("FetchPass 🐕")
        self.setMinimumSize(480, 580)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()

    def _stylesheet(self) -> str:
        return """
        QMainWindow, QWidget#central { background: #1A1A1A; }
        QLabel { color: #F0F0F0; }
        QPushButton#btn_voucher {
            background: #2A2A2A;
            color: #F0F0F0;
            border: 2px solid #E8581A;
            border-radius: 10px;
            font-size: 17px;
            font-weight: bold;
            padding: 20px 16px;
            min-height: 70px;
        }
        QPushButton#btn_voucher:hover {
            background: #E8581A;
            color: #FFFFFF;
            border-color: #E8581A;
        }
        QPushButton#btn_voucher:disabled {
            background: #222;
            border-color: #3A3A3A;
            color: #555;
        }
        QPushButton#btn_settings {
            background: transparent;
            color: #666;
            border: 1px solid #3A3A3A;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 12px;
        }
        QPushButton#btn_settings:hover { color: #E8581A; border-color: #E8581A; }
        QFrame#ticket_frame {
            background: #222222;
            border: 1px solid #3A3A3A;
            border-radius: 10px;
            padding: 12px;
        }
        QLabel#ticket_label {
            color: #F0F0F0;
            font-family: Courier New;
            font-size: 13px;
        }
        QLabel#status_label { color: #666; font-size: 12px; }
        QLabel#status_ok    { color: #4CAF50; font-size: 12px; }
        QLabel#status_err   { color: #E8581A; font-size: 12px; }
        """

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Header ───────────────────────────────────────────────
        header = QHBoxLayout()
        logo = QLabel("🐕  FetchPass")
        logo.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        logo.setStyleSheet("color: #E8581A; font-weight: bold;")
        self.lbl_mode = QLabel(self._mode_label())
        self.lbl_mode.setStyleSheet("color: #555; font-size: 12px;")
        btn_settings = QPushButton("⚙  Settings")
        btn_settings.setObjectName("btn_settings")
        btn_settings.clicked.connect(self._open_settings)
        header.addWidget(logo)
        header.addStretch()
        header.addWidget(self.lbl_mode)
        header.addWidget(btn_settings)
        layout.addLayout(header)

        # ── Divider ──────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333;")
        layout.addWidget(line)

        # ── Status ───────────────────────────────────────────────
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("status_label")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        # ── Voucher Buttons ──────────────────────────────────────
        self.voucher_buttons = []
        for i, btn_cfg in enumerate(self.config["buttons"]):
            btn = QPushButton(self._btn_label(btn_cfg))
            btn.setObjectName("btn_voucher")
            btn.clicked.connect(lambda checked, cfg=btn_cfg: self._generate(cfg))
            layout.addWidget(btn)
            self.voucher_buttons.append(btn)

        # ── Ticket Display ───────────────────────────────────────
        self.ticket_frame = QFrame()
        self.ticket_frame.setObjectName("ticket_frame")
        ticket_layout = QVBoxLayout(self.ticket_frame)
        self.lbl_ticket = QLabel("No voucher generated yet.")
        self.lbl_ticket.setObjectName("ticket_label")
        self.lbl_ticket.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.lbl_ticket.setWordWrap(True)
        self.lbl_ticket.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        ticket_layout.addWidget(self.lbl_ticket)
        layout.addWidget(self.ticket_frame)

        layout.addStretch()

    # ── Helpers ──────────────────────────────────────────────────
    def _mode_label(self) -> str:
        if self.config["mode"] == "unleashed":
            ip = self.config["unleashed"].get("ip", "not configured")
            return f"Unleashed  {ip}"
        else:
            region = self.config["ruckus_one"].get("region", "eu").upper()
            return f"Ruckus One  {region}"

    def _btn_label(self, btn_cfg: dict) -> str:
        label    = btn_cfg.get("label", "")
        dur      = btn_cfg.get("duration", 0)
        unit     = btn_cfg.get("unit", "hour")
        unit_lbl = {"hour": "h", "day": "day(s)", "week": "week(s)"}
        return f"{label}\n{dur} {unit_lbl.get(unit, unit)}"

    # ── Generate Voucher ─────────────────────────────────────────
    def _generate(self, btn_cfg: dict):
        duration = btn_cfg.get("duration", 4)
        unit     = btn_cfg.get("unit", "hour")
        self._set_busy(True)
        self.lbl_status.setText("⏳  Generating voucher...")
        self.lbl_status.setStyleSheet("color: #f0a500; font-size: 12px;")

        self.thread = VoucherThread(self.config, duration, unit)
        self.thread.success.connect(self._on_voucher_success)
        self.thread.error.connect(self._on_voucher_error)
        self.thread.start()

    def _on_voucher_success(self, voucher: dict):
        self._set_busy(False)
        self.lbl_status.setText("✓  Voucher created successfully")
        self.lbl_status.setStyleSheet("color: #4caf50; font-size: 12px;")
        self._display_voucher(voucher)

        # Print
        from printing.printer import Printer
        p = Printer(self.config["printer"])
        p.print_voucher(voucher, self.config["ticket"])

    def _on_voucher_error(self, msg: str):
        self._set_busy(False)
        self.lbl_status.setText(f"✗  Error — see details below")
        self.lbl_status.setStyleSheet("color: #E8581A; font-size: 12px;")
        # Show full error in ticket frame for easy copy-paste
        self.lbl_ticket.setText(f"ERROR:\n\n{msg}")

    def _display_voucher(self, voucher: dict):
        tc = self.config["ticket"]
        lines = []
        if tc.get("header1"):
            lines.append(f"  {tc['header1']}")
        if tc.get("header2"):
            lines.append(f"  {tc['header2']}")
        lines.append("  " + "─" * 28)
        lines.append(f"  Network  : {voucher['ssid']}")
        lines.append(f"  Password : {voucher['key']}")
        lines.append("  " + "─" * 28)
        lines.append(f"  Valid    : {voucher['duration']}")
        lines.append(f"  Created  : {voucher['created']}")
        lines.append(f"  Expires  : {voucher['expires']}")
        if tc.get("footer"):
            lines.append("  " + "─" * 28)
            lines.append(f"  {tc['footer']}")
        self.lbl_ticket.setText("\n".join(lines))

    def _set_busy(self, busy: bool):
        for btn in self.voucher_buttons:
            btn.setEnabled(not busy)

    # ── Settings ─────────────────────────────────────────────────
    def _open_settings(self):
        from gui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.config = dlg.get_config()
            self._save_config()
            self.lbl_mode.setText(self._mode_label())
            self._refresh_buttons()

    def _refresh_buttons(self):
        for i, btn in enumerate(self.voucher_buttons):
            if i < len(self.config["buttons"]):
                btn.setText(self._btn_label(self.config["buttons"][i]))

    def _save_config(self):
        try:
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass
