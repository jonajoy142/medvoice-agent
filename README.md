# 🎙️ MedVoice AI — Real-Time Voice Agent

> **AI-powered voice agent for hospitals and restaurants** · Real-time speech · Gemini AI · Exotel Telephony · Multi-tenant SaaS

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Try%20Now-6366f1?style=for-the-badge&logo=google-chrome)](https://jonajoy142.github.io/medvoice-agent/)
[![GitHub](https://img.shields.io/badge/GitHub-Source-black?style=for-the-badge&logo=github)](https://github.com/jonajoy142/medvoice-agent)

---

## 🚀 Live Demo — Works Right Now

**[👉 Try the live demo in your browser →](https://jonajoy142.github.io/medvoice-agent/)**

> Open `frontend/demo.html` locally to try instantly — no backend needed.

```bash
open frontend/demo.html   # Mac
# or just double-click demo.html in Finder
```

The demo lets you:
- 🎤 **Speak to the AI agent** using your real microphone
- 🏥 **Hospital mode** — book appointments, check doctors, emergency guidance
- 🍕 **Restaurant mode** — order pizza by voice, get totals, confirm orders
- ⚡ **Real Gemini AI responses** (add your free API key) or scripted demo mode
- 📊 **Live metrics** — response latency, conversation turns, waveform visualizer
- 🔄 **Barge-in** — interrupt the AI mid-sentence just like a real phone call

---

## 🎯 What This Is

MedVoice AI is a **production-grade multi-tenant SaaS voice agent platform** that enables businesses (hospitals, restaurants, clinics) to deploy AI-powered receptionists that:

- Answer phone calls in real-time using **Exotel WebSocket telephony**
- Process speech with **Sarvam STT** and **OpenAI Whisper** (streaming)
- Generate responses via **Gemini / GPT-4o-mini** with function calling
- Synthesize voice replies with **Sarvam TTS** / **OpenAI TTS** (streaming)
- Handle **barge-in** (interrupting the AI mid-sentence) via energy-based VAD
- Track every call: latency P50/P95, transcripts, revenue, conversion rate

---

## 🏗️ Architecture

```
Phone Call (Exotel)
    ↓ WebSocket
ExotelVoiceBotHandler
    ↓
Voice Activity Detector (VAD) ── barge-in detection
    ↓
AI State Manager ── LISTENING / SPEAKING / THINKING states
    ↓
Voice Runtime Pipeline
    ├─ STT: Sarvam / OpenAI Whisper (streaming)
    ├─ LLM: Gemini / GPT-4o-mini + function calling
    └─ TTS: Sarvam / OpenAI (streaming)
    ↓
Event Bus → Persistence (PostgreSQL)
    ↓
Analytics Dashboard (React)
```

---

## ✨ Key Features

| Feature | Status | Details |
|---------|--------|---------|
| Real phone calls | ✅ | Exotel WebSocket bidirectional streaming |
| Voice barge-in | ✅ | Energy-based VAD with cancellation tokens |
| Multi-provider STT | ✅ | OpenAI Whisper + Sarvam (switchable) |
| Multi-provider LLM | ✅ | OpenAI, Anthropic, Ollama, Gemini |
| Multi-provider TTS | ✅ | OpenAI + Sarvam streaming |
| Restaurant ordering | ✅ | Menu, cart, orders, revenue tracking |
| Hospital receptionist | ✅ | Appointments, patient lookup, escalation |
| Multi-tenant SaaS | ✅ | Hospital isolation, RBAC, Supabase auth |
| Live analytics | ✅ | 15+ KPIs, P50/P95 latency, revenue |
| In-browser demo | ✅ | Works without any backend setup |

---

## 🛠️ Tech Stack

**Backend:** Python · FastAPI · WebSockets · PostgreSQL · Supabase · Alembic · Redis

**AI/Voice:** Google Gemini · OpenAI GPT-4o-mini · Sarvam STT/TTS · Exotel Telephony · Web Speech API

**Frontend:** React · Vite · TypeScript · Tailwind CSS

**Infrastructure:** Docker · Railway · Vercel · GitHub Actions

---

## 📁 Project Structure

```
medvoice-agent/
├── frontend/
│   ├── demo.html          ← 🎯 STANDALONE DEMO — open this!
│   ├── src/App.jsx        ← Full dashboard
│   └── src/services/api.js
├── backend/
│   ├── app/
│   │   ├── voice/         ← VAD, state machine, runtime pipeline
│   │   ├── telephony/     ← Exotel WebSocket handler
│   │   ├── stt/           ← Streaming STT providers
│   │   ├── llm/           ← Streaming LLM providers
│   │   ├── tts/           ← Streaming TTS providers
│   │   ├── workflows/     ← Restaurant + hospital tools
│   │   └── api/v1/        ← REST endpoints
│   └── alembic/           ← Database migrations
└── docker-compose.yml
```

---

## ⚡ Quick Start (Browser Demo — No Setup)

```bash
# Just open this file in Chrome/Edge:
open frontend/demo.html

# Add your free Gemini API key in the popup for real AI responses
# Or click "Skip" for scripted demo mode — works without any key
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/app/apikey) (no credit card, 1500 requests/day free).

---

## 🖥️ Full Backend Setup

```bash
# 1. Configure environment
cp .env.example backend/.env
# Edit backend/.env with your credentials (see below)

# 2. Install dependencies
cd backend
poetry install

# 3. Run migrations
poetry run alembic upgrade head

# 4. Seed demo data
poetry run python scripts/seed_demo_pizza.py

# 5. Start backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Required Environment Variables

```env
# Database
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service key>
DATABASE_URL=postgresql://postgres:<pass>@<host>:5432/postgres
USE_DATABASE=true
JWT_SECRET=<random string>
REDIS_URL=redis://localhost:6379/0

# AI Providers
OPENAI_API_KEY=<your key>
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# Telephony (Exotel)
TELEPHONY_PROVIDER=exotel
TELEPHONY_ACCOUNT_SID=<sid>
TELEPHONY_AUTH_TOKEN=<token>
TELEPHONY_PHONE_NUMBER=<number>

# Voice (Sarvam)
SARVAM_API_KEY=<key>
SARVAM_STT_ENDPOINT=<endpoint>
SARVAM_TTS_ENDPOINT=<endpoint>
```

---

## 📊 Analytics & Business Metrics

The platform tracks 15+ real-time KPIs:

- **Calls**: total, connected, successful, converted
- **Performance**: AI resolution rate, human transfer rate, failure rate
- **Latency**: average, P50, P95 response times
- **Revenue**: total, daily breakdown, average order value
- **Cost**: AI cost per call, cost per minute

---

## 🧪 Tests

```bash
cd backend
poetry run pytest -q
# 141/152 tests passing (92.8%)
```

---

## 🌐 Deploy for Free

| Platform | Method | URL |
|----------|--------|-----|
| **Demo only** | GitHub Pages | `github.com/<user>/<repo>/demo.html` |
| **Frontend** | Vercel | Auto-deploy from `frontend/` |
| **Backend** | Railway | `railway.json` already configured |
| **Database** | Supabase | Free tier (500MB) |

The standalone `demo.html` can be hosted anywhere as a single file — GitHub Pages, Netlify Drop, or just share the file directly.

---

## 👤 Author

Built by **Jona Joy** · [GitHub](https://github.com/jonajoy142) · Real-time voice AI for healthcare & hospitality

---

*MedVoice is not a clinical diagnostic tool. The platform tracks business operations data only: calls, appointments, orders, and revenue. No medical records are stored.*


MedVoice is a multi-tenant hospital/clinic AI voice-agent SaaS foundation for receptionist operations: overview analytics, agents, calls, reports, knowledge base, contacts, settings, billing views, and platform administration.

