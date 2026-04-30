from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.voice_service import VoiceService
from app.repo.mock_db import get_doctors, get_appointments, add_appointment, get_patient
from app.services.llm_service import llm_service

router = APIRouter()
voice_service = VoiceService()

class VoiceRequest(BaseModel):
    session_id: Optional[str] = None
    voice: str = "female"

class AppointmentRequest(BaseModel):
    patient_opid: str
    specialization: str
    preferred_time: str
    doctor_name: Optional[str] = None

@router.post("/voice")
async def handle_voice(request: VoiceRequest):
    """Process voice input and return response"""
    try:
        # Run voice processing in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            voice_service.process_voice,
            request.session_id,
            request.voice
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/availability")
async def check_availability(specialization: Optional[str] = None):
    """Check doctor availability"""
    try:
        if specialization:
            doctors = get_doctors(specialization)
            if not doctors:
                return {"message": f"No {specialization} doctors available", "doctors": []}
        else:
            doctors = get_doctors()
            # Flatten all doctors
            all_doctors = []
            for spec, doc_list in doctors.items():
                for doctor in doc_list:
                    doctor["specialization"] = spec
                    all_doctors.append(doctor)
            doctors = all_doctors
        
        return {
            "specialization": specialization,
            "doctors": doctors,
            "count": len(doctors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/appointment")
async def book_appointment(request: AppointmentRequest):
    """Book a new appointment"""
    try:
        # Validate patient
        patient = get_patient(request.patient_opid)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Check doctor availability
        doctors = get_doctors(request.specialization)
        if not doctors:
            raise HTTPException(status_code=404, detail="No doctors available for this specialization")
        
        # Create appointment
        appointment_data = {
            "patient_opid": request.patient_opid,
            "patient_name": patient["name"],
            "specialization": request.specialization,
            "requested_time": request.preferred_time,
            "doctor_name": request.doctor_name or doctors[0]["name"],
            "status": "confirmed"
        }
        
        appointment = add_appointment(appointment_data)
        
        return {
            "message": "Appointment booked successfully",
            "appointment": appointment
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/appointments")
async def get_appointments(patient_opid: Optional[str] = None):
    """Get appointments, optionally filtered by patient"""
    try:
        if patient_opid:
            # Validate patient
            patient = get_patient(patient_opid)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            appointments = [apt for apt in get_appointments() if apt.get("patient_opid") == patient_opid]
        else:
            appointments = get_appointments()
        
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
async def get_patient_info(opid: str):
    """Get patient information by OPID"""
    try:
        patient = get_patient(opid)
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
        ollama_status = llm_service.check_connection()
        return {
            "status": "healthy",
            "ollama_connected": ollama_status,
            "services": {
                "voice_pipeline": True,
                "intent_service": True,
                "mock_db": True,
                "logger": True
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }