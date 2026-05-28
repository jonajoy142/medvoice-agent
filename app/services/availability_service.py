from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories import doctor_repository


class AvailabilityService:
    def get(self, specialization: Optional[str] = None) -> Dict[str, Any]:
        repo = doctor_repository()
        if specialization:
            doctors = repo.get_doctors(specialization)
            return {"specialization": specialization, "doctors": doctors, "count": len(doctors)}

        grouped = repo.get_doctors()
        all_doctors: List[Dict[str, Any]] = []
        for spec, items in grouped.items():
            for doctor in items:
                row = dict(doctor)
                row["specialization"] = row.get("specialization") or spec
                all_doctors.append(row)
        return {"specialization": None, "doctors": all_doctors, "count": len(all_doctors)}


availability_service = AvailabilityService()
