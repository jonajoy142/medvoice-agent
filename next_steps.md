# MedVoice Next Steps

## Completed In This Pass

- Reworked the active product UI into a restrained enterprise SaaS shell: neutral app background, dark sidebar, compact topbar, clean tables, simple metric cards, and one primary accent color.
- Removed the kid-style marketing/tour treatment from auth pages.
- Added real `/auth/register` support that creates/fetches a Supabase Auth user, creates a hospital workspace, creates the `staff_users` mapping, assigns `hospital_admin`, and returns role/hospital/permissions data.
- Exposed clean auth endpoints (`/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/invite-staff`) while keeping `/api/v1/auth/...` compatibility.
- Updated redirects to `/admin` for `super_admin` and `/overview` for hospital roles.
- Added role-specific frontend navigation and client-side guards for super-admin/staff-only restrictions.
- Added Contacts page based on real call rows and allowed business fields only.
- Added `scripts/create_super_admin.py` for env-only super-admin creation.
- Added `POST /auth/invite-staff` backend endpoint for hospital admin staff creation.
- Confirmed backend compile succeeds.
- Confirmed frontend production build succeeds.
- Confirmed backend tests pass: `29 passed, 1 skipped`.

## Still Needs Real Credentials / External Verification

1. Live Supabase Auth registration/login must be verified with your real `SUPABASE_URL`, anon key, service role key, and Postgres connection string.
2. `scripts/create_super_admin.py` requires `SEED_SUPER_ADMIN_EMAIL`, `SEED_SUPER_ADMIN_PASSWORD`, and backend Supabase service credentials.
3. Supabase Storage upload path exists, but production document extraction/chunking/embedding worker is not complete.
4. Sarvam STT/TTS endpoint payloads still need validation with real Sarvam credentials.
5. Exotel inbound/outbound/media webhook behavior still needs validation with real Exotel credentials.
6. Billing schema/UI exists, but no payment provider is connected yet.
7. `poetry.lock` should be refreshed in a network-enabled environment if dependency resolution changes are required.

## Prioritized Backlog

1. Fill real Supabase env vars, run migrations, run `scripts/create_super_admin.py`, and verify `/register`, `/login`, and `/auth/me` end-to-end.
2. Add frontend Team invite form wired to `POST /auth/invite-staff`.
3. Add KB background worker for PDF/DOCX/TXT/Markdown parsing, chunking, embeddings, and reprocess status.
4. Add agent archive/delete endpoint and UI action if hospital admins need lifecycle cleanup.
5. Add env-gated integration tests for live Supabase registration, Supabase Storage, Sarvam, and Exotel.
6. Connect billing provider when pricing and invoicing decisions are finalized.
