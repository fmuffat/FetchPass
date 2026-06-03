"""
FetchPass - Ruckus One Core
Handles OAuth2 authentication and guest pass creation for Ruckus One.
"""

import requests
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REGION_URLS = {
    "eu": "https://api.eu.ruckus.cloud",
    "us": "https://api.ruckus.cloud",
    "ap": "https://api.asia.ruckus.cloud",
}

AUTH_URLS = {
    "eu": "https://eu.ruckus.cloud/oauth2/token",
    "us": "https://ruckus.cloud/oauth2/token",
    "ap": "https://asia.ruckus.cloud/oauth2/token",
}


class RuckusOneClient:

    def __init__(self, region: str, tenant_id: str,
                 client_id: str, client_secret: str, ssid: str):
        self.region        = region
        self.tenant_id     = tenant_id
        self.client_id     = client_id
        self.client_secret = client_secret
        self.ssid          = ssid
        self.api_base      = REGION_URLS.get(region, REGION_URLS["eu"])
        self.auth_url      = f"{AUTH_URLS.get(region, AUTH_URLS['eu'])}/{tenant_id}"
        self.token         = None

    def _get_token(self) -> str:
        """Obtain JWT token via OAuth2 client credentials flow."""
        resp = requests.post(
            self.auth_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type":    "client_credentials",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data.get("access_token", "")
        if not self.token:
            raise Exception("No access_token in response")
        return self.token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def _get_network_id(self) -> str:
        """Find the network ID matching the configured SSID."""
        # Try wifiNetworks endpoint (new API)
        for endpoint in ["/wifiNetworks", "/networks"]:
            try:
                url = f"{self.api_base}{endpoint}"
                resp = requests.get(url, headers=self._headers(), timeout=10)
                if not resp.ok:
                    continue
                data = resp.json()
                items = data if isinstance(data, list) else data.get("content", data.get("data", data.get("list", [])))
                for net in items:
                    if net.get("ssid") == self.ssid or net.get("name") == self.ssid:
                        return net.get("id", "")
            except Exception:
                continue

        raise Exception(f"SSID '{self.ssid}' not found on Ruckus One")

    def test_connection(self) -> tuple:
        """Test connection — returns (success: bool, message: str)"""
        try:
            self._get_token()
            # Try wifiNetworks to verify connectivity
            for endpoint in ["/wifiNetworks", "/networks"]:
                resp = requests.get(
                    f"{self.api_base}{endpoint}",
                    headers=self._headers(), timeout=10)
                if resp.ok:
                    return True, f"Connected — Ruckus One ({self.region.upper()})"
            return False, f"Auth OK but API unreachable"
        except Exception as e:
            msg = str(e).split("\n")[0][:120]
            return False, msg

    def create_voucher(self, duration: int, unit: str = "hour") -> dict:
        """
        Create a guest pass voucher on Ruckus One.
        unit: 'hour' | 'day' | 'week'
        Returns voucher info dict.
        """
        self._get_token()
        network_id = self._get_network_id()

        now = datetime.now()
        guest_name = f"FetchPass-{now.strftime('%Y%m%d-%H%M%S')}"

        # Convert unit to Ruckus One format
        unit_map = {"hour": "Hour", "day": "Day", "week": "Week"}
        r1_unit = unit_map.get(unit, "Hour")

        # Calculate hours for expiry display
        hours_map = {"hour": duration, "day": duration * 24, "week": duration * 24 * 7}
        hours = hours_map.get(unit, duration)

        # Try both payload formats on wifiNetworks endpoint (correct endpoint)
        errors = []
        url = f"{self.api_base}/wifiNetworks/{network_id}/guestUsers"

        for payload in [
            # Format 1: single object without networkId
            {
                "name":              guest_name,
                "deliveryMethods":   ["STUB"],
                "mobilePhoneNumber": "",
                "maxDevices":        1,
                "expiration": {
                    "activationType": "Creation",
                    "duration":       duration,
                    "unit":           r1_unit,
                },
            },
            # Format 2: with email field (some versions require it)
            {
                "name":              guest_name,
                "deliveryMethods":   ["STUB"],
                "mobilePhoneNumber": "",
                "email":             "",
                "maxDevices":        1,
                "expiration": {
                    "activationType": "Creation",
                    "duration":       duration,
                    "unit":           r1_unit,
                },
            },
        ]:
            try:
                resp = requests.post(url, headers=self._headers(),
                                    json=payload, timeout=10)
                if resp.ok:
                    data = resp.json()
                    # Extract guest from response
                    if isinstance(data, list):
                        guest = data[0]
                    elif "response" in data:
                        r = data["response"]
                        guest = r[0] if isinstance(r, list) else r
                    elif "content" in data:
                        c = data["content"]
                        guest = c[0] if isinstance(c, list) else c
                    else:
                        guest = data

                    key = guest.get("password", "")
                    if not key:
                        errors.append(f"No password in: {str(data)[:200]}")
                        continue

                    unit_labels = {"hour": "h", "day": "day(s)", "week": "week(s)"}
                    duration_str = f"{duration} {unit_labels.get(unit, unit)}"
                    expires_dt = now + timedelta(hours=hours)
                    exp_ts = guest.get("expirationDate", 0)
                    expires_str = (datetime.fromtimestamp(exp_ts / 1000).strftime("%d.%m.%Y %H:%M")
                                  if exp_ts else expires_dt.strftime("%d.%m.%Y %H:%M"))

                    return {
                        "name":     guest.get("name", guest_name),
                        "key":      key,
                        "ssid":     self.ssid,
                        "created":  now.strftime("%d.%m.%Y %H:%M"),
                        "expires":  expires_str,
                        "duration": duration_str,
                    }
                else:
                    errors.append(f"{url}: HTTP {resp.status_code} — {resp.text[:300]}")
            except Exception as e:
                errors.append(f"{url}: {str(e)[:100]}")

        raise Exception("\n".join(errors))
