/**
 * Cloudflare Worker for MedVoice AI
 * Serves frontend static assets + provides backend API endpoints in a SINGLE Worker:
 *  - /tts or /api/tts: Proxies to Fish Audio API (s2.1-pro-free) securely using FISH_AUDIO_API_KEY
 *  - /signup: Early access form submission forwarder
 *  - /health or /api/health: Health check and config status
 *  - All other routes: Serves static frontend assets (dist/)
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // CORS headers for all responses
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ── 1. Health Check Endpoint ──
    if (pathname === '/health' || pathname === '/api/health') {
      const fishKey = env.FISH_AUDIO_API_KEY || env.FISH_API_KEY || '';
      return new Response(
        JSON.stringify({
          ok: true,
          fishKey: !!fishKey,
          voiceId: env.FISH_AUDIO_VOICE_ID || '0429f2b252464b88b2ab2128f084290c',
          model: 's2.1-pro-free',
          runtime: 'cloudflare-worker',
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders,
          },
        }
      );
    }

    // ── 2. TTS Endpoint (Proxies securely to Fish Audio) ──
    if ((pathname === '/tts' || pathname === '/api/tts') && request.method === 'POST') {
      try {
        const body = await request.json().catch(() => ({}));
        const text = (body.text || '').trim().slice(0, 1000);
        if (!text) {
          return new Response(JSON.stringify({ error: 'Text is required' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders },
          });
        }

        const fishKey = env.FISH_AUDIO_API_KEY || env.FISH_API_KEY;
        if (!fishKey) {
          return new Response(
            JSON.stringify({
              error: 'FISH_AUDIO_API_KEY is not set in Cloudflare Worker Variables & Secrets.',
            }),
            {
              status: 401,
              headers: { 'Content-Type': 'application/json', ...corsHeaders },
            }
          );
        }

        const voiceId =
          body.reference_id ||
          body.voiceId ||
          env.FISH_AUDIO_VOICE_ID ||
          '0429f2b252464b88b2ab2128f084290c';

        const fishRes = await fetch('https://api.fish.audio/v1/tts', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${fishKey}`,
            'Content-Type': 'application/json',
            model: 's2.1-pro-free',
          },
          body: JSON.stringify({
            text,
            reference_id: voiceId,
            format: 'mp3',
          }),
        });

        if (!fishRes.ok) {
          const errText = await fishRes.text();
          return new Response(errText, {
            status: fishRes.status,
            headers: { 'Content-Type': 'application/json', ...corsHeaders },
          });
        }

        const audioBytes = await fishRes.arrayBuffer();
        return new Response(audioBytes, {
          status: 200,
          headers: {
            'Content-Type': 'audio/mpeg',
            'Cache-Control': 'no-cache',
            ...corsHeaders,
          },
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 502,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }
    }

    // ── 3. Early Access Signup ──
    if (pathname === '/signup' && request.method === 'POST') {
      try {
        const data = await request.json().catch(() => ({}));
        await fetch('https://formspree.io/f/xpwrdbvg', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: JSON.stringify({
            name: data.name,
            email: data.email,
            usecase: data.usecase,
            _subject: '🎙️ MedVoice Early Access Request',
          }),
        });
        return new Response(JSON.stringify({ ok: true }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      } catch (err) {
        return new Response(JSON.stringify({ ok: true }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }
    }

    // ── 4. Optional: Reverse-Proxy /api/v1/* to external backend (if BACKEND_URL configured) ──
    if (pathname.startsWith('/api/v1') && env.BACKEND_URL) {
      try {
        const targetUrl = new URL(request.url);
        const backendBase = new URL(env.BACKEND_URL);
        targetUrl.protocol = backendBase.protocol;
        targetUrl.host = backendBase.host;
        targetUrl.port = backendBase.port;
        const modifiedRequest = new Request(targetUrl, request);
        return fetch(modifiedRequest);
      } catch (e) {
        return new Response(JSON.stringify({ error: 'Failed to proxy request to backend' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }
    }

    // ── 5. Static Assets (Frontend) ──
    if (env.ASSETS) {
      // If root, serve demo.html (or fallback to index.html)
      if (pathname === '/' || pathname === '' || pathname === '/demo') {
        const demoReq = new Request(new URL('/demo.html', request.url), request);
        const demoRes = await env.ASSETS.fetch(demoReq);
        if (demoRes.status === 200) return demoRes;
      }
      return env.ASSETS.fetch(request);
    }

    return new Response('MedVoice Cloudflare Worker running.', {
      status: 200,
      headers: { 'Content-Type': 'text/plain' },
    });
  },
};
