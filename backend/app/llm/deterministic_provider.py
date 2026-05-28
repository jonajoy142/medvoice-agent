from __future__ import annotations

from app.llm.base import LLMRequest


class DeterministicLLMProvider:
    name = "deterministic"

    def generate(self, request: LLMRequest) -> str:
        text = request.user_text.lower()
        if any(term in text for term in ["chart", "record", "records", "report", "previous visit"]):
            return (
                "I can help with that. To access a patient chart, I'll need a verified patient ID "
                "or phone number plus date of birth first."
            )
        if any(term in text for term in ["appointment", "book", "schedule"]):
            return "I can help with appointments. Please provide the patient ID and preferred specialty or time."
        if any(term in text for term in ["available", "availability", "doctor", "specialist"]):
            return "I can check doctor availability. Please tell me the specialty you need."
        if any(term in text for term in ["hours", "visiting", "location", "address"]):
            return "I can help with hospital questions. Please ask for the specific detail you need."
        return "I can help with appointments, doctor availability, or verified patient lookup. Please clarify your request."

    def is_available(self) -> bool:
        return True
