import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  Users, TrendingUp, AlertTriangle, Smartphone, BookOpen,
  Activity, Play, Square, CheckCircle, Clock, BarChart3
} from 'lucide-react';
import { getActiveSession, getSessionOverview, startSession, endSession } from '../api';

const GRADE_COLOR = { A: '#22c55e', B: '#86efac', C: '#facc15', D: '#fb923c', F: '#ef4444' };

const DONUT_COLORS = ['#22c55e', '#facc15', '#ef4444', '#fb923c'];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    return (
      <div style={{
        background: '#0f172a', border: '1px solid rgba(99,102,241,0.2)',
        borderRadius: 10, padding: '10px 14px', fontSize: 13
      }}>
        <div style={{ fontWeight: 600, color: payload[0].payload.color }}>{payload[0].name}</div>
        <div style={{ color: '#94a3b8', marginTop: 2 }}>{payload[0].value} students</div>
      </div>
    );
  }
  return null;
};

function StatCard({ label, value, sub, icon: Icon, color = '#6366f1' }) {
  return (
    <div className="stat-card" style={{ '--accent-color': color }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
        <div className="stat-label">{label}</div>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `${color}18`, border: `1px solid ${color}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Icon size={16} color={color} />
        </div>
      </div>
      <div className="stat-value" style={{ color }}>{value ?? '—'}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function StartSessionModal({ onStart, onClose }) {
  const [label, setLabel] = useState('');
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!label.trim()) return;
    setLoading(true);
    try { await onStart(label.trim()); }
    finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">Start New Session</div>
        <div className="input-group">
          <label className="input-label">Session Label</label>
          <input
            className="input"
            placeholder="e.g. Math Class – April 5"
            value={label}
            onChange={e => setLabel(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleStart()}
            autoFocus
          />
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleStart} disabled={loading}>
            <Play size={14} />
            {loading ? 'Starting…' : 'Start Session'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function DashboardHome() {
  const [sessionData, setSessionData] = useState(null);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [endingSession, setEndingSession] = useState(false);

  const fetchData = async () => {
    try {
      const active = await getActiveSession();
      setSessionData(active);
      if (active.active && active.session?.id) {
        try {
          const ov = await getSessionOverview(active.session.id);
          setOverview(ov);
        } catch { setOverview(null); }
      } else {
        setOverview(null);
      }
    } catch {
      setSessionData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartSession = async (label) => {
    await startSession(label);
    setShowModal(false);
    fetchData();
  };

  const handleEndSession = async () => {
    if (!sessionData?.session?.id) return;
    setEndingSession(true);
    try {
      await endSession(sessionData.session.id);
      fetchData();
    } finally {
      setEndingSession(false);
    }
  };

  const isActive = sessionData?.active;
  const session = sessionData?.session;

  const donutData = overview ? [
    { name: 'Attentive', value: overview.attentive_count, color: '#22c55e' },
    { name: 'Partial', value: overview.partially_attentive_count, color: '#facc15' },
    { name: 'Distracted', value: overview.distracted_count, color: '#ef4444' },
    { name: 'Phone', value: overview.phone_detected_count, color: '#fb923c' },
  ].filter(d => d.value > 0) : [];

  const formatTime = (dt) => {
    if (!dt) return '—';
    return new Date(dt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dt) => {
    if (!dt) return '';
    return new Date(dt).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span>Connecting to session…</span>
      </div>
    );
  }

  return (
    <>
      {showModal && (
        <StartSessionModal
          onStart={handleStartSession}
          onClose={() => setShowModal(false)}
        />
      )}

      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            {isActive
              ? `Live: ${session?.label} — started at ${formatTime(session?.started_at)}`
              : 'No active monitoring session'}
          </p>
        </div>
        <div className="flex gap-2">
          {isActive ? (
            <button
              className="btn btn-danger"
              onClick={handleEndSession}
              disabled={endingSession}
            >
              <Square size={14} />
              {endingSession ? 'Ending…' : 'End Session'}
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              <Play size={14} />
              Start Session
            </button>
          )}
          {isActive && session?.id && (
            <Link to={`/sessions/${session.id}`} className="btn btn-ghost">
              <BarChart3 size={14} />
              View Detail
            </Link>
          )}
        </div>
      </div>

      {/* Status Banner */}
      <div className="card" style={{
        background: isActive
          ? 'linear-gradient(135deg, rgba(34,197,94,0.08), rgba(99,102,241,0.08))'
          : 'var(--bg-card)',
        borderColor: isActive ? 'rgba(34,197,94,0.3)' : 'var(--border)'
      }}>
        <div className="flex items-center gap-3">
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: isActive ? 'rgba(34,197,94,0.15)' : 'rgba(71,85,105,0.2)',
            border: `1px solid ${isActive ? 'rgba(34,197,94,0.3)' : 'rgba(71,85,105,0.3)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            {isActive
              ? <Activity size={20} color="#22c55e" />
              : <Clock size={20} color="#475569" />}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: isActive ? '#22c55e' : '#94a3b8' }}>
              {isActive ? 'Monitoring Active' : 'System Idle'}
            </div>
            <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>
              {isActive
                ? `Session ID #${session?.id} • ${formatDate(session?.started_at)}`
                : 'Start a session manually or run the AI detection script'}
            </div>
          </div>
          {isActive && overview && (
            <div style={{ textAlign: 'right', paddingRight: '4px' }}>
              <div style={{
                fontSize: 32, fontWeight: 800, lineHeight: 1, paddingBottom: '4px',
                color: GRADE_COLOR[overview.class_grade] || '#94a3b8'
              }}>
                {overview.class_grade}
              </div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Class Grade</div>
            </div>
          )}
        </div>
      </div>

      {/* Stats Row */}
      {overview ? (
        <>
          <div className="stats-grid">
            <StatCard
              label="Total Students"
              value={overview.total_students}
              sub="Tracked this session"
              icon={Users}
              color="#6366f1"
            />
            <StatCard
              label="Avg Attention"
              value={`${(overview.class_avg_score * 100).toFixed(0)}%`}
              sub="Class average score"
              icon={TrendingUp}
              color={GRADE_COLOR[overview.class_grade] || '#6366f1'}
            />
            <StatCard
              label="Attentive"
              value={`${overview.attentive_pct?.toFixed(1)}%`}
              sub={`${overview.attentive_count} students`}
              icon={CheckCircle}
              color="#22c55e"
            />
            <StatCard
              label="Distracted"
              value={`${overview.distracted_pct?.toFixed(1)}%`}
              sub={`${overview.distracted_count} students`}
              icon={AlertTriangle}
              color="#ef4444"
            />
            <StatCard
              label="Phone Detections"
              value={overview.phone_detected_count}
              sub="Students using phone"
              icon={Smartphone}
              color="#fb923c"
            />
          </div>

          {/* Donut Chart */}
          <div className="grid-2" style={{ alignItems: 'start' }}>
            <div className="card">
              <div className="card-title"><Activity size={14} /> Attention Distribution</div>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={110}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {donutData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => (
                      <span style={{ color: '#94a3b8', fontSize: 13 }}>{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-title"><BarChart3 size={14} /> Breakdown</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 8 }}>
                {[
                  { label: 'Attentive', count: overview.attentive_count, total: overview.total_students, color: '#22c55e' },
                  { label: 'Partially Attentive', count: overview.partially_attentive_count, total: overview.total_students, color: '#facc15' },
                  { label: 'Distracted', count: overview.distracted_count, total: overview.total_students, color: '#ef4444' },
                  { label: 'Phone Detected', count: overview.phone_detected_count, total: overview.total_students, color: '#fb923c' },
                ].map(({ label, count, total, color }) => (
                  <div key={label}>
                    <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                      <span style={{ fontSize: 13, color: '#94a3b8' }}>{label}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color }}>{count} / {total}</span>
                    </div>
                    <div className="score-bar">
                      <div
                        className="score-fill"
                        style={{
                          width: `${total > 0 ? (count / total) * 100 : 0}%`,
                          background: color
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">📡</div>
            <h3>Waiting for Session Data</h3>
            <p>
              {isActive
                ? 'The AI script is running. Data will appear once frames are processed.'
                : 'No session is active. Run the AI detection script or start a session above.'}
            </p>
          </div>
        </div>
      )}
    </>
  );
}
