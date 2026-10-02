# 🐕 FetchPass

**Guest Wi-Fi voucher generator for Ruckus Unleashed, Ruckus One and SmartZone.**

FetchPass is a lightweight desktop application that generates guest Wi-Fi vouchers with a single click, and optionally prints them on a thermal printer.

> **Tested on:**
> - Ruckus Unleashed 200.19
> - Ruckus One (June 2026 release)
> - SmartZone vSZ-E / vSZ-H 7.1.1

---

## Features

- ✅ Ruckus Unleashed support (firmware 200.19+)
- ✅ Ruckus One support (EU / North America / Asia)
- ✅ SmartZone support (vSZ-E / vSZ-H, firmware 7.0+)
- 3 configurable voucher buttons (duration in hours, days or weeks)
- Thermal printing on any printer installed in Windows (Star TSP, Epson TM, …) — or simulation mode
- Fully customisable ticket (header, footer, language: en / fr / de / it)
- Dark UI with Ruckus color scheme
- Runs on Windows — on Linux / Raspberry Pi, voucher generation works but printing is simulation only

---

## Requirements

- Python 3.9+
- Google Chrome installed on the machine *(required for Unleashed only — Ruckus One does not need it)*

```bash
pip install -r requirements.txt
```

`pywin32` (Windows printing) is installed automatically on Windows only.

---

## Installation

```bash
git clone https://github.com/fmuffat/FetchPass.git
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
│   ├── ruckus_one.py        ← Ruckus One integration
│   ├── smartzone.py         ← SmartZone integration
│   └── utils.py             ← shared helpers (config path)
├── gui/
│   ├── main_window.py       ← main window with 3 voucher buttons
│   └── settings_dialog.py   ← settings (Connection, Buttons, Ticket, Printer)
└── printing/
    ├── printer.py           ← simulation and Windows printer output
    └── ticket_text.py       ← ticket labels (en / fr / de / it)
```

---

## Configuration

On first launch, click **⚙ Settings** to configure:

### Connection tab
- Choose **Ruckus Unleashed**, **Ruckus One** or **SmartZone**
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
Customise the printed ticket: header lines, footer, and the language of the ticket labels (Network, Password, Valid for…).

### Printer tab
Choose between:
- **Simulation** *(default)* — displays the ticket on screen and saves it as a `.txt` file in the `tickets/` folder next to the app
- **ESC/POS / Star / Epson (Windows)** — prints as plain text on any printer installed in Windows (Star TSP, Epson TM, …) via the Windows spooler

Accented characters are sent in code page `cp437` (Star / Epson default). If they print incorrectly, change `printer.codepage` in `config.json` (e.g. `cp858`, `cp850`).

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
| SmartZone vSZ-E | 7.1.1 | admin, guestadmin |
| SmartZone vSZ-H | 7.1.1 | admin, guestadmin |

---


## SmartZone Notes

### Zone and WLAN names are case sensitive
When configuring FetchPass for SmartZone, the Zone name and WLAN name must match exactly as configured on the controller, including upper/lower case.

### Password length
SmartZone allows administrators to configure the guest pass password length. FetchPass recommends setting the password to a maximum of **8 characters** to ensure the printed ticket remains readable and well-formatted on thermal printers.

If a password longer than 8 characters is generated, FetchPass will display a warning.

### Firmware requirement
The guest pass password retrieval via API requires SmartZone firmware **7.0 or later**. A known bug in vSZ-H 6.1.2 causes the guest pass list to always return empty, making it impossible to retrieve the password via API.

### Connection test
The Test Connection button in Settings verifies your credentials and, when the account is allowed to list zones and WLANs, checks that the Zone and WLAN names exist (and suggests the available names otherwise). Accounts without these rights only get the credentials check — make sure the names are correctly typed, including case.

## Building the .exe (Windows)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name FetchPass main.py
```

The executable will be in the `dist/` folder. `config.json` and the `tickets/` folder are created next to the `.exe`.

---

## License

MIT License — free to use, modify and distribute.

---

*Built with ❤️ because Ruckus doesn't provide this natively.*
*Developed with the assistance of Claude (Anthropic).*
