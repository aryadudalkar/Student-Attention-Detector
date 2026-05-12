import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ChevronRight, Pencil, X, Check } from 'lucide-react';
import { getStudents, updateStudent } from '../api';

export default function StudentsList() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editStudent, setEditStudent] = useState(null);
  const [editName, setEditName] = useState('');
  const [editUsn, setEditUsn] = useState('');
  const [saving, setSaving] = useState(false);

  const loadStudents = () => {
    getStudents()
      .then(setStudents)
      .catch(() => setStudents([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadStudents(); }, []);

  const filtered = students.filter(s => {
    const q = search.toLowerCase();
    return (
      (s.name || '').toLowerCase().includes(q) ||
      (s.usn || '').toLowerCase().includes(q) ||
      String(s.student_id || s.id || '').includes(q)
    );
  });

  const openEdit = (student, e) => {
    e.preventDefault();
    e.stopPropagation();
    setEditStudent(student);
    setEditName(student.name || '');
    setEditUsn(student.usn || '');
  };

  const handleSave = async () => {
    if (!editStudent) return;
    setSaving(true);
    try {
      await updateStudent(editStudent.student_id ?? editStudent.id, {
        name: editName,
        usn: editUsn,
      });
      loadStudents();
      setEditStudent(null);
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  const getInitials = (name, id) => {
    if (name) return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
    return `S${id}`;
  };

  const AVATAR_COLORS = [
    ['#6366f1', '#8b5cf6'], ['#06b6d4', '#3b82f6'], ['#10b981', '#059669'],
    ['#f59e0b', '#d97706'], ['#ec4899', '#db2777'], ['#8b5cf6', '#7c3aed'],
  ];

  const getAvatarGradient = (id) => {
    const [a, b] = AVATAR_COLORS[(id || 0) % AVATAR_COLORS.length];
    return `linear-gradient(135deg, ${a}, ${b})`;
  };

  if (loading) {
    return <div className="loading-state"><div className="spinner" /><span>Loading students…</span></div>;
  }

  return (
    <>
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">Students</h1>
          <p className="page-subtitle">{students.length} registered student{students.length !== 1 ? 's' : ''}</p>
        </div>
      </div>

      <div className="filter-bar">
        <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
          <Search size={15} style={{
            position: 'absolute', left: 12, top: '50%',
            transform: 'translateY(-50%)', color: '#475569', pointerEvents: 'none'
          }} />
          <input className="input" style={{ width: '100%', paddingLeft: 36 }}
            placeholder="Search by name, USN, or ID…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <span style={{ fontSize: 13, color: '#475569' }}>
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">👥</div>
            <h3>{search ? 'No Students Found' : 'No Students Enrolled'}</h3>
            <p>{search ? 'Try a different search term.' : 'Students are enrolled via the enrollment_cli.py script.'}</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
          {filtered.map(student => {
            const sid = student.student_id ?? student.id;
            const initials = getInitials(student.name, sid);
            return (
              <Link key={sid} to={`/students/${sid}`} style={{ textDecoration: 'none' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 14, padding: '16px 18px',
                  borderRadius: 14, border: '1px solid rgba(99,102,241,0.12)',
                  background: 'rgba(15,23,42,0.8)', backdropFilter: 'blur(20px)',
                  transition: 'all 0.25s ease', cursor: 'pointer', position: 'relative', overflow: 'hidden',
                }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'rgba(99,102,241,0.35)';
                    e.currentTarget.style.transform = 'translateY(-3px)';
                    e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.25)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'rgba(99,102,241,0.12)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                    background: getAvatarGradient(sid), opacity: 0.6, borderRadius: '14px 14px 0 0'
                  }} />

                  <div style={{
                    width: 48, height: 48, borderRadius: 14, flexShrink: 0,
                    background: getAvatarGradient(sid),
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 16, fontWeight: 700, color: 'white', boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                  }}>{initials}</div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 15, fontWeight: 600, color: '#f1f5f9',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                    }}>{student.name || `Student #${sid}`}</div>
                    <div style={{ marginTop: 4, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {student.usn ? (
                        <span style={{
                          fontSize: 11, color: '#818cf8', fontFamily: 'monospace',
                          background: 'rgba(99,102,241,0.1)', padding: '2px 8px',
                          borderRadius: 6, border: '1px solid rgba(99,102,241,0.2)'
                        }}>{student.usn}</span>
                      ) : (
                        <span style={{ fontSize: 11, color: '#475569' }}>No USN assigned</span>
                      )}
                      <span style={{ fontSize: 11, color: '#475569' }}>ID #{sid}</span>
                    </div>
                  </div>

                  <button onClick={(e) => openEdit(student, e)}
                    style={{
                      background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)',
                      borderRadius: 8, padding: 6, cursor: 'pointer', color: '#818cf8',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}
                    title="Edit student">
                    <Pencil size={14} />
                  </button>

                  <ChevronRight size={16} color="#475569" style={{ flexShrink: 0 }} />
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Edit Modal */}
      {editStudent && (
        <div className="modal-overlay" onClick={() => setEditStudent(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between" style={{ marginBottom: 20 }}>
              <h3 className="modal-title" style={{ margin: 0 }}>Edit Student</h3>
              <button onClick={() => setEditStudent(null)}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            <div className="input-group" style={{ marginBottom: 16 }}>
              <label className="input-label">Student Name</label>
              <input className="input" value={editName} onChange={e => setEditName(e.target.value)}
                placeholder="Enter student name" />
            </div>

            <div className="input-group" style={{ marginBottom: 16 }}>
              <label className="input-label">USN (University Serial Number)</label>
              <input className="input" value={editUsn} onChange={e => setEditUsn(e.target.value)}
                placeholder="e.g., 1RV22CS001" />
            </div>

            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setEditStudent(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                <Check size={14} />
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
