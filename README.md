# UST Reception AI Insight Dashboard

A computer-vision powered digital signage dashboard designed for the UST Cyberjaya campus reception. 
It uses a live webcam feed and AI to anonymously track footfall, analyze visitor sentiment, and display real-time curated insights.

![Dashboard Preview](docs/dashboard-preview.png) *(Note: Add a screenshot to a `docs/` folder before pushing to GitHub)*

## Features

The dashboard consists of four real-time panels:

1. **Happiness Index (Top Left)**: Uses OpenCV and an ONNX FERPlus model to analyze the webcam feed stream in real-time, detecting faces and classifying aggregate group sentiment (Positive, Neutral, Negative).
2. **Cyberjaya Weather (Top Right)**: Fetches live temperature and 24-hour forecasts for Cyberjaya using the Open-Meteo API. Features dynamic gradients and a 24-hour temperature trend sparkline.
3. **UST News Feed (Bottom Left)**: Auto-scrolling carousel of internal UST announcements with priority badges and an infinitely scrolling news ticker.
4. **Visitor Intelligence (Bottom Right)**: Samples face counts from the AI pipeline to derive real-time footfall. Features current occupancy levels, an hourly peak traffic bar chart, and a 60-minute per-minute average sparkline trend.

## Architecture

The project is split into a Python backend and a Node.js frontend, loosely coupled via REST APIs and MJPEG streaming.

* **Backend (`/backend`)**: Python 3.9+, FastAPI, OpenCV, ONNXRuntime. 
  * Runs background daemon threads for inference (to avoid blocking HTTP requests).
  * Exposes `/api/emotion/feed` for the live video stream.
  * Exposes JSON endpoints for weather, news, and footfall metrics.
* **Frontend (`/frontend`)**: Next.js 14, React 18, standard CSS (no Tailwind).
  * Dark-mode, glassmorphism UI designed for a 1080p display.
  * Polls backend APIs continuously to keep UI elements matching the AI state.

## Hardware Requirements

* Windows PC, Mac, or Linux environment (e.g., Raspberry Pi 5).
* A standard USB Webcam or integrated laptop camera.
* Internet connection (for Weather API).

## Prerequisites (Install Once)

To run this repository on a completely new, blank computer, you only need exactly three things installed beforehand:

1. **Git**: To clone the repository from GitHub.
2. **Python (3.9 to 3.12)**: Required to run the backend AI and the web server. When installing Python on Windows, you must ensure the box **"Add python.exe to PATH"** is checked.
3. **Node.js (v18 or v20+)**: Required to run the Next.js frontend application.

## Installation & Running (Zero-Config)

Once those three programs are installed, running the application requires exactly zero manual dependency configuration on your end. The provided launcher scripts are designed to automatically download all heavy Python libraries (like OpenCV and ONNX models) and Node modules on the first run.

### 1. Clone the repository
```bash
git clone https://github.com/sSaintV/UST-Dashboard-AI.git
cd UST-Dashboard-AI
```

### 2. Configure Environment (Optional)
If your camera is not at `index 0`, create a `.env` file in the `backend/` folder:
```env
CAMERA_INDEX=1    # Change this if your webcam isn't detected (0, 1, 2...)
DEMO_MODE=false   # Set to true to inject simulated AI faces without a real camera
```

### 3. Launch the Application

**On Windows:**
Double-click `start.bat` or run it from command prompt:
```cmd
.\start.bat
```
This script ensures paths are set, `pip` and `npm` installs are run, and launches both servers in background command windows.

**On Mac / Linux / Raspberry Pi:**
```bash
chmod +x start.sh
./start.sh
```

### 4. Access the Dashboard
Once the servers boot (which may take a moment on the very first run to download the ONNX emotion model):
- **Dashboard UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Development

If you wish to run the components separately for development:

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Privacy Notice
This system does **not** record, save, or transmit video feeds over the internet. The AI processing happens entirely on the edge device in memory, and only anonymous metadata (e.g., "5 faces, 80% neutral") is accessible via the local `/api/emotion` endpoint.
