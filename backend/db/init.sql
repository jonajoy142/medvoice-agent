CREATE TABLE IF NOT EXISTS bootstrap_marker (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW()
);

-- NOTE:
-- Domain tables are managed by SQLAlchemy metadata bootstrap in app startup for now.
-- TODO(SUPABASE): move this to Alembic migrations when managed Postgres is enabled.
