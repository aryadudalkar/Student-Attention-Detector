import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell
} from 'recharts';
import {
  ArrowLeft, Users, AlertTriangle, Smartphone,
  ChevronUp, ChevronDown, Clock, MessageSquare, Mail, Send, FileText, Download
} from 'lucide-react';
import {
  getSessionOverview, getSessionSummary, getSessionTimeline,
  getTeacherFeedback, generateTeacherFeedback, sendFeedbackEmail, downloadSessionPdf
} from '../api';

const GRADE_COLOR = { A: '#22c55e', B: '#86efac', C: '#facc15', D: '#fb923c', F: '#ef4444' };

function getRowClass(grade) {
  if (['A', 'B'].includes(grade)) return 'row-green';
  if (grade === 'C') return 'row-yellow';
  return 'row-red';
}

function ScoreBar({ value }) {
  const pct = (value * 100).toFixed(0);
  const color = value >= 0.85 ? '#22c55e' : value >= 0.70 ? '#86efac' :
    value >= 0.55 ? '#facc15' : value >= 0.40 ? '#fb923c' : '#ef4444';
  return (
    <div>
      <span style={{ fontSize: 13, fontWeight: 600, color }}>{pct}%</span>
      <div className="score-bar" style={{ marginTop: 4, width: 80 }}>
        <div className="score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

const TimelineTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <div style={{
        background: '#0f172a', border: '1px solid rgba(99,102,241,0.3)',
        borderRadius: 12, padding: '12px 16px', fontSize: 13
      }}>
        <div style={{ fontWeight: 700, color: '#f1f5f9', marginBottom: 6 }}>
          Segment {d.segment} ({d.time})
        </div>
        <div style={{ color: '#22c55e' }}>Attention: {d.attention_pct}%</div>
        <div style={{ color: '#ef4444' }}>Distraction: {d.distraction_pct}%</div>
        {d.phone_count > 0 && <div style={{ color: '#fb923c' }}>📱 Phones: {d.phone_count}</div>}
        <div style={{ color: '#64748b', marginTop: 4 }}>
          {d.student_count} students · {d.total_observations} observations
        </div>
      </div>
    );
  }
  return null;
};

function getBarColor(pct) {
  if (pct >= 70) return '#22c55e';
  if (pct >= 50) return '#facc15';
  return '#ef4444';
}

