"""Add SaaS onboarding requests

Revision ID: 20260618_03
Revises: 20260618_02
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260618_03"
down_revision = "20260618_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supabase_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("work_email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("hospital_name", sa.String(180), nullable=False),
        sa.Column("phone", sa.String(48), nullable=True),
        sa.Column("role_requested", sa.String(64), nullable=False, server_default="hospital_admin"),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("approved_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_email_status", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_onboarding_requests_status", "onboarding_requests", ["status"], if_not_exists=True)
    op.create_index("ix_onboarding_requests_work_email", "onboarding_requests", ["work_email"], if_not_exists=True)
    op.execute("ALTER TABLE onboarding_requests ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY super_admin_onboarding_access ON onboarding_requests
        FOR ALL USING (medvoice_is_super_admin())
        WITH CHECK (medvoice_is_super_admin())
        """
    )


def downgrade() -> None:
    op.drop_table("onboarding_requests")
