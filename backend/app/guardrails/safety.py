from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


EMERGENCY_PATTERNS = [
    r"\b(chest pain|cannot breathe|can't breathe|shortness of breath)\b",
    r"\b(unconscious|not waking|severe bleeding|stroke|heart attack|seizure)\b",
    r"\b(suicide|self harm|poison|overdose)\b",
    r"\b(emergency|critical|life threatening)\b",
]

FORBIDDEN_MEDICAL_PATTERNS = [
    r"\b(diagnose|diagnosis|what disease|do i have)\b",
    r"\b(prescribe|prescription|medicine should i take|dosage|dose)\b",
    r"\b(stop taking|change my medicine|increase.*medicine|decrease.*medicine)\b",
    r"\b(alter.*doctor|ignore.*doctor|change.*doctor.*instruction)\b",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"system prompt",
    r"developer message",
    r"reveal.*secret",
    r"act as (?!a hospital)",
    r"jailbreak",
]

PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(OPID\s*)?\d{6}\b", re.I), "[REDACTED_OPID]"),
]


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    escalation_required: bool
    reason: str
    safe_response: str | None = None
    flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SafetyGuardrails:
    emergency_response = (
        "This may be an emergency. I am escalating to hospital staff now. "
        "Please call local emergency services or go to the nearest emergency department immediately."
    )
    medical_boundary_response = (
        "I cannot diagnose, prescribe medicine, or change doctor instructions. "
        "I can connect you with hospital staff or help with appointments and administrative questions."
    )
    low_confidence_response = (
        "I am not confident enough to answer that safely. I will route this to hospital staff for help."
    )

    def evaluate_input(self, text: str, *, intent_confidence: float | None = None) -> GuardrailDecision:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in EMERGENCY_PATTERNS):
            return GuardrailDecision(False, True, "emergency_detected", self.emergency_response, ["emergency"])
        if any(re.search(pattern, lowered) for pattern in FORBIDDEN_MEDICAL_PATTERNS):
            return GuardrailDecision(False, True, "medical_boundary", self.medical_boundary_response, ["medical_boundary"])
        if intent_confidence is not None and intent_confidence < settings.low_confidence_threshold:
            return GuardrailDecision(False, True, "low_intent_confidence", self.low_confidence_response, ["low_confidence"])
        return GuardrailDecision(True, False, "allowed")

    def evaluate_rag(self, *, confidence: float, answer: str) -> GuardrailDecision:
        if confidence < settings.rag_confidence_threshold:
            return GuardrailDecision(False, True, "low_rag_confidence", self.low_confidence_response, ["low_rag_confidence"])
        if self.has_prompt_injection(answer):
            return GuardrailDecision(False, True, "kb_prompt_injection", self.low_confidence_response, ["prompt_injection"])
        return GuardrailDecision(True, False, "allowed")

    def has_prompt_injection(self, text: str) -> bool:
        lowered = text.lower()
        return any(re.search(pattern, lowered) for pattern in PROMPT_INJECTION_PATTERNS)

    def redact(self, text: str) -> str:
        redacted = text
        for pattern, replacement in PII_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        return redacted


safety_guardrails = SafetyGuardrails()
