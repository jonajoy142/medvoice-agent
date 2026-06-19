# MedVoice AI

MedVoice is a multi-tenant hospital/clinic AI voice-agent SaaS foundation for receptionist operations: overview analytics, agents, calls, reports, knowledge base, contacts, settings, billing views, and platform administration.

MedVoice is not a diagnostic tool. The schema tracks business and operations data only: calls, leads, appointments, outcomes, revenue influence, and safe escalation metadata. Do not store diagnosis, prescriptions, clinical history, or medical reports.

## Supabase-First Setup

For real login and dashboard data, point the backend at your Supabase project database. Docker Postgres is only a local fallback if you intentionally set `DATABASE_URL` to localhost.

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key, backend only>
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
USE_DATABASE=true
JWT_SECRET=<long random value>
REDIS_URL=redis://localhost:6379/0
```

Correct split Postgres env names are preferred:

```env
SUPABASE_HOST=
SUPABASE_PORT=5432
SUPABASE_DB=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=
```

Old compatibility names are still accepted if already present:

```env
SUPBASE_PORT=5432
SUPBASE_PSWD=
```

Never put real secret values in git.

## Local Backend

```bash
cd /Users/jonajoy/Projects/medVoice-ai
cp .env.example backend/.env
# edit backend/.env with Supabase URL, keys, DATABASE_URL, Redis, and provider keys

cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

## Local Frontend

```bash
cd /Users/jonajoy/Projects/medVoice-ai/frontend
cp .env.example .env
npm install
npm run dev
```

Set:

```env
VITE_API_URL=http://localhost:8000
```

## Register/Login Flow

`/register` is real, not local-only:

1. Frontend posts to `POST /auth/register`.
2. Backend creates or finds the Supabase Auth user using the backend-only service role key.
3. Backend creates a hospital workspace.
4. Backend creates a `staff_users` row mapped to the Supabase user id with role `hospital_admin`.
5. Backend returns user role, hospital, permissions, redirect target, and a session when password login succeeds.
6. Frontend redirects hospital users to `/overview` and platform admins to `/admin`.

`/login` posts to `POST /auth/login`, then the frontend fetches `/auth/me` through the stored bearer token.

## First Super Admin

Use env vars only. Do not hardcode passwords in source.

```env
SEED_SUPER_ADMIN_EMAIL=owner@medvoice.ai
SEED_SUPER_ADMIN_PASSWORD=<temporary password from your local env or secret manager>
SEED_SUPER_ADMIN_NAME=MedVoice Admin
```

Run:

```bash
cd backend
poetry run python scripts/create_super_admin.py
```

The script creates the Supabase Auth user if missing and upserts an active `staff_users` row with role `super_admin` and no hospital id.

## Optional Demo Seed

```env
SEED_HOSPITAL_ADMIN_EMAIL=admin@examplehospital.com
SEED_STAFF_EMAIL=staff@examplehospital.com
SEED_DEFAULT_PASSWORD=<temporary password>
```

Then run:

```bash
cd backend
poetry run python scripts/seed_saas_dev.py
```

The demo seed creates a demo hospital, approved staff mappings, two agents, sample calls, summaries, appointment outcomes, revenue estimates, and KB metadata.

## Migrations

```bash
cd backend
poetry run alembic upgrade head
```

Current migration chain includes:

- `20260528_01_initial_schema.py`
- `20260618_01_full_medvoice_operations.py`
- `20260618_02_saas_foundation.py`
- `20260618_03_onboarding_requests.py`

## Role Redirects

- `super_admin` -> `/admin`
- `hospital_admin` -> `/overview`
- `staff` -> `/overview` with limited navigation/actions

## Auth/API Endpoints

Both clean and versioned auth paths are available:

```text
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
POST /auth/invite-staff
```

Versioned aliases also exist under `/api/v1/auth/...`.

## Required Production Env Vars

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
USE_DATABASE=true
JWT_SECRET=
REDIS_URL=
SARVAM_API_KEY=
SARVAM_STT_ENDPOINT=
SARVAM_TTS_ENDPOINT=
LLM_PROVIDER=openai
OPENAI_API_KEY=
TELEPHONY_PROVIDER=exotel
TELEPHONY_ACCOUNT_SID=
TELEPHONY_AUTH_TOKEN=
TELEPHONY_PHONE_NUMBER=
```

## Tests

```bash
cd backend
poetry run pytest -q
poetry run python scripts/evaluate_workflows.py

cd ../frontend
npm run build
```

Supabase integration tests are gated:

```env
RUN_SUPABASE_INTEGRATION_TESTS=true
```

## Render Deployment With Supabase/Postgres

Backend service:

- Root directory: `backend`
- Build: `poetry install`
- Start: `poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set all production env vars in Render, never in source.
- Run migrations from a Render shell or CI job: `poetry run alembic upgrade head`.

Frontend service:

- Root directory: `frontend`
- Build: `npm install && npm run build`
- Publish directory: `dist`
- Set `VITE_API_URL=https://<backend-host>`.

Recommended production layout:

```text
Frontend: Vercel or Render Static Site
Backend: Render Web Service
Database: Supabase Postgres
Auth: Supabase Auth
Storage: Supabase Storage
```

## Known Remaining Integration Work

- Verify Sarvam STT/TTS endpoint payloads with real credentials.
- Verify Exotel outbound/inbound/media webhook contracts with real credentials.
- Connect production billing provider if required.
- Implement full document text extraction, chunking, and embeddings after document upload.
