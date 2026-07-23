"""
FetchPass - Printer Module
Supports simulation and ESC/POS via Windows printer spooler (win32print RAW).
"""

import os
from datetime import datetime
from core.utils import get_desktop_path


class Printer:

    def __init__(self, config: dict):
        self.type         = config.get("type", "simulation")
        self.printer_name = config.get("printer_name", "")

    def print_voucher(self, voucher: dict, ticket_config: dict) -> tuple:
        """Print voucher ticket. Returns (success: bool, message: str)"""
        if self.type == "simulation":
            return self._print_simulation(voucher, ticket_config)
        elif self.type == "escpos":
            return self._print_escpos(voucher, ticket_config)
        else:
            return False, f"Unknown printer type: {self.type}"

    def _build_lines(self, voucher: dict, ticket_config: dict) -> list:
        """Build ticket as plain text lines."""
        w    = 32
        sep  = "=" * w
        sep2 = "-" * w

        header1 = ticket_config.get("header1", "WiFi Guest Pass")
        header2 = ticket_config.get("header2", "")
        footer  = ticket_config.get("footer", "")

        lines = ["", "", ""]  # leading space

        lines.append(sep)
        if header1:
            lines.append(header1.center(w))
        if header2:
            lines.append(header2.center(w))
        lines.append(sep)
        lines.append("")
        lines.append(f"Network  : {voucher.get('ssid', '')}")
        lines.append("")
        lines.append(f"Password : {voucher.get('key', '')}")
        lines.append("")
        lines.append(sep2)
        lines.append(f"Valid for: {voucher.get('duration', '')}")
        lines.append(f"Created  : {voucher.get('created', '')}")
        lines.append(f"Expires  : {voucher.get('expires', '')}")
        lines.append(sep2)

        if footer:
            lines.append("")
            lines.append(footer.center(w))

        lines.append(sep)

        # Trailing space for clean cut
        for _ in range(12):
            lines.append("")

        return lines

    def _print_simulation(self, voucher: dict, ticket_config: dict) -> tuple:
        lines = self._build_lines(voucher, ticket_config)
        print("\n--- TICKET SIMULATION ---")
        for line in lines:
            print(line)
        print("--- END SIMULATION ---\n")

        filename = f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(get_desktop_path(), filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True, f"Simulation — ticket saved to {filepath}"
        except Exception:
            return True, "Simulation — ticket displayed in console"

    def _print_escpos(self, voucher: dict, ticket_config: dict) -> tuple:
        """Print via Windows printer spooler — plain text RAW."""
        if not self.printer_name:
            return False, "No printer selected — configure in Settings → Printer"
        try:
            import win32print
            lines = self._build_lines(voucher, ticket_config)
            text  = "\n".join(lines) + "\n"

            hprinter = win32print.OpenPrinter(self.printer_name)
            try:
                win32print.StartDocPrinter(hprinter, 1, ("FetchPass Ticket", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, text.encode("utf-8"))
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)

            return True, f"Printed on {self.printer_name}"

        except ImportError:
            return False, "pywin32 not installed — run: pip install pywin32"
        except Exception as e:
            return False, f"Print error: {str(e)[:100]}"

    def test_print(self, ticket_config: dict) -> tuple:
        test_voucher = {
            "ssid":     "TestNetwork",
            "key":      "123456",
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "expires":  "Test",
            "duration": "Test print",
        }
        return self.print_voucher(test_voucher, ticket_config)
