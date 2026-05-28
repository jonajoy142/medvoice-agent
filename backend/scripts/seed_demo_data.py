from app.db.session import db_session
from app.models.doctor import Doctor
from app.models.patient import Patient


def seed() -> None:
    with db_session() as db:
        if db.query(Patient).count() == 0:
            db.add_all(
                [
                    Patient(opid="411326", name="Jonah Carlisle", phone="+1-555-0123", history="eczema,skin allergy"),
                    Patient(opid="411327", name="Sarah Johnson", phone="+1-555-0124", history="acne,dry skin"),
                ]
            )
        if db.query(Doctor).count() == 0:
            db.add_all(
                [
                    Doctor(
                        name="Meera",
                        specialization="dermatologist",
                        branch="City Center",
                        consultation_mode="in-person",
                        fee=900,
                        languages="English,Hindi",
                        slots="10:00,11:00,14:00,15:00",
                        available_days="Monday,Wednesday,Friday",
                    ),
                    Doctor(
                        name="Arjun Rao",
                        specialization="cardiologist",
                        branch="Main Block",
                        consultation_mode="hybrid",
                        fee=1500,
                        languages="English,Hindi,Tamil",
                        slots="09:00,12:00,16:00",
                        available_days="Tuesday,Thursday",
                    ),
                ]
            )


if __name__ == "__main__":
    seed()
    print("Demo data seeded.")
