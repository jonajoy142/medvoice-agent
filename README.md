# MedVoice AI

MedVoice is a FastAPI + React hospital voice receptionist demo with deterministic healthcare guardrails, optional LLM phrasing providers, voice provider switching, and Postgres-ready persistence.

## Repository Split

```text
medVoice-ai/
  backend/          FastAPI app, tests, Alembic, Poetry, backend deployment config
  frontend/         React/Vite app
  docker-compose.yml
  README.md
```

Deployment split:
- Frontend: Vercel
- Backend: Render, Railway, Fly.io, or any container host
- Database: Docker Postgres locally, Supabase Postgres later

## Architecture

```text
Frontend UI
  -> FastAPI API
    -> VoiceService
      -> Intent + healthcare guardrails
      -> deterministic workflows for records, appointments, availability, emergency handling
      -> optional LLM phrasing for generic unsupported turns only
    -> Repository factory
      -> mock repositories by default
      -> SQLAlchemy repositories when USE_DATABASE=true
    -> Docker Postgres / Supabase-compatible Postgres
```

Safety rules:
- Patient chart and record requests require verified patient ID or phone number plus DOB.
- Patient lookup, appointments, doctor availability, emergency escalation, and verified-data FAQ flows do not require an LLM.
- LLM providers must not invent patient, doctor, appointment, or medical facts.
- Missing hosted API keys or unavailable Ollama fall back to deterministic responses.

## Local Development

### 1. Start Postgres from the root

```bash
docker compose up -d postgres
```

### 2. Backend

```bash
cd backend
poetry install
cp .env.example .env
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

Root convenience commands are also available after `poetry install` from the repo root:

```bash
poetry run backend-dev
poetry run backend-test
poetry run backend-migrate
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

## LLM Providers

Configure the backend with:

```env
LLM_PROVIDER=deterministic|ollama|openai|groq|openrouter
LLM_FALLBACK_PROVIDER=deterministic
LLM_ENABLE_FALLBACK=true
LLM_TIMEOUT_SECONDS=8
```

Default production-safe mode:

```env
LLM_PROVIDER=deterministic
```

Local Ollama mode:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Hosted provider mode:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

Groq and OpenRouter are also supported through OpenAI-compatible chat APIs:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant

LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

API keys are backend-only environment variables. Do not expose them to the frontend.

## Database

Local Docker Postgres:

```bash
docker compose up -d postgres
cd backend
USE_DATABASE=true poetry run alembic upgrade head
poetry run python scripts/seed_demo_data.py
```

Supabase migration path:
- Create a Supabase Postgres database.
- Set backend `DATABASE_URL` to the Supabase connection string.
- Run `cd backend && poetry run alembic upgrade head`.
- Keep repository and service code unchanged.

## Docker Backend

Build and run the FastAPI container from the repo root:

```bash
docker build -t medvoice-backend ./backend
docker run --env-file backend/.env.example -p 8000:8000 medvoice-backend
```

For Render/Fly.io:
- Root/build context: `backend`
- Dockerfile: `backend/Dockerfile`
- Start command if not using Docker: `poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set `LLM_PROVIDER=deterministic` unless a hosted provider API key is configured.
- Set `DATABASE_URL` for managed Postgres or Supabase.

For Railway:
- Service Root Directory: `backend`
- Builder: Dockerfile, using `backend/Dockerfile`
- Railway config: `backend/railway.json`
- Start command: `poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Healthcheck path: `/api/v1/health`
- Required environment variables:
  - `PORT` is provided by Railway
  - `ENVIRONMENT=production`
  - `LLM_PROVIDER=deterministic`
  - `LLM_FALLBACK_PROVIDER=deterministic`
  - `LLM_ENABLE_FALLBACK=true`
  - `CORS_ORIGINS=https://your-vercel-app.vercel.app`
- Optional database variables:
  - `USE_DATABASE=true`
  - `DATABASE_URL=postgresql+psycopg://...`
- Optional hosted LLM variables:
  - `OPENAI_API_KEY`, `OPENAI_MODEL`
  - `GROQ_API_KEY`, `GROQ_MODEL`
  - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`

For Vercel:
- Preferred project root: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- If Vercel is connected at the repository root, the root `vercel.json` delegates install/build/output to `frontend/`.
- If Vercel tries to build `backend/`, change the Vercel project Root Directory to `frontend` in Settings -> Build & Development Settings.
- Configure API base URL for the deployed backend when moving beyond the local Vite proxy.

## Validation

```bash
cd backend
poetry install
poetry run alembic upgrade head
poetry run pytest -q

cd ../frontend
npm run build

cd ..
docker compose config
```

## API Endpoints

- `POST /api/v1/voice`
- `POST /api/v1/voice/stream`
- `POST /api/v1/voice/demo`
- `GET /api/v1/availability`
- `POST /api/v1/appointment`
- `GET /api/v1/appointments`
- `GET /api/v1/patient/{opid}`
- `GET /api/v1/health`

## Limitations

- `/voice/stream` is a streaming-ready response contract, not full SSE audio streaming yet.
- Local STT/TTS still depends on the host audio stack.
- Strong production auth/RBAC and tenant isolation remain future work.
