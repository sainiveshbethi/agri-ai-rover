from typing import Dict, Any

class TelemetryService:
    def __init__(self):
        # Default initial test sample values (as specified in guidelines for UI testing)
        self._current_readings: Dict[str, float] = {
            "soil_moisture": 39.0,
            "temperature": 25.0,
            "humidity": 68.0,
            "ph": 7.0
        }

    def get_telemetry(self) -> Dict[str, float]:
        """Returns latest telemetry readings."""
        return self._current_readings.copy()

    def update_telemetry(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Updates telemetry readings from ESP32 or manual UI POST request."""
        if "soil_moisture" in data and data["soil_moisture"] is not None:
            try:
                self._current_readings["soil_moisture"] = float(data["soil_moisture"])
            except (ValueError, TypeError):
                pass

        if "temperature" in data and data["temperature"] is not None:
            try:
                self._current_readings["temperature"] = float(data["temperature"])
            except (ValueError, TypeError):
                pass

        if "humidity" in data and data["humidity"] is not None:
            try:
                self._current_readings["humidity"] = float(data["humidity"])
            except (ValueError, TypeError):
                pass

        if "ph" in data and data["ph"] is not None:
            try:
                self._current_readings["ph"] = float(data["ph"])
            except (ValueError, TypeError):
                pass

        return self.get_telemetry()
