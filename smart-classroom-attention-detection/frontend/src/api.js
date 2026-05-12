const BASE_URL = 'http://127.0.0.1:8000/api';

async function apiFetch(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }
  return response.json();
}

// Sessions
export const getSessions = () => apiFetch('/sessions/');
export const getActiveSession = () => apiFetch('/sessions/active/');
export const getSessionDetail = (id) => apiFetch(`/sessions/${id}/`);
export const getSessionOverview = (id) => apiFetch(`/sessions/${id}/overview/`);
export const getSessionSummary = (id) => apiFetch(`/sessions/${id}/summary/`);
export const getSessionLogs = (id) => apiFetch(`/sessions/${id}/logs/`);
export const getSessionTimeline = (id) => apiFetch(`/sessions/${id}/timeline/`);
export const startSession = (label) =>
  apiFetch('/sessions/start/', { method: 'POST', body: JSON.stringify({ label }) });
export const endSession = (id) =>
  apiFetch(`/sessions/${id}/end/`, { method: 'POST' });

// Teacher Feedback
export const getTeacherFeedback = (id) => apiFetch(`/sessions/${id}/feedback/`);
export const generateTeacherFeedback = (id, email = '') =>
  apiFetch(`/sessions/${id}/feedback/generate/`, {
    method: 'POST',
    body: JSON.stringify({ send_email: !!email, email }),
  });
export const listFeedbacks = () => apiFetch('/feedbacks/');

// Students
export const getStudents = (search = '') =>
  apiFetch(`/students/${search ? `?search=${encodeURIComponent(search)}` : ''}`);
export const getStudent = (id) => apiFetch(`/students/${id}/`);
export const updateStudent = (id, data) =>
  apiFetch(`/students/${id}/`, { method: 'PATCH', body: JSON.stringify(data) });
export const getStudentWeeklyReport = (id) => apiFetch(`/students/${id}/weekly-report/`);
export const getStudentSessions = (id) => apiFetch(`/students/${id}/sessions/`);
export const sendFeedbackEmail = (sessionId, email) =>
  apiFetch(`/sessions/${sessionId}/feedback/email/`, {
    method: 'POST', body: JSON.stringify({ email }),
  });
