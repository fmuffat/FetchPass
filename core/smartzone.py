"""
FetchPass - SmartZone Core
Handles authentication and guest pass creation for vSZ-E and vSZ-H.

Tested on:
- vSZ-E 7.1.1
- vSZ-H 7.1.1
Note: vSZ-H < 7.0 has a known API bug — guest pass list always returns empty.

Requirements: pip install requests
"""

import requests
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_VERSION = "v11_1"


class SmartZoneClient:

    def __init__(self, host: str, username: str, password: str,
                 zone: str, wlan: str):
        self.host     = host
        self.username = username
        self.password = password
        self.zone     = zone
        self.wlan     = wlan
        self.base_url = f"https://{host}:8443/wsg/api/public/{API_VERSION}"
        self.session  = requests.Session()
        self.session.verify = False

    def _ticket_name(self) -> str:
        """Generate a readable guest pass name with FetchPass prefix."""
        return f"FetchPass-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _login(self) -> str:
        """Login and return service ticket."""
        resp = self.session.post(
            f"{self.base_url}/serviceTicket",
            json={"username": self.username, "password": self.password},
            timeout=10
        )
        if not resp.ok:
            raise Exception(f"Authentication failed — check your credentials ({resp.status_code})")
        ticket = resp.json().get("serviceTicket", "")
        if not ticket:
            raise Exception("No service ticket in response")
        return ticket

    def _logoff(self, ticket: str):
        """Logoff and release service ticket."""
        try:
            self.session.delete(
                f"{self.base_url}/serviceTicket",
                params={"serviceTicket": ticket},
                timeout=5
            )
        except Exception:
            pass

    def _verify_wlan(self, ticket: str):
        """
        Verify that the configured WLAN exists in the configured zone.
        Raises an exception with a clear message if not found.
        """
        params = {"serviceTicket": ticket}

        # Find zone ID
        resp = self.session.get(f"{self.base_url}/rkszones", params=params, timeout=10)
        if not resp.ok:
            return  # Can't verify — skip silently

        zone_id = None
        for z in resp.json().get("list", []):
            if z.get("name") == self.zone:
                zone_id = z.get("id")
                break

        if not zone_id:
            available = [z.get("name") for z in resp.json().get("list", [])]
            raise Exception(
                f"Zone '{self.zone}' not found on this SmartZone.\n"
                f"Available zones: {', '.join(available[:10])}"
            )

        # Find WLAN in zone
        resp2 = self.session.get(
            f"{self.base_url}/rkszones/{zone_id}/wlans",
            params=params, timeout=10
        )
        if not resp2.ok:
            return  # Can't verify — skip silently

        wlans = [w.get("name") for w in resp2.json().get("list", [])]
        if self.wlan not in wlans:
            raise Exception(
                f"WLAN '{self.wlan}' not found in zone '{self.zone}'.\n"
                f"Available WLANs: {', '.join(wlans)}"
            )

    def test_connection(self) -> tuple:
        """
        Test connection — verifies credentials only.
        Zone and WLAN names are case sensitive and cannot be verified
        without admin privileges.
        """
        ticket = None
        try:
            ticket = self._login()
            params = {"serviceTicket": ticket}

            # Get controller info for version display
            resp = self.session.get(
                f"{self.base_url}/controller",
                params=params, timeout=10
            )
            version = ""
            if resp.ok:
                items = resp.json().get("list", [{}])
                version = items[0].get("controllerVersion", "") if items else ""

            msg = f"Authentication successful"
            if version:
                msg += f" — SmartZone {version}"
            msg += f" ⚠ Zone '{self.zone}' and WLAN '{self.wlan}' are case sensitive — not verified"
            return True, msg

        except Exception as e:
            msg = str(e).split("\n")[0][:150]
            return False, msg
        finally:
            if ticket:
                self._logoff(ticket)

    def create_voucher(self, duration: int, unit: str = "hour") -> dict:
        """
        Create a guest pass voucher.
        unit: 'hour' | 'day' | 'week'
        Returns voucher info dict.
        """
        # Convert unit to SmartZone format
        unit_map = {"hour": "HOUR", "day": "DAY", "week": "WEEK"}
        sz_unit = unit_map.get(unit, "HOUR")

        # Calculate expiry for display
        hours_map = {"hour": duration, "day": duration * 24, "week": duration * 24 * 7}
        hours = hours_map.get(unit, duration)

        ticket = None
        try:
            ticket = self._login()
            params = {"serviceTicket": ticket}

            guest_name = self._ticket_name()
            now = datetime.now()

            payload = {
                "guestName":             guest_name,
                "wlan":                  {"name": self.wlan},
                "zone":                  {"name": self.zone},
                "numberOfPasses":        1,
                "passValidFor":          {"expirationValue": duration, "expirationUnit": sz_unit},
                "autoGeneratedPassword": True,
                "passEffectSince":       "CREATION_TIME",
                "maxDevices":            {"maxDevicesAllowed": "LIMITED", "maxDevicesNumber": 1},
            }

            resp = self.session.post(
                f"{self.base_url}/identity/guestpass/generate",
                params=params,
                json=payload,
                timeout=10
            )

            if not resp.ok:
                error_msg = resp.text[:300]
                try:
                    error_data = resp.json()
                    msg = error_data.get("message", error_msg)
                    if "Zone can not be found" in msg:
                        raise Exception(f"Zone '{self.zone}' not found — check name and case sensitivity")
                    elif "WLAN can not be found" in msg or "wlan" in msg.lower():
                        raise Exception(f"WLAN '{self.wlan}' not found in zone '{self.zone}' — check name and case sensitivity")
                    else:
                        raise Exception(f"HTTP {resp.status_code}: {msg[:150]}")
                except (ValueError, KeyError):
                    raise Exception(f"HTTP {resp.status_code}: {error_msg}")

            guest_id = resp.json().get("id", "")
            if not guest_id:
                raise Exception("No ID in response")

            # Retrieve password from list
            key = self._get_password(params, guest_id, guest_name)

            # Build duration string
            unit_labels = {"hour": "h", "day": "day(s)", "week": "week(s)"}
            duration_str = f"{duration} {unit_labels.get(unit, unit)}"
            expires_dt = now + timedelta(hours=hours)

            return {
                "name":     guest_name,
                "key":      key,
                "ssid":     self.wlan,
                "created":  now.strftime("%d.%m.%Y %H:%M"),
                "expires":  expires_dt.strftime("%d.%m.%Y %H:%M"),
                "duration": duration_str,
            }

        except Exception as e:
            msg = str(e).split("\n")[0][:150]
            raise Exception(msg)
        finally:
            if ticket:
                self._logoff(ticket)

    def _get_password(self, params: dict, guest_id: str, guest_name: str) -> str:
        """Retrieve the password (key) for a just-created guest pass."""
        import time
        time.sleep(1)

        resp = self.session.get(
            f"{self.base_url}/identity/guestpass",
            params=params, timeout=10
        )
        if resp.ok:
            for gp in resp.json().get("list", []):
                if gp.get("userId") == guest_id or gp.get("guestName") == guest_name:
                    key = gp.get("key", "")
                    if key:
                        return key

        raise Exception(
            f"Guest pass created (ID: {guest_id}) but could not retrieve password. "
            f"This is a known issue on vSZ-H firmware < 7.0."
        )
