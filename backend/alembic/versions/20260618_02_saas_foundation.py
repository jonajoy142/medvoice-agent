"""SaaS foundation tables and RBAC policies

Revision ID: 20260618_02
Revises: 20260618_01
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260618_02"
down_revision = "20260618_01"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "departments", "doctors", "patients", "appointments", "calls", "transcripts",
    "conversation_turns", "intents", "escalations", "leads", "call_summaries",
    "knowledge_base_documents", "agent_configs", "consent_records", "audit_logs",
    "payment_reminders", "staff_users", "roles", "agents", "agent_versions",
    "knowledge_documents", "knowledge_chunks", "usage_events", "subscriptions",
    "hospital_settings", "agent_test_runs",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    _add_column_if_missing("staff_users", "role", "text NOT NULL DEFAULT 'staff'")
    _add_column_if_missing("staff_users", "updated_at", "timestamptz NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE staff_users ALTER COLUMN hospital_id DROP NOT NULL")

    _add_column_if_missing("hospitals", "status", "text NOT NULL DEFAULT 'active'")
    _add_column_if_missing("hospitals", "plan", "text NOT NULL DEFAULT 'pilot'")
    _add_column_if_missing("hospitals", "admin_email", "text")

    _add_column_if_missing("calls", "caller_phone", "text")
    _add_column_if_missing("calls", "agent_id", "uuid")
    _add_column_if_missing("calls", "appointment_status", "text")
    _add_column_if_missing("calls", "revenue_estimate", "numeric(12,2) DEFAULT 0")
    _add_column_if_missing("calls", "final_bill_amount", "numeric(12,2) DEFAULT 0")
    _add_column_if_missing("calls", "recording_url", "text")
    _add_column_if_missing("calls", "answered_by_ai", "boolean NOT NULL DEFAULT false")
    _add_column_if_missing("calls", "missed", "boolean NOT NULL DEFAULT false")
    _add_column_if_missing("calls", "response_latency_ms", "integer")

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(140), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("language", sa.String(32), nullable=False, server_default="en-IN"),
        sa.Column("voice_provider", sa.String(40), nullable=False, server_default="sarvam"),
        sa.Column("voice_name", sa.String(80), nullable=True),
        sa.Column("tts_pace", sa.Numeric(4, 2), nullable=False, server_default="1.0"),
        sa.Column("greeting", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("escalation_rules", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("working_hours", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("transfer_phone_number", sa.String(48), nullable=True),
        sa.Column("appointment_behavior", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("knowledge_source_ids", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("fallback_behavior", sa.Text, nullable=True),
        sa.Column("created_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "agent_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("created_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_type", sa.String(40), nullable=True),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column("source_type", sa.String(40), nullable=False, server_default="upload"),
        sa.Column("status", sa.String(40), nullable=False, server_default="processing"),
        sa.Column("chunks_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_index"),
    )
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL")

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(40), nullable=False, server_default="event"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("plan", sa.String(80), nullable=False, server_default="pilot"),
        sa.Column("status", sa.String(40), nullable=False, server_default="trialing"),
        sa.Column("billing_email", sa.String(255), nullable=True),
        sa.Column("monthly_call_limit", sa.Integer, nullable=True),
        sa.Column("current_period_start", sa.Date, nullable=True),
        sa.Column("current_period_end", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "hospital_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("business_hours", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("telephony", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("voice", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ai", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("security", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "agent_test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_message", sa.Text, nullable=False),
        sa.Column("agent_response", sa.Text, nullable=False),
        sa.Column("detected_intent", sa.String(80), nullable=True),
        sa.Column("matched_snippets", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    _indexes()
    _rls()


def downgrade() -> None:
    for table in ["agent_test_runs", "hospital_settings", "subscriptions", "usage_events", "knowledge_chunks", "knowledge_documents", "agent_versions", "agents"]:
        op.drop_table(table)


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")


def _indexes() -> None:
    for table in TENANT_TABLES:
        op.create_index(f"ix_{table}_hospital_id", table, ["hospital_id"], if_not_exists=True)
    for table, columns in {
        "agents": ["status", "updated_at"],
        "agent_versions": ["agent_id", "created_at"],
        "knowledge_documents": ["status", "updated_at"],
        "knowledge_chunks": ["document_id"],
        "usage_events": ["event_type", "created_at"],
        "subscriptions": ["status"],
        "agent_test_runs": ["agent_id", "created_at"],
        "calls": ["agent_id", "caller_phone", "appointment_status"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column], if_not_exists=True)
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)")


def _rls() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION medvoice_is_super_admin()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM staff_users
                WHERE supabase_user_id = auth.uid()
                  AND role = 'super_admin'
                  AND status = 'active'
            );
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION medvoice_has_hospital_access(target_hospital_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
            SELECT medvoice_is_super_admin() OR EXISTS (
                SELECT 1 FROM staff_users
                WHERE supabase_user_id = auth.uid()
                  AND hospital_id = target_hospital_id
                  AND status = 'active'
            );
        $$;
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS hospital_members_can_read_hospitals ON hospitals;
        CREATE POLICY hospital_members_can_read_hospitals ON hospitals
        FOR SELECT USING (medvoice_is_super_admin() OR medvoice_has_hospital_access(id));
        """
    )
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_select_{table} ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_write_{table} ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_select_{table} ON {table}
            FOR SELECT USING (medvoice_has_hospital_access(hospital_id))
            """
        )
        op.execute(
            f"""
            CREATE POLICY tenant_write_{table} ON {table}
            FOR ALL USING (medvoice_has_hospital_access(hospital_id))
            WITH CHECK (medvoice_has_hospital_access(hospital_id))
            """
        )
