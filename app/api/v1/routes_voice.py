from fastapi import APIRouter
from app.services.voice_service import VoiceService

router = APIRouter()
voice_service = VoiceService()

@router.post("/voice")
def handle_voice():
    return voice_service.process_voice()