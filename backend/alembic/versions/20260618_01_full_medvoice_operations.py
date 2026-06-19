"""Full MedVoice hospital operations schema

Revision ID: 20260618_01
Revises: 20260528_01
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260618_01"
down_revision = "20260528_01"
branch_labels = None
depends_on = None


REQUIRED_TABLES = [
    "hospitals",
    "departments",
    "doctors",
    "patients",
    "appointments",
    "calls",
    "transcripts",
    "conversation_turns",
    "intents",
    "escalations",
    "leads",
    "call_summaries",
    "knowledge_base_documents",
    "agent_configs",
    "consent_records",
    "audit_logs",
    "payment_reminders",
    "staff_users",
    "roles",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    _ensure_auth_uid_function()
    _create_enums()

    op.create_table(
        "hospitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("permissions", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("hospital_id", "name", name="uq_roles_hospital_name"),
    )

    op.create_table(
        "staff_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supabase_user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(140), nullable=False),
        sa.Column("routing_phone", sa.String(48), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("hospital_id", "name", name="uq_departments_hospital_name"),
    )

    _add_hospital_column("doctors")
    _add_hospital_column("patients")
    _add_hospital_column("appointments")
    _add_hospital_column("audit_logs")
    _add_column_if_missing("doctors", "department_id", "uuid")
    _add_column_if_missing("doctors", "status", "text DEFAULT 'active'")
    _add_column_if_missing("patients", "external_patient_id", "text")
    _add_column_if_missing("patients", "consent_status", "text DEFAULT 'unknown'")
    _add_column_if_missing("appointments", "appointment_time", "timestamptz")
    _add_column_if_missing("appointments", "source_call_id", "uuid")
    _add_column_if_missing("audit_logs", "actor_staff_user_id", "uuid")
    _add_column_if_missing("audit_logs", "resource_type", "text")
    _add_column_if_missing("audit_logs", "resource_id", "uuid")
    _add_column_if_missing("audit_logs", "event_json", "jsonb DEFAULT '{}'::jsonb")
    _add_column_if_missing("conversation_sessions", "recording_consent", "text DEFAULT 'false'")

    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_opid", sa.String(32), nullable=True),
        sa.Column("direction", _enum("call_direction", "inbound", "outbound"), nullable=False),
        sa.Column("workflow_type", sa.String(80), nullable=False),
        sa.Column("status", _enum("call_status", "active", "completed", "failed", "escalated"), nullable=False, server_default="active"),
        sa.Column("outcome", sa.String(120), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("language", sa.String(16), nullable=False, server_default="en-IN"),
        sa.Column("telephony_provider", sa.String(40), nullable=True),
        sa.Column("telephony_call_id", sa.String(160), nullable=True),
        sa.Column("consent_required", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("consent_granted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("redacted_text", sa.Text, nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_index", sa.Integer, nullable=False),
        sa.Column("speaker", sa.String(24), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("redacted_text", sa.Text, nullable=False),
        sa.Column("intent", sa.String(80), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("call_id", "turn_index", name="uq_turn_call_index"),
    )

    op.create_table(
        "intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("entities", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(160), nullable=False),
        sa.Column("severity", _enum("escalation_severity", "low", "medium", "high", "critical"), nullable=False),
        sa.Column("status", _enum("escalation_status", "open", "in_review", "resolved"), nullable=False, server_default="open"),
        sa.Column("assigned_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_opid", sa.String(32), nullable=True),
        sa.Column("service_interest", sa.String(160), nullable=False),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "call_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("intent", sa.String(80), nullable=False),
        sa.Column("discussed", sa.Text, nullable=False),
        sa.Column("decision", sa.String(160), nullable=True),
        sa.Column("follow_up_needed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("follow_up_notes", sa.Text, nullable=True),
        sa.Column("summary_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "knowledge_base_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("source_uri", sa.Text, nullable=True),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("embedding", sa.Text, nullable=True),
        sa.Column("content_gap_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute("ALTER TABLE knowledge_base_documents ALTER COLUMN embedding TYPE vector(1536) USING NULL")

    op.create_table(
        "agent_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("language_pair", sa.String(64), nullable=False, server_default="en-IN/ml-IN"),
        sa.Column("llm_provider", sa.String(40), nullable=False, server_default="openai"),
        sa.Column("stt_provider", sa.String(40), nullable=False, server_default="sarvam"),
        sa.Column("tts_provider", sa.String(40), nullable=False, server_default="sarvam"),
        sa.Column("guardrail_config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=True),
        sa.Column("patient_opid", sa.String(32), nullable=True),
        sa.Column("consent_type", sa.String(80), nullable=False),
        sa.Column("granted", sa.Boolean, nullable=False),
        sa.Column("captured_by", sa.String(80), nullable=False, server_default="voice_agent"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "payment_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_opid", sa.String(32), nullable=True),
        sa.Column("amount_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("script", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    _create_indexes()
    _enable_rls()


def downgrade() -> None:
    for table in [
        "payment_reminders",
        "consent_records",
        "agent_configs",
        "knowledge_base_documents",
        "call_summaries",
        "leads",
        "escalations",
        "intents",
        "conversation_turns",
        "transcripts",
        "calls",
        "departments",
        "staff_users",
        "roles",
        "hospitals",
    ]:
        op.drop_table(table)
    for enum in ["escalation_status", "escalation_severity", "call_status", "call_direction"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")


def _create_enums() -> None:
    for name, values in {
        "call_direction": ("inbound", "outbound"),
        "call_status": ("active", "completed", "failed", "escalated"),
        "escalation_severity": ("low", "medium", "high", "critical"),
        "escalation_status": ("open", "in_review", "resolved"),
    }.items():
        quoted_values = ", ".join(f"'{value}'" for value in values)
        op.execute(
            f"""
            DO $$
            BEGIN
                CREATE TYPE {name} AS ENUM ({quoted_values});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$;
            """
        )


def _ensure_auth_uid_function() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'auth' AND p.proname = 'uid' AND pg_get_function_arguments(p.oid) = ''
            ) THEN
                CREATE FUNCTION auth.uid()
                RETURNS uuid
                LANGUAGE sql
                STABLE
                AS $fn$
                    SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
                $fn$;
            END IF;
        END
        $$;
        """
    )


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def _add_hospital_column(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS hospital_id uuid")
    op.create_index(f"ix_{table}_hospital_id", table, ["hospital_id"], if_not_exists=True)


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")


def _create_indexes() -> None:
    for table in REQUIRED_TABLES:
        if table not in {"hospitals", "roles"}:
            op.create_index(f"ix_{table}_hospital_id", table, ["hospital_id"], if_not_exists=True)
    indexed = {
        "calls": ["started_at", "status", "workflow_type", "telephony_call_id"],
        "transcripts": ["call_id", "created_at"],
        "conversation_turns": ["call_id", "created_at"],
        "intents": ["call_id", "name", "created_at"],
        "escalations": ["call_id", "status", "created_at"],
        "leads": ["call_id", "status", "created_at"],
        "call_summaries": ["call_id", "created_at"],
        "knowledge_base_documents": ["status", "created_at"],
        "consent_records": ["call_id", "patient_opid", "captured_at"],
        "audit_logs": ["created_at", "event_type"],
        "payment_reminders": ["status", "due_date"],
    }
    for table, columns in indexed.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column], if_not_exists=True)
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_embedding ON knowledge_base_documents USING ivfflat (embedding vector_cosine_ops)")


def _enable_rls() -> None:
    for table in REQUIRED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        if table == "hospitals":
            op.execute(
                """
                CREATE POLICY hospital_members_can_read_hospitals ON hospitals
                FOR SELECT USING (
                  id IN (SELECT hospital_id FROM staff_users WHERE supabase_user_id = auth.uid())
                )
                """
            )
        else:
            op.execute(
                f"""
                CREATE POLICY tenant_select_{table} ON {table}
                FOR SELECT USING (
                  hospital_id IN (SELECT hospital_id FROM staff_users WHERE supabase_user_id = auth.uid())
                )
                """
            )
            op.execute(
                f"""
                CREATE POLICY tenant_write_{table} ON {table}
                FOR ALL USING (
                  hospital_id IN (SELECT hospital_id FROM staff_users WHERE supabase_user_id = auth.uid())
                ) WITH CHECK (
                  hospital_id IN (SELECT hospital_id FROM staff_users WHERE supabase_user_id = auth.uid())
                )
                """
            )
