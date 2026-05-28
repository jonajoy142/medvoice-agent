import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export async function getHealth() {
  const response = await api.get('/api/v1/health');
  return response.data;
}

export async function processVoice(payload) {
  const response = await api.post('/api/v1/voice', payload);
  return response.data;
}

export async function runDemoScenario(payload) {
  const response = await api.post('/api/v1/voice/demo', payload);
  return response.data;
}