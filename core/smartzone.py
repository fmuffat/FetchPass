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

    def _verify_wlan(self, ticket: str) -> str:
        """
        Check that the configured zone and WLAN exist — returns a status string.
        Accounts without admin rights usually cannot list zones/WLANs; the result
        is then 'not verified' rather than an error.
        """
        not_verified = (f"⚠ Zone '{self.zone}' and WLAN '{self.wlan}' are case sensitive "
                        f"— not verified")
        params = {"serviceTicket": ticket}
        try:
            resp = self.session.get(f"{self.base_url}/rkszones", params=params, timeout=10)
            if not resp.ok:
                return not_verified
            zones = resp.json().get("list", [])
            zone_id = next((z.get("id") for z in zones if z.get("name") == self.zone), None)
            if not zone_id:
                available = ", ".join(z.get("name", "") for z in zones[:5])
                return f"⚠ Zone '{self.zone}' not found — available: {available}"

            resp2 = self.session.get(f"{self.base_url}/rkszones/{zone_id}/wlans",
                                     params=params, timeout=10)
            if not resp2.ok:
                return not_verified
            wlans = [w.get("name", "") for w in resp2.json().get("list", [])]
            if self.wlan not in wlans:
                return (f"⚠ WLAN '{self.wlan}' not found in zone '{self.zone}' "
                        f"— available: {', '.join(wlans[:5])}")
            return f"Zone '{self.zone}' / WLAN '{self.wlan}' ✓"
        except Exception:
            return not_verified

    def test_connection(self) -> tuple:
        """
        Test connection — verifies credentials, and the zone / WLAN names
        when the account is allowed to list them.
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
            msg += f" — {self._verify_wlan(ticket)}"
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
                    elif "wlan can not be found" in msg.lower():
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
        # The new pass may take a moment to appear in the list — retry a few times
        for attempt in range(3):
            time.sleep(1)
            key = self._find_password(params, guest_id, guest_name)
            if key:
                return key

        raise Exception(
            f"Guest pass created (ID: {guest_id}) but could not retrieve password. "
            f"This is a known issue on vSZ-H firmware < 7.0."
        )

    def _find_password(self, params: dict, guest_id: str, guest_name: str) -> str:
        """Walk all pages of the guest pass list — returns the key, or '' if not found."""
        page_size = 500
        index = 0
        seen_first = set()
        for _ in range(50):  # safety cap: 25'000 guest passes
            resp = self.session.get(
                f"{self.base_url}/identity/guestpass",
                params={**params, "index": index, "listSize": page_size},
                timeout=10
            )
            if not resp.ok:
                return ""
            data  = resp.json()
            items = data.get("list", [])
            if not items:
                return ""
            # Stop if the controller ignores paging and keeps returning the same page
            first = items[0].get("userId") or items[0].get("guestName")
            if first in seen_first:
                return ""
            seen_first.add(first)

            for gp in items:
                if gp.get("userId") == guest_id or gp.get("guestName") == guest_name:
                    return gp.get("key", "")

            if not data.get("hasMore"):
                return ""
            index += len(items)
        return ""
