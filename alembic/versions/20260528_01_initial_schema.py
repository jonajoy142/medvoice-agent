"""Initial MedVoice schema

Revision ID: 20260528_01
Revises: 
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa


revision = "20260528_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("opid", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("dob", sa.String(length=16), nullable=True),
        sa.Column("history", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("opid"),
    )
    op.create_index(op.f("ix_patients_opid"), "patients", ["opid"], unique=False)

    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=False),
        sa.Column("branch", sa.String(length=120), nullable=True),
        sa.Column("consultation_mode", sa.String(length=32), nullable=True),
        sa.Column("fee", sa.Integer(), nullable=True),
        sa.Column("languages", sa.Text(), nullable=True),
        sa.Column("slots", sa.Text(), nullable=True),
        sa.Column("available_days", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_doctors_id"), "doctors", ["id"], unique=False)
    op.create_index(op.f("ix_doctors_specialization"), "doctors", ["specialization"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_opid", sa.String(length=32), nullable=False),
        sa.Column("patient_name", sa.String(length=120), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=False),
        sa.Column("doctor_name", sa.String(length=120), nullable=True),
        sa.Column("requested_time", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_appointments_id"), "appointments", ["id"], unique=False)
    op.create_index(op.f("ix_appointments_patient_opid"), "appointments", ["patient_opid"], unique=False)

    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("opid", sa.String(length=32), nullable=True),
        sa.Column("patient_name", sa.String(length=120), nullable=True),
        sa.Column("last_doctor_list", sa.Text(), nullable=True),
        sa.Column("conversation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversation_sessions_id"), "conversation_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_conversation_sessions_opid"), "conversation_sessions", ["opid"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_session_id"), "audit_logs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_session_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_conversation_sessions_opid"), table_name="conversation_sessions")
    op.drop_index(op.f("ix_conversation_sessions_id"), table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
    op.drop_index(op.f("ix_appointments_patient_opid"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_id"), table_name="appointments")
    op.drop_table("appointments")
    op.drop_index(op.f("ix_doctors_specialization"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_id"), table_name="doctors")
    op.drop_table("doctors")
    op.drop_index(op.f("ix_patients_opid"), table_name="patients")
    op.drop_table("patients")
