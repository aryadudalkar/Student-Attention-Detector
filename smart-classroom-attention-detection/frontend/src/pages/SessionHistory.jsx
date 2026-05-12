import { useEffect, useState, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Calendar, Clock, Users, ChevronRight, History } from 'lucide-react';
import { getSessions } from '../api';

function formatDuration(start, end) {
  if (!start) return '—';
  const s = new Date(start);
  const e = end ? new Date(end) : new Date();
  const diff = Math.floor((e - s) / 1000);
  const m = Math.floor(diff / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  return `${m}m`;
}

function formatDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString([], {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
  });
}

function formatTime(dt) {
  if (!dt) return '';
  return new Date(dt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function SessionHistory() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const location = useLocation();

  const fetchSessions = useCallback(() => {
    getSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, []);

  // Re-fetch whenever this page is navigated to
  useEffect(() => {
    setLoading(true);
    fetchSessions();
  }, [location.key, fetchSessions]);

  // Also poll every 10 seconds so active sessions update
  useEffect(() => {
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, [fetchSessions]);

  const filtered = sessions.filter(s => {
    const label = (s.label || `Session #${s.id}`).toLowerCase();
    return label.includes(search.toLowerCase());
  });

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span>Loading sessions…</span>
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Session History</h1>
        <p className="page-subtitle">{sessions.length} recorded sessions</p>
      </div>

      <div className="filter-bar">
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="Search sessions…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <span style={{ fontSize: 13, color: '#475569' }}>
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No Sessions Found</h3>
            <p>Sessions will appear here after the AI script runs.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map(session => (
            <Link
              key={session.id}
              to={`/sessions/${session.id}`}
              className="session-card"
            >
              {/* Left: icon + info */}
              <div className="flex items-center gap-3" style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                  background: session.is_active
                    ? 'rgba(34,197,94,0.12)' : 'rgba(99,102,241,0.10)',
                  border: `1px solid ${session.is_active ? 'rgba(34,197,94,0.3)' : 'rgba(99,102,241,0.2)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <History size={18} color={session.is_active ? '#22c55e' : '#818cf8'} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{
                    fontSize: 15, fontWeight: 600, color: '#f1f5f9',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                  }}>
                    {session.label || `Session #${session.id}`}
                  </div>
                  <div className="flex items-center gap-3 mt-1" style={{ flexWrap: 'wrap' }}>
                    <span className="flex items-center gap-2 text-sm text-muted">
                      <Calendar size={12} /> {formatDate(session.started_at)}
                    </span>
                    <span className="flex items-center gap-2 text-sm text-muted">
                      <Clock size={12} /> {formatTime(session.started_at)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right: meta */}
              <div className="flex items-center gap-3">
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, color: '#94a3b8', fontWeight: 500 }}>
                    Duration
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: '#f1f5f9' }}>
                    {formatDuration(session.started_at, session.ended_at)}
                  </div>
                </div>
                {session.is_active ? (
                  <span className="chip chip-green">
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: '#22c55e', display: 'inline-block',
                      boxShadow: '0 0 6px #22c55e', animation: 'pulse-dot 1.5s ease infinite'
                    }} />
                    Live
                  </span>
                ) : (
                  <span className="chip chip-gray">Ended</span>
                )}
                <ChevronRight size={16} color="#475569" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
