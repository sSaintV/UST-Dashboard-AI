'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface HistoryPoint {
  ts:       number;
  positive: number;
  neutral:  number;
  negative: number;
  faces:    number;
}

interface EmotionData {
  available:  boolean;
  demo:       boolean;
  positive:   number;
  neutral:    number;
  negative:   number;
  face_count: number;
  fps:        number;
  dominant:   string;
  history:    HistoryPoint[];
}

// ── Mood configuration map ────────────────────────────────────────────────────
// Maps FERPlus class labels → display emoji, accent colour, and friendly label.
const MOOD_CFG: Record<string, { emoji: string; color: string; label: string }> = {
  happiness: { emoji: '😊', color: '#22c55e',  label: 'Happy'     },
  surprise:  { emoji: '😮', color: '#00B5B8',  label: 'Surprised' },
  neutral:   { emoji: '😐', color: '#94a3b8',  label: 'Neutral'   },
  sadness:   { emoji: '😔', color: '#818cf8',  label: 'Sad'       },
  fear:      { emoji: '😨', color: '#f59e0b',  label: 'Fearful'   },
  anger:     { emoji: '😠', color: '#f43f5e',  label: 'Angry'     },
  disgust:   { emoji: '🤢', color: '#84cc16',  label: 'Disgusted' },
  contempt:  { emoji: '😒', color: '#a78bfa',  label: 'Contempt'  },
};
const DEFAULT_MOOD = MOOD_CFG.neutral;

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Sparkline({ 
  history, 
  color, 
  dataKey 
}: { 
  history: HistoryPoint[]; 
  color: string; 
  dataKey: 'positive' | 'negative' | 'neutral' 
}) {
  if (history.length < 2) return null;

  const W  = 300;
  const H  = 60;
  const PX = 4;  // horizontal padding
  const PY = 4;  // vertical padding

  // Map each history point to SVG coordinates
  const pts = history.map((h, i) => {
    const x = PX + (i / (history.length - 1)) * (W - 2 * PX);
    const val = h[dataKey];
    // y=0 is top → invert so 100% is at the top
    const y = H - PY - (val / 100) * (H - 2 * PY);
    return { x, y };
  });

  const polylineStr = pts.map(p => `${p.x},${p.y}`).join(' ');

  // Filled area path: trace the line, drop to baseline, return left
  const first = pts[0];
  const last  = pts[pts.length - 1];
  const fillD = [
    `M ${first.x},${first.y}`,
    ...pts.slice(1).map(p => `L ${p.x},${p.y}`),
    `L ${last.x},${H - PY}`,
    `L ${first.x},${H - PY}`,
    'Z',
  ].join(' ');

  const gradId = `sg-${color.replace('#', '')}`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ width: '100%', height: '100%', display: 'block' }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Filled area under the curve */}
      <path d={fillD} fill={`url(#${gradId})`} />

      {/* Line */}
      <polyline
        points={polylineStr}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* Current-value dot with glow ring */}
      <circle cx={last.x} cy={last.y} r="6"  fill={color} opacity="0.25" />
      <circle cx={last.x} cy={last.y} r="3.5" fill={color} />
    </svg>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function HappinessPanel() {
  const [data,  setData]  = useState<EmotionData | null>(null);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/emotion', { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as EmotionData;
      setData(json);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, 2000);  // poll every 2 s
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchData]);

  // Derived display values
  const isAvailable  = data?.available ?? false;
  let dominant       = data?.dominant ?? 'neutral';
  
  // Logic: If Negative sentiment is significantly higher than Positive, 
  // and dominant is Neutral, we show a generic negative mood to be more reactive.
  if (data && data.negative > 20 && data.negative > data.positive && dominant === 'neutral') {
    dominant = 'sadness';
  }
  
  const moodCfg      = MOOD_CFG[dominant] ?? DEFAULT_MOOD;
  const accentColor  = moodCfg.color;

  // ── Render: backend unreachable ──
  if (error) {
    return (
      <div className="panel happiness-panel">
        <PanelHeader data={null} />
        <div className="panel-unavailable">
          <div className="unavail-icon">⚠️</div>
          <p>Backend unreachable</p>
          <p className="unavail-sub">
            Ensure FastAPI is running on port 8000
          </p>
        </div>
      </div>
    );
  }

  // ── Render: camera / model not ready ──
  if (!data || !isAvailable) {
    return (
      <div className="panel happiness-panel">
        <PanelHeader data={data} />
        <div className="panel-unavailable">
          <div className="unavail-icon">📷</div>
          <p>Initialising…</p>
          <p className="unavail-sub">
            Camera feed or ONNX model loading. Set DEMO_MODE=true for instant demo.
          </p>
        </div>
      </div>
    );
  }

  // ── Render: live / demo data ──
  return (
    <div className="panel happiness-panel">
      <PanelHeader data={data} />

      <div className="happiness-content">
        {/* ── Live Video Feed ── */}
        <div className="live-feed-wrapper">
          {isAvailable ? (
            <img 
              src="/api/emotion/feed" 
              alt="Live camera feed" 
              className="live-feed-img"
              onError={(e) => {
                 (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          ) : (
            <div className="panel-unavailable" style={{ height: '100%', background: 'transparent' }}>
              <div className="unavail-icon">📷</div>
              <p>Camera Off</p>
            </div>
          )}
        </div>

        {/* ── Stats Column ── */}
        <div className="happiness-content-stats">
          {/* ── Mood orb ── */}
          <div className="mood-orb-wrapper">
            {/* Diffuse background glow — transitions colour with mood */}
            <div
              className="mood-aura"
              style={{
                background: `radial-gradient(circle, ${accentColor}55 0%, transparent 72%)`,
              }}
            />

            <div
              className="mood-orb"
              style={{
                borderColor: accentColor,
                boxShadow:   `0 0 32px ${accentColor}55, 0 0 8px ${accentColor}33`,
              }}
            >
              <span className="mood-emoji" role="img" aria-label={moodCfg.label}>
                {moodCfg.emoji}
              </span>
            </div>

            <div className="mood-label" style={{ color: accentColor }}>
              {moodCfg.label}
            </div>

            <div className="face-count">
              <span className="face-icon" aria-hidden="true">👤</span>
              <span>
                {data.face_count} {data.face_count === 1 ? 'person' : 'people'} detected
              </span>
            </div>
          </div>

          {/* ── Sentiment bars ── */}
          <div className="sentiment-bars" role="region" aria-label="Sentiment breakdown">
            <SentimentRow
              label="😊 Positive"
              pct={data.positive}
              fillClass="bar-positive"
              labelClass="positive-label"
            />
            <SentimentRow
              label="😐 Neutral"
              pct={data.neutral}
              fillClass="bar-neutral"
              labelClass="neutral-label"
            />
            <SentimentRow
              label="😔 Negative"
              pct={data.negative}
              fillClass="bar-negative"
              labelClass="negative-label"
            />
          </div>

          {/* ── Sparklines (rolling window) ── */}
          {data.history.length >= 2 && (
            <div className="sparkline-section">
              <div className="sparkline-row">
                <div className="sparkline-item">
                  <div className="sparkline-label">Positive % (30s)</div>
                  <div className="sparkline-svg-wrapper">
                    <Sparkline history={data.history} color="#22c55e" dataKey="positive" />
                  </div>
                </div>
                <div className="sparkline-item">
                  <div className="sparkline-label">Negative % (30s)</div>
                  <div className="sparkline-svg-wrapper">
                    <Sparkline history={data.history} color="#f43f5e" dataKey="negative" />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PanelHeader({ data }: { data: EmotionData | null }) {
  return (
    <div className="panel-header">
      <span className="panel-title">Happiness Index</span>
      <div className="panel-badges">
        {data?.demo && (
          <span className="badge badge-demo">DEMO</span>
        )}
        {data?.fps != null && data.fps > 0 && (
          <span className="badge badge-fps">{data.fps} FPS</span>
        )}
        <span className={`badge ${data?.available ? 'badge-live' : 'badge-offline'}`}>
          {data?.available ? '● LIVE' : '○ OFFLINE'}
        </span>
      </div>
    </div>
  );
}

function SentimentRow({
  label,
  pct,
  fillClass,
  labelClass,
}: {
  label:      string;
  pct:        number;
  fillClass:  string;
  labelClass: string;
}) {
  return (
    <div className="sentiment-row">
      <span className={`sentiment-label ${labelClass}`}>{label}</span>
      <div className="bar-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div
          className={`bar-fill ${fillClass}`}
          style={{ width: `${Math.max(pct, 0.5)}%` }}
        />
      </div>
      <span className="sentiment-pct">{pct.toFixed(1)}%</span>
    </div>
  );
}
