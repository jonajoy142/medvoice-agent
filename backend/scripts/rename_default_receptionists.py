from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import db_session


DEFAULT_RECEPTIONISTS = [
    (
        "Emma",
        "Emma",
        "Front Desk Receptionist",
        "Hi, this is Emma from the front desk. I can help you book, reschedule, or reach the right person.",
    ),
    (
        "Maya",
        "Maya",
        "Appointment Coordinator",
        "Hi, this is Maya. I can help find an appointment time and confirm the next step.",
    ),
    (
        "Sara",
        "Sarah",
        "Patient Follow-up Specialist",
        "Hi, this is Sarah. I can help with reminders, confirmations, and follow-up calls.",
    ),
    (
        "Daniel",
        "David",
        "Department Routing Assistant",
        "Hi, this is David. I can understand what you need and connect you to the right department.",
    ),
    (
        "Thomas",
        "Priya",
        "Patient Support Assistant",
        "Hi, this is Priya. I can answer front desk questions or arrange a staff callback.",
    ),
]

OLD_DESCRIPTIONS = ("Appointments", "Reception", "Follow Ups", "Lead Qualification", "Call Transfer")


def main() -> None:
    with db_session() as db:
        for old_name, new_name, description, greeting in DEFAULT_RECEPTIONISTS:
            db.execute(
                text(
                    """
                    UPDATE agents
                    SET name=:new_name, description=:description, greeting=:greeting, updated_at=now()
                    WHERE name=:old_name AND description = ANY(:old_descriptions)
                    """
                ),
                {
                    "old_name": old_name,
                    "new_name": new_name,
                    "description": description,
                    "greeting": greeting,
                    "old_descriptions": list(OLD_DESCRIPTIONS),
                },
            )
    print("Updated default receptionist placeholders.")


if __name__ == "__main__":
    main()
