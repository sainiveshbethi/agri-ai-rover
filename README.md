# AGRI AI ROVER 🌾🤖
### Hardware Integration & AI Agriculture Intelligence System
*Smart India Hackathon (SIH) Project*

---

## 📌 Project Overview
**AGRI AI ROVER** is an end-to-end smart agriculture monitoring and hardware intelligence platform. It combines **multimodal vision AI (Google Gemini)** with real-time **ESP32 Rover sensor telemetry** (Soil Moisture, Temperature, Humidity, Soil pH), **ESP32-CAM live streaming & frame capture**, and a **server-side Twilio SMS alert engine** with per-alert cooldown protection.

---

## 🌟 Architecture & Operating Modes

```
+-------------------------------------------------------------------------------+
|                                LOCAL LAN MODE                                 |
|                                                                               |
|  ESP32-CAM (http://192.168.1.100) ------> Live MJPEG Stream / Frame Capture   |
|  Main ESP32 (http://192.168.1.101) -----> Direct Sensor Telemetry Fetch       |
|                                                                               |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
|                                CLOUD MODE                                     |
|                                                                               |
|  Main ESP32 -----> HTTPS POST /api/telemetry -----> Render Cloud Server        |
|                                                          │                    |
|  Render Cloud Server -----> GET /api/telemetry --------> Web Dashboard        |
|  Render Cloud Server -----> Twilio API ---------------> SMS Alerts to Farmer |
|                                                                               |
+-------------------------------------------------------------------------------+
```

### 1. Local Mode (Wi-Fi Direct)
- The browser running on the local Wi-Fi network directly connects to the **ESP32-CAM** (`http://192.168.1.100`) for live MJPEG video streaming and single frame capture.
- The browser fetches live sensor readings directly from the **Main ESP32** (`http://192.168.1.101/api/telemetry`).

### 2. Cloud Mode (Render Hosted)
- The **Render cloud backend** (`https://agri-ai-rover.onrender.com`) is a public cloud server. Since cloud servers cannot directly reach private LAN IPs (like `192.168.x.x`), the **Main ESP32** sends telemetry by making outbound HTTPS `POST` requests to `https://agri-ai-rover.onrender.com/api/telemetry`.
- Render stores the latest hardware readings in memory, tracks connection staleness (`last_seen`), and automatically evaluates sensor thresholds to trigger Twilio SMS alerts.

---

## 🔒 HTTPS / Local HTTP Mixed-Content Browser Restriction

When accessing the web app over HTTPS (`https://agri-ai-rover.onrender.com`), modern browsers enforce security policies preventing unencrypted `http://192.168.x.x` streams or API calls from embedding directly inside the HTTPS page (**Mixed Content Restriction**).

**Solutions Provided:**
1. **Cloud Mode (Recommended for Render)**: Configure Main ESP32 to POST telemetry to Render. Render provides telemetry to the frontend securely over HTTPS.
2. **Open Camera in New Tab**: Click **OPEN CAMERA** to view the raw camera stream directly in a browser tab.
3. **Local Testing**: Run the backend locally on `http://127.0.0.1:5000` where HTTP-to-HTTP access is allowed.

---

## 🛠️ Step-by-Step Setup Guide

### STEP 1: Flash ESP32-CAM Firmware
1. Open `firmware/esp32_cam/esp32_cam.ino` in Arduino IDE.
2. Select Board: **AI Thinker ESP32-CAM**.
3. Set your Wi-Fi credentials:
   ```cpp
   const char* WIFI_SSID = "YOUR_WIFI_NAME";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   ```
4. Flash firmware onto the ESP32-CAM module.

---

### STEP 2: Connect ESP32-CAM to Wi-Fi
1. Open Serial Monitor at `115200 baud`.
2. Press the Reset button on ESP32-CAM.
3. Wait for `[Wi-Fi] Connected!` message.

---

### STEP 3: Copy ESP32-CAM IP Address
1. Note the assigned IP address in Serial Monitor:
   ```text
   ESP32-CAM Ready! Use URL: http://192.168.1.100
   Live Stream Endpoint: http://192.168.1.100:81/stream
   ```

---

### STEP 4: Enter ESP32-CAM IP in Website
1. Open the website interface.
2. In **ESP32-CAM HARDWARE FEED**, enter `http://192.168.1.100`.
3. Click **CONNECT CAMERA**.
4. Green status `🟢 Camera connected` will display with live video stream.

