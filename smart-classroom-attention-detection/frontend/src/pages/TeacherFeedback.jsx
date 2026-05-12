import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageSquare, Calendar, Clock, ChevronRight, AlertTriangle, TrendingUp, Mail, Send } from 'lucide-react';
import { listFeedbacks, sendFeedbackEmail } from '../api';

const GRADE_COLOR = { A: '#22c55e', B: '#86efac', C: '#facc15', D: '#fb923c', F: '#ef4444' };

function scoreToGrade(s) {
  if (s >= 0.85) return 'A';
  if (s >= 0.70) return 'B';
  if (s >= 0.55) return 'C';
  if (s >= 0.40) return 'D';
  return 'F';
}

function formatDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString([], { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
}

function formatTime(dt) {
  if (!dt) return '';
  return new Date(dt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function TeacherFeedbackPage() {
  const [feedbacks, setFeedbacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [emailFor, setEmailFor] = useState(null);
  const [emailInput, setEmailInput] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailSent, setEmailSent] = useState(null);

  const handleSendEmail = async (sessionId) => {
    if (!emailInput.trim()) return;
    setEmailSending(true);
    try {
      await sendFeedbackEmail(sessionId, emailInput.trim());
      setEmailSent(sessionId);
      setEmailFor(null);
    } catch (e) { console.error(e); }
    finally { setEmailSending(false); }
  };

  useEffect(() => {
    listFeedbacks()
      .then(setFeedbacks)
      .catch(() => setFeedbacks([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span>Loading feedback reports…</span>
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Teacher Feedback</h1>
        <p className="page-subtitle">
          {feedbacks.length} report{feedbacks.length !== 1 ? 's' : ''} generated — Auto-generated when sessions end
        </p>
      </div>

      {feedbacks.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No Feedback Reports Yet</h3>
            <p>Feedback reports are automatically generated when a session ends.<br />
              You can also generate them manually from any session's detail page.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {feedbacks.map(fb => {
            const grade = scoreToGrade(fb.avg_attention_score);
            const isExpanded = expanded === fb.id;
            const scorePct = (fb.avg_attention_score * 100).toFixed(0);
            const hasPeaks = fb.peak_distraction_periods?.length > 0;

            return (
              <div key={fb.id} className="card feedback-list-card" style={{ padding: 0, cursor: 'pointer' }}
                onClick={() => setExpanded(isExpanded ? null : fb.id)}>
                {/* Header */}
                <div style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: 14, flexShrink: 0,
                    background: `${GRADE_COLOR[grade]}15`, border: `1px solid ${GRADE_COLOR[grade]}30`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20, fontWeight: 800, color: GRADE_COLOR[grade]
                  }}>
                    {grade}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#f1f5f9' }}>
                      {fb.session_label || `Session #${fb.session}`}
                    </div>
                    <div className="flex items-center gap-3 mt-1" style={{ flexWrap: 'wrap' }}>
                      <span className="flex items-center gap-2 text-sm text-muted">
                        <Calendar size={12} /> {formatDate(fb.session_started_at)}
                      </span>
                      <span className="flex items-center gap-2 text-sm text-muted">
                        <Clock size={12} /> {formatTime(fb.session_started_at)}
                      </span>
                      <span className="flex items-center gap-2 text-sm" style={{ color: GRADE_COLOR[grade] }}>
                        <TrendingUp size={12} /> {scorePct}% attention
                      </span>
                      {hasPeaks && (
                        <span className="chip chip-red" style={{ fontSize: 11 }}>
                          <AlertTriangle size={10} /> {fb.peak_distraction_periods.length} peak{fb.peak_distraction_periods.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="chip chip-gray">{fb.total_students_tracked} students</span>
                    <Link to={`/sessions/${fb.session}`} className="btn btn-ghost"
                      style={{ padding: '6px 12px', fontSize: 12 }}
                      onClick={e => e.stopPropagation()}>
                      View Session <ChevronRight size={14} />
                    </Link>
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div style={{ padding: '0 20px 20px', borderTop: '1px solid rgba(99,102,241,0.1)' }}>
                    <div style={{ marginTop: 16 }}>
                      <div className="feedback-summary">
                        {fb.overall_summary.split('\n').map((line, i) => (
                          <div key={i} style={{
                            color: line.includes('⚠️') ? '#fb923c' : line.includes('•') ? '#94a3b8' : '#cbd5e1',
                            fontWeight: line.includes('Session:') || line.includes('⚠️') ? 600 : 400,
                            fontSize: 13, marginTop: line === '' ? 8 : 2,
                            paddingLeft: line.includes('•') ? 8 : 0,
                          }}>
                            {line || '\u00A0'}
                          </div>
                        ))}
                      </div>

                      {hasPeaks && (
                        <div style={{ marginTop: 14 }}>
                          <div style={{ fontSize: 11, fontWeight: 600, color: '#ef4444', textTransform: 'uppercase',
                            letterSpacing: '0.06em', marginBottom: 6 }}>Distraction Peaks</div>
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            {fb.peak_distraction_periods.map((p, i) => (
                              <div key={i} className="distraction-badge">
                                <span style={{ fontWeight: 600 }}>{p.start}–{p.end}</span>
                                <span style={{ color: '#ef4444' }}>{p.distraction_pct}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(34,197,94,0.06)',
                        borderRadius: 10, border: '1px solid rgba(34,197,94,0.12)' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: '#22c55e', textTransform: 'uppercase',
                          letterSpacing: '0.06em', marginBottom: 6 }}>Recommendations</div>
                        {fb.recommendations.split('\n').map((line, i) => (
                          <div key={i} style={{ fontSize: 13, color: '#94a3b8', marginTop: 3 }}>{line}</div>
                        ))}
                      </div>

                      {/* Email Send Section */}
                      <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                        {emailFor === fb.id ? (
                          <>
                            <input className="input" placeholder="Enter teacher's email"
                              value={emailInput} onChange={e => setEmailInput(e.target.value)}
                              onClick={e => e.stopPropagation()}
                              onKeyDown={e => { if (e.key === 'Enter') handleSendEmail(fb.session); }}
                              style={{ flex: 1, maxWidth: 280, padding: '7px 12px', fontSize: 13 }} />
                            <button className="btn btn-primary" onClick={e => { e.stopPropagation(); handleSendEmail(fb.session); }}
                              disabled={emailSending || !emailInput.trim()}
                              style={{ fontSize: 12, padding: '7px 14px' }}>
                              <Send size={12} /> {emailSending ? 'Sending…' : 'Send'}
                            </button>
                            <button className="btn btn-ghost" onClick={e => { e.stopPropagation(); setEmailFor(null); }}
                              style={{ fontSize: 12, padding: '7px 10px' }}>Cancel</button>
                          </>
                        ) : (
                          <button className="btn btn-ghost" onClick={e => {
                            e.stopPropagation(); setEmailFor(fb.id); setEmailInput(''); setEmailSent(null);
                          }} style={{ fontSize: 12, padding: '7px 14px' }}>
                            <Mail size={12} /> Email to Teacher
                          </button>
                        )}
                        {emailSent === fb.session && (
                          <span style={{ fontSize: 12, color: '#22c55e' }}>✓ Sent!</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
