import React from 'react';
import { useUsageHistory } from '@/hooks/useUsageHistory';

function formatMMSS(totalSec: number): string {
  const m = Math.floor(totalSec / 60);
  const s = Math.floor(totalSec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function Sparkline({ points, color = '#3b82f6', title }: { points: number[]; color?: string; title: string }) {
  const width = 320;
  const height = 64;
  const padding = 8;
  const n = points.length;
  const min = Math.min(...points, 0);
  const max = Math.max(...points, 0);
  const span = Math.max(max - min, 1);
  const xFor = (i: number) => padding + (i * (width - padding * 2)) / Math.max(n - 1, 1);
  const yFor = (v: number) => padding + (height - padding * 2) * (1 - (v - min) / span);
  const d = points.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i)} ${yFor(v)}`).join(' ');
  const todayX = xFor(n - 1);
  const todayY = yFor(points[n - 1] ?? 0);
  const minIdx = points.reduce((mi, v, i) => (v < points[mi] ? i : mi), 0);
  const maxIdx = points.reduce((mi, v, i) => (v > points[mi] ? i : mi), 0);
  return (
    <svg width={width} height={height} role="img" aria-label={title} tabIndex={0}>
      <rect x={0} y={0} width={width} height={height} fill="#f9fafb" stroke="#e5e7eb" />
      <path d={d} stroke={color} fill="none" strokeWidth={2} />
      {/* min/max dots */}
      <circle cx={xFor(minIdx)} cy={yFor(points[minIdx] ?? 0)} r={3} fill="#ef4444" aria-label="Min" />
      <circle cx={xFor(maxIdx)} cy={yFor(points[maxIdx] ?? 0)} r={3} fill="#22c55e" aria-label="Max" />
      {/* today marker */}
      <circle cx={todayX} cy={todayY} r={3} fill="#374151" aria-label="Today" />
    </svg>
  );
}

export default function UsagePage(): React.JSX.Element {
  const { days, data, loading, error, setDays, totals } = useUsageHistory(14);
  const series = data?.series ?? [];
  const rendersSeries = series.map(s => s.renders);
  const ttsSeries = series.map(s => s.tts_sec);
  const isEmpty = !loading && series.every(s => (s.renders || 0) === 0 && (s.tts_sec || 0) === 0);

  return (
    <div style={{ padding: 16 }}>
      <h1>Your usage</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }} role="group" aria-label="Range selector">
        {[14,30,90].map((d) => (
          <button
            key={d}
            className={days===d ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setDays(d)}
            aria-pressed={days===d}
          >{d}</button>
        ))}
      </div>

      {loading && <div role="status" aria-live="polite">Loading…</div>}
      {error && <div role="alert" style={{ color: '#ef4444' }}>{error}</div>}

      {!loading && !error && (
        <>
          {/* KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div className="empty-state-card">
              <div className="text-sm">Renders</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{totals.renders}</div>
            </div>
            <div className="empty-state-card">
              <div className="text-sm">TTS time</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{formatMMSS(totals.tts_sec)}</div>
            </div>
            <div className="empty-state-card">
              <div className="text-sm">Avg per day</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{totals.avg_per_day.toFixed(2)}</div>
            </div>
          </div>

          {/* Charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div className="empty-state-card">
              <h3 className="text-sm" style={{ marginBottom: 8 }}>Renders</h3>
              <Sparkline points={rendersSeries} title={`Renders over ${days} days`} />
            </div>
            <div className="empty-state-card">
              <h3 className="text-sm" style={{ marginBottom: 8 }}>TTS seconds</h3>
              <Sparkline points={ttsSeries} color="#10b981" title={`TTS seconds over ${days} days`} />
            </div>
          </div>

          {/* Table */}
          {isEmpty ? (
            <div className="empty-state-card">No activity yet</div>
          ) : (
            <table className="empty-state-card" aria-label="Usage table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th className="text-xs" style={{ textAlign: 'left', padding: '6px 8px' }}>Day</th>
                  <th className="text-xs" style={{ textAlign: 'right', padding: '6px 8px' }}>Renders</th>
                  <th className="text-xs" style={{ textAlign: 'right', padding: '6px 8px' }}>TTS</th>
                </tr>
              </thead>
              <tbody>
                {series.map((p) => (
                  <tr key={p.day}>
                    <td className="text-xs" style={{ padding: '6px 8px' }}>{p.day}</td>
                    <td className="text-xs" style={{ textAlign: 'right', padding: '6px 8px' }}>{p.renders}</td>
                    <td className="text-xs" style={{ textAlign: 'right', padding: '6px 8px' }}>{formatMMSS(p.tts_sec)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
