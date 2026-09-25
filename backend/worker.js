/**
 * MedVoice Backend - Cloudflare Worker
 * Handles API endpoints, Fish Audio TTS Proxy, Signups, and CORS for Vercel Frontend
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    const origin = request.headers.get('Origin') || '*';

    // Permissive CORS for Vercel, localhost, and custom domains
    const corsHeaders = {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
      'Access-Control-Allow-Credentials': 'true',
    };

    // Preflight OPTIONS handler
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ── 1. Health check ──
    if (pathname === '/health' || pathname === '/api/health' || pathname === '/api/v1/health') {
      const fishKey = env.FISH_AUDIO_API_KEY || env.FISH_API_KEY || '';
      return new Response(
        JSON.stringify({
          status: 'ok',
          ok: true,
          service: 'medvoice-backend-worker',
          runtime: 'cloudflare-worker',
          fishAudioReady: !!fishKey,
          fishKey: !!fishKey,
          voiceId: env.FISH_AUDIO_VOICE_ID || '0429f2b252464b88b2ab2128f084290c',
          model: 's2.1-pro-free',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        }
      );
    }

    // ── 2. TTS Proxy Endpoint (Fish Audio) ──
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

    // ── 4. Proxy to external Python Backend (Optional) ──
    if (env.PYTHON_BACKEND_URL && pathname.startsWith('/api/v1')) {
      try {
        const targetUrl = new URL(request.url);
        const backendBase = new URL(env.PYTHON_BACKEND_URL);
        targetUrl.protocol = backendBase.protocol;
        targetUrl.host = backendBase.host;
        targetUrl.port = backendBase.port;
        const modifiedRequest = new Request(targetUrl, request);
        return fetch(modifiedRequest);
      } catch (err) {
        return new Response(JSON.stringify({ error: 'Failed to proxy request to Python backend' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }
    }

    return new Response(
      JSON.stringify({
        message: 'MedVoice Cloudflare Backend API is running.',
        endpoints: ['/health', '/tts', '/signup', '/api/v1/health'],
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      }
    );
  },
};
