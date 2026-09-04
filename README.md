# AGRI AI ROVER 🌾🤖
### AI-Powered Agriculture Monitoring & Smart Decision System
*Smart India Hackathon (SIH) Project*

---

## 📌 Project Overview
**AGRI AI ROVER** is a full-stack smart agriculture monitoring platform designed for farmers, agronomists, and agricultural students. It combines **real-time multimodal vision AI (Google Gemini)** with **rover sensor telemetry** (Soil Moisture, Temperature, Humidity, Soil pH) and a structured **Crop Knowledge Database** to provide scientific crop identification, visual health condition diagnosis, environmental suitability matrix, and smart context-aware irrigation guidance.

---

## 🌟 Key Features

1. **Real Vision AI Image Analysis (No Fake Results)**:
   - Evaluates user-uploaded photos of seeds, grains, leaves, plants, vegetables, or fruits.
   - Identifies crop species, scientific names, confidence scores, and alternative candidates.
   - Detects physical defects, decay/rot, discoloration, lesions, or insect damage.
   - Returns `"Unknown / Low confidence"` or `"Not a crop/seed or unable to identify"` when uncertain or given non-agricultural images.

2. **Pluggable Seed Classification Architecture**:
   - Built-in `SeedClassifierAdapter` hook supporting dedicated local seed classification models alongside Gemini Vision AI.

3. **Rover Telemetry & ESP32 Integration**:
   - `POST /api/telemetry` endpoint for live ESP32 sensor hardware updates.
   - Manual UI sensor controls for on-site testing.

4. **Structured Crop Knowledge Base**:
   - Local JSON database covering major Indian agricultural crops: *Paddy/Rice, Wheat, Maize, Soybean, Cotton, Groundnut, Chickpea, Green Gram, Black Gram, Mustard, Sunflower, Tomato, Potato, Chilli, Brinjal*.

5. **Agricultural Decision & Irrigation Engine**:
   - Evaluates environmental sensor metrics against crop agronomic specifications into 5 categories: `OPTIMAL`, `GOOD`, `MODERATE`, `NEEDS ATTENTION`, `UNSUITABLE`.
   - Tailors irrigation advice considering crop type + soil moisture + growth stage + temperature + humidity.

