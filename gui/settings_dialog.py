"""
FetchPass - Settings Dialog
Configure Unleashed / Ruckus One / SmartZone, buttons, ticket design, and printer.
"""

import json
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QButtonGroup,
    QRadioButton, QGroupBox, QFormLayout, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class TestConnectionThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            mode = self.config["mode"]
            if mode == "unleashed":
                from core.unleashed import UnleashedClient
                uc = self.config["unleashed"]
                client = UnleashedClient(
                    ip=uc["ip"], username=uc["username"],
                    password=uc["password"], ssid=uc["ssid"],
                    account_type=uc["account_type"]
                )
            elif mode == "ruckus_one":
                from core.ruckus_one import RuckusOneClient
                r1 = self.config["ruckus_one"]
                client = RuckusOneClient(
                    region=r1["region"], tenant_id=r1["tenant_id"],
                    client_id=r1["client_id"], client_secret=r1["client_secret"],
                    ssid=r1["ssid"]
                )
            else:  # smartzone
                from core.smartzone import SmartZoneClient
                sz = self.config["smartzone"]
                client = SmartZoneClient(
                    host=sz["host"], username=sz["username"],
                    password=sz["password"], zone=sz["zone"],
                    wlan=sz["wlan"]
                )
            success, msg = client.test_connection()
            self.result.emit(success, msg)
        except Exception as e:
            self.result.emit(False, str(e).split("\n")[0][:120])


