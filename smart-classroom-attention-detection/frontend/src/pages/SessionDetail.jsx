import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Users, TrendingUp, AlertTriangle, Smartphone, ChevronUp, ChevronDown } from 'lucide-react';
import { getSessionOverview, getSessionSummary } from '../api';

const GRADE_COLOR = { A: '#22c55e', B: '#86efac', C: '#facc15', D: '#fb923c', F: '#ef4444' };

function getRowClass(grade) {
  if (['A', 'B'].includes(grade)) return 'row-green';
  if (grade === 'C') return 'row-yellow';
  return 'row-red';
}

function ScoreBar({ value }) {
  const pct = (value * 100).toFixed(0);
  const color =
    value >= 0.85 ? '#22c55e' :
    value >= 0.70 ? '#86efac' :
    value >= 0.55 ? '#facc15' :
    value >= 0.40 ? '#fb923c' : '#ef4444';
  return (
    <div>
      <span style={{ fontSize: 13, fontWeight: 600, color }}>{pct}%</span>
      <div className="score-bar" style={{ marginTop: 4, width: 80 }}>
        <div className="score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export default function SessionDetail() {
  const { id } = useParams();
  const [overview, setOverview] = useState(null);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('avg_score');
  const [sortDir, setSortDir] = useState('desc');
  const [search, setSearch] = useState('');

  useEffect(() => {
    Promise.all([
      getSessionOverview(id),
      getSessionSummary(id)
    ]).then(([ov, sm]) => {
      setOverview(ov);
      setSummary(sm);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

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
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span>Loading session data…</span>
      </div>
    );
  }

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
          <div className="stat-card">
            <div className="stat-label">Class Grade</div>
            <div className="stat-value" style={{ color: GRADE_COLOR[overview.class_grade] }}>
              {overview.class_grade}
            </div>
            <div className="stat-sub">Overall performance</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg Score</div>
            <div className="stat-value" style={{ color: '#818cf8' }}>
              {(overview.class_avg_score * 100).toFixed(0)}%
            </div>
            <div className="stat-sub">Attention score</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Students</div>
            <div className="stat-value">{overview.total_students}</div>
            <div className="stat-sub">Tracked in session</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Attentive</div>
            <div className="stat-value" style={{ color: '#22c55e' }}>
              {overview.attentive_pct?.toFixed(0)}%
            </div>
            <div className="stat-sub">{overview.attentive_count} students</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Distracted</div>
            <div className="stat-value" style={{ color: '#ef4444' }}>
              {overview.distracted_pct?.toFixed(0)}%
            </div>
            <div className="stat-sub">{overview.distracted_count} students</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Phone Detected</div>
            <div className="stat-value" style={{ color: '#fb923c' }}>
              {overview.phone_detected_count}
            </div>
            <div className="stat-sub">Students using phone</div>
          </div>
        </div>
      )}

      {/* Student Table */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
          <div className="flex items-center justify-between">
            <div className="card-title" style={{ marginBottom: 0 }}>
              <Users size={14} /> Per-Student Results
            </div>
            <input
              className="input"
              style={{ maxWidth: 240, padding: '7px 12px', fontSize: 13 }}
              placeholder="Search name / USN…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">👤</div>
            <h3>No Student Data</h3>
            <p>Session summary will appear after the session ends.</p>
          </div>
        ) : (
          <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleSort('student_name')}>
                    Student <SortIcon col="student_name" />
                  </th>
                  <th>USN</th>
                  <th onClick={() => handleSort('avg_score')}>
                    Avg Score <SortIcon col="avg_score" />
                  </th>
                  <th onClick={() => handleSort('grade')}>
                    Grade <SortIcon col="grade" />
                  </th>
                  <th onClick={() => handleSort('attentive_pct')}>
                    Attentive % <SortIcon col="attentive_pct" />
                  </th>
                  <th onClick={() => handleSort('distracted_pct')}>
                    Distracted % <SortIcon col="distracted_pct" />
                  </th>
                  <th onClick={() => handleSort('phone_frames')}>
                    Phone Frames <SortIcon col="phone_frames" />
                  </th>
                  <th>Frames</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
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
                    <td>
                      <span style={{ fontSize: 12, color: '#64748b', fontFamily: 'monospace' }}>
                        {s.student_usn || '—'}
                      </span>
                    </td>
                    <td><ScoreBar value={s.avg_score} /></td>
                    <td>
                      <span className={`grade-badge grade-${s.grade}`}>{s.grade}</span>
                    </td>
                    <td>
                      <span style={{ color: '#22c55e', fontWeight: 600 }}>
                        {s.attentive_pct?.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span style={{ color: '#ef4444', fontWeight: 600 }}>
                        {s.distracted_pct?.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      {s.phone_frames > 0 ? (
                        <span className="chip chip-orange">
                          <Smartphone size={10} /> {s.phone_frames}
                        </span>
                      ) : (
                        <span style={{ color: '#475569' }}>0</span>
                      )}
                    </td>
                    <td style={{ color: '#64748b' }}>{s.total_frames}</td>
                    <td>
                      {s.student_id && (
                        <Link
                          to={`/students/${s.student_id}`}
                          className="btn btn-ghost"
                          style={{ padding: '5px 10px', fontSize: 12 }}
                        >
                          Profile
                        </Link>
                      )}
                    </td>
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
