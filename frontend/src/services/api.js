import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'https://medvoice-agent-production.up.railway.app';
console.log('VITE_API_URL:', import.meta.env.VITE_API_URL);
console.log('API_BASE_URL:', API_BASE_URL);
const api = axios.create({
  baseURL: API_BASE_URL,
});

export async function getHealth() {
  const response = await api.get('/api/v1/health');
  return response.data;
}

export async function processVoice(payload) {
  const formData = new FormData();
  formData.append('audio', payload.audio, payload.audioName || 'voice-turn.webm');
  formData.append('session_id', payload.session_id);
  formData.append('voice', payload.voice);
  if (payload.voice_provider) formData.append('voice_provider', payload.voice_provider);
  if (payload.persona_id) formData.append('persona_id', payload.persona_id);
  if (payload.language) formData.append('language', payload.language);

  const response = await api.post('/api/v1/voice', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function runDemoScenario(payload) {
  const response = await api.post('/api/v1/voice/demo', payload);
  return response.data;
}
