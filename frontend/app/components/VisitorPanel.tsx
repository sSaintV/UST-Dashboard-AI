'use client';

import { useEffect, useState, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface HourlyBucket { hour: number; peak: number; }
interface MinuteBucket { minute: number; avg: number; }

interface FootfallData {
  available:     boolean;
  current_count: number;
  session_peak:  number;
  total_visits:  number;
  hourly_trend:  HourlyBucket[];
  minute_trend:  MinuteBucket[];
}

// ── Helper: format a unix timestamp as "HH:mm" in local time ─────────────────
function fmtHour(ts: number): string {
  const d = new Date(ts * 1000);
  return d.getHours().toString().padStart(2, '0') + ':00';
}

// ── Occupancy level helper ─────────────────────────────────────────────────────
function occupancyLevel(count: number): { label: string; color: string } {
  if (count === 0)  return { label: 'Empty',    color: '#4a5a7a' };
  if (count <= 2)   return { label: 'Quiet',    color: '#22c55e' };
  if (count <= 5)   return { label: 'Moderate', color: '#FFB81C' };
  return                  { label: 'Busy',     color: '#f43f5e' };
}

// ── Mini sparkline (60-min per-minute) ───────────────────────────────────────
function MinuteSparkline({ data, color }: { data: MinuteBucket[]; color: string }) {
  if (data.length < 2) return null;
  const W   = 300;
  const H   = 48;
  const max = Math.max(...data.map(d => d.avg), 1);
  const pts = data.map((d, i) => ({
    x: (i / (data.length - 1)) * W,
    y: H - (d.avg / max) * H,
  }));
  const line  = pts.map(p => `${p.x},${p.y}`).join(' ');
  const last  = pts[pts.length - 1];
  const areaD = [
    `M ${pts[0].x},${pts[0].y}`,
    ...pts.slice(1).map(p => `L ${p.x},${p.y}`),
    `L ${last.x},${H}`, `L ${pts[0].x},${H}`, 'Z',
  ].join(' ');
  const gid = `fg-${color.replace('#', '')}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: '100%', display: 'block' }} aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path  d={areaD} fill={`url(#${gid})`} />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={last.x} cy={last.y} r="4" fill={color} />
    </svg>
  );
}

// ── Hourly bar chart ──────────────────────────────────────────────────────────
function HourlyChart({ data }: { data: HourlyBucket[] }) {
  const max = Math.max(...data.map(d => d.peak), 1);
  // Show last 8 hours for readability
  const visible = data.slice(-8);
  return (
    <div className="hourly-chart">
      {visible.map((bucket, i) => {
        const pct  = (bucket.peak / max) * 100;
        const isNow = i === visible.length - 1;
        return (
          <div key={bucket.hour} className="hourly-bar-col">
            <div className="hourly-bar-track">
              <div
                className={`hourly-bar-fill ${isNow ? 'hourly-bar-now' : ''}`}
                style={{ height: `${Math.max(pct, 2)}%` }}
                title={`${bucket.peak} people`}
              />
            </div>
            <span className="hourly-label">{fmtHour(bucket.hour)}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── KPI tile ──────────────────────────────────────────────────────────────────
function KpiTile({ label, value, sub, accent }: {
  label:  string;
  value:  string | number;
  sub?:   string;
  accent: string;
}) {
  return (
    <div className="visitor-kpi-tile" style={{ borderColor: `${accent}33` }}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value" style={{ color: accent }}>{value}</span>
      {sub && <span className="kpi-sub">{sub}</span>}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function VisitorPanel() {
  const [data,  setData]  = useState<FootfallData | null>(null);
  const [error, setError] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res  = await fetch('/api/footfall', { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as FootfallData;
      setData(json);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 2000);
    return () => clearInterval(t);
  }, [fetchData]);

  // ── Error ──
  if (error) {
    return (
      <div className="panel visitor-panel">
        <PanelHeader />
        <div className="panel-unavailable">
          <div className="unavail-icon">⚠️</div>
          <p>Backend unreachable</p>
          <p className="unavail-sub">Ensure FastAPI is running on port 8000</p>
        </div>
      </div>
    );
  }

  // ── Loading ──
  if (!data) {
    return (
      <div className="panel visitor-panel">
        <PanelHeader />
        <div className="panel-unavailable">
          <div className="unavail-icon">📷</div>
          <p>Initialising…</p>
          <p className="unavail-sub">Waiting for camera and footfall data.</p>
        </div>
      </div>
    );
  }

  const occ     = occupancyLevel(data.current_count);
  const visits  = data.total_visits > 9999
    ? `${(data.total_visits / 1000).toFixed(1)}k`
    : data.total_visits.toString();

  return (
    <div className="panel visitor-panel">
      <PanelHeader available={data.available} />

      {/* ── KPI row ── */}
      <div className="visitor-kpi-row">
        <KpiTile
          label="Now"
          value={data.current_count}
          sub={occ.label}
          accent={occ.color}
        />
        <KpiTile
          label="Session Peak"
          value={data.session_peak}
          sub="people"
          accent="#00B5B8"
        />
        <KpiTile
          label="Cumulative"
          value={visits}
          sub="counted"
          accent="#FFB81C"
        />
      </div>

      {/* ── Occupancy status bar ── */}
      <div className="occupancy-bar-wrapper">
        <span className="occupancy-bar-label">Occupancy Level</span>
        <div className="occupancy-bar-track">
          <div
            className="occupancy-bar-fill"
            style={{
              width: `${Math.min((data.current_count / Math.max(data.session_peak, 1)) * 100, 100)}%`,
              background: `linear-gradient(90deg, ${occ.color}88, ${occ.color})`,
              boxShadow: `0 0 10px ${occ.color}55`,
            }}
          />
        </div>
        <span className="occupancy-bar-pct" style={{ color: occ.color }}>
          {occ.label}
        </span>
      </div>

      {/* ── Hourly bar chart ── */}
      <div className="visitor-section">
        <div className="visitor-section-header">
          <span className="visitor-section-title">Hourly Peak Traffic</span>
          <span className="visitor-section-sub">last 8 hours</span>
        </div>
        <HourlyChart data={data.hourly_trend} />
      </div>

      {/* ── 60-min sparkline ── */}
      <div className="visitor-section visitor-sparkline-section">
        <div className="visitor-section-header">
          <span className="visitor-section-title">60-min Live Trend</span>
          <span className="visitor-section-sub">per-minute avg</span>
        </div>
        <div className="visitor-sparkline-wrapper">
          <MinuteSparkline data={data.minute_trend} color="#00B5B8" />
        </div>
      </div>
    </div>
  );
}

function PanelHeader({ available }: { available?: boolean }) {
  return (
    <div className="panel-header">
      <span className="panel-title">Visitor Intelligence</span>
      <div className="panel-badges">
        <span className={`badge ${available ? 'badge-live' : 'badge-offline'}`}>
          {available ? '● LIVE' : '○ OFFLINE'}
        </span>
      </div>
    </div>
  );
}
