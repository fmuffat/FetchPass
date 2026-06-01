"""
FetchPass - Printer Module
Supports simulation, Brother QL (USB), and ESC/POS (USB/Network).
"""

import os
from datetime import datetime


class Printer:

    def __init__(self, config: dict):
        self.type       = config.get("type", "simulation")   # simulation | brother_ql | escpos
        self.connection = config.get("connection", "usb")     # usb | network
        self.ip         = config.get("ip", "")
        self.port       = config.get("port", 9100)

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
        """Print to ESC/POS printer (Epson, Star, generic)."""
        try:
            if self.connection == "network":
                from escpos.printer import Network
                p = Network(self.ip, self.port)
            else:
                from escpos.printer import Usb
                p = Usb(0x04b8, 0x0202)  # Default Epson USB IDs

            p.set(align="center", text_type="B", width=2, height=2)
            for line in lines[:2]:  # Header bold
                p.text(line + "\n")

            p.set(align="left", text_type="normal", width=1, height=1)
            for line in lines[2:]:
                p.text(line + "\n")

            p.cut()
            return True, "Printed on ESC/POS printer"

        except ImportError:
            return False, "python-escpos not installed. Run: pip install python-escpos"
        except Exception as e:
            return False, f"ESC/POS error: {e}"

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
