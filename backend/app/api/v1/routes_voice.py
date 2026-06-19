import os
import tempfile

from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.services.voice_service import VoiceService
from app.services.llm_service import llm_service
from app.core.auth import require_api_key
from app.core.config import settings
from app.services.appointment_service import appointment_service
from app.services.availability_service import availability_service
from app.services.patient_service import patient_service
from app.db.session import check_db_connection
from app.voice.providers import get_voice_provider

router = APIRouter()
voice_service = VoiceService()

class VoiceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: Optional[str] = None
    voice: str = Field(default="female", alias="voice_type")
    voice_provider: Optional[str] = None
    persona_id: Optional[str] = None
    language: Optional[str] = None

class AppointmentRequest(BaseModel):
    patient_opid: str
    specialization: str
    preferred_time: str
    doctor_name: Optional[str] = None

class DemoRequest(BaseModel):
    scenario: str
    session_id: Optional[str] = None
    voice_provider: Optional[str] = None
    persona_id: Optional[str] = None
    language: Optional[str] = None


DEMO_SCENARIOS = {
    "book_cardiology_appointment": "Book cardiology appointment for patient OPID 411326 tomorrow at 10 am",
    "doctor_availability": "Check availability for dermatologist",
    "verified_patient_lookup": "Lookup patient record for OPID 411326",
    "visiting_hours_faq": "What are your visiting hours?",
    "emergency_escalation": "I have severe chest pain and cannot breathe",
    "hindi_english_appointment": "Mujhe kal dermatology appointment book karna hai OPID 411326",
    "voice_persona_preview": "Introduce yourself as a hospital receptionist",
    "database_provider_fallback": "Show me provider fallback status and database health",
}

@router.post("/voice")
async def handle_voice(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    voice: str = Form("female"),
    voice_type: Optional[str] = Form(None),
    voice_provider: Optional[str] = Form(None),
    persona_id: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
):
    """Process uploaded browser microphone audio and return response."""
    audio_path = None
    try:
        suffix = _audio_suffix(audio.filename, audio.content_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            audio_path = temp_file.name
            temp_file.write(await audio.read())

        # Run voice processing in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            voice_service.process_uploaded_voice,
            audio_path,
            session_id,
            voice_type or voice,
            voice_provider,
            persona_id,
            language,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if audio_path:
                os.unlink(audio_path)
        except Exception:
            pass


@router.post("/voice/stream")
async def handle_voice_stream(request: VoiceRequest):
    """
    Streaming-ready endpoint surface for future SSE/WebSocket rollout.
    Currently returns the same contract so frontend can stay streaming-ready.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        voice_service.process_voice,
        request.session_id,
        request.voice,
        request.voice_provider,
        request.persona_id,
        request.language,
    )
    result["streaming_ready"] = True
    return result


def _audio_suffix(filename: Optional[str], content_type: Optional[str]) -> str:
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


@router.post("/voice/demo")
async def run_demo_scenario(request: DemoRequest):
    scenario_input = DEMO_SCENARIOS.get(request.scenario)
    if not scenario_input:
        raise HTTPException(status_code=400, detail="Unknown demo scenario")
    result = voice_service.process_text(
        user_text=scenario_input,
        session_id=request.session_id,
        preferred_provider=request.voice_provider,
        persona_id=request.persona_id,
        language=request.language,
    )
    result["demo_scenario"] = request.scenario
    return result

@router.get("/availability")
async def check_availability(specialization: Optional[str] = None):
    """Check doctor availability"""
    try:
        result = availability_service.get(specialization)
        if specialization and result["count"] == 0:
            return {"message": f"No {specialization} doctors available", "doctors": []}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/appointment")
async def book_appointment(request: AppointmentRequest, _: None = Depends(require_api_key)):
    """Book a new appointment"""
    try:
        patient = patient_service.get_by_opid(request.patient_opid)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        appointment = appointment_service.book(
            patient_opid=request.patient_opid,
            specialization=request.specialization,
            preferred_time=request.preferred_time,
            doctor_name=request.doctor_name,
        )
        
        return {
            "message": "Appointment booked successfully",
            "appointment": appointment
        }
    except HTTPException:
        raise
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/appointments")
async def get_appointments_route(
    patient_opid: Optional[str] = None,
    _: None = Depends(require_api_key),
):
    """Get appointments, optionally filtered by patient"""
    try:
        if patient_opid:
            patient = patient_service.get_by_opid(patient_opid)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
        appointments = appointment_service.list(patient_opid=patient_opid)
        
        return {
            "patient_opid": patient_opid,
            "appointments": appointments,
            "count": len(appointments)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patient/{opid}")
async def get_patient_info(opid: str, _: None = Depends(require_api_key)):
    """Get patient information by OPID"""
    try:
        patient = patient_service.get_by_opid(opid)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return {
            "opid": opid,
            "patient": patient
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        llm_status = llm_service.provider_status()
        sarvam_configured = bool(settings.sarvam_api_key and settings.sarvam_stt_endpoint and settings.sarvam_tts_endpoint)
        return {
            "status": "healthy",
            "ollama_connected": llm_status["active"] == "ollama" and llm_status["available"],
            "llm_provider": llm_status,
            "database_connected": check_db_connection(),
            "provider_requested": settings.voice_provider,
            "provider_active": get_voice_provider().name,
            "provider": "sarvam" if sarvam_configured else "browser_fallback",
            "voice_service_configured": _voice_service_configured(),
            "sarvam_configured": sarvam_configured,
            "sarvamConfigured": sarvam_configured,
            "sarvam_missing": [
                name for name, value in [
                    ("SARVAM_API_KEY", settings.sarvam_api_key),
                    ("SARVAM_STT_ENDPOINT", settings.sarvam_stt_endpoint),
                    ("SARVAM_TTS_ENDPOINT", settings.sarvam_tts_endpoint),
                ] if not value
            ],
            "services": {
                "voice_pipeline": True,
                "intent_service": True,
                "repository_layer": True,
                "logger": True
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def _voice_service_configured() -> bool:
    if settings.voice_provider == "sarvam":
        return bool(settings.sarvam_api_key and settings.sarvam_stt_endpoint and settings.sarvam_tts_endpoint)
    if settings.voice_provider == "local":
        return bool(settings.enable_local_stt and settings.enable_local_tts)
    if settings.voice_provider == "openai":
        return bool(settings.openai_api_key)
    return False
