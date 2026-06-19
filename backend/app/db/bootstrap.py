from app.db.base import Base
from app.db.session import get_engine
from sqlalchemy import text
import app.models  # noqa: F401


def bootstrap_database() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        for column, definition in {
            "selected_receptionist_id": "text",
            "hospital_id": "text",
            "current_intent": "text",
            "slots": "text",
            "missing_slots": "text",
            "last_assistant_question": "text",
            "workflow_state": "text",
        }.items():
            connection.execute(text(f"ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS {column} {definition}"))
