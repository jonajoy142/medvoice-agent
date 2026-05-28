import os
import tempfile
import time
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logger import conversation_logger
from app.repositories import patient_repository, session_repository
from app.services.intent_service import intent_service
from app.services.llm_service import llm_service
from app.voice.personas import get_persona
from app.voice.providers import get_voice_provider


class VoiceService:
    def process_voice(
        self,
        session_id: Optional[str] = None,
        voice: str = "female",
        preferred_provider: Optional[str] = None,
        persona_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.core.voice_pipeline import record_audio

        started_at = time.perf_counter()
        provider = get_voice_provider(preferred_provider)
        active_persona = persona_id or settings.default_voice_persona
        target_language = language or str(get_persona(active_persona).get("language", settings.default_language))

        session_id, session = self._ensure_session(session_id)

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                audio_path = temp_file.name
            file = record_audio(audio_path)
            if not file:
                return self._empty_response(session_id, provider.name, active_persona, target_language, started_at)

            stt_start = time.perf_counter()
            text = provider.transcribe(file, target_language)
            stt_latency_ms = round((time.perf_counter() - stt_start) * 1000, 2)
            if not text:
                return self._empty_response(
                    session_id, provider.name, active_persona, target_language, started_at, stt_latency_ms
                )

            result = self._process_text_internal(
                user_text=text,
                session_id=session_id,
                session=session,
                voice=voice,
                preferred_provider=preferred_provider,
                persona_id=active_persona,
                language=target_language,
                stt_latency_ms=stt_latency_ms,
                started_at=started_at,
            )
            return result
        except Exception as exc:
            return self._error_response(session_id, str(exc), provider.name, active_persona, target_language, started_at)
        finally:
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def process_text(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        persona_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        active_persona = persona_id or settings.default_voice_persona
        target_language = language or str(get_persona(active_persona).get("language", settings.default_language))
        session_id, session = self._ensure_session(session_id)
        return self._process_text_internal(
            user_text=user_text,
            session_id=session_id,
            session=session,
            voice="female",
            preferred_provider=preferred_provider,
            persona_id=active_persona,
            language=target_language,
            stt_latency_ms=0.0,
            started_at=started_at,
        )

    def _process_text_internal(
        self,
        user_text: str,
        session_id: str,
        session: Dict[str, Any],
        voice: str,
        preferred_provider: Optional[str],
        persona_id: str,
        language: str,
        stt_latency_ms: float,
        started_at: float,
    ) -> Dict[str, Any]:
        provider = get_voice_provider(preferred_provider)
        provider_used = provider.name
        persona = get_persona(persona_id)
        session_repo = session_repository()
        llm_latency_ms = 0.0
        tts_latency_ms = 0.0

        intent = intent_service.detect_intent(user_text)
        entities = intent_service.extract_entities(user_text)
        if self._is_emergency(user_text):
            intent = "emergency_escalation"
            intent_result = {
                "action": "emergency_escalation",
                "response": "This may be urgent. Please call emergency services or visit the nearest emergency room now.",
                "data": {"escalation": True, "severity": "high"},
            }
        else:
            intent_result = intent_service.route_intent(intent, entities, session)

        if "opid" in entities and not session.get("opid"):
            session_repo.update_session(session_id, {"opid": entities["opid"]})
            session["opid"] = entities["opid"]
            patient = patient_repository().get_patient(entities["opid"])
            if patient:
                session_repo.update_session(session_id, {"patient_name": patient["name"]})
                session["patient_name"] = patient["name"]

        if intent_result["action"] in {"general", "greet", "goodbye"}:
            llm_start = time.perf_counter()
            reply = llm_service.generate_reply(
                user_text=user_text,
                history=session.get("conversation", []),
                session_id=session_id,
                context=self._build_context(entities, session),
            )
            llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)
        else:
            reply = intent_result["response"]

        conversation = session.get("conversation", [])
        conversation.append({"role": "user", "content": user_text})
        conversation.append({"role": "assistant", "content": reply})
        session_repo.update_session(session_id, {"conversation": conversation})

        conversation_logger.log_interaction(
            session_id=session_id,
            user_text=user_text,
            ai_response=reply,
            intent=intent,
            entities=entities,
            action=intent_result["action"],
            metadata={"provider": provider_used, "persona": persona_id, "data": intent_result.get("data")},
        )

        try:
            tts_start = time.perf_counter()
            provider.synthesize(reply, voice, language, float(persona.get("speaking_speed", 1.0)))
            tts_latency_ms = round((time.perf_counter() - tts_start) * 1000, 2)
        except Exception:
            if provider.name != "local":
                local_provider = get_voice_provider("local")
                provider_used = "local"
                local_provider.synthesize(reply, voice, settings.default_language, 1.0)

        total_latency = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "session_id": session_id,
            "status": "success",
            "user_input": user_text,
            "intent": intent,
            "confidence": self._intent_confidence(intent),
            "spoken_response": reply,
            "display_response": reply,
            "response": reply,
            "structured_data": intent_result.get("data") or {},
            "data": intent_result.get("data"),
            "guardrail_status": "active",
            "provider": provider_used,
            "persona": persona_id,
            "voice_persona": persona_id,
            "language": language,
            "latency_ms": total_latency,
            "stage_timings": {
                "stt_latency_ms": stt_latency_ms,
                "llm_latency_ms": llm_latency_ms,
                "tts_latency_ms": tts_latency_ms,
                "total_latency_ms": total_latency,
            },
            "requires_confirmation": intent in {"book_appointment", "check_availability"},
            "safe_to_speak": True,
            "action": intent_result["action"],
            "entities": entities,
        }

    def _ensure_session(self, session_id: Optional[str]) -> tuple[str, Dict[str, Any]]:
        repo = session_repository()
        if session_id:
            session = repo.get_session(session_id)
            if session:
                return session_id, session
        new_id = session_id or conversation_logger.generate_session_id()
        return new_id, repo.create_session(new_id)

    def _build_context(self, entities: Dict[str, Any], session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        context: Dict[str, Any] = {}
        if "opid" in entities:
            patient = patient_repository().get_patient(entities["opid"])
            if patient:
                context["patient"] = patient
                context["opid"] = entities["opid"]
        if "specialization" in entities:
            from app.repositories import doctor_repository

            doctors = doctor_repository().get_doctors(entities["specialization"])
            if doctors:
                context["doctors"] = doctors
        if session.get("patient_name"):
            context["patient_name"] = session["patient_name"]
        return context or None

    def _empty_response(
        self,
        session_id: str,
        provider: str,
        persona_id: str,
        language: str,
        started_at: float,
        stt_latency_ms: float = 0.0,
    ) -> Dict[str, Any]:
        total = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "session_id": session_id,
            "status": "no_audio",
            "intent": "general",
            "confidence": 0.4,
            "spoken_response": "I did not hear anything clearly. Please try again.",
            "display_response": "I did not hear anything clearly. Please try again.",
            "structured_data": {},
            "guardrail_status": "active",
            "provider": provider,
            "persona": persona_id,
            "language": language,
            "latency_ms": total,
            "stage_timings": {
                "stt_latency_ms": stt_latency_ms,
                "llm_latency_ms": 0.0,
                "tts_latency_ms": 0.0,
                "total_latency_ms": total,
            },
            "requires_confirmation": False,
            "safe_to_speak": True,
        }

    def _error_response(
        self, session_id: str, error: str, provider: str, persona_id: str, language: str, started_at: float
    ) -> Dict[str, Any]:
        total = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "session_id": session_id,
            "status": "error",
            "intent": "general",
            "confidence": 0.2,
            "spoken_response": "Something went wrong. Please try again.",
            "display_response": "Something went wrong. Please try again.",
            "structured_data": {"error": error},
            "guardrail_status": "active",
            "provider": provider,
            "persona": persona_id,
            "language": language,
            "latency_ms": total,
            "stage_timings": {
                "stt_latency_ms": 0.0,
                "llm_latency_ms": 0.0,
                "tts_latency_ms": 0.0,
                "total_latency_ms": total,
            },
            "requires_confirmation": False,
            "safe_to_speak": False,
        }

    @staticmethod
    def _is_emergency(text: str) -> bool:
        lowered = text.lower()
        return any(
            term in lowered
            for term in ["emergency", "chest pain", "cannot breathe", "unconscious", "severe bleeding", "stroke"]
        )

    @staticmethod
    def _intent_confidence(intent: str) -> float:
        if intent in {"book_appointment", "check_availability", "patient_lookup", "doctor_info", "emergency_escalation"}:
            return 0.92
        if intent in {"greeting", "goodbye"}:
            return 0.88
        return 0.74
