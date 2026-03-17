"""
Emotion detection service — runs in a background daemon thread.

Pipeline:
  1. cv2.VideoCapture reads frames at up to 30 FPS.
  2. MediaPipe FaceDetection locates face bounding boxes (~1-3 ms/frame,
     ARM-optimised for Raspberry Pi 5).
  3. Each face is cropped, converted to 64×64 greyscale float32.
  4. onnxruntime runs the FERPlus INT8-quantised ONNX model (~78 KB)
     to get 8-class emotion probabilities.
  5. Classes are mapped to Positive / Neutral / Negative and accumulated
     in a 60-second rolling deque.
  6. A thread-safe snapshot is read by the FastAPI endpoint every poll.

PRIVACY:  No frames, crops, or face images are ever written to disk.
          Only aggregated numeric probabilities leave this module.
"""

import cv2
import numpy as np
import onnxruntime as ort
import threading
import time
import os
import logging
import urllib.request
from collections import deque

logger = logging.getLogger(__name__)

# ── FERPlus 8-class emotion labels (model output order) ──────────────────────
EMOTION_LABELS = [
    "neutral", "happiness", "surprise", "sadness",
    "anger", "disgust", "fear", "contempt",
]
POSITIVE_SET = {"happiness", "surprise"}
NEGATIVE_SET = {"fear", "disgust", "anger", "sadness", "contempt"}
# "neutral" → neutral bucket

