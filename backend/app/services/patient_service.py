from __future__ import annotations

from typing import Any, Dict, Optional

from app.repositories import patient_repository


class PatientService:
    def get_by_opid(self, opid: str) -> Optional[Dict[str, Any]]:
        return patient_repository().get_patient(opid)


patient_service = PatientService()
