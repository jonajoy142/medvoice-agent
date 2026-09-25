/**
 * MedVoice Demo Server — Zero-dependency Node.js proxy
 * Reads FISH_AUDIO_API_KEY from backend/.env
 * Proxies /tts → Fish Audio API (model: s2.1-pro-free, reference_id: 0429f2b252464b88b2ab2128f084290c)
 * Handles /signup → Formspree → jonajoy142@gmail.com
 * Serves demo.html at http://localhost:3333
 */
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

function getEnv() {
  const envPaths = [
    path.join(__dirname, 'backend', '.env'),
    path.join(__dirname, '.env'),
    path.join(__dirname, 'frontend', '.env'),
  ];
  const env = {};
  for (const envPath of envPaths) {
    try {
      if (!fs.existsSync(envPath)) continue;
      const lines = fs.readFileSync(envPath, 'utf8').split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const idx = trimmed.indexOf('=');
        if (idx === -1) continue;
        const key = trimmed.slice(0, idx).trim();
        let val = trimmed.slice(idx + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1);
        }
        if (val) env[key] = val;
      }
    } catch (e) {}
  }
  return env;
}

function resolveFishKey(env) {
  return env.FISH_AUDIO_API_KEY || env.FISH_API_KEY || env.FISHAUDIO_API_KEY || env.FISH_KEY || process.env.FISH_AUDIO_API_KEY || process.env.FISH_API_KEY || '';
}

const PORT = 3333;
// modal-1 voice reference ID from Fish Audio playground
const DEFAULT_VOICE_ID = '0429f2b252464b88b2ab2128f084290c';

function setCORS(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function readBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', c => { body += c; });
    req.on('end', () => resolve(body));
  });
}

async function proxyTTS(req, res) {
  const env = getEnv();
  const fishKey = resolveFishKey(env);
  const configuredVoiceId = env.FISH_AUDIO_VOICE_ID || env.FISH_VOICE_ID || DEFAULT_VOICE_ID;

  const body = await readBody(req);
  let payload = {};
  try {
    payload = JSON.parse(body || '{}');
  } catch (e) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid JSON body' }));
    return;
  }

  const text = (payload.text || '').trim().slice(0, 1000);
  if (!text) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Text is required' }));
    return;
  }

  const voiceId = payload.reference_id || payload.voiceId || configuredVoiceId;

  if (!fishKey) {
    console.warn('⚠️  FISH_AUDIO_API_KEY not found in backend/.env — returning 401');
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'FISH_AUDIO_API_KEY not set in backend/.env' }));
    return;
  }

  // Matches Fish Audio API playground request
  const fishPayload = JSON.stringify({
    text,
    reference_id: voiceId,
    format: 'mp3',
  });

  const opts = {
    hostname: 'api.fish.audio',
    port: 443,
    path: '/v1/tts',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${fishKey}`,
      'Content-Type': 'application/json',
      'model': 's2.1-pro-free',
      'Content-Length': Buffer.byteLength(fishPayload),
    },
  };

  const fishReq = https.request(opts, (fishRes) => {
    console.log(`🔊 Fish Audio [${fishRes.statusCode}] for "${text.slice(0, 40)}..."`);
    if (fishRes.statusCode !== 200) {
      let errBody = '';
      fishRes.on('data', d => { errBody += d; });
      fishRes.on('end', () => {
        console.error(`Fish Audio error response: ${errBody}`);
        res.writeHead(fishRes.statusCode, { 'Content-Type': 'application/json' });
        res.end(errBody);
      });
      return;
    }
    res.writeHead(200, {
      'Content-Type': 'audio/mpeg',
      'Cache-Control': 'no-cache',
    });
    fishRes.pipe(res);
  });

  fishReq.on('error', (err) => {
    console.error('Fish Audio request failed:', err.message);
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: err.message }));
  });

  fishReq.write(fishPayload);
  fishReq.end();
}

async function handleSignup(req, res) {
  const body = await readBody(req);
  let data;
  try { data = JSON.parse(body); } catch (e) { res.writeHead(400); res.end(); return; }

  console.log('\n🎉 EARLY ACCESS SIGNUP:');
  console.log(`   Name:     ${data.name}`);
  console.log(`   Email:    ${data.email}`);
  console.log(`   Use case: ${data.usecase}`);
  console.log('   → jonajoy142@gmail.com\n');

  const formData = JSON.stringify({
    name: data.name,
    email: data.email,
    usecase: data.usecase,
    _subject: '🎙️ MedVoice Early Access Request',
  });

  const fReq = https.request({
    hostname: 'formspree.io',
    port: 443,
    path: '/f/xpwrdbvg',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Content-Length': Buffer.byteLength(formData),
    },
  }, () => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
  });
  fReq.on('error', () => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
  });
  fReq.write(formData);
  fReq.end();
}

function serveDemo(res) {
  const demoPath = path.join(__dirname, 'frontend', 'demo.html');
  fs.readFile(demoPath, (err, data) => {
    if (err) { res.writeHead(404); res.end('demo.html not found'); return; }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  setCORS(res);
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const reqUrl = new URL(req.url, `http://${req.headers.host || 'localhost:3333'}`);
  const pathname = reqUrl.pathname;

  if (pathname === '/tts' && req.method === 'POST') return proxyTTS(req, res);
  if (pathname === '/signup' && req.method === 'POST') return handleSignup(req, res);
  if (pathname === '/health') {
    const env = getEnv();
    const fishKey = resolveFishKey(env);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      fishKey: !!fishKey,
      voiceId: env.FISH_AUDIO_VOICE_ID || env.FISH_VOICE_ID || DEFAULT_VOICE_ID,
      model: 's2.1-pro-free'
    }));
    return;
  }
  if (['/', '', '/demo', '/demo.html'].includes(pathname)) return serveDemo(res);
  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, () => {
  const env = getEnv();
  const fishKey = env.FISH_AUDIO_API_KEY || process.env.FISH_AUDIO_API_KEY || '';
  console.log('\n╔══════════════════════════════════════╗');
  console.log('║   🎙️  MedVoice Demo Server           ║');
  console.log('╠══════════════════════════════════════╣');
  console.log(`║   URL:   http://localhost:${PORT}        ║`);
  console.log(`║   Key:   ${fishKey ? '✅ Fish Audio key loaded' : '❌ Missing FISH_AUDIO_API_KEY'} ║`);
  console.log(`║   Voice: modal-1 (${DEFAULT_VOICE_ID.slice(0, 8)}...)  ║`);
  console.log(`║   Model: s2.1-pro-free (Header-based)║`);
  console.log('╚══════════════════════════════════════╝\n');
  console.log('   Open http://localhost:3333 in Chrome\n');
});
