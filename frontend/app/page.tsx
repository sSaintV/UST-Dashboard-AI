import HappinessPanel from './components/HappinessPanel';
import WeatherPanel   from './components/WeatherPanel';
import NewsPanel      from './components/NewsPanel';
import VisitorPanel   from './components/VisitorPanel';

/**
 * Dashboard root page — 2×2 full-screen grid.
 * Panel 1 (Happiness Index) is fully implemented.
 * Panels 2–4 are styled placeholders, replaced panel-by-panel.
 */
export default function DashboardPage() {
  return (
    <main className="dashboard-grid">
      {/* ── Panel 1: Happiness Index (top-left) ─── */}
      <HappinessPanel />

      {/* ── Panel 2: Weather (top-right) ─── */}
      <WeatherPanel />

      {/* ── Panel 3: News (bottom-left) ─── */}
      <NewsPanel />

      {/* ── Panel 4: Visitor Intelligence (bottom-right) ─── */}
      <VisitorPanel />
    </main>
  );
}
