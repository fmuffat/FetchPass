"""
FetchPass - Printer Module
Supports simulation, Brother QL (USB), and ESC/POS (USB/Network).
"""

import os
from datetime import datetime


class Printer:

    def __init__(self, config: dict):
        self.type         = config.get("type", "simulation")
        self.connection   = config.get("connection", "usb")
        self.ip           = config.get("ip", "")
        self.port         = config.get("port", 9100)
        self.printer_name = config.get("printer_name", "")

    def print_voucher(self, voucher: dict, ticket_config: dict) -> tuple:
        """
        Print voucher ticket.
        Returns (success: bool, message: str)
        """
        lines = self._build_ticket(voucher, ticket_config)

        if self.type == "simulation":
            return self._print_simulation(lines)
        elif self.type == "brother_ql":
            return self._print_brother_ql(lines)
        elif self.type == "escpos":
            return self._print_escpos(lines)
        else:
            return False, f"Unknown printer type: {self.type}"

    def _build_ticket(self, voucher: dict, ticket_config: dict) -> list:
        """Build ticket lines from voucher info and ticket config."""
        w = 32
        sep = "=" * w
        sep2 = "-" * w

        lines = []

        # Leading blank lines — arrow from driver appears just above ticket
        lines.append("")
        lines.append("")
        lines.append("")

        lines.append(sep)

        header1 = ticket_config.get("header1", "WiFi Guest Pass")
        if header1:
            lines.append(header1.center(w))

        header2 = ticket_config.get("header2", "")
        if header2:
            lines.append(header2.center(w))

        lines.append(sep)
        lines.append("")
        lines.append(f"Network  : {voucher.get('ssid', '')}")
        lines.append(f"Password : {voucher.get('key', '')}")
        lines.append("")
        lines.append(sep2)
        lines.append(f"Valid for: {voucher.get('duration', '')}")
        lines.append(f"Created  : {voucher.get('created', '')}")
        lines.append(f"Expires  : {voucher.get('expires', '')}")
        lines.append(sep2)

        footer = ticket_config.get("footer", "")
        if footer:
            lines.append("")
            lines.append(footer.center(w))

        lines.append(sep)

        # Trailing blank lines — push all content above the cutter
        for _ in range(8):
            lines.append("")

        return lines

    def _print_simulation(self, lines: list) -> tuple:
        """Simulate printing — display in console and save to file."""
        print("\n--- TICKET SIMULATION ---")
        for line in lines:
            print(line)
        print("--- END SIMULATION ---\n")

        # Save to file
        filename = f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True, f"Simulation — ticket saved to {filepath}"
        except Exception:
            return True, "Simulation — ticket displayed in console"

    def _print_brother_ql(self, lines: list) -> tuple:
        """Print to Brother QL printer via brother_ql library."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from brother_ql.conversion import convert
            from brother_ql.backends.helpers import send
            from brother_ql.raster import BrotherQLRaster

            # Render ticket as image
            img_width = 696  # 62mm label width in pixels at 300dpi
            line_height = 30
            padding = 20
            img_height = len(lines) * line_height + padding * 2

            img = Image.new("RGB", (img_width, img_height), color="white")
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("cour.ttf", 24)
            except Exception:
                font = ImageFont.load_default()

            y = padding
            for line in lines:
                draw.text((padding, y), line, fill="black", font=font)
                y += line_height

            # Convert and send to printer
            qlr = BrotherQLRaster("QL-800")
            convert(qlr, [img], "62", cut=True)
            send(qlr.data, printer_identifier="usb://", backend_identifier="pyusb")

            return True, "Printed on Brother QL"

        except ImportError:
            return False, "brother_ql / Pillow not installed. Run: pip install brother_ql Pillow"
        except Exception as e:
            return False, f"Brother QL error: {e}"

    def _print_escpos(self, lines: list) -> tuple:
        """Print to ESC/POS printer via Windows printer spooler (win32print direct)."""
        printer_name = self.printer_name
        if not printer_name:
            return False, "No printer selected — configure in Settings → Printer"
        try:
            import win32print
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(hprinter, 1, ("FetchPass Ticket", None, "RAW"))
                win32print.StartPagePrinter(hprinter)

                # Send plain text only — no ESC codes
                text = "\n".join(lines) + "\n"
                win32print.WritePrinter(hprinter, text.encode("utf-8"))

                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)

            return True, f"Printed on {printer_name}"

        except ImportError:
            return False, "pywin32 not installed — run: pip install pywin32"
        except Exception as e:
            return False, f"Print error: {str(e)[:100]}"
        except Exception as e:
            return False, f"Print error: {str(e)[:100]}"

    def test_print(self, ticket_config: dict) -> tuple:
        """Print a test ticket."""
        test_voucher = {
            "ssid":     "TestNetwork",
            "key":      "123456",
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "expires":  "Test",
            "duration": "Test print",
        }
        return self.print_voucher(test_voucher, ticket_config)
