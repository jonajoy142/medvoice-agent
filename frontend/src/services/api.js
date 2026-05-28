import axios from 'axios';

export async function getHealth() {
  const response = await axios.get('/api/v1/health');
  return response.data;
}

export async function processVoice(payload) {
  const response = await axios.post('/api/v1/voice', payload);
  return response.data;
}

export async function runDemoScenario(payload) {
  const response = await axios.post('/api/v1/voice/demo', payload);
  return response.data;
}
