import os
import time
import pytest
from app import app
from services.telemetry import TelemetryService
from services.sms_alert import SmsAlertService, LOW_SOIL_MOISTURE_THRESHOLD, HIGH_TEMPERATURE_THRESHOLD

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_telemetry_service_initial_empty():
    ts = TelemetryService(stale_threshold_seconds=30)
    data = ts.get_telemetry()
    assert data["connected"] is False
    assert data["stale"] is False
    assert data["message"] == "No telemetry received"
    assert data["soil_moisture"] is None

def test_telemetry_service_update_and_stale():
    ts = TelemetryService(stale_threshold_seconds=2)
    payload = {
        "device_id": "rover-test-01",
        "soil_moisture": 42.5,
        "temperature": 29.4,
        "humidity": 71.2,
        "soil_ph": 6.7
    }
    updated = ts.update_telemetry(payload)
    assert updated["connected"] is True
    assert updated["stale"] is False
    assert updated["soil_moisture"] == 42.5
    assert updated["temperature"] == 29.4
    assert updated["humidity"] == 71.2
    assert updated["soil_ph"] == 6.7
    assert updated["device_id"] == "rover-test-01"

    # Simulate staleness by advancing time or setting _last_seen
    ts._last_seen = time.time() - 5  # > 2s threshold
    stale_data = ts.get_telemetry()
    assert stale_data["connected"] is False
    assert stale_data["stale"] is True
    assert "stale data" in stale_data["message"].lower() or "lost" in stale_data["message"].lower()

def test_rover_token_authentication(client):
    # Set expected token in environment
    os.environ["ROVER_API_TOKEN"] = "SECRET_ROVER_TOKEN_123"

    try:
        post_payload = {
            "device_id": "secured-rover-01",
            "soil_moisture": 45.0,
            "temperature": 26.0
        }

        # 1. Missing Authorization header -> HTTP 401
        res_no_auth = client.post('/api/telemetry', json=post_payload)
        assert res_no_auth.status_code == 401
        assert "Unauthorized" in res_no_auth.get_json()["message"]

        # 2. Invalid Bearer Token -> HTTP 401
        res_bad_auth = client.post('/api/telemetry', json=post_payload, headers={"Authorization": "Bearer WRONG_TOKEN"})
        assert res_bad_auth.status_code == 401

        # 3. Valid Bearer Token -> HTTP 200
        res_valid_auth = client.post('/api/telemetry', json=post_payload, headers={"Authorization": "Bearer SECRET_ROVER_TOKEN_123"})
        assert res_valid_auth.status_code == 200
        assert res_valid_auth.get_json()["status"] == "success"
    finally:
        # Clean up env var
        os.environ.pop("ROVER_API_TOKEN", None)

def test_telemetry_api_endpoints(client):
    # GET initial telemetry
    res = client.get('/api/telemetry')
    assert res.status_code == 200
    json_data = res.get_json()
    assert "connected" in json_data

    # POST new telemetry
    post_payload = {
        "device_id": "api-rover-99",
        "soil_moisture": 38.0,
        "temperature": 27.5,
        "humidity": 65.0,
        "soil_ph": 6.8
    }
    res_post = client.post('/api/telemetry', json=post_payload)
    assert res_post.status_code == 200
    data_post = res_post.get_json()
    assert data_post["status"] == "success"
    assert data_post["telemetry"]["soil_moisture"] == 38.0

def test_sms_alert_service_phone_validation():
    sms = SmsAlertService()
    assert sms.validate_phone_number("+919876543210") is True
    assert sms.validate_phone_number("+12025550123") is True
    assert sms.validate_phone_number("invalid-phone") is False
    assert sms.validate_phone_number("123") is False

def test_sms_settings_api(client):
    # Test invalid phone number error
    bad_payload = {
        "phone_number": "12345",
        "cooldown_minutes": 5
    }
    res_bad = client.post('/api/sms/settings', json=bad_payload)
    assert res_bad.status_code == 400
    assert "Invalid phone number" in res_bad.get_json()["message"]

    # Test valid phone number save
    good_payload = {
        "phone_number": "+919876543210",
        "cooldown_minutes": 10,
        "low_soil_moisture": True,
        "high_temperature": True,
        "abnormal_humidity": True,
        "abnormal_soil_ph": True
    }
    res_good = client.post('/api/sms/settings', json=good_payload)
    assert res_good.status_code == 200
    assert res_good.get_json()["status"] == "success"

def test_sms_test_unconfigured(client):
    # Without valid Twilio env vars, test SMS must return failure message
    res = client.post('/api/sms/test', json={"phone_number": "+919876543210"})
    json_res = res.get_json()
    assert res.status_code in (400, 200)
    if not json_res.get("success"):
        assert "twilio" in json_res["message"].lower() or "failed" in json_res["message"].lower()

def test_sms_cooldown_and_different_alert_types():
    sms = SmsAlertService()
    sms.save_settings({
        "phone_number": "+919876543210",
        "cooldown_minutes": 5,
        "low_soil_moisture": True,
        "high_temperature": True
    })

    # Mock send_sms to record calls without hitting Twilio API
    sent_log = []
    sms.send_sms = lambda phone, msg: sent_log.append(msg) or {"success": True, "sid": "MOCK123"}
    sms.is_twilio_configured = lambda: True

    # Combined anomaly trigger: Low moisture (18% < 30%) AND High temp (39°C > 35°C)
    telemetry_trigger = {
        "device_id": "rover-multi-01",
        "soil_moisture": 18.0,
        "temperature": 39.0,
        "humidity": 60.0,
        "soil_ph": 6.8
    }

    alerts1 = sms.evaluate_and_trigger_alerts(telemetry_trigger)
    assert len(alerts1) == 2
    assert len(sent_log) == 2

    # Immediate second telemetry request -> both low moisture and high temp blocked by independent per-alert cooldown
    alerts2 = sms.evaluate_and_trigger_alerts(telemetry_trigger)
    assert len(alerts2) == 0
    assert len(sent_log) == 2  # No new SMS dispatched!
