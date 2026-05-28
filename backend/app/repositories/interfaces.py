from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class PatientRepository(Protocol):
    def get_patient(self, opid: str) -> Optional[Dict[str, Any]]:
        ...


class DoctorRepository(Protocol):
    def get_doctors(self, specialization: Optional[str] = None) -> Any:
        ...


class AppointmentRepository(Protocol):
    def add_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def list_appointments(self) -> List[Dict[str, Any]]:
        ...


class SessionRepository(Protocol):
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        ...

    def create_session(self, session_id: str) -> Dict[str, Any]:
        ...

    def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...
