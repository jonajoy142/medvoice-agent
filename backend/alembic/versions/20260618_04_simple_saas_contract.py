"""Align simple SaaS contract columns

Revision ID: 20260618_04
Revises: 20260618_03
Create Date: 2026-06-18
"""
from alembic import op


revision = "20260618_04"
down_revision = "20260618_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE hospitals ADD COLUMN IF NOT EXISTS phone text")
    op.execute("ALTER TABLE hospitals ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'Asia/Kolkata'")
    op.execute("ALTER TABLE staff_users ADD COLUMN IF NOT EXISTS phone text")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS voice text")
    op.execute("UPDATE agents SET voice = coalesce(voice, voice_name) WHERE voice IS NULL")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS transfer_phone text")
    op.execute("UPDATE agents SET transfer_phone = coalesce(transfer_phone, transfer_phone_number) WHERE transfer_phone IS NULL")
    op.execute("ALTER TABLE calls ADD COLUMN IF NOT EXISTS caller_name text")
    op.execute("ALTER TABLE calls ADD COLUMN IF NOT EXISTS summary text")
    op.execute("ALTER TABLE calls ADD COLUMN IF NOT EXISTS estimated_revenue numeric DEFAULT 0")
    op.execute("UPDATE calls SET estimated_revenue = coalesce(estimated_revenue, revenue_estimate, 0) WHERE estimated_revenue IS NULL")
    op.execute("ALTER TABLE calls ADD COLUMN IF NOT EXISTS appointment_booked boolean DEFAULT false")
    op.execute("UPDATE calls SET appointment_booked = true WHERE appointment_status = 'confirmed' AND appointment_booked IS NOT TRUE")
    op.execute("ALTER TABLE conversation_turns ADD COLUMN IF NOT EXISTS message text")
    op.execute("UPDATE conversation_turns SET message = coalesce(message, text) WHERE message IS NULL")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS file_url text")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS actor_user_id uuid")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS action text")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_type text")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_id uuid")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb")


def downgrade() -> None:
    pass
