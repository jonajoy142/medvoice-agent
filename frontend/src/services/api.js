import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'medvoice_session';
const REMEMBER_KEY = 'medvoice_remember_session';
let refreshPromise = null;

export function getStoredSession() {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || 'null');
  } catch {
    return null;
  }
}

export function setStoredSession(session, options = {}) {
  const remember = options.remember ?? localStorage.getItem(REMEMBER_KEY) !== 'false';
  if (!session) {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    return;
  }
  const normalized = {
    ...session,
    expires_at: session.expires_at || (session.expires_in ? Math.floor(Date.now() / 1000) + Number(session.expires_in) : undefined),
  };
  localStorage.setItem(REMEMBER_KEY, remember ? 'true' : 'false');
  if (remember) {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.setItem(TOKEN_KEY, JSON.stringify(normalized));
  } else {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.setItem(TOKEN_KEY, JSON.stringify(normalized));
  }
}

const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const session = getStoredSession();
  if (session?.access_token) config.headers.Authorization = `Bearer ${session.access_token}`;
  return config;
});

api.interceptors.response.use((response) => response, async (error) => {
  const original = error.config;
  if (error.response?.status !== 401 || original?._retry || original?.url?.includes('/auth/refresh') || original?.url?.includes('/auth/login')) {
    return Promise.reject(error);
  }
  original._retry = true;
  const session = await refreshSession();
  if (!session?.access_token) return Promise.reject(error);
  original.headers = { ...(original.headers || {}), Authorization: `Bearer ${session.access_token}` };
  return api(original);
});

export async function ensureFreshSession() {
  const session = getStoredSession();
  if (!session?.access_token) return null;
  const expiresAt = Number(session.expires_at || 0);
  if (session.refresh_token && expiresAt && expiresAt - Math.floor(Date.now() / 1000) < 300) {
    return refreshSession();
  }
  return session;
}

export async function refreshSession() {
  const current = getStoredSession();
  if (!current?.refresh_token) return current;
  if (!refreshPromise) {
    refreshPromise = api.post('/auth/refresh', { refresh_token: current.refresh_token })
      .then((response) => {
        setStoredSession(response.data.session);
        return response.data.session;
      })
      .finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

export async function login(email, password, options = {}) {
  const response = await api.post('/auth/login', { email, password });
  setStoredSession(response.data.session, { remember: options.remember });
  return response.data;
}

export async function register(payload, options = {}) {
  const response = await api.post('/auth/register', payload);
  if (response.data.session) setStoredSession(response.data.session, { remember: options.remember });
  return response.data;
}

export async function logout() {
  try { await api.post('/auth/logout'); } finally { setStoredSession(null); }
}

export async function getMe() { return (await api.get('/auth/me')).data; }
export async function getDashboardMetrics() { return (await api.get('/api/v1/dashboard/metrics')).data; }
export async function getAgents() { return (await api.get('/api/v1/agents')).data; }
export async function getAgent(id) { return (await api.get(`/api/v1/agents/${id}`)).data; }
export async function createAgent(payload) { return (await api.post('/api/v1/agents', payload)).data; }
export async function updateAgent(id, payload) { return (await api.put(`/api/v1/agents/${id}`, payload)).data; }
export async function duplicateAgent(id) { return (await api.post(`/api/v1/agents/${id}/duplicate`)).data; }
export async function testAgent(id, message, sessionId) { return (await api.post(`/api/v1/agents/${id}/test`, { message, session_id: sessionId })).data; }
export async function processVoiceTurn({ agentId, audio, sessionId, voice = 'female', voiceProvider = 'sarvam', personaId, language = 'en-IN' }) {
  const form = new FormData();
  form.append('audio', audio, `voice-turn-${Date.now()}.webm`);
  if (sessionId) form.append('session_id', sessionId);
  form.append('voice', voice);
  form.append('voice_provider', voiceProvider);
  if (personaId) form.append('persona_id', personaId);
  form.append('language', language);
  return (await api.post(agentId ? `/api/v1/agents/${agentId}/voice` : '/api/v1/voice', form)).data;
}
export async function getCalls(params = {}) { return (await api.get('/api/v1/calls', { params })).data; }
export async function getCallDetail(id) { return (await api.get(`/api/v1/calls/${id}`)).data; }
export async function getReports() { return (await api.get('/api/v1/reports/metrics')).data; }
export async function getKnowledgeBase() { return (await api.get('/api/v1/knowledge-base')).data; }
export async function uploadKnowledgeDocument(file) {
  const form = new FormData();
  form.append('file', file);
  return (await api.post('/api/v1/knowledge-base', form)).data;
}
export async function deleteKnowledgeDocument(id) { return (await api.delete(`/api/v1/knowledge-base/${id}`)).data; }
export async function getSettings() { return (await api.get('/api/v1/settings')).data; }
export async function updateSettings(payload) { return (await api.put('/api/v1/settings', payload)).data; }
export async function getSuperOverview() { return (await api.get('/api/v1/super-admin/overview')).data; }
export async function getSuperHospitals() { return (await api.get('/api/v1/super-admin/hospitals')).data; }
export async function createHospital(payload) { return (await api.post('/api/v1/super-admin/hospitals', payload)).data; }
export async function getOnboardingRequests() { return (await api.get('/api/v1/super-admin/onboarding')).data; }
export async function approveOnboarding(id, payload = {}) { return (await api.post(`/api/v1/super-admin/onboarding/${id}/approve`, payload)).data; }
export async function getHealth() { return (await api.get('/api/v1/health')).data; }
