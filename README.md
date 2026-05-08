# ⚡ WattWatch — Intelligent Energy Waste Detection System

> **Camera-based AI system that detects occupancy and monitors appliance states (lights, fans, monitors) to prevent energy waste in real-time.**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" />
  <img src="https://img.shields.io/badge/YOLOv8-Ultralytics-red?logo=yolo" />
  <img src="https://img.shields.io/badge/Roboflow-Inference%20API-purple?logo=roboflow" />
  <img src="https://img.shields.io/badge/React-Vite%20Dashboard-61DAFB?logo=react" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite" />
</p>

---

## 📖 Table of Contents

1. [What is WattWatch?](#-what-is-wattwatch)
2. [How It Works — System Overview](#-how-it-works--system-overview)
3. [AI Models Used](#-ai-models-used)
4. [Project Structure](#-project-structure)
5. [Key Features](#-key-features)
6. [Installation & Setup](#-installation--setup)
7. [Configuration](#-configuration)
8. [Running the System](#-running-the-system)
9. [Dashboard (Frontend)](#-dashboard-frontend)
10. [API Endpoints](#-api-endpoints)
11. [Energy Metrics Explained](#-energy-metrics-explained)
12. [Privacy & Anonymization](#-privacy--anonymization)
13. [Alert System](#-alert-system)
14. [Roboflow Model Training Guide](#-roboflow-model-training-guide)

---

## 🔍 What is WattWatch?

WattWatch is an AI-powered energy monitoring system for smart buildings, offices, and classrooms. It uses a combination of:

- **Computer Vision** (YOLOv8) to detect if people are present in a room
- **Custom Roboflow ML Models** to detect the ON/OFF state of lights, ceiling fans, and monitors
- **A real-time React dashboard** to visualize room-level energy waste and send alerts

The core idea is simple: **if no one is in the room but appliances are still ON → that's energy waste.** WattWatch automates this detection, calculates the cost in real-time, and alerts facility managers via WhatsApp/SMS.

---

## 🧠 How It Works — System Overview

```
                          ┌──────────────────────┐
  IP Camera / Webcam ──▶  │   FastAPI Backend     │
                          │   (api/main.py)       │
                          └────────┬─────────────┘
                                   │ Each Frame
                    ┌──────────────┼──────────────────┐
                    ▼              ▼                   ▼
           ┌──────────────┐ ┌───────────────┐ ┌─────────────────┐
           │  YOLOv8n.pt  │ │ Roboflow API  │ │  Privacy Filter │
           │ (Person Det.)│ │ (3 ML Models) │ │  (Face Blur)    │
           └──────┬───────┘ └───────┬───────┘ └────────┬────────┘
                  │                 │                   │
                  ▼                 ▼                   │
           Person Count    Light/Fan/Monitor            │
                           ON or OFF status             │
                    │                 │                 │
                    └─────────────────▼─────────────────┘
                                      │
                          ┌───────────▼──────────────┐
                          │   Room State Engine      │
                          │   AlertManager           │
                          │   MicrozoneTracker       │
                          └───────────┬──────────────┘
                                      │
                     ┌────────────────▼────────────────┐
                     │  WebSocket Stream to Dashboard  │
                     │  React (Vite) Frontend          │
                     └─────────────────────────────────┘
```

### Frame Processing Pipeline (per room per frame)

1. **Frame Capture** — from IP camera stream or webcam
2. **Person Detection** — YOLOv8 detects humans → count of people
3. **Appliance Detection** — Roboflow API checks if Light/Fan/Monitor is ON or OFF (every N frames to reduce cost)
4. **Privacy Anonymization** — Faces are auto-blurred using Haar cascade + pixelation before storage
5. **Microzone Tracking** — Frame split into 4×4 grid, per-zone occupancy tracked for heatmaps
6. **Waste Detection** — `person_count == 0` AND any appliance is `ON` → "WASTE" state
7. **AlertManager** — debounced alerts sent via Twilio SMS / WhatsApp after configurable delay
8. **WebSocket Push** — annotated frame + all metadata streamed to dashboard in real-time

---

## 🤖 AI Models Used

WattWatch uses **4 models in total**. Here is a complete breakdown:

---

### Model 1: YOLOv8n — Human / Person Detection (Primary Model in Use)

| Property               | Value                                                                   |
| ---------------------- | ----------------------------------------------------------------------- |
| **Framework**          | [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)        |
| **Model File**         | `yolov8n.pt` (also `yolov8s.pt` available)                              |
| **Task**               | Object Detection — Person class only (`class_id = 0` from COCO dataset) |
| **Config Key**         | `config.yaml → model.name`                                              |
| **Default Confidence** | `0.25`                                                                  |
| **Where it runs**      | Locally on your CPU/GPU                                                 |
| **Purpose**            | Counts how many people are in the room                                  |

> **`yolov8n.pt`** is the **currently active** model (nano variant — fastest).
> `yolov8s.pt` (small variant) is also present for higher accuracy at a cost of speed.

**How to switch:** Edit `config.yaml`:

```yaml
model:
  name: yolov8s.pt # switch to small model for better accuracy
```

**Code location:** `src/detector.py` → `YOLODetector` class

---

### Model 2 (Roboflow): Light ON/OFF Detector

| Property          | Value                                                               |
| ----------------- | ------------------------------------------------------------------- |
| **Platform**      | [Roboflow](https://roboflow.com) — Hosted Serverless Inference      |
| **Model ID**      | `coms-room-light-63vyv/1`                                           |
| **Task**          | Classification / Detection — Is the light ON or OFF?                |
| **Training Data** | Custom-labeled room images with lights on/off (trained on Roboflow) |
| **API Endpoint**  | `https://serverless.roboflow.com`                                   |
| **Config Key**    | `config.yaml → appliance.roboflow.light_model`                      |
| **Purpose**       | Detects if the ceiling/room light is switched ON or OFF             |

**Response parsing logic (from `src/appliance_status.py`):**

- If predicted class contains `"on"`, `"light"`, `"glow"`, `"lamp"`, `"bright"`, or `"tube"` → **Status: ON**
- If class contains `"off"` → **Status: OFF**

---

### Model 3 (Roboflow): Ceiling Fan ON/OFF Detector

| Property          | Value                                                          |
| ----------------- | -------------------------------------------------------------- |
| **Platform**      | [Roboflow](https://roboflow.com) — Hosted Serverless Inference |
| **Model ID**      | `ceiling-fan-detection-epfsk/1`                                |
| **Task**          | Detection — Is the ceiling fan spinning (ON) or stopped (OFF)? |
| **Training Data** | Custom-labeled ceiling fan images (trained on Roboflow)        |
| **API Endpoint**  | `https://serverless.roboflow.com`                              |
| **Config Key**    | `config.yaml → appliance.roboflow.fan_model`                   |
| **Purpose**       | Detects the rotational state of ceiling fans                   |

**Response parsing logic:**

- If class contains `"on"`, `"fan"`, `"spinning"`, `"ceiling"`, or `"rotor"` → **Status: ON**
- If class contains `"off"` → **Status: OFF**

---

### Model 4 (Roboflow): Monitor / Display ON/OFF Detector

| Property          | Value                                                          |
| ----------------- | -------------------------------------------------------------- |
| **Platform**      | [Roboflow](https://roboflow.com) — Hosted Serverless Inference |
| **Model ID**      | `monitor_detection-uj19t-zqnlq/1`                              |
| **Task**          | Detection — Is the monitor/screen turned ON or OFF?            |
| **Training Data** | Custom-labeled monitor images (trained on Roboflow)            |
| **API Endpoint**  | `https://serverless.roboflow.com`                              |
| **Config Key**    | `config.yaml → appliance.roboflow.monitor_model`               |
| **Purpose**       | Detects if desktop monitors are left powered on in empty rooms |

**Response parsing logic:**

- If class contains `"on"`, `"active"`, `"display"`, `"monitor"`, `"screen"`, or `"power"` → **Status: ON**
- Otherwise → **Status: OFF**

---

### Which Model is Active Right Now?

| Model                               | Active?    | Notes                                                                         |
| ----------------------------------- | ---------- | ----------------------------------------------------------------------------- |
| `yolov8n.pt`                        | ✅ **YES** | Configured in `config.yaml`, runs locally                                     |
| `yolov8s.pt`                        | ❌ No      | Available on disk but not selected                                            |
| Roboflow Light                      | ✅ **YES** | Called every `frame_skip=20` frames                                           |
| Roboflow Fan                        | ✅ **YES** | Called every `frame_skip=20` frames                                           |
| Roboflow Monitor                    | ✅ **YES** | Called every `frame_skip=20` frames                                           |
| `MLApplianceDetector` (MobileNetV2) | ❌ No      | Fallback only, requires `models/appliance_classifier.pt` which is not present |

> **Summary:** The system currently uses **YOLOv8n** for person detection and the **3 Roboflow hosted models** for appliance status. All 3 Roboflow calls are made in parallel (via `ThreadPoolExecutor`) to minimize latency.

---

## 📁 Project Structure

```
watt-watch/
│
├── main.py                    # CLI entry point (detect/live/benchmark/calibrate)
├── config.yaml                # Master configuration file
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── yolov8n.pt                 # YOLOv8 Nano model (person detection) ← ACTIVE
├── yolov8s.pt                 # YOLOv8 Small model (alternative, not active)
│
├── src/                       # Core Python source code
│   ├── __init__.py
│   ├── detector.py            # YOLOv8 person detection wrapper
│   ├── tracker.py             # Centroid-based multi-person tracker
│   ├── appliance_status.py    # Roboflow API calls (Light/Fan/Monitor)
│   ├── appliance_detector.py  # Rule-based fallback detector (brightness/edge analysis)
│   ├── ml_appliance_detector.py # MobileNetV2 local ML detector (optional fallback)
│   ├── alert_manager.py       # Waste event tracking + Twilio SMS/WhatsApp alerts
│   ├── microzone.py           # 4×4 grid zone tracking + heatmap generation
│   ├── privacy_filter.py      # Face detection (Haar cascade) + anonymization
│   ├── intensity_calibrator.py # Room brightness threshold calibration
│   ├── smoothing.py           # Temporal smoothing for detection signals
│   ├── preprocessing.py       # Frame preprocessing utilities
│   ├── model_utils.py         # Model download and path utilities
│   ├── mqtt_manager.py        # MQTT publish/subscribe for IoT integration
│   ├── utils.py               # FPS counter, video extractor, JSON logger
│   └── database/              # SQLite database layer
│
├── api/
│   └── main.py                # FastAPI backend (~75KB) — WebSocket, REST API
│
├── dashboard-vite/            # React + Vite frontend dashboard
│   ├── src/
│   │   ├── App.jsx            # Main dashboard component (~920 lines)
│   │   ├── App.css            # Dashboard styling
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── scripts/
│   ├── download_samples.py    # Download sample test videos
│   ├── extract_frames.py      # Extract frames from videos
│   └── migrate_json_to_sqlite.py
│
├── configs/                   # Additional configuration files
├── data/                      # Test clips and raw data
│   └── clips/                 # occupied.mp4, empty.mp4, quiet-reader.mp4
├── output/                    # Detection results, JSON logs
├── logs/                      # FPS logs, appliance debug logs
├── models/                    # Optional local ML model files
├── docs/                      # Documentation
├── tests/                     # Unit tests
│
├── ENERGY_METRICS.md          # Detailed energy calculation documentation
├── test_detection.py          # Manual detection tests
└── test_appliance.py          # Manual appliance detection tests
```

---

## ✨ Key Features

| Feature                    | Description                                                       |
| -------------------------- | ----------------------------------------------------------------- |
| 🧍 **Person Detection**    | YOLOv8n detects and counts people in real-time                    |
| 💡 **Light Detection**     | Roboflow model classifies room lights as ON/OFF                   |
| 🌀 **Fan Detection**       | Roboflow model detects spinning/stopped ceiling fans              |
| 🖥️ **Monitor Detection**   | Roboflow model detects powered-on/off monitors                    |
| ⚡ **Energy Waste Alerts** | SMS/WhatsApp alerts when room is empty but appliances are ON      |
| 🔒 **Privacy First**       | Automatic face anonymization (pixelation/blur) before any storage |
| 🗺️ **Microzone Heatmap**   | 4×4 grid zone tracking shows where people congregate              |
| 📊 **Cost Calculation**    | Real-time cost/hour and cumulative waste cost in ₹ or $           |
| 🎛️ **Calibration Studio**  | Per-room brightness threshold tuning via visual dashboard         |
| 📡 **Multi-Room Support**  | Monitor up to 2 IP camera rooms simultaneously                    |
| 🗄️ **SQLite Logging**      | All waste events persisted in SQLite database                     |
| 🌐 **WebSocket Streaming** | Live annotated frames pushed to dashboard                         |

---

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.9 or higher
- Node.js 18+ (for dashboard)
- A Roboflow account with API key
- (Optional) CUDA GPU for faster YOLO inference

### Step 1 — Clone & Install Python Dependencies

```bash
git clone <your-repo-url>
cd watt-watch

pip install -r requirements.txt
```

The key packages installed:

```
ultralytics>=8.0.0       # YOLOv8 (person detection)
opencv-python>=4.8.0     # Video processing
torch>=2.0.0             # Deep learning backend
inference-sdk>=1.0.0     # Roboflow API client
fastapi>=0.104.0         # Backend API server
uvicorn>=0.24.0          # ASGI server
websockets>=12.0         # Real-time streaming
pyyaml>=6.0              # Config file parsing
```

### Step 2 — Configure API Keys

Open `config.yaml` and set your Roboflow API key:

```yaml
appliance:
  roboflow:
    api_key: YOUR_ROBOFLOW_API_KEY_HERE
    light_model: coms-room-light-63vyv/1
    fan_model: ceiling-fan-detection-epfsk/1
    monitor_model: monitor_detection-uj19t-zqnlq/1
```

### Step 3 — (Optional) Configure Twilio for Alerts

```yaml
alerts:
  twilio:
    enabled: true
    account_sid: YOUR_TWILIO_ACCOUNT_SID
    auth_token: YOUR_TWILIO_AUTH_TOKEN
    from_number: "+1xxxxxxxxxx"
    to_number: "+91xxxxxxxxxx"
```

### Step 4 — Install Dashboard Dependencies

```bash
cd dashboard-vite
npm install
```

---

## ⚙️ Configuration

All system behavior is controlled by `config.yaml`. Key sections:

```yaml
# ── Model selection ──────────────────────────────────
model:
  name: yolov8n.pt # Switch to yolov8s.pt for higher accuracy
  confidence_threshold: 0.25

# ── Detection settings ───────────────────────────────
detection:
  frame_skip: 1 # Process every frame (increase for speed)
  min_confidence: 0.25

# ── Appliance wattage for cost calculation ───────────
appliance:
  enabled: true
  frame_skip: 20 # Run Roboflow every 20 frames
  wattage:
    light: 40 # Watts per light bulb
    ceiling_fan: 65 # Watts per ceiling fan
    monitor: 35 # Watts per monitor
  electricity_rate: 0.12 # USD per kWh
  electricity_rate_inr: 6.5 # INR per kWh

# ── Alert debouncing ─────────────────────────────────
alerts:
  initial_delay_seconds: 60 # Wait 60s before first alert
  repeat_interval_seconds: 600 # Repeat alert every 10 min

# ── Privacy settings ─────────────────────────────────
privacy:
  enabled: true
  blur_method: pixelate # Options: pixelate, gaussian, solid
  blur_level: 99

# ── Microzone grid ───────────────────────────────────
microzone:
  enabled: true
  rows: 4
  cols: 4
  decay: 0.98 # Heatmap decay factor
```

---

## 🚀 Running the System

### Option A — CLI Commands (for testing/video processing)

**Process a video file:**

```bash
python main.py detect data/test_clip.mp4
```

**Run live webcam detection:**

```bash
python main.py live
```

**Run live on a specific camera:**

```bash
python main.py live --camera 0
```

**Run benchmark on test clips:**

```bash
python main.py benchmark
```

**Run intensity calibration on a room:**

```bash
python main.py calibrate data/test_clip.mp4 --room classroom_1 --samples 30
```

**Check calibration status:**

```bash
python main.py calibrate --status
```

**Process image (single frame):**

```bash
python main.py detect test_img.jpg --output result.jpg
```

### Option B — Full System (Backend API + Dashboard)

**Step 1: Start the FastAPI Backend**

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at: `http://localhost:8000`
API docs available at: `http://localhost:8000/docs`

**Step 2: Start the React Dashboard**

```bash
cd dashboard-vite
npm run dev
```

Dashboard runs at: `http://localhost:5173`

**Step 3: Connect a camera**
In the dashboard, enter your IP camera stream URL (e.g., `http://192.168.0.154:8080/video`) and click **CONNECT**.

---

## 📊 Dashboard (Frontend)

The dashboard (built with React + Vite) has 5 tabs:

### 1. MONITOR Tab

- **Live video feed** from up to 2 IP cameras
- **Person count**, Light/Fan/Monitor status displayed per room
- **WASTE_DETECTED** alert banner when room is empty with appliances ON
- **Privacy mode toggle** (GHOST_MODE) — enables/disables face blur
- Real-time energy load and cumulative waste cost

### 2. SUMMARY Tab

- **Annual energy projections** — kWh/day, savings in INR/year, CO₂/year
- **Last 30 days** savings report
- Per-room breakdown with cost and CO₂ metrics

### 3. PRIVACY Tab

- Privacy measures status (face anonymization, data retention)
- Stakeholder compliance commitments
- Data retention policy overview

### 4. CALIBRATE Tab (Luminance Studio)

- **Visual real-time brightness meter** for selected room
- **Dark / Medium threshold sliders** for day and night modes
- Drag sliders to tune thresholds and commit changes to `config.yaml`
- Shows classification: DARK / MEDIUM / BRIGHT based on live feed

### 5. DATABASE Tab

- Browse the SQLite database schema
- View raw table data (waste events, detection logs)
- Export and inspect historical energy waste records

---

## 🔌 API Endpoints

| Method | Endpoint                     | Description                             |
| ------ | ---------------------------- | --------------------------------------- |
| `POST` | `/api/camera/connect`        | Connect a room camera (start streaming) |
| `POST` | `/api/camera/disconnect`     | Disconnect a room camera                |
| `WS`   | `/ws/stream/{room_id}`       | WebSocket for live frame streaming      |
| `GET`  | `/api/energy/metrics`        | Current energy metrics per room         |
| `GET`  | `/api/energy/dashboard`      | Annual projections and 30-day summary   |
| `GET`  | `/api/alerts/events`         | Recent waste alert events               |
| `GET`  | `/api/alerts/status`         | Room status + waste duration            |
| `GET`  | `/api/calibration`           | Get current threshold calibration       |
| `POST` | `/api/calibration`           | Update brightness thresholds            |
| `GET`  | `/api/privacy/assurance`     | Privacy compliance report               |
| `GET`  | `/api/database/info`         | Database statistics                     |
| `GET`  | `/api/database/schema`       | Database table schema                   |
| `GET`  | `/api/database/rows/{table}` | Browse table rows                       |

---

## 💰 Energy Metrics Explained

### How cost is calculated:

```
estimated_watts = (40W if Light is ON) + (65W if Fan is ON) + (35W if Monitor is ON)

cost_per_hour  = (estimated_watts / 1000) × electricity_rate     # in USD
cost_per_hour_inr = (estimated_watts / 1000) × 6.5              # in INR

cumulative_cost = cost_per_hour × (waste_duration_seconds / 3600)
```

### Waste State Definition:

```python
is_waste = (person_count == 0) AND (light == "ON" OR fan == "ON" OR monitor == "ON")
```

### Annual Projections:

```
kwh_per_day = estimated_watts × 24 / 1000
inr_per_year = kwh_per_day × 365 × electricity_rate_inr
co2_per_year_kg = kwh_per_day × 365 × co2_factor (0.71 kg/kWh)
```

See [ENERGY_METRICS.md](ENERGY_METRICS.md) for the complete calculation documentation.

---

## 🔒 Privacy & Anonymization

WattWatch is designed to be **privacy-first** in compliance with institutional requirements:

- **Haar Cascade** face detection runs on every N frames
- Detected faces are **pixelated** (or gaussian-blurred) with a large padding to obscure the entire head region
- **Raw images are NEVER stored** by default (`privacy.storage.save_raw: false`)
- Only **anonymized thumbnails** are saved (for alert evidence)
- All processing happens **locally** — no raw video leaves the machine

### Privacy configuration:

```yaml
privacy:
  blur_method: pixelate # pixelate / gaussian / solid
  pixelate_blocks: 12 # More blocks = finer pixelation
  blur_level: 99 # For gaussian mode
  skip_frames: 3 # Re-detect faces every 3 frames
  storage:
    save_raw: false # NEVER store raw video
    save_anonymized: false # Only enable for auditing
```

---

## 🚨 Alert System

The `AlertManager` watches each room for waste conditions:

1. **Waste detected** → starts a timer
2. After `initial_delay_seconds` (default: 60s) → fires first alert
3. If waste continues, repeats every `repeat_interval_seconds` (default: 600s = 10 min)
4. When room is occupied or appliances are OFF → resets the timer

### Alert channels:

- **Twilio SMS** — text message to facility manager
- **Twilio WhatsApp** — WhatsApp template message with room name and duration
- **SQLite Database** — event persisted to `data/wattwatch.db`
- **JSON fallback** — events saved to `output/waste_events.json`

Alert message format:

```
⚠️ WATTWATCH ALERT
Energy waste detected in Room 101!
Duration: 5.2 mins
Lights: ON, Fans: ON, Mon: OFF
Please check the facility.
```

---

## 🏋️ Roboflow Model Training Guide

The 3 Roboflow models (light, fan, monitor) were trained using Roboflow's platform. Here's how they were set up:

### Steps to train your own models:

1. **Create a Roboflow account** at [app.roboflow.com](https://app.roboflow.com)

2. **Create a new project** → select `Object Detection` or `Classification`

3. **Upload images:**
   - For **light model**: collect images of your room with light ON and light OFF
   - For **fan model**: collect images of ceiling fans spinning (ON) and still (OFF)
   - For **monitor model**: collect images of monitors powered ON and OFF

4. **Annotate** → draw bounding boxes and assign class labels:
   - Light model classes: `light-on`, `light-off` (or similar)
   - Fan model classes: `fan-on`, `fan-off`
   - Monitor model classes: `monitor-on`, `monitor-off`

5. **Train** → Use Roboflow's auto-train feature (YOLOv8 recommended)

6. **Get model ID** → from the Roboflow dashboard, copy the `workspace/project/version` format

7. **Update `config.yaml`:**

```yaml
appliance:
  roboflow:
    api_key: YOUR_API_KEY
    light_model: YOUR-WORKSPACE/YOUR-LIGHT-PROJECT/1
    fan_model: YOUR-WORKSPACE/YOUR-FAN-PROJECT/1
    monitor_model: YOUR-WORKSPACE/YOUR-MONITOR-PROJECT/1
```

### Current models in use:

| Appliance   | Roboflow Model ID                 |
| ----------- | --------------------------------- |
| Light       | `coms-room-light-63vyv/1`         |
| Ceiling Fan | `ceiling-fan-detection-epfsk/1`   |
| Monitor     | `monitor_detection-uj19t-zqnlq/1` |

> **Tip:** The more diverse your training images (different rooms, lighting conditions, angles), the more accurate your model will be.

---

## 🧪 Testing

**Test person detection on a single image:**

```bash
python test_detection.py
```

**Test appliance detection (light/fan) on a test image:**

```bash
python test_appliance.py
```

**Run detection with max frames limit:**

```bash
python main.py detect data/clips/occupied.mp4 --max-frames 100
```

---

## 📝 Logging & Output

| File                            | Contents                                  |
| ------------------------------- | ----------------------------------------- |
| `output/detections.json`        | Per-frame detection results (JSON)        |
| `output/waste_events.json`      | Waste alert event log (JSON)              |
| `output/appliance_status.json`  | Appliance ON/OFF history per frame        |
| `output/benchmark_results.json` | Benchmark test results                    |
| `logs/fps.log`                  | Frame-by-frame FPS log                    |
| `logs/appliance_debug.log`      | Raw Roboflow API response debug log       |
| `data/wattwatch.db`             | SQLite database (all events + detections) |
| `data/alerts/*.jpg`             | Anonymized thumbnails for waste events    |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgements

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — person detection backbone
- [Roboflow](https://roboflow.com) — model training platform and inference API
- [Twilio](https://twilio.com) — SMS and WhatsApp alerting
- [FastAPI](https://fastapi.tiangolo.com) — high-performance Python backend
- [React + Vite](https://vitejs.dev) — fast frontend tooling
