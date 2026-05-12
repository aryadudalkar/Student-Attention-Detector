import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { LayoutDashboard, History, Users, Eye, WifiOff, MessageSquare } from 'lucide-react';
import { getActiveSession } from './api';
import DashboardHome from './pages/DashboardHome';
import SessionHistory from './pages/SessionHistory';
import SessionDetail from './pages/SessionDetail';
import StudentsList from './pages/StudentsList';
import StudentProfile from './pages/StudentProfile';
import TeacherFeedback from './pages/TeacherFeedback';
import './index.css';

function Sidebar({ isLive, sessionLabel }) {
  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/sessions', icon: History, label: 'Session History' },
    { to: '/students', icon: Users, label: 'Students' },
    { to: '/feedback', icon: MessageSquare, label: 'Teacher Feedback' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Eye size={20} color="white" />
        </div>
        <div className="sidebar-logo-text">
          <h2>SmartClass AI</h2>
          <span>Attention Monitor</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <span className="sidebar-section-label">Navigation</span>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Icon className="nav-icon" size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        {isLive ? (
          <div className="live-badge">
            <div className="live-dot" />
            <div>
              <div style={{ fontWeight: 600 }}>Live Session</div>
              <div style={{ fontSize: 11, opacity: 0.8, marginTop: 2 }}>{sessionLabel || 'Active'}</div>
            </div>
          </div>
        ) : (
          <div className="idle-badge">
            <WifiOff size={14} />
            <span>No Active Session</span>
          </div>
        )}
      </div>
    </aside>
  );
}

function AppLayout() {
  const [isLive, setIsLive] = useState(false);
  const [sessionLabel, setSessionLabel] = useState('');

  useEffect(() => {
    const check = async () => {
      try {
        const data = await getActiveSession();
        setIsLive(data.active);
        setSessionLabel(data.session?.label || '');
      } catch { setIsLive(false); }
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-layout">
      <Sidebar isLive={isLive} sessionLabel={sessionLabel} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="/sessions" element={<SessionHistory />} />
          <Route path="/sessions/:id" element={<SessionDetail />} />
          <Route path="/students" element={<StudentsList />} />
          <Route path="/students/:id" element={<StudentProfile />} />
          <Route path="/feedback" element={<TeacherFeedback />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
