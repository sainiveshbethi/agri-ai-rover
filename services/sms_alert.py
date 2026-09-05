import os
import re
import time
from typing import Dict, Any, List, Optional
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
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
        self.from_number = os.environ.get("TWILIO_PHONE_NUMBER", "").strip()

    def is_twilio_configured(self) -> bool:
        self._reload_env()
        return bool(
            self.account_sid and len(self.account_sid) > 5 and
            self.auth_token and len(self.auth_token) > 5 and
            self.from_number and len(self.from_number) > 3
        )

    def validate_phone_number(self, phone: str) -> bool:
        if not phone or not isinstance(phone, str):
            return False
        clean = phone.strip()
        # E.164 format: + followed by 7 to 15 digits
        pattern = r"^\+?[1-9]\d{7,14}$"
        return bool(re.match(pattern, clean))

    def get_settings(self) -> Dict[str, Any]:
        return {
            "configured": self.is_twilio_configured(),
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
            raise ValueError("Invalid phone number format. Please use E.164 format (e.g., +919876543210 or +1234567890).")

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
        if not self.is_twilio_configured():
            return {
                "success": False,
                "message": "SMS failed: Twilio credentials not configured. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER to environment variables."
            }

        if not self.validate_phone_number(to_number):
            return {
                "success": False,
                "message": "SMS failed: Invalid recipient phone number format."
            }

        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)

            is_trial_env = os.environ.get("TWILIO_IS_TRIAL", "").strip().lower() in ("true", "1", "yes") or \
                           os.environ.get("TWILIO_TRIAL", "").strip().lower() in ("true", "1", "yes")

            if is_trial_env:
                message = client.messages.create(
                    content_sid="sms_internal_alerts",
                    from_=self.from_number,
                    to=to_number
                )
            else:
                try:
                    message = client.messages.create(
                        body=message_body,
                        from_=self.from_number,
                        to=to_number
                    )
                except Exception as e:
                    err_msg = str(e).lower()
                    if any(term in err_msg for term in ["trial", "disallowed parameters", "limited parameter access", "400"]):
                        message = client.messages.create(
                            content_sid="sms_internal_alerts",
                            from_=self.from_number,
                            to=to_number
                        )
                    else:
                        raise e

            return {
                "success": True,
                "sid": message.sid,
                "message": "SMS sent successfully"
            }
        except Exception as e:
            err_msg = str(e)
            return {
                "success": False,
                "message": f"SMS failed: {err_msg}"
            }

    def send_test_sms(self, target_phone: Optional[str] = None) -> Dict[str, Any]:
        phone = (target_phone or self._settings.get("phone_number", "")).strip()
        if not phone:
            return {
                "success": False,
                "message": "SMS failed: No phone number provided. Please enter and save a mobile number first."
            }

        test_msg = (
            "Agri AI Rover Alert System Test\n"
            "This is a test notification from your Agri AI Rover backend server. "
            "Your SMS alert integration is active and working properly!"
        )
        return self.send_sms(phone, test_msg)

    def evaluate_and_trigger_alerts(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        target_phone = self._settings.get("phone_number", "").strip()
        if not target_phone or not self.validate_phone_number(target_phone):
            return []

        if not self.is_twilio_configured():
            return []

        device_id = str(telemetry.get("device_id", "agri-rover-01")).strip()
        cooldown_seconds = self._settings.get("cooldown_minutes", 5) * 60
        now = time.time()
        dispatched_alerts: List[Dict[str, Any]] = []

        soil_moisture = telemetry.get("soil_moisture")
        temperature = telemetry.get("temperature")
        humidity = telemetry.get("humidity")
        soil_ph = telemetry.get("soil_ph") if telemetry.get("soil_ph") is not None else telemetry.get("ph")

        # 1. Low Soil Moisture Alert
        if self._settings.get("low_soil_moisture") and soil_moisture is not None:
            if float(soil_moisture) < LOW_SOIL_MOISTURE_THRESHOLD:
                key = f"{device_id}:low_soil_moisture:{target_phone}"
                last_sent = self._last_sent_timestamps.get(key, 0)
                if now - last_sent >= cooldown_seconds:
                    msg = (
                        f"Agri AI Rover Alert:\n"
                        f"Low soil moisture detected.\n"
                        f"Current soil moisture: {soil_moisture}% (Threshold: {LOW_SOIL_MOISTURE_THRESHOLD}%).\n"
                        f"Please check irrigation system."
                    )
                    res = self.send_sms(target_phone, msg)
                    if res.get("success"):
                        self._last_sent_timestamps[key] = now
                        dispatched_alerts.append({"type": "low_soil_moisture", "status": "sent", "res": res})

        # 2. High Temperature Alert
        if self._settings.get("high_temperature") and temperature is not None:
            if float(temperature) > HIGH_TEMPERATURE_THRESHOLD:
                key = f"{device_id}:high_temperature:{target_phone}"
                last_sent = self._last_sent_timestamps.get(key, 0)
                if now - last_sent >= cooldown_seconds:
                    msg = (
                        f"Agri AI Rover Alert:\n"
                        f"High temperature detected.\n"
                        f"Current temperature: {temperature}°C (Threshold: {HIGH_TEMPERATURE_THRESHOLD}°C).\n"
                        f"Provide shade or cooling to protect crops."
                    )
                    res = self.send_sms(target_phone, msg)
                    if res.get("success"):
                        self._last_sent_timestamps[key] = now
                        dispatched_alerts.append({"type": "high_temperature", "status": "sent", "res": res})

        # 3. Abnormal Humidity Alert
        if self._settings.get("abnormal_humidity") and humidity is not None:
            hum_val = float(humidity)
            if hum_val < LOW_HUMIDITY_THRESHOLD or hum_val > HIGH_HUMIDITY_THRESHOLD:
                key = f"{device_id}:abnormal_humidity:{target_phone}"
                last_sent = self._last_sent_timestamps.get(key, 0)
                if now - last_sent >= cooldown_seconds:
                    cond_str = "Low" if hum_val < LOW_HUMIDITY_THRESHOLD else "High"
                    msg = (
                        f"Agri AI Rover Alert:\n"
                        f"Abnormal humidity ({cond_str}) detected.\n"
                        f"Current humidity: {humidity}% RH (Target range: {LOW_HUMIDITY_THRESHOLD}% - {HIGH_HUMIDITY_THRESHOLD}%)."
                    )
                    res = self.send_sms(target_phone, msg)
                    if res.get("success"):
                        self._last_sent_timestamps[key] = now
                        dispatched_alerts.append({"type": "abnormal_humidity", "status": "sent", "res": res})

        # 4. Abnormal Soil pH Alert
        if self._settings.get("abnormal_soil_ph") and soil_ph is not None:
            ph_val = float(soil_ph)
            if ph_val < LOW_SOIL_PH_THRESHOLD or ph_val > HIGH_SOIL_PH_THRESHOLD:
                key = f"{device_id}:abnormal_soil_ph:{target_phone}"
                last_sent = self._last_sent_timestamps.get(key, 0)
                if now - last_sent >= cooldown_seconds:
                    cond_str = "Acidic" if ph_val < LOW_SOIL_PH_THRESHOLD else "Alkaline"
                    msg = (
                        f"Agri AI Rover Alert:\n"
                        f"Abnormal soil pH ({cond_str}) detected.\n"
                        f"Current soil pH: {soil_ph} (Optimal range: {LOW_SOIL_PH_THRESHOLD} - {HIGH_SOIL_PH_THRESHOLD})."
                    )
                    res = self.send_sms(target_phone, msg)
                    if res.get("success"):
                        self._last_sent_timestamps[key] = now
                        dispatched_alerts.append({"type": "abnormal_soil_ph", "status": "sent", "res": res})

        return dispatched_alerts
