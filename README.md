# 🐕 FetchPass

**Guest Wi-Fi voucher generator for Ruckus Unleashed and Ruckus One.**

FetchPass is a lightweight desktop application that generates guest Wi-Fi vouchers with a single click, and optionally prints them on a thermal printer.

> **Tested on:**
> - Ruckus Unleashed 200.19
> - Ruckus One (June 2026 release)

---

## Features

- ✅ Ruckus Unleashed support (firmware 200.19+)
- ✅ Ruckus One support (EU / North America / Asia)
- 3 configurable voucher buttons (duration in hours, days or weeks)
- Thermal printer support: simulation mode, Brother QL (USB), ESC/POS (USB/Network)
- Fully customisable ticket (header, footer, language)
- Dark UI with Ruckus color scheme
- Runs on Windows / Linux / Raspberry Pi

---

## Requirements

- Python 3.9+
- Google Chrome installed on the machine *(required for Unleashed only — Ruckus One does not need it)*

```bash
pip install PyQt6 selenium webdriver-manager requests
```

For Brother QL printing (optional):
```bash
pip install brother_ql Pillow
```

For ESC/POS printing (optional):
```bash
pip install python-escpos
```

---

## Installation

```bash
git clone https://github.com/your-username/FetchPass.git
cd FetchPass
pip install -r requirements.txt
python main.py
```

---

## Project Structure

```
FetchPass/
├── main.py                  ← entry point
├── config.json              ← persistent settings (auto-generated)
├── requirements.txt
├── core/
│   ├── unleashed.py         ← Ruckus Unleashed integration
│   └── ruckus_one.py        ← Ruckus One integration
├── gui/
│   ├── main_window.py       ← main window with 3 voucher buttons
│   └── settings_dialog.py   ← settings (Connection, Buttons, Ticket, Printer)
└── printing/
    └── printer.py           ← simulation, Brother QL, ESC/POS
```

---

## Configuration

On first launch, click **⚙ Settings** to configure:

### Connection tab
- Choose **Ruckus Unleashed** or **Ruckus One**
- Enter your credentials and Guest SSID
- Click **Test Connection** to verify

**Unleashed account types:**
- `guestadmin` *(recommended)* — Guest Pass Manager role, limited privileges, logs in via `/user/user_login_guestpass.jsp`


**Ruckus One regions:**
- Europe → `api.eu.ruckus.cloud`
- North America → `api.ruckus.cloud`
- Asia → `api.asia.ruckus.cloud`

### Buttons tab
Set the label, duration and unit (hours / days / weeks) for each of the 3 buttons.

### Ticket Design tab
Customise the printed ticket: header lines, footer, language.

### Printer tab
Choose between:
- **Simulation** *(default)* — displays ticket on screen and saves to a `.txt` file on the Desktop
- **Brother QL (USB)** — requires `brother_ql` and `Pillow`
- **ESC/POS (USB)** — requires `python-escpos`, works with Epson TM series, Star Micronics, and generic ESC/POS printers

---

## Technical Notes

### Why Chrome for Unleashed?
Ruckus Unleashed uses a fully JavaScript-based authentication flow with a dynamic CSRF token. It is not possible to replicate this with a simple HTTP request library. FetchPass uses a headless Chrome browser (via Selenium) to handle the login transparently.

Ruckus One uses a standard OAuth2 client credentials flow — no browser required.

### Tested configurations
| Platform | Version | Account type |
|---|---|---|
| Ruckus Unleashed | 200.19 | guestadmin |
| Ruckus One | June 2026 release | OAuth2 Client Credentials |

---

## Building the .exe (Windows)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name FetchPass main.py
```

The executable will be in the `dist/` folder.

---

## License

MIT License — free to use, modify and distribute.

---

*Built with ❤️ because Ruckus doesn't provide this natively.*
*Developed with the assistance of Claude (Anthropic).*
