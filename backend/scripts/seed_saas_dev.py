from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from sqlalchemy import text

from app.core.config import settings
from app.db.session import db_session
from app.api.v1.routes_saas import _default_agent_specs


def main() -> None:
    os.environ.setdefault("SEED_HOSPITAL_ADMIN_EMAIL", "admin@demo.com")
    os.environ.setdefault("SEED_DEFAULT_PASSWORD", "Demo123!")
    hospital_id = str(uuid4())
    admin_user_id = _resolve_user_id("SEED_HOSPITAL_ADMIN")
    staff_user_id = _resolve_user_id("SEED_STAFF")
    super_user_id = _resolve_user_id("SEED_SUPER_ADMIN")
    admin_email = os.getenv("SEED_HOSPITAL_ADMIN_EMAIL", "admin@demo.com")
    with db_session() as db:
        existing = db.execute(text("SELECT id FROM hospitals WHERE slug='demo-dental' LIMIT 1")).scalar()
        if existing:
            hospital_id = str(existing)
            db.execute(text("UPDATE hospitals SET name='Demo Dental', admin_email=:admin_email, status='active', plan='pilot', updated_at=now() WHERE id=:id"), {"id": hospital_id, "admin_email": admin_email})
        else:
            db.execute(text("""
                INSERT INTO hospitals (id, name, slug, timezone, status, plan, admin_email)
                VALUES (:id, 'Demo Dental', 'demo-dental', 'Asia/Kolkata', 'active', 'pilot', :admin_email)
            """), {"id": hospital_id, "admin_email": admin_email})
            db.execute(text("INSERT INTO subscriptions (hospital_id, plan, status, billing_email) VALUES (:id, 'pilot', 'trialing', :email) ON CONFLICT DO NOTHING"), {"id": hospital_id, "email": admin_email})
            db.execute(text("INSERT INTO hospital_settings (hospital_id, business_hours, telephony, voice, ai, security) VALUES (:id, CAST(:hours AS jsonb), CAST(:telephony AS jsonb), CAST(:voice AS jsonb), CAST(:ai AS jsonb), CAST(:security AS jsonb)) ON CONFLICT DO NOTHING"), {
                "id": hospital_id,
                "hours": _json_param({"mon_fri": "09:00-18:00", "sat": "09:00-13:00"}),
                "telephony": _json_param({"provider": "exotel", "status": "not_configured"}),
                "voice": _json_param({"provider": "sarvam", "languages": ["en-IN", "ml-IN"]}),
                "ai": _json_param({"provider": settings.llm_provider, "low_confidence_threshold": settings.low_confidence_threshold}),
                "security": _json_param({"rbac": True, "rls": True}),
            })
        _staff(db, hospital_id, super_user_id, os.getenv("SEED_SUPER_ADMIN_EMAIL"), "MedVoice Super Admin", "super_admin")
        _staff(db, hospital_id, admin_user_id, admin_email, "Demo Dental Admin", "hospital_admin")
        _staff(db, hospital_id, staff_user_id, os.getenv("SEED_STAFF_EMAIL"), "Demo Reception Staff", "staff")
        agent_ids = _agents(db, hospital_id)
        _sample_business_data(db, hospital_id, agent_ids)
    print("Seed complete. Demo Dental is populated. Login: admin@demo.com / Demo123! when Supabase service credentials are configured.")


def _staff(db, hospital_id: str, user_id: str | None, email: str | None, full_name: str, role: str) -> None:
    if not user_id or not email:
        print(f"Skipped {role}: set SEED_{role.upper()}_EMAIL and either SEED_{role.upper()}_USER_ID or SEED_DEFAULT_PASSWORD with server admin credentials.")
        return
    db.execute(text("""
        INSERT INTO staff_users (hospital_id, supabase_user_id, email, full_name, role, status)
        VALUES (:hospital_id, :supabase_user_id, :email, :full_name, :role, 'active')
        ON CONFLICT (supabase_user_id) DO UPDATE SET email=excluded.email, full_name=excluded.full_name, role=excluded.role, status='active', updated_at=now()
    """), {"hospital_id": None if role == "super_admin" else hospital_id, "supabase_user_id": user_id, "email": email, "full_name": full_name, "role": role})


