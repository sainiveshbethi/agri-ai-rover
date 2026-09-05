import os
import io
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image

from services.vision import VisionAIService
from services.crop_database import CropDatabaseService
from services.analysis_engine import AgriculturalDecisionEngine
from services.telemetry import TelemetryService
from services.sms_alert import SmsAlertService

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit

# Initialize Services
vision_service = VisionAIService()
crop_db_service = CropDatabaseService()
decision_engine = AgriculturalDecisionEngine()
telemetry_service = TelemetryService()
sms_alert_service = SmsAlertService()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/')
def index():
    """Renders main user interface using templates/index.html."""
    return render_template('index.html')

@app.route('/api/test-gemini', methods=['GET', 'OPTIONS'])
def test_gemini():
    """Endpoint for testing live Gemini Vision API connectivity."""
    if request.method == 'OPTIONS':
        return '', 200
    res = vision_service.test_connection()
    status_code = 200 if res.get("status") == "connected" else 400
    return jsonify(res), status_code

@app.route('/api/telemetry', methods=['GET', 'POST', 'OPTIONS'])
def handle_telemetry():
    """Endpoint for reading and submitting live ESP32 rover telemetry data."""
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'POST':
        # Verify Rover Authentication Token if configured on server
        expected_token = os.environ.get("ROVER_API_TOKEN", "").strip()
        if expected_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != f"Bearer {expected_token}":
                return jsonify({
                    "status": "error",
                    "message": "Unauthorized: Missing or invalid Rover API Token"
                }), 401

        try:
            data = request.get_json(force=True, silent=True) or {}
            updated = telemetry_service.update_telemetry(data)
            dispatched_alerts = sms_alert_service.evaluate_and_trigger_alerts(updated)
            return jsonify({
                "status": "success",
                "message": "Telemetry updated successfully",
                "telemetry": updated,
                "alerts_triggered": len(dispatched_alerts)
            }), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400
    else:
        return jsonify(telemetry_service.get_telemetry()), 200

@app.route('/api/sms/settings', methods=['GET', 'POST', 'OPTIONS'])
def sms_settings():
    """Endpoint for reading and saving SMS alert system configurations."""
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'POST':
        try:
            data = request.get_json(force=True, silent=True) or {}
            updated = sms_alert_service.save_settings(data)
            return jsonify({
                "status": "success",
                "message": "SMS settings saved successfully",
                "data": updated
            }), 200
        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify(sms_alert_service.get_settings()), 200

@app.route('/api/sms/test', methods=['POST', 'OPTIONS'])
def sms_test():
    """Endpoint for sending real test SMS via Twilio."""
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(force=True, silent=True) or {}
    target_phone = data.get("phone_number")
    res = sms_alert_service.send_test_sms(target_phone)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_crop():
    """Main image analysis route processing upload through Gemini Vision AI and Decision Engine."""
    if request.method == 'OPTIONS':
        return '', 200
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided in request."}), 400

    file = request.files['image']
    if file.filename == '' or not file:
        return jsonify({"error": "No image file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file format. Supported formats: PNG, JPG, JPEG, WEBP."}), 400

    # Parse sensor inputs (optional)
    def parse_optional_float(val):
        if val is None or str(val).strip() == '':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    soil_moisture = parse_optional_float(request.form.get('soil_moisture'))
    temperature = parse_optional_float(request.form.get('temperature'))
    humidity = parse_optional_float(request.form.get('humidity'))
    ph = parse_optional_float(request.form.get('ph'))

    sensor_data = {
        "soil_moisture": soil_moisture,
        "temperature": temperature,
        "humidity": humidity,
        "ph": ph
    }

    # Process image with PIL
    try:
        image_bytes = file.read()
        pil_image = Image.open(io.BytesIO(image_bytes))
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')
    except Exception as e:
        return jsonify({"error": f"Invalid image file: {str(e)}. Image quality is insufficient for reliable identification."}), 400

    # Check API key before sending
    if not vision_service.is_configured():
        return jsonify({
            "error": "Gemini API key missing. Please set GEMINI_API_KEY in .env file."
        }), 400

    # 1. Gemini Multimodal Vision AI Analysis
    try:
        vision_result = vision_service.analyze_crop_image(pil_image)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        err_msg = str(e)
        if vision_service.api_key and vision_service.api_key in err_msg:
            err_msg = err_msg.replace(vision_service.api_key, "[REDACTED_API_KEY]")
        return jsonify({"error": f"Gemini API request failed: {err_msg}"}), 500

    # 2. Database Lookup
    identified_item = vision_result.get("identified_item") or vision_result.get("crop_name", "")
    crop_profile = crop_db_service.get_crop(identified_item)

    # 3. Agricultural Decision Engine Evaluation
    analysis_output = decision_engine.analyze(
        vision_result=vision_result,
        crop_profile=crop_profile,
        sensor_data=sensor_data
    )

    return jsonify(analysis_output), 200

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Uploaded image file is too large (max 16 MB)."}), 413

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal server error occurred."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    is_debug = os.environ.get("FLASK_ENV", "development").lower() == "development"
    print(f"==================================================")
    print(f"[AGRI AI ROVER] Server Starting on port {port} (Debug: {is_debug})")
    print(f"==================================================")
    app.run(host='0.0.0.0', port=port, debug=is_debug)
