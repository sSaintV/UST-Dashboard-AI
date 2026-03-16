'use client';

import { useEffect, useState, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface WeatherData {
  current: {
    temp: number;
    wind_speed: number;
    wind_direction: number;
    weather_code: number;
    time: string;
  };
  hourly: {
    times: string[];
    temps: number[];
    codes: number[];
    humidity: number[];
    uv_index: number[];
  };
  location: string;
}

// ── WMO Weather Codes mapping ──────────────────────────────────────────────────
// Ref: https://open-meteo.com/en/docs
const WEATHER_MAP: Record<number, { label: string; icon: string; bg: string }> = {
  0:  { label: 'Clear Sky',            icon: '☀️', bg: 'linear-gradient(135deg, #FFB81C 0%, #003087 100%)' },
  1:  { label: 'Mainly Clear',         icon: '🌤️', bg: 'linear-gradient(135deg, #FFB81C 0%, #003087 100%)' },
  2:  { label: 'Partly Cloudy',        icon: '⛅', bg: 'linear-gradient(135deg, #94a3b8 0%, #003087 100%)' },
  3:  { label: 'Overcast',             icon: '☁️', bg: 'linear-gradient(135deg, #4a5a7a 0%, #003087 100%)' },
  45: { label: 'Foggy',                icon: '🌫️', bg: 'linear-gradient(135deg, #8899b8 0%, #003087 100%)' },
  48: { label: 'Rime Fog',             icon: '🌫️', bg: 'linear-gradient(135deg, #8899b8 0%, #003087 100%)' },
  51: { label: 'Light Drizzle',        icon: '🌦️', bg: 'linear-gradient(135deg, #00B5B8 0%, #003087 100%)' },
  61: { label: 'Slight Rain',          icon: '🌧️', bg: 'linear-gradient(135deg, #00B5B8 0%, #003087 100%)' },
  63: { label: 'Moderate Rain',        icon: '🌧️', bg: 'linear-gradient(135deg, #00B5B8 0%, #003087 100%)' },
  65: { label: 'Heavy Rain',           icon: '🌧️', bg: 'linear-gradient(135deg, #003087 0%, #07091a 100%)' },
  80: { label: 'Rain Showers',         icon: '🌦️', bg: 'linear-gradient(135deg, #00B5B8 0%, #003087 100%)' },
  95: { label: 'Thunderstorms',        icon: '⛈️', bg: 'linear-gradient(135deg, #003087 0%, #f43f5e 100%)' },
};

const DEFAULT_WEATHER = { label: 'Unknown', icon: '❓', bg: 'var(--bg-panel)' };

// ── Sparkline component (adapted for temperature) ─────────────────────────────
function TempSparkline({ temps, color }: { temps: number[]; color: string }) {
  if (temps.length < 2) return null;

  const W  = 400;
  const H  = 80;
  const min = Math.min(...temps) - 1;
  const max = Math.max(...temps) + 1;
  const range = max - min;

  const pts = temps.map((t, i) => ({
    x: (i / (temps.length - 1)) * W,
    y: H - ((t - min) / range) * H
  }));

  const polylineStr = pts.map(p => `${p.x},${p.y}`).join(' ');
  const last = pts[pts.length - 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="temp-sparkline-svg">
      <polyline
        points={polylineStr}
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={last.x} cy={last.y} r="4" fill={color} />
    </svg>
  );
}

export default function WeatherPanel() {
  const [data, setData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchWeather = useCallback(async () => {
    try {
      const res = await fetch('/api/weather');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (err) {
      console.error('Weather fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWeather();
    const interval = setInterval(fetchWeather, 900000); // 15 mins
    return () => clearInterval(interval);
  }, [fetchWeather]);

  if (loading || !data) {
    return (
      <div className="panel weather-panel">
        <div className="panel-header">
            <span className="panel-title">Cyberjaya Weather</span>
        </div>
        <div className="panel-unavailable">
          <p>Loading weather data...</p>
        </div>
      </div>
    );
  }

  const weather = WEATHER_MAP[data.current.weather_code] || DEFAULT_WEATHER;

  return (
    <div className="panel weather-panel" style={{ background: weather.bg }}>
      <div className="weather-overlay" />
      
      <div className="panel-header">
        <span className="panel-title">Cyberjaya Weather</span>
        <span className="badge badge-live">● LIVE</span>
      </div>

      <div className="weather-content">
        {/* Side-by-side: Left = icon + temp, Right = 4 stat cards */}
        <div className="weather-main">
          {/* Left column: icon + temperature */}
          <div className="weather-hero">
            <span className="weather-icon-large">{weather.icon}</span>
            <div className="weather-temp-group">
              <span className="weather-temp">{Math.round(data.current.temp)}°</span>
              <span className="weather-desc">{weather.label}</span>
            </div>
          </div>

          {/* Right column: 2x2 stat grid */}
          <div className="weather-grid">
            <WeatherStat label="Humidity" value={`${data.hourly.humidity[0]}%`} icon="💧" />
            <WeatherStat label="Wind"     value={`${data.current.wind_speed} km/h`} icon="💨" />
            <WeatherStat label="UV Index" value={data.hourly.uv_index[0].toFixed(1)} icon="☀️" />
            <WeatherStat label="Location" value={data.location} icon="📍" />
          </div>
        </div>

        {/* Footer: 24h trend sparkline full-width */}
        <div className="weather-footer">
          <div className="forecast-header">
            <span className="forecast-title">24h Temperature Trend</span>
            <span className="forecast-range">
              {Math.min(...data.hourly.temps)}° — {Math.max(...data.hourly.temps)}°
            </span>
          </div>
          <div className="forecast-graph">
            <TempSparkline temps={data.hourly.temps} color="#ffffff" />
          </div>
        </div>
      </div>
    </div>
  );
}

function WeatherStat({ label, value, icon }: { label: string; value: string | number; icon: string }) {
  return (
    <div className="weather-stat-card">
      <span className="stat-icon">{icon}</span>
      <div className="stat-info">
        <span className="stat-label">{label}</span>
        <span className="stat-value">{value}</span>
      </div>
    </div>
  );
}