class SettingsDialog(QDialog):

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = json.loads(json.dumps(config))  # deep copy
        self.setWindowTitle("FetchPass — Settings")
        self.setMinimumWidth(560)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()

    def _stylesheet(self) -> str:
        return """
        QDialog { background: #1A1A1A; color: #F0F0F0; }
        QTabWidget::pane { border: 1px solid #333; border-radius: 6px; background: #1A1A1A; }
        QTabBar::tab {
            background: #2A2A2A; color: #888; padding: 8px 20px;
            border-radius: 4px 4px 0 0; margin-right: 2px; font-size: 13px;
        }
        QTabBar::tab:selected { background: #E8581A; color: #FFFFFF; font-weight: bold; }
        QTabBar::tab:hover:!selected { background: #3A3A3A; color: #E8581A; }
        QGroupBox {
            border: 1px solid #3A3A3A; border-radius: 6px;
            margin-top: 12px; padding-top: 8px; color: #888; font-size: 11px;
            background: #222222;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #E8581A; font-size: 11px; }
        QLineEdit {
            background: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 4px;
            color: #F0F0F0; padding: 6px; font-size: 13px;
        }
        QLineEdit:focus { border-color: #E8581A; }
        QPushButton {
            background: #2A2A2A; color: #F0F0F0; border: 1px solid #3A3A3A;
            border-radius: 4px; padding: 8px 16px; font-size: 13px;
        }
        QPushButton:hover { background: #E8581A; border-color: #E8581A; color: #FFFFFF; }
        QPushButton#btn_save { background: #E8581A; border-color: #E8581A; font-weight: bold; color: #FFFFFF; }
        QPushButton#btn_save:hover { background: #C94A0E; }
        QRadioButton { color: #F0F0F0; spacing: 8px; }
        QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #555; background: #2A2A2A; }
        QRadioButton::indicator:checked { background: #E8581A; border-color: #E8581A; }
        QComboBox {
            background: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 4px;
            color: #F0F0F0; padding: 6px; font-size: 13px;
        }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView {
            background: #2A2A2A; color: #F0F0F0; selection-background-color: #E8581A;
            border: 1px solid #3A3A3A;
        }
        QSpinBox {
            background: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 4px;
            color: #F0F0F0; padding: 6px; font-size: 13px;
        }
        QLabel { color: #AAAAAA; }
        QLabel#status_ok  { color: #4CAF50; font-weight: bold; }
        QLabel#status_err { color: #E8581A; font-weight: bold; }
        """

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("⚙  Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #E8581A; margin-bottom: 4px;")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._tab_connection(), "Connection")
        tabs.addTab(self._tab_buttons(), "Buttons")
        tabs.addTab(self._tab_ticket(), "Ticket Design")
        tabs.addTab(self._tab_printer(), "Printer")
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save")
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    # ── TAB: Connection ──────────────────────────────────────────
    def _tab_connection(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        # Mode selector — 3 platforms
        mode_group = QGroupBox("Platform")
        mode_layout = QHBoxLayout(mode_group)
        self.rb_unleashed  = QRadioButton("Ruckus Unleashed")
        self.rb_r1         = QRadioButton("Ruckus One")
        self.rb_smartzone  = QRadioButton("SmartZone")
        self.rb_unleashed.setChecked(self.config["mode"] == "unleashed")
        self.rb_r1.setChecked(self.config["mode"] == "ruckus_one")
        self.rb_smartzone.setChecked(self.config["mode"] == "smartzone")
        self.rb_unleashed.toggled.connect(self._on_mode_changed)
        self.rb_r1.toggled.connect(self._on_mode_changed)
        self.rb_smartzone.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.rb_unleashed)
        mode_layout.addWidget(self.rb_r1)
        mode_layout.addWidget(self.rb_smartzone)
        layout.addWidget(mode_group)

        # ── Unleashed fields ──────────────────────────────────────
        self.grp_unleashed = QGroupBox("Unleashed Configuration")
        form = QFormLayout(self.grp_unleashed)
        uc = self.config["unleashed"]
        self.f_ip       = QLineEdit(uc["ip"])
        self.f_ip.setPlaceholderText("192.168.1.1")
        self.f_user     = QLineEdit(uc["username"])
        self.f_pass     = QLineEdit(uc["password"])
        self.f_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_ssid     = QLineEdit(uc["ssid"])
        self.f_ssid.setPlaceholderText("Guest")
        self.cb_account = QComboBox()
        self.cb_account.addItems(["guestadmin"])
        self.cb_account.setCurrentText(uc["account_type"])
        form.addRow("IP Address",   self.f_ip)
        form.addRow("Username",     self.f_user)
        form.addRow("Password",     self.f_pass)
        form.addRow("Guest SSID",   self.f_ssid)
        form.addRow("Account Type", self.cb_account)
        layout.addWidget(self.grp_unleashed)

        # ── Ruckus One fields ─────────────────────────────────────
        self.grp_r1 = QGroupBox("Ruckus One Configuration")
        form_r1 = QFormLayout(self.grp_r1)
        r1 = self.config["ruckus_one"]

        region_layout = QHBoxLayout()
        self.region_group = QButtonGroup()
        regions = [("Europe", "eu", "api.eu.ruckus.cloud"),
                   ("North America", "us", "api.ruckus.cloud"),
                   ("Asia", "ap", "api.asia.ruckus.cloud")]
        for label, key, url in regions:
            btn = QPushButton(f"{label}\n{url}")
            btn.setCheckable(True)
            btn.setChecked(r1["region"] == key)
            btn.setProperty("region_key", key)
            btn.clicked.connect(lambda checked, k=key: self._on_region(k))
            btn.setStyleSheet("QPushButton { padding: 8px; font-size: 11px; } QPushButton:checked { background: #E8581A; }")
            self.region_group.addButton(btn)
            region_layout.addWidget(btn)
        form_r1.addRow("Region", region_layout)

        self.f_tenant        = QLineEdit(r1["tenant_id"])
        self.f_client_id     = QLineEdit(r1["client_id"])
        self.f_client_secret = QLineEdit(r1["client_secret"])
        self.f_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_ssid_r1       = QLineEdit(r1["ssid"])
        form_r1.addRow("Tenant ID",     self.f_tenant)
        form_r1.addRow("Client ID",     self.f_client_id)
        form_r1.addRow("Client Secret", self.f_client_secret)
        form_r1.addRow("Guest SSID",    self.f_ssid_r1)
        layout.addWidget(self.grp_r1)

        # ── SmartZone fields ──────────────────────────────────────
        self.grp_sz = QGroupBox("SmartZone Configuration")
        form_sz = QFormLayout(self.grp_sz)
        sz = self.config.get("smartzone", {})
        self.f_sz_host = QLineEdit(sz.get("host", ""))
        self.f_sz_host.setPlaceholderText("192.168.1.1 or hostname")
        self.f_sz_user = QLineEdit(sz.get("username", ""))
        self.f_sz_pass = QLineEdit(sz.get("password", ""))
        self.f_sz_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_sz_zone = QLineEdit(sz.get("zone", ""))
        self.f_sz_zone.setPlaceholderText("Zone name")
        self.f_sz_wlan = QLineEdit(sz.get("wlan", ""))
        self.f_sz_wlan.setPlaceholderText("Guest WLAN name")
        form_sz.addRow("Host / IP",  self.f_sz_host)
        form_sz.addRow("Username",   self.f_sz_user)
        form_sz.addRow("Password",   self.f_sz_pass)
        form_sz.addRow("Zone Name",  self.f_sz_zone)
        form_sz.addRow("WLAN Name",  self.f_sz_wlan)
        lbl_note = QLabel("⚠  Requires vSZ-E or vSZ-H firmware ≥ 7.0")
        lbl_note.setStyleSheet("color: #888; font-size: 11px;")
        form_sz.addRow("", lbl_note)
        layout.addWidget(self.grp_sz)

        # Test connection
        test_row = QHBoxLayout()
        self.btn_test   = QPushButton("🔌  Test Connection")
        self.lbl_status = QLabel("")
        self.btn_test.clicked.connect(self._test_connection)
        test_row.addWidget(self.btn_test)
        test_row.addWidget(self.lbl_status)
        test_row.addStretch()
        layout.addLayout(test_row)
        layout.addStretch()

        self._on_mode_changed()
        return w

    def _on_mode_changed(self):
        mode = ("unleashed" if self.rb_unleashed.isChecked()
                else "ruckus_one" if self.rb_r1.isChecked()
                else "smartzone")
        self.grp_unleashed.setVisible(mode == "unleashed")
        self.grp_r1.setVisible(mode == "ruckus_one")
        self.grp_sz.setVisible(mode == "smartzone")

    def _on_region(self, key: str):
        self.config["ruckus_one"]["region"] = key

    def _test_connection(self):
        self._sync_to_config()
        self.btn_test.setEnabled(False)
        self.lbl_status.setText("Testing...")
        self.lbl_status.setStyleSheet("color: #888;")
        self.thread = TestConnectionThread(self.config)
        self.thread.result.connect(self._on_test_result)
        self.thread.start()

    def _on_test_result(self, success: bool, msg: str):
        self.btn_test.setEnabled(True)
        short_msg = msg.split("\n")[0][:120]
        self.lbl_status.setText(("✓  " if success else "✗  ") + short_msg)
        self.lbl_status.setStyleSheet(
            "color: #4caf50;" if success else "color: #E8581A;")

    # ── TAB: Buttons ─────────────────────────────────────────────
    def _tab_buttons(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        info = QLabel("Configure the 3 voucher generation buttons.")
        info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info)

        self.btn_fields = []
        for i, btn in enumerate(self.config["buttons"]):
            grp = QGroupBox(f"Button {i+1}")
            form = QFormLayout(grp)
            f_label    = QLineEdit(btn["label"])
            f_duration = QSpinBox()
            f_duration.setRange(1, 8760)
            f_duration.setValue(btn["duration"])
            f_duration.setStyleSheet("background: #2A2A2A; color: #F0F0F0; padding: 4px;")
            f_unit = QComboBox()
            f_unit.addItems(["hours", "days", "weeks"])
            unit_map = {"hour": "hours", "day": "days", "week": "weeks"}
            f_unit.setCurrentText(unit_map.get(btn.get("unit", "hour"), "hours"))
            form.addRow("Label",    f_label)
            form.addRow("Duration", f_duration)
            form.addRow("Unit",     f_unit)
            layout.addWidget(grp)
            self.btn_fields.append((f_label, f_duration, f_unit))

        layout.addStretch()
        return w

    # ── TAB: Ticket Design ───────────────────────────────────────
    def _tab_ticket(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        tc = self.config["ticket"]

        grp = QGroupBox("Ticket Content")
        form = QFormLayout(grp)
        self.f_header1 = QLineEdit(tc.get("header1", ""))
        self.f_header1.setPlaceholderText("Hotel Bellevue")
        self.f_header2 = QLineEdit(tc.get("header2", ""))
        self.f_header2.setPlaceholderText("Welcome / Bienvenue  (optional)")
        self.f_footer  = QLineEdit(tc.get("footer", ""))
        self.f_footer.setPlaceholderText("Thank you for visiting  (optional)")
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(["en", "fr", "de", "it"])
        self.cb_lang.setCurrentText(tc.get("language", "en"))
        form.addRow("Header line 1", self.f_header1)
        form.addRow("Header line 2", self.f_header2)
        form.addRow("Footer",        self.f_footer)
        form.addRow("Language",      self.cb_lang)
        layout.addWidget(grp)
        layout.addStretch()
        return w

    # ── TAB: Printer ─────────────────────────────────────────────
    def _tab_printer(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        pc = self.config["printer"]

        grp_type = QGroupBox("Printer Type")
        type_layout = QHBoxLayout(grp_type)
        self.rb_sim     = QRadioButton("Simulation")
        self.rb_brother = QRadioButton("Brother QL (USB)")
        self.rb_escpos  = QRadioButton("ESC/POS (USB)")
        self.rb_sim.setChecked(pc["type"] == "simulation")
        self.rb_brother.setChecked(pc["type"] == "brother_ql")
        self.rb_escpos.setChecked(pc["type"] == "escpos")
        self.rb_sim.toggled.connect(self._on_printer_type_changed)
        self.rb_brother.toggled.connect(self._on_printer_type_changed)
        self.rb_escpos.toggled.connect(self._on_printer_type_changed)
        type_layout.addWidget(self.rb_sim)
        type_layout.addWidget(self.rb_brother)
        type_layout.addWidget(self.rb_escpos)
        layout.addWidget(grp_type)

        self.grp_brother = QGroupBox("Brother QL Model")
        brother_form = QFormLayout(self.grp_brother)
        self.cb_brother_model = QComboBox()
        self.cb_brother_model.addItems([
            "QL-700", "QL-710W", "QL-720NW",
            "QL-800", "QL-810W", "QL-820NWB",
            "QL-1100", "QL-1110NWB"
        ])
        self.cb_brother_model.setCurrentText(pc.get("brother_model", "QL-800"))
        brother_form.addRow("Model", self.cb_brother_model)
        layout.addWidget(self.grp_brother)

        self.grp_port = QGroupBox("USB Port")
        port_layout = QFormLayout(self.grp_port)
        port_row = QHBoxLayout()
        self.cb_port = QComboBox()
        self.cb_port.setMinimumWidth(200)
        self.cb_port.setEditable(True)
        self.cb_port.setCurrentText(pc.get("usb_port", ""))
        btn_detect = QPushButton("🔍  Detect")
        btn_detect.setFixedWidth(100)
        btn_detect.clicked.connect(self._detect_ports)
        port_row.addWidget(self.cb_port)
        port_row.addWidget(btn_detect)
        self.lbl_ports_status = QLabel("")
        self.lbl_ports_status.setStyleSheet("color: #666; font-size: 11px;")
        port_layout.addRow("Port", port_row)
        port_layout.addRow("", self.lbl_ports_status)
        layout.addWidget(self.grp_port)

        btn_test_print = QPushButton("🖨  Test Print")
        btn_test_print.clicked.connect(self._test_print)
        layout.addWidget(btn_test_print)
        layout.addStretch()

        self._on_printer_type_changed()
        self._detect_ports()
        return w

    def _on_printer_type_changed(self):
        self.grp_brother.setVisible(self.rb_brother.isChecked())
        self.grp_port.setVisible(not self.rb_sim.isChecked())

    def _detect_ports(self):
        self.lbl_ports_status.setText("Scanning...")
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            self.cb_port.clear()
            if ports:
                for p in ports:
                    self.cb_port.addItem(f"{p.device} — {p.description}", p.device)
                self.lbl_ports_status.setText(f"✓  {len(ports)} port(s) found")
                self.lbl_ports_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                self.cb_port.addItem("No ports found")
                self.lbl_ports_status.setText("No USB ports detected")
                self.lbl_ports_status.setStyleSheet("color: #E8581A; font-size: 11px;")
        except ImportError:
            self.cb_port.addItem("pyserial not installed")
            self.lbl_ports_status.setText("Run: pip install pyserial")
            self.lbl_ports_status.setStyleSheet("color: #E8581A; font-size: 11px;")

    def _test_print(self):
        self._sync_to_config()
        from printing.printer import Printer
        p = Printer(self.config["printer"])
        success, msg = p.test_print(self.config["ticket"])
        QMessageBox.information(self, "Test Print", msg)

    # ── Sync & Save ──────────────────────────────────────────────
    def _sync_to_config(self):
        if self.rb_unleashed.isChecked():
            self.config["mode"] = "unleashed"
        elif self.rb_r1.isChecked():
            self.config["mode"] = "ruckus_one"
        else:
            self.config["mode"] = "smartzone"

        uc = self.config["unleashed"]
        uc["ip"]           = self.f_ip.text().strip()
        uc["username"]     = self.f_user.text().strip()
        uc["password"]     = self.f_pass.text()
        uc["ssid"]         = self.f_ssid.text().strip()
        uc["account_type"] = self.cb_account.currentText()

        r1 = self.config["ruckus_one"]
        r1["tenant_id"]     = self.f_tenant.text().strip()
        r1["client_id"]     = self.f_client_id.text().strip()
        r1["client_secret"] = self.f_client_secret.text()
        r1["ssid"]          = self.f_ssid_r1.text().strip()

        sz = self.config.setdefault("smartzone", {})
        sz["host"]     = self.f_sz_host.text().strip()
        sz["username"] = self.f_sz_user.text().strip()
        sz["password"] = self.f_sz_pass.text()
        sz["zone"]     = self.f_sz_zone.text().strip()
        sz["wlan"]     = self.f_sz_wlan.text().strip()

        unit_back = {"hours": "hour", "days": "day", "weeks": "week"}
        for i, (f_label, f_dur, f_unit) in enumerate(self.btn_fields):
            self.config["buttons"][i]["label"]    = f_label.text()
            self.config["buttons"][i]["duration"] = f_dur.value()
            self.config["buttons"][i]["unit"]     = unit_back.get(f_unit.currentText(), f_unit.currentText())

        tc = self.config["ticket"]
        tc["header1"]  = self.f_header1.text()
        tc["header2"]  = self.f_header2.text()
        tc["footer"]   = self.f_footer.text()
        tc["language"] = self.cb_lang.currentText()

        if self.rb_sim.isChecked():
            self.config["printer"]["type"] = "simulation"
        elif self.rb_brother.isChecked():
            self.config["printer"]["type"] = "brother_ql"
        else:
            self.config["printer"]["type"] = "escpos"
        port_data = self.cb_port.currentData()
        self.config["printer"]["usb_port"]      = port_data if port_data else self.cb_port.currentText()
        self.config["printer"]["brother_model"] = self.cb_brother_model.currentText()

    def _save(self):
        self._sync_to_config()
        self.accept()

    def get_config(self) -> dict:
        return self.config
