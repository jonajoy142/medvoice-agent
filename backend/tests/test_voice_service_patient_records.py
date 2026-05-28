import requests

from app.llm.deterministic_provider import DeterministicLLMProvider
from app.llm.provider_factory import get_llm_provider
from app.services.llm_service import LLMService
from app.services.voice_service import VoiceService


class SilentProvider:
    name = "local"

    def transcribe(self, audio_path, language):
        return ""

    def synthesize(self, text, voice, language, speed):
        return None


def test_latest_chart_request_asks_for_verification_without_llm(monkeypatch):
    def fail_if_llm_called(*args, **kwargs):
        raise AssertionError("patient record lookup should not call the LLM")

    monkeypatch.setattr("app.services.voice_service.llm_service.generate_reply", fail_if_llm_called)
    monkeypatch.setattr("app.services.voice_service.get_voice_provider", lambda preferred=None: SilentProvider())

    result = VoiceService().process_text(
        "Check my latest chart earlier.",
        session_id="patient-record-missing-verification",
    )

    assert result["status"] == "success"
    assert result["intent"] == "patient_lookup"
    assert result["action"] == "request_patient_verification"
    assert "verified patient ID or phone number plus DOB" in result["response"]
    assert result["structured_data"] == {"missing": ["verified_patient_identifier"]}
    assert result["stage_timings"]["llm_latency_ms"] == 0.0


def test_missing_patient_verification_does_not_hallucinate_records(monkeypatch):
    monkeypatch.setattr("app.services.voice_service.get_voice_provider", lambda preferred=None: SilentProvider())

    result = VoiceService().process_text(
        "Please check my medical chart.",
        session_id="patient-record-no-hallucination",
    )

    response = result["response"].lower()
    assert result["data"] == {"missing": ["verified_patient_identifier"]}
    assert "jonah" not in response
    assert "sarah" not in response
    assert "eczema" not in response
    assert "skin allergy" not in response
    assert "acne" not in response


def test_ollama_unavailable_returns_deterministic_healthcare_fallback(monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.exceptions.ConnectionError("ollama offline")

    monkeypatch.setattr("app.llm.ollama_provider.requests.post", unavailable)

    reply = LLMService(provider_name="ollama").generate_reply(
        user_text="What services do you provide?",
        history=[],
        session_id="llm-unavailable",
    )

    assert reply == DeterministicLLMProvider().generate(
        type("Request", (), {"user_text": "What services do you provide?"})()
    )
    assert "AI service" not in reply


def test_missing_hosted_api_key_uses_deterministic_provider():
    import app.llm.provider_factory as provider_factory

    object.__setattr__(provider_factory.settings, "openai_api_key", "")
    provider = get_llm_provider("openai")

    assert provider.name == "deterministic"
    assert provider.is_available() is True


def test_appointment_and_availability_do_not_need_llm(monkeypatch):
    def fail_if_llm_called(*args, **kwargs):
        raise AssertionError("deterministic appointment and availability flows should not call the LLM")

    monkeypatch.setattr("app.services.voice_service.llm_service.generate_reply", fail_if_llm_called)
    monkeypatch.setattr("app.services.voice_service.get_voice_provider", lambda preferred=None: SilentProvider())

    appointment = VoiceService().process_text(
        "Book an appointment with a dermatologist.",
        session_id="appointment-no-llm",
    )
    availability = VoiceService().process_text(
        "Check availability for dermatologist.",
        session_id="availability-no-llm",
    )

    assert appointment["intent"] == "book_appointment"
    assert appointment["action"] == "request_opid"
    assert "Jonah" not in appointment["response"]
    assert availability["intent"] == "check_availability"
    assert availability["action"] == "availability_info"
    assert "Medical history" not in availability["response"]


def test_static_faq_does_not_need_llm(monkeypatch):
    def fail_if_llm_called(*args, **kwargs):
        raise AssertionError("static FAQ flow should not call the LLM")

    monkeypatch.setattr("app.services.voice_service.llm_service.generate_reply", fail_if_llm_called)
    monkeypatch.setattr("app.services.voice_service.get_voice_provider", lambda preferred=None: SilentProvider())

    result = VoiceService().process_text(
        "What are your visiting hours?",
        session_id="faq-no-llm",
    )

    assert result["intent"] == "faq"
    assert result["action"] == "faq_answer"
    assert result["structured_data"] == {"source": "static_faq", "topic": "visiting_hours"}


def test_generic_unsupported_query_returns_safe_fallback(monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.exceptions.ConnectionError("provider offline")

    monkeypatch.setattr("app.llm.ollama_provider.requests.post", unavailable)

    reply = LLMService(provider_name="ollama").generate_reply(
        user_text="Can you explain quantum mechanics?",
        history=[],
        session_id="unsupported-fallback",
    )

    assert reply == "I can help with appointments, doctor availability, or verified patient lookup. Please clarify your request."
    assert "AI service" not in reply
