# Project Issues Log: UST Reception AI Insight Dashboard

This document tracks technical hurdles, bugs, and configuration issues encountered during the development and maintenance of the UST Reception AI Insight Dashboard.

## 2026-03-16

### 1. Backend Service Initialization Race Condition
- **Issue**: Environment variables from `.env` (like `CAMERA_INDEX`) were being ignored because `load_dotenv()` was called after the `EmotionService` was already imported and instantiated.
- **Resolution**: Moved `load_dotenv()` to the top of `backend/main.py`, before any service imports.

### 2. Camera Access Failure (Logitech MX Brio)
- **Issue**: The dashboard failed to detect the Logitech MX Brio camera on the NVIDIA Jetson/Orin Nano system.
- **Diagnosis**: `v4l2-ctl` identified the device as `/dev/video1`, but the application was defaulting to `CAMERA_INDEX=0` (built-in/internal device).
- **Resolution**: Updated `CAMERA_INDEX=1` in the `.env` file.

### 3. Backend `NameError` in `EmotionService`
- **Issue**: The background thread `emotion-svc` crashed with `NameError: name 'face_det' is not defined` when the camera was unavailable.
- **Cause**: Leftover reference to an old detector object in the camera failure cleanup path.
- **Resolution**: Removed the `face_det.close()` call and added proper `cap.release()` handling.

### 4. Frontend `TypeError: can't access property "toFixed"`
- **Issue**: The JS console reported a crash in `HappinessPanel.tsx` because `data.positive`, `data.neutral`, etc., were undefined.
- **Cause**: The backend's Pydantic response models (`EmotionResponse` and `HistoryPoint`) were missing the fields required by the frontend after a recent sentiment classification update.
- **Resolution**: Added the missing numeric fields and timestamps to the backend router schemas.

### 5. Emotion Classification Refactoring
- **Context**: Requirement to group the 8 FERPlus emotions into Positive, Neutral, and Negative categories.
- **Change**: Updated `EmotionService` to preserve individual scores while aggregating them for the main dashboard display.

---

## 2025-11-26

### 1. Camera Feed Optimization (Streamlit)
- **Issue**: Latency in the real-time USB camera feed on the Streamlit dashboard.
- **Resolution**: Optimized the detection pipeline speed to maintain a stable display without downgrading the model.

---

## 2025-11-25

### 1. API Data Integration & Fallback
- **Issue**: Requirement for real-time commodity price data integration with a fallback mechanism.
- **Resolution**: Implemented an API client that uses mock data when API keys are missing, ensuring system stability.

### 2. Codebase Redundancy
- **Task**: Identification of non-essential files to streamline the Jetson deployment.
- **Result**: Cleaned up the project structure based on prioritized file lists.