export default function SessionDetail() {
  const { id } = useParams();
  const [overview, setOverview] = useState(null);
  const [summary, setSummary] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('avg_score');
  const [sortDir, setSortDir] = useState('desc');
  const [search, setSearch] = useState('');
  const [genLoading, setGenLoading] = useState(false);
  const [emailInput, setEmailInput] = useState('');
  const [showGenEmail, setShowGenEmail] = useState(false);
  const [showSendEmail, setShowSendEmail] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [emailError, setEmailError] = useState('');

  useEffect(() => {
    Promise.all([
      getSessionOverview(id).catch(() => null),
      getSessionSummary(id).catch(() => []),
      getSessionTimeline(id).catch(() => []),
      getTeacherFeedback(id).catch(() => null),
    ]).then(([ov, sm, tl, fb]) => {
      setOverview(ov);
      setSummary(sm);
      setTimeline(tl);
      setFeedback(fb);
    }).finally(() => setLoading(false));
  }, [id]);

  const handleGenerate = async () => {
    setGenLoading(true);
    try {
      const fb = await generateTeacherFeedback(id, emailInput);
      setFeedback(fb);
      setShowGenEmail(false);
      if (emailInput) setEmailSent(true);
    } catch (e) { console.error(e); }
    finally { setGenLoading(false); }
  };

  const handleSendEmail = async () => {
    if (!emailInput.trim()) return;
    setEmailSending(true);
    setEmailError('');
    try {
      await sendFeedbackEmail(id, emailInput.trim());
      setEmailSent(true);
      setShowSendEmail(false);
    } catch (e) {
      console.error(e);
      try {
        const errObj = JSON.parse(e.message);
        setEmailError(errObj.error || 'Failed to send email.');
      } catch {
        setEmailError('Failed to send email. Check address and try again.');
      }
    }
    finally { setEmailSending(false); }
  };

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <ChevronUp size={12} style={{ opacity: 0.2 }} />;
    return sortDir === 'asc'
      ? <ChevronUp size={12} style={{ color: '#818cf8' }} />
      : <ChevronDown size={12} style={{ color: '#818cf8' }} />;
  };

  const filtered = summary
    .filter(s => {
      const name = (s.student_name || `ID ${s.student_id || ''}`).toLowerCase();
      const usn = (s.student_usn || '').toLowerCase();
      const q = search.toLowerCase();
      return name.includes(q) || usn.includes(q);
    })
    .sort((a, b) => {
      let aVal = a[sortKey] ?? 0;
      let bVal = b[sortKey] ?? 0;
      if (typeof aVal === 'string') aVal = aVal.charCodeAt(0);
      if (typeof bVal === 'string') bVal = bVal.charCodeAt(0);
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
    });

  if (loading) {
    return <div className="loading-state"><div className="spinner" /><span>Loading session…</span></div>;
  }

  const useBarChart = timeline.length <= 3;

  return (
    <>
      <div className="page-header flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/sessions" className="btn btn-ghost" style={{ padding: '8px 12px' }}>
            <ArrowLeft size={16} />
          </Link>
          <div>
            <h1 className="page-title">Session #{id}</h1>
            <p className="page-subtitle">Detailed per-student breakdown</p>
          </div>
        </div>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div className="stats-grid">
          {[
            { label: 'Class Grade', value: overview.class_grade, color: GRADE_COLOR[overview.class_grade], sub: 'Overall performance' },
            { label: 'Avg Score', value: `${(overview.class_avg_score * 100).toFixed(0)}%`, color: '#818cf8', sub: 'Attention score' },
            { label: 'Total Students', value: overview.total_students, color: '#f1f5f9', sub: 'Tracked in session' },
            { label: 'Attentive', value: `${overview.attentive_pct?.toFixed(0)}%`, color: '#22c55e', sub: `${overview.attentive_count} students` },
            { label: 'Partial', value: `${overview.partially_attentive_pct?.toFixed(0)}%`, color: '#facc15', sub: `${overview.partially_attentive_count} students` },
            { label: 'Distracted', value: `${overview.distracted_pct?.toFixed(0)}%`, color: '#ef4444', sub: `${overview.distracted_count} students` },
            { label: 'Phone Detected', value: overview.phone_detected_count, color: '#fb923c', sub: 'Students using phone' },
          ].map(({ label, value, color, sub }) => (
            <div key={label} className="stat-card">
              <div className="stat-label">{label}</div>
              <div className="stat-value" style={{ color }}>{value}</div>
              <div className="stat-sub">{sub}</div>
            </div>
          ))}
        </div>
      )}

      {/* Distraction Timeline Chart */}
      {timeline.length > 0 && (
        <div className="card timeline-card">
          <div className="card-title"><Clock size={14} /> Attention Timeline</div>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
            Attention levels across {timeline.length} segments during the session
          </p>
          <ResponsiveContainer width="100%" height={280}>
            {useBarChart ? (
              <BarChart data={timeline} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                <Tooltip content={<TimelineTooltip />} />
                <ReferenceLine y={70} stroke="#22c55e" strokeDasharray="4 4" opacity={0.4} />
                <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="4 4" opacity={0.4} />
                <Bar dataKey="attention_pct" radius={[6, 6, 0, 0]} name="Attention %">
                  {timeline.map((entry, idx) => (
                    <Cell key={idx} fill={getBarColor(entry.attention_pct)} fillOpacity={0.8} />
                  ))}
                </Bar>
                <Bar dataKey="distraction_pct" fill="#ef4444" fillOpacity={0.5} radius={[6, 6, 0, 0]} name="Distraction %" />
              </BarChart>
            ) : (
              <AreaChart data={timeline} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                <Tooltip content={<TimelineTooltip />} />
                <ReferenceLine y={70} stroke="#22c55e" strokeDasharray="4 4" opacity={0.4} />
                <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="4 4" opacity={0.4} />
                <Area type="monotone" dataKey="attention_pct" stroke="#22c55e" strokeWidth={2}
                  fill="url(#greenGrad)" name="Attention %" />
                <Area type="monotone" dataKey="distraction_pct" stroke="#ef4444" strokeWidth={2}
                  fill="url(#redGrad)" name="Distraction %" />
              </AreaChart>
            )}
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 12, color: '#64748b' }}>
            <div className="flex items-center gap-2">
              <div style={{ width: 20, height: 3, background: '#22c55e', borderRadius: 2 }} /> Attention %
            </div>
            <div className="flex items-center gap-2">
              <div style={{ width: 20, height: 3, background: '#ef4444', borderRadius: 2 }} /> Distraction %
            </div>
          </div>
        </div>
      )}

      {/* Teacher Feedback Card */}
      <div className="card feedback-card">
        <div className="card-title flex items-center justify-between" style={{ marginBottom: 0 }}>
          <div className="flex items-center gap-2">
            <MessageSquare size={14} /> Teacher Feedback Report
          </div>
          <div className="flex items-center gap-2">
            {feedback && (
              <>
                <button className="btn btn-ghost" onClick={() => downloadSessionPdf(id)}
                  style={{ fontSize: 12, padding: '6px 14px' }}>
                  <Download size={13} /> Download PDF
                </button>
                <button className="btn btn-ghost" onClick={() => { setShowSendEmail(!showSendEmail); setEmailSent(false); }}
                  style={{ fontSize: 12, padding: '6px 14px' }}>
                  <Mail size={13} /> Email Report
                </button>
              </>
            )}
            {!feedback && (
              <button className="btn btn-primary" onClick={() => setShowGenEmail(true)}
                disabled={genLoading} style={{ fontSize: 12, padding: '6px 14px' }}>
                <FileText size={13} />
                {genLoading ? 'Generating…' : 'Generate Report'}
              </button>
            )}
          </div>
        </div>

        {/* Generate with email option */}
        {showGenEmail && !feedback && (
          <div style={{ marginTop: 16, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input className="input" placeholder="Teacher email (optional)"
              value={emailInput} onChange={e => setEmailInput(e.target.value)}
              style={{ flex: 1, maxWidth: 300, padding: '8px 12px', fontSize: 13 }} />
            <button className="btn btn-primary" onClick={handleGenerate}
              disabled={genLoading} style={{ fontSize: 12, padding: '8px 16px' }}>
              <Send size={13} />
              {genLoading ? 'Generating…' : emailInput ? 'Generate & Email' : 'Generate'}
            </button>
            <button className="btn btn-ghost" onClick={() => setShowGenEmail(false)}
              style={{ fontSize: 12, padding: '8px 12px' }}>Cancel</button>
          </div>
        )}

        {/* Send email for existing feedback */}
        {showSendEmail && feedback && (
          <div style={{ marginTop: 16, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input className="input" placeholder="Enter teacher's email address"
              value={emailInput} onChange={e => setEmailInput(e.target.value)}
              style={{ flex: 1, maxWidth: 340, padding: '8px 12px', fontSize: 13 }}
              onKeyDown={e => e.key === 'Enter' && handleSendEmail()} />
            <button className="btn btn-primary" onClick={handleSendEmail}
              disabled={emailSending || !emailInput.trim()} style={{ fontSize: 12, padding: '8px 16px' }}>
              <Send size={13} />
              {emailSending ? 'Sending…' : 'Send Email'}
            </button>
            <button className="btn btn-ghost" onClick={() => { setShowSendEmail(false); setEmailError(''); }}
              style={{ fontSize: 12, padding: '8px 12px' }}>Cancel</button>
          </div>
        )}
        
        {emailError && (
          <div style={{ marginTop: 10, fontSize: 13, color: '#ef4444' }} className="flex items-center gap-2">
            <AlertTriangle size={13} /> {emailError}
          </div>
        )}

        {emailSent && (
          <div style={{ marginTop: 10, fontSize: 13, color: '#22c55e' }} className="flex items-center gap-2">
            <Mail size={13} /> ✓ Report sent to {emailInput}
          </div>
        )}

        {/* Feedback Content */}
        {feedback ? (
          <div style={{ marginTop: 20 }}>
            <div className="feedback-summary">
              {feedback.overall_summary.split('\n').map((line, i) => (
                <div key={i} style={{
                  color: line.includes('⚠️') ? '#fb923c' : line.startsWith('  •') ? '#94a3b8' : '#cbd5e1',
                  fontWeight: line.includes('Session:') || line.includes('⚠️') ? 600 : 400,
                  fontSize: line.includes('Session:') ? 15 : 13,
                  marginTop: line === '' ? 8 : 2,
                  paddingLeft: line.startsWith('  •') ? 8 : 0,
                }}>{line || '\u00A0'}</div>
              ))}
            </div>

            {feedback.peak_distraction_periods?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ef4444', textTransform: 'uppercase',
                  letterSpacing: '0.06em', marginBottom: 8 }}>
                  <AlertTriangle size={12} style={{ display: 'inline', verticalAlign: -2 }} /> Peak Distraction Windows
                </div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {feedback.peak_distraction_periods.map((p, i) => (
                    <div key={i} className="distraction-badge">
                      <span style={{ fontWeight: 600 }}>{p.start} – {p.end}</span>
                      <span style={{ color: '#ef4444' }}>{p.distraction_pct}%</span>
                      {p.phone_count > 0 && <span style={{ color: '#fb923c' }}>📱 {p.phone_count}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {feedback.recommendations && (
              <div style={{ marginTop: 16, padding: '14px 16px', background: 'rgba(34,197,94,0.06)',
                borderRadius: 12, border: '1px solid rgba(34,197,94,0.15)' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#22c55e', textTransform: 'uppercase',
                  letterSpacing: '0.06em', marginBottom: 8 }}>💡 Recommendations</div>
                {feedback.recommendations.split('\n').map((line, i) => (
                  <div key={i} style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>{line}</div>
                ))}
              </div>
            )}
          </div>
        ) : !showGenEmail && (
          <div className="empty-state" style={{ padding: 40 }}>
            <div className="empty-icon" style={{ fontSize: 36 }}>📋</div>
            <p>Click "Generate Report" to analyze this session</p>
          </div>
        )}
      </div>

      {/* Student Table */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
          <div className="flex items-center justify-between">
            <div className="card-title" style={{ marginBottom: 0 }}><Users size={14} /> Per-Student Results</div>
            <input className="input" style={{ maxWidth: 240, padding: '7px 12px', fontSize: 13 }}
              placeholder="Search name / USN…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
        </div>
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">👤</div>
            <h3>No Student Data</h3>
            <p>Summary will appear after the session ends.</p>
          </div>
        ) : (
          <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleSort('student_name')}>Student <SortIcon col="student_name" /></th>
                  <th>USN</th>
                  <th onClick={() => handleSort('avg_score')}>Score <SortIcon col="avg_score" /></th>
                  <th onClick={() => handleSort('grade')}>Grade <SortIcon col="grade" /></th>
                  <th onClick={() => handleSort('attentive_pct')}>Attentive <SortIcon col="attentive_pct" /></th>
                  <th onClick={() => handleSort('distracted_pct')}>Distracted <SortIcon col="distracted_pct" /></th>
                  <th onClick={() => handleSort('phone_frames')}>Phone <SortIcon col="phone_frames" /></th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(s => (
                  <tr key={s.id} className={getRowClass(s.grade)}>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="avatar" style={{ width: 30, height: 30, fontSize: 12, borderRadius: 8 }}>
                          {(s.student_name || '?')[0].toUpperCase()}
                        </div>
                        <span style={{ color: '#f1f5f9', fontWeight: 500 }}>
                          {s.student_name || `Student #${s.student_id}`}
                        </span>
                      </div>
                    </td>
                    <td><span style={{ fontSize: 12, color: '#64748b', fontFamily: 'monospace' }}>
                      {s.student_usn || '—'}</span></td>
                    <td><ScoreBar value={s.avg_score} /></td>
                    <td><span className={`grade-badge grade-${s.grade}`}>{s.grade}</span></td>
                    <td><span style={{ color: '#22c55e', fontWeight: 600 }}>{s.attentive_pct?.toFixed(1)}%</span></td>
                    <td><span style={{ color: '#ef4444', fontWeight: 600 }}>{s.distracted_pct?.toFixed(1)}%</span></td>
                    <td>{s.phone_frames > 0
                      ? <span className="chip chip-orange"><Smartphone size={10} /> {s.phone_frames}</span>
                      : <span style={{ color: '#475569' }}>0</span>}</td>
                    <td>{s.student_id && (
                      <Link to={`/students/${s.student_id}`} className="btn btn-ghost"
                        style={{ padding: '5px 10px', fontSize: 12 }}>Profile</Link>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
