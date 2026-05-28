# MedVoice Flagship

MedVoice is a production-style AI hospital voice receptionist platform with realtime conversational UX, healthcare guardrails, configurable voice providers, and migration-ready database architecture.

## Product Pitch

MedVoice demonstrates a pilot-ready AI receptionist for hospitals and clinics:
- Conversational appointment booking
- Doctor availability lookup
- Verified patient record lookup
- FAQ assistant
- Emergency-safe escalation
- Voice provider switching (Local/Sarvam-ready)

## Why This Project Matters

It combines voice AI engineering, safety-first healthcare UX, and startup-grade architecture in one deployable repository suitable for recruiter demos and technical interviews.

## Architecture Overview

### System Diagram (Logical)

```text
Patient Voice/UI
   -> FastAPI API Layer
      -> Voice Service Orchestrator
         -> STT Provider (Local | Sarvam-ready)
         -> Intent + Guardrail Routing
         -> LLM Service (Ollama)
         -> TTS Provider (Local | Sarvam-ready)
      -> Repository Factory
         -> Mock Repositories (default dev stability)
         -> SQLAlchemy Repositories (Postgres mode)
            -> Docker Postgres / Managed Postgres / Supabase Postgres
```

### Backend Architecture

- `app/api/v1/routes_voice.py`: API contracts, voice routes, demo scenarios, health.
- `app/services/`: domain services and voice orchestration.
- `app/repositories/`: repository pattern with mock + SQLAlchemy implementations.
- `app/models/`: persistence entities (`patients`, `doctors`, `appointments`, `conversation_sessions`, `audit_logs`).
- `app/voice/`: provider abstraction + voice personas.
- `app/core/`: config, auth, logger, legacy voice pipeline integration.

### Frontend Architecture

- `frontend/src/App.jsx`: premium dashboard shell + realtime state machine UX.
- `frontend/src/services/api.js`: API abstraction.
- `frontend/src/config/voicePersonas.js`: provider/language/persona catalogs.
- `frontend/src/components/StateBadge.jsx`: reusable status cards.

### Voice Architecture

- Default provider: `local`.
- Optional provider: `sarvam` (config-driven, key required).
- Automatic fallback: if Sarvam requested but unavailable/misconfigured, local is used.
- Persona system includes 10 configurable profiles.

### Database Architecture

- Docker Postgres for local production-like persistence.
- SQLAlchemy models + repository pattern.
- Alembic migrations for production schema management.
- Mock fallback keeps local demos stable without DB.

### Realtime UX Architecture

- Frontend stage machine: `idle -> listening -> transcribing -> thinking -> speaking`.
- Backend returns structured response contract with stage timings:
  - `stt_latency_ms`
  - `llm_latency_ms`
  - `tts_latency_ms`
  - `total_latency_ms`
- Streaming-ready endpoint: `/api/v1/voice/stream` (contract-compatible placeholder).

## Structured Response Contract

```json
{
  "intent": "book_appointment",
  "confidence": 0.92,
  "spoken_response": "Sure, I can help with that.",
  "display_response": "Sure, I can help with that.",
  "structured_data": {},
  "guardrail_status": "active",
  "provider": "local",
  "persona": "female_warm_indian",
  "language": "en-IN",
  "latency_ms": 240.3,
  "stage_timings": {
    "stt_latency_ms": 80.1,
    "llm_latency_ms": 110.7,
    "tts_latency_ms": 42.2,
    "total_latency_ms": 240.3
  },
  "requires_confirmation": true,
  "safe_to_speak": true
}
```

## Healthcare Safety Guardrails

- Never fabricates patient/doctor/appointment records.
- Emergency phrase detection triggers escalation-safe response.
- PHI-safe logging redacts sensitive values.
- Optional API key guard for patient-sensitive endpoints.
- Provider fallback avoids hard failures in live demos.

## Setup

## 1) Prerequisites

