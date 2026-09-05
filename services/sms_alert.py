import os
import re
import time
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

# Base directory environment loading
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv(override=True)

# Default Agriculture Threshold Config (easily adjustable)
LOW_SOIL_MOISTURE_THRESHOLD = 30.0   # %
HIGH_TEMPERATURE_THRESHOLD = 35.0   # °C
LOW_HUMIDITY_THRESHOLD = 40.0       # %
HIGH_HUMIDITY_THRESHOLD = 85.0      # %
LOW_SOIL_PH_THRESHOLD = 5.5
HIGH_SOIL_PH_THRESHOLD = 7.5

class SmsAlertService:
    def __init__(self):
        self._reload_env()
        self._settings: Dict[str, Any] = {
            "phone_number": "",
            "cooldown_minutes": 5,
            "low_soil_moisture": True,
            "high_temperature": True,
            "abnormal_humidity": True,
            "abnormal_soil_ph": True
        }
        self._last_sent_timestamps: Dict[str, float] = {}

    def _reload_env(self):
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
        self.api_key = os.environ.get("FAST2SMS_API_KEY", "").strip()

    def is_sms_configured(self) -> bool:
        self._reload_env()
        return bool(self.api_key and len(self.api_key) > 5)

    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Safely normalizes Indian phone numbers for Fast2SMS (e.g. 9876543210 -> 919876543210)."""
        if not phone or not isinstance(phone, str):
            return None
        clean = re.sub(r"\D", "", phone.strip())
        if len(clean) == 10 and clean[0] in "6789":
            return f"91{clean}"
        elif len(clean) == 11 and clean.startswith("0") and clean[1] in "6789":
            return f"91{clean[1:]}"
        elif len(clean) == 12 and clean.startswith("91") and clean[2] in "6789":
            return clean
        return None

    def validate_phone_number(self, phone: str) -> bool:
        return self.normalize_phone_number(phone) is not None

    def get_settings(self) -> Dict[str, Any]:
        return {
            "configured": self.is_sms_configured(),
            "settings": self._settings.copy(),
            "thresholds": {
                "low_soil_moisture": LOW_SOIL_MOISTURE_THRESHOLD,
                "high_temperature": HIGH_TEMPERATURE_THRESHOLD,
                "low_humidity": LOW_HUMIDITY_THRESHOLD,
                "high_humidity": HIGH_HUMIDITY_THRESHOLD,
                "low_soil_ph": LOW_SOIL_PH_THRESHOLD,
                "high_soil_ph": HIGH_SOIL_PH_THRESHOLD
            }
        }

    def save_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Invalid settings payload: must be a JSON object")

        phone = str(data.get("phone_number", "")).strip()
        if phone and not self.validate_phone_number(phone):
            raise ValueError("Invalid phone number format. Please enter a valid 10-digit mobile number.")

        cooldown = data.get("cooldown_minutes", 5)
        try:
            cooldown_val = max(1, int(cooldown))
        except (ValueError, TypeError):
            cooldown_val = 5

        self._settings["phone_number"] = phone
        self._settings["cooldown_minutes"] = cooldown_val
        self._settings["low_soil_moisture"] = bool(data.get("low_soil_moisture", True))
        self._settings["high_temperature"] = bool(data.get("high_temperature", True))
        self._settings["abnormal_humidity"] = bool(data.get("abnormal_humidity", True))
        self._settings["abnormal_soil_ph"] = bool(data.get("abnormal_soil_ph", True))

        return self.get_settings()

    def send_sms(self, to_number: str, message_body: str) -> Dict[str, Any]:
        if not self.is_sms_configured():
            return {
                "success": False,
                "message": "SMS service not configured. FAST2SMS_API_KEY environment variable missing."
            }

        normalized_phone = self.normalize_phone_number(to_number)
        if not normalized_phone:
            return {
                "success": False,
                "message": "SMS failed: Invalid recipient phone number format."
            }

        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "route": "q",
            "message": message_body,
            "numbers": normalized_phone
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            res_data = response.json() if response.content else {}

            if response.status_code == 200 and res_data.get("return") is True:
                msg_list = res_data.get("message", [])
                succ_msg = msg_list[0] if isinstance(msg_list, list) and msg_list else "SMS sent successfully."
                return {
                    "success": True,
                    "request_id": res_data.get("request_id"),
                    "message": f"SMS sent successfully. ({succ_msg})"
                }
            else:
                err_msg = res_data.get("message") or res_data.get("error") or f"HTTP {response.status_code} error from Fast2SMS"
                if isinstance(err_msg, list):
                    err_msg = ", ".join(err_msg)
                return {
                    "success": False,
                    "message": f"Fast2SMS API error: {err_msg}"
                }
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Fast2SMS API error: Request timed out."}
        except requests.exceptions.RequestException as req_err:
            return {"success": False, "message": f"Fast2SMS network error: {str(req_err)}"}
        except Exception as e:
            return {"success": False, "message": f"SMS dispatch failed: {str(e)}"}

    def send_test_sms(self, target_phone: Optional[str] = None) -> Dict[str, Any]:
        phone = (target_phone or self._settings.get("phone_number", "")).strip()
        if not phone:
            return {
                "success": False,
                "message": "SMS failed: No phone number provided. Please enter a mobile number first."
            }

        test_msg = "AGRI AI ROVER TEST ALERT: SMS system is working successfully."
        return self.send_sms(phone, test_msg)

    def evaluate_and_trigger_alerts(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        target_phone = self._settings.get("phone_number", "").strip()
        normalized_phone = self.normalize_phone_number(target_phone)
        if not normalized_phone or not self.is_sms_configured():
            return []

        device_id = str(telemetry.get("device_id", "agri-rover-01")).strip()
        cooldown_seconds = self._settings.get("cooldown_minutes", 5) * 60
        now = time.time()
        dispatched_alerts: List[Dict[str, Any]] = []

        soil_moisture = telemetry.get("soil_moisture", "N/A")
        temperature = telemetry.get("temperature", "N/A")
        humidity = telemetry.get("humidity", "N/A")
        soil_ph = telemetry.get("soil_ph") if telemetry.get("soil_ph") is not None else telemetry.get("ph", "N/A")

        def build_alert_sms(alert_text: str, action_text: str) -> str:
            return (
                f"AGRI AI ROVER ALERT:\n"
                f"Soil Moisture: {soil_moisture}%\n"
                f"Temperature: {temperature}°C\n"
                f"Humidity: {humidity}%\n"
                f"Soil pH: {soil_ph}\n"
                f"Alert: {alert_text}\n"
                f"Action: {action_text}"
            )

        # 1. Low Soil Moisture Alert
        if self._settings.get("low_soil_moisture") and soil_moisture != "N/A":
            try:
                if float(soil_moisture) < LOW_SOIL_MOISTURE_THRESHOLD:
                    key = f"{device_id}:low_soil_moisture:{normalized_phone}"
                    last_sent = self._last_sent_timestamps.get(key, 0)
                    if now - last_sent >= cooldown_seconds:
                        msg = build_alert_sms("Low soil moisture detected.", "Irrigation recommended.")
                        res = self.send_sms(normalized_phone, msg)
                        if res.get("success"):
                            self._last_sent_timestamps[key] = now
                            dispatched_alerts.append({"type": "low_soil_moisture", "status": "sent", "res": res})
            except (ValueError, TypeError):
                pass

        # 2. High Temperature Alert
        if self._settings.get("high_temperature") and temperature != "N/A":
            try:
                if float(temperature) > HIGH_TEMPERATURE_THRESHOLD:
                    key = f"{device_id}:high_temperature:{normalized_phone}"
                    last_sent = self._last_sent_timestamps.get(key, 0)
                    if now - last_sent >= cooldown_seconds:
                        msg = build_alert_sms("High temperature detected.", "Cooling / shading recommended.")
                        res = self.send_sms(normalized_phone, msg)
                        if res.get("success"):
                            self._last_sent_timestamps[key] = now
                            dispatched_alerts.append({"type": "high_temperature", "status": "sent", "res": res})
            except (ValueError, TypeError):
                pass

        # 3. Abnormal Humidity Alert
        if self._settings.get("abnormal_humidity") and humidity != "N/A":
            try:
                hum_val = float(humidity)
                if hum_val < LOW_HUMIDITY_THRESHOLD or hum_val > HIGH_HUMIDITY_THRESHOLD:
                    key = f"{device_id}:abnormal_humidity:{normalized_phone}"
                    last_sent = self._last_sent_timestamps.get(key, 0)
                    if now - last_sent >= cooldown_seconds:
                        cond_str = "Low humidity" if hum_val < LOW_HUMIDITY_THRESHOLD else "High humidity"
                        msg = build_alert_sms(f"Abnormal humidity ({cond_str}).", "Regulate greenhouse/ventilation.")
                        res = self.send_sms(normalized_phone, msg)
                        if res.get("success"):
                            self._last_sent_timestamps[key] = now
                            dispatched_alerts.append({"type": "abnormal_humidity", "status": "sent", "res": res})
            except (ValueError, TypeError):
                pass

        # 4. Abnormal Soil pH Alert
        if self._settings.get("abnormal_soil_ph") and soil_ph != "N/A":
            try:
                ph_val = float(soil_ph)
                if ph_val < LOW_SOIL_PH_THRESHOLD or ph_val > HIGH_SOIL_PH_THRESHOLD:
                    key = f"{device_id}:abnormal_soil_ph:{normalized_phone}"
                    last_sent = self._last_sent_timestamps.get(key, 0)
                    if now - last_sent >= cooldown_seconds:
                        cond_str = "Acidic soil" if ph_val < LOW_SOIL_PH_THRESHOLD else "Alkaline soil"
                        msg = build_alert_sms(f"Abnormal soil pH ({cond_str}).", "Soil amendment recommended.")
                        res = self.send_sms(normalized_phone, msg)
                        if res.get("success"):
                            self._last_sent_timestamps[key] = now
                            dispatched_alerts.append({"type": "abnormal_soil_ph", "status": "sent", "res": res})
            except (ValueError, TypeError):
                pass

        return dispatched_alerts
