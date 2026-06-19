from __future__ import annotations

import base64
import os
import tempfile
import time
from datetime import date
import json
import re
import secrets
import string
from typing import Any
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import settings
from app.core.rbac import CurrentUser, load_staff_profile, readable_hospital_filter, require_current_user, require_hospital_admin, require_roles, writable_hospital_id
from app.db.session import check_db_connection, db_session
from app.repositories import session_repository
from app.services.intent_service import intent_service
from app.voice.providers import get_voice_provider

router = APIRouter(tags=["saas"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshSessionRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: str | None = None
    work_email: str | None = None
    password: str = Field(min_length=8)
    full_name: str
    hospital_name: str
    phone: str | None = None


class InviteStaffRequest(BaseModel):
    email: str
    full_name: str | None = None
    role: str = "staff"
    password: str | None = Field(default=None, min_length=8)


class ApproveOnboardingPayload(BaseModel):
    plan: str = "pilot"
    status: str = "active"
    notes: str | None = None


class AgentPayload(BaseModel):
    name: str
    description: str | None = None
    status: str = "draft"
    language: str = "en-IN"
    voice_provider: str = "sarvam"
    voice_name: str | None = None
    tts_pace: float = 1.0
    greeting: str | None = None
    system_prompt: str | None = None
    escalation_rules: dict[str, Any] = Field(default_factory=dict)
    working_hours: dict[str, Any] = Field(default_factory=dict)
    transfer_phone_number: str | None = None
    appointment_behavior: dict[str, Any] = Field(default_factory=dict)
    knowledge_source_ids: list[str] = Field(default_factory=list)
    fallback_behavior: str | None = None
    hospital_id: str | None = None


class AgentTestPayload(BaseModel):
    message: str
    session_id: str | None = None
    messages: list[dict[str, Any]] | None = None


class SettingsPayload(BaseModel):
    hospital_name: str | None = None
    timezone: str | None = None
    business_hours: dict[str, Any] | None = None
    telephony: dict[str, Any] | None = None
    voice: dict[str, Any] | None = None
    ai: dict[str, Any] | None = None
    security: dict[str, Any] | None = None


class HospitalPayload(BaseModel):
    name: str
    slug: str
    timezone: str = "Asia/Kolkata"
    status: str = "active"
    plan: str = "pilot"
    admin_email: str | None = None


@router.post("/auth/login")
async def login(payload: LoginRequest):
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Sign-in is not configured for this deployment")
    response = requests.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={"email": payload.email, "password": payload.password},
        timeout=12,
    )
    if response.status_code in {400, 401, 403}:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="Sign-in service is temporarily unavailable")
    data = response.json()
    access_token = data.get("access_token")
    user = data.get("user") or {}
    if not access_token or not user.get("id"):
        raise HTTPException(status_code=503, detail="Sign-in service returned an invalid response")
    from app.core.rbac import load_staff_profile

    profile = load_staff_profile(str(user["id"]))
    return {"session": _public_session(data), "profile": _profile(profile), "user": _me_payload(profile), "redirect_to": _redirect(profile.role)}


