"""
Footfall / Visitor Intelligence service.

Instead of opening a second camera, this service samples the face_count
from the already-running EmotionService every second.  This ensures no
extra CPU cost and zero camera contention.

Metrics produced:
  - current_count   : people visible right now
  - session_peak    : highest count seen this session
  - total_visits    : cumulative count (non-zero frames where count > 0)
  - hourly_trend    : people count bucketed into the last 12 hours (hourly)
  - minute_trend    : rolling 60-minute per-minute average (sparkline)
  - available       : True once the emotion service is up
"""

import threading
import time
import logging
from collections import deque, defaultdict
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────
SAMPLE_INTERVAL_S  = 1      # how often we poll EmotionService (seconds)
MINUTE_WINDOW      = 60     # minutes of rolling per-minute data to keep
HOURLY_WINDOW      = 12     # hours of hourly data to keep


class FootfallService:
    """Samples face_count from EmotionService and derives visitor KPIs."""

    def __init__(self):
        self._lock          = threading.Lock()
        self._thread        = None

        # Per-second raw samples: deque of (timestamp, count) for last 60 min
        self._samples: deque = deque()

        # Hourly buckets: {hour_ts: max_count_in_hour}
        self._hourly: Dict[int, int] = defaultdict(int)

        self._session_peak   = 0
        self._total_visits   = 0   # increments by face_count every sample
        self._current_count  = 0
        self._available      = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="footfall-svc"
        )
        self._thread.start()
        logger.info("FootfallService started.")

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "available":     self._available,
                "current_count": self._current_count,
                "session_peak":  self._session_peak,
                "total_visits":  self._total_visits,
                "minute_trend":  self._compute_minute_trend(),
                "hourly_trend":  self._compute_hourly_trend(),
            }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _run(self) -> None:
        # Import here to avoid circular imports at module load time
        from services.emotion_service import emotion_service

        logger.info("FootfallService polling emotion_service every %ds.", SAMPLE_INTERVAL_S)

        while True:
            ts      = time.time()
            state   = emotion_service.get_state()
            count   = state.get("face_count", 0)
            avail   = state.get("available", False)

            with self._lock:
                self._available     = avail
                self._current_count = count

                if avail and count > 0:
                    # Rolling 60-min raw samples
                    self._samples.append((ts, count))
                    cutoff = ts - MINUTE_WINDOW * 60
                    while self._samples and self._samples[0][0] < cutoff:
                        self._samples.popleft()

                    # Hourly bucket (floor to hour)
                    hour_key = int(ts // 3600) * 3600
                    self._hourly[hour_key] = max(
                        self._hourly[hour_key], count
                    )
                    # Keep only last HOURLY_WINDOW hours
                    cutoff_h = int(ts // 3600) * 3600 - HOURLY_WINDOW * 3600
                    for k in [k for k in self._hourly if k < cutoff_h]:
                        del self._hourly[k]

                    # Session stats
                    self._session_peak  = max(self._session_peak, count)
                    self._total_visits += count  # proxy: accumulate per second

            time.sleep(SAMPLE_INTERVAL_S)

    def _compute_minute_trend(self) -> List[Dict]:
        """Compute per-minute average count over the last 60 minutes."""
        now = time.time()
        buckets: Dict[int, list] = defaultdict(list)
        for ts, cnt in self._samples:
            minute_key = int(ts // 60) * 60
            buckets[minute_key].append(cnt)

        # Build 60 slots (newest = last)
        result = []
        for i in range(MINUTE_WINDOW - 1, -1, -1):
            key = int((now // 60) * 60) - i * 60
            avg = (sum(buckets[key]) / len(buckets[key])) if buckets[key] else 0
            result.append({"minute": key, "avg": round(avg, 1)})
        return result

    def _compute_hourly_trend(self) -> List[Dict]:
        """Return hourly peak counts for the last 12 hours."""
        now = time.time()
        result = []
        for i in range(HOURLY_WINDOW - 1, -1, -1):
            key  = int((now // 3600) * 3600) - i * 3600
            peak = self._hourly.get(key, 0)
            result.append({"hour": key, "peak": peak})
        return result


# Module-level singleton
footfall_service = FootfallService()
