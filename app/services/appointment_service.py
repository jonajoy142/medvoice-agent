from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories import appointment_repository, doctor_repository, patient_repository


class AppointmentService:
    def book(self, patient_opid: str, specialization: str, preferred_time: str, doctor_name: Optional[str] = None) -> Dict[str, Any]:
        patient = patient_repository().get_patient(patient_opid)
        if not patient:
            raise ValueError("Patient not found")

        doctors = doctor_repository().get_doctors(specialization)
        if not doctors:
            raise LookupError("No doctors available for this specialization")

        appointment_data = {
            "patient_opid": patient_opid,
            "patient_name": patient["name"],
            "specialization": specialization,
            "requested_time": preferred_time,
            "doctor_name": doctor_name or doctors[0]["name"],
            "status": "confirmed",
        }
        return appointment_repository().add_appointment(appointment_data)

    def list(self, patient_opid: Optional[str] = None) -> List[Dict[str, Any]]:
        items = appointment_repository().list_appointments()
        if not patient_opid:
            return items
        return [item for item in items if item.get("patient_opid") == patient_opid]


appointment_service = AppointmentService()