- Python 3.11
- Node 18+
- Docker Desktop
- Ollama running with `llama3`

## 2) Backend install

```bash
pip install -e .
```

## 3) Frontend install

```bash
cd frontend
npm install
```

## 4) Environment

Create `.env` from `.env.example`.

## 5) Start Docker Postgres

```bash
docker compose up -d postgres
```

## 6) Run migrations (production path)

```bash
alembic upgrade head
```

## 7) Seed demo data (optional when DB mode enabled)

```bash
python scripts/seed_demo_data.py
```

## 8) Run backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 9) Run frontend

```bash
cd frontend
npm run dev
```

## Alembic Guide

- Upgrade:
  - `alembic upgrade head`
- Create new migration:
  - `alembic revision --autogenerate -m "message"`
- Downgrade one step:
  - `alembic downgrade -1`

Alembic reads `DATABASE_URL` from app config/env via `alembic/env.py`.

## Provider Switching (Local vs Sarvam)

Local mode (default):

```env
VOICE_PROVIDER=local
```

Sarvam mode:

```env
VOICE_PROVIDER=sarvam
SARVAM_API_KEY=your_key
SARVAM_TTS_MODEL=...
SARVAM_STT_MODEL=...
SARVAM_TTS_URL=...
SARVAM_STT_URL=...
```

Behavior:
- `VOICE_PROVIDER=local` -> always local
- `VOICE_PROVIDER=sarvam` + key/config present -> Sarvam attempted
- `VOICE_PROVIDER=sarvam` but missing/failed config -> automatic fallback to local

No code changes are needed to switch provider.

## Supabase Migration Path

Current architecture is Supabase-ready:
- Set `DATABASE_URL` to Supabase Postgres connection string.
- Keep repositories/services unchanged.
- Optionally add Supabase auth/storage adapters later (TODO hooks in code).

## Recruiter Demo Walkthrough

Use one-click scenarios from dashboard:
1. Book cardiology appointment
2. Doctor availability lookup
3. Verified patient lookup
4. Visiting hours FAQ
5. Emergency escalation
6. Hindi-English appointment flow
7. Persona preview
8. Provider fallback + DB health demo

Narrative script:
1. Show health panel (DB + provider).
2. Switch persona/language/provider live.
3. Run two normal scenarios + one emergency scenario.
4. Highlight latency cards and guardrail panel.
5. Show fallback behavior by selecting Sarvam without valid key.
6. Conclude with migration readiness (Docker Postgres + Alembic + Supabase path).

## API Endpoints

- `POST /api/v1/voice`
- `POST /api/v1/voice/stream`
- `POST /api/v1/voice/demo`
- `GET /api/v1/availability`
- `POST /api/v1/appointment`
- `GET /api/v1/appointments`
- `GET /api/v1/patient/{opid}`
- `GET /api/v1/health`

## Validation Commands

- Backend tests:
  - `python -m pytest -q`
- Frontend build:
  - `cd frontend && npm run build`
- Docker compose validation:
  - `docker compose config`
- Migrations:
  - `alembic upgrade head`

## Screenshots Placeholders

- `docs/screenshots/dashboard-overview.png`
- `docs/screenshots/voice-console.png`
- `docs/screenshots/demo-scenarios.png`
- `docs/screenshots/health-guardrails-panel.png`

## Limitations (Honest)

- Sarvam payload contracts are integration-ready but may need endpoint-specific payload refinement.
- `/voice/stream` is streaming-ready contract surface, not full SSE audio chunking yet.
- Local STT/TTS still relies on host audio stack quality.

## Production Roadmap

- Full SSE/WebSocket streaming with barge-in control.
- Strong auth/RBAC and tenant isolation.
- Observability stack (Prometheus/Grafana/OpenTelemetry).
- Supabase auth/storage integration and managed deployment templates.
- Clinical safety policy engine and red-team tests.
