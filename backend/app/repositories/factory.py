from __future__ import annotations

from app.core.config import settings
from app.db.session import check_db_connection
from app.repositories.mock_repositories import (
    MockAppointmentRepository,
    MockDoctorRepository,
    MockPatientRepository,
    MockSessionRepository,
)
from app.repositories.sqlalchemy_repositories import (
    SqlAppointmentRepository,
    SqlDoctorRepository,
    SqlPatientRepository,
    SqlSessionRepository,
)


def _use_sql() -> bool:
    return settings.use_database and check_db_connection()


def patient_repository():
    return SqlPatientRepository() if _use_sql() else MockPatientRepository()


def doctor_repository():
    return SqlDoctorRepository() if _use_sql() else MockDoctorRepository()


def appointment_repository():
    return SqlAppointmentRepository() if _use_sql() else MockAppointmentRepository()


def session_repository():
    return SqlSessionRepository() if _use_sql() else MockSessionRepository()
