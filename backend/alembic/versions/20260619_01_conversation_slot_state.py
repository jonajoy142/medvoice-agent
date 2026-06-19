"""Persist conversation slot state.

Revision ID: 20260619_01
Revises: 20260618_04
Create Date: 2026-06-19
"""

from alembic import op


revision = "20260619_01"
down_revision = "20260618_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        "selected_receptionist_id": "text",
        "hospital_id": "text",
        "current_intent": "text",
        "slots": "text",
        "missing_slots": "text",
        "last_assistant_question": "text",
        "workflow_state": "text",
    }
    for column, definition in columns.items():
        op.execute(f"ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS {column} {definition}")


def downgrade() -> None:
    for column in (
        "workflow_state",
        "last_assistant_question",
        "missing_slots",
        "slots",
        "current_intent",
        "hospital_id",
        "selected_receptionist_id",
    ):
        op.execute(f"ALTER TABLE conversation_sessions DROP COLUMN IF EXISTS {column}")
