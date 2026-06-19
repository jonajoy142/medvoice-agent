from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.routes_voice import voice_service
from app.repo import mock_db


client = TestClient(app)


def test_health_endpoint_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload


def test_voice_endpoint_accepts_voice_alias(monkeypatch):
    def fake_process_uploaded_voice(audio_path, session_id, voice, preferred_provider=None, persona_id=None, language=None):
        return {
            "session_id": session_id or "s1",
            "status": "success",
            "user_input": "hello",
            "intent": "greeting",
            "entities": {},
            "response": "Hello! How can I help you?",
            "action": "greet",
            "data": None,
            "voice_used": voice,
            "provider": preferred_provider or "local",
            "voice_persona": persona_id or "female_warm_indian",
            "language": language or "en-IN",
        }

    monkeypatch.setattr(voice_service, "process_uploaded_voice", fake_process_uploaded_voice)
    response = client.post(
        "/api/v1/voice",
        data={"session_id": "abc", "voice_type": "female"},
        files={"audio": ("voice-turn.webm", b"audio-bytes", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["voice_used"] == "female"


def test_appointments_endpoint_no_recursion_and_returns_payload():
    mock_db.appointments.clear()
    mock_db.add_appointment({"patient_opid": "411326", "patient_name": "Jonah Carlisle", "status": "confirmed"})

    response = client.get("/api/v1/appointments")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert isinstance(payload["appointments"], list)
