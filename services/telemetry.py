import time
from typing import Dict, Any, Optional

class TelemetryService:
    def __init__(self, stale_threshold_seconds: int = 30):
        self._soil_moisture: Optional[float] = None
        self._temperature: Optional[float] = None
        self._humidity: Optional[float] = None
        self._soil_ph: Optional[float] = None
        self._last_seen: Optional[float] = None
        self._device_id: str = "agri-rover-01"
        self._stale_threshold_seconds: int = stale_threshold_seconds

    def _parse_float(self, val: Any) -> Optional[float]:
        if val is None or str(val).strip() == "" or str(val).strip().lower() in ("null", "none", "nan", "--"):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns latest telemetry readings along with connection state and staleness tracking."""
        if self._last_seen is None:
            return {
                "connected": False,
                "stale": False,
                "message": "No telemetry received",
                "device_id": self._device_id,
                "last_seen": None,
                "age_seconds": None,
                "soil_moisture": None,
                "temperature": None,
                "humidity": None,
                "soil_ph": None,
                "ph": None
            }

        age_seconds = int(time.time() - self._last_seen)
        is_stale = age_seconds > self._stale_threshold_seconds

        return {
            "connected": not is_stale,
            "stale": is_stale,
            "message": "ESP32 connection lost (stale data)" if is_stale else "ESP32 connected",
            "device_id": self._device_id,
            "last_seen": self._last_seen,
            "age_seconds": age_seconds,
            "soil_moisture": self._soil_moisture,
            "temperature": self._temperature,
            "humidity": self._humidity,
            "soil_ph": self._soil_ph,
            "ph": self._soil_ph
        }

    def update_telemetry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates telemetry readings from ESP32 or manual UI POST request."""
        if not isinstance(data, dict):
            raise ValueError("Invalid telemetry payload: must be a JSON object")

        if "device_id" in data and isinstance(data["device_id"], str) and data["device_id"].strip():
            self._device_id = data["device_id"].strip()

        if "soil_moisture" in data:
            self._soil_moisture = self._parse_float(data["soil_moisture"])

        if "temperature" in data:
            self._temperature = self._parse_float(data["temperature"])

        if "humidity" in data:
            self._humidity = self._parse_float(data["humidity"])

        # Support both 'soil_ph' and 'ph'
        if "soil_ph" in data:
            self._soil_ph = self._parse_float(data["soil_ph"])
        elif "ph" in data:
            self._soil_ph = self._parse_float(data["ph"])

        self._last_seen = time.time()
        return self.get_telemetry()