---

### STEP 5: Flash ESP32 Rover Firmware
1. Open `firmware/esp32_rover/esp32_rover.ino` in Arduino IDE.
2. Select Board: **ESP32 Dev Module**.
3. Configure Wi-Fi & Render Backend URL:
   ```cpp
   const char* WIFI_SSID = "YOUR_WIFI_NAME";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* RENDER_BACKEND_URL = "https://agri-ai-rover.onrender.com";
   ```
4. Upload firmware to ESP32.

---

### STEP 6: Connect Rover ESP32 to Wi-Fi
1. Open Serial Monitor at `115200 baud`.
2. Verify Wi-Fi connection and assigned IP (e.g. `http://192.168.1.101`).

---

### STEP 7: Configure Render Backend URL
1. Click **⚙️ Settings & Test** on top header.
2. Enter your Render backend URL:
   `https://agri-ai-rover.onrender.com`
3. Click **Save Settings** & **Test Connection**.

---

### STEP 8: Enter ESP32 IP for Local Telemetry
1. In **MAIN ESP32 ROVER TELEMETRY**, enter `http://192.168.1.101`.
2. Click **CONNECT ESP32**.
3. Status badge updates to `🟢 ESP32 connected`.

---

### STEP 9: Add Twilio Environment Variables in Render
1. Open your Render Dashboard -> Service -> **Environment**.
2. Add the following variables:
   - `GEMINI_API_KEY` = `your_gemini_vision_key`
   - `TWILIO_ACCOUNT_SID` = `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - `TWILIO_AUTH_TOKEN` = `your_twilio_auth_token`
   - `TWILIO_PHONE_NUMBER` = `+1XXXXXXXXXX`

---

### STEP 10: Save SMS Settings
1. On website under **SMS ALERT SYSTEM**:
2. Enter Farmer Mobile Number (E.164 format, e.g. `+919876543210`).
3. Set Cooldown Minutes (default `5`).
4. Click **SAVE SMS SETTINGS**.

---

### STEP 11: Send TEST SMS
1. Click **SEND TEST SMS**.
2. Real SMS dispatch status will display: `✅ SMS sent successfully`.

---

### STEP 12: Verify Real Sensor Values
1. Submerge moisture sensor or change pH/temperature.
2. Click **FETCH TELEMETRY** or wait 5 seconds for auto-refresh.
3. Observe live numbers update instantly!

---

## 🔌 Hardware Pinouts

| Sensor Module | ESP32 Pin | Signal Type | Range / Notes |
|:---|:---|:---|:---|
| Capacitive Soil Moisture | **GPIO 34 (A0)** | Analog Input | 0.0% to 100.0% |
| DHT22 / DHT11 Temp & Humidity | **GPIO 4** | Digital Input | -10°C to 60°C / 0-100% RH |
| Analog Soil pH Sensor | **GPIO 35** | Analog Input | pH 0.0 to 14.0 |
| ESP32-CAM Module | **AI-Thinker Pins** | CSI Camera | `/stream` (81) & `/capture` (80) |

---

## 📡 REST API Reference

### Telemetry Endpoints
- **`GET /api/telemetry`**
  - Returns current telemetry, connection state, `last_seen`, staleness (`stale: true` if > 30s).
- **`POST /api/telemetry`**
  - Payload: `{"device_id": "agri-rover-01", "soil_moisture": 42.5, "temperature": 29.4, "humidity": 71.2, "soil_ph": 6.7}`

### SMS Endpoints
- **`GET /api/sms/settings`**: Returns current SMS alert settings & Twilio configuration state.
- **`POST /api/sms/settings`**: Saves farmer mobile number, cooldown timer, and enabled alert flags.
- **`POST /api/sms/test`**: Sends real test SMS via Twilio.

### Vision AI Endpoint
- **`POST /api/analyze`**: Multipart form data with `image` file and optional sensor readings. Processes through multimodal Gemini Vision AI.

---

## 🧪 Running Automated Tests

Run the automated pytest test suite covering telemetry staleness, validation, SMS settings, Twilio failure handling, and alert cooldowns:

```bash
py -m pytest tests/
```

Output:
```text
tests/test_hardware_and_sms.py ....... [100%]
7 passed in 4.58s
```

---

## 📄 License & Hackathon Info
Developed for **Smart India Hackathon (SIH)** — AGRI AI ROVER Team.
