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
export const startSession = (label) =>
  apiFetch('/sessions/start/', { method: 'POST', body: JSON.stringify({ label }) });
export const endSession = (id) =>
  apiFetch(`/sessions/${id}/end/`, { method: 'POST' });

// Students
export const getStudents = () => apiFetch('/students/');
export const getStudent = (id) => apiFetch(`/students/${id}/`);
export const getStudentWeeklyReport = (id) => apiFetch(`/students/${id}/weekly-report/`);
