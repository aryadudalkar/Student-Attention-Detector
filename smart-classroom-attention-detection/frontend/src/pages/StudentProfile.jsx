import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts';
import { ArrowLeft, Smartphone, BookOpen, TrendingUp, Award, Calendar, Activity } from 'lucide-react';
import { getStudent, getStudentWeeklyReport } from '../api';

const GRADE_COLOR = { A: '#22c55e', B: '#86efac', C: '#facc15', D: '#fb923c', F: '#ef4444' };

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{
        background: '#0f172a', border: '1px solid rgba(99,102,241,0.2)',
        borderRadius: 10, padding: '10px 14px', fontSize: 13
      }}>
        <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
        <div style={{ color: '#818cf8', fontWeight: 600 }}>
          {(payload[0].value * 100).toFixed(0)}% attention
        </div>
      </div>
    );
  }
  return null;
};

function StatBlock({ label, value, sub, color = '#818cf8', icon: Icon }) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
        <div className="stat-label">{label}</div>
        {Icon && (
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: `${color}18`, border: `1px solid ${color}30`,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Icon size={14} color={color} />
          </div>
        )}
      </div>
      <div className="stat-value" style={{ fontSize: 26, color }}>{value ?? '—'}</div>
      {sub && <div className="stat-sub" style={{ marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function StudentProfile() {
  const { id } = useParams();
  const [student, setStudent] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getStudent(id),
      getStudentWeeklyReport(id)
    ]).then(([s, r]) => {
      setStudent(s);
      setReport(r);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span>Loading student profile…</span>
      </div>
    );
  }

  if (!student) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-icon">❓</div>
          <h3>Student Not Found</h3>
          <p>This student may not be enrolled yet.</p>
        </div>
      </div>
    );
  }

  const initials = (student.name || `S${id}`)
    .split(' ')
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  // Build mock trend data from weekly report if available
  // Since API returns aggregated data, show as a single reference point
  const trendData = report ? [
    { session: 'Weekly Avg', score: report.weekly_avg_score }
  ] : [];

  const grade = report?.grade;
  const gradeColor = GRADE_COLOR[grade] || '#818cf8';

  return (
    <>
      <div className="page-header flex items-center gap-3">
        <Link to="/students" className="btn btn-ghost" style={{ padding: '8px 12px' }}>
          <ArrowLeft size={16} />
        </Link>
        <div>
          <h1 className="page-title">Student Profile</h1>
          <p className="page-subtitle">Individual attention analytics</p>
        </div>
      </div>

      {/* Profile Header */}
      <div className="profile-header">
        <div className="profile-avatar">{initials}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9' }}>
            {student.name || `Student #${id}`}
          </div>
          <div style={{ marginTop: 6, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {student.usn && (
              <span className="chip chip-blue">
                🎓 {student.usn}
              </span>
            )}
            {student.registered_at && (
              <span className="chip chip-gray">
                <Calendar size={10} />
                Registered {new Date(student.registered_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        {grade && (
          <div style={{ textAlign: 'center', padding: '12px 24px' }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: gradeColor, lineHeight: 1 }}>
              {grade}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Weekly Grade
            </div>
          </div>
        )}
      </div>

      {report ? (
        <>
          {/* Stats Grid */}
          <div className="stats-grid">
            <StatBlock
              label="Weekly Avg Score"
              value={`${(report.weekly_avg_score * 100).toFixed(0)}%`}
              sub="Average attention this week"
              color={gradeColor}
              icon={TrendingUp}
            />
            <StatBlock
              label="Sessions Attended"
              value={report.sessions_recorded}
              sub="This week"
              color="#818cf8"
              icon={Calendar}
            />
            <StatBlock
              label="Attentive"
              value={`${report.avg_attentive_pct?.toFixed(1)}%`}
              sub="Average attentive time"
              color="#22c55e"
              icon={Activity}
            />
            <StatBlock
              label="Distracted"
              value={`${report.avg_distracted_pct?.toFixed(1)}%`}
              sub="Average distracted time"
              color="#ef4444"
              icon={Activity}
            />
            <StatBlock
              label="Phone Usage"
              value={report.total_phone_frames}
              sub="Total frames with phone"
              color="#fb923c"
              icon={Smartphone}
            />
            <StatBlock
              label="Reading Frames"
              value={report.total_reading_frames}
              sub="Total frames reading"
              color="#60a5fa"
              icon={BookOpen}
            />
          </div>

          {/* Attention gauge */}
          <div className="grid-2" style={{ alignItems: 'stretch' }}>
            <div className="card">
              <div className="card-title"><Award size={14} /> Performance Summary</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 8 }}>
                {[
                  { label: 'Attentive Time', value: report.avg_attentive_pct, color: '#22c55e' },
                  { label: 'Distracted Time', value: report.avg_distracted_pct, color: '#ef4444' },
                  {
                    label: 'Other (Partial / Reading)',
                    value: Math.max(0, 100 - report.avg_attentive_pct - report.avg_distracted_pct),
                    color: '#facc15'
                  },
                ].map(({ label, value, color }) => (
                  <div key={label}>
                    <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                      <span style={{ fontSize: 13, color: '#94a3b8' }}>{label}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color }}>
                        {value?.toFixed(1)}%
                      </span>
                    </div>
                    <div className="score-bar">
                      <div
                        className="score-fill"
                        style={{ width: `${value || 0}%`, background: color }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div style={{
                marginTop: 24, padding: '14px 16px',
                background: `${gradeColor}0d`, borderRadius: 10,
                border: `1px solid ${gradeColor}25`,
                display: 'flex', alignItems: 'center', gap: 12
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: `${gradeColor}20`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, fontWeight: 800, color: gradeColor
                }}>
                  {grade}
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: gradeColor, fontSize: 14 }}>
                    {grade === 'A' ? 'Excellent Attention' :
                     grade === 'B' ? 'Good Attention' :
                     grade === 'C' ? 'Average Attention' :
                     grade === 'D' ? 'Below Average' : 'Needs Improvement'}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                    Based on {report.sessions_recorded} session{report.sessions_recorded !== 1 ? 's' : ''}
                    — {report.total_frames?.toLocaleString()} frames observed
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-title"><TrendingUp size={14} /> Attention Trend</div>
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={trendData} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                    <XAxis dataKey="session" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={0.7} stroke="#22c55e" strokeDasharray="4 4" opacity={0.5} />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#6366f1"
                      strokeWidth={2.5}
                      dot={{ fill: '#6366f1', r: 5 }}
                      activeDot={{ r: 7, fill: '#818cf8' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state" style={{ padding: 40 }}>
                  <div className="empty-icon" style={{ fontSize: 36 }}>📈</div>
                  <p>Trend data will appear after multiple sessions</p>
                </div>
              )}
              <div style={{
                marginTop: 12, fontSize: 12, color: '#475569',
                display: 'flex', alignItems: 'center', gap: 6
              }}>
                <div style={{
                  width: 24, height: 2, background: '#22c55e',
                  borderTop: '1px dashed #22c55e'
                }} />
                70% threshold (Good performance)
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">📊</div>
            <h3>No Weekly Report Yet</h3>
            <p>This student needs at least one completed session to generate a report.</p>
          </div>
        </div>
      )}
    </>
  );
}