def _agents(db, hospital_id: str) -> list[str]:
    agent_ids = []
    for spec in _default_agent_specs():
        existing = db.execute(text("SELECT id FROM agents WHERE hospital_id=:hospital_id AND name=:name LIMIT 1"), {"hospital_id": hospital_id, "name": spec["name"]}).scalar()
        if existing:
            agent_ids.append(str(existing))
            continue
        row = db.execute(text("""
            INSERT INTO agents (hospital_id, name, description, status, language, voice_provider, voice_name, greeting, system_prompt, fallback_behavior, transfer_phone_number, working_hours)
            VALUES (:hospital_id, :name, :description, 'active', :language, 'sarvam', :voice_name, :greeting, :system_prompt, :fallback_behavior, :transfer_phone_number, CAST(:working_hours AS jsonb))
            RETURNING id
        """), {"hospital_id": hospital_id, **{**spec, "working_hours": _json_param(spec["working_hours"])}}).scalar_one()
        agent_ids.append(str(row))
    return agent_ids


def _json_param(value) -> str:
    return json.dumps(value, default=str)


def _sample_business_data(db, hospital_id: str, agent_ids: list[str]) -> None:
    doc_id = db.execute(text("SELECT id FROM knowledge_documents WHERE hospital_id=:hospital_id AND title='Demo Dental FAQ' LIMIT 1"), {"hospital_id": hospital_id}).scalar()
    if not doc_id:
        doc_id = db.execute(text("""
            INSERT INTO knowledge_documents (hospital_id, title, file_name, file_type, status, chunks_count)
            VALUES (:hospital_id, 'Demo Dental FAQ', 'demo-dental-faq.md', 'md', 'active', 4)
            RETURNING id
        """), {"hospital_id": hospital_id}).scalar_one()
        for idx, content in enumerate([
            "Demo Dental is open from 9 AM to 6 PM on weekdays and 9 AM to 1 PM on Saturdays.",
            "Cleaning, whitening, orthodontic, implant, and emergency dental consultations can be booked by phone.",
            "For billing or insurance questions, the front desk can arrange a callback during business hours.",
            "Urgent pain, swelling, trauma, or bleeding should be escalated to clinic staff immediately.",
        ]):
            db.execute(text("INSERT INTO knowledge_chunks (hospital_id, document_id, chunk_index, content) VALUES (:hospital_id, :document_id, :idx, :content)"), {"hospital_id": hospital_id, "document_id": doc_id, "idx": idx, "content": content})

    existing_calls = db.execute(text("SELECT count(*) FROM calls WHERE hospital_id=:hospital_id"), {"hospital_id": hospital_id}).scalar() or 0
    created_call_ids = []
    for idx in range(existing_calls, 50):
        agent_id = agent_ids[idx % len(agent_ids)] if agent_ids else None
        call_id = db.execute(text("""
            INSERT INTO calls (hospital_id, agent_id, caller_phone, direction, workflow_type, status, outcome, started_at, ended_at, duration_seconds, language, consent_granted, answered_by_ai, missed, appointment_status, revenue_estimate, final_bill_amount, response_latency_ms)
            VALUES (:hospital_id, :agent_id, :phone, 'inbound', :workflow, :status, :outcome, now() - (:hours * interval '1 hour'), now() - (:hours * interval '1 hour') + (:duration * interval '1 second'), :duration, :language, true, :ai, :missed, :appointment_status, :revenue_estimate, :final_bill_amount, :latency)
            RETURNING id
        """), {"hospital_id": hospital_id, "agent_id": agent_id, "phone": f"+91987654{idx:03d}", "workflow": "appointment_booking" if idx % 2 == 0 else "faq", "status": "escalated" if idx in {7, 23, 41} else "completed", "outcome": "lead" if idx % 5 == 0 else "appointment_booked", "hours": idx * 5, "duration": 95 + (idx % 9) * 24, "language": "hi-IN" if idx % 7 == 0 else "en-IN", "ai": idx not in {7, 23, 41}, "missed": idx in {11, 37}, "appointment_status": "confirmed" if idx < 10 or idx % 3 == 0 else "requested", "revenue_estimate": 1500 + (idx % 8) * 650, "final_bill_amount": 2200 if idx < 10 else 0, "latency": 640 + (idx % 10) * 35}).scalar_one()
        created_call_ids.append(str(call_id))
        db.execute(text("INSERT INTO call_summaries (hospital_id, call_id, intent, discussed, decision, follow_up_needed) VALUES (:hospital_id, :call_id, :intent, 'Caller requested operational dental front desk help. No clinical notes stored.', :decision, :follow_up)"), {"hospital_id": hospital_id, "call_id": call_id, "intent": "appointment_booking" if idx % 2 == 0 else "faq", "decision": "appointment confirmed" if idx < 10 else "appointment requested", "follow_up": idx % 4 == 0})
        db.execute(text("INSERT INTO conversation_turns (hospital_id, call_id, turn_index, speaker, text, redacted_text, intent, confidence, latency_ms) VALUES (:hospital_id, :call_id, 1, 'caller', 'I want to book a dental appointment', 'I want to book a dental appointment', 'book_appointment', 0.92, 700)"), {"hospital_id": hospital_id, "call_id": call_id})
        db.execute(text("INSERT INTO conversation_turns (hospital_id, call_id, turn_index, speaker, text, redacted_text, intent, confidence, latency_ms) VALUES (:hospital_id, :call_id, 2, 'agent', 'I can help with that. Which day works best for you?', 'I can help with that. Which day works best for you?', 'book_appointment', 0.95, 680)"), {"hospital_id": hospital_id, "call_id": call_id})
        if idx in {7, 23, 41}:
            db.execute(text("INSERT INTO escalations (hospital_id, call_id, reason, severity, status) VALUES (:hospital_id, :call_id, 'low confidence handoff', 'medium', 'open')"), {"hospital_id": hospital_id, "call_id": call_id})
        if idx % 5 == 0:
            db.execute(text("INSERT INTO leads (hospital_id, call_id, service_interest, context, status) VALUES (:hospital_id, :call_id, 'Dental consultation', 'Caller requested callback for appointment availability.', 'new')"), {"hospital_id": hospital_id, "call_id": call_id})

    existing_appointments = db.execute(text("SELECT count(*) FROM appointments WHERE hospital_id=:hospital_id"), {"hospital_id": hospital_id}).scalar() or 0
    for idx in range(existing_appointments, 20):
        opid = f"DD{idx + 1:04d}"
        db.execute(text("""
            INSERT INTO patients (opid, hospital_id, name, phone, email, consent_status)
            VALUES (:opid, :hospital_id, :name, :phone, :email, 'granted')
            ON CONFLICT (opid) DO UPDATE SET name=excluded.name, phone=excluded.phone, email=excluded.email
        """), {"opid": opid, "hospital_id": hospital_id, "name": f"Demo Patient {idx + 1}", "phone": f"+91888000{idx:04d}", "email": f"patient{idx + 1}@demo.com"})
        db.execute(text("""
            INSERT INTO appointments (hospital_id, patient_opid, patient_name, specialization, doctor_name, requested_time, appointment_time, source_call_id, status)
            VALUES (:hospital_id, :patient_opid, :patient_name, :specialization, :doctor_name, :requested_time, now() + (:days * interval '1 day'), :source_call_id, :status)
        """), {
            "hospital_id": hospital_id,
            "patient_opid": opid,
            "patient_name": f"Demo Patient {idx + 1}",
            "specialization": ["Cleaning", "Whitening", "Orthodontics", "Implants"][idx % 4],
            "doctor_name": ["Dr. Rao", "Dr. Mehta", "Dr. Iyer"][idx % 3],
            "requested_time": "Tomorrow morning" if idx % 2 == 0 else "This week afternoon",
            "days": idx % 14 + 1,
            "source_call_id": created_call_ids[idx] if idx < len(created_call_ids) else None,
            "status": "completed" if idx < 10 else "confirmed",
        })


