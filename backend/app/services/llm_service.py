from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.llm.base import LLMRequest
from app.llm.deterministic_provider import DeterministicLLMProvider
from app.llm.provider_factory import get_llm_provider

SYSTEM_PROMPT = """
You are a hospital receptionist.

IMPORTANT: NEVER invent patient data, doctor names, or medical information.
Only use data provided in the context from the database.

RULES:
- Use only provided patient/doctor data
- Keep answers under 12 words
- Speak naturally and professionally
- Avoid repetition
- Use "Dr. [Name]" not "Dr Dr"
- Ask for verified patient identification before any chart or record lookup
"""


class LLMService:
    def __init__(self, provider_name: Optional[str] = None):
        self.provider_name = provider_name or settings.llm_provider
        self.max_history = 3

    def generate_reply(
        self,
        user_text: str,
        history: List[Dict[str, str]],
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate optional phrasing through the configured LLM provider.

        Safety-critical healthcare workflows are routed before this service.
        This layer only improves generic wording and always falls back to the
        deterministic provider when hosted/local LLMs are unavailable.
        """
        prompt = self._build_prompt(user_text, history, context)
        request = LLMRequest(user_text=user_text, prompt=prompt, context=context)
        provider = get_llm_provider(self.provider_name)

        try:
            reply = provider.generate(request).strip()
            if not reply:
                raise RuntimeError(f"{provider.name} returned an empty response.")
            return reply
        except Exception as exc:
            fallback = DeterministicLLMProvider()
            reply = fallback.generate(request)
            return reply

    def _build_prompt(
        self,
        user_text: str,
        history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        return f"""
{SYSTEM_PROMPT}

{self._build_context(context)}

Recent Conversation:
{self._build_history(history)}

User: {user_text}
Assistant:
""".strip()

    def _build_history(self, history: List[Dict[str, str]]) -> str:
        if not history:
            return "No previous conversation."

        recent_history = history[-self.max_history:] if len(history) > self.max_history else history
        history_lines = []
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                history_lines.append(f"{role.title()}: {content}")

        return "\n".join(history_lines)

    def _build_context(self, context: Optional[Dict[str, Any]]) -> str:
        if not context:
            return "No specific context available."

        context_parts = []
        if "patient" in context:
            patient = context["patient"]
            context_parts.append(
                f"Current Patient: {patient.get('name', 'Unknown')} (OPID: {context.get('opid', 'Unknown')})"
            )
            context_parts.append(f"Medical History: {', '.join(patient.get('history', []))}")

        if "doctors" in context:
            doctors = context["doctors"]
            if isinstance(doctors, list):
                doctor_names = [f"Dr. {d.get('name', 'Unknown')}" for d in doctors]
                context_parts.append(f"Available Doctors: {', '.join(doctor_names)}")

        if "appointments" in context:
            appointments = context["appointments"]
            context_parts.append(f"Recent Appointments: {len(appointments)} found")

        return "\n".join(context_parts) if context_parts else "No specific context available."

    def check_connection(self) -> bool:
        provider = get_llm_provider(self.provider_name)
        try:
            return provider.is_available()
        except Exception:
            return False

    def provider_status(self) -> Dict[str, Any]:
        provider = get_llm_provider(self.provider_name)
        try:
            available = provider.is_available()
        except Exception:
            available = False
        return {
            "requested": self.provider_name,
            "active": provider.name,
            "available": available,
            "fallback_enabled": settings.llm_enable_fallback,
            "fallback_provider": settings.llm_fallback_provider,
        }


llm_service = LLMService()
