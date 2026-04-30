from fastapi import FastAPI
from app.api.v1.routes_voice import router as voice_router

app = FastAPI(title="MedVoice AI")

app.include_router(voice_router, prefix="/api/v1")