# ── ONNX model location ───────────────────────────────────────────────────────
_BASE_DIR   = os.path.dirname(__file__)
MODEL_DIR   = os.path.join(_BASE_DIR, "..", "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "emotion-ferplus-8.onnx")
# Stable permalink from the ONNX Model Zoo (validated folder, v8)
MODEL_URL   = (
    "https://github.com/onnx/models/raw/main/validated/"
    "vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
)

# ── Tuning constants ──────────────────────────────────────────────────────────
WINDOW_SECONDS      = 30    # shortened to 30s for better responsiveness
MAX_INFERENCE_FPS   = 20    # cap to leave OS/other-panel headroom
INTRA_OP_THREADS    = 4     # ONNX CPU threads (Pi 5 has 4 cores)
HISTORY_MAXLEN      = 30    # sparkline data-points sent to frontend


class EmotionService:
    """Singleton service managing the camera + inference background thread."""

    def __init__(self):
        self._lock   = threading.Lock()
        self._state  = self._default_state(available=False)
        self._thread = None
        self._camera_index = int(os.getenv("CAMERA_INDEX", "0"))
        self._demo_mode    = os.getenv("DEMO_MODE", "false").lower() == "true"
        self._frame_cond   = threading.Condition()
        self._latest_jpeg  = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the background daemon thread (idempotent)."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="emotion-svc")
        self._thread.start()
        logger.info("EmotionService started (demo_mode=%s)", self._demo_mode)

    def get_state(self) -> dict:
        """Thread-safe snapshot of the current emotion state."""
        with self._lock:
            return dict(self._state)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _default_state(available: bool) -> dict:
        return {
            "available":  available,
            "demo":       False,
            "positive":   0.0,
            "neutral":    100.0,
            "negative":   0.0,
            "face_count": 0,
            "fps":        0.0,
            "dominant":   "neutral",
            "history":    [],
            "emotions":   {label: 0.0 for label in EMOTION_LABELS},
        }

    def _set_state(self, **kwargs) -> None:
        with self._lock:
            self._state.update(kwargs)

    def _download_model(self) -> bool:
        """Download the FERPlus ONNX model once and cache it locally."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        if os.path.exists(MODEL_PATH):
            logger.info("ONNX model cached at: %s", MODEL_PATH)
            return True
        logger.info("Downloading FERPlus ONNX model from ONNX Model Zoo…")
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            logger.info("Model saved to: %s", MODEL_PATH)
            return True
        except Exception as exc:
            logger.error("Model download failed: %s", exc)
            return False

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax."""
        e = np.exp(x - x.max())
        return e / e.sum()

    @staticmethod
    def _sentiment_from_probs(probs: np.ndarray) -> tuple[dict, str, dict]:
        """Map 8-class softmax probabilities to pos/neu/neg buckets and return all scores."""
        sent = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
        raw_emotions = {}
        for i, label in enumerate(EMOTION_LABELS):
            score = float(probs[i])
            raw_emotions[label] = score
            if label in POSITIVE_SET:
                sent["positive"] += score
            elif label in NEGATIVE_SET:
                sent["negative"] += score
            else:
                sent["neutral"] += score
        dominant = EMOTION_LABELS[int(probs.argmax())]
        return sent, dominant, raw_emotions

    @staticmethod
    def _window_averages(window: deque) -> tuple[float, float, float, str, dict]:
        """Compute mean pos/neu/neg% and most-frequent dominant label."""
        if not window:
            return 0.0, 100.0, 0.0, "neutral", {label: 0.0 for label in EMOTION_LABELS}
        pos = float(np.mean([s["positive"] for _, s, _, _ in window])) * 100
        neu = float(np.mean([s["neutral"]  for _, s, _, _ in window])) * 100
        neg = float(np.mean([s["negative"] for _, s, _, _ in window])) * 100
        
        avg_emotions = {}
        for label in EMOTION_LABELS:
            avg_emotions[label] = float(np.mean([r[label] for _, _, _, r in window])) * 100

        dominant = max(
            {d for _, _, d, _ in window},
            key=lambda em: sum(1 for _, _, d2, _ in window if d2 == em),
        )
        return pos, neu, neg, dominant, avg_emotions

    # ── Main run path ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        if self._demo_mode:
            self._run_demo()
            return

        # 1. Download / verify model
        if not self._download_model():
            logger.warning("No ONNX model — switching to demo mode.")
            self._run_demo()
            return

        # 2. Load ONNX session
        try:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = INTRA_OP_THREADS
            session     = ort.InferenceSession(
                MODEL_PATH, sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
            input_name  = session.get_inputs()[0].name
            logger.info("ONNX session ready (input: '%s')", input_name)
        except Exception as exc:
            logger.error("ONNX load error: %s — switching to demo mode.", exc)
            self._run_demo()
            return

        # 3. Init OpenCV Haar Cascade face detectors (Frontal + Profile)
        face_det_f = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        face_det_p = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
        
        if face_det_f.empty() or face_det_p.empty():
            logger.error("Failed to load Haar cascades.")
            self._run_demo()
            return

        # 4. Open camera
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            logger.warning(
                "Camera %d unavailable — switching to demo mode.", self._camera_index
            )
            cap.release()
            self._run_demo()
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        # 5. Inference loop
        window:      deque = deque()           # (ts, sentiment_dict, dominant_str, raw_emotions_dict)
        frame_times: deque = deque(maxlen=30)  # for FPS calculation
        history:     list  = []
        min_interval = 1.0 / MAX_INFERENCE_FPS

        logger.info("Inference loop started.")
        try:
            while True:
                t0 = time.perf_counter()

                ret, frame = cap.read()
                if not ret:
                    logger.warning("Frame read failed; retrying…")
                    time.sleep(0.05)
                    continue

                h, w = frame.shape[:2]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect frontal then profile (profile is harder, so we prioritize frontal)
                faces_f = face_det_f.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
                faces_p = face_det_p.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
                
                # Merge detections (basic overlap check to avoid double-counting)
                faces = list(faces_f)
                for (px, py, pw, ph) in faces_p:
                    is_duplicate = False
                    for (fx, fy, fw, fh) in faces_f:
                        # If center of profile is inside frontal, it's a dupe
                        if fx < px+pw/2 < fx+fw and fy < py+ph/2 < fy+fh:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        faces.append((px, py, pw, ph))

                now    = time.time()
                cutoff = now - WINDOW_SECONDS
                # Prune stale entries from rolling window
                while window and window[0][0] < cutoff:
                    window.popleft()

                for (fx, fy, fw, fh) in faces:
                    x1 = max(0, fx)
                    y1 = max(0, fy)
                    x2 = min(w, fx + fw)
                    y2 = min(h, fy + fh)
                    if x2 <= x1 or y2 <= y1:
                        continue

                    # Crop → greyscale → 64×64 float32 (FERPlus input format)
                    # We already have gray frame, crop from there directly
                    crop  = gray[y1:y2, x1:x2]
                    face  = cv2.resize(crop, (64, 64)).astype(np.float32)
                    inp   = face.reshape(1, 1, 64, 64)   # (batch, channel, H, W)

                    # Run ONNX inference → (1, 8) logits
                    logits = session.run(None, {input_name: inp})[0][0]
                    probs  = self._softmax(logits)
                    sent, dominant, raw = self._sentiment_from_probs(probs)
                    window.append((now, sent, dominant, raw))

                pos, neu, neg, dominant, avg_emotions = self._window_averages(window)

                # Draw bounding boxes for video feed
                vis_frame = frame.copy()
                for (fx, fy, fw, fh) in faces:
                    x1 = max(0, fx)
                    y1 = max(0, fy)
                    x2 = min(w, fx + fw)
                    y2 = min(h, fy + fh)
                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 181, 184), 2)
                        
                # Encode and keep latest frame for MJPEG stream
                _, jpeg = cv2.imencode('.jpg', vis_frame)
                with self._frame_cond:
                    self._latest_jpeg = jpeg.tobytes()
                    self._frame_cond.notify_all()

                # FPS (rolling over last 30 frames)
                frame_times.append(now)
                fps = (
                    (len(frame_times) - 1) / (frame_times[-1] - frame_times[0])
                    if len(frame_times) >= 2 else 0.0
                )

                # Append sparkline snapshot
                snap = {
                    "ts":       now,
                    "positive": round(pos, 1),
                    "neutral":  round(neu, 1),
                    "negative": round(neg, 1),
                    "faces":    len(faces),
                    "emotions": {k: round(v, 1) for k, v in avg_emotions.items()}
                }
                history.append(snap)
                if len(history) > HISTORY_MAXLEN:
                    history = history[-HISTORY_MAXLEN:]

                with self._lock:
                    self._state = {
                        "available":  True,
                        "demo":       False,
                        "positive":   round(pos, 1),
                        "neutral":    round(neu, 1),
                        "negative":   round(neg, 1),
                        "face_count": len(faces),
                        "fps":        round(fps, 1),
                        "dominant":   dominant,
                        "history":    list(history),
                        "emotions":   {k: round(v, 1) for k, v in avg_emotions.items()}
                    }

                # Throttle to MAX_INFERENCE_FPS to spare CPU for other panels
                elapsed = time.perf_counter() - t0
                spare   = min_interval - elapsed
                if spare > 0:
                    time.sleep(spare)

        finally:
            cap.release()
            logger.info("Camera released.")

    # ── Demo / fallback path ──────────────────────────────────────────────────

    def _run_demo(self) -> None:
        """
        Synthetic emotion data for demo / no-camera environments.
        Values perform a smooth random walk with mean reversion so the UI
        looks naturally dynamic without a real camera feed.
        """
        logger.info("EmotionService: DEMO MODE active (synthetic data).")
        rng   = np.random.default_rng(seed=42)
        pos, neu, neg = 65.0, 25.0, 10.0
        face_count    = 3
        history: list = []

        while True:
            # Smooth random walk with soft clamping
            pos = float(np.clip(pos + rng.normal(0, 2.5), 10, 85))
            neg = float(np.clip(neg + rng.normal(0, 1.5),  2, 35))
            neu = max(5.0, 100.0 - pos - neg)
            total = pos + neu + neg
            pos, neu, neg = (pos/total)*100, (neu/total)*100, (neg/total)*100

            face_count = int(np.clip(face_count + rng.integers(-1, 3), 0, 8))

            if pos >= neu and pos >= neg:
                dominant = "happiness"
            elif neg >= pos and neg >= neu:
                dominant = "sadness"
            else:
                dominant = "neutral"

            # Create synthetic visual frame for demo stream
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "DEMO MODE ACTIVE", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (28, 184, 255), 2)
            cv2.putText(frame, f"Faces: {face_count} | Dominant: {dominant}", (120, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            _, jpeg = cv2.imencode('.jpg', frame)
            with self._frame_cond:
                self._latest_jpeg = jpeg.tobytes()
                self._frame_cond.notify_all()

            now  = time.time()
            # Demo emotions: just map to neutral for simplicity or distribute based on pos/neu/neg
            demo_emotions = {label: 0.0 for label in EMOTION_LABELS}
            demo_emotions["happiness"] = pos if pos > 0 else 0.0
            demo_emotions["neutral"]   = neu if neu > 0 else 0.0
            demo_emotions["sadness"]   = neg if neg > 0 else 0.0

            snap = {
                "ts":       now,
                "positive": round(pos, 1),
                "neutral":  round(neu, 1),
                "negative": round(neg, 1),
                "faces":    face_count,
                "emotions": {k: round(v, 1) for k, v in demo_emotions.items()}
            }
            history.append(snap)
            if len(history) > HISTORY_MAXLEN:
                history = history[-HISTORY_MAXLEN:]

            with self._lock:
                self._state = {
                    "available":  True,   # demo data counts as "available" for UI
                    "demo":       True,
                    "positive":   round(pos, 1),
                    "neutral":    round(neu, 1),
                    "negative":   round(neg, 1),
                    "face_count": face_count,
                    "fps":        15.0,   # representative synthetic FPS
                    "dominant":   dominant,
                    "history":    list(history),
                    "emotions":   {k: round(v, 1) for k, v in demo_emotions.items()}
                }

            time.sleep(2)  # update every 2 s (matches frontend poll interval)

    # ── MJPEG Streaming ───────────────────────────────────────────────────────

    def get_frame_generator(self):
        """Yields MJPEG frames for a streaming HTTP response."""
        while True:
            with self._frame_cond:
                # Wait until a new frame is ready
                self._frame_cond.wait()
                jpeg = self._latest_jpeg
            
            if jpeg is None:
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')


# Module-level singleton — imported by main.py and the router
emotion_service = EmotionService()
