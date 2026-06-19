from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


WorkflowValidator = Callable[[dict], list[str]]


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    allowed_intents: set[str]
    required_slots: tuple[str, ...]
    completion_action: str
    escalation_triggers: tuple[str, ...]
    safe_templates: dict[str, str]
    validate: WorkflowValidator | None = None

    def missing_slots(self, slots: dict) -> list[str]:
        missing = [slot for slot in self.required_slots if not slots.get(slot)]
        if self.validate:
            missing.extend(self.validate(slots))
        return list(dict.fromkeys(missing))


@dataclass(frozen=True)
class WorkflowResult:
    workflow: str
    state: str
    missing_slots: list[str] = field(default_factory=list)
    response_template: str | None = None
    escalation_required: bool = False


class WorkflowEngine:
    def __init__(self, workflows: dict[str, WorkflowDefinition] | None = None) -> None:
        self.workflows = workflows or DEFAULT_WORKFLOWS

    def route(self, intent: str, slots: dict) -> WorkflowResult:
        workflow = self._find_workflow(intent)
        if workflow is None:
            return WorkflowResult("human_handoff", "escalated", escalation_required=True, response_template="handoff")
        missing = workflow.missing_slots(slots)
        if missing:
            return WorkflowResult(workflow.name, "collecting_slots", missing, "missing_slots")
        return WorkflowResult(workflow.name, "ready_to_complete", [], workflow.completion_action)

    def _find_workflow(self, intent: str) -> WorkflowDefinition | None:
        for workflow in self.workflows.values():
            if intent in workflow.allowed_intents:
                return workflow
        return None


def _phone_validator(slots: dict) -> list[str]:
    phone = str(slots.get("phone") or "")
    return [] if not phone or len("".join(ch for ch in phone if ch.isdigit())) >= 10 else ["valid_phone"]


DEFAULT_WORKFLOWS: dict[str, WorkflowDefinition] = {
    "appointment_booking": WorkflowDefinition(
        name="appointment_booking",
        allowed_intents={"book_appointment"},
        required_slots=("patient_identifier", "department_or_specialization", "preferred_time"),
        completion_action="appointment_booked",
        escalation_triggers=("no_matching_doctor", "slot_conflict", "low_confidence"),
        safe_templates={"missing_slots": "I need patient ID, department, and preferred time to request the appointment."},
    ),
    "appointment_reschedule": WorkflowDefinition(
        name="appointment_reschedule",
        allowed_intents={"reschedule_appointment"},
        required_slots=("appointment_id", "preferred_time"),
        completion_action="appointment_rescheduled",
        escalation_triggers=("appointment_not_found", "slot_conflict"),
        safe_templates={"missing_slots": "I need the appointment reference and preferred new time."},
    ),
    "patient_intake": WorkflowDefinition(
        name="patient_intake",
        allowed_intents={"patient_intake"},
        required_slots=("patient_identifier", "visit_reason", "consent"),
        completion_action="intake_recorded",
        escalation_triggers=("emergency", "medical_advice_requested"),
        safe_templates={"missing_slots": "I can collect visit intake after patient identity and consent are confirmed."},
    ),
    "follow_up": WorkflowDefinition(
        name="follow_up",
        allowed_intents={"follow_up"},
        required_slots=("patient_identifier", "doctor_approved_script_id"),
        completion_action="follow_up_logged",
        escalation_triggers=("worsening_symptoms", "medical_question"),
        safe_templates={"missing_slots": "Follow-up calls require a doctor-approved script."},
    ),
    "reminder": WorkflowDefinition(
        name="reminder",
        allowed_intents={"medicine_reminder", "visit_reminder"},
        required_slots=("patient_identifier", "doctor_approved_script_id"),
        completion_action="reminder_delivered",
        escalation_triggers=("script_missing", "medical_question"),
        safe_templates={"missing_slots": "Reminder calls can only use doctor-approved scripted content."},
    ),
    "lab_report": WorkflowDefinition(
        name="lab_report",
        allowed_intents={"lab_report_ready"},
        required_slots=("patient_identifier", "report_reference"),
        completion_action="lab_report_notified",
        escalation_triggers=("identity_not_verified"),
        safe_templates={"missing_slots": "I need verified identity before discussing report readiness."},
    ),
    "faq": WorkflowDefinition(
        name="faq",
        allowed_intents={"faq"},
        required_slots=("grounded_answer",),
        completion_action="faq_answered",
        escalation_triggers=("low_rag_confidence", "kb_gap"),
        safe_templates={"missing_slots": "I could not find a grounded answer in the hospital knowledge base."},
    ),
    "department_routing": WorkflowDefinition(
        name="department_routing",
        allowed_intents={"department_routing", "doctor_info", "check_availability"},
        required_slots=("department_or_specialization",),
        completion_action="routed_to_department",
        escalation_triggers=("unknown_department"),
        safe_templates={"missing_slots": "Which department or specialty should I route you to?"},
    ),
    "billing_reminder": WorkflowDefinition(
        name="billing_reminder",
        allowed_intents={"billing_payment_reminder"},
        required_slots=("patient_identifier", "payment_reference"),
        completion_action="billing_reminder_delivered",
        escalation_triggers=("billing_dispute", "medical_content_detected"),
        safe_templates={"missing_slots": "Billing reminders require a billing reference and must not include medical advice."},
    ),
    "emergency_escalation": WorkflowDefinition(
        name="emergency_escalation",
        allowed_intents={"emergency_escalation"},
        required_slots=(),
        completion_action="escalated_to_staff",
        escalation_triggers=("always",),
        safe_templates={"escalate": "This may be urgent. I am escalating immediately."},
    ),
    "human_handoff": WorkflowDefinition(
        name="human_handoff",
        allowed_intents={"human_handoff", "complaint", "low_confidence"},
        required_slots=(),
        completion_action="escalated_to_staff",
        escalation_triggers=("always",),
        safe_templates={"handoff": "I will connect you with hospital staff."},
        validate=_phone_validator,
    ),
}


workflow_engine = WorkflowEngine()
