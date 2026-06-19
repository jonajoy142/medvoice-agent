from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.db.session import db_session
from app.models.appointment import Appointment
from app.models.conversation_session import ConversationSession
from app.models.doctor import Doctor
from app.models.patient import Patient


class SqlPatientRepository:
    def get_patient(self, opid: str) -> Optional[Dict[str, Any]]:
        with db_session() as db:
            patient = db.get(Patient, opid)
            if not patient:
                return None
            history = patient.history.split(",") if patient.history else []
            return {
                "name": patient.name,
                "history": [item.strip() for item in history if item.strip()],
                "phone": patient.phone,
                "email": patient.email,
                "dob": patient.dob,
            }


class SqlDoctorRepository:
    def get_doctors(self, specialization: Optional[str] = None) -> Any:
        with db_session() as db:
            query = select(Doctor)
            if specialization:
                query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))
                doctors = db.execute(query).scalars().all()
                return [self._to_dict(doc) for doc in doctors]

            doctors = db.execute(query).scalars().all()
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for doctor in doctors:
                key = (doctor.specialization or "general").lower()
                grouped.setdefault(key, []).append(self._to_dict(doctor))
            return grouped

    @staticmethod
    def _to_dict(doctor: Doctor) -> Dict[str, Any]:
        return {
            "name": doctor.name,
            "specialization": doctor.specialization,
            "branch": doctor.branch,
            "consultation_mode": doctor.consultation_mode,
            "fee": doctor.fee,
            "languages": (doctor.languages.split(",") if doctor.languages else []),
            "slots": (doctor.slots.split(",") if doctor.slots else []),
            "available_days": (doctor.available_days.split(",") if doctor.available_days else []),
        }


class SqlAppointmentRepository:
    def add_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        with db_session() as db:
            row = Appointment(
                patient_opid=appointment_data["patient_opid"],
                patient_name=appointment_data["patient_name"],
                specialization=appointment_data["specialization"],
                doctor_name=appointment_data.get("doctor_name"),
                requested_time=appointment_data["requested_time"],
                status=appointment_data.get("status", "pending"),
            )
            db.add(row)
            db.flush()
            return self._to_dict(row)

    def list_appointments(self) -> List[Dict[str, Any]]:
        with db_session() as db:
            rows = db.execute(select(Appointment).order_by(Appointment.id.desc())).scalars().all()
            return [self._to_dict(row) for row in rows]

    @staticmethod
    def _to_dict(row: Appointment) -> Dict[str, Any]:
        return {
            "id": row.id,
            "patient_opid": row.patient_opid,
            "patient_name": row.patient_name,
            "specialization": row.specialization,
            "doctor_name": row.doctor_name,
            "requested_time": row.requested_time,
            "status": row.status,
        }


class SqlSessionRepository:
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with db_session() as db:
            row = db.get(ConversationSession, session_id)
            if not row:
                return None
            return {
                "conversation": json.loads(row.conversation) if row.conversation else [],
                "opid": row.opid,
                "patient_name": row.patient_name,
                "last_doctor_list": json.loads(row.last_doctor_list) if row.last_doctor_list else [],
                "recording_consent": row.recording_consent == "true",
                "selected_receptionist_id": row.selected_receptionist_id,
                "hospital_id": row.hospital_id,
                "current_intent": row.current_intent,
                "slots": json.loads(row.slots) if row.slots else {},
                "missing_slots": json.loads(row.missing_slots) if row.missing_slots else [],
                "last_assistant_question": row.last_assistant_question,
                "workflow_state": row.workflow_state,
            }

    def create_session(self, session_id: str) -> Dict[str, Any]:
        with db_session() as db:
            row = ConversationSession(
                id=session_id,
                conversation="[]",
                last_doctor_list="[]",
                recording_consent="false",
                slots="{}",
                missing_slots="[]",
                workflow_state="idle",
            )
            db.add(row)
            db.flush()
        return {
            "conversation": [],
            "opid": None,
            "patient_name": None,
            "last_doctor_list": [],
            "recording_consent": False,
            "selected_receptionist_id": None,
            "hospital_id": None,
            "current_intent": None,
            "slots": {},
            "missing_slots": [],
            "last_assistant_question": None,
            "workflow_state": "idle",
        }

    def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with db_session() as db:
            row = db.get(ConversationSession, session_id)
            if not row:
                return None
            if "conversation" in data:
                row.conversation = json.dumps(data["conversation"])
            if "opid" in data:
                row.opid = data["opid"]
            if "patient_name" in data:
                row.patient_name = data["patient_name"]
            if "last_doctor_list" in data:
                row.last_doctor_list = json.dumps(data["last_doctor_list"])
            if "recording_consent" in data:
                row.recording_consent = "true" if data["recording_consent"] else "false"
            if "selected_receptionist_id" in data:
                row.selected_receptionist_id = data["selected_receptionist_id"]
            if "hospital_id" in data:
                row.hospital_id = data["hospital_id"]
            if "current_intent" in data:
                row.current_intent = data["current_intent"]
            if "slots" in data:
                row.slots = json.dumps(data["slots"])
            if "missing_slots" in data:
                row.missing_slots = json.dumps(data["missing_slots"])
            if "last_assistant_question" in data:
                row.last_assistant_question = data["last_assistant_question"]
            if "workflow_state" in data:
                row.workflow_state = data["workflow_state"]
            db.flush()
            return {
                "conversation": json.loads(row.conversation) if row.conversation else [],
                "opid": row.opid,
                "patient_name": row.patient_name,
                "last_doctor_list": json.loads(row.last_doctor_list) if row.last_doctor_list else [],
                "recording_consent": row.recording_consent == "true",
                "selected_receptionist_id": row.selected_receptionist_id,
                "hospital_id": row.hospital_id,
                "current_intent": row.current_intent,
                "slots": json.loads(row.slots) if row.slots else {},
                "missing_slots": json.loads(row.missing_slots) if row.missing_slots else [],
                "last_assistant_question": row.last_assistant_question,
                "workflow_state": row.workflow_state,
            }