def _resolve_user_id(prefix: str) -> str | None:
    explicit = os.getenv(f"{prefix}_USER_ID")
    if explicit:
        return explicit
    email = os.getenv(f"{prefix}_EMAIL")
    if not email or not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    existing = _find_auth_user(email)
    if existing:
        return existing
    password = os.getenv("SEED_DEFAULT_PASSWORD")
    if not password:
        print(f"Sign-in user not found for {email}; set {prefix}_USER_ID or SEED_DEFAULT_PASSWORD to create one.")
        return None
    response = requests.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"seed_role": prefix.lower()},
        },
        timeout=20,
    )
    if response.status_code >= 400:
        print(f"Could not create sign-in user for {email}; set {prefix}_USER_ID explicitly.")
        return None
    payload = response.json()
    return payload.get("id") or payload.get("user", {}).get("id")


def _find_auth_user(email: str) -> str | None:
    response = requests.get(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
        headers={"Authorization": f"Bearer {settings.supabase_service_role_key}", "apikey": settings.supabase_service_role_key},
        timeout=20,
    )
    if response.status_code >= 400:
        print(f"Could not list sign-in users for {email}.")
        return None
    payload = response.json()
    users = payload.get("users", []) if isinstance(payload, dict) else []
    for user in users:
        if str(user.get("email", "")).lower() == email.lower():
            return user.get("id")
    return None


if __name__ == "__main__":
    main()