6. **Single-File Frontend & Decoupled Production Architecture**:
   - Entire frontend packaged into single self-contained file: [`agri_ai_rover.html`](file:///c:/Users/SAI%20NIVESH/.antigravity-ide/extensions/vscjava.vscode-maven-0.45.3-universal/agri_ai_rover/agri_ai_rover.html).
   - Zero Gemini API key exposure on frontend. Key remains 100% server-side on backend.

---

## 🛠️ Project Structure

```
agri_ai_rover/
├── agri_ai_rover.html          # Standalone single-file frontend for Netlify deployment
├── app.py                      # Flask web server & REST API endpoints
├── requirements.txt            # Production dependencies (Flask, Flask-CORS, Gunicorn, Pillow)
├── Procfile                    # Deployment entry point (web: gunicorn app:app)
├── render.yaml                 # Render Blueprint configuration file
├── .env                        # Private environment configuration (GEMINI_API_KEY)
├── .env.example                # Environment variable configuration template
├── README.md                   # Documentation & deployment guide
├── services/
│   ├── __init__.py             # Package initializer
│   ├── vision.py               # Multimodal Gemini Vision AI & seed adapter
│   ├── crop_database.py        # Structured crop database search engine
│   ├── analysis_engine.py      # Agronomic evaluation & irrigation decision engine
│   └── telemetry.py            # Hardware telemetry cache & state manager
├── data/
│   └── crops.json              # 15+ Indian crop profiles database
├── templates/
│   └── index.html              # Synchronized frontend template
└── static/
    ├── style.css               # Vanilla CSS design system
    └── app.js                  # Frontend controller
```

---

## 🚀 Quickstart & Local Development

### 1. Prerequisites
- Python 3.9 or higher
- A Google Gemini API Key (obtain from [Google AI Studio](https://aistudio.google.com/))

### 2. Setup Environment
Open your terminal in the `agri_ai_rover` project directory:

```bash
# Create virtual environment (optional)
py -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install required dependencies
py -m pip install -r requirements.txt
```

### 3. Configure API Key
Copy `.env.example` to `.env` and add your Gemini API Key:

```env
GEMINI_API_KEY=AIzaSy...your_actual_gemini_api_key...
PORT=5000
FLASK_ENV=development
```

### 4. Run Application Locally
```bash
python app.py
# or using py launcher:
py app.py
```

Access the application in your web browser:
👉 **`http://127.0.0.1:5000`**

---

## 🌐 Production Deployment Architecture (Netlify + Render)

To make the application available publicly so anyone can access the site from any browser without exposing your Gemini API key:

```
┌───────────────────────────────┐                  ┌───────────────────────────────┐
│       NETLIFY FRONTEND        │                  │         RENDER BACKEND        │
│    (agri_ai_rover.html)       │ ───────────────> │           (app.py)            │
│  Public Single-Page Website   │   HTTPS API      │  Hosts Gemini API Key safely  │
└───────────────────────────────┘   Requests       └───────────────────────────────┘
                                                          │
                                                          ▼
                                                   ┌──────────────┐
                                                   │ Google Gemini│
                                                   │ Vision AI API│
                                                   └──────────────┘
```

### Step 1: Deploy Backend to Render (Python Host)

1. Push your project code to a **GitHub / GitLab repository**.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** -> **Web Service**.
4. Connect your repository and select the `agri_ai_rover` folder.
5. Set the following build settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Under **Environment Variables**, add:
   - `GEMINI_API_KEY` = `your_actual_gemini_api_key`
   - `FLASK_ENV` = `production`
7. Click **Create Web Service**.
8. Once deployed, copy your public Render URL (e.g., `https://agri-ai-rover-backend.onrender.com`).

---

### Step 2: Deploy Frontend to Netlify

1. Log in to [Netlify](https://app.netlify.com/).
2. Click **Add new site** -> **Deploy manually**.
3. Drag and drop the `agri_ai_rover.html` file (or select the project root folder).
4. Netlify will deploy your single-file frontend immediately and give you a site URL (e.g., `https://your-agri-rover.netlify.app`).

---

### Step 3: Connect Frontend to Render Backend

1. Open your Netlify site URL (`https://your-agri-rover.netlify.app`) in any web browser.
2. Click **⚙️ Settings / Diagnostics** in the top navigation bar.
3. In **Backend API URL**, enter your deployed Render backend URL:
   `https://agri-ai-rover-backend.onrender.com`
4. Click **Save Settings** & **🧪 Test Connection**.
5. You will see `✅ Gemini Vision API is connected and responding normally!`.
6. Your production deployment is now live and fully operational!

> **Note**: You can also pre-set your backend URL in JavaScript by defining `window.AGRI_AI_ROVER_API_BASE = 'https://agri-ai-rover-backend.onrender.com';` inside `<script>` before deploying to Netlify.

---

## 📡 Hardware / ESP32 Telemetry API

The AGRI AI ROVER backend accepts sensor telemetry directly from ESP32 microcontrollers over HTTP:

### Submit Telemetry (`POST /api/telemetry`)
**Request Body:**
```json
{
  "soil_moisture": 39.5,
  "temperature": 25.4,
  "humidity": 68.0,
  "ph": 7.0
}
```

**cURL Example:**
```bash
curl -X POST https://agri-ai-rover-backend.onrender.com/api/telemetry \
     -H "Content-Type: application/json" \
     -d '{"soil_moisture": 39.5, "temperature": 25.4, "humidity": 68.0, "ph": 7.0}'
```

### Retrieve Telemetry (`GET /api/telemetry`)
```bash
curl https://agri-ai-rover-backend.onrender.com/api/telemetry
```

---

## 🧪 Testing Guidelines

1. **Healthy Crop Sample**: Upload a clear photo of a fresh tomato or healthy paddy leaf. Expect high confidence identification and "Healthy / Good" condition status.
2. **Diseased/Spoiled Crop**: Upload a photo of a rotten fruit or leaf with fungal spots. Expect accurate crop identification with "Poor" or "Damaged" condition and visible issue detection.
3. **Non-Agricultural Image**: Upload an image of a car, shoes, or gadget. System will return `"Not a crop/seed or unable to identify"` with 0% confidence.

---

## 📄 License & Hackathon Info
Developed for **Smart India Hackathon (SIH)** — AGRI AI ROVER Team.
