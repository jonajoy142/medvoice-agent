from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.api.v1.routes_saas import _create_or_get_supabase_user, _ensure_default_agent
from app.db.session import db_session

PASSWORD = "Password123!"
SUPER_EMAIL = "superadmin@medvoice.test"
ADMIN_EMAIL = "admin@demo-hospital.test"
STAFF_EMAIL = "staff@demo-hospital.test"


def main() -> None:
    super_id = _create_or_get_supabase_user(SUPER_EMAIL, PASSWORD, "MedVoice Super Admin")
    admin_id = _create_or_get_supabase_user(ADMIN_EMAIL, PASSWORD, "Demo Hospital Admin")
    staff_id = _create_or_get_supabase_user(STAFF_EMAIL, PASSWORD, "Demo Hospital Staff")

    with db_session() as db:
        hospital = db.execute(
            text(
                """
                INSERT INTO hospitals (name, slug, phone, timezone, status, plan, admin_email)
                VALUES ('Demo Hospital', 'demo-hospital', '+919999999999', 'Asia/Kolkata', 'active', 'pilot', :admin_email)
                ON CONFLICT (slug) DO UPDATE SET name=excluded.name, phone=excluded.phone, updated_at=now()
                RETURNING *
                """
            ),
            {"admin_email": ADMIN_EMAIL},
        ).mappings().one()
        hospital_id = hospital["id"]
        db.execute(text("INSERT INTO hospital_settings (hospital_id) VALUES (:hospital_id) ON CONFLICT DO NOTHING"), {"hospital_id": hospital_id})
        db.execute(text("INSERT INTO subscriptions (hospital_id, plan, status, billing_email) VALUES (:hospital_id, 'pilot', 'trialing', :email) ON CONFLICT DO NOTHING"), {"hospital_id": hospital_id, "email": ADMIN_EMAIL})
        _staff(db, None, super_id, SUPER_EMAIL, "MedVoice Super Admin", "super_admin")
        _staff(db, hospital_id, admin_id, ADMIN_EMAIL, "Demo Hospital Admin", "hospital_admin")
        _staff(db, hospital_id, staff_id, STAFF_EMAIL, "Demo Hospital Staff", "staff")
        primary_agent = _ensure_default_agent(db, hospital_id)
        second_agent = db.execute(
            text(
                """
                INSERT INTO agents (hospital_id, name, description, status, language, voice_provider, voice_name, voice, greeting, system_prompt, fallback_behavior)
                VALUES (:hospital_id, 'Malayalam Front Desk', 'Malayalam receptionist for routing and appointments.', 'active', 'ml-IN', 'sarvam', 'Meera', 'Meera', 'Namaskaram, hospital assistant aanu. Engane sahayikkam?', 'Handle hospital operations in Malayalam and English. Escalate emergencies. Do not provide medical advice.', 'I can help with hospital operations and connect you to staff when needed.')
                ON CONFLICT DO NOTHING
                RETURNING *
                """
            ),
            {"hospital_id": hospital_id},
        ).mappings().first()
        agent_ids = [primary_agent["id"]]
        if second_agent:
            agent_ids.append(second_agent["id"])
        _knowledge(db, hospital_id)
        _calls(db, hospital_id, agent_ids)
    print("Demo seed complete. Users: superadmin@medvoice.test, admin@demo-hospital.test, staff@demo-hospital.test")


def _staff(db, hospital_id, user_id: str, email: str, full_name: str, role: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO staff_users (hospital_id, supabase_user_id, email, full_name, role, status)
            VALUES (:hospital_id, :supabase_user_id, :email, :full_name, :role, 'active')
            ON CONFLICT (supabase_user_id) DO UPDATE SET hospital_id=excluded.hospital_id, email=excluded.email, full_name=excluded.full_name, role=excluded.role, status='active', updated_at=now()
            """
        ),
        {"hospital_id": hospital_id, "supabase_user_id": user_id, "email": email, "full_name": full_name, "role": role},
    )


def _knowledge(db, hospital_id) -> None:
    db.execute(
        text(
            """
            INSERT INTO knowledge_documents (hospital_id, title, source_type, status, file_name, file_type, chunks_count, file_url)
            VALUES (:hospital_id, 'Demo Hospital FAQ', 'upload', 'active', 'demo-faq.md', 'md', 2, NULL)
            """
        ),
        {"hospital_id": hospital_id},
    )


def _calls(db, hospital_id, agent_ids: list) -> None:
    for idx in range(8):
        agent_id = agent_ids[idx % len(agent_ids)] if agent_ids else None
        booked = idx in {0, 2, 4, 6}
        status = "completed" if idx != 3 else "escalated"
        outcome = "appointment_booked" if booked else "faq_resolved"
        call = db.execute(
            text(
                """
                INSERT INTO calls (hospital_id, agent_id, caller_phone, caller_name, direction, workflow_type, status, outcome, duration_seconds, started_at, ended_at, language, consent_granted, answered_by_ai, missed, appointment_status, revenue_estimate, estimated_revenue, final_bill_amount, response_latency_ms, summary, appointment_booked)
                VALUES (:hospital_id, :agent_id, :phone, :name, 'inbound', :workflow, :status, :outcome, :duration, now() - (:idx || ' hours')::interval, now() - (:idx || ' hours')::interval + (:duration || ' seconds')::interval, :language, true, :answered_by_ai, false, :appointment_status, :revenue, :revenue, :final_bill, :latency, :summary, :booked)
                RETURNING id
                """
            ),
            {
                "hospital_id": hospital_id,
                "agent_id": agent_id,
                "phone": f"+9198765400{idx}",
                "name": f"Caller {idx + 1}",
                "workflow": "appointment_booking" if booked else "faq",
                "status": status,
                "outcome": outcome,
                "duration": 110 + idx * 18,
                "idx": idx,
                "language": "ml-IN" if idx % 3 == 0 else "en-IN",
                "answered_by_ai": idx != 3,
                "appointment_status": "confirmed" if booked else "none",
                "revenue": 1500 + idx * 350 if booked else 0,
                "final_bill": 1200 + idx * 250 if booked else 0,
                "latency": 720 + idx * 25,
                "summary": "Operational call handled by AI receptionist. No clinical record stored.",
                "booked": booked,
            },
        ).scalar_one()
        db.execute(text("INSERT INTO call_summaries (hospital_id, call_id, intent, discussed, decision, follow_up_needed) VALUES (:hospital_id, :call_id, :intent, :discussed, :decision, :follow_up)"), {"hospital_id": hospital_id, "call_id": call, "intent": "appointment_booking" if booked else "faq", "discussed": "Caller requested hospital operations support.", "decision": outcome, "follow_up": not booked})
        db.execute(text("INSERT INTO conversation_turns (hospital_id, call_id, turn_index, speaker, text, message, intent, confidence, latency_ms) VALUES (:hospital_id, :call_id, 1, 'caller', 'I need help with an appointment', 'I need help with an appointment', :intent, 0.91, 650)"), {"hospital_id": hospital_id, "call_id": call, "intent": "book_appointment" if booked else "faq"})


if __name__ == "__main__":
    main()
