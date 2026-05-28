from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repo import mock_db


class MockPatientRepository:
    def get_patient(self, opid: str) -> Optional[Dict[str, Any]]:
        return mock_db.get_patient(opid)


class MockDoctorRepository:
    def get_doctors(self, specialization: Optional[str] = None) -> Any:
        return mock_db.get_doctors(specialization)


class MockAppointmentRepository:
    def add_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        return mock_db.add_appointment(appointment_data)

    def list_appointments(self) -> List[Dict[str, Any]]:
        return mock_db.get_appointments()


class MockSessionRepository:
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return mock_db.get_session(session_id)

    def create_session(self, session_id: str) -> Dict[str, Any]:
        return mock_db.create_session(session_id)

    def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return mock_db.update_session(session_id, data)
