/*
 * AGRI AI ROVER — Main ESP32 Rover Firmware
 * Hardware Telemetry Server & Cloud Sync Client
 * 
 * Target Board: ESP32 Dev Module
 * Sensor Hardware:
 *   - Soil Moisture: Capacitive Soil Moisture Sensor (Analog PIN 34)
 *   - Temperature & Humidity: DHT22 / DHT11 Sensor (Digital PIN 4)
 *   - Soil pH: Analog Soil pH Sensor Module (Analog PIN 35)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================================================
// NETWORK & CLOUD AUTHENTICATION CONFIGURATION (USER EDITABLE)
// ============================================================================
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Render Backend Cloud URL (HTTPS)
const char* RENDER_BACKEND_URL = "https://agri-ai-rover.onrender.com";
const char* DEVICE_ID = "agri-rover-01";

// Rover Authentication Token (Must match ROVER_API_TOKEN in Render environment variables)
const char* ROVER_API_TOKEN = "YOUR_ROVER_API_TOKEN";

// Cloud POST interval (milliseconds)
const unsigned long CLOUD_SYNC_INTERVAL = 5000; // 5 seconds

// ============================================================================
// HARDWARE SENSOR CONFIGURATION & SIMULATION FLAG
// ============================================================================
// IMPORTANT: SENSOR_SIMULATION MUST DEFAULT TO FALSE FOR REAL HARDWARE
#define SENSOR_SIMULATION false

const int PIN_SOIL_MOISTURE = 34; // Analog Input GPIO 34
const int PIN_DHT_DATA      = 4;  // Digital Input GPIO 4
const int PIN_SOIL_PH       = 35; // Analog Input GPIO 35

// WebServer instance on port 80
WebServer server(80);
unsigned long lastCloudSync = 0;

// ============================================================================
// HARDWARE SENSOR READ FUNCTIONS (HARDWARE ABSTRACTION LAYER)
// ============================================================================

/**
 * Reads capacitive soil moisture sensor (Analog Pin 34).
 * Returns moisture percentage (0.0% to 100.0%).
 */
float readSoilMoisture() {
#if SENSOR_SIMULATION
    // Development Simulation Only (Used ONLY when SENSOR_SIMULATION is true)
    return 42.5;
#else
    int raw = analogRead(PIN_SOIL_MOISTURE);
    // Typical ESP32 ADC: Dry ~3200, Wet ~1400 (Adjust calibration for your sensor)
    const int airValue = 3200;
    const int waterValue = 1400;
    float moisture = map(raw, airValue, waterValue, 0, 100);
    return constrain(moisture, 0.0, 100.0);
#endif
}

/**
 * Reads ambient temperature (°C).
 */
float readTemperature() {
#if SENSOR_SIMULATION
    return 29.4;
#else
    // Replace with DHT sensor library call e.g., dht.readTemperature()
    int raw = analogRead(PIN_DHT_DATA);
    float temp = 15.0 + (raw / 4095.0) * 30.0;
    return constrain(temp, -10.0, 60.0);
#endif
}

/**
 * Reads relative humidity (% RH).
 */
float readHumidity() {
#if SENSOR_SIMULATION
    return 71.2;
#else
    // Replace with DHT sensor library call e.g., dht.readHumidity()
    int raw = analogRead(PIN_DHT_DATA);
    float hum = 30.0 + (raw / 4095.0) * 60.0;
    return constrain(hum, 0.0, 100.0);
#endif
}

/**
 * Reads analog soil pH probe (0.0 to 14.0).
 */
float readSoilPH() {
#if SENSOR_SIMULATION
    return 6.7;
#else
    int raw = analogRead(PIN_SOIL_PH);
    float voltage = (raw / 4095.0) * 3.3;
    float ph = 3.5 * voltage;
    return constrain(ph, 0.0, 14.0);
#endif
}

// ============================================================================
// HTTP ROUTE HANDLERS WITH CORS
// ============================================================================

void setCORSHeaders() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
}

void handleOptions() {
    setCORSHeaders();
    server.send(200, "text/plain", "");
}

