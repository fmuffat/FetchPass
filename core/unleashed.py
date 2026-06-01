"""
FetchPass - Unleashed Core
Handles authentication and voucher generation for Ruckus Unleashed.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time


class UnleashedClient:

    def __init__(self, ip: str, username: str, password: str,
                 ssid: str, account_type: str = "guestadmin"):
        self.ip           = ip
        self.username     = username
        self.password     = password
        self.ssid         = ssid
        self.account_type = account_type

        if account_type == "guestadmin":
            self.base_url  = f"https://{ip}/user"
            self.login_url = f"{self.base_url}/user_login_guestpass.jsp"
            self.dash_url  = f"{self.base_url}/guestinfo.jsp"
            self.api_url   = f"{self.base_url}/_cmdstat.jsp"
            self.wait_for  = "guestinfo"
            self.btn_text  = "Login"
            self.wait_elem = "submit-btn"
        else:
            self.base_url  = f"https://{ip}/admin"
            self.login_url = f"{self.base_url}/login.jsp"
            self.dash_url  = f"{self.base_url}/dashboard.jsp"
            self.api_url   = f"{self.base_url}/_cmdstat.jsp"
            self.wait_for  = "dashboard"
            self.btn_text  = "Unleash"
            self.wait_elem = None

    def _make_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--log-level=3")
        options.add_argument("--page-load-strategy=eager")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.set_page_load_timeout(10)
        return driver

    def _api_call(self, driver, action: str, comp: str, xml_body: str) -> dict:
        result = driver.execute_async_script("""
            var callback = arguments[arguments.length - 1];
            var action   = arguments[0];
            var comp     = arguments[1];
            var body     = arguments[2];
            var apiUrl   = arguments[3];
            var referer  = arguments[4];

            var ts      = Date.now();
            var rnd     = Math.floor(Math.random() * 9000) + 1000;
            var updater = comp + '.' + ts + '.' + rnd;
            var xml     = "<ajax-request action='" + action + "' updater='" + updater
                        + "' comp='" + comp + "'>" + body + "</ajax-request>";

            var xhr = new XMLHttpRequest();
            xhr.open('POST', apiUrl, true);
            xhr.setRequestHeader('content-type', 'application/x-www-form-urlencoded; charset=UTF-8');
            xhr.setRequestHeader('x-csrf-token', window.csfrToken || '');
            xhr.setRequestHeader('Referer', referer);
            xhr.addEventListener('load', function() {
                callback({status: xhr.status, len: xhr.responseText.length, body: xhr.responseText});
            });
            xhr.addEventListener('error', function() {
                callback({status: -1, len: 0, body: 'XHR_ERROR'});
            });
            xhr.send(xml);
        """, action, comp, xml_body, self.api_url, self.dash_url)
        return result or {}

    def _login(self, driver) -> bool:
        wait = WebDriverWait(driver, 10)
        driver.get(self.login_url)
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(self.username)
        driver.find_element(By.ID, "password").send_keys(self.password)
        btn = driver.find_element(By.XPATH, f"//button[contains(text(),'{self.btn_text}')]")
        driver.execute_script("arguments[0].click();", btn)
        wait.until(EC.url_contains(self.wait_for))
        if self.wait_elem:
            wait.until(EC.presence_of_element_located((By.ID, self.wait_elem)))
        time.sleep(2)
        return True

    def test_connection(self) -> tuple:
        """Test connection — returns (success: bool, message: str)"""
        driver = self._make_driver()
        try:
            self._login(driver)

            if self.account_type == "admin":
                resp = self._api_call(driver, "getstat", "system", "<sysinfo/>")
                body = resp.get("body", "")
                if "version-num" in body:
                    root = ET.fromstring(body)
                    sysinfo = root.find(".//sysinfo")
                    version = sysinfo.get("version-num", "unknown") if sysinfo is not None else "unknown"
                    return True, f"Connected — Unleashed {version}"
                return False, "Connected but could not retrieve system info"
            else:
                resp = self._api_call(driver, "getstat", "system", "<guest-list/>")
                body = resp.get("body", "")
                if "ajax-response" in body:
                    return True, f"Connected — Guest Manager ({self.username})"
                return False, "Connected but could not reach guest API"

        except Exception as e:
            msg = str(e).split("\n")[0][:120]
            return False, msg
        finally:
            driver.quit()

    def create_voucher(self, duration: int, unit: str = "hour") -> dict:
        """
        Create a guest voucher.
        unit: 'hour' | 'day' | 'week'
        Returns voucher info dict.
        """
        driver = self._make_driver()
        try:
            self._login(driver)

            # Generate key
            resp = self._api_call(driver, "docmd", "system",
                f"<xcmd cmd='generate-guest-key' ssid='{self.ssid}' />")
            body = resp.get("body", "")
            if not body.strip():
                raise Exception("Empty response from generate-guest-key")

            root = ET.fromstring(body)
            xmsg = root.find(".//xmsg")
            key = xmsg.get("x-key", "") if xmsg is not None else ""
            if not key:
                raise Exception("Could not extract guest key from response")

            # Create voucher — pass unit directly to API
            now = datetime.now()
            guest_name = f"Guest-{now.strftime('%Y%m%d-%H%M%S')}"
            resp2 = self._api_call(driver, "docmd", "system",
                f"<xcmd cmd='create-guest' name='{guest_name}' ssid='{self.ssid}' "
                f"duration='{duration}' duration-unit='{unit}' x-key='{key}' "
                f"share-number='1' reauth-enabled='false' />")

            # Build duration string for display
            unit_labels = {"hour": "h", "day": "day(s)", "week": "week(s)"}
            duration_str = f"{duration} {unit_labels.get(unit, unit)}"

            # Calculate expiry for display
            if unit == "hour":
                expires_dt = now + timedelta(hours=duration)
            elif unit == "day":
                expires_dt = now + timedelta(days=duration)
            elif unit == "week":
                expires_dt = now + timedelta(weeks=duration)
            else:
                expires_dt = now + timedelta(hours=duration)

            info = {
                "name":     guest_name,
                "key":      key,
                "ssid":     self.ssid,
                "created":  now.strftime("%d.%m.%Y %H:%M"),
                "expires":  expires_dt.strftime("%d.%m.%Y %H:%M"),
                "duration": duration_str,
            }

            # Try to get exact expiry from API response
            body2 = resp2.get("body", "")
            if body2.strip():
                try:
                    root2 = ET.fromstring(body2)
                    xmsg2 = root2.find(".//xmsg")
                    if xmsg2 is not None:
                        guest_elem = xmsg2.find("guest")
                        guest = guest_elem if guest_elem is not None else xmsg2
                        expire_ts = guest.get("expire-time", "")
                        if expire_ts:
                            info["expires"] = datetime.fromtimestamp(
                                int(expire_ts)).strftime("%d.%m.%Y %H:%M")
                        info["name"] = guest.get("name", guest_name)
                except Exception:
                    pass

            return info

        except Exception as e:
            msg = str(e).split("\n")[0][:120]
            raise Exception(msg)
        finally:
            driver.quit()