@router.post("/auth/register")
async def register(payload: RegisterRequest):
    if not check_db_connection():
        raise HTTPException(status_code=503, detail="Registration is temporarily unavailable")
    email = (payload.email or payload.work_email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")
    supabase_user_id = _create_or_get_supabase_user(email, payload.password, payload.full_name)
    with db_session() as db:
        existing_staff = db.execute(
            text("SELECT * FROM staff_users WHERE supabase_user_id=:supabase_user_id LIMIT 1"),
            {"supabase_user_id": supabase_user_id},
        ).mappings().first()
        if existing_staff:
            user = load_staff_profile(str(supabase_user_id))
            session = _password_login(email, payload.password)
            hospital = db.execute(text("SELECT * FROM hospitals WHERE id=:hospital_id"), {"hospital_id": user.hospital_id}).mappings().first() if user.hospital_id else None
            return {
                "ok": True,
                "user": _me_payload(user),
                "profile": _profile(user),
                "hospital": _json(hospital),
                "staff_user": _json(existing_staff),
                "session": session,
                "access_token": session.get("access_token") if session else None,
                "redirect_to": _redirect(user.role),
                "message": "Workspace already exists. You can continue.",
            }
        slug = _unique_slug(db, payload.hospital_name)
        hospital = db.execute(
            text(
                """
                INSERT INTO hospitals (name, slug, phone, status, plan, admin_email)
                VALUES (:name, :slug, :phone, 'active', 'pilot', :admin_email)
                RETURNING *
                """
            ),
            {"name": payload.hospital_name, "slug": slug, "phone": payload.phone, "admin_email": email},
        ).mappings().one()
        db.execute(
            text("INSERT INTO subscriptions (hospital_id, plan, status, billing_email) VALUES (:hospital_id, 'pilot', 'trialing', :email) ON CONFLICT DO NOTHING"),
            {"hospital_id": hospital["id"], "email": email},
        )
        db.execute(text("INSERT INTO hospital_settings (hospital_id) VALUES (:hospital_id) ON CONFLICT DO NOTHING"), {"hospital_id": hospital["id"]})
        staff = db.execute(
            text(
                """
                INSERT INTO staff_users (hospital_id, supabase_user_id, email, full_name, phone, role, status)
                VALUES (:hospital_id, :supabase_user_id, :email, :full_name, :phone, 'hospital_admin', 'active')
                ON CONFLICT (supabase_user_id) DO UPDATE
                  SET hospital_id=excluded.hospital_id,
                      email=excluded.email,
                      full_name=excluded.full_name,
                      phone=excluded.phone,
                      role='hospital_admin',
                      status='active',
                      updated_at=now()
                RETURNING *
                """
            ),
            {
                "supabase_user_id": supabase_user_id,
                "hospital_id": hospital["id"],
                "email": email,
                "full_name": payload.full_name,
                "phone": payload.phone,
            },
        ).mappings().one()
        agent = _ensure_default_agent(db, hospital["id"])
        db.execute(
            text(
                """
                INSERT INTO onboarding_requests (hospital_id, supabase_user_id, work_email, full_name, hospital_name, phone, status, approved_at, approval_email_status)
                VALUES (:hospital_id, :supabase_user_id, :work_email, :full_name, :hospital_name, :phone, 'approved', now(), 'auto_approved_registration')
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "hospital_id": hospital["id"],
                "supabase_user_id": supabase_user_id,
                "work_email": email,
                "full_name": payload.full_name,
                "hospital_name": payload.hospital_name,
                "phone": payload.phone,
            },
        )
        db.execute(
            text(
                """
                INSERT INTO audit_logs (hospital_id, actor_staff_user_id, session_id, event_type, message, resource_type, resource_id, event_json)
                VALUES (:hospital_id, :staff_user_id, 'registration', 'workspace_registered', 'Workspace registered from self-service signup.', 'hospital', :hospital_id, CAST(:event_json AS jsonb))
                """
            ),
            {"hospital_id": hospital["id"], "staff_user_id": staff["id"], "event_json": _json_param({"email": email})},
        )
    user = load_staff_profile(str(supabase_user_id))
    session = _password_login(email, payload.password)
    return {
        "ok": True,
        "requires_email_confirmation": False,
        "user": _me_payload(user),
        "profile": _profile(user),
        "hospital": _json(hospital),
        "staff_user": _json(staff),
        "agent": _json(agent),
        "session": session,
        "access_token": session.get("access_token") if session else None,
        "redirect_to": _redirect(user.role),
        "message": "Workspace created. Redirecting to your dashboard.",
    }


@router.post("/auth/logout")
async def logout(_: CurrentUser = Depends(require_current_user)):
    return {"ok": True}


@router.post("/auth/refresh")
async def refresh_auth(payload: RefreshSessionRequest):
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Session refresh is not configured for this deployment")
    response = requests.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=refresh_token",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={"refresh_token": payload.refresh_token},
        timeout=12,
    )
    if response.status_code in {400, 401, 403}:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="Could not refresh your session")
    data = response.json()
    session = _public_session(data)
    user = data.get("user") or {}
    profile = load_staff_profile(str(user["id"])) if user.get("id") else None
    return {"session": session, "profile": _profile(profile) if profile else None, "user": _me_payload(profile) if profile else None}


@router.get("/auth/me")
async def me(user: CurrentUser = Depends(require_current_user)):
    payload = _me_payload(user)
    return {**payload, "profile": _profile(user), "redirect_to": _redirect(user.role)}


@router.post("/auth/invite-staff")
async def invite_staff(payload: InviteStaffRequest, user: CurrentUser = Depends(require_hospital_admin)):
    if user.is_super_admin and not user.hospital_id:
        raise HTTPException(status_code=400, detail="Select a hospital before inviting staff")
    if payload.role not in {"hospital_admin", "staff"}:
        raise HTTPException(status_code=400, detail="Role must be hospital_admin or staff")
    target_hospital_id = writable_hospital_id(user)
    password = payload.password or _temporary_password()
    supabase_user_id = _create_or_get_supabase_user(payload.email.strip().lower(), password, payload.full_name or payload.email)
    with db_session() as db:
        row = db.execute(
            text(
                """
                INSERT INTO staff_users (hospital_id, supabase_user_id, email, full_name, role, status)
                VALUES (:hospital_id, :supabase_user_id, :email, :full_name, :role, 'active')
                ON CONFLICT (supabase_user_id) DO UPDATE
                  SET hospital_id=excluded.hospital_id,
                      email=excluded.email,
                      full_name=excluded.full_name,
                      role=excluded.role,
                      status='active',
                      updated_at=now()
                RETURNING id, hospital_id, supabase_user_id, email, full_name, role, status, created_at
                """
            ),
            {
                "hospital_id": target_hospital_id,
                "supabase_user_id": supabase_user_id,
                "email": payload.email.strip().lower(),
                "full_name": payload.full_name,
                "role": payload.role,
            },
        ).mappings().one()
    return {"ok": True, "staff_user": _json(row), "temporary_password_created": payload.password is None}


@router.get("/dashboard/metrics")
async def dashboard_metrics(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = Query(default=None)):
    where, params = readable_hospital_filter(user, hospital_id)
    with db_session() as db:
        calls = db.execute(text(f"""
            SELECT
              count(*) FILTER (WHERE started_at >= date_trunc('day', now()))::int AS calls_today,
              count(*) FILTER (WHERE started_at >= date_trunc('day', now()) AND answered_by_ai)::int AS ai_answered_today,
              count(*) FILTER (WHERE started_at >= date_trunc('day', now()) AND missed)::int AS missed_today,
              count(*) FILTER (WHERE started_at >= date_trunc('day', now()) AND status = 'escalated')::int AS escalations_today,
              count(*) FILTER (WHERE started_at >= date_trunc('month', now()))::int AS calls_month,
              count(*) FILTER (WHERE started_at >= date_trunc('month', now()) AND appointment_status = 'requested')::int AS appointments_requested,
              count(*) FILTER (WHERE started_at >= date_trunc('month', now()) AND appointment_status = 'confirmed')::int AS appointments_confirmed,
              count(*) FILTER (WHERE started_at >= date_trunc('month', now()) AND outcome = 'lead')::int AS new_leads,
              coalesce(avg(duration_seconds), 0)::int AS avg_duration,
              coalesce(avg(response_latency_ms), 0)::int AS avg_latency,
              count(*) FILTER (WHERE status = 'completed')::int AS completed,
              count(*) FILTER (WHERE status = 'escalated')::int AS escalated,
              count(*)::int AS total,
              coalesce(sum(revenue_estimate), 0)::float AS revenue_influenced,
              coalesce(sum(final_bill_amount), 0)::float AS confirmed_revenue
            FROM calls {where}
        """), params).mappings().one()
        languages = db.execute(text(f"SELECT language, count(*)::int AS calls FROM calls {where} GROUP BY language ORDER BY calls DESC"), params).mappings().all()
    total = calls["total"] or 0
    ai_answered = calls["ai_answered_today"] or 0
    return {
        "today": {
            "calls_received": calls["calls_today"],
            "calls_answered_by_ai": calls["ai_answered_today"],
            "missed_calls": calls["missed_today"],
            "appointments_booked": calls["appointments_confirmed"],
            "escalations": calls["escalations_today"],
        },
        "month": {
            "total_calls": calls["calls_month"],
            "new_leads": calls["new_leads"],
            "appointments_requested": calls["appointments_requested"],
            "appointments_confirmed": calls["appointments_confirmed"],
            "conversion_rate": _pct(calls["appointments_confirmed"], calls["appointments_requested"]),
        },
        "performance": {
            "average_call_duration": calls["avg_duration"],
            "average_response_latency": calls["avg_latency"],
            "success_rate": _pct(calls["completed"], total),
            "escalation_rate": _pct(calls["escalated"], total),
            "languages_handled": [dict(row) for row in languages],
        },
        "business_impact": {
            "estimated_revenue_influenced": calls["revenue_influenced"],
            "confirmed_revenue": calls["confirmed_revenue"],
            "appointment_conversion_rate": _pct(calls["appointments_confirmed"], calls["appointments_requested"]),
            "ai_handled_percentage": _pct(ai_answered, calls["calls_today"]),
            "human_time_saved_minutes": round((ai_answered * max(calls["avg_duration"] or 180, 180)) / 60, 1),
        },
    }


@router.get("/dashboard/summary")
async def dashboard_summary(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = Query(default=None)):
    return await dashboard_metrics(user, hospital_id)


@router.get("/agents")
async def list_agents(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = Query(default=None)):
    where, params = readable_hospital_filter(user, hospital_id)
    with db_session() as db:
        rows = db.execute(text(f"""
            SELECT a.*, count(c.id)::int AS calls_handled,
                   coalesce(avg(CASE WHEN c.appointment_status = 'confirmed' THEN 1 ELSE 0 END), 0)::float AS conversion_rate
            FROM agents a
            LEFT JOIN calls c ON c.agent_id = a.id
            {_where_for_alias(where, 'a')}
            GROUP BY a.id
            ORDER BY a.updated_at DESC
        """), params).mappings().all()
    return [_json(row) for row in rows]


@router.post("/agents")
async def create_agent(payload: AgentPayload, user: CurrentUser = Depends(require_hospital_admin)):
    hospital_id = writable_hospital_id(user, payload.hospital_id)
    with db_session() as db:
        row = db.execute(text("""
            INSERT INTO agents (hospital_id, name, description, status, language, voice_provider, voice_name, tts_pace,
              greeting, system_prompt, escalation_rules, working_hours, transfer_phone_number, appointment_behavior,
              knowledge_source_ids, fallback_behavior, created_by_staff_user_id)
            VALUES (:hospital_id, :name, :description, :status, :language, :voice_provider, :voice_name, :tts_pace,
              :greeting, :system_prompt, CAST(:escalation_rules AS jsonb), CAST(:working_hours AS jsonb), :transfer_phone_number, CAST(:appointment_behavior AS jsonb),
              CAST(:knowledge_source_ids AS jsonb), :fallback_behavior, :staff_user_id)
            RETURNING *
        """), _agent_params(payload, hospital_id, user.staff_user_id)).mappings().one()
        _save_agent_version(db, row["id"], hospital_id, user.staff_user_id, dict(row))
    return _json(row)


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, user: CurrentUser = Depends(require_current_user)):
    return _get_owned_agent(agent_id, user)


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, payload: AgentPayload, user: CurrentUser = Depends(require_hospital_admin)):
    agent = _get_owned_agent(agent_id, user)
    hospital_id = agent["hospital_id"]
    with db_session() as db:
        row = db.execute(text("""
            UPDATE agents SET name=:name, description=:description, status=:status, language=:language,
              voice_provider=:voice_provider, voice_name=:voice_name, tts_pace=:tts_pace, greeting=:greeting,
              system_prompt=:system_prompt, escalation_rules=CAST(:escalation_rules AS jsonb), working_hours=CAST(:working_hours AS jsonb),
              transfer_phone_number=:transfer_phone_number, appointment_behavior=CAST(:appointment_behavior AS jsonb),
              knowledge_source_ids=CAST(:knowledge_source_ids AS jsonb), fallback_behavior=:fallback_behavior, updated_at=now()
            WHERE id=:agent_id AND hospital_id=:hospital_id
            RETURNING *
        """), {**_agent_params(payload, hospital_id, user.staff_user_id), "agent_id": agent_id}).mappings().one()
        _save_agent_version(db, row["id"], hospital_id, user.staff_user_id, dict(row))
    return _json(row)


@router.patch("/agents/{agent_id}")
async def patch_agent(agent_id: str, payload: AgentPayload, user: CurrentUser = Depends(require_hospital_admin)):
    return await update_agent(agent_id, payload, user)


@router.post("/agents/{agent_id}/duplicate")
async def duplicate_agent(agent_id: str, user: CurrentUser = Depends(require_hospital_admin)):
    agent = _get_owned_agent(agent_id, user)
    payload = AgentPayload(**{key: agent.get(key) for key in AgentPayload.model_fields if key in agent})
    payload.name = f"{agent['name']} Copy"
    return await create_agent(payload, user)


@router.post("/agents/{agent_id}/test")
async def test_agent(agent_id: str, payload: AgentTestPayload, user: CurrentUser = Depends(require_current_user)):
    agent = _get_owned_agent(agent_id, user)
    result = _run_agent_conversation(agent, payload.message, user, payload.session_id)
    with db_session() as db:
        row = db.execute(text("""
            INSERT INTO agent_test_runs (hospital_id, agent_id, staff_user_id, user_message, agent_response, detected_intent, matched_snippets, latency_ms)
            VALUES (:hospital_id, :agent_id, :staff_user_id, :user_message, :agent_response, :detected_intent, CAST(:matched_snippets AS jsonb), :latency_ms)
            RETURNING *
        """), {
            "hospital_id": agent["hospital_id"], "agent_id": agent_id, "staff_user_id": user.staff_user_id,
            "user_message": payload.message, "agent_response": result["response"], "detected_intent": result["intent"],
            "matched_snippets": _json_param(result["matched_snippets"]), "latency_ms": result["latency_ms"],
        }).mappings().one()
    return {**result, "run": _json(row)}


@router.post("/agents/{agent_id}/voice")
async def agent_voice_turn(
    agent_id: str,
    audio: UploadFile = File(...),
    session_id: str | None = Form(None),
    language: str | None = Form(None),
    user: CurrentUser = Depends(require_current_user),
):
    agent = _get_owned_agent(agent_id, user)
    audio_path = None
    try:
        suffix = _audio_suffix(audio.filename, audio.content_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            audio_path = temp_file.name
            temp_file.write(await audio.read())
        provider = get_voice_provider(agent.get("voice_provider") or settings.voice_provider)
        target_language = language or agent.get("language") or settings.default_language
        started = time.perf_counter()
        transcript = provider.transcribe(audio_path, target_language)
        stt_latency_ms = round((time.perf_counter() - started) * 1000)
        if not transcript:
            return {
                "status": "no_audio",
                "session_id": session_id,
                "response": "I did not hear that clearly. Please try again.",
                "user_input": "",
                "intent": "general",
                "provider": provider.name,
                "stage_timings": {"stt_latency_ms": stt_latency_ms, "tts_latency_ms": 0, "total_latency_ms": stt_latency_ms},
            }
        result = _run_agent_conversation(agent, transcript, user, session_id)
        tts_started = time.perf_counter()
        tts_result = provider.synthesize(
            result["response"],
            agent.get("voice_name") or "female",
            target_language,
            float(agent.get("tts_pace") or 1.0),
        )
        audio_content = getattr(tts_result, "audio_content", None)
        audio_url = getattr(tts_result, "audio_url", None)
        tts_latency_ms = round((time.perf_counter() - tts_started) * 1000)
        result["provider"] = provider.name
        result["stage_timings"] = {
            "stt_latency_ms": stt_latency_ms,
            "tts_latency_ms": tts_latency_ms,
            "total_latency_ms": result["latency_ms"] + stt_latency_ms + tts_latency_ms,
        }
        result["audio"] = {
            "audio_base64": base64.b64encode(audio_content).decode("ascii") if audio_content else None,
            "audio_url": audio_url,
            "mime_type": "audio/wav" if audio_content else None,
            "provider": getattr(tts_result, "provider", provider.name),
        }
        return result
    finally:
        try:
            if audio_path:
                os.unlink(audio_path)
        except Exception:
            pass


@router.get("/calls")
async def list_calls(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = None, agent_id: str | None = None, outcome: str | None = None, escalated_only: bool = False, booked_only: bool = False, language: str | None = None):
    where, params = readable_hospital_filter(user, hospital_id)
    clauses = [_where_clause_for_alias(where, "c")] if where else []
    if agent_id:
        clauses.append("c.agent_id = :agent_id"); params["agent_id"] = agent_id
    if outcome:
        clauses.append("c.outcome = :outcome"); params["outcome"] = outcome
    if escalated_only:
        clauses.append("c.status = 'escalated'")
    if booked_only:
        clauses.append("c.appointment_status = 'confirmed'")
    if language:
        clauses.append("c.language = :language"); params["language"] = language
    sql_where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with db_session() as db:
        rows = db.execute(text(f"""
            SELECT c.id, c.started_at, c.caller_phone, c.language, c.duration_seconds, c.outcome, c.appointment_status,
                   c.revenue_estimate, c.final_bill_amount, c.status, c.recording_url, a.name AS agent_name,
                   e.status AS escalation_status
            FROM calls c
            LEFT JOIN agents a ON a.id = c.agent_id
            LEFT JOIN escalations e ON e.call_id = c.id
            {sql_where}
            ORDER BY c.started_at DESC LIMIT 200
        """), params).mappings().all()
    return [_json(row) for row in rows]


@router.get("/calls/{call_id}")
async def call_detail(call_id: str, user: CurrentUser = Depends(require_current_user)):
    where, params = readable_hospital_filter(user)
    params["call_id"] = call_id
    with db_session() as db:
        call = db.execute(text(f"""
            SELECT c.*, a.name AS agent_name FROM calls c LEFT JOIN agents a ON a.id = c.agent_id
            {_where_for_alias(where, 'c') if where else 'WHERE true'} AND c.id = :call_id
        """), params).mappings().first()
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        summary = db.execute(text("SELECT * FROM call_summaries WHERE call_id=:call_id"), {"call_id": call_id}).mappings().first()
        turns = db.execute(text("SELECT * FROM conversation_turns WHERE call_id=:call_id ORDER BY turn_index"), {"call_id": call_id}).mappings().all()
        intents = db.execute(text("SELECT * FROM intents WHERE call_id=:call_id ORDER BY created_at"), {"call_id": call_id}).mappings().all()
        escalation = db.execute(text("SELECT * FROM escalations WHERE call_id=:call_id ORDER BY created_at DESC LIMIT 1"), {"call_id": call_id}).mappings().first()
        appointment = db.execute(text("SELECT * FROM appointments WHERE source_call_id=:call_id ORDER BY created_at DESC LIMIT 1"), {"call_id": call_id}).mappings().first()
    return {"call": _json(call), "summary": _json(summary), "conversation": [_json(row) for row in turns], "intents": [_json(row) for row in intents], "escalation": _json(escalation), "appointment": _json(appointment)}


@router.get("/reports/metrics")
async def reports(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = None):
    where, params = readable_hospital_filter(user, hospital_id)
    with db_session() as db:
        volume = db.execute(text(f"SELECT date_trunc('day', started_at)::date AS day, count(*)::int AS calls FROM calls {where} GROUP BY 1 ORDER BY 1"), params).mappings().all()
        outcomes = db.execute(text(f"SELECT coalesce(outcome, 'unknown') AS outcome, count(*)::int AS calls FROM calls {where} GROUP BY 1 ORDER BY calls DESC"), params).mappings().all()
        agents = db.execute(text(f"""
            SELECT coalesce(a.name, 'Unassigned') AS agent, count(c.id)::int AS calls,
                   coalesce(avg(c.duration_seconds), 0)::int AS avg_duration,
                   coalesce(sum(c.revenue_estimate), 0)::float AS revenue
            FROM calls c LEFT JOIN agents a ON a.id = c.agent_id
            {_where_for_alias(where, 'c')}
            GROUP BY 1 ORDER BY calls DESC
        """), params).mappings().all()
        language = db.execute(text(f"SELECT language, count(*)::int AS calls, coalesce(avg(duration_seconds), 0)::int AS avg_duration FROM calls {where} GROUP BY language ORDER BY calls DESC"), params).mappings().all()
    return {"call_volume": [_json(r) for r in volume], "outcome_breakdown": [_json(r) for r in outcomes], "appointment_funnel": await dashboard_metrics(user, hospital_id), "agent_comparison": [_json(r) for r in agents], "language_performance": [_json(r) for r in language]}


@router.get("/reports/summary")
async def reports_summary(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = None):
    return await reports(user, hospital_id)


@router.get("/knowledge-base")
async def kb_list(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = None):
    where, params = readable_hospital_filter(user, hospital_id)
    with db_session() as db:
        rows = db.execute(text(f"SELECT * FROM knowledge_documents {where} ORDER BY updated_at DESC"), params).mappings().all()
    return [_json(row) for row in rows]


@router.get("/knowledge-documents")
async def knowledge_documents(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = None):
    return await kb_list(user, hospital_id)


@router.post("/knowledge-base")
async def kb_upload(file: UploadFile = File(...), user: CurrentUser = Depends(require_hospital_admin), hospital_id: str | None = Query(default=None)):
    target_hospital_id = writable_hospital_id(user, hospital_id)
    allowed = {"pdf", "docx", "txt", "md", "markdown"}
    ext = (file.filename or "document").rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT, Markdown")
    storage_path = None
    status_value = "processing"
    error_message = None
    content = await file.read()
    if settings.supabase_url and settings.supabase_service_role_key:
        storage_path = f"{target_hospital_id}/{int(time.time())}-{file.filename}"
        storage_response = requests.post(
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_storage_bucket}/{storage_path}",
            headers={"Authorization": f"Bearer {settings.supabase_service_role_key}", "apikey": settings.supabase_service_role_key, "Content-Type": file.content_type or "application/octet-stream"},
            data=content,
            timeout=20,
        )
        if storage_response.status_code >= 400:
            status_value = "failed"
            error_message = "Document storage upload failed. Check bucket and server credential configuration."
    else:
        status_value = "failed"
        error_message = "Document storage is not configured for this deployment."
    with db_session() as db:
        row = db.execute(text("""
            INSERT INTO knowledge_documents (hospital_id, title, file_name, file_type, storage_path, status, error_message, created_by_staff_user_id)
            VALUES (:hospital_id, :title, :file_name, :file_type, :storage_path, :status, :error_message, :staff_user_id)
            RETURNING *
        """), {"hospital_id": target_hospital_id, "title": file.filename or "Untitled", "file_name": file.filename, "file_type": ext, "storage_path": storage_path, "status": status_value, "error_message": error_message, "staff_user_id": user.staff_user_id}).mappings().one()
    return _json(row)


@router.post("/knowledge-documents")
async def knowledge_documents_upload(file: UploadFile = File(...), user: CurrentUser = Depends(require_hospital_admin), hospital_id: str | None = Query(default=None)):
    return await kb_upload(file, user, hospital_id)


@router.delete("/knowledge-base/{document_id}")
async def kb_delete(document_id: str, user: CurrentUser = Depends(require_hospital_admin)):
    where, params = readable_hospital_filter(user)
    params["document_id"] = document_id
    with db_session() as db:
        row = db.execute(text(f"UPDATE knowledge_documents SET status='inactive', updated_at=now() {where.replace('WHERE', 'WHERE id=:document_id AND') if where else 'WHERE id=:document_id'} RETURNING *"), params).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return _json(row)


@router.get("/settings")
async def get_settings_api(user: CurrentUser = Depends(require_current_user), hospital_id: str | None = None):
    target_hospital_id = writable_hospital_id(user, hospital_id) if hospital_id or not user.is_super_admin else user.hospital_id
    if not target_hospital_id:
        raise HTTPException(status_code=400, detail="hospital_id is required")
    with db_session() as db:
        hospital = db.execute(text("SELECT * FROM hospitals WHERE id=:hospital_id"), {"hospital_id": target_hospital_id}).mappings().first()
        settings_row = db.execute(text("SELECT * FROM hospital_settings WHERE hospital_id=:hospital_id"), {"hospital_id": target_hospital_id}).mappings().first()
        team = db.execute(text("SELECT id, email, full_name, role, status, created_at FROM staff_users WHERE hospital_id=:hospital_id ORDER BY created_at DESC"), {"hospital_id": target_hospital_id}).mappings().all()
    return {"hospital": _json(hospital), "settings": _json(settings_row), "team": [_json(row) for row in team]}


@router.put("/settings")
async def update_settings_api(payload: SettingsPayload, user: CurrentUser = Depends(require_hospital_admin), hospital_id: str | None = None):
    target_hospital_id = writable_hospital_id(user, hospital_id)
    with db_session() as db:
        if payload.hospital_name or payload.timezone:
            db.execute(text("UPDATE hospitals SET name=coalesce(:name, name), timezone=coalesce(:timezone, timezone), updated_at=now() WHERE id=:hospital_id"), {"name": payload.hospital_name, "timezone": payload.timezone, "hospital_id": target_hospital_id})
        row = db.execute(text("""
            INSERT INTO hospital_settings (hospital_id, business_hours, telephony, voice, ai, security)
            VALUES (:hospital_id, CAST(:business_hours AS jsonb), CAST(:telephony AS jsonb), CAST(:voice AS jsonb), CAST(:ai AS jsonb), CAST(:security AS jsonb))
            ON CONFLICT (hospital_id) DO UPDATE SET business_hours=coalesce(CAST(:business_hours AS jsonb), hospital_settings.business_hours), telephony=coalesce(CAST(:telephony AS jsonb), hospital_settings.telephony), voice=coalesce(CAST(:voice AS jsonb), hospital_settings.voice), ai=coalesce(CAST(:ai AS jsonb), hospital_settings.ai), security=coalesce(CAST(:security AS jsonb), hospital_settings.security), updated_at=now()
            RETURNING *
        """), {"hospital_id": target_hospital_id, "business_hours": _json_param(payload.business_hours), "telephony": _json_param(payload.telephony), "voice": _json_param(payload.voice), "ai": _json_param(payload.ai), "security": _json_param(payload.security)}).mappings().one()
    return _json(row)


@router.get("/super-admin/overview")
async def super_overview(user: CurrentUser = Depends(require_roles("super_admin"))):
    with db_session() as db:
        row = db.execute(text("""
            SELECT count(*)::int AS total_hospitals,
                   count(*) FILTER (WHERE status='active')::int AS active_hospitals,
                   (SELECT count(*)::int FROM calls) AS total_calls,
                   (SELECT coalesce(sum(duration_seconds),0)::int / 60 FROM calls) AS total_minutes,
                   (SELECT count(*)::int FROM subscriptions WHERE status NOT IN ('active','trialing')) AS failed_integrations
            FROM hospitals
        """)).mappings().one()
    return _json(row)


@router.get("/super-admin/hospitals")
async def super_hospitals(user: CurrentUser = Depends(require_roles("super_admin"))):
    with db_session() as db:
        rows = db.execute(text("""
            SELECT h.id, h.name, h.status, h.plan, h.created_at, h.admin_email,
                   count(c.id) FILTER (WHERE c.started_at >= date_trunc('month', now()))::int AS calls_this_month,
                   s.status AS subscription_status
            FROM hospitals h
            LEFT JOIN calls c ON c.hospital_id = h.id
            LEFT JOIN subscriptions s ON s.hospital_id = h.id
            GROUP BY h.id, s.status
            ORDER BY h.created_at DESC
        """)).mappings().all()
    return [_json(row) for row in rows]


@router.get("/super-admin/onboarding")
async def onboarding_requests(user: CurrentUser = Depends(require_roles("super_admin"))):
    with db_session() as db:
        rows = db.execute(text("SELECT * FROM onboarding_requests ORDER BY created_at DESC LIMIT 200")).mappings().all()
    return [_json(row) for row in rows]


@router.post("/super-admin/onboarding/{request_id}/approve")
async def approve_onboarding(request_id: str, payload: ApproveOnboardingPayload, user: CurrentUser = Depends(require_roles("super_admin"))):
    with db_session() as db:
        request_row = db.execute(text("SELECT * FROM onboarding_requests WHERE id=:id FOR UPDATE"), {"id": request_id}).mappings().first()
        if not request_row:
            raise HTTPException(status_code=404, detail="Onboarding request not found")
        if request_row["status"] == "approved" and request_row["hospital_id"]:
            return {"request": _json(request_row), "message": "Workspace is already approved."}
        supabase_user_id = request_row["supabase_user_id"] or _find_supabase_user_by_email(request_row["work_email"])
        if not supabase_user_id:
            raise HTTPException(status_code=400, detail="Create the sign-in account first, then approve this request.")
        slug = _unique_slug(db, request_row["hospital_name"])
        hospital = db.execute(text("""
            INSERT INTO hospitals (name, slug, status, plan, admin_email)
            VALUES (:name, :slug, :status, :plan, :admin_email)
            RETURNING *
        """), {"name": request_row["hospital_name"], "slug": slug, "status": payload.status, "plan": payload.plan, "admin_email": request_row["work_email"]}).mappings().one()
        db.execute(text("INSERT INTO subscriptions (hospital_id, plan, status, billing_email) VALUES (:hospital_id, :plan, 'trialing', :email) ON CONFLICT DO NOTHING"), {"hospital_id": hospital["id"], "plan": payload.plan, "email": request_row["work_email"]})
        db.execute(text("INSERT INTO hospital_settings (hospital_id) VALUES (:hospital_id) ON CONFLICT DO NOTHING"), {"hospital_id": hospital["id"]})
        db.execute(text("""
            INSERT INTO staff_users (hospital_id, supabase_user_id, email, full_name, role, status)
            VALUES (:hospital_id, :supabase_user_id, :email, :full_name, 'hospital_admin', 'active')
            ON CONFLICT (supabase_user_id) DO UPDATE SET hospital_id=excluded.hospital_id, role='hospital_admin', status='active', updated_at=now()
        """), {"hospital_id": hospital["id"], "supabase_user_id": supabase_user_id, "email": request_row["work_email"], "full_name": request_row["full_name"]})
        updated = db.execute(text("""
            UPDATE onboarding_requests
            SET status='approved', hospital_id=:hospital_id, supabase_user_id=:supabase_user_id,
                approved_by_staff_user_id=:staff_user_id, approved_at=now(),
                approval_email_status='account_enabled', notes=:notes, updated_at=now()
            WHERE id=:id
            RETURNING *
        """), {"id": request_id, "hospital_id": hospital["id"], "supabase_user_id": supabase_user_id, "staff_user_id": user.staff_user_id, "notes": payload.notes}).mappings().one()
    return {
        "request": _json(updated),
        "hospital": _json(hospital),
        "message": "Workspace approved. The user can now sign in with their registered email and password.",
    }


@router.post("/super-admin/hospitals")
async def create_hospital(payload: HospitalPayload, user: CurrentUser = Depends(require_roles("super_admin"))):
    with db_session() as db:
        row = db.execute(text("""
            INSERT INTO hospitals (name, slug, timezone, status, plan, admin_email)
            VALUES (:name, :slug, :timezone, :status, :plan, :admin_email)
            RETURNING *
        """), payload.model_dump()).mappings().one()
        db.execute(text("INSERT INTO subscriptions (hospital_id, plan, status, billing_email) VALUES (:hospital_id, :plan, 'trialing', :email) ON CONFLICT DO NOTHING"), {"hospital_id": row["id"], "plan": payload.plan, "email": payload.admin_email})
        db.execute(text("INSERT INTO hospital_settings (hospital_id) VALUES (:hospital_id) ON CONFLICT DO NOTHING"), {"hospital_id": row["id"]})
    return _json(row)


def _public_session(data: dict[str, Any]) -> dict[str, Any]:
    session = {key: data.get(key) for key in ["access_token", "refresh_token", "expires_in", "expires_at", "token_type"]}
    if not session.get("expires_at") and session.get("expires_in"):
        session["expires_at"] = int(time.time()) + int(session["expires_in"])
    return session


def _password_login(email: str, password: str) -> dict[str, Any] | None:
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None
    response = requests.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=12,
    )
    if response.status_code >= 400:
        return None
    return _public_session(response.json())


def _create_or_get_supabase_user(email: str, password: str, full_name: str | None = None) -> str:
    if not settings.supabase_url:
        raise HTTPException(status_code=503, detail="Registration service is unavailable. Add SUPABASE_URL to backend environment.")
    if settings.supabase_service_role_key:
        existing = _find_supabase_user_by_email(email)
        if existing:
            return existing
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
                "user_metadata": {"full_name": full_name or ""},
            },
            timeout=20,
        )
        if response.status_code in {400, 409, 422} and "already" in response.text.lower():
            existing = _find_supabase_user_by_email(email)
            if existing:
                return existing
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail="Could not create sign-in account. Check email/password and try again.")
        data = response.json()
        user_id = data.get("id") or (data.get("user") or {}).get("id")
        if not user_id:
            raise HTTPException(status_code=503, detail="Sign-in service returned an invalid response")
        return str(user_id)
    if not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Registration service is unavailable. Add SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY to backend environment.")
    response = requests.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password, "data": {"full_name": full_name or ""}},
        timeout=20,
    )
    if response.status_code >= 400:
        detail = "Account already exists. Sign in, or configure SUPABASE_SERVICE_ROLE_KEY so the backend can safely link existing users."
        if "already" not in response.text.lower():
            detail = "Could not create sign-in account. Check email/password and try again."
        raise HTTPException(status_code=400, detail=detail)
    data = response.json()
    user = data.get("user") if isinstance(data, dict) else None
    user_id = user.get("id") if isinstance(user, dict) else data.get("id")
    if not user_id:
        raise HTTPException(status_code=503, detail="Sign-in service returned an invalid response")
    return str(user_id)


def _signup_supabase_user(email: str, password: str, full_name: str) -> str | None:
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None
    response = requests.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password, "data": {"full_name": full_name}},
        timeout=12,
    )
    if response.status_code in {400, 422} and "already" in response.text.lower():
        return _find_supabase_user_by_email(email)
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Could not create sign-in account. Check email/password and try again.")
    data = response.json()
    user = data.get("user") if isinstance(data, dict) else None
    return user.get("id") if isinstance(user, dict) else None


def _find_supabase_user_by_email(email: str) -> str | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    response = requests.get(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
        headers={"Authorization": f"Bearer {settings.supabase_service_role_key}", "apikey": settings.supabase_service_role_key},
        timeout=20,
    )
    if response.status_code >= 400:
        return None
    payload = response.json()
    users = payload.get("users", []) if isinstance(payload, dict) else []
    for user in users:
        if str(user.get("email", "")).lower() == email.lower():
            return user.get("id")
    return None


def _registration_message(status_value: str) -> str:
    if status_value == "approved":
        return "Your workspace is approved. You can sign in now."
    if status_value == "rejected":
        return "This workspace request was not approved. Contact MedVoice support."
    return "Your workspace request is being reviewed."


def _profile(user: CurrentUser) -> dict[str, Any]:
    return user.__dict__


def _me_payload(user: CurrentUser) -> dict[str, Any]:
    return {
        "id": user.staff_user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "hospital_id": user.hospital_id,
        "hospital": {"id": user.hospital_id, "name": user.hospital_name} if user.hospital_id else None,
        "permissions": _permissions_for_role(user.role),
    }


def _permissions_for_role(role: str) -> list[str]:
    if role == "super_admin":
        return ["platform:read", "platform:write", "hospitals:write", "agents:write", "billing:write", "settings:write"]
    if role == "hospital_admin":
        return ["overview:read", "agents:write", "calls:read", "reports:read", "knowledge:write", "settings:write", "billing:read", "staff:invite"]
    return ["overview:read", "calls:read", "reports:read", "knowledge:read"]


def _redirect(role: str) -> str:
    return "/admin" if role == "super_admin" else "/dashboard"


def _temporary_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "hospital"


def _unique_slug(db, name: str) -> str:
    base = _slugify(name)
    slug = base
    idx = 2
    while db.execute(text("SELECT 1 FROM hospitals WHERE slug=:slug"), {"slug": slug}).first():
        slug = f"{base}-{idx}"
        idx += 1
    return slug


def _pct(num: Any, den: Any) -> float:
    return round((float(num or 0) / float(den or 0)) * 100, 2) if den else 0.0


def _json(row: Any) -> Any:
    if row is None:
        return None
    data = dict(row)
    out = {}
    for key, value in data.items():
        if isinstance(value, (date,)):
            out[key] = value.isoformat()
        elif isinstance(value, UUID):
            out[key] = str(value)
        else:
            out[key] = float(value) if value.__class__.__name__ == "Decimal" else value
    return out


def _agent_params(payload: AgentPayload, hospital_id: str, staff_user_id: str) -> dict[str, Any]:
    data = payload.model_dump(exclude={"hospital_id"})
    for key in ("escalation_rules", "working_hours", "appointment_behavior", "knowledge_source_ids"):
        data[key] = _json_param(data.get(key))
    data.update({"hospital_id": hospital_id, "staff_user_id": staff_user_id})
    return data


def _save_agent_version(db, agent_id: Any, hospital_id: str, staff_user_id: str, config: dict[str, Any]) -> None:
    version = db.execute(text("SELECT coalesce(max(version), 0) + 1 FROM agent_versions WHERE agent_id=:agent_id"), {"agent_id": agent_id}).scalar_one()
    db.execute(text("INSERT INTO agent_versions (hospital_id, agent_id, version, config, created_by_staff_user_id) VALUES (:hospital_id, :agent_id, :version, CAST(:config AS jsonb), :staff_user_id)"), {"hospital_id": hospital_id, "agent_id": agent_id, "version": version, "config": _json_param(config), "staff_user_id": staff_user_id})


def _ensure_default_agent(db, hospital_id: Any) -> Any:
    existing_rows = db.execute(
        text("SELECT * FROM agents WHERE hospital_id=:hospital_id ORDER BY created_at"),
        {"hospital_id": hospital_id},
    ).mappings().all()
    existing_by_name = {row["name"]: row for row in existing_rows}
    first_created = existing_rows[0] if existing_rows else None
    for spec in _default_agent_specs():
        if spec["name"] in existing_by_name:
            continue
        row = db.execute(
            text(
                """
                INSERT INTO agents (
                  hospital_id, name, description, status, language, voice_provider, voice_name,
                  greeting, system_prompt, fallback_behavior, transfer_phone_number, working_hours
                )
                VALUES (
                  :hospital_id, :name, :description, 'active', :language, 'sarvam', :voice_name,
                  :greeting, :system_prompt, :fallback_behavior, :transfer_phone_number, CAST(:working_hours AS jsonb)
                )
                RETURNING *
                """
            ),
            {"hospital_id": hospital_id, **{**spec, "working_hours": _json_param(spec["working_hours"])}},
        ).mappings().one()
        if first_created is None:
            first_created = row
    return first_created


def _json_param(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _run_agent_conversation(agent: dict[str, Any], message: str, user: CurrentUser, session_id: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    stable_session_id = session_id or f"playground:{user.staff_user_id}:{agent['id']}"
    repo = session_repository()
    session = repo.get_session(stable_session_id) or repo.create_session(stable_session_id)
    session = dict(session or {})
    session["agent_name"] = agent.get("name")
    session["agent_role"] = agent.get("description")
    session["hospital_name"] = user.hospital_name
    session["system_prompt"] = agent.get("system_prompt")
    session["business_rules"] = agent.get("fallback_behavior")
    session["selected_receptionist_id"] = str(agent.get("id"))
    session["hospital_id"] = str(agent.get("hospital_id"))

    detected_intent = intent_service.detect_intent(message)
    entities = intent_service.extract_entities(message)
    slots = dict(session.get("slots") or {})
    slot_update = _extract_dialogue_slots(message, entities, slots)
    slots.update(slot_update["slots"])
    intent = _effective_dialogue_intent(detected_intent, message, session, slots)
    if intent in {"book_appointment", "check_availability", "reschedule_appointment"}:
        session["current_intent"] = intent
    snippets = _kb_snippets(agent["hospital_id"], message)

    appointment_result = None
    if intent == "book_appointment" or session.get("current_intent") == "book_appointment":
        intent = "book_appointment"
        session["current_intent"] = intent
        appointment_result = _handle_appointment_dialogue(message, slots, slot_update)

    opid_validation_result = None
    if not appointment_result and slot_update["opid_status"] in {"too_short", "too_long"}:
        opid_validation_result = _handle_opid_validation(slot_update)
        session["current_intent"] = session.get("current_intent") or intent

    if appointment_result:
        response = appointment_result["response"]
        routed = {"action": appointment_result["next_action"], "data": {"missing": appointment_result["missing_slots"]}}
        session["missing_slots"] = appointment_result["missing_slots"]
        session["workflow_state"] = appointment_result["workflow_state"]
        session["last_assistant_question"] = appointment_result["last_assistant_question"]
    elif opid_validation_result:
        response = opid_validation_result["response"]
        routed = {"action": opid_validation_result["next_action"], "data": {"missing": opid_validation_result["missing_slots"]}}
        session["missing_slots"] = opid_validation_result["missing_slots"]
        session["workflow_state"] = opid_validation_result["workflow_state"]
        session["last_assistant_question"] = opid_validation_result["last_assistant_question"]
    elif intent == "greeting":
        response = _agent_greeting(agent, user)
        routed = {"action": "greet", "data": None}
        session["workflow_state"] = session.get("workflow_state") or "idle"
        session["last_assistant_question"] = response
    elif snippets and intent in {"faq", "general"}:
        response = _kb_response(snippets)
        routed = {"action": "knowledge_answer", "data": {"source": "knowledge_base"}}
        session["workflow_state"] = "answered"
        session["last_assistant_question"] = response
    else:
        if slots.get("opid"):
            session["opid"] = slots["opid"]
            entities["opid"] = slots["opid"]
        routed = intent_service.route_intent(intent, entities, session)
        response = routed.get("response") or agent.get("fallback_behavior") or _handoff_response(agent)
        missing = (routed.get("data") or {}).get("missing") or []
        session["missing_slots"] = missing
        session["workflow_state"] = "collecting_slots" if missing else "answered"
        session["last_assistant_question"] = response

    if intent != "greeting" and _is_generic_greeting(response):
        response = _handoff_response(agent)
        session["last_assistant_question"] = response

    if slot_update["opid_status"] == "valid":
        session["opid"] = slots["opid"]

    conversation = list(session.get("conversation") or [])
    conversation.append({"role": "user", "content": message})
    conversation.append({"role": "assistant", "content": response})
    repo.update_session(stable_session_id, {
        "conversation": conversation,
        "last_doctor_list": session.get("last_doctor_list", []),
        "opid": session.get("opid"),
        "patient_name": session.get("patient_name"),
        "selected_receptionist_id": session.get("selected_receptionist_id"),
        "hospital_id": session.get("hospital_id"),
        "current_intent": session.get("current_intent"),
        "slots": slots,
        "missing_slots": session.get("missing_slots", []),
        "last_assistant_question": session.get("last_assistant_question"),
        "workflow_state": session.get("workflow_state"),
    })

    latency = round((time.perf_counter() - started) * 1000)
    return {
        "ok": True,
        "status": "success",
        "session_id": stable_session_id,
        "user_input": message,
        "response": response,
        "spoken_response": response,
        "display_response": response,
        "intent": intent,
        "detected_intent": detected_intent,
        "current_intent": session.get("current_intent") or intent,
        "slots": slots,
        "missing_slots": session.get("missing_slots", []),
        "workflow_state": session.get("workflow_state"),
        "next_action": routed.get("action"),
        "last_assistant_question": session.get("last_assistant_question"),
        "messages": conversation,
        "action": routed.get("action"),
        "data": routed.get("data"),
        "matched_snippets": snippets,
        "latency_ms": latency,
        "confidence": 0.92 if intent != "general" else 0.66,
        "agent": {"id": agent.get("id"), "name": agent.get("name"), "role": agent.get("description")},
        "hospital": {"id": agent.get("hospital_id"), "name": user.hospital_name},
    }


DEMO_APPOINTMENT_AVAILABILITY = {
    ("dermatology", "tomorrow"): ["10:30 AM", "11:00 AM", "3:30 PM"],
    ("dentistry", "tomorrow"): ["9:30 AM", "12:00 PM", "4:00 PM"],
    ("general medicine", "tomorrow"): ["10:00 AM", "2:00 PM", "5:00 PM"],
    ("general", "tomorrow"): ["10:00 AM", "2:00 PM", "5:00 PM"],
}


def _extract_dialogue_slots(message: str, entities: dict[str, Any], existing_slots: dict[str, Any] | None = None) -> dict[str, Any]:
    text_lower = message.lower()
    existing_slots = existing_slots or {}
    slots: dict[str, Any] = {}

    opid_status = None
    preferred_time = _extract_preferred_time(text_lower, existing_slots) or entities.get("time")
    opid_candidate = _extract_opid_candidate(message)
    if opid_candidate and not (existing_slots.get("opid") and preferred_time):
        if len(opid_candidate) == 6:
            slots["opid"] = opid_candidate
            slots["patient_identifier"] = opid_candidate
            opid_status = "valid"
        elif len(opid_candidate) < 6:
            opid_status = "too_short"
        else:
            opid_status = "too_long"

    specialization = _normalize_department(entities.get("specialization") or _extract_specialization(text_lower))
    if specialization:
        slots["department"] = specialization
        slots["department_or_specialization"] = specialization

    doctor = entities.get("doctor_name")
    if doctor:
        slots["doctor"] = f"Dr. {doctor}"

    preferred_date = _extract_preferred_date(text_lower)
    if preferred_date:
        slots["preferred_date"] = preferred_date

    if preferred_time:
        slots["preferred_time"] = preferred_time

    return {"slots": slots, "opid_status": opid_status, "opid_candidate": opid_candidate}


def _effective_dialogue_intent(detected_intent: str, message: str, session: dict[str, Any], slots: dict[str, Any]) -> str:
    current_intent = session.get("current_intent")
    text_lower = message.lower()
    expects_slot = session.get("workflow_state") == "collecting_slots" or bool(session.get("missing_slots"))

    if current_intent == "book_appointment" and (
        detected_intent in {"general", "patient_lookup", "book_appointment"}
        or _is_slot_like_reply(text_lower, slots)
        or expects_slot
    ):
        return "book_appointment"

    if detected_intent == "patient_lookup" and (_mentions_appointment(text_lower) or (slots.get("opid") and (slots.get("department") or slots.get("doctor")))):
        return "book_appointment"

    if detected_intent == "general" and _mentions_appointment(text_lower):
        return "book_appointment"

    return detected_intent


def _handle_appointment_dialogue(message: str, slots: dict[str, Any], slot_update: dict[str, Any]) -> dict[str, Any]:
    opid_status = slot_update.get("opid_status")
    opid_candidate = slot_update.get("opid_candidate")
    if opid_status == "too_short" and not slots.get("opid"):
        return _dialogue_response(
            "That looks short. OPID is usually 6 digits. Could you confirm it?",
            ["opid"],
            "collecting_slots",
            "confirm_opid",
        )
    if opid_status == "too_long" and not slots.get("opid"):
        return _dialogue_response(
            f"I heard {opid_candidate}. Could you confirm your 6-digit OPID?",
            ["opid"],
            "collecting_slots",
            "confirm_opid",
        )

    missing = _appointment_missing_slots(slots)
    if missing:
        next_slot = missing[0]
        if next_slot == "preferred_time" and (slots.get("department") or slots.get("doctor")) and slots.get("preferred_date"):
            return _offer_available_slots(slots)
        questions = {
            "opid": "Sure. Could you share your 6-digit OPID?",
            "department": "Thank you. Which department or doctor would you like to book?",
            "preferred_date": "Which day works for you?",
            "preferred_time": "What time of day works best?",
        }
        return _dialogue_response(
            questions[next_slot],
            missing,
            "collecting_slots",
            f"collect_{next_slot}",
        )

    department = slots.get("doctor") or slots.get("department") or "the requested department"
    date_label = slots.get("preferred_date")
    time_label = slots.get("preferred_time")
    response = f"Got it. I can book {department} {date_label} at {time_label} for OPID {slots['opid']}. Should I confirm it?"
    return _dialogue_response(response, [], "ready_to_confirm", "confirm_appointment")


def _offer_available_slots(slots: dict[str, Any]) -> dict[str, Any]:
    department = _normalize_department(slots.get("department") or slots.get("doctor") or "Dermatology")
    date_label = slots.get("preferred_date") or "tomorrow"
    available = _available_demo_slots(department, date_label)
    if available:
        response = f"{date_label.title()}, {department} has {_format_list(available)} available. Which one should I book?"
        return _dialogue_response(response, ["preferred_time"], "collect_time_or_offer_slots", "offer_available_slots")

    response = f"I don't currently have {department} availability for {date_label}. Would you like me to connect you to reception?"
    return _dialogue_response(response, ["preferred_time"], "collect_time_or_offer_slots", "availability_unavailable")


def _handle_opid_validation(slot_update: dict[str, Any]) -> dict[str, Any]:
    opid_candidate = slot_update.get("opid_candidate")
    if slot_update.get("opid_status") == "too_short":
        response = "That looks short. OPID is usually 6 digits. Could you confirm it?"
    else:
        response = f"I heard {opid_candidate}. Could you confirm your 6-digit OPID?"
    return _dialogue_response(response, ["opid"], "collecting_slots", "confirm_opid")


def _dialogue_response(response: str, missing_slots: list[str], workflow_state: str, next_action: str) -> dict[str, Any]:
    return {
        "response": response,
        "missing_slots": missing_slots,
        "workflow_state": workflow_state,
        "next_action": next_action,
        "last_assistant_question": response,
    }


def _appointment_missing_slots(slots: dict[str, Any]) -> list[str]:
    missing = []
    if not slots.get("opid"):
        missing.append("opid")
    if not slots.get("department") and not slots.get("doctor"):
        missing.append("department")
    if not slots.get("preferred_date"):
        missing.append("preferred_date")
    if not slots.get("preferred_time"):
        missing.append("preferred_time")
    return missing


def _extract_opid_candidate(message: str) -> str | None:
    text_without_times = re.sub(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", " ", message.lower())
    groups = re.findall(r"\d+", text_without_times)
    if not groups:
        return None
    if len(groups) == 1:
        return groups[0]
    combined = "".join(groups)
    if 3 <= len(combined) <= 8:
        return combined
    return None


def _extract_specialization(text_lower: str) -> str | None:
    aliases = {
        "dermat": "Dermatology",
        "skin": "Dermatology",
        "cardio": "Cardiology",
        "heart": "Cardiology",
        "pediatric": "Pediatrics",
        "paediatric": "Pediatrics",
        "child": "Pediatrics",
        "dental": "Dentistry",
        "dentist": "Dentistry",
        "general medicine": "General Medicine",
        "general": "General Medicine",
    }
    for token, label in aliases.items():
        if token in text_lower:
            return label
    return None


def _normalize_department(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower().strip()
    if "dermat" in lowered or "skin" in lowered:
        return "Dermatology"
    if "dent" in lowered:
        return "Dentistry"
    if "cardio" in lowered or "heart" in lowered:
        return "Cardiology"
    if "pediatric" in lowered or "paediatric" in lowered or "child" in lowered:
        return "Pediatrics"
    if "general" in lowered:
        return "General Medicine"
    return value[:1].upper() + value[1:]


def _extract_preferred_date(text_lower: str) -> str | None:
    if "today" in text_lower:
        return "today"
    if "tomorrow" in text_lower:
        return "tomorrow"
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
        if day in text_lower:
            return day.title()
    return None


def _extract_preferred_time(text_lower: str, existing_slots: dict[str, Any] | None = None) -> str | None:
    if "morning" in text_lower:
        return "morning"
    if "afternoon" in text_lower:
        return "afternoon"
    if "evening" in text_lower:
        return "evening"
    if "night" in text_lower:
        return "night"
    normalized = text_lower.replace("a.m.", "am").replace("p.m.", "pm").replace("a.m", "am").replace("p.m", "pm")
    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", normalized)
    if time_match:
        hour = int(time_match.group(1))
        minutes = time_match.group(2) or "00"
        meridiem = time_match.group(3).upper()
        return f"{hour}:{minutes} {meridiem}"
    if existing_slots and existing_slots.get("opid") and (existing_slots.get("department") or existing_slots.get("doctor")) and existing_slots.get("preferred_date"):
        bare_hour = re.fullmatch(r"\s*(\d{1,2})\s*", normalized)
        if bare_hour and 1 <= int(bare_hour.group(1)) <= 12:
            return f"{int(bare_hour.group(1))}:00 AM"
    return None


def _available_demo_slots(department: str | None, date_label: str | None) -> list[str]:
    department_key = (_normalize_department(department) or "Dermatology").lower()
    date_key = (date_label or "tomorrow").lower()
    return DEMO_APPOINTMENT_AVAILABILITY.get((department_key, date_key), [])


def _format_list(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _is_slot_like_reply(text_lower: str, slots: dict[str, Any]) -> bool:
    return bool(
        _extract_opid_candidate(text_lower)
        or _extract_specialization(text_lower)
        or _extract_preferred_date(text_lower)
        or _extract_preferred_time(text_lower)
        or slots.get("opid")
    )


def _mentions_appointment(text_lower: str) -> bool:
    return bool(re.search(r"\b(?:book|appointment|consultation)\b|ab ka appointment|doctor today", text_lower))


def _agent_greeting(agent: dict[str, Any], user: CurrentUser) -> str:
    first_name = (user.full_name or user.email or "there").split()[0]
    role = (agent.get("description") or "front desk receptionist").lower()
    hospital = user.hospital_name or "the clinic"
    return f"Hello {first_name}. I'm {agent.get('name')}, the {role} for {hospital}. How can I help you today?"


def _handoff_response(agent: dict[str, Any]) -> str:
    return agent.get("fallback_behavior") or "I can help with front desk requests, appointments, routing, and safe staff handoff."


def _kb_response(snippets: list[dict[str, Any]]) -> str:
    content = " ".join(str(snippet.get("content") or "") for snippet in snippets).strip()
    if not content:
        return "I could not find an approved answer for that. Would you like me to connect you to reception?"
    return f"Based on the clinic information I have: {content[:320]}"


def _is_generic_greeting(response: str | None) -> bool:
    lowered = (response or "").lower()
    return "i'm your hospital assistant" in lowered or "how can i help you today" == lowered.strip()


def _audio_suffix(filename: str | None, content_type: str | None) -> str:
    if filename:
        suffix = os.path.splitext(filename)[1]
        if suffix:
            return suffix
    return {
        "audio/webm": ".webm",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }.get(content_type or "", ".webm")


def _where_for_alias(where: str, alias: str) -> str:
    return where.replace("WHERE hospital_id = :hospital_id", f"WHERE {alias}.hospital_id = :hospital_id")


def _where_clause_for_alias(where: str, alias: str) -> str:
    return _where_for_alias(where, alias).replace("WHERE ", "", 1)


def _default_agent_specs() -> list[dict[str, Any]]:
    prompt = (
        "You are a hospital operations voice receptionist. Help with appointments, routing, reminders, billing callbacks, "
        "lead qualification, and FAQs. Do not diagnose, prescribe, or alter medical instructions. Escalate emergencies immediately."
    )
    return [
        {
            "name": "Emma",
            "description": "Front Desk Receptionist",
            "language": "en-IN",
            "voice_name": "Anaya",
            "greeting": "Hi, this is Emma from the front desk. I can help you book, reschedule, or reach the right person.",
            "system_prompt": prompt,
            "fallback_behavior": "Collect the caller request and transfer to staff when the patient needs clinical guidance.",
            "transfer_phone_number": None,
            "working_hours": {"weekdays": "09:00-18:00", "saturday": "09:00-13:00"},
        },
        {
            "name": "Maya",
            "description": "Appointment Coordinator",
            "language": "en-IN",
            "voice_name": "Meera",
            "greeting": "Hi, this is Maya. I can help find an appointment time and confirm the next step.",
            "system_prompt": prompt,
            "fallback_behavior": "Collect scheduling preferences and escalate clinical questions to staff.",
            "transfer_phone_number": None,
            "working_hours": {"weekdays": "09:00-18:00", "saturday": "09:00-13:00"},
        },
        {
            "name": "Sarah",
            "description": "Patient Follow-up Specialist",
            "language": "en-IN",
            "voice_name": "Kavya",
            "greeting": "Hi, this is Sarah. I can help with reminders, confirmations, and follow-up calls.",
            "system_prompt": prompt,
            "fallback_behavior": "Keep follow ups operational and avoid discussing clinical details.",
            "transfer_phone_number": None,
            "working_hours": {"weekdays": "10:00-17:00"},
        },
        {
            "name": "David",
            "description": "Department Routing Assistant",
            "language": "en-IN",
            "voice_name": "Arjun",
            "greeting": "Hi, this is David. I can understand what you need and connect you to the right department.",
            "system_prompt": prompt,
            "fallback_behavior": "Route urgent, billing, insurance, and clinical questions to the correct team.",
            "transfer_phone_number": None,
            "working_hours": {"weekdays": "09:00-18:00"},
        },
        {
            "name": "Priya",
            "description": "Patient Support Assistant",
            "language": "en-IN",
            "voice_name": "Rohan",
            "greeting": "Hi, this is Priya. I can answer front desk questions or arrange a staff callback.",
            "system_prompt": prompt,
            "fallback_behavior": "Capture the support request and schedule a callback when needed.",
            "transfer_phone_number": None,
            "working_hours": {"weekdays": "09:00-18:00", "saturday": "09:00-13:00"},
        },
    ]


def _get_owned_agent(agent_id: str, user: CurrentUser) -> dict[str, Any]:
    where, params = readable_hospital_filter(user)
    params["agent_id"] = agent_id
    with db_session() as db:
        row = db.execute(text(f"SELECT * FROM agents {where.replace('WHERE', 'WHERE id=:agent_id AND') if where else 'WHERE id=:agent_id'}"), params).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _json(row)


def _kb_snippets(hospital_id: str, message: str) -> list[dict[str, Any]]:
    terms = [term for term in message.lower().split() if len(term) > 3][:5]
    if not terms:
        return []
    condition = " OR ".join(f"lower(content) LIKE :term{i}" for i, _ in enumerate(terms))
    params = {f"term{i}": f"%{term}%" for i, term in enumerate(terms)}
    params["hospital_id"] = hospital_id
    with db_session() as db:
        rows = db.execute(text(f"SELECT document_id, content FROM knowledge_chunks WHERE hospital_id=:hospital_id AND ({condition}) LIMIT 3"), params).mappings().all()
    return [_json(row) for row in rows]