void handleRoot() {
    setCORSHeaders();
    String html = "<html><head><title>Agri AI Rover - ESP32 Telemetry Server</title></head>"
                  "<body style='font-family:sans-serif; padding:2rem;'>"
                  "<h1>🌱 Agri AI Rover - ESP32 Telemetry Hardware Node</h1>"
                  "<p>Status: <strong>Online & Transmitting</strong></p>"
                  "<p>Local Telemetry Endpoint: <a href='/api/telemetry'>/api/telemetry</a></p>"
                  "</body></html>";
    server.send(200, "text/html", html);
}

void handleTelemetryGET() {
    setCORSHeaders();

    float moisture = readSoilMoisture();
    float temp = readTemperature();
    float hum = readHumidity();
    float ph = readSoilPH();

    StaticJsonDocument<256> doc;
    doc["soil_moisture"] = moisture;
    doc["temperature"] = temp;
    doc["humidity"] = hum;
    doc["soil_ph"] = ph;
    doc["timestamp"] = millis() / 1000;
    doc["device_id"] = DEVICE_ID;

    String jsonResponse;
    serializeJson(doc, jsonResponse);

    server.send(200, "application/json", jsonResponse);
}

// ============================================================================
// HTTPS CLOUD TELEMETRY POST FUNCTION (WiFiClientSecure)
// ============================================================================

void postTelemetryToCloud() {
    if (WiFi.status() != WL_CONNECTED) return;

    WiFiClientSecure client;
    // DEMO ONLY: setInsecure() bypasses SSL cert verification for testing.
    // PRODUCTION REQUIREMENT: Replace setInsecure() with client.setCACert(rootCACertificate) for full TLS validation.
    client.setInsecure();

    HTTPClient http;
    String endpoint = String(RENDER_BACKEND_URL) + "/api/telemetry";

    if (http.begin(client, endpoint)) {
        http.addHeader("Content-Type", "application/json");

        // Add Bearer Token if configured
        if (String(ROVER_API_TOKEN).length() > 0 && String(ROVER_API_TOKEN) != "YOUR_ROVER_API_TOKEN") {
            http.addHeader("Authorization", String("Bearer ") + ROVER_API_TOKEN);
        }

        StaticJsonDocument<256> doc;
        doc["device_id"] = DEVICE_ID;
        doc["soil_moisture"] = readSoilMoisture();
        doc["temperature"] = readTemperature();
        doc["humidity"] = readHumidity();
        doc["soil_ph"] = readSoilPH();

        String payload;
        serializeJson(doc, payload);

        int httpCode = http.POST(payload);
        if (httpCode > 0) {
            Serial.printf("[HTTPS CLOUD SYNC] Telemetry POST success (HTTP %d)\n", httpCode);
        } else {
            Serial.printf("[HTTPS CLOUD SYNC] Telemetry POST failed: %s\n", http.errorToString(httpCode).c_str());
        }
        http.end();
    } else {
        Serial.println("[HTTPS CLOUD SYNC] Failed to establish WiFiClientSecure connection");
    }
}

// ============================================================================
// SETUP & LOOP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n==================================================");
    Serial.println("Agri AI Rover - Main ESP32 Hardware Starting...");
    Serial.println("==================================================");

    // Pin Modes
    pinMode(PIN_SOIL_MOISTURE, INPUT);
    pinMode(PIN_SOIL_PH, INPUT);

    // Wi-Fi Connection
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n[Wi-Fi] Connected Successfully!");
    Serial.print("[Wi-Fi] ESP32 Rover Local IP: http://");
    Serial.println(WiFi.localIP());

    // Register Server Routes
    server.on("/", HTTP_GET, handleRoot);
    server.on("/api/telemetry", HTTP_GET, handleTelemetryGET);
    server.on("/api/telemetry", HTTP_OPTIONS, handleOptions);

    server.begin();
    Serial.println("[HTTP Server] Listening on port 80");
}

void loop() {
    server.handleClient();

    // Periodic HTTPS Cloud Telemetry Sync
    unsigned long currentMillis = millis();
    if (currentMillis - lastCloudSync >= CLOUD_SYNC_INTERVAL) {
        lastCloudSync = currentMillis;
        postTelemetryToCloud();
    }
}
