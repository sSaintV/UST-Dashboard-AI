'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface NewsItem {
  id:        number;
  category:  string;
  title:     string;
  summary:   string;
  priority:  'urgent' | 'high' | 'normal';
  timestamp: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function timeAgo(ts: number): string {
  const diff = Math.floor((Date.now() / 1000) - ts);
  if (diff < 60)       return 'just now';
  if (diff < 3600)     return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)    return `${Math.floor(diff / 3600)}h ago`;
  return               `${Math.floor(diff / 86400)}d ago`;
}

const PRIORITY_STYLES: Record<string, { label: string; cls: string }> = {
  urgent: { label: '🔴 Urgent',  cls: 'badge-urgent' },
  high:   { label: '🟡 Priority', cls: 'badge-priority' },
  normal: { label: '🔵 Update',   cls: 'badge-update' },
};

// ── Main Component ────────────────────────────────────────────────────────────
export default function NewsPanel() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [error, setError] = useState(false);
  const [active, setActive] = useState(0);   // which card is "featured"
  const tickerRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchNews = useCallback(async () => {
    try {
      const res  = await fetch('/api/news', { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setItems(json.items as NewsItem[]);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  // Fetch on mount, then every 5 minutes
  useEffect(() => {
    fetchNews();
    const refresh = setInterval(fetchNews, 300_000);
    return () => clearInterval(refresh);
  }, [fetchNews]);

  // Auto-advance the featured card every 6 seconds
  useEffect(() => {
    if (items.length < 2) return;
    intervalRef.current = setInterval(() => {
      setActive(prev => (prev + 1) % items.length);
    }, 6000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [items.length]);

  // ── Error state ──
  if (error) {
    return (
      <div className="panel news-panel">
        <PanelHeader />
        <div className="panel-unavailable">
          <div className="unavail-icon">⚠️</div>
          <p>News service unreachable</p>
          <p className="unavail-sub">Ensure backend is running on port 8000</p>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="panel news-panel">
        <PanelHeader />
        <div className="panel-unavailable">
          <div className="unavail-icon">📰</div>
          <p>Loading announcements…</p>
        </div>
      </div>
    );
  }

  const featured = items[active];
  const pStyle   = PRIORITY_STYLES[featured.priority] ?? PRIORITY_STYLES.normal;

  return (
    <div className="panel news-panel">
      <PanelHeader count={items.length} />

      {/* ── Featured article ── */}
      <div className="news-featured" key={featured.id}>
        <div className="news-featured-meta">
          <span className={`news-badge ${pStyle.cls}`}>{pStyle.label}</span>
          <span className="news-category">{featured.category}</span>
          <span className="news-time">{timeAgo(featured.timestamp)}</span>
        </div>
        <h2 className="news-featured-title">{featured.title}</h2>
        <p  className="news-featured-summary">{featured.summary}</p>
      </div>

      {/* ── Dot indicators ── */}
      <div className="news-dots" role="tablist" aria-label="Article navigation">
        {items.map((_, i) => (
          <button
            key={i}
            className={`news-dot ${i === active ? 'news-dot--active' : ''}`}
            onClick={() => {
              setActive(i);
              if (intervalRef.current) clearInterval(intervalRef.current);
              intervalRef.current = setInterval(
                () => setActive(p => (p + 1) % items.length),
                6000,
              );
            }}
            aria-label={`Show article ${i + 1}`}
            role="tab"
            aria-selected={i === active}
          />
        ))}
      </div>

      {/* ── Horizontal ticker strip ── */}
      <div className="news-ticker-wrapper" aria-hidden="true">
        <div className="news-ticker" ref={tickerRef}>
          {/* Duplicate for seamless loop */}
          {[...items, ...items].map((item, i) => (
            <span key={`${item.id}-${i}`} className="news-ticker-item">
              <span className="ticker-cat">{item.category}</span>
              &nbsp;·&nbsp;{item.title}
              <span className="ticker-sep">◆</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function PanelHeader({ count }: { count?: number }) {
  return (
    <div className="panel-header">
      <span className="panel-title">UST News Feed</span>
      <div className="panel-badges">
        {count != null && (
          <span className="badge badge-fps">{count} articles</span>
        )}
        <span className="badge badge-live">● LIVE</span>
      </div>
    </div>
  );
}